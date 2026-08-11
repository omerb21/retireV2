from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.m09_cashflow import (
    M09MonthlyResult,
    M09ResolvedComponentInventory,
    M09ScenarioRun,
)
from app.models.retirement_facts import RecurringExpense, RecurringIncome
from app.services import m06_conversion_service as m06_service
from app.services import m09_cashflow_service as service


REQUEST = {
    "scenario_family": "deterministic_monthly_cashflow",
    "scenario_contract_version": "v1",
    "start_month": "2026-01",
    "end_month": "2026-02",
}


def income(**overrides):
    values = {
        "client_id": 1,
        "income_category": "employment",
        "description": "Salary",
        "amount": Decimal("1000.00"),
        "amount_basis": "gross",
        "frequency": "monthly",
        "continuation_status": "ongoing",
        "lifecycle_status": "current",
        "source_status": "planner entered",
        "verification_state": "reviewed",
    }
    values.update(overrides)
    return RecurringIncome(**values)


def expense(**overrides):
    values = {
        "client_id": 1,
        "expense_category": "housing",
        "description": "Housing",
        "amount": Decimal("300.00"),
        "frequency": "monthly",
        "expense_type": "mandatory",
        "continuation_status": "ongoing",
        "lifecycle_status": "current",
        "source_status": "planner entered",
        "verification_state": "reviewed",
    }
    values.update(overrides)
    return RecurringExpense(**values)


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    load_all_models()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pkg013.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                Client(client_id=1, display_name="One", id_number="001", status="delivered"),
                Client(client_id=2, display_name="Two", id_number="002", status="delivered"),
            ]
        )
        db.commit()
    monkeypatch.setattr(service, "list_m06_subjects", lambda _db, _client_id: [])

    def override():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), sessions
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def seed(sessions, *rows) -> None:
    with sessions() as db:
        db.add_all(rows)
        db.commit()


def test_exact_family_horizon_and_extra_fields_fail_closed(api) -> None:
    client, _ = api
    assert client.post(
        "/api/clients/1/m09/inventories", json=REQUEST | {"scenario_family": "generic"}
    ).status_code == 422
    assert client.post(
        "/api/clients/1/m09/inventories", json=REQUEST | {"selected_ids": []}
    ).status_code == 422
    assert client.post(
        "/api/clients/1/m09/inventories",
        json=REQUEST | {"start_month": "2026-1"},
    ).status_code == 422
    assert client.post(
        "/api/clients/1/m09/inventories",
        json=REQUEST | {"start_month": "2026-03"},
    ).status_code == 422


def test_server_inventory_and_none_are_server_owned(api) -> None:
    client, _ = api
    response = client.post("/api/clients/1/m09/inventories", json=REQUEST)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["complete"] is True
    assert body["actor"].startswith("system:m09-cashflow")
    assert len(body["inventory_fingerprint"]) == 64
    assert {item["domain_identity"] for item in body["domains"]} == {
        "recurring_income",
        "recurring_expense",
        "m06_monthly_pension",
    }
    for domain in body["domains"]:
        none = domain["server_resolved_none"]
        assert none["inventory_assessment_id"] == body["inventory_id"]
        assert none["resolver_actor"].startswith("system:m09-cashflow")
        assert len(none["result_fingerprint"]) == 64


def test_exact_decimal_aggregation_and_immutable_evidence(api) -> None:
    client, sessions = api
    seed(sessions, income(), expense())
    response = client.post("/api/clients/1/m09/runs", json=REQUEST)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "success_complete"
    assert body["range_totals"] == {
        "gross_inflow_total": "2000.00",
        "gross_outflow_total": "600.00",
        "period_net": "1400.00",
    }
    assert [item["month"] for item in body["monthly_results"]] == [
        "2026-01",
        "2026-02",
    ]
    assert all(item["period_net"] == "700.00" for item in body["monthly_results"])
    assert body["currentness"]["is_current"] is True
    assert body["m10_eligibility"]["eligible_for_m10"] is True
    assert "selected" not in str(body["assumption_manifest"]).lower()
    with sessions() as db:
        assert len(list(db.scalars(select(M09ResolvedComponentInventory)))) == 1
        assert len(list(db.scalars(select(M09ScenarioRun)))) == 1
        assert len(list(db.scalars(select(M09MonthlyResult)))) == 2


def test_replay_semantic_fingerprint_excludes_run_metadata(api) -> None:
    client, sessions = api
    seed(sessions, income(), expense())
    first = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    second = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert first["run_id"] != second["run_id"]
    assert second["predecessor_run_id"] == first["run_id"]
    assert first["semantic_result_fingerprint"] == second["semantic_result_fingerprint"]
    assert client.get(
        f"/api/clients/1/m09/runs/{first['run_id']}/currentness"
    ).json()["reason_codes"] == ["run_not_current"]
    assert second["currentness"]["is_current"] is True


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (income(frequency="annual"), "frequency_not_monthly"),
        (income(amount_basis="net"), "income_amount_basis_not_gross"),
        (income(start_date=date(2026, 1, 15)), "partial_month_unsupported"),
        (expense(amount=Decimal("-1.00")), "amount_not_canonical_nonnegative_ils"),
        (income(source_status="not recorded"), "source_authority_not_recorded"),
        (expense(verification_state="collected - not yet reviewed"), "source_review_incomplete"),
    ],
)
def test_ineligible_current_recurring_record_blocks_partial_success(api, row, reason) -> None:
    client, sessions = api
    seed(sessions, row)
    response = client.post("/api/clients/1/m09/runs", json=REQUEST)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "dependency_failed"
    assert reason in body["blocker_codes"]
    assert body["monthly_results"] == []
    assert body["range_totals"] is None
    assert body["m10_eligibility"]["eligible_for_m10"] is False


def test_superseded_and_outside_horizon_do_not_become_components(api) -> None:
    client, sessions = api
    seed(
        sessions,
        income(lifecycle_status="superseded"),
        expense(start_date=date(2027, 1, 1)),
    )
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "success_complete"
    assert all(row["component_evidence"] == [] for row in body["monthly_results"])
    assert body["range_totals"]["period_net"] == "0.00"


def test_duplicate_recurring_economic_meaning_blocks(api) -> None:
    client, sessions = api
    seed(sessions, income(), income())
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "dependency_failed"
    assert "duplicate_economic_meaning_unresolved" in body["blocker_codes"]


def fake_m06_subject(
    amount: str = "500.00", *, suffix: str = "1", input_identity: str = "component:pension-one"
) -> SimpleNamespace:
    eligibility = SimpleNamespace(
        eligible_for_downstream=True,
        exclusion_reasons=[],
        informational_warnings=[],
    )
    eligibility.model_dump = lambda mode=None: {
        "eligible_for_downstream": True,
        "exclusion_reasons": [],
        "informational_warnings": [],
    }
    manifest = SimpleNamespace(
        manifest_id=f"M06-M-{suffix}",
        fingerprint="a" * 64,
        authoritative_monthly_amount=amount,
        evidence={
            "authoritative_downstream_handoff": {
                "contract_version": "m06-to-m09-monthly-amount-v1",
                "amount": amount,
                "currency": "ILS",
                "unit": "ILS/month",
                "formula_owner": "M06",
                "rounding_owner": "M06",
            }
        },
    )
    revision = SimpleNamespace(
        revision_id=f"M06-R-{suffix}",
        state="resolved",
        mode="balance_to_monthly_pension",
        input_identity=input_identity,
        manifest=manifest,
        predecessor_snapshot={"m05_revision_id": "M05-R-1"},
    )
    return SimpleNamespace(
        subject_id=f"M06-S-{suffix}", current_revision=revision, eligibility=eligibility
    )


def test_m06_handoff_is_consumed_without_conversion(api, monkeypatch) -> None:
    client, _ = api
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [fake_m06_subject()])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "success_complete"
    components = body["monthly_results"][0]["component_evidence"]
    assert components[0]["component_type"] == "m06_monthly_pension_result"
    assert components[0]["amount"] == "500.00"
    assert components[0]["provenance"]["formula_owner"] == "M06"


def test_recurring_pension_and_m06_overlap_blocks_without_deduplication(
    api, monkeypatch
) -> None:
    client, sessions = api
    seed(sessions, income(income_category="pension"))
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [fake_m06_subject()])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "dependency_failed"
    assert "duplicate_economic_meaning_unresolved" in body["blocker_codes"]


def test_missing_or_invalid_m06_handoff_fails_closed(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject()
    subject.current_revision.manifest.authoritative_monthly_amount = None
    subject.current_revision.manifest.evidence["authoritative_downstream_handoff"] = None
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "dependency_failed"
    assert "m06_authoritative_monthly_handoff_missing" in body["blocker_codes"]


def test_m06_handoff_column_and_fingerprinted_manifest_integrity_contract() -> None:
    leaf = SimpleNamespace(
        formula_id="m06.balance_to_monthly_pension.v1",
        input_identity="component:pension-one",
        predecessor_snapshot={"m05_revision_id": "M05-R-1"},
    )
    coefficient = SimpleNamespace(evidence_id="M06-E-1")
    payload = {
        "formula_id": leaf.formula_id,
        "input_identity": leaf.input_identity,
        "coefficient_evidence_id": coefficient.evidence_id,
        "predecessors": leaf.predecessor_snapshot,
        "authoritative_downstream_handoff": {"amount": "500.00"},
    }
    fingerprint = m06_service._manifest_fingerprint(payload)
    payload["fingerprint"] = fingerprint
    valid = SimpleNamespace(
        manifest=payload,
        fingerprint=fingerprint,
        authoritative_monthly_amount="500.00",
    )
    assert m06_service._manifest_integrity_reasons(leaf, coefficient, valid) == []

    tampered_column = SimpleNamespace(**vars(valid))
    tampered_column.authoritative_monthly_amount = "501.00"
    assert m06_service._manifest_integrity_reasons(leaf, coefficient, tampered_column) == [
        "authoritative_downstream_handoff_integrity_invalid"
    ]

    tampered_json_payload = dict(payload)
    tampered_json_payload["authoritative_downstream_handoff"] = {"amount": "501.00"}
    tampered_json = SimpleNamespace(
        manifest=tampered_json_payload,
        fingerprint=fingerprint,
        authoritative_monthly_amount="500.00",
    )
    assert m06_service._manifest_integrity_reasons(leaf, coefficient, tampered_json) == [
        "manifest_integrity_invalid"
    ]

    mismatched_payload = dict(tampered_json_payload)
    mismatched_fingerprint = m06_service._manifest_fingerprint(mismatched_payload)
    mismatched_payload["fingerprint"] = mismatched_fingerprint
    mismatch = SimpleNamespace(
        manifest=mismatched_payload,
        fingerprint=mismatched_fingerprint,
        authoritative_monthly_amount="500.00",
    )
    assert m06_service._manifest_integrity_reasons(leaf, coefficient, mismatch) == [
        "authoritative_downstream_handoff_integrity_invalid"
    ]

    bad_fingerprint = SimpleNamespace(
        manifest=payload,
        fingerprint="f" * 64,
        authoritative_monthly_amount="500.00",
    )
    assert m06_service._manifest_integrity_reasons(leaf, coefficient, bad_fingerprint) == [
        "manifest_integrity_invalid"
    ]


def test_m09_rejects_mismatched_m06_handoff_without_success(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject()
    subject.current_revision.manifest.authoritative_monthly_amount = "501.00"
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "dependency_failed"
    assert "m06_authoritative_handoff_integrity_invalid" in body["blocker_codes"]


def test_numeric_20_2_exact_boundaries_are_explicit() -> None:
    assert service.M09_MONEY_MAX == Decimal("999999999999999999.99")
    assert service.M09_MONEY_MIN == Decimal("-999999999999999999.99")
    assert service._money_text(service.M09_MONEY_MAX) == "999999999999999999.99"
    assert service._validate_aggregate(service.M09_MONEY_MIN) == service.M09_MONEY_MIN
    with pytest.raises(service.M09NumericDomainError):
        service._money_text(service.M09_MONEY_MAX + Decimal("0.01"))
    with pytest.raises(service.M09NumericDomainError):
        service._validate_aggregate(service.M09_MONEY_MIN - Decimal("0.01"))


def test_oversized_component_is_typed_dependency_failure(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject("1000000000000000000.00")
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "dependency_failed"
    assert body["blocker_codes"] == ["component_amount_outside_numeric_20_2"]
    assert body["monthly_results"] == []


def test_exact_maximum_component_persists_for_one_month(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject("999999999999999999.99")
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    body = client.post(
        "/api/clients/1/m09/runs",
        json=REQUEST | {"end_month": "2026-01"},
    ).json()
    assert body["status"] == "success_complete"
    assert body["monthly_results"][0]["gross_inflow_total"] == "999999999999999999.99"


def test_period_net_accepts_exact_negative_boundary_and_rejects_below_it() -> None:
    component = {
        "component_id": "M09-C-max-expense",
        "component_type": "recurring_expense_record",
        "direction": "outflow",
        "amount": "999999999999999999.99",
        "month": "2026-01",
        "source_identity": "recurring_expense:max",
    }
    rows, totals, _ = service._monthly_rows(
        "M09-R-boundary", 1, ["2026-01"], [component]
    )
    assert rows[0].period_net == Decimal("-999999999999999999.99")
    assert totals["period_net"] == "-999999999999999999.99"
    with pytest.raises(service.M09NumericDomainError) as caught:
        service._validate_aggregate(Decimal("-1000000000000000000.00"))
    assert caught.value.code == "aggregate_outside_numeric_20_2"


def test_monthly_aggregate_overflow_is_persisted_calculation_failure(api, monkeypatch) -> None:
    client, _ = api
    subjects = [
        fake_m06_subject("999999999999999999.99", suffix="1", input_identity="component:one"),
        fake_m06_subject("0.01", suffix="2", input_identity="component:two"),
    ]
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: subjects)
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "calculation_failed"
    assert body["blocker_codes"] == ["aggregate_outside_numeric_20_2"]
    assert body["monthly_results"] == [] and body["range_totals"] is None


def test_range_total_overflow_is_persisted_calculation_failure(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject("999999999999999999.99")
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    body = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert body["status"] == "calculation_failed"
    assert body["blocker_codes"] == ["aggregate_outside_numeric_20_2"]


def test_source_edit_preserves_history_and_invalidates_currentness(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    with sessions() as db:
        row = db.scalar(select(RecurringIncome).where(RecurringIncome.client_id == 1))
        row.amount = Decimal("1200.00")
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
    historical = client.get(f"/api/clients/1/m09/runs/{saved['run_id']}").json()
    assert historical["monthly_results"][0]["gross_inflow_total"] == "1000.00"
    assert historical["currentness"]["is_current"] is False
    assert "dependency_materially_changed" in historical["currentness"]["reason_codes"]
    assert historical["m10_eligibility"]["eligible_for_m10"] is False


def test_client_isolation_and_direct_service_non_leakage(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    foreign = client.get(f"/api/clients/2/m09/runs/{saved['run_id']}")
    missing = client.get("/api/clients/2/m09/runs/M09-R-missing")
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())
    with sessions() as db:
        with pytest.raises(service.M09CashflowError) as caught:
            service.run_response(db, 2, saved["run_id"])
        assert caught.value.code == "m09_resource_not_found"


def test_archived_case_is_read_only_but_history_remains_readable(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    with sessions() as db:
        row = db.get(Client, 1)
        row.status = "archived"
        db.commit()
    assert client.post("/api/clients/1/m09/runs", json=REQUEST).status_code == 409
    assert client.get(f"/api/clients/1/m09/runs/{saved['run_id']}").status_code == 200


def test_failed_inventory_is_persisted_without_partial_rows(api) -> None:
    client, sessions = api
    seed(sessions, income(frequency="quarterly"))
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert saved["status"] == "dependency_failed"
    assert saved["range_totals"] is None
    with sessions() as db:
        run = db.get(M09ScenarioRun, saved["run_id"])
        assert run is not None and run.blocker_codes == ["frequency_not_monthly"]
        assert list(db.scalars(select(M09MonthlyResult).where(M09MonthlyResult.run_id == saved["run_id"]))) == []


def test_append_only_records_reject_orm_and_bulk_mutation(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    with sessions() as db:
        row = db.get(M09ScenarioRun, saved["run_id"])
        row.status = "unsupported"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()
        with pytest.raises(ValueError, match="append-only"):
            db.execute(update(M09ScenarioRun).values(status="unsupported"))
        with pytest.raises(ValueError, match="append-only"):
            db.execute(delete(M09ScenarioRun))


def test_m10_reason_codes_cover_superseded_and_failed_runs(api) -> None:
    client, sessions = api
    seed(sessions, income())
    first = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    second = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    stale = client.get(f"/api/clients/1/m09/runs/{first['run_id']}/m10-eligibility").json()
    assert stale["eligible_for_m10"] is False
    assert stale["reason_codes"] == ["run_not_current"]
    assert client.get(f"/api/clients/1/m09/runs/{second['run_id']}/m10-eligibility").json()["reason_codes"] == []


def test_all_client_scoped_resources_hide_foreign_existence(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    inventory_id = saved["inventory"]["inventory_id"]
    for foreign, missing in (
        (f"/api/clients/2/m09/inventories/{inventory_id}", "/api/clients/2/m09/inventories/M09-I-missing"),
        (f"/api/clients/2/m09/runs/{saved['run_id']}/currentness", "/api/clients/2/m09/runs/M09-R-missing/currentness"),
        (f"/api/clients/2/m09/runs/{saved['run_id']}/m10-eligibility", "/api/clients/2/m09/runs/M09-R-missing/m10-eligibility"),
    ):
        foreign_response, missing_response = client.get(foreign), client.get(missing)
        assert (foreign_response.status_code, foreign_response.json()) == (missing_response.status_code, missing_response.json())


def test_component_contract_is_closed_and_has_no_float_authority(api) -> None:
    client, sessions = api
    seed(sessions, income(amount=Decimal("0.00")), expense(amount=Decimal("0.00")))
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert saved["status"] == "success_complete"
    assert saved["range_totals"] == {"gross_inflow_total": "0.00", "gross_outflow_total": "0.00", "period_net": "0.00"}
    kinds = {component["component_type"] for row in saved["monthly_results"] for component in row["component_evidence"]}
    assert kinds <= {"recurring_income_record", "recurring_expense_record", "m06_monthly_pension_result"}
    assert all(isinstance(component["amount"], str) for row in saved["monthly_results"] for component in row["component_evidence"])


def test_duplicate_component_identity_fails_before_result_persistence() -> None:
    component = {
        "component_id": "M09-C-duplicate",
        "component_type": "recurring_income_record",
        "direction": "inflow",
        "amount": "1.00",
        "month": "2026-01",
        "source_identity": "recurring_income:1",
    }
    with pytest.raises(service.M09CashflowError) as caught:
        service._monthly_rows("M09-R-test", 1, ["2026-01"], [component, component])
    assert caught.value.code == "duplicate_component_identity"


def test_broken_result_fingerprint_makes_success_not_current_or_m10_eligible(api) -> None:
    client, sessions = api
    seed(sessions, income())
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    with sessions() as db:
        database_path = str(db.get_bind().url.database)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE m09_scenario_runs SET result_integrity_fingerprint = ? WHERE run_id = ?",
            ("b" * 64, saved["run_id"]),
        )
        connection.commit()
    response = client.get(f"/api/clients/1/m09/runs/{saved['run_id']}").json()
    assert response["status"] == "success_complete"
    assert response["currentness"]["is_current"] is False
    assert "result_integrity_invalid" in response["currentness"]["reason_codes"]
    assert response["m10_eligibility"]["eligible_for_m10"] is False


def test_warning_categories_are_typed_and_have_no_generic_bypass(api, monkeypatch) -> None:
    client, _ = api
    subject = fake_m06_subject()
    subject.eligibility.informational_warnings = ["m06_information_only"]
    subject.eligibility.model_dump = lambda mode=None: {
        "eligible_for_downstream": True,
        "exclusion_reasons": [],
        "informational_warnings": ["m06_information_only"],
    }
    monkeypatch.setattr(service, "list_m06_subjects", lambda *_: [subject])
    saved = client.post("/api/clients/1/m09/runs", json=REQUEST).json()
    assert saved["warnings"] == [{"code": "m06_information_only", "classification": "informational_warning"}]
    assert saved["m10_eligibility"]["eligible_for_m10"] is True
    assert saved["m10_eligibility"]["informational_warnings"] == ["m06_information_only"]
    assert saved["assumption_manifest"]["warning_dispositions"] == []
