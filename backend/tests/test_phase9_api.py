from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.actual_capitalization import ActualCapitalization
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.fixation_run import FixationRun

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


def _run_alembic(db_path: Path, *args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", *args],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _build_client(tmp_path: Path) -> tuple[TestClient, sessionmaker, Path]:
    db_path = tmp_path / "phase9_api.db"
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
    client = TestClient(app)
    return client, session_local, db_path


def _create_client(client: TestClient, *, id_number: str = "1001") -> dict:
    response = client.post(
        "/api/clients",
        json={
            "full_name": "Jane Doe",
            "id_number": id_number,
            "birth_date": "1970-01-01",
        },
    )
    assert response.status_code == 200
    return response.json()


def _fixation_input(*, calc_id: str, eligibility_year: int = 2025) -> dict:
    return {
        "calculation_id": calc_id,
        "calculation_version": "v1",
        "eligibility_date": f"{eligibility_year}-01-01",
        "eligibility_year": eligibility_year,
        "upstream_context": {"profile_id": "M07-1", "client_id": 1, "state": "qualified"},
        "parameter_set": {
            "parameter_set_id": f"PARAMS-{eligibility_year}",
            "client_id": 1,
            "tax_year": eligibility_year,
            "values": {
                "monthly_cap": 1000.0,
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
                "client_id": 1,
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


def test_phase9_api_end_to_end(tmp_path: Path) -> None:
    client, session_local, db_path = _build_client(tmp_path)
    try:
        empty_list_resp = client.get("/api/clients")
        assert empty_list_resp.status_code == 200
        assert empty_list_resp.json() == []

        missing_id_number_resp = client.post(
            "/api/clients",
            json={"full_name": "Missing ID"},
        )
        assert missing_id_number_resp.status_code == 422

        # 1. Client id_number roundtrip and no status overload
        created = _create_client(client, id_number="001234567")
        created_client_id = created["client_id"]
        assert isinstance(created_client_id, int)
        assert created["full_name"] == "Jane Doe"
        assert created["id_number"] == "001234567"

        second_created = _create_client(client, id_number="001234568")
        list_clients_resp = client.get("/api/clients")
        assert list_clients_resp.status_code == 200
        assert list_clients_resp.json() == [created, second_created]

        get_client_resp = client.get(f"/api/clients/{created_client_id}")
        assert get_client_resp.status_code == 200
        assert get_client_resp.json()["id_number"] == "001234567"

        with session_local() as db:
            persisted_client = db.get(Client, created_client_id)
            assert persisted_client is not None
            assert persisted_client.id_number == "001234567"
            assert persisted_client.status in (None, "active")
            assert persisted_client.status != "001234567"

        # 3. Missing client returns 404 CLIENT_NOT_FOUND
        missing_client_resp = client.get("/api/clients/9999")
        assert missing_client_resp.status_code == 404
        assert missing_client_resp.json()["detail"]["code"] == "CLIENT_NOT_FOUND"

        # 4. Create/update profile
        put_profile_resp = client.put(
            f"/api/clients/{created_client_id}/profile",
            json={"birth_date": "1971-02-02", "gender": "f", "notes": "updated"},
        )
        assert put_profile_resp.status_code == 200
        assert put_profile_resp.json()["profile"]["birth_date"] == "1971-02-02"
        assert put_profile_resp.json()["profile"]["id_number"] == "001234567"

        with session_local() as db:
            persisted_client = db.get(Client, created_client_id)
            persisted_profile = db.scalar(
                select(ClientProfile).where(ClientProfile.client_id == created_client_id)
            )
            assert persisted_client is not None
            assert persisted_client.birth_date.isoformat() == "1971-02-02"
            assert persisted_profile is not None
            assert persisted_profile.birth_date is None

        unchanged_birth_date_resp = client.put(
            f"/api/clients/{created_client_id}/profile",
            json={"gender": "f", "notes": "kept birth date"},
        )
        assert unchanged_birth_date_resp.status_code == 200
        assert unchanged_birth_date_resp.json()["profile"]["birth_date"] == "1971-02-02"

        clear_birth_date_resp = client.put(
            f"/api/clients/{created_client_id}/profile",
            json={"birth_date": None, "gender": "f", "notes": "cleared birth date"},
        )
        assert clear_birth_date_resp.status_code == 200
        assert clear_birth_date_resp.json()["profile"]["birth_date"] is None

        with session_local() as db:
            persisted_client = db.get(Client, created_client_id)
            persisted_profile = db.scalar(
                select(ClientProfile).where(ClientProfile.client_id == created_client_id)
            )
            assert persisted_client is not None
            assert persisted_client.birth_date is None
            assert persisted_profile is not None
            assert persisted_profile.birth_date is None

        # 5. Get profile
        get_profile_resp = client.get(f"/api/clients/{created_client_id}/profile")
        assert get_profile_resp.status_code == 200
        assert get_profile_resp.json()["profile"]["gender"] == "f"
        assert get_profile_resp.json()["profile"]["birth_date"] is None

        # 6. Create/list employment records
        create_employment_resp = client.post(
            f"/api/clients/{created_client_id}/employment-records",
            json={
                "employer_name": "Employer Inc",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "is_current": False,
                "notes": "employment",
            },
        )
        assert create_employment_resp.status_code == 200
        list_employment_resp = client.get(f"/api/clients/{created_client_id}/employment-records")
        assert list_employment_resp.status_code == 200
        assert len(list_employment_resp.json()) == 1
        update_employment_resp = client.put(
            f"/api/clients/{created_client_id}/employment-records/{create_employment_resp.json()['employment_record_id']}",
            json={
                "employer_name": "Updated Employer Inc",
                "work_start_date": "2011-01-01",
                "work_end_date": None,
                "is_current": True,
                "notes": "updated employment",
            },
        )
        assert update_employment_resp.status_code == 200
        assert update_employment_resp.json()["employer_name"] == "Updated Employer Inc"
        assert update_employment_resp.json()["is_current"] is True

        # 7. Create/list grants
        employment_id = create_employment_resp.json()["employment_record_id"]
        create_grant_resp = client.post(
            f"/api/clients/{created_client_id}/grants",
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
        assert create_grant_resp.status_code == 200
        list_grants_resp = client.get(f"/api/clients/{created_client_id}/grants")
        assert list_grants_resp.status_code == 200
        assert len(list_grants_resp.json()) == 1
        update_grant_resp = client.put(
            f"/api/clients/{created_client_id}/grants/{create_grant_resp.json()['grant_id']}",
            json={
                "employment_record_id": employment_id,
                "employer_name": "Updated Employer Inc",
                "nominal_amount": 11000.0,
                "indexed_amount": 12000.0,
                "grant_date": "2021-01-01",
                "work_start_date": "2011-01-01",
                "work_end_date": "2021-01-01",
                "notes": "updated grant",
            },
        )
        assert update_grant_resp.status_code == 200
        assert update_grant_resp.json()["indexed_amount"] == "12000.00"
        blank_grant_numeric_resp = client.post(
            f"/api/clients/{created_client_id}/grants",
            json={
                "employment_record_id": employment_id,
                "indexed_amount": "",
                "grant_date": "2021-01-01",
                "work_start_date": "2011-01-01",
                "work_end_date": "2021-01-01",
            },
        )
        assert blank_grant_numeric_resp.status_code == 422
        negative_grant_numeric_resp = client.post(
            f"/api/clients/{created_client_id}/grants",
            json={
                "employment_record_id": employment_id,
                "indexed_amount": -1,
                "grant_date": "2021-01-01",
                "work_start_date": "2011-01-01",
                "work_end_date": "2021-01-01",
            },
        )
        assert negative_grant_numeric_resp.status_code == 422

        # 8. Create/list actual capitalizations
        create_cap_resp = client.post(
            f"/api/clients/{created_client_id}/actual-capitalizations",
            json={
                "amount": 500.0,
                "capitalization_date": "2023-01-01",
                "source_label": "manual",
                "notes": "cap",
            },
        )
        assert create_cap_resp.status_code == 200
        assert create_cap_resp.json()["source_basis"] is None
        list_cap_resp = client.get(f"/api/clients/{created_client_id}/actual-capitalizations")
        assert list_cap_resp.status_code == 200
        assert len(list_cap_resp.json()) == 1
        assert list_cap_resp.json()[0]["source_basis"] is None
        assertion_without_basis_resp = client.post(
            f"/api/clients/{created_client_id}/actual-capitalizations",
            json={
                "amount": 100.0,
                "capitalization_date": "2023-02-01",
                "planner_assertion": "advisor confirmed taxable event",
            },
        )
        assert assertion_without_basis_resp.status_code == 422
        blank_cap_numeric_resp = client.post(
            f"/api/clients/{created_client_id}/actual-capitalizations",
            json={
                "amount": "",
                "capitalization_date": "2023-02-01",
            },
        )
        assert blank_cap_numeric_resp.status_code == 422
        negative_cap_numeric_resp = client.post(
            f"/api/clients/{created_client_id}/actual-capitalizations",
            json={
                "amount": -1,
                "capitalization_date": "2023-02-01",
            },
        )
        assert negative_cap_numeric_resp.status_code == 422
        update_cap_resp = client.put(
            f"/api/clients/{created_client_id}/actual-capitalizations/{create_cap_resp.json()['capitalization_id']}",
            json={
                "amount": 750.0,
                "capitalization_date": "2024-01-01",
                "source_label": "updated manual",
                "source_basis": "advisor source document",
                "planner_assertion": "advisor confirmed amount",
                "planner_assertion_basis": "reviewed capitalization certificate",
                "notes": "updated cap",
            },
        )
        assert update_cap_resp.status_code == 200
        assert update_cap_resp.json()["amount"] == "750.00"
        assert update_cap_resp.json()["source_basis"] == "advisor source document"
        assert update_cap_resp.json()["planner_assertion"] == "advisor confirmed amount"
        assert update_cap_resp.json()["planner_assertion_basis"] == "reviewed capitalization certificate"

        with session_local() as db:
            persisted_cap = db.get(ActualCapitalization, create_cap_resp.json()["capitalization_id"])
            assert persisted_cap is not None
            assert str(persisted_cap.amount) == "750.00"
            assert persisted_cap.source_basis == "advisor source document"

        # 8a. Create/retrieve clearinghouse snapshots and preserve snapshot history
        first_snapshot_resp = client.post(
            f"/api/clients/{created_client_id}/clearinghouse-snapshots",
            json={
                "import_date": "2026-06-01",
                "source_type": "clearinghouse",
                "source_file": "first-clearinghouse.csv",
                "collection_status": "collected",
                "collection_notes": "first import",
            },
        )
        assert first_snapshot_resp.status_code == 200
        second_snapshot_resp = client.post(
            f"/api/clients/{created_client_id}/clearinghouse-snapshots",
            json={
                "import_date": "2026-06-15",
                "source_type": "clearinghouse",
                "source_file": "second-clearinghouse.csv",
                "collection_status": "collected",
                "collection_notes": "second import",
            },
        )
        assert second_snapshot_resp.status_code == 200
        list_snapshots_resp = client.get(f"/api/clients/{created_client_id}/clearinghouse-snapshots")
        assert list_snapshots_resp.status_code == 200
        assert len(list_snapshots_resp.json()) == 2
        get_snapshot_resp = client.get(
            f"/api/clients/{created_client_id}/clearinghouse-snapshots/"
            f"{first_snapshot_resp.json()['clearinghouse_snapshot_id']}"
        )
        assert get_snapshot_resp.status_code == 200
        assert get_snapshot_resp.json()["source_file"] == "first-clearinghouse.csv"
        assert get_snapshot_resp.json()["verification_status"] == "unverified"
        snapshot_verification_resp = client.put(
            f"/api/clients/{created_client_id}/clearinghouse-snapshots/"
            f"{first_snapshot_resp.json()['clearinghouse_snapshot_id']}/verification",
            json={"verification_status": "verified", "verification_notes": "advisor checked source"},
        )
        assert snapshot_verification_resp.status_code == 200
        assert snapshot_verification_resp.json()["verification_status"] == "verified"
        assert snapshot_verification_resp.json()["verification_notes"] == "advisor checked source"
        assert snapshot_verification_resp.json()["source_file"] == "first-clearinghouse.csv"
        assert snapshot_verification_resp.json()["collection_status"] == "collected"

        # 8b. Register/retrieve retirement planning documents and preserve document history
        first_document_resp = client.post(
            f"/api/clients/{created_client_id}/documents",
            json={
                "document_type": "161",
                "source_type": "document",
                "source_file": "first-161.pdf",
                "collection_date": "2026-06-02",
                "collection_status": "collected",
                "collection_notes": "first document",
            },
        )
        assert first_document_resp.status_code == 200
        second_document_resp = client.post(
            f"/api/clients/{created_client_id}/documents",
            json={
                "document_type": "employment summary",
                "source_type": "document",
                "source_file": "employment-summary.pdf",
                "collection_date": "2026-06-16",
                "collection_status": "collected",
                "collection_notes": "second document",
            },
        )
        assert second_document_resp.status_code == 200
        list_documents_resp = client.get(f"/api/clients/{created_client_id}/documents")
        assert list_documents_resp.status_code == 200
        assert len(list_documents_resp.json()) == 2
        get_document_resp = client.get(
            f"/api/clients/{created_client_id}/documents/{first_document_resp.json()['document_id']}"
        )
        assert get_document_resp.status_code == 200
        assert get_document_resp.json()["source_file"] == "first-161.pdf"
        assert get_document_resp.json()["verification_status"] == "unverified"
        document_verification_resp = client.put(
            f"/api/clients/{created_client_id}/documents/{first_document_resp.json()['document_id']}/verification",
            json={"verification_status": "requires_review", "verification_notes": "missing advisor review"},
        )
        assert document_verification_resp.status_code == 200
        assert document_verification_resp.json()["verification_status"] == "requires_review"
        assert document_verification_resp.json()["verification_notes"] == "missing advisor review"
        assert document_verification_resp.json()["source_file"] == "first-161.pdf"
        assert document_verification_resp.json()["collection_status"] == "collected"

        # 8c. Register/retrieve missing required data and missing document requirements
        missing_data_resp = client.post(
            f"/api/clients/{created_client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Tax credits",
                "missing_status": "missing",
                "notes": "advisor needs interview completion",
            },
        )
        assert missing_data_resp.status_code == 200
        missing_document_resp = client.post(
            f"/api/clients/{created_client_id}/missing-items",
            json={
                "missing_item_type": "document",
                "missing_item_label": "Form 161",
                "missing_status": "requested",
                "notes": "client to provide document",
            },
        )
        assert missing_document_resp.status_code == 200
        list_missing_resp = client.get(f"/api/clients/{created_client_id}/missing-items")
        assert list_missing_resp.status_code == 200
        assert len(list_missing_resp.json()) == 2
        assert {item["missing_item_type"] for item in list_missing_resp.json()} == {"data", "document"}

        other_created = _create_client(client, id_number="3003")
        other_client_id = other_created["client_id"]
        wrong_client_employment_resp = client.put(
            f"/api/clients/{other_client_id}/employment-records/{employment_id}",
            json={
                "employer_name": "Wrong Client",
                "work_start_date": "2011-01-01",
                "work_end_date": None,
                "is_current": True,
                "notes": None,
            },
        )
        assert wrong_client_employment_resp.status_code == 404
        assert wrong_client_employment_resp.json()["detail"]["code"] == "EMPLOYMENT_RECORD_NOT_FOUND"
        wrong_client_grant_resp = client.delete(
            f"/api/clients/{other_client_id}/grants/{create_grant_resp.json()['grant_id']}"
        )
        assert wrong_client_grant_resp.status_code == 404
        assert wrong_client_grant_resp.json()["detail"]["code"] == "GRANT_NOT_FOUND"
        wrong_client_cap_resp = client.delete(
            f"/api/clients/{other_client_id}/actual-capitalizations/{create_cap_resp.json()['capitalization_id']}"
        )
        assert wrong_client_cap_resp.status_code == 404
        assert wrong_client_cap_resp.json()["detail"]["code"] == "ACTUAL_CAPITALIZATION_NOT_FOUND"

        delete_cap_resp = client.delete(
            f"/api/clients/{created_client_id}/actual-capitalizations/{create_cap_resp.json()['capitalization_id']}"
        )
        assert delete_cap_resp.status_code == 200
        assert client.get(f"/api/clients/{created_client_id}/actual-capitalizations").json() == []
        delete_grant_resp = client.delete(f"/api/clients/{created_client_id}/grants/{create_grant_resp.json()['grant_id']}")
        assert delete_grant_resp.status_code == 200
        assert client.get(f"/api/clients/{created_client_id}/grants").json() == []
        delete_employment_resp = client.delete(f"/api/clients/{created_client_id}/employment-records/{employment_id}")
        assert delete_employment_resp.status_code == 200
        assert client.get(f"/api/clients/{created_client_id}/employment-records").json() == []

        # 9. Validate fixation without persistence
        input_payload = _fixation_input(calc_id="calc-validate")
        validate_resp = client.post(
            f"/api/clients/{created_client_id}/fixation/validate",
            json=input_payload,
        )
        assert validate_resp.status_code == 200

        with session_local() as db:
            run_count_after_validate = db.scalar(select(func.count()).select_from(FixationRun))
            assert run_count_after_validate == 0

        # 10. Calculate fixation without persistence
        calculate_resp = client.post(
            f"/api/clients/{created_client_id}/fixation/calculate",
            json=input_payload,
        )
        assert calculate_resp.status_code == 200

        with session_local() as db:
            run_count_after_calculate = db.scalar(select(func.count()).select_from(FixationRun))
            assert run_count_after_calculate == 0

        # 11. Validate and calculate return same result for same input
        assert validate_resp.json() == calculate_resp.json()

        # 12. Save fixation success
        save_success_resp = client.post(
            "/api/fixation/save",
            json={"client_id": created_client_id, "input_data": _fixation_input(calc_id="calc-save-success")},
        )
        assert save_success_resp.status_code == 200
        assert save_success_resp.json()["status"] == "success"
        success_run_id = save_success_resp.json()["run_id"]
        assert isinstance(success_run_id, int)
        with session_local() as db:
            persisted_run = db.get(FixationRun, success_run_id)
            assert persisted_run is not None
            assert persisted_run.id == success_run_id

        # 13. Save fixation validation_failed
        invalid_input = _fixation_input(calc_id="calc-save-failed", eligibility_year=2026)
        invalid_input["eligibility_date"] = "2025-01-01"
        save_failed_resp = client.post(
            "/api/fixation/save",
            json={"client_id": created_client_id, "input_data": invalid_input},
        )
        assert save_failed_resp.status_code == 200
        assert save_failed_resp.json()["status"] == "validation_failed"
        failed_run_id = save_failed_resp.json()["run_id"]

        # 14. Latest result returns {"result": FixationResult}
        latest_resp = client.get(f"/api/clients/{created_client_id}/fixation/latest")
        assert latest_resp.status_code == 200
        assert latest_resp.json()["result"] is not None
        assert latest_resp.json()["result"]["status"] == "success"

        # 15. Latest result returns {"result": null} for existing client with no success
        _create_client(client, id_number="2002")
        latest_null_resp = client.get("/api/clients/2/fixation/latest")
        assert latest_null_resp.status_code == 200
        assert latest_null_resp.json() == {"result": None}

        # 16. History returns all runs newest first
        history_resp = client.get(f"/api/clients/{created_client_id}/fixation/history")
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert len(history) == 2
        assert history[0]["run_id"] == failed_run_id
        assert history[1]["run_id"] == success_run_id

        # 17. Run detail returns snapshot/result/audit or validation errors
        success_detail_resp = client.get(
            f"/api/clients/{created_client_id}/fixation/runs/{success_run_id}"
        )
        assert success_detail_resp.status_code == 200
        success_detail = success_detail_resp.json()
        assert success_detail["input_snapshot"] is not None
        assert success_detail["result"] is not None
        assert len(success_detail["audit_rows"]) > 0
        assert len(success_detail["validation_errors"]) == 0

        failed_detail_resp = client.get(
            f"/api/clients/{created_client_id}/fixation/runs/{failed_run_id}"
        )
        assert failed_detail_resp.status_code == 200
        failed_detail = failed_detail_resp.json()
        assert failed_detail["input_snapshot"] is not None
        assert failed_detail["result"] is None
        assert len(failed_detail["validation_errors"]) > 0

        assert success_detail["run"]["run_id"] == success_run_id
        assert failed_detail["run"]["run_id"] == failed_run_id

        # 18. Missing run returns 404 FIXATION_RUN_NOT_FOUND
        missing_run_resp = client.get(
            f"/api/clients/{created_client_id}/fixation/runs/999999999"
        )
        assert missing_run_resp.status_code == 404
        assert missing_run_resp.json()["detail"]["code"] == "FIXATION_RUN_NOT_FOUND"

        # 19. Verify API routes do not calculate formulas
        routes_dir = _backend_root() / "app" / "api"
        clients_routes_src = (routes_dir / "clients_routes.py").read_text(encoding="utf-8")
        fixation_routes_src = (routes_dir / "fixation_routes.py").read_text(encoding="utf-8")
        forbidden_markers = [
            "GRANT_IMPACT_MULTIPLIER",
            "IDF_MONTHLY_CAP_FACTOR",
            "monthly_cap *",
            "capital_multiplier *",
            "future_grant_reserved *",
            ".like(",
            "_external_run_id",
        ]
        for marker in forbidden_markers:
            assert marker not in clients_routes_src
            assert marker not in fixation_routes_src

        # 20. Verify only approved DB schema/migration files are present.
        migration_files = sorted(((_backend_root() / "alembic" / "versions").glob("*.py")))
        migration_names = [path.name for path in migration_files]
        assert "a2f36c3147d2_phase_1_fixation_schema.py" in migration_names
        assert "eb25e18b9fcd_align_phase_1_ids_for_api.py" in migration_names
        assert "6f2e9b2b4a11_stage_b_additive_id_columns.py" in migration_names
        assert "9a6f3b8c21de_stage_c_cutover_integer_ids.py" in migration_names
        assert "4e7a1c2d9b30_package_2_collection_foundation.py" in migration_names
        assert "5b8d2e1f4c61_package_3_verification_missing_data.py" in migration_names
        assert "7c1d9e4a2b83_slice_1_actual_capitalization_metadata.py" in migration_names
        tables = set(inspect(create_engine(f"sqlite:///{db_path.as_posix()}")) .get_table_names())
        assert tables == APPROVED_TABLES | ACCEPTED_ADDITIVE_TABLES | {"alembic_version"}

    finally:
        app.dependency_overrides.clear()


def test_slice_1_actual_capitalization_metadata_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "slice1_actual_capitalization_metadata.db"
    _run_alembic(db_path, "upgrade", "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    actual_cap_columns = {column["name"] for column in inspector.get_columns("actual_capitalizations")}
    assert {"source_basis", "planner_assertion", "planner_assertion_basis"}.issubset(actual_cap_columns)
    assert "source_basis" not in {column["name"] for column in inspector.get_columns("clients")}

    _run_alembic(db_path, "downgrade", "5b8d2e1f4c61")
    downgraded_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    downgraded_inspector = inspect(downgraded_engine)
    downgraded_actual_cap_columns = {
        column["name"] for column in downgraded_inspector.get_columns("actual_capitalizations")
    }
    assert "source_basis" not in downgraded_actual_cap_columns
    assert "planner_assertion" not in downgraded_actual_cap_columns
    assert "planner_assertion_basis" not in downgraded_actual_cap_columns
