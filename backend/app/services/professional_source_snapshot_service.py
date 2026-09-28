"""Derived SELECT-only source view; no forecast, cache or stored authority."""
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from sqlalchemy import select, or_
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.pension_product import PensionProduct, PensionProductComponent, COMPONENT_CODES
from app.models.canonical_conversion import conversions, pensions, allocations, batches
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.retirement_facts import CapitalAsset, RetirementTimingWorkIntention
from app.services.pension_product_service import PensionProductError
from app.services import pension_monthly_basis_service as pension_basis

CONTRACT = "canonical-professional-source-snapshot-v1"


def invalid():
    raise PensionProductError("SOURCE_STRUCTURE_INVALID", "קשרי המקור אינם תקינים; אין להשתמש בתמונה", 409)


def serialize(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value


def record(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def begin_read(db):
    # The route owns a fresh Session. Never turn an existing writer transaction
    # into a supposedly read-only snapshot or let pending ORM changes autoflush.
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise PensionProductError("SNAPSHOT_REQUIRES_FRESH_TRANSACTION", "נדרשת טרנזקציית קריאה חדשה", 409)
    dialect = db.get_bind().dialect.name
    connection = db.connection()
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif dialect == "sqlite":
        # Python sqlite legacy transaction mode does not BEGIN on SELECT.
        # Explicit BEGIN holds one MVCC/read snapshot through every SELECT.
        connection.exec_driver_sql("BEGIN")
    else:
        raise PensionProductError("UNSUPPORTED_DATABASE", "מסד הנתונים אינו נתמך", 503)


def number(value, *, positive=False):
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or (positive and result == 0):
            invalid()
        return result
    except (ArithmeticError, ValueError, TypeError):
        invalid()


def snapshot(db, client_id, *, as_of=None):
    begin_read(db)
    with db.no_autoflush:
        return _snapshot(db, client_id, as_of=as_of or date.today())


def _snapshot(db, client_id, *, as_of):
    if db.get(Client, client_id) is None:
        raise PensionProductError("CLIENT_NOT_FOUND", "הלקוח לא נמצא", 404)
    products = db.scalars(select(PensionProduct).where(PensionProduct.client_id == client_id).order_by(PensionProduct.product_id)).all()
    product_map = {p.product_id: p for p in products}
    components = db.scalars(select(PensionProductComponent).where(PensionProductComponent.product_id.in_(product_map)).order_by(PensionProductComponent.component_id)).all()
    component_map = {c.component_id: c for c in components}
    product_output = []
    for p in products:
        rows = [c for c in components if c.product_id == p.product_id]
        if len(rows) != 11 or {c.component_code for c in rows} != set(COMPONENT_CODES):
            invalid()
        item = record(p)
        controls = {k: item.pop(k) for k in ("reported_product_total", "reported_rewards_total", "reported_severance_total")}
        item["reported_controls"] = {"authority": "CONTROL_RECONCILIATION_ONLY", **controls}
        item["balance_kind"] = "remaining_unconverted_source"
        item["components"] = [{"component_id": c.component_id, "component_code": c.component_code, "balance": number(c.balance)} for c in sorted(rows, key=lambda c: COMPONENT_CODES.index(c.component_code))]
        product_output.append(item)
    conv = {r["conversion_id"]: dict(r) for r in db.execute(select(conversions).where(conversions.c.client_id == client_id)).mappings()}
    batch_map = {r["batch_id"]: dict(r) for r in db.execute(select(batches).where(batches.c.client_id == client_id)).mappings()}
    for c in conv.values():
        if c["batch_id"] not in batch_map or batch_map[c["batch_id"]]["source_product_id"] not in product_map:
            invalid()
    pension_rows = db.execute(select(pensions).where(or_(pensions.c.client_id == client_id, pensions.c.conversion_id.in_(conv))).order_by(pensions.c.pension_destination_id)).mappings().all()
    allocation_rows = db.execute(select(allocations).where(allocations.c.conversion_id.in_(conv)).order_by(allocations.c.allocation_id)).mappings().all()
    sources = []
    represented = set()
    for p in pension_rows:
        c = conv.get(p["conversion_id"])
        if p["client_id"] != client_id or c is None or c["destination_type"] != "pension" or c["status"] != p["status"]:
            invalid()
        represented.add(c["conversion_id"])
        if p["status"] != "active":
            continue
        trace = [dict(a) for a in allocation_rows if a["conversion_id"] == c["conversion_id"]]
        for a in trace:
            component = component_map.get(a["source_component_id"])
            if component is None or component.product_id != a["source_product_id"] or component.component_code != a["component_code_snapshot"] or a["source_product_id"] != batch_map[c["batch_id"]]["source_product_id"]:
                invalid()
        numerator = number(p["monthly_numerator"])
        denominator = number(p["monthly_denominator"], positive=True)
        if not trace or sum((a["amount"] for a in trace), Decimal(0)) != numerator or numerator != p["converted_balance"] or numerator != c["converted_amount"] or denominator != number(p["annuity_factor_text"], positive=True) or p["tax_treatment"] != c["tax_treatment"]:
            invalid()
        source_product = product_map[batch_map[c["batch_id"]]["source_product_id"]]
        basis = pension_basis.conversion(db, client_id, batch_map[c['batch_id']], c, p, trace)
        sources.append({"source_id": "conversion:" + p["pension_destination_id"], "kind": "conversion", "payer_name": p["name"],
            "monthly_amount_basis": basis,
            "version": p["version"], "lifecycle_status": "current", "pension_start_date": p["pension_start_date"], "tax_treatment": p["tax_treatment"],
            "amount_authority": {"authority_kind": "persisted_conversion_ratio", "numerator": p["monthly_numerator"], "denominator": p["monthly_denominator"]},
            "provenance": {"conversion_id": c["conversion_id"], "pension_destination_id": p["pension_destination_id"], "allocations": trace,
                "source_reference": source_product.account_reference, "coefficient_source": p["coefficient_source"]},
            "missing_or_blocking_facts": []})
    manual_rows = db.scalars(select(Manual).where(Manual.client_id == client_id, Manual.lifecycle_status == "current").order_by(Manual.manual_pension_source_id)).all()
    for m in manual_rows:
        item = record(m)
        basis = pension_basis.manual(m, client_id)
        authority = {"authority_kind": "entered_monthly_amount", "amount": m.monthly_amount} if m.input_mode == "entered" else {
            "authority_kind": "manual_balance_ratio", "numerator": m.balance, "denominator": m.annuity_factor}
        missing = []
        if m.input_mode == "entered":
            if m.monthly_amount is None:
                missing.append("monthly_amount_missing")
            else:
                if number(m.monthly_amount) == 0:
                    missing.append("monthly_amount_not_positive")
        else:
            if m.balance is None:
                missing.append("balance_missing")
            else:
                if number(m.balance) == 0:
                    missing.append("balance_not_positive")
            if m.annuity_factor is None:
                missing.append("annuity_factor_missing")
            # Basis Authority reports invalid/non-positive stored factor facts
            # as visible blockers instead of deriving a monthly amount.
        if not m.payer_name:
            missing.append("payer_name_missing")
        if m.indexation_method not in ("none", "cpi", "fixed"):
            missing.append("indexation_method_missing_or_unsupported")
        if m.indexation_method == "fixed":
            if m.fixed_indexation_rate is None:
                missing.append("fixed_indexation_rate_missing")
            else:
                # V1 PensionFunds/handlers.ts at e4bd8618 rejects both zero
                # (!rate) and negative rates. Preserve incomplete facts, not
                # their readiness; never substitute or calculate indexation.
                rate = Decimal(m.fixed_indexation_rate)
                if not rate.is_finite() or rate <= 0:
                    missing.append("fixed_indexation_rate_not_positive")
        sources.append({**item, "kind": "manual", "source_id": "manual:" + m.manual_pension_source_id,
            "monthly_amount_basis": basis,
            "amount_authority": authority, "provenance": {"manual_pension_source_id": m.manual_pension_source_id, "source_reference": m.source_reference, "source_note": m.source_note},
            "missing_or_blocking_facts": missing})
    warnings = []
    for s in sources:
        missing = s["missing_or_blocking_facts"]
        missing.extend(s['monthly_amount_basis']['basis_blockers'])
        missing[:] = sorted(set(missing))
        if s["pension_start_date"] is None:
            missing.append("pension_start_date_missing")
        if s["tax_treatment"] not in ("taxable", "exempt"):
            missing.append("tax_treatment_missing_or_unsupported")
        reference = s["provenance"].get("source_reference")
        duplicates = [o["source_id"] for o in sources if o is not s and
            ((reference and reference in (o["source_id"], o["provenance"].get("source_reference"))) or o["provenance"].get("source_reference") == s["source_id"])
            and (s["kind"] == "manual" or o["kind"] == "manual")]
        if duplicates:
            missing.append("potential_duplicate_source")
            warnings.append({"code": "potential_duplicate_source", "source_id": s["source_id"], "related_sources": sorted(duplicates)})
        s["visible"] = True
        s["calculation_ready"] = not missing
        s["started_as_of"] = as_of.isoformat()
        s["has_started"] = None if s["pension_start_date"] is None else s["pension_start_date"] <= as_of
    assets = db.scalars(select(CapitalAsset).where(or_(CapitalAsset.client_id == client_id, CapitalAsset.conversion_id.in_(conv))).order_by(CapitalAsset.id)).all()
    capital = []
    for a in assets:
        if a.client_id != client_id:
            invalid()
        if a.origin_kind == "canonical_component_conversion":
            c = conv.get(a.conversion_id)
            if c is None or c["destination_type"] != "capital" or a.known_value_amount != c["converted_amount"]:
                invalid()
            represented.add(c["conversion_id"])
            if (c["status"] == "active") != (a.lifecycle_status == "current"):
                invalid()
            if c["status"] != "active":
                continue
        elif a.origin_kind != "manual" or a.conversion_id is not None:
            invalid()
        if a.lifecycle_status != "current":
            continue
        missing = ["known_value_missing"] if a.known_value_amount is None else []
        capital.append({**record(a), "source_id": f"capital:{a.id}", "visible": True, "calculation_ready": not missing, "missing_or_blocking_facts": missing})
    if any(c["status"] == "active" and cid not in represented for cid, c in conv.items()):
        invalid()
    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
    client_warnings = [field + "_missing" for field in ("birth_date", "gender") if not profile or getattr(profile, field) is None]
    if db.scalar(select(EmploymentRecord.employment_record_id).where(EmploymentRecord.client_id == client_id).limit(1)) is None:
        client_warnings.append("employment_facts_missing")
    timing = db.scalars(select(RetirementTimingWorkIntention).where(
        RetirementTimingWorkIntention.client_id == client_id, RetirementTimingWorkIntention.lifecycle_status == "current")).all()
    if not any(t.planned_work_end_date or t.intended_pension_start_date or t.other_known_retirement_date or t.anticipated_work_end_date for t in timing):
        client_warnings.append("retirement_date_facts_missing")
    result = serialize({"contract_version": CONTRACT, "client_id": client_id, "pension_products": product_output,
        "pension_monthly_amount_basis_fingerprint": pension_basis.registry(client_id, [s['monthly_amount_basis'] for s in sources]),
        "pension_sources": sorted(sources, key=lambda s: s["source_id"]), "capital_sources": capital,
        "client_fact_warnings": client_warnings, "source_warnings": sorted(warnings, key=lambda w: w["source_id"])})
    # Calendar presentation is not source state. Crossing midnight must not
    # pretend that authoritative balances/versions changed.
    state = {**result, "pension_sources": [{k: v for k, v in s.items() if k not in ("has_started", "started_as_of")} for s in result["pension_sources"]]}
    result["source_state_fingerprint"] = hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return result
