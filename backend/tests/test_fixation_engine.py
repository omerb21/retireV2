from copy import deepcopy
from datetime import date

from app.engines.fixation_engine import (
    _shift_years,
    calculate_fixation,
    calculate_fixation_from_payload,
)
from app.schemas.fixation_contracts import FixationInput, FixationResult, ValidationError


def valid_payload() -> dict:
    return {
        "calculation_id": "calc-1",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2025,
        "monthly_cap": 1000,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180,
        "grant_impact_multiplier": 1.35,
        "grants": [],
        "future_grant_reserved": 0,
        "actual_capitalizations": [],
        "idf": None,
        "metadata": {"trace": "x"},
    }


def test_fixation_engine_base_case_success() -> None:
    result = calculate_fixation(FixationInput(**valid_payload()))

    assert result.status == "success"
    assert result.initial_exempt_capital == 90000.0
    assert result.total_impact == 0.0
    assert result.remaining_exempt_capital == 90000.0
    rows = result.audit_rows or []
    assert [row.category for row in rows] == [
        "initial_entitlement",
        "initial_entitlement",
        "total",
        "remaining_exemption",
        "remaining_exemption",
    ]


def test_fixation_engine_grant_excluded_by_15_year_rule() -> None:
    payload = valid_payload()
    payload["grants"] = [
        {
            "grant_id": "G-OLD",
            "indexed_amount": 100000,
            "grant_date": "2009-12-31",
            "work_start_date": "1995-01-01",
            "work_end_date": "2010-01-01",
        }
    ]

    result = calculate_fixation(FixationInput(**payload))

    assert result.grant_impact_total == 0.0
    assert result.grant_results is not None
    assert result.grant_results[0].impact_amount == 0.0
    assert result.grant_results[0].exclusion_reason == "excluded_15_year_rule"
    grant_rows = [r for r in (result.audit_rows or []) if r.category == "grant" and r.label == "grant impact"]
    assert len(grant_rows) == 1


def test_fixation_engine_grant_included_day_based_ratio() -> None:
    payload = valid_payload()
    payload["grants"] = [
        {
            "grant_id": "G-NEW",
            "indexed_amount": 100000,
            "grant_date": "2020-01-01",
            "work_start_date": "2020-01-01",
            "work_end_date": "2024-01-01",
        }
    ]

    result = calculate_fixation(FixationInput(**payload))

    eligibility_date = date(2025, 1, 1)
    window_start = date(1993, 1, 1)
    expected_ratio = (date(2024, 1, 1) - date(2020, 1, 1)).days / (eligibility_date - window_start).days
    expected_impact = round(100000 * 1.35 * expected_ratio, 2)

    assert result.grant_results is not None
    assert result.grant_results[0].impact_amount == expected_impact


def test_fixation_engine_leap_day_window_start_leap_target_2024() -> None:
    payload = valid_payload()
    payload["eligibility_date"] = "2024-02-29"
    payload["eligibility_year"] = 2024
    payload["grants"] = [
        {
            "grant_id": "G-LEAP-2024",
            "indexed_amount": 100000,
            "grant_date": "2020-01-01",
            "work_start_date": "1992-02-29",
            "work_end_date": "2024-02-29",
        }
    ]

    result = calculate_fixation(FixationInput(**payload))

    expected_impact = round(100000 * payload["grant_impact_multiplier"], 2)

    assert result.grant_results is not None
    assert result.grant_results[0].impact_amount == expected_impact


def test_fixation_engine_leap_day_window_start_leap_target_2020() -> None:
    payload = valid_payload()
    payload["eligibility_date"] = "2020-02-29"
    payload["eligibility_year"] = 2020
    payload["grants"] = [
        {
            "grant_id": "G-LEAP-2020",
            "indexed_amount": 100000,
            "grant_date": "2015-01-01",
            "work_start_date": "1988-02-29",
            "work_end_date": "2020-02-29",
        }
    ]

    result = calculate_fixation(FixationInput(**payload))

    expected_impact = round(100000 * payload["grant_impact_multiplier"], 2)

    assert result.grant_results is not None
    assert result.grant_results[0].impact_amount == expected_impact


def test_shift_years_leap_day_normalizes_to_feb_28_on_non_leap_target() -> None:
    assert _shift_years(date(2020, 2, 29), 1) == date(2021, 2, 28)


def test_fixation_engine_future_grant_impact() -> None:
    payload = valid_payload()
    payload["future_grant_reserved"] = 10000

    result = calculate_fixation(FixationInput(**payload))

    assert result.future_grant_impact == 13500.0


def test_fixation_engine_actual_capitalization_impact() -> None:
    payload = valid_payload()
    payload["actual_capitalizations"] = [
        {"capitalization_id": "C1", "amount": 1000, "capitalization_date": "2023-01-01"},
        {"capitalization_id": "C2", "amount": 500, "capitalization_date": "2024-01-01"},
    ]

    result = calculate_fixation(FixationInput(**payload))

    assert result.actual_capitalization_impact == 1500.0


def test_fixation_engine_idf_full_months() -> None:
    payload = valid_payload()
    payload["idf"] = {
        "idf_id": "I1",
        "reduction_amount": 1000,
        "original_commutation_percent": 25,
        "current_commutation_percent": 20,
        "commutation_date": "2025-01-15",
        "promoter_age_date": "2025-04-16",
    }

    result = calculate_fixation(FixationInput(**payload))

    assert result.idf_result is not None
    assert result.idf_result.overlap_months >= 1
    assert result.idf_result.monthly_reduction_for_calc == 350.0
    assert result.idf_impact == 0.0
    assert result.total_impact == 0.0
    idf_rows = [r for r in (result.audit_rows or []) if r.category == "idf"]
    assert len(idf_rows) == 1
    assert idf_rows[0].impact_amount == 0.0


def test_fixation_engine_15_year_boundary_exactly_on_boundary_is_excluded() -> None:
    payload = valid_payload()
    payload["eligibility_date"] = "2026-01-01"
    payload["eligibility_year"] = 2026
    payload["grants"] = [
        {
            "grant_id": "G-BOUND",
            "indexed_amount": 100000,
            "grant_date": "2011-01-01",
            "work_start_date": "1994-01-01",
            "work_end_date": "2026-01-01",
        }
    ]

    result = calculate_fixation(FixationInput(**payload))

    assert result.grant_impact_total == 0.0
    assert result.grant_results is not None
    assert result.grant_results[0].exclusion_reason == "excluded_15_year_rule"


def test_fixation_engine_zero_entitlement() -> None:
    payload = valid_payload()
    payload["exemption_percentage"] = 0

    result = calculate_fixation(FixationInput(**payload))

    assert result.initial_exempt_capital == 0.0
    assert result.remaining_exempt_capital == 0.0
    assert result.monthly_exempt_pension == 0.0
    assert result.capital_exemption_percentage == 0.0
    assert result.pension_exemption_percentage == 0.0


def test_fixation_engine_echo_fields_are_not_rounded() -> None:
    payload = valid_payload()
    payload["monthly_cap"] = 1000.129
    payload["exemption_percentage"] = 0.3333
    payload["capital_multiplier"] = 179.987
    payload["future_grant_reserved"] = 1234.567

    result = calculate_fixation(FixationInput(**payload))

    assert result.monthly_cap == payload["monthly_cap"]
    assert result.exemption_percentage == payload["exemption_percentage"]
    assert result.capital_multiplier == payload["capital_multiplier"]
    assert result.future_grant_reserved == payload["future_grant_reserved"]


def test_fixation_engine_is_deterministic_and_does_not_mutate_input() -> None:
    payload = valid_payload()
    payload["grants"] = [
        {
            "grant_id": "G-NEW",
            "indexed_amount": 100000,
            "grant_date": "2020-01-01",
            "work_start_date": "2020-01-01",
            "work_end_date": "2024-01-01",
        }
    ]

    input_model = FixationInput(**payload)
    before = deepcopy(input_model.model_dump())

    result_one = calculate_fixation(input_model)
    result_two = calculate_fixation(input_model)

    assert result_one.model_dump() == result_two.model_dump()
    assert input_model.model_dump() == before


def test_fixation_engine_validation_failed_for_invalid_payload() -> None:
    payload = valid_payload()
    del payload["monthly_cap"]

    result = calculate_fixation_from_payload(payload)

    assert isinstance(result, list)
    assert result
    assert all(isinstance(err, ValidationError) for err in result)
    assert not isinstance(result, FixationResult)
