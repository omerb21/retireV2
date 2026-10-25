"""SC-03C: detached factual-versus-decision scenario snapshot candidate.

A candidate is NOT a planning-calculation input. Does not admit tax,
professional eligibility, permission or execution. No database writes.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping

from app.services.scenario_input_manifest_service import _fingerprint


def build_snapshot_candidate(manifest: Mapping) -> dict:
    """Partition checked manifest evidence into source facts and proposed decisions.

    Caller must obtain the manifest in one isolated read-only DB snapshot.
    The recorded fingerprint is recomputed to reject tampered/stale envelopes.
    """
    blockers: list[str] = []
    envelope_fields = ("schema_version", "client_id", "scenario_id", "scenario_version",
                       "scenario_status", "decisions")
    if not isinstance(manifest, Mapping) or any(k not in manifest for k in envelope_fields):
        return _invalid(["MANIFEST_SHAPE_INVALID"])
    identity = {key: manifest[key] for key in envelope_fields}
    if manifest.get("schema_version") != "SCENARIO_INERT_MANIFEST_V1" or (
        manifest.get("manifest_fingerprint") != _fingerprint(identity)
    ):
        return _invalid(["MANIFEST_INTEGRITY_INVALID"])
    if manifest.get("execution_allowed") is not False or (
        manifest.get("planning_snapshot") is not None
        or manifest.get("financial_result") is not None
        or manifest.get("authority_state") != "NOT_EVALUATED"
    ):
        return _invalid(["MANIFEST_AUTHORITY_CONTRACT_INVALID"])
    if manifest["scenario_status"] != "draft":
        blockers.append("SCENARIO_NOT_ACTIVE_DRAFT")
    if not isinstance(manifest["decisions"], list) or not manifest["decisions"]:
        return _invalid(blockers + ["SCENARIO_DECISIONS_EMPTY_OR_INVALID"])

    facts = {}
    proposed = []
    allocated = defaultdict(lambda: Decimal("0.00"))
    seen_decisions = set()
    for row in manifest["decisions"]:
        if not isinstance(row, Mapping):
            return _invalid(blockers + ["DECISION_SHAPE_INVALID"])
        try:
            decision_id = row["decision_id"]
            product_id = row["product_id"]
            component_id = row["component_id"]
            code = row["component_code"]
            source = row["source"]
            amount_text = row["amount"]
            amount = Decimal(amount_text)
            if not all(isinstance(v, str) and v for v in (decision_id, product_id, component_id, code)):
                raise ValueError("invalid identifier")
            if not isinstance(amount_text, str) or not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
                raise ValueError("invalid amount")
            if row["action"] not in {"pension", "capital_asset"}:
                raise ValueError("invalid action")
            if not isinstance(source, Mapping):
                blockers.append("SOURCE_MISSING:" + decision_id)
                continue
            key = (product_id, component_id)
            if (source["product_id"], source["component_id"], source["component_code"]) != (product_id, component_id, code):
                blockers.append("SOURCE_IDENTITY_MISMATCH:" + decision_id)
                continue
            balance = Decimal(source["balance"])
            if not balance.is_finite() or balance < 0 or balance.as_tuple().exponent < -2:
                raise ValueError("invalid balance")
            fact = {
                "product_id": product_id, "component_id": component_id, "component_code": code,
                "product_version": source["product_version"], "balance": format(balance, ".2f"),
                "source_fingerprint": source["source_fingerprint"],
            }
            if key in facts and facts[key] != fact:
                blockers.append("CONFLICTING_SOURCE_FACTS:" + decision_id)
            facts[key] = fact
            allocated[key] += amount
            if (row["product_version_at_review"] != source["product_version"]
                or row["source_fingerprint_at_review"] != source["source_fingerprint"]
                or row["validation_state"] != "unverified"):
                blockers.append("SOURCE_STALE:" + decision_id)
            if decision_id in seen_decisions:
                blockers.append("DUPLICATE_DECISION_ID:" + decision_id)
            seen_decisions.add(decision_id)
            proposed.append({
                "decision_id": decision_id, "product_id": product_id,
                "component_id": component_id, "component_code": code,
                "amount": format(amount, ".2f"), "action": row["action"],
                "effective_date": row["effective_date"],
            })
        except (KeyError, TypeError, ValueError, InvalidOperation):
            blockers.append("DECISION_INVALID")
    for key, total in allocated.items():
        if total > Decimal(facts[key]["balance"]):
            blockers.append("SOURCE_OVERALLOCATED:" + key[0] + ":" + key[1])
    source_facts = [facts[key] for key in sorted(facts)]
    decisions = sorted(proposed, key=lambda row: row["decision_id"])
    partition = {
        "client_id": manifest["client_id"], "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "source_facts": source_facts, "proposed_decisions": decisions,
    }
    blockers = sorted(set(blockers))
    return {
        "schema_version": "SCENARIO_SNAPSHOT_CANDIDATE_V1",
        **partition,
        "partition_fingerprint": _fingerprint(partition),
        "evidence_state": "BLOCKED" if blockers else "STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
        "blockers": blockers,
        "planning_snapshot": None, "execution_allowed": False,
        "financial_result": None, "authority_state": "NOT_EVALUATED",
    }


def _invalid(blockers: list[str]) -> dict:
    return {
        "schema_version": "SCENARIO_SNAPSHOT_CANDIDATE_V1",
        "evidence_state": "BLOCKED", "blockers": blockers,
        "planning_snapshot": None, "execution_allowed": False,
        "financial_result": None, "authority_state": "NOT_EVALUATED",
    }
