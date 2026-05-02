from __future__ import annotations

from datetime import date
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


def _build_validation_errors(exc: PydanticValidationError) -> list[ValidationError]:
    mapped: list[ValidationError] = []
    for error in exc.errors():
        error_type = str(error.get("type", "validation_error")).lower()
        if "missing" in error_type:
            code = "ERR_REQUIRED_FIELD_MISSING"
        elif "date" in error_type:
            code = "ERR_INVALID_DATE"
        elif "greater" in error_type or "less" in error_type or "number" in error_type:
            code = "ERR_INVALID_NUMERIC_VALUE"
        else:
            code = "ERR_INVALID_INPUT"

        mapped.append(
            ValidationError(
                code=code,
                path=_loc_to_path(tuple(error.get("loc", ()))),
                message=str(error.get("msg", "Invalid input")),
                severity="error",
                source_id=None,
            )
        )

    if mapped:
        return mapped

    return [
        ValidationError(
            code="ERR_INVALID_INPUT",
            path="__root__",
            message="Invalid fixation input",
            severity="error",
            source_id=None,
        )
    ]


def _validation_failed_result(
    validation_errors: list[ValidationError],
    calculation_id: str | None,
    calculation_version: str | None,
) -> FixationResult:
    return FixationResult(
        calculation_id=calculation_id,
        calculation_version=calculation_version,
        status="validation_failed",
        validation_errors=validation_errors,
    )


def calculate_fixation_from_payload(input_payload: dict[str, Any]) -> FixationResult:
    calculation_id = input_payload.get("calculation_id") if isinstance(input_payload, dict) else None
    calculation_version = input_payload.get("calculation_version") if isinstance(input_payload, dict) else None

    try:
        parsed_input = FixationInput(**input_payload)
    except PydanticValidationError as exc:
        return _validation_failed_result(
            validation_errors=_build_validation_errors(exc),
            calculation_id=calculation_id,
            calculation_version=calculation_version,
        )

    return calculate_fixation(parsed_input)


def _is_grant_excluded_15_year_rule(grant_date: date, eligibility_date: date) -> bool:
    threshold = _shift_years(eligibility_date, -15)
    return grant_date < threshold


def _compute_grant_ratio(grant: GrantInput, eligibility_date: date) -> float:
    window_start = _shift_years(eligibility_date, -32)
    effective_work_start = max(grant.work_start_date, window_start)
    effective_work_end = min(grant.work_end_date, eligibility_date)

    eligible_work_days = max((effective_work_end - effective_work_start).days, 0)
    total_days_in_32_year_window = (eligibility_date - window_start).days

    if total_days_in_32_year_window <= 0:
        return 0.0

    ratio = eligible_work_days / total_days_in_32_year_window
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
                category=category,
                source_id=source_id,
                label=label,
                input_amount=None if input_amount is None else _round2(input_amount),
                output_amount=_round2(output_amount),
                impact_amount=_round2(impact_amount),
                details=details,
            )
        )

    initial_exempt_capital_raw = (
        input_data.monthly_cap * input_data.capital_multiplier * input_data.exemption_percentage
    )

    add_audit_row(
        category="initial_entitlement",
        source_id=None,
        label="Initial exempt capital entitlement",
        input_amount=input_data.monthly_cap,
        output_amount=initial_exempt_capital_raw,
        impact_amount=0.0,
        details={
            "capital_multiplier": input_data.capital_multiplier,
            "exemption_percentage": input_data.exemption_percentage,
        },
    )

    grant_impact_total_raw = 0.0
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

        add_audit_row(
            category="grant",
            source_id=grant.grant_id,
            label=f"Grant {grant.grant_id}",
            input_amount=grant.indexed_amount,
            output_amount=grant_impact_raw,
            impact_amount=grant_impact_raw,
            details={
                "work_years_ratio": work_years_ratio,
                "exclusion_reason": exclusion_reason,
                "grant_date": grant.grant_date.isoformat(),
            },
        )

    future_grant_impact_raw = input_data.future_grant_reserved * GRANT_IMPACT_MULTIPLIER
    if input_data.future_grant_reserved > 0:
        add_audit_row(
            category="future_grant_reserve",
            source_id=None,
            label="Future grant reserve impact",
            input_amount=input_data.future_grant_reserved,
            output_amount=future_grant_impact_raw,
            impact_amount=future_grant_impact_raw,
            details={"multiplier": GRANT_IMPACT_MULTIPLIER},
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
                category="actual_capitalization",
                source_id=capitalization.capitalization_id,
                label=f"Actual capitalization {capitalization.capitalization_id}",
                input_amount=capitalization.amount,
                output_amount=impact_raw,
                impact_amount=impact_raw,
                details={"capitalization_date": capitalization.capitalization_date.isoformat()},
            )

    idf_impact_raw = 0.0
    idf_result: IDFResult | None = None

    if input_data.idf is not None:
        overlap_start = max(input_data.idf.commutation_date, input_data.eligibility_date)
        overlap_end = input_data.idf.promoter_age_date
        overlap_months = _full_calendar_months(overlap_start, overlap_end)

        base_reduction_raw = (
            input_data.idf.reduction_amount
            * (input_data.idf.original_commutation_percent / input_data.idf.current_commutation_percent)
        )
        monthly_reduction_for_calc_raw = min(base_reduction_raw, input_data.monthly_cap * IDF_MONTHLY_CAP_FACTOR)
        idf_impact_raw = monthly_reduction_for_calc_raw * overlap_months

        idf_result = IDFResult(
            idf_id=input_data.idf.idf_id,
            base_reduction=_round2(base_reduction_raw),
            monthly_reduction_for_calc=_round2(monthly_reduction_for_calc_raw),
            overlap_months=float(overlap_months),
            impact_amount=_round2(idf_impact_raw),
        )

        add_audit_row(
            category="idf",
            source_id=input_data.idf.idf_id,
            label="IDF impact",
            input_amount=input_data.idf.reduction_amount,
            output_amount=idf_impact_raw,
            impact_amount=idf_impact_raw,
            details={
                "overlap_months": overlap_months,
                "base_reduction": _round2(base_reduction_raw),
                "monthly_reduction_for_calc": _round2(monthly_reduction_for_calc_raw),
            },
        )

    total_impact_raw = (
        grant_impact_total_raw
        + future_grant_impact_raw
        + actual_capitalization_impact_raw
        + idf_impact_raw
    )

    add_audit_row(
        category="total",
        source_id=None,
        label="Total impact",
        input_amount=None,
        output_amount=total_impact_raw,
        impact_amount=total_impact_raw,
        details={},
    )

    remaining_exempt_capital_raw = max(initial_exempt_capital_raw - total_impact_raw, 0.0)
    add_audit_row(
        category="remaining_exemption",
        source_id=None,
        label="Remaining exempt capital",
        input_amount=initial_exempt_capital_raw,
        output_amount=remaining_exempt_capital_raw,
        impact_amount=0.0,
        details={"total_impact": _round2(total_impact_raw)},
    )

    monthly_exempt_pension_raw = remaining_exempt_capital_raw / input_data.capital_multiplier

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
        idf_impact=_round2(idf_impact_raw),
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
