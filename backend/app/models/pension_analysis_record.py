from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PensionAnalysisRecord(Base):
    __tablename__ = "pension_analysis_record"
    __table_args__ = (
        UniqueConstraint(
            "pension_holding_id",
            name="uq_pension_analysis_record_pension_holding_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    pension_holding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pension_holding.id"), nullable=False
    )
    analysis_record_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="pension_analysis_records")
    pension_holding: Mapped["PensionHolding"] = relationship("PensionHolding")
