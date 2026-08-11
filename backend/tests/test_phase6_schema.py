from __future__ import annotations

import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.actual_capitalization import ActualCapitalization
from app.models.clearinghouse_snapshot import ClearinghouseSnapshot
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.fixation_audit_row import FixationAuditRow
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_result import FixationResult
from app.models.fixation_run import FixationRun
from app.models.fixation_validation_error import FixationValidationError
from app.models.grant import Grant
from app.models.missing_data_item import MissingDataItem
from app.models.retirement_planning_document import RetirementPlanningDocument

APPROVED_TABLES = {
    "clients",
    "client_profiles",
    "employment_records",
    "grants",
    "actual_capitalizations",
    "clearinghouse_snapshots",
    "retirement_planning_documents",
    "missing_data_items",
    "fixation_runs",
    "fixation_input_snapshots",
    "fixation_results",
    "fixation_audit_rows",
    "fixation_validation_errors",
}

ACCEPTED_ADDITIVE_TABLES = {
    "capital_asset",
    "fixation_dependency_manifests",
    "internal_planner_judgments",
    "m07_assessment_findings",
    "m07_evidence_revisions",
    "m07_fact_evidence",
    "m07_planner_assertions",
    "official_parameter_sets",
    "pension_analysis_record",
    "pension_holding",
    "planner_assumption",
    "recurring_expense",
    "recurring_income",
    "retirement_timing_work_intention",
    "m02_intake_records",
    "m02_preserved_blobs",
    "m02_preserved_sources",
    "m03_review_revisions",
    "m03_annotations",
    "m04_classification_subjects",
    "m04_classification_revisions",
    "m04_component_decisions",
    "m05_ledger_subjects",
    "m05_candidate_links",
    "m05_ledger_revisions",
    "m05_ledger_values",
    "m05_adjustment_evidence",
    "m06_conversion_subjects",
    "m06_conversion_revisions",
    "m06_coefficient_evidence",
    "m06_calculation_manifests",
    "m06_warning_dispositions",
    "m09_resolved_component_inventories",
    "m09_scenario_runs",
    "m09_monthly_results",
}

EXCLUDED_TABLES = {
    "users",
    "pension_results",
    "tax_results",
    "cashflow_results",
    "scenario_runs",
    "reports",
    "pdf_artifacts",
    "llm_chats",
}


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_sqlite_database(db_path: Path) -> str:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout + result.stderr


def test_database_design_draft_exists() -> None:
    design_draft = _backend_root().parent / "specs" / "phase1" / "database_design_draft.md"
    assert design_draft.exists()


def test_phase6_migration_applies_and_exact_table_set_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "phase6_schema.db"
    _upgrade_sqlite_database(db_path)

    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    actual_tables = set(inspector.get_table_names())

    assert actual_tables - {"alembic_version"} == APPROVED_TABLES | ACCEPTED_ADDITIVE_TABLES
    assert EXCLUDED_TABLES.isdisjoint(actual_tables)

    clients_columns = {col["name"] for col in inspector.get_columns("clients")}
    run_columns = {col["name"] for col in inspector.get_columns("fixation_runs")}
    assert "id_number" in clients_columns
    assert "birth_date" in clients_columns
    assert "id" in run_columns


def test_source_snapshot_result_audit_separation_exists() -> None:
    load_all_models()

    snapshot_columns = set(FixationInputSnapshot.__table__.columns.keys())
    result_columns = set(FixationResult.__table__.columns.keys())
    audit_columns = set(FixationAuditRow.__table__.columns.keys())

    assert "input_payload" in snapshot_columns
    assert "result_payload" not in snapshot_columns

    assert "result_payload" in result_columns
    assert "input_payload" not in result_columns

    assert "details_payload" in audit_columns
    assert "result_payload" not in audit_columns
    assert "input_payload" not in audit_columns


def test_basic_insert_read_relationships_and_constraints(tmp_path: Path) -> None:
    db_path = tmp_path / "phase6_relationships.db"
    _upgrade_sqlite_database(db_path)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    with Session(engine) as session:
        client = Client(
            client_id=1,
            display_name="Client 1",
            id_number="1001",
            birth_date=date(1970, 1, 1),
            status="active",
        )
        session.add(client)
        session.add(
            ClientProfile(
                client_profile_id="CP1",
                client_id=1,
                birth_date=date(1970, 1, 1),
                gender="f",
                notes="profile",
            )
        )
        session.add(
            EmploymentRecord(
                employment_record_id="E1",
                client_id=1,
                employer_name="Employer",
                work_start_date=date(2010, 1, 1),
                work_end_date=date(2020, 1, 1),
                is_current=False,
            )
        )
        session.add(
            Grant(
                grant_id="G1",
                client_id=1,
                employment_record_id="E1",
                indexed_amount=Decimal("10000.00"),
                grant_date=date(2020, 1, 1),
                work_start_date=date(2010, 1, 1),
                work_end_date=date(2020, 1, 1),
            )
        )
        session.add(
            ActualCapitalization(
                capitalization_id="AC1",
                client_id=1,
                amount=Decimal("500.00"),
                capitalization_date=date(2023, 1, 1),
            )
        )
        session.add(
            ClearinghouseSnapshot(
                clearinghouse_snapshot_id="CHS1",
                client_id=1,
                import_date=date(2026, 1, 1),
                source_type="clearinghouse",
                source_file="clearinghouse.csv",
                collection_status="collected",
            )
        )
        session.add(
            RetirementPlanningDocument(
                document_id="DOC1",
                client_id=1,
                document_type="161",
                source_type="document",
                source_file="161.pdf",
                collection_date=date(2026, 1, 2),
                collection_status="collected",
            )
        )
        session.add(
            MissingDataItem(
                missing_data_item_id="MD1",
                client_id=1,
                missing_item_type="data",
                missing_item_label="Tax credit fact",
                missing_status="missing",
            )
        )
        session.add(
            FixationRun(
                id=1,
                fixation_run_id="R1",
                client_id=1,
                calculation_version="v1",
                status="success",
                is_latest=True,
            )
        )
        session.add(
            FixationInputSnapshot(
                fixation_input_snapshot_id="S1",
                fixation_run_id=1,
                input_contract_version="v1",
                input_payload={"eligibility_year": 2025},
            )
        )
        session.add(
            FixationResult(
                fixation_result_id="FR1",
                fixation_run_id=1,
                result_contract_version="v1",
                initial_exempt_capital=Decimal("90000.00"),
                grant_impact_total=Decimal("0.00"),
                future_grant_reserved=Decimal("0.00"),
                future_grant_impact=Decimal("0.00"),
                actual_capitalization_impact=Decimal("0.00"),
                idf_impact=Decimal("0.00"),
                total_impact=Decimal("0.00"),
                remaining_exempt_capital=Decimal("90000.00"),
                monthly_exempt_pension=Decimal("500.00"),
                capital_exemption_percentage=Decimal("1.000000"),
                pension_exemption_percentage=Decimal("0.500000"),
                result_payload={"status": "success"},
            )
        )
        session.add(
            FixationAuditRow(
                fixation_audit_row_id="AR1",
                fixation_run_id=1,
                row_order=1,
                category="initial_entitlement",
                label="Initial entitlement",
                input_amount=Decimal("1000.00"),
                output_amount=Decimal("90000.00"),
                impact_amount=Decimal("0.00"),
                details_payload={"source": "engine"},
            )
        )
        session.add(
            FixationValidationError(
                fixation_validation_error_id="VE1",
                fixation_run_id=1,
                error_order=1,
                code="ERR_TEST",
                path="field",
                message="test",
                severity="error",
            )
        )
        session.commit()

        persisted_client = session.get(Client, 1)
        assert persisted_client is not None
        assert persisted_client.id_number == "1001"
        assert persisted_client.birth_date == date(1970, 1, 1)
        assert persisted_client.client_profile is not None
        assert len(persisted_client.employment_records) == 1
        assert len(persisted_client.grants) == 1
        assert len(persisted_client.actual_capitalizations) == 1
        assert len(persisted_client.clearinghouse_snapshots) == 1
        assert len(persisted_client.retirement_planning_documents) == 1
        assert len(persisted_client.missing_data_items) == 1
        assert len(persisted_client.fixation_runs) == 1

        persisted_run = session.get(FixationRun, 1)
        assert persisted_run is not None
        assert persisted_run.fixation_input_snapshot is not None
        assert persisted_run.fixation_result is not None
        assert len(persisted_run.fixation_audit_rows) == 1
        assert len(persisted_run.fixation_validation_errors) == 1


def test_required_non_negative_constraint_on_grants(tmp_path: Path) -> None:
    db_path = tmp_path / "phase6_constraints.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    with Session(engine) as session:
        session.add(
            Client(
                client_id=2,
                display_name="Client 2",
                id_number="2002",
                birth_date=None,
                status="active",
            )
        )
        session.commit()

        session.add(
            Grant(
                grant_id="G-BAD",
                client_id=2,
                indexed_amount=Decimal("-1.00"),
                grant_date=date(2020, 1, 1),
                work_start_date=date(2010, 1, 1),
                work_end_date=date(2020, 1, 1),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
