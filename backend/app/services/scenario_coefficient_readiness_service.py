"""SC-06A: read-only documentary readiness, never professional admission.

Reuses the SC-03 PostgreSQL REPEATABLE READ READ ONLY snapshot owner.
A matched documentary review does not grant coefficient/calculation authority.
"""
from datetime import timezone

from sqlalchemy import select

from app.models.scenario_coefficient_professional_review import (
    ScenarioCoefficientProfessionalReview as Review,
)
from app.services.scenario_coefficient_professional_review_contract import validate_documentary_review
from app.services.scenario_coefficient_review_context_service import derive_documentary_review_context
from app.services.scenario_draft_service import DraftError
from app.services.scenario_snapshot_candidate_service import build_manifest_candidate_snapshot


def _blocked(code: str) -> dict:
    return {
        "schema_version": "SCENARIO_COEFFICIENT_READINESS_V1",
        "state": "BLOCKED",
        "blockers": [code],
        "documentary_review_state": "NOT_MATCHED",
        "authority_state": "NOT_EVALUATED",
        "execution_allowed": False,
        "coefficient_candidate": None,
        "financial_result": None,
        "planning_snapshot": None,
    }


def _record(row: Review) -> dict:
    return {
        "schema_version": "SCENARIO_COEFFICIENT_REVIEW_V1",
        "client_id": row.client_id,
        "scenario_id": row.scenario_id,
        "scenario_version": row.scenario_version,
        "decision_id": row.decision_id,
        "product_id": row.product_id,
        "component_id": row.component_id,
        "product_version": row.product_version,
        "manifest_fingerprint": row.manifest_fingerprint,
        "inventory_fingerprint": row.inventory_fingerprint,
        "election_fingerprint": row.election_fingerprint,
        "source_fingerprint": row.source_fingerprint,
        "professional_actor_id": row.professional_actor_id,
        "reviewed_at": row.reviewed_at.astimezone(timezone.utc).isoformat()
            if row.reviewed_at.tzinfo is not None else "",
        "review_reference": row.review_reference,
        "decision": row.decision,
        "record_fingerprint": row.record_fingerprint,
    }


def assess_documentary_readiness(factory, *, client_id: int, scenario_id: str,
                                  decision_id: str) -> dict:
    """Derive canonical facts and inspect immutable reviews in a single snapshot.

    This function has no public route, admission transition or write path.
    """
    if type(decision_id) is not str or not decision_id or len(decision_id) > 64:
        return _blocked("SCENARIO_DECISION_ID_INVALID")

    def within_snapshot(db, pair):
        if pair["candidate"]["evidence_state"] != "STRUCTURALLY_CONSISTENT_NOT_ADMITTED":
            return _blocked("SCENARIO_SOURCE_UNVERIFIED")
        try:
            expected = derive_documentary_review_context(
                db, client_id=client_id, scenario_id=scenario_id,
                decision_id=decision_id,
            )
        except DraftError as error:
            return _blocked(error.code)
        rows = db.scalars(select(Review).where(
            Review.client_id == client_id,
            Review.scenario_id == scenario_id,
            Review.decision_id == decision_id,
        ).order_by(Review.created_at, Review.review_id)).all()
        if not rows:
            return _blocked("DOCUMENTARY_REVIEW_MISSING")
        results = [validate_documentary_review(_record(row), expected) for row in rows]
        matched = [
            (row, result) for row, result in zip(rows, results)
            if result["state"] == "DOCUMENTARY_REVIEW_MATCHED_NOT_AUTHORIZED"
        ]
        if not matched:
            return _blocked("DOCUMENTARY_REVIEW_STALE_OR_INVALID")
        # Any matching rejection prevents an optimistic readiness conclusion.
        if any(row.decision == "rejected" for row, _ in matched):
            return _blocked("DOCUMENTARY_REVIEW_REJECTED")
        return {
            **_blocked("PROFESSIONAL_ADMISSION_NOT_AUTHORIZED"),
            "state": "UNRESOLVED",
            "documentary_review_state": "MATCHED_NOT_AUTHORIZED",
            "scenario_version": expected["scenario_version"],
            "manifest_fingerprint": expected["manifest_fingerprint"],
            "inventory_fingerprint": expected["inventory_fingerprint"],
            "election_fingerprint": expected["election_fingerprint"],
        }

    result = build_manifest_candidate_snapshot(
        factory, client_id=client_id, scenario_id=scenario_id,
        _snapshot_extension=within_snapshot,
    )
    # Snapshot owner returns the extension result as detached data.
    return result
