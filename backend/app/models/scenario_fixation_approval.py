"""Persisted, non-authoritative professional fixation review drafts.

A head row supplies atomic CAS. Immutable revisions preserve history. Neither
table is a tax determination or grants authority to run a fixation engine.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScenarioFixationApprovalHead(Base):
    __tablename__ = "scenario_fixation_approval_heads"
    __table_args__ = (
        UniqueConstraint("client_id", "scenario_id", name="uq_fixation_approval_client_scenario"),
        CheckConstraint("current_version > 0", name="ck_fixation_approval_head_version"),
        CheckConstraint("status IN ('DRAFT','BLOCKED','APPROVED_INTERNAL')", name="ck_fixation_approval_head_status"),
    )

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ScenarioFixationApprovalRevision(Base):
    __tablename__ = "scenario_fixation_approval_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["approval_id"], ["scenario_fixation_approval_heads.approval_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("approval_id", "approval_version", name="uq_fixation_approval_revision"),
        CheckConstraint("approval_version > 0", name="ck_fixation_approval_revision_version"),
        CheckConstraint("scenario_version > 0", name="ck_fixation_approval_revision_scenario_version"),
        CheckConstraint("status IN ('DRAFT','BLOCKED','APPROVED_INTERNAL')", name="ck_fixation_approval_revision_status"),
    )

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    approval_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False)
    approval_version: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    readiness_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    decisions_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    blockers_json: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
