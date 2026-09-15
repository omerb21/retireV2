"""Explicit planning decisions only; never a persisted derived input view."""
from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PlanningInputDecision(Base):
    __tablename__ = "planning_input_decisions"
    __table_args__ = (CheckConstraint("version > 0", name="ck_planning_decision_version"),)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    planning_base_date: Mapped[date | None] = mapped_column(Date)
    retirement_target_date: Mapped[date | None] = mapped_column(Date)
    retirement_target_decision_actor: Mapped[str | None] = mapped_column(String(128))
    retirement_target_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retirement_target_reference_fingerprint: Mapped[str | None] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PensionIncomeResolution(Base):
    __tablename__ = "pension_income_resolutions"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_pension_resolution_version"),
        CheckConstraint("decision_kind IN ('SAME_CANONICAL_PENSION','PENSION_NOT_YET_CANONICAL','MISCLASSIFIED_GENERAL_INCOME')", name="ck_pension_resolution_kind"),
    )
    income_id: Mapped[int] = mapped_column(ForeignKey("recurring_income.id", ondelete="RESTRICT"), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    income_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_source_id: Mapped[str | None] = mapped_column(String(128))
    canonical_fingerprint: Mapped[str | None] = mapped_column(String(64))
    reference: Mapped[str] = mapped_column(String(512), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
