"""Pure, non-financial scenario allocation reconciliation.

This module produces evidence of how much of each accepted *factual* component
has been assigned to hypothetical scenario decisions. It never estimates
income, taxes, capital withdrawals, eligibility, or executable permissions.

Caller must supply an already validated, database-derived inert manifest.
This module deliberately does not open a transaction or accept financial
authority based on a caller-supplied hash.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.services.scenario_input_manifest_service import _fingerprint, validate_inert_manifest


def reconcile_inert_manifest_allocations(manifest: dict) -> dict:
    """Return detached per-source reconciliation, never execution admission.

    The output is evidence only and must not be treated as current financial
    result. A missing source, conflicting factual representation, stale review,
    or over-allocation blocks the relevant source evidence.

    A source appears only if at least one scenario decision references it.
    Therefore this function does *not* claim to inventory other client assets.
    """
    valid = validate_inert_manifest(manifest)
    sources: dict[tuple[str, str], dict] = {}
    allocated: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))
    decisions: dict[tuple[str, str], list[str]] = defaultdict(list)
    reasons: dict[tuple[str, str], set[str]] = defaultdict(set)
    inactive = valid["scenario_status"] != "draft"

    for decision in valid["decisions"]:
        key = (decision["product_id"], decision["component_id"])
        decision_id = decision["decision_id"]
        decisions[key].append(decision_id)
        allocated[key] += Decimal(decision["amount"])
        source = decision["source"]
        if source is None:
            reasons[key].add("SOURCE_MISSING")
            continue
        if key in sources and sources[key] != source:
            reasons[key].add("SOURCE_CONFLICT")
        else:
            sources.setdefault(key, source)
        if (
            decision["validation_state"] != "unverified"
            or decision["product_version_at_review"] != source["product_version"]
            or decision["source_fingerprint_at_review"] != source["source_fingerprint"]
        ):
            reasons[key].add("SOURCE_STALE")

    rows = []
    all_blockers: set[str] = set()
    if not valid["decisions"]:
        all_blockers.add("SCENARIO_DECISIONS_EMPTY_OR_INVALID")
    for product_id, component_id in sorted(decisions):
        key = (product_id, component_id)
        source = sources.get(key)
        total = allocated[key]
        balance = Decimal(source["balance"]) if source is not None else None
        blocked = reasons[key]
        if inactive:
            blocked.add("SCENARIO_NOT_ACTIVE_DRAFT")
        if balance is not None and total > balance:
            blocked.add("SOURCE_OVERALLOCATED")
        # With conflicting evidence, a subtracted number would be misleading.
        remainder = (
            balance - total
            if balance is not None and not blocked
            else None
        )
        all_blockers.update(blocked)
        rows.append({
            "product_id": product_id,
            "component_id": component_id,
            "component_code": source["component_code"] if source else None,
            "source_fingerprint": source["source_fingerprint"] if source else None,
            "balance": format(balance, ".2f") if balance is not None else None,
            "allocated": format(total, ".2f"),
            "unallocated": format(remainder, ".2f") if remainder is not None else None,
            "decision_ids": sorted(decisions[key]),
            "status": "BLOCKED" if blocked else "STRUCTURAL_ONLY",
            "blocker_codes": sorted(blocked),
        })
    evidence = {
        "schema_version": "SCENARIO_ALLOCATION_EVIDENCE_V1",
        "client_id": valid["client_id"],
        "scenario_id": valid["scenario_id"],
        "scenario_version": valid["scenario_version"],
        "manifest_fingerprint": valid["manifest_fingerprint"],
        "sources": rows,
        "overall_status": "BLOCKED" if all_blockers else "STRUCTURAL_ONLY",
        "blocker_codes": sorted(all_blockers),
        "financial_result": None,
        "execution_allowed": False,
    }
    return {**evidence, "evidence_fingerprint": _fingerprint(evidence)}
