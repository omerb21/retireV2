from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql.dml import Delete, Update
from sqlalchemy.sql.elements import TextClause

from app.db.base import Base


M06_WORKFLOW_ACTOR = "system:m06-conversion-ui:M06 conversion workflow"


def m06_server_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def _new(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


class M06ConversionSubject(Base):
    __tablename__ = "m06_conversion_subjects"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('balance_to_monthly_pension','monthly_pension_to_capital_equivalent')",
            name="ck_m06_subject_mode",
        ),
        CheckConstraint(
            "length(semantic_digest) = 64 AND length(provider_identity_digest) = 64 AND length(account_identity_digest) = 64 AND length(product_context_digest) = 64",
            name="ck_m06_subject_digests",
        ),
        ForeignKeyConstraint(
            ["m05_subject_id", "client_id"],
            ["m05_ledger_subjects.subject_id", "m05_ledger_subjects.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("semantic_digest", name="uq_m06_subject_semantic_digest"),
        UniqueConstraint(
            "subject_id", "client_id", name="uq_m06_subject_identity_client"
        ),
        Index("ix_m06_subject_client", "client_id", "created_at"),
    )
    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False
    )
    m05_subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    input_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_identity_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    account_identity_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    product_context_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class M06ConversionRevision(Base):
    __tablename__ = "m06_conversion_revisions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('draft','resolved','warning_reviewed','blocked','superseded')",
            name="ck_m06_revision_state",
        ),
        CheckConstraint(
            "action_type IN ('start','resolve','review_warnings','correct_coefficient','supersede')",
            name="ck_m06_revision_action",
        ),
        CheckConstraint(
            "(revision_sequence = 1 AND predecessor_revision_id IS NULL AND action_type = 'start') OR (revision_sequence > 1 AND predecessor_revision_id IS NOT NULL)",
            name="ck_m06_revision_shape",
        ),
        CheckConstraint("length(evidence_digest) = 64", name="ck_m06_revision_digest"),
        ForeignKeyConstraint(
            ["subject_id", "client_id"],
            ["m06_conversion_subjects.subject_id", "m06_conversion_subjects.client_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["predecessor_revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["m02_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["m03_revision_id", "client_id"],
            ["m03_review_revisions.revision_id", "m03_review_revisions.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id", "revision_sequence", name="uq_m06_revision_subject_sequence"
        ),
        UniqueConstraint(
            "predecessor_revision_id", name="uq_m06_revision_predecessor_child"
        ),
        UniqueConstraint(
            "revision_id",
            "client_id",
            "subject_id",
            name="uq_m06_revision_identity_subject",
        ),
        Index(
            "ix_m06_revision_subject", "client_id", "subject_id", "revision_sequence"
        ),
    )
    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_revision_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    revision_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_id: Mapped[str] = mapped_column(String(96), nullable=False)
    input_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    input_amount: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    m02_intake_id: Mapped[str] = mapped_column(String(64), nullable=False)
    m03_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    m04_revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("m04_classification_revisions.revision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    m05_revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("m05_ledger_revisions.revision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    predecessor_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    blocking_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    informational_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class M06CoefficientEvidence(Base):
    __tablename__ = "m06_coefficient_evidence"
    __table_args__ = (
        CheckConstraint(
            "authority_class IN ('documentary','planner_declared')",
            name="ck_m06_coefficient_authority",
        ),
        CheckConstraint(
            "length(coefficient_text) > 0 AND length(evidence_digest) = 64",
            name="ck_m06_coefficient_digest",
        ),
        CheckConstraint(
            "(authority_class = 'documentary' AND source_intake_id IS NOT NULL AND (source_locator IS NOT NULL OR source_note IS NOT NULL)) OR (authority_class = 'planner_declared' AND source_note IS NOT NULL AND applicability_declared = true)",
            name="ck_m06_coefficient_shape",
        ),
        ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_intake_id", "client_id"],
            ["m02_intake_records.intake_id", "m02_intake_records.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("revision_id", name="uq_m06_coefficient_revision"),
    )
    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_class: Mapped[str] = mapped_column(String(32), nullable=False)
    coefficient_text: Mapped[str] = mapped_column(Text, nullable=False)
    decimal_precision: Mapped[int] = mapped_column(Integer, nullable=False)
    decimal_exponent: Mapped[int] = mapped_column(Integer, nullable=False)
    source_intake_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    provider_context: Mapped[str] = mapped_column(Text, nullable=False)
    product_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_semantics: Mapped[str] = mapped_column(String(128), nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicability_declared: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class M06CalculationManifest(Base):
    __tablename__ = "m06_calculation_manifests"
    __table_args__ = (
        CheckConstraint("length(fingerprint) = 64", name="ck_m06_manifest_fingerprint"),
        CheckConstraint(
            "(raw_result_kind IS NULL AND raw_decimal IS NULL AND raw_numerator IS NULL AND raw_denominator IS NULL AND display_result IS NULL) OR (raw_result_kind = 'exact_ratio' AND raw_decimal IS NULL AND raw_numerator IS NOT NULL AND raw_denominator IS NOT NULL AND display_result IS NOT NULL) OR (raw_result_kind = 'exact_decimal' AND raw_decimal IS NOT NULL AND raw_numerator IS NULL AND raw_denominator IS NULL AND display_result IS NOT NULL)",
            name="ck_m06_manifest_result_shape",
        ),
        ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("revision_id", name="uq_m06_manifest_revision"),
    )
    manifest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_result_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_decimal: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_numerator: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_denominator: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_result: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class M06WarningDisposition(Base):
    __tablename__ = "m06_warning_dispositions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "client_id", "subject_id"],
            [
                "m06_conversion_revisions.revision_id",
                "m06_conversion_revisions.client_id",
                "m06_conversion_revisions.subject_id",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("revision_id", "warning_id", name="uq_m06_warning_revision"),
    )
    disposition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


_CLASSES = (
    M06ConversionSubject,
    M06ConversionRevision,
    M06CoefficientEvidence,
    M06CalculationManifest,
    M06WarningDisposition,
)
_TABLE_NAMES = {model.__tablename__ for model in _CLASSES}


def authorize_m06_insert(target: object) -> None:
    setattr(target, "_m06_server_insert_authorized", True)


def _before_insert(_mapper, _connection, target: object) -> None:
    if not getattr(target, "_m06_server_insert_authorized", False):
        raise ValueError("M06 records may be inserted only by the M06 service")
    now = m06_server_timestamp()
    if isinstance(target, M06ConversionSubject):
        target.subject_id, target.created_at = _new("M06-S"), now
    elif isinstance(target, M06ConversionRevision):
        target.revision_id, target.actor, target.created_at = (
            _new("M06-R"),
            M06_WORKFLOW_ACTOR,
            now,
        )
    elif isinstance(target, M06CoefficientEvidence):
        target.evidence_id, target.actor, target.created_at = (
            _new("M06-C"),
            M06_WORKFLOW_ACTOR,
            now,
        )
    elif isinstance(target, M06CalculationManifest):
        target.manifest_id, target.created_at = _new("M06-M"), now
    elif isinstance(target, M06WarningDisposition):
        target.disposition_id, target.actor, target.created_at = (
            _new("M06-W"),
            M06_WORKFLOW_ACTOR,
            now,
        )


def _prevent_update(_mapper, _connection, target: object) -> None:
    if inspect(target).persistent:
        raise ValueError("M06 append-only records are immutable")


def _prevent_delete(_mapper, _connection, _target: object) -> None:
    raise ValueError("M06 append-only records cannot be deleted")


for _model in _CLASSES:
    event.listen(_model, "before_insert", _before_insert)
    event.listen(_model, "before_update", _prevent_update)
    event.listen(_model, "before_delete", _prevent_delete)


def _sql_mutates_m06(sql: str) -> bool:
    # Reuse the repository's comment/string-aware lexical guard and inspect only
    # executable UPDATE/DELETE targets. This covers ORM, Connection, and driver SQL.
    from app.models.m05_ledger import _qualified_identifier, _sql_tokens

    tokens = _sql_tokens(sql)
    for index, token in enumerate(tokens):
        target_index: int | None = None
        if token.kind == "keyword" and token.value == "update":
            target_index = index + 1
            if target_index + 1 < len(tokens) and tokens[target_index].value == "or":
                target_index += 2
            if target_index < len(tokens) and tokens[target_index].value == "only":
                target_index += 1
        elif (
            token.kind == "keyword"
            and token.value == "delete"
            and index + 1 < len(tokens)
            and tokens[index + 1].value == "from"
        ):
            target_index = index + 2
            if target_index < len(tokens) and tokens[target_index].value == "only":
                target_index += 1
        if target_index is not None:
            target, _ = _qualified_identifier(tokens, target_index)
            if target in _TABLE_NAMES:
                return True
    return False


@event.listens_for(Session, "do_orm_execute")
def _prevent_m06_bulk_mutation(orm_execute_state) -> None:
    statement = orm_execute_state.statement
    table = getattr(statement, "table", None)
    if (
        isinstance(statement, (Update, Delete))
        and getattr(table, "name", None) in _TABLE_NAMES
    ):
        raise ValueError("M06 append-only records cannot be updated or deleted")
    if isinstance(statement, TextClause) and _sql_mutates_m06(statement.text):
        raise ValueError("M06 append-only records cannot be updated or deleted")


@event.listens_for(Engine, "before_cursor_execute")
def _prevent_m06_connection_mutation(
    _connection, _cursor, statement: str, _parameters, _context, _many: bool
) -> None:
    if _sql_mutates_m06(statement):
        raise ValueError("M06 append-only records cannot be updated or deleted")
