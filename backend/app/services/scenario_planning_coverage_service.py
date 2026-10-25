"""SC-03D/D2: non-executing scenario producer-coverage inventory.

Only consumes the authoritative manifest/candidate pair returned from the
database-owned PostgreSQL snapshot. Presence is never inferred from a draft
source row: no scenario-safe authority producers are admitted here.
"""
from __future__ import annotations

from app.services.scenario_input_manifest_service import (
    ManifestValidationError, _fingerprint, validate_inert_manifest,
)

REQUIREMENTS = {
    "pension": (
        "scenario_safe_pension_monthly_basis",
        "scenario_safe_pension_temporal_authority",
        "scenario_safe_retirement_target",
    ),
    "capital_asset": (
        "scenario_safe_capital_asset_registry",
        "scenario_safe_capital_projection_basis",
        "scenario_safe_retirement_target",
    ),
}


def _blocked(code: str) -> dict:
    return {
        "schema_version": "SCENARIO_PLANNING_COVERAGE_V1",
        "coverage_state": "BLOCKED",
        "blockers": [code],
        "execution_allowed": False,
        "planning_snapshot": None,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }


def inventory_from_authoritative_pair(pair: object) -> dict:
    """Inventory within a trusted internal boundary; never infer approval.

    The pair must originate from build_manifest_candidate_snapshot, not a
    user-supplied JSON object. Schema checks detect accidental inconsistencies,
    not cryptographically authenticate externally constructed pairs.
    """
    if type(pair) is not dict or set(pair) != {"manifest", "candidate"}:
        return _blocked("SNAPSHOT_PAIR_INVALID")
    try:
        manifest = validate_inert_manifest(pair["manifest"])
    except ManifestValidationError:
        return _blocked("MANIFEST_INVALID")
    candidate = pair["candidate"]
    if type(candidate) is not dict or (
        candidate.get("client_id") != manifest["client_id"]
        or candidate.get("scenario_id") != manifest["scenario_id"]
        or candidate.get("scenario_version") != manifest["scenario_version"]
        or candidate.get("manifest_fingerprint") != manifest["manifest_fingerprint"]
        or candidate.get("execution_allowed") is not False
        or candidate.get("planning_snapshot") is not None
        or candidate.get("financial_result") is not None
        or candidate.get("authority_state") != "NOT_EVALUATED"
    ):
        return _blocked("CANDIDATE_IDENTITY_INVALID")
    # Do not silently treat an invalid or blocked candidate as a producer.
    if candidate.get("evidence_state") != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED" or candidate.get("blockers") != []:
        return _blocked("CANDIDATE_NOT_STRUCTURALLY_CONSISTENT")
    proposed = candidate.get("proposed_decisions")
    if type(proposed) is not list or len(proposed) != len(manifest["decisions"]):
        return _blocked("DECISION_COVERAGE_INVALID")
    expected = sorted(
        ((row["decision_id"], row["action"], row["product_id"], row["component_id"])
         for row in manifest["decisions"])
    )
    actual = sorted(
        ((row.get("decision_id"), row.get("action"), row.get("product_id"), row.get("component_id"))
         for row in proposed if type(row) is dict)
    )
    if expected != actual:
        return _blocked("DECISION_COVERAGE_INVALID")
    entries = []
    for row in manifest["decisions"]:
        entries.append({
            "decision_id": row["decision_id"],
            "action": row["action"],
            "requirements": [{
                "producer": name,
                "state": "UNRESOLVED",
                "blocker": "MISSING_SCENARIO_SAFE_PRODUCER",
            } for name in REQUIREMENTS[row["action"]]],
        })
    identity = {
        "schema_version": "SCENARIO_PLANNING_COVERAGE_V1",
        "client_id": manifest["client_id"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "decision_coverage": entries,
    }
    return {
        **identity,
        "inventory_fingerprint": _fingerprint(identity),
        "coverage_state": "UNRESOLVED",
        "blockers": ["MISSING_SCENARIO_SAFE_PRODUCER"],
        "execution_allowed": False,
        "planning_snapshot": None,
        "financial_result": None,
        "authority_state": "NOT_EVALUATED",
    }


def build_planning_coverage_snapshot(
    factory,
    *,
    client_id: int,
    scenario_id: str,
) -> dict:
    """Public DB-owned D3 entrypoint; accepts identities, never a caller pair.

    Existing snapshot owner generates source evidence in one PostgreSQL RR/RO
    transaction. The inventory is a pure, inert post-processing step on the
    detached verified pair; no second DB read or independent transaction.
    """
    from app.services.scenario_snapshot_candidate_service import (
        build_manifest_candidate_snapshot,
    )

    pair = build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
    )
    return inventory_from_authoritative_pair(pair)
