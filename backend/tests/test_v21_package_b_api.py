from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.missing_data_item import MissingDataItem
from app.models.retirement_facts import (
    CapitalAsset,
    PensionHolding,
    RecurringExpense,
    RecurringIncome,
    RetirementTimingWorkIntention,
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


def _build_client(tmp_path: Path) -> tuple[TestClient, sessionmaker]:
    db_path = tmp_path / "v21_package_b_api.db"
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


RESOURCE_CASES: list[dict[str, Any]] = [
    {
        "path": "pension-holdings",
        "model": PensionHolding,
        "not_found_code": "PENSION_HOLDING_NOT_FOUND",
        "payload": {
            "provider_name": "Provider",
            "product_type": "pension fund",
            "known_balance_amount": "1000.00",
            "balance_as_of_date": "2026-01-01",
            "source_type": "statement",
        },
        "update": {"product_name": "Updated product"},
        "updated_field": "product_name",
        "updated_value": "Updated product",
        "invalid_enum": {"product_type": "retirement account"},
    },
    {
        "path": "capital-assets",
        "model": CapitalAsset,
        "not_found_code": "CAPITAL_ASSET_NOT_FOUND",
        "payload": {
            "asset_category": "bank deposit",
            "asset_description": "Deposit",
            "known_value_amount": "5000.00",
            "value_as_of_date": "2026-01-02",
        },
        "update": {"liquidity_note": "Updated liquidity"},
        "updated_field": "liquidity_note",
        "updated_value": "Updated liquidity",
        "invalid_enum": {"asset_category": "boat"},
    },
    {
        "path": "recurring-incomes",
        "model": RecurringIncome,
        "not_found_code": "RECURRING_INCOME_NOT_FOUND",
        "payload": {
            "income_category": "employment",
            "description": "Salary",
            "amount": "10000.00",
            "amount_basis": "gross",
            "frequency": "monthly",
            "continuation_status": "ongoing",
        },
        "update": {"description": "Updated salary"},
        "updated_field": "description",
        "updated_value": "Updated salary",
        "invalid_enum": {"frequency": "weekly"},
    },
    {
        "path": "recurring-expenses",
        "model": RecurringExpense,
        "not_found_code": "RECURRING_EXPENSE_NOT_FOUND",
        "payload": {
            "expense_category": "housing",
            "description": "Rent",
            "amount": "3000.00",
            "frequency": "monthly",
            "expense_type": "mandatory",
            "continuation_status": "ongoing",
        },
        "update": {"description": "Updated rent"},
        "updated_field": "description",
        "updated_value": "Updated rent",
        "invalid_enum": {"expense_type": "preferred"},
    },
    {
        "path": "retirement-timing-work-intentions",
        "model": RetirementTimingWorkIntention,
        "not_found_code": "RETIREMENT_TIMING_WORK_INTENTION_NOT_FOUND",
        "payload": {
            "timing_confidence": "known",
            "work_after_retirement_intention": "stop working",
            "other_known_retirement_date": "2030-01-01",
            "other_known_retirement_date_label": "Contractual date",
        },
        "update": {"work_intention_note": "Updated note"},
        "updated_field": "work_intention_note",
        "updated_value": "Updated note",
        "invalid_enum": {"timing_confidence": "confirmed by system"},
    },
]


def _case_id(case: dict[str, Any]) -> str:
    return str(case["path"])


def _create_resource(client: TestClient, client_id: int, case: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/clients/{client_id}/{case['path']}", json=case["payload"])
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=_case_id)
def test_fact_resource_create_list_read_one_partial_update_defaults_and_ownership(
    tmp_path: Path,
    case: dict[str, Any],
) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-1001")
        other_client_id = _create_client(client, id_number="B-1002")

        created = _create_resource(client, client_id, case)
        row_id = created["id"]
        assert created["client_id"] == client_id
        assert created["lifecycle_status"] == "current"
        assert created["source_status"] == "not recorded"
        assert created["verification_state"] == "collected - not yet reviewed"
        for field_name, value in case["payload"].items():
            if field_name in created:
                assert created[field_name] == value

        list_resp = client.get(f"/api/clients/{client_id}/{case['path']}")
        assert list_resp.status_code == 200
        assert [row["id"] for row in list_resp.json()] == [row_id]

        read_resp = client.get(f"/api/clients/{client_id}/{case['path']}/{row_id}")
        assert read_resp.status_code == 200
        assert read_resp.json()["id"] == row_id

        update_resp = client.put(
            f"/api/clients/{client_id}/{case['path']}/{row_id}",
            json=case["update"],
        )
        assert update_resp.status_code == 200
        assert update_resp.json()[case["updated_field"]] == case["updated_value"]
        assert update_resp.json()["lifecycle_status"] == "current"

        with session_local() as db:
            stored = db.get(case["model"], row_id)
            assert stored is not None
            assert getattr(stored, case["updated_field"]) == case["updated_value"]

        wrong_client_read = client.get(f"/api/clients/{other_client_id}/{case['path']}/{row_id}")
        assert wrong_client_read.status_code == 404
        assert wrong_client_read.json()["detail"]["code"] == case["not_found_code"]

        wrong_client_update = client.put(
            f"/api/clients/{other_client_id}/{case['path']}/{row_id}",
            json=case["update"],
        )
        assert wrong_client_update.status_code == 404
        assert wrong_client_update.json()["detail"]["code"] == case["not_found_code"]

        missing_client_resp = client.post("/api/clients/999999/pension-holdings", json=RESOURCE_CASES[0]["payload"])
        assert missing_client_resp.status_code == 404
        assert missing_client_resp.json()["detail"]["code"] == "CLIENT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=_case_id)
def test_fact_resource_invalid_enum_returns_422(tmp_path: Path, case: dict[str, Any]) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-2001")

        invalid_payload = {**case["payload"], **case["invalid_enum"]}
        invalid_enum_resp = client.post(f"/api/clients/{client_id}/{case['path']}", json=invalid_payload)
        assert invalid_enum_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=_case_id)
def test_fact_resource_rejects_lifecycle_status_in_create_and_update(
    tmp_path: Path,
    case: dict[str, Any],
) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-2101")

        create_lifecycle_resp = client.post(
            f"/api/clients/{client_id}/{case['path']}",
            json={**case["payload"], "lifecycle_status": "superseded"},
        )
        assert create_lifecycle_resp.status_code == 422

        created = _create_resource(client, client_id, case)
        row_id = created["id"]

        update_lifecycle_resp = client.put(
            f"/api/clients/{client_id}/{case['path']}/{row_id}",
            json={"lifecycle_status": "superseded"},
        )
        assert update_lifecycle_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=_case_id)
def test_fact_resource_delete_and_supersede_routes_absent(tmp_path: Path, case: dict[str, Any]) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-2201")
        created = _create_resource(client, client_id, case)
        row_id = created["id"]

        delete_resp = client.delete(f"/api/clients/{client_id}/{case['path']}/{row_id}")
        assert delete_resp.status_code == 405

        supersede_resp = client.post(f"/api/clients/{client_id}/{case['path']}/{row_id}/supersede")
        assert supersede_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_planner_assumption_route_absent(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-2301")
        planner_assumption_resp = client.post(
            f"/api/clients/{client_id}/planner-assumptions",
            json={"title": "Not authorized"},
        )
        assert planner_assumption_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=_case_id)
def test_lifecycle_list_filters_default_current_superseded_and_all(
    tmp_path: Path,
    case: dict[str, Any],
) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-3001")

        current = _create_resource(client, client_id, case)
        superseded = _create_resource(client, client_id, case)
        current_id = current["id"]
        superseded_id = superseded["id"]

        with session_local() as db:
            row = db.get(case["model"], superseded_id)
            assert row is not None
            row.lifecycle_status = "superseded"
            db.commit()

        default_resp = client.get(f"/api/clients/{client_id}/{case['path']}")
        assert default_resp.status_code == 200
        assert [row["id"] for row in default_resp.json()] == [current_id]

        current_filter_resp = client.get(
            f"/api/clients/{client_id}/{case['path']}",
            params={"lifecycle_status": "current"},
        )
        assert current_filter_resp.status_code == 200
        assert [row["id"] for row in current_filter_resp.json()] == [current_id]

        superseded_filter_resp = client.get(
            f"/api/clients/{client_id}/{case['path']}",
            params={"lifecycle_status": "superseded"},
        )
        assert superseded_filter_resp.status_code == 200
        assert [row["id"] for row in superseded_filter_resp.json()] == [superseded_id]

        all_filter_resp = client.get(
            f"/api/clients/{client_id}/{case['path']}",
            params={"lifecycle_status": "all"},
        )
        assert all_filter_resp.status_code == 200
        assert {row["id"] for row in all_filter_resp.json()} == {current_id, superseded_id}

        invalid_filter_resp = client.get(
            f"/api/clients/{client_id}/{case['path']}",
            params={"lifecycle_status": "archived"},
        )
        assert invalid_filter_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_package_a_conditional_validation_is_enforced(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-4001")

        pension_balance_resp = client.post(
            f"/api/clients/{client_id}/pension-holdings",
            json={
                "provider_name": "Provider",
                "product_type": "pension fund",
                "known_balance_amount": "1000.00",
            },
        )
        assert pension_balance_resp.status_code == 422

        pension_amount_resp = client.post(
            f"/api/clients/{client_id}/pension-holdings",
            json={
                "provider_name": "Provider",
                "product_type": "pension fund",
                "known_monthly_pension_amount": "100.00",
            },
        )
        assert pension_amount_resp.status_code == 422

        asset_value_resp = client.post(
            f"/api/clients/{client_id}/capital-assets",
            json={
                "asset_category": "bank deposit",
                "asset_description": "Deposit",
                "known_value_amount": "500.00",
            },
        )
        assert asset_value_resp.status_code == 422

        retirement_date_resp = client.post(
            f"/api/clients/{client_id}/retirement-timing-work-intentions",
            json={
                "timing_confidence": "known",
                "work_after_retirement_intention": "undecided",
                "other_known_retirement_date": "2030-01-01",
            },
        )
        assert retirement_date_resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_legacy_create_without_v21_fields_remains_accepted(tmp_path: Path) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5001")

        legacy_create_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "Legacy create",
                "missing_status": "missing",
            },
        )
        assert legacy_create_resp.status_code == 200
        payload = legacy_create_resp.json()
        assert payload["planning_domain"] is None
        assert payload["related_record_type"] is None
        assert payload["related_record_id"] is None
        assert payload["advisory_status"] is None
        assert payload["neutral_reason"] is None

        with session_local() as db:
            persisted = db.get(MissingDataItem, payload["missing_data_item_id"])
            assert persisted is not None
            assert persisted.planning_domain is None
            assert persisted.advisory_status is None
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_stored_legacy_row_reads_null_v21_fields_without_open_injection(
    tmp_path: Path,
) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5002")

        with session_local() as db:
            db.add(
                MissingDataItem(
                    missing_data_item_id="MD-LEGACY",
                    client_id=client_id,
                    missing_item_type="data",
                    missing_item_label="Legacy item",
                    missing_status="missing",
                    notes=None,
                )
            )
            db.commit()

        list_legacy_resp = client.get(f"/api/clients/{client_id}/missing-items")
        assert list_legacy_resp.status_code == 200
        legacy_item = next(item for item in list_legacy_resp.json() if item["missing_data_item_id"] == "MD-LEGACY")
        assert legacy_item["planning_domain"] is None
        assert legacy_item["related_record_type"] is None
        assert legacy_item["related_record_id"] is None
        assert legacy_item["advisory_status"] is None
        assert legacy_item["neutral_reason"] is None

        with session_local() as db:
            legacy = db.get(MissingDataItem, "MD-LEGACY")
            assert legacy is not None
            assert legacy.planning_domain is None
            assert legacy.related_record_type is None
            assert legacy.related_record_id is None
            assert legacy.advisory_status is None
            assert legacy.neutral_reason is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("v21_field", "value", "expected_code"),
    [
        ("planning_domain", "pension holdings", "ADVISORY_STATUS_REQUIRED"),
        ("related_record_type", "pension_holding", "PLANNING_DOMAIN_REQUIRED"),
        ("related_record_id", 1, "PLANNING_DOMAIN_REQUIRED"),
        ("advisory_status", "open", "PLANNING_DOMAIN_REQUIRED"),
        ("neutral_reason", "not applicable", "PLANNING_DOMAIN_REQUIRED"),
    ],
)
def test_missing_data_item_v21_creation_detected_when_any_v21_field_is_supplied(
    tmp_path: Path,
    v21_field: str,
    value: Any,
    expected_code: str,
) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number=f"B-51-{v21_field}")

        response = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": f"V2.1 detection {v21_field}",
                "missing_status": "missing",
                v21_field: value,
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == expected_code
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_v21_creation_requires_planning_domain(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5201")
        missing_domain_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "V2.1 missing domain",
                "missing_status": "missing",
                "advisory_status": "open",
            },
        )
        assert missing_domain_resp.status_code == 422
        assert missing_domain_resp.json()["detail"]["code"] == "PLANNING_DOMAIN_REQUIRED"
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_v21_creation_requires_advisory_status(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5202")
        missing_advisory_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "V2.1 missing advisory",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
            },
        )
        assert missing_advisory_resp.status_code == 422
        assert missing_advisory_resp.json()["detail"]["code"] == "ADVISORY_STATUS_REQUIRED"
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_v21_creation_rejects_non_open_advisory_status(tmp_path: Path) -> None:
    client, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5203")
        invalid_advisory_resp = client.post(
            f"/api/clients/{client_id}/missing-items",
            json={
                "missing_item_type": "data",
                "missing_item_label": "V2.1 invalid advisory",
                "missing_status": "missing",
                "planning_domain": "pension holdings",
                "advisory_status": "resolved",
            },
        )
        assert invalid_advisory_resp.status_code == 422
        assert invalid_advisory_resp.json()["detail"]["code"] == "ADVISORY_STATUS_INVALID"
    finally:
        app.dependency_overrides.clear()


def test_missing_data_item_v21_creation_accepts_open_status_and_null_related_linkage(
    tmp_path: Path,
) -> None:
    client, session_local = _build_client(tmp_path)
    try:
        client_id = _create_client(client, id_number="B-5204")
        v21_resp = client.post(
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
        assert v21_resp.status_code == 200
        assert v21_resp.json()["planning_domain"] == "pension holdings"
        assert v21_resp.json()["advisory_status"] == "open"
        assert v21_resp.json()["related_record_type"] is None
        assert v21_resp.json()["related_record_id"] is None

        with session_local() as db:
            persisted = db.get(MissingDataItem, v21_resp.json()["missing_data_item_id"])
            assert persisted is not None
            assert persisted.planning_domain == "pension holdings"
            assert persisted.advisory_status == "open"
            assert persisted.related_record_type is None
            assert persisted.related_record_id is None
    finally:
        app.dependency_overrides.clear()


def test_no_package_b_migration_or_prohibited_file_changes_exist() -> None:
    versions_dir = _backend_root() / "alembic" / "versions"
    assert list(versions_dir.glob("*v21_package_b*.py")) == []
