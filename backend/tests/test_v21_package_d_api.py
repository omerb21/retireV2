from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.missing_data_item import MissingDataItem
from app.models.retirement_facts import PlannerAssumption


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
    db_path = tmp_path / "v21_package_d_api.db"
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


def _planner_assumption_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "assumption_category": "income",
        "title": "Income assumption",
        "assumption_value_text": "Income continues",
        "rationale": "Planner entered planning assumption",
        "owner": "planner",
        "effective_start_date": "2026-01-01",
        "effective_end_date": None,
        "review_date": "2026-06-01",
    }
    payload.update(overrides)
    return payload


def _create_planner_assumption(client: TestClient, client_id: int, **overrides: object) -> dict[str, object]:
    response = client.post(
        f"/api/clients/{client_id}/planner-assumptions",
        json=_planner_assumption_payload(**overrides),
    )
    assert response.status_code == 200
    return response.json()


def test_planner_assumption_create_list_read_one_and_partial_update(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
      client_id = _create_client(client, id_number="D-1001")
      created = _create_planner_assumption(client, client_id)
      row_id = created["id"]

      assert created["client_id"] == client_id
      assert created["lifecycle_status"] == "current"
      assert created["assumption_category"] == "income"
      assert "source_status" not in created
      assert "verification_state" not in created

      list_resp = client.get(f"/api/clients/{client_id}/planner-assumptions")
      assert list_resp.status_code == 200
      assert [item["id"] for item in list_resp.json()] == [row_id]

      read_resp = client.get(f"/api/clients/{client_id}/planner-assumptions/{row_id}")
      assert read_resp.status_code == 200
      assert read_resp.json()["title"] == "Income assumption"

      update_resp = client.put(
          f"/api/clients/{client_id}/planner-assumptions/{row_id}",
          json={"title": "Updated assumption", "review_date": None},
      )
      assert update_resp.status_code == 200
      assert update_resp.json()["title"] == "Updated assumption"
      assert update_resp.json()["review_date"] is None
      assert update_resp.json()["assumption_value_text"] == "Income continues"
    finally:
      app.dependency_overrides.clear()


def test_planner_assumption_lifecycle_filters_and_invalid_filter(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-1002")
        current = _create_planner_assumption(client, client_id, title="Current")
        superseded = _create_planner_assumption(client, client_id, title="Superseded")

        with session_local() as db:
            row = db.get(PlannerAssumption, superseded["id"])
            assert row is not None
            row.lifecycle_status = "superseded"
            db.commit()

        default_resp = client.get(f"/api/clients/{client_id}/planner-assumptions")
        assert default_resp.status_code == 200
        assert [row["id"] for row in default_resp.json()] == [current["id"]]

        current_resp = client.get(
            f"/api/clients/{client_id}/planner-assumptions",
            params={"lifecycle_status": "current"},
        )
        assert current_resp.status_code == 200
        assert [row["id"] for row in current_resp.json()] == [current["id"]]

        superseded_resp = client.get(
            f"/api/clients/{client_id}/planner-assumptions",
            params={"lifecycle_status": "superseded"},
        )
        assert superseded_resp.status_code == 200
        assert [row["id"] for row in superseded_resp.json()] == [superseded["id"]]

        all_resp = client.get(
            f"/api/clients/{client_id}/planner-assumptions",
            params={"lifecycle_status": "all"},
        )
        assert all_resp.status_code == 200
        assert {row["id"] for row in all_resp.json()} == {current["id"], superseded["id"]}

        invalid_resp = client.get(
            f"/api/clients/{client_id}/planner-assumptions",
            params={"lifecycle_status": "archived"},
        )
        assert invalid_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_planner_assumption_rejects_lifecycle_source_and_verification_fields(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-1003")
        create_resp = client.post(
            f"/api/clients/{client_id}/planner-assumptions",
            json=_planner_assumption_payload(lifecycle_status="superseded"),
        )
        assert create_resp.status_code == 422

        for source_field, value in [
            ("source_status", "reviewed"),
            ("source_type", "statement"),
            ("source_label", "Statement"),
        ]:
            source_resp = client.post(
                f"/api/clients/{client_id}/planner-assumptions",
                json=_planner_assumption_payload(**{source_field: value}),
            )
            assert source_resp.status_code == 422

        verification_resp = client.post(
            f"/api/clients/{client_id}/planner-assumptions",
            json=_planner_assumption_payload(verification_state="verified"),
        )
        assert verification_resp.status_code == 422

        created = _create_planner_assumption(client, client_id)
        update_lifecycle_resp = client.put(
            f"/api/clients/{client_id}/planner-assumptions/{created['id']}",
            json={"lifecycle_status": "superseded"},
        )
        assert update_lifecycle_resp.status_code == 422

        update_source_resp = client.put(
            f"/api/clients/{client_id}/planner-assumptions/{created['id']}",
            json={"source_type": "statement"},
        )
        assert update_source_resp.status_code == 422

        update_verification_resp = client.put(
            f"/api/clients/{client_id}/planner-assumptions/{created['id']}",
            json={"verification_state": "verified"},
        )
        assert update_verification_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_planner_assumption_rejects_invalid_category_and_owner(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-1003-B")
        invalid_category_resp = client.post(
            f"/api/clients/{client_id}/planner-assumptions",
            json=_planner_assumption_payload(assumption_category="cashflow"),
        )
        assert invalid_category_resp.status_code == 422

        invalid_owner_resp = client.post(
            f"/api/clients/{client_id}/planner-assumptions",
            json=_planner_assumption_payload(owner="client"),
        )
        assert invalid_owner_resp.status_code == 422

        created = _create_planner_assumption(client, client_id)
        invalid_category_update_resp = client.put(
            f"/api/clients/{client_id}/planner-assumptions/{created['id']}",
            json={"assumption_category": "cashflow"},
        )
        assert invalid_category_update_resp.status_code == 422

        invalid_owner_update_resp = client.put(
            f"/api/clients/{client_id}/planner-assumptions/{created['id']}",
            json={"owner": "client"},
        )
        assert invalid_owner_update_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_planner_assumption_wrong_client_not_found_and_no_delete_or_supersede(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        first_client_id = _create_client(client, id_number="D-1004-A")
        second_client_id = _create_client(client, id_number="D-1004-B")
        created = _create_planner_assumption(client, first_client_id)

        wrong_read = client.get(f"/api/clients/{second_client_id}/planner-assumptions/{created['id']}")
        assert wrong_read.status_code == 404
        assert wrong_read.json()["detail"]["code"] == "PLANNER_ASSUMPTION_NOT_FOUND"

        wrong_update = client.put(
            f"/api/clients/{second_client_id}/planner-assumptions/{created['id']}",
            json={"title": "Wrong client"},
        )
        assert wrong_update.status_code == 404
        assert wrong_update.json()["detail"]["code"] == "PLANNER_ASSUMPTION_NOT_FOUND"

        delete_resp = client.delete(f"/api/clients/{first_client_id}/planner-assumptions/{created['id']}")
        assert delete_resp.status_code == 405

        supersede_resp = client.post(
            f"/api/clients/{first_client_id}/planner-assumptions/{created['id']}/supersede"
        )
        assert supersede_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_missing_data_legacy_create_and_read_remain_unchanged(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-2001")
        create_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Legacy item",
                "missing_status": "missing",
            },
        )
        assert create_resp.status_code == 200
        payload = create_resp.json()
        assert payload["planning_domain"] is None
        assert payload["related_record_type"] is None
        assert payload["related_record_id"] is None
        assert payload["advisory_status"] is None
        assert payload["neutral_reason"] is None

        with session_local() as db:
            db.add(
                MissingDataItem(
                    missing_data_item_id="MD-LEGACY-D",
                    client_id=client_id,
                    missing_item_type="data",
                    missing_item_label="Stored legacy item",
                    missing_status="missing",
                    notes=None,
                )
            )
            db.commit()

        list_resp = client.get(f"/api/clients/{client_id}/missing-items")
        assert list_resp.status_code == 200
        stored_legacy = next(item for item in list_resp.json() if item["missing_data_item_id"] == "MD-LEGACY-D")
        assert stored_legacy["missing_status"] == "missing"
        assert stored_legacy["planning_domain"] is None
        assert stored_legacy["related_record_type"] is None
        assert stored_legacy["related_record_id"] is None
        assert stored_legacy["advisory_status"] is None
        assert stored_legacy["neutral_reason"] is None

        with session_local() as db:
            stored_row = db.get(MissingDataItem, "MD-LEGACY-D")
            assert stored_row is not None
            assert stored_row.missing_status == "missing"
            assert stored_row.planning_domain is None
            assert stored_row.related_record_type is None
            assert stored_row.related_record_id is None
            assert stored_row.advisory_status is None
            assert stored_row.neutral_reason is None
    finally:
        app.dependency_overrides.clear()


def test_missing_data_v21_create_rules_remain_binding(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-2002")
        missing_domain = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Missing domain",
                "missing_status": "missing",
                "advisory_status": "open",
            },
        )
        assert missing_domain.status_code == 422
        assert missing_domain.json()["detail"]["code"] == "PLANNING_DOMAIN_REQUIRED"

        missing_advisory = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Missing advisory",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
            },
        )
        assert missing_advisory.status_code == 422
        assert missing_advisory.json()["detail"]["code"] == "ADVISORY_STATUS_REQUIRED"

        invalid_advisory = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Invalid advisory",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
                "advisory_status": "resolved",
            },
        )
        assert invalid_advisory.status_code == 422
        assert invalid_advisory.json()["detail"]["code"] == "ADVISORY_STATUS_INVALID"
    finally:
        app.dependency_overrides.clear()


def test_missing_data_partial_update_approved_fields_statuses_and_null_linkage(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="D-2003")
        create_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "V2.1 item",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
                "advisory_status": "open",
                "related_record_type": None,
                "related_record_id": None,
                "neutral_reason": None,
            },
        )
        assert create_resp.status_code == 200
        item_id = create_resp.json()["missing_data_item_id"]

        for status in ["open", "resolved", "no longer relevant"]:
            update_resp = client.put(
                f"/api/clients/{client_id}/missing-items/{item_id}",
                json={
                    "planning_domain": "planner assumptions",
                    "advisory_status": status,
                    "related_record_type": None,
                    "related_record_id": None,
                    "neutral_reason": "Updated neutral reason",
                },
            )
            assert update_resp.status_code == 200
            assert update_resp.json()["advisory_status"] == status
            assert update_resp.json()["related_record_type"] is None
            assert update_resp.json()["related_record_id"] is None

        for prohibited_field, value in [
            ("missing_status", "resolved"),
            ("missing_item_label", "Rewritten label"),
            ("notes", "Rewritten notes"),
        ]:
            approved_only_resp = client.put(
                f"/api/clients/{client_id}/missing-items/{item_id}",
                json={prohibited_field: value},
            )
            assert approved_only_resp.status_code == 422

        invalid_status_resp = client.put(
            f"/api/clients/{client_id}/missing-items/{item_id}",
            json={"advisory_status": "blocked"},
        )
        assert invalid_status_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_missing_data_wrong_client_update_not_found_and_no_delete(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        first_client_id = _create_client(client, id_number="D-2004-A")
        second_client_id = _create_client(client, id_number="D-2004-B")
        create_resp = client.post(
            f"/api/clients/{first_client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "V2.1 item",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
                "advisory_status": "open",
            },
        )
        assert create_resp.status_code == 200
        item_id = create_resp.json()["missing_data_item_id"]

        wrong_update = client.put(
            f"/api/clients/{second_client_id}/missing-items/{item_id}",
            json={"advisory_status": "resolved"},
        )
        assert wrong_update.status_code == 404
        assert wrong_update.json()["detail"]["code"] == "MISSING_DATA_ITEM_NOT_FOUND"

        delete_resp = client.delete(f"/api/clients/{first_client_id}/missing-items/{item_id}")
        assert delete_resp.status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_no_package_d_migration_or_prohibited_model_changes_exist() -> None:
    versions_dir = _backend_root() / "alembic" / "versions"
    assert list(versions_dir.glob("*v21_package_d*.py")) == []
