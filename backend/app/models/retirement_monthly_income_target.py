"""Explicit confirmed retirement-income target authority."""
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetirementMonthlyIncomeTargetElection(Base):
    __tablename__ = "retirement_monthly_income_target_elections"
    __table_args__ = (
        CheckConstraint("version BETWEEN 1 AND 9223372036854775807", name="ck_rit_version"),
        CheckConstraint("lifecycle_state IN ('CONFIRMED','STALE')", name="ck_rit_lifecycle"),
        CheckConstraint("currency = 'ILS'", name="ck_rit_currency"),
        CheckConstraint("income_basis IN ('GROSS','NET')", name="ck_rit_income_basis"),
        CheckConstraint(
            "price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','REAL_AT_REFERENCE_DATE')",
            name="ck_rit_price_basis",
        ),
        CheckConstraint(
            "(price_basis = 'NOMINAL_AT_RETIREMENT_TARGET_DATE' AND price_reference_date IS NULL) OR "
            "(price_basis = 'REAL_AT_REFERENCE_DATE' AND price_reference_date IS NOT NULL)",
            name="ck_rit_price_reference",
        ),
        CheckConstraint(
            "source_kind IN ('CLIENT_SUPPLIED','PLANNER_SUPPLIED','CLIENT_SUPPLIED_PLANNER_CONFIRMED')",
            name="ck_rit_source_kind",
        ),
        CheckConstraint("confirmation_state = 'CONFIRMED'", name="ck_rit_confirmation_state"),
        CheckConstraint("length(confirmation_actor) BETWEEN 1 AND 128", name="ck_rit_actor_length"),
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.client_id", ondelete="RESTRICT"), primary_key=True
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(16), nullable=False)
    planning_calculation_input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    retirement_target_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_amount_text: Mapped[str] = mapped_column(String(25), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    income_basis: Mapped[str] = mapped_column(String(8), nullable=False)
    price_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    price_reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(16), nullable=False)
    confirmation_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_semantic_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
