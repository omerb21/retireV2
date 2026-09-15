"""Explicit target authority; closed references, no financial calculation."""
from datetime import date, datetime, timezone
from sqlalchemy import select
from app.models.client import Client
from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import RetirementTimingWorkIntention
from app.services.pension_product_service import PensionProductError, lock_client
from app.services.professional_source_snapshot_service import _snapshot, serialize
from app.services.planning_input_service import fingerprint

CONTRACT = "canonical-retirement-target-date-authority-v1"
PROVENANCE = "explicit_professional_retirement_target_date"
ADAPTERS = ("CLIENT_PLANNED_RETIREMENT_DATE", "CLIENT_PLANNED_RETIREMENT_AGE",
            "RETIREMENT_TIMING_WORK_INTENTION", "CANONICAL_PENSION_SOURCE_START_DATE")
TIMING_FIELDS = ("planned_work_end_date", "intended_pension_start_date",
                 "other_known_retirement_date", "anticipated_work_end_date")


def references(client, timings, snapshot):
    facts = []

    def add(rid, sid, kind, field, value, *, age=False, lifecycle="current", version=None, semantic=None, unresolved=()):
        if value is None:
            return
        facts.append(dict(reference_id=rid, source_id=sid, source_kind=kind, source_field=field,
            value_kind="age" if age else "date", date_value=None if age else value,
            age_value=value if age else None, source_semantic_fingerprint=semantic,
            source_version=version, lifecycle_state=lifecycle, unresolved_state=sorted(unresolved)))

    sid = f"client:{client.client_id}"
    add(f"{sid}:planned_retirement_date", sid, ADAPTERS[0], "planned_retirement_date", client.planned_retirement_date)
    add(f"{sid}:planned_retirement_age", sid, ADAPTERS[1], "planned_retirement_age", client.planned_retirement_age, age=True)
    for row in timings:
        if row.lifecycle_status == "current":
            for field in TIMING_FIELDS:
                add(f"timing:{row.id}:{field}", f"timing:{row.id}", ADAPTERS[2], field, getattr(row, field), lifecycle=row.lifecycle_status)
    for source in snapshot["pension_sources"]:
        if source["lifecycle_status"] == "current" and source["visible"]:
            sid = source["source_id"]
            add(f"pension:{sid}:pension_start_date", sid, ADAPTERS[3], "pension_start_date", source["pension_start_date"],
                lifecycle=source["lifecycle_status"], version=source.get("version"),
                semantic=source.get("source_semantic_fingerprint"), unresolved=source["missing_or_blocking_facts"])
    return canonical_references(facts)


def canonical_references(facts):
    if len({fact["reference_id"] for fact in facts}) != len(facts):
        raise PensionProductError("TARGET_REFERENCE_STRUCTURE_INVALID", "זהות עובדות הייחוס אינה תקינה", 409)
    return sorted(serialize(facts), key=lambda fact: fact["reference_id"])


def reference_fingerprint(client_id, facts):
    return fingerprint({"contract": CONTRACT, "client_id": client_id, "references": canonical_references(facts)})


def extend_read(result, decision, client, timings, snapshot):
    facts = references(client, timings, snapshot)
    current = reference_fingerprint(client.client_id, facts)
    target = decision.retirement_target_date if decision else None
    base = decision.planning_base_date if decision else None
    blockers = []
    if base is None:
        blockers.append("planning_base_date_missing")
    if target is None:
        blockers.append("retirement_target_date_missing")
    if base is None and target is None:
        relation = "base_and_target_missing"
    elif base is None:
        relation = "base_missing"
    elif target is None:
        relation = "target_missing"
    elif target < base:
        relation = "before_base"
        blockers.append("retirement_target_before_planning_base_date")
    else:
        relation = "equal_to_base" if target == base else "after_base"
    dates = {f["date_value"] for f in facts if f["value_kind"] == "date"}
    warnings = []
    if len(dates) > 1:
        warnings.append("target_reference_dates_conflict")
    if target and dates and any(d != target.isoformat() for d in dates):
        warnings.append("retirement_target_differs_from_reference_dates")
    stored = decision.retirement_target_reference_fingerprint if decision else None
    if target and stored != current:
        warnings.append("target_reference_state_changed_since_decision")
    target_fp = fingerprint({"contract": CONTRACT, "client_id": client.client_id,
        "retirement_target_date": target, "decision_provenance": PROVENANCE})
    ready = not blockers
    result["retirement_target"] = dict(contract_version=CONTRACT, retirement_target_date=target,
        decision_provenance=PROVENANCE, decision_actor=decision.retirement_target_decision_actor if decision else None,
        decided_at=decision.retirement_target_decided_at if decision else None, relation_to_planning_base=relation,
        retirement_target_ready=ready, blockers=sorted(blockers), warnings=sorted(warnings),
        reference_fingerprint_at_decision=stored, current_reference_fingerprint=current, decision_fingerprint=target_fp)
    result["target_reference_facts"] = facts
    result["ready_for_next_planning_calculation"] = result["planning_input_ready"] and ready
    result["planning_calculation_input_fingerprint"] = fingerprint({"contract": CONTRACT,
        "planning_input_fingerprint": result["planning_input_fingerprint"], "retirement_target_decision_fingerprint": target_fp,
        "current_target_reference_fingerprint": current, "retirement_target_ready": ready, "retirement_target_blockers": sorted(blockers)})


def set_target(db, client_id, payload):
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise PensionProductError("TARGET_REQUIRES_FRESH_TRANSACTION", "נדרשת טרנזקציה חדשה להחלטת היעד", 409)
    dialect = db.get_bind().dialect.name
    connection = db.connection()
    if dialect == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise PensionProductError("UNSUPPORTED_DATABASE", "מסד הנתונים אינו נתמך", 503)
    lock_client(db, client_id)
    decision = db.scalar(select(PlanningInputDecision).where(PlanningInputDecision.client_id == client_id).with_for_update())
    if (decision.version if decision else 0) != payload.expected_version:
        raise PensionProductError("PLANNING_DECISION_STALE", "ההחלטה השתנתה; יש לרענן ולאשר מחדש", 409)
    client = db.get(Client, client_id)
    timings = db.scalars(select(RetirementTimingWorkIntention).where(RetirementTimingWorkIntention.client_id == client_id)).all()
    snapshot = _snapshot(db, client_id, as_of=date.min)
    current = reference_fingerprint(client_id, references(client, timings, snapshot))
    if current != payload.expected_target_reference_fingerprint:
        raise PensionProductError("TARGET_REFERENCE_STATE_STALE", "עובדות הייחוס השתנו; יש לרענן ולאשר מחדש", 409)
    if decision is None:
        decision = PlanningInputDecision(client_id=client_id, version=0, actor="planner:planning-input")
        db.add(decision)
    decision.retirement_target_date = payload.retirement_target_date
    decision.retirement_target_decision_actor = "planner:planning-input" if payload.retirement_target_date else None
    decision.retirement_target_decided_at = datetime.now(timezone.utc) if payload.retirement_target_date else None
    decision.retirement_target_reference_fingerprint = current if payload.retirement_target_date else None
    decision.version += 1
    db.flush()
    return {"decision_version": decision.version}
