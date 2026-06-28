from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActualCapitalization(Base):
    __tablename__ = "actual_capitalizations"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_actual_caps_amount_non_negative"),
    )

    capitalization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    capitalization_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planner_assertion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planner_assertion_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="actual_capitalizations")
