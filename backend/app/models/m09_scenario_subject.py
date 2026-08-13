from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, Numeric, String, UniqueConstraint, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.m09_cashflow import M09_WORKFLOW_ACTOR, authorize_m09_insert, m09_server_timestamp, new_m09_id


SUBJECT_FAMILY = "declared_retirement_cashflow_adjustments"
SUBJECT_VERSION = "v1"


class M09ScenarioSubject(Base):
    __tablename__ = "m09_scenario_subjects"
    __table_args__ = (
        CheckConstraint("scenario_family = 'declared_retirement_cashflow_adjustments'", name="ck_m09_subject_family"),
        CheckConstraint("scenario_contract_version = 'v1'", name="ck_m09_subject_version"),
        CheckConstraint("subject_type IN ('baseline','adjusted')", name="ck_m09_subject_type"),
        CheckConstraint("length(calculation_semantic_fingerprint) = 64 AND length(integrity_fingerprint) = 64 AND length(adjustment_manifest_fingerprint) = 64", name="ck_m09_subject_fingerprints"),
        UniqueConstraint("scenario_subject_id", "client_id", name="uq_m09_subject_identity_client"),
        UniqueConstraint("client_id", "scenario_family", "scenario_contract_version", "calculation_semantic_fingerprint", name="uq_m09_subject_semantics"),
        Index("ix_m09_subject_client", "client_id", "created_at"),
        Index("uq_m09_subject_baseline", "client_id", "scenario_family", "scenario_contract_version", unique=True, sqlite_where=text("subject_type = 'baseline'"), postgresql_where=text("subject_type = 'baseline'")),
    )
    scenario_subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    adjustment_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    adjustment_manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_semantic_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    integrity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class M09ScenarioAdjustment(Base):
    __tablename__ = "m09_scenario_adjustments"
    __table_args__ = (
        CheckConstraint("adjustment_type IN ('declared_additional_monthly_income','declared_additional_monthly_expense')", name="ck_m09_adjustment_type"),
        CheckConstraint("amount >= 0.01 AND amount <= 999999999999999999.99", name="ck_m09_adjustment_amount"),
        CheckConstraint("length(semantic_fingerprint) = 64", name="ck_m09_adjustment_fingerprint"),
        ForeignKeyConstraint(["scenario_subject_id", "client_id"], ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"], ondelete="RESTRICT"),
        UniqueConstraint("scenario_subject_id", "adjustment_id", name="uq_m09_subject_adjustment"),
        UniqueConstraint("scenario_subject_id", "ordinal", name="uq_m09_subject_adjustment_ordinal"),
        Index("ix_m09_adjustment_subject", "client_id", "scenario_subject_id", "ordinal"),
    )
    adjustment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    amount_text: Mapped[str] = mapped_column(String(32), nullable=False)
    start_month: Mapped[str] = mapped_column(String(7), nullable=False)
    end_month: Mapped[str] = mapped_column(String(7), nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class M09ScenarioSubjectSeal(Base):
    __tablename__ = "m09_scenario_subject_seals"
    __table_args__ = (
        CheckConstraint("adjustment_count >= 0", name="ck_m09_subject_seal_count"),
        CheckConstraint("length(adjustment_manifest_fingerprint) = 64", name="ck_m09_subject_seal_fingerprint"),
        ForeignKeyConstraint(
            ["scenario_subject_id", "client_id"],
            ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("scenario_subject_id", "client_id", name="uq_m09_subject_seal_client"),
    )
    scenario_subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustment_manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class M09SubjectRun(Base):
    __tablename__ = "m09_subject_runs"
    __table_args__ = (
        CheckConstraint("scenario_family = 'declared_retirement_cashflow_adjustments'", name="ck_m09_subject_run_family"),
        CheckConstraint("scenario_contract_version = 'v1'", name="ck_m09_subject_run_version"),
        CheckConstraint("status IN ('success_complete','validation_failed','dependency_failed','calculation_failed','unsupported')", name="ck_m09_subject_run_status"),
        CheckConstraint("length(factual_inventory_fingerprint) = 64 AND length(factual_baseline_material_fingerprint) = 64 AND length(adjustment_manifest_fingerprint) = 64 AND length(upstream_snapshot_fingerprint) = 64", name="ck_m09_subject_run_fingerprints"),
        CheckConstraint("(status = 'success_complete' AND range_totals IS NOT NULL AND semantic_result_fingerprint IS NOT NULL AND result_integrity_fingerprint IS NOT NULL) OR (status <> 'success_complete' AND range_totals IS NULL AND semantic_result_fingerprint IS NULL AND result_integrity_fingerprint IS NULL)", name="ck_m09_subject_run_shape"),
        ForeignKeyConstraint(["scenario_subject_id", "client_id"], ["m09_scenario_subjects.scenario_subject_id", "m09_scenario_subjects.client_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["predecessor_run_id", "scenario_subject_id", "client_id"], ["m09_subject_runs.run_id", "m09_subject_runs.scenario_subject_id", "m09_subject_runs.client_id"], ondelete="RESTRICT"),
        UniqueConstraint("run_id", "scenario_subject_id", "client_id", name="uq_m09_subject_run_identity"),
        UniqueConstraint("scenario_subject_id", "run_sequence", name="uq_m09_subject_run_sequence"),
        UniqueConstraint("predecessor_run_id", name="uq_m09_subject_run_predecessor"),
        Index("ix_m09_subject_run_client", "client_id", "scenario_subject_id", "created_at"),
    )
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    start_month: Mapped[str] = mapped_column(String(7), nullable=False)
    end_month: Mapped[str] = mapped_column(String(7), nullable=False)
    component_domain_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    factual_inventory: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    factual_inventory_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    factual_baseline_material_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    adjustment_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    adjustment_manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    upstream_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    upstream_snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    blocker_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    range_totals: Mapped[dict[str, str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    semantic_result_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_integrity_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class M09SubjectMonthlyResult(Base):
    __tablename__ = "m09_subject_monthly_results"
    __table_args__ = (
        CheckConstraint("length(result_fingerprint) = 64", name="ck_m09_subject_month_fingerprint"),
        ForeignKeyConstraint(["run_id", "scenario_subject_id", "client_id"], ["m09_subject_runs.run_id", "m09_subject_runs.scenario_subject_id", "m09_subject_runs.client_id"], ondelete="RESTRICT"),
        UniqueConstraint("run_id", "month", name="uq_m09_subject_run_month"),
    )
    monthly_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    gross_inflow_total: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    gross_outflow_total: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    period_net: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    component_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    result_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


SUBJECT_CLASSES = (M09ScenarioSubject, M09ScenarioAdjustment, M09ScenarioSubjectSeal, M09SubjectRun, M09SubjectMonthlyResult)


def authorize_subject_insert(row: object) -> None:
    authorize_m09_insert(row)
    now = m09_server_timestamp()
    if isinstance(row, M09ScenarioSubject):
        row.scenario_subject_id = row.scenario_subject_id or new_m09_id("M09-S")
    if isinstance(row, M09ScenarioAdjustment):
        row.adjustment_id = row.adjustment_id or new_m09_id("M09-A")
    if isinstance(row, M09SubjectRun):
        row.run_id = row.run_id or new_m09_id("M09-SR")
    if hasattr(row, "actor"):
        row.actor = getattr(row, "actor", None) or M09_WORKFLOW_ACTOR
    if hasattr(row, "created_at"):
        row.created_at = getattr(row, "created_at", None) or now


def _subject_before_insert(_mapper, _connection, row: object) -> None:
    if not getattr(row, "_m09_server_insert_authorized", False):
        raise ValueError("M09 subject evidence may be inserted only by the service")


def _subject_prevent_update(_mapper, _connection, row: object) -> None:
    if inspect(row).persistent:
        raise ValueError("M09 subject evidence is immutable")


def _subject_prevent_delete(_mapper, _connection, _row: object) -> None:
    raise ValueError("M09 subject evidence cannot be deleted")


for _model in SUBJECT_CLASSES:
    event.listen(_model, "before_insert", _subject_before_insert)
    event.listen(_model, "before_update", _subject_prevent_update)
    event.listen(_model, "before_delete", _subject_prevent_delete)


@event.listens_for(Engine, "before_execute", retval=True)
def _block_subject_bulk_mutation(conn, clauseelement, multiparams, params, execution_options):
    from sqlalchemy.sql.dml import Delete, Update

    table = getattr(clauseelement, "table", None)
    if isinstance(clauseelement, (Update, Delete)) and table is not None and table.name in {model.__tablename__ for model in SUBJECT_CLASSES}:
        raise ValueError("M09 subject evidence cannot be updated or deleted")
    return clauseelement, multiparams, params
