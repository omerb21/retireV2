from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FixationValidationError(Base):
    __tablename__ = "fixation_validation_errors"
    __table_args__ = (
        UniqueConstraint(
            "fixation_run_id",
            "error_order",
            name="uq_fixation_validation_errors_run_order",
        ),
        CheckConstraint("severity = 'error'", name="ck_fixation_validation_errors_severity"),
    )

    fixation_validation_error_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fixation_runs.id"), nullable=False
    )
    error_order: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    fixation_run: Mapped["FixationRun"] = relationship(
        "FixationRun", back_populates="fixation_validation_errors"
    )
