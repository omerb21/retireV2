"""Ordinary, negative and mutation-sensitive CMIA contract evidence."""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.services import retirement_target_date_comparable_monthly_income_service as subject
from app.services import retirement_target_date_income_comparison_basis_service as rticb
from app.services import retirement_target_date_income_source_basis_service as crtisba
from test_retirement_target_date_income_comparison_basis import (
    PLANNING, TARGET_DATE, _collection, _entry, _request, _target,
)


def _sha(character):
    return character * 64


def _independent_fingerprint(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class _Connection:
    def __init__(self, db):
        self.dialect = SimpleNamespace(name=db.dialect)
        self.commands = []
        self.invalidated = False

    def exec_driver_sql(self, command):
        self.commands.append(command)

    def invalidate(self):
        self.invalidated = True


class _DB:
    def __init__(self, dialect="sqlite", active=False):
        self.dialect = dialect
        self.active = active
        self.new = set()
        self.dirty = set()
        self.deleted = set()
        self.connection_value = _Connection(self)
        self.rollback_count = 0
        self.close_count = 0

    def in_transaction(self):
        return self.active

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))

    def connection(self):
        self.active = True
        return self.connection_value

    def expire_all(self):
        pass

    @property
    def no_autoflush(self):
        return nullcontext()

    def rollback(self):
        self.rollback_count += 1
        self.active = False

    def close(self):
        self.close_count += 1

    def commit(self):
        raise AssertionError("CMIA must not commit")

    def flush(self):
        raise AssertionError("CMIA must not flush")


def _recurring_source(index, amount, frequency, basis="gross"):
    source_id = f"income:{index}"
    source_fp = _sha(str((index % 8) + 1))
    source = {
        "source_id": source_id, "source_fingerprint": source_fp, "amount": amount,
        "amount_basis": basis, "frequency": frequency,
    }
    preimage = {
        "contract": crtisba.RECURRING_AMOUNT_CONTRACT, "client_id": 1,
        "source_id": source_id, "source_fingerprint": source_fp, "amount": amount,
        "amount_basis": basis, "frequency": frequency,
    }
    amount_fp = crtisba.fingerprint(preimage)
    denominator = {"monthly": "1", "quarterly": "3", "annual": "12"}[frequency]
    rtisa_entry = {
        "source_id": source_id, "source_category": "RENTAL", "admission_state": "INCLUDED",
        "upstream_identity": {"source_fingerprint": source_fp, "pension_source_result_fingerprint": None},
        "monthly_equivalent": {"numerator": amount, "denominator": denominator},
    }
    context = {
        "kind": "RECURRING_INCOME", "source_version": source_fp,
        "source_fingerprint": source_fp, "amount": amount_fp,
        "amount_preimage": preimage, "monthly_equivalent": deepcopy(rtisa_entry["monthly_equivalent"]),
    }
    basis_entry = _entry(source_id=source_id)
    basis_entry.update({
        "source_version": source_fp, "source_fingerprint": source_fp,
        "amount_authority_fingerprint": amount_fp,
        "income_basis": "GROSS" if basis == "gross" else "NET",
    })
    return source, rtisa_entry, context, basis_entry


def _pension_source(amount="5000.123456789", source_id="manual:1"):
    source_fp = _sha("a")
    source = {
        "source_id": source_id, "source_fingerprint": source_fp, "version": 3,
        "monthly_amount_basis": {
            "base_amount_semantic_fingerprint": _sha("b"),
            "base_amount_source_fingerprint": _sha("c"),
        },
        "temporal_authority": {
            "temporal_semantic_fingerprint": _sha("d"),
            "temporal_source_fingerprint": _sha("e"),
        },
    }
    rtisa_entry = {
        "source_id": source_id, "source_category": "PENSION", "admission_state": "INCLUDED",
        "upstream_identity": {
            "source_fingerprint": source_fp,
            "pension_source_result_fingerprint": _sha("f"),
        },
        "monthly_equivalent": {"numerator": amount, "denominator": "1"},
    }
    pte = {
        "source_id": source_id, "source_execution_fingerprint": _sha("1"),
        "unquantized_target_monthly_amount": amount,
    }
    portfolio_entry = {"source_id": source_id, "source_entry_fingerprint": _sha("2")}
    preimage = {
        "contract": crtisba.PENSION_AMOUNT_CONTRACT, "client_id": 1, "source_id": source_id,
        "source_version": 3, "source_fingerprint": source_fp,
        "base_amount_semantic_fingerprint": _sha("b"),
        "base_amount_source_fingerprint": _sha("c"),
        "temporal_semantic_fingerprint": _sha("d"),
        "temporal_source_fingerprint": _sha("e"),
        "planning_calculation_input_fingerprint": PLANNING,
        "retirement_target_date": TARGET_DATE,
        "pension_source_execution_fingerprint": _sha("1"),
        "pension_source_result_fingerprint": _sha("f"),
        "portfolio_source_entry_fingerprint": _sha("2"),
        "amount": {"numerator": amount, "denominator": "1", "currency": "ILS", "frequency": "MONTHLY"},
    }
    amount_fp = crtisba.fingerprint(preimage)
    context = {
        "kind": "PENSION", "source_version": 3, "source_fingerprint": source_fp,
        "amount": amount_fp, "pension_source_execution_fingerprint": _sha("1"),
        "pension_source_result_fingerprint": _sha("f"),
        "portfolio_source_entry_fingerprint": _sha("2"), "retirement_target_date": TARGET_DATE,
        "amount_preimage": preimage, "monthly_equivalent": deepcopy(rtisa_entry["monthly_equivalent"]),
    }
    basis_entry = _entry(kind="PENSION", source_id=source_id)
    basis_entry.update({
        "source_version": 3, "source_fingerprint": source_fp,
        "amount_authority_fingerprint": amount_fp,
    })
    return source, rtisa_entry, context, basis_entry, pte, portfolio_entry


def _evidence(*, recurring=(), pension=(), excluded=(), state_override=None):
    planning = {
        "client_id": 1, "planning_calculation_input_fingerprint": PLANNING,
        "retirement_target": {"retirement_target_date": TARGET_DATE},
        "pension_inputs": [], "general_income_inputs": [], "excluded_sources": [],
    }
    rtisa_entries = []
    contexts = {}
    basis_entries = []
    source_results = []
    source_entry_fingerprints = []
    for source in recurring:
        planning_source, rtisa_entry, context, basis_entry = source
        planning["general_income_inputs"].append(planning_source)
        rtisa_entries.append(rtisa_entry)
        contexts[basis_entry["source_id"]] = context
        basis_entries.append(basis_entry)
    for source in pension:
        planning_source, rtisa_entry, context, basis_entry, pte, portfolio_entry = source
        planning["pension_inputs"].append(planning_source)
        rtisa_entries.append(rtisa_entry)
        contexts[basis_entry["source_id"]] = context
        basis_entries.append(basis_entry)
        source_results.append(pte)
        source_entry_fingerprints.append(portfolio_entry)
    for source_id in excluded:
        source_fp = _sha("9")
        planning["excluded_sources"].append({"source_id": source_id, "source_fingerprint": source_fp})
        rtisa_entries.append({
            "source_id": source_id, "source_category": "PENSION_REPRESENTATION",
            "admission_state": "EXCLUDED", "upstream_identity": {"source_fingerprint": source_fp},
            "monthly_equivalent": None,
        })
        contexts[source_id] = {
            "kind": "RECURRING_INCOME", "source_version": source_fp,
            "source_fingerprint": source_fp, "amount": None,
            "amount_preimage": None, "monthly_equivalent": None,
        }
        entry = _entry("NOT_APPLICABLE_DELEGATED", source_id=source_id)
        entry.update({"source_id": source_id, "source_version": source_fp, "source_fingerprint": source_fp})
        basis_entries.append(entry)
    if state_override:
        basis_entries[0].update(state_override)
    basis_entries.sort(key=lambda item: item["source_id"])
    rtisa_entries.sort(key=lambda item: item["source_id"])
    collection = _collection(basis_entries)
    rtisa_result = {
        "client_id": 1, "planning_calculation_input_fingerprint": PLANNING,
        "retirement_target_date": TARGET_DATE, "source_entries": rtisa_entries,
        "admission_result_fingerprint": collection["rtisa_admission_result_fingerprint"],
    }
    target = _target(income="GROSS")
    request = _request()
    comparison = rticb._result(request, target, collection)
    return {
        "comparison": comparison, "target": target, "crtisba_collection": collection,
        "rtisa": rtisa_result, "planning": planning,
        "portfolio": {
            "client_id": 1, "planning_calculation_input_fingerprint": PLANNING,
            "retirement_target_date": TARGET_DATE, "source_results": source_results,
            "source_entry_fingerprints": source_entry_fingerprints,
        },
        "amount_contexts": contexts,
    }


def _run(monkeypatch, evidence, db=None):
    db = db or _DB()
    monkeypatch.setattr(crtisba, "_planning_envelope_valid", lambda *_: True)
    monkeypatch.setattr(crtisba.rtisa_service, "_portfolio_is_valid", lambda *_: True)
    monkeypatch.setattr(crtisba, "_rtisa_envelope_valid", lambda *_: True)
    monkeypatch.setattr(rticb, "assess_with_evidence_in_snapshot", lambda actual, request: deepcopy(evidence))
    return subject.assess(db, _request()), db


def test_empty_and_all_excluded_complete_zero(monkeypatch):
    for evidence, excluded in ((_evidence(), []), (_evidence(excluded=("income:9",)), ["income:9"])):
        result, db = _run(monkeypatch, evidence)
        assert result["result_state"] == "COMPLETE"
        assert result["included_contributions"] == [] and result["source_count"] == 0
        assert result["excluded_source_ids"] == excluded
        assert result["total_monthly_equivalent"] == {
            "numerator": "0", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
        }
        assert db.rollback_count == 1 and not db.in_transaction()


def test_exact_unrounded_pension_and_mixed_recurring_rational_sum(monkeypatch):
    evidence = _evidence(
        pension=(_pension_source(),),
        recurring=(
            _recurring_source(1, "1200.00", "monthly"),
            _recurring_source(2, "1200.00", "quarterly"),
            _recurring_source(3, "1200.00", "annual"),
        ),
    )
    result, _ = _run(monkeypatch, evidence)
    assert [item["source_id"] for item in result["included_contributions"]] == [
        "income:1", "income:2", "income:3", "manual:1",
    ]
    assert result["total_monthly_equivalent"] == {
        "numerator": "6700123456789", "denominator": "1000000000",
        "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["included_contributions"][-1]["monthly_equivalent"] == {
        "numerator": "5000123456789", "denominator": "1000000000",
        "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["source_count"] == 4


def _professional_block_evidence():
    source = _recurring_source(1, "1200.00", "monthly")
    evidence = _evidence(recurring=(source,))
    collection_entry = evidence["crtisba_collection"]["source_basis_entries"][0]
    collection_entry.update({
        "decision_state": "MISSING", "decision_version": None, "decision_fingerprint": None,
        "price_basis": "UNKNOWN", "price_reference_date": None,
        "price_basis_provenance": "MISSING", "blockers": ["CRTISBA_DECISION_MISSING"],
    })
    evidence["crtisba_collection"] = _collection([collection_entry])
    evidence["comparison"] = rticb._result(_request(), evidence["target"], evidence["crtisba_collection"])
    evidence["rtisa"]["source_entries"][0]["monthly_equivalent"] = None
    evidence["amount_contexts"]["income:1"].update(amount=None, amount_preimage=None, monthly_equivalent=None)
    return evidence


def test_valid_not_ready_missing_amount_is_professional_block(monkeypatch):
    evidence = _professional_block_evidence()
    result, _ = _run(monkeypatch, evidence)
    assert result["result_state"] == "BLOCK_NO_TOTAL"
    assert result["failure_stage"] == "comparability"
    assert result["failure_detail_code"] == "CMIA_DIRECT_COMPARISON_NOT_READY"
    assert result["blocked_source_ids"] == ["income:1"]
    assert "total_monthly_equivalent" not in result


def test_blocked_result_has_independently_fixed_fingerprint_golden():
    comparison = {
        "result_state": "complete",
        "comparison_result_fingerprint": _sha("2"),
        "source_comparisons": [
            {"source_id": "income:2", "comparison_state": "BASIS_UNRESOLVED"},
            {"source_id": "income:1", "comparison_state": "NORMALIZATION_REQUIRED"},
        ],
    }
    result = subject._blocked(
        _request(), comparison=comparison,
        collection={"result_fingerprint": _sha("3")},
        rtisa={"admission_result_fingerprint": _sha("4")},
    )
    fingerprint = result.pop("result_fingerprint")
    assert fingerprint == _independent_fingerprint({
        "contract": subject.BLOCK_CONTRACT, "result": result,
    })
    assert fingerprint == "45a8c28046a7b4ac44d721e43efe90548d89898e0b9b035bdf60685c6f005329"
    assert result["blocked_source_ids"] == ["income:1", "income:2"]


def test_valid_upstream_block_is_preserved_and_corrupt_block_is_rejected(monkeypatch):
    target = _target()
    comparison = rticb._failure(
        _request(), "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY", target=target,
    )
    evidence = {
        "comparison": comparison, "target": target, "crtisba_collection": None,
        "rtisa": None, "planning": None, "portfolio": None, "amount_contexts": None,
    }
    result, _ = _run(monkeypatch, evidence)
    assert result["failure_stage"] == "upstream_authority"
    assert result["observed_upstream_failure_stage"] == "target_authority"
    assert result["observed_upstream_failure_detail_code"] == "RTICB_TARGET_AUTHORITY_NOT_READY"
    assert result["observed_upstream_failure_fingerprint"] == comparison["result_fingerprint"]
    corrupt = deepcopy(evidence)
    corrupt["comparison"]["result_fingerprint"] = _sha("0")
    with pytest.raises(subject.CMIAContractError) as caught:
        _run(monkeypatch, corrupt)
    assert (caught.value.stage, caught.value.code) == ("classification", "CMIA_COMPARISON_RESULT_INVALID")


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "source", "amount"])
def test_source_universe_and_amount_authority_tampering_fail_closed(monkeypatch, mutation):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    if mutation == "missing":
        evidence["planning"]["general_income_inputs"] = []
    elif mutation == "duplicate":
        evidence["planning"]["general_income_inputs"].append(
            deepcopy(evidence["planning"]["general_income_inputs"][0])
        )
    elif mutation == "extra":
        evidence["planning"]["general_income_inputs"].append({
            "source_id": "income:2", "source_fingerprint": _sha("3"),
            "amount": "100.00", "amount_basis": "gross", "frequency": "monthly",
        })
    elif mutation == "source":
        evidence["amount_contexts"]["income:1"]["source_version"] = _sha("8")
    else:
        evidence["planning"]["general_income_inputs"][0]["amount"] = "1201.00"
    with pytest.raises(subject.CMIAContractError) as caught:
        _run(monkeypatch, evidence)
    assert caught.value.stage in {"source_universe", "amount_authority"}


@pytest.mark.parametrize("mutation,stage", [
    ("admission", "source_universe"),
    ("rtisa_result_fingerprint", "crtisba_authority"),
])
def test_admission_and_crtisba_rtisa_binding_mutation_killed_and_restored(monkeypatch, mutation, stage):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))

    def ordinary_oracle():
        result, _ = _run(monkeypatch, evidence)
        assert result["result_state"] == "COMPLETE"

    ordinary_oracle()
    if mutation == "admission":
        original = evidence["rtisa"]["source_entries"][0]["admission_state"]
        evidence["rtisa"]["source_entries"][0]["admission_state"] = "EXCLUDED"
    else:
        original = evidence["rtisa"]["admission_result_fingerprint"]
        evidence["rtisa"]["admission_result_fingerprint"] = _sha("0")
    with pytest.raises(subject.CMIAContractError) as caught:
        ordinary_oracle()
    assert caught.value.stage == stage
    if mutation == "admission":
        evidence["rtisa"]["source_entries"][0]["admission_state"] = original
    else:
        evidence["rtisa"]["admission_result_fingerprint"] = original
    ordinary_oracle()


@pytest.mark.parametrize("mutation", ["count", "membership", "ordering", "amount"])
def test_complete_result_fingerprint_covers_contribution_integrity(monkeypatch, mutation):
    result, _ = _run(monkeypatch, _evidence(recurring=(
        _recurring_source(1, "1200.00", "monthly"),
        _recurring_source(2, "900.00", "quarterly"),
    )))
    stored = result["result_fingerprint"]

    def observed_fingerprint(value):
        payload = {key: item for key, item in value.items() if key != "result_fingerprint"}
        return _independent_fingerprint({"contract": subject.RESULT_CONTRACT, "result": payload})

    assert observed_fingerprint(result) == stored
    tampered = deepcopy(result)
    if mutation == "count":
        tampered["source_count"] += 1
    elif mutation == "membership":
        tampered["included_contributions"].pop()
    elif mutation == "ordering":
        tampered["included_contributions"].reverse()
    else:
        tampered["included_contributions"][0]["monthly_equivalent"]["numerator"] = "1201"
    assert observed_fingerprint(tampered) != stored
    assert observed_fingerprint(result) == stored


def test_rounded_pension_substitution_rejected_against_authoritative_producer_amount(monkeypatch):
    evidence = _evidence(pension=(_pension_source(),))

    def ordinary_oracle():
        result, _ = _run(monkeypatch, evidence)
        assert result["included_contributions"][0]["monthly_equivalent"]["numerator"] == "5000123456789"

    ordinary_oracle()
    authoritative = evidence["portfolio"]["source_results"][0]["unquantized_target_monthly_amount"]
    assert authoritative == "5000.123456789"
    original_rtisa = deepcopy(evidence["rtisa"]["source_entries"][0]["monthly_equivalent"])
    original_context = deepcopy(evidence["amount_contexts"]["manual:1"]["monthly_equivalent"])
    rounded = {"numerator": "5000.12", "denominator": "1"}
    evidence["rtisa"]["source_entries"][0]["monthly_equivalent"] = deepcopy(rounded)
    evidence["amount_contexts"]["manual:1"]["monthly_equivalent"] = deepcopy(rounded)
    with pytest.raises(subject.CMIAContractError) as caught:
        ordinary_oracle()
    assert (caught.value.stage, caught.value.code) == (
        "amount_authority", "CMIA_RTISA_AMOUNT_INVALID",
    )
    evidence["rtisa"]["source_entries"][0]["monthly_equivalent"] = original_rtisa
    evidence["amount_contexts"]["manual:1"]["monthly_equivalent"] = original_context
    ordinary_oracle()


@pytest.mark.parametrize("numerator,denominator", [
    ("1200.00", "0"), ("1200.00", "-1"), ("+1200.00", "1"),
    ("01.00", "1"), ("NaN", "1"), ("1200.00", "01"),
])
def test_malformed_rtisa_rationals_are_rejected(monkeypatch, numerator, denominator):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    evidence["rtisa"]["source_entries"][0]["monthly_equivalent"] = {
        "numerator": numerator, "denominator": denominator,
    }
    evidence["amount_contexts"]["income:1"]["monthly_equivalent"] = {
        "numerator": numerator, "denominator": denominator,
    }
    with pytest.raises(subject.CMIAContractError) as caught:
        _run(monkeypatch, evidence)
    assert caught.value.code == "CMIA_RTISA_AMOUNT_INVALID"


def test_closed_result_keys_fingerprints_and_independent_golden(monkeypatch):
    result, _ = _run(monkeypatch, _evidence(recurring=(_recurring_source(1, "1200.00", "quarterly"),)))
    assert set(result) == {
        "schema_version", "result_state", "client_id", "planning_calculation_input_fingerprint",
        "retirement_target_date", "target_result_fingerprint", "target_semantic_fingerprint",
        "comparison_input_fingerprint", "comparison_result_fingerprint", "crtisba_result_fingerprint",
        "rtisa_admission_result_fingerprint", "target_income_basis", "target_price_basis",
        "target_price_reference_date", "included_contributions", "excluded_source_ids",
        "total_monthly_equivalent", "source_count", "result_fingerprint",
    }
    contribution = result["included_contributions"][0]
    assert set(contribution) == {
        "source_id", "source_kind", "source_version", "source_fingerprint",
        "amount_authority_fingerprint", "source_comparison_fingerprint", "monthly_equivalent",
        "contribution_fingerprint",
    }
    raw_contribution = {key: value for key, value in contribution.items() if key != "contribution_fingerprint"}
    assert contribution["contribution_fingerprint"] == subject._fingerprint({
        "contract": subject.CONTRIBUTION_CONTRACT, "contribution": raw_contribution,
    }, 1)
    raw_result = {key: value for key, value in result.items() if key != "result_fingerprint"}
    assert result["result_fingerprint"] == subject._fingerprint({
        "contract": subject.RESULT_CONTRACT, "result": raw_result,
    }, 1)
    assert result["result_fingerprint"] == "9da1a2e4d4decc54dfa94938a093bd8356259559e0a647166759d67b863c084f"


@pytest.mark.parametrize("payload,code,client_id", [
    ({}, "CMIA_REQUEST_SCHEMA_INVALID", None),
    (_request(client_id=True), "CMIA_CLIENT_ID_INVALID", None),
    (_request(expected_planning_calculation_input_fingerprint="x"), "CMIA_EXPECTED_PLANNING_FINGERPRINT_INVALID", 1),
    (_request(expected_retirement_target_date="2030-02-30"), "CMIA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID", 1),
])
def test_request_rejection_precedes_database(monkeypatch, payload, code, client_id):
    db = _DB()
    monkeypatch.setattr(db, "get_bind", lambda: (_ for _ in ()).throw(AssertionError("database touched")))
    with pytest.raises(subject.CMIAContractError) as caught:
        subject.assess(db, payload)
    assert (caught.value.code, caught.value.client_id) == (code, client_id)


def test_internal_exception_identity_is_immutable():
    error = subject.CMIAContractError("classification", "CMIA_COMPARISON_RESULT_INVALID", 1)
    assert (error.stage, error.code, error.client_id) == (
        "classification", "CMIA_COMPARISON_RESULT_INVALID", 1,
    )
    for attribute in ("_stage", "_code", "_client_id"):
        with pytest.raises(AttributeError, match="immutable"):
            setattr(error, attribute, "forged")


def test_single_snapshot_no_nested_public_reader_and_rollback(monkeypatch):
    evidence = _evidence()
    db = _DB()
    calls = []
    monkeypatch.setattr(crtisba, "_planning_envelope_valid", lambda *_: True)
    monkeypatch.setattr(crtisba.rtisa_service, "_portfolio_is_valid", lambda *_: True)
    monkeypatch.setattr(crtisba, "_rtisa_envelope_valid", lambda *_: True)
    monkeypatch.setattr(rticb, "assess", lambda *_: (_ for _ in ()).throw(AssertionError("nested reader")))
    monkeypatch.setattr(
        rticb, "assess_with_evidence_in_snapshot",
        lambda actual, request: calls.append((actual, request)) or deepcopy(evidence),
    )
    result = subject.assess(db, _request())
    assert result["result_state"] == "COMPLETE"
    assert calls == [(db, _request())]
    assert db.rollback_count == 1 and not db.in_transaction()


def test_original_exception_propagates_after_rollback_and_cleanup_failure_wins(monkeypatch):
    db = _DB()
    monkeypatch.setattr(
        rticb, "assess_with_evidence_in_snapshot",
        lambda *_: (_ for _ in ()).throw(RuntimeError("producer")),
    )
    with pytest.raises(RuntimeError, match="producer"):
        subject.assess(db, _request())
    assert db.rollback_count == 1

    engine = create_engine("sqlite://")
    failed = Session(engine)
    monkeypatch.setattr(failed, "rollback", lambda: (_ for _ in ()).throw(OSError("cleanup")))
    with pytest.raises(OSError, match="cleanup"):
        subject.assess(failed, _request())
    with pytest.raises(InvalidRequestError, match="permanently unusable"):
        failed.scalar(text("SELECT 1"))


def test_rollback_failure_after_accepted_professional_block_takes_precedence(monkeypatch):
    class RollbackFailureDB(_DB):
        def rollback(self):
            raise OSError("block cleanup")

    evidence = _professional_block_evidence()
    blocked_calls = []
    original = subject._blocked

    def observed_block(*args, **kwargs):
        result = original(*args, **kwargs)
        blocked_calls.append(result)
        return result

    monkeypatch.setattr(subject, "_blocked", observed_block)
    failed = RollbackFailureDB()
    with pytest.raises(OSError, match="block cleanup"):
        _run(monkeypatch, evidence, failed)
    assert len(blocked_calls) == 1
    assert blocked_calls[0]["result_state"] == "BLOCK_NO_TOTAL"
    assert blocked_calls[0]["failure_detail_code"] == "CMIA_DIRECT_COMPARISON_NOT_READY"


def test_rollback_exception_survives_connection_and_session_cleanup_failures(monkeypatch):
    class InvalidationFailureConnection(_Connection):
        def __init__(self, db):
            super().__init__(db)
            self.invalidate_count = 0

        def invalidate(self):
            self.invalidate_count += 1
            raise RuntimeError("connection invalidation")

    class CleanupFailureDB(_DB):
        def __init__(self):
            super().__init__()
            self.connection_value = InvalidationFailureConnection(self)
            self.session_invalidate_count = 0

        def rollback(self):
            raise OSError("rollback primary")

        def invalidate(self):
            self.session_invalidate_count += 1
            raise RuntimeError("session cleanup")

    failed = CleanupFailureDB()
    monkeypatch.setattr(subject.event, "contains", lambda *_: False)
    monkeypatch.setattr(subject.event, "listen", lambda *_: None)
    monkeypatch.setattr(
        rticb, "assess_with_evidence_in_snapshot",
        lambda *_: (_ for _ in ()).throw(RuntimeError("technical original")),
    )
    with pytest.raises(OSError, match="rollback primary"):
        subject.assess(failed, _request())
    assert failed.connection_value.invalidate_count == 1
    assert failed.session_invalidate_count == 1


def test_connection_acquisition_defines_transaction_ownership(monkeypatch):
    class AcquisitionFailureDB(_DB):
        def connection(self):
            raise OSError("acquisition")

    failed = AcquisitionFailureDB()
    with pytest.raises(OSError, match="acquisition"):
        subject.assess(failed, _request())
    assert failed.rollback_count == 0

    class PostAcquisitionFailureDB(_DB):
        def expire_all(self):
            raise OSError("post-acquisition")

    acquired = PostAcquisitionFailureDB()
    with pytest.raises(OSError, match="post-acquisition"):
        subject.assess(acquired, _request())
    assert acquired.rollback_count == 1


def test_rollback_failure_invalidates_retained_connection_without_lookup(monkeypatch):
    class RetainedConnectionDB(_DB):
        def __init__(self):
            super().__init__()
            self.connection_calls = 0

        def connection(self):
            self.connection_calls += 1
            if self.connection_calls > 1:
                raise AssertionError("connection lookup after acquisition")
            return super().connection()

        def rollback(self):
            raise OSError("cleanup")

    failed = RetainedConnectionDB()
    monkeypatch.setattr(
        rticb, "assess_with_evidence_in_snapshot",
        lambda *_: (_ for _ in ()).throw(RuntimeError("producer")),
    )
    with pytest.raises(OSError, match="cleanup"):
        subject.assess(failed, _request())
    assert failed.connection_calls == 1
    assert failed.connection_value.invalidated is True


def test_public_rticb_and_crtisba_outputs_remain_byte_identical(monkeypatch):
    target = _target()
    collection = _collection([_entry()])
    request = _request()
    expected = rticb._result(request, target, collection)
    db = _DB()
    monkeypatch.setattr(rticb.target_service, "assess_in_snapshot", lambda *_: deepcopy(target))
    monkeypatch.setattr(rticb.crtisba_service, "derive_in_snapshot", lambda *_args, **_kwargs: deepcopy(collection))
    actual = rticb.assess(db, request)
    assert actual == expected


def test_amount_selection_mapping_mutation_fails_same_ordinary_oracle_and_restores(monkeypatch):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "quarterly"),))

    def ordinary_oracle():
        result, _ = _run(monkeypatch, evidence)
        assert result["total_monthly_equivalent"] == {
            "numerator": "400", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
        }

    ordinary_oracle()
    original = subject._reconstruct_amount

    def redirected(*args, **kwargs):
        preimage, _monthly = original(*args, **kwargs)
        return preimage, {"numerator": "1200.00", "denominator": "1"}

    monkeypatch.setattr(subject, "_reconstruct_amount", redirected)
    mutant_killed = False
    try:
        ordinary_oracle()
    except BaseException:
        mutant_killed = True
    assert mutant_killed
    monkeypatch.setattr(subject, "_reconstruct_amount", original)
    ordinary_oracle()


def test_source_universe_guard_mutation_fails_same_negative_oracle_and_restores(monkeypatch):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    evidence["planning"]["general_income_inputs"].append({
        "source_id": "income:2", "source_fingerprint": _sha("3"),
        "amount": "100.00", "amount_basis": "gross", "frequency": "monthly",
    })

    def ordinary_oracle():
        with pytest.raises(subject.CMIAContractError) as caught:
            _run(monkeypatch, evidence)
        assert caught.value.code == "CMIA_SOURCE_UNIVERSE_MISMATCH"

    ordinary_oracle()
    original = subject._planning_sources
    monkeypatch.setattr(
        subject, "_planning_sources",
        lambda planning, client_id: {
            key: value for key, value in original(planning, client_id).items() if key != "income:2"
        },
    )
    mutant_killed = False
    try:
        ordinary_oracle()
    except BaseException:
        mutant_killed = True
    assert mutant_killed
    monkeypatch.setattr(subject, "_planning_sources", original)
    ordinary_oracle()


def test_rollback_mapping_mutation_fails_same_ordinary_oracle_and_restores(monkeypatch):
    evidence = _evidence()

    def ordinary_oracle():
        db = _DB()
        result, _ = _run(monkeypatch, evidence, db)
        assert result["result_state"] == "COMPLETE"
        assert db.rollback_count == 1 and not db.in_transaction()

    ordinary_oracle()
    original = subject._rollback_owned_transaction
    monkeypatch.setattr(subject, "_rollback_owned_transaction", lambda _db, _connection: None)
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "_rollback_owned_transaction", original)
    ordinary_oracle()
