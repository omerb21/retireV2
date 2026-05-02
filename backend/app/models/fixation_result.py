from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FixationResult(Base):
    __tablename__ = "fixation_results"
    __table_args__ = (
        CheckConstraint(
            "initial_exempt_capital >= 0 AND grant_impact_total >= 0 AND "
            "future_grant_reserved >= 0 AND future_grant_impact >= 0 AND "
            "actual_capitalization_impact >= 0 AND idf_impact >= 0 AND total_impact >= 0 AND "
            "remaining_exempt_capital >= 0 AND monthly_exempt_pension >= 0",
            name="ck_fixation_results_non_negative_money",
        ),
    )

    fixation_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fixation_runs.id"), nullable=False, unique=True
    )
    result_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    initial_exempt_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    grant_impact_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    future_grant_reserved: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    future_grant_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    actual_capitalization_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    idf_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_impact: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remaining_exempt_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_exempt_pension: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    capital_exemption_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    pension_exemption_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    fixation_run: Mapped["FixationRun"] = relationship("FixationRun", back_populates="fixation_result")
