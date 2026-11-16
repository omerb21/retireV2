"""Static eligibility review for a prepared scenario fixation candidate.

This service deliberately stops before full admission.  It never invokes CBS,
the fixation engine, or a write path, and it does not confer professional or
tax authority.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.engines.fixation_engine import PKG012_GRANT_FORMULA_VERSION
from app.schemas.fixation_admissibility import FixationAdmissionRequest
from app.services import scenario_fixation_admission_preparation_service as preparation
from app.services import scenario_fixation_approval_service as approval
from app.services.scenario_input_manifest_service import _fingerprint


CONTRACT = "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1"
SUPPORTED_VERSIONS = {PKG012_GRANT_FORMULA_VERSION}


def _reason(code: str, *source_ids: str | None) -> dict[str, Any]:
    return {
        "code": code,
        "source_ids": sorted({value for value in source_ids if value}),
    }


def _result(
    *,
    client_id: int,
    scenario_id: str,
    prepared: dict[str, Any],
    state: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    unique = {
        (item["code"], tuple(sorted(set(item["source_ids"]))))
        for item in reasons
    }
    ordered = sorted(
        ({"code": code, "source_ids": list(source_ids)}
         for code, source_ids in unique),
        key=lambda item: (item["code"], item["source_ids"]),
    )
    preimage = {
        "contract": CONTRACT,
        "client_id": client_id,
        "scenario_id": scenario_id,
        "preparation_fingerprint": prepared["preparation_fingerprint"],
        "state": state,
        "reasons": ordered,
    }
    return {
        **preimage,
        "eligibility_fingerprint": _fingerprint(preimage),
        "professional_authority": False,
        "execution_allowed": False,
        "admission_review_required": state == "ELIGIBLE_FOR_ADMISSION_REVIEW",
        "tax_authority_approval": None,
    }


def _selected_eligibility_date(review: dict[str, Any]) -> date | None:
    values = {
        row.get("eligibility_date")
        for row in review["decisions"]
        if row["group"] == "eligibility"
        and row["determination"] == "PLANNER_ASSERTED"
        and row.get("eligibility_date")
    }
    if len(values) != 1:
        return None
    try:
        return date.fromisoformat(values.pop())
    except (TypeError, ValueError):
        return None


def assess(db, client_id: int, scenario_id: str) -> dict[str, Any]:
    """Return static eligibility only; never run full admission or calculation."""
    prepared = preparation.prepare(db, client_id, scenario_id)
    if prepared["state"] != "PREPARED":
        reason_codes = (
            prepared["incomplete_reasons"]
            if prepared["state"] == "INCOMPLETE"
            else prepared["blockers"]
        )
        return _result(
            client_id=client_id,
            scenario_id=scenario_id,
            prepared=prepared,
            state=prepared["state"],
            reasons=[_reason(code) for code in reason_codes],
        )

    try:
        candidate = FixationAdmissionRequest.model_validate(prepared["candidate"])
    except (ValidationError, TypeError, ValueError):
        return _result(
            client_id=client_id,
            scenario_id=scenario_id,
            prepared=prepared,
            state="BLOCKED",
            reasons=[_reason("FIXATION_ELIGIBILITY_PREPARED_CANDIDATE_INVALID")],
        )

    review = approval.read(db, client_id, scenario_id)
    eligibility_date = _selected_eligibility_date(review)
    blockers: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []

    if candidate.calculation_version not in SUPPORTED_VERSIONS:
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_CALCULATION_VERSION_UNSUPPORTED",
            candidate.calculation_version,
        ))
    parameter = candidate.parameter_set
    if parameter.client_id != client_id:
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_PARAMETER_CLIENT_MISMATCH",
            parameter.parameter_set_id,
        ))
    if not parameter.accepted_for_use or parameter.status != "accepted":
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_PARAMETER_SET_NOT_ACCEPTED",
            parameter.parameter_set_id,
        ))
    if eligibility_date is None:
        blockers.append(_reason("FIXATION_ELIGIBILITY_DATE_NOT_BOUND"))
    else:
        if parameter.tax_year != eligibility_date.year:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_PARAMETER_TAX_YEAR_MISMATCH",
                parameter.parameter_set_id,
            ))
        if parameter.effective_from and eligibility_date < parameter.effective_from:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_PARAMETER_NOT_YET_EFFECTIVE",
                parameter.parameter_set_id,
            ))
        if parameter.effective_to and eligibility_date > parameter.effective_to:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_PARAMETER_EXPIRED",
                parameter.parameter_set_id,
            ))
    if Decimal(str(parameter.values.grant_impact_multiplier)) != Decimal("1.35"):
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_GRANT_MULTIPLIER_UNSUPPORTED",
            parameter.parameter_set_id,
        ))

    for item in candidate.grants:
        if item.client_id != client_id:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_CLIENT_MISMATCH", item.grant_id,
            ))
        if item.inclusion_decision == "exclude":
            continue
        if not item.employer_name or not item.employer_name.strip():
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_EMPLOYER_MISSING", item.grant_id,
            ))
        if (not item.employer_withholding_file_number
                or not item.employer_withholding_file_number.strip()):
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_WITHHOLDING_FILE_MISSING", item.grant_id,
            ))
        if eligibility_date is not None and item.grant_date > eligibility_date:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_AFTER_ELIGIBILITY_DATE", item.grant_id,
            ))
        if not item.accepted_for_use:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_NOT_ACCEPTED", item.grant_id,
            ))
        if item.support_status != "supported":
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_SUPPORT_UNRESOLVED", item.grant_id,
            ))
        selected_amount = item.accepted_value if item.conflict_indicator else item.nominal_amount
        if selected_amount is None and item.indexation_mode == "cbs_system_calculation_required":
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_GRANT_AMOUNT_MISSING", item.grant_id,
            ))
        elif (item.indexation_mode == "cbs_system_calculation_required"
              and Decimal(str(selected_amount)) > 0):
            external.append(_reason(
                "FIXATION_ELIGIBILITY_CBS_INDEXATION_REQUIRED", item.grant_id,
            ))

    for item in candidate.actual_capitalizations:
        if item.inclusion_decision == "exclude":
            continue
        if not item.accepted_for_use:
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_CAPITALIZATION_NOT_ACCEPTED",
                item.capitalization_id,
            ))
        if item.support_status != "supported":
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_CAPITALIZATION_SUPPORT_UNRESOLVED",
                item.capitalization_id,
            ))

    if candidate.future_grant_reservation is not None:
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_FUTURE_GRANT_NOT_REPRESENTED_BY_PREPARATION",
        ))
    if candidate.idf is not None:
        blockers.append(_reason(
            "FIXATION_ELIGIBILITY_IDF_UNSUPPORTED", candidate.idf.idf_id,
        ))

    for decision in review["decisions"]:
        if decision["determination"] != "PLANNER_ASSERTED":
            continue
        if decision["group"] == "severance_continuity":
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_CONTINUITY_NOT_REPRESENTED_BY_ADMISSION",
                decision["source_id"],
            ))
        elif (decision["group"] == "planned_withdrawal_or_commutation"
              and decision.get("inclusion_decision") == "include"):
            blockers.append(_reason(
                "FIXATION_ELIGIBILITY_PLANNED_WITHDRAWAL_NOT_REPRESENTED_BY_ADMISSION",
                decision["source_id"],
            ))

    if blockers:
        state, reasons = "BLOCKED", blockers
    elif external:
        state, reasons = "REQUIRES_EXTERNAL_VALIDATION", external
    else:
        state, reasons = "ELIGIBLE_FOR_ADMISSION_REVIEW", []
    return _result(
        client_id=client_id,
        scenario_id=scenario_id,
        prepared=prepared,
        state=state,
        reasons=reasons,
    )
