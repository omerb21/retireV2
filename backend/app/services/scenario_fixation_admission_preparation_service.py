"""Prepare, but never execute, scenario fixation admission input."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from sqlalchemy import select

from app.engines.fixation_engine import PKG012_GRANT_FORMULA_VERSION
from app.models.actual_capitalization import ActualCapitalization
from app.models.grant import Grant
from app.models.official_parameter_set import OfficialParameterSet
from app.models.scenario_draft import ScenarioDraftDecision
from app.schemas.fixation_admissibility import FixationAdmissionRequest
from app.schemas.m07_calculation_input_resolution import CalculationInputResolutionRequest
from app.services.m07_calculation_input_manifest import (
    M08A_FIXATION_CALCULATION_SCOPE, M08A_FIXATION_MANIFEST_VERSION,
)
from app.services.m07_calculation_input_resolver import (
    resolve_calculation_inputs, M07CalculationInputReferenceError,
    M07CalculationInputSelectionError,
)
from app.services.official_parameter_service import resolve_official_parameter_set
from app.services.scenario_input_manifest_service import _fingerprint
from app.services import scenario_fixation_approval_service as approval

CONTRACT = "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1"
SUPPORTED_VERSIONS = {PKG012_GRANT_FORMULA_VERSION}


def _one(decisions, group):
    rows = [row for row in decisions if row["group"] == group
            and row["determination"] == "PLANNER_ASSERTED"]
    return rows[0] if len(rows) == 1 else None


def prepare(db, client_id: int, scenario_id: str) -> dict:
    review = approval.read(db, client_id, scenario_id)
    decisions = review["decisions"]
    controls = review.get("admission_controls")
    incomplete, blocked = set(), set()
    candidate = None
    preimage = {
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "approval_version": review["approval_version"],
        "approval_fingerprint": review["approval_fingerprint"],
        "current_readiness": review["current_readiness"],
        "decisions": decisions, "admission_controls": controls,
    }
    if review["record_status"] == "MISSING" or controls is None:
        incomplete.add("FIXATION_PREPARATION_CONTROLS_MISSING")
    if review["validity_state"] == "STALE":
        blocked.add("FIXATION_PREPARATION_PROFESSIONAL_REVIEW_STALE")
    if "FIXATION_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in review[
            "current_readiness"]["blockers"]:
        blocked.add("FIXATION_PREPARATION_SOURCE_OVERLAP_UNRESOLVED")
    if controls is not None and controls["calculation_version"] not in SUPPORTED_VERSIONS:
        blocked.add("FIXATION_PREPARATION_CALCULATION_VERSION_UNSUPPORTED")

    eligibility = _one(decisions, "eligibility")
    parameter = _one(decisions, "tax_year_and_parameters")
    eligibility_date = None
    resolution = None
    if eligibility is None or eligibility.get("eligibility_date") is None:
        incomplete.add("FIXATION_PREPARATION_ELIGIBILITY_MISSING")
    else:
        try:
            resolution = resolve_calculation_inputs(
                db_session=db, client_id=client_id,
                request=CalculationInputResolutionRequest(
                    calculation_scope=M08A_FIXATION_CALCULATION_SCOPE,
                    manifest_version=M08A_FIXATION_MANIFEST_VERSION,
                    b1_evidence_revision_id=eligibility["source_id"], selections=[],
                ),
            )
        except (M07CalculationInputReferenceError, M07CalculationInputSelectionError):
            resolution = None
            blocked.add("FIXATION_PREPARATION_ELIGIBILITY_SOURCE_INVALID")
        if resolution is None:
            pass
        elif resolution.outcome != "resolved" or resolution.calculation_payload is None:
            blocked.add("FIXATION_PREPARATION_ELIGIBILITY_NOT_RESOLVED")
        else:
            resolved = resolution.normalized_selected_values.get("eligibility_date")
            if resolved != eligibility["eligibility_date"]:
                blocked.add("FIXATION_PREPARATION_ELIGIBILITY_MISMATCH")
            else:
                eligibility_date = date.fromisoformat(resolved)

    parameter_row = None
    if parameter is None or parameter.get("tax_year") is None or not parameter.get("parameter_set_id"):
        incomplete.add("FIXATION_PREPARATION_PARAMETER_SET_MISSING")
    elif eligibility_date is not None:
        resolved_parameter = resolve_official_parameter_set(
            db_session=db, tax_year=parameter["tax_year"], effective_date=eligibility_date,
        )
        if (resolved_parameter.result != "resolved"
                or resolved_parameter.selected_parameter_set_id != parameter["parameter_set_id"]
                or parameter["source_id"] != parameter["parameter_set_id"]):
            blocked.add("FIXATION_PREPARATION_PARAMETER_SET_NOT_APPLICABLE")
        else:
            parameter_row = db.get(OfficialParameterSet, parameter["parameter_set_id"])

    scenario_decisions = db.scalars(select(ScenarioDraftDecision).where(
        ScenarioDraftDecision.scenario_id == scenario_id,
    )).all()
    pension_ids = {row.decision_id for row in scenario_decisions if row.action == "pension"}
    capital_ids = {row.decision_id for row in scenario_decisions if row.action == "capital_asset"}
    pension_reviews = {row["source_id"] for row in decisions
                       if row["group"] == "pension_classification"
                       and row["determination"] == "PLANNER_ASSERTED"
                       and row.get("tax_classification")}
    capital_reviews = {row["source_id"] for row in decisions
                       if row["group"] == "planned_withdrawal_or_commutation"
                       and row["determination"] == "PLANNER_ASSERTED"
                       and row.get("inclusion_decision") is not None}
    if pension_reviews != pension_ids:
        incomplete.add("FIXATION_PREPARATION_PENSION_CLASSIFICATION_INCOMPLETE")
    if capital_reviews != capital_ids:
        incomplete.add("FIXATION_PREPARATION_PLANNED_CAPITAL_INCOMPLETE")

    grants = db.scalars(select(Grant).where(Grant.client_id == client_id).order_by(Grant.grant_id)).all()
    caps = db.scalars(select(ActualCapitalization).where(
        ActualCapitalization.client_id == client_id).order_by(
            ActualCapitalization.capitalization_id)).all()
    grant_items, cap_items = [], []
    if controls is not None:
        for name, rows, control in (
            ("GRANTS", grants, controls["grants_collection"]),
            ("CAPITALIZATIONS", caps, controls["actual_capitalizations_collection"]),
        ):
            if control["state"] in {"unknown", "not_collected"}:
                incomplete.add(f"FIXATION_PREPARATION_{name}_NOT_COLLECTED")
            elif control["state"] == "confirmed_none" and rows:
                blocked.add(f"FIXATION_PREPARATION_{name}_CONFIRMED_NONE_CONTRADICTS_SOURCE")
            elif control["state"] == "items_recorded" and not rows:
                blocked.add(f"FIXATION_PREPARATION_{name}_ITEMS_MISSING")
        idf = controls["idf"]
        if idf["applicability"] == "NOT_REVIEWED":
            incomplete.add("FIXATION_PREPARATION_IDF_NOT_REVIEWED")

    by_key = {(row["group"], row["source_id"]): row for row in decisions
              if row["determination"] == "PLANNER_ASSERTED"}
    for row in grants:
        decision = by_key.get(("historical_grant", row.grant_id))
        if decision is None:
            incomplete.add("FIXATION_PREPARATION_GRANT_DECISION_MISSING")
            continue
        if decision.get("payment_status") == "UNKNOWN":
            blocked.add("FIXATION_PREPARATION_GRANT_PAYMENT_UNKNOWN")
        grant_items.append({
            "grant_id": row.grant_id, "client_id": client_id,
            "item_type": "exempt_grant", "employer_name": row.employer_name,
            "employer_withholding_file_number": row.employer_withholding_file_number,
            "nominal_amount": row.nominal_amount, "indexed_amount": row.indexed_amount,
            "grant_date": row.grant_date, "work_start_date": row.work_start_date,
            "work_end_date": row.work_end_date,
            "inclusion_decision": decision["inclusion_decision"],
            "support_status": decision["support_status"], "conflict_indicator": False,
            "accepted_value": None, "indexation_mode": (
                "asserted_indexed_amount" if row.indexed_amount is not None
                else "cbs_system_calculation_required"),
            "source_basis": "scenario_professional_review",
            "status": decision["payment_status"],
            "accepted_for_use": decision["accepted_for_use"],
            "actor": review["actor_id"], "decision_timestamp": review["occurred_at"],
        })
    for row in caps:
        decision = by_key.get(("historical_capitalization", row.capitalization_id))
        if decision is None:
            incomplete.add("FIXATION_PREPARATION_CAPITALIZATION_DECISION_MISSING")
            continue
        cap_items.append({
            "capitalization_id": row.capitalization_id, "item_type": "historical_capitalization",
            "amount": float(row.amount), "capitalization_date": row.capitalization_date,
            "recorded_meaning": row.source_basis or "reported_historical_capitalization",
            "inclusion_decision": decision["inclusion_decision"],
            "support_status": decision["support_status"], "conflict_indicator": False,
            "accepted_value": None, "source_basis": "scenario_professional_review",
            "status": "recorded", "accepted_for_use": decision["accepted_for_use"],
            "actor": review["actor_id"], "decision_timestamp": review["occurred_at"],
        })

    if not incomplete and not blocked and controls is not None and parameter_row is not None:
        candidate = {
            "calculation_id": None, "calculation_version": controls["calculation_version"],
            "m07_input_reference": {"b1_evidence_revision_id": eligibility["source_id"],
                                    "selections": []},
            "parameter_set": {
                "parameter_set_id": parameter_row.parameter_set_id, "client_id": client_id,
                "tax_year": parameter_row.tax_year, "effective_from": parameter_row.effective_from,
                "effective_to": parameter_row.effective_to,
                "values": {"monthly_cap": float(parameter_row.monthly_cap),
                           "exemption_percentage": float(parameter_row.exemption_percentage),
                           "capital_multiplier": float(parameter_row.capital_multiplier),
                           "grant_impact_multiplier": float(parameter_row.grant_impact_multiplier)},
                "source_basis": parameter_row.official_source_reference,
                "status": "accepted", "accepted_for_use": True,
                "accepted_by": parameter_row.activated_by,
                "decision_timestamp": parameter_row.activated_at,
            },
            "grants_collection_state": controls["grants_collection"]["state"],
            "grants": grant_items, "future_grant_reservation": None,
            "actual_capitalizations_collection_state": controls[
                "actual_capitalizations_collection"]["state"],
            "actual_capitalizations": cap_items,
            "idf": controls["idf"]["input"] if controls["idf"]["applicability"] == "APPLICABLE" else None,
            "metadata": {"scenario_contract": CONTRACT,
                         "professional_controls_fingerprint": _fingerprint(controls)},
        }
        candidate = FixationAdmissionRequest.model_validate(candidate).model_dump(mode="json")
        preimage["candidate"] = candidate

    state = "BLOCKED" if blocked else "INCOMPLETE" if incomplete else "PREPARED"
    fingerprint = _fingerprint(preimage)
    return {
        "contract": CONTRACT, "client_id": client_id, "scenario_id": scenario_id,
        "state": state, "candidate": candidate,
        "incomplete_reasons": sorted(incomplete), "blockers": sorted(blocked),
        "preparation_fingerprint": fingerprint,
        "professional_authority": False, "execution_allowed": False,
        "tax_authority_approval": None,
    }
