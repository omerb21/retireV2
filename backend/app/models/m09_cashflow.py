from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


M09_WORKFLOW_ACTOR = "system:m09-cashflow:M09 cashflow workflow"


def m09_server_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def new_m09_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


class M09ResolvedComponentInventory(Base):
    __tablename__ = "m09_resolved_component_inventories"
    __table_args__ = (
        CheckConstraint(
            "scenario_family = 'deterministic_monthly_cashflow'",
            name="ck_m09_inventory_family",
        ),
        CheckConstraint(
            "scenario_contract_version = 'v1'",
            name="ck_m09_inventory_version",
        ),
        CheckConstraint(
            "length(inventory_fingerprint) = 64",
            name="ck_m09_inventory_fingerprint",
        ),
        UniqueConstraint(
            "inventory_id", "client_id", name="uq_m09_inventory_identity_client"
        ),
        Index("ix_m09_inventory_client", "client_id", "assessment_timestamp"),
    )

    inventory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False
    )
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    start_month: Mapped[str] = mapped_column(String(7), nullable=False)
    end_month: Mapped[str] = mapped_column(String(7), nullable=False)
    component_domain_contract_version: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    assessment_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    inventory_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    inventory_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocker_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class M09ScenarioRun(Base):
    __tablename__ = "m09_scenario_runs"
    __table_args__ = (
        CheckConstraint(
            "scenario_family = 'deterministic_monthly_cashflow'",
            name="ck_m09_run_family",
        ),
        CheckConstraint(
            "scenario_contract_version = 'v1'",
            name="ck_m09_run_version",
        ),
        CheckConstraint(
            "status IN ('success_complete','validation_failed','dependency_failed','calculation_failed','unsupported')",
            name="ck_m09_run_status",
        ),
        CheckConstraint(
            "length(assumption_manifest_fingerprint) = 64 AND length(upstream_snapshot_fingerprint) = 64",
            name="ck_m09_run_required_fingerprints",
        ),
        CheckConstraint(
            "(status = 'success_complete' AND range_totals IS NOT NULL AND semantic_result_fingerprint IS NOT NULL AND result_integrity_fingerprint IS NOT NULL) OR (status <> 'success_complete' AND range_totals IS NULL AND semantic_result_fingerprint IS NULL AND result_integrity_fingerprint IS NULL)",
            name="ck_m09_run_result_shape",
        ),
        ForeignKeyConstraint(
            ["inventory_id", "client_id"],
            [
                "m09_resolved_component_inventories.inventory_id",
                "m09_resolved_component_inventories.client_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["predecessor_run_id", "client_id"],
            ["m09_scenario_runs.run_id", "m09_scenario_runs.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id", "client_id", name="uq_m09_run_identity_client"),
        UniqueConstraint(
            "client_id",
            "scenario_family",
            "scenario_contract_version",
            "run_sequence",
            name="uq_m09_run_client_family_sequence",
        ),
        UniqueConstraint("predecessor_run_id", name="uq_m09_run_predecessor_child"),
        Index("ix_m09_run_client", "client_id", "created_at"),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    start_month: Mapped[str] = mapped_column(String(7), nullable=False)
    end_month: Mapped[str] = mapped_column(String(7), nullable=False)
    inventory_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    assumption_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    assumption_manifest_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    upstream_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    upstream_snapshot_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    blocker_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    range_totals: Mapped[dict[str, str] | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )
    semantic_result_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    result_integrity_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class M09MonthlyResult(Base):
    __tablename__ = "m09_monthly_results"
    __table_args__ = (
        CheckConstraint(
            "length(result_fingerprint) = 64", name="ck_m09_month_result_fingerprint"
        ),
        ForeignKeyConstraint(
            ["run_id", "client_id"],
            ["m09_scenario_runs.run_id", "m09_scenario_runs.client_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id", "month", name="uq_m09_run_month"),
        Index("ix_m09_monthly_run", "client_id", "run_id", "month"),
    )

    monthly_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    gross_inflow_total: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    gross_outflow_total: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    period_net: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    component_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    result_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


_CLASSES = (
    M09ResolvedComponentInventory,
    M09ScenarioRun,
    M09MonthlyResult,
)
_TABLE_NAMES = {model.__tablename__ for model in _CLASSES}


def authorize_m09_insert(target: object) -> None:
    setattr(target, "_m09_server_insert_authorized", True)


def _before_insert(_mapper, _connection, target: object) -> None:
    if not getattr(target, "_m09_server_insert_authorized", False):
        raise ValueError("M09 records may be inserted only by the M09 service")
    now = m09_server_timestamp()
    if isinstance(target, M09ResolvedComponentInventory):
        target.inventory_id = target.inventory_id or new_m09_id("M09-I")
        target.assessment_timestamp = target.assessment_timestamp or now
        target.actor = target.actor or M09_WORKFLOW_ACTOR
    elif isinstance(target, M09ScenarioRun):
        target.run_id = target.run_id or new_m09_id("M09-R")
        target.created_at = target.created_at or now
        target.actor = target.actor or M09_WORKFLOW_ACTOR


def _prevent_update(_mapper, _connection, target: object) -> None:
    if inspect(target).persistent:
        raise ValueError("M09 append-only records are immutable")


def _prevent_delete(_mapper, _connection, _target: object) -> None:
    raise ValueError("M09 append-only records cannot be deleted")


for _model in _CLASSES:
    event.listen(_model, "before_insert", _before_insert)
    event.listen(_model, "before_update", _prevent_update)
    event.listen(_model, "before_delete", _prevent_delete)


@event.listens_for(Engine, "before_execute", retval=True)
def _block_bulk_mutation(conn, clauseelement, multiparams, params, execution_options):
    from sqlalchemy.sql.dml import Delete, Update

    if isinstance(clauseelement, (Update, Delete)):
        table = getattr(clauseelement, "table", None)
        if table is not None and table.name in _TABLE_NAMES:
            raise ValueError("M09 append-only records cannot be updated or deleted")
    return clauseelement, multiparams, params
