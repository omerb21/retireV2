"""Targeted V1-reference permission contract checks; no execution or money mutation."""
import pytest

from app.models.pension_product import COMPONENT_CODES
from app.services.canonical_conversion_matrix import destinations, MATRIX_VERSION
from app.services.pension_product_service import PensionProductError


EXPECTED = {
    "פיצויים_מעסיק_נוכחי": (),
    "פיצויים_לאחר_התחשבנות": ("pension", "capital"),
    "פיצויים_שלא_עברו_התחשבנות": (),
    "פיצויים_ממעסיקים_קודמים_רצף_זכויות": (),
    "פיצויים_ממעסיקים_קודמים_רצף_קצבה": ("pension",),
    "תגמולי_עובד_עד_2000": ("pension", "capital"),
    "תגמולי_עובד_אחרי_2000": ("pension",),
    "תגמולי_עובד_אחרי_2008_לא_משלמת": ("pension",),
    "תגמולי_מעביד_עד_2000": ("pension", "capital"),
    "תגמולי_מעביד_אחרי_2000": ("pension",),
    "תגמולי_מעביד_אחרי_2008_לא_משלמת": ("pension",),
}


@pytest.mark.parametrize("code", tuple(EXPECTED))
def test_default_product_permissions_match_v1_backend_reference(code):
    assert set(COMPONENT_CODES) == set(EXPECTED)
    assert set(destinations(code, "קרן פנסיה")) == set(EXPECTED[code])


def test_investment_and_education_fund_type_overrides_match_v1_backend_reference():
    for code in COMPONENT_CODES:
        assert destinations(code, "גמל להשקעה") == {"pension": "exempt", "capital": "capital_gains"}
        assert destinations(code, "קרן השתלמות") == {"pension": "exempt", "capital": "exempt"}


def test_unknown_component_fails_closed():
    with pytest.raises(PensionProductError):
        destinations("רכיב_לא_מוכר", "קרן פנסיה")


def test_matrix_is_explicitly_versioned():
    assert MATRIX_VERSION == "canonical-component-conversion-matrix-v1"


def test_pre_2000_pension_tax_is_backend_taxable_and_requires_professional_reconciliation():
    # V1 FRONTEND defaults say exempt; both V1/V2 BACKEND say taxable.
    # This test preserves CURRENT backend behavior, not professional tax approval.
    for code in ("תגמולי_עובד_עד_2000", "תגמולי_מעביד_עד_2000"):
        assert destinations(code, "קרן פנסיה")["pension"] == "taxable"
