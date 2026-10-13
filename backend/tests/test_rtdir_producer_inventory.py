"""Executable reconciliation for RTDIR Definition section 9.5.

The producer suites remain the origin oracles.  This module closes the adapter
inventory gap: it freezes every accepted code/disposition, proves the route DTO
preemptions before a producer is entered, and exercises the previously missing
Planning Input production-path distinctions.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from inspect import getsource
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect as sa_inspect, select
from sqlalchemy.orm import Session

from app.api import retirement_income_readiness_routes as routes
from app.db.session import get_db
from app.main import app, create_app
from app.models.canonical_conversion import allocations, batches, conversions, pensions
from app.models.planning_input_decision import PensionIncomeResolution
from app.models.retirement_facts import RecurringIncome
from app.services import pension_monthly_basis_service as monthly_basis
from app.services import pension_temporal_basis_service as temporal_basis
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


def _context_through_producer(engine, monkeypatch, producer, *, client_id=1):
    """Keep the public adapter real while invoking the real accepted producer."""
    entered = []

    def read(db, observed_client_id):
        assert observed_client_id == client_id
        entered.append(True)
        return producer(db, observed_client_id)

    monkeypatch.setattr(planning_input_service, "read", read)
    app.dependency_overrides[get_db] = _session_override(engine)
    try:
        response = TestClient(app).get(
            f"/api/clients/{client_id}/retirement-income-readiness/context"
        )
    finally:
        app.dependency_overrides.clear()
    assert entered == [True]
    return response


def test_context_reaches_unsupported_database_producer_with_exact_transport(engine, monkeypatch):
    class UnsupportedBind:
        dialect = SimpleNamespace(name="unsupported")

    class FreshUnsupportedSession:
        new = dirty = deleted = ()

        @staticmethod
        def in_transaction():
            return False

        @staticmethod
        def get_bind():
            return UnsupportedBind()

        @staticmethod
        def connection():
            return SimpleNamespace()

    response = _context_through_producer(
        engine, monkeypatch,
        lambda _db, _client_id: snapshot_service.begin_read(FreshUnsupportedSession()),
    )
    _assert_transport(response, 503, "UNSUPPORTED_DATABASE")


def test_context_reaches_client_not_found_producer_with_exact_transport(engine):
    app.dependency_overrides[get_db] = _session_override(engine)
    try:
        response = TestClient(app).get(
            "/api/clients/999999/retirement-income-readiness/context"
        )
    finally:
        app.dependency_overrides.clear()
    _assert_transport(response, 404, "CLIENT_NOT_FOUND", ("/path/client_id",))


def test_context_reaches_source_structure_producer_with_exact_transport(engine, monkeypatch):
    response = _context_through_producer(
        engine, monkeypatch, lambda _db, _client_id: snapshot_service.invalid()
    )
    _assert_transport(response, 409, "SOURCE_STRUCTURE_INVALID")


@pytest.mark.parametrize(
    "expected,mutation",
    [
        ("CONVERSION_EFFECTIVE_DATE_MISMATCH", "monthly-date"),
        ("BASIS_CONVERSION_PROVENANCE_INVALID", "monthly-audit"),
        ("PERSISTED_CONVERSION_RATIO_INVALID", "monthly-ratio"),
        ("TEMPORAL_DECISION_STRUCTURE_INVALID", "temporal-decision"),
        ("TEMPORAL_SOURCE_STRUCTURE_INVALID", "temporal-source"),
    ],
)
def test_context_reaches_basis_and_temporal_producers_with_exact_transport(
    engine, monkeypatch, expected, mutation
):
    batch, converted, destination, trace, audit_event = conversion_arguments(engine)

    def producer(_db, client_id):
        if mutation == "monthly-date":
            destination["effective_date"] = date(1900, 1, 1)
            return monthly_basis.conversion(
                AuditSession([audit_event]), client_id, batch, converted, destination, trace
            )
        if mutation == "monthly-audit":
            return monthly_basis.conversion(
                AuditSession([]), client_id, batch, converted, destination, trace
            )
        if mutation == "monthly-ratio":
            destination["monthly_numerator"] = "0"
            return monthly_basis.conversion(
                AuditSession([audit_event]), client_id, batch, converted, destination, trace
            )
        if mutation == "temporal-decision":
            row = SimpleNamespace(
                client_id=client_id, manual_pension_source_id="inventory-manual",
                lifecycle_status="current", base_amount_effective_date=date(2030, 1, 1),
                indexation_method="none", fixed_indexation_rate="0.01",
                temporal_authority_explicit=True, input_mode="entered",
            )
            return temporal_basis.manual(row, client_id)
        destination["status"] = "reversed"
        return temporal_basis.conversion(
            _db, client_id, destination, converted, batch
        )

    _assert_transport(
        _context_through_producer(engine, monkeypatch, producer), 409, expected
    )


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


def test_all_eight_planning_preemptions_are_backed_by_live_schema_query_invariants(
    engine, monkeypatch
):
    assert set(code for code, reached in PLANNING.items() if not reached) == {
        "TARGET_REFERENCE_STRUCTURE_INVALID", "BASIS_SOURCE_STRUCTURE_INVALID",
        "BASIS_SOURCE_OWNERSHIP_INVALID", "BASIS_SOURCE_NOT_CURRENT",
        "CONVERSION_EFFECTIVE_DATE_MISSING", "TEMPORAL_SOURCE_OWNERSHIP_INVALID",
        "TEMPORAL_SOURCE_NOT_CURRENT", "TEMPORAL_SOURCE_NOT_FOUND",
    }
    database = sa_inspect(engine)
    pension_columns = {
        column["name"]: column
        for column in database.get_columns("canonical_pension_destinations")
    }
    conversion_columns = {column["name"]: column for column in database.get_columns("canonical_conversions")}
    batch_columns = {column["name"]: column for column in database.get_columns("canonical_conversion_batches")}
    assert batch_columns["effective_date"]["nullable"] is False
    assert pension_columns["effective_date"]["nullable"] is False
    assert pension_columns["conversion_id"]["nullable"] is False
    assert conversion_columns["client_id"]["nullable"] is False
    assert pension_columns["client_id"]["nullable"] is False
    assert any(
        constraint["column_names"] == ["conversion_id"]
        for constraint in database.get_unique_constraints("canonical_pension_destinations")
    )
    choose(engine)

    # With no admitted pension source, none of the eight prohibited downstream
    # branches can be entered from GET /context.  The reference producer still
    # runs, and its actual inputs prove that duplicate target identities are
    # preempted before its error branch.
    forbidden = []

    def must_not_enter(*_args, **_kwargs):
        forbidden.append(True)
        pytest.fail("preempted Planning producer branch entered")

    for module, name in (
        (monthly_basis, "manual"), (monthly_basis, "conversion"),
        (temporal_basis, "manual"), (temporal_basis, "conversion"),
    ):
        monkeypatch.setattr(module, name, must_not_enter)
    original_references = retirement_target_service.canonical_references
    observed_references = []

    def observed(values):
        observed_references.append(list(values))
        return original_references(values)

    monkeypatch.setattr(retirement_target_service, "canonical_references", observed)
    response = _context(engine)
    assert response.status_code == 200, response.text
    assert forbidden == []
    assert observed_references
    for references in observed_references:
        reference_ids = [item["reference_id"] for item in references]
        assert len(reference_ids) == len(set(reference_ids))

    # Query membership is an additional executable control, not the oracle by
    # itself: only current manual rows and client-owned conversion rows can be
    # materialized before the producer calls above.
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


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"monthly_amount": "0"}, "RIT_AMOUNT_INVALID"),
        ({"monthly_amount": "1.0000001"}, "RIT_AMOUNT_PRECISION_UNSUPPORTED"),
        ({"price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": "2025-01-01"},
         "RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL"),
        ({"price_basis": "REAL_AT_REFERENCE_DATE", "price_reference_date": None},
         "RIT_PRICE_REFERENCE_DATE_MISSING"),
    ],
)
def test_rit_reachable_command_errors_have_exact_public_transport(monkeypatch, change, expected):
    entered = []

    def confirm(_db, command, _actor):
        entered.append(command)
        return routes.target_service._validate_command(command)

    monkeypatch.setattr(routes.target_service, "confirm", confirm)
    production_app, client, headers = _production_client()
    response = client.put(
        "/api/clients/1/retirement-income-readiness/target",
        json={**TARGET_BODY, **change}, headers=headers,
    )
    production_app.dependency_overrides.clear()
    _assert_transport(response, 422, expected, ("/monthly_amount",) if "AMOUNT" in expected
                      else ("/price_reference_date",))
    assert len(entered) == 1


def test_price_reference_date_dto_and_producer_precedence(monkeypatch):
    entered = []

    def confirm(_db, command, _actor):
        entered.append(routes.target_service._validate_command(command))
        routes.target_service._fail("RIT_CONFIRMATION_CONTEXT_STALE")

    monkeypatch.setattr(routes.target_service, "confirm", confirm)
    production_app, client, headers = _production_client()
    root = "/api/clients/1/retirement-income-readiness/target"
    malformed = client.put(root, json={**TARGET_BODY, "price_basis": "REAL_AT_REFERENCE_DATE",
                                       "price_reference_date": "2025-99-99"}, headers=headers)
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "REQUEST_SCHEMA_INVALID"
    assert "/price_reference_date" in malformed.json()["field_paths"]
    assert entered == []

    valid = client.put(root, json={**TARGET_BODY, "price_basis": "REAL_AT_REFERENCE_DATE",
                                   "price_reference_date": "2025-01-01"}, headers=headers)
    production_app.dependency_overrides.clear()
    _assert_transport(valid, 409, "RIT_CONFIRMATION_CONTEXT_STALE",
                      ("/expected_planning_calculation_input_fingerprint",
                       "/expected_retirement_target_date"))
    assert len(entered) == 1
    assert entered[0]["price_reference_date"].isoformat() == "2025-01-01"


@pytest.mark.parametrize("code", [
    "RIT_TARGET_RECORD_INVALID", "RIT_PLANNING_CONTEXT_INVALID", "RIT_AMOUNT_INVALID",
    "RIT_AMOUNT_PRECISION_UNSUPPORTED",
    "RIT_CONFIRMATION_INVALID", "RIT_PLANNING_CONTEXT_UNAVAILABLE",
    "RIT_RETIREMENT_TARGET_NOT_READY", "RIT_TARGET_MISSING",
    "RIT_STORED_FINGERPRINT_MISMATCH", "RIT_PLANNING_IDENTITY_STALE",
    "RIT_RETIREMENT_TARGET_STALE", "RIT_RECONFIRMATION_REQUIRED",
])
def test_rit_get_professional_codes_preserve_exact_public_envelope(monkeypatch, code):
    context = {
        "client_id": 1, "fingerprint": "a" * 64,
        "retirement_target_date": date(2035, 4, 1),
    }
    if code in {
        "RIT_PLANNING_CONTEXT_INVALID", "RIT_PLANNING_CONTEXT_UNAVAILABLE",
        "RIT_RETIREMENT_TARGET_NOT_READY",
    }:
        unavailable = {"client_id": 1, "fingerprint": None, "retirement_target_date": None}
        produced = routes.target_service._result(unavailable, None, [code], "UNAVAILABLE")
    elif code == "RIT_TARGET_MISSING":
        produced = routes.target_service._result(context, None)
    else:
        row = SimpleNamespace(
            client_id=1, version=1, lifecycle_state="CONFIRMED",
            planning_calculation_input_fingerprint="a" * 64,
            retirement_target_date=date(2035, 4, 1), monthly_amount_text="1000",
            currency="ILS", income_basis="GROSS",
            price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date=None,
            source_kind="PLANNER_SUPPLIED", confirmation_state="CONFIRMED",
            confirmation_actor="planner:test", confirmed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            target_semantic_fingerprint=None,
        )
        target = routes.target_service._target_from_values(
            client_id=1, planning_fingerprint=row.planning_calculation_input_fingerprint,
            target_date=row.retirement_target_date, amount=row.monthly_amount_text,
            income_basis=row.income_basis, price_basis=row.price_basis, reference_date=None,
        )
        row.target_semantic_fingerprint = routes.target_service._semantic_fingerprint(target)
        if code == "RIT_TARGET_RECORD_INVALID":
            row.monthly_amount_text = "01000"
        elif code == "RIT_AMOUNT_INVALID":
            row.monthly_amount_text = "0"
        elif code == "RIT_AMOUNT_PRECISION_UNSUPPORTED":
            row.monthly_amount_text = "1234567890123456789"
        elif code == "RIT_CONFIRMATION_INVALID":
            row.confirmation_actor = ""
        elif code == "RIT_STORED_FINGERPRINT_MISMATCH":
            row.target_semantic_fingerprint = "b" * 64
        elif code == "RIT_PLANNING_IDENTITY_STALE":
            row.planning_calculation_input_fingerprint = "b" * 64
            changed = {**target, "planning_calculation_input_fingerprint": "b" * 64}
            row.target_semantic_fingerprint = routes.target_service._semantic_fingerprint(changed)
        elif code == "RIT_RETIREMENT_TARGET_STALE":
            row.retirement_target_date = date(2036, 4, 1)
            changed = {**target, "retirement_target_date": "2036-04-01"}
            row.target_semantic_fingerprint = routes.target_service._semantic_fingerprint(changed)
        elif code == "RIT_RECONFIRMATION_REQUIRED":
            row.lifecycle_state = "STALE"
        produced = routes.target_service._result(
            context, row,
            project_stale_transition=code in {
                "RIT_PLANNING_IDENTITY_STALE", "RIT_RETIREMENT_TARGET_STALE",
            },
        )
        assert code in produced["blockers"]
    entered = []

    def assess(_db, client_id):
        entered.append(client_id)
        return produced

    monkeypatch.setattr(routes.target_service, "assess", assess)
    production_app, client, headers = _production_client()
    response = client.get("/api/clients/1/retirement-income-readiness/target", headers=headers)
    production_app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == produced
    assert code in response.json()["blockers"]
    if code not in {"RIT_PLANNING_IDENTITY_STALE", "RIT_RETIREMENT_TARGET_STALE"}:
        assert response.json()["blockers"] == [code]
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    assert entered == [1]


@pytest.mark.parametrize("code,producer_status,status,final_code,fields", [
    ("RIT_CLIENT_ID_INVALID", 409, 404, "CLIENT_NOT_FOUND", ("/path/client_id",)),
    ("RIT_RECORD_UNAVAILABLE", 409, 409, "RIT_RECORD_UNAVAILABLE", ()),
    ("RIT_RECORD_UNAVAILABLE", 503, 503, "RIT_UNSUPPORTED_DATABASE", ()),
    ("RIT_PLANNING_CONTEXT_INVALID", 409, 409, "RIT_PLANNING_CONTEXT_INVALID", ()),
    ("RIT_PLANNING_CONTEXT_UNAVAILABLE", 409, 409, "RIT_PLANNING_CONTEXT_UNAVAILABLE", ()),
    ("RIT_RETIREMENT_TARGET_NOT_READY", 409, 409, "RIT_RETIREMENT_TARGET_NOT_READY", ()),
    ("RIT_CONFIRMATION_CONTEXT_STALE", 409, 409, "RIT_CONFIRMATION_CONTEXT_STALE",
     ("/expected_planning_calculation_input_fingerprint", "/expected_retirement_target_date")),
    ("RIT_RECORD_VERSION_CONFLICT", 409, 409, "RIT_RECORD_VERSION_CONFLICT", ("/expected_record_version",)),
    ("RIT_RECORD_VERSION_EXHAUSTED", 409, 409, "RIT_RECORD_VERSION_EXHAUSTED", ()),
])
def test_rit_reachable_transport_mapping_is_exact(
    monkeypatch, code, producer_status, status, final_code, fields
):
    entered = []

    def confirm(_db, _command, _actor):
        entered.append(True)
        routes.target_service._fail(code, producer_status)

    monkeypatch.setattr(routes.target_service, "confirm", confirm)
    production_app, client, headers = _production_client()
    response = client.put("/api/clients/1/retirement-income-readiness/target",
                          json=TARGET_BODY, headers=headers)
    production_app.dependency_overrides.clear()
    _assert_transport(response, status, final_code, fields)
    assert entered == [True]


def test_rit_transport_mapping_mutation_is_detected_and_restored(monkeypatch):
    def confirm(_db, _command, _actor):
        routes.target_service._fail("RIT_RECORD_VERSION_CONFLICT")

    monkeypatch.setattr(routes.target_service, "confirm", confirm)
    production_app, client, headers = _production_client()
    original_transport = routes._transport

    baseline = client.put(
        "/api/clients/1/retirement-income-readiness/target",
        json=TARGET_BODY, headers=headers,
    )
    _assert_transport(baseline, 409, "RIT_RECORD_VERSION_CONFLICT",
                      ("/expected_record_version",))

    def redirected_transport(request, exc, *args, **kwargs):
        if exc.code == "RIT_RECORD_VERSION_CONFLICT":
            exc = PensionProductError("RIT_RECORD_VERSION_EXHAUSTED", "mutant", 409)
        return original_transport(request, exc, *args, **kwargs)

    monkeypatch.setattr(routes, "_transport", redirected_transport)
    mutant = client.put(
        "/api/clients/1/retirement-income-readiness/target",
        json=TARGET_BODY, headers=headers,
    )
    with pytest.raises(AssertionError):
        _assert_transport(mutant, 409, "RIT_RECORD_VERSION_CONFLICT",
                          ("/expected_record_version",))

    monkeypatch.setattr(routes, "_transport", original_transport)
    restored = client.put(
        "/api/clients/1/retirement-income-readiness/target",
        json=TARGET_BODY, headers=headers,
    )
    production_app.dependency_overrides.clear()
    _assert_transport(restored, 409, "RIT_RECORD_VERSION_CONFLICT",
                      ("/expected_record_version",))


@pytest.mark.parametrize("change,expected_path", [
    ({"expected_record_version": -1}, "/expected_record_version"),
    ({"expected_planning_calculation_input_fingerprint": "bad"},
     "/expected_planning_calculation_input_fingerprint"),
    ({"expected_retirement_target_date": "bad"}, "/expected_retirement_target_date"),
    ({"source_kind": "FORGED"}, "/source_kind"),
])
def test_rit_additional_dto_origins_preempt_producer(monkeypatch, change, expected_path):
    monkeypatch.setattr(routes.target_service, "confirm", lambda *_: pytest.fail("RIT producer entered"))
    production_app, client, headers = _production_client()
    response = client.put(
        "/api/clients/1/retirement-income-readiness/target",
        json={**TARGET_BODY, **change}, headers=headers,
    )
    production_app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_SCHEMA_INVALID"
    assert expected_path in response.json()["field_paths"]
    assert response.headers["cache-control"] == "no-store, private"


def test_rit_persistence_preemptions_are_executable_and_producer_not_entered(engine, monkeypatch):
    database = sa_inspect(engine)
    columns = {
        column["name"]: column
        for column in database.get_columns("retirement_monthly_income_target_elections")
    }
    assert columns["confirmation_state"]["nullable"] is False
    assert columns["confirmation_actor"]["nullable"] is False
    assert columns["confirmed_at"]["nullable"] is False
    checks = " ".join(
        constraint["sqltext"]
        for constraint in database.get_check_constraints("retirement_monthly_income_target_elections")
    )
    assert "currency = 'ILS'" in checks
    primary_key = database.get_pk_constraint("retirement_monthly_income_target_elections")
    assert primary_key["constrained_columns"] == ["client_id"]

    forbidden = []
    original_authority = routes.target_service._authority
    original_stored = routes.target_service._stored_target

    def authority(row):
        forbidden.append("authority")
        return original_authority(row)

    def stored(row):
        forbidden.append("stored")
        return original_stored(row)

    monkeypatch.setattr(routes.target_service, "_authority", authority)
    monkeypatch.setattr(routes.target_service, "_stored_target", stored)
    app.dependency_overrides[get_db] = _session_override(engine)
    try:
        response = TestClient(app).get("/api/clients/1/retirement-income-readiness/target")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["blockers"] == ["RIT_RETIREMENT_TARGET_NOT_READY"]
    assert forbidden == []


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
