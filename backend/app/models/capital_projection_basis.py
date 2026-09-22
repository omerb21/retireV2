"""Exact per-capital-source assumptions, never calculated results."""
import re
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

CONTRACT = 'canonical-pre-retirement-projection-basis-v1'
PROVENANCE = 'explicit_professional_capital_projection_basis'
RATE_PATTERN = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z', re.ASCII)


def parse_rate(value):
    if not isinstance(value, str) or not RATE_PATTERN.fullmatch(value) or value == '-0':
        raise ValueError('נדרש שיעור עשרוני מדויק ללא מעריך, רווחים או אפסים מיותרים')
    number = Decimal(value)
    if not number.is_finite() or number <= -1:
        raise ValueError('השיעור חייב להיות גדול ממינוס אחד')
    return number


def rate_string(value):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError('Invalid exact rate storage')
    if value == 0:
        return '0'
    result = format(value, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


class ExactRate(TypeDecorator):
    """Unconstrained PostgreSQL NUMERIC; exact text on SQLite, never REAL."""
    impl = Numeric
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(Text() if dialect.name == 'sqlite' else Numeric())

    def process_bind_param(self, value, dialect):
        if value is None: return None
        canonical = rate_string(value) if isinstance(value, Decimal) else value
        parsed = parse_rate(canonical)
        return canonical if dialect.name == 'sqlite' else parsed

    def process_result_value(self, value, dialect):
        if value is None: return None
        if isinstance(value, float): raise ValueError('Binary float rate storage is forbidden')
        return Decimal(value)


class CapitalProjectionBasisDecision(Base):
    __tablename__ = 'capital_projection_basis_decisions'
    __table_args__ = (
        CheckConstraint("return_basis IN ('NET','GROSS')", name='ck_projection_return_basis'),
        CheckConstraint("price_basis IN ('NOMINAL','REAL')", name='ck_projection_price_basis'),
        CheckConstraint(f"contract_version = '{CONTRACT}'", name='ck_projection_contract'),
        CheckConstraint(f"provenance = '{PROVENANCE}'", name='ck_projection_provenance'),
    )
    capital_asset_id: Mapped[int] = mapped_column(ForeignKey('capital_asset.id', ondelete='RESTRICT'), primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.client_id', ondelete='RESTRICT'), nullable=False)
    annual_rate: Mapped[Decimal] = mapped_column(ExactRate(), nullable=False)
    return_basis: Mapped[str] = mapped_column(String(8), nullable=False)
    price_basis: Mapped[str] = mapped_column(String(8), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_semantic_fingerprint_at_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    timing_context_fingerprint_at_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    planning_calculation_input_fingerprint_at_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    provenance: Mapped[str] = mapped_column(String(80), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
