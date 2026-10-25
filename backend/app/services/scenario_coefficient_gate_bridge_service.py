"""SC-05D: DB-owned bridge from draft coefficient inventory to admission gate.

A draft pension election is not an authorization to invoke the coefficient
lookup. No untrusted source_verified / professional_permission_verified flags.
"""
from app.services.scenario_coefficient_input_inventory_service import build_coefficient_input_inventory
from app.services.scenario_input_manifest_service import _fingerprint


def build_coefficient_gate_bridge(factory, *, client_id: int, scenario_id: str) -> dict:
    inventory = build_coefficient_input_inventory(
        factory, client_id=client_id, scenario_id=scenario_id)
    entries = []
    for entry in inventory["entries"]:
        blockers = entry["blockers"]
        structurally_ready = (
            entry["state"] == "UNRESOLVED"
            and entry["election_state"] == "CURRENT_DRAFT_NOT_ADMITTED"
            and all(code == "SCENARIO_COEFFICIENT_PERMISSION_NOT_EVALUATED" for code in blockers)
        )
        entries.append({
            "decision_id": entry["decision_id"],
            "product_id": entry["product_id"],
            "component_id": entry["component_id"],
            "handoff_state": "PROFESSIONAL_AUTHORITY_REQUIRED" if structurally_ready else "INPUTS_UNRESOLVED",
            "blockers": list(blockers),
            "coefficient_candidate": None,
        })
    identity = {
        "schema_version": "SCENARIO_COEFFICIENT_GATE_BRIDGE_V1",
        "client_id": inventory["client_id"],
        "scenario_id": inventory["scenario_id"],
        "scenario_version": inventory["scenario_version"],
        "manifest_fingerprint": inventory["manifest_fingerprint"],
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "entries": entries,
    }
    return {
        **identity, "bridge_fingerprint": _fingerprint(identity),
        "bridge_state": "BLOCKED" if inventory["inventory_state"] == "BLOCKED" else "UNRESOLVED",
        "execution_allowed": False, "planning_snapshot": None,
        "financial_result": None, "authority_state": "NOT_EVALUATED",
    }
