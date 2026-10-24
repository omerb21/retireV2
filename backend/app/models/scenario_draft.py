"""Isolated, non-authoritative retirement scenario drafts."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.pension_product import COMPONENT_CODES

class ScenarioDraft(Base):
    __tablename__ = "scenario_drafts"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_scenario_draft_version"),
        CheckConstraint("status IN ('draft','needs_revalidation','archived')", name="ck_scenario_draft_status"),
    )
    scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class ScenarioDraftDecision(Base):
    __tablename__ = "scenario_draft_decisions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_scenario_draft_decision_positive"),
        CheckConstraint("action IN ('pension','capital_asset')", name="ck_scenario_draft_decision_action"),
        CheckConstraint("validation_state IN ('unverified','needs_revalidation')", name="ck_scenario_draft_decision_validation"),
        CheckConstraint("component_code IN (" + ",".join("'" + code + "'" for code in COMPONENT_CODES) + ")", name="ck_scenario_draft_decision_component"),
    )
    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    source_product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_component_id: Mapped[str] = mapped_column(String(64), nullable=False)
    component_code: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20,2), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    product_version_at_review: Mapped[int | None] = mapped_column(Integer)
    source_fingerprint_at_review: Mapped[str | None] = mapped_column(String(64))
    ruleset_digest_at_review: Mapped[str | None] = mapped_column(String(64))
    permission_preview_id_at_review: Mapped[str | None] = mapped_column(String(64))

class ScenarioDraftRevision(Base):
    __tablename__ = "scenario_draft_revisions"
    __table_args__ = (UniqueConstraint("scenario_id", "version", name="uq_scenario_draft_revision_version"),)
    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
