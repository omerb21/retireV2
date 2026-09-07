"""Single canonical write boundary. The caller owns commit/rollback.

Every mutation takes the same per-client lock before reading current data.
PostgreSQL uses a transaction advisory lock and row lock; SQLite takes its
writer reservation with a no-op client UPDATE. Version checks remain mandatory.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductAuditEvent, PensionProductComponent, PensionProductSourceLink
from app.schemas.pension_product import ProductCreate, ProductUpdate, SaveSelected
from app.services.pension_product_reconciliation import reconcile


class PensionProductError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def lock_client(db: Session, client_id: int) -> None:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        key = int.from_bytes(hashlib.sha256(f"pension-products:{client_id}".encode()).digest()[:8], "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    elif dialect == "sqlite":
        db.execute(update(Client).where(Client.client_id == client_id).values(client_id=client_id, updated_at=Client.updated_at))
    else:
        raise PensionProductError("UNSUPPORTED_DATABASE", "מסד הנתונים אינו נתמך", 503)
    client = db.scalar(select(Client).where(Client.client_id == client_id).with_for_update().execution_options(populate_existing=True))
    if client is None:
        raise PensionProductError("CLIENT_NOT_FOUND", "הלקוח לא נמצא", 404)


def get_product(db: Session, client_id: int, product_id: str, *, locked: bool = False) -> PensionProduct:
    query = select(PensionProduct).where(PensionProduct.client_id == client_id, PensionProduct.product_id == product_id)
    if locked:
        query = query.with_for_update().execution_options(populate_existing=True)
    product = db.scalar(query)
    if product is None:
        raise PensionProductError("PRODUCT_NOT_FOUND", "המוצר לא נמצא", 404)
    return product


def component_balances(db: Session, product_id: str) -> dict:
    rows = db.scalars(select(PensionProductComponent).where(PensionProductComponent.product_id == product_id).execution_options(populate_existing=True)).all()
    if len(rows) != 11 or {row.component_code for row in rows} != set(COMPONENT_CODES):
        raise PensionProductError("CANONICAL_SOURCE_INVALID", "נתוני הרכיבים אינם שלמים")
    return {row.component_code: row.balance for row in rows}


def product_response(db: Session, product: PensionProduct) -> dict:
    balances = component_balances(db, product.product_id)
    response = {column.name: getattr(product, column.name) for column in PensionProduct.__table__.columns}
    response["components"] = balances
    response["reconciliation"] = reconcile(balances, product.reported_product_total, product.reported_rewards_total, product.reported_severance_total)
    response["source_history"] = [
        {"checksum": row.checksum, "filename": row.filename, "statement_date": row.statement_date, "diagnostics": row.diagnostics}
        for row in db.scalars(select(PensionProductSourceLink).where(PensionProductSourceLink.client_id == product.client_id, PensionProductSourceLink.product_id == product.product_id).order_by(PensionProductSourceLink.created_at, PensionProductSourceLink.source_link_id))
    ]
    # Decimal strings preserve all 20 digits through JSON and the browser.
    return _json_snapshot(response)


def _json_snapshot(value):
    from datetime import date
    from decimal import Decimal
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_snapshot(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_snapshot(item) for item in value]
    return value


def audit(db: Session, product: PensionProduct, action: str, actor: str) -> None:
    db.add(PensionProductAuditEvent(event_id=uuid4().hex, client_id=product.client_id, product_id=product.product_id, action=action, version=product.version, snapshot=product_response(db, product), actor=actor))


def create_product(db: Session, client_id: int, request: ProductCreate, actor: str) -> PensionProduct:
    lock_client(db, client_id)
    product_id = uuid4().hex
    metadata = request.model_dump()
    metadata["account_reference"] = metadata["account_reference"] or f"MANUAL-{product_id}"
    product = PensionProduct(product_id=product_id, client_id=client_id, source_kind="manual", source_identity=product_id, version=1, created_by=actor, updated_by=actor, **metadata)
    db.add(product)
    db.flush()
    db.add_all([PensionProductComponent(component_id=uuid4().hex, product_id=product_id, component_code=code, balance=0) for code in COMPONENT_CODES])
    db.flush()
    audit(db, product, "create", actor)
    return product


def _update_locked(db: Session, client_id: int, product_id: str, request: ProductUpdate, actor: str) -> PensionProduct:
    product = get_product(db, client_id, product_id, locked=True)
    component_balances(db, product_id)
    if product.version != request.expected_version:
        raise PensionProductError("STALE_PRODUCT_VERSION", "המוצר השתנה. יש לטעון מחדש לפני שמירה")
    values = request.model_dump(exclude={"expected_version", "components", "product_id"})
    values["account_reference"] = values["account_reference"] or product.account_reference
    changed = db.execute(update(PensionProduct).where(PensionProduct.product_id == product_id, PensionProduct.version == request.expected_version).values(**values, version=request.expected_version + 1, updated_by=actor, updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        raise PensionProductError("STALE_PRODUCT_VERSION", "המוצר השתנה. יש לטעון מחדש לפני שמירה")
    for code, balance in request.components.items():
        db.execute(update(PensionProductComponent).where(PensionProductComponent.product_id == product_id, PensionProductComponent.component_code == code).values(balance=balance))
    db.flush()
    db.refresh(product)
    audit(db, product, "save", actor)
    return product


def update_product(db: Session, client_id: int, product_id: str, request: ProductUpdate, actor: str) -> PensionProduct:
    lock_client(db, client_id)
    return _update_locked(db, client_id, product_id, request, actor)


def save_selected(db: Session, client_id: int, request: SaveSelected, actor: str) -> list[PensionProduct]:
    lock_client(db, client_id)
    # Preflight every version before the first write; caller transaction also
    # rolls back every product if any later structural/integrity error occurs.
    for item in sorted(request.products, key=lambda item: item.product_id):
        product = get_product(db, client_id, item.product_id, locked=True)
        if product.version != item.expected_version:
            raise PensionProductError("STALE_PRODUCT_VERSION", "אחד המוצרים השתנה. השמירה לא בוצעה")
    return [_update_locked(db, client_id, item.product_id, item, actor) for item in request.products]


def delete_product(db: Session, client_id: int, product_id: str, expected_version: int, actor: str) -> None:
    lock_client(db, client_id)
    product = get_product(db, client_id, product_id, locked=True)
    if product.version != expected_version:
        raise PensionProductError("STALE_PRODUCT_VERSION", "המוצר השתנה. יש לטעון מחדש לפני מחיקה")
    # No cascade to any downstream object. A downstream FK is RESTRICT/NO ACTION
    # and must be surfaced by the API as an integrity conflict with full rollback.
    audit(db, product, "delete", actor)
    db.flush()
    db.execute(delete(PensionProductComponent).where(PensionProductComponent.product_id == product_id))
    db.delete(product)
    db.flush()
