from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M09_SERVICE = ROOT / "app/services/m09_cashflow_service.py"
M09_PATHS = [
    ROOT / "app/models/m09_cashflow.py",
    ROOT / "app/schemas/m09_cashflow.py",
    ROOT / "app/services/m09_cashflow_service.py",
    ROOT / "app/api/m09_cashflow_routes.py",
]


def test_m09_business_arithmetic_is_only_addition_and_subtraction() -> None:
    tree = ast.parse(M09_SERVICE.read_text(encoding="utf-8"))
    prohibited = (ast.Mult, ast.Div, ast.FloorDiv, ast.Pow, ast.Mod)
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.BinOp) and isinstance(node.op, prohibited)]
    source = M09_SERVICE.read_text(encoding="utf-8")
    assert "net = inflow - outflow" in source
    assert "range_inflow += inflow" in source
    assert "range_outflow += outflow" in source


def test_m09_has_no_upstream_formula_or_forbidden_scope_import() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in M09_PATHS).lower()
    forbidden_imports = (
        "m05_ledger_service", "fixation", "cbs", "grant_offset", "tax_",
        "m08", "m07", "npv", "discount_rate", "minimum_pension",
    )
    assert all(term not in source for term in forbidden_imports)
    forbidden_authority_literals = ('decimal("0.03")', "5500", "pension_coefficient", "max_age_for_npv")
    assert all(term not in source for term in forbidden_authority_literals)


def test_m09_consumes_the_m06_authoritative_handoff_without_formula_copy() -> None:
    m09 = M09_SERVICE.read_text(encoding="utf-8")
    m06 = (ROOT / "app/services/m06_conversion_service.py").read_text(encoding="utf-8")
    assert "manifest.authoritative_monthly_amount" in m09
    assert '"formula_owner": "M06"' in m09
    assert "raw_numerator" not in m09 and "raw_denominator" not in m09
    assert "authoritative_monthly_amount" in m06
    assert '"rounding_owner": "M06"' in m06


def test_m09_request_and_ui_have_no_caller_portfolio_authority() -> None:
    schema = (ROOT / "app/schemas/m09_cashflow.py").read_text(encoding="utf-8")
    assert 'ConfigDict(extra="forbid")' in schema
    request_class = schema.split("class M09ContractRequest", 1)[1].split("class M09InventoryResponse", 1)[0]
    for forbidden in ("selected", "component_ids", "required_domains", "confirmed_none", "actor", "eligibility"):
        assert forbidden not in request_class
