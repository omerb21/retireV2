"""Executable reconciliation for RTDIR Definition section 9.5.

The producer suites remain the origin oracles.  This module closes the adapter
inventory gap: it freezes every accepted code/disposition, proves the route DTO
preemptions before a producer is entered, and exercises the previously missing
Planning Input production-path distinctions.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from inspect import getsource

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import retirement_income_readiness_routes as routes
from app.db.session import get_db
from app.main import app, create_app
from app.models.canonical_conversion import allocations, batches, conversions, pensions
from app.models.planning_input_decision import PensionIncomeResolution
from app.models.retirement_facts import RecurringIncome
from app.services import pension_monthly_basis_service as monthly_basis
from app.services import planning_input_service
from app.services import professional_source_snapshot_service as snapshot_service
from app.services import retirement_target_service
from app.services import retirement_target_date_income_source_admission_service as rtisa_service
from app.services.pension_product_service import PensionProductError
from app.security.session import COOKIE_NAME, issue
from test_pension_monthly_basis import AuditSession, conversion_arguments
from test_planning_input import choose
from test_recovery_pension_products import engine
from test_rtdir_vertical_slice import _edge_headers, _production_config
from test_retirement_target_date_income_comparison_basis import _entry, _rtisa, _run
from test_retirement_target_date_income_source_admission import _authority, _read


PLANNING = {
    "SNAPSHOT_REQUIRES_FRESH_TRANSACTION": True, "UNSUPPORTED_DATABASE": True,
    "CLIENT_NOT_FOUND": True, "SOURCE_STRUCTURE_INVALID": True,
    "RESOLUTION_OWNERSHIP_INVALID": True, "TARGET_REFERENCE_STRUCTURE_INVALID": False,
    "BASIS_SOURCE_STRUCTURE_INVALID": False, "BASIS_SOURCE_OWNERSHIP_INVALID": False,
    "BASIS_SOURCE_NOT_CURRENT": False, "CONVERSION_EFFECTIVE_DATE_MISSING": False,
    "CONVERSION_EFFECTIVE_DATE_MISMATCH": True,
    "BASIS_CONVERSION_PROVENANCE_INVALID": True,
    "PERSISTED_CONVERSION_RATIO_INVALID": True,
    "TEMPORAL_SOURCE_OWNERSHIP_INVALID": False, "TEMPORAL_SOURCE_NOT_CURRENT": False,
    "TEMPORAL_SOURCE_NOT_FOUND": False, "TEMPORAL_DECISION_STRUCTURE_INVALID": True,
    "TEMPORAL_SOURCE_STRUCTURE_INVALID": True,
}
RIT = {
    "RIT_COMMAND_SCHEMA_INVALID": False, "RIT_CLIENT_ID_INVALID": True,
    "RIT_TARGET_RECORD_INVALID": True, "RIT_PLANNING_CONTEXT_INVALID": True,
    "RIT_AMOUNT_MISSING": False, "RIT_AMOUNT_INVALID": True,
    "RIT_AMOUNT_PRECISION_UNSUPPORTED": True, "RIT_INCOME_BASIS_MISSING": False,
    "RIT_INCOME_BASIS_INVALID": False, "RIT_PRICE_BASIS_MISSING": False,
    "RIT_PRICE_BASIS_INVALID": False, "RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL": True,
    "RIT_PRICE_REFERENCE_DATE_MISSING": True, "RIT_PRICE_REFERENCE_DATE_INVALID": False,
    "RIT_CONFIRMATION_INVALID": True, "RIT_RECORD_UNAVAILABLE": True,
    "RIT_PLANNING_CONTEXT_UNAVAILABLE": True, "RIT_RETIREMENT_TARGET_NOT_READY": True,
    "RIT_CONFIRMATION_CONTEXT_STALE": True, "RIT_RECORD_VERSION_CONFLICT": True,
    "RIT_RECORD_VERSION_EXHAUSTED": True, "RIT_CONFIRMATION_MISSING": False,
    "RIT_CURRENCY_INVALID": False, "RIT_TARGET_MISSING": True,
    "RIT_TARGET_CLIENT_MISMATCH": False, "RIT_STORED_FINGERPRINT_MISMATCH": True,
    "RIT_PLANNING_IDENTITY_STALE": True, "RIT_RETIREMENT_TARGET_STALE": True,
    "RIT_RECONFIRMATION_REQUIRED": True,
}
RTISA = {
    "RTISA_CLIENT_ID_INVALID": False, "RTISA_EXPECTED_PLANNING_FINGERPRINT_INVALID": False,
    "RTISA_PLANNING_CONTEXT_UNAVAILABLE": True, "RTISA_PLANNING_CONTEXT_INVALID": True,
    "RTISA_PLANNING_IDENTITY_STALE": True, "RTISA_RETIREMENT_TARGET_NOT_READY": True,
    "RTISA_SOURCE_UNIVERSE_INVALID": True, "RTISA_PENSION_RESULT_INVALID": True,
    "RTISA_PENSION_AUTHORITY_UNAVAILABLE": True, "RTISA_PENSION_SOURCE_NOT_READY": True,
    "RTISA_PENSION_APPLICABILITY_UNRESOLVED": True,
    "RTISA_SOURCE_CURRENCY_UNSUPPORTED": True, "RTISA_SOURCE_IDENTITY_UNRESOLVED": True,
    "RTISA_SOURCE_IDENTITY_STALE": True, "RTISA_SOURCE_RECORD_INVALID": True,
    "RTISA_SOURCE_AUTHORITY_NOT_RECORDED": True, "RTISA_SOURCE_REVIEW_INCOMPLETE": True,
    "RTISA_SOURCE_AMOUNT_INVALID": True, "RTISA_SOURCE_FREQUENCY_UNSUPPORTED": True,
    "RTISA_NATIVE_INCOME_BASIS_UNKNOWN": True, "RTISA_SOURCE_START_DATE_MISSING": True,
    "RTISA_SOURCE_CONTINUATION_UNRESOLVED": True, "RTISA_SOURCE_END_DATE_MISSING": True,
    "RTISA_SOURCE_DATE_RANGE_INVALID": True, "RTISA_SOURCE_IDENTITY_AMBIGUOUS": True,
    "RTISA_DUPLICATE_COLLISION_UNRESOLVED": True, "RTISA_SOURCE_UNIVERSE_INCOMPLETE": True,
    "RTISA_FUTURE_SOURCE": True, "RTISA_ENDED_SOURCE": True,
    "RTISA_SAME_CANONICAL_PENSION": True,
}
RTICB = {
    "RTICB_REQUEST_SCHEMA_INVALID": False, "RTICB_CLIENT_ID_INVALID": False,
    "RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID": False,
    "RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID": False,
    "RTICB_REQUIRES_FRESH_TRANSACTION": True, "RTICB_UNSUPPORTED_DATABASE": True,
    "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID": True,
    "RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID": True,
    "RTICB_TARGET_AUTHORITY_UNAVAILABLE": True, "RTICB_TARGET_AUTHORITY_NOT_READY": True,
    "RTICB_RTISA_AUTHORITY_SCHEMA_INVALID": True,
    "RTICB_RTISA_AUTHORITY_FINGERPRINT_INVALID": True,
    "RTICB_RTISA_AUTHORITY_UNAVAILABLE": True, "RTICB_RTISA_AUTHORITY_NOT_READY": True,
    "RTICB_CLIENT_ID_MISMATCH": True, "RTICB_PLANNING_IDENTITY_MISMATCH": True,
    "RTICB_RETIREMENT_TARGET_DATE_MISMATCH": True, "RTICB_SOURCE_UNIVERSE_INVALID": True,
    "RTICB_SOURCE_COVERAGE_MISMATCH": True, "RTICB_SOURCE_BASIS_EVIDENCE_INVALID": True,
}


def test_exact_97_code_reconciliation_is_closed_and_partitioned():
    groups = (PLANNING, RIT, RTISA, RTICB)
    assert [len(group) for group in groups] == [18, 29, 30, 20]
    assert len(set().union(*groups)) == 97
    assert [sum(group.values()) for group in groups] == [10, 19, 28, 16]
    assert sum(sum(group.values()) for group in groups) == 73
    assert sum(sum(not reached for reached in group.values()) for group in groups) == 24
    assert sum(PLANNING.values()) + sum(RIT.values()) + sum(RTICB.values()) == 45
    assert sum(RTISA.values()) == 28


def _session_override(engine):
    def dependency():
        with Session(engine) as db:
            yield db
    return dependency


def _context(engine):
    app.dependency_overrides[get_db] = _session_override(engine)
    try:
        response = TestClient(app).get("/api/clients/1/retirement-income-readiness/context")
    finally:
        app.dependency_overrides.clear()
    return response


def _assert_transport(response, status, code, fields=()):
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["field_paths"] == list(fields)
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    assert set(response.json()) == {"schema_version", "request_id", "code", "message", "field_paths"}


def test_context_reaches_fresh_transaction_guard_with_exact_transport(engine):
    def dependency():
        with Session(engine) as db:
            db.begin()
            yield db
    app.dependency_overrides[get_db] = dependency
    try:
        response = TestClient(app).get("/api/clients/1/retirement-income-readiness/context")
    finally:
        app.dependency_overrides.clear()
    _assert_transport(response, 409, "SNAPSHOT_REQUIRES_FRESH_TRANSACTION")


def test_context_reaches_resolution_ownership_guard(engine):
    choose(engine)
    with Session(engine) as db, db.begin():
        row = RecurringIncome(
            client_id=1, income_category="pension", description="ownership",
            amount=Decimal("1.00"), amount_basis="gross", frequency="monthly",
            continuation_status="ongoing", lifecycle_status="current", start_date=date(2020, 1, 1),
        )
        db.add(row); db.flush()
        db.add(PensionIncomeResolution(
            income_id=row.id, client_id=2, version=1, decision_kind="MISCLASSIFIED_GENERAL_INCOME",
            income_fingerprint="a" * 64, canonical_source_id=None, canonical_fingerprint=None,
            reference="test", actor="planner:test",
        ))
    _assert_transport(_context(engine), 409, "RESOLUTION_OWNERSHIP_INVALID")


@pytest.mark.parametrize(
    "side,expected,monthly_entered",
    [("numerator", "PERSISTED_CONVERSION_RATIO_INVALID", True),
     ("denominator", "SOURCE_STRUCTURE_INVALID", False)],
)
def test_persisted_ratio_numerator_and_denominator_have_distinct_producer_boundaries(
    engine, monkeypatch, side, expected, monthly_entered
):
    batch, converted, destination, trace, event = conversion_arguments(engine)
    calls = []
    original = monthly_basis.conversion

    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(monthly_basis, "conversion", observed)
    with pytest.raises(PensionProductError) as failure:
        if side == "numerator":
            destination["monthly_numerator"] = "0"
            observed(AuditSession([event]), 1, batch, converted, destination, trace)
        else:
            # This is the exact earlier adapter invariant: the monthly producer
            # is not entered when the persisted denominator is non-positive.
            snapshot_service.number(Decimal("0"), positive=True)
    assert failure.value.code == expected
    assert bool(calls) is monthly_entered


def test_all_eight_planning_preemptions_are_backed_by_live_schema_query_invariants():
    assert set(code for code, reached in PLANNING.items() if not reached) == {
        "TARGET_REFERENCE_STRUCTURE_INVALID", "BASIS_SOURCE_STRUCTURE_INVALID",
        "BASIS_SOURCE_OWNERSHIP_INVALID", "BASIS_SOURCE_NOT_CURRENT",
        "CONVERSION_EFFECTIVE_DATE_MISSING", "TEMPORAL_SOURCE_OWNERSHIP_INVALID",
        "TEMPORAL_SOURCE_NOT_CURRENT", "TEMPORAL_SOURCE_NOT_FOUND",
    }
    assert batches.c.effective_date.nullable is False
    assert pensions.c.effective_date.nullable is False
    assert pensions.c.conversion_id.nullable is False
    assert pensions.c.conversion_id.unique is True
    assert conversions.c.client_id.nullable is False and pensions.c.client_id.nullable is False
    assert len(retirement_target_service.canonical_references([
        {"reference_id": "client:1:date"}, {"reference_id": "timing:1:date"},
    ])) == 2
    snapshot_source = getsource(planning_input_service._snapshot)
    assert "Manual.client_id == client_id" in snapshot_source
    assert "Manual.lifecycle_status == \"current\"" in snapshot_source
    assert "p[\"status\"] != \"active\"" in snapshot_source
    assert "pension_rows" in snapshot_source and "pensions.c.client_id == client_id" in snapshot_source


@pytest.mark.parametrize("group,expected", [
    ("payable_current", ["RTISA_PENSION_SOURCE_NOT_READY"]),
    ("unresolved", ["RTISA_PENSION_APPLICABILITY_UNRESOLVED", "RTISA_PENSION_SOURCE_NOT_READY"]),
])
def test_rtisa_pension_readiness_observations_are_produced_by_actual_classifier(group, expected):
    source = {
        "source_id": "manual:1", "source_fingerprint": "1" * 64,
        "pension_start_date": "2030-01-01", "tax_treatment": "taxable",
    }
    blocked_execution = {
        "result_state": "block_no_result", "source_result_fingerprint": "2" * 64,
        "currency": "ILS", "temporal_authority_kind": None, "temporal_origin_date": None,
        "annual_rate": None,
    }
    entry = rtisa_service._pension_entry(source, blocked_execution, group)
    assert entry["admission_state"] == "UNRESOLVED"
    assert entry["reason_codes"] == expected


def test_rtisa_unresolved_pension_identity_is_produced_and_consumed_by_rticb(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        db.add(RecurringIncome(
            client_id=1, income_category="pension", description="unresolved pension identity",
            amount=Decimal("1000.00"), amount_basis="gross", frequency="monthly",
            continuation_status="ongoing", lifecycle_status="current", source_status="planner entered",
            verification_state="reviewed", start_date=date(2020, 1, 1),
        ))
    admission = _read(engine, _authority(engine))
    assert admission["source_entries"][0]["reason_codes"] == ["RTISA_SOURCE_IDENTITY_UNRESOLVED"]
    assert admission["blockers"] == [
        "RTISA_SOURCE_IDENTITY_UNRESOLVED", "RTISA_SOURCE_UNIVERSE_INCOMPLETE"
    ]
    comparison_entry = _entry(admission="UNRESOLVED")
    comparison_entry["reason_codes"] = ["RTISA_SOURCE_IDENTITY_UNRESOLVED"]
    result, _, _ = _run(
        monkeypatch,
        rtisa=_rtisa([comparison_entry], completeness="PARTIAL", readiness="NOT_READY", ready=False),
    )
    assert result["result_state"] == "block_no_result"
    assert result["failure_detail_code"] == "RTICB_RTISA_AUTHORITY_NOT_READY"


TARGET_BODY = {
    "expected_record_version": 0,
    "expected_planning_calculation_input_fingerprint": "a" * 64,
    "expected_retirement_target_date": "2035-04-01",
    "monthly_amount": "1000", "income_basis": "GROSS",
    "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
    "source_kind": "PLANNER_SUPPLIED",
}


class _UntouchedDB:
    def rollback(self):
        pass


def _without_database():
    def dependency():
        yield _UntouchedDB()
    return dependency


def _production_client():
    config = _production_config()
    production_app = create_app(config)
    production_app.dependency_overrides[get_db] = _without_database()
    token, payload = issue(config)
    client = TestClient(production_app)
    client.cookies.set(COOKIE_NAME, token)
    headers = _edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": payload["csrf"]})
    return production_app, client, headers


@pytest.mark.parametrize("change,expected_path", [
    ({"unexpected": True}, "/unexpected"),
    ({"monthly_amount": None}, "/monthly_amount"),
    ({"income_basis": None}, "/income_basis"),
    ({"income_basis": "gross"}, "/income_basis"),
    ({"price_basis": None}, "/price_basis"),
    ({"price_basis": "nominal"}, "/price_basis"),
    ({"price_reference_date": "2025-99-99"}, "/price_reference_date"),
])
def test_rit_dto_preemptions_reject_before_producer_entry(monkeypatch, change, expected_path):
    monkeypatch.setattr(routes.target_service, "confirm", lambda *_: pytest.fail("RIT producer entered"))
    body = {**TARGET_BODY, **change}
    production_app, client, headers = _production_client()
    response = client.put("/api/clients/1/retirement-income-readiness/target", json=body, headers=headers)
    production_app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_SCHEMA_INVALID"
    assert expected_path in response.json()["field_paths"]
    assert response.headers["cache-control"] == "no-store, private"


@pytest.mark.parametrize("path,body,expected_path", [
    ("/api/clients/0/retirement-income-readiness/comparison", {
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01"}, "/path/client_id"),
    ("/api/clients/1/retirement-income-readiness/comparison", {
        "expected_planning_calculation_input_fingerprint": "bad",
        "expected_retirement_target_date": "2035-04-01"},
     "/expected_planning_calculation_input_fingerprint"),
    ("/api/clients/1/retirement-income-readiness/comparison", {
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "bad"}, "/expected_retirement_target_date"),
    ("/api/clients/1/retirement-income-readiness/comparison", {
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01", "client_id": 1}, "/client_id"),
])
def test_rtisa_rticb_request_preemptions_reject_before_producer_entry(
    monkeypatch, path, body, expected_path
):
    monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: pytest.fail("RTICB producer entered"))
    production_app, client, headers = _production_client()
    response = client.post(path, json=body, headers=headers)
    production_app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_SCHEMA_INVALID"
    assert expected_path in response.json()["field_paths"]
    assert response.headers["cache-control"] == "no-store, private"
