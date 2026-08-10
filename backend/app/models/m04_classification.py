from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

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


M04_TARGET_KINDS = ("source_evidence_review", "manual_record_review")
M04_STATES = ("under_review", "proposed", "accepted", "unresolved", "rejected")
M04_ACTIONS = (
    "start",
    "proposal",
    "unresolved",
    "accept",
    "reject",
    "reopen",
    "override",
    "undo",
    "start_revalidation",
)
M04_PRODUCT_FAMILIES = (
    "insurance_policy",
    "savings_policy",
    "provident_fund",
    "investment_provident_fund",
    "education_fund",
    "pension_fund",
    "unknown_or_unresolved",
)
M04_COMPONENT_KINDS = (
    "severance_component",
    "contribution_component",
    "unknown_component",
)
M04_INTERPRETATIONS = ("pension", "capital", "mixed", "unresolved")
M04_COMPONENT_INTERPRETATIONS = ("pension", "capital", "unresolved")
M04_EMPLOYER_RELATED = ("yes", "no", "unknown")
M04_CATALOGUE_VERSION = "m04-rules-v1"
M04_WORKFLOW_ACTOR = (
    "system:m04-classification-ui:M04 classification workflow"
)


def new_m04_subject_id() -> str:
    return f"M04-S-{uuid4().hex}"


def new_m04_revision_id() -> str:
    return f"M04-R-{uuid4().hex}"


def new_m04_component_id() -> str:
    return f"M04-C-{uuid4().hex}"


def m04_server_timestamp() -> datetime:
    return datetime.now(timezone.utc)


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


def authorize_m04_insert(target: object) -> None:
    setattr(target, "_m04_server_insert_authorized", True)


def _require_server_insert(target: object) -> None:
    if not getattr(target, "_m04_server_insert_authorized", False):
        raise ValueError("M04 records may be inserted only by the M04 service")


def _prevent_update(_mapper, _connection, target) -> None:
    if inspect(target).persistent:
        raise ValueError("M04 append-only records are immutable")


def _prevent_delete(_mapper, _connection, _target) -> None:
    raise ValueError("M04 append-only records cannot be deleted")


_M04_IMMUTABLE_TABLE_NAMES = {
    "m04_classification_subjects",
    "m04_classification_revisions",
    "m04_component_decisions",
}


def _statement_table_name(statement: object) -> str | None:
    table = getattr(statement, "table", None)
    while table is not None:
        name = getattr(table, "name", None)
        if name in _M04_IMMUTABLE_TABLE_NAMES:
            return name
        table = getattr(table, "original", None)
    return None


@event.listens_for(Session, "do_orm_execute")
def _prevent_m04_bulk_mutation(orm_execute_state) -> None:
    statement = orm_execute_state.statement
    if isinstance(statement, (Update, Delete)) and _statement_table_name(statement):
        raise ValueError("M04 append-only records cannot be bulk updated or deleted")


def _validate_subject_insert(_mapper, _connection, target: M04ClassificationSubject) -> None:
    _require_server_insert(target)
    target.subject_id = new_m04_subject_id()
    target.archive_generation = 0


def _validate_revision_insert(
    _mapper, connection, target: M04ClassificationRevision
) -> None:
    _require_server_insert(target)
    target.revision_id = new_m04_revision_id()
    target.actor = M04_WORKFLOW_ACTOR
    target.created_at = m04_server_timestamp()
    if target.catalogue_version != M04_CATALOGUE_VERSION:
        raise ValueError("M04 catalogue version must be server-controlled")
    if not isinstance(target.input_snapshot, dict):
        raise ValueError("M04 input snapshot must be server-owned structured evidence")
    if not isinstance(target.matched_rule_evidence, list):
        raise ValueError("M04 matched-rule evidence must be server-owned structured evidence")
    if not isinstance(target.action_evidence, dict):
        raise ValueError("M04 action evidence must be server-owned structured evidence")
    if (
        not isinstance(target.evidence_digest, str)
        or len(target.evidence_digest) != 64
        or any(character not in "0123456789abcdef" for character in target.evidence_digest)
    ):
        raise ValueError("M04 evidence digest must be server-controlled")

    subject = connection.execute(
        select(
            M04ClassificationSubject.client_id,
            M04ClassificationSubject.intake_id,
            M04ClassificationSubject.target_kind,
        ).where(M04ClassificationSubject.subject_id == target.subject_id)
    ).one_or_none()
    if (
        subject is None
        or subject.client_id != target.client_id
        or subject.intake_id != target.intake_id
        or subject.target_kind != target.target_kind
    ):
        raise ValueError("M04 revision subject must belong to the same target")

    if target.revision_sequence == 1:
        if (
            target.predecessor_revision_id is not None
            or target.action_type != "start"
            or target.state != "under_review"
        ):
            raise ValueError("M04 root revision is inconsistent")
        return

    predecessor = connection.execute(
        select(
            M04ClassificationRevision.client_id,
            M04ClassificationRevision.intake_id,
            M04ClassificationRevision.target_kind,
            M04ClassificationRevision.revision_sequence,
        ).where(
            M04ClassificationRevision.revision_id
            == target.predecessor_revision_id
        )
    ).one_or_none()
    if (
        predecessor is None
        or predecessor.client_id != target.client_id
        or predecessor.intake_id != target.intake_id
        or predecessor.target_kind != target.target_kind
        or predecessor.revision_sequence + 1 != target.revision_sequence
    ):
        raise ValueError("M04 predecessor must belong to the same target chain")


def _validate_component_insert(
    _mapper, connection, target: M04ComponentDecision
) -> None:
    _require_server_insert(target)
    target.component_decision_id = new_m04_component_id()
    target.created_at = m04_server_timestamp()
    revision = connection.execute(
        select(
            M04ClassificationRevision.client_id,
            M04ClassificationRevision.intake_id,
            M04ClassificationRevision.target_kind,
        ).where(M04ClassificationRevision.revision_id == target.revision_id)
    ).one_or_none()
    if (
        revision is None
        or revision.client_id != target.client_id
        or revision.intake_id != target.intake_id
        or revision.target_kind != target.target_kind
    ):
        raise ValueError("M04 component must belong to the same revision target")


@event.listens_for(Client, "before_update")
def _mark_subjects_after_case_archive(_mapper, connection, target: Client) -> None:
    state = inspect(target)
    status_history = state.attrs.status.history
    if (
        status_history.has_changes()
        and target.status == "archived"
        and "archived" not in status_history.deleted
    ):
        connection.execute(
            update(M04ClassificationSubject)
            .where(M04ClassificationSubject.client_id == target.client_id)
            .values(
                archive_generation=M04ClassificationSubject.archive_generation + 1
            )
        )


event.listen(M04ClassificationSubject, "before_insert", _validate_subject_insert)
event.listen(M04ClassificationSubject, "before_update", _prevent_update)
event.listen(M04ClassificationSubject, "before_delete", _prevent_delete)
event.listen(M04ClassificationRevision, "before_insert", _validate_revision_insert)
event.listen(M04ClassificationRevision, "before_update", _prevent_update)
event.listen(M04ClassificationRevision, "before_delete", _prevent_delete)
event.listen(M04ComponentDecision, "before_insert", _validate_component_insert)
event.listen(M04ComponentDecision, "before_update", _prevent_update)
event.listen(M04ComponentDecision, "before_delete", _prevent_delete)
