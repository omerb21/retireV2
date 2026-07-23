from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


REVISION_STATUSES = ("draft", "finalized", "superseded", "abandoned")
COLLECTION_STATES = (
    "recorded",
    "confirmed_none",
    "unknown",
    "not_collected",
    "unresolved",
    "not_applicable",
)
VERIFICATION_STATES = (
    "unverified",
    "partly_verified",
    "verified",
    "planner_asserted",
    "source_conflict",
    "rejected",
    "superseded",
)


class M07EvidenceRevision(Base):
    __tablename__ = "m07_evidence_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_evidence_revisions_predecessor_client",
        ),
        ForeignKeyConstraint(
            ["superseded_by_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_evidence_revisions_successor_client",
        ),
        CheckConstraint(
            "status IN ('draft','finalized','superseded','abandoned')",
            name="ck_m07_evidence_revisions_status",
        ),
        CheckConstraint(
            "authority_classification = 'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_evidence_revisions_authority",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="ck_m07_evidence_revisions_number_positive",
        ),
        CheckConstraint(
            "status NOT IN ('finalized','superseded') OR "
            "(finalized_at IS NOT NULL AND finalized_by IS NOT NULL "
            "AND canonical_payload IS NOT NULL AND evidence_fingerprint IS NOT NULL "
            "AND source_snapshot_fingerprint IS NOT NULL)",
            name="ck_m07_evidence_revisions_finalization_evidence",
        ),
        CheckConstraint(
            "status != 'abandoned' OR "
            "(abandoned_at IS NOT NULL AND abandoned_by IS NOT NULL)",
            name="ck_m07_evidence_revisions_abandonment_evidence",
        ),
        CheckConstraint(
            "status != 'superseded' OR "
            "(superseded_at IS NOT NULL AND superseded_by IS NOT NULL "
            "AND superseded_by_revision_id IS NOT NULL)",
            name="ck_m07_evidence_revisions_supersession_evidence",
        ),
        UniqueConstraint(
            "client_id",
            "profile_id",
            "revision_number",
            name="uq_m07_evidence_revisions_client_profile_number",
        ),
        UniqueConstraint(
            "m07_evidence_revision_id",
            "client_id",
            name="uq_m07_evidence_revisions_id_client",
        ),
        Index(
            "ix_m07_evidence_revisions_client_profile",
            "client_id",
            "profile_id",
            "revision_number",
        ),
        Index(
            "ix_m07_evidence_revisions_client_tax_event_year",
            "client_id",
            "tax_year",
            "event_year",
        ),
        Index(
            "ix_m07_evidence_revisions_client_status",
            "client_id",
            "status",
        ),
        Index(
            "ix_m07_evidence_revisions_client_event_reference",
            "client_id",
            "event_type",
            "event_id",
        ),
    )

    m07_evidence_revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    superseded_by_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    event_year: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, active_history=True)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    technical_outcomes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    assessment_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canonical_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fingerprint_algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    parameter_set_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("official_parameter_sets.parameter_set_id"), nullable=True
    )
    parameter_set_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    parameter_resolution_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parameter_requested_tax_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    parameter_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class M07FactEvidence(Base):
    __tablename__ = "m07_fact_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_fact_evidence_revision_client",
        ),
        ForeignKeyConstraint(
            ["assertion_id", "m07_evidence_revision_id", "client_id"],
            [
                "m07_planner_assertions.assertion_id",
                "m07_planner_assertions.m07_evidence_revision_id",
                "m07_planner_assertions.client_id",
            ],
            name="fk_m07_fact_evidence_assertion_scope",
        ),
        CheckConstraint(
            "collection_state IN "
            "('recorded','confirmed_none','unknown','not_collected','unresolved','not_applicable')",
            name="ck_m07_fact_evidence_collection_state",
        ),
        CheckConstraint(
            "verification_state IN "
            "('unverified','partly_verified','verified','planner_asserted',"
            "'source_conflict','rejected','superseded')",
            name="ck_m07_fact_evidence_verification_state",
        ),
        CheckConstraint(
            "authority_classification = 'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_fact_evidence_authority",
        ),
        CheckConstraint(
            "collection_state != 'recorded' OR structured_value IS NOT NULL",
            name="ck_m07_fact_evidence_recorded_value",
        ),
        CheckConstraint(
            "collection_state NOT IN ('confirmed_none','not_applicable') OR "
            "collection_basis IS NOT NULL",
            name="ck_m07_fact_evidence_collection_basis",
        ),
        CheckConstraint(
            "verification_state NOT IN ('verified','partly_verified') OR "
            "(verified_at IS NOT NULL AND verified_by IS NOT NULL "
            "AND verification_basis IS NOT NULL)",
            name="ck_m07_fact_evidence_verification_evidence",
        ),
        CheckConstraint(
            "verification_state != 'planner_asserted' OR assertion_id IS NOT NULL",
            name="ck_m07_fact_evidence_assertion_link",
        ),
        UniqueConstraint(
            "client_id",
            "m07_evidence_revision_id",
            "fact_identity_key",
            name="uq_m07_fact_evidence_identity_key",
        ),
        Index(
            "ix_m07_fact_evidence_revision_field",
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
        ),
        Index(
            "uq_m07_fact_evidence_persisted_source_identity",
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "source_record_type",
            "source_record_id",
            unique=True,
        ),
        Index(
            "uq_m07_fact_evidence_document_identity",
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "source_document_reference",
            unique=True,
        ),
        Index(
            "uq_m07_fact_evidence_assertion_identity",
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
            "assertion_id",
            unique=True,
        ),
    )

    fact_evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    m07_evidence_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    field_code: Mapped[str] = mapped_column(String(128), nullable=False)
    fact_identity_key: Mapped[str] = mapped_column(String(64), nullable=False)
    structured_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    collection_state: Mapped[str] = mapped_column(String(32), nullable=False)
    collection_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_state: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_record_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_document_reference: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class M07PlannerAssertion(Base):
    __tablename__ = "m07_planner_assertions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_planner_assertions_revision_client",
        ),
        ForeignKeyConstraint(
            [
                "predecessor_assertion_id",
                "m07_evidence_revision_id",
                "client_id",
            ],
            [
                "m07_planner_assertions.assertion_id",
                "m07_planner_assertions.m07_evidence_revision_id",
                "m07_planner_assertions.client_id",
            ],
            name="fk_m07_planner_assertions_predecessor_scope",
        ),
        CheckConstraint(
            "authority_classification = "
            "'ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_planner_assertions_authority",
        ),
        UniqueConstraint(
            "assertion_id",
            "m07_evidence_revision_id",
            "client_id",
            name="uq_m07_planner_assertions_scope",
        ),
        Index(
            "ix_m07_planner_assertions_revision_field",
            "client_id",
            "m07_evidence_revision_id",
            "field_code",
        ),
    )

    assertion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    m07_evidence_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    field_code: Mapped[str] = mapped_column(String(128), nullable=False)
    asserted_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    assertion_basis: Mapped[str] = mapped_column(Text, nullable=False)
    assertion_reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_note: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    asserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    asserted_by: Mapped[str] = mapped_column(String(128), nullable=False)
    predecessor_assertion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class M07AssessmentFinding(Base):
    __tablename__ = "m07_assessment_findings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["m07_evidence_revision_id", "client_id"],
            [
                "m07_evidence_revisions.m07_evidence_revision_id",
                "m07_evidence_revisions.client_id",
            ],
            name="fk_m07_assessment_findings_revision_client",
        ),
        CheckConstraint(
            "finding_kind IN "
            "('missing_required_field','not_collected','unknown','unresolved',"
            "'source_conflict','rejected_evidence','confirmed_none','not_applicable',"
            "'incompatible_evidence','technical_warning','technical_rule_outcome')",
            name="ck_m07_assessment_findings_kind",
        ),
        CheckConstraint(
            "authority_classification = "
            "'TECHNICAL_ASSESSMENT_ONLY_NOT_PROFESSIONAL_AUTHORITY'",
            name="ck_m07_assessment_findings_authority",
        ),
        Index(
            "ix_m07_assessment_findings_revision_code",
            "client_id",
            "m07_evidence_revision_id",
            "finding_code",
        ),
    )

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    m07_evidence_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    finding_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_code: Mapped[str] = mapped_column(String(128), nullable=False)
    authority_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    field_references: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fact_references: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    assertion_references: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_references: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    technical_blocking_effect: Mapped[bool] = mapped_column(nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class M07EvidenceImmutableError(ValueError):
    pass


def _parent_status(connection, revision_id: str, client_id: int) -> str | None:
    return connection.execute(
        select(M07EvidenceRevision.status).where(
            M07EvidenceRevision.m07_evidence_revision_id == revision_id,
            M07EvidenceRevision.client_id == client_id,
        )
    ).scalar_one_or_none()


@event.listens_for(M07EvidenceRevision, "before_update")
def _protect_revision_update(_mapper, _connection, target: M07EvidenceRevision) -> None:
    state = inspect(target)
    history = state.attrs.status.history
    persisted_status = history.deleted[0] if history.deleted else target.status
    if history.has_changes():
        raise M07EvidenceImmutableError(
            "revision lifecycle changes require the purpose-specific service"
        )
    if persisted_status != "draft" and any(
        state.attrs[column.key].history.has_changes()
        for column in state.mapper.column_attrs
    ):
        raise M07EvidenceImmutableError(f"{persisted_status} revision is immutable")


@event.listens_for(M07EvidenceRevision, "before_delete")
def _protect_revision_delete(_mapper, _connection, _target: M07EvidenceRevision) -> None:
    raise M07EvidenceImmutableError("M07 evidence revisions cannot be deleted")


def _protect_child_mutation(_mapper, connection, target) -> None:
    if _parent_status(
        connection, target.m07_evidence_revision_id, target.client_id
    ) != "draft":
        raise M07EvidenceImmutableError("children of a closed revision are immutable")


for _child_type in (M07FactEvidence, M07PlannerAssertion, M07AssessmentFinding):
    event.listen(_child_type, "before_insert", _protect_child_mutation)
    event.listen(_child_type, "before_update", _protect_child_mutation)
    event.listen(_child_type, "before_delete", _protect_child_mutation)


@event.listens_for(M07PlannerAssertion, "before_update")
@event.listens_for(M07PlannerAssertion, "before_delete")
def _protect_assertion_append_only(_mapper, _connection, _target) -> None:
    raise M07EvidenceImmutableError("planner assertions are append-only")
