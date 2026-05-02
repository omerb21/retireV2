from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FixationRun(Base):
    __tablename__ = "fixation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'validation_failed')",
            name="ck_fixation_runs_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixation_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_data_version_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship("Client", back_populates="fixation_runs")
    fixation_input_snapshot: Mapped["FixationInputSnapshot | None"] = relationship(
        "FixationInputSnapshot", back_populates="fixation_run", uselist=False
    )
    fixation_result: Mapped["FixationResult | None"] = relationship(
        "FixationResult", back_populates="fixation_run", uselist=False
    )
    fixation_audit_rows: Mapped[list["FixationAuditRow"]] = relationship(
        "FixationAuditRow", back_populates="fixation_run"
    )
    fixation_validation_errors: Mapped[list["FixationValidationError"]] = relationship(
        "FixationValidationError", back_populates="fixation_run"
    )
