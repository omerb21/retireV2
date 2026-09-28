"""Manual pension facts are a distinct authority, never RecurringIncome."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.pension_product import ExactMoney


class CanonicalManualPensionSource(Base):
    __tablename__ = "canonical_manual_pension_sources"
    __table_args__ = (
        CheckConstraint("input_mode IN ('entered','calculated')", name="ck_manual_pension_mode"),
        CheckConstraint("lifecycle_status IN ('current','superseded')", name="ck_manual_pension_lifecycle"),
        CheckConstraint("version > 0", name="ck_manual_pension_version"),
        CheckConstraint("monthly_amount IS NULL OR CAST(monthly_amount AS NUMERIC) >= 0", name="ck_manual_pension_amount"),
        CheckConstraint("balance IS NULL OR CAST(balance AS NUMERIC) >= 0", name="ck_manual_pension_balance"),
        CheckConstraint("annuity_factor IS NULL OR CAST(annuity_factor AS NUMERIC) > 0", name="ck_manual_pension_factor"),
        CheckConstraint("(input_mode = 'entered' AND balance IS NULL AND annuity_factor IS NULL) OR (input_mode = 'calculated' AND monthly_amount IS NULL)", name="ck_manual_pension_exclusive"),
    )
    manual_pension_source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT"), index=True)
    input_mode: Mapped[str] = mapped_column(String(16))
    payer_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(String(255))
    monthly_amount: Mapped[Decimal | None] = mapped_column(ExactMoney())
    balance: Mapped[Decimal | None] = mapped_column(ExactMoney())
    annuity_factor: Mapped[str | None] = mapped_column(String(128))
    pension_start_date: Mapped[date | None] = mapped_column(Date)
    base_amount_effective_date: Mapped[date | None] = mapped_column(Date)
    tax_treatment: Mapped[str | None] = mapped_column(String(64))
    indexation_method: Mapped[str | None] = mapped_column(String(64))
    fixed_indexation_rate: Mapped[str | None] = mapped_column(String(128))
    source_note: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(String(16), default="current", server_default="current")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
