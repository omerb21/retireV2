"""Ordinary, negative and mutation-sensitive RMIGA contract evidence."""
from copy import deepcopy
import hashlib
import json
from math import gcd
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.services import retirement_monthly_income_gap_service as subject
from app.services import retirement_target_date_comparable_monthly_income_service as cmia
from app.services import retirement_target_date_income_comparison_basis_service as rticb
from app.services import retirement_target_date_income_source_basis_service as crtisba
from app.services import retirement_monthly_income_target_service as target_service
from test_retirement_target_date_comparable_monthly_income import (
    _DB, _evidence, _professional_block_evidence, _recurring_source, _request,
)


def _independent_fingerprint(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _install_evidence(monkeypatch, evidence):
    monkeypatch.setattr(crtisba, "_planning_envelope_valid", lambda *_: True)
    monkeypatch.setattr(crtisba.rtisa_service, "_portfolio_is_valid", lambda *_: True)
    monkeypatch.setattr(crtisba, "_rtisa_envelope_valid", lambda *_: True)
    monkeypatch.setattr(rticb, "assess_with_evidence_in_snapshot", lambda *_: deepcopy(evidence))


def _run(monkeypatch, evidence, db=None):
    _install_evidence(monkeypatch, evidence)
    db = db or _DB()
    return subject.assess(db, _request()), db


def _rehash_cmia_block(result):
    payload = {key: value for key, value in result.items() if key != "result_fingerprint"}
    result["result_fingerprint"] = _independent_fingerprint({
        "contract": cmia.BLOCK_CONTRACT, "result": payload,
    })


def _rehash_cmia_complete(result):
    payload = {key: value for key, value in result.items() if key != "result_fingerprint"}
    result["result_fingerprint"] = _independent_fingerprint({
        "contract": cmia.RESULT_CONTRACT, "result": payload,
    })


def _composition(monkeypatch, evidence):
    _install_evidence(monkeypatch, evidence)
    return cmia.assess_with_target_in_snapshot(_DB(active=True), _request())


def _upstream_block_evidence():
    evidence = _evidence()
    evidence["comparison"] = rticb._failure(
        _request(), "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY",
        target=evidence["target"],
    )
    return evidence


def _chunk_int(value):
    result = 0
    for offset in range(0, len(value), 7):
        chunk = value[offset:offset + 7]
        result = result * (10 ** len(chunk)) + int(chunk)
    return result


def _chunk_ascii(value):
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    pieces = []
    while value:
        value, piece = divmod(value, 10_000_000)
        pieces.append(piece)
    return sign + str(pieces.pop()) + "".join(f"{piece:07d}" for piece in reversed(pieces))


@pytest.mark.parametrize(("amount", "gap", "state"), [
    ("1200.00", {"numerator": "8800", "denominator": "1"}, "SHORTFALL"),
    ("10000.00", {"numerator": "0", "denominator": "1"}, "EQUAL"),
    ("12000.00", {"numerator": "-2000", "denominator": "1"}, "SURPLUS"),
])
def test_exact_signed_gap_uses_real_same_snapshot_composition(monkeypatch, amount, gap, state):
    result, db = _run(
        monkeypatch, _evidence(recurring=(_recurring_source(1, amount, "monthly"),)),
    )
    assert result["result_state"] == "COMPLETE"
    assert result["monthly_gap"] == {
        **gap, "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["gap_state"] == state
    assert result["target_monthly_amount"] == {
        "numerator": "10000", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["included_contributions"][0]["source_id"] == "income:1"
    assert result["source_count"] == 1
    assert db.rollback_count == 1 and not db.in_transaction()


def test_complete_result_closed_schema_and_independent_fingerprint(monkeypatch):
    result, _ = _run(monkeypatch, _evidence(recurring=(
        _recurring_source(1, "1000.00", "quarterly"),
    )))
    assert set(result) == {
        "schema_version", "result_state", "client_id",
        "planning_calculation_input_fingerprint", "retirement_target_date",
        "target_result_fingerprint", "target_semantic_fingerprint",
        "cmia_result_fingerprint", "target_income_basis", "target_price_basis",
        "target_price_reference_date", "target_monthly_amount",
        "comparable_monthly_income", "monthly_gap", "gap_state",
        "included_contributions", "excluded_source_ids", "source_count",
        "result_fingerprint",
    }
    payload = {key: value for key, value in result.items() if key != "result_fingerprint"}
    assert result["result_fingerprint"] == _independent_fingerprint({
        "contract": subject.RESULT_CONTRACT, "result": payload,
    })


def test_valid_request_bound_block_short_circuits_target_and_arithmetic(monkeypatch):
    evidence = _professional_block_evidence()
    result, db = _run(monkeypatch, evidence)
    assert result["result_state"] == "BLOCK_NO_GAP"
    assert result["failure_stage"] == "upstream_authority"
    assert result["failure_detail_code"] == "RMIGA_COMPARABLE_INCOME_BLOCKED"
    assert result["observed_cmia_blocked_source_ids"] == ["income:1"]
    assert not set(result).intersection({
        "target_monthly_amount", "comparable_monthly_income", "monthly_gap", "gap_state",
    })
    assert db.rollback_count == 1


@pytest.mark.parametrize("evidence_factory", [_professional_block_evidence, _upstream_block_evidence])
def test_both_accepted_cmia_block_variants_short_circuit(monkeypatch, evidence_factory):
    result, _ = _run(monkeypatch, evidence_factory())
    assert result["result_state"] == "BLOCK_NO_GAP"
    assert result["failure_detail_code"] == "RMIGA_COMPARABLE_INCOME_BLOCKED"
    assert "monthly_gap" not in result


@pytest.mark.parametrize(
    "evidence,excluded",
    [(_evidence(), []), (_evidence(excluded=("income:9",)), ["income:9"])],
)
def test_zero_comparable_income_from_empty_or_all_excluded_sources(monkeypatch, evidence, excluded):
    result, _ = _run(monkeypatch, evidence)
    assert result["comparable_monthly_income"] == {
        "numerator": "0", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["monthly_gap"]["numerator"] == "10000"
    assert result["included_contributions"] == []
    assert result["excluded_source_ids"] == excluded


def test_six_decimal_target_and_mixed_denominators_are_exact(monkeypatch):
    evidence = _evidence(recurring=(
        _recurring_source(1, "1.00", "quarterly"),
        _recurring_source(2, "1.00", "annual"),
    ))
    target = evidence["target"]
    target["target"]["monthly_amount"] = "10000.123456"
    target["target_semantic_fingerprint"] = _independent_fingerprint({
        "contract": target_service.SEMANTIC_CONTRACT, **target["target"],
    })
    target_payload = {key: value for key, value in target.items() if key != "target_result_fingerprint"}
    target["target_result_fingerprint"] = _independent_fingerprint({
        "contract": target_service.RESULT_CONTRACT, **target_payload,
    })
    evidence["comparison"] = rticb._result(
        _request(), target, evidence["crtisba_collection"],
    )
    result, _ = _run(monkeypatch, evidence)
    assert result["target_monthly_amount"] == {
        "numerator": "156251929", "denominator": "15625",
        "currency": "ILS", "frequency": "MONTHLY",
    }
    assert result["comparable_monthly_income"]["numerator"] == "5"
    assert result["comparable_monthly_income"]["denominator"] == "12"
    assert result["monthly_gap"] == {
        "numerator": "1874945023", "denominator": "187500",
        "currency": "ILS", "frequency": "MONTHLY",
    }


@pytest.mark.parametrize(("numerator", "denominator"), [
    ("1" + "0" * 5000, "3"),
    ("1", "1" + "0" * 5000 + "3"),
])
def test_rmiga_accepts_contract_valid_arbitrary_precision_cmia_amount(
    monkeypatch, numerator, denominator,
):
    composition = _composition(
        monkeypatch, _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),)),
    )
    rational = {
        "numerator": numerator, "denominator": denominator,
        "currency": "ILS", "frequency": "MONTHLY",
    }
    contribution = composition["cmia_result"]["included_contributions"][0]
    contribution["monthly_equivalent"] = deepcopy(rational)
    contribution_payload = {
        key: value for key, value in contribution.items() if key != "contribution_fingerprint"
    }
    contribution["contribution_fingerprint"] = _independent_fingerprint({
        "contract": cmia.CONTRIBUTION_CONTRACT, "contribution": contribution_payload,
    })
    composition["cmia_result"]["total_monthly_equivalent"] = deepcopy(rational)
    _rehash_cmia_complete(composition["cmia_result"])
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: deepcopy(composition))

    result = subject.assess(_DB(), _request())
    input_numerator = _chunk_int(numerator)
    input_denominator = _chunk_int(denominator)
    expected_numerator = 10_000 * input_denominator - input_numerator
    divisor = gcd(abs(expected_numerator), input_denominator)
    assert result["monthly_gap"]["numerator"] == _chunk_ascii(expected_numerator // divisor)
    assert result["monthly_gap"]["denominator"] == _chunk_ascii(input_denominator // divisor)
    assert result["gap_state"] == ("SHORTFALL" if expected_numerator > 0 else "SURPLUS")


@pytest.mark.parametrize(
    "field",
    [
        "client_id",
        "supplied_planning_calculation_input_fingerprint",
        "supplied_retirement_target_date",
    ],
)
def test_each_blocked_request_identity_field_has_positive_binding(monkeypatch, field):
    result, _ = _run(monkeypatch, _professional_block_evidence())
    expected = {
        "client_id": 1,
        "supplied_planning_calculation_input_fingerprint": _request()[
            "expected_planning_calculation_input_fingerprint"
        ],
        "supplied_retirement_target_date": _request()["expected_retirement_target_date"],
    }
    assert result[field] == expected[field]


def test_rmiga_fixed_complete_and_block_fingerprint_goldens(monkeypatch):
    complete, _ = _run(
        monkeypatch, _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),)),
    )
    blocked, _ = _run(monkeypatch, _professional_block_evidence())
    assert complete["result_fingerprint"] == (
        "ea2124d47ee2041e0c4981a3fa8ff09d47f401fe7ecd27f3c605dd6cbc92b8a6"
    )
    assert blocked["result_fingerprint"] == (
        "8a3fa677e9fd24253d6f9f1ac22f7e83c08e246981beef6fe7562b2e202c1e55"
    )


@pytest.mark.parametrize(("field", "replacement"), [
    ("client_id", 2),
    ("supplied_planning_calculation_input_fingerprint", "9" * 64),
    ("supplied_retirement_target_date", "2031-01-01"),
])
def test_coherently_rehashed_block_request_identity_mismatch_fails_closed(
    monkeypatch, field, replacement,
):
    evidence = _professional_block_evidence()
    _install_evidence(monkeypatch, evidence)
    active = _DB(active=True)
    block = cmia.assess_with_target_in_snapshot(active, _request())["cmia_result"]
    block[field] = replacement
    _rehash_cmia_block(block)
    monkeypatch.setattr(
        cmia, "assess_with_target_in_snapshot",
        lambda *_: {"cmia_result": deepcopy(block), "target": None},
    )
    with pytest.raises(subject.RMIGAContractError) as caught:
        subject.assess(_DB(), _request())
    assert (caught.value.stage, caught.value.code, caught.value.client_id) == (
        "cmia_authority", "RMIGA_CMIA_RESULT_INVALID", 1,
    )


def test_complete_target_identity_and_basis_tampering_fail_closed(monkeypatch):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    _install_evidence(monkeypatch, evidence)
    active = _DB(active=True)
    composition = cmia.assess_with_target_in_snapshot(active, _request())
    planning_tampered = deepcopy(composition)
    planning_tampered["cmia_result"]["planning_calculation_input_fingerprint"] = "9" * 64
    payload = {
        key: value for key, value in planning_tampered["cmia_result"].items()
        if key != "result_fingerprint"
    }
    planning_tampered["cmia_result"]["result_fingerprint"] = _independent_fingerprint({
        "contract": cmia.RESULT_CONTRACT, "result": payload,
    })
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: planning_tampered)
    with pytest.raises(subject.RMIGAContractError) as caught:
        subject.assess(_DB(), _request())
    assert caught.value.code == "RMIGA_CROSS_AUTHORITY_IDENTITY_MISMATCH"

    basis_tampered = deepcopy(composition)
    basis_tampered["cmia_result"]["target_income_basis"] = "NET"
    payload = {
        key: value for key, value in basis_tampered["cmia_result"].items()
        if key != "result_fingerprint"
    }
    basis_tampered["cmia_result"]["result_fingerprint"] = _independent_fingerprint({
        "contract": cmia.RESULT_CONTRACT, "result": payload,
    })
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: basis_tampered)
    with pytest.raises(subject.RMIGAContractError) as caught:
        subject.assess(_DB(), _request())
    assert caught.value.code == "RMIGA_BASIS_IDENTITY_MISMATCH"


@pytest.mark.parametrize(("payload", "code", "client_id"), [
    ({}, "RMIGA_REQUEST_SCHEMA_INVALID", None),
    (_request(client_id=True), "RMIGA_CLIENT_ID_INVALID", None),
    (_request(expected_planning_calculation_input_fingerprint="x"),
     "RMIGA_EXPECTED_PLANNING_FINGERPRINT_INVALID", 1),
    (_request(expected_retirement_target_date="2030-02-30"),
     "RMIGA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID", 1),
])
def test_closed_request_rejection_precedes_database(payload, code, client_id):
    db = _DB()
    db.get_bind = lambda: (_ for _ in ()).throw(AssertionError("database touched"))
    with pytest.raises(subject.RMIGAContractError) as caught:
        subject.assess(db, payload)
    assert (caught.value.code, caught.value.client_id) == (code, client_id)


def test_validator_and_result_mapping_mutations_kill_ordinary_oracle_and_restore(monkeypatch):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    accepted_result_contract = subject.RESULT_CONTRACT

    def ordinary_oracle():
        result, _ = _run(monkeypatch, evidence)
        assert result["monthly_gap"]["numerator"] == "8800"
        payload = {key: value for key, value in result.items() if key != "result_fingerprint"}
        assert result["result_fingerprint"] == _independent_fingerprint({
            "contract": accepted_result_contract, "result": payload,
        })

    ordinary_oracle()
    _install_evidence(monkeypatch, evidence)
    composition = cmia.assess_with_target_in_snapshot(_DB(active=True), _request())
    malformed = deepcopy(composition)
    malformed["cmia_result"]["total_monthly_equivalent"] = {
        "numerator": "1201", "denominator": "1", "currency": "ILS", "frequency": "MONTHLY",
    }
    cmia_payload = {
        key: value for key, value in malformed["cmia_result"].items()
        if key != "result_fingerprint"
    }
    malformed["cmia_result"]["result_fingerprint"] = _independent_fingerprint({
        "contract": cmia.RESULT_CONTRACT, "result": cmia_payload,
    })
    original_adapter = cmia.assess_with_target_in_snapshot
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: deepcopy(malformed))

    def unchanged_validator_oracle():
        with pytest.raises(cmia.CMIAResultValidationError):
            subject.assess(_DB(), _request())

    unchanged_validator_oracle()
    original_validator = cmia.validate_public_result
    monkeypatch.setattr(
        cmia, "validate_public_result",
        lambda value: cmia.ValidatedCMIAResult("COMPLETE", value),
    )
    mutant_killed = False
    try:
        unchanged_validator_oracle()
    except BaseException:
        mutant_killed = True
    assert mutant_killed
    monkeypatch.setattr(cmia, "validate_public_result", original_validator)
    unchanged_validator_oracle()
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", original_adapter)
    ordinary_oracle()

    original_contract = subject.RESULT_CONTRACT
    monkeypatch.setattr(subject, "RESULT_CONTRACT", "MUTATED_RMIGA_RESULT_CONTRACT")
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(subject, "RESULT_CONTRACT", original_contract)
    ordinary_oracle()


@pytest.mark.parametrize(("field", "replacement"), [
    ("client_id", 2),
    ("supplied_planning_calculation_input_fingerprint", "9" * 64),
    ("supplied_retirement_target_date", "2031-01-01"),
])
def test_each_blocked_identity_guard_mutation_is_killed_and_restored(
    monkeypatch, field, replacement,
):
    composition = _composition(monkeypatch, _professional_block_evidence())
    composition["cmia_result"][field] = replacement
    _rehash_cmia_block(composition["cmia_result"])
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: deepcopy(composition))

    def unchanged_oracle():
        try:
            subject.assess(_DB(), _request())
        except subject.RMIGAContractError as error:
            return error.code == "RMIGA_CMIA_RESULT_INVALID"
        return False

    assert unchanged_oracle()
    original = subject._blocked_identity_valid
    reached = []
    monkeypatch.setattr(subject, "_blocked_identity_valid", lambda *_: reached.append(True) or True)
    assert not unchanged_oracle()
    assert reached
    monkeypatch.setattr(subject, "_blocked_identity_valid", original)
    assert unchanged_oracle()


@pytest.mark.parametrize(("kind", "expected_code"), [
    ("identity", "RMIGA_CROSS_AUTHORITY_IDENTITY_MISMATCH"),
    ("basis", "RMIGA_BASIS_IDENTITY_MISMATCH"),
])
def test_complete_identity_and_basis_guard_mutations_are_killed_and_restored(
    monkeypatch, kind, expected_code,
):
    composition = _composition(
        monkeypatch, _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),)),
    )
    if kind == "identity":
        composition["cmia_result"]["target_result_fingerprint"] = "9" * 64
        helper = "_complete_identity_valid"
    else:
        composition["cmia_result"]["target_income_basis"] = "NET"
        helper = "_basis_valid"
    _rehash_cmia_complete(composition["cmia_result"])
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", lambda *_: deepcopy(composition))

    def unchanged_oracle():
        try:
            subject.assess(_DB(), _request())
        except subject.RMIGAContractError as error:
            return error.code == expected_code
        return False

    assert unchanged_oracle()
    original = getattr(subject, helper)
    reached = []
    monkeypatch.setattr(subject, helper, lambda *_: reached.append(True) or True)
    assert not unchanged_oracle()
    assert reached
    monkeypatch.setattr(subject, helper, original)
    assert unchanged_oracle()


@pytest.mark.parametrize("helper", ["_subtract", "_gap_state", "_source_projection"])
def test_arithmetic_sign_and_source_projection_mutations_are_killed_and_restored(
    monkeypatch, helper,
):
    evidence = _evidence(recurring=(
        _recurring_source(1, "1200.00", "monthly"),
        _recurring_source(2, "900.00", "quarterly"),
    ), excluded=("income:9",))

    def ordinary_oracle():
        result, _ = _run(monkeypatch, evidence)
        assert result["monthly_gap"]["numerator"] == "8500"
        assert result["gap_state"] == "SHORTFALL"
        assert [item["source_id"] for item in result["included_contributions"]] == [
            "income:1", "income:2",
        ]
        assert result["excluded_source_ids"] == ["income:9"]
        assert result["source_count"] == 2

    ordinary_oracle()
    original = getattr(subject, helper)
    reached = []
    if helper == "_subtract":
        mutant = lambda left, right: reached.append(True) or (left + right)
    elif helper == "_gap_state":
        mutant = lambda gap: reached.append(True) or "SURPLUS"
    else:
        mutant = lambda value: reached.append(True) or ([], [], 0)
    monkeypatch.setattr(subject, helper, mutant)
    with pytest.raises(AssertionError):
        ordinary_oracle()
    assert reached
    monkeypatch.setattr(subject, helper, original)
    ordinary_oracle()


@pytest.mark.parametrize("mutation", ["second_read", "write", "flush", "commit"])
def test_same_snapshot_and_forbidden_database_action_mutations_are_killed_and_restored(
    monkeypatch, mutation,
):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    _install_evidence(monkeypatch, evidence)
    original = cmia.assess_with_target_in_snapshot
    calls = []

    def counted(db, request):
        calls.append("read")
        return original(db, request)

    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", counted)

    def ordinary_oracle():
        calls.clear()
        db = _DB()
        db.add = lambda _value: (_ for _ in ()).throw(AssertionError("RMIGA must not write"))
        result = subject.assess(db, _request())
        assert result["monthly_gap"]["numerator"] == "8800"
        assert calls == ["read"]

    ordinary_oracle()

    def mutant(db, request):
        if mutation == "second_read":
            counted(db, request)
        elif mutation == "write":
            db.add(SimpleNamespace())
        elif mutation == "flush":
            db.flush()
        else:
            db.commit()
        return counted(db, request)

    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", mutant)
    with pytest.raises(AssertionError):
        ordinary_oracle()
    monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", counted)
    ordinary_oracle()


def test_rollback_mapping_mutation_is_killed_and_restored(monkeypatch):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))

    def ordinary_oracle():
        result, db = _run(monkeypatch, evidence)
        assert result["monthly_gap"]["numerator"] == "8800"
        assert db.rollback_count == 1 and not db.in_transaction()

    ordinary_oracle()
    original = subject._rollback_owned_transaction
    reached = []
    monkeypatch.setattr(
        subject, "_rollback_owned_transaction", lambda *_: reached.append(True),
    )
    with pytest.raises(AssertionError):
        ordinary_oracle()
    assert reached
    monkeypatch.setattr(subject, "_rollback_owned_transaction", original)
    ordinary_oracle()


def test_transaction_cleanup_and_rollback_failure_precedence_poison_session(monkeypatch):
    evidence = _evidence()
    _install_evidence(monkeypatch, evidence)
    db = Session(create_engine("sqlite://"))
    monkeypatch.setattr(db, "rollback", lambda: (_ for _ in ()).throw(OSError("rmiga cleanup")))
    with pytest.raises(OSError, match="rmiga cleanup"):
        subject.assess(db, _request())
    with pytest.raises(InvalidRequestError, match="RMIGA Session is permanently unusable"):
        db.scalar(text("SELECT 1"))


def test_rollback_failure_precedence_and_session_poisoning_mutations_fail_and_restore(
    monkeypatch,
):
    evidence = _evidence(recurring=(_recurring_source(1, "1200.00", "monthly"),))
    _install_evidence(monkeypatch, evidence)
    production_adapter = cmia.assess_with_target_in_snapshot
    expected = (
        ("OSError", "rmiga rollback failure", True),
        ("OSError", "rmiga rollback failure", True),
    )

    def run_case(*, technical_failure):
        if technical_failure:
            monkeypatch.setattr(
                cmia, "assess_with_target_in_snapshot",
                lambda *_: (_ for _ in ()).throw(RuntimeError("earlier technical failure")),
            )
        else:
            monkeypatch.setattr(cmia, "assess_with_target_in_snapshot", production_adapter)
        db = Session(create_engine("sqlite://"))
        monkeypatch.setattr(
            db, "rollback",
            lambda: (_ for _ in ()).throw(OSError("rmiga rollback failure")),
        )
        caught = None
        try:
            subject.assess(db, _request())
        except BaseException as error:
            caught = error
        reuse_blocked = False
        try:
            db.scalar(text("SELECT 1"))
        except InvalidRequestError as error:
            reuse_blocked = "permanently unusable" in str(error)
        finally:
            db.close()
        return (
            type(caught).__name__ if caught is not None else None,
            str(caught) if caught is not None else None,
            reuse_blocked,
        )

    def ordinary_oracle():
        return (
            run_case(technical_failure=False),
            run_case(technical_failure=True),
        )

    assert ordinary_oracle() == expected

    production_rollback = subject._rollback_owned_transaction
    precedence_mutation_reached = []

    def suppress_rollback_failure(db, connection):
        precedence_mutation_reached.append(True)
        try:
            production_rollback(db, connection)
        except OSError:
            return None

    monkeypatch.setattr(subject, "_rollback_owned_transaction", suppress_rollback_failure)
    assert ordinary_oracle() != expected
    assert precedence_mutation_reached
    monkeypatch.setattr(subject, "_rollback_owned_transaction", production_rollback)
    assert ordinary_oracle() == expected

    production_poison = subject._poison_session
    poisoning_mutation_reached = []
    monkeypatch.setattr(
        subject, "_poison_session", lambda _db: poisoning_mutation_reached.append(True),
    )
    assert ordinary_oracle() != expected
    assert poisoning_mutation_reached
    monkeypatch.setattr(subject, "_poison_session", production_poison)
    assert ordinary_oracle() == expected


def test_connection_acquisition_ownership_and_retained_connection_invalidation(monkeypatch):
    class AcquisitionFailureDB(_DB):
        def connection(self):
            raise OSError("acquisition")

    failed = AcquisitionFailureDB()
    with pytest.raises(OSError, match="acquisition"):
        subject.assess(failed, _request())
    assert failed.rollback_count == 0

    class RollbackFailureDB(_DB):
        def rollback(self):
            raise OSError("rollback")

    acquired = RollbackFailureDB()
    _install_evidence(monkeypatch, _evidence())
    with pytest.raises(OSError, match="rollback"):
        subject.assess(acquired, _request())
    assert acquired.connection_value.invalidated is True
