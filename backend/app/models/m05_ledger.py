from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql.dml import Delete, Update
from sqlalchemy.sql.elements import TextClause

from app.db.base import Base


M05_WORKFLOW_ACTOR = "system:m05-ledger-ui:M05 ledger workflow"
M05_TARGET_KIND = "manual_record_review"
M05_CURRENCY = "ILS"
M05_ALGORITHM_VERSION = "m05-reconciliation-v1"
M05_STATES = ("draft", "reconciled", "warning_reviewed", "blocked", "superseded")
M05_ACTIONS = (
    "start",
    "reconcile",
    "review_warning",
    "mark_blocked",
    "adjust",
    "supersede",
    "revalidate",
)
M05_COMPONENT_KINDS = (
    "total_balance",
    "contribution_component",
    "severance_component",
    "unknown_component",
)
M05_MONETARY_STATES = (
    "recorded_value",
    "recorded_zero",
    "missing",
    "excluded",
    "malformed",
)


def _new(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def m05_server_timestamp() -> datetime:
    return datetime.now(timezone.utc)


class M05LedgerSubject(Base):
    __tablename__ = "m05_ledger_subjects"
    __table_args__ = (
        CheckConstraint("length(provider_name) > 0", name="ck_m05_subject_provider"),
        CheckConstraint("length(account_reference) > 0", name="ck_m05_subject_account"),
        CheckConstraint(
            "length(provider_identity_digest) = 64 AND "
            "provider_identity_digest = lower(provider_identity_digest)",
            name="ck_m05_subject_provider_digest",
        ),
        CheckConstraint(
            "length(account_identity_digest) = 64 AND "
            "account_identity_digest = lower(account_identity_digest)",
            name="ck_m05_subject_account_digest",
        ),
        UniqueConstraint(
            "client_id",
            "provider_identity_digest",
            "account_identity_digest",
            name="uq_m05_subject_exact_account",
        ),
        UniqueConstraint(
            "subject_id", "client_id", name="uq_m05_subject_identity_client"
        ),
        Index("ix_m05_subject_client", "client_id", "created_at"),
    )

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_identity_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    account_identity_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M05CandidateLink(Base):
    __tablename__ = "m05_candidate_links"
    __table_args__ = (
        CheckConstraint(
            "target_kind = 'manual_record_review'",
            name="ck_m05_candidate_target_kind",
        ),
        CheckConstraint(
            "length(source_snapshot_digest) = 64 AND "
            "source_snapshot_digest = lower(source_snapshot_digest)",
            name="ck_m05_candidate_source_digest",
        ),
        ForeignKeyConstraint(
            ["subject_id", "client_id"],
            ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"],
            name="fk_m05_candidate_subject_client",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            name="fk_m05_candidate_intake_client",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["m03_revision_id", "client_id"],
            ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"],
            name="fk_m05_candidate_m03_client",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["m04_revision_id", "client_id", "intake_id", "target_kind"],
            [
                "m04_classification_revisions.revision_id",
                "m04_classification_revisions.client_id",
                "m04_classification_revisions.intake_id",
                "m04_classification_revisions.target_kind",
            ],
            name="fk_m05_candidate_m04_target",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "client_id",
            "intake_id",
            "target_kind",
            "m03_revision_id",
            "m04_revision_id",
            name="uq_m05_candidate_tuple",
        ),
        UniqueConstraint(
            "candidate_id",
            "client_id",
            "subject_id",
            name="uq_m05_candidate_identity_subject",
        ),
        Index(
            "ix_m05_candidate_subject_precedence",
            "subject_id",
            "statement_date",
            "m03_decided_at",
        ),
    )

    candidate_id: Mapped[str] = mapped_column(String(72), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    m03_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    m04_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    m03_decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_snapshot_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M05LedgerRevision(Base):
    __tablename__ = "m05_ledger_revisions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('draft','reconciled','warning_reviewed','blocked','superseded')",
            name="ck_m05_revision_state",
        ),
        CheckConstraint(
            "action_type IN ('start','reconcile','review_warning','mark_blocked',"
            "'adjust','supersede','revalidate')",
            name="ck_m05_revision_action",
        ),
        CheckConstraint(
            "target_kind = 'manual_record_review'",
            name="ck_m05_revision_target_kind",
        ),
        CheckConstraint("currency = 'ILS'", name="ck_m05_revision_currency"),
        CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL "
            "AND action_type = 'start' AND state = 'draft') OR "
            "(revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m05_revision_shape",
        ),
        CheckConstraint(
            "absolute_discrepancy IS NULL OR absolute_discrepancy >= 0",
            name="ck_m05_revision_absolute_discrepancy",
        ),
        CheckConstraint(
            "length(evidence_digest) = 64 AND evidence_digest = lower(evidence_digest)",
            name="ck_m05_revision_evidence_digest",
        ),
        ForeignKeyConstraint(
            ["subject_id", "client_id"],
            ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"],
            name="fk_m05_revision_subject_client",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["candidate_id", "client_id", "subject_id"],
            [
                "m05_candidate_links.candidate_id",
                "m05_candidate_links.client_id",
                "m05_candidate_links.subject_id",
            ],
            name="fk_m05_revision_candidate_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id", "subject_id"],
            [
                "m05_ledger_revisions.revision_id",
                "m05_ledger_revisions.client_id",
                "m05_ledger_revisions.subject_id",
            ],
            name="fk_m05_revision_predecessor_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id", "revision_sequence", name="uq_m05_revision_subject_sequence"
        ),
        UniqueConstraint(
            "predecessor_revision_id", name="uq_m05_revision_predecessor_child"
        ),
        UniqueConstraint(
            "revision_id",
            "client_id",
            "subject_id",
            name="uq_m05_revision_identity_subject",
        ),
        Index(
            "ix_m05_revision_client_subject",
            "client_id",
            "subject_id",
            "revision_sequence",
        ),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(72), nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    m03_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    m04_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    predecessor_revision_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    revision_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    product_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_snapshot_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    currency_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    currency_confirmation_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )
    source_total_state: Mapped[str] = mapped_column(String(32), nullable=False)
    source_total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    effective_total_state: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    signed_discrepancy: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    absolute_discrepancy: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    tolerance_satisfied: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    included_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    excluded_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    warning_dispositions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M05LedgerValue(Base):
    __tablename__ = "m05_ledger_values"
    __table_args__ = (
        CheckConstraint(
            "component_kind IN ('total_balance','contribution_component',"
            "'severance_component','unknown_component')",
            name="ck_m05_value_component_kind",
        ),
        CheckConstraint(
            "source_state IN ('recorded_value','recorded_zero','missing','excluded','malformed')",
            name="ck_m05_value_source_state",
        ),
        CheckConstraint(
            "effective_state IN ('recorded_value','recorded_zero','missing','excluded','malformed')",
            name="ck_m05_value_effective_state",
        ),
        CheckConstraint(
            "(source_state IN ('recorded_value','recorded_zero') AND source_value IS NOT NULL) "
            "OR (source_state NOT IN ('recorded_value','recorded_zero') AND source_value IS NULL)",
            name="ck_m05_value_source_shape",
        ),
        CheckConstraint(
            "(effective_state IN ('recorded_value','recorded_zero') AND effective_value IS NOT NULL) "
            "OR (effective_state NOT IN ('recorded_value','recorded_zero') AND effective_value IS NULL)",
            name="ck_m05_value_effective_shape",
        ),
        ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m05_ledger_revisions.revision_id",
                "m05_ledger_revisions.client_id",
                "m05_ledger_revisions.subject_id",
            ],
            name="fk_m05_value_revision_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "revision_id", "evidence_identity", name="uq_m05_value_revision_identity"
        ),
        UniqueConstraint(
            "value_id", "client_id", "subject_id", name="uq_m05_value_identity_subject"
        ),
        Index("ix_m05_value_revision", "revision_id", "component_index"),
    )

    value_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    component_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    component_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_state: Mapped[str] = mapped_column(String(32), nullable=False)
    source_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    effective_state: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    included_in_reconciliation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class M05AdjustmentEvidence(Base):
    __tablename__ = "m05_adjustment_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m05_ledger_revisions.revision_id",
                "m05_ledger_revisions.client_id",
                "m05_ledger_revisions.subject_id",
            ],
            name="fk_m05_adjustment_revision_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("revision_id", name="uq_m05_adjustment_revision"),
        Index("ix_m05_adjustment_subject", "subject_id", "created_at"),
    )

    adjustment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_effective_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    new_effective_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


_M05_CLASSES = (
    M05LedgerSubject,
    M05CandidateLink,
    M05LedgerRevision,
    M05LedgerValue,
    M05AdjustmentEvidence,
)
_M05_TABLE_NAMES = {item.__tablename__ for item in _M05_CLASSES}
_TEXT_MUTATION_ERROR = "M05 append-only records cannot be updated or deleted"


def authorize_m05_insert(target: object) -> None:
    setattr(target, "_m05_server_insert_authorized", True)


def _before_insert(_mapper, _connection, target: object) -> None:
    if not getattr(target, "_m05_server_insert_authorized", False):
        raise ValueError("M05 records may be inserted only by the M05 service")
    if isinstance(target, M05LedgerSubject):
        target.subject_id = _new("M05-S")
    elif isinstance(target, M05CandidateLink):
        if not target.candidate_id:
            target.candidate_id = _new("M05-C")
    elif isinstance(target, M05LedgerRevision):
        if not target.revision_id:
            target.revision_id = _new("M05-R")
        if target.actor != M05_WORKFLOW_ACTOR:
            raise ValueError("M05 actor must be server-controlled")
        if target.created_at is None:
            target.created_at = m05_server_timestamp()
        if (
            not isinstance(target.evidence_digest, str)
            or len(target.evidence_digest) != 64
            or any(character not in "0123456789abcdef" for character in target.evidence_digest)
        ):
            raise ValueError("M05 revision evidence digest must be server-controlled")
    elif isinstance(target, M05LedgerValue):
        target.value_id = _new("M05-V")
    elif isinstance(target, M05AdjustmentEvidence):
        if not target.adjustment_id:
            target.adjustment_id = _new("M05-A")
        target.actor = M05_WORKFLOW_ACTOR
        if target.created_at is None:
            target.created_at = m05_server_timestamp()


def _prevent_update(_mapper, _connection, target: object) -> None:
    if inspect(target).persistent:
        raise ValueError("M05 append-only records are immutable")


def _prevent_delete(_mapper, _connection, _target: object) -> None:
    raise ValueError("M05 append-only records cannot be deleted")


def _statement_table_name(statement: object) -> str | None:
    table = getattr(statement, "table", None)
    while table is not None:
        name = getattr(table, "name", None)
        if name in _M05_TABLE_NAMES:
            return name
        table = getattr(table, "original", None)
    return None


def _sql_tokens(sql: str) -> list[str]:
    """Tokenize executable SQL while discarding comments and string literals.

    This is intentionally a small lexical guard, not a SQL parser. It recognizes
    identifiers, quoted identifiers, and punctuation needed to locate UPDATE and
    DELETE targets, including mutations following a CTE.
    """
    tokens: list[str] = []
    index = 0
    length = len(sql)
    while index < length:
        char = sql[index]
        if char.isspace():
            index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if char == "'":
            index += 1
            while index < length:
                if sql[index] == "'":
                    if index + 1 < length and sql[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            tokens.append("<string>")
            continue
        if char in {'"', "`", "["}:
            closing = "]" if char == "[" else char
            index += 1
            value: list[str] = []
            while index < length:
                if sql[index] == closing:
                    if closing != "]" and index + 1 < length and sql[index + 1] == closing:
                        value.append(closing)
                        index += 2
                        continue
                    index += 1
                    break
                value.append(sql[index])
                index += 1
            tokens.append("".join(value).lower())
            continue
        if char.isalpha() or char == "_":
            end = index + 1
            while end < length and (sql[end].isalnum() or sql[end] in {"_", "$"}):
                end += 1
            tokens.append(sql[index:end].lower())
            index = end
            continue
        if char in {".", ",", "(", ")", ";"}:
            tokens.append(char)
        index += 1
    return tokens


def _qualified_identifier(tokens: list[str], index: int) -> tuple[str | None, int]:
    if index >= len(tokens) or tokens[index] in {".", ",", "(", ")", ";", "<string>"}:
        return None, index
    parts = [tokens[index]]
    index += 1
    while index + 1 < len(tokens) and tokens[index] == ".":
        part = tokens[index + 1]
        if part in {".", ",", "(", ")", ";", "<string>"}:
            break
        parts.append(part)
        index += 2
    return parts[-1], index


def _text_mutates_m05(statement: TextClause) -> bool:
    tokens = _sql_tokens(statement.text)
    for index, token in enumerate(tokens):
        target_index: int | None = None
        if token == "update":
            target_index = index + 1
        elif token == "delete" and index + 1 < len(tokens) and tokens[index + 1] == "from":
            target_index = index + 2
        if target_index is None:
            continue
        target, _ = _qualified_identifier(tokens, target_index)
        if target in _M05_TABLE_NAMES:
            return True
    return False


@event.listens_for(Session, "do_orm_execute")
def _prevent_m05_bulk_mutation(orm_execute_state) -> None:
    statement = orm_execute_state.statement
    if isinstance(statement, (Update, Delete)) and _statement_table_name(statement):
        raise ValueError(_TEXT_MUTATION_ERROR)
    if isinstance(statement, TextClause) and _text_mutates_m05(statement):
        raise ValueError(_TEXT_MUTATION_ERROR)


for _model in _M05_CLASSES:
    event.listen(_model, "before_insert", _before_insert)
    event.listen(_model, "before_update", _prevent_update)
    event.listen(_model, "before_delete", _prevent_delete)
