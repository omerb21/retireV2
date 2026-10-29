"""Focused read-only gross goal gap tests; no PTE or M09 execution."""
import pytest
from app.services.scenario_stage6_gross_goal_gap_service import (
    compare_monthly_gross_income_with_goal as compare,
)


def source(rows):
    return {
        "schema_version": "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_V1",
        "client_id": 4, "scenario_id": "scenario-4", "scenario_version": 7,
        "cashflow_fingerprint": "a" * 64, "execution_allowed": False,
        "monthly_rows": rows,
    }


def complete(month, amount):
    return {
        "month": month, "cashflow_state": "COMPLETE",
        "gross_income_total_ils": amount, "blocker_codes": [],
    }


def blocked(month):
    return {
        "month": month, "cashflow_state": "PARTIAL",
        "gross_income_total_ils": None, "blocker_codes": ["SOURCE_BLOCKED"],
    }


def test_shortfall_and_surplus_do_not_infer_net_income():
    result = compare(source([
        complete("2028-01", "5000.00"),
        complete("2028-02", "8500.50"),
    ]), "7000.00")
    assert result["comparison_state"] == "COMPLETE"
    assert result["goal_basis"] == "MONTHLY_GROSS_ILS_NOMINAL_UNINDEXED"
    assert result["monthly_rows"][0]["gross_shortfall_ils"] == "2000.00"
    assert result["monthly_rows"][0]["gross_surplus_ils"] is None
    assert result["monthly_rows"][1]["gross_surplus_ils"] == "1500.50"
    assert result["monthly_rows"][1]["gross_shortfall_ils"] is None
    assert result["execution_allowed"] is False
    assert len(result["comparison_fingerprint"]) == 64


def test_partial_month_never_publishes_gap():
    result = compare(source([
        complete("2028-01", "5000.00"), blocked("2028-02"),
    ]), "6000")
    assert result["comparison_state"] == "PARTIAL"
    assert result["monthly_rows"][1]["gross_income_ils"] is None
    assert result["monthly_rows"][1]["gross_shortfall_ils"] is None
    assert result["monthly_rows"][1]["gross_surplus_ils"] is None


@pytest.mark.parametrize("invalid", ["-1", "Infinity", "NaN", "1000.001", "", "abc"])
def test_invalid_goal_rejected(invalid):
    with pytest.raises(ValueError, match="STAGE6_GOAL_GROSS_AMOUNT_INVALID"):
        compare(source([complete("2028-01", "100.00")]), invalid)


def test_forged_partial_month_with_total_rejected():
    row = blocked("2028-01")
    row["gross_income_total_ils"] = "99999.00"
    with pytest.raises(ValueError, match="STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID"):
        compare(source([row]), "9000")


def test_duplicate_month_rejected():
    with pytest.raises(ValueError, match="STAGE6_GOAL_CASHFLOW_CONTRACT_INVALID"):
        compare(source([complete("2028-01", "100.00")] * 2), "100")


def test_goal_changes_fingerprint_not_source_fingerprint():
    cashflow = source([complete("2028-01", "1000.00")])
    a = compare(cashflow, "1000")
    b = compare(cashflow, "2000")
    assert a["comparison_fingerprint"] != b["comparison_fingerprint"]
    assert a["cashflow_fingerprint"] == b["cashflow_fingerprint"]
