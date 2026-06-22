from __future__ import annotations

import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.actual_capitalization import ActualCapitalization
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.fixation_audit_row import FixationAuditRow
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_result import FixationResult as FixationResultModel
from app.models.fixation_run import FixationRun
from app.models.fixation_validation_error import FixationValidationError
from app.models.grant import Grant
from app.schemas.fixation_contracts import AuditRow, FixationInput, FixationResult

APPROVED_TABLES = {
    "clients",
    "client_profiles",
    "employment_records",
    "grants",
    "actual_capitalizations",
    "fixation_runs",
    "fixation_input_snapshots",
    "fixation_results",
    "fixation_audit_rows",
    "fixation_validation_errors",
}


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_sqlite_database(db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _create_source_data(session: Session, *, client_id: int = 1) -> None:
    session.add(
        Client(
            client_id=client_id,
            display_name=f"Client {client_id}",
            id_number=str(client_id),
            birth_date=date(1970, 1, 1),
            status="active",
        )
    )
    session.add(
        ClientProfile(
            client_profile_id=f"CP-{client_id}",
            client_id=client_id,
            birth_date=date(1970, 1, 1),
            gender="f",
            notes="profile",
        )
    )
    session.add(
        EmploymentRecord(
            employment_record_id=f"E-{client_id}",
            client_id=client_id,
            employer_name="Employer",
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2020, 1, 1),
            is_current=False,
        )
    )
    session.add(
        Grant(
            grant_id=f"G-{client_id}",
            client_id=client_id,
            employment_record_id=f"E-{client_id}",
            indexed_amount=Decimal("10000.00"),
            grant_date=date(2020, 1, 1),
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2020, 1, 1),
        )
    )
    session.add(
        ActualCapitalization(
            capitalization_id=f"AC-{client_id}",
            client_id=client_id,
            amount=Decimal("500.00"),
            capitalization_date=date(2023, 1, 1),
            source_label="manual",
        )
    )


def _input_payload(calc_id: str, year: int) -> dict:
    return {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": f"{year}-01-01",
        "eligibility_year": year,
        "monthly_cap": 5200.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grants": [
            {
                "grant_id": "G-1",
                "employer_name": "Employer",
                "nominal_amount": 10000.0,
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
            }
        ],
        "future_grant_reserved": 500.0,
        "actual_capitalizations": [
            {
                "capitalization_id": "AC-1",
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "source_label": "manual",
                "notes": "actual capitalization",
            }
        ],
        "idf": {
            "idf_id": "IDF-1",
            "reduction_amount": 1200.0,
            "original_commutation_percent": 35.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2024-01-01",
            "promoter_age_date": "2028-01-01",
            "source_label": "idf_source",
        },
        "metadata": {"source_data_version_label": "source-v1"},
    }


def _result_payload(calc_id: str, year: int) -> dict:
    return {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "status": "success",
        "validation_errors": [],
        "eligibility_date": f"{year}-01-01",
        "eligibility_year": year,
        "monthly_cap": 5200.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "initial_exempt_capital": 90000.0,
        "grant_impact_total": 1000.0,
        "future_grant_reserved": 500.0,
        "future_grant_impact": 300.0,
        "actual_capitalization_impact": 200.0,
        "idf_impact": 100.0,
        "total_impact": 1600.0,
        "remaining_exempt_capital": 88400.0,
        "monthly_exempt_pension": 450.0,
        "capital_exemption_percentage": 0.982222,
        "pension_exemption_percentage": 0.45,
        "grant_results": [],
        "actual_capitalization_results": [],
        "idf_result": None,
        "audit_rows": [
            {
                "row_id": "A1",
                "category": "initial_entitlement",
                "stage_order": 2,
                "source_id": None,
                "label": "Initial entitlement",
                "input_amount": None,
                "output_amount": 90000.0,
                "impact_amount": 0.0,
                "details": {"phase": "initial"},
            }
        ],
    }


def _create_run(session: Session, *, run_trace: str, status: str = "success") -> int:
    run = FixationRun(
        fixation_run_id=run_trace,
        client_id=1,
        calculation_version="v1",
        status=status,
        is_latest=True,
    )
    session.add(run)
    session.flush()
    return int(run.id)


def test_source_data_save_and_read(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_source.db"
    _upgrade_sqlite_database(db_path)
    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        _create_source_data(session)
        session.commit()
        client = session.get(Client, 1)
        assert client is not None
        assert client.id_number == "1"
        assert len(client.grants) == 1


def test_snapshot_and_result_payload_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_roundtrip.db"
    _upgrade_sqlite_database(db_path)
    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        _create_source_data(session)
        run_id = _create_run(session, run_trace="RUN1")
        input_payload = _input_payload("CALC1", 2025)
        result_payload = _result_payload("CALC1", 2025)
        session.add(
            FixationInputSnapshot(
                fixation_input_snapshot_id="S1",
                fixation_run_id=run_id,
                input_contract_version="v1",
                input_payload=input_payload,
            )
        )
        session.add(
            FixationResultModel(
                fixation_result_id="R1",
                fixation_run_id=run_id,
                result_contract_version="v1",
                initial_exempt_capital=Decimal("90000.00"),
                grant_impact_total=Decimal("1000.00"),
                future_grant_reserved=Decimal("500.00"),
                future_grant_impact=Decimal("300.00"),
                actual_capitalization_impact=Decimal("200.00"),
                idf_impact=Decimal("100.00"),
                total_impact=Decimal("1600.00"),
                remaining_exempt_capital=Decimal("88400.00"),
                monthly_exempt_pension=Decimal("450.00"),
                capital_exemption_percentage=Decimal("0.982222"),
                pension_exemption_percentage=Decimal("0.450000"),
                result_payload=result_payload,
            )
        )
        session.commit()
        snapshot = session.get(FixationInputSnapshot, "S1")
        result = session.get(FixationResultModel, "R1")
        assert snapshot is not None and result is not None
        FixationInput(**snapshot.input_payload)
        parsed = FixationResult(**result.result_payload)
        assert parsed.status == "success"


def test_audit_and_validation_link_to_integer_run_id(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_linkage.db"
    _upgrade_sqlite_database(db_path)
    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        _create_source_data(session)
        run_id = _create_run(session, run_trace="RUN-LINK", status="validation_failed")
        session.add(
            FixationAuditRow(
                fixation_audit_row_id="AR1",
                fixation_run_id=run_id,
                row_order=1,
                category="initial_entitlement",
                label="Initial",
                output_amount=Decimal("90000.00"),
                impact_amount=Decimal("0.00"),
                details_payload={"k": "v"},
            )
        )
        session.add(
            FixationValidationError(
                fixation_validation_error_id="VE1",
                fixation_run_id=run_id,
                error_order=1,
                code="ERR",
                path="p",
                message="m",
                severity="error",
            )
        )
        session.commit()
        run = session.get(FixationRun, run_id)
        assert run is not None
        assert len(run.fixation_audit_rows) == 1
        assert len(run.fixation_validation_errors) == 1


def test_immutability_between_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_immutability.db"
    _upgrade_sqlite_database(db_path)
    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        _create_source_data(session)
        run1 = _create_run(session, run_trace="RUN1")
        run2 = _create_run(session, run_trace="RUN2")
        session.add(
            FixationInputSnapshot(
                fixation_input_snapshot_id="S1",
                fixation_run_id=run1,
                input_contract_version="v1",
                input_payload=_input_payload("C1", 2025),
            )
        )
        session.add(
            FixationInputSnapshot(
                fixation_input_snapshot_id="S2",
                fixation_run_id=run2,
                input_contract_version="v1",
                input_payload=_input_payload("C2", 2026),
            )
        )
        session.commit()
        s1 = session.get(FixationInputSnapshot, "S1")
        s2 = session.get(FixationInputSnapshot, "S2")
        assert s1 is not None and s2 is not None
        assert s1.input_payload["calculation_id"] == "C1"
        assert s2.input_payload["calculation_id"] == "C2"


def test_reproducibility_payload_contracts(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_repro.db"
    _upgrade_sqlite_database(db_path)
    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        _create_source_data(session)
        run_id = _create_run(session, run_trace="RUN-REP")
        payload = _result_payload("CREP", 2027)
        session.add(
            FixationResultModel(
                fixation_result_id="R-REP",
                fixation_run_id=run_id,
                result_contract_version="v1",
                initial_exempt_capital=Decimal("90000.00"),
                grant_impact_total=Decimal("1000.00"),
                future_grant_reserved=Decimal("500.00"),
                future_grant_impact=Decimal("300.00"),
                actual_capitalization_impact=Decimal("200.00"),
                idf_impact=Decimal("100.00"),
                total_impact=Decimal("1600.00"),
                remaining_exempt_capital=Decimal("88400.00"),
                monthly_exempt_pension=Decimal("450.00"),
                capital_exemption_percentage=Decimal("0.982222"),
                pension_exemption_percentage=Decimal("0.450000"),
                result_payload=payload,
            )
        )
        session.commit()
        run = session.scalar(select(FixationRun).where(FixationRun.id == run_id))
        assert run is not None and run.fixation_result is not None
        parsed_result = FixationResult(**run.fixation_result.result_payload)
        assert parsed_result.audit_rows is not None
        for row in parsed_result.audit_rows:
            AuditRow(**row.model_dump())


def test_database_contains_only_approved_phase1_tables_plus_alembic_version(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_tables.db"
    _upgrade_sqlite_database(db_path)
    actual_tables = set(inspect(create_engine(f"sqlite:///{db_path.as_posix()}")) .get_table_names())
    assert actual_tables == APPROVED_TABLES | {"alembic_version"}
