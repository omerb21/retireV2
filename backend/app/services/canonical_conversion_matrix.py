"""The sole professional component/destination permission and tax matrix."""
from app.models.pension_product import COMPONENT_CODES
from app.services.pension_product_service import PensionProductError

MATRIX_VERSION = "canonical-component-conversion-matrix-v1"
BASE_MATRIX = dict(zip(COMPONENT_CODES, (
    {}, {"pension": "exempt", "capital": "capital_gains"}, {}, {},
    {"pension": "taxable"}, {"pension": "taxable", "capital": "exempt"},
    {"pension": "taxable"}, {"pension": "taxable"},
    {"pension": "taxable", "capital": "exempt"},
    {"pension": "taxable"}, {"pension": "taxable"},
)))


def destinations(component_code: str, product_type: str) -> dict[str, str]:
    if component_code not in BASE_MATRIX:
        raise PensionProductError("NON_CANONICAL_COMPONENT", "הרכיב אינו רכיב קנוני", 422)
    kind = product_type.lower()
    if any(token in kind for token in ("השתלמות", "education_fund", "klal_stud")):
        return {"pension": "exempt", "capital": "exempt"}
    if any(token in kind for token in ("גמל להשקעה", "investment_provident_fund")):
        return {"pension": "exempt", "capital": "capital_gains"}
    return dict(BASE_MATRIX[component_code])


def tax_for(component_code: str, product_type: str, destination: str) -> str:
    tax = destinations(component_code, product_type).get(destination)
    if tax is None:
        raise PensionProductError("INVALID_COMPONENT_DESTINATION", "היעד אינו מותר לרכיב", 422)
    return tax
