"""M09-P1: non-executable current scenario input inventory, from canonical DB snapshot.

Not an M09 run; does not periodize, sum monthly income or admit financial
execution. The same read-only repeatable-read snapshot owner handles provenance.
"""
from __future__ import annotations

from app.services.scenario_input_manifest_service import _fingerprint
from app.services.scenario_allocation_evidence import reconcile_inert_manifest_allocations
from app.services.scenario_snapshot_candidate_service import build_manifest_candidate_snapshot


def _m09_p1_extension(_db, pair: dict) -> dict:
    manifest = pair["manifest"]
    candidate = pair["candidate"]
    allocation = reconcile_inert_manifest_allocations(manifest)
    structurally_consistent = (
        candidate["evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
        and not candidate["blockers"]
        and allocation["overall_status"] == "STRUCTURAL_ONLY"
    )
    source_status = {
        decision_id: source["status"]
        for source in allocation["sources"]
        for decision_id in source["decision_ids"]
    }
    # Never assume all structural decisions are financial-ready.
    decisions = [{
        "decision_id": row["decision_id"],
        "product_id": row["product_id"],
        "component_id": row["component_id"],
        "component_code": row["component_code"],
        "action": row["action"],
        "effective_date": row["effective_date"],
        "amount_principal": row["amount"],
        "source_fingerprint_at_review": row["source_fingerprint_at_review"],
        "product_version_at_review": row["product_version_at_review"],
        "validation_state": row["validation_state"],
        "ruleset_digest_at_review": row["ruleset_digest_at_review"],
        "permission_preview_id_at_review": row["permission_preview_id_at_review"],
        "input_state": "STRUCTURAL_ONLY" if source_status.get(row["decision_id"]) == "STRUCTURAL_ONLY" else "BLOCKED",
        "monthly_income": None,
        "periodization": None,
    } for row in manifest["decisions"]]
    blockers = sorted(set(candidate["blockers"]) | set(allocation["blocker_codes"]))
    if not decisions:
        blockers = sorted(set(blockers) | {"SCENARIO_DECISIONS_EMPTY_OR_INVALID"})
    if not structurally_consistent and not blockers:
        # Unknown or unadmitted candidate states must carry an explicit reason.
        blockers = ["SCENARIO_CANDIDATE_NOT_ADMITTED"]
    evidence = {
        "schema_version": "M09_CURRENT_SCENARIO_INPUT_INVENTORY_P1_V1",
        "client_id": manifest["client_id"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "allocation_evidence_fingerprint": allocation["evidence_fingerprint"],
        "candidate_partition_fingerprint": candidate.get("partition_fingerprint"),
        "inventory_state": "BLOCKED" if blockers or not structurally_consistent else "STRUCTURAL_ONLY",
        "blocker_codes": blockers,
        "decisions": decisions,
        "source_allocations": allocation["sources"],
        "periodization": None,
        "monthly_cashflow": None,
        "financial_result": None,
        "execution_allowed": False,
    }
    return {**evidence, "inventory_fingerprint": _fingerprint(evidence)}


def build_m09_current_input_inventory(factory, *, client_id: int, scenario_id: str) -> dict:
    """One authoritative DB-owned read transaction; no supplied client facts."""
    return build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
        _snapshot_extension=_m09_p1_extension,
    )
