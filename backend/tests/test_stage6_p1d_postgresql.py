"""Stage 6 P1D end-to-end evidence on a dedicated PostgreSQL 16 database."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, func, select, text
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
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.services import scenario_stage6_single_pension_estimate_service as subject
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_permission_preview_service import ruleset_digest
from app.services.scenario_pension_factor_admission_write_service import (
    append_authenticated_serializable_factor_admission,
)
from test_stage6_p1c_postgresql import _dependencies, _migration_module, _request, _url

load_all_models()


def _assert_blocked_without_pte(factory, monkeypatch, expected_code):
    calls = 0
    real = subject.execute_from_planning_result

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(subject, "execute_from_planning_result", counted)
    result = subject.estimate_single_pension_decision(
        factory, client_id=27, scenario_id="scenario", decision_id="decision",
    )
    assert result["result_state"] == "BLOCKED"
    assert result["execution_allowed"] is False
    assert result["blockers"] == [expected_code]
    assert result["monthly_estimate_gross_ils"] is None
    assert result["pte_source_execution_fingerprint"] is None
    assert result["pte_source_result_fingerprint"] is None
    assert calls == 0


def test_stage6_p1d_real_postgresql_result_and_all_pre_pte_invalidations(monkeypatch):
    engine = create_engine(_url())
    assert engine.dialect.name == "postgresql"
    schema = "stage6_p1d_" + uuid4().hex[:12]
    role = "stage6_p1d_role_" + uuid4().hex[:10]
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
                "client_id": 27, "display_name": "Stage6 P1D Synthetic",
                "id_number": "STAGE6-P1D-27",
            })
            connection.execute(ClientProfile.__table__.insert(), {
                "client_profile_id": "profile-27", "client_id": 27,
                "birth_date": date(1965, 4, 2), "gender": "female",
            })
            connection.execute(PensionProduct.__table__.insert(), {
                "product_id": "product", "client_id": 27,
                "source_kind": "imported", "source_identity": "imported:27:product",
                "product_name": "Synthetic", "product_type": "קרן פנסיה",
                "account_reference": "SYNTHETIC", "statement_date": date(2026, 9, 30),
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "component", "product_id": "product",
                "component_code": component_code, "balance": Decimal("1000.00"),
            })
            connection.execute(PensionProduct.__table__.insert(), {
                "product_id": "product-2", "client_id": 27,
                "source_kind": "imported", "source_identity": "imported:27:product-2",
                "product_name": "Synthetic 2", "product_type": "קרן פנסיה",
                "account_reference": "SYNTHETIC-2", "statement_date": date(2026, 9, 30),
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "component-2", "product_id": "product-2",
                "component_code": component_code, "balance": Decimal("1200.00"),
            })
            source = _source_evidence(
                SimpleNamespace(
                    client_id=27, product_id="product", version=1,
                    product_type="קרן פנסיה", source_kind="imported",
                    source_identity="imported:27:product",
                ),
                SimpleNamespace(
                    product_id="product", component_id="component",
                    component_code=component_code, balance=Decimal("1000.00"),
                ),
            )
            source2 = _source_evidence(
                SimpleNamespace(
                    client_id=27, product_id="product-2", version=1,
                    product_type="קרן פנסיה", source_kind="imported",
                    source_identity="imported:27:product-2",
                ),
                SimpleNamespace(
                    product_id="product-2", component_id="component-2",
                    component_code=component_code, balance=Decimal("1200.00"),
                ),
            )
            connection.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "scenario", "client_id": 27, "name": "Synthetic",
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
            connection.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "decision-2", "scenario_id": "scenario",
                "source_product_id": "product-2", "source_component_id": "component-2",
                "component_code": component_code, "amount": Decimal("600.00"),
                "action": "pension", "effective_date": date(2026, 10, 27),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source2["source_fingerprint"],
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
            connection.execute(ScenarioDraftPensionElection.__table__.insert(), {
                "election_id": "election-2", "scenario_id": "scenario",
                "decision_id": "decision-2", "scenario_version": 1,
                "pension_start_date": date(2027, 9, 30), "target_year": 2027,
                "survivors_option": "60%", "spouse_age_diff": 0,
                "coefficient_selection": "manual_review_required",
                "option_name": "standard-2",
            })

        factory = sessionmaker(bind=scoped, autoflush=False, expire_on_commit=False)
        admission = append_authenticated_serializable_factor_admission(
            factory, request=_request(), client_id=27, scenario_id="scenario",
            decision_id="decision", expected_scenario_version=1,
            expected_admission_revision=0, factor_value="200",
            factor_evidence_type="PLANNER_ASSUMPTION",
            factor_evidence_reference="synthetic professional assumption",
        )
        assert admission["admission_revision"] == 1
        admission2 = append_authenticated_serializable_factor_admission(
            factory, request=_request(), client_id=27, scenario_id="scenario",
            decision_id="decision-2", expected_scenario_version=1,
            expected_admission_revision=0, factor_value="300",
            factor_evidence_type="PLANNER_ASSUMPTION",
            factor_evidence_reference="synthetic professional assumption 2",
        )
        assert admission2["admission_revision"] == 1

        calls = 0
        real = subject.execute_from_planning_result

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(subject, "execute_from_planning_result", counted)
        ready = subject.estimate_single_pension_decision(
            factory, client_id=27, scenario_id="scenario", decision_id="decision",
        )
        assert calls == 1
        assert ready["result_state"] == "RESULT_READY"
        assert ready["execution_allowed"] is True
        assert ready["blockers"] == []
        assert ready["monthly_estimate_gross_ils"] == "2.00"
        assert ready["statement_date"] == "2026-09-30"
        assert ready["retirement_target_date"] == "2027-09-30"
        assert ready["coefficient_provenance"] == {
            "source_level": "MANUAL_PROFESSIONAL_OVERRIDE",
            "factor_value": "200",
            "factor_evidence_type": "PLANNER_ASSUMPTION",
            "factor_evidence_reference": "synthetic professional assumption",
            "payout_option_name": "standard",
            "admission_revision": 1,
        }
        for field in (
            "professional_admission_fingerprint",
            "planning_calculation_input_fingerprint",
            "monthly_basis_semantic_fingerprint", "monthly_basis_source_fingerprint",
            "temporal_semantic_fingerprint", "temporal_source_fingerprint",
            "pte_source_execution_fingerprint", "pte_source_result_fingerprint",
            "result_fingerprint",
        ):
            assert isinstance(ready[field], str) and len(ready[field]) == 64

        aggregate = subject.estimate_scenario_pension_aggregate(
            factory, client_id=27, scenario_id="scenario",
        )
        assert calls == 3
        assert aggregate["aggregation_state"] == "COMPLETE"
        assert aggregate["monthly_pension_gross_total_ils"] == "4.00"
        assert aggregate["comparison_basis"] == {
            "currency": "ILS", "income_basis": "GROSS",
            "price_basis": "NOMINAL_UNINDEXED",
            "retirement_target_date": "2027-09-30",
            "source_reference_date": "2026-09-30",
        }
        assert [row["monthly_estimate_gross_ils"]
                for row in aggregate["decision_results"]] == ["2.00", "2.00"]
        assert len(aggregate["aggregate_fingerprint"]) == 64
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(
                ScenarioPensionFactorAdmission)) == 2
            db.rollback()

        # A changed payout route makes the immutable professional admission stale.
        with scoped.begin() as connection:
            connection.execute(ScenarioDraftPensionElection.__table__.update().where(
                ScenarioDraftPensionElection.election_id == "election",
            ).values(option_name="changed-route"))
        monkeypatch.undo()
        _assert_blocked_without_pte(
            factory, monkeypatch, "STAGE6_P1C_FACTOR_ADMISSION_BLOCKED")

        # A changed pension date also invalidates the old admission before PTE.
        with scoped.begin() as connection:
            connection.execute(ScenarioDraftPensionElection.__table__.update().where(
                ScenarioDraftPensionElection.election_id == "election",
            ).values(option_name="standard", pension_start_date=date(2028, 9, 30)))
        monkeypatch.undo()
        _assert_blocked_without_pte(
            factory, monkeypatch, "STAGE6_P1C_FACTOR_ADMISSION_BLOCKED")

        # A factual balance change invalidates permission/source identity.
        with scoped.begin() as connection:
            connection.execute(ScenarioDraftPensionElection.__table__.update().where(
                ScenarioDraftPensionElection.election_id == "election",
            ).values(pension_start_date=date(2027, 9, 30)))
            connection.execute(PensionProductComponent.__table__.update().where(
                PensionProductComponent.component_id == "component",
            ).values(balance=Decimal("900.00")))
        monkeypatch.undo()
        _assert_blocked_without_pte(
            factory, monkeypatch, "STAGE6_P1C_SOURCE_BLOCKED")

        # Restore the factual source and prove a conflicting global target blocks.
        with scoped.begin() as connection:
            connection.execute(PensionProductComponent.__table__.update().where(
                PensionProductComponent.component_id == "component",
            ).values(balance=Decimal("1000.00")))
            connection.execute(PlanningInputDecision.__table__.insert(), {
                "client_id": 27, "version": 1,
                "retirement_target_date": date(2028, 9, 30),
                "retirement_target_decision_actor": "planner-1",
                "retirement_target_reference_fingerprint": "a" * 64,
                "actor": "planner-1",
            })
        monkeypatch.undo()
        _assert_blocked_without_pte(
            factory, monkeypatch, "SCENARIO_GLOBAL_TARGET_CONFLICT")

        # Read-only execution persisted neither a result nor a replacement approval.
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(
                ScenarioPensionFactorAdmission)) == 2
            db.rollback()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        scoped.dispose()
        engine.dispose()
