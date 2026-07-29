from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event, func, inspect, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


M03_TARGET_KINDS = ("source_evidence_review", "manual_record_review")
M03_REVIEW_STATES = ("under_review", "accepted", "rejected")
M03_WORKFLOW_ACTOR = "system:m03-review-ui:M03 review workflow"


def new_m03_revision_id() -> str:
    return f"M03-R-{uuid4().hex}"


def new_m03_annotation_id() -> str:
    return f"M03-A-{uuid4().hex}"


def m03_server_timestamp() -> datetime:
    return datetime.now(timezone.utc)


class M03ReviewRevision(Base):
    __tablename__ = "m03_review_revisions"
    __table_args__ = (
        CheckConstraint("target_kind IN ('source_evidence_review','manual_record_review')", name="ck_m03_review_target_kind"),
        CheckConstraint("state IN ('under_review','accepted','rejected')", name="ck_m03_review_state"),
        CheckConstraint(
            "(target_kind = 'source_evidence_review' AND source_id IS NOT NULL) OR "
            "(target_kind = 'manual_record_review' AND source_id IS NULL)",
            name="ck_m03_review_target_provenance",
        ),
        CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL AND state = 'under_review') OR "
            "(revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m03_review_revision_shape",
        ),
        UniqueConstraint("client_id", "intake_id", "revision_sequence", name="uq_m03_review_target_sequence"),
        UniqueConstraint("predecessor_revision_id", name="uq_m03_review_predecessor_child"),
        UniqueConstraint("revision_id", "client_id", name="uq_m03_review_revision_client"),
        Index("ix_m03_review_client_target", "client_id", "intake_id", "revision_sequence"),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("m02_intake_records.intake_id"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("m02_preserved_sources.source_id"), nullable=True)
    predecessor_revision_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("m03_review_revisions.revision_id"), nullable=True)
    revision_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class M03Annotation(Base):
    __tablename__ = "m03_annotations"
    __table_args__ = (
        CheckConstraint("length(trim(topic)) > 0", name="ck_m03_annotation_topic"),
        CheckConstraint("length(trim(note)) > 0", name="ck_m03_annotation_note"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_m03_annotation_reason"),
        CheckConstraint("supersedes_annotation_id IS NULL OR supersedes_annotation_id != annotation_id", name="ck_m03_annotation_not_self"),
        UniqueConstraint("supersedes_annotation_id", name="uq_m03_annotation_superseded_once"),
        Index("ix_m03_annotation_client_target", "client_id", "intake_id", "created_at"),
    )

    annotation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), ForeignKey("m02_intake_records.intake_id"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("m02_preserved_sources.source_id"), nullable=True)
    review_revision_id: Mapped[str] = mapped_column(String(64), ForeignKey("m03_review_revisions.revision_id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    supersedes_annotation_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("m03_annotations.annotation_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _prevent_update(_mapper, _connection, target) -> None:
    if inspect(target).persistent:
        raise ValueError("M03 append-only records are immutable")


def _prevent_delete(_mapper, _connection, _target) -> None:
    raise ValueError("M03 append-only records cannot be deleted")


def _validate_review_insert(_mapper, connection, target: M03ReviewRevision) -> None:
    from app.models.m02_intake import M02IntakeRecord, M02PreservedSource

    target.revision_id = new_m03_revision_id()
    target.decided_at = m03_server_timestamp()

    intake = connection.execute(
        select(
            M02IntakeRecord.client_id,
            M02IntakeRecord.record_kind,
        ).where(M02IntakeRecord.intake_id == target.intake_id)
    ).one_or_none()
    if intake is None or intake.client_id != target.client_id:
        raise ValueError("M03 review target must belong to the same client")

    if intake.record_kind == "manual":
        if target.target_kind != "manual_record_review" or target.source_id is not None:
            raise ValueError("M03 manual review provenance is inconsistent")
    elif intake.record_kind == "uploaded_source":
        source = connection.execute(
            select(
                M02PreservedSource.client_id,
                M02PreservedSource.intake_id,
            ).where(M02PreservedSource.source_id == target.source_id)
        ).one_or_none()
        if (
            target.target_kind != "source_evidence_review"
            or source is None
            or source.client_id != target.client_id
            or source.intake_id != target.intake_id
        ):
            raise ValueError("M03 uploaded review provenance is inconsistent")
    else:
        raise ValueError("M03 review target kind is unsupported")

    if target.actor != M03_WORKFLOW_ACTOR:
        raise ValueError("M03 review actor must be server-controlled")
    if target.reason is not None:
        target.reason = target.reason.strip()

    if target.revision_sequence == 1:
        if (
            target.predecessor_revision_id is not None
            or target.state != "under_review"
            or target.reason is not None
        ):
            raise ValueError("M03 root review revision is inconsistent")
        return

    if target.reason is None or not target.reason.strip():
        raise ValueError("M03 state-changing revisions require a reason")
    predecessor = connection.execute(
        select(
            M03ReviewRevision.client_id,
            M03ReviewRevision.intake_id,
            M03ReviewRevision.source_id,
            M03ReviewRevision.target_kind,
            M03ReviewRevision.revision_sequence,
            M03ReviewRevision.state,
        ).where(M03ReviewRevision.revision_id == target.predecessor_revision_id)
    ).one_or_none()
    if predecessor is None:
        raise ValueError("M03 predecessor revision does not exist")
    if (
        predecessor.client_id != target.client_id
        or predecessor.intake_id != target.intake_id
        or predecessor.source_id != target.source_id
        or predecessor.target_kind != target.target_kind
        or predecessor.revision_sequence + 1 != target.revision_sequence
    ):
        raise ValueError("M03 predecessor must belong to the same target chain")
    allowed = (
        predecessor.state == "under_review"
        and target.state in {"accepted", "rejected"}
    ) or (
        predecessor.state in {"accepted", "rejected"}
        and target.state == "under_review"
    )
    if not allowed:
        raise ValueError("M03 review lifecycle transition is invalid")


def _validate_annotation_insert(_mapper, connection, target: M03Annotation) -> None:
    from app.models.m02_intake import M02IntakeRecord, M02PreservedSource

    target.annotation_id = new_m03_annotation_id()
    target.created_at = m03_server_timestamp()

    if target.actor != M03_WORKFLOW_ACTOR:
        raise ValueError("M03 annotation actor must be server-controlled")
    target.topic = target.topic.strip()
    target.note = target.note.strip()
    target.reason = target.reason.strip()
    if any(not value.strip() for value in (target.topic, target.note, target.reason)):
        raise ValueError("M03 annotation text must not be blank")

    intake = connection.execute(
        select(
            M02IntakeRecord.client_id,
            M02IntakeRecord.record_kind,
        ).where(M02IntakeRecord.intake_id == target.intake_id)
    ).one_or_none()
    if intake is None or intake.client_id != target.client_id:
        raise ValueError("M03 annotation target must belong to the same client")
    if intake.record_kind == "manual":
        if target.source_id is not None:
            raise ValueError("M03 manual annotation cannot reference a source")
    else:
        source = connection.execute(
            select(
                M02PreservedSource.client_id,
                M02PreservedSource.intake_id,
            ).where(M02PreservedSource.source_id == target.source_id)
        ).one_or_none()
        if (
            source is None
            or source.client_id != target.client_id
            or source.intake_id != target.intake_id
        ):
            raise ValueError("M03 uploaded annotation provenance is inconsistent")

    revision = connection.execute(
        select(
            M03ReviewRevision.client_id,
            M03ReviewRevision.intake_id,
            M03ReviewRevision.source_id,
        ).where(M03ReviewRevision.revision_id == target.review_revision_id)
    ).one_or_none()
    if (
        revision is None
        or revision.client_id != target.client_id
        or revision.intake_id != target.intake_id
        or revision.source_id != target.source_id
    ):
        raise ValueError("M03 annotation revision must belong to the same target chain")

    if target.supersedes_annotation_id is None:
        return
    if target.supersedes_annotation_id == target.annotation_id:
        raise ValueError("M03 annotation cannot supersede itself")
    prior = connection.execute(
        select(
            M03Annotation.client_id,
            M03Annotation.intake_id,
            M03Annotation.source_id,
            M03Annotation.review_revision_id,
        ).where(M03Annotation.annotation_id == target.supersedes_annotation_id)
    ).one_or_none()
    if (
        prior is None
        or prior.client_id != target.client_id
        or prior.intake_id != target.intake_id
        or prior.source_id != target.source_id
    ):
        raise ValueError("M03 superseded annotation must belong to the same target")
    prior_revision = connection.execute(
        select(
            M03ReviewRevision.client_id,
            M03ReviewRevision.intake_id,
            M03ReviewRevision.source_id,
        ).where(M03ReviewRevision.revision_id == prior.review_revision_id)
    ).one_or_none()
    if (
        prior_revision is None
        or prior_revision.client_id != revision.client_id
        or prior_revision.intake_id != revision.intake_id
        or prior_revision.source_id != revision.source_id
    ):
        raise ValueError("M03 superseded annotation must belong to the same review chain")


event.listen(M03ReviewRevision, "before_update", _prevent_update)
event.listen(M03ReviewRevision, "before_delete", _prevent_delete)
event.listen(M03ReviewRevision, "before_insert", _validate_review_insert)
event.listen(M03Annotation, "before_update", _prevent_update)
event.listen(M03Annotation, "before_delete", _prevent_delete)
event.listen(M03Annotation, "before_insert", _validate_annotation_insert)
