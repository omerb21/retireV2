"""Retained pure M06 precision and historical manifest contract tests.
Source-dependent mutation tests are replaced by canonical cutover negatives.
"""
from datetime import date
from decimal import Decimal
import copy
import pytest
from app.db.base import load_all_models
from app.models.m06_conversion import M06ConversionRevision
from app.schemas.m06_conversion import M06CoefficientIntent
from app.services import m06_conversion_service as service
load_all_models()

def test_exact_multiplication_and_zero_are_not_missing() -> None:
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount="0.00",
    )
    evidence = type("Evidence", (), {"coefficient_text": "200.1250"})()
    assert service._calculate(row, evidence) == (
        "exact_decimal",
        "0",
        None,
        None,
        "0.00",
    )

def test_exact_multiplication_retains_raw_precision_and_rounds_display_half_up() -> (
    None
):
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount="10.01",
    )
    evidence = type("Evidence", (), {"coefficient_text": "2.500"})()
    assert service._calculate(row, evidence) == (
        "exact_decimal",
        "25.025",
        None,
        None,
        "25.03",
    )

def test_manifest_fingerprint_is_canonical_for_mapping_order() -> None:
    assert service._digest({"b": 2, "a": [3, 1]}) == service._digest(
        {"a": [3, 1], "b": 2}
    )
    assert service._digest({"a": [1, 3], "b": 2}) != service._digest(
        {"a": [3, 1], "b": 2}
    )

def test_documentary_intent_requires_complete_provenance() -> None:
    with pytest.raises(ValueError):
        M06CoefficientIntent(
            authority_class="documentary",
            coefficient="200",
            reason="source",
            applicability_declared=False,
        )

@pytest.mark.parametrize(
    ("coefficient", "code"),
    [("0", "coefficient_zero"), ("-0.01", "coefficient_negative")],
)
def test_coefficient_domain_rejections_have_stable_codes(coefficient, code) -> None:
    with pytest.raises(service.M06ConversionError) as raised:
        service._coefficient(coefficient)
    assert raised.value.code == code

def test_large_exact_multiplication_never_uses_context_rounding() -> None:
    amount = "123456789012345678901234567890.12345"
    coefficient = "987654321098765432109876543210.54321"
    row = M06ConversionRevision(
        mode="monthly_pension_to_capital_equivalent",
        formula_id="m06.monthly_pension_to_capital_equivalent.v1",
        input_amount=amount,
    )
    evidence = type("Evidence", (), {"coefficient_text": coefficient})()
    result = service._calculate(row, evidence)
    with service.localcontext() as context:
        context.prec = 200
        expected = service._decimal_text(Decimal(amount) * Decimal(coefficient))
    assert result[0] == "exact_decimal" and result[1] == expected

def test_material_manifest_change_changes_fingerprint() -> None:
    baseline = {"warnings": ["a", "b"], "coefficient": "200"}
    changed = {"warnings": ["a", "b"], "coefficient": "201"}
    assert service._manifest_fingerprint(baseline) != service._manifest_fingerprint(
        changed
    )

def test_manifest_fingerprint_normalizes_only_unordered_collections() -> None:
    baseline = {
        "mode": "balance_to_monthly_pension",
        "input_identity": "component:one",
        "coefficient": "200.000",
        "warnings": [
            {"warning_id": "b", "classification": "mandatory"},
            {"warning_id": "a", "classification": "mandatory"},
        ],
        "informational_warnings": [
            "stale_warning",
            "newer_ineligible_candidate_exists",
        ],
        "blocking_reasons": ["input_amount_missing", "relevant_source_date_missing"],
        "predecessors": {
            "m05_source_snapshot_digest": "a" * 64,
            "m05_warning_snapshot": [
                {"warning_id": "z", "classification": "informational"},
                {"warning_id": "y", "classification": "informational"},
            ],
            "m05_warning_dispositions": [
                {"warning_id": "b", "confirmed": True, "reason": "two"},
                {"warning_id": "a", "confirmed": True, "reason": "one"},
            ],
        },
    }
    expected = service._manifest_fingerprint(baseline)
    for path in (
        ("warnings",),
        ("informational_warnings",),
        ("blocking_reasons",),
        ("predecessors", "m05_warning_snapshot"),
        ("predecessors", "m05_warning_dispositions"),
    ):
        reordered = copy.deepcopy(baseline)
        container = reordered
        for key in path[:-1]:
            container = container[key]
        container[path[-1]] = list(reversed(container[path[-1]]))
        assert service._manifest_fingerprint(reordered) == expected

    for mutate in (
        lambda item: item.update(coefficient="201.000"),
        lambda item: item.update(mode="monthly_pension_to_capital_equivalent"),
        lambda item: item.update(input_identity="component:two"),
        lambda item: item["predecessors"].update(m05_source_snapshot_digest="b" * 64),
        lambda item: item["predecessors"]["m05_warning_dispositions"][0].update(
            confirmed=False
        ),
    ):
        changed = copy.deepcopy(baseline)
        mutate(changed)
        assert service._manifest_fingerprint(changed) != expected
