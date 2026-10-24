"""Fail-closed assessment tests; no transaction, authorization or calculation writes."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest

from app.services import scenario_calculation_admission_service as service
from app.services.scenario_draft_service import DraftError


class FakeDb:
    def __init__(self, scenario, decisions, products=None, components=None):
        self.scenario, self.decisions = scenario, decisions
        self.products = products or {}
        self.components = components or {}
        self.calls = 0
    def scalar(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return self.scenario
        # The service selects exactly one product then component per decision.
        index = self.calls - 2
        decision = self.decisions[index // 2]
        return (self.products.get(decision.source_product_id)
                if index % 2 == 0 else self.components.get(decision.source_component_id))
    def scalars(self, _statement):
        return SimpleNamespace(all=lambda: self.decisions)


def scenario(status="draft"):
    return SimpleNamespace(client_id=3, scenario_id="s", status=status, version=4)


def decision(id="d", amount="20.00"):
    return SimpleNamespace(
        decision_id=id, source_product_id="p", source_component_id="c",
        component_code="standard-component-02", amount=Decimal(amount),
        action="pension", effective_date=date(2026, 10, 25),
        validation_state="unverified", product_version_at_review=1,
        source_fingerprint_at_review="known",
    )


def test_absent_and_archived_drafts_fail_closed():
    with pytest.raises(DraftError):
        service.assess(FakeDb(None, []), 3, "s")
    result = service.assess(FakeDb(scenario("archived"), []), 3, "s")
    assert result["assessment_state"] == "blocked"
    assert result["financial_result"] is None
    assert {b["code"] for b in result["blockers"]} == {"SCENARIO_ARCHIVED", "SCENARIO_EMPTY"}


def test_missing_source_has_no_financial_result():
    result = service.assess(FakeDb(scenario(), [decision()]), 3, "s")
    assert result["assessment_state"] == "blocked"
    assert result["financial_result"] is None
    assert result["blockers"] == [{"code": "SOURCE_NOT_FOUND", "decision_id": "d"}]


def test_present_source_still_requires_permissions_tax_and_professional_admission(monkeypatch):
    row = decision()
    product = SimpleNamespace(product_id="p", version=1)
    component = SimpleNamespace(component_id="c", balance=Decimal("10.00"))
    monkeypatch.setattr(service, "_source_digest", lambda _p, _c: "known")
    result = service.assess(FakeDb(scenario(), [row], {"p": product}, {"c": component}), 3, "s")
    codes = {b["code"] for b in result["blockers"]}
    assert "SOURCE_OVERALLOCATED" in codes
    assert "PERMISSION_NOT_ADMITTED" in codes
    assert "PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED" in codes
    assert "TAX_NOT_EVALUATED" in codes
    assert result["financial_result"] is None
