from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmploymentRecord(Base):
    __tablename__ = "employment_records"
    __table_args__ = (
        CheckConstraint(
            "work_end_date IS NULL OR work_end_date >= work_start_date",
            name="ck_employment_dates_order",
        ),
    )

    employment_record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    work_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="employment_records")
    grants: Mapped[list["Grant"]] = relationship("Grant", back_populates="employment_record")
