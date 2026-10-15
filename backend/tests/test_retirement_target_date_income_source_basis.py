from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import RecurringIncome
from app.models.retirement_income_source_basis import RetirementTargetDateIncomeSourceBasisDecision
from app.main import app
from app.db.session import get_db
from app.schemas.retirement_income_source_basis import CRTISBACommand
from app.services import planning_input_service
from app.services import canonical_manual_pension_service
from app.services import retirement_target_date_income_source_basis_service as subject
from test_recovery_pension_products import engine
from test_professional_source_snapshot import facts

H = "a" * 64
_PRODUCTION_BEGIN = subject._begin


@pytest.fixture(autouse=True)
def sqlite_transaction_adapter(monkeypatch):
    """SQLite is used only as a pure deterministic service/DTO oracle here."""
    monkeypatch.setattr(subject, "_begin", lambda db, *, write: db.begin())


def _authority(engine):
    with Session(engine) as db, db.begin():
        db.add(PlanningInputDecision(
            client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 1), retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint=H, actor="planner:test",
        ))
        db.add(RecurringIncome(
            client_id=1, income_category="rental", description="rent", amount=Decimal("1200.00"),
            amount_basis="gross", frequency="monthly", continuation_status="ongoing",
            lifecycle_status="current", source_status="planner entered", verification_state="reviewed",
            start_date=date(2025, 1, 1),
        ))


def _read(engine):
    with Session(engine) as db:
        return subject.read(db, 1)


def _command(entry, *, operation="CLASSIFY", price="NOMINAL_AT_RETIREMENT_TARGET_DATE"):
    body = {
        "schema_version": f"CRTISBA_RECURRING_{operation}_COMMAND_V1",
        "operation": operation, "source_kind": "RECURRING_INCOME",
        "expected_decision_version": entry["decision_version"] or 0,
        "expected_planning_calculation_input_fingerprint": _CURRENT_PLANNING,
        "expected_source_version": entry["source_version"],
        "expected_source_fingerprint": entry["source_fingerprint"],
        "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"],
    }
    if operation == "CLASSIFY":
        body.update(price_basis=price, price_reference_date="2026-01-01" if price == "REAL_AT_REFERENCE_DATE" else None)
    return TypeAdapter(CRTISBACommand).validate_python(body)


def test_empty_universe_is_ready_and_read_owns_no_commit(engine):
    with Session(engine) as db, db.begin():
        db.add(PlanningInputDecision(client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 1), retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint=H, actor="planner:test"))
    result = _read(engine)
    assert result["schema_version"] == "CRTISBA_COLLECTION_RESULT_V1"
    assert result["source_basis_entries"] == []
    assert result["basis_ready"] is True and result["blockers"] == []
    assert set(result["partitions"]) == set(subject.PARTITION_STATES.values())


def test_recurring_classify_clear_append_only_and_exact_bindings(engine):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    entry = initial["source_basis_entries"][0]
    assert entry["source_id"] == "income:1" and entry["decision_state"] == "MISSING"
    assert entry["income_basis"] == "GROSS" and entry["price_basis"] == "UNKNOWN"
    with Session(engine) as db:
        result = subject.write(db, 1, "income:1", _command(entry), "authenticated-professional")
    assert result["decision_version"] == 1 and result["decision_state"] == "CURRENT"
    after = _read(engine)
    current = after["source_basis_entries"][0]
    assert current["decision_state"] == "CURRENT"
    assert current["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
    with Session(engine) as db:
        cleared = subject.write(db, 1, "income:1", _command(current, operation="CLEAR"), "authenticated-professional")
    assert cleared["decision_version"] == 2 and cleared["decision_state"] == "UNKNOWN"
    final = _read(engine)["source_basis_entries"][0]
    assert final["decision_state"] == "UNKNOWN" and final["price_basis"] == "UNKNOWN"
    with Session(engine) as db:
        rows = list(db.scalars(select(RetirementTargetDateIncomeSourceBasisDecision).order_by(
            RetirementTargetDateIncomeSourceBasisDecision.decision_version)))
    assert [row.decision_version for row in rows] == [1, 2]
    assert all(row.decision_actor == "authenticated-professional" for row in rows)
    assert rows[0].recurring_source_version_fingerprint == rows[0].source_fingerprint


def test_pension_od1_is_stored_and_od2_is_result_only(engine):
    with Session(engine) as db, db.begin():
        source = canonical_manual_pension_service.create(db, 1, facts(
            monthly_amount="5000.00", pension_start_date=date(2025, 1, 1),
            base_amount_effective_date=date(2025, 1, 1), tax_treatment="taxable",
        ))
        db.add(PlanningInputDecision(client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 1), retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint=H, actor="planner:test"))
    initial = _read(engine)
    source_id = f"manual:{source['manual_pension_source_id']}"
    entry = next(item for item in initial["source_basis_entries"] if item["source_id"] == source_id)
    assert entry["amount_authority_fingerprint"] is not None, entry
    assert entry["decision_state"] == "MISSING" and isinstance(entry["source_version"], int)
    assert entry["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
    body = {
        "schema_version": "CRTISBA_PENSION_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
        "source_kind": "PENSION", "expected_decision_version": 0,
        "expected_planning_calculation_input_fingerprint": initial["planning_calculation_input_fingerprint"],
        "expected_source_version": entry["source_version"], "expected_source_fingerprint": entry["source_fingerprint"],
        "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"], "income_basis": "NET",
    }
    command = TypeAdapter(CRTISBACommand).validate_python(body)
    with Session(engine) as db:
        result = subject.write(db, 1, source_id, command, "authenticated-professional")
    assert result["income_basis"] == "NET"
    assert result["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
    assert result["price_basis_provenance"] == "OWNER_DECISION_OD2"
    current = next(item for item in _read(engine)["source_basis_entries"] if item["source_id"] == source_id)
    assert current["income_basis"] == "NET"
    assert current["price_basis"] == "NOMINAL_AT_RETIREMENT_TARGET_DATE"
    assert current["price_basis_provenance"] == "OWNER_DECISION_OD2"
    with Session(engine) as db:
        row = db.scalar(select(RetirementTargetDateIncomeSourceBasisDecision))
    assert row.price_basis is row.price_reference_date is row.price_basis_provenance is None
    assert '"price_basis":null' in subject.canonical_json(subject._decision_preimage(subject._row_values(row)))


@pytest.mark.parametrize("price,reference", [
    ("NOMINAL_AT_RETIREMENT_TARGET_DATE", "2026-01-01"),
    ("REAL_AT_REFERENCE_DATE", None),
])
def test_recurring_reference_date_contract_is_strict(price, reference):
    body = {
        "schema_version": "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
        "source_kind": "RECURRING_INCOME", "expected_decision_version": 0,
        "expected_planning_calculation_input_fingerprint": H, "expected_source_version": H,
        "expected_source_fingerprint": H, "expected_amount_authority_fingerprint": H,
        "price_basis": price, "price_reference_date": reference,
    }
    with pytest.raises(ValidationError):
        TypeAdapter(CRTISBACommand).validate_python(body)


@pytest.mark.parametrize("mutation", [
    {"decision_actor": "forged"}, {"price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE"},
    {"expected_source_version": True}, {"unknown": "x"},
])
def test_discriminated_dto_forbids_cross_kind_actor_coercion_and_extra(mutation):
    body = {
        "schema_version": "CRTISBA_PENSION_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
        "source_kind": "PENSION", "expected_decision_version": 0,
        "expected_planning_calculation_input_fingerprint": H, "expected_source_version": 1,
        "expected_source_fingerprint": H, "expected_amount_authority_fingerprint": H,
        "income_basis": "GROSS",
    } | mutation
    with pytest.raises(ValidationError):
        TypeAdapter(CRTISBACommand).validate_python(body)


def test_decision_fingerprint_excludes_actor_time_and_derived_od2():
    values = {
        "client_id": 1, "source_id": "manual:1", "source_kind": "PENSION", "decision_version": 1,
        "planning_calculation_input_fingerprint": H, "source_version": 1, "source_fingerprint": H,
        "amount_authority_fingerprint": H, "income_basis": "GROSS",
        "income_basis_provenance": "EXPLICIT_PROFESSIONAL", "price_basis": None,
        "price_reference_date": None, "price_basis_provenance": None,
    }
    expected = subject.decision_fingerprint(values)
    assert subject.decision_fingerprint(values | {"decision_actor": "other", "decided_at": "tomorrow",
                                                    "derived_od2": "hostile"}) == expected
    assert '"price_basis":null' in subject.canonical_json(subject._decision_preimage(values))


def test_cas_and_forbidden_source_fail_closed(engine):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    entry = initial["source_basis_entries"][0]
    command = _command(entry)
    command.expected_decision_version = 2
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as caught:
        subject.write(db, 1, "income:1", command, "actor")
    assert caught.value.code == "CRTISBA_DECISION_VERSION_CONFLICT"


def test_pristine_session_rejection_precedes_authoritative_derivation(engine, monkeypatch):
    calls = []
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *_: calls.append(True))
    with Session(engine) as db:
        db.begin()
        with pytest.raises(subject.CRTISBAError) as caught:
            subject.read(db, 1)
    assert caught.value.code == "CRTISBA_REQUIRES_FRESH_TRANSACTION" and calls == []


@pytest.mark.parametrize("invalidated,state,constraint,expected", [
    (True, "23505", "uq_crtisba_source_decision_version", "CRTISBA_COMMIT_OUTCOME_UNKNOWN"),
    (False, "08006", "uq_crtisba_source_decision_version", "CRTISBA_COMMIT_OUTCOME_UNKNOWN"),
    (False, "23505", "uq_crtisba_source_decision_version", "CRTISBA_DECISION_VERSION_CONFLICT"),
    (False, "P7501", "trg_crtisba_decision_immutable", "CRTISBA_PERSISTENCE_IMMUTABILITY_VIOLATION"),
    (False, "P7501", "wrong", "CRTISBA_COMMIT_OUTCOME_UNKNOWN"),
])
def test_post_dispatch_classifier_order_is_structured_and_fail_closed(invalidated, state, constraint, expected):
    orig = RuntimeError("message must not classify")
    orig.pgcode = state
    orig.diag = SimpleNamespace(constraint_name=constraint)
    exc = DBAPIError.instance("statement", {}, orig, RuntimeError, connection_invalidated=invalidated)
    assert subject._classify_integrity(exc, "COMMIT_DISPATCHED").code == expected


def test_non_postgresql_public_transaction_owner_is_rejected(engine):
    with Session(engine) as db:
        with pytest.raises(subject.CRTISBAError) as caught:
            _PRODUCTION_BEGIN(db, write=False)
    assert caught.value.code == "CRTISBA_UNSUPPORTED_DATABASE"


def test_amount_authority_binds_raw_source_not_rtisa_display(monkeypatch):
    planning = {"client_id": 1, "general_income_inputs": [{
        "source_id": "income:7", "amount": "1200.00", "amount_basis": "gross", "frequency": "quarterly"
    }], "pension_inputs": []}
    rtisa = {"source_entries": [{"source_id": "income:7", "admission_state": "INCLUDED", "reason_codes": [], "native_amount": {
        "amount": "400.00", "currency": "ILS", "frequency": "MONTHLY"},
        "upstream_identity": {"source_fingerprint": H}}]}
    context = subject._amount_context(planning, {"source_results": [], "source_entry_fingerprints": []}, rtisa)["income:7"]
    expected = subject.fingerprint({"contract": subject.RECURRING_AMOUNT_CONTRACT, "client_id": 1,
        "source_id": "income:7", "source_fingerprint": H, "amount": "1200.00",
        "amount_basis": "gross", "frequency": "quarterly"})
    assert context["amount"] == expected


def test_public_get_put_routes_exact_transport_and_actor_non_forgeability(engine):
    _authority(engine)
    def dependency():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    client = TestClient(app)
    try:
        initial = client.get("/api/clients/1/retirement-income-readiness/source-bases")
        assert initial.status_code == 200
        assert initial.headers["cache-control"] == "no-store, private"
        entry = initial.json()["source_basis_entries"][0]
        body = {
            "schema_version": "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
            "source_kind": "RECURRING_INCOME", "expected_decision_version": 0,
            "expected_planning_calculation_input_fingerprint": initial.json()["planning_calculation_input_fingerprint"],
            "expected_source_version": entry["source_version"], "expected_source_fingerprint": entry["source_fingerprint"],
            "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"],
            "price_basis": "REAL_AT_REFERENCE_DATE", "price_reference_date": "2026-01-01",
        }
        forged = client.put("/api/clients/1/retirement-income-readiness/source-bases/income:1",
                            json=body | {"decision_actor": "forged"})
        assert forged.status_code == 422 and "decision_actor" in str(forged.json())
        written = client.put("/api/clients/1/retirement-income-readiness/source-bases/income:1", json=body)
        assert written.status_code == 200 and written.json()["decision_version"] == 1
        assert "decision_actor" not in written.json() and "decided_at" not in written.json()
        stale = client.put("/api/clients/1/retirement-income-readiness/source-bases/income:1", json=body)
        assert stale.status_code == 409 and stale.json()["code"] == "CRTISBA_DECISION_VERSION_CONFLICT"
        assert stale.json()["field_paths"] == ["/expected_decision_version"]
        missing = client.get("/api/clients/999/retirement-income-readiness/source-bases")
        assert missing.status_code == 404 and missing.json()["code"] == "CLIENT_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("constraint,expected", [
    ("pk_crtisba_decisions", "CRTISBA_PERSISTENCE_IDENTITY_CONFLICT"),
    ("uq_crtisba_source_decision_version", "CRTISBA_DECISION_VERSION_CONFLICT"),
    ("fk_crtisba_decision_client", "CLIENT_NOT_FOUND"),
    *[(name, "CRTISBA_PERSISTENCE_CONTRACT_VIOLATION") for name in sorted(subject.CHECK_CONSTRAINTS)],
])
def test_closed_named_constraint_classifier(constraint, expected):
    state = "23505" if constraint.startswith(("pk_", "uq_")) else "23503" if constraint.startswith("fk_") else "23514"
    orig = RuntimeError("message is deliberately irrelevant")
    orig.pgcode = state
    orig.diag = SimpleNamespace(constraint_name=constraint)
    exc = DBAPIError.instance("statement", {}, orig, RuntimeError, connection_invalidated=False)
    assert subject._classify_integrity(exc, "COMMIT_DISPATCHED").code == expected
    orig.diag = SimpleNamespace(constraint_name="unlisted")
    assert subject._classify_integrity(exc, "COMMIT_DISPATCHED").code == "CRTISBA_COMMIT_OUTCOME_UNKNOWN"


@pytest.mark.parametrize("blocker,stage,code", [
    ("RTISA_SOURCE_UNIVERSE_INVALID", "source_universe", "CRTISBA_SOURCE_UNIVERSE_INVALID"),
    ("RTISA_PENSION_RESULT_INVALID", "pension_result", "CRTISBA_PENSION_RESULT_INVALID"),
])
def test_reachable_no_collection_mapping_and_mapping_mutation(monkeypatch, blocker, stage, code):
    planning = {
        "client_id": 1,
        "planning_calculation_input_fingerprint": H,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [], "general_income_inputs": [],
    }
    rtisa = subject.rtisa_service._empty_result(1, H, "2030-01-01", blocker)
    db = SimpleNamespace(get=lambda *_: object())
    monkeypatch.setattr(subject, "_planning", lambda *_: (planning, None))
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *_: {})
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", lambda *_: rtisa)

    before, _ = subject._derive_snapshot(db, 1, "READ")
    assert (before["failure_stage"], before["failure_detail_code"]) == (stage, code)

    original = subject.NO_COLLECTION.pop(blocker)
    try:
        with pytest.raises(subject.CRTISBAError) as mutated:
            subject._derive_snapshot(db, 1, "READ")
        assert mutated.value.code == "PRODUCER_RESPONSE_INVALID"
    finally:
        subject.NO_COLLECTION[blocker] = original

    after, _ = subject._derive_snapshot(db, 1, "READ")
    assert (after["failure_stage"], after["failure_detail_code"]) == (stage, code)


def test_no_collection_rejects_multiple_unlisted_and_tampered_results(monkeypatch):
    planning = {
        "client_id": 1, "planning_calculation_input_fingerprint": H,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [], "general_income_inputs": [],
    }
    db = SimpleNamespace(get=lambda *_: object())
    monkeypatch.setattr(subject, "_planning", lambda *_: (planning, None))
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *_: {})
    candidate = subject.rtisa_service._empty_result(1, H, "2030-01-01", "RTISA_SOURCE_UNIVERSE_INVALID")
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", lambda *_: candidate)
    for blockers in ([], ["UNKNOWN"], ["RTISA_SOURCE_UNIVERSE_INVALID", "RTISA_PENSION_RESULT_INVALID"]):
        payload = {**candidate, "blockers": blockers}
        raw = {key: value for key, value in payload.items() if key != "admission_result_fingerprint"}
        payload["admission_result_fingerprint"] = subject.rtisa_service._result_fingerprint(raw)
        candidate.clear(); candidate.update(payload)
        with pytest.raises(subject.CRTISBAError) as caught:
            subject._derive_snapshot(db, 1, "READ")
        assert caught.value.code == "PRODUCER_RESPONSE_INVALID"


def test_planning_preemptions_do_not_enter_rtisa(monkeypatch):
    entered = []
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", lambda *_: entered.append(True))
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *_: (_ for _ in ()).throw(
        subject.PensionProductError("X", "x", 409)
    ))
    result, blocked = subject._planning(SimpleNamespace(), 1, "READ")
    assert result is None and blocked["failure_detail_code"] == "CRTISBA_PLANNING_CONTEXT_UNAVAILABLE"
    assert entered == []

    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *_: {
        "client_id": 1, "planning_calculation_input_fingerprint": H,
        "retirement_target": {"retirement_target_ready": False, "retirement_target_date": None},
        "pension_inputs": [],
    })
    result, blocked = subject._planning(SimpleNamespace(), 1, "READ")
    assert result is None and blocked["failure_detail_code"] == "CRTISBA_RETIREMENT_TARGET_NOT_READY"
    assert entered == []


def test_decision_preimage_mutation_is_detected_and_restored(monkeypatch):
    values = {
        "client_id": 1, "source_id": "income:1", "source_kind": "RECURRING_INCOME", "decision_version": 1,
        "planning_calculation_input_fingerprint": H, "source_version": H, "source_fingerprint": H,
        "amount_authority_fingerprint": H, "income_basis": "GROSS",
        "income_basis_provenance": "UPSTREAM_RECURRING_AMOUNT_BASIS",
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
        "price_basis_provenance": "EXPLICIT_PROFESSIONAL",
    }
    expected = subject.decision_fingerprint(values)
    original = subject._decision_preimage
    monkeypatch.setattr(subject, "_decision_preimage", lambda item: {
        key: value for key, value in original(item).items() if key != "amount_authority_fingerprint"
    })
    assert subject.decision_fingerprint(values) != expected
    monkeypatch.setattr(subject, "_decision_preimage", original)
    assert subject.decision_fingerprint(values) == expected
