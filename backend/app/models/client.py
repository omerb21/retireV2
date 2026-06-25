from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    id_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client_profile: Mapped["ClientProfile | None"] = relationship(
        "ClientProfile", back_populates="client", uselist=False
    )
    employment_records: Mapped[list["EmploymentRecord"]] = relationship(
        "EmploymentRecord", back_populates="client"
    )
    grants: Mapped[list["Grant"]] = relationship("Grant", back_populates="client")
    actual_capitalizations: Mapped[list["ActualCapitalization"]] = relationship(
        "ActualCapitalization", back_populates="client"
    )
    clearinghouse_snapshots: Mapped[list["ClearinghouseSnapshot"]] = relationship(
        "ClearinghouseSnapshot", back_populates="client"
    )
    retirement_planning_documents: Mapped[list["RetirementPlanningDocument"]] = relationship(
        "RetirementPlanningDocument", back_populates="client"
    )
    fixation_runs: Mapped[list["FixationRun"]] = relationship(
        "FixationRun", back_populates="client"
    )
