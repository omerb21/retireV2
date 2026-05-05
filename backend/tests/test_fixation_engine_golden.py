from __future__ import annotations

from app.engines.fixation_engine import calculate_fixation, calculate_fixation_from_payload
from app.schemas.fixation_contracts import FixationInput, FixationResult, ValidationError


def _base_input() -> dict:
    return {
        "calculation_id": "golden-calc",
        "calculation_version": "v1",
        "eligibility_date": "2026-01-01",
        "eligibility_year": 2026,
        "monthly_cap": 10000.0,
        "exemption_percentage": 0.57,
        "capital_multiplier": 180,
        "grants": [],
        "future_grant_reserved": 0.0,
        "actual_capitalizations": [],
        "idf_relevant": False,
        "idf": None,
    }


def _audit_pairs(result: FixationResult) -> list[tuple[int, str]]:
    return [(row.stage_order, row.category) for row in (result.audit_rows or [])]


SUCCESS_CASES = [
    {
        "case_id": "GC01_BASE_CASE",
        "input": _base_input(),
        "expected_numeric": {
            "initial_exempt_capital": 1026000.0,
            "grant_impact_total": 0.0,
            "future_grant_impact": 0.0,
            "actual_capitalization_impact": 0.0,
            "idf_impact": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 1026000.0,
            "monthly_exempt_pension": 5700.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC02_SINGLE_GRANT_FULL_IMPACT",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_001",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 135000.0,
            "total_impact": 135000.0,
            "remaining_exempt_capital": 891000.0,
            "monthly_exempt_pension": 4950.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC03A_15Y_ONE_DAY_BEFORE_BOUNDARY",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_15y_before",
                    "indexed_amount": 100000.0,
                    "grant_date": "2010-12-31",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 1026000.0,
            "monthly_exempt_pension": 5700.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC03B_15Y_EXACTLY_ON_BOUNDARY",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_15y_exact",
                    "indexed_amount": 100000.0,
                    "grant_date": "2011-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 1026000.0,
            "monthly_exempt_pension": 5700.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC03C_15Y_ONE_DAY_AFTER_BOUNDARY",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_15y_after",
                    "indexed_amount": 100000.0,
                    "grant_date": "2011-01-02",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 135000.0,
            "total_impact": 135000.0,
            "remaining_exempt_capital": 891000.0,
            "monthly_exempt_pension": 4950.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC04A_32Y_FULL_PERIOD",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_32y_full",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 135000.0,
            "total_impact": 135000.0,
            "remaining_exempt_capital": 891000.0,
            "monthly_exempt_pension": 4950.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC04B_32Y_PARTIAL_PERIOD",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_32y_partial",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "2010-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 67500.0,
            "total_impact": 67500.0,
            "remaining_exempt_capital": 958500.0,
            "monthly_exempt_pension": 5325.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC04C_32Y_OVER_CAP",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_32y_over_cap",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1991-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 135000.0,
            "total_impact": 135000.0,
            "remaining_exempt_capital": 891000.0,
            "monthly_exempt_pension": 4950.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC05_MULTIPLE_GRANTS",
        "input": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_multi_included_full",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                },
                {
                    "grant_id": "grant_multi_excluded_15y",
                    "indexed_amount": 80000.0,
                    "grant_date": "2010-12-31",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                },
                {
                    "grant_id": "grant_multi_included_partial",
                    "indexed_amount": 60000.0,
                    "grant_date": "2023-06-01",
                    "work_start_date": "2010-01-01",
                    "work_end_date": "2026-01-01",
                },
            ],
        },
        "expected_numeric": {
            "grant_impact_total": 175500.0,
            "total_impact": 175500.0,
            "remaining_exempt_capital": 850500.0,
            "monthly_exempt_pension": 4725.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC06_ACTUAL_CAPITALIZATION_IMPACT",
        "input": {
            **_base_input(),
            "actual_capitalizations": [
                {
                    "capitalization_id": "cap_001",
                    "amount": 60000.0,
                    "capitalization_date": "2024-06-01",
                }
            ],
        },
        "expected_numeric": {
            "actual_capitalization_impact": 60000.0,
            "total_impact": 60000.0,
            "remaining_exempt_capital": 966000.0,
            "monthly_exempt_pension": 5366.67,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (7, "actual_capitalization"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC07_IDF_INFORMATIONAL_ONLY",
        "input": {
            **_base_input(),
            "idf_relevant": True,
            "idf": {
                "idf_id": "idf_001",
                "reduction_amount": 25000.0,
                "original_commutation_percent": 25.0,
                "current_commutation_percent": 10.0,
                "commutation_date": "2020-01-01",
                "promoter_age_date": "2026-02-01",
                "source_label": "golden_idf_sample",
            },
        },
        "expected_numeric": {
            "idf_impact": 0.0,
            "total_impact": 0.0,
            "remaining_exempt_capital": 1026000.0,
            "monthly_exempt_pension": 5700.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (8, "idf_treatment"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC08_FUTURE_GRANT_RESERVE_ONLY",
        "input": {**_base_input(), "future_grant_reserved": 50000.0},
        "expected_numeric": {
            "future_grant_impact": 67500.0,
            "total_impact": 67500.0,
            "remaining_exempt_capital": 958500.0,
            "monthly_exempt_pension": 5325.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (6, "future_grant_reserve"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC09_COMBINED_FULL_SCENARIO",
        "input": {
            **_base_input(),
            "idf_relevant": True,
            "grants": [
                {
                    "grant_id": "combined_grant_included",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "2010-01-01",
                    "work_end_date": "2026-01-01",
                },
                {
                    "grant_id": "combined_grant_excluded",
                    "indexed_amount": 80000.0,
                    "grant_date": "2010-12-31",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                },
            ],
            "future_grant_reserved": 50000.0,
            "actual_capitalizations": [
                {
                    "capitalization_id": "combined_cap_001",
                    "amount": 60000.0,
                    "capitalization_date": "2024-06-01",
                }
            ],
            "idf": {
                "idf_id": "combined_idf_001",
                "reduction_amount": 25000.0,
                "original_commutation_percent": 25.0,
                "current_commutation_percent": 10.0,
                "commutation_date": "2020-01-01",
                "promoter_age_date": "2026-02-01",
                "source_label": "combined_idf_sample",
            },
        },
        "expected_numeric": {
            "grant_impact_total": 67500.0,
            "future_grant_impact": 67500.0,
            "actual_capitalization_impact": 60000.0,
            "idf_impact": 0.0,
            "total_impact": 195000.0,
            "remaining_exempt_capital": 831000.0,
            "monthly_exempt_pension": 4616.67,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (6, "future_grant_reserve"),
            (7, "actual_capitalization"),
            (8, "idf_treatment"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
    {
        "case_id": "GC10_ZERO_REMAINING_EXEMPTION",
        "input": {
            **_base_input(),
            "monthly_cap": 1000.0,
            "grants": [
                {
                    "grant_id": "zero_floor_grant",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
            "actual_capitalizations": [
                {
                    "capitalization_id": "zero_floor_cap",
                    "amount": 60000.0,
                    "capitalization_date": "2024-06-01",
                }
            ],
        },
        "expected_numeric": {
            "initial_exempt_capital": 102600.0,
            "grant_impact_total": 135000.0,
            "actual_capitalization_impact": 60000.0,
            "total_impact": 195000.0,
            "remaining_exempt_capital": 0.0,
            "monthly_exempt_pension": 0.0,
        },
        "expected_audit": [
            (1, "input_validation"),
            (2, "initial_entitlement"),
            (3, "grant_impact"),
            (4, "15_year_exclusion"),
            (5, "32_year_ratio"),
            (7, "actual_capitalization"),
            (9, "total_impact"),
            (10, "remaining_exemption"),
            (11, "exempt_pension"),
        ],
    },
]


def test_fixation_engine_successful_golden_cases() -> None:
    for case in SUCCESS_CASES:
        result = calculate_fixation(FixationInput(**case["input"]))
        assert result.status == "success", case["case_id"]

        for field_name, expected_value in case["expected_numeric"].items():
            assert getattr(result, field_name) == expected_value, f"{case['case_id']}::{field_name}"

        assert _audit_pairs(result) == case["expected_audit"], case["case_id"]


VALIDATION_CASES = [
    {
        "case_id": "GC11A_VALIDATION_MISSING_GRANT_DATE",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "invalid_missing_grant_date",
                    "grant_date": None,
                    "indexed_amount": 100000.0,
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected": [("grants[0].grant_date", "MISSING_REQUIRED_VALUE")],
    },
    {
        "case_id": "GC11B_VALIDATION_MISSING_IDF_INPUT",
        "payload": {**_base_input(), "idf_relevant": True, "idf": None},
        "expected": [("fixation_input", "INVALID_GLOBAL_INPUT")],
    },
    {
        "case_id": "GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT",
        "payload": {
            "calculation_id": "golden-calc",
            "calculation_version": "v1",
            "eligibility_date": "2026-01-01",
            "eligibility_year": 2026,
            "monthly_cap": 10000.0,
            "exemption_percentage": 0.57,
            "capital_multiplier": 180,
            "grants": [],
            "actual_capitalizations": [],
            "idf_relevant": False,
            "idf": None,
        },
        "expected": [("future_grant_reserved", "MISSING_REQUIRED_VALUE")],
    },
    {
        "case_id": "GC11D_VALIDATION_INVALID_AMOUNT",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "invalid_negative_amount",
                    "indexed_amount": -1000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected": [("grants[0].indexed_amount", "INVALID_NESTED_ITEM")],
    },
    {
        "case_id": "GC11E_VALIDATION_INVALID_DATE",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "invalid_date_grant",
                    "indexed_amount": 100000.0,
                    "grant_date": "not-a-date",
                    "work_start_date": "1994-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected": [("grants[0].grant_date", "INVALID_DATE")],
    },
    {
        "case_id": "GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "invalid_missing_work_period",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": None,
                    "work_end_date": None,
                }
            ],
        },
        "expected": [
            ("grants[0].work_start_date", "INVALID_DATE"),
            ("grants[0].work_end_date", "INVALID_DATE"),
        ],
    },
    {
        "case_id": "GC04D_ZERO_WORK_PERIOD",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_zero_work_period",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": "2026-01-01",
                    "work_end_date": "2026-01-01",
                }
            ],
        },
        "expected": [("grants[0]", "INVALID_NESTED_ITEM")],
    },
    {
        "case_id": "GC04E_MISSING_WORK_PERIOD_CONTEXT",
        "payload": {
            **_base_input(),
            "grants": [
                {
                    "grant_id": "grant_missing_work_period_context",
                    "indexed_amount": 100000.0,
                    "grant_date": "2024-01-01",
                    "work_start_date": None,
                    "work_end_date": None,
                }
            ],
        },
        "expected": [
            ("grants[0].work_start_date", "INVALID_DATE"),
            ("grants[0].work_end_date", "INVALID_DATE"),
        ],
    },
]


def test_fixation_engine_validation_only_golden_cases() -> None:
    for case in VALIDATION_CASES:
        result = calculate_fixation_from_payload(case["payload"])
        assert isinstance(result, list), case["case_id"]
        assert result, case["case_id"]
        assert all(isinstance(err, ValidationError) for err in result), case["case_id"]
        assert not isinstance(result, FixationResult), case["case_id"]

        actual = [(err.path, err.code) for err in result]
        assert actual == case["expected"], case["case_id"]
