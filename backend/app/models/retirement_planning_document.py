from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RetirementPlanningDocument(Base):
    __tablename__ = "retirement_planning_documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.client_id"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    collection_status: Mapped[str] = mapped_column(String(100), nullable=False)
    collection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="retirement_planning_documents")
