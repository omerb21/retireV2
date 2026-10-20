"""Ordinary, negative and mutation-sensitive RMIGA contract evidence."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.services import retirement_monthly_income_gap_service as subject
from app.services import retirement_target_date_comparable_monthly_income_service as cmia
from app.services import retirement_target_date_income_comparison_basis_service as rticb
from app.services import retirement_target_date_income_source_basis_service as crtisba
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


def test_transaction_cleanup_and_rollback_failure_precedence_poison_session(monkeypatch):
    evidence = _evidence()
    _install_evidence(monkeypatch, evidence)
    db = Session(create_engine("sqlite://"))
    monkeypatch.setattr(db, "rollback", lambda: (_ for _ in ()).throw(OSError("rmiga cleanup")))
    with pytest.raises(OSError, match="rmiga cleanup"):
        subject.assess(db, _request())
    with pytest.raises(InvalidRequestError, match="RMIGA Session is permanently unusable"):
        db.scalar(text("SELECT 1"))


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
