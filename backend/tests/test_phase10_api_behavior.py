from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session as SASession, sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.fixation_audit_row import FixationAuditRow
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.models.fixation_result import FixationResult as FixationResultModel
from app.models.fixation_run import FixationRun
from app.models.fixation_validation_error import FixationValidationError
from app.schemas.fixation_contracts import FixationInput, FixationResult


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


def _build_client(
    tmp_path: Path,
    *,
    db_name: str,
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, sessionmaker]:
    db_path = tmp_path / db_name
    _upgrade_sqlite_database(db_path)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
    return client, session_local


def _create_client(client: TestClient, *, id_number: str) -> int:
    response = client.post(
        "/api/clients",
        json={
            "full_name": "Jane Doe",
            "id_number": id_number,
            "birth_date": "1970-01-01",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["client_id"], int)
    return int(payload["client_id"])


def _fixation_input(*, calc_id: str, eligibility_year: int = 2025, monthly_cap: float = 1000.0) -> dict:
    return {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": f"{eligibility_year}-01-01",
        "eligibility_year": eligibility_year,
        "monthly_cap": monthly_cap,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grants": [
            {
                "grant_id": "G1",
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
            }
        ],
        "future_grant_reserved": 500.0,
        "actual_capitalizations": [
            {
                "capitalization_id": "AC1",
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "source_label": "manual",
            }
        ],
        "idf": {
            "idf_id": "IDF1",
            "reduction_amount": 1200.0,
            "original_commutation_percent": 35.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2024-01-01",
            "promoter_age_date": "2028-01-01",
            "source_label": "idf_source",
        },
    }


def _fixation_review_input(*, calc_id: str = "review-valid") -> dict:
    payload = _fixation_input(calc_id=calc_id)
    payload["grants"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                **payload["grants"][0],
                "source_item_id": "GR-1",
                "disposition": "include",
            }
        ],
    }
    payload["actual_capitalizations"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                **payload["actual_capitalizations"][0],
                "source_item_id": "AC-1",
                "source_basis": "capitalization certificate",
                "planner_assertion": "advisor confirmed amount",
                "planner_assertion_basis": "reviewed certificate",
                "disposition": "include",
            }
        ],
    }
    return payload


def _invalid_fixation_input(calc_id: str) -> dict:
    payload = _fixation_input(calc_id=calc_id, eligibility_year=2026)
    payload["eligibility_date"] = "2025-01-01"
    return payload


def _counts(session_local: sessionmaker) -> dict[str, int]:
    with session_local() as db:
        return {
            "runs": int(db.scalar(select(func.count()).select_from(FixationRun)) or 0),
            "snapshots": int(db.scalar(select(func.count()).select_from(FixationInputSnapshot)) or 0),
            "results": int(db.scalar(select(func.count()).select_from(FixationResultModel)) or 0),
            "audit_rows": int(db.scalar(select(func.count()).select_from(FixationAuditRow)) or 0),
            "validation_errors": int(db.scalar(select(func.count()).select_from(FixationValidationError)) or 0),
    }


def test_phase10_review_validate_endpoint_validates_without_calculation_or_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_review_validate.db")

    def fail_if_calculation_called(*args, **kwargs):
        raise AssertionError("review validation must not call calculation")

    monkeypatch.setattr("app.api.fixation_routes.calculate_fixation_payload", fail_if_calculation_called)
    monkeypatch.setattr("app.api.fixation_routes.run_fixation", fail_if_calculation_called)

    try:
        unknown_payload = _fixation_review_input(calc_id="review-unknown")
        unknown_payload["grants"] = {"collection_state": "unknown", "items": []}
        unknown_resp = client.post("/api/fixation/review/validate", json=unknown_payload)
        assert unknown_resp.status_code == 200
        assert unknown_resp.json()["valid"] is False
        assert unknown_resp.json()["errors"][0]["path"] == "grants.collection_state"
        assert unknown_resp.json()["errors"][0]["code"] == "UNSUPPORTED_OR_UNAPPROVED_VALUE"

        not_collected_payload = _fixation_review_input(calc_id="review-not-collected")
        not_collected_payload["actual_capitalizations"] = {
            "collection_state": "not_collected",
            "items": [],
        }
        not_collected_resp = client.post("/api/fixation/review/validate", json=not_collected_payload)
        assert not_collected_resp.status_code == 200
        assert not_collected_resp.json()["valid"] is False
        assert not_collected_resp.json()["errors"][0]["path"] == "actual_capitalizations.collection_state"
        assert not_collected_resp.json()["errors"][0]["code"] == "UNSUPPORTED_OR_UNAPPROVED_VALUE"

        confirmed_none_payload = _fixation_review_input(calc_id="review-confirmed-none")
        confirmed_none_payload["grants"] = {"collection_state": "confirmed_none", "items": []}
        confirmed_none_payload["actual_capitalizations"] = {
            "collection_state": "confirmed_none",
            "items": [],
        }
        confirmed_none_resp = client.post("/api/fixation/review/validate", json=confirmed_none_payload)
        assert confirmed_none_resp.status_code == 200
        assert confirmed_none_resp.json() == {"valid": True, "errors": []}

        items_recorded_resp = client.post("/api/fixation/review/validate", json=_fixation_review_input())
        assert items_recorded_resp.status_code == 200
        assert items_recorded_resp.json() == {"valid": True, "errors": []}

        missing_source_payload = _fixation_review_input(calc_id="review-missing-source")
        del missing_source_payload["grants"]["items"][0]["source_item_id"]
        missing_source_resp = client.post("/api/fixation/review/validate", json=missing_source_payload)
        assert missing_source_resp.status_code == 200
        assert missing_source_resp.json()["valid"] is False
        assert missing_source_resp.json()["errors"][0]["path"] == "grants.items[0].source_item_id"
        assert missing_source_resp.json()["errors"][0]["code"] == "MISSING_REQUIRED_VALUE"

        blank_source_payload = _fixation_review_input(calc_id="review-blank-source")
        blank_source_payload["grants"]["items"][0]["source_item_id"] = " "
        blank_source_resp = client.post("/api/fixation/review/validate", json=blank_source_payload)
        assert blank_source_resp.status_code == 200
        assert blank_source_resp.json()["valid"] is False
        assert blank_source_resp.json()["errors"][0]["path"] == "grants.items[0].source_item_id"
        assert blank_source_resp.json()["errors"][0]["code"] == "INVALID_NESTED_ITEM"

        invalid_source_payload = _fixation_review_input(calc_id="review-invalid-source")
        invalid_source_payload["actual_capitalizations"]["items"][0]["source_item_id"] = "bad/source"
        invalid_source_resp = client.post("/api/fixation/review/validate", json=invalid_source_payload)
        assert invalid_source_resp.status_code == 200
        assert invalid_source_resp.json()["valid"] is False
        assert invalid_source_resp.json()["errors"][0]["path"] == "actual_capitalizations.items[0].source_item_id"
        assert invalid_source_resp.json()["errors"][0]["code"] == "INVALID_NESTED_ITEM"

        invalid_payload = _fixation_review_input(calc_id="review-invalid")
        invalid_payload["eligibility_year"] = 2026
        invalid_resp = client.post("/api/fixation/review/validate", json=invalid_payload)
        assert invalid_resp.status_code == 200
        assert invalid_resp.json()["valid"] is False
        assert invalid_resp.json()["errors"][0]["path"] == "fixation_input"

        assert _counts(session_local) == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_full_http_end_to_end_flow(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_e2e.db")
    try:
        client_id = _create_client(client, id_number="001234567")

        employment_resp = client.post(
            f"/api/clients/{client_id}/employment-records",
            json={
                "employer_name": "Employer Inc",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "is_current": False,
                "notes": "employment",
            },
        )
        assert employment_resp.status_code == 200

        employment_id = employment_resp.json()["employment_record_id"]
        grant_resp = client.post(
            f"/api/clients/{client_id}/grants",
            json={
                "employment_record_id": employment_id,
                "employer_name": "Employer Inc",
                "nominal_amount": 10000.0,
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "notes": "grant",
            },
        )
        assert grant_resp.status_code == 200

        cap_resp = client.post(
            f"/api/clients/{client_id}/actual-capitalizations",
            json={
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "source_label": "manual",
                "notes": "cap",
            },
        )
        assert cap_resp.status_code == 200

        payload = _fixation_input(calc_id="calc-e2e")
        validate_resp = client.post("/api/fixation/validate", json=payload)
        calculate_resp = client.post("/api/fixation/calculate", json=payload)
        assert validate_resp.status_code == 200
        assert calculate_resp.status_code == 200
        assert validate_resp.json() == calculate_resp.json()

        save_success_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _fixation_input(calc_id="calc-save-success")},
        )
        assert save_success_resp.status_code == 200
        assert save_success_resp.json()["status"] == "success"
        success_run_id = save_success_resp.json()["run_id"]
        assert isinstance(success_run_id, int)

        save_failed_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _invalid_fixation_input("calc-save-failed")},
        )
        assert save_failed_resp.status_code == 200
        assert save_failed_resp.json()["status"] == "validation_failed"
        failed_run_id = save_failed_resp.json()["run_id"]
        assert isinstance(failed_run_id, int)

        latest_resp = client.get(f"/api/clients/{client_id}/fixation/latest")
        assert latest_resp.status_code == 200
        assert latest_resp.json()["result"] is not None
        assert latest_resp.json()["result"]["status"] == "success"

        history_resp = client.get(f"/api/clients/{client_id}/fixation/history")
        assert history_resp.status_code == 200
        history_payload = history_resp.json()
        assert [row["run_id"] for row in history_payload] == [failed_run_id, success_run_id]

        success_detail_resp = client.get(f"/api/fixation/runs/{success_run_id}")
        failed_detail_resp = client.get(f"/api/fixation/runs/{failed_run_id}")
        assert success_detail_resp.status_code == 200
        assert failed_detail_resp.status_code == 200

        success_detail = success_detail_resp.json()
        failed_detail = failed_detail_resp.json()
        assert success_detail["run"]["run_id"] == success_run_id
        assert failed_detail["run"]["run_id"] == failed_run_id
        assert isinstance(success_detail["run"]["run_id"], int)
        assert isinstance(success_detail["run"]["client_id"], int)
        assert success_detail["result"] is not None
        assert len(success_detail["audit_rows"]) > 0
        assert failed_detail["result"] is None
        assert len(failed_detail["validation_errors"]) > 0
    finally:
        app.dependency_overrides.clear()


def test_phase10_validate_calculate_consistency_without_persistence(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_validate_calculate.db")
    try:
        payload = _fixation_input(calc_id="calc-no-persist")
        validate_resp = client.post("/api/fixation/validate", json=payload)
        calculate_resp = client.post("/api/fixation/calculate", json=payload)

        assert validate_resp.status_code == 200
        assert calculate_resp.status_code == 200
        assert validate_resp.json() == calculate_resp.json()

        counts = _counts(session_local)
        assert counts == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_save_behavior_persistence_boundaries(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_save_behavior.db")
    try:
        client_id = _create_client(client, id_number="3001")

        success_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _fixation_input(calc_id="calc-success")},
        )
        assert success_resp.status_code == 200
        success_run_id = success_resp.json()["run_id"]

        failed_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _invalid_fixation_input("calc-failed")},
        )
        assert failed_resp.status_code == 200
        failed_run_id = failed_resp.json()["run_id"]

        counts = _counts(session_local)
        assert counts["runs"] == 2
        assert counts["snapshots"] == 2
        assert counts["results"] == 1
        assert counts["audit_rows"] > 0
        assert counts["validation_errors"] > 0

        failed_detail_resp = client.get(f"/api/fixation/runs/{failed_run_id}")
        success_detail_resp = client.get(f"/api/fixation/runs/{success_run_id}")
        assert failed_detail_resp.status_code == 200
        assert success_detail_resp.status_code == 200
        failed_detail = failed_detail_resp.json()
        success_detail = success_detail_resp.json()

        assert failed_detail["result"] is None
        assert len(failed_detail["audit_rows"]) == 0
        assert len(failed_detail["validation_errors"]) > 0
        assert success_detail["result"] is not None
        assert len(success_detail["audit_rows"]) > 0
        assert len(success_detail["validation_errors"]) == 0
    finally:
        app.dependency_overrides.clear()


def test_phase10_immutability_and_snapshot_result_integrity(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path, db_name="phase10_immutability.db")
    try:
        client_id = _create_client(client, id_number="4001")

        save_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": _fixation_input(calc_id="calc-immutable", monthly_cap=1000.0),
            },
        )
        assert save_resp.status_code == 200
        run_id = save_resp.json()["run_id"]

        before_detail_resp = client.get(f"/api/fixation/runs/{run_id}")
        assert before_detail_resp.status_code == 200
        before_detail = before_detail_resp.json()
        before_snapshot = copy.deepcopy(before_detail["input_snapshot"])
        before_result = copy.deepcopy(before_detail["result"])

        _ = client.post(
            f"/api/clients/{client_id}/actual-capitalizations",
            json={
                "amount": 99999.0,
                "capitalization_date": "2024-06-01",
                "source_label": "mutated",
            },
        )

        after_detail_resp = client.get(f"/api/fixation/runs/{run_id}")
        assert after_detail_resp.status_code == 200
        after_detail = after_detail_resp.json()

        assert after_detail["input_snapshot"] == before_snapshot
        assert after_detail["result"] == before_result

        reconstructed_input = FixationInput(**after_detail["input_snapshot"])
        reconstructed_result = FixationResult(**after_detail["result"])
        assert reconstructed_input.model_dump(mode="json") == after_detail["input_snapshot"]
        assert reconstructed_result.model_dump(mode="json") == after_detail["result"]
    finally:
        app.dependency_overrides.clear()


def test_phase10_latest_history_rules_and_strict_errors(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path, db_name="phase10_latest_history_errors.db")
    try:
        client_no_runs = _create_client(client, id_number="5001")
        latest_none_resp = client.get(f"/api/clients/{client_no_runs}/fixation/latest")
        assert latest_none_resp.status_code == 200
        assert latest_none_resp.json() == {"result": None}

        client_failed_only = _create_client(client, id_number="5002")
        failed_only_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_failed_only, "input_data": _invalid_fixation_input("calc-only-fail")},
        )
        assert failed_only_resp.status_code == 200
        latest_failed_only_resp = client.get(f"/api/clients/{client_failed_only}/fixation/latest")
        assert latest_failed_only_resp.status_code == 200
        assert latest_failed_only_resp.json() == {"result": None}

        client_mixed = _create_client(client, id_number="5003")
        success_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_mixed, "input_data": _fixation_input(calc_id="calc-mixed-success")},
        )
        failed_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_mixed, "input_data": _invalid_fixation_input("calc-mixed-failed")},
        )
        assert success_resp.status_code == 200
        assert failed_resp.status_code == 200

        latest_mixed_resp = client.get(f"/api/clients/{client_mixed}/fixation/latest")
        assert latest_mixed_resp.status_code == 200
        assert latest_mixed_resp.json()["result"] is not None
        assert latest_mixed_resp.json()["result"]["status"] == "success"

        history_resp = client.get(f"/api/clients/{client_mixed}/fixation/history")
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert len(history) == 2
        assert history[0]["run_id"] == failed_resp.json()["run_id"]
        assert history[1]["run_id"] == success_resp.json()["run_id"]

        missing_client_resp = client.get("/api/clients/999999/fixation/latest")
        assert missing_client_resp.status_code == 404
        assert missing_client_resp.json()["detail"]["code"] == "CLIENT_NOT_FOUND"

        missing_run_resp = client.get("/api/fixation/runs/999999")
        assert missing_run_resp.status_code == 404
        assert missing_run_resp.json()["detail"]["code"] == "FIXATION_RUN_NOT_FOUND"

        invalid_payload = {"calculation_id": "bad"}
        invalid_validate_payload_resp = client.post("/api/fixation/validate", json=invalid_payload)
        invalid_calc_payload_resp = client.post("/api/fixation/calculate", json=invalid_payload)
        invalid_save_payload_resp = client.post(
            "/api/fixation/save",
            json={"client_id": "not-an-int", "input_data": _fixation_input(calc_id="calc-invalid")},
        )
        assert invalid_validate_payload_resp.status_code == 200
        assert invalid_calc_payload_resp.status_code == 200
        assert invalid_validate_payload_resp.json() == invalid_calc_payload_resp.json()
        assert invalid_calc_payload_resp.json()["status"] == "validation_failed"
        assert invalid_calc_payload_resp.json()["validation_errors"]
        assert set(invalid_calc_payload_resp.json()["validation_errors"][0]) == {
            "code",
            "path",
            "message",
            "severity",
            "source_id",
        }
        assert invalid_save_payload_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_phase10_transaction_safety_rollback_on_save_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_local = _build_client(
        tmp_path,
        db_name="phase10_rollback.db",
        raise_server_exceptions=False,
    )
    try:
        client_id = _create_client(client, id_number="6001")

        def failing_commit(self: SASession) -> None:
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(SASession, "commit", failing_commit)

        save_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _fixation_input(calc_id="calc-rollback")},
        )
        assert save_resp.status_code == 500

        counts = _counts(session_local)
        assert counts == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
        }
    finally:
        app.dependency_overrides.clear()
