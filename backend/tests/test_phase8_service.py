from __future__ import annotations

import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from app.models.actual_capitalization import ActualCapitalization
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_result import FixationResult as FixationResultModel
from app.models.fixation_run import FixationRun
from app.models.fixation_validation_error import FixationValidationError
from app.models.grant import Grant
from app.schemas.fixation_contracts import FixationInput
from app.services.fixation_service import (
    assemble_fixation_input,
    create_client_source_data,
    get_fixation_history,
    get_fixation_run_detail,
    get_latest_fixation_result,
    run_fixation,
)


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


def _seed_source_data(session: Session, *, client_id: int = 1) -> int:
    return create_client_source_data(
        db_session=session,
        client_data={
            "client_id": client_id,
            "display_name": f"Client {client_id}",
            "id_number": str(client_id),
            "birth_date": date(1970, 1, 1),
            "status": "active",
        },
        profile_data={
            "client_profile_id": f"CP-{client_id}",
            "birth_date": date(1970, 1, 1),
            "gender": "f",
            "notes": "profile",
        },
        employment_records_data=[
            {
                "employment_record_id": f"E-{client_id}",
                "employer_name": "Employer",
                "work_start_date": date(2010, 1, 1),
                "work_end_date": date(2020, 1, 1),
                "is_current": False,
            }
        ],
        grants_data=[
            {
                "grant_id": f"G-{client_id}",
                "employment_record_id": f"E-{client_id}",
                "employer_name": "Employer",
                "nominal_amount": Decimal("10000.00"),
                "indexed_amount": Decimal("10000.00"),
                "grant_date": date(2020, 1, 1),
                "work_start_date": date(2010, 1, 1),
                "work_end_date": date(2020, 1, 1),
            }
        ],
        actual_capitalizations_data=[
            {
                "capitalization_id": f"AC-{client_id}",
                "amount": Decimal("500.00"),
                "capitalization_date": date(2023, 1, 1),
                "source_label": "manual",
                "notes": "cap",
            }
        ],
    )


def _explicit_parameters(*, calc_id: str, monthly_cap: float, eligibility_year: int = 2025) -> dict:
    return {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": date(eligibility_year, 1, 1),
        "eligibility_year": eligibility_year,
        "monthly_cap": monthly_cap,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grant_impact_multiplier": 1.35,
        "future_grant_reserved": 500.0,
        "idf": {
            "idf_id": "IDF-1",
            "reduction_amount": 1200.0,
            "original_commutation_percent": 35.0,
            "current_commutation_percent": 20.0,
            "commutation_date": date(2024, 1, 1),
            "promoter_age_date": date(2028, 1, 1),
            "source_label": "idf_source",
        },
    }


def _admissible_payload(client_id: int, input_model: FixationInput) -> dict:
    return {
        "calculation_id": input_model.calculation_id,
        "calculation_version": input_model.calculation_version,
        "eligibility_date": input_model.eligibility_date,
        "eligibility_year": input_model.eligibility_year,
        "upstream_context": {
            "profile_id": f"M07-{client_id}",
            "client_id": client_id,
            "state": "qualified",
        },
        "parameter_set": {
            "parameter_set_id": f"PARAMS-{client_id}-{input_model.eligibility_year}",
            "client_id": client_id,
            "tax_year": input_model.eligibility_year,
            "values": {
                "monthly_cap": input_model.monthly_cap,
                "exemption_percentage": input_model.exemption_percentage,
                "capital_multiplier": input_model.capital_multiplier,
                "grant_impact_multiplier": input_model.grant_impact_multiplier,
            },
            "source_basis": "accepted service fixture",
            "status": "accepted",
            "accepted_for_use": True,
            "accepted_by": "test-planner",
            "decision_timestamp": "2025-01-01T00:00:00Z",
        },
        "grants_collection_state": "items_recorded" if input_model.grants else "confirmed_none",
        "grants": [
            {
                **grant.model_dump(mode="json"),
                "item_type": "severance_grant",
                "source_basis": "grant fixture",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "test-planner",
                "decision_timestamp": "2025-01-01T00:00:00Z",
            }
            for grant in input_model.grants
        ],
        "future_grant_reservation": {
            "amount": input_model.future_grant_reserved,
            "source_basis": "reserve fixture",
            "status": "reviewed",
            "accepted_for_use": True,
            "actor": "test-planner",
            "decision_timestamp": "2025-01-01T00:00:00Z",
        },
        "actual_capitalizations_collection_state": (
            "items_recorded" if input_model.actual_capitalizations else "confirmed_none"
        ),
        "actual_capitalizations": [
            {
                "capitalization_id": cap.capitalization_id,
                "item_type": "actual_capitalization",
                "amount": cap.amount,
                "capitalization_date": cap.capitalization_date,
                "recorded_meaning": "historical actual capitalization",
                "source_basis": cap.source_label or "capitalization fixture",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "test-planner",
                "decision_timestamp": "2025-01-01T00:00:00Z",
                "notes": cap.notes,
            }
            for cap in input_model.actual_capitalizations
        ],
        "idf": None,
        "metadata": input_model.metadata,
    }


def test_create_client_source_data_persists_source_entities_only(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_source_create.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        assert session.get(Client, client_id) is not None
        assert session.get(ClientProfile, "CP-1") is not None
        assert session.get(EmploymentRecord, "E-1") is not None
        assert session.get(Grant, "G-1") is not None
        assert session.get(ActualCapitalization, "AC-1") is not None

    tables = set(inspect(create_engine(f"sqlite:///{db_path.as_posix()}")) .get_table_names())
    assert not any(name.startswith("idf") for name in tables)


def test_assemble_fixation_input_from_source_and_explicit_parameters(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_assemble.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)
        params = _explicit_parameters(calc_id="calc-assemble", monthly_cap=1000.0)

        model = assemble_fixation_input(client_id=client_id, db_session=session, explicit_parameters=params)

        assert isinstance(model, FixationInput)
        assert len(model.grants) == 1
        assert model.grants[0].grant_id == "G-1"
        assert len(model.actual_capitalizations) == 1
        assert model.actual_capitalizations[0].capitalization_id == "AC-1"
        assert model.idf is not None
        assert model.idf.idf_id == "IDF-1"
        assert model.idf.reduction_amount == 1200.0
        assert model.monthly_cap == 1000.0
        assert model.exemption_percentage == 0.5
        assert model.capital_multiplier == 180.0
        assert model.metadata is None


def test_run_fixation_success_persists_run_snapshot_result_and_audit(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_run_success.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)
        input_model = assemble_fixation_input(
            client_id=client_id,
            db_session=session,
            explicit_parameters=_explicit_parameters(calc_id="calc-success", monthly_cap=1000.0),
        )

        run_id = run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(client_id, input_model),
            db_session=session,
        )

        run = session.get(FixationRun, run_id)
        assert run is not None
        assert run.status == "success"
        assert run.fixation_input_snapshot is not None
        assert run.fixation_result is not None
        assert len(run.fixation_audit_rows) > 0
        assert len(run.fixation_validation_errors) == 0


def test_run_fixation_validation_failed_persists_errors_without_result(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_run_validation_failed.db"
    _upgrade_sqlite_database(db_path)

    invalid_payload = {
        "calculation_id": "calc-fail",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2026,
        "monthly_cap": 1000.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grants": [],
        "future_grant_reserved": 0.0,
        "actual_capitalizations": [],
        "idf": None,
    }

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        run_id = run_fixation(client_id=client_id, input_data=invalid_payload, db_session=session)

        run = session.get(FixationRun, run_id)
        assert run is not None
        assert run.status == "validation_failed"
        assert run.fixation_input_snapshot is not None
        assert run.fixation_result is None
        assert len(run.fixation_audit_rows) == 0
        assert len(run.fixation_validation_errors) > 0


def test_multi_run_immutability_keeps_previous_run_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_multi_run.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        run1_input = assemble_fixation_input(
            client_id=client_id,
            db_session=session,
            explicit_parameters=_explicit_parameters(calc_id="calc-run1", monthly_cap=1000.0),
        )
        run1_id = run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(client_id, run1_input),
            db_session=session,
        )

        run1 = session.get(FixationRun, run1_id)
        assert run1 is not None
        assert run1.fixation_input_snapshot is not None
        assert run1.fixation_result is not None
        run1_snapshot_before = dict(run1.fixation_input_snapshot.input_payload)
        run1_result_before = dict(run1.fixation_result.result_payload)
        run1_audit_before = [
            {
                "row_order": row.row_order,
                "category": row.category,
                "source_id": row.source_id,
                "label": row.label,
                "input_amount": row.input_amount,
                "output_amount": row.output_amount,
                "impact_amount": row.impact_amount,
                "details_payload": dict(row.details_payload),
            }
            for row in run1.fixation_audit_rows
        ]
        run1_validation_errors_before = [
            {
                "error_order": err.error_order,
                "code": err.code,
                "path": err.path,
                "message": err.message,
                "severity": err.severity,
                "source_id": err.source_id,
            }
            for err in run1.fixation_validation_errors
        ]

        run2_input = assemble_fixation_input(
            client_id=client_id,
            db_session=session,
            explicit_parameters=_explicit_parameters(calc_id="calc-run2", monthly_cap=1200.0),
        )
        run2_id = run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(client_id, run2_input),
            db_session=session,
        )

        run1 = session.get(FixationRun, run1_id)
        run2 = session.get(FixationRun, run2_id)

        assert run1 is not None
        assert run2 is not None
        assert run1_id != run2_id
        assert run1.fixation_input_snapshot is not None
        assert run2.fixation_input_snapshot is not None
        assert run1.fixation_result is not None
        assert run2.fixation_result is not None
        assert run1.is_latest is False
        assert run2.is_latest is True
        assert session.scalar(
            select(func.count()).select_from(FixationRun).where(
                FixationRun.client_id == client_id,
                FixationRun.is_latest.is_(True),
            )
        ) == 1
        assert run1.fixation_input_snapshot.input_payload["parameter_set"]["values"]["monthly_cap"] == 1000.0
        assert run2.fixation_input_snapshot.input_payload["parameter_set"]["values"]["monthly_cap"] == 1200.0
        assert run1.fixation_input_snapshot.input_payload == run1_snapshot_before
        assert run1.fixation_result.result_payload == run1_result_before
        assert [
            {
                "row_order": row.row_order,
                "category": row.category,
                "source_id": row.source_id,
                "label": row.label,
                "input_amount": row.input_amount,
                "output_amount": row.output_amount,
                "impact_amount": row.impact_amount,
                "details_payload": dict(row.details_payload),
            }
            for row in run1.fixation_audit_rows
        ] == run1_audit_before
        assert [
            {
                "error_order": err.error_order,
                "code": err.code,
                "path": err.path,
                "message": err.message,
                "severity": err.severity,
                "source_id": err.source_id,
            }
            for err in run1.fixation_validation_errors
        ] == run1_validation_errors_before


def test_get_latest_fixation_result_returns_newest_successful_run(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_latest.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(
                client_id,
                assemble_fixation_input(
                    client_id=client_id,
                    db_session=session,
                    explicit_parameters=_explicit_parameters(calc_id="calc-old", monthly_cap=1000.0),
                ),
            ),
            db_session=session,
        )
        run2_id = run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(
                client_id,
                assemble_fixation_input(
                    client_id=client_id,
                    db_session=session,
                    explicit_parameters=_explicit_parameters(calc_id="calc-new", monthly_cap=1300.0),
                ),
            ),
            db_session=session,
        )

        latest = get_latest_fixation_result(client_id=client_id, db_session=session)
        assert latest is not None
        assert latest.id == run2_id
        assert latest.fixation_result is not None


def test_get_fixation_history_returns_all_runs_newest_first(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_history.db"
    _upgrade_sqlite_database(db_path)

    invalid_payload = {
        "calculation_id": "calc-fail",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2026,
        "monthly_cap": 1000.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grants": [],
        "future_grant_reserved": 0.0,
        "actual_capitalizations": [],
        "idf": None,
    }

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(
                client_id,
                assemble_fixation_input(
                    client_id=client_id,
                    db_session=session,
                    explicit_parameters=_explicit_parameters(calc_id="calc-success", monthly_cap=1000.0),
                ),
            ),
            db_session=session,
        )
        failed_id = run_fixation(client_id=client_id, input_data=invalid_payload, db_session=session)

        history = get_fixation_history(client_id=client_id, db_session=session)
        assert len(history) == 2
        assert history[0].id == failed_id
        assert history[0].status == "validation_failed"
        assert history[1].status == "success"


def test_get_fixation_run_detail_returns_full_run_data(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_run_detail.db"
    _upgrade_sqlite_database(db_path)

    invalid_payload = {
        "calculation_id": "calc-fail",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2026,
        "monthly_cap": 1000.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grants": [],
        "future_grant_reserved": 0.0,
        "actual_capitalizations": [],
        "idf": None,
    }

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)

        success_id = run_fixation(
            client_id=client_id,
            input_data=_admissible_payload(
                client_id,
                assemble_fixation_input(
                    client_id=client_id,
                    db_session=session,
                    explicit_parameters=_explicit_parameters(calc_id="calc-success", monthly_cap=1000.0),
                ),
            ),
            db_session=session,
        )
        failed_id = run_fixation(client_id=client_id, input_data=invalid_payload, db_session=session)

        success_detail = get_fixation_run_detail(
            client_id=client_id,
            run_id=success_id,
            db_session=session,
        )
        failed_detail = get_fixation_run_detail(
            client_id=client_id,
            run_id=failed_id,
            db_session=session,
        )

        assert success_detail is not None
        assert success_detail.fixation_input_snapshot is not None
        assert success_detail.fixation_result is not None
        assert len(success_detail.fixation_audit_rows) > 0
        assert len(success_detail.fixation_validation_errors) == 0

        assert failed_detail is not None
        assert failed_detail.fixation_input_snapshot is not None
        assert failed_detail.fixation_result is None
        assert len(failed_detail.fixation_validation_errors) > 0


def test_run_fixation_rolls_back_on_persistence_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "phase8_rollback.db"
    _upgrade_sqlite_database(db_path)

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        client_id = _seed_source_data(session, client_id=1)
        input_model = assemble_fixation_input(
            client_id=client_id,
            db_session=session,
            explicit_parameters=_explicit_parameters(calc_id="calc-rollback", monthly_cap=1000.0),
        )

        original_commit = session.commit

        def failing_commit() -> None:
            raise RuntimeError("simulated commit failure")

        session.commit = failing_commit

        with pytest.raises(RuntimeError, match="simulated commit failure"):
            run_fixation(
                client_id=client_id,
                input_data=_admissible_payload(client_id, input_model),
                db_session=session,
            )

        session.commit = original_commit

        run_count = session.scalar(select(func.count()).select_from(FixationRun))
        snapshot_count = session.scalar(select(func.count()).select_from(FixationInputSnapshot))
        result_count = session.scalar(select(func.count()).select_from(FixationResultModel))
        error_count = session.scalar(select(func.count()).select_from(FixationValidationError))

        assert run_count == 0
        assert snapshot_count == 0
        assert result_count == 0
        assert error_count == 0
