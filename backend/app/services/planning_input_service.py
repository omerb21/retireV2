"""Canonical planning input: exact source classification, not calculation."""
from datetime import date
from decimal import Decimal
import hashlib
import json
from sqlalchemy import select, or_
from app.models.client import Client
from app.models.retirement_facts import RecurringIncome, RecurringExpense, RetirementTimingWorkIntention
from app.models.planning_input_decision import PlanningInputDecision, PensionIncomeResolution
from app.services.professional_source_snapshot_service import begin_read, _snapshot, record, serialize
from app.services.pension_product_service import PensionProductError, lock_client

CONTRACT = "canonical-retirement-planning-input-v1"


def fingerprint(value):
    return hashlib.sha256(json.dumps(serialize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def source_context(source):
    return {k: v for k, v in source.items() if k not in ("has_started", "started_as_of", "monthly_display_amount")}


def fail(code, message="המקור או ההחלטה השתנו; יש לרענן ולאשר מחדש"):
    raise PensionProductError(code, message, 409)


def rows(db, model, client_id):
    return db.scalars(select(model).where(model.client_id == client_id).order_by(model.id)).all()


def applicability(start, end, base):
    if base is None:
        return "base_date_missing"
    if start and start > base:
        return "future_start"
    if end and end < base:
        return "ended"
    return "active_at_base"


def read(db, client_id):
    begin_read(db)
    with db.no_autoflush:
        return derive(db, client_id)


def planning_decision_semantics(decision):
    """Closed pre-target semantic boundary, independent of row existence."""
    return {"planning_base_date": decision.planning_base_date if decision else None}


def derive(db, client_id):
    # Same transaction as all subsequent reads. The fixed as_of value has no
    # financial meaning and its calendar-only output is discarded below.
    snapshot = _snapshot(db, client_id, as_of=date.min)
    decision = db.get(PlanningInputDecision, client_id)
    base = decision.planning_base_date if decision else None
    client = db.get(Client, client_id)
    incomes, expenses, timings = (rows(db, model, client_id) for model in
        (RecurringIncome, RecurringExpense, RetirementTimingWorkIntention))
    income_ids = {r.id for r in incomes}
    resolutions = db.scalars(select(PensionIncomeResolution).where(or_(PensionIncomeResolution.client_id == client_id,
                            PensionIncomeResolution.income_id.in_(income_ids)))
                            .order_by(PensionIncomeResolution.income_id)).all()
    if any(r.client_id != client_id or r.income_id not in income_ids for r in resolutions):
        fail("RESOLUTION_OWNERSHIP_INVALID", "שיוך הכרעת הזהות ללקוח או למקור אינו תקין")
    resolution_map = {r.income_id: r for r in resolutions}
    result = dict(contract_version=CONTRACT, client_id=client_id, decision_version=decision.version if decision else 0,
        planning_base_date=base, date_candidates=[], source_state_fingerprint=snapshot["source_state_fingerprint"],
        pension_monthly_amount_basis_fingerprint=snapshot['pension_monthly_amount_basis_fingerprint'],
        pension_inputs=[], general_income_inputs=[], expense_inputs=[], capital_inputs=[], reference_only=[],
        excluded_sources=[], unresolved_items=[], warnings=[], blocking_facts=[], planning_input_ready=False)
    if base is None:
        result["blocking_facts"].append({"source_id": None, "code": "planning_base_date_missing"})
    for code in snapshot["client_fact_warnings"]:
        result["warnings"].append({"source_id": None, "code": code})

    def candidate(source_id, field, value):
        if value is not None:
            result["date_candidates"].append({"source_id": source_id, "field": field, "date": value})

    candidate(f"client:{client_id}", "planned_retirement_date", client.planned_retirement_date)
    result["client_reference_facts"] = {"birth_date": client.birth_date, "planned_retirement_age": client.planned_retirement_age}
    for timing in timings:
        if timing.lifecycle_status == "current":
            for field in ("planned_work_end_date", "intended_pension_start_date", "other_known_retirement_date", "anticipated_work_end_date"):
                candidate(f"timing:{timing.id}", field, getattr(timing, field))

    def classify(item, blockers, app):
        item["applicability"] = app
        item["blocking_facts"] = sorted(set(blockers))
        item["inclusion_state"] = "unresolved" if blockers else ("reference_only" if app == "ended" else "included")
        item["active_at_base"] = not blockers and app == "active_at_base"
        if blockers:
            result["unresolved_items"].append({"source_id": item["source_id"], "reasons": item["blocking_facts"]})
            result["blocking_facts"].extend({"source_id": item["source_id"], "code": b} for b in item["blocking_facts"])
        elif app == "ended":
            result["reference_only"].append(item)

    pensions = {p["source_id"]: source_context(p) for p in snapshot["pension_sources"]}
    for source in pensions.values():
        item = {**source, "source_calculation_ready": source["calculation_ready"], "source_fingerprint": fingerprint(source)}
        candidate(item["source_id"], "pension_start_date", item["pension_start_date"])
        start = date.fromisoformat(item["pension_start_date"]) if item["pension_start_date"] else None
        classify(item, source["missing_or_blocking_facts"], applicability(start, None, base))
        result["pension_inputs"].append(item)

    for income in incomes:
        if income.lifecycle_status != "current":
            continue
        resolution = resolution_map.get(income.id)
        stale = False
        linked = False
        if resolution:
            stale = resolution.income_fingerprint != fingerprint(record(income))
            if resolution.decision_kind != "MISCLASSIFIED_GENERAL_INCOME":
                target = pensions.get(resolution.canonical_source_id)
                stale = stale or income.income_category != "pension" or target is None or fingerprint(target) != resolution.canonical_fingerprint
                linked = not stale
            else:
                stale = stale or income.income_category == "pension" or resolution.canonical_source_id is not None or resolution.canonical_fingerprint is not None
        if income.income_category == "pension" or stale:
            item = {**record(income), "source_id": f"income:{income.id}", "source_fingerprint": fingerprint(record(income)),
                    "resolution": record(resolution) if resolution else None}
            if linked:
                item.update(inclusion_state="excluded", reason="same_canonical_pension", canonical_source_id=resolution.canonical_source_id)
                result["excluded_sources"].append(item)
            else:
                classify(item, ["identity_resolution_stale" if stale else "identity_resolution_required"], "identity_unresolved")
                result["excluded_sources"].append(item)
            continue
        result["general_income_inputs"].append(normalized(income, "income", base, classify))

    for expense in expenses:
        if expense.lifecycle_status == "current":
            result["expense_inputs"].append(normalized(expense, "expense", base, classify))

    # Descriptive similarity is never identity. Stable row IDs remain distinct.
    groups = {}
    for item in result["general_income_inputs"]:
        signature = tuple(str(item.get(k)) for k in ("income_category", "amount", "frequency", "start_date", "end_date", "description"))
        groups.setdefault(signature, []).append(item["source_id"])
    for ids in groups.values():
        if len(ids) > 1:
            result["warnings"].append({"code": "potential_duplicate_warning", "source_ids": ids})

    for source in snapshot["capital_sources"]:
        item = dict(source)
        blockers = []
        if source["known_value_amount"] is None:
            blockers.append("capital_value_missing")
        if source["value_as_of_date"] is None:
            blockers.append("capital_valuation_date_missing")
        # source_date remains provenance, never a substitute valuation date.
        app = "base_date_missing" if base is None else ("future_start" if source["value_as_of_date"] and date.fromisoformat(source["value_as_of_date"]) > base else "active_at_base")
        classify(item, blockers, app)
        result["capital_inputs"].append(item)
    for product in snapshot["pension_products"]:
        for component in product["components"]:
            result["reference_only"].append({**component, "source_id": "component:" + component["component_id"],
                "product_id": product["product_id"], "product_name": product["product_name"], "classification": "remaining_unconverted_source", "inclusion_state": "reference_only"})
    result["planning_input_ready"] = not result["blocking_facts"]
    result["planning_input_fingerprint"] = fingerprint({"contract": CONTRACT, "source": snapshot["source_state_fingerprint"],
        "incomes": [record(r) for r in incomes], "expenses": [record(r) for r in expenses], "timings": [record(r) for r in timings],
        "client": record(client), "decision": planning_decision_semantics(decision), "resolutions": [record(r) for r in resolutions]})
    from app.services.retirement_target_service import extend_read
    extend_read(result, decision, client, timings, snapshot)
    return serialize(result)


def normalized(row, kind, base, classify):
    item = {**record(row), "source_id": f"{kind}:{row.id}", "source_fingerprint": fingerprint(record(row))}
    blockers = []
    denominator = {"monthly": 1, "quarterly": 3, "annual": 12}.get(row.frequency)
    item["monthly_equivalent_ratio"] = {"numerator": row.amount, "denominator": denominator} if denominator else None
    if denominator is None:
        blockers.append("frequency_unsupported")
    if row.amount is None or not Decimal(row.amount).is_finite() or row.amount < 0:
        blockers.append("amount_invalid")
    if row.start_date is None:
        blockers.append("start_date_missing")
    if row.continuation_status == "known end date" and row.end_date is None:
        blockers.append("end_date_missing")
    if row.continuation_status == "unknown":
        blockers.append("continuation_unknown")
    if row.start_date and row.end_date and row.start_date > row.end_date:
        blockers.append("date_range_contradictory")
    if kind == "income" and row.amount_basis not in ("gross", "net"):
        blockers.append("amount_basis_unknown")
    classify(item, blockers, applicability(row.start_date, row.end_date, base))
    return item


def writable_decision(db, client_id, expected):
    lock_client(db, client_id)
    decision = db.get(PlanningInputDecision, client_id, populate_existing=True)
    if (decision.version if decision else 0) != expected:
        fail("PLANNING_DECISION_STALE")
    if decision is None:
        decision = PlanningInputDecision(client_id=client_id, version=1, actor="planner:planning-input")
        db.add(decision)
    else:
        decision.version += 1
    return decision


def set_base_date(db, client_id, payload):
    decision = writable_decision(db, client_id, payload.expected_version)
    decision.planning_base_date = payload.planning_base_date
    db.flush()
    return serialize(record(decision))


def resolve_income(db, client_id, income_id, payload):
    decision = writable_decision(db, client_id, payload.expected_version)
    income = db.scalar(select(RecurringIncome).where(RecurringIncome.id == income_id, RecurringIncome.client_id == client_id)
                       .with_for_update().execution_options(populate_existing=True))
    if income is None or income.lifecycle_status != "current" or fingerprint(record(income)) != payload.expected_income_fingerprint:
        fail("INCOME_SOURCE_STALE")
    resolution = db.get(PensionIncomeResolution, income_id)
    if income.income_category != "pension" and resolution is None:
        fail("INCOME_NOT_PENSION")
    canonical_fingerprint = None
    if payload.decision_kind == "MISCLASSIFIED_GENERAL_INCOME":
        income.income_category = payload.income_category
        db.flush()
    else:
        if income.income_category != "pension":
            fail("INCOME_NOT_PENSION")
        source = next((p for p in _snapshot(db, client_id, as_of=date.min)["pension_sources"] if p["source_id"] == payload.canonical_source_id), None)
        if source is None or (payload.decision_kind == "PENSION_NOT_YET_CANONICAL" and source["kind"] != "manual"):
            fail("CANONICAL_PENSION_NOT_CURRENT")
        canonical_fingerprint = fingerprint(source_context(source))
        if canonical_fingerprint != payload.expected_canonical_fingerprint:
            fail("CANONICAL_PENSION_STALE")
    # Load server-updated source facts before adding a partially initialized
    # decision. PostgreSQL may expire updated_at after the source UPDATE.
    income_fingerprint = fingerprint(record(income))
    if resolution is None:
        resolution = PensionIncomeResolution(income_id=income_id, client_id=client_id, version=1)
        db.add(resolution)
    elif resolution.client_id != client_id:
        fail("RESOLUTION_OWNERSHIP_INVALID")
    else:
        resolution.version += 1
    resolution.decision_kind = payload.decision_kind
    resolution.income_fingerprint = income_fingerprint
    resolution.canonical_source_id = payload.canonical_source_id
    resolution.canonical_fingerprint = canonical_fingerprint
    resolution.reference = payload.reference
    resolution.actor = "planner:planning-input"
    db.flush()
    return {"decision_version": decision.version, "resolution": serialize(record(resolution))}
