"""SC-04: actual canonical registry in the same PostgreSQL scenario snapshot.

No canonical producer mocks; isolated schema in dedicated local test DB.
"""
from datetime import date
import json
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
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision
from app.models.canonical_conversion import batches, conversions, allocations, pensions
from app.models.retirement_facts import CapitalAsset, RetirementTimingWorkIntention
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.services.scenario_draft_service import _source_evidence
from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.schemas.scenario_draft import DraftReplace, DraftDecisionWrite
from app.services.scenario_draft_service import replace, rename, DraftError
from app.services.scenario_pension_election_store_service import replace_elections, current_elections

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


def test_atomic_pension_election_store_real_postgresql():
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "sc05c_real_" + uuid.uuid4().hex[:16]
    restricted_role = "sc05c_runtime_" + uuid.uuid4().hex[:12]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        tables = _dependent_tables(
            Client.__table__, PensionProduct.__table__, PensionProductAuditEvent.__table__,
            ScenarioDraftPensionElection.__table__, ScenarioDraftRevision.__table__,
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
                    "balance": Decimal("100.00") if index in (0, 1) else Decimal("0.00"),
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
        SessionFactory = sessionmaker(bind=scoped, expire_on_commit=False)
        payload = ScenarioPensionElectionSet.model_validate({
            "expected_scenario_version": 1,
            "elections": [{
                "decision_id": "d", "pension_start_date": date(2040, 1, 1),
                "target_year": 2040, "survivors_option": "תקנוני",
                "spouse_age_diff": 0, "coefficient_selection": "manual_review_required",
            }],
        })
        with SessionFactory() as db, db.begin():
            result = replace_elections(db, 7, "s", payload, "test")
            assert result["version"] == 2
            revision = db.scalar(select(ScenarioDraftRevision).where(
                ScenarioDraftRevision.scenario_id == "s",
                ScenarioDraftRevision.version == 2))
            assert revision is not None
            audit = json.loads(revision.snapshot_json)
            assert len(audit["pension_elections"]) == 1
            assert audit["pension_elections"][0]["decision_id"] == "d"
            assert audit["pension_elections"][0]["scenario_version"] == 2
            assert audit["pension_elections"][0]["pension_start_date"] == "2040-01-01"
            assert audit["pension_elections"][0]["authority_state"] == "NOT_EVALUATED"
            current = current_elections(db, 7, "s")
            assert len(current) == 1
            assert current[0]["decision_id"] == "d"
            assert current[0]["authority_state"] == "NOT_EVALUATED"
            assert db.get(ScenarioDraftPensionElection, db.scalar(
                select(ScenarioDraftPensionElection.election_id))) is not None
        with SessionFactory() as db:
            with pytest.raises(DraftError, match="SCENARIO_VERSION_CONFLICT"):
                replace_elections(db, 7, "s", payload, "test")
            db.rollback()
            assert len(current_elections(db, 7, "s")) == 1
        # Confirm the real app role cannot UPDATE an election. The new
        # continuity algorithm must use DELETE/INSERT and still be atomic.
        with engine.begin() as conn:
            conn.execute(text(f'CREATE ROLE "{restricted_role}" NOLOGIN'))
            conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{restricted_role}"'))
            grants = {
                "clients": "SELECT",
                "pension_products": "SELECT",
                "pension_product_components": "SELECT",
                "scenario_drafts": "SELECT, UPDATE",
                "scenario_draft_decisions": "SELECT, INSERT, DELETE",
                "scenario_draft_revisions": "SELECT, INSERT",
                "scenario_draft_pension_elections": "SELECT, INSERT, DELETE",
            }
            for table, permissions in grants.items():
                conn.execute(text(
                    f'GRANT {permissions} ON "{schema}"."{table}" TO "{restricted_role}"'
                ))
            assert not conn.scalar(text(
                "SELECT has_table_privilege(:role,:table,'UPDATE')"
            ), {
                "role": restricted_role,
                "table": f'{schema}.scenario_draft_pension_elections',
            })

        # Add a separate pension component. The existing election MUST survive
        # the draft version change, even with restricted PostgreSQL DML grants.
        with SessionFactory() as db, db.begin():
            db.execute(text(f'SET LOCAL ROLE "{restricted_role}"'))
            draft = replace(db, 7, "s", DraftReplace(
                expected_version=2, name="Synthetic",
                decisions=[
                    DraftDecisionWrite(
                        decision_id="d", source_product_id="p",
                        source_component_id="c", component_code=COMPONENT_CODES[0],
                        amount=Decimal("40.00"), action="pension",
                        effective_date=date(2026, 10, 24),
                    ),
                    DraftDecisionWrite(
                        source_product_id="p", source_component_id="c1",
                        component_code=COMPONENT_CODES[1], amount=Decimal("20.00"),
                        action="capital_asset", effective_date=date(2026, 10, 25),
                    ),
                ],
            ), "test")
            assert draft["version"] == 3
            assert len(draft["decisions"]) == 2
            assert len(current_elections(db, 7, "s")) == 1
            assert current_elections(db, 7, "s")[0]["decision_id"] == "d"

        # Metadata-only version bump must likewise preserve a current choice.
        with SessionFactory() as db, db.begin():
            db.execute(text(f'SET LOCAL ROLE "{restricted_role}"'))
            renamed = rename(db, 7, "s", "Renamed", 3, "test")
            assert renamed["version"] == 4
            assert len(current_elections(db, 7, "s")) == 1
            second_decision_id = next(
                row["decision_id"] for row in renamed["decisions"]
                if row["decision_id"] != "d"
            )

        # Simulate a canonical balance change committed by another session
        # while the draft replacement transaction is still open. The draft
        # writer must never be able to present stale source facts as current
        # on a fresh read or retain the stale election as usable.
        with SessionFactory() as draft_db:
            with draft_db.begin():
                draft_db.execute(text(f'SET LOCAL ROLE "{restricted_role}"'))
                changed = replace(draft_db, 7, "s", DraftReplace(
                    expected_version=4, name="Renamed",
                    decisions=[
                        DraftDecisionWrite(
                            decision_id="d", source_product_id="p",
                            source_component_id="c", component_code=COMPONENT_CODES[0],
                            amount=Decimal("40.00"), action="pension",
                            effective_date=date(2026, 10, 24),
                        ),
                        DraftDecisionWrite(
                            decision_id=second_decision_id, source_product_id="p",
                            source_component_id="c1", component_code=COMPONENT_CODES[1],
                            amount=Decimal("20.00"), action="capital_asset",
                            effective_date=date(2026, 10, 25),
                        ),
                    ],
                ), "test")
                assert changed["version"] == 5
                with scoped.begin() as updater:
                    updater.execute(PensionProductComponent.__table__.update().where(
                        PensionProductComponent.component_id == "c"
                    ).values(balance=Decimal("39.00")))
        with SessionFactory() as db:
            from app.services.scenario_draft_service import read as read_draft
            stale = read_draft(db, 7, "s")
            assert stale["status"] == "needs_revalidation"
            assert next(row for row in stale["decisions"]
                        if row["decision_id"] == "d")["validation_state"] == (
                            "needs_revalidation")
            assert current_elections(db, 7, "s") == []

        # Material change removes only the relevant old pension election.
        with SessionFactory() as db, db.begin():
            db.execute(text(f'SET LOCAL ROLE "{restricted_role}"'))
            rows = db.scalars(select(ScenarioDraftDecision).where(
                ScenarioDraftDecision.scenario_id == "s")).all()
            second = next(row for row in rows if row.decision_id != "d")
            draft = replace(db, 7, "s", DraftReplace(
                expected_version=5, name="Changed",
                decisions=[
                    DraftDecisionWrite(
                        decision_id="d", source_product_id="p",
                        source_component_id="c", component_code=COMPONENT_CODES[0],
                        amount=Decimal("30.00"), action="pension",
                        effective_date=date(2026, 10, 24),
                    ),
                    DraftDecisionWrite(
                        decision_id=second.decision_id, source_product_id="p",
                        source_component_id="c1", component_code=COMPONENT_CODES[1],
                        amount=Decimal("20.00"), action="capital_asset",
                        effective_date=date(2026, 10, 25),
                    ),
                ],
            ), "test")
            assert draft["version"] == 6
            assert current_elections(db, 7, "s") == []
            assert db.scalar(select(func.count()).select_from(
                ScenarioDraftPensionElection)) == 0
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{restricted_role}"'))
        scoped.dispose()
        engine.dispose()
