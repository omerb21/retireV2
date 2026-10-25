"""SC-03C fail-closed factual/decision partition tests."""
from copy import deepcopy
from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_snapshot_candidate_service import build_snapshot_candidate


def envelope(decisions=None):
    if decisions is None:
        decisions = [{
            "decision_id": "d1", "product_id": "p", "component_id": "c",
            "component_code": "component", "amount": "60.00", "action": "pension",
            "effective_date": "2026-10-25", "validation_state": "unverified",
            "product_version_at_review": 2, "source_fingerprint_at_review": "abc",
            "source": {"product_id": "p", "component_id": "c",
                       "component_code": "component", "product_version": 2,
                       "balance": "100.00", "source_fingerprint": "abc"},
        }]
    identity = {
        "schema_version": "SCENARIO_INERT_MANIFEST_V1", "client_id": 7,
        "scenario_id": "s", "scenario_version": 4, "scenario_status": "draft",
        "decisions": decisions,
    }
    return {**identity, "manifest_fingerprint": _fingerprint(identity),
            "execution_allowed": False, "planning_snapshot": None,
            "financial_result": None, "authority_state": "NOT_EVALUATED"}


def test_verified_partition_still_does_not_admit_financial_execution():
    result = build_snapshot_candidate(envelope())
    assert result["evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
    assert result["source_facts"][0]["balance"] == "100.00"
    assert result["proposed_decisions"][0]["amount"] == "60.00"
    assert result["execution_allowed"] is False and result["planning_snapshot"] is None


def test_modified_manifest_without_updated_fingerprint_is_rejected():
    m = envelope()
    m["decisions"][0]["amount"] = "90.00"
    assert build_snapshot_candidate(m)["blockers"] == ["MANIFEST_INTEGRITY_INVALID"]


def test_source_staleness_detected_despite_valid_envelope():
    m = envelope()
    m["decisions"][0]["source"]["product_version"] = 3
    m["manifest_fingerprint"] = _fingerprint({k: m[k] for k in (
        "schema_version", "client_id", "scenario_id", "scenario_version",
        "scenario_status", "decisions",
    )})
    result = build_snapshot_candidate(m)
    assert "SOURCE_STALE:d1" in result["blockers"]
    assert result["execution_allowed"] is False


def test_exact_cent_aggregate_overallocation_across_actions():
    m = envelope()
    second = deepcopy(m["decisions"][0])
    second.update(decision_id="d2", action="capital_asset", amount="40.01")
    m = envelope([m["decisions"][0], second])
    result = build_snapshot_candidate(m)
    assert "SOURCE_OVERALLOCATED:p:c" in result["blockers"]
    assert len(result["source_facts"]) == 1


def test_cross_component_identity_never_enters_partition():
    m = envelope()
    m["decisions"][0]["source"]["component_id"] = "unrelated"
    m = envelope(m["decisions"])
    result = build_snapshot_candidate(m)
    assert "SOURCE_IDENTITY_MISMATCH:d1" in result["blockers"]
    assert result["source_facts"] == []
