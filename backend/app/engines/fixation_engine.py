from __future__ import annotations

from datetime import date
import re
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.schemas.fixation_contracts import (
    ActualCapitalizationInput,
    ActualCapitalizationResult,
    AuditRow,
    FixationInput,
    FixationResult,
    GrantInput,
    GrantResult,
    IDFResult,
    ValidationError,
    map_contract_validation_errors,
)


GRANT_IMPACT_MULTIPLIER = 1.35
IDF_MONTHLY_CAP_FACTOR = 0.35


def _round2(value: float) -> float:
    return round(value, 2)


def _shift_years(base_date: date, years: int) -> date:
    target_year = base_date.year + years
    if (
        base_date.month == 2
        and base_date.day == 29
        and not _is_leap_year(target_year)
    ):
        return date(target_year, 2, 28)
    return base_date.replace(year=target_year)


def _is_leap_year(year: int) -> bool:
    return year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)


def _loc_to_path(loc: tuple[Any, ...]) -> str:
    if not loc:
        return "__root__"

    parts: list[str] = []
    for token in loc:
        if isinstance(token, int):
            if not parts:
                parts.append(f"[{token}]")
            else:
                parts[-1] = f"{parts[-1]}[{token}]"
        else:
            parts.append(str(token))
    return ".".join(parts)


def _payload_value_by_path(payload: dict[str, Any], path: str) -> Any:
    if not path:
        return None

    current: Any = payload
    for token in path.split("."):
        indexed_tokens = re.findall(r"([^\[]+)|\[(\d+)\]", token)
        for key_part, idx_part in indexed_tokens:
            if key_part:
                if not isinstance(current, dict):
                    return None
                current = current.get(key_part)
            elif idx_part:
                if not isinstance(current, list):
                    return None
                idx = int(idx_part)
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
    return current


def _normalize_validation_errors(
    *,
    errors: list[ValidationError],
    input_payload: dict[str, Any],
) -> list[ValidationError]:
    normalized: list[ValidationError] = []
    for error in errors:
        code = error.code
        # Locked validation case GC11A expects grant_date=null to map to missing required value.
        if error.path.endswith(".grant_date") and _payload_value_by_path(input_payload, error.path) is None:
            code = "MISSING_REQUIRED_VALUE"

        normalized.append(
            ValidationError(
                code=code,
                path=error.path,
                message=error.message,
                severity=error.severity,
                source_id=error.source_id,
            )
        )
    return normalized


FixationEngineOutput = FixationResult | list[ValidationError]


def calculate_fixation_from_payload(input_payload: dict[str, Any]) -> FixationEngineOutput:
    try:
        parsed_input = FixationInput(**input_payload)
    except PydanticValidationError as exc:
        return _normalize_validation_errors(
            errors=map_contract_validation_errors(exc),
            input_payload=input_payload,
        )

    return calculate_fixation(parsed_input)


def _is_grant_excluded_15_year_rule(grant_date: date, eligibility_date: date) -> bool:
    threshold = _shift_years(eligibility_date, -15)
    return grant_date <= threshold


def _compute_grant_ratio(grant: GrantInput, eligibility_date: date) -> float:
    window_start = _shift_years(eligibility_date, -32)
    total_work_days = max((grant.work_end_date - grant.work_start_date).days, 0)
    total_days_in_32_year_window = (eligibility_date - window_start).days

    if total_days_in_32_year_window <= 0:
        return 0.0

    ratio = total_work_days / total_days_in_32_year_window
    return min(max(ratio, 0.0), 1.0)


def _full_calendar_months(start_date: date, end_date: date) -> int:
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day < start_date.day:
        months -= 1
    return max(months, 0)


def calculate_fixation(input_data: FixationInput) -> FixationResult:
    audit_rows: list[AuditRow] = []
    grant_results: list[GrantResult] = []
    actual_capitalization_results: list[ActualCapitalizationResult] = []

    row_index = 0

    def add_audit_row(
        *,
        stage_order: int,
        category: str,
        source_id: str | None,
        label: str,
        input_amount: float | None,
        output_amount: float,
        impact_amount: float,
        details: dict[str, Any],
    ) -> None:
        nonlocal row_index
        row_index += 1
        audit_rows.append(
            AuditRow(
                row_id=f"row_{row_index}",
                stage_order=stage_order,
                category=category,
                source_id=source_id,
                label=label,
                input_amount=None if input_amount is None else _round2(input_amount),
                output_amount=_round2(output_amount),
                impact_amount=_round2(impact_amount),
                details=details,
            )
        )

    add_audit_row(
        stage_order=1,
        category="input_validation",
        source_id=None,
        label="input validation passed",
        input_amount=None,
        output_amount=0.0,
        impact_amount=0.0,
        details={"status": "passed"},
    )

    initial_exempt_capital_raw = (
        input_data.monthly_cap * input_data.capital_multiplier * input_data.exemption_percentage
    )

    add_audit_row(
        stage_order=2,
        category="initial_entitlement",
        source_id=None,
        label="initial entitlement",
        input_amount=input_data.monthly_cap,
        output_amount=initial_exempt_capital_raw,
        impact_amount=0.0,
        details={
            "monthly_cap": _round2(input_data.monthly_cap),
            "capital_multiplier": input_data.capital_multiplier,
            "exemption_percentage": input_data.exemption_percentage,
        },
    )

    grant_impact_total_raw = 0.0
    grant_boundary_date = _shift_years(input_data.eligibility_date, -15)
    included_grants: list[dict[str, Any]] = []
    all_grants_15y: list[dict[str, Any]] = []

    for grant in input_data.grants:
        is_excluded = _is_grant_excluded_15_year_rule(grant.grant_date, input_data.eligibility_date)
        if is_excluded:
            work_years_ratio = 0.0
            limited_indexed_amount_raw = 0.0
            grant_impact_raw = 0.0
            exclusion_reason = "excluded_15_year_rule"
        else:
            work_years_ratio = _compute_grant_ratio(grant, input_data.eligibility_date)
            limited_indexed_amount_raw = grant.indexed_amount * work_years_ratio
            grant_impact_raw = grant.indexed_amount * GRANT_IMPACT_MULTIPLIER * work_years_ratio
            exclusion_reason = None

        grant_impact_total_raw += grant_impact_raw
        grant_results.append(
            GrantResult(
                grant_id=grant.grant_id,
                indexed_amount=_round2(grant.indexed_amount),
                limited_indexed_amount=_round2(limited_indexed_amount_raw),
                impact_amount=_round2(grant_impact_raw),
                exclusion_reason=exclusion_reason,
            )
        )

        all_grants_15y.append(
            {
                "source_id": grant.grant_id,
                "grant_date": grant.grant_date.isoformat(),
                "included": not is_excluded,
            }
        )

        if not is_excluded:
            included_grants.append(
                {
                    "source_id": grant.grant_id,
                    "indexed_amount": grant.indexed_amount,
                    "qualifying_amount": limited_indexed_amount_raw,
                    "ratio_32y": work_years_ratio,
                    "work_start_date": grant.work_start_date.isoformat(),
                    "work_end_date": grant.work_end_date.isoformat(),
                    "impact_amount": grant_impact_raw,
                }
            )

    if input_data.grants:
        if len(input_data.grants) == 1:
            only = input_data.grants[0]
            only_included = included_grants[0] if included_grants else None
            stage3_input = only_included["qualifying_amount"] if only_included is not None else only.indexed_amount
            stage3_details: dict[str, Any] = {
                "component_type": "historical_grant",
                "multiplier": GRANT_IMPACT_MULTIPLIER,
                "post_multiplier_impact": _round2(grant_impact_total_raw),
            }
            if only_included is not None:
                stage3_details["pre_multiplier_amount"] = _round2(only_included["qualifying_amount"])
            else:
                stage3_details["excluded_by_15_year_rule"] = True

            add_audit_row(
                stage_order=3,
                category="grant_impact",
                source_id=only.grant_id,
                label="grant impact",
                input_amount=stage3_input,
                output_amount=grant_impact_total_raw,
                impact_amount=grant_impact_total_raw,
                details=stage3_details,
            )

            add_audit_row(
                stage_order=4,
                category="15_year_exclusion",
                source_id=only.grant_id,
                label="15-year exclusion",
                input_amount=only.indexed_amount,
                output_amount=only_included["indexed_amount"] if only_included is not None else 0.0,
                impact_amount=0.0,
                details={
                    "grant_date": only.grant_date.isoformat(),
                    "boundary_date": grant_boundary_date.isoformat(),
                    "included": only_included is not None,
                },
            )
        else:
            add_audit_row(
                stage_order=3,
                category="grant_impact",
                source_id=None,
                label="grant impact",
                input_amount=None,
                output_amount=grant_impact_total_raw,
                impact_amount=grant_impact_total_raw,
                details={
                    "multiplier": GRANT_IMPACT_MULTIPLIER,
                    "grants": [
                        {
                            "source_id": item["source_id"],
                            "pre_multiplier_amount": _round2(item["qualifying_amount"]),
                            "post_multiplier_impact": _round2(item["impact_amount"]),
                        }
                        for item in included_grants
                    ],
                },
            )

            add_audit_row(
                stage_order=4,
                category="15_year_exclusion",
                source_id=None,
                label="15-year exclusion",
                input_amount=None,
                output_amount=sum(item["indexed_amount"] for item in included_grants),
                impact_amount=0.0,
                details={"grants": all_grants_15y},
            )

        if included_grants:
            if len(included_grants) == 1:
                only_included = included_grants[0]
                add_audit_row(
                    stage_order=5,
                    category="32_year_ratio",
                    source_id=only_included["source_id"],
                    label="32-year ratio",
                    input_amount=only_included["indexed_amount"],
                    output_amount=only_included["qualifying_amount"],
                    impact_amount=0.0,
                    details={
                        "work_start_date": only_included["work_start_date"],
                        "work_end_date": only_included["work_end_date"],
                        "ratio_32y": _round2(only_included["ratio_32y"]),
                        "capped": only_included["ratio_32y"] >= 1.0,
                    },
                )
            else:
                add_audit_row(
                    stage_order=5,
                    category="32_year_ratio",
                    source_id=None,
                    label="32-year ratio",
                    input_amount=None,
                    output_amount=sum(item["qualifying_amount"] for item in included_grants),
                    impact_amount=0.0,
                    details={
                        "grants": [
                            {
                                "source_id": item["source_id"],
                                "ratio_32y": _round2(item["ratio_32y"]),
                            }
                            for item in included_grants
                        ]
                    },
                )

    future_grant_impact_raw = input_data.future_grant_reserved * GRANT_IMPACT_MULTIPLIER
    if input_data.future_grant_reserved > 0:
        add_audit_row(
            stage_order=6,
            category="future_grant_reserve",
            source_id=None,
            label="future grant reserve",
            input_amount=input_data.future_grant_reserved,
            output_amount=future_grant_impact_raw,
            impact_amount=future_grant_impact_raw,
            details={
                "component_type": "future_reserve",
                "pre_multiplier_amount": _round2(input_data.future_grant_reserved),
                "multiplier": GRANT_IMPACT_MULTIPLIER,
                "post_multiplier_impact": _round2(future_grant_impact_raw),
                "effect_on_remaining_exemption": _round2(future_grant_impact_raw),
            },
        )

    actual_capitalization_impact_raw = 0.0
    for capitalization in input_data.actual_capitalizations:
        impact_raw = capitalization.amount
        actual_capitalization_impact_raw += impact_raw

        actual_capitalization_results.append(
            ActualCapitalizationResult(
                capitalization_id=capitalization.capitalization_id,
                amount=_round2(capitalization.amount),
                impact_amount=_round2(impact_raw),
            )
        )

        if impact_raw > 0:
            add_audit_row(
                stage_order=7,
                category="actual_capitalization",
                source_id=capitalization.capitalization_id,
                label="actual capitalization impact",
                input_amount=capitalization.amount,
                output_amount=impact_raw,
                impact_amount=impact_raw,
                details={"capitalization_date": capitalization.capitalization_date.isoformat()},
            )

    idf_impact_raw = 0.0
    idf_result: IDFResult | None = None

    if input_data.idf is not None:
        base_reduction_raw = (
            input_data.idf.reduction_amount
            * (input_data.idf.original_commutation_percent / input_data.idf.current_commutation_percent)
        )
        monthly_reduction_for_calc_raw = min(base_reduction_raw, input_data.monthly_cap * IDF_MONTHLY_CAP_FACTOR)
        overlap_months = max(
            _full_calendar_months(max(input_data.idf.commutation_date, input_data.eligibility_date), input_data.idf.promoter_age_date),
            1,
        )

        idf_result = IDFResult(
            idf_id=input_data.idf.idf_id,
            base_reduction=_round2(base_reduction_raw),
            monthly_reduction_for_calc=_round2(monthly_reduction_for_calc_raw),
            overlap_months=float(overlap_months),
            impact_amount=0.0,
            informational_only=True,
        )

        add_audit_row(
            stage_order=8,
            category="idf_treatment",
            source_id=input_data.idf.idf_id,
            label="IDF informational treatment",
            input_amount=input_data.idf.reduction_amount,
            output_amount=0.0,
            impact_amount=0.0,
            details={
                "informational_only": True,
                "no_total_impact_effect": True,
                "no_remaining_exemption_effect": True,
                "no_exempt_pension_effect": True,
            },
        )

    total_impact_raw = (
        grant_impact_total_raw
        + future_grant_impact_raw
        + actual_capitalization_impact_raw
    )

    add_audit_row(
        stage_order=9,
        category="total_impact",
        source_id=None,
        label="total impact aggregation",
        input_amount=None,
        output_amount=total_impact_raw,
        impact_amount=total_impact_raw,
        details={
            "grant_impact": _round2(grant_impact_total_raw),
            "future_reserve_impact": _round2(future_grant_impact_raw),
            "actual_capitalization_impact": _round2(actual_capitalization_impact_raw),
            "idf_excluded_as_informational": True,
        },
    )

    remaining_before_floor_raw = initial_exempt_capital_raw - total_impact_raw
    remaining_exempt_capital_raw = max(remaining_before_floor_raw, 0.0)
    add_audit_row(
        stage_order=10,
        category="remaining_exemption",
        source_id=None,
        label="remaining exemption",
        input_amount=initial_exempt_capital_raw,
        output_amount=remaining_exempt_capital_raw,
        impact_amount=total_impact_raw,
        details={
            "total_impact": _round2(total_impact_raw),
            "remaining_before_floor": _round2(remaining_before_floor_raw),
            "zero_floor_applied": remaining_before_floor_raw < 0,
        },
    )

    monthly_exempt_pension_raw = remaining_exempt_capital_raw / input_data.capital_multiplier

    add_audit_row(
        stage_order=11,
        category="exempt_pension",
        source_id=None,
        label="exempt pension",
        input_amount=remaining_exempt_capital_raw,
        output_amount=monthly_exempt_pension_raw,
        impact_amount=0.0,
        details={"capital_multiplier": input_data.capital_multiplier},
    )

    if initial_exempt_capital_raw == 0:
        capital_exemption_percentage_raw = 0.0
        pension_exemption_percentage_raw = 0.0
    else:
        capital_exemption_percentage_raw = remaining_exempt_capital_raw / initial_exempt_capital_raw
        pension_exemption_percentage_raw = monthly_exempt_pension_raw / input_data.monthly_cap

    return FixationResult(
        calculation_id=input_data.calculation_id,
        calculation_version=input_data.calculation_version,
        status="success",
        validation_errors=[],
        eligibility_date=input_data.eligibility_date,
        eligibility_year=input_data.eligibility_year,
        monthly_cap=input_data.monthly_cap,
        exemption_percentage=input_data.exemption_percentage,
        capital_multiplier=input_data.capital_multiplier,
        initial_exempt_capital=_round2(initial_exempt_capital_raw),
        grant_impact_total=_round2(grant_impact_total_raw),
        future_grant_reserved=input_data.future_grant_reserved,
        future_grant_impact=_round2(future_grant_impact_raw),
        actual_capitalization_impact=_round2(actual_capitalization_impact_raw),
        idf_impact=0.0,
        total_impact=_round2(total_impact_raw),
        remaining_exempt_capital=_round2(remaining_exempt_capital_raw),
        monthly_exempt_pension=_round2(monthly_exempt_pension_raw),
        capital_exemption_percentage=_round2(capital_exemption_percentage_raw),
        pension_exemption_percentage=_round2(pension_exemption_percentage_raw),
        grant_results=grant_results,
        actual_capitalization_results=actual_capitalization_results,
        idf_result=idf_result,
        audit_rows=audit_rows,
    )
