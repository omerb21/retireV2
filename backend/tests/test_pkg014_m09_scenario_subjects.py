from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m09_scenario_subject import M09ScenarioAdjustment, M09ScenarioSubject, M09SubjectRun
from app.models.retirement_facts import RecurringExpense, RecurringIncome
from app.services import m09_cashflow_service as legacy
from app.services import m09_scenario_subject_service as service


HORIZON = {"start_month": "2026-01", "end_month": "2026-03"}
FAMILY = "declared_retirement_cashflow_adjustments"


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    load_all_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'pkg014.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all([
            Client(client_id=1, display_name="One", id_number="001", status="delivered"),
            Client(client_id=2, display_name="Two", id_number="002", status="delivered"),
            RecurringIncome(client_id=1, income_category="employment", description="Income", amount=Decimal("1000.00"), amount_basis="gross", frequency="monthly", continuation_status="ongoing", lifecycle_status="current", source_status="planner entered", verification_state="reviewed"),
            RecurringExpense(client_id=1, expense_category="housing", description="Expense", amount=Decimal("300.00"), frequency="monthly", expense_type="mandatory", continuation_status="ongoing", lifecycle_status="current", source_status="planner entered", verification_state="reviewed"),
        ])
        db.commit()
    monkeypatch.setattr(legacy, "list_m06_subjects", lambda _db, _client_id: [])
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def adjusted(label="Alternative", adjustments=None):
    return {
        "scenario_family": FAMILY,
        "scenario_contract_version": "v1",
        "display_label": label,
        "adjustments": adjustments if adjustments is not None else [{"adjustment_type": "declared_additional_monthly_income", "amount": "100.00", "start_month": "2026-01", "end_month": "2026-02"}],
    }


def test_baseline_is_server_owned_and_idempotent(api):
    client, _, _ = api
    first = client.post("/api/clients/1/m09/subjects/baseline")
    second = client.post("/api/clients/1/m09/subjects/baseline")
    assert first.status_code == second.status_code == 200
    assert first.json()["scenario_subject_id"] == second.json()["scenario_subject_id"]
    assert first.json()["subject_type"] == "baseline"
    assert first.json()["adjustment_manifest"]["baseline_evidence"] == "server_resolved_no_scenario_adjustments"


def test_adjusted_validation_and_semantic_duplicate_rejection(api):
    client, _, _ = api
    assert client.post("/api/clients/1/m09/subjects", json=adjusted()).status_code == 201
    duplicate = client.post("/api/clients/1/m09/subjects", json=adjusted("Other label"))
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "scenario_subject_semantically_duplicate"
    for amount in ["0.00", "-1.00", "1", "1.001", "1e2", 1.25]:
        body = adjusted(adjustments=[adjusted()["adjustments"][0] | {"amount": amount}])
        assert client.post("/api/clients/1/m09/subjects", json=body).status_code == 422
    assert client.post("/api/clients/1/m09/subjects", json=adjusted(adjustments=[])).status_code == 422
    assert client.post("/api/clients/1/m09/subjects", json=adjusted() | {"scenario_family": "deterministic_monthly_cashflow"}).status_code == 422


def test_semantic_identity_is_order_independent(api):
    client, _, _ = api
    first = [
        {"adjustment_type": "declared_additional_monthly_expense", "amount": "50.00", "start_month": "2026-02", "end_month": "2026-03"},
        {"adjustment_type": "declared_additional_monthly_income", "amount": "100.00", "start_month": "2026-01", "end_month": "2026-02"},
    ]
    created = client.post("/api/clients/1/m09/subjects", json=adjusted(adjustments=first))
    assert created.status_code == 201
    reversed_request = client.post("/api/clients/1/m09/subjects", json=adjusted("Permutation", list(reversed(first))))
    assert reversed_request.status_code == 409
    assert reversed_request.json()["detail"]["code"] == "scenario_subject_semantically_duplicate"


def test_additive_execution_multiplicity_and_partial_range(api):
    client, _, _ = api
    inputs = [
        {"adjustment_type": "declared_additional_monthly_income", "amount": "100.00", "start_month": "2026-01", "end_month": "2026-02"},
        {"adjustment_type": "declared_additional_monthly_income", "amount": "100.00", "start_month": "2026-01", "end_month": "2026-02"},
        {"adjustment_type": "declared_additional_monthly_expense", "amount": "50.00", "start_month": "2026-02", "end_month": "2026-03"},
    ]
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted(adjustments=inputs)).json()
    assert len(subject["adjustments"]) == 3
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON)
    assert run.status_code == 201, run.text
    body = run.json()
    assert [m["period_net"] for m in body["monthly_results"]] == ["900.00", "850.00", "650.00"]
    assert body["range_totals"] == {"gross_inflow_total": "3400.00", "gross_outflow_total": "1000.00", "period_net": "2400.00"}
    assert body["m10_eligibility"]["eligibility_contract_version"] == "m09-to-m10-eligibility-v2"
    assert body["currentness"]["assessment_contract_version"] == "m09-subject-currentness-v1"


def test_adjustment_must_be_contained_and_failure_is_not_persisted(api):
    client, sessions, _ = api
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    response = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json={"start_month": "2026-02", "end_month": "2026-03"})
    assert response.status_code == 422
    with sessions() as db:
        assert db.scalar(select(M09SubjectRun)) is None


def test_parallel_currentness_and_replay_semantics(api):
    client, _, _ = api
    baseline = client.post("/api/clients/1/m09/subjects/baseline").json()
    adjusted_subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    base_run = client.post(f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs", json=HORIZON).json()
    a1 = client.post(f"/api/clients/1/m09/subjects/{adjusted_subject['scenario_subject_id']}/runs", json=HORIZON).json()
    base_current = client.get(f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs/{base_run['run_id']}/currentness").json()
    assert base_current["is_current"] is True, base_current["reason_codes"]
    a2 = client.post(f"/api/clients/1/m09/subjects/{adjusted_subject['scenario_subject_id']}/runs", json=HORIZON).json()
    assert a1["semantic_result_fingerprint"] == a2["semantic_result_fingerprint"]
    assert client.get(f"/api/clients/1/m09/subjects/{adjusted_subject['scenario_subject_id']}/runs/{a1['run_id']}/currentness").json()["is_current"] is False
    assert client.get(f"/api/clients/1/m09/subjects/{adjusted_subject['scenario_subject_id']}/runs/{a2['run_id']}/currentness").json()["is_current"] is True
    assert client.get(f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs/{base_run['run_id']}/currentness").json()["is_current"] is True
    assert base_run["factual_baseline_material_fingerprint"] == a2["factual_baseline_material_fingerprint"]


def test_client_isolation_hides_foreign_resources(api):
    client, _, _ = api
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON).json()
    assert client.get(f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}").status_code == 404
    assert client.get(f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}").status_code == 404


def test_client_isolation_matrix_matches_nonexistent_resources(api):
    client, sessions, _ = api
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON).json()
    paths = [
        ("get", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}", None, f"/api/clients/2/m09/subjects/missing"),
        ("post", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs", HORIZON, f"/api/clients/2/m09/subjects/missing/runs"),
        ("get", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs", None, f"/api/clients/2/m09/subjects/missing/runs"),
        ("get", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}", None, f"/api/clients/2/m09/subjects/missing/runs/missing"),
        ("get", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/currentness", None, f"/api/clients/2/m09/subjects/missing/runs/missing/currentness"),
        ("get", f"/api/clients/2/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/m10-eligibility", None, f"/api/clients/2/m09/subjects/missing/runs/missing/m10-eligibility"),
    ]
    for method, foreign, payload, missing in paths:
        left = getattr(client, method)(foreign, json=payload) if payload else getattr(client, method)(foreign)
        right = getattr(client, method)(missing, json=payload) if payload else getattr(client, method)(missing)
        assert (left.status_code, left.json()) == (right.status_code, right.json())
    with sessions() as db:
        for target in (subject["scenario_subject_id"], "missing"):
            with pytest.raises(service.M09CashflowError) as captured:
                service.get_subject(db, 2, target)
            assert (captured.value.status_code, captured.value.code) == (404, "m09_subject_resource_not_found")
        for target in (subject["scenario_subject_id"], "missing"):
            with pytest.raises(service.M09CashflowError) as captured:
                service.execute_subject_run(db, 2, target, service.SubjectExecutionRequest(**HORIZON))
            assert (captured.value.status_code, captured.value.code) == (404, "m09_subject_resource_not_found")
    assert client.post("/api/clients/999/m09/subjects/baseline").status_code == 404


def test_upstream_factual_change_stales_run_and_eligibility(api):
    client, sessions, _ = api
    subject = client.post("/api/clients/1/m09/subjects/baseline").json()
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON).json()
    with sessions() as db:
        income = db.scalar(select(RecurringIncome).where(RecurringIncome.client_id == 1))
        income.amount = Decimal("1100.00")
        db.commit()
    current = client.get(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/currentness").json()
    eligibility = client.get(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/m10-eligibility").json()
    assert current["is_current"] is False
    assert "factual_baseline_material_changed" in current["reason_codes"]
    assert eligibility["eligible_for_m10"] is False


def test_factual_material_fingerprint_binds_dimensions_and_excludes_scenario_metadata(monkeypatch):
    inventory = SimpleNamespace(
        component_domain_contract_version="domains-v1",
        start_month="2026-01", end_month="2026-02",
        inventory_payload={"material_fingerprint": "a" * 64},
    )
    original = service._factual_material(inventory)
    for field, value in (("component_domain_contract_version", "domains-v2"), ("start_month", "2025-12"), ("end_month", "2026-03")):
        changed = SimpleNamespace(**inventory.__dict__); setattr(changed, field, value)
        assert service._factual_material(changed) != original
    changed_material = SimpleNamespace(**inventory.__dict__); changed_material.inventory_payload = {"material_fingerprint": "b" * 64}
    assert service._factual_material(changed_material) != original
    monkeypatch.setattr(service, "ENGINE_VERSION", "changed-engine")
    assert service._factual_material(inventory) != original
    monkeypatch.setattr(service, "ENGINE_VERSION", legacy.ENGINE_VERSION)
    monkeypatch.setattr(service, "RESULT_SCHEMA_VERSION", "changed-schema")
    assert service._factual_material(inventory) != original
    # Subject IDs, labels, actors, run IDs, timestamps and adjustments are not inputs.
    assert service._factual_material(inventory) == service._factual_material(SimpleNamespace(**inventory.__dict__))


def test_manifest_child_drift_fails_all_authoritative_paths(api):
    client, sessions, engine = api
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON).json()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """INSERT INTO m09_scenario_adjustments
            (adjustment_id,scenario_subject_id,client_id,ordinal,adjustment_type,amount,amount_text,start_month,end_month,provenance,semantic_fingerprint,actor,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            ("tampered", subject["scenario_subject_id"], 1, 2, "declared_additional_monthly_income", 900, "900.00", "2026-01", "2026-02", "planner_declared_scenario_adjustment", "f" * 64, "system:m09"),
        )
    current_path=f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/currentness"
    eligibility_path=f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}/m10-eligibility"
    current=client.get(current_path).json(); eligibility=client.get(eligibility_path).json()
    assert current["is_current"] is False and service.MANIFEST_INTEGRITY_REASON in current["reason_codes"]
    assert eligibility["eligible_for_m10"] is False and service.MANIFEST_INTEGRITY_REASON in eligibility["reason_codes"]
    history=client.get(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs").json()
    assert history[0]["status"] == "integrity_failed" and history[0]["is_current"] is False and history[0]["eligible_for_m10"] is False
    for method, path, payload in (
        (client.get, f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}", None),
        (client.get, f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}", None),
        (client.post, f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", HORIZON),
    ):
        response=method(path, json=payload) if payload else method(path)
        assert response.status_code == 409
    with sessions() as db:
        assert len(list(db.scalars(select(M09SubjectRun)))) == 1


@pytest.mark.parametrize("tamper_sql", [
    "UPDATE m09_subject_monthly_results SET gross_inflow_total = gross_inflow_total + 1 WHERE run_id = ?",
    "UPDATE m09_subject_monthly_results SET result_fingerprint = ? WHERE run_id = ?",
    "UPDATE m09_subject_runs SET range_totals = ? WHERE run_id = ?",
])
def test_result_tampering_is_non_authoritative(api, tamper_sql):
    client, _, engine = api
    subject = client.post("/api/clients/1/m09/subjects/baseline").json()
    run = client.post(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs", json=HORIZON).json()
    with engine.begin() as connection:
        if "result_fingerprint" in tamper_sql:
            connection.exec_driver_sql(tamper_sql, ("0" * 64, run["run_id"]))
        elif "range_totals" in tamper_sql:
            connection.exec_driver_sql(tamper_sql, (json.dumps({"gross_inflow_total":"1.00","gross_outflow_total":"0.00","period_net":"1.00"}), run["run_id"]))
        else:
            connection.exec_driver_sql(tamper_sql, (run["run_id"],))
    root=f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}/runs/{run['run_id']}"
    assert client.get(f"{root}/currentness").json()["is_current"] is False
    assert client.get(f"{root}/m10-eligibility").json()["eligible_for_m10"] is False
    detail=client.get(root)
    assert detail.status_code == 409 and detail.json()["detail"]["code"] == "m09_subject_result_integrity_invalid"


def test_manifest_json_tampering_is_detected(api):
    client, _, engine = api
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE m09_scenario_subjects SET adjustment_manifest = ? WHERE scenario_subject_id = ?", (json.dumps({"adjustments": []}), subject["scenario_subject_id"]))
    response=client.get(f"/api/clients/1/m09/subjects/{subject['scenario_subject_id']}")
    assert response.status_code == 409 and response.json()["detail"]["code"] == service.MANIFEST_INTEGRITY_REASON


def test_orm_and_database_append_only(api):
    _, sessions, engine = api
    client = TestClient(app)
    subject = client.post("/api/clients/1/m09/subjects", json=adjusted()).json()
    with sessions() as db:
        row = db.get(M09ScenarioSubject, subject["scenario_subject_id"])
        row.display_label = "mutated"
        with pytest.raises(ValueError): db.commit()
        db.rollback()
        with pytest.raises(ValueError): db.execute(update(M09ScenarioAdjustment).values(amount=Decimal("1.00")))
        db.rollback()
        with pytest.raises(ValueError): db.execute(delete(M09ScenarioSubject))
    # create_all does not install migration triggers; the migration suite proves DB-trigger enforcement.


def test_existing_family_remains_separate(api):
    client, sessions, _ = api
    baseline = client.post("/api/clients/1/m09/subjects/baseline").json()
    client.post(f"/api/clients/1/m09/subjects/{baseline['scenario_subject_id']}/runs", json=HORIZON)
    legacy_request = {"scenario_family": "deterministic_monthly_cashflow", "scenario_contract_version": "v1"} | HORIZON
    legacy_run = client.post("/api/clients/1/m09/runs", json=legacy_request)
    assert legacy_run.status_code == 201
    assert legacy_run.json()["scenario_family"] == "deterministic_monthly_cashflow"
    with sessions() as db:
        assert len(list(db.scalars(select(M09ScenarioSubject)))) == 1
