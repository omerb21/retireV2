"""Synthetic-only canonical PTE smoke tests."""
from render_synthetic_stage6 import SyntheticInput, estimate

def test_one_million_divided_by_two_hundred():
    result = estimate(SyntheticInput(balance="1000000.00", divisor="200"))
    assert result["result"]["result_state"] == "RESULT_READY"
    assert result["result"]["monthly_estimate_gross_ils"] == "5000.00"

def test_two_million_divided_by_two_hundred():
    result = estimate(SyntheticInput(balance="2000000.00", divisor="200"))
    assert result["result"]["result_state"] == "RESULT_READY"
    assert result["result"]["monthly_estimate_gross_ils"] == "10000.00"
