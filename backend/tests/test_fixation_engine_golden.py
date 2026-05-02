from __future__ import annotations

from collections import defaultdict

from app.engines.fixation_engine import calculate_fixation
from app.schemas.fixation_contracts import FixationInput


def _base_input() -> dict:
    return {
        "calculation_id": "golden-calc",
        "calculation_version": "v1",
        "eligibility_date": "2025-01-01",
        "eligibility_year": 2025,
        "monthly_cap": 1000,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180,
        "grants": [],
        "future_grant_reserved": 0,
        "actual_capitalizations": [],
        "idf": None,
        "metadata": {"source": "golden-phase5"},
    }


GOLDEN_CASES = [
    {
        "case_id": "GOLDEN_01_BASE",
        "case_name": "Base case",
        "input": _base_input(),
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 90000.0,
            "monthly_exempt_pension": 500.0,
            "capital_exemption_percentage": 1.0,
            "pension_exemption_percentage": 0.5,
        },
        "expected_grants": [],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"total": 0.0},
    },
    {
        "case_id": "GOLDEN_02_SINGLE_GRANT",
        "case_name": "Single grant full ratio",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G1",
                    "indexed_amount": 10000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "1980-01-01",
                    "work_end_date": "2025-01-01",
                }
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 13500.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 13500.0,
            "remaining_exempt_capital": 76500.0,
            "monthly_exempt_pension": 425.0,
            "capital_exemption_percentage": 0.85,
            "pension_exemption_percentage": 0.42,
        },
        "expected_grants": [
            {
                "grant_id": "G1",
                "indexed_amount": 10000.0,
                "limited_indexed_amount": 10000.0,
                "impact_amount": 13500.0,
                "exclusion_reason": None,
            }
        ],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "grant", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"grant": 13500.0, "total": 13500.0},
    },
    {
        "case_id": "GOLDEN_03_EXCLUSION_15Y",
        "case_name": "15-year exclusion",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G2",
                    "indexed_amount": 10000,
                    "grant_date": "2009-12-31",
                    "work_start_date": "1980-01-01",
                    "work_end_date": "2025-01-01",
                }
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 90000.0,
            "monthly_exempt_pension": 500.0,
            "capital_exemption_percentage": 1.0,
            "pension_exemption_percentage": 0.5,
        },
        "expected_grants": [
            {
                "grant_id": "G2",
                "indexed_amount": 10000.0,
                "limited_indexed_amount": 0.0,
                "impact_amount": 0.0,
                "exclusion_reason": "excluded_15_year_rule",
            }
        ],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "grant", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"grant": 0.0, "total": 0.0},
    },
    {
        "case_id": "GOLDEN_04_PARTIAL_RATIO_32Y",
        "case_name": "Partial 32-year ratio",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G3",
                    "indexed_amount": 12000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "2017-01-01",
                    "work_end_date": "2025-01-01",
                }
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 4050.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 4050.0,
            "remaining_exempt_capital": 85950.0,
            "monthly_exempt_pension": 477.5,
            "capital_exemption_percentage": 0.95,
            "pension_exemption_percentage": 0.48,
        },
        "expected_grants": [
            {
                "grant_id": "G3",
                "indexed_amount": 12000.0,
                "limited_indexed_amount": 3000.0,
                "impact_amount": 4050.0,
                "exclusion_reason": None,
            }
        ],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "grant", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"grant": 4050.0, "total": 4050.0},
    },
    {
        "case_id": "GOLDEN_05_MULTIPLE_GRANTS",
        "case_name": "Multiple grants",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G4",
                    "indexed_amount": 5000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "1980-01-01",
                    "work_end_date": "2025-01-01",
                },
                {
                    "grant_id": "G5",
                    "indexed_amount": 8000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "2009-01-01",
                    "work_end_date": "2025-01-01",
                },
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 12150.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 12150.0,
            "remaining_exempt_capital": 77850.0,
            "monthly_exempt_pension": 432.5,
            "capital_exemption_percentage": 0.86,
            "pension_exemption_percentage": 0.43,
        },
        "expected_grants": [
            {
                "grant_id": "G4",
                "indexed_amount": 5000.0,
                "limited_indexed_amount": 5000.0,
                "impact_amount": 6750.0,
                "exclusion_reason": None,
            },
            {
                "grant_id": "G5",
                "indexed_amount": 8000.0,
                "limited_indexed_amount": 4000.0,
                "impact_amount": 5400.0,
                "exclusion_reason": None,
            },
        ],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "grant", "grant", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"grant": 12150.0, "total": 12150.0},
    },
    {
        "case_id": "GOLDEN_06_FUTURE_GRANT",
        "case_name": "Future grant reserve",
        "input": {**_base_input(), "future_grant_reserved": 20000},
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 20000,
            "future_grant_impact": 27000.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 27000.0,
            "remaining_exempt_capital": 63000.0,
            "monthly_exempt_pension": 350.0,
            "capital_exemption_percentage": 0.7,
            "pension_exemption_percentage": 0.35,
        },
        "expected_grants": [],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "future_grant_reserve", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"future_grant_reserve": 27000.0, "total": 27000.0},
    },
    {
        "case_id": "GOLDEN_07_ACTUAL_CAPITALIZATION",
        "case_name": "Actual capitalization",
        "input": {
            **_base_input(),
            "actual_capitalizations": [
                {"capitalization_id": "C1", "amount": 1234.56, "capitalization_date": "2023-01-01"},
                {"capitalization_id": "C2", "amount": 765.44, "capitalization_date": "2024-01-01"},
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 2000.0,
            "idf_impact": 0.0,
            "total_impact": 2000.0,
            "remaining_exempt_capital": 88000.0,
            "monthly_exempt_pension": 488.89,
            "capital_exemption_percentage": 0.98,
            "pension_exemption_percentage": 0.49,
        },
        "expected_grants": [],
        "expected_actual_caps": [
            {"capitalization_id": "C1", "amount": 1234.56, "impact_amount": 1234.56},
            {"capitalization_id": "C2", "amount": 765.44, "impact_amount": 765.44},
        ],
        "expected_idf": None,
        "expected_audit_categories": [
            "initial_entitlement",
            "actual_capitalization",
            "actual_capitalization",
            "total",
            "remaining_exemption",
        ],
        "expected_audit_impact_by_category": {"actual_capitalization": 2000.0, "total": 2000.0},
    },
    {
        "case_id": "GOLDEN_08_IDF_FULL_MONTH",
        "case_name": "IDF full-month case",
        "input": {
            **_base_input(),
            "idf": {
                "idf_id": "I1",
                "reduction_amount": 1000,
                "original_commutation_percent": 25,
                "current_commutation_percent": 20,
                "commutation_date": "2025-01-15",
                "promoter_age_date": "2025-04-15",
            },
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 1050.0,
            "total_impact": 1050.0,
            "remaining_exempt_capital": 88950.0,
            "monthly_exempt_pension": 494.17,
            "capital_exemption_percentage": 0.99,
            "pension_exemption_percentage": 0.49,
        },
        "expected_grants": [],
        "expected_actual_caps": [],
        "expected_idf": {
            "idf_id": "I1",
            "base_reduction": 1250.0,
            "monthly_reduction_for_calc": 350.0,
            "overlap_months": 3.0,
            "impact_amount": 1050.0,
        },
        "expected_audit_categories": ["initial_entitlement", "idf", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"idf": 1050.0, "total": 1050.0},
    },
    {
        "case_id": "GOLDEN_09_IDF_PARTIAL_MONTH",
        "case_name": "IDF partial-month zero-impact case",
        "input": {
            **_base_input(),
            "idf": {
                "idf_id": "I2",
                "reduction_amount": 1000,
                "original_commutation_percent": 25,
                "current_commutation_percent": 20,
                "commutation_date": "2025-01-15",
                "promoter_age_date": "2025-02-14",
            },
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 90000.0,
            "monthly_exempt_pension": 500.0,
            "capital_exemption_percentage": 1.0,
            "pension_exemption_percentage": 0.5,
        },
        "expected_grants": [],
        "expected_actual_caps": [],
        "expected_idf": {
            "idf_id": "I2",
            "base_reduction": 1250.0,
            "monthly_reduction_for_calc": 350.0,
            "overlap_months": 0.0,
            "impact_amount": 0.0,
        },
        "expected_audit_categories": ["initial_entitlement", "idf", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"idf": 0.0, "total": 0.0},
    },
    {
        "case_id": "GOLDEN_10_COMBINED",
        "case_name": "Combined scenario",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G6",
                    "indexed_amount": 10000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "2009-01-01",
                    "work_end_date": "2025-01-01",
                }
            ],
            "future_grant_reserved": 5000,
            "actual_capitalizations": [
                {"capitalization_id": "C3", "amount": 1000, "capitalization_date": "2023-01-01"},
                {"capitalization_id": "C4", "amount": 500, "capitalization_date": "2024-01-01"},
            ],
            "idf": {
                "idf_id": "I3",
                "reduction_amount": 1000,
                "original_commutation_percent": 25,
                "current_commutation_percent": 20,
                "commutation_date": "2025-01-15",
                "promoter_age_date": "2025-04-15",
            },
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 6750.0,
            "future_grant_reserved": 5000,
            "future_grant_impact": 6750.0,
            "actual_capitalization_impact": 1500.0,
            "idf_impact": 1050.0,
            "total_impact": 16050.0,
            "remaining_exempt_capital": 73950.0,
            "monthly_exempt_pension": 410.83,
            "capital_exemption_percentage": 0.82,
            "pension_exemption_percentage": 0.41,
        },
        "expected_grants": [
            {
                "grant_id": "G6",
                "indexed_amount": 10000.0,
                "limited_indexed_amount": 5000.0,
                "impact_amount": 6750.0,
                "exclusion_reason": None,
            }
        ],
        "expected_actual_caps": [
            {"capitalization_id": "C3", "amount": 1000.0, "impact_amount": 1000.0},
            {"capitalization_id": "C4", "amount": 500.0, "impact_amount": 500.0},
        ],
        "expected_idf": {
            "idf_id": "I3",
            "base_reduction": 1250.0,
            "monthly_reduction_for_calc": 350.0,
            "overlap_months": 3.0,
            "impact_amount": 1050.0,
        },
        "expected_audit_categories": [
            "initial_entitlement",
            "grant",
            "future_grant_reserve",
            "actual_capitalization",
            "actual_capitalization",
            "idf",
            "total",
            "remaining_exemption",
        ],
        "expected_audit_impact_by_category": {
            "grant": 6750.0,
            "future_grant_reserve": 6750.0,
            "actual_capitalization": 1500.0,
            "idf": 1050.0,
            "total": 16050.0,
        },
    },
    {
        "case_id": "GOLDEN_11_ZERO_REMAINING",
        "case_name": "Zero remaining exemption",
        "input": {**_base_input(), "future_grant_reserved": 70000},
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 0.0,
            "future_grant_reserved": 70000,
            "future_grant_impact": 94500.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 94500.0,
            "remaining_exempt_capital": 0.0,
            "monthly_exempt_pension": 0.0,
            "capital_exemption_percentage": 0.0,
            "pension_exemption_percentage": 0.0,
        },
        "expected_grants": [],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "future_grant_reserve", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"future_grant_reserve": 94500.0, "total": 94500.0},
    },
    {
        "case_id": "GOLDEN_12_RATIO_BOUNDARIES",
        "case_name": "Ratio boundaries",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "G7",
                    "indexed_amount": 4000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "1960-01-01",
                    "work_end_date": "1970-01-01",
                },
                {
                    "grant_id": "G8",
                    "indexed_amount": 4000,
                    "grant_date": "2020-01-01",
                    "work_start_date": "1980-01-01",
                    "work_end_date": "2030-01-01",
                },
            ],
        },
        "expected_numeric": {
            "eligibility_year": 2025,
            "monthly_cap": 1000,
            "exemption_percentage": 0.5,
            "capital_multiplier": 180,
            "initial_exempt_capital": 90000.0,
            "grant_impact_total": 5400.0,
            "future_grant_reserved": 0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 5400.0,
            "remaining_exempt_capital": 84600.0,
            "monthly_exempt_pension": 470.0,
            "capital_exemption_percentage": 0.94,
            "pension_exemption_percentage": 0.47,
        },
        "expected_grants": [
            {
                "grant_id": "G7",
                "indexed_amount": 4000.0,
                "limited_indexed_amount": 0.0,
                "impact_amount": 0.0,
                "exclusion_reason": None,
            },
            {
                "grant_id": "G8",
                "indexed_amount": 4000.0,
                "limited_indexed_amount": 4000.0,
                "impact_amount": 5400.0,
                "exclusion_reason": None,
            },
        ],
        "expected_actual_caps": [],
        "expected_idf": None,
        "expected_audit_categories": ["initial_entitlement", "grant", "grant", "total", "remaining_exemption"],
        "expected_audit_impact_by_category": {"grant": 5400.0, "total": 5400.0},
    },
]


def _assert_grant_results(result, expected_grants: list[dict]) -> None:
    assert result.grant_results is not None
    assert len(result.grant_results) == len(expected_grants)
    for actual, expected in zip(result.grant_results, expected_grants):
        assert actual.grant_id == expected["grant_id"]
        assert actual.indexed_amount == expected["indexed_amount"]
        assert actual.limited_indexed_amount == expected["limited_indexed_amount"]
        assert actual.impact_amount == expected["impact_amount"]
        assert actual.exclusion_reason == expected["exclusion_reason"]


def _assert_actual_cap_results(result, expected_caps: list[dict]) -> None:
    assert result.actual_capitalization_results is not None
    assert len(result.actual_capitalization_results) == len(expected_caps)
    for actual, expected in zip(result.actual_capitalization_results, expected_caps):
        assert actual.capitalization_id == expected["capitalization_id"]
        assert actual.amount == expected["amount"]
        assert actual.impact_amount == expected["impact_amount"]


def _assert_idf_result(result, expected_idf: dict | None) -> None:
    if expected_idf is None:
        assert result.idf_result is None
        return

    assert result.idf_result is not None
    assert result.idf_result.idf_id == expected_idf["idf_id"]
    assert result.idf_result.base_reduction == expected_idf["base_reduction"]
    assert result.idf_result.monthly_reduction_for_calc == expected_idf["monthly_reduction_for_calc"]
    assert result.idf_result.overlap_months == expected_idf["overlap_months"]
    assert result.idf_result.impact_amount == expected_idf["impact_amount"]


def _assert_audit_rows(result, expected_categories: list[str], expected_impact_by_category: dict[str, float]) -> None:
    rows = result.audit_rows or []
    categories = [row.category for row in rows]
    assert categories == expected_categories

    impact_by_category: dict[str, float] = defaultdict(float)
    for row in rows:
        impact_by_category[row.category] += row.impact_amount

    for category, expected_impact in expected_impact_by_category.items():
        assert impact_by_category[category] == expected_impact


def test_fixation_engine_golden_cases() -> None:
    for case in GOLDEN_CASES:
        result = calculate_fixation(FixationInput(**case["input"]))

        assert result.status == "success", case["case_id"]
        for field_name, expected_value in case["expected_numeric"].items():
            assert getattr(result, field_name) == expected_value, f"{case['case_id']}::{field_name}"

        _assert_grant_results(result, case["expected_grants"])
        _assert_actual_cap_results(result, case["expected_actual_caps"])
        _assert_idf_result(result, case["expected_idf"])
        _assert_audit_rows(result, case["expected_audit_categories"], case["expected_audit_impact_by_category"])
