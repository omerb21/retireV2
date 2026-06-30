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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.retirement_fact_contracts import (
    AMOUNT_BASES,
    ASSUMPTION_CATEGORIES,
    ASSUMPTION_OWNERS,
    CAPITAL_ASSET_CATEGORIES,
    CONTINUATION_STATUSES,
    EXPENSE_CATEGORIES,
    EXPENSE_TYPES,
    FREQUENCIES,
    INCOME_CATEGORIES,
    LIFECYCLE_STATUSES,
    PENSION_PRODUCT_TYPES,
    SOURCE_STATUSES,
    TIMING_CONFIDENCES,
    VERIFICATION_STATES,
    WORK_AFTER_RETIREMENT_INTENTIONS,
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


FACT_CONTEXT_COLUMNS = (
    "source_type",
    "source_date",
    "source_note",
    "source_status",
    "verification_state",
)


class PensionHolding(Base):
    __tablename__ = "pension_holding"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_pension_holding_lifecycle_status",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(SOURCE_STATUSES)})",
            name="ck_pension_holding_source_status",
        ),
        CheckConstraint(
            f"verification_state IN ({_quoted(VERIFICATION_STATES)})",
            name="ck_pension_holding_verification_state",
        ),
        CheckConstraint(
            f"product_type IN ({_quoted(PENSION_PRODUCT_TYPES)})",
            name="ck_pension_holding_product_type",
        ),
        CheckConstraint(
            "known_balance_amount IS NULL OR balance_as_of_date IS NOT NULL",
            name="ck_pension_holding_balance_date_required",
        ),
        CheckConstraint(
            "known_monthly_pension_amount IS NULL OR pension_amount_as_of_date IS NOT NULL",
            name="ck_pension_holding_pension_amount_date_required",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    source_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not recorded", server_default=text("'not recorded'")
    )
    verification_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="collected - not yet reviewed",
        server_default=text("'collected - not yet reviewed'"),
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    known_balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    balance_as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    known_monthly_pension_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    pension_amount_as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="pension_holdings")


class CapitalAsset(Base):
    __tablename__ = "capital_asset"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_capital_asset_lifecycle_status",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(SOURCE_STATUSES)})",
            name="ck_capital_asset_source_status",
        ),
        CheckConstraint(
            f"verification_state IN ({_quoted(VERIFICATION_STATES)})",
            name="ck_capital_asset_verification_state",
        ),
        CheckConstraint(
            f"asset_category IN ({_quoted(CAPITAL_ASSET_CATEGORIES)})",
            name="ck_capital_asset_asset_category",
        ),
        CheckConstraint(
            "known_value_amount IS NULL OR value_as_of_date IS NOT NULL",
            name="ck_capital_asset_value_date_required",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    asset_category: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_description: Mapped[str] = mapped_column(String(255), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    source_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not recorded", server_default=text("'not recorded'")
    )
    verification_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="collected - not yet reviewed",
        server_default=text("'collected - not yet reviewed'"),
    )
    known_value_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    value_as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    liquidity_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    restriction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="capital_assets")


class RecurringIncome(Base):
    __tablename__ = "recurring_income"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_recurring_income_lifecycle_status",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(SOURCE_STATUSES)})",
            name="ck_recurring_income_source_status",
        ),
        CheckConstraint(
            f"verification_state IN ({_quoted(VERIFICATION_STATES)})",
            name="ck_recurring_income_verification_state",
        ),
        CheckConstraint(
            f"income_category IN ({_quoted(INCOME_CATEGORIES)})",
            name="ck_recurring_income_income_category",
        ),
        CheckConstraint(
            f"amount_basis IN ({_quoted(AMOUNT_BASES)})",
            name="ck_recurring_income_amount_basis",
        ),
        CheckConstraint(
            f"frequency IN ({_quoted(FREQUENCIES)})",
            name="ck_recurring_income_frequency",
        ),
        CheckConstraint(
            f"continuation_status IN ({_quoted(CONTINUATION_STATUSES)})",
            name="ck_recurring_income_continuation_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    income_category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    continuation_status: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    source_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not recorded", server_default=text("'not recorded'")
    )
    verification_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="collected - not yet reviewed",
        server_default=text("'collected - not yet reviewed'"),
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="recurring_incomes")


class RecurringExpense(Base):
    __tablename__ = "recurring_expense"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_recurring_expense_lifecycle_status",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(SOURCE_STATUSES)})",
            name="ck_recurring_expense_source_status",
        ),
        CheckConstraint(
            f"verification_state IN ({_quoted(VERIFICATION_STATES)})",
            name="ck_recurring_expense_verification_state",
        ),
        CheckConstraint(
            f"expense_category IN ({_quoted(EXPENSE_CATEGORIES)})",
            name="ck_recurring_expense_expense_category",
        ),
        CheckConstraint(
            f"frequency IN ({_quoted(FREQUENCIES)})",
            name="ck_recurring_expense_frequency",
        ),
        CheckConstraint(
            f"expense_type IN ({_quoted(EXPENSE_TYPES)})",
            name="ck_recurring_expense_expense_type",
        ),
        CheckConstraint(
            f"continuation_status IN ({_quoted(CONTINUATION_STATUSES)})",
            name="ck_recurring_expense_continuation_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    expense_category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    expense_type: Mapped[str] = mapped_column(String(32), nullable=False)
    continuation_status: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    source_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not recorded", server_default=text("'not recorded'")
    )
    verification_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="collected - not yet reviewed",
        server_default=text("'collected - not yet reviewed'"),
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="recurring_expenses")


class RetirementTimingWorkIntention(Base):
    __tablename__ = "retirement_timing_work_intention"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_retirement_timing_work_intention_lifecycle_status",
        ),
        CheckConstraint(
            f"source_status IN ({_quoted(SOURCE_STATUSES)})",
            name="ck_retirement_timing_work_intention_source_status",
        ),
        CheckConstraint(
            f"verification_state IN ({_quoted(VERIFICATION_STATES)})",
            name="ck_retirement_timing_work_intention_verification_state",
        ),
        CheckConstraint(
            f"timing_confidence IN ({_quoted(TIMING_CONFIDENCES)})",
            name="ck_retirement_timing_work_intention_timing_confidence",
        ),
        CheckConstraint(
            "work_after_retirement_intention IN "
            f"({_quoted(WORK_AFTER_RETIREMENT_INTENTIONS)})",
            name="ck_retirement_timing_work_intention_work_intention",
        ),
        CheckConstraint(
            "other_known_retirement_date IS NULL "
            "OR other_known_retirement_date_label IS NOT NULL",
            name="ck_retirement_timing_work_intention_other_date_label_required",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    timing_confidence: Mapped[str] = mapped_column(String(64), nullable=False)
    work_after_retirement_intention: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    source_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not recorded", server_default=text("'not recorded'")
    )
    verification_state: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="collected - not yet reviewed",
        server_default=text("'collected - not yet reviewed'"),
    )
    planned_work_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    intended_pension_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    other_known_retirement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    other_known_retirement_date_label: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    anticipated_work_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    work_intention_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(
        "Client", back_populates="retirement_timing_work_intentions"
    )


class PlannerAssumption(Base):
    __tablename__ = "planner_assumption"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN ({_quoted(LIFECYCLE_STATUSES)})",
            name="ck_planner_assumption_lifecycle_status",
        ),
        CheckConstraint(
            f"assumption_category IN ({_quoted(ASSUMPTION_CATEGORIES)})",
            name="ck_planner_assumption_assumption_category",
        ),
        CheckConstraint(
            f"owner IN ({_quoted(ASSUMPTION_OWNERS)})",
            name="ck_planner_assumption_owner",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.client_id"), nullable=False)
    assumption_category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    assumption_value_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="current", server_default=text("'current'")
    )
    effective_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="planner_assumptions")
