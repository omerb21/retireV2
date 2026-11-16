"""M11 non-authoritative, client-scoped preferred scenario selection history."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class M11PreferredScenarioRevision(Base):
    __tablename__ = "m11_preferred_scenario_revisions"
    __table_args__ = (
        ForeignKeyConstraint(["scenario_id", "client_id"], ["scenario_drafts.scenario_id", "scenario_drafts.client_id"], ondelete="RESTRICT"),
        UniqueConstraint("client_id", "revision", name="uq_m11_client_revision"),
        CheckConstraint("revision > 0", name="ck_m11_revision_positive"),
        CheckConstraint("scenario_version > 0", name="ck_m11_scenario_version_positive"),
    )
    selection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    calculation_references: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
