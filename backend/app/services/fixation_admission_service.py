from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.engines.fixation_engine import AdmittedFixationInput, _admit_fixation_input
from app.schemas.cbs_indexation import CbsIndexationFailure
from app.schemas.fixation_admissibility import AdmissibleFixationInput
from app.schemas.fixation_contracts import (
    FixationInput,
    FixationResult,
    ValidationError,
    map_contract_validation_errors,
)
from app.services.cbs_indexation_adapter import calculate_cbs_indexation


def _error(
    path: str,
    message: str,
    source_id: str | None = None,
    *,
    code: str = "UNSUPPORTED_OR_UNAPPROVED_VALUE",
) -> ValidationError:
    return ValidationError(
        code=code,
        path=path,
        message=message,
        severity="error",
        source_id=source_id,
    )


def parse_and_admit_fixation_payload(
    payload: dict[str, Any],
    *,
    client_id: int | None = None,
    cbs_calculator=None,
) -> tuple[AdmissibleFixationInput | None, AdmittedFixationInput | None, list[ValidationError]]:
    try:
        context = AdmissibleFixationInput(**payload)
    except PydanticValidationError as exc:
        return None, None, map_contract_validation_errors(exc)

    errors: list[ValidationError] = []
    parameter_set = context.parameter_set

    if context.upstream_context.client_id != parameter_set.client_id:
        errors.append(
            _error(
                "parameter_set.client_id",
                "parameter set and upstream context belong to different clients",
            )
        )

    if client_id is not None:
        if context.upstream_context.client_id != client_id:
            errors.append(_error("upstream_context.client_id", "upstream context belongs to another client"))
        if parameter_set.client_id != client_id:
            errors.append(_error("parameter_set.client_id", "parameter set belongs to another client"))

    if context.upstream_context.state not in {"qualified", "warning_reviewed"}:
        errors.append(
            _error(
                "upstream_context.state",
                "only qualified or warning_reviewed M07 context may reach M08",
            )
        )

    if not parameter_set.accepted_for_use:
        errors.append(_error("parameter_set.accepted_for_use", "parameter set was not accepted for use"))
    if parameter_set.tax_year != context.eligibility_year:
        errors.append(_error("parameter_set.tax_year", "parameter-set tax year does not match eligibility year"))
    if parameter_set.effective_from and context.eligibility_date < parameter_set.effective_from:
        errors.append(_error("parameter_set.effective_from", "parameter set is not yet effective"))
    if parameter_set.effective_to and context.eligibility_date > parameter_set.effective_to:
        errors.append(_error("parameter_set.effective_to", "parameter set is no longer effective"))

    for path, state in (
        ("grants_collection_state", context.grants_collection_state),
        ("actual_capitalizations_collection_state", context.actual_capitalizations_collection_state),
    ):
        if state in {"unknown", "not_collected"}:
            errors.append(_error(path, f"collection state '{state}' blocks calculation"))

    for index, item in enumerate(context.grants):
        path = f"grants[{index}]"
        raw_item = payload.get("grants", [])[index]
        if item.indexation_mode != "cbs_system_calculated" and isinstance(raw_item, dict):
            system_evidence_fields = (
                "asserted_indexed_amount",
                "system_calculated_amount",
                "selected_calculation_amount",
                "resolved_base_date",
                "base_date_source",
                "target_date",
                "cpi_code",
                "cbs_request_evidence",
                "cbs_response_evidence",
                "indexation_failure_evidence",
            )
            for field_name in system_evidence_fields:
                if raw_item.get(field_name) is not None:
                    errors.append(
                        _error(
                            f"{path}.{field_name}",
                            "indexation evidence fields are system-produced",
                            item.grant_id,
                        )
                    )
            if raw_item.get("indexation_warnings") not in (None, []):
                errors.append(
                    _error(
                        f"{path}.indexation_warnings",
                        "indexation warnings are system-produced",
                        item.grant_id,
                    )
                )
            if raw_item.get("indexation_calculation_status") not in (None, "pending"):
                errors.append(
                    _error(
                        f"{path}.indexation_calculation_status",
                        "indexation status is system-produced",
                        item.grant_id,
                    )
                )
        if item.client_id != context.upstream_context.client_id:
            errors.append(
                _error(f"{path}.client_id", "grant indexation context belongs to another client", item.grant_id)
            )
        if item.inclusion_decision == "exclude":
            continue
        if not item.accepted_for_use:
            errors.append(_error(f"{path}.accepted_for_use", "included grant was not accepted for use", item.grant_id))
        if item.support_status != "supported":
            errors.append(
                _error(
                    f"{path}.support_status",
                    f"included grant requires '{item.support_status}' handling",
                    item.grant_id,
                )
            )
        if item.indexation_mode == "cbs_system_calculated":
            errors.append(
                _error(
                    f"{path}.indexation_mode",
                    "CBS-calculated evidence cannot be supplied as authoritative input",
                    item.grant_id,
                )
            )

    admitted_capitalizations: list[dict[str, Any]] = []
    for index, item in enumerate(context.actual_capitalizations):
        if item.inclusion_decision == "exclude":
            continue
        path = f"actual_capitalizations[{index}]"
        if not item.accepted_for_use:
            errors.append(
                _error(
                    f"{path}.accepted_for_use",
                    "included actual capitalization was not accepted for use",
                    item.capitalization_id,
                )
            )
        if item.support_status != "supported":
            errors.append(
                _error(
                    f"{path}.support_status",
                    f"included actual capitalization requires '{item.support_status}' handling",
                    item.capitalization_id,
                )
            )
        admitted_capitalizations.append(
            {
                "capitalization_id": item.capitalization_id,
                "amount": item.accepted_value if item.conflict_indicator else item.amount,
                "capitalization_date": item.capitalization_date,
                "source_label": item.source_basis,
                "notes": item.notes,
            }
        )

    future_reserve = context.future_grant_reservation
    if future_reserve is not None and not future_reserve.accepted_for_use:
        errors.append(
            _error(
                "future_grant_reservation.accepted_for_use",
                "future-grant reservation was not accepted for use",
            )
        )

    if context.idf is not None:
        errors.append(
            _error(
                "idf",
                "IDF/security-forces calculation is not supported in PKG-001 and requires special handling",
                context.idf.idf_id,
            )
        )

    if errors:
        return context, None, errors

    admitted_grants: list[dict[str, Any]] = []
    calculator = cbs_calculator or calculate_cbs_indexation
    for index, item in enumerate(context.grants):
        if item.inclusion_decision == "exclude":
            continue

        path = f"grants[{index}]"
        if item.indexation_mode == "asserted_indexed_amount":
            selected_amount = item.accepted_value if item.conflict_indicator else item.indexed_amount
            assert selected_amount is not None
            item.asserted_indexed_amount = selected_amount
            item.selected_calculation_amount = selected_amount
            item.resolved_base_date = item.grant_date
            item.base_date_source = "grant_date"
            item.target_date = context.eligibility_date
            item.indexation_calculation_status = "asserted"
            item.indexation_warnings = [
                "Asserted indexed amount accepted for use; not a CBS system-calculated result"
            ]
        else:
            accepted_amount = item.accepted_value if item.conflict_indicator else item.nominal_amount
            assert accepted_amount is not None
            item.asserted_indexed_amount = item.indexed_amount
            outcome = calculator(
                amount=Decimal(str(accepted_amount)),
                grant_date=item.grant_date,
                work_end_date=item.work_end_date,
                eligibility_date=context.eligibility_date,
            )
            if isinstance(outcome, CbsIndexationFailure):
                item.cbs_request_evidence = outcome.request
                item.indexation_failure_evidence = outcome.failure
                item.indexation_calculation_status = (
                    "unsupported"
                    if outcome.failure.outcome_status == "unsupported_calculation"
                    else "failed"
                )
                item.indexation_warnings = [outcome.failure.safe_technical_message]
                errors.append(
                    _error(
                        f"{path}.indexation_mode",
                        outcome.failure.safe_technical_message,
                        item.grant_id,
                        code=(
                            "CBS_UNSUPPORTED_CALCULATION"
                            if outcome.failure.outcome_status == "unsupported_calculation"
                            else "CBS_CALCULATION_FAILED"
                        ),
                    )
                )
                continue

            application_amount = round(float(outcome.response.raw_to_value), 2)
            item.indexation_mode = "cbs_system_calculated"
            item.system_calculated_amount = application_amount
            item.selected_calculation_amount = application_amount
            item.resolved_base_date = outcome.request.resolved_base_date
            item.base_date_source = outcome.request.base_date_source
            item.target_date = outcome.request.target_date
            item.cpi_code = outcome.request.cpi_code
            item.cbs_request_evidence = outcome.request
            item.cbs_response_evidence = outcome.response
            item.indexation_calculation_status = "calculated"
            item.indexation_warnings = (
                ["Asserted indexed amount retained as provenance and not used for CBS calculation"]
                if item.indexed_amount is not None
                else []
            )
            selected_amount = application_amount

        admitted_grants.append(
            {
                "grant_id": item.grant_id,
                "employer_name": item.employer_name,
                "nominal_amount": item.nominal_amount,
                "indexed_amount": selected_amount,
                "grant_date": item.grant_date,
                "work_start_date": item.work_start_date,
                "work_end_date": item.work_end_date,
            }
        )

    if errors:
        return context, None, errors

    values = parameter_set.values
    formula_input = FixationInput(
        calculation_id=context.calculation_id,
        calculation_version=context.calculation_version,
        eligibility_date=context.eligibility_date,
        eligibility_year=context.eligibility_year,
        monthly_cap=values.monthly_cap,
        exemption_percentage=values.exemption_percentage,
        capital_multiplier=values.capital_multiplier,
        grant_impact_multiplier=values.grant_impact_multiplier,
        grants=admitted_grants,
        future_grant_reserved=0 if future_reserve is None else future_reserve.amount,
        actual_capitalizations=admitted_capitalizations,
        idf=None,
        metadata=context.metadata,
    )
    return context, _admit_fixation_input(formula_input), []


def validation_failed_result(
    payload: dict[str, Any],
    errors: list[ValidationError],
    *,
    status: str = "validation_failed",
) -> FixationResult:
    calculation_id = payload.get("calculation_id")
    calculation_version = payload.get("calculation_version")
    return FixationResult(
        calculation_id=calculation_id if isinstance(calculation_id, str) else None,
        calculation_version=calculation_version if isinstance(calculation_version, str) else None,
        status=status,
        validation_errors=errors,
    )
