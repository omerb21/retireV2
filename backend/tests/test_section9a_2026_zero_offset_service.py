"""Published 2026 ITA 161d examples; scope must never expand implicitly."""
import pytest

from app.services.section9a_2026_zero_offset_service import (
    Section9aScopeError, calculate_2026_zero_offset_exempt_pension,
)


def case(**changes):
    values = {
        "qualifying_pension_gross_ils": "10000.00",
        "tax_year": 2026,
        "eligibility_verified": True,
        "pension_classification_verified": True,
        "no_exempt_grants_verified": True,
        "no_exempt_commutations_verified": True,
    }
    values.update(changes)
    return calculate_2026_zero_offset_exempt_pension(**values)


def test_official_2026_example_10000_gross():
    result = case()
    assert result["pension_exemption_ils"] == "5422.00"
    assert result["pension_taxable_before_other_tax_rules_ils"] == "4578.00"
    assert result["rights_fixation_approved"] is False
    assert result["income_tax_computed"] is False
    assert result["execution_allowed"] is False


def test_smaller_pension_exempt_only_up_to_income():
    result = case(qualifying_pension_gross_ils="5000.00")
    assert result["pension_exemption_ils"] == "5000.00"
    assert result["pension_taxable_before_other_tax_rules_ils"] == "0.00"


@pytest.mark.parametrize("flag", [
    "eligibility_verified", "pension_classification_verified",
    "no_exempt_grants_verified", "no_exempt_commutations_verified",
])
def test_unproven_professional_prerequisites_block(flag):
    with pytest.raises(Section9aScopeError, match="EVIDENCE_REQUIRED"):
        case(**{flag: False})


@pytest.mark.parametrize("raw", ["-1", "Infinity", "NaN", "1000.001", "abc"])
def test_invalid_amounts_block(raw):
    with pytest.raises(Section9aScopeError, match="AMOUNT_INVALID"):
        case(qualifying_pension_gross_ils=raw)


def test_unknown_tax_year_blocks_instead_of_reusing_2026():
    with pytest.raises(Section9aScopeError, match="TAX_YEAR_NOT_SUPPORTED"):
        case(tax_year=2027)
