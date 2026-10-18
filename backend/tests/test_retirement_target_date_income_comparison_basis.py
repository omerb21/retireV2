"""Executable RTICB V2 contract, golden, failure and mutation oracles."""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as subject


PLANNING = "1" * 64
TARGET_DATE = "2030-01-01"
SOURCE_SHA = "4" * 64
AMOUNT_SHA = "5" * 64
DECISION_SHA = "6" * 64
RTISA_SHA = "7" * 64


def _digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _target(*, client_id=1, planning=PLANNING, target_date=TARGET_DATE,
            income="GROSS", price="NOMINAL_AT_RETIREMENT_TARGET_DATE", reference=None,
            state="CURRENT", ready=True):
    target = {
        "client_id": client_id, "planning_calculation_input_fingerprint": planning,
        "retirement_target_date": target_date, "monthly_amount": "10000", "currency": "ILS",
        "income_basis": income, "price_basis": price, "price_reference_date": reference,
    }
    authority = {
        "record_version": 1, "source_kind": "PLANNER_SUPPLIED", "confirmation_state": "CONFIRMED",
        "confirmation_actor": "planner:test", "confirmed_at": "2026-01-01T00:00:00.000000Z",
        "lifecycle_state": "CONFIRMED" if state == "CURRENT" else "STALE",
    }
    result = {
        "schema_version": target_service.SCHEMA_VERSION, "client_id": client_id,
        "planning_calculation_input_fingerprint": planning, "retirement_target_date": target_date,
        "target": target, "authority": authority, "authority_state": state,
        "target_readiness_state": "READY" if ready else "NOT_READY", "target_ready": ready,
        "blockers": [] if ready else ["RIT_RECONFIRMATION_REQUIRED"],
        "target_semantic_fingerprint": _digest({"contract": target_service.SEMANTIC_CONTRACT, **target}),
    }
    result["target_result_fingerprint"] = _digest({"contract": target_service.RESULT_CONTRACT, **result})
    return result


def _entry(state="CURRENT", *, kind="RECURRING_INCOME", source_id=None, income="GROSS",
           price="NOMINAL_AT_RETIREMENT_TARGET_DATE", reference=None):
    pension = kind == "PENSION"
    source_id = source_id or ("manual:1" if pension else "income:1")
    entry = {
        "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1", "source_id": source_id,
        "source_kind": kind, "source_category": "PENSION" if pension else "RENTAL",
        "admission_state": "INCLUDED", "rtisa_reason_codes": [],
        "source_version": 1 if pension else SOURCE_SHA, "source_fingerprint": SOURCE_SHA,
        "amount_authority_fingerprint": AMOUNT_SHA, "decision_version": 1,
        "decision_fingerprint": DECISION_SHA, "decision_state": state, "income_basis": income,
        "income_basis_provenance": "EXPLICIT_PROFESSIONAL" if pension else (
            "MISSING" if income == "UNKNOWN" else "UPSTREAM_RECURRING_AMOUNT_BASIS"
        ),
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE" if pension else price,
        "price_reference_date": None if pension else reference,
        "price_basis_provenance": "OWNER_DECISION_OD2" if pension else "EXPLICIT_PROFESSIONAL",
        "blockers": [],
    }
    if state in {"MISSING", "UNKNOWN", "STALE", "INVALID"}:
        entry["blockers"] = [f"CRTISBA_DECISION_{state}"]
        if state in {"MISSING", "INVALID"}:
            entry["decision_version"] = entry["decision_fingerprint"] = None
        if pension:
            entry["income_basis"] = "UNKNOWN"; entry["income_basis_provenance"] = "MISSING"
        else:
            entry["price_basis"] = "UNKNOWN"; entry["price_reference_date"] = None
            entry["price_basis_provenance"] = "MISSING"
    elif state == "UPSTREAM_UNRESOLVED":
        entry.update({
            "admission_state": "UNRESOLVED", "rtisa_reason_codes": ["RTISA_SOURCE_REVIEW_INCOMPLETE"],
            "amount_authority_fingerprint": None, "decision_version": None,
            "decision_fingerprint": None, "income_basis": None, "income_basis_provenance": None,
            "price_basis": None, "price_reference_date": None, "price_basis_provenance": None,
            "blockers": ["RTISA_SOURCE_REVIEW_INCOMPLETE"],
        })
    elif state in {"NOT_APPLICABLE_DELEGATED", "DELEGATION_UNRESOLVED", "DELEGATION_STALE"}:
        reason = {"NOT_APPLICABLE_DELEGATED": "RTISA_SAME_CANONICAL_PENSION",
                  "DELEGATION_UNRESOLVED": "RTISA_SOURCE_IDENTITY_UNRESOLVED",
                  "DELEGATION_STALE": "RTISA_SOURCE_IDENTITY_STALE"}[state]
        entry.update({
            "source_kind": "RECURRING_INCOME", "source_id": "income:1",
            "source_category": "PENSION_REPRESENTATION", "source_version": SOURCE_SHA,
            "admission_state": "EXCLUDED" if state == "NOT_APPLICABLE_DELEGATED" else "UNRESOLVED",
            "rtisa_reason_codes": [reason], "amount_authority_fingerprint": None,
            "decision_version": None, "decision_fingerprint": None, "income_basis": None,
            "income_basis_provenance": None, "price_basis": None, "price_reference_date": None,
            "price_basis_provenance": None,
            "blockers": [] if state == "NOT_APPLICABLE_DELEGATED" else [reason],
        })
    elif state == "NOT_APPLICABLE_NOT_ADMITTED":
        entry.update({
            "admission_state": "EXCLUDED", "rtisa_reason_codes": ["RTISA_FUTURE_SOURCE"],
            "amount_authority_fingerprint": None, "decision_version": None,
            "decision_fingerprint": None, "income_basis": None, "income_basis_provenance": None,
            "price_basis": None, "price_reference_date": None, "price_basis_provenance": None,
            "blockers": [],
        })
    return entry


def _frequency_unresolved(*, with_decision):
    entry = _entry()
    entry.update({"admission_state": "UNRESOLVED", "decision_state": "UPSTREAM_UNRESOLVED",
                  "rtisa_reason_codes": ["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"],
                  "blockers": ["RTISA_SOURCE_FREQUENCY_UNSUPPORTED"]})
    if not with_decision:
        entry.update({"decision_version": None, "decision_fingerprint": None, "price_basis": "UNKNOWN",
                      "price_reference_date": None, "price_basis_provenance": "MISSING"})
    return entry


def _collection(entries, *, client_id=1, planning=PLANNING, target_date=TARGET_DATE):
    entries = sorted(deepcopy(entries), key=lambda item: item["source_id"])
    partitions = {name: [] for name in subject.PARTITIONS.values()}
    for entry in entries:
        partitions[subject.PARTITIONS[entry["decision_state"]]].append(entry["source_id"])
    blockers = sorted({code for entry in entries for code in entry["blockers"]})
    result = {
        "schema_version": "CRTISBA_COLLECTION_RESULT_V1", "client_id": client_id,
        "planning_calculation_input_fingerprint": planning, "retirement_target_date": target_date,
        "rtisa_admission_result_fingerprint": RTISA_SHA, "source_basis_entries": entries,
        "partitions": partitions, "blockers": blockers,
        "basis_readiness_state": "READY" if not blockers else "NOT_READY", "basis_ready": not blockers,
    }
    result["result_fingerprint"] = _digest({"contract": subject.COLLECTION_CONTRACT, "result": result})
    return result


def _rehash_collection(value):
    value = deepcopy(value); value.pop("result_fingerprint", None)
    value["result_fingerprint"] = _digest({"contract": subject.COLLECTION_CONTRACT, "result": value})
    return value


def _blocked(stage):
    result = {
        "schema_version": "CRTISBA_BLOCK_NO_RESULT_V1", "result_state": "block_no_result",
        "client_id": 1, "source_id": None, "operation": "READ", "failure_stage": stage,
        "failure_detail_code": subject.BLOCKED_CODES[stage], "field_paths": [],
        "observed_planning_calculation_input_fingerprint": PLANNING if stage != "planning_context" else None,
        "observed_source_version": None, "observed_source_fingerprint": None,
        "observed_amount_authority_fingerprint": None, "observed_decision_version": None,
    }
    result["failure_fingerprint"] = _digest({"contract": subject.BLOCKED_CONTRACT, **{
        key: value for key, value in result.items()
        if key not in {"schema_version", "result_state", "failure_fingerprint"}
    }})
    return result


class _Connection:
    def __init__(self, db):
        self.dialect = SimpleNamespace(name=db.dialect); self.commands = []; self.invalidated = False
    def exec_driver_sql(self, command): self.commands.append(command)
    def invalidate(self): self.invalidated = True


class _DB:
    def __init__(self, *, dialect="sqlite", active=False):
        self.dialect = dialect; self.active = active; self.new = set(); self.dirty = set(); self.deleted = set()
        self.connection_value = _Connection(self); self.rollback_count = 0; self.expire_count = 0
    def in_transaction(self): return self.active
    def get_bind(self): return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))
    def connection(self): self.active = True; return self.connection_value
    def expire_all(self): self.expire_count += 1
    @property
    def no_autoflush(self): return nullcontext()
    def rollback(self): self.rollback_count += 1; self.active = False
    def commit(self): raise AssertionError("RTICB must not commit")
    def flush(self): raise AssertionError("RTICB must not flush")


def _request(**changes):
    value = {"client_id": 1, "expected_planning_calculation_input_fingerprint": PLANNING,
             "expected_retirement_target_date": TARGET_DATE}
    value.update(changes); return value


def _run(monkeypatch, *, target=None, collection=None, request=None, db=None):
    target = deepcopy(target or _target()); collection = deepcopy(collection or _collection([_entry()]))
    db = db or _DB(); reached = []
    def target_reader(actual, client_id):
        assert actual is db and client_id == 1; reached.append("target"); return deepcopy(target)
    def basis_reader(actual, client_id, operation="READ"):
        assert actual is db and client_id == 1 and operation == "READ"
        reached.append("crtisba"); return deepcopy(collection)
    monkeypatch.setattr(subject.target_service, "assess_in_snapshot", target_reader)
    monkeypatch.setattr(subject.crtisba_service, "derive_in_snapshot", basis_reader)
    return subject.assess(db, request or _request()), db, reached


@pytest.mark.parametrize("state", list(subject.PARTITIONS))
def test_all_ten_decision_states_are_valid_and_classified(monkeypatch, state):
    result, db, reached = _run(monkeypatch, collection=_collection([_entry(state)]))
    assert reached == ["target", "crtisba"] and db.rollback_count == 1
    assert result["classification_complete"] is True
    comparison = result["source_comparisons"][0]
    if state.startswith("NOT_APPLICABLE"):
        assert (comparison["comparison_state"], comparison["reason_codes"]) == (
            "NOT_ADMITTED", ["RTICB_SOURCE_NOT_ADMITTED"])
    elif state == "CURRENT": assert comparison["comparison_state"] == "DIRECTLY_COMPARABLE"
    else: assert comparison["comparison_state"] == "BASIS_UNRESOLVED"
    assert subject.public_result_valid(result, 1, PLANNING, TARGET_DATE)


@pytest.mark.parametrize("entry", [_entry(kind="PENSION"), _entry(), _frequency_unresolved(with_decision=True), _frequency_unresolved(with_decision=False)])
def test_pension_recurring_and_frequency_subtypes(entry):
    assert subject._entry_authority_valid(entry) and subject._entry_state_valid(entry)


@pytest.mark.parametrize("state,kind", [
    *((state, kind) for state in ("CURRENT", "MISSING", "UNKNOWN", "STALE", "INVALID", "UPSTREAM_UNRESOLVED")
      for kind in ("PENSION", "RECURRING_INCOME")),
    ("NOT_APPLICABLE_DELEGATED", "RECURRING_INCOME"),
    ("DELEGATION_UNRESOLVED", "RECURRING_INCOME"),
    ("DELEGATION_STALE", "RECURRING_INCOME"),
    ("NOT_APPLICABLE_NOT_ADMITTED", "PENSION"),
    ("NOT_APPLICABLE_NOT_ADMITTED", "RECURRING_INCOME"),
])
def test_all_legal_state_and_source_kind_subroutes(state, kind):
    entry = _entry(state, kind=kind)
    assert subject._entry_authority_valid(entry)
    assert subject._entry_state_valid(entry)


@pytest.mark.parametrize("income,price,reference,target_price,target_reference,state,reasons", [
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "DIRECTLY_COMPARABLE", []),
    ("NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-02-01", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]),
    ("UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"]),
])
def test_comparison_equivalence_classes(monkeypatch, income, price, reference, target_price, target_reference, state, reasons):
    result, _, _ = _run(monkeypatch, target=_target(price=target_price, reference=target_reference),
                        collection=_collection([_entry(income=income, price=price, reference=reference)]))
    comparison = result["source_comparisons"][0]
    assert (comparison["comparison_state"], comparison["reason_codes"]) == (state, reasons)


CURRENT_COMPARISON_CLASSES = [
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "DIRECTLY_COMPARABLE", []),
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"]),
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"]),
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NET", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-01-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_PRICE_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "DIRECTLY_COMPARABLE", []),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NET", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-01-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "GROSS", "REAL_AT_REFERENCE_DATE", "2029-02-01", "NORMALIZATION_REQUIRED", ["RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NET", "REAL_AT_REFERENCE_DATE", "2029-02-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]),
    ("GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-02-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]),
    ("NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "DIRECTLY_COMPARABLE", []),
]


@pytest.mark.parametrize(
    "target_income,target_price,target_reference,source_income,source_price,source_reference,state,reasons",
    CURRENT_COMPARISON_CLASSES,
)
def test_complete_legal_current_comparison_equivalence_matrix(
    monkeypatch, target_income, target_price, target_reference,
    source_income, source_price, source_reference, state, reasons,
):
    result, _, _ = _run(
        monkeypatch,
        target=_target(income=target_income, price=target_price, reference=target_reference),
        collection=_collection([_entry(
            income=source_income, price=source_price, reference=source_reference,
        )]),
    )
    comparison = result["source_comparisons"][0]
    assert (comparison["comparison_state"], comparison["reason_codes"]) == (state, reasons)
    assert result["blockers"] == (
        ["RTICB_BASIS_UNRESOLVED"] if state == "BASIS_UNRESOLVED"
        else ["RTICB_NORMALIZATION_REQUIRED"] if state == "NORMALIZATION_REQUIRED"
        else []
    )


@pytest.mark.parametrize("stage", list(subject.BLOCKED_CODES))
def test_all_four_professional_blocked_results_preserve_identity(monkeypatch, stage):
    upstream = _blocked(stage); result, _, reached = _run(monkeypatch, collection=upstream)
    assert reached == ["target", "crtisba"]
    assert result["failure_stage"] == "crtisba_authority"
    assert result["failure_detail_code"] == subject.BLOCKED_RTICB[stage]
    assert result["observed_crtisba_failure_fingerprint"] == upstream["failure_fingerprint"]
    assert subject.public_result_valid(result, 1, PLANNING, TARGET_DATE)


@pytest.mark.parametrize("field_paths,accepted", [
    (["/a~0b/~1x"], True),
    (["/a~2b"], False),
    (["not-a-pointer"], False),
])
def test_blocked_result_requires_canonical_json_pointers(monkeypatch, field_paths, accepted):
    upstream = _blocked("source_universe")
    upstream["field_paths"] = field_paths
    upstream.pop("failure_fingerprint")
    upstream["failure_fingerprint"] = _digest({"contract": subject.BLOCKED_CONTRACT, **{
        key: value for key, value in upstream.items()
        if key not in {"schema_version", "result_state", "failure_fingerprint"}
    }})
    result, _, _ = _run(monkeypatch, collection=upstream)
    expected = (
        subject.BLOCKED_RTICB["source_universe"]
        if accepted else "RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID"
    )
    assert result["failure_detail_code"] == expected


@pytest.mark.parametrize("mutate,stage,code", [
    (lambda value: value.update(partitions={**value["partitions"], "current": []}), "source_universe", "RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH"),
    (lambda value: value.update(basis_ready=False), "source_universe", "RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID"),
    (lambda value: value["source_basis_entries"][0].update(source_version=None), "source_universe", "RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID"),
    (lambda value: value["source_basis_entries"][0].update(income_basis_provenance="MISSING"), "classification", "RTICB_CRTISBA_STATE_BASIS_INVALID"),
])
def test_coherently_rehashed_near_misses_fail_at_exact_stage(monkeypatch, mutate, stage, code):
    collection = _collection([_entry()]); mutate(collection); collection = _rehash_collection(collection)
    result, _, _ = _run(monkeypatch, collection=collection)
    assert (result["failure_stage"], result["failure_detail_code"]) == (stage, code)


def test_coherently_rehashed_foreign_source_category_fails_authority(monkeypatch):
    collection = _collection([_entry()])
    collection["source_basis_entries"][0]["source_category"] = "UNRECOGNIZED"
    result, _, _ = _run(monkeypatch, collection=_rehash_collection(collection))
    assert (result["failure_stage"], result["failure_detail_code"]) == (
        "source_universe", "RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID",
    )


def test_category_a_goldens_are_independently_fixed(monkeypatch):
    result, _, _ = _run(monkeypatch); entry = result["source_comparisons"][0]
    assert result["comparison_input_fingerprint"] == "464cc188c5a73915e77f30bf3cf3d4d641bf44b8529807e884a85ad34a50ae9a"
    assert entry["source_comparison_fingerprint"] == "5f02a7f47e4d127b46a61dc33274831b3641862bd3676b751d155e469c6129ad"
    assert result["comparison_result_fingerprint"] == "7477751db4046bd7bc4c5e33a47993a728c6c1732c5b998f43527e96e94c654c"
    failure = subject._failure(
        _request(), "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY",
        target=_target(state="STALE", ready=False),
    )
    failure_preimage = {
        "contract": subject.FAILURE_FINGERPRINT_CONTRACT,
        "failure": {
            key: deepcopy(value) for key, value in failure.items() if key != "result_fingerprint"
        },
    }
    assert _digest(failure_preimage) == "2bdf35542dfe16220ba7999016e47acdb7e5f4c61e53271d56ea1a64729047cd"
    assert failure["result_fingerprint"] == "2bdf35542dfe16220ba7999016e47acdb7e5f4c61e53271d56ea1a64729047cd"


def test_mutation_kills_actual_classification_branch_and_restores(monkeypatch):
    ordinary, _, _ = _run(monkeypatch)
    original = subject._basis_reasons; reached = []
    def mutant(entry, target): reached.append(entry["source_id"]); return ["RTICB_INCOME_BASIS_MISMATCH"]
    monkeypatch.setattr(subject, "_basis_reasons", mutant); changed, _, _ = _run(monkeypatch)
    assert reached == ["income:1"] and changed != ordinary
    monkeypatch.setattr(subject, "_basis_reasons", original); restored, _, _ = _run(monkeypatch)
    assert restored == ordinary


@pytest.mark.parametrize("validator,mutate,stage,code", [
    (
        "_collection_fingerprint_valid",
        lambda value: value.update(result_fingerprint="9" * 64),
        "crtisba_authority", "RTICB_CRTISBA_RESULT_FINGERPRINT_MISMATCH",
    ),
    (
        "_universe_valid",
        lambda value: value.update(partitions={**value["partitions"], "current": []}),
        "source_universe", "RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH",
    ),
    (
        "_consistent",
        lambda value: value.update(basis_ready=False),
        "source_universe", "RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID",
    ),
    (
        "_entry_authority_valid",
        lambda value: value["source_basis_entries"][0].update(source_category="UNRECOGNIZED"),
        "source_universe", "RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID",
    ),
    (
        "_entry_state_valid",
        lambda value: value["source_basis_entries"][0].update(income_basis_provenance="MISSING"),
        "classification", "RTICB_CRTISBA_STATE_BASIS_INVALID",
    ),
])
def test_validation_branch_mutations_are_killed_and_restored(
    monkeypatch, validator, mutate, stage, code,
):
    collection = _collection([_entry()])
    mutate(collection)
    if validator != "_collection_fingerprint_valid":
        collection = _rehash_collection(collection)

    def ordinary_oracle():
        result, _, _ = _run(monkeypatch, collection=collection)
        assert (result["failure_stage"], result["failure_detail_code"]) == (stage, code)

    ordinary_oracle()
    original = getattr(subject, validator)
    reached = []
    def bypass(*args, **kwargs):
        reached.append((args, kwargs))
        return True
    monkeypatch.setattr(subject, validator, bypass)
    with pytest.raises((AssertionError, KeyError)):
        ordinary_oracle()
    assert reached
    monkeypatch.setattr(subject, validator, original)
    ordinary_oracle()


def test_blocked_stage_mapping_mutation_is_killed_and_restored(monkeypatch):
    upstream = _blocked("planning_context")
    expected = subject.BLOCKED_RTICB["planning_context"]
    def ordinary_oracle():
        result, _, _ = _run(monkeypatch, collection=upstream)
        assert result["failure_detail_code"] == expected
        assert result["observed_crtisba_failure_fingerprint"] == upstream["failure_fingerprint"]
    ordinary_oracle()
    subject.BLOCKED_RTICB["planning_context"] = "RTICB_CRTISBA_BLOCKED_PENSION_RESULT_INVALID"
    try:
        with pytest.raises(AssertionError):
            ordinary_oracle()
    finally:
        subject.BLOCKED_RTICB["planning_context"] = expected
    ordinary_oracle()


def test_target_then_crtisba_one_snapshot_and_no_public_owner(monkeypatch):
    monkeypatch.setattr(subject.target_service, "assess", lambda *_: pytest.fail("public target owner"))
    monkeypatch.setattr(subject.crtisba_service, "read", lambda *_: pytest.fail("public CRTISBA owner"))
    result, db, reached = _run(monkeypatch)
    assert reached == ["target", "crtisba"] and db.connection_value.commands == ["BEGIN"]
    assert db.rollback_count == 1 and result["classification_complete"] is True


def test_pre_db_failure_does_not_touch_session():
    db = _DB(); result = subject.assess(db, _request(extra=True))
    assert result["failure_detail_code"] == "RTICB_REQUEST_SCHEMA_INVALID"
    assert db.rollback_count == 0 and db.connection_value.commands == []


@pytest.mark.parametrize("request_payload,code", [
    ({"client_id": 1}, "RTICB_REQUEST_SCHEMA_INVALID"),
    (_request(client_id=True), "RTICB_CLIENT_ID_INVALID"),
    (_request(expected_planning_calculation_input_fingerprint="bad"), "RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID"),
    (_request(expected_retirement_target_date="2030-02-30"), "RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID"),
])
def test_all_request_failures_precede_database(request_payload, code):
    db = _DB()
    result = subject.assess(db, request_payload)
    assert (result["failure_stage"], result["failure_detail_code"]) == (
        "request_validation", code,
    )
    assert db.rollback_count == 0 and db.connection_value.commands == []


def test_fresh_session_and_unsupported_database_do_not_open_owned_snapshot():
    active = _DB(active=True)
    result = subject.assess(active, _request())
    assert result["failure_detail_code"] == "RTICB_REQUIRES_FRESH_TRANSACTION"
    assert active.active is True and active.rollback_count == 0
    unsupported = _DB(dialect="mysql")
    result = subject.assess(unsupported, _request())
    assert result["failure_detail_code"] == "RTICB_UNSUPPORTED_DATABASE"
    assert unsupported.rollback_count == 0 and unsupported.connection_value.commands == []


@pytest.mark.parametrize("change,stage,code", [
    ({"client_id": 2}, "cross_authority_identity", "RTICB_CLIENT_ID_MISMATCH"),
    ({"planning_calculation_input_fingerprint": "8" * 64}, "cross_authority_identity", "RTICB_PLANNING_IDENTITY_MISMATCH"),
    ({"retirement_target_date": "2031-01-01"}, "cross_authority_identity", "RTICB_RETIREMENT_TARGET_DATE_MISMATCH"),
])
def test_cross_authority_identity_precedence(monkeypatch, change, stage, code):
    collection = _collection([_entry()]); collection.update(change)
    result, _, _ = _run(monkeypatch, collection=_rehash_collection(collection))
    assert (result["failure_stage"], result["failure_detail_code"]) == (stage, code)


@pytest.mark.parametrize("field", ["target_result_fingerprint", "target_semantic_fingerprint"])
def test_target_category_b_tampering_fails_before_crtisba(monkeypatch, field):
    target = _target(); target[field] = "9" * 64
    result, _, reached = _run(monkeypatch, target=target)
    assert reached == ["target"]
    assert (result["failure_stage"], result["failure_detail_code"]) == (
        "target_authority", "RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID",
    )


def test_technical_exception_rolls_back_and_propagates(monkeypatch):
    db = _DB()
    monkeypatch.setattr(subject.target_service, "assess_in_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"): subject.assess(db, _request())
    assert db.rollback_count == 1 and not db.in_transaction()


def test_technical_exception_cleanup_runs_even_if_driver_loses_transaction_state(monkeypatch):
    db = _DB()
    def fail_after_connection_loss(*_):
        db.active = False
        raise RuntimeError("connection lost")
    monkeypatch.setattr(subject.target_service, "assess_in_snapshot", fail_after_connection_loss)
    with pytest.raises(RuntimeError, match="connection lost"):
        subject.assess(db, _request())
    assert db.rollback_count == 1


def test_public_validator_rejects_coherently_rehashed_mixed_target_basis(monkeypatch):
    collection = _collection([_entry(source_id="income:1"), _entry(source_id="income:2")])
    result, _, _ = _run(monkeypatch, collection=collection)
    result["source_comparisons"][1]["target_income_basis"] = "NET"
    entry = result["source_comparisons"][1]
    entry_without_fingerprint = {
        key: deepcopy(value) for key, value in entry.items()
        if key != "source_comparison_fingerprint"
    }
    entry["source_comparison_fingerprint"] = _digest({
        "contract": subject.ENTRY_FINGERPRINT_CONTRACT,
        "comparison_input_fingerprint": result["comparison_input_fingerprint"],
        "entry": entry_without_fingerprint,
    })
    result_without_fingerprint = {
        key: deepcopy(value) for key, value in result.items()
        if key != "comparison_result_fingerprint"
    }
    result["comparison_result_fingerprint"] = _digest({
        "contract": subject.RESULT_FINGERPRINT_CONTRACT,
        "result": result_without_fingerprint,
    })
    assert not subject.public_result_valid(result, 1, PLANNING, TARGET_DATE)


def test_public_validator_rejects_authority_observations_at_pre_db_stage():
    result = subject._failure(
        _request(), "snapshot_admission", "RTICB_REQUIRES_FRESH_TRANSACTION",
    )
    result["observed_target_result_fingerprint"] = "9" * 64
    result_without_fingerprint = {
        key: deepcopy(value) for key, value in result.items() if key != "result_fingerprint"
    }
    result["result_fingerprint"] = _digest({
        "contract": subject.FAILURE_FINGERPRINT_CONTRACT,
        "failure": result_without_fingerprint,
    })
    assert not subject.public_result_valid(result, 1, PLANNING, TARGET_DATE)


def test_public_validator_rejects_missing_visited_authority_observations(monkeypatch):
    collection = _collection([_entry()])
    collection["source_basis_entries"][0]["income_basis_provenance"] = "MISSING"
    result, _, _ = _run(monkeypatch, collection=_rehash_collection(collection))
    assert result["failure_stage"] == "classification"
    result["observed_crtisba_result_fingerprint"] = None
    result_without_fingerprint = {
        key: deepcopy(value) for key, value in result.items() if key != "result_fingerprint"
    }
    result["result_fingerprint"] = _digest({
        "contract": subject.FAILURE_FINGERPRINT_CONTRACT,
        "failure": result_without_fingerprint,
    })
    assert not subject.public_result_valid(result, 1, PLANNING, TARGET_DATE)
