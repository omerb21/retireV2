from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Grant(Base):
    __tablename__ = "grants"
    __table_args__ = (
        CheckConstraint(
            "indexed_amount IS NULL OR indexed_amount >= 0",
            name="ck_grants_indexed_amount_non_negative",
        ),
        CheckConstraint(
            "nominal_amount IS NULL OR nominal_amount >= 0",
            name="ck_grants_nominal_amount_non_negative",
        ),
        CheckConstraint("work_end_date > work_start_date", name="ck_grants_work_dates_order"),
    )

    grant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    employment_record_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("employment_records.employment_record_id"), nullable=True
    )
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employer_withholding_file_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    nominal_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    indexed_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    grant_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="grants")
    employment_record: Mapped["EmploymentRecord | None"] = relationship(
        "EmploymentRecord", back_populates="grants"
    )
