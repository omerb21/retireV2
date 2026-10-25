"""SC-05E internal append-only documentary review writer.

Only a trusted server caller can supply the authenticated actor and a
same-snapshot DB-derived expected context. No public API or authority grant.
Caller owns the database transaction and MUST NOT take expected from a request.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario_coefficient_professional_review import ScenarioCoefficientProfessionalReview as Review
from app.services.scenario_coefficient_professional_review_contract import validate_documentary_review
from app.services.scenario_draft_service import DraftError, _scenario
from app.services.scenario_input_manifest_service import _fingerprint


_DERIVED_CONTEXT_CAPABILITY = object()


def _append_documentary_review(
    db: Session, *, client_id: int, scenario_id: str,
    expected: dict, authenticated_actor: str, review_reference: str,
    decision: str, _capability: object = None,
) -> dict:
    """Record immutable evidence; NEVER confer coefficient/execution authority."""
    if _capability is not _DERIVED_CONTEXT_CAPABILITY:
        raise DraftError("PROFESSIONAL_REVIEW_DERIVED_CONTEXT_REQUIRED", 403)
    if (not isinstance(authenticated_actor, str)
            or not authenticated_actor.strip()
            or authenticated_actor == "local-development-only"
            or len(authenticated_actor) > 128):
        raise DraftError("PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED", 403)
    if (not isinstance(review_reference, str) or not review_reference.strip()
            or len(review_reference) > 128):
        raise DraftError("PROFESSIONAL_REVIEW_REFERENCE_REQUIRED", 422)
    if decision not in {"reviewed_for_candidate", "rejected"}:
        raise DraftError("PROFESSIONAL_REVIEW_DECISION_INVALID", 422)
    scenario = _scenario(db, client_id, scenario_id)
    if scenario.status != "draft":
        raise DraftError("PROFESSIONAL_REVIEW_SCENARIO_NOT_DRAFT", 409)
    if (type(expected) is not dict or expected.get("client_id") != client_id
            or expected.get("scenario_id") != scenario_id
            or expected.get("scenario_version") != scenario.version):
        raise DraftError("PROFESSIONAL_REVIEW_CONTEXT_STALE", 409)
    # Ensure a scenario decision exists. The full source identity must already
    # have been constructed in the same transaction by a trusted projection.
    from app.models.scenario_draft import ScenarioDraftDecision
    row = db.scalar(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
        ScenarioDraftDecision.decision_id == expected.get("decision_id"),
        ScenarioDraftDecision.action == "pension"))
    if row is None or row.source_product_id != expected.get("product_id") or row.source_component_id != expected.get("component_id"):
        raise DraftError("PROFESSIONAL_REVIEW_DECISION_STALE", 409)
    record = {
        **expected, "schema_version": "SCENARIO_COEFFICIENT_REVIEW_V1",
        "professional_actor_id": authenticated_actor,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_reference": review_reference, "decision": decision,
    }
    record["record_fingerprint"] = _fingerprint(record)
    validation = validate_documentary_review(record, expected)
    if validation["state"] != "DOCUMENTARY_REVIEW_MATCHED_NOT_AUTHORIZED":
        raise DraftError("PROFESSIONAL_REVIEW_EVIDENCE_INVALID", 409)
    db.add(Review(
        review_id=uuid4().hex,
        **{key: value for key, value in record.items()
           if key not in {"schema_version", "reviewed_at"}},
        reviewed_at=datetime.fromisoformat(record["reviewed_at"]),
    ))
    db.flush()
    return {
        "schema_version": "SCENARIO_DOCUMENTARY_REVIEW_WRITE_V1",
        "review_fingerprint": record["record_fingerprint"],
        "review_state": "RECORDED_NOT_AUTHORIZED",
        "execution_allowed": False, "coefficient_candidate": None,
        "financial_result": None, "planning_snapshot": None,
        "authority_state": "NOT_EVALUATED",
    }


def append_database_derived_documentary_review(
    db: Session, *, client_id: int, scenario_id: str, decision_id: str,
    authenticated_actor: str, review_reference: str, decision: str,
) -> dict:
    """Trusted internal writer: independently derive provenance in this transaction.

    The caller MUST control authenticated_actor using verified server session
    state. This is documentary evidence, not coefficient/calculation permission.
    """
    from app.services.scenario_coefficient_review_context_service import (
        derive_documentary_review_context,
    )
    # Validate actor before initiating any evidence reads.
    if (not isinstance(authenticated_actor, str) or not authenticated_actor.strip()
            or authenticated_actor == "local-development-only"
            or len(authenticated_actor) > 128):
        raise DraftError("PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED", 403)
    expected = derive_documentary_review_context(
        db, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id)
    return _append_documentary_review(
        db, client_id=client_id, scenario_id=scenario_id, expected=expected,
        authenticated_actor=authenticated_actor, review_reference=review_reference,
        decision=decision, _capability=_DERIVED_CONTEXT_CAPABILITY,
    )


def append_authenticated_serializable_review(
    factory, *, request, client_id: int, scenario_id: str,
    decision_id: str, review_reference: str, decision: str,
) -> dict:
    """Private production-only orchestration with authenticated actor and DB ownership.

    No public route is registered. Owns SERIALIZABLE write transaction from its
    first SQL statement. A caller must never pass a pre-used ORM Session.
    """
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.engine import Engine

    auth_config = getattr(getattr(request, "app", None), "state", None)
    auth_config = getattr(auth_config, "auth_config", None)
    state = getattr(request, "state", None)
    verified_session = getattr(state, "auth_session", None)
    actor = getattr(state, "trusted_professional_actor", None)
    if (auth_config is None or getattr(auth_config, "production", None) is not True
            or type(verified_session) is not dict
            or type(actor) is not str or not actor
            or actor != verified_session.get("actor_id")):
        raise DraftError("PROFESSIONAL_REVIEW_AUTHENTICATED_ACTOR_REQUIRED", 403)
    if not isinstance(factory, sessionmaker):
        raise DraftError("PROFESSIONAL_REVIEW_POSTGRESQL_REQUIRED", 503)
    engine = factory.kw.get("bind")
    if not isinstance(engine, Engine) or engine.dialect.name != "postgresql":
        raise DraftError("PROFESSIONAL_REVIEW_POSTGRESQL_REQUIRED", 503)
    with factory() as db:
        # Caller-owned sessions and transaction state never cross this boundary.
        with db.begin():
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            with db.no_autoflush:
                return append_database_derived_documentary_review(
                    db, client_id=client_id, scenario_id=scenario_id,
                    decision_id=decision_id, authenticated_actor=actor,
                    review_reference=review_reference, decision=decision,
                )
