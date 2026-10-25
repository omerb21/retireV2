"""SC-04/P2: inert, deterministic source-identity reconciliation.

Pure processing of a database-derived candidate and canonical pension-source
snapshot from the SAME transaction. A conversion trace establishes history,
not a scenario-admitted pension calculation source. No inferred conversion.
"""
from __future__ import annotations

from app.services.scenario_input_manifest_service import _fingerprint


def reconcile_pension_source_identities(pair: object, pension_sources: object) -> dict:
    """Internal only: caller must own one DB snapshot for both inputs.

    The output is never admission evidence. Fail closed on malformed input.
    """
    blocked = {
        "schema_version": "SCENARIO_PENSION_SOURCE_BRIDGE_V1",
        "bridge_state": "BLOCKED",
        "blockers": ["UNVERIFIED_SHARED_DATABASE_SNAPSHOT"],
        "execution_allowed": False, "planning_snapshot": None,
        "financial_result": None, "authority_state": "NOT_EVALUATED",
    }
    if type(pair) is not dict or type(pair.get("manifest")) is not dict or type(pair.get("candidate")) is not dict or type(pension_sources) is not list:
        return blocked
    manifest, candidate = pair["manifest"], pair["candidate"]
    if (
        candidate.get("evidence_state") != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
        or candidate.get("blockers") != []
        or candidate.get("execution_allowed") is not False
        or candidate.get("manifest_fingerprint") != manifest.get("manifest_fingerprint")
        or candidate.get("scenario_version") != manifest.get("scenario_version")
        or candidate.get("client_id") != manifest.get("client_id")
        or candidate.get("scenario_id") != manifest.get("scenario_id")
    ):
        return blocked
    decisions = candidate.get("proposed_decisions")
    if type(decisions) is not list or not all(type(d) is dict for d in decisions):
        return blocked
    if len({d.get("decision_id") for d in decisions}) != len(decisions):
        return blocked
    if any(type(s) is not dict or type(s.get("source_id")) is not str for s in pension_sources):
        return blocked
    # Histories are never source identities for newly proposed allocations.
    traces: dict[tuple[str, str], set[str]] = {}
    for source in pension_sources:
        if source.get("kind") != "conversion":
            continue
        provenance = source.get("provenance")
        if type(provenance) is not dict:
            return blocked
        allocations = provenance.get("allocations")
        if type(allocations) is not list:
            return blocked
        for trace in allocations:
            if type(trace) is not dict:
                return blocked
            product, component = trace.get("source_product_id"), trace.get("source_component_id")
            if type(product) is not str or type(component) is not str:
                return blocked
            traces.setdefault((product, component), set()).add(source["source_id"])
    entries = []
    for row in sorted(decisions, key=lambda d: d["decision_id"]):
        if row.get("action") != "pension":
            continue
        ids = sorted(traces.get((row.get("product_id"), row.get("component_id")), ()))
        entries.append({
            "decision_id": row["decision_id"],
            "product_id": row["product_id"],
            "component_id": row["component_id"],
            "historical_conversion_source_ids": ids,
            "reconciliation_state": "UNRESOLVED",
            "blocker": "SCENARIO_PENSION_SOURCE_BRIDGE_UNAVAILABLE",
            "trace_note": "HISTORICAL_CONVERSION_NOT_CURRENT_SCENARIO_AUTHORITY" if ids else "NO_HISTORICAL_CONVERSION_TRACE",
        })
    identity = {
        "schema_version": "SCENARIO_PENSION_SOURCE_BRIDGE_V1",
        "client_id": manifest.get("client_id"),
        "scenario_id": manifest.get("scenario_id"),
        "scenario_version": manifest.get("scenario_version"),
        "manifest_fingerprint": manifest.get("manifest_fingerprint"),
        "entries": entries,
    }
    return {
        **identity, "bridge_fingerprint": _fingerprint(identity),
        "bridge_state": "UNRESOLVED", "blockers": ["SCENARIO_PENSION_SOURCE_BRIDGE_UNAVAILABLE"],
        "execution_allowed": False, "planning_snapshot": None,
        "financial_result": None, "authority_state": "NOT_EVALUATED",
    }
