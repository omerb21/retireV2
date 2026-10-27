"""Stage 6 P1C real PostgreSQL snapshot and invalidation evidence."""
from datetime import date
from decimal import Decimal
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.pension_product import (
    COMPONENT_CODES, PensionProduct, PensionProductComponent,
)
from app.models.planning_input_decision import PlanningInputDecision
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_permission_preview_service import ruleset_digest
from app.services.scenario_pension_factor_admission_write_service import (
    append_authenticated_serializable_factor_admission,
)
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, build_stage6_p1c_planning_snapshot,
)

load_all_models()


def _url() -> str:
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL absent")
    parsed = urlsplit(value)
    if parsed.hostname not in {None, "localhost", "127.0.0.1", "::1"}:
        pytest.fail("local PostgreSQL required")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test permitted")
    return value


def _dependencies(*tables):
    found = set(tables)
    pending = list(tables)
    while pending:
        table = pending.pop()
        for foreign_key in table.foreign_keys:
            parent = foreign_key.column.table
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return list(found)


def _migration_module():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / (
        "d6f1a9c3b704_stage6_pension_factor_admissions.py")
    spec = importlib.util.spec_from_file_location("stage6_p1c_migration_pg", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _request():
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=True))),
        state=SimpleNamespace(
            trusted_professional_actor="planner-1",
            auth_session={"actor_id": "planner-1"}),
    )


def test_stage6_p1c_real_snapshot_staleness_and_target_conflict(monkeypatch):
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "stage6_p1c_" + uuid4().hex[:12]
    role = "stage6_p1c_role_" + uuid4().hex[:10]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    migration = _migration_module()
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
            connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(connection, tables=_dependencies(
                Client.__table__, ClientProfile.__table__, PensionProduct.__table__,
                PensionProductComponent.__table__, ScenarioDraft.__table__,
                ScenarioDraftDecision.__table__, ScenarioDraftPensionElection.__table__,
                PlanningInputDecision.__table__,
            ))
            monkeypatch.setenv("CRTISBA_APPLICATION_DB_ROLE", role)
            original_operation = migration.op
            try:
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
            finally:
                migration.op = original_operation

            component_code = COMPONENT_CODES[1]
            connection.execute(Client.__table__.insert(), {
                "client_id": 17, "display_name": "Stage6 P1C Synthetic",
                "id_number": "STAGE6-P1C-17",
            })
            connection.execute(ClientProfile.__table__.insert(), {
                "client_profile_id": "profile-17", "client_id": 17,
                "birth_date": date(1965, 4, 2), "gender": "female",
            })
            connection.execute(PensionProduct.__table__.insert(), {
                "product_id": "product", "client_id": 17,
                "source_kind": "imported", "source_identity": "imported:17:product",
                "product_name": "Synthetic", "product_type": "קרן פנסיה",
                "account_reference": "SYNTHETIC", "statement_date": date(2026, 9, 30),
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "component", "product_id": "product",
                "component_code": component_code, "balance": Decimal("1000.00"),
            })
            source = _source_evidence(
                SimpleNamespace(
                    client_id=17, product_id="product", version=1,
                    product_type="קרן פנסיה", source_kind="imported",
                    source_identity="imported:17:product"),
                SimpleNamespace(
                    product_id="product", component_id="component",
                    component_code=component_code, balance=Decimal("1000.00")),
            )
            connection.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "scenario", "client_id": 17, "name": "Synthetic",
                "status": "draft", "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "decision", "scenario_id": "scenario",
                "source_product_id": "product", "source_component_id": "component",
                "component_code": component_code, "amount": Decimal("400.00"),
                "action": "pension", "effective_date": date(2026, 10, 27),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": ruleset_digest(),
            })
            connection.execute(ScenarioDraftPensionElection.__table__.insert(), {
                "election_id": "election", "scenario_id": "scenario",
                "decision_id": "decision", "scenario_version": 1,
                "pension_start_date": date(2027, 9, 30), "target_year": 2027,
                "survivors_option": "60%", "spouse_age_diff": 0,
                "coefficient_selection": "manual_review_required",
                "option_name": "standard",
            })

        factory = sessionmaker(bind=scoped, autoflush=False, expire_on_commit=False)
        admission = append_authenticated_serializable_factor_admission(
            factory, request=_request(), client_id=17, scenario_id="scenario",
            decision_id="decision", expected_scenario_version=1,
            expected_admission_revision=0, factor_value="200",
            factor_evidence_type="PLANNER_ASSUMPTION",
            factor_evidence_reference="synthetic professional assumption",
        )
        assert admission["admission_revision"] == 1

        result = build_stage6_p1c_planning_snapshot(
            factory, client_id=17, scenario_id="scenario", decision_id="decision")
        assert result["execution_allowed"] is False
        assert result["financial_result"] is None
        assert len(result["planning_result"]["pension_inputs"]) == 1
        assert result["planning_result"]["pension_inputs"][0][
            "monthly_amount_basis"]["base_amount_representation"] == {
                "representation_kind": "exact_ratio",
                "numerator": "400.00", "denominator": "200",
            }
        for field in (
            "monthly_semantic_fingerprint", "monthly_source_fingerprint",
            "temporal_semantic_fingerprint", "temporal_source_fingerprint",
            "planning_calculation_input_fingerprint",
        ):
            assert len(result[field]) == 64

        # The immutable admission is preserved but no longer current when the
        # DB-owned election changes without a replacement admission.
        with scoped.begin() as connection:
            connection.execute(ScenarioDraftPensionElection.__table__.update().where(
                ScenarioDraftPensionElection.election_id == "election",
            ).values(option_name="changed-option"))
        with pytest.raises(
            ScenarioSnapshotError, match="STAGE6_P1C_FACTOR_ADMISSION_BLOCKED",
        ):
            build_stage6_p1c_planning_snapshot(
                factory, client_id=17, scenario_id="scenario", decision_id="decision")

        with scoped.begin() as connection:
            connection.execute(ScenarioDraftPensionElection.__table__.update().where(
                ScenarioDraftPensionElection.election_id == "election",
            ).values(option_name="standard"))
            connection.execute(PlanningInputDecision.__table__.insert(), {
                "client_id": 17, "version": 1,
                "retirement_target_date": date(2028, 9, 30),
                "retirement_target_decision_actor": "planner-1",
                "retirement_target_reference_fingerprint": "a" * 64,
                "actor": "planner-1",
            })
        with pytest.raises(
            ScenarioSnapshotError, match="SCENARIO_GLOBAL_TARGET_CONFLICT",
        ):
            build_stage6_p1c_planning_snapshot(
                factory, client_id=17, scenario_id="scenario", decision_id="decision")
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        scoped.dispose()
        engine.dispose()
