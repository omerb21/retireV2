from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FixationAuditRow(Base):
    __tablename__ = "fixation_audit_rows"
    __table_args__ = (
        UniqueConstraint("fixation_run_id", "row_order", name="uq_fixation_audit_rows_run_order"),
        CheckConstraint("impact_amount >= 0", name="ck_fixation_audit_rows_impact_non_negative"),
    )

    fixation_audit_row_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fixation_runs.id"), nullable=False
    )
    row_order: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    input_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    output_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    impact_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    details_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    fixation_run: Mapped["FixationRun"] = relationship(
        "FixationRun", back_populates="fixation_audit_rows"
    )
