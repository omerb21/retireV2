"""Database-authoritative snapshot adapter for non-financial allocation evidence.

Reuses the accepted SC-03 read-only PostgreSQL snapshot owner. Does not mount
a route, persist an outcome, evaluate cashflow, or grant execution authority.
"""
from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.services.scenario_allocation_evidence import (
    reconcile_inert_manifest_allocations,
)
from app.services.scenario_snapshot_candidate_service import (
    build_manifest_candidate_snapshot,
)


def _allocation_extension(_db: Session, pair: dict) -> dict:
    """Called inside the single canonical read-only transaction."""
    manifest = pair["manifest"]
    candidate = pair["candidate"]
    evidence = reconcile_inert_manifest_allocations(manifest)
    blocked = (\n        candidate["evidence_state"] != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"\n        or bool(candidate["blockers"])\n        or evidence["overall_status"] == "BLOCKED"\n    )
    # SC-03A/C remains the owner of structural admission and its blockers.
    # Do not let this informational adapter convert a BLOCKED candidate into
    # financial approval or a current, eligible scenario calculation.
    return {
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "candidate_evidence_state": candidate["evidence_state"],
        "candidate_blockers": list(candidate["blockers"]),
        "overall_status": "BLOCKED" if blocked else "STRUCTURAL_ONLY",
        "allocation_evidence": evidence,
        "financial_result": None,
        "execution_allowed": False,
    }


def build_readonly_allocation_snapshot(
    factory: sessionmaker[Session], *, client_id: int, scenario_id: str,
) -> dict:
    """Derive read-only allocation evidence from the exact original SC-03 snapshot.

    Transaction isolation, session lifecycle, client identity and database
    failure semantics are delegated to the existing canonical snapshot owner.
    """
    return build_manifest_candidate_snapshot(
        factory,
        client_id=client_id,
        scenario_id=scenario_id,
        _snapshot_extension=_allocation_extension,
    )
