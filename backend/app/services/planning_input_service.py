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
        pension_temporal_authority_registry_fingerprint=snapshot['pension_temporal_authority_registry_fingerprint'],
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


# Stage 6 P1C: canonical scenario identity, distinct from factual planning hash.
def scenario_decision_calculation_identity(facts: dict) -> dict:
    """Produce P1 only from current admitted identities (caller validates snapshot).

    Identity-only producer; no pension calculation and no executive grant.
    """
    from urllib.parse import quote
    required=frozenset((
        "client_id","scenario_id","scenario_version","decision_id","source_id",
        "manifest_fingerprint","partition_fingerprint","source_fingerprint",
        "statement_date","amount","action","election_fingerprint",
        "retirement_target_date","monthly_semantic_fingerprint",
        "monthly_source_fingerprint","temporal_semantic_fingerprint",
        "temporal_source_fingerprint","professional_admission_revision",
        "professional_admission_fingerprint","ruleset_digest",
        "permission_admission_fingerprint"))
    if type(facts) is not dict or set(facts)!=required:
        raise ValueError("SCENARIO_PLANNING_FIELDS_INVALID")
    for k in ("client_id","scenario_version","professional_admission_revision"):
        if type(facts[k]) is not int or facts[k]<=0:
            raise ValueError("SCENARIO_PLANNING_VERSION_INVALID")
    if facts["action"]!="pension":
        raise ValueError("SCENARIO_PLANNING_ACTION_INVALID")
    for k in ("scenario_id","decision_id"):
        if type(facts[k]) is not str or not facts[k]:
            raise ValueError("SCENARIO_PLANNING_ID_INVALID")
    expected="scenario-decision:"+quote(facts["scenario_id"],safe="")+":"+quote(facts["decision_id"],safe="")
    if facts["source_id"]!=expected:
        raise ValueError("SCENARIO_PLANNING_SOURCE_INVALID")
    for k in ("manifest_fingerprint","partition_fingerprint","source_fingerprint",
              "election_fingerprint","monthly_semantic_fingerprint",
              "monthly_source_fingerprint","temporal_semantic_fingerprint",
              "temporal_source_fingerprint","professional_admission_fingerprint",
              "ruleset_digest","permission_admission_fingerprint"):
        v=facts[k]
        if type(v) is not str or len(v)!=64 or any(c not in "0123456789abcdef" for c in v):
            raise ValueError("SCENARIO_PLANNING_HASH_INVALID")
    from datetime import date as _date
    from app.services.pension_monthly_basis_service import money,decimal
    for k in ("statement_date","retirement_target_date"):
        if type(facts[k]) is not str or _date.fromisoformat(facts[k]).isoformat()!=facts[k]:
            raise ValueError("SCENARIO_PLANNING_DATE_INVALID")
    if facts["retirement_target_date"]<facts["statement_date"]:
        raise ValueError("SCENARIO_PLANNING_TARGET_INVALID")
    if type(facts["amount"]) is not str or money(facts["amount"])!=facts["amount"] or decimal(facts["amount"])<=0:
        raise ValueError("SCENARIO_PLANNING_AMOUNT_INVALID")
    preimage={"contract":"canonical-scenario-pension-planning-calculation-input-v1",**facts}
    return {"planning_calculation_input_fingerprint":fingerprint(preimage),
            "planning_calculation_input_preimage":preimage}


def scenario_decision_one_source_planning_result(*, facts: dict, monthly: dict,
                                                 temporal: dict, factor_value: str) -> dict:
    """P1C/N1.2: assemble one non-executable scenario planning result.

    Caller must prove fresh PostgreSQL admission; this function cannot
    independently authorize execution. PTE acceptance is deferred to P1D.
    """
    from app.services.pension_monthly_basis_service import factor as canonical_factor
    p1=scenario_decision_calculation_identity(facts)
    required_monthly=frozenset(("source_id","representation","monthly_semantic_fingerprint",
                                "monthly_source_fingerprint","monthly_source_preimage"))
    required_temporal=frozenset(("temporal_semantic_fingerprint","temporal_source_fingerprint",
                                 "temporal_source_preimage"))
    if type(monthly) is not dict or set(monthly)!=required_monthly or type(temporal) is not dict or set(temporal)!=required_temporal:
        raise ValueError("SCENARIO_PLANNING_BASIS_INVALID")
    from app.services.pension_monthly_basis_service import (
        fingerprint as canonical_basis_hash, semantic as canonical_monthly_semantic,
    )
    from app.services.pension_temporal_basis_service import semantic_fingerprint
    if monthly["source_id"]!=facts["source_id"]:
        raise ValueError("SCENARIO_PLANNING_MONTHLY_SOURCE_INVALID")
    monthly_source=monthly["monthly_source_preimage"]
    temporal_source=temporal["temporal_source_preimage"]
    if type(monthly_source) is not dict or type(temporal_source) is not dict:
        raise ValueError("SCENARIO_PLANNING_PREIMAGE_INVALID")
    monthly_source_fields=frozenset((
        "contract_version","source_id","source_kind","client_id","scenario_id",
        "scenario_version","decision_id","manifest_fingerprint",
        "partition_fingerprint","source_product_id","source_product_version",
        "source_component_id","component_code","source_fingerprint","amount",
        "statement_date","election_fingerprint","professional_admission_revision",
        "professional_admission_fingerprint","monthly_semantic_fingerprint"))
    temporal_source_fields=frozenset((
        "contract_version","source_id","source_kind","client_id","scenario_id",
        "scenario_version","decision_id","statement_date","retirement_target_date",
        "monthly_source_fingerprint","temporal_semantic_fingerprint",
        "professional_admission_fingerprint"))
    if (set(monthly_source)!=monthly_source_fields
            or monthly_source.get("contract_version")
                !="canonical-scenario-pension-monthly-source-v1"
            or monthly_source.get("source_kind")!="scenario_decision"):
        raise ValueError("SCENARIO_PLANNING_MONTHLY_SOURCE_INVALID")
    monthly_bindings={
        "source_id":"source_id","client_id":"client_id","scenario_id":"scenario_id",
        "scenario_version":"scenario_version","decision_id":"decision_id",
        "manifest_fingerprint":"manifest_fingerprint",
        "partition_fingerprint":"partition_fingerprint",
        "source_fingerprint":"source_fingerprint","amount":"amount",
        "statement_date":"statement_date","election_fingerprint":"election_fingerprint",
        "professional_admission_revision":"professional_admission_revision",
        "professional_admission_fingerprint":"professional_admission_fingerprint",
        "monthly_semantic_fingerprint":"monthly_semantic_fingerprint",
    }
    if any(monthly_source[source]!=facts[target]
           for source,target in monthly_bindings.items()):
        raise ValueError("SCENARIO_PLANNING_MONTHLY_SOURCE_INVALID")
    if (set(temporal_source)!=temporal_source_fields
            or temporal_source.get("contract_version")
                !="canonical-scenario-pension-temporal-source-v1"
            or temporal_source.get("source_kind")!="scenario_decision"):
        raise ValueError("SCENARIO_PLANNING_TEMPORAL_SOURCE_INVALID")
    temporal_bindings={
        "source_id":"source_id","client_id":"client_id","scenario_id":"scenario_id",
        "scenario_version":"scenario_version","decision_id":"decision_id",
        "statement_date":"statement_date","retirement_target_date":"retirement_target_date",
        "monthly_source_fingerprint":"monthly_source_fingerprint",
        "temporal_semantic_fingerprint":"temporal_semantic_fingerprint",
        "professional_admission_fingerprint":"professional_admission_fingerprint",
    }
    if any(temporal_source[source]!=facts[target]
           for source,target in temporal_bindings.items()):
        raise ValueError("SCENARIO_PLANNING_TEMPORAL_SOURCE_INVALID")
    if canonical_monthly_semantic(
            "scenario_decision_balance_ratio",monthly["representation"],facts["statement_date"]
        )!=facts["monthly_semantic_fingerprint"]:
        raise ValueError("SCENARIO_PLANNING_MONTHLY_SEMANTIC_INVALID")
    if semantic_fingerprint("none",facts["statement_date"],None,None)!=facts["temporal_semantic_fingerprint"]:
        raise ValueError("SCENARIO_PLANNING_TEMPORAL_SEMANTIC_INVALID")
    if canonical_basis_hash(monthly_source)!=facts["monthly_source_fingerprint"]:
        raise ValueError("SCENARIO_PLANNING_MONTHLY_SOURCE_FINGERPRINT_INVALID")
    if canonical_basis_hash(temporal_source)!=facts["temporal_source_fingerprint"]:
        raise ValueError("SCENARIO_PLANNING_TEMPORAL_SOURCE_FINGERPRINT_INVALID")
    for field in ("monthly_semantic_fingerprint","monthly_source_fingerprint"):
        if monthly[field]!=facts[field]:
            raise ValueError("SCENARIO_PLANNING_MONTHLY_FINGERPRINT_INVALID")
    for field in ("temporal_semantic_fingerprint","temporal_source_fingerprint"):
        if temporal[field]!=facts[field]:
            raise ValueError("SCENARIO_PLANNING_TEMPORAL_FINGERPRINT_INVALID")
    if monthly["representation"]!={"representation_kind":"exact_ratio",
                                    "numerator":facts["amount"],
                                    "denominator":canonical_factor(factor_value)}:
        raise ValueError("SCENARIO_PLANNING_REPRESENTATION_INVALID")
    statement=facts["statement_date"]
    target=facts["retirement_target_date"]
    return {
        "contract_version":"SCENARIO_PENSION_PLANNING_RESULT_V1",
        "client_id":facts["client_id"],"scenario_id":facts["scenario_id"],
        "scenario_version":facts["scenario_version"],"decision_id":facts["decision_id"],
        "planning_calculation_input_fingerprint":p1["planning_calculation_input_fingerprint"],
        "retirement_target":{"retirement_target_date":target,"retirement_target_ready":True},
        "pension_inputs":[{
            "source_id":facts["source_id"],"pension_start_date":target,"currency":"ILS",
            "monthly_amount_basis":{
                "contract_version":"canonical-pension-monthly-amount-basis-v1",
                "source_id":facts["source_id"],"source_kind":"scenario_decision",
                "authority_kind":"scenario_decision_balance_ratio",
                "base_amount_representation":monthly["representation"],
                "base_amount_effective_date":statement,
                "basis_authority_ready":True,"basis_blockers":[],
                "base_amount_semantic_fingerprint":facts["monthly_semantic_fingerprint"],
                "base_amount_source_fingerprint":facts["monthly_source_fingerprint"]},
            "temporal_authority":{
                "contract_version":"canonical-pension-temporal-indexation-basis-v1",
                "source_id":facts["source_id"],"source_kind":"scenario_decision",
                "temporal_authority_kind":"none","temporal_origin_date":statement,
                "annual_rate":None,"rate_basis":None,
                "temporal_authority_ready":True,"temporal_blockers":[],
                "temporal_semantic_fingerprint":facts["temporal_semantic_fingerprint"],
                "temporal_source_fingerprint":facts["temporal_source_fingerprint"]}}
        ]}
