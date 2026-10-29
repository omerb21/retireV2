"""Bounded 2026 section 9A pension exemption arithmetic -- NOT fixation approval.

Authority: Israel Tax Authority 2026 Form 161d guide (2026-02),
https://www.gov.il/BlobFolder/guide/2026-filling-out-form-161d/he/Guides_IncomeTax_filling-out-form-161d-2026.pdf

This deliberately covers ONLY a qualifying pension in a verified zero-offset
case, with no exempt grants and no tax-exempt commutations. It is not a
replacement for rights fixation, the offset formula, pension classification,
tax calculation or an assessor's approval. Do not call without independent
professional eligibility and evidence checks.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

RULE_YEAR = 2026
QUALIFYING_PENSION_CEILING_ILS = Decimal("9430")
TOTAL_EXEMPTION_RATE = Decimal("0.575")
# 2026 ITA published monthly example uses whole NIS 5,422, even though
# multiplying the published ceiling by 57.5% yields 5,422.25.
PUBLISHED_MAX_MONTHLY_EXEMPTION_ILS = Decimal("5422")


class Section9aScopeError(ValueError):
    pass


def _amount(raw: str) -> Decimal:
    if type(raw) is not str or len(raw) > 30:
        raise Section9aScopeError("SECTION9A_2026_AMOUNT_INVALID")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise Section9aScopeError("SECTION9A_2026_AMOUNT_INVALID") from None
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise Section9aScopeError("SECTION9A_2026_AMOUNT_INVALID")
    return amount


def calculate_2026_zero_offset_exempt_pension(
    *, qualifying_pension_gross_ils: str, tax_year: int,
    eligibility_verified: bool, pension_classification_verified: bool,
    no_exempt_grants_verified: bool, no_exempt_commutations_verified: bool,
) -> dict:
    """Calculate published 2026 example only when every prerequisite is proven.

    This function cannot determine eligibility, infer missing facts, perform
    161d allocations or calculate income tax. Its result is non-authoritative.
    """
    if type(tax_year) is not int or tax_year != RULE_YEAR:
        raise Section9aScopeError("SECTION9A_TAX_YEAR_NOT_SUPPORTED")
    if not all(type(x) is bool and x is True for x in (
        eligibility_verified, pension_classification_verified,
        no_exempt_grants_verified, no_exempt_commutations_verified,
    )):
        raise Section9aScopeError("SECTION9A_ZERO_OFFSET_EVIDENCE_REQUIRED")
    gross = _amount(qualifying_pension_gross_ils)
    exempt = min(gross, PUBLISHED_MAX_MONTHLY_EXEMPTION_ILS)
    taxable = gross - exempt
    return {
        "schema_version": "SECTION9A_2026_ZERO_OFFSET_ARITHMETIC_V1",
        "tax_year": RULE_YEAR,
        "qualifying_pension_ceiling_ils": "9430.00",
        "exemption_rate": "0.575",
        "published_max_monthly_exemption_ils": "5422.00",
        "qualifying_pension_gross_ils": f"{gross:.2f}",
        "pension_exemption_ils": f"{exempt:.2f}",
        "pension_taxable_before_other_tax_rules_ils": f"{taxable:.2f}",
        "rights_fixation_approved": False,
        "income_tax_computed": False,
        "execution_allowed": False,
    }
