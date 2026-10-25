"""SC-02B: real application tables in a disposable PostgreSQL schema.

Only opt-in against the dedicated local retire_v2_scenario_test database.
No Alembic migration, no changes to retire_v2, and no permanent fixture rows.
"""
from datetime import date
from decimal import Decimal
import os
import uuid
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent, COMPONENT_CODES
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import _source_digest
from app.services.scenario_calculation_admission_service import assess


def _engine():
    url = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("dedicated PostgreSQL test URL not supplied")
    parsed = urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path != "/retire_v2_scenario_test":
        pytest.fail("Must use dedicated LOCAL retire_v2_scenario_test")
    engine = create_engine(url)
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    return engine


def test_real_scenario_admission_keeps_snapshot_under_concurrent_version_change():
    engine = _engine()
    schema = "sc02b_" + uuid.uuid4().hex[:16]
    tables = [
        Client.__table__, PensionProduct.__table__, PensionProductComponent.__table__,
        ScenarioDraft.__table__, ScenarioDraftDecision.__table__,
    ]
    try:
        with engine.begin() as setup:
            setup.execute(text(f'CREATE SCHEMA "{schema}"'))
            setup.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            for table in tables:
                table.create(setup, checkfirst=False)

            # Seed with SQLAlchemy Core: ORM construction here would configure
            # unrelated Client relationships outside this deliberately narrow fixture.
            setup.execute(Client.__table__.insert().values(
                client_id=900010, display_name="Isolation fixture",
                id_number="test-" + uuid.uuid4().hex[:20],
            ))
            setup.execute(PensionProduct.__table__.insert().values(
                product_id="sc02b-product", client_id=900010, source_kind="manual",
                source_identity="sc02b-source", product_name="Test source",
                product_type="Test product", account_reference="test", version=1,
                created_by="test", updated_by="test",
            ))
            setup.execute(PensionProductComponent.__table__.insert().values(
                component_id="sc02b-component", product_id="sc02b-product",
                component_code=COMPONENT_CODES[5], balance=Decimal("100.00"),
            ))
            # Use the same canonical source digest as the production draft service.
            with Session(bind=setup, autoflush=False) as seed_session:
                from sqlalchemy import select
                p = seed_session.scalar(select(PensionProduct).where(PensionProduct.product_id == "sc02b-product"))
                c = seed_session.scalar(select(PensionProductComponent).where(PensionProductComponent.component_id == "sc02b-component"))
                digest = _source_digest(p, c)
            setup.execute(ScenarioDraft.__table__.insert().values(
                scenario_id="sc02b-draft", client_id=900010, name="Test draft",
                status="draft", version=1, created_by="test", updated_by="test",
            ))
            setup.execute(ScenarioDraftDecision.__table__.insert().values(
                decision_id="sc02b-decision", scenario_id="sc02b-draft",
                source_product_id="sc02b-product", source_component_id="sc02b-component",
                component_code=COMPONENT_CODES[5], amount=Decimal("60.00"),
                action="pension", effective_date=date(2026, 10, 25),
                validation_state="unverified", product_version_at_review=1,
                source_fingerprint_at_review=digest,
            ))

        with engine.connect() as reader, engine.connect() as writer:
            reader.execute(text(f'SET search_path TO "{schema}", public'))
            reader.commit()
            writer.execute(text(f'SET search_path TO "{schema}", public'))
            writer.commit()

            reader.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            with Session(bind=reader, autoflush=False) as session:
                first = assess(session, 900010, "sc02b-draft")
            assert first["scenario_version"] == 1
            assert "SOURCE_STALE" not in {b["code"] for b in first["blockers"]}
            assert first["assessment_state"] == "blocked"
            assert first["financial_result"] is None

            writer.execute(text("UPDATE scenario_drafts SET version=2 WHERE scenario_id='sc02b-draft'"))
            writer.execute(text("UPDATE pension_products SET version=2 WHERE product_id='sc02b-product'"))
            writer.commit()

            with Session(bind=reader, autoflush=False) as session:
                same_snapshot = assess(session, 900010, "sc02b-draft")
            assert same_snapshot == first
            reader.rollback()

            reader.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            with Session(bind=reader, autoflush=False) as session:
                next_snapshot = assess(session, 900010, "sc02b-draft")
            assert next_snapshot["scenario_version"] == 2
            assert "SOURCE_STALE" in {b["code"] for b in next_snapshot["blockers"]}
            reader.rollback()
    finally:
        # The schema contains only test fixtures; the application and other schemas stay untouched.
        with engine.begin() as cleanup:
            cleanup.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
