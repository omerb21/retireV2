from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event, func, inspect
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


M03_TARGET_KINDS = ("source_evidence_review", "manual_record_review")
M03_REVIEW_STATES = ("under_review", "accepted", "rejected")


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
    if inspect(target).modified:
        raise ValueError("M03 append-only records are immutable")


event.listen(M03ReviewRevision, "before_update", _prevent_update)
event.listen(M03Annotation, "before_update", _prevent_update)
