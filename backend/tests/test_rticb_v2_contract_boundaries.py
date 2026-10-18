"""Focused RTICB V2 pure-contract controls; no database or producer fixture spoofing."""
from copy import deepcopy

from app.services import retirement_target_date_income_comparison_basis_service as svc


SHA = "a" * 64
TARGET = {"income_basis": "GROSS", "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None}


def entry(state="CURRENT", kind="PENSION", admitted="INCLUDED"):
    return {
        "schema_version": "CRTISBA_SOURCE_BASIS_ENTRY_V1", "source_id": "manual:1",
        "source_kind": kind, "source_category": "PENSION", "admission_state": admitted,
        "rtisa_reason_codes": [], "source_version": 1, "source_fingerprint": SHA,
        "amount_authority_fingerprint": SHA, "decision_version": 1,
        "decision_fingerprint": SHA, "decision_state": state,
        "income_basis": "GROSS", "income_basis_provenance": "EXPLICIT_PROFESSIONAL",
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
        "price_basis_provenance": "OWNER_DECISION_OD2", "blockers": [],
    }


def collection(entries):
    parts = {name: [] for name in svc.PARTITIONS.values()}
    for e in entries:
        parts[svc.PARTITIONS[e["decision_state"]]].append(e["source_id"])
    blockers = sorted({b for e in entries for b in e["blockers"]})
    obj = {
        "schema_version": "CRTISBA_COLLECTION_RESULT_V1", "client_id": 3,
        "planning_calculation_input_fingerprint": SHA, "retirement_target_date": "2036-01-01",
        "rtisa_admission_result_fingerprint": SHA, "source_basis_entries": entries,
        "partitions": parts, "blockers": blockers,
        "basis_readiness_state": "READY" if not blockers else "NOT_READY",
        "basis_ready": not blockers,
    }
    obj["result_fingerprint"] = svc._fingerprint({"contract": svc.COLLECTION_CONTRACT, "result": deepcopy(obj)})
    return obj


def test_v2_identity_contract_literals():
    assert svc.SCHEMA_VERSION.endswith("_V2")
    assert svc.INPUT_FINGERPRINT_CONTRACT.endswith("_V2")
    assert svc.RESULT_FINGERPRINT_CONTRACT.endswith("_V2")
    assert len(svc.ENTRY_FIELDS) == 18
    assert len(svc.BLOCKED_FIELDS) == 14
    assert len(svc.PARTITIONS) == 10


def test_current_direct_and_mismatch_golden_construction():
    e = entry()
    direct = svc._entry_comparison(e, TARGET, SHA)
    assert direct["comparison_state"] == "DIRECTLY_COMPARABLE"
    assert direct["reason_codes"] == []
    assert len(direct) == 22
    e["income_basis"] = "NET"
    mismatch = svc._entry_comparison(e, TARGET, SHA)
    assert mismatch["comparison_state"] == "NORMALIZATION_REQUIRED"
    assert mismatch["reason_codes"] == ["RTICB_INCOME_BASIS_MISMATCH"]
    assert mismatch["source_comparison_fingerprint"] != direct["source_comparison_fingerprint"]


def test_excluded_source_does_not_infer_basis():
    e = entry(state="NOT_APPLICABLE_NOT_ADMITTED", admitted="EXCLUDED")
    for key in ("income_basis", "income_basis_provenance", "price_basis", "price_reference_date", "price_basis_provenance"):
        e[key] = None
    e["decision_version"] = e["decision_fingerprint"] = e["amount_authority_fingerprint"] = None
    assert svc._entry_valid(e)
    out = svc._entry_comparison(e, TARGET, SHA)
    assert out["comparison_state"] == "NOT_ADMITTED"
    assert out["reason_codes"] == ["RTICB_SOURCE_NOT_ADMITTED"]
    assert out["income_basis"] is None


def test_not_ready_collection_is_structurally_valid():
    e = entry(state="MISSING")
    e["decision_version"] = e["decision_fingerprint"] = None
    e["income_basis"] = "UNKNOWN"
    e["income_basis_provenance"] = "MISSING"
    e["blockers"] = ["CRTISBA_DECISION_MISSING"]
    obj = collection([e])
    assert svc._collection_shape(obj)
    assert svc._collection_fingerprint_valid(obj)
    assert svc._universe_valid(obj)
    assert svc._consistent(obj)
    assert obj["basis_ready"] is False
    out = svc._entry_comparison(e, TARGET, SHA)
    assert out["comparison_state"] == "BASIS_UNRESOLVED"
    assert out["reason_codes"] == ["RTICB_CRTISBA_DECISION_MISSING"]


def test_coherent_rehash_cannot_bypass_readiness_equality():
    obj = collection([entry()])
    obj["basis_ready"] = False
    obj["result_fingerprint"] = svc._fingerprint({
        "contract": svc.COLLECTION_CONTRACT,
        "result": {k: deepcopy(v) for k, v in obj.items() if k != "result_fingerprint"},
    })
    assert svc._collection_fingerprint_valid(obj)
    assert not svc._consistent(obj)


def test_blocked_producer_hash_and_wrong_client_preemption():
    obj = {
        "schema_version": "CRTISBA_BLOCK_NO_RESULT_V1", "result_state": "block_no_result",
        "client_id": 3, "source_id": None, "operation": "READ",
        "failure_stage": "planning_context",
        "failure_detail_code": "CRTISBA_PLANNING_CONTEXT_UNAVAILABLE",
        "field_paths": [], "observed_planning_calculation_input_fingerprint": None,
        "observed_source_version": None, "observed_source_fingerprint": None,
        "observed_amount_authority_fingerprint": None, "observed_decision_version": None,
    }
    obj["failure_fingerprint"] = svc._fingerprint({
        "contract": svc.BLOCKED_CONTRACT,
        **{k: v for k, v in obj.items() if k not in {"schema_version", "result_state", "failure_fingerprint"}},
    })
    assert svc._blocked_valid(obj, 3)
    assert not svc._blocked_valid(obj, 4)
    changed = deepcopy(obj)
    changed["failure_detail_code"] = "CRTISBA_PENSION_RESULT_INVALID"
    assert not svc._blocked_valid(changed, 3)
