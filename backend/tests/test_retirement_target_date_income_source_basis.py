from datetime import date
from decimal import Decimal
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select, text
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
        "pension_inputs": [], "general_income_inputs": [], "excluded_sources": [],
        "blocking_facts": [], "planning_input_ready": True,
    }
    rtisa = subject.rtisa_service._empty_result(1, H, "2030-01-01", blocker)
    db = SimpleNamespace(get=lambda *_: object())
    monkeypatch.setattr(subject, "_planning", lambda *_: (planning, None))
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
        "pension_inputs": [], "general_income_inputs": [], "excluded_sources": [],
        "blocking_facts": [], "planning_input_ready": True,
    }
    db = SimpleNamespace(get=lambda *_: object())
    monkeypatch.setattr(subject, "_planning", lambda *_: (planning, None))
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


def test_actual_rtisa_source_universe_no_collection_branch_is_consumed(engine, monkeypatch):
    _authority(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO recurring_income "
            "(id,client_id,income_category,description,amount,amount_basis,frequency,"
            "continuation_status,lifecycle_status,source_status,verification_state,start_date) "
            "VALUES (-1,1,'rental','invalid identity',100,'gross','monthly','ongoing',"
            "'current','planner entered','reviewed','2025-01-01')"
        ))
    original = subject.rtisa_service.read_in_snapshot
    produced = []

    def observed(*args, **kwargs):
        result = original(*args, **kwargs)
        produced.append(result)
        return result

    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", observed)
    result = _read(engine)
    assert produced and produced[0]["blockers"] == ["RTISA_SOURCE_UNIVERSE_INVALID"]
    assert produced[0]["source_entries"] == []
    assert (result["failure_stage"], result["failure_detail_code"]) == (
        "source_universe", "CRTISBA_SOURCE_UNIVERSE_INVALID"
    )


def test_actual_rtisa_pension_result_no_collection_branch_is_consumed(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        db.add(PlanningInputDecision(
            client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 1),
            retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint=H, actor="planner:test",
        ))
    original_portfolio = subject.portfolio_service.execute_from_planning_result
    original_rtisa = subject.rtisa_service.read_in_snapshot
    calls = []
    produced = []

    def portfolio_by_boundary(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            return original_portfolio(*args, **kwargs)
        return {"schema_version": "malformed-actual-upstream-result"}

    def observed(*args, **kwargs):
        result = original_rtisa(*args, **kwargs)
        produced.append(result)
        return result

    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", portfolio_by_boundary)
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", observed)
    result = _read(engine)
    assert len(calls) == 2 and produced
    assert produced[0]["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]
    assert produced[0]["source_entries"] == []
    assert (result["failure_stage"], result["failure_detail_code"]) == (
        "pension_result", "CRTISBA_PENSION_RESULT_INVALID"
    )


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
        "client_id": 2, "planning_calculation_input_fingerprint": H,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [],
    })
    with pytest.raises(subject.CRTISBAError) as invalid:
        subject._planning(SimpleNamespace(), 1, "READ")
    assert invalid.value.code == "PRODUCER_RESPONSE_INVALID" and entered == []

    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *_: {
        "client_id": 1, "planning_calculation_input_fingerprint": H,
        "retirement_target": {"retirement_target_ready": False, "retirement_target_date": None},
        "pension_inputs": [],
    })
    result, blocked = subject._planning(SimpleNamespace(), 1, "READ")
    assert result is None and blocked["failure_detail_code"] == "CRTISBA_RETIREMENT_TARGET_NOT_READY"
    assert entered == []


def test_stale_planning_cas_is_revalidated_after_source_and_decision_locks(engine, monkeypatch):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    command = _command(initial["source_basis_entries"][0])
    command.expected_planning_calculation_input_fingerprint = "b" * 64
    entered = []
    original = subject.rtisa_service.read_in_snapshot
    def observed_rtisa(*args, **kwargs):
        entered.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", observed_rtisa)
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as caught:
        subject.write(db, 1, "income:1", command, "actor")
    assert caught.value.code == "CRTISBA_PLANNING_IDENTITY_STALE"
    assert caught.value.field_paths == ["/expected_planning_calculation_input_fingerprint"]
    assert entered == [True]


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


def test_non_contiguous_append_only_version_chain_is_invalid(engine):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    entry = initial["source_basis_entries"][0]
    with Session(engine) as db:
        subject.write(db, 1, "income:1", _command(entry), "actor")
    with Session(engine) as db, db.begin():
        first = db.scalar(select(RetirementTargetDateIncomeSourceBasisDecision))
        values = subject._row_values(first) | {"decision_version": 3}
        db.add(RetirementTargetDateIncomeSourceBasisDecision(
            client_id=first.client_id, source_id=first.source_id, source_kind=first.source_kind,
            decision_version=3,
            planning_calculation_input_fingerprint=first.planning_calculation_input_fingerprint,
            pension_source_version=None,
            recurring_source_version_fingerprint=first.recurring_source_version_fingerprint,
            source_fingerprint=first.source_fingerprint,
            amount_authority_fingerprint=first.amount_authority_fingerprint,
            pension_source_execution_fingerprint=None, pension_source_result_fingerprint=None,
            portfolio_source_entry_fingerprint=None, retirement_target_date=None,
            income_basis=first.income_basis, income_basis_provenance=first.income_basis_provenance,
            price_basis=first.price_basis, price_reference_date=first.price_reference_date,
            price_basis_provenance=first.price_basis_provenance,
            decision_actor="actor", decision_fingerprint=subject.decision_fingerprint(values),
        ))
    observed = _read(engine)["source_basis_entries"][0]
    assert observed["decision_state"] == "INVALID"
    assert observed["decision_version"] is None and observed["decision_fingerprint"] is None


class _TerminationConnection:
    def __init__(self):
        self.invalidated = 0

    def invalidate(self):
        self.invalidated += 1


class _TerminationSession:
    new = dirty = deleted = ()

    def __init__(self, *, rollback_raises=False):
        self.active = False
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.rollback_raises = rollback_raises
        self.conn = _TerminationConnection()

    def in_transaction(self):
        return self.active

    def connection(self, **_):
        self.active = True
        return self.conn

    def rollback(self):
        self.rollbacks += 1
        if self.rollback_raises:
            raise RuntimeError("rollback failed")
        self.active = False

    def commit(self):
        self.commits += 1
        self.active = False

    def close(self):
        self.closed += 1


def test_read_termination_success_mutation_and_restoration(monkeypatch):
    original_rollback = subject._rollback
    monkeypatch.setattr(subject, "_begin", lambda db, *, write: db.connection())
    monkeypatch.setattr(subject, "derive_in_snapshot", lambda *_: {"ordinary": "result"})

    def ordinary_oracle():
        db = _TerminationSession()
        assert subject.read(db, 1) == {"ordinary": "result"}
        assert (db.rollbacks, db.commits, db.closed) == (1, 0, 0)

    ordinary_oracle()
    monkeypatch.setattr(subject, "_rollback", lambda db: db.commit())
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_rollback", original_rollback)
    ordinary_oracle()


def test_read_failure_rollback_mutation_and_restoration(monkeypatch):
    original_rollback = subject._rollback
    monkeypatch.setattr(subject, "_begin", lambda db, *, write: db.connection())
    monkeypatch.setattr(subject, "derive_in_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("derive")))

    def ordinary_oracle():
        db = _TerminationSession()
        with pytest.raises(subject.CRTISBAError) as caught:
            subject.read(db, 1)
        assert caught.value.code == "CRTISBA_DATABASE_FAILURE"
        assert (db.rollbacks, db.commits, db.closed) == (1, 0, 0)

    ordinary_oracle()
    monkeypatch.setattr(subject, "_rollback", lambda db: None)
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_rollback", original_rollback)
    ordinary_oracle()


def test_rollback_failure_invalidates_closes_and_is_not_reused(monkeypatch):
    def ordinary_oracle():
        db = _TerminationSession(rollback_raises=True)
        db.active = True
        with pytest.raises(subject.CRTISBAError) as caught:
            subject._rollback(db)
        assert caught.value.code == "CRTISBA_ROLLBACK_FAILED"
        assert db.conn.invalidated == 1 and db.closed == 1 and db.rollbacks == 1

    ordinary_oracle()
    original = _TerminationConnection.invalidate
    monkeypatch.setattr(_TerminationConnection, "invalidate", lambda self: None)
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(_TerminationConnection, "invalidate", original)
    ordinary_oracle()


def test_transaction_acquisition_failure_does_not_rollback_before_acquired(monkeypatch):
    db = _TerminationSession()
    monkeypatch.setattr(subject, "_begin", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("acquire")))
    with pytest.raises(subject.CRTISBAError) as caught:
        subject.read(db, 1)
    assert caught.value.code == "CRTISBA_DATABASE_FAILURE"
    assert db.rollbacks == 0 and db.conn.invalidated == 0 and db.closed == 0


@pytest.mark.parametrize("kind,entry,context,expected", [
    ("PENSION", {"source_id": "manual:1", "source_category": "PENSION_REPRESENTATION",
                 "admission_state": "INCLUDED", "reason_codes": [],
                 "upstream_identity": {"source_fingerprint": H}},
     {"kind": "PENSION", "source_version": 1, "source_fingerprint": H, "amount": H},
     ("UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE")),
    ("RECURRING_INCOME", {"source_id": "income:1", "source_category": "GENERAL_INCOME",
                          "admission_state": "INCLUDED", "reason_codes": [],
                          "native_income_basis": "GROSS",
                          "upstream_identity": {"source_fingerprint": H}},
     {"kind": "RECURRING_INCOME", "source_version": H, "source_fingerprint": H, "amount": H},
     ("GROSS", "UNKNOWN")),
])
def test_forbidden_od_inference_mutation_and_restoration(monkeypatch, kind, entry, context, expected):
    def ordinary_oracle():
        actual = subject._entry(entry, context, None, H)
        assert (actual["income_basis"], actual["price_basis"]) == expected
        assert actual["decision_state"] == "MISSING"

    ordinary_oracle()
    original = subject._safe_basis
    monkeypatch.setattr(subject, "_safe_basis", lambda *_: (
        "NET", "EXPLICIT_PROFESSIONAL", "REAL_AT_REFERENCE_DATE", "2020-01-01", "EXPLICIT_PROFESSIONAL"
    ))
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_safe_basis", original)
    ordinary_oracle()


def test_canonical_entry_order_mutation_and_restoration(monkeypatch):
    entries = [{"source_id": "income:10"}, {"source_id": "income:2"}, {"source_id": "א"}]
    def ordinary_oracle():
        assert [item["source_id"] for item in subject._sort_entries(entries)] == ["income:10", "income:2", "א"]
    ordinary_oracle()
    original = subject._sort_entries
    monkeypatch.setattr(subject, "_sort_entries", lambda value: list(reversed(value)))
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_sort_entries", original)
    ordinary_oracle()


@pytest.mark.parametrize("invalidated,state", [(True, "23505"), (False, "08006")])
def test_post_dispatch_uncertainty_precedence_mutation_and_restoration(monkeypatch, invalidated, state):
    orig = RuntimeError("recognized constraint must lose to uncertainty")
    orig.pgcode = state
    orig.diag = SimpleNamespace(constraint_name="uq_crtisba_source_decision_version")
    exc = DBAPIError.instance("statement", {}, orig, RuntimeError, connection_invalidated=invalidated)

    def ordinary_oracle():
        assert subject._classify_integrity(exc, "COMMIT_DISPATCHED").code == "CRTISBA_COMMIT_OUTCOME_UNKNOWN"

    ordinary_oracle()
    original = subject._classify_integrity
    monkeypatch.setattr(subject, "_classify_integrity", lambda *_: subject.CRTISBAError(
        "CRTISBA_DECISION_VERSION_CONFLICT", 409, ["/expected_decision_version"]
    ))
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_classify_integrity", original)
    ordinary_oracle()


def test_fixed_independent_golden_fingerprints():
    source_fp = "1" * 64
    planning_fp = "2" * 64
    amount_fp = "3" * 64
    admission_fp = "4" * 64
    amount_preimage = {
        "contract": subject.RECURRING_AMOUNT_CONTRACT,
        "client_id": 7, "source_id": "income:9", "source_fingerprint": source_fp,
        "amount": "1234.50", "amount_basis": "gross", "frequency": "monthly",
    }
    assert subject.fingerprint(amount_preimage) == "27152ba73c864b4110a9ac9fc1e0d9baec965e5fe594d6d7a11aaf36a261256f"

    decision = {
        "client_id": 7, "source_id": "income:9", "source_kind": "RECURRING_INCOME",
        "decision_version": 3, "planning_calculation_input_fingerprint": planning_fp,
        "source_version": source_fp, "source_fingerprint": source_fp,
        "amount_authority_fingerprint": amount_fp, "income_basis": "GROSS",
        "income_basis_provenance": "UPSTREAM_RECURRING_AMOUNT_BASIS",
        "price_basis": "REAL_AT_REFERENCE_DATE", "price_reference_date": date(2026, 1, 15),
        "price_basis_provenance": "EXPLICIT_PROFESSIONAL",
    }
    assert subject.decision_fingerprint(decision) == "70ff8553393765b20541889b6f03f463a0a158d848f43dec0db1ad3e1bafe34b"

    failure = subject._failure(7, "income:9", "CLASSIFY", "source_identity",
        "CRTISBA_SOURCE_FINGERPRINT_STALE", ["/expected_source_fingerprint"], {
            "planning": planning_fp, "source_version": source_fp,
            "source_fingerprint": source_fp, "amount": amount_fp, "decision_version": 2,
        })
    assert failure["failure_fingerprint"] == "3111e947dc8278c7cd49563e2f32578946f17512e08e6569d0c1e52186b98582"

    collection = {
        "schema_version": "CRTISBA_COLLECTION_RESULT_V1", "client_id": 7,
        "planning_calculation_input_fingerprint": planning_fp,
        "retirement_target_date": "2035-06-30",
        "rtisa_admission_result_fingerprint": admission_fp,
        "source_basis_entries": [],
        "partitions": {name: [] for name in subject.PARTITION_STATES.values()},
        "blockers": [], "basis_readiness_state": "READY", "basis_ready": True,
    }
    assert subject.fingerprint({"contract": subject.RESULT_CONTRACT, "result": collection}) \
        == "3107c133184b4b14df596ab2d68bcf4da89361e4af8e9d92ecabdcd4b673cd48"


def test_complete_upstream_envelopes_reject_semantic_tampering_with_matching_hash(engine, monkeypatch):
    _authority(engine)
    original_planning = subject.planning_input_service.derive

    def wrong_planning(*args, **kwargs):
        result = deepcopy(original_planning(*args, **kwargs))
        result["general_income_inputs"][0]["source_fingerprint"] = "not-a-sha"
        # The accepted calculation fingerprint is intentionally left intact:
        # a matching outer hash cannot bless a malformed source envelope.
        return result

    monkeypatch.setattr(subject.planning_input_service, "derive", wrong_planning)
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as planning_error:
        subject.read(db, 1)
    assert planning_error.value.code == "PRODUCER_RESPONSE_INVALID"
    monkeypatch.setattr(subject.planning_input_service, "derive", original_planning)

    original_portfolio = subject.portfolio_service.execute_from_planning_result

    def wrong_portfolio(*args, **kwargs):
        result = deepcopy(original_portfolio(*args, **kwargs))
        result["client_id"] = 2
        payload = subject.portfolio_service._ready_result_payload(result)
        result["portfolio_result_fingerprint"] = subject.portfolio_service._result_fingerprint(payload)
        return result

    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", wrong_portfolio)
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as portfolio_error:
        subject.read(db, 1)
    assert portfolio_error.value.code == "PRODUCER_RESPONSE_INVALID"
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", original_portfolio)

    original_rtisa = subject.rtisa_service.read_in_snapshot
    def rebound_rtisa(*args, **kwargs):
        result = deepcopy(original_rtisa(*args, **kwargs))
        result["source_entries"][0]["upstream_identity"]["source_fingerprint"] = "f" * 64
        payload = {key: value for key, value in result.items() if key != "admission_result_fingerprint"}
        result["admission_result_fingerprint"] = subject.rtisa_service._result_fingerprint(payload)
        return result
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", rebound_rtisa)
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as rtisa_error:
        subject.read(db, 1)
    assert rtisa_error.value.code == "PRODUCER_RESPONSE_INVALID"


def test_bigint_max_version_chain_is_bounded_and_invalid_without_range_allocation(engine):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    entry = initial["source_basis_entries"][0]
    with Session(engine) as db:
        subject.write(db, 1, "income:1", _command(entry), "actor")
    with Session(engine) as db, db.begin():
        first = db.scalar(select(RetirementTargetDateIncomeSourceBasisDecision))
        values = subject._row_values(first) | {"decision_version": subject.MAX_VERSION}
        db.add(RetirementTargetDateIncomeSourceBasisDecision(
            client_id=1, source_id="income:1", source_kind="RECURRING_INCOME",
            decision_version=subject.MAX_VERSION,
            planning_calculation_input_fingerprint=first.planning_calculation_input_fingerprint,
            pension_source_version=None,
            recurring_source_version_fingerprint=first.recurring_source_version_fingerprint,
            source_fingerprint=first.source_fingerprint,
            amount_authority_fingerprint=first.amount_authority_fingerprint,
            pension_source_execution_fingerprint=None, pension_source_result_fingerprint=None,
            portfolio_source_entry_fingerprint=None, retirement_target_date=None,
            income_basis=first.income_basis, income_basis_provenance=first.income_basis_provenance,
            price_basis=first.price_basis, price_reference_date=first.price_reference_date,
            price_basis_provenance=first.price_basis_provenance,
            decision_actor="actor", decision_fingerprint=subject.decision_fingerprint(values),
        ))
    observed = _read(engine)["source_basis_entries"][0]
    assert observed["decision_state"] == "INVALID"
    assert observed["decision_version"] is None and observed["decision_fingerprint"] is None


def test_frequency_unsupported_never_exposes_stale_decision_identity(engine):
    global _CURRENT_PLANNING
    _authority(engine)
    initial = _read(engine)
    _CURRENT_PLANNING = initial["planning_calculation_input_fingerprint"]
    with Session(engine) as db:
        subject.write(db, 1, "income:1", _command(initial["source_basis_entries"][0]), "actor")
    with Session(engine) as db, db.begin():
        db.scalar(select(RecurringIncome).where(RecurringIncome.id == 1)).frequency = "other"
    observed = _read(engine)["source_basis_entries"][0]
    assert observed["decision_state"] == "UPSTREAM_UNRESOLVED"
    assert observed["rtisa_reason_codes"] == ["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"]
    assert observed["decision_version"] is None and observed["decision_fingerprint"] is None
    assert observed["price_basis"] == "UNKNOWN"


def test_existing_source_wrong_kind_is_mismatch_not_not_found(engine):
    _authority(engine)
    initial = _read(engine)
    entry = initial["source_basis_entries"][0]
    command = TypeAdapter(CRTISBACommand).validate_python({
        "schema_version": "CRTISBA_PENSION_CLASSIFY_COMMAND_V1", "operation": "CLASSIFY",
        "source_kind": "PENSION", "expected_decision_version": 0,
        "expected_planning_calculation_input_fingerprint": initial["planning_calculation_input_fingerprint"],
        "expected_source_version": 1, "expected_source_fingerprint": entry["source_fingerprint"],
        "expected_amount_authority_fingerprint": entry["amount_authority_fingerprint"],
        "income_basis": "GROSS",
    })
    with Session(engine) as db, pytest.raises(subject.CRTISBAError) as caught:
        subject.write(db, 1, "income:1", command, "actor")
    assert caught.value.code == "CRTISBA_SOURCE_KIND_MISMATCH"


def test_malformed_pgcode_falls_back_to_valid_sqlstate():
    orig = RuntimeError("structured fields only")
    orig.pgcode = "not-a-state"
    orig.sqlstate = "23505"
    orig.diag = SimpleNamespace(constraint_name="uq_crtisba_source_decision_version")
    exc = DBAPIError.instance("statement", {}, orig, RuntimeError, connection_invalidated=False)
    assert subject._classify_integrity(exc, "COMMIT_DISPATCHED").code == "CRTISBA_DECISION_VERSION_CONFLICT"
