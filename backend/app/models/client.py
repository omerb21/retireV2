from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint(
            "employment_status IS NULL OR employment_status IN "
            "('salaried_employee', 'self_employed', 'salaried_and_self_employed', "
            "'not_currently_working', 'unknown')",
            name="ck_clients_employment_status",
        ),
        CheckConstraint(
            "planned_retirement_age IS NULL "
            "OR planned_retirement_age BETWEEN 18 AND 120",
            name="ck_clients_planned_retirement_age",
        ),
        CheckConstraint(
            "planned_retirement_age IS NULL OR planned_retirement_date IS NULL",
            name="ck_clients_planned_retirement_exclusive",
        ),
    )

    client_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    id_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    planned_retirement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_retirement_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    missing_data_items: Mapped[list["MissingDataItem"]] = relationship(
        "MissingDataItem", back_populates="client"
    )
    pension_holdings: Mapped[list["PensionHolding"]] = relationship(
        "PensionHolding", back_populates="client"
    )
    pension_analysis_records: Mapped[list["PensionAnalysisRecord"]] = relationship(
        "PensionAnalysisRecord", back_populates="client"
    )
    capital_assets: Mapped[list["CapitalAsset"]] = relationship(
        "CapitalAsset", back_populates="client"
    )
    recurring_incomes: Mapped[list["RecurringIncome"]] = relationship(
        "RecurringIncome", back_populates="client"
    )
    recurring_expenses: Mapped[list["RecurringExpense"]] = relationship(
        "RecurringExpense", back_populates="client"
    )
    retirement_timing_work_intentions: Mapped[list["RetirementTimingWorkIntention"]] = (
        relationship("RetirementTimingWorkIntention", back_populates="client")
    )
    planner_assumptions: Mapped[list["PlannerAssumption"]] = relationship(
        "PlannerAssumption", back_populates="client"
    )
    fixation_runs: Mapped[list["FixationRun"]] = relationship(
        "FixationRun", back_populates="client"
    )
