"""Canonical pension source cutover. Frozen migration implementation.

Historical professional records and raw sources are retained, not dropped.
Online preflight is mandatory. Downgrade is prohibited: reverting schema/code
would reactivate obsolete authority without a verified reverse transformation.
"""
from __future__ import annotations
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision = "d3e9a6b2c410"
down_revision = "c2d8f5a1b309"
branch_labels = None
depends_on = None

COMPONENT_CODES = (
    "פיצויים_מעסיק_נוכחי", "פיצויים_לאחר_התחשבנות",
    "פיצויים_שלא_עברו_התחשבנות", "פיצויים_ממעסיקים_קודמים_רצף_זכויות",
    "פיצויים_ממעסיקים_קודמים_רצף_קצבה", "תגמולי_עובד_עד_2000",
    "תגמולי_עובד_אחרי_2000", "תגמולי_עובד_אחרי_2008_לא_משלמת",
    "תגמולי_מעביד_עד_2000", "תגמולי_מעביד_אחרי_2000",
    "תגמולי_מעביד_אחרי_2008_לא_משלמת",
)

def exact_money(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Inexact legacy money")
    amount = Decimal(value)
    if not amount.is_finite() or abs(amount) >= Decimal("1000000000000000000"):
        raise ValueError("Legacy money out of range")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Legacy money has more than two decimal places")
    return amount.quantize(Decimal("0.01"))

def source_identity(provider_identifier, provider_name, account_reference, source_reference=None):
    provider = provider_identifier or provider_name
    if provider and account_reference:
        identity = ["provider-account", "id" if provider_identifier else "name", provider.strip(), account_reference.strip()]
    elif source_reference:
        identity = ["source", source_reference]
    else:
        raise ValueError("Ambiguous legacy product identity")
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


from decimal import Decimal
from typing import Any



class CutoverConflict(ValueError):
    def __init__(self, conflicts: list[dict]):
        self.conflicts = sorted(conflicts, key=lambda item: (item["client_id"], item["record_id"], item["code"]))
        super().__init__(f"Canonical cutover aborted: {self.conflicts}")


def build_cutover_plan(intakes: list[dict], revisions: list[dict], ledger_values: list[dict]) -> dict[str, Any]:
    conflicts: list[dict] = []
    products: dict[tuple[int, str], dict] = {}
    by_intake: dict[str, dict] = {}
    def conflict(row, code, record_id=None):
        conflicts.append({"client_id": row["client_id"], "record_id": record_id or row.get("intake_id") or row["revision_id"], "code": code})
    for row in sorted(intakes, key=lambda item: (item["client_id"], item["intake_id"])):
        if row["lifecycle_status"] in {"rejected", "superseded"}:
            continue
        # An opaque preserved upload with no authored product values is technical
        # evidence, not a product. Its archive row remains physically untouched.
        if row["record_kind"] == "uploaded_source" and not row.get("declared_component_values") and row.get("declared_total_balance_amount") is None and not row.get("declared_account_reference"):
            continue
        try:
            identity = source_identity(None, row.get("declared_provider_name"), row.get("declared_account_reference") or "", row.get("manual_technical_reference") if row["record_kind"] == "manual" else None)
        except ValueError:
            conflict(row, "ambiguous_product_identity")
            continue
        key = row["client_id"], identity
        if key in products:
            conflict(row, "competing_active_intakes")
            conflict(products[key]["legacy_intake"], "competing_active_intakes")
            continue
        components = dict.fromkeys(COMPONENT_CODES, Decimal("0.00"))
        mapped = set()
        diagnostics = []
        for index, item in enumerate(row.get("declared_component_values") or []):
            code = item.get("code") or item.get("label")
            if code not in COMPONENT_CODES:
                diagnostics.append({"code": "unmapped_legacy_component", "index": index, "source": item})
                continue
            if code in mapped:
                conflict(row, "duplicate_canonical_component")
                continue
            try:
                components[code] = exact_money(item["value"])
                mapped.add(code)
            except (ValueError, KeyError):
                conflict(row, "invalid_canonical_component_amount")
        try:
            total = None if row.get("declared_total_balance_amount") is None else exact_money(row["declared_total_balance_amount"])
        except ValueError:
            conflict(row, "invalid_reported_product_total")
            continue
        product = {
            "client_id": row["client_id"], "source_identity": identity,
            "legacy_intake": row, "components": components, "mapped_codes": mapped,
            "reported_product_total": total,
            # Legacy generic contribution/severance values were components, not
            # proven summary fields. They cannot populate these control totals.
            "reported_rewards_total": None, "reported_severance_total": None,
            "diagnostics": diagnostics, "legacy_revision_ids": [],
        }
        products[key] = product
        by_intake[row["intake_id"]] = product
    # Current leaf is determined by ancestry, not arbitrary timestamp ordering.
    parent_ids = {row["predecessor_revision_id"] for row in revisions if row.get("predecessor_revision_id")}
    leaves: dict[tuple[int, str], list[dict]] = {}
    for row in revisions:
        if row["revision_id"] not in parent_ids:
            leaves.setdefault((row["client_id"], row["subject_id"]), []).append(row)
    for _, rows in sorted(leaves.items()):
        if len(rows) != 1:
            for row in rows:
                conflict(row, "competing_ledger_leaves", row["revision_id"])
            continue
        row = rows[0]
        if row["state"] == "superseded":
            continue
        product = by_intake.get(row["intake_id"])
        if product is None or product["client_id"] != row["client_id"]:
            conflict(row, "ledger_without_unique_active_source", row["revision_id"])
            continue
        try:
            ledger_identity = source_identity(None, row["provider_name"], row["account_reference"])
        except ValueError:
            conflict(row, "ambiguous_ledger_identity", row["revision_id"])
            continue
        if ledger_identity != product["source_identity"]:
            conflict(row, "ledger_source_identity_conflict", row["revision_id"])
        total = row.get("effective_total_value")
        if total is not None and exact_money(total) != product["reported_product_total"]:
            conflict(row, "ledger_source_total_conflict", row["revision_id"])
        seen_codes = set()
        for value in ledger_values:
            if value["revision_id"] != row["revision_id"]:
                continue
            code = value.get("original_code") or value.get("original_label")
            if code not in COMPONENT_CODES:
                product["diagnostics"].append({"code": "unmapped_legacy_ledger_value", "source": value})
                continue
            if code in seen_codes:
                conflict(row, "duplicate_ledger_canonical_component", row["revision_id"])
                continue
            seen_codes.add(code)
            amount = value.get("effective_value")
            if amount is None:
                product["diagnostics"].append({"code": "missing_legacy_ledger_value", "source": value})
                continue
            amount = exact_money(amount)
            if code in product["mapped_codes"] and product["components"][code] != amount:
                conflict(row, "ledger_source_component_conflict", row["revision_id"])
            else:
                product["components"][code] = amount
        product["legacy_revision_ids"].append(row["revision_id"])
    if conflicts:
        raise CutoverConflict(conflicts)
    planned = [products[key] for key in sorted(products)]
    return {"products": planned, "counts": {"products": len(planned), "components": 11 * len(planned), "source_links": len(planned), "conflicts": 0, "unmapped_values": sum(len(item["diagnostics"]) for item in planned)}}


def _create_schema():
    op.create_table('pension_products',
    sa.Column('product_id', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('source_kind', sa.String(length=16), nullable=False),
    sa.Column('source_identity', sa.String(length=64), nullable=False),
    sa.Column('provider_name', sa.String(length=255), nullable=True),
    sa.Column('provider_identifier', sa.String(length=128), nullable=True),
    sa.Column('product_name', sa.String(length=255), nullable=False),
    sa.Column('product_type', sa.String(length=255), nullable=False),
    sa.Column('account_reference', sa.String(length=255), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('statement_date', sa.Date(), nullable=True),
    sa.Column('historical_employers', sa.JSON(), nullable=False),
    sa.Column('reported_product_total', sa.Numeric(20, 2).with_variant(sa.String(22), "sqlite"), nullable=True),
    sa.Column('reported_rewards_total', sa.Numeric(20, 2).with_variant(sa.String(22), "sqlite"), nullable=True),
    sa.Column('reported_severance_total', sa.Numeric(20, 2).with_variant(sa.String(22), "sqlite"), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('updated_by', sa.String(length=128), nullable=False),
    sa.CheckConstraint("source_kind IN ('manual','imported')", name='ck_pension_product_kind'),
    sa.CheckConstraint('version > 0', name='ck_pension_product_version'),
    sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ),
    sa.PrimaryKeyConstraint('product_id'),
    sa.UniqueConstraint('client_id', 'source_identity', name='uq_pension_product_identity')
    )
    op.create_index(op.f('ix_pension_products_client_id'), 'pension_products', ['client_id'], unique=False)
    op.create_table('pension_product_components',
    sa.Column('component_id', sa.String(length=64), nullable=False),
    sa.Column('product_id', sa.String(length=64), nullable=False),
    sa.Column('component_code', sa.String(length=128), nullable=False),
    sa.Column('balance', sa.Numeric(20, 2).with_variant(sa.String(22), "sqlite"), nullable=False),
    sa.CheckConstraint("component_code IN ('פיצויים_מעסיק_נוכחי','פיצויים_לאחר_התחשבנות','פיצויים_שלא_עברו_התחשבנות','פיצויים_ממעסיקים_קודמים_רצף_זכויות','פיצויים_ממעסיקים_קודמים_רצף_קצבה','תגמולי_עובד_עד_2000','תגמולי_עובד_אחרי_2000','תגמולי_עובד_אחרי_2008_לא_משלמת','תגמולי_מעביד_עד_2000','תגמולי_מעביד_אחרי_2000','תגמולי_מעביד_אחרי_2008_לא_משלמת')", name='ck_pension_product_component_code'),
    sa.ForeignKeyConstraint(['product_id'], ['pension_products.product_id'], ),
    sa.PrimaryKeyConstraint('component_id'),
    sa.UniqueConstraint('product_id', 'component_code', name='uq_pension_product_component')
    )
    op.create_index(op.f('ix_pension_product_components_product_id'), 'pension_product_components', ['product_id'], unique=False)
    op.create_table('pension_product_source_links',
    sa.Column('source_link_id', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.String(length=64), nullable=False),
    sa.Column('source_identity', sa.String(length=64), nullable=False),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=True),
    sa.Column('raw_content', sa.LargeBinary(), nullable=True),
    sa.Column('legacy_intake_id', sa.String(length=64), nullable=True),
    sa.Column('statement_date', sa.Date(), nullable=True),
    sa.Column('diagnostics', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ),
    sa.ForeignKeyConstraint(['legacy_intake_id'], ['m02_intake_records.intake_id'], ),
    sa.PrimaryKeyConstraint('source_link_id'),
    sa.UniqueConstraint('client_id', 'source_identity', 'checksum', name='uq_pension_source_replay')
    )
    op.create_index(op.f('ix_pension_product_source_links_product_id'), 'pension_product_source_links', ['product_id'], unique=False)
    op.create_table('pension_product_audit_events',
    sa.Column('event_id', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.String(length=64), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('actor', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ),
    sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_pension_product_audit_events_product_id'), 'pension_product_audit_events', ['product_id'], unique=False)

def _jsonable(value):
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in (sorted(value) if isinstance(value, set) else value)]
    return value

def _id(value):
    return uuid5(NAMESPACE_URL, "retireV2:recovery001:" + value).hex

def upgrade():
    if op.get_context().as_sql:
        raise RuntimeError("CANONICAL_CUTOVER_REQUIRES_ONLINE_PREFLIGHT")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # pysqlite otherwise autocommits DDL even inside SQLAlchemy autobegin.
        if not bind.connection.driver_connection.in_transaction:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    elif bind.dialect.name == "postgresql":
        bind.exec_driver_sql("LOCK TABLE m02_intake_records, m05_ledger_revisions, m05_ledger_values IN SHARE ROW EXCLUSIVE MODE")
    else:
        raise RuntimeError("Unsupported cutover database")
    legacy = sa.MetaData()
    def rows(name):
        table = sa.Table(name, legacy, autoload_with=bind)
        return [dict(row) for row in bind.execute(sa.select(table)).mappings()]
    plan = build_cutover_plan(rows("m02_intake_records"), rows("m05_ledger_revisions"), rows("m05_ledger_values"))
    _create_schema()
    schema = sa.MetaData()
    tables = {name: sa.Table(name, schema, autoload_with=bind) for name in ("pension_products", "pension_product_components", "pension_product_source_links", "pension_product_audit_events")}
    def money(value):
        return None if value is None else format(value, ".2f") if bind.dialect.name == "sqlite" else value
    for product in plan["products"]:
        row = product["legacy_intake"]
        product_id = _id(str(product["client_id"]) + ":" + product["source_identity"])
        bind.execute(tables["pension_products"].insert().values(
            product_id=product_id, client_id=product["client_id"],
            source_kind="manual" if row["record_kind"] == "manual" else "imported",
            source_identity=product["source_identity"],
            provider_name=row.get("declared_provider_name"), provider_identifier=None,
            product_name=row.get("product_name") or "שם תכנית לא נמסר",
            product_type=row.get("declared_product_type") or "סוג מוצר לא נמסר",
            account_reference=row.get("declared_account_reference") or row["manual_technical_reference"],
            start_date=row.get("declared_start_date"), statement_date=row.get("declared_statement_date"),
            historical_employers=[],
            reported_product_total=money(product["reported_product_total"]),
            reported_rewards_total=None, reported_severance_total=None,
            version=1, created_by="migration:d3e9a6b2c410", updated_by="migration:d3e9a6b2c410",
        ))
        for code, value in product["components"].items():
            bind.execute(tables["pension_product_components"].insert().values(
                component_id=_id(product_id + ":" + code), product_id=product_id,
                component_code=code, balance=money(value)))
        preserved = _jsonable(product)
        checksum = hashlib.sha256(json.dumps(preserved, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        bind.execute(tables["pension_product_source_links"].insert().values(
            source_link_id=_id(product_id + ":source"), client_id=product["client_id"],
            product_id=product_id, source_identity=product["source_identity"], checksum=checksum,
            filename=None, raw_content=None, legacy_intake_id=row["intake_id"],
            statement_date=row.get("declared_statement_date"),
            diagnostics=[{"code": "legacy_cutover_snapshot", "snapshot": preserved}],
        ))
        bind.execute(tables["pension_product_audit_events"].insert().values(
            event_id=_id(product_id + ":audit"), client_id=product["client_id"],
            product_id=product_id, action="migration", version=1,
            snapshot={"preflight": preserved, "counts": plan["counts"]}, actor="migration:d3e9a6b2c410",
        ))
    for table in ("pension_product_source_links", "pension_product_audit_events"):
        if bind.dialect.name == "sqlite":
            for action in ("UPDATE", "DELETE"):
                op.execute(f"CREATE TRIGGER trg_{table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'canonical_evidence_immutable'); END")
        else:
            op.execute(f"CREATE FUNCTION {table}_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'canonical_evidence_immutable'; END; $$")
            op.execute(f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION {table}_immutable()")
    # Physical archive retention is not permission to create more professional
    # revisions, even through an old binary or direct SQL after cutover.
    archive_tables = (
        "pension_holding", "pension_analysis_record",
        "m02_intake_records", "m03_review_revisions", "m03_annotations",
        "m04_classification_subjects", "m04_classification_revisions", "m04_component_decisions",
        "m05_ledger_subjects", "m05_candidate_links", "m05_ledger_revisions",
        "m05_ledger_values", "m05_adjustment_evidence",
    )
    if bind.dialect.name == "postgresql":
        op.execute("CREATE FUNCTION legacy_pension_archive_only() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY'; END; $$")
    for table in archive_tables:
        if bind.dialect.name == "sqlite":
            for action in ("INSERT", "UPDATE", "DELETE"):
                op.execute(f"CREATE TRIGGER trg_{table}_archive_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'LEGACY_PENSION_WORKFLOW_ARCHIVE_ONLY'); END")
        else:
            op.execute(f"CREATE TRIGGER trg_{table}_archive BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION legacy_pension_archive_only()")
    print("CANONICAL_CUTOVER_COUNTS=" + json.dumps(plan["counts"], sort_keys=True))

def downgrade():
    raise RuntimeError("CANONICAL_CUTOVER_DOWNGRADE_PROHIBITED: restore a verified pre-cutover backup; do not reactivate legacy authority")
