"""Explicit temporal/indexation decisions for converted pension destinations."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CanonicalPensionTemporalDecision(Base):
    __tablename__ = "canonical_pension_temporal_decisions"
    __table_args__ = (
        CheckConstraint("authority_kind IN ('none','fixed_manual')", name="ck_pension_temporal_kind"),
        CheckConstraint("source_version_at_decision > 0", name="ck_pension_temporal_source_version"),
        CheckConstraint("version > 0", name="ck_pension_temporal_version"),
        CheckConstraint(
            "(authority_kind = 'none' AND annual_rate_text IS NULL AND rate_basis IS NULL) OR "
            "(authority_kind = 'fixed_manual' AND annual_rate_text IS NOT NULL AND rate_basis = 'ANNUAL_EFFECTIVE')",
            name="ck_pension_temporal_semantics",
        ),
    )

    pension_destination_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("canonical_pension_destinations.pension_destination_id", ondelete="RESTRICT"), primary_key=True
    )
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False)
    authority_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    annual_rate_text: Mapped[str | None] = mapped_column(String(128))
    rate_basis: Mapped[str | None] = mapped_column(String(32))
    source_version_at_decision: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
