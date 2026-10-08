from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as subject
from app.services import retirement_target_date_income_source_admission_service as rtisa_service


PLANNING = "1" * 64
TARGET_FP = "2" * 64
RTISA_FP = "3" * 64
TARGET_DATE = "2030-01-01"


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _target(*, client_id=1, planning=PLANNING, target_date=TARGET_DATE,
            income="GROSS", price="NOMINAL_AT_RETIREMENT_TARGET_DATE", reference=None,
            state="CURRENT", ready=True):
    target = {
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning,
        "retirement_target_date": target_date,
        "monthly_amount": "10000",
        "currency": "ILS",
        "income_basis": income,
        "price_basis": price,
        "price_reference_date": reference,
    }
    authority = {
        "record_version": 1,
        "source_kind": "PLANNER_SUPPLIED",
        "confirmation_state": "CONFIRMED",
        "confirmation_actor": "planner:test",
        "confirmed_at": "2026-01-01T00:00:00.000000Z",
        "lifecycle_state": "CONFIRMED" if state == "CURRENT" else "STALE",
    }
    result = {
        "schema_version": target_service.SCHEMA_VERSION,
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning,
        "retirement_target_date": target_date,
        "target": target,
        "authority": authority,
        "authority_state": state,
        "target_readiness_state": "READY" if ready else "NOT_READY",
        "target_ready": ready,
        "blockers": [] if ready else ["RIT_RECONFIRMATION_REQUIRED"],
        "target_semantic_fingerprint": _digest({"contract": target_service.SEMANTIC_CONTRACT, **target}),
    }
    result["target_result_fingerprint"] = _digest({"contract": target_service.RESULT_CONTRACT, **result})
    return result


def _entry(source_id="income:1", *, admission="INCLUDED", income="GROSS",
           price="NOMINAL_AT_RETIREMENT_TARGET_DATE", reference=None,
           source_fingerprint="4" * 64, pension_fingerprint=None, resolution=None):
    return {
        "source_id": source_id,
        "source_category": "RENTAL",
        "source_authority": "CANONICAL_PLANNING_RECURRING_INCOME",
        "admission_state": admission,
        "native_amount": {"amount": "1200.00", "currency": "ILS", "frequency": "MONTHLY"},
        "monthly_equivalent": {"numerator": "1200.00", "denominator": "1"},
        "native_income_basis": income,
        "native_tax_characterization": {"kind": "UNKNOWN", "value": None},
        "native_price_evidence": {
            "price_basis": price,
            "price_reference_date": reference,
            "temporal_authority_kind": None,
            "temporal_origin_date": None,
            "annual_rate": None,
            "rate_basis": None,
        },
        "applicability": {
            "start_date": "2025-01-01", "end_date": None,
            "continuation_status": "ongoing", "at_target": "ACTIVE" if admission == "INCLUDED" else "FUTURE",
        },
        "provenance": {
            "origin_kind": "recurring_income", "source_status": "planner entered",
            "verification_state": "reviewed",
        },
        "upstream_identity": {
            "source_fingerprint": source_fingerprint,
            "pension_source_result_fingerprint": pension_fingerprint,
            "resolution": resolution,
        },
        "reason_codes": [] if admission == "INCLUDED" else ["RTISA_FUTURE_SOURCE"],
    }


def _rtisa(entries, *, client_id=1, planning=PLANNING, target_date=TARGET_DATE,
           completeness="COMPLETE_EVIDENCED", readiness="READY", ready=True):
    ordered = sorted(deepcopy(entries), key=lambda item: item["source_id"])
    result = {
        "schema_version": rtisa_service.SCHEMA_VERSION,
        "client_id": client_id,
        "planning_calculation_input_fingerprint": planning,
        "retirement_target_date": target_date,
        "pension_portfolio_result_fingerprint": "5" * 64,
        "source_entries": ordered,
        "included_source_ids": sorted(item["source_id"] for item in ordered if item["admission_state"] == "INCLUDED"),
        "excluded_source_ids": sorted(item["source_id"] for item in ordered if item["admission_state"] == "EXCLUDED"),
        "unresolved_source_ids": sorted(item["source_id"] for item in ordered if item["admission_state"] == "UNRESOLVED"),
        "universe_completeness_state": completeness,
        "admission_readiness_state": readiness,
        "admission_ready": ready,
        "blockers": [] if ready else ["RTISA_SOURCE_UNIVERSE_INCOMPLETE"],
    }
    result["admission_result_fingerprint"] = _digest({"contract": rtisa_service.RESULT_CONTRACT, **result})
    return result


def _rehash_rtisa(result):
    result = deepcopy(result)
    result.pop("admission_result_fingerprint", None)
    result["admission_result_fingerprint"] = _digest({"contract": rtisa_service.RESULT_CONTRACT, **result})
    return result


def _rehash_target(result):
    result = deepcopy(result)
    if result["target"] is None:
        result["target_semantic_fingerprint"] = None
    else:
        result["target_semantic_fingerprint"] = _digest({
            "contract": target_service.SEMANTIC_CONTRACT,
            **result["target"],
        })
    result.pop("target_result_fingerprint", None)
    result["target_result_fingerprint"] = _digest({
        "contract": target_service.RESULT_CONTRACT,
        **result,
    })
    return result


def _assert_exact_failure_fingerprint(result):
    failure = {key: value for key, value in result.items() if key != "result_fingerprint"}
    assert result["result_fingerprint"] == _digest({
        "contract": subject.FAILURE_FINGERPRINT_CONTRACT,
        "failure": failure,
    })


class _Connection:
    def __init__(self, db):
        self.db = db
        self.dialect = SimpleNamespace(name=db.dialect)
        self.commands = []
        self.invalidated = False

    def exec_driver_sql(self, command):
        self.commands.append(command)

    def invalidate(self):
        self.invalidated = True


class _DB:
    def __init__(self, *, dialect="sqlite", active=False):
        self.dialect = dialect
        self.active = active
        self.new = set()
        self.dirty = set()
        self.deleted = set()
        self.connection_value = _Connection(self)
        self.rollback_count = 0
        self.expire_count = 0

    def in_transaction(self):
        return self.active

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))

    def connection(self):
        self.active = True
        return self.connection_value

    def expire_all(self):
        self.expire_count += 1

    @property
    def no_autoflush(self):
        return nullcontext()

    def rollback(self):
        self.rollback_count += 1
        self.active = False

    def commit(self):
        raise AssertionError("RTICB must not commit")

    def flush(self):
        raise AssertionError("RTICB must not flush")


def _request(**changes):
    value = {
        "client_id": 1,
        "expected_planning_calculation_input_fingerprint": PLANNING,
        "expected_retirement_target_date": TARGET_DATE,
    }
    value.update(changes)
    return value


def _run(monkeypatch, *, target=None, rtisa=None, request=None, db=None):
    target = target or _target()
    rtisa = rtisa or _rtisa([_entry()])
    reached = {"target": 0, "rtisa": 0}

    def target_reader(received_db, client_id):
        reached["target"] += 1
        assert received_db is db_value and client_id == 1
        return deepcopy(target)

    def rtisa_reader(received_db, client_id, expected):
        reached["rtisa"] += 1
        assert received_db is db_value and client_id == 1 and expected == PLANNING
        return deepcopy(rtisa)

    db_value = db or _DB()
    monkeypatch.setattr(subject.target_service, "assess_in_snapshot", target_reader)
    monkeypatch.setattr(subject.rtisa_service, "read_in_snapshot", rtisa_reader)
    result = subject.assess(db_value, request or _request())
    return result, db_value, reached


INCLUDED_OUTPUT_CLASSES = [
    ("gross_nominal_direct", "GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "DIRECTLY_COMPARABLE", [], []),
    ("gross_nominal_real_mismatch", "GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_PRICE_BASIS_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("gross_nominal_real_missing", "GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_PRICE_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
    ("gross_real_direct", "GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-01-01", "DIRECTLY_COMPARABLE", [], []),
    ("gross_real_date_mismatch", "GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-02-01", "NORMALIZATION_REQUIRED", ["RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("gross_real_missing", "GROSS", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
    ("net_nominal_direct", "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("net_nominal_real_mismatch", "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_PRICE_BASIS_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("net_nominal_real_missing", "NET", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_PRICE_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
    ("net_real_direct", "NET", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-01-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("net_real_date_mismatch", "NET", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-02-01", "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"], ["RTICB_NORMALIZATION_REQUIRED"]),
    ("net_real_missing", "NET", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_nominal_direct", "UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_nominal_real_mismatch", "UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", "2029-01-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_PRICE_BASIS_MISMATCH"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_nominal_real_missing", "UNKNOWN", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None, "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_PRICE_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_real_direct", "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-01-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_real_date_mismatch", "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", "2029-02-01", "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"], ["RTICB_BASIS_UNRESOLVED"]),
    ("unknown_real_missing", "UNKNOWN", "REAL_AT_REFERENCE_DATE", "2029-01-01", "REAL_AT_REFERENCE_DATE", None, "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"], ["RTICB_BASIS_UNRESOLVED"]),
]


@pytest.mark.parametrize(
    "name,source_income,target_price,target_reference,source_price,source_reference,expected_state,expected_reasons,expected_blockers",
    INCLUDED_OUTPUT_CLASSES,
    ids=[case[0] for case in INCLUDED_OUTPUT_CLASSES],
)
def test_all_18_distinct_included_output_classes(
    monkeypatch, name, source_income, target_price, target_reference,
    source_price, source_reference, expected_state, expected_reasons, expected_blockers,
):
    result, db, reached = _run(
        monkeypatch,
        target=_target(price=target_price, reference=target_reference),
        rtisa=_rtisa([_entry(income=source_income, price=source_price, reference=source_reference)]),
    )
    comparison = result["source_comparisons"][0]
    assert comparison["comparison_state"] == expected_state
    assert comparison["reason_codes"] == expected_reasons
    expected_comparison = {
        "source_id": "income:1",
        "rtisa_admission_state": "INCLUDED",
        "source_upstream_identity": _entry()["upstream_identity"],
        "source_income_basis": source_income,
        "source_price_basis": source_price,
        "source_price_reference_date": source_reference,
        "comparison_state": expected_state,
        "reason_codes": expected_reasons,
    }
    assert comparison["source_comparison_fingerprint"] == _digest({
        "contract": subject.ENTRY_FINGERPRINT_CONTRACT,
        "comparison_input_fingerprint": result["comparison_input_fingerprint"],
        "source_comparison": expected_comparison,
    }), name
    assert result["blockers"] == expected_blockers
    assert result["direct_comparison_ready"] is (not expected_blockers)
    assert reached == {"target": 1, "rtisa": 1}
    assert db.rollback_count == 1 and not db.active


def test_included_matrix_has_18_distinct_contract_classes_and_net_net_positive_control(monkeypatch):
    identities = {
        (case[1], case[2], case[3], case[4], case[5], case[6], tuple(case[7]))
        for case in INCLUDED_OUTPUT_CLASSES
    }
    assert len(INCLUDED_OUTPUT_CLASSES) == len(identities) == 18
    result, _, _ = _run(
        monkeypatch,
        target=_target(income="NET"),
        rtisa=_rtisa([_entry(income="NET")]),
    )
    comparison = result["source_comparisons"][0]
    assert comparison["comparison_state"] == "DIRECTLY_COMPARABLE"
    assert comparison["reason_codes"] == []
    assert result["direct_comparison_ready"] is True


@pytest.mark.parametrize("income,price,reference", [
    ("GROSS", "NOMINAL_AT_RETIREMENT_TARGET_DATE", None),
    ("UNKNOWN", "UNKNOWN", None),
    ("NET", "REAL_AT_REFERENCE_DATE", None),
])
def test_excluded_positive_controls_preserve_basis_without_comparison(monkeypatch, income, price, reference):
    result, _, _ = _run(monkeypatch, rtisa=_rtisa([
        _entry(admission="EXCLUDED", income=income, price=price, reference=reference)
    ]))
    comparison = result["source_comparisons"][0]
    assert comparison["comparison_state"] == "NOT_ADMITTED"
    assert comparison["reason_codes"] == ["RTICB_SOURCE_NOT_ADMITTED"]
    assert comparison["source_income_basis"] == income
    assert comparison["source_price_basis"] == price
    assert comparison["source_price_reference_date"] == reference


@pytest.mark.parametrize("mutation", [
    lambda entry: entry.update(native_income_basis=None),
    lambda entry: entry.update(native_income_basis=" GROSS"),
    lambda entry: entry.update(native_income_basis="OTHER"),
    lambda entry: entry.update(native_income_basis=["GROSS"]),
    lambda entry: entry["native_price_evidence"].update(price_basis=None),
    lambda entry: entry["native_price_evidence"].update(price_basis="OTHER"),
    lambda entry: entry["native_price_evidence"].update(price_basis=["UNKNOWN"]),
    lambda entry: entry["native_price_evidence"].update(price_basis=" REAL_AT_REFERENCE_DATE"),
    lambda entry: entry["native_price_evidence"].update(price_basis="REAL_AT_REFERENCE_DATE", price_reference_date="2030-99-01"),
    lambda entry: entry["native_price_evidence"].update(price_basis="NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date="2029-01-01"),
    lambda entry: entry["native_price_evidence"].update(price_basis="UNKNOWN", price_reference_date="2029-01-01"),
])
def test_malformed_excluded_basis_is_fatal_after_independent_rtisa_rehash(monkeypatch, mutation):
    entry = _entry(admission="EXCLUDED")
    mutation(entry)
    rtisa = _rtisa([entry])
    result, _, reached = _run(monkeypatch, rtisa=rtisa)
    assert result["result_state"] == "block_no_result"
    assert result["failure_stage"] == "classification"
    assert result["failure_detail_code"] == "RTICB_SOURCE_BASIS_EVIDENCE_INVALID"
    assert result["observed_target_result_fingerprint"] is not None
    assert result["observed_rtisa_admission_result_fingerprint"] == rtisa["admission_result_fingerprint"]
    assert "source_comparisons" not in result
    assert reached == {"target": 1, "rtisa": 1}


@pytest.mark.parametrize("admission", ["INCLUDED", "EXCLUDED"])
@pytest.mark.parametrize("missing", [
    "native_income_basis",
    "native_price_evidence",
    "native_price_evidence.price_basis",
    "native_price_evidence.price_reference_date",
])
def test_missing_basis_keys_route_to_classification_with_exact_identity(
    monkeypatch, admission, missing,
):
    entry = _entry(admission=admission)
    container = entry
    key = missing
    if "." in missing:
        outer, key = missing.split(".")
        container = entry[outer]
    del container[key]
    rtisa = _rtisa([entry])
    result, _, reached = _run(monkeypatch, rtisa=rtisa)
    assert result["result_state"] == "block_no_result"
    assert result["failure_stage"] == "classification"
    assert result["failure_detail_code"] == "RTICB_SOURCE_BASIS_EVIDENCE_INVALID"
    assert result["observed_target_result_fingerprint"] is not None
    assert result["observed_rtisa_admission_result_fingerprint"] == rtisa["admission_result_fingerprint"]
    assert "source_comparisons" not in result
    _assert_exact_failure_fingerprint(result)
    assert reached == {"target": 1, "rtisa": 1}


@pytest.mark.parametrize("source_id", [
    " income:1", "income:1 ", "\tincome:1", "income:1\n",
    "\u00a0income:1", "income:1\u00a0", "income:\x001", "",
])
def test_source_ids_must_be_canonical_without_ascii_or_unicode_repair(monkeypatch, source_id):
    result, _, _ = _run(monkeypatch, rtisa=_rtisa([_entry(source_id)]))
    assert result["failure_stage"] == "source_universe"
    assert result["failure_detail_code"] == "RTICB_SOURCE_UNIVERSE_INVALID"


def test_valid_non_ascii_source_id_and_partition_are_preserved(monkeypatch):
    source_id = "הכנסה:קצבה"
    result, _, _ = _run(monkeypatch, rtisa=_rtisa([_entry(source_id)]))
    assert result["directly_comparable_source_ids"] == [source_id]
    assert result["source_comparisons"][0]["source_id"] == source_id


def test_partition_ids_use_same_unicode_canonicality_contract(monkeypatch):
    rtisa = _rtisa([_entry()])
    rtisa["included_source_ids"] = ["\u00a0income:1"]
    rtisa = _rehash_rtisa(rtisa)
    result, _, _ = _run(monkeypatch, rtisa=rtisa)
    assert result["failure_stage"] == "source_universe"
    assert result["failure_detail_code"] == "RTICB_SOURCE_COVERAGE_MISMATCH"


def test_empty_all_excluded_and_mixed_universes(monkeypatch):
    empty, _, _ = _run(monkeypatch, rtisa=_rtisa([]))
    assert empty["source_comparisons"] == [] and empty["direct_comparison_ready"] is True
    excluded, _, _ = _run(monkeypatch, rtisa=_rtisa([
        _entry("income:1", admission="EXCLUDED"),
        _entry("income:2", admission="EXCLUDED", income="UNKNOWN", price="UNKNOWN"),
    ]))
    assert excluded["not_admitted_source_ids"] == ["income:1", "income:2"]
    assert excluded["direct_comparison_ready"] is True
    mixed, _, _ = _run(monkeypatch, rtisa=_rtisa([
        _entry("income:1"), _entry("income:2", admission="EXCLUDED"),
    ]))
    assert mixed["directly_comparable_source_ids"] == ["income:1"]
    assert mixed["not_admitted_source_ids"] == ["income:2"]


@pytest.mark.parametrize("request_value,code", [
    (None, "RTICB_REQUEST_SCHEMA_INVALID"),
    ({}, "RTICB_REQUEST_SCHEMA_INVALID"),
    ({**_request(), "extra": 1}, "RTICB_REQUEST_SCHEMA_INVALID"),
    (_request(client_id=True), "RTICB_CLIENT_ID_INVALID"),
    (_request(expected_planning_calculation_input_fingerprint="A" * 64), "RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID"),
    (_request(expected_retirement_target_date="2030-01-01T00:00:00"), "RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID"),
])
def test_request_failures_precede_database_and_have_exact_identity(request_value, code):
    class Untouched:
        def __getattribute__(self, name):
            if name.startswith("__"):
                return object.__getattribute__(self, name)
            raise AssertionError("database touched")

    result = subject.assess(Untouched(), request_value)
    assert result["failure_stage"] == "request_validation"
    assert result["failure_detail_code"] == code


def test_fresh_transaction_rejection_never_mutates_caller(monkeypatch):
    db = _DB(active=True)
    db.rollback = lambda: (_ for _ in ()).throw(AssertionError("caller transaction mutated"))
    result = subject.assess(db, _request())
    assert result["failure_stage"] == "snapshot_admission"
    assert result["failure_detail_code"] == "RTICB_REQUIRES_FRESH_TRANSACTION"
    assert db.active is True


def test_fresh_transaction_rejection_oracle_kills_caller_rollback_mutation(monkeypatch):
    original = subject.assess
    reached = []

    def mutated(db, request):
        if db.in_transaction():
            reached.append("caller_rollback")
            db.rollback()
        return subject._failure(
            request, "snapshot_admission", "RTICB_REQUIRES_FRESH_TRANSACTION"
        )

    def ordinary_oracle(db):
        result = subject.assess(db, _request())
        assert result["failure_detail_code"] == "RTICB_REQUIRES_FRESH_TRANSACTION"
        assert db.active is True, "caller-owned transaction must remain active"

    monkeypatch.setattr(subject, "assess", mutated)
    with pytest.raises(AssertionError, match="caller-owned transaction"):
        ordinary_oracle(_DB(active=True))
    assert reached == ["caller_rollback"]

    monkeypatch.setattr(subject, "assess", original)
    ordinary_oracle(_DB(active=True))


def test_unsupported_database_is_semantic_and_opens_no_connection():
    db = _DB(dialect="oracle")
    db.connection = lambda: (_ for _ in ()).throw(AssertionError("connection opened"))
    result = subject.assess(db, _request())
    assert result["failure_detail_code"] == "RTICB_UNSUPPORTED_DATABASE"


def test_category_b_target_and_rtisa_mutations_fail_closed(monkeypatch):
    bad_target = _target(); bad_target["target"]["income_basis"] = "NET"
    result, _, reached = _run(monkeypatch, target=bad_target)
    assert result["failure_detail_code"] == "RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID"
    assert reached == {"target": 1, "rtisa": 0}
    bad_rtisa = _rtisa([_entry()]); bad_rtisa["source_entries"][0]["native_income_basis"] = "NET"
    result, _, _ = _run(monkeypatch, rtisa=bad_rtisa)
    assert result["failure_detail_code"] == "RTICB_RTISA_AUTHORITY_FINGERPRINT_INVALID"


@pytest.mark.parametrize("mutation", [
    lambda value: value["target"].update(monthly_amount="abc"),
    lambda value: value["target"].update(monthly_amount="0"),
    lambda value: value["target"].update(monthly_amount="-1"),
    lambda value: value["target"].update(monthly_amount="01.00"),
    lambda value: value["authority"].update(confirmed_at="2026-02-30T00:00:00.000000Z"),
    lambda value: value["authority"].update(record_version=target_service.MAX_VERSION + 1),
    lambda value: value["authority"].update(confirmation_actor="x" * 129),
    lambda value: value["authority"].update(lifecycle_state="STALE"),
    lambda value: value.update(blockers=["RIT_INVENTED_BLOCKER"]),
])
def test_rehashed_noncanonical_target_results_fail_schema_validation(monkeypatch, mutation):
    target = _target()
    mutation(target)
    target = _rehash_target(target)
    result, _, reached = _run(monkeypatch, target=target)
    assert result["failure_stage"] == "target_authority"
    assert result["failure_detail_code"] == "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID"
    _assert_exact_failure_fingerprint(result)
    assert reached == {"target": 1, "rtisa": 0}


def test_canonical_target_current_stale_missing_unavailable_and_nullable_invalid_routes():
    current = _target()
    stale = _target(state="STALE", ready=False)

    missing = _target()
    missing.update(
        target=None,
        authority=None,
        authority_state="MISSING",
        target_readiness_state="NOT_READY",
        target_ready=False,
        blockers=["RIT_TARGET_MISSING"],
    )
    missing = _rehash_target(missing)

    unavailable = _target()
    unavailable.update(
        planning_calculation_input_fingerprint=None,
        retirement_target_date=None,
        target=None,
        authority=None,
        authority_state="UNAVAILABLE",
        target_readiness_state="NOT_READY",
        target_ready=False,
        blockers=["RIT_PLANNING_CONTEXT_UNAVAILABLE"],
    )
    unavailable = _rehash_target(unavailable)

    invalid = _target()
    invalid.update(
        authority=None,
        authority_state="INVALID",
        target_readiness_state="NOT_READY",
        target_ready=False,
        blockers=["RIT_CONFIRMATION_MISSING"],
    )
    invalid = _rehash_target(invalid)

    invalid_with_stale_authority = _target()
    invalid_with_stale_authority["authority"]["lifecycle_state"] = "STALE"
    invalid_with_stale_authority.update(
        target=None,
        authority_state="INVALID",
        target_readiness_state="NOT_READY",
        target_ready=False,
        blockers=["RIT_TARGET_RECORD_INVALID"],
    )
    invalid_with_stale_authority = _rehash_target(invalid_with_stale_authority)

    for result in (current, stale, missing, unavailable, invalid, invalid_with_stale_authority):
        assert subject._target_schema_valid(result)
        assert subject._target_fingerprints_valid(result)


def test_wrong_type_enums_and_resolution_relationships_are_semantic_schema_failures(monkeypatch):
    bad_target = _target()
    bad_target["target"]["income_basis"] = ["GROSS"]
    bad_target["target_result_fingerprint"] = _digest({
        "contract": target_service.RESULT_CONTRACT,
        **{key: value for key, value in bad_target.items() if key != "target_result_fingerprint"},
    })
    result, _, _ = _run(monkeypatch, target=bad_target)
    assert result["failure_detail_code"] == "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID"

    resolution = {
        "decision_kind": "MISCLASSIFIED_GENERAL_INCOME",
        "record_version": 1,
        "income_fingerprint": "8" * 64,
        "canonical_source_id": "manual:1",
        "canonical_fingerprint": "9" * 64,
    }
    result, _, _ = _run(monkeypatch, rtisa=_rtisa([_entry(resolution=resolution)]))
    assert result["failure_stage"] == "source_universe"
    assert result["failure_detail_code"] == "RTICB_SOURCE_UNIVERSE_INVALID"


@pytest.mark.parametrize("kind,stage,code", [
    ("target_schema", "target_authority", "RTICB_TARGET_AUTHORITY_SCHEMA_INVALID"),
    ("target_unavailable", "target_authority", "RTICB_TARGET_AUTHORITY_UNAVAILABLE"),
    ("target_not_ready", "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY"),
    ("rtisa_schema", "rtisa_authority", "RTICB_RTISA_AUTHORITY_SCHEMA_INVALID"),
    ("rtisa_unavailable", "rtisa_authority", "RTICB_RTISA_AUTHORITY_UNAVAILABLE"),
    ("rtisa_not_ready", "rtisa_authority", "RTICB_RTISA_AUTHORITY_NOT_READY"),
    ("client", "cross_authority_identity", "RTICB_CLIENT_ID_MISMATCH"),
    ("planning", "cross_authority_identity", "RTICB_PLANNING_IDENTITY_MISMATCH"),
    ("date", "cross_authority_identity", "RTICB_RETIREMENT_TARGET_DATE_MISMATCH"),
    ("source", "source_universe", "RTICB_SOURCE_UNIVERSE_INVALID"),
    ("coverage", "source_universe", "RTICB_SOURCE_COVERAGE_MISMATCH"),
])
def test_semantic_failure_stage_and_precedence(monkeypatch, kind, stage, code):
    target = _target(); rtisa = _rtisa([_entry()])
    if kind == "target_schema": target["extra"] = 1
    elif kind == "target_unavailable":
        target.update(
            planning_calculation_input_fingerprint=None,
            retirement_target_date=None,
            target=None,
            authority=None,
            authority_state="UNAVAILABLE",
            target_ready=False,
            target_readiness_state="NOT_READY",
            blockers=["RIT_PLANNING_CONTEXT_UNAVAILABLE"],
        )
        target = _rehash_target(target)
    elif kind == "target_not_ready": target = _target(state="STALE", ready=False)
    elif kind == "rtisa_schema": rtisa["extra"] = 1
    elif kind == "rtisa_unavailable":
        rtisa = _rtisa([], completeness="UNAVAILABLE", readiness="NOT_READY", ready=False)
    elif kind == "rtisa_not_ready":
        unresolved = _entry(admission="UNRESOLVED")
        rtisa = _rtisa([unresolved], completeness="PARTIAL", readiness="NOT_READY", ready=False)
    elif kind == "client":
        rtisa["client_id"] = 2; rtisa = _rehash_rtisa(rtisa)
    elif kind == "planning":
        rtisa["planning_calculation_input_fingerprint"] = "6" * 64; rtisa = _rehash_rtisa(rtisa)
    elif kind == "date":
        rtisa["retirement_target_date"] = "2031-01-01"; rtisa = _rehash_rtisa(rtisa)
    elif kind == "source":
        rtisa["source_entries"][0]["source_id"] = " income:1"; rtisa["included_source_ids"] = [" income:1"]
        rtisa = _rehash_rtisa(rtisa)
    elif kind == "coverage":
        rtisa["included_source_ids"] = []; rtisa = _rehash_rtisa(rtisa)
    result, _, _ = _run(monkeypatch, target=target, rtisa=rtisa)
    assert result["failure_stage"] == stage
    assert result["failure_detail_code"] == code


def test_authority_specific_observations_never_substitute_request(monkeypatch):
    target = _target(planning="6" * 64, target_date="2031-01-01")
    rtisa = _rtisa([_entry()], planning="7" * 64, target_date="2032-01-01")
    result, _, _ = _run(monkeypatch, target=target, rtisa=rtisa)
    assert result["supplied_planning_calculation_input_fingerprint"] == PLANNING
    assert result["observed_target_planning_calculation_input_fingerprint"] == "6" * 64
    assert result["observed_rtisa_planning_calculation_input_fingerprint"] == "7" * 64
    assert result["supplied_retirement_target_date"] == TARGET_DATE
    assert result["observed_target_retirement_target_date"] == "2031-01-01"
    assert result["observed_rtisa_retirement_target_date"] == "2032-01-01"


def test_category_c_identity_is_opaque_preserved_and_identity_sensitive(monkeypatch):
    first_rtisa = _rtisa([_entry(source_fingerprint="8" * 64)])
    first, _, _ = _run(monkeypatch, rtisa=first_rtisa)
    second_rtisa = _rtisa([_entry(source_fingerprint="9" * 64)])
    second, _, _ = _run(monkeypatch, rtisa=second_rtisa)
    assert first["source_comparisons"][0]["source_upstream_identity"]["source_fingerprint"] == "8" * 64
    assert first["source_comparisons"][0]["source_comparison_fingerprint"] != second["source_comparisons"][0]["source_comparison_fingerprint"]
    assert first["comparison_result_fingerprint"] != second["comparison_result_fingerprint"]


def test_malformed_category_c_identity_fails_at_source_universe(monkeypatch):
    entry = _entry(); del entry["upstream_identity"]["source_fingerprint"]
    result, _, _ = _run(monkeypatch, rtisa=_rtisa([entry]))
    assert result["failure_stage"] == "source_universe"
    assert result["failure_detail_code"] == "RTICB_SOURCE_UNIVERSE_INVALID"


def test_technical_upstream_and_fingerprint_failures_propagate(monkeypatch):
    db = _DB()
    monkeypatch.setattr(subject.target_service, "assess_in_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        subject.assess(db, _request())
    assert db.rollback_count == 1 and not db.active

    monkeypatch.setattr(subject, "_fingerprint", lambda *_: (_ for _ in ()).throw(subject.RTICBFingerprintConstructionError("hash")))
    with pytest.raises(subject.RTICBFingerprintConstructionError, match="hash"):
        subject.assess(_DB(), _request(client_id=True))


def test_public_transaction_owners_are_never_nested(monkeypatch):
    monkeypatch.setattr(target_service, "assess", lambda *_: (_ for _ in ()).throw(AssertionError("public target called")))
    monkeypatch.setattr(rtisa_service, "read", lambda *_: (_ for _ in ()).throw(AssertionError("public RTISA called")))
    result, _, reached = _run(monkeypatch)
    assert result["classification_complete"] is True
    assert reached == {"target": 1, "rtisa": 1}


def test_source_order_and_partitions_are_canonical(monkeypatch):
    rtisa = _rtisa([_entry("income:z"), _entry("income:a", admission="EXCLUDED")])
    result, _, _ = _run(monkeypatch, rtisa=rtisa)
    assert [item["source_id"] for item in result["source_comparisons"]] == ["income:a", "income:z"]
    assert result["directly_comparable_source_ids"] == ["income:z"]
    assert result["not_admitted_source_ids"] == ["income:a"]


@pytest.mark.parametrize("name,target_value,entry_value,expected_state,expected_reasons", [
    ("unknown_income_as_match", _target(), _entry(income="UNKNOWN"), "BASIS_UNRESOLVED", ["RTICB_INCOME_BASIS_UNKNOWN"]),
    ("unknown_price_as_match", _target(), _entry(price="UNKNOWN"), "BASIS_UNRESOLVED", ["RTICB_PRICE_BASIS_UNKNOWN"]),
    ("gross_net_as_direct", _target(income="NET"), _entry(income="GROSS"), "NORMALIZATION_REQUIRED", ["RTICB_INCOME_BASIS_MISMATCH"]),
    ("nominal_real_as_direct", _target(), _entry(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01"), "NORMALIZATION_REQUIRED", ["RTICB_PRICE_BASIS_MISMATCH"]),
    ("real_date_mismatch_as_direct", _target(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01"), _entry(price="REAL_AT_REFERENCE_DATE", reference="2029-02-01"), "NORMALIZATION_REQUIRED", ["RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]),
    ("missing_real_date_as_normalization", _target(), _entry(price="REAL_AT_REFERENCE_DATE", reference=None), "BASIS_UNRESOLVED", ["RTICB_PRICE_BASIS_MISMATCH", "RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"]),
])
def test_mutation_sensitive_classification_oracle(
    monkeypatch, name, target_value, entry_value, expected_state, expected_reasons
):
    original = subject._comparison_entry
    reached = []
    def mutated(entry, target_basis, input_fingerprint):
        reached.append(name)
        value = original(entry, target_basis, input_fingerprint)
        value["comparison_state"] = "DIRECTLY_COMPARABLE" if name != "missing_real_date_as_normalization" else "NORMALIZATION_REQUIRED"
        value["reason_codes"] = [] if name != "missing_real_date_as_normalization" else ["RTICB_PRICE_BASIS_MISMATCH"]
        return value
    monkeypatch.setattr(subject, "_comparison_entry", mutated)
    result, _, _ = _run(monkeypatch, target=target_value, rtisa=_rtisa([entry_value]))
    actual = result["source_comparisons"][0]
    with pytest.raises(AssertionError):
        assert (actual["comparison_state"], actual["reason_codes"]) == (expected_state, expected_reasons)
    assert reached == [name]


def test_real_target_real_source_missing_date_oracle_kills_normalization_mutation(monkeypatch):
    original = subject._comparison_entry
    reached = []

    def mutated(entry, target_basis, input_fingerprint):
        value = original(entry, target_basis, input_fingerprint)
        if (
            target_basis["price_basis"] == "REAL_AT_REFERENCE_DATE"
            and entry["native_price_evidence"]["price_basis"] == "REAL_AT_REFERENCE_DATE"
            and entry["native_price_evidence"]["price_reference_date"] is None
        ):
            reached.append(entry["source_id"])
            value["comparison_state"] = "NORMALIZATION_REQUIRED"
            value["reason_codes"] = ["RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH"]
        return value

    monkeypatch.setattr(subject, "_comparison_entry", mutated)
    result, _, _ = _run(
        monkeypatch,
        target=_target(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01"),
        rtisa=_rtisa([_entry(price="REAL_AT_REFERENCE_DATE", reference=None)]),
    )
    comparison = result["source_comparisons"][0]
    with pytest.raises(AssertionError):
        assert (
            comparison["comparison_state"],
            comparison["reason_codes"],
            result["blockers"],
        ) == (
            "BASIS_UNRESOLVED",
            ["RTICB_REAL_PRICE_REFERENCE_DATE_MISSING"],
            ["RTICB_BASIS_UNRESOLVED"],
        )
    assert reached == ["income:1"]


def test_mutation_sensitive_excluded_basis_validation_cannot_be_bypassed(monkeypatch):
    entry = _entry(admission="EXCLUDED")
    entry["native_income_basis"] = None
    rtisa = _rtisa([entry])
    reached = []
    monkeypatch.setattr(subject, "_basis_valid", lambda value: reached.append(value["source_id"]) or True)
    mutated, _, _ = _run(monkeypatch, rtisa=rtisa)
    with pytest.raises(AssertionError):
        assert "failure_detail_code" in mutated
    assert reached == ["income:1"]


def test_mutation_sensitive_identity_order_coverage_and_readiness_oracle(monkeypatch):
    original = subject._success
    reached = []
    def mutated(request, target, rtisa):
        reached.append("success")
        result = original(request, target, rtisa)
        result["source_comparisons"].reverse()
        result["basis_unresolved_source_ids"] = []
        result["direct_comparison_ready"] = True
        result["direct_comparison_state"] = "READY"
        result["blockers"] = []
        result["source_comparisons"][0]["source_upstream_identity"] = None
        return result
    monkeypatch.setattr(subject, "_success", mutated)
    rtisa = _rtisa([
        _entry("income:a", income="UNKNOWN"),
        _entry("income:z"),
    ])
    result, _, _ = _run(monkeypatch, rtisa=rtisa)
    with pytest.raises(AssertionError):
        assert [entry["source_id"] for entry in result["source_comparisons"]] == ["income:a", "income:z"]
    with pytest.raises(AssertionError):
        assert result["basis_unresolved_source_ids"] == ["income:a"] and not result["direct_comparison_ready"]
    with pytest.raises(AssertionError):
        assert all(entry["source_upstream_identity"] is not None for entry in result["source_comparisons"])
    assert reached == ["success"]


def test_fixed_independent_goldens(monkeypatch):
    goldens = json.loads((Path(__file__).parent / "fixtures" / "rticb_goldens.json").read_text(encoding="utf-8"))
    direct, _, _ = _run(monkeypatch)
    excluded, _, _ = _run(monkeypatch, rtisa=_rtisa([_entry(admission="EXCLUDED")]))
    empty, _, _ = _run(monkeypatch, rtisa=_rtisa([]))
    failure = subject.assess(_DB(active=True), _request())
    assert direct["comparison_input_fingerprint"] == goldens["direct_nominal"]["input"]
    direct_target = _target()
    direct_rtisa = _rtisa([_entry()])
    independent_input_preimage = {
        "contract": subject.INPUT_FINGERPRINT_CONTRACT,
        "client_id": 1,
        "planning_calculation_input_fingerprint": PLANNING,
        "retirement_target_date": TARGET_DATE,
        "target_result_fingerprint": direct_target["target_result_fingerprint"],
        "target_semantic_fingerprint": direct_target["target_semantic_fingerprint"],
        "rtisa_admission_result_fingerprint": direct_rtisa["admission_result_fingerprint"],
    }
    assert _bytes(independent_input_preimage).decode("utf-8") == goldens["direct_nominal"]["input_canonical_json"]
    assert _digest(independent_input_preimage) == goldens["direct_nominal"]["input"]
    assert direct["source_comparisons"][0]["source_comparison_fingerprint"] == goldens["direct_nominal"]["entry"]
    assert direct["comparison_result_fingerprint"] == goldens["direct_nominal"]["result"]
    assert excluded["comparison_result_fingerprint"] == goldens["excluded"]["result"]
    assert empty["comparison_result_fingerprint"] == goldens["empty"]["result"]
    assert failure["result_fingerprint"] == goldens["fresh_transaction_failure"]

    material = {
        "direct_real": _run(
            monkeypatch,
            target=_target(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01"),
            rtisa=_rtisa([_entry(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01")]),
        )[0],
        "price_mismatch": _run(
            monkeypatch,
            rtisa=_rtisa([_entry(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01")]),
        )[0],
        "real_date_mismatch": _run(
            monkeypatch,
            target=_target(price="REAL_AT_REFERENCE_DATE", reference="2029-01-01"),
            rtisa=_rtisa([_entry(price="REAL_AT_REFERENCE_DATE", reference="2029-02-01")]),
        )[0],
        "missing_real_date": _run(
            monkeypatch,
            rtisa=_rtisa([_entry(price="REAL_AT_REFERENCE_DATE", reference=None)]),
        )[0],
        "combined_unresolved_mismatch": _run(
            monkeypatch,
            target=_target(income="NET"),
            rtisa=_rtisa([_entry(income="UNKNOWN", price="REAL_AT_REFERENCE_DATE", reference=None)]),
        )[0],
        "all_excluded": _run(
            monkeypatch,
            rtisa=_rtisa([
                _entry("income:1", admission="EXCLUDED"),
                _entry("income:2", admission="EXCLUDED"),
            ]),
        )[0],
    }
    for name, actual in material.items():
        assert actual["comparison_input_fingerprint"] == goldens[name]["input"]
        assert [entry["source_comparison_fingerprint"] for entry in actual["source_comparisons"]] == goldens[name]["entries"]
        assert actual["comparison_result_fingerprint"] == goldens[name]["result"]

    request_failure = subject.assess(_DB(active=True), _request(client_id=2))
    target_failure = _run(monkeypatch, target=_target(planning="6" * 64))[0]
    rtisa_failure = _run(monkeypatch, rtisa=_rtisa([_entry()], planning="7" * 64))[0]
    assert request_failure["result_fingerprint"] == goldens["request_observation_failure"]
    assert target_failure["result_fingerprint"] == goldens["target_observation_failure"]
    assert rtisa_failure["result_fingerprint"] == goldens["rtisa_observation_failure"]
