"""SC-03D/D4: real PostgreSQL integration for the public inventory entrypoint.

Uses only the dedicated local retire_v2_scenario_test database and a unique
disposable schema; never modifies an application database.
"""
from datetime import date
from decimal import Decimal
import os
import uuid
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_planning_coverage_service import build_planning_coverage_snapshot

load_all_models()


def _url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("SCENARIO_TEST_POSTGRES_URL is required")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("requires local PostgreSQL")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("requires dedicated retire_v2_scenario_test database")
    return value


def test_inventory_uses_current_database_owned_snapshot_and_never_executes():
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("requires PostgreSQL")
    schema = "sc03d_inventory_" + uuid.uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped, expire_on_commit=False)
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        with scoped.begin() as conn:
            for table in (
                Client.__table__, PensionProduct.__table__,
                PensionProductComponent.__table__, ScenarioDraft.__table__,
                ScenarioDraftDecision.__table__,
            ):
                table.create(conn)
            conn.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "D4 Synthetic", "id_number": "SC03D-7",
            })
            conn.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "manual",
                "source_identity": "manual:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            conn.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "c", "product_id": "p",
                "component_code": "תגמולי_עובד_עד_2000",
                "balance": Decimal("100.00"),
            })
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "D4 Synthetic",
                "status": "draft", "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            from types import SimpleNamespace
            source = _source_evidence(
                SimpleNamespace(client_id=7, product_id="p", version=1,
                    product_type="קרן פנסיה", source_kind="manual",
                    source_identity="manual:7:p"),
                SimpleNamespace(product_id="p", component_id="c",
                    component_code="תגמולי_עובד_עד_2000",
                    balance=Decimal("100.00")),
            )
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s",
                "source_product_id": "p", "source_component_id": "c",
                "component_code": "תגמולי_עובד_עד_2000",
                "amount": Decimal("40.00"), "action": "pension",
                "effective_date": date(2026, 10, 24),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": "a" * 64,
                "permission_preview_id_at_review": "b" * 64,
            })
        first = build_planning_coverage_snapshot(
            factory, client_id=7, scenario_id="s",
        )
        second = build_planning_coverage_snapshot(
            factory, client_id=7, scenario_id="s",
        )
        assert first == second
        assert first["coverage_state"] == "UNRESOLVED"
        assert first["blockers"] == ["MISSING_SCENARIO_SAFE_PRODUCER"]
        assert first["execution_allowed"] is False
        assert first["financial_result"] is None
        assert first["planning_snapshot"] is None
        assert first["authority_state"] == "NOT_EVALUATED"
        assert first["decision_coverage"][0]["requirements"]
        assert all(r["state"] == "UNRESOLVED"
                   for row in first["decision_coverage"]
                   for r in row["requirements"])
        with scoped.begin() as conn:
            conn.execute(ScenarioDraft.__table__.update().where(
                ScenarioDraft.scenario_id == "s",
            ).values(version=2))
        fresh = build_planning_coverage_snapshot(
            factory, client_id=7, scenario_id="s",
        )
        assert fresh["scenario_version"] == 2
        assert first["inventory_fingerprint"] != fresh["inventory_fingerprint"]
        assert fresh["execution_allowed"] is False
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
