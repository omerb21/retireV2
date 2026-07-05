from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.pension_analysis_record import PensionAnalysisRecord
from app.models.retirement_facts import PensionHolding


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


def _build_client(tmp_path: Path) -> tuple[TestClient, sessionmaker]:
    db_path = tmp_path / "v22_slice1_analysis_record.db"
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
    return TestClient(app), session_local


def _create_client(client: TestClient, *, id_number: str) -> int:
    response = client.post(
        "/api/clients",
        json={
            "full_name": f"Client {id_number}",
            "id_number": id_number,
            "birth_date": "1970-01-01",
        },
    )
    assert response.status_code == 200
    return int(response.json()["client_id"])


def _create_pension_holding(client: TestClient, client_id: int) -> dict:
    response = client.post(
        f"/api/clients/{client_id}/pension-holdings",
        json={
            "provider_name": "Existing Pension Provider",
            "product_type": "pension fund",
            "known_balance_amount": "1000.00",
            "balance_as_of_date": "2026-01-01",
            "known_monthly_pension_amount": "200.00",
            "pension_amount_as_of_date": "2026-01-02",
            "source_type": "statement",
            "source_date": "2026-01-03",
            "source_note": "Source context remains on the holding",
        },
    )
    assert response.status_code == 200
    return response.json()


def _analysis_record_path(client_id: int, pension_holding_id: int) -> str:
    return f"/api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record"


def test_analysis_record_create_read_update_and_preserves_holding_context(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="S1-1001")
        holding = _create_pension_holding(client, client_id)
        holding_id = holding["id"]

        empty_read = client.get(_analysis_record_path(client_id, holding_id))
        assert empty_read.status_code == 200
        assert empty_read.json() is None

        create_resp = client.post(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "Internal analysis record text"},
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["client_id"] == client_id
        assert created["pension_holding_id"] == holding_id
        assert created["analysis_record_text"] == "Internal analysis record text"
        assert "lifecycle_status" not in created
        assert "source_status" not in created
        assert "verification_state" not in created

        read_resp = client.get(_analysis_record_path(client_id, holding_id))
        assert read_resp.status_code == 200
        assert read_resp.json()["id"] == created["id"]

        update_resp = client.put(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "Updated internal analysis record text"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["analysis_record_text"] == "Updated internal analysis record text"

        holding_resp = client.get(f"/api/clients/{client_id}/pension-holdings/{holding_id}")
        assert holding_resp.status_code == 200
        preserved = holding_resp.json()
        assert preserved["provider_name"] == holding["provider_name"]
        assert preserved["product_type"] == holding["product_type"]
        assert preserved["known_balance_amount"] == holding["known_balance_amount"]
        assert preserved["balance_as_of_date"] == holding["balance_as_of_date"]
        assert preserved["known_monthly_pension_amount"] == holding["known_monthly_pension_amount"]
        assert preserved["pension_amount_as_of_date"] == holding["pension_amount_as_of_date"]
        assert preserved["source_type"] == holding["source_type"]
        assert preserved["source_date"] == holding["source_date"]
        assert preserved["source_note"] == holding["source_note"]
        assert preserved["source_status"] == holding["source_status"]
        assert preserved["verification_state"] == holding["verification_state"]

        with session_local() as db:
            stored_holding = db.get(PensionHolding, holding_id)
            assert stored_holding is not None
            assert stored_holding.provider_name == "Existing Pension Provider"
            assert db.scalars(select(PensionAnalysisRecord)).all()[0].pension_holding_id == holding_id
    finally:
        app.dependency_overrides.clear()


def test_analysis_record_one_current_record_only_per_holding(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="S1-1002")
        holding = _create_pension_holding(client, client_id)
        holding_id = holding["id"]

        first_resp = client.post(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "First analysis record text"},
        )
        assert first_resp.status_code == 200

        duplicate_resp = client.post(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "Second analysis record text"},
        )
        assert duplicate_resp.status_code == 409
        assert duplicate_resp.json()["detail"]["code"] == "PENSION_ANALYSIS_RECORD_EXISTS"

        with session_local() as db:
            rows = db.scalars(select(PensionAnalysisRecord)).all()
            assert len(rows) == 1
            assert rows[0].analysis_record_text == "First analysis record text"
    finally:
        app.dependency_overrides.clear()


def test_analysis_record_client_scoped_ownership(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        first_client_id = _create_client(client, id_number="S1-1003-A")
        second_client_id = _create_client(client, id_number="S1-1003-B")
        holding = _create_pension_holding(client, first_client_id)
        holding_id = holding["id"]
        create_resp = client.post(
            _analysis_record_path(first_client_id, holding_id),
            json={"analysis_record_text": "Owned analysis record text"},
        )
        assert create_resp.status_code == 200

        wrong_read = client.get(_analysis_record_path(second_client_id, holding_id))
        assert wrong_read.status_code == 404
        assert wrong_read.json()["detail"]["code"] == "PENSION_HOLDING_NOT_FOUND"

        wrong_create = client.post(
            _analysis_record_path(second_client_id, holding_id),
            json={"analysis_record_text": "Wrong client analysis record text"},
        )
        assert wrong_create.status_code == 404
        assert wrong_create.json()["detail"]["code"] == "PENSION_HOLDING_NOT_FOUND"

        wrong_update = client.put(
            _analysis_record_path(second_client_id, holding_id),
            json={"analysis_record_text": "Wrong client update"},
        )
        assert wrong_update.status_code == 404
        assert wrong_update.json()["detail"]["code"] == "PENSION_HOLDING_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_analysis_record_contract_rejects_prohibited_fields_and_routes(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="S1-1004")
        holding = _create_pension_holding(client, client_id)
        holding_id = holding["id"]

        for field_name in [
            "lifecycle_status",
            "source_status",
            "verification_state",
            "classification",
            "recommendation",
            "readiness_status",
            "workflow_status",
        ]:
            response = client.post(
                _analysis_record_path(client_id, holding_id),
                json={"analysis_record_text": "Analysis text", field_name: "not allowed"},
            )
            assert response.status_code == 422

        blank_resp = client.post(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "   "},
        )
        assert blank_resp.status_code == 422

        created = client.post(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "Allowed analysis text"},
        )
        assert created.status_code == 200

        update_reject = client.put(
            _analysis_record_path(client_id, holding_id),
            json={"analysis_record_text": "Allowed update", "source_status": "not allowed"},
        )
        assert update_reject.status_code == 422

        missing_record_update = client.put(
            _analysis_record_path(client_id, holding_id + 1000),
            json={"analysis_record_text": "Missing record update"},
        )
        assert missing_record_update.status_code == 404

        delete_resp = client.delete(_analysis_record_path(client_id, holding_id))
        assert delete_resp.status_code == 405

        supersede_resp = client.post(f"{_analysis_record_path(client_id, holding_id)}/supersede")
        assert supersede_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
