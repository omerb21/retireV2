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
from app.models.internal_planner_judgment import InternalPlannerJudgment
from app.schemas.fixation_admissibility import ResolvedFixationAdmissionInput
from app.schemas.fixation_contracts import FixationInput, FixationResult
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision


_M07_REVISIONS: dict[int, str] = {}


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


def _create_client(
    client: TestClient,
    session_local: sessionmaker,
    *,
    id_number: str,
) -> int:
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
    client_id = int(payload["client_id"])
    with session_local() as db:
        revision_id, _ = seed_eligibility_revision(
            db,
            client_id=client_id,
            eligibility_dates=("2025-01-01",),
        )
        db.commit()
    _M07_REVISIONS[client_id] = revision_id
    return client_id


def _fixation_input(
    *,
    calc_id: str,
    eligibility_year: int = 2025,
    monthly_cap: float = 1000.0,
    client_id: int = 1,
) -> dict:
    legacy_payload = {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": f"{eligibility_year}-01-01",
        "eligibility_year": eligibility_year,
        "upstream_context": {
            "profile_id": f"M07-{client_id}",
            "client_id": client_id,
            "state": "qualified",
        },
        "parameter_set": {
            "parameter_set_id": f"PARAMS-{client_id}-{eligibility_year}",
            "client_id": client_id,
            "tax_year": eligibility_year,
            "values": {
                "monthly_cap": monthly_cap,
                "exemption_percentage": 0.5,
                "capital_multiplier": 180.0,
                "grant_impact_multiplier": 1.35,
            },
            "source_basis": "accepted regression fixture",
            "status": "accepted",
            "accepted_for_use": True,
            "accepted_by": "test-planner",
            "decision_timestamp": "2025-01-01T00:00:00Z",
        },
        "grants_collection_state": "items_recorded",
        "grants": [
            {
                "grant_id": "G1",
                "client_id": client_id,
                "item_type": "severance_grant",
                "indexation_mode": "asserted_indexed_amount",
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "source_basis": "grant fixture",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "test-planner",
                "decision_timestamp": "2025-01-01T00:00:00Z",
            }
        ],
        "future_grant_reservation": {
            "amount": 500.0,
            "source_basis": "reserve fixture",
            "status": "reviewed",
            "accepted_for_use": True,
            "actor": "test-planner",
            "decision_timestamp": "2025-01-01T00:00:00Z",
        },
        "actual_capitalizations_collection_state": "items_recorded",
        "actual_capitalizations": [
            {
                "capitalization_id": "AC1",
                "item_type": "actual_capitalization",
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "recorded_meaning": "historical actual capitalization",
                "source_basis": "capitalization fixture",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "test-planner",
                "decision_timestamp": "2025-01-01T00:00:00Z",
            }
        ],
        "idf": None,
    }
    return resolver_payload(
        legacy_payload,
        revision_id=_M07_REVISIONS[client_id],
    )


def _fixation_review_input(*, calc_id: str = "review-valid") -> dict:
    payload = {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2025,
        "monthly_cap": 1000.0,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180.0,
        "grant_impact_multiplier": 1.35,
        "future_grant_reserved": 500.0,
        "idf": None,
    }
    payload["grants"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                "grant_id": "G1",
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "source_item_id": "GR-1",
                "disposition": "include",
            }
        ],
    }
    payload["actual_capitalizations"] = {
        "collection_state": "items_recorded",
        "items": [
            {
                "capitalization_id": "AC1",
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "source_label": "manual",
                "notes": None,
                "source_item_id": "AC-1",
                "source_basis": "capitalization certificate",
                "planner_assertion": "advisor confirmed amount",
                "planner_assertion_basis": "reviewed certificate",
                "disposition": "include",
            }
        ],
    }
    return payload


def _planner_review_context() -> dict:
    return {
        "grants": {
            "collection_state": "items_recorded",
            "included_source_reference_ids": ["GR-1"],
            "excluded_source_reference_ids": ["GR-2"],
        },
        "actual_capitalizations": {
            "collection_state": "items_recorded",
            "included_source_reference_ids": ["AC-1"],
            "excluded_source_reference_ids": ["AC-2"],
        },
    }


def _internal_planner_judgment_payload() -> dict:
    return {
        "handling_status": "continue_internal_review",
        "next_internal_action": "Review supporting source records internally",
        "internal_note": "Internal planner note",
    }


def _invalid_fixation_input(calc_id: str, *, client_id: int = 1) -> dict:
    payload = _fixation_input(calc_id=calc_id, eligibility_year=2026, client_id=client_id)
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
            "internal_planner_judgments": int(
                db.scalar(select(func.count()).select_from(InternalPlannerJudgment)) or 0
            ),
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
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_review_convert_endpoint_transient_conversion_without_calculation_or_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_review_convert.db")

    def fail_if_calculation_called(*args, **kwargs):
        raise AssertionError("review conversion must not call calculation or save")

    monkeypatch.setattr("app.api.fixation_routes.calculate_fixation_payload", fail_if_calculation_called)
    monkeypatch.setattr("app.api.fixation_routes.run_fixation", fail_if_calculation_called)

    try:
        payload = _fixation_review_input(calc_id="review-convert")
        payload["metadata"] = {"source_data_version_label": "review-only"}
        payload["grants"]["items"].append(
            {
                **payload["grants"]["items"][0],
                "source_item_id": "GR-2",
                "grant_id": "G2",
                "disposition": "exclude",
            }
        )
        payload["actual_capitalizations"]["items"].append(
            {
                **payload["actual_capitalizations"]["items"][0],
                "source_item_id": "AC-2",
                "capitalization_id": "AC2",
                "amount": 250.0,
                "disposition": "exclude",
            }
        )

        response = client.post("/api/fixation/review/convert", json=payload)

        assert response.status_code == 200
        converted = response.json()
        FixationInput(**converted)
        assert converted["calculation_id"] == "review-convert"
        assert [grant["grant_id"] for grant in converted["grants"]] == ["G1"]
        assert [cap["capitalization_id"] for cap in converted["actual_capitalizations"]] == ["AC1"]
        assert "metadata" not in converted
        assert "collection_state" not in converted["grants"][0]
        assert "source_item_id" not in converted["grants"][0]
        assert "disposition" not in converted["grants"][0]
        assert "source_item_id" not in converted["actual_capitalizations"][0]
        assert "disposition" not in converted["actual_capitalizations"][0]
        assert "source_basis" not in converted["actual_capitalizations"][0]
        assert "planner_assertion" not in converted["actual_capitalizations"][0]
        assert "planner_assertion_basis" not in converted["actual_capitalizations"][0]
        assert _counts(session_local) == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("domain", "state", "expected_path"),
    [
        ("grants", "unknown", "grants.collection_state"),
        ("actual_capitalizations", "not_collected", "actual_capitalizations.collection_state"),
    ],
)
def test_phase10_review_convert_endpoint_rejects_blocking_states(
    tmp_path: Path,
    domain: str,
    state: str,
    expected_path: str,
) -> None:
    client, session_local = _build_client(tmp_path, db_name=f"phase10_review_convert_{domain}.db")
    try:
        payload = _fixation_review_input(calc_id="review-blocked")
        payload[domain] = {"collection_state": state, "items": []}

        response = client.post("/api/fixation/review/convert", json=payload)

        assert response.status_code == 422
        assert response.json()[0]["path"] == expected_path
        assert response.json()[0]["code"] == "UNSUPPORTED_OR_UNAPPROVED_VALUE"
        assert _counts(session_local) == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_review_convert_endpoint_rejects_invalid_payload_with_stable_errors(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_review_convert_invalid.db")
    try:
        payload = _fixation_review_input(calc_id="review-invalid-convert")
        del payload["grants"]["items"][0]["source_item_id"]

        response = client.post("/api/fixation/review/convert", json=payload)

        assert response.status_code == 422
        assert response.json()[0]["path"] == "grants.items[0].source_item_id"
        assert response.json()[0]["code"] == "MISSING_REQUIRED_VALUE"
        assert _counts(session_local) == {
            "runs": 0,
            "snapshots": 0,
            "results": 0,
            "audit_rows": 0,
            "validation_errors": 0,
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_full_http_end_to_end_flow(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_e2e.db")
    try:
        client_id = _create_client(client, session_local, id_number="001234567")

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
                "employer_name": "Employer Inc",
                "employer_withholding_file_number": "WF-100",
                "exempt_grant_amount": 10000.0,
                "grant_receipt_date": "2020-01-01",
                "employment_start_date": "2010-01-01",
                "employment_end_date": "2020-01-01",
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
        validate_resp = client.post(f"/api/clients/{client_id}/fixation/validate", json=payload)
        calculate_resp = client.post(f"/api/clients/{client_id}/fixation/calculate", json=payload)
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

        success_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{success_run_id}")
        failed_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{failed_run_id}")
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
        client_id = _create_client(
            client, session_local, id_number="phase10-no-persist"
        )
        payload = _fixation_input(calc_id="calc-no-persist")
        validate_resp = client.post(f"/api/clients/{client_id}/fixation/validate", json=payload)
        calculate_resp = client.post(f"/api/clients/{client_id}/fixation/calculate", json=payload)

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
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()


def test_phase10_save_behavior_persistence_boundaries(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_save_behavior.db")
    try:
        client_id = _create_client(client, session_local, id_number="3001")

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

        failed_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{failed_run_id}")
        success_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{success_run_id}")
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


def test_phase10_save_persists_optional_planner_review_context_without_changing_snapshot_or_result(
    tmp_path: Path,
) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_review_context.db")
    try:
        client_id = _create_client(client, session_local, id_number="3101")
        input_payload = _fixation_input(calc_id="calc-review-context")
        review_context = _planner_review_context()

        response = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": input_payload,
                "planner_review_context": {
                    **review_context,
                    "source_metadata_context": [{"source_basis": "must not persist"}],
                },
            },
        )
        assert response.status_code == 422

        save_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": input_payload,
                "planner_review_context": review_context,
            },
        )
        assert save_resp.status_code == 200
        run_id = save_resp.json()["run_id"]

        detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        resolved_snapshot = ResolvedFixationAdmissionInput(
            **detail["input_snapshot"]
        )
        expected_snapshot = resolved_snapshot.model_dump(mode="json")
        assert resolved_snapshot.eligibility_date.isoformat() == "2025-01-01"
        assert resolved_snapshot.eligibility_year == 2025
        assert resolved_snapshot.grants[0].selected_calculation_amount == 10000.0
        assert resolved_snapshot.m07_resolution.outcome == "resolved"
        assert detail["planner_review_context"] == review_context
        assert detail["input_snapshot"] == expected_snapshot
        assert FixationResult(**detail["result"]).status == "success"

        with session_local() as db:
            snapshot = db.scalar(
                select(FixationInputSnapshot).where(FixationInputSnapshot.fixation_run_id == run_id)
            )
            assert snapshot is not None
            assert snapshot.planner_review_context == review_context
            assert snapshot.input_payload == expected_snapshot
    finally:
        app.dependency_overrides.clear()


def test_phase10_save_without_planner_review_context_remains_valid(tmp_path: Path) -> None:
    client, session_local = _build_client(
        tmp_path, db_name="phase10_no_review_context.db"
    )
    try:
        client_id = _create_client(client, session_local, id_number="3102")

        save_resp = client.post(
            "/api/fixation/save",
            json={"client_id": client_id, "input_data": _fixation_input(calc_id="calc-no-review-context")},
        )
        assert save_resp.status_code == 200

        detail_resp = client.get(
            f"/api/clients/{client_id}/fixation/runs/{save_resp.json()['run_id']}"
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["planner_review_context"] is None
        assert detail_resp.json()["input_snapshot"] is not None
        assert detail_resp.json()["result"] is not None
    finally:
        app.dependency_overrides.clear()


def test_phase10_internal_planner_judgment_create_and_run_detail_are_immutable(
    tmp_path: Path,
) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_internal_judgment.db")
    try:
        client_id = _create_client(client, session_local, id_number="3201")
        input_payload = _fixation_input(calc_id="calc-internal-judgment")
        review_context = _planner_review_context()

        save_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": input_payload,
                "planner_review_context": review_context,
            },
        )
        assert save_resp.status_code == 200
        run_id = save_resp.json()["run_id"]

        before_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}")
        assert before_detail_resp.status_code == 200
        before_detail = before_detail_resp.json()
        assert before_detail["internal_planner_judgment"] is None
        before_snapshot = copy.deepcopy(before_detail["input_snapshot"])
        before_result = copy.deepcopy(before_detail["result"])
        before_review_context = copy.deepcopy(before_detail["planner_review_context"])

        create_resp = client.post(
            f"/api/clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
            json=_internal_planner_judgment_payload(),
        )
        assert create_resp.status_code == 200
        assert create_resp.json() == {
            "saved_run_id": run_id,
            **_internal_planner_judgment_payload(),
        }

        detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["internal_planner_judgment"] == create_resp.json()
        assert detail["input_snapshot"] == before_snapshot
        assert detail["result"] == before_result
        assert detail["planner_review_context"] == before_review_context

        duplicate_resp = client.post(
            f"/api/clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
            json={
                "handling_status": "internal_action_identified",
                "next_internal_action": "Different internal action",
                "internal_note": "Replacement attempt",
            },
        )
        assert duplicate_resp.status_code == 409
        assert duplicate_resp.json()["detail"]["code"] == "INTERNAL_PLANNER_JUDGMENT_ALREADY_EXISTS"

        with session_local() as db:
            judgments = list(db.scalars(select(InternalPlannerJudgment)).all())
            assert len(judgments) == 1
            assert judgments[0].fixation_run_id == run_id
            assert judgments[0].handling_status == "continue_internal_review"
    finally:
        app.dependency_overrides.clear()


def test_phase10_internal_planner_judgment_rejects_missing_run_invalid_status_and_extra_fields(
    tmp_path: Path,
) -> None:
    client, session_local = _build_client(tmp_path, db_name="phase10_internal_judgment_errors.db")
    try:
        missing_resp = client.post(
            "/api/clients/999999/fixation/runs/999999/internal-planner-judgment",
            json=_internal_planner_judgment_payload(),
        )
        assert missing_resp.status_code == 404
        assert missing_resp.json()["detail"]["code"] == "FIXATION_RUN_NOT_FOUND"

        client_id = _create_client(client, session_local, id_number="3202")
        save_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": _fixation_input(calc_id="calc-internal-jgment-errors"),
            },
        )
        assert save_resp.status_code == 200
        run_id = save_resp.json()["run_id"]

        invalid_status_resp = client.post(
            f"/api/clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
            json={
                **_internal_planner_judgment_payload(),
                "handling_status": "ready_for_client_decision",
            },
        )
        assert invalid_status_resp.status_code == 422

        extra_field_resp = client.post(
            f"/api/clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
            json={
                **_internal_planner_judgment_payload(),
                "saved_run_id": run_id,
            },
        )
        assert extra_field_resp.status_code == 422

        blank_action_resp = client.post(
            f"/api/clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
            json={
                "handling_status": "not_used_for_decision",
                "next_internal_action": " ",
            },
        )
        assert blank_action_resp.status_code == 422

        counts = _counts(session_local)
        assert counts["internal_planner_judgments"] == 0
    finally:
        app.dependency_overrides.clear()


def test_phase10_immutability_and_snapshot_result_integrity(tmp_path: Path) -> None:
    client, session_local = _build_client(
        tmp_path, db_name="phase10_immutability.db"
    )
    try:
        client_id = _create_client(client, session_local, id_number="4001")

        save_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_id,
                "input_data": _fixation_input(calc_id="calc-immutable", monthly_cap=1000.0),
            },
        )
        assert save_resp.status_code == 200
        run_id = save_resp.json()["run_id"]

        before_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}")
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

        after_detail_resp = client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}")
        assert after_detail_resp.status_code == 200
        after_detail = after_detail_resp.json()

        assert after_detail["input_snapshot"] == before_snapshot
        assert after_detail["result"] == before_result

        reconstructed_input = ResolvedFixationAdmissionInput(
            **after_detail["input_snapshot"]
        )
        reconstructed_result = FixationResult(**after_detail["result"])
        assert reconstructed_input.model_dump(mode="json") == after_detail["input_snapshot"]
        assert reconstructed_result.model_dump(mode="json") == after_detail["result"]
    finally:
        app.dependency_overrides.clear()


def test_phase10_latest_history_rules_and_strict_errors(tmp_path: Path) -> None:
    client, session_local = _build_client(
        tmp_path, db_name="phase10_latest_history_errors.db"
    )
    try:
        client_no_runs = _create_client(client, session_local, id_number="5001")
        latest_none_resp = client.get(f"/api/clients/{client_no_runs}/fixation/latest")
        assert latest_none_resp.status_code == 200
        assert latest_none_resp.json() == {"result": None}

        client_failed_only = _create_client(
            client, session_local, id_number="5002"
        )
        failed_only_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_failed_only,
                "input_data": _invalid_fixation_input("calc-only-fail", client_id=client_failed_only),
            },
        )
        assert failed_only_resp.status_code == 200
        latest_failed_only_resp = client.get(f"/api/clients/{client_failed_only}/fixation/latest")
        assert latest_failed_only_resp.status_code == 200
        assert latest_failed_only_resp.json() == {"result": None}

        client_mixed = _create_client(client, session_local, id_number="5003")
        success_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_mixed,
                "input_data": _fixation_input(calc_id="calc-mixed-success", client_id=client_mixed),
            },
        )
        failed_resp = client.post(
            "/api/fixation/save",
            json={
                "client_id": client_mixed,
                "input_data": _invalid_fixation_input("calc-mixed-failed", client_id=client_mixed),
            },
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

        missing_run_resp = client.get(f"/api/clients/{client_mixed}/fixation/runs/999999")
        assert missing_run_resp.status_code == 404
        assert missing_run_resp.json()["detail"]["code"] == "FIXATION_RUN_NOT_FOUND"

        invalid_payload = {"calculation_id": "bad"}
        invalid_validate_payload_resp = client.post(
            f"/api/clients/{client_mixed}/fixation/validate",
            json=invalid_payload,
        )
        invalid_calc_payload_resp = client.post(
            f"/api/clients/{client_mixed}/fixation/calculate",
            json=invalid_payload,
        )
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
        client_id = _create_client(client, session_local, id_number="6001")

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
            "internal_planner_judgments": 0,
        }
    finally:
        app.dependency_overrides.clear()
