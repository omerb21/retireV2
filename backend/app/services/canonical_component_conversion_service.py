"""Single canonical conversion transaction boundary; caller commits/rolls back."""
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
import json
from uuid import uuid4

from sqlalchemy import select, update, inspect, Table, MetaData, and_
from sqlalchemy.orm import Session

from app.models.canonical_conversion import batches, conversions, allocations, pensions, reversals
from app.models.client_profile import ClientProfile
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.models.retirement_facts import CapitalAsset
from app.schemas.pension_product import exact_money
from app.services.pension_product_service import PensionProductError, lock_client, get_product, component_balances, audit, _json_snapshot
from app.services.canonical_conversion_matrix import MATRIX_VERSION, destinations, tax_for
from app.services.annuity_coefficient_service import coefficient


def fail(code, message="הפעולה לא בוצעה; יש לבדוק את הנתונים ולטעון מחדש", status=409):
    raise PensionProductError(code, message, status)


def fingerprint(request):
    return hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def replay(db, table, client_id, request):
    row = db.execute(select(table).where(table.c.client_id == client_id, table.c.idempotency_key == request.idempotency_key)).mappings().first()
    if row:
        if row["request_fingerprint"] != fingerprint(request):
            fail("IDEMPOTENCY_CONFLICT", "מפתח הפעולה כבר שימש לבקשה אחרת")
        return row["result"]
    return None


def _preflight(db, client_id, request):
    product = get_product(db, client_id, request.product_id, locked=True)
    if product.version != request.expected_product_version:
        fail("STALE_PRODUCT_VERSION")
    component_balances(db, product.product_id)
    rows = db.scalars(select(PensionProductComponent).where(PensionProductComponent.product_id == product.product_id)
        .order_by(PensionProductComponent.component_id).with_for_update().execution_options(populate_existing=True)).all()
    by_id = {row.component_id: row for row in rows}
    selected, skipped = [], []
    if request.whole_product:
        if request.selections:
            fail("INVALID_CONVERSION_SELECTION", status=422)
        for row in rows:
            if row.balance <= 0:
                continue
            if request.destination_type not in destinations(row.component_code, product.product_type):
                skipped.append({"component_id": row.component_id, "component_code": row.component_code, "reason": "INVALID_COMPONENT_DESTINATION"})
            else:
                selected.append((row, row.balance))
    else:
        if not request.selections or len({s.component_id for s in request.selections}) != len(request.selections):
            fail("INVALID_CONVERSION_SELECTION", status=422)
        for item in request.selections:
            if item.component_code in ("reported_product_total", "reported_rewards_total", "reported_severance_total", "product_discrepancy", "reconciliation"):
                fail("RECONCILIATION_VALUE_NOT_CONVERTIBLE", status=422)
            if item.component_code not in COMPONENT_CODES:
                fail("NON_CANONICAL_COMPONENT", status=422)
            row = by_id.get(item.component_id)
            if row is None or row.component_code != item.component_code:
                fail("CONVERSION_SOURCE_MISMATCH", status=422)
            tax_for(row.component_code, product.product_type, request.destination_type)
            try:
                amount = row.balance if item.amount is None else exact_money(item.amount)
            except ValueError:
                fail("INVALID_CONVERSION_AMOUNT", status=422)
            if amount <= 0:
                fail("INVALID_CONVERSION_AMOUNT", status=422)
            if amount > row.balance:
                fail("OVER_CONVERSION", status=422)
            selected.append((row, amount))
    if not selected:
        fail("NO_ELIGIBLE_COMPONENTS", "אין רכיבים חיוביים הזכאים ליעד שנבחר", 422)
    groups = {}
    for row, amount in selected:
        tax = tax_for(row.component_code, product.product_type, request.destination_type)
        groups.setdefault(tax, []).append({"component_id": row.component_id, "component_code": row.component_code,
            "amount": amount, "before": row.balance, "after": exact_money(row.balance - amount)})
    coef = None
    if request.destination_type == "pension":
        if request.pension is None:
            fail("PENSION_INPUTS_REQUIRED", status=422)
        profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
        coef = coefficient(product, profile, **request.pension.model_dump())
    elif request.pension is not None:
        fail("INVALID_DESTINATION_INPUTS", status=422)
    result = []
    for tax, items in sorted(groups.items()):
        total = exact_money(sum((item["amount"] for item in items), Decimal("0.00")))
        group = {"tax_treatment": tax, "amount": total, "allocations": items, "coefficient": coef}
        if coef:
            with localcontext() as context:
                context.prec = 80
                group["monthly_display_amount"] = exact_money((total / Decimal(coef["annuity_factor"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
        result.append(group)
    return product, result, skipped


def preview(db, client_id, request):
    lock_client(db, client_id)
    product, groups, skipped = _preflight(db, client_id, request)
    return _json_snapshot({"product_id": product.product_id, "product_version": product.version,
        "matrix_version": MATRIX_VERSION, "groups": groups, "skipped": skipped})


def _bump(db, product, actor):
    version = product.version
    changed = db.execute(update(PensionProduct).where(PensionProduct.product_id == product.product_id,
        PensionProduct.version == version).values(version=version + 1, updated_by=actor, updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        fail("STALE_PRODUCT_VERSION")
    db.flush()
    db.refresh(product)


def execute(db: Session, client_id, request, actor):
    lock_client(db, client_id)
    old = replay(db, batches, client_id, request)
    if old is not None:
        return old
    product, groups, skipped = _preflight(db, client_id, request)
    batch_id = uuid4().hex
    db.execute(batches.insert().values(batch_id=batch_id, client_id=client_id, source_product_id=product.product_id,
        destination_type=request.destination_type, matrix_version=MATRIX_VERSION, idempotency_key=request.idempotency_key,
        request_fingerprint=fingerprint(request), expected_product_version=product.version, status="completed",
        effective_date=request.effective_date, actor=actor, result={}))
    output = []
    for group in groups:
        cid = uuid4().hex
        db.execute(conversions.insert().values(conversion_id=cid, batch_id=batch_id, client_id=client_id,
            destination_type=request.destination_type, tax_treatment=group["tax_treatment"], converted_amount=group["amount"], status="active", version=1))
        for item in group["allocations"]:
            db.execute(allocations.insert().values(allocation_id=uuid4().hex, conversion_id=cid,
                source_product_id=product.product_id, source_component_id=item["component_id"], component_code_snapshot=item["component_code"],
                amount=item["amount"], source_balance_before=item["before"], source_balance_after=item["after"],
                tax_treatment=group["tax_treatment"], matrix_version=MATRIX_VERSION))
            db.execute(update(PensionProductComponent).where(PensionProductComponent.component_id == item["component_id"]).values(balance=item["after"]))
        if request.destination_type == "pension":
            destination_id = uuid4().hex
            coef = group["coefficient"]
            db.execute(pensions.insert().values(pension_destination_id=destination_id, client_id=client_id, conversion_id=cid,
                name=product.product_name, description="קצבה מהמרת רכיבים קנוניים", converted_balance=group["amount"],
                effective_date=request.effective_date, pension_start_date=request.pension.pension_start_date,
                annuity_factor_text=coef["annuity_factor"], coefficient_source=coef["source"], coefficient_source_keys=coef["lookup_keys"],
                coefficient_notes=coef["notes"], coefficient_catalog_version=coef["catalog_version"], coefficient_fallback_used=coef["fallback_used"],
                monthly_numerator=format(group["amount"], ".2f"), monthly_denominator=coef["annuity_factor"],
                monthly_display_amount=group["monthly_display_amount"], tax_treatment=group["tax_treatment"], status="active", version=1))
        else:
            asset = CapitalAsset(client_id=client_id, asset_category="other", asset_description=product.product_name,
                known_value_amount=group["amount"], value_as_of_date=request.effective_date, origin_kind="canonical_component_conversion",
                conversion_id=cid, tax_treatment=group["tax_treatment"], lifecycle_status="current", source_status="planner entered",
                verification_state="verification not applicable")
            db.add(asset)
            db.flush()
            destination_id = asset.id
        output.append({"conversion_id": cid, "destination_id": destination_id, "version": 1, "status": "active", **group})
    _bump(db, product, actor)
    audit(db, product, "conversion", actor, operation={"batch_id": batch_id, "matrix_version": MATRIX_VERSION,
        "allocations": [item for group in groups for item in group["allocations"]]})
    result = _json_snapshot({"batch_id": batch_id, "product_id": product.product_id, "product_version": product.version,
        "matrix_version": MATRIX_VERSION, "conversions": output, "skipped": skipped})
    db.execute(batches.update().where(batches.c.batch_id == batch_id).values(result=result))
    return result


def history(db, client_id, product_id=None):
    query = select(conversions, batches.c.source_product_id, batches.c.effective_date, batches.c.actor).join(batches, conversions.c.batch_id == batches.c.batch_id).where(conversions.c.client_id == client_id)
    if product_id:
        query = query.where(batches.c.source_product_id == product_id)
    result = []
    for row in db.execute(query.order_by(conversions.c.created_at, conversions.c.conversion_id)).mappings():
        item = dict(row)
        item["allocations"] = [dict(a) for a in db.execute(select(allocations).where(allocations.c.conversion_id == row["conversion_id"])).mappings()]
        item["pension"] = None
        item["capital_asset"] = None
        if row["destination_type"] == "pension":
            found = db.execute(select(pensions).where(pensions.c.conversion_id == row["conversion_id"])).mappings().one()
            item["pension"] = dict(found)
        else:
            asset = db.scalar(select(CapitalAsset).where(CapitalAsset.conversion_id == row["conversion_id"], CapitalAsset.client_id == client_id))
            if asset is None:
                fail("CONVERSION_DESTINATION_MISMATCH")
            item["capital_asset"] = {"id": asset.id, "known_value_amount": asset.known_value_amount,
                "origin_kind": asset.origin_kind, "conversion_id": asset.conversion_id,
                "tax_treatment": asset.tax_treatment, "lifecycle_status": asset.lifecycle_status}
        item["reversals"] = [dict(r) for r in db.execute(select(reversals).where(reversals.c.conversion_id == row["conversion_id"])).mappings()]
        result.append(item)
    return _json_snapshot(result)


def _downstream_used(db, target_table, target_row):
    # No downstream policy is inferred. Any external FK consumer blocks reversal.
    owned = {batches.name, conversions.name, allocations.name, pensions.name, reversals.name, "capital_asset"}
    inspector = inspect(db.connection())
    for name in inspector.get_table_names():
        if name in owned:
            continue
        for fk in inspector.get_foreign_keys(name):
            if fk["referred_table"] != target_table:
                continue
            table = Table(name, MetaData(), autoload_with=db.connection())
            predicates = [table.c[local] == target_row[remote] for local, remote in zip(fk["constrained_columns"], fk["referred_columns"])]
            if db.execute(select(table).where(and_(*predicates)).limit(1)).first():
                return True
    return False


def reverse(db, client_id, conversion_id, request, actor):
    lock_client(db, client_id)
    old = replay(db, reversals, client_id, request)
    if old is not None:
        if old["conversion_id"] != conversion_id:
            fail("IDEMPOTENCY_CONFLICT")
        return old
    initial = db.execute(select(conversions, batches.c.source_product_id).join(batches,
        conversions.c.batch_id == batches.c.batch_id).where(conversions.c.client_id == client_id,
        conversions.c.conversion_id == conversion_id)).mappings().first()
    if initial is None:
        fail("CONVERSION_SOURCE_MISMATCH", status=404)
    # The unlocked identification read grants no authority. Lock order is
    # client -> product -> conversion -> destination, then reread every value.
    product = get_product(db, client_id, initial["source_product_id"], locked=True)
    conversion = db.execute(select(conversions).where(conversions.c.conversion_id == conversion_id,
        conversions.c.client_id == client_id).with_for_update()).mappings().one()
    if conversion["status"] != "active":
        fail("CONVERSION_ALREADY_REVERSED")
    if conversion["version"] != request.expected_conversion_version:
        fail("STALE_CONVERSION_VERSION")
    if product.version != request.expected_product_version:
        fail("STALE_PRODUCT_VERSION")
    source = db.execute(select(allocations).where(allocations.c.conversion_id == conversion_id).order_by(allocations.c.source_component_id)).mappings().all()
    component_balances(db, product.product_id)
    restores = []
    before_after = []
    for allocation in source:
        row = db.scalar(select(PensionProductComponent).where(PensionProductComponent.product_id == product.product_id,
            PensionProductComponent.component_id == allocation["source_component_id"]).with_for_update().execution_options(populate_existing=True))
        if row is None or allocation["source_product_id"] != product.product_id or row.component_code != allocation["component_code_snapshot"]:
            fail("CONVERSION_SOURCE_MISMATCH")
        restored = exact_money(row.balance + allocation["amount"])
        restores.append((row, restored))
        before_after.append({"component_id": row.component_id, "component_code": row.component_code,
            "amount": allocation["amount"], "before": row.balance, "after": restored})
    if not source or sum((a["amount"] for a in source), Decimal(0)) != conversion["converted_amount"]:
        fail("CONVERSION_SOURCE_MISMATCH")
    capital = None
    if conversion["destination_type"] == "pension":
        destination = db.execute(select(pensions).where(pensions.c.conversion_id == conversion_id,
            pensions.c.client_id == client_id).with_for_update()).mappings().one()
        if destination["status"] != "active" or destination["converted_balance"] != conversion["converted_amount"]:
            fail("CONVERSION_DESTINATION_MISMATCH")
        used = _downstream_used(db, pensions.name, destination)
    else:
        capital = db.scalar(select(CapitalAsset).where(CapitalAsset.conversion_id == conversion_id,
            CapitalAsset.client_id == client_id).with_for_update().execution_options(populate_existing=True))
        if capital is None or capital.origin_kind != "canonical_component_conversion" or capital.lifecycle_status != "current" or capital.known_value_amount != conversion["converted_amount"]:
            fail("CONVERSION_DESTINATION_MISMATCH")
        used = _downstream_used(db, "capital_asset", {c.name: getattr(capital, c.name) for c in CapitalAsset.__table__.columns})
    if used or _downstream_used(db, conversions.name, conversion):
        fail("DESTINATION_HAS_DOWNSTREAM_USAGE", "היעד משמש תהליך המשך; מדיניות הביטול דורשת החלטת בעלים")
    now = datetime.now(timezone.utc)
    for row, amount in restores:
        row.balance = amount
    changed = db.execute(conversions.update().where(conversions.c.conversion_id == conversion_id,
        conversions.c.version == request.expected_conversion_version, conversions.c.status == "active")
        .values(status="reversed", version=request.expected_conversion_version + 1, reversed_at=now))
    if changed.rowcount != 1:
        fail("STALE_CONVERSION_VERSION")
    if capital:
        capital.lifecycle_status = "superseded"
    else:
        db.execute(pensions.update().where(pensions.c.conversion_id == conversion_id).values(status="reversed", version=destination["version"] + 1, reversed_at=now))
    _bump(db, product, actor)
    audit(db, product, "reversal", actor, operation={"conversion_id": conversion_id,
        "matrix_version": source[0]["matrix_version"], "allocations": before_after})
    result = {"reversal_id": uuid4().hex, "conversion_id": conversion_id, "status": "reversed",
        "version": request.expected_conversion_version + 1, "product_id": product.product_id, "product_version": product.version}
    db.execute(reversals.insert().values(reversal_id=result["reversal_id"], client_id=client_id,
        conversion_id=conversion_id, idempotency_key=request.idempotency_key, request_fingerprint=fingerprint(request),
        expected_conversion_version=request.expected_conversion_version, reason=request.reason, actor=actor, result=result))
    return result
