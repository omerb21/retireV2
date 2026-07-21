from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.db.session import get_db
from app.main import app
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.services.fixation_admission_service import parse_and_admit_fixation_payload
from app.services.fixation_service import calculate_fixation_payload


load_all_models()


def _payload(*, client_id: int = 1) -> dict:
    return {
        "calculation_id": "pkg-001",
        "calculation_version": "pkg-001-v1",
        "eligibility_date": "2026-01-01",
        "eligibility_year": 2026,
        "upstream_context": {
            "profile_id": "m07-1",
            "client_id": client_id,
            "state": "qualified",
        },
        "parameter_set": {
            "parameter_set_id": "params-2026-accepted",
            "client_id": client_id,
            "tax_year": 2026,
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "values": {
                "monthly_cap": 1000.0,
                "exemption_percentage": 0.5,
                "capital_multiplier": 180.0,
                "grant_impact_multiplier": 1.35,
            },
            "source_basis": "accepted test evidence",
            "status": "reviewed",
            "accepted_for_use": True,
            "accepted_by": "planner-1",
            "decision_timestamp": "2026-01-01T08:00:00Z",
        },
        "grants_collection_state": "items_recorded",
        "grants": [
            {
                "grant_id": "grant-1",
                "item_type": "severance_grant",
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "source_basis": "grant source",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T08:01:00Z",
            }
        ],
        "future_grant_reservation": {
            "amount": 500.0,
            "source_basis": "reserve basis",
            "status": "reviewed",
            "accepted_for_use": True,
            "actor": "planner-1",
            "decision_timestamp": "2026-01-01T08:02:00Z",
        },
        "actual_capitalizations_collection_state": "items_recorded",
        "actual_capitalizations": [
            {
                "capitalization_id": "cap-1",
                "item_type": "actual_capitalization",
                "amount": 250.0,
                "capitalization_date": "2025-01-01",
                "recorded_meaning": "historical actual capitalization",
                "source_basis": "capitalization source",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T08:03:00Z",
            }
        ],
        "idf": None,
        "metadata": {"source_data_version_label": "source-v1"},
    }


def _error_paths(payload: dict, *, client_id: int | None = None) -> set[str]:
    _, _, errors = parse_and_admit_fixation_payload(payload, client_id=client_id)
    return {error.path for error in errors}


def test_parameter_set_is_mandatory_accepted_complete_and_applicable() -> None:
    missing_set = _payload()
    del missing_set["parameter_set"]
    assert "parameter_set" in _error_paths(missing_set)

    unaccepted = _payload()
    unaccepted["parameter_set"]["accepted_for_use"] = False
    assert "parameter_set.accepted_for_use" in _error_paths(unaccepted)

    missing_required_value = _payload()
    del missing_required_value["parameter_set"]["values"]["grant_impact_multiplier"]
    assert "parameter_set.values.grant_impact_multiplier" in _error_paths(missing_required_value)

    wrong_year = _payload()
    wrong_year["parameter_set"]["tax_year"] = 2025
    assert "parameter_set.tax_year" in _error_paths(wrong_year)

    stale = _payload()
    stale["parameter_set"]["effective_from"] = "2025-01-01"
    stale["parameter_set"]["effective_to"] = "2025-12-31"
    assert "parameter_set.effective_to" in _error_paths(stale)


def test_only_admitted_values_reach_engine_and_result_is_deterministic() -> None:
    payload = _payload()
    before = copy.deepcopy(payload)

    first = calculate_fixation_payload(payload)
    second = calculate_fixation_payload(payload)

    assert first.status == "success"
    assert first.model_dump() == second.model_dump()
    assert payload == before
    assert first.monthly_cap == payload["parameter_set"]["values"]["monthly_cap"]
    assert first.future_grant_impact == 675.0


def test_reviewed_zero_and_preserved_exclusion_decisions() -> None:
    payload = _payload()
    payload["grants"][0]["inclusion_decision"] = "exclude"
    payload["actual_capitalizations"][0]["inclusion_decision"] = "exclude"
    payload["future_grant_reservation"] = None

    context, engine_input, errors = parse_and_admit_fixation_payload(payload, client_id=1)
    result = calculate_fixation_payload(payload)

    assert errors == []
    assert context is not None and context.grants[0].inclusion_decision == "exclude"
    assert engine_input is not None and engine_input.grants == []
    assert engine_input.actual_capitalizations == []
    assert result.status == "success"
    assert result.total_impact == 0.0


def test_conflict_decision_is_used_without_system_source_ranking() -> None:
    payload = _payload()
    grant = payload["grants"][0]
    grant["conflict_indicator"] = True
    grant["accepted_value"] = 1234.0

    context, engine_input, errors = parse_and_admit_fixation_payload(payload)

    assert errors == []
    assert context is not None and context.grants[0].conflict_indicator is True
    assert engine_input is not None and engine_input.grants[0].indexed_amount == 1234.0


def test_acceptance_evidence_unsupported_inputs_idf_and_m07_gate_block_engine() -> None:
    unaccepted_grant = _payload()
    unaccepted_grant["grants"][0]["accepted_for_use"] = False
    assert "grants[0].accepted_for_use" in _error_paths(unaccepted_grant)

    unsupported_grant = _payload()
    unsupported_grant["grants"][0]["support_status"] = "unsupported"
    assert "grants[0].support_status" in _error_paths(unsupported_grant)

    missing_support_decision = _payload()
    del missing_support_decision["grants"][0]["support_status"]
    assert "grants[0].support_status" in _error_paths(missing_support_decision)

    unaccepted_reserve = _payload()
    unaccepted_reserve["future_grant_reservation"]["accepted_for_use"] = False
    assert "future_grant_reservation.accepted_for_use" in _error_paths(unaccepted_reserve)

    unaccepted_cap = _payload()
    unaccepted_cap["actual_capitalizations"][0]["accepted_for_use"] = False
    assert "actual_capitalizations[0].accepted_for_use" in _error_paths(unaccepted_cap)

    blocked_m07 = _payload()
    blocked_m07["upstream_context"]["state"] = "blocked"
    assert "upstream_context.state" in _error_paths(blocked_m07)

    idf = _payload()
    idf["idf"] = {
        "idf_id": "idf-1",
        "reduction_amount": 1000.0,
        "original_commutation_percent": 25.0,
        "current_commutation_percent": 20.0,
        "commutation_date": "2025-01-01",
        "promoter_age_date": "2027-01-01",
    }
    result = calculate_fixation_payload(idf)
    assert result.status == "requires_special_handling"
    assert result.validation_errors[0].path == "idf"


def _upgrade_database(db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_saved_manifest_is_immutable_and_run_access_is_client_isolated(tmp_path: Path) -> None:
    db_path = tmp_path / "pkg001.db"
    _upgrade_database(db_path)
    session_local = sessionmaker(bind=create_engine(f"sqlite:///{db_path.as_posix()}"))

    def override_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        owner = client.post(
            "/api/clients",
            json={"full_name": "Owner", "id_number": "pkg-owner", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        other = client.post(
            "/api/clients",
            json={"full_name": "Other", "id_number": "pkg-other", "birth_date": "1970-01-01"},
        ).json()["client_id"]

        payload = _payload(client_id=owner)
        saved = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": payload},
        )
        assert saved.status_code == 200
        assert saved.json()["status"] == "success"
        run_id = saved.json()["run_id"]

        payload["parameter_set"]["values"]["monthly_cap"] = 999999.0
        owner_detail = client.get(f"/api/clients/{owner}/fixation/runs/{run_id}")
        other_detail = client.get(f"/api/clients/{other}/fixation/runs/{run_id}")
        assert owner_detail.status_code == 200
        assert other_detail.status_code == 404
        assert owner_detail.json()["input_snapshot"]["parameter_set"]["values"]["monthly_cap"] == 1000.0
        assert owner_detail.json()["input_snapshot"]["grants"][0]["inclusion_decision"] == "include"

        cross_client_calculation = client.post(
            f"/api/clients/{other}/fixation/calculate",
            json=_payload(client_id=owner),
        )
        assert cross_client_calculation.status_code == 200
        assert cross_client_calculation.json()["status"] == "validation_failed"
        assert {
            error["path"] for error in cross_client_calculation.json()["validation_errors"]
        } == {"upstream_context.client_id", "parameter_set.client_id"}

        idf_payload = _payload(client_id=owner)
        idf_payload["idf"] = {
            "idf_id": "idf-save",
            "reduction_amount": 1000.0,
            "original_commutation_percent": 25.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2025-01-01",
            "promoter_age_date": "2027-01-01",
        }
        idf_saved = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": idf_payload},
        )
        assert idf_saved.status_code == 200
        assert idf_saved.json()["status"] == "requires_special_handling"
        idf_detail = client.get(
            f"/api/clients/{owner}/fixation/runs/{idf_saved.json()['run_id']}"
        ).json()
        assert idf_detail["run"]["status"] == "requires_special_handling"
        assert idf_detail["result"] is None

        with session_local() as session:
            snapshot = session.scalar(
                select(FixationInputSnapshot).where(FixationInputSnapshot.fixation_run_id == run_id)
            )
            assert snapshot is not None
            assert snapshot.input_payload["parameter_set"]["parameter_set_id"] == "params-2026-accepted"

        mismatched = _payload(client_id=other)
        rejected = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": mismatched},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "validation_failed"
    finally:
        app.dependency_overrides.clear()
