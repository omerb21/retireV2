from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
    select,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql.dml import Delete, Update

from app.db.base import Base
from app.models.client import Client


class M04ClassificationSubject(Base):
    __tablename__ = "m04_classification_subjects"
    __table_args__ = (
        CheckConstraint(
            "target_kind IN ('source_evidence_review','manual_record_review')",
            name="ck_m04_subject_target_kind",
        ),
        CheckConstraint(
            "archive_generation >= 0",
            name="ck_m04_subject_archive_generation",
        ),
        ForeignKeyConstraint(
            ["intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m04_subject_intake_client",
        ),
        UniqueConstraint(
            "client_id",
            "intake_id",
            "target_kind",
            name="uq_m04_subject_target",
        ),
        UniqueConstraint(
            "subject_id",
            "client_id",
            "intake_id",
            "target_kind",
            name="uq_m04_subject_identity_target",
        ),
        Index("ix_m04_subject_client_target", "client_id", "intake_id"),
    )

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    archive_generation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M04ClassificationRevision(Base):
    __tablename__ = "m04_classification_revisions"
    __table_args__ = (
        CheckConstraint(
            "target_kind IN ('source_evidence_review','manual_record_review')",
            name="ck_m04_revision_target_kind",
        ),
        CheckConstraint(
            "state IN ('under_review','proposed','accepted','unresolved','rejected')",
            name="ck_m04_revision_state",
        ),
        CheckConstraint(
            "action_type IN "
            "('start','proposal','unresolved','accept','reject','reopen',"
            "'override','undo','start_revalidation')",
            name="ck_m04_revision_action_type",
        ),
        CheckConstraint(
            "product_family IS NULL OR product_family IN "
            "('insurance_policy','savings_policy','provident_fund',"
            "'investment_provident_fund','education_fund','pension_fund',"
            "'unknown_or_unresolved')",
            name="ck_m04_revision_product_family",
        ),
        CheckConstraint(
            "aggregate_interpretation IS NULL OR aggregate_interpretation IN "
            "('pension','capital','mixed','unresolved')",
            name="ck_m04_revision_aggregate_interpretation",
        ),
        CheckConstraint(
            "length(evidence_digest) = 64 AND evidence_digest = lower(evidence_digest)",
            name="ck_m04_revision_evidence_digest",
        ),
        CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL "
            "AND action_type = 'start' AND state = 'under_review') OR "
            "(revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m04_revision_shape",
        ),
        ForeignKeyConstraint(
            ["subject_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_subjects.subject_id",
                "m04_classification_subjects.client_id",
                "m04_classification_subjects.intake_id",
                "m04_classification_subjects.target_kind",
            ],
            name="fk_m04_revision_subject_target",
        ),
        ForeignKeyConstraint(
            [
                "predecessor_revision_id",
                "client_id",
                "intake_id",
                "target_kind",
            ],
            [
                "m04_classification_revisions.revision_id",
                "m04_classification_revisions.client_id",
                "m04_classification_revisions.intake_id",
                "m04_classification_revisions.target_kind",
            ],
            name="fk_m04_revision_predecessor_target",
        ),
        ForeignKeyConstraint(
            ["m03_revision_id", "client_id"],
            ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"],
            name="fk_m04_revision_m03_client",
        ),
        UniqueConstraint(
            "subject_id",
            "revision_sequence",
            name="uq_m04_revision_subject_sequence",
        ),
        UniqueConstraint(
            "predecessor_revision_id",
            name="uq_m04_revision_predecessor_child",
        ),
        UniqueConstraint(
            "revision_id",
            "client_id",
            "intake_id",
            "target_kind",
            name="uq_m04_revision_identity_target",
        ),
        UniqueConstraint("revision_id", "client_id", name="uq_m04_revision_identity_client"),
        Index(
            "ix_m04_revision_client_target",
            "client_id",
            "intake_id",
            "target_kind",
            "revision_sequence",
        ),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("m02_preserved_sources.source_id"), nullable=True
    )
    m03_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    predecessor_revision_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    revision_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pension_subtype: Mapped[str | None] = mapped_column(String(128), nullable=True)
    aggregate_interpretation: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    catalogue_version: Mapped[str] = mapped_column(String(64), nullable=False)
    matched_rule_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    match_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    action_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    historical_revision_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("m04_classification_revisions.revision_id"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M04ComponentDecision(Base):
    __tablename__ = "m04_component_decisions"
    __table_args__ = (
        CheckConstraint(
            "component_kind IN "
            "('severance_component','contribution_component','unknown_component')",
            name="ck_m04_component_kind",
        ),
        CheckConstraint(
            "interpretation IN ('pension','capital','unresolved')",
            name="ck_m04_component_interpretation",
        ),
        CheckConstraint(
            "current_employer_related IN ('yes','no','unknown')",
            name="ck_m04_component_employer_related",
        ),
        ForeignKeyConstraint(
            ["revision_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_revisions.revision_id",
                "m04_classification_revisions.client_id",
                "m04_classification_revisions.intake_id",
                "m04_classification_revisions.target_kind",
            ],
            name="fk_m04_component_revision_target",
        ),
        UniqueConstraint(
            "revision_id",
            "evidence_identity",
            name="uq_m04_component_revision_evidence",
        ),
        Index(
            "ix_m04_component_revision",
            "revision_id",
            "evidence_identity",
        ),
    )

    component_decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    original_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    component_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    interpretation: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_rule_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    current_employer_related: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown", server_default="unknown"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )



# Frozen archive/FK targets only. No new professional revision is permitted.
def _archive_only(_mapper, _connection, _target):
    raise ValueError("LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY")

event.listen(M04ClassificationSubject, "before_insert", _archive_only)
event.listen(M04ClassificationSubject, "before_update", _archive_only)
event.listen(M04ClassificationSubject, "before_delete", _archive_only)
event.listen(M04ClassificationRevision, "before_insert", _archive_only)
event.listen(M04ClassificationRevision, "before_update", _archive_only)
event.listen(M04ClassificationRevision, "before_delete", _archive_only)
event.listen(M04ComponentDecision, "before_insert", _archive_only)
event.listen(M04ComponentDecision, "before_update", _archive_only)
event.listen(M04ComponentDecision, "before_delete", _archive_only)
