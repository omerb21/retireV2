"""Canonical pension source; legacy review/ledger records are not authorities."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


COMPONENT_CODES = (
    "פיצויים_מעסיק_נוכחי",
    "פיצויים_לאחר_התחשבנות",
    "פיצויים_שלא_עברו_התחשבנות",
    "פיצויים_ממעסיקים_קודמים_רצף_זכויות",
    "פיצויים_ממעסיקים_קודמים_רצף_קצבה",
    "תגמולי_עובד_עד_2000",
    "תגמולי_עובד_אחרי_2000",
    "תגמולי_עובד_אחרי_2008_לא_משלמת",
    "תגמולי_מעביד_עד_2000",
    "תגמולי_מעביד_אחרי_2000",
    "תגמולי_מעביד_אחרי_2008_לא_משלמת",
)
SEVERANCE_CODES = COMPONENT_CODES[:5]
REWARDS_CODES = COMPONENT_CODES[5:]


class ExactMoney(TypeDecorator):
    """NUMERIC(20,2) on PostgreSQL; lossless fixed-decimal text on SQLite.

    SQLite NUMERIC affinity stores nonintegral values as binary floats. It has
    no native fixed decimal type, so bind the same two-decimal representation
    as text there and perform all arithmetic in the Decimal service boundary.
    """
    impl = Numeric(20, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(String(22) if dialect.name == "sqlite" else Numeric(20, 2))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from app.schemas.pension_product import exact_money
        amount = exact_money(value)
        return format(amount, ".2f") if dialect.name == "sqlite" else amount

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


class PensionProduct(Base):
    __tablename__ = "pension_products"
    __table_args__ = (
        UniqueConstraint("client_id", "source_identity", name="uq_pension_product_identity"),
        CheckConstraint("source_kind IN ('manual','imported')", name="ck_pension_product_kind"),
        CheckConstraint("version > 0", name="ck_pension_product_version"),
    )

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), index=True)
    source_kind: Mapped[str] = mapped_column(String(16))
    source_identity: Mapped[str] = mapped_column(String(64))
    provider_name: Mapped[str | None] = mapped_column(String(255))
    provider_identifier: Mapped[str | None] = mapped_column(String(128))
    product_name: Mapped[str] = mapped_column(String(255))
    product_type: Mapped[str] = mapped_column(String(255))
    account_reference: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    statement_date: Mapped[date | None] = mapped_column(Date)
    historical_employers: Mapped[list] = mapped_column(JSON, default=list)
    reported_product_total: Mapped[Decimal | None] = mapped_column(ExactMoney())
    reported_rewards_total: Mapped[Decimal | None] = mapped_column(ExactMoney())
    reported_severance_total: Mapped[Decimal | None] = mapped_column(ExactMoney())
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(128))
    updated_by: Mapped[str] = mapped_column(String(128))


class PensionProductComponent(Base):
    __tablename__ = "pension_product_components"
    __table_args__ = (
        UniqueConstraint("product_id", "component_code", name="uq_pension_product_component"),
        CheckConstraint(
            "component_code IN (" + ",".join("'" + code + "'" for code in COMPONENT_CODES) + ")",
            name="ck_pension_product_component_code",
        ),
    )
    component_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("pension_products.product_id"), index=True)
    component_code: Mapped[str] = mapped_column(String(128))
    balance: Mapped[Decimal] = mapped_column(ExactMoney(), default=Decimal("0.00"))


class PensionProductSourceLink(Base):
    """Preserved technical evidence survives deletion of the current product.

    product_id is a historical identifier, deliberately not a cascading FK.
    source_identity + checksum stays unique even after deletion, so replay cannot
    silently resurrect a product. Raw bytes are stored transactionally.
    """
    __tablename__ = "pension_product_source_links"
    __table_args__ = (
        UniqueConstraint("client_id", "source_identity", "checksum", name="uq_pension_source_replay"),
    )
    source_link_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"))
    product_id: Mapped[str] = mapped_column(String(64), index=True)
    source_identity: Mapped[str] = mapped_column(String(64))
    checksum: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str | None] = mapped_column(String(255))
    raw_content: Mapped[bytes | None] = mapped_column(LargeBinary)
    legacy_intake_id: Mapped[str | None] = mapped_column(ForeignKey("m02_intake_records.intake_id"))
    statement_date: Mapped[date | None] = mapped_column(Date)
    diagnostics: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PensionProductAuditEvent(Base):
    """Append-only snapshots; no current professional authority or cascade."""
    __tablename__ = "pension_product_audit_events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"))
    product_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    actor: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
