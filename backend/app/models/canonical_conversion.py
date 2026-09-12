"""Canonical conversion records; no legacy source/destination authority."""
from sqlalchemy import Column, Table, String, Integer, ForeignKey, Date, DateTime, JSON, Boolean, UniqueConstraint, CheckConstraint, func
from app.db.base import Base
from app.models.pension_product import ExactMoney
from sqlalchemy import event
from app.services.canonical_conversion_archive_service import install_conversion_guards


def identity(name):
    return Column(name, String(64), primary_key=True)


def client():
    return Column("client_id", Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)


def created():
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now())


batches = Table("canonical_conversion_batches", Base.metadata,
    identity("batch_id"), client(),
    Column("source_product_id", String(64), ForeignKey("pension_products.product_id", ondelete="RESTRICT"), nullable=False),
    Column("destination_type", String(16), nullable=False), Column("matrix_version", String(128), nullable=False),
    Column("idempotency_key", String(128), nullable=False), Column("request_fingerprint", String(64), nullable=False),
    Column("expected_product_version", Integer, nullable=False), Column("status", String(16), nullable=False),
    Column("effective_date", Date, nullable=False), Column("actor", String(128), nullable=False),
    Column("result", JSON, nullable=False), created(),
    UniqueConstraint("client_id", "idempotency_key", name="uq_canonical_batch_key"),
    CheckConstraint("destination_type IN ('pension','capital')", name="ck_canonical_batch_destination"),
    CheckConstraint("status = 'completed'", name="ck_canonical_batch_status"))

conversions = Table("canonical_conversions", Base.metadata,
    identity("conversion_id"), client(),
    Column("batch_id", String(64), ForeignKey("canonical_conversion_batches.batch_id", ondelete="RESTRICT"), nullable=False),
    Column("destination_type", String(16), nullable=False), Column("tax_treatment", String(32), nullable=False),
    Column("converted_amount", ExactMoney(), nullable=False), Column("status", String(16), nullable=False),
    Column("version", Integer, nullable=False), created(), Column("reversed_at", DateTime(timezone=True)),
    CheckConstraint("status IN ('active','reversed')", name="ck_canonical_conversion_status"),
    CheckConstraint("version > 0", name="ck_canonical_conversion_version"),
    CheckConstraint("(destination_type = 'pension' AND tax_treatment IN ('taxable','exempt')) OR (destination_type = 'capital' AND tax_treatment IN ('exempt','capital_gains'))", name="ck_canonical_conversion_tax"))

allocations = Table("canonical_conversion_allocations", Base.metadata,
    identity("allocation_id"),
    Column("conversion_id", String(64), ForeignKey("canonical_conversions.conversion_id", ondelete="RESTRICT"), nullable=False),
    Column("source_product_id", String(64), ForeignKey("pension_products.product_id", ondelete="RESTRICT"), nullable=False),
    Column("source_component_id", String(64), ForeignKey("pension_product_components.component_id", ondelete="RESTRICT"), nullable=False),
    Column("component_code_snapshot", String(128), nullable=False), Column("amount", ExactMoney(), nullable=False),
    Column("source_balance_before", ExactMoney(), nullable=False), Column("source_balance_after", ExactMoney(), nullable=False),
    Column("tax_treatment", String(32), nullable=False), Column("matrix_version", String(128), nullable=False),
    UniqueConstraint("conversion_id", "source_component_id", name="uq_canonical_allocation_component"))

pensions = Table("canonical_pension_destinations", Base.metadata,
    identity("pension_destination_id"), client(),
    Column("conversion_id", String(64), ForeignKey("canonical_conversions.conversion_id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("name", String(255), nullable=False), Column("description", String(255), nullable=False),
    Column("converted_balance", ExactMoney(), nullable=False), Column("effective_date", Date, nullable=False),
    Column("pension_start_date", Date, nullable=False), Column("annuity_factor_text", String(128), nullable=False),
    Column("coefficient_source", String(128), nullable=False), Column("coefficient_source_keys", JSON, nullable=False),
    Column("coefficient_notes", String(2048), nullable=False), Column("coefficient_catalog_version", String(128), nullable=False),
    Column("coefficient_fallback_used", Boolean, nullable=False), Column("monthly_numerator", String(128), nullable=False),
    Column("monthly_denominator", String(128), nullable=False), Column("monthly_display_amount", ExactMoney(), nullable=False),
    Column("tax_treatment", String(32), nullable=False), Column("status", String(16), nullable=False),
    Column("version", Integer, nullable=False), created(), Column("reversed_at", DateTime(timezone=True)),
    CheckConstraint("status IN ('active','reversed')", name="ck_canonical_pension_status"),
    CheckConstraint("tax_treatment IN ('taxable','exempt')", name="ck_canonical_pension_tax"))

reversals = Table("canonical_conversion_reversals", Base.metadata,
    identity("reversal_id"), client(),
    Column("conversion_id", String(64), ForeignKey("canonical_conversions.conversion_id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("idempotency_key", String(128), nullable=False), Column("request_fingerprint", String(64), nullable=False),
    Column("expected_conversion_version", Integer, nullable=False), Column("reason", String(1024), nullable=False),
    Column("actor", String(128), nullable=False), Column("result", JSON, nullable=False), created(),
    UniqueConstraint("client_id", "idempotency_key", name="uq_canonical_reversal_key"))


@event.listens_for(Base.metadata, "after_create")
def _install_guards(metadata, connection, **kwargs):
    # Base.create_all fixtures get the same SQL-level retention as migrations.
    names = {batches.name, conversions.name, allocations.name, pensions.name, reversals.name, "capital_asset"}
    install_conversion_guards(connection, [table for table in kwargs.get("tables", []) if table.name in names])
