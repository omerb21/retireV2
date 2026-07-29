from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.m02_intake import M02IntakeRecord, M02PreservedSource
from app.models.m03_review import M03Annotation, M03ReviewRevision
from app.schemas.m03_review import M03AnnotationRequest, M03AnnotationResponse, M03RevisionResponse, M03TargetResponse
from app.services.m01_case_service import effective_lifecycle_status


ACTOR = "system:m03-review-ui:M03 review workflow"


class M03ReviewError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _not_found() -> M03ReviewError:
    return M03ReviewError(404, "M03_RESOURCE_NOT_FOUND", "Resource not found")


def _client(db: Session, client_id: int) -> Client:
    row = db.scalar(select(Client).where(Client.client_id == client_id))
    if row is None:
        raise _not_found()
    return row


def _mutable_client(db: Session, client_id: int) -> Client:
    row = _client(db, client_id)
    if effective_lifecycle_status(row.status) == "archived":
        raise M03ReviewError(409, "M03_ARCHIVED_CASE_READ_ONLY", "Archived client cases are read-only")
    return row


def _intake(db: Session, client_id: int, intake_id: str) -> M02IntakeRecord:
    row = db.scalar(select(M02IntakeRecord).where(M02IntakeRecord.client_id == client_id, M02IntakeRecord.intake_id == intake_id))
    if row is None:
        raise _not_found()
    return row


def _target(intake: M02IntakeRecord) -> tuple[str, M02PreservedSource | None]:
    source = intake.preserved_source
    if intake.record_kind == "manual":
        if source is not None:
            raise M03ReviewError(409, "M03_INVALID_MANUAL_PROVENANCE", "Manual target provenance is inconsistent")
        return "manual_record_review", None
    if intake.record_kind == "uploaded_source" and source is not None and source.blob is not None:
        if source.client_id != intake.client_id or source.blob.client_id != intake.client_id:
            raise _not_found()
        return "source_evidence_review", source
    raise M03ReviewError(409, "M03_INCOMPLETE_UPLOADED_PROVENANCE", "Uploaded target provenance is incomplete")


def _history(db: Session, client_id: int, intake_id: str) -> list[M03ReviewRevision]:
    return list(db.scalars(select(M03ReviewRevision).where(
        M03ReviewRevision.client_id == client_id,
        M03ReviewRevision.intake_id == intake_id,
    ).order_by(M03ReviewRevision.revision_sequence)).all())


def _leaf(rows: list[M03ReviewRevision]) -> M03ReviewRevision | None:
    if not rows:
        return None
    for index, row in enumerate(rows, 1):
        expected_parent = None if index == 1 else rows[index - 2].revision_id
        if row.revision_sequence != index or row.predecessor_revision_id != expected_parent:
            raise M03ReviewError(409, "M03_REVIEW_CHAIN_INCONSISTENT", "Review chain is inconsistent")
    return rows[-1]


def revision_response(row: M03ReviewRevision) -> M03RevisionResponse:
    return M03RevisionResponse(
        revision_id=row.revision_id,
        revision_sequence=row.revision_sequence,
        predecessor_revision_id=row.predecessor_revision_id,
        state=row.state,
        reason=row.reason,
        actor=row.actor,
        decided_at=row.decided_at,
    )


def target_response(db: Session, client_id: int, intake_id: str) -> M03TargetResponse:
    _client(db, client_id)
    intake = _intake(db, client_id, intake_id)
    kind, source = _target(intake)
    rows = _history(db, client_id, intake_id)
    try:
        leaf = _leaf(rows)
    except M03ReviewError:
        leaf = None
        exclusion = "review_chain_inconsistent"
    else:
        exclusion = None
    if exclusion is None:
        if intake.lifecycle_status != "accepted_for_review":
            exclusion = f"m02_{intake.lifecycle_status}"
        elif leaf is None:
            exclusion = "review_not_started"
        elif leaf.state != "accepted":
            exclusion = f"review_{leaf.state}"
    eligible = exclusion is None
    return M03TargetResponse(
        client_id=client_id,
        intake_id=intake_id,
        target_kind=kind,
        m02_lifecycle_status=intake.lifecycle_status,
        source_id=source.source_id if source else None,
        blob_id=source.blob_id if source else None,
        sha256_checksum=source.blob.sha256_checksum if source else None,
        current_revision=revision_response(leaf) if leaf else None,
        accepted_revision_id=leaf.revision_id if eligible and leaf else None,
        eligible=eligible,
        exclusion_reason=exclusion,
    )


def list_candidates(db: Session, client_id: int) -> list[M03TargetResponse]:
    _client(db, client_id)
    rows = db.scalars(select(M02IntakeRecord).where(
        M02IntakeRecord.client_id == client_id,
        M02IntakeRecord.lifecycle_status == "accepted_for_review",
    ).order_by(M02IntakeRecord.created_at, M02IntakeRecord.intake_id)).all()
    return [target_response(db, client_id, row.intake_id) for row in rows]


def review_history(db: Session, client_id: int, intake_id: str) -> list[M03RevisionResponse]:
    _intake(db, client_id, intake_id)
    return [revision_response(row) for row in _history(db, client_id, intake_id)]


def _append(db: Session, intake: M02IntakeRecord, state: str, reason: str | None, expected: str | None) -> M03ReviewRevision:
    kind, source = _target(intake)
    rows = _history(db, intake.client_id, intake.intake_id)
    leaf = _leaf(rows)
    if expected is not None and (leaf is None or leaf.revision_id != expected):
        raise M03ReviewError(409, "M03_STALE_CURRENT_REVISION", "The review changed before this action")
    row = M03ReviewRevision(
        revision_id=f"M03-R-{uuid4().hex}",
        client_id=intake.client_id,
        target_kind=kind,
        intake_id=intake.intake_id,
        source_id=source.source_id if source else None,
        predecessor_revision_id=leaf.revision_id if leaf else None,
        revision_sequence=len(rows) + 1,
        state=state,
        reason=reason.strip() if reason else None,
        actor=ACTOR,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise M03ReviewError(409, "M03_CONCURRENT_LEAF_CONFLICT", "The review changed concurrently") from error
    db.refresh(row)
    return row


def start_review(db: Session, client_id: int, intake_id: str) -> M03ReviewRevision:
    _mutable_client(db, client_id)
    intake = _intake(db, client_id, intake_id)
    if intake.lifecycle_status != "accepted_for_review":
        raise M03ReviewError(409, "M03_M02_NOT_ACCEPTED_FOR_REVIEW", "M02 intake is not accepted for review")
    if _history(db, client_id, intake_id):
        raise M03ReviewError(409, "M03_REVIEW_ALREADY_STARTED", "Review already exists")
    return _append(db, intake, "under_review", None, None)


def decide_review(db: Session, client_id: int, intake_id: str, action: str, reason: str, expected: str) -> M03ReviewRevision:
    _mutable_client(db, client_id)
    intake = _intake(db, client_id, intake_id)
    leaf = _leaf(_history(db, client_id, intake_id))
    if leaf is None:
        raise M03ReviewError(409, "M03_REVIEW_NOT_STARTED", "Review has not started")
    allowed = leaf.state == "under_review" if action in {"accepted", "rejected"} else leaf.state in {"accepted", "rejected"}
    if not allowed:
        raise M03ReviewError(409, "M03_WRONG_CURRENT_STATE", "The action is not allowed from the current state")
    return _append(db, intake, "under_review" if action == "reopen" else action, reason, expected)


def add_annotation(db: Session, client_id: int, intake_id: str, payload: M03AnnotationRequest) -> M03Annotation:
    _mutable_client(db, client_id)
    intake = _intake(db, client_id, intake_id)
    kind, source = _target(intake)
    revision = db.scalar(select(M03ReviewRevision).where(
        M03ReviewRevision.revision_id == payload.review_revision_id,
        M03ReviewRevision.client_id == client_id,
        M03ReviewRevision.intake_id == intake_id,
    ))
    if revision is None:
        raise _not_found()
    if payload.supersedes_annotation_id:
        prior = db.scalar(select(M03Annotation).where(
            M03Annotation.annotation_id == payload.supersedes_annotation_id,
            M03Annotation.client_id == client_id,
            M03Annotation.intake_id == intake_id,
        ))
        if prior is None:
            raise _not_found()
    row = M03Annotation(
        annotation_id=f"M03-A-{uuid4().hex}",
        client_id=client_id,
        intake_id=intake_id,
        source_id=source.source_id if kind == "source_evidence_review" else None,
        review_revision_id=revision.revision_id,
        topic=payload.topic.strip(),
        note=payload.note.strip(),
        reason=payload.reason.strip(),
        actor=ACTOR,
        supersedes_annotation_id=payload.supersedes_annotation_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise M03ReviewError(409, "M03_ANNOTATION_CONFLICT", "Annotation conflicts with existing history") from error
    db.refresh(row)
    return row


def annotation_response(row: M03Annotation) -> M03AnnotationResponse:
    return M03AnnotationResponse(
        annotation_id=row.annotation_id, review_revision_id=row.review_revision_id,
        intake_id=row.intake_id, source_id=row.source_id, topic=row.topic, note=row.note,
        reason=row.reason, actor=row.actor, supersedes_annotation_id=row.supersedes_annotation_id,
        created_at=row.created_at,
    )


def annotation_history(db: Session, client_id: int, intake_id: str) -> list[M03AnnotationResponse]:
    _intake(db, client_id, intake_id)
    rows = db.scalars(select(M03Annotation).where(
        M03Annotation.client_id == client_id, M03Annotation.intake_id == intake_id
    ).order_by(M03Annotation.created_at, M03Annotation.annotation_id)).all()
    return [annotation_response(row) for row in rows]
