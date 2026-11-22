"""Independent numeric checks for the PTE engine's intermediate values.

The expected values here are derived from the synthetic inputs, not from a
second invocation of the implementation under test.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction

from app.services.pension_target_date_execution_service import execute_source


def _run(*, kind: str, rate: str | None, origin: str, target: str, balance: str, factor: str):
    return execute_source(
        source_id="scenario-decision:acceptance-276:one",
        source_current_state="current",
        monthly_basis={
            "authority_kind": "scenario_decision_balance_ratio",
            "base_amount_representation": {
                "representation_kind": "exact_ratio", "numerator": balance,
                "denominator": factor,
            },
            "base_amount_semantic_fingerprint": "a" * 64,
            "base_amount_source_fingerprint": "b" * 64,
            "basis_authority_ready": True, "basis_blockers": [],
        },
        temporal_authority={
            "temporal_authority_kind": kind,
            "temporal_origin_date": origin, "annual_rate": rate,
            "temporal_semantic_fingerprint": "c" * 64,
            "temporal_source_fingerprint": "d" * 64,
            "temporal_authority_ready": True, "temporal_blockers": [],
        },
        retirement_target={"retirement_target_date": target, "retirement_target_ready": True},
        current_planning_calculation_input_fingerprint="e" * 64,
        supplied_planning_calculation_input_fingerprint="e" * 64,
        supplied_monthly_basis_semantic_fingerprint="a" * 64,
        supplied_monthly_basis_source_fingerprint="b" * 64,
        supplied_temporal_semantic_fingerprint="c" * 64,
        supplied_temporal_source_fingerprint="d" * 64,
        pension_start_date=origin, currency="ILS",
    )


def test_no_indexation_intermediates_and_rounding():
    result = _run(kind="none", rate=None, origin="2026-11-20",
                  target="2027-01-01", balance="600000", factor="200")
    assert result["result_state"] == "result_ready"
    assert result["elapsed_year_fraction"] == {"numerator": "42", "denominator": "365"}
    assert Decimal(result["derived_base_monthly_amount"]) == Decimal("3000")
    assert result["temporal_authority_kind"] == "none"
    assert Decimal(result["temporal_factor"]) == Decimal("1")
    assert Decimal(result["unquantized_target_monthly_amount"]) == Decimal("3000")
    assert result["final_monthly_amount"] == "3000.00"


def test_fixed_manual_indexation_intermediates_against_independent_decimal():
    origin, target = date(2025, 1, 1), date(2026, 1, 1)
    result = _run(kind="fixed_manual", rate="0.12", origin=origin.isoformat(),
                  target=target.isoformat(), balance="600000", factor="200")
    expected_years = Fraction((target - origin).days, 365)
    with localcontext() as ctx:
        ctx.prec = 90
        base = Decimal(600000) / Decimal(200)
        # One full year: 1.12 exactly. No call to the PTE math implementation.
        expected_factor = Decimal("1.12") ** Decimal(expected_years.numerator)
        expected_amount = base * expected_factor
        expected_final = expected_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    assert result["result_state"] == "result_ready"
    assert result["elapsed_year_fraction"] == {"numerator": "1", "denominator": "1"}
    assert result["temporal_authority_kind"] == "fixed_manual"
    assert Decimal(result["temporal_factor"]) == expected_factor
    assert Decimal(result["unquantized_target_monthly_amount"]) == expected_amount
    assert Decimal(result["final_monthly_amount"]) == expected_final == Decimal("3360.00")
