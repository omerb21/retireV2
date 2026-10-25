"""P2 bridge distinguishes historical lineage from scenario source authority."""
from copy import deepcopy
from app.services.scenario_pension_source_bridge_service import reconcile_pension_source_identities as reconcile


def sample():
    pair = {
        "manifest": {"client_id": 7, "scenario_id": "s", "scenario_version": 2, "manifest_fingerprint": "a"*64},
        "candidate": {
            "client_id": 7, "scenario_id": "s", "scenario_version": 2,
            "manifest_fingerprint": "a"*64, "evidence_state": "STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
            "blockers": [], "execution_allowed": False,
            "proposed_decisions": [
                {"decision_id": "d1", "product_id": "p", "component_id": "c", "action": "pension"},
                {"decision_id": "d2", "product_id": "p", "component_id": "z", "action": "capital_asset"},
            ],
        },
    }
    sources = [{
        "kind": "conversion", "source_id": "conversion:one",
        "provenance": {"allocations": [{"source_product_id": "p", "source_component_id": "c"}]},
    }]
    return pair, sources


def test_history_is_not_admitted_source():
    pair, sources = sample()
    result = reconcile(pair, sources)
    assert result == reconcile(pair, sources)
    assert result["bridge_state"] == "UNRESOLVED"
    assert result["execution_allowed"] is False
    assert result["planning_snapshot"] is None and result["financial_result"] is None
    assert len(result["entries"]) == 1
    assert result["entries"][0]["historical_conversion_source_ids"] == ["conversion:one"]
    assert result["entries"][0]["reconciliation_state"] == "UNRESOLVED"


def test_missing_trace_never_becomes_match():
    pair, sources = sample()
    assert reconcile(pair, [])["entries"][0]["trace_note"] == "NO_HISTORICAL_CONVERSION_TRACE"


def test_identity_tamper_fails_closed():
    pair, sources = sample()
    pair["candidate"]["scenario_version"] += 1
    assert reconcile(pair, sources)["bridge_state"] == "BLOCKED"


def test_ambiguous_history_still_unresolved():
    pair, sources = sample()
    second = deepcopy(sources[0])
    second["source_id"] = "conversion:two"
    result = reconcile(pair, sources + [second])
    assert len(result["entries"][0]["historical_conversion_source_ids"]) == 2
    assert result["entries"][0]["reconciliation_state"] == "UNRESOLVED"


def test_malformed_lineage_blocks():
    pair, sources = sample()
    sources[0]["provenance"]["allocations"] = [{"source_component_id": "c"}]
    assert reconcile(pair, sources)["bridge_state"] == "BLOCKED"


def test_public_bridge_uses_same_snapshot_session(monkeypatch):
    from app.services import scenario_pension_source_bridge_service as bridge
    from app.services import scenario_snapshot_candidate_service as owner
    from app.services import professional_source_snapshot_service as canonical
    pair, sources = sample()
    shared_session = object()
    observed = []

    def fake_owner(factory, *, client_id, scenario_id, _snapshot_extension):
        observed.append(("owner", factory, client_id, scenario_id))
        return _snapshot_extension(shared_session, pair)

    def fake_snapshot(db, client_id, *, as_of):
        observed.append(("canonical", db, client_id))
        return {"pension_sources": sources}

    monkeypatch.setattr(owner, "build_manifest_candidate_snapshot", fake_owner)
    monkeypatch.setattr(canonical, "_snapshot", fake_snapshot)
    factory = object()
    result = bridge.build_pension_source_bridge_snapshot(
        factory, client_id=7, scenario_id="s",
    )
    assert observed == [("owner", factory, 7, "s"), ("canonical", shared_session, 7)]
    assert result["bridge_state"] == "UNRESOLVED"
    assert result["execution_allowed"] is False


def test_public_bridge_does_not_fallback_after_snapshot_failure(monkeypatch):
    import pytest
    from app.services import scenario_pension_source_bridge_service as bridge
    from app.services import scenario_snapshot_candidate_service as owner

    def failed(*args, **kwargs):
        raise owner.ScenarioSnapshotError("SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE")

    monkeypatch.setattr(owner, "build_manifest_candidate_snapshot", failed)
    with pytest.raises(owner.ScenarioSnapshotError):
        bridge.build_pension_source_bridge_snapshot(object(), client_id=7, scenario_id="s")
