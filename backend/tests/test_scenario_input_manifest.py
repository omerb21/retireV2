"""SC-03A manifest invariants: identity, deterministic digest and no execution."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.services import scenario_input_manifest_service as manifest
from app.services.scenario_draft_service import DraftError


class FakeDb:
    def __init__(self, scenario, decisions, product=None, component=None):
        self.scenario, self.decisions = scenario, decisions
        self.product, self.component = product, component
        self.calls = 0

    def scalar(self, statement):
        self.calls += 1
        if self.calls == 1:
            return self.scenario
        return self.product if self.calls % 2 == 0 else self.component

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.decisions)


def _fixture(amount="50.00", version=1):
    scenario = SimpleNamespace(scenario_id="s", client_id=7, version=version, status="draft")
    row = SimpleNamespace(
        decision_id="d", source_product_id="p", source_component_id="c",
        component_code="test-code", amount=Decimal(amount), action="pension",
        effective_date=date(2026, 10, 25), validation_state="unverified",
        product_version_at_review=1, source_fingerprint_at_review="prior",
    )
    product = SimpleNamespace(product_id="p", version=1)
    component = SimpleNamespace(component_id="c", component_code="test-code", balance=Decimal("100.00"))
    return FakeDb(scenario, [row], product, component)


def test_manifest_is_stable_but_not_an_execution_authority(monkeypatch):
    monkeypatch.setattr(manifest, "_source_digest", lambda _p, _c: "canonical")
    first = manifest.build_inert_manifest(_fixture(), 7, "s")
    second = manifest.build_inert_manifest(_fixture(), 7, "s")
    assert first == second
    assert first["execution_allowed"] is False
    assert first["planning_snapshot"] is None
    assert first["financial_result"] is None
    assert first["authority_state"] == "NOT_EVALUATED"
    assert first["decisions"][0]["source"]["source_fingerprint"] == "canonical"


def test_version_and_decision_amount_change_fingerprint(monkeypatch):
    monkeypatch.setattr(manifest, "_source_digest", lambda _p, _c: "canonical")
    first = manifest.build_inert_manifest(_fixture(), 7, "s")
    assert manifest.build_inert_manifest(_fixture(version=2), 7, "s")["manifest_fingerprint"] != first["manifest_fingerprint"]
    assert manifest.build_inert_manifest(_fixture(amount="50.01"), 7, "s")["manifest_fingerprint"] != first["manifest_fingerprint"]


def test_missing_source_is_explicit_and_not_filled_in():
    db = _fixture()
    db.product = None
    result = manifest.build_inert_manifest(db, 7, "s")
    assert result["decisions"][0]["source"] is None
    assert result["execution_allowed"] is False


def test_missing_scenario_never_returns_manifest():
    db = _fixture()
    db.scenario = None
    with pytest.raises(DraftError):
        manifest.build_inert_manifest(db, 7, "s")
