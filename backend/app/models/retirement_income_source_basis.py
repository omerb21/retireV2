"""Append-only professional income and price-basis decisions at retirement target date."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetirementTargetDateIncomeSourceBasisDecision(Base):
    __tablename__ = "retirement_target_date_income_source_basis_decisions"
    __table_args__ = (
        UniqueConstraint("client_id", "source_kind", "source_id", "decision_version", name="uq_crtisba_source_decision_version"),
        CheckConstraint("decision_version BETWEEN 1 AND 9223372036854775807", name="ck_crtisba_decision_version_positive"),
        CheckConstraint("source_kind IN ('PENSION','RECURRING_INCOME')", name="ck_crtisba_source_kind"),
        CheckConstraint("(source_kind = 'PENSION' AND (source_id LIKE 'manual:%' OR source_id LIKE 'conversion:%')) OR (source_kind = 'RECURRING_INCOME' AND source_id LIKE 'income:%')", name="ck_crtisba_source_identity_shape"),
        CheckConstraint("income_basis IN ('GROSS','NET','UNKNOWN')", name="ck_crtisba_income_basis"),
        CheckConstraint("income_basis_provenance IN ('EXPLICIT_PROFESSIONAL','UPSTREAM_RECURRING_AMOUNT_BASIS','MISSING')", name="ck_crtisba_income_basis_provenance"),
        CheckConstraint("price_basis IS NULL OR price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','REAL_AT_REFERENCE_DATE','UNKNOWN')", name="ck_crtisba_price_basis"),
        CheckConstraint("price_basis_provenance IS NULL OR price_basis_provenance IN ('EXPLICIT_PROFESSIONAL','MISSING')", name="ck_crtisba_price_basis_provenance"),
        CheckConstraint("(source_kind = 'PENSION' AND pension_source_version IS NOT NULL AND recurring_source_version_fingerprint IS NULL AND pension_source_execution_fingerprint IS NOT NULL AND pension_source_result_fingerprint IS NOT NULL AND portfolio_source_entry_fingerprint IS NOT NULL AND retirement_target_date IS NOT NULL AND price_basis IS NULL AND price_reference_date IS NULL AND price_basis_provenance IS NULL) OR (source_kind = 'RECURRING_INCOME' AND pension_source_version IS NULL AND recurring_source_version_fingerprint IS NOT NULL AND pension_source_execution_fingerprint IS NULL AND pension_source_result_fingerprint IS NULL AND portfolio_source_entry_fingerprint IS NULL AND retirement_target_date IS NULL AND price_basis IS NOT NULL AND price_basis_provenance IS NOT NULL)", name="ck_crtisba_kind_payload"),
        CheckConstraint("(price_basis = 'REAL_AT_REFERENCE_DATE' AND price_reference_date IS NOT NULL) OR (price_basis IS NULL OR price_basis <> 'REAL_AT_REFERENCE_DATE') AND price_reference_date IS NULL", name="ck_crtisba_reference_date"),
        CheckConstraint("length(planning_calculation_input_fingerprint)=64 AND (recurring_source_version_fingerprint IS NULL OR length(recurring_source_version_fingerprint)=64) AND length(source_fingerprint)=64 AND length(amount_authority_fingerprint)=64 AND (pension_source_execution_fingerprint IS NULL OR length(pension_source_execution_fingerprint)=64) AND (pension_source_result_fingerprint IS NULL OR length(pension_source_result_fingerprint)=64) AND (portfolio_source_entry_fingerprint IS NULL OR length(portfolio_source_entry_fingerprint)=64) AND length(decision_fingerprint)=64", name="ck_crtisba_hash_shapes"),
        Index("ix_crtisba_source_latest_version", "client_id", "source_kind", "source_id", desc("decision_version")),
    )

    decision_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id", ondelete="RESTRICT", name="fk_crtisba_decision_client"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    planning_calculation_input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    pension_source_version: Mapped[int | None] = mapped_column(Integer)
    recurring_source_version_fingerprint: Mapped[str | None] = mapped_column(String(64))
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_authority_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    pension_source_execution_fingerprint: Mapped[str | None] = mapped_column(String(64))
    pension_source_result_fingerprint: Mapped[str | None] = mapped_column(String(64))
    portfolio_source_entry_fingerprint: Mapped[str | None] = mapped_column(String(64))
    retirement_target_date: Mapped[date | None] = mapped_column(Date)
    income_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    income_basis_provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    price_basis: Mapped[str | None] = mapped_column(String(64))
    price_reference_date: Mapped[date | None] = mapped_column(Date)
    price_basis_provenance: Mapped[str | None] = mapped_column(String(40))
    decision_actor: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decision_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
