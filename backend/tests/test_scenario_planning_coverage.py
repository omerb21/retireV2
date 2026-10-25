"""D2 inventory: deterministic, inert coverage with strict identity checks."""
from copy import deepcopy

from app.services import scenario_planning_coverage_service as coverage


def pair():
    manifest = {
        "client_id": 7, "scenario_id": "draft", "scenario_version": 2,
        "manifest_fingerprint": "a" * 64,
        "decisions": [
            {"decision_id": "a", "action": "pension", "product_id": "p1", "component_id": "c1"},
            {"decision_id": "b", "action": "capital_asset", "product_id": "p2", "component_id": "c2"},
        ],
    }
    candidate = {
        "client_id": 7, "scenario_id": "draft", "scenario_version": 2,
        "manifest_fingerprint": "a" * 64,
        "evidence_state": "STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
        "blockers": [], "execution_allowed": False,
        "planning_snapshot": None, "financial_result": None,
        "authority_state": "NOT_EVALUATED",
        "proposed_decisions": [
            {"decision_id": "a", "action": "pension", "product_id": "p1", "component_id": "c1"},
            {"decision_id": "b", "action": "capital_asset", "product_id": "p2", "component_id": "c2"},
        ],
    }
    return {"manifest": manifest, "candidate": candidate}


def test_deterministic_inert_inventory(monkeypatch):
    monkeypatch.setattr(coverage, "validate_inert_manifest", lambda value: value)
    first = coverage.inventory_from_authoritative_pair(pair())
    assert first == coverage.inventory_from_authoritative_pair(pair())
    assert first["coverage_state"] == "UNRESOLVED"
    assert first["execution_allowed"] is False
    assert first["planning_snapshot"] is None and first["financial_result"] is None
    assert first["decision_coverage"][0]["requirements"] != first["decision_coverage"][1]["requirements"]
    assert all(r["state"] == "UNRESOLVED" for e in first["decision_coverage"] for r in e["requirements"])


def test_cross_client_and_scenario_version_fail_closed(monkeypatch):
    monkeypatch.setattr(coverage, "validate_inert_manifest", lambda value: value)
    altered = pair()
    altered["candidate"]["client_id"] = 8
    assert coverage.inventory_from_authoritative_pair(altered)["coverage_state"] == "BLOCKED"
    altered = pair()
    altered["candidate"]["scenario_version"] += 1
    assert coverage.inventory_from_authoritative_pair(altered)["coverage_state"] == "BLOCKED"


def test_cross_source_substitution_and_duplicate_decisions_fail_closed(monkeypatch):
    monkeypatch.setattr(coverage, "validate_inert_manifest", lambda value: value)
    altered = pair()
    altered["candidate"]["proposed_decisions"][0]["product_id"] = "foreign-product"
    assert coverage.inventory_from_authoritative_pair(altered)["coverage_state"] == "BLOCKED"
    altered = pair()
    altered["candidate"]["proposed_decisions"][1] = deepcopy(altered["candidate"]["proposed_decisions"][0])
    assert coverage.inventory_from_authoritative_pair(altered)["coverage_state"] == "BLOCKED"


def test_manifest_identity_changes_inventory_fingerprint(monkeypatch):
    monkeypatch.setattr(coverage, "validate_inert_manifest", lambda value: value)
    base = pair()
    first = coverage.inventory_from_authoritative_pair(base)
    new = pair()
    new["manifest"]["scenario_version"] = 3
    new["candidate"]["scenario_version"] = 3
    assert first["inventory_fingerprint"] != coverage.inventory_from_authoritative_pair(new)["inventory_fingerprint"]
    new = pair()
    new["manifest"]["manifest_fingerprint"] = "b" * 64
    new["candidate"]["manifest_fingerprint"] = "b" * 64
    assert first["inventory_fingerprint"] != coverage.inventory_from_authoritative_pair(new)["inventory_fingerprint"]


def test_reject_unknown_claim_and_missing_source_authority():
    assert coverage.inventory_from_authoritative_pair({"manifest": {}, "candidate": {}})["coverage_state"] == "BLOCKED"


def test_public_entrypoint_derives_pair_from_db_owner(monkeypatch):
    called = []
    from app.services import scenario_snapshot_candidate_service as snapshots

    def fake_owner(factory, *, client_id, scenario_id):
        called.append((factory, client_id, scenario_id))
        return pair()

    monkeypatch.setattr(snapshots, "build_manifest_candidate_snapshot", fake_owner)
    monkeypatch.setattr(coverage, "validate_inert_manifest", lambda value: value)
    factory = object()
    result = coverage.build_planning_coverage_snapshot(factory, client_id=7, scenario_id="draft")
    assert called == [(factory, 7, "draft")]
    assert result["coverage_state"] == "UNRESOLVED"
    assert result["execution_allowed"] is False
    assert result["planning_snapshot"] is None
    assert result["financial_result"] is None


def test_public_entrypoint_propagates_snapshot_failure_without_fallback(monkeypatch):
    from app.services import scenario_snapshot_candidate_service as snapshots

    def failing_owner(*args, **kwargs):
        raise snapshots.ScenarioSnapshotError("SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE")

    monkeypatch.setattr(snapshots, "build_manifest_candidate_snapshot", failing_owner)
    import pytest
    with pytest.raises(snapshots.ScenarioSnapshotError):
        coverage.build_planning_coverage_snapshot(object(), client_id=7, scenario_id="draft")
