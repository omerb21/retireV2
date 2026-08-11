from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.fixation_engine import AdmittedFixationInput, _admit_fixation_input
from app.models.grant import Grant
from app.schemas.cbs_indexation import CbsIndexationFailure
from app.schemas.fixation_admissibility import (
    FixationAdmissionRequest,
    ResolvedFixationAdmissionInput,
)
from app.schemas.fixation_contracts import (
    FixationInput,
    FixationResult,
    ValidationError,
    map_contract_validation_errors,
)
from app.schemas.m07_calculation_input_resolution import (
    CalculationInputResolutionRequest,
    CalculationInputResolutionResult,
)
from app.services.cbs_indexation_adapter import calculate_cbs_indexation
from app.services.m07_calculation_input_manifest import (
    M08A_FIXATION_CALCULATION_SCOPE,
    M08A_FIXATION_MANIFEST_VERSION,
    M07CalculationInputManifestError,
)
from app.services.m07_calculation_input_resolver import (
    M07CalculationInputReferenceError,
    M07CalculationInputSelectionError,
    resolve_calculation_inputs,
)


CBS_SERVER_CONTROLLED_INPUT_FIELDS = (
    "parameter_set_id",
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
MONEY_QUANTUM = Decimal("0.01")


def caller_supplied_cbs_system_evidence_fields(raw_item: Any) -> list[str]:
    if not isinstance(raw_item, dict):
        return []
    fields = [
        field_name
        for field_name in CBS_SERVER_CONTROLLED_INPUT_FIELDS
        if raw_item.get(field_name) is not None
    ]
    if raw_item.get("indexation_warnings") not in (None, []):
        fields.append("indexation_warnings")
    if raw_item.get("indexation_calculation_status") not in (None, "pending"):
        fields.append("indexation_calculation_status")
    if raw_item.get("indexation_mode") == "cbs_system_calculated":
        fields.append("indexation_mode")
    return fields


def caller_supplied_cbs_system_evidence_paths(payload: dict[str, Any]) -> list[str]:
    raw_grants = payload.get("grants")
    if not isinstance(raw_grants, list):
        return []
    return [
        f"grants[{index}].{field_name}"
        for index, raw_item in enumerate(raw_grants)
        for field_name in caller_supplied_cbs_system_evidence_fields(raw_item)
    ]


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
    client_id: int,
    db_session: Session,
    cbs_calculator=None,
    use_persisted_grants: bool = False,
) -> tuple[
    FixationAdmissionRequest | ResolvedFixationAdmissionInput | None,
    AdmittedFixationInput | None,
    list[ValidationError],
    CalculationInputResolutionResult | None,
]:
    caller_evidence_paths = caller_supplied_cbs_system_evidence_paths(payload)
    caller_grants = payload.get("grants")
    caller_supplied_grant_envelope = bool(
        use_persisted_grants and isinstance(caller_grants, list) and caller_grants
    )
    effective_payload = dict(payload)
    if use_persisted_grants:
        rows = db_session.scalars(
            select(Grant).where(Grant.client_id == client_id).order_by(Grant.grant_id)
        ).all()
        effective_payload["grants_collection_state"] = (
            "items_recorded" if rows else "confirmed_none"
        )
        effective_payload["grants"] = [
            {
                "grant_id": row.grant_id,
                "client_id": client_id,
                "item_type": "exempt_grant",
                "employer_name": row.employer_name,
                "employer_withholding_file_number": row.employer_withholding_file_number,
                "nominal_amount": row.nominal_amount,
                "indexed_amount": None,
                "grant_date": row.grant_date,
                "work_start_date": row.work_start_date,
                "work_end_date": row.work_end_date,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "accepted_value": None,
                "indexation_mode": "cbs_system_calculation_required",
                "source_basis": "direct_m08c_grant_record",
                "status": "recorded",
                "accepted_for_use": True,
                "actor": "system:pkg-012",
                "decision_timestamp": row.updated_at or row.created_at,
            }
            for row in rows
        ]
    try:
        request_context = FixationAdmissionRequest(**effective_payload)
    except PydanticValidationError as exc:
        return None, None, map_contract_validation_errors(exc), None

    errors: list[ValidationError] = []
    parameter_set = request_context.parameter_set
    if parameter_set.client_id != client_id:
        return (
            request_context,
            None,
            [
                _error(
                    "parameter_set.client_id",
                    "parameter set belongs to another client",
                )
            ],
            None,
        )

    resolution_request = CalculationInputResolutionRequest(
        calculation_scope=M08A_FIXATION_CALCULATION_SCOPE,
        manifest_version=M08A_FIXATION_MANIFEST_VERSION,
        b1_evidence_revision_id=(
            request_context.m07_input_reference.b1_evidence_revision_id
        ),
        selections=request_context.m07_input_reference.selections,
    )
    try:
        resolution = resolve_calculation_inputs(
            db_session=db_session,
            client_id=client_id,
            request=resolution_request,
        )
    except M07CalculationInputReferenceError as error:
        return (
            request_context,
            None,
            [
                _error(
                    "m07_input_reference.b1_evidence_revision_id",
                    str(error),
                    code="MISSING_REQUIRED_VALUE",
                )
            ],
            None,
        )
    except M07CalculationInputSelectionError as error:
        return (
            request_context,
            None,
            [
                _error(
                    "m07_input_reference.selections",
                    str(error),
                )
            ],
            None,
        )
    except M07CalculationInputManifestError as error:
        return (
            request_context,
            None,
            [
                _error(
                    "m07_input_reference",
                    str(error),
                )
            ],
            None,
        )

    if resolution.outcome == "missing_inputs":
        return (
            request_context,
            None,
            [
                _error(
                    f"m07_input_reference.{field_code}",
                    f"required calculation input '{field_code}' is missing or invalid",
                    code="MISSING_REQUIRED_VALUE",
                )
                for field_code in resolution.missing_fields
            ],
            resolution,
        )
    if resolution.outcome == "ambiguous_inputs":
        return (
            request_context,
            None,
            [
                _error(
                    f"m07_input_reference.{field.field_code}",
                    (
                        f"calculation input '{field.field_code}' is ambiguous; "
                        "an explicit available-candidate selection is required"
                    ),
                )
                for field in resolution.ambiguous_fields
            ],
            resolution,
        )

    calculation_payload = resolution.calculation_payload
    if (
        calculation_payload is None
        or calculation_payload.client_id != client_id
        or calculation_payload.calculation_scope
        != M08A_FIXATION_CALCULATION_SCOPE
        or calculation_payload.manifest_version
        != M08A_FIXATION_MANIFEST_VERSION
        or calculation_payload.b1_evidence_revision_id
        != request_context.m07_input_reference.b1_evidence_revision_id
        or set(calculation_payload.normalized_selected_values)
        != {"eligibility_date"}
        or set(calculation_payload.source_references) != {"eligibility_date"}
    ):
        return (
            request_context,
            None,
            [
                _error(
                    "m07_input_reference",
                    "resolved calculation input payload does not match M08A admission",
                )
            ],
            resolution,
        )
    normalized_date = calculation_payload.normalized_selected_values[
        "eligibility_date"
    ]
    try:
        if not isinstance(normalized_date, str) or len(normalized_date) != 10:
            raise ValueError
        eligibility_date = date.fromisoformat(normalized_date)
        if eligibility_date.isoformat() != normalized_date:
            raise ValueError
    except ValueError:
        return (
            request_context,
            None,
            [
                _error(
                    "m07_input_reference.eligibility_date",
                    "resolved eligibility_date is not an exact ISO calendar date",
                    code="INVALID_DATE",
                )
            ],
            resolution,
        )

    context = ResolvedFixationAdmissionInput(
        **request_context.model_dump(mode="python", exclude_unset=True),
        eligibility_date=eligibility_date,
        eligibility_year=eligibility_date.year,
        m07_resolution=resolution,
    )

    if use_persisted_grants:
        if caller_supplied_grant_envelope:
            errors.append(
                _error(
                    "grants",
                    "caller-authored grant envelopes are not authoritative; use persisted client grants",
                )
            )
        for path in caller_evidence_paths:
            errors.append(
                _error(path, "CBS indexation evidence is server-produced and cannot be supplied")
            )

    if not parameter_set.accepted_for_use:
        errors.append(_error("parameter_set.accepted_for_use", "parameter set was not accepted for use"))
    if parameter_set.tax_year != context.eligibility_year:
        errors.append(_error("parameter_set.tax_year", "parameter-set tax year does not match eligibility year"))
    if parameter_set.effective_from and context.eligibility_date < parameter_set.effective_from:
        errors.append(_error("parameter_set.effective_from", "parameter set is not yet effective"))
    if parameter_set.effective_to and context.eligibility_date > parameter_set.effective_to:
        errors.append(_error("parameter_set.effective_to", "parameter set is no longer effective"))
    if Decimal(str(parameter_set.values.grant_impact_multiplier)) != Decimal("1.35"):
        errors.append(
            _error(
                "parameter_set.values.grant_impact_multiplier",
                "PKG-012 requires accepted grant_impact_multiplier 1.35",
            )
        )

    for path, state in (
        ("grants_collection_state", context.grants_collection_state),
        ("actual_capitalizations_collection_state", context.actual_capitalizations_collection_state),
    ):
        if state in {"unknown", "not_collected"}:
            errors.append(_error(path, f"collection state '{state}' blocks calculation"))

    for index, item in enumerate(context.grants):
        path = f"grants[{index}]"
        raw_item = (
            {}
            if use_persisted_grants
            else payload.get("grants", [])[index]
        )
        caller_system_fields = caller_supplied_cbs_system_evidence_fields(raw_item)
        for field_name in caller_system_fields:
            errors.append(
                _error(
                    f"{path}.{field_name}",
                    (
                        "CBS-calculated evidence cannot be supplied as authoritative input"
                        if field_name == "indexation_mode"
                        else "indexation evidence fields are system-produced"
                    ),
                    item.grant_id,
                )
            )
        if caller_system_fields:
            item.indexation_mode = "cbs_system_calculation_required"
            item.system_calculated_amount = None
            item.selected_calculation_amount = None
            item.resolved_base_date = None
            item.base_date_source = None
            item.target_date = None
            item.cpi_code = None
            item.cbs_request_evidence = None
            item.cbs_response_evidence = None
            item.indexation_warnings = []
            item.indexation_calculation_status = "pending"
            item.indexation_failure_evidence = None
        if item.client_id != client_id:
            errors.append(
                _error(f"{path}.client_id", "grant indexation context belongs to another client", item.grant_id)
            )
        if use_persisted_grants:
            required_values = {
                "employer_name": item.employer_name,
                "employer_withholding_file_number": item.employer_withholding_file_number,
                "nominal_amount": item.nominal_amount,
            }
            for field_name, value in required_values.items():
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(
                        _error(
                            f"{path}.{field_name}",
                            "legacy grant is incomplete for PKG-012 calculation",
                            item.grant_id,
                            code="MISSING_REQUIRED_VALUE",
                        )
                    )
            if item.grant_date > context.eligibility_date:
                errors.append(
                    _error(
                        f"{path}.grant_date",
                        "grant receipt date cannot be after eligibility date",
                        item.grant_id,
                        code="INVALID_DATE",
                    )
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
        return context, None, errors, resolution

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
            if Decimal(str(accepted_amount)) == Decimal("0"):
                item.indexation_mode = "cbs_system_calculated"
                item.system_calculated_amount = 0
                item.selected_calculation_amount = 0
                item.resolved_base_date = item.grant_date
                item.base_date_source = "grant_date"
                item.target_date = context.eligibility_date
                item.cpi_code = "120010"
                item.indexation_calculation_status = "calculated"
                selected_amount = 0
                admitted_grants.append(
                    {
                        "grant_id": item.grant_id,
                        "client_id": item.client_id,
                        "employer_name": item.employer_name,
                        "employer_withholding_file_number": item.employer_withholding_file_number,
                        "nominal_amount": item.nominal_amount,
                        "indexed_amount": selected_amount,
                        "grant_date": item.grant_date,
                        "work_start_date": item.work_start_date,
                        "work_end_date": item.work_end_date,
                        "parameter_set_id": parameter_set.parameter_set_id,
                    }
                )
                continue
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

            application_amount = outcome.response.raw_to_value.quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
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
                "client_id": item.client_id,
                "employer_name": item.employer_name,
                "employer_withholding_file_number": item.employer_withholding_file_number,
                "nominal_amount": item.nominal_amount,
                "indexed_amount": selected_amount,
                "grant_date": item.grant_date,
                "work_start_date": item.work_start_date,
                "work_end_date": item.work_end_date,
                "parameter_set_id": parameter_set.parameter_set_id,
                "cbs_request_evidence": (
                    item.cbs_request_evidence.model_dump(mode="json")
                    if item.cbs_request_evidence is not None
                    else None
                ),
                "cbs_response_evidence": (
                    item.cbs_response_evidence.model_dump(mode="json")
                    if item.cbs_response_evidence is not None
                    else None
                ),
            }
        )

    if errors:
        return context, None, errors, resolution

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
    return context, _admit_fixation_input(formula_input), [], resolution


def validation_failed_result(
    payload: dict[str, Any],
    errors: list[ValidationError],
    *,
    status: str = "validation_failed",
    m07_resolution: CalculationInputResolutionResult | None = None,
) -> FixationResult:
    calculation_id = payload.get("calculation_id")
    calculation_version = payload.get("calculation_version")
    return FixationResult(
        calculation_id=calculation_id if isinstance(calculation_id, str) else None,
        calculation_version=calculation_version if isinstance(calculation_version, str) else None,
        status=status,
        validation_errors=errors,
        m07_resolution=m07_resolution,
    )
