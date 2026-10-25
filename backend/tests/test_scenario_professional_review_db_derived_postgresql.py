"""SC-04: actual canonical registry in the same PostgreSQL scenario snapshot.

No canonical producer mocks; isolated schema in dedicated local test DB.
"""
from datetime import date, timezone
from decimal import Decimal
import os
import uuid
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, event, text, select, func
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent, PensionProductAuditEvent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision, ScenarioDraftRevision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.models.scenario_coefficient_professional_review import ScenarioCoefficientProfessionalReview
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision
from app.models.canonical_conversion import batches, conversions, allocations, pensions
from app.models.retirement_facts import CapitalAsset, RetirementTimingWorkIntention
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.services.scenario_draft_service import _source_evidence
from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.schemas.scenario_draft import DraftReplace, DraftDecisionWrite
from app.services.scenario_draft_service import replace, DraftError
from app.services.scenario_coefficient_professional_review_store_service import append_database_derived_documentary_review
from app.services.scenario_coefficient_review_context_service import derive_documentary_review_context
from app.services.scenario_coefficient_professional_review_contract import validate_documentary_review

load_all_models()


def _url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL absent")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("local PostgreSQL required")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test permitted")
    return value


def _dependent_tables(*tables):
    """Include foreign-key dependencies in real metadata, not hand-built DDL."""
    found = set(tables)
    pending = list(tables)
    while pending:
        table = pending.pop()
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return list(found)


def test_database_derived_professional_review_staleness_real_postgresql():
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "sc05e_derived_" + uuid.uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        tables = _dependent_tables(
            Client.__table__, PensionProduct.__table__, PensionProductAuditEvent.__table__,
            ScenarioCoefficientProfessionalReview.__table__, ScenarioDraftPensionElection.__table__, ScenarioDraftRevision.__table__,
            PensionProductComponent.__table__, ScenarioDraft.__table__,
            ScenarioDraftDecision.__table__, CanonicalManualPensionSource.__table__,
            batches, conversions, allocations, pensions,
            CanonicalPensionTemporalDecision.__table__,
            CapitalAsset.__table__, RetirementTimingWorkIntention.__table__,
            ClientProfile.__table__, EmploymentRecord.__table__,
        )
        with scoped.begin() as conn:
            # Canonical conversion DDL guards use unqualified CREATE TRIGGER
            # statements. Resolve those names within this isolated test schema.
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(conn, tables=tables)
            conn.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "Real Registry Synthetic",
                "id_number": "SC04-REAL-7",
            })
            conn.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "manual",
                "source_identity": "manual:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            from app.models.pension_product import COMPONENT_CODES
            for index, code in enumerate(COMPONENT_CODES):
                conn.execute(PensionProductComponent.__table__.insert(), {
                    "component_id": "c" if index == 0 else f"c{index}",
                    "product_id": "p", "component_code": code,
                    "balance": Decimal("100.00") if index == 0 else Decimal("0.00"),
                })
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "Synthetic",
                "status": "draft", "version": 1, "created_by": "test",
                "updated_by": "test",
            })
            from types import SimpleNamespace
            source = _source_evidence(
                SimpleNamespace(client_id=7, product_id="p", version=1,
                    product_type="קרן פנסיה", source_kind="manual",
                    source_identity="manual:7:p"),
                SimpleNamespace(product_id="p", component_id="c",
                    component_code=COMPONENT_CODES[0], balance=Decimal("100.00")),
            )
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s", "source_product_id": "p",
                "source_component_id": "c", "component_code": COMPONENT_CODES[0],
                "amount": Decimal("40.00"), "action": "pension",
                "effective_date": date(2026, 10, 24),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": "a" * 64,
                "permission_preview_id_at_review": "b" * 64,
            })
            conn.execute(CanonicalManualPensionSource.__table__.insert(), {
                "manual_pension_source_id": "manual-1", "client_id": 7,
                "input_mode": "entered", "payer_name": "Synthetic payer",
                "monthly_amount": Decimal("100.00"), "tax_treatment": "taxable",
                "pension_start_date": date(2040, 1, 1),
                "base_amount_effective_date": date(2026, 9, 1),
                "temporal_authority_explicit": True,
                "indexation_method": "none", "lifecycle_status": "current",
                "version": 1,
            })
        with scoped.begin() as conn:
            conn.execute(ClientProfile.__table__.insert(), {
                "client_profile_id": "profile-7", "client_id": 7,
                "birth_date": date(1965, 4, 2), "gender": "female",
            })
            conn.execute(ScenarioDraftPensionElection.__table__.insert(), {
                "election_id": "e", "scenario_id": "s", "decision_id": "d",
                "scenario_version": 1, "pension_start_date": date(2040, 1, 1),
                "target_year": 2040, "survivors_option": "תקנוני",
                "spouse_age_diff": 0, "coefficient_selection": "catalog_candidate",
            })
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        with factory() as db, db.begin():
            original = derive_documentary_review_context(
                db, client_id=7, scenario_id="s", decision_id="d")
            saved = append_database_derived_documentary_review(
                db, client_id=7, scenario_id="s", decision_id="d",
                authenticated_actor="trusted-test-actor", review_reference="case-1",
                decision="reviewed_for_candidate")
            assert saved["review_state"] == "RECORDED_NOT_AUTHORIZED"
            assert saved["execution_allowed"] is False
            assert saved["coefficient_candidate"] is None
            records = db.scalars(select(ScenarioCoefficientProfessionalReview)).all()
            assert len(records) == 1
            stored = records[0]
            assert stored.manifest_fingerprint == original["manifest_fingerprint"]
            assert stored.inventory_fingerprint == original["inventory_fingerprint"]
            assert stored.source_fingerprint == original["source_fingerprint"]
            assert stored.record_fingerprint == saved["review_fingerprint"]
        with factory() as db, db.begin():
            # A profile fact change invalidates the documentary review without
            # silently granting coefficient authority or bumping draft version.
            db.execute(ClientProfile.__table__.update().where(
                ClientProfile.client_id == 7).values(birth_date=date(1966, 4, 2)))
        with factory() as db:
            new_context = derive_documentary_review_context(
                db, client_id=7, scenario_id="s", decision_id="d")
            assert new_context["inventory_fingerprint"] != original["inventory_fingerprint"]
            record = db.scalar(select(ScenarioCoefficientProfessionalReview))
            assert record is not None
            archived = {
                "schema_version": "SCENARIO_COEFFICIENT_REVIEW_V1",
                **{k: getattr(record, k) for k in original},
                "professional_actor_id": record.professional_actor_id,
                "reviewed_at": record.reviewed_at.astimezone(timezone.utc).isoformat(),
                "review_reference": record.review_reference,
                "decision": record.decision,
                "record_fingerprint": record.record_fingerprint,
            }
            assert validate_documentary_review(archived, new_context)["blockers"] == [
                "REVIEW_PROVENANCE_STALE"]
            assert db.scalar(select(func.count()).select_from(
                ScenarioCoefficientProfessionalReview)) == 1
            db.rollback()
        with factory() as db, db.begin():
            # A changed source balance also invalidates the old provenance.
            db.execute(PensionProductComponent.__table__.update().where(
                PensionProductComponent.component_id == "c").values(balance=Decimal("90.00")))
        with factory() as db:
            with pytest.raises(DraftError, match="PROFESSIONAL_REVIEW_SOURCE_UNVERIFIED"):
                derive_documentary_review_context(
                    db, client_id=7, scenario_id="s", decision_id="d")
            db.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
