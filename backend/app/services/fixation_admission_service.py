from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.schemas.fixation_admissibility import AdmissibleFixationInput
from app.schemas.fixation_contracts import (
    FixationInput,
    FixationResult,
    ValidationError,
    map_contract_validation_errors,
)


def _error(path: str, message: str, source_id: str | None = None) -> ValidationError:
    return ValidationError(
        code="UNSUPPORTED_OR_UNAPPROVED_VALUE",
        path=path,
        message=message,
        severity="error",
        source_id=source_id,
    )


def parse_and_admit_fixation_payload(
    payload: dict[str, Any],
    *,
    client_id: int | None = None,
) -> tuple[AdmissibleFixationInput | None, FixationInput | None, list[ValidationError]]:
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

    admitted_grants: list[dict[str, Any]] = []
    for index, item in enumerate(context.grants):
        if item.inclusion_decision == "exclude":
            continue
        path = f"grants[{index}]"
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
        admitted_grants.append(
            {
                "grant_id": item.grant_id,
                "employer_name": item.employer_name,
                "nominal_amount": item.nominal_amount,
                "indexed_amount": item.accepted_value if item.conflict_indicator else item.indexed_amount,
                "grant_date": item.grant_date,
                "work_start_date": item.work_start_date,
                "work_end_date": item.work_end_date,
            }
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

    values = parameter_set.values
    engine_input = FixationInput(
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
    return context, engine_input, []


def validation_failed_result(
    payload: dict[str, Any], errors: list[ValidationError]
) -> FixationResult:
    calculation_id = payload.get("calculation_id")
    calculation_version = payload.get("calculation_version")
    return FixationResult(
        calculation_id=calculation_id if isinstance(calculation_id, str) else None,
        calculation_version=calculation_version if isinstance(calculation_version, str) else None,
        status="validation_failed",
        validation_errors=errors,
    )
