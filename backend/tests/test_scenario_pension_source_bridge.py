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
