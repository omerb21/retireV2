"""Explicit, source-bound price comparability decisions for Stage 6 pensions."""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScenarioPensionPriceBasis(Base):
    __tablename__ = "scenario_pension_price_basis_decisions"
    __table_args__ = (
        UniqueConstraint("client_id", "scenario_id", "decision_id", "revision", name="uq_s6_price_basis_revision"),
        CheckConstraint("scenario_version > 0 AND revision > 0", name="ck_s6_price_basis_versions"),
        CheckConstraint("price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','UNKNOWN')", name="ck_s6_price_basis_choice"),
        CheckConstraint("length(actor_id) BETWEEN 1 AND 128", name="ck_s6_price_basis_actor"),
        CheckConstraint("length(source_fingerprint) = 64 AND length(target_fingerprint) = 64 AND length(record_fingerprint) = 64", name="ck_s6_price_basis_hashes"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False)
    decision_id: Mapped[str] = mapped_column(ForeignKey("scenario_draft_decisions.decision_id", ondelete="RESTRICT"), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    target_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_basis: Mapped[str] = mapped_column(String(48), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    record_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
