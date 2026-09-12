"""Canonical conversion records; no legacy source/destination authority."""
from sqlalchemy import Column, Table, String, Integer, ForeignKey, Date, DateTime, JSON, Boolean, UniqueConstraint, CheckConstraint, func
from sqlalchemy import MetaData, Numeric
from sqlalchemy.types import TypeDecorator

metadata = MetaData()
class ExactMoney(TypeDecorator):
    impl = Numeric(20, 2)
    cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(String(22) if dialect.name == "sqlite" else Numeric(20, 2))

Table("clients", metadata, Column("client_id", Integer, primary_key=True))
Table("pension_products", metadata, Column("product_id", String(64), primary_key=True))
Table("pension_product_components", metadata, Column("component_id", String(64), primary_key=True))


def identity(name):
    return Column(name, String(64), primary_key=True)


def client():
    return Column("client_id", Integer, ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)


def created():
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now())


batches = Table("canonical_conversion_batches", metadata,
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

conversions = Table("canonical_conversions", metadata,
    identity("conversion_id"), client(),
    Column("batch_id", String(64), ForeignKey("canonical_conversion_batches.batch_id", ondelete="RESTRICT"), nullable=False),
    Column("destination_type", String(16), nullable=False), Column("tax_treatment", String(32), nullable=False),
    Column("converted_amount", ExactMoney(), nullable=False), Column("status", String(16), nullable=False),
    Column("version", Integer, nullable=False), created(), Column("reversed_at", DateTime(timezone=True)),
    CheckConstraint("status IN ('active','reversed')", name="ck_canonical_conversion_status"),
    CheckConstraint("version > 0", name="ck_canonical_conversion_version"),
    CheckConstraint("(destination_type = 'pension' AND tax_treatment IN ('taxable','exempt')) OR (destination_type = 'capital' AND tax_treatment IN ('exempt','capital_gains'))", name="ck_canonical_conversion_tax"))

allocations = Table("canonical_conversion_allocations", metadata,
    identity("allocation_id"),
    Column("conversion_id", String(64), ForeignKey("canonical_conversions.conversion_id", ondelete="RESTRICT"), nullable=False),
    Column("source_product_id", String(64), ForeignKey("pension_products.product_id", ondelete="RESTRICT"), nullable=False),
    Column("source_component_id", String(64), ForeignKey("pension_product_components.component_id", ondelete="RESTRICT"), nullable=False),
    Column("component_code_snapshot", String(128), nullable=False), Column("amount", ExactMoney(), nullable=False),
    Column("source_balance_before", ExactMoney(), nullable=False), Column("source_balance_after", ExactMoney(), nullable=False),
    Column("tax_treatment", String(32), nullable=False), Column("matrix_version", String(128), nullable=False),
    UniqueConstraint("conversion_id", "source_component_id", name="uq_canonical_allocation_component"))

pensions = Table("canonical_pension_destinations", metadata,
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

reversals = Table("canonical_conversion_reversals", metadata,
    identity("reversal_id"), client(),
    Column("conversion_id", String(64), ForeignKey("canonical_conversions.conversion_id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("idempotency_key", String(128), nullable=False), Column("request_fingerprint", String(64), nullable=False),
    Column("expected_conversion_version", Integer, nullable=False), Column("reason", String(1024), nullable=False),
    Column("actor", String(128), nullable=False), Column("result", JSON, nullable=False), created(),
    UniqueConstraint("client_id", "idempotency_key", name="uq_canonical_reversal_key"))


from alembic import op
import sqlalchemy as sa
from decimal import Decimal

revision = "f5a1c8d4e632"
down_revision = "e4f0b7c3d521"
branch_labels = None
depends_on = None
NEW_TABLES = (batches, conversions, allocations, pensions, reversals)


def install_conversion_guards(connection, tables):
    """Database-enforced history retention, independent of API reachability."""
    immutable = {"canonical_conversion_allocations", "canonical_conversion_reversals"}
    mutable = {
        "canonical_conversion_batches": {"result"},
        "canonical_conversions": {"status", "version", "reversed_at"},
        "canonical_pension_destinations": {"status", "version", "reversed_at"},
        "capital_asset": {"lifecycle_status", "updated_at"},
    }
    for table in tables:
        name = table.name
        fields = [c.name for c in table.columns if c.name not in mutable.get(name, set())]
        archive = "OLD.origin_kind = 'canonical_component_conversion'" if name == "capital_asset" else "1=1"
        if connection.dialect.name == "postgresql":
            comparisons = " OR ".join(f'to_jsonb(NEW."{field}") IS DISTINCT FROM to_jsonb(OLD."{field}")' for field in fields)
            update_bad = "TRUE" if name in immutable else "(" + comparisons + ")"
            if name == "canonical_conversion_batches":
                update_bad += " OR OLD.result::jsonb <> '{}'::jsonb"
            if name in {"canonical_conversions", "canonical_pension_destinations"}:
                update_bad += " OR OLD.status <> 'active' OR NEW.status <> 'reversed' OR NEW.version <> OLD.version + 1 OR NEW.reversed_at IS NULL"
            if name == "capital_asset":
                update_bad = f"(({archive}) AND {update_bad}) OR NEW.origin_kind IS DISTINCT FROM OLD.origin_kind OR NEW.conversion_id IS DISTINCT FROM OLD.conversion_id"
            fn = "guard_" + name + "_canonical"
            connection.exec_driver_sql(f"""CREATE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF TG_OP = 'DELETE' THEN
                    IF {archive} THEN RAISE EXCEPTION 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'; END IF;
                    RETURN OLD;
                  END IF;
                  IF {update_bad} THEN RAISE EXCEPTION 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'; END IF;
                  RETURN NEW;
                END $$""")
            connection.exec_driver_sql(f"CREATE TRIGGER trg_{name}_canonical BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION {fn}()")
        else:
            comparisons = " OR ".join(f'NEW."{field}" IS NOT OLD."{field}"' for field in fields)
            update_bad = "1=1" if name in immutable else "(" + comparisons + ")"
            if name == "canonical_conversion_batches":
                update_bad += " OR OLD.result <> '{}'"
            if name in {"canonical_conversions", "canonical_pension_destinations"}:
                update_bad += " OR OLD.status <> 'active' OR NEW.status <> 'reversed' OR NEW.version <> OLD.version + 1 OR NEW.reversed_at IS NULL"
            if name == "capital_asset":
                update_bad = f"(({archive}) AND {update_bad}) OR NEW.origin_kind IS NOT OLD.origin_kind OR NEW.conversion_id IS NOT OLD.conversion_id"
            connection.exec_driver_sql(f"""CREATE TRIGGER trg_{name}_canonical_delete BEFORE DELETE ON {name}
                WHEN {archive} BEGIN SELECT RAISE(ABORT, 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'); END""")
            connection.exec_driver_sql(f"""CREATE TRIGGER trg_{name}_canonical_update BEFORE UPDATE ON {name}
                WHEN {update_bad} BEGIN SELECT RAISE(ABORT, 'CANONICAL_CONVERSION_HISTORY_IMMUTABLE'); END""")


def upgrade():
    bind = op.get_bind()
    # PostgreSQL widens NUMERIC without a float or text intermediary.
    if bind.dialect.name == "postgresql":
        op.alter_column("capital_asset", "known_value_amount", existing_type=sa.Numeric(14, 2),
                        type_=sa.Numeric(20, 2), existing_nullable=True)
    elif bind.dialect.name == "sqlite":
        # Old SQLite affinity is not exact-money authority. Refuse anomalous
        # legacy values rather than silently "repairing" their precision.
        for value in bind.execute(sa.text("SELECT known_value_amount FROM capital_asset WHERE known_value_amount IS NOT NULL")).scalars():
            amount = Decimal(str(value))
            if abs(amount) >= Decimal("1000000000000") or amount != amount.quantize(Decimal("0.01")):
                raise RuntimeError("SQLITE_LEGACY_MONEY_NOT_EXACTLY_REPRESENTABLE")
        with op.batch_alter_table("capital_asset") as batch:
            batch.alter_column("known_value_amount", existing_type=sa.Numeric(14, 2), type_=sa.String(22), existing_nullable=True)
    else:
        raise RuntimeError("UNSUPPORTED_DATABASE")
    for table in NEW_TABLES:
        table.create(bind)
    with op.batch_alter_table("capital_asset") as batch:
        batch.add_column(sa.Column("origin_kind", sa.String(40), nullable=False, server_default="manual"))
        batch.add_column(sa.Column("conversion_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("tax_treatment", sa.String(32), nullable=True))
        batch.create_foreign_key("fk_capital_asset_canonical_conversion", "canonical_conversions", ["conversion_id"], ["conversion_id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_capital_asset_canonical_conversion", ["conversion_id"])
    capital = sa.Table("capital_asset", sa.MetaData(), autoload_with=bind)
    install_conversion_guards(bind, [*NEW_TABLES, capital])


def downgrade():
    bind = op.get_bind()
    # All guards precede the first DDL/data mutation.
    for value in bind.execute(sa.text("SELECT known_value_amount FROM capital_asset WHERE known_value_amount IS NOT NULL")).scalars():
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) >= Decimal("1000000000000") or amount != amount.quantize(Decimal("0.01")):
            raise RuntimeError("CAPITAL_ASSET_DOWNGRADE_PRECISION_LOSS")
    if any(bind.execute(sa.select(sa.func.count()).select_from(table)).scalar_one() for table in NEW_TABLES):
        raise RuntimeError("CANONICAL_CONVERSION_HISTORY_DOWNGRADE_PROHIBITED")
    for name in [table.name for table in NEW_TABLES] + ["capital_asset"]:
        if bind.dialect.name == "postgresql":
            bind.exec_driver_sql(f"DROP TRIGGER trg_{name}_canonical ON {name}")
            bind.exec_driver_sql(f"DROP FUNCTION guard_{name}_canonical()")
        else:
            bind.exec_driver_sql(f"DROP TRIGGER trg_{name}_canonical_update")
            bind.exec_driver_sql(f"DROP TRIGGER trg_{name}_canonical_delete")
    with op.batch_alter_table("capital_asset") as batch:
        batch.drop_constraint("fk_capital_asset_canonical_conversion", type_="foreignkey")
        batch.drop_constraint("uq_capital_asset_canonical_conversion", type_="unique")
        batch.drop_column("tax_treatment")
        batch.drop_column("conversion_id")
        batch.drop_column("origin_kind")
        batch.alter_column("known_value_amount", existing_type=sa.Numeric(20, 2) if bind.dialect.name == "postgresql" else sa.String(22),
                           type_=sa.Numeric(14, 2), existing_nullable=True,
                           postgresql_using="known_value_amount::numeric(14,2)")
    for table in reversed(NEW_TABLES):
        table.drop(bind)
