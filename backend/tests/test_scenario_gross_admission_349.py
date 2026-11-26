"""349: the existing Stage 6 gross engine is the ONLY forecast authority."""
from decimal import Decimal
from types import SimpleNamespace

from app.services import scenario_calculation_admission_service as service
from test_scenario_calculation_admission import FakeDb, decision, scenario


def _db(monkeypatch, *, source_version=1, action="pension"):
    row = decision(amount="20.00")
    row.action = action
    row.product_version_at_review = 1
    product = SimpleNamespace(product_id="p", version=source_version)
    component = SimpleNamespace(component_id="c", balance=Decimal("100.00"))
    monkeypatch.setattr(service, "_source_digest", lambda _p, _c: "known")
    return FakeDb(scenario(), [row], {"p": product}, {"c": component})


def _complete():
    return {
        "aggregation_state": "COMPLETE", "scenario_version": 4,
        "monthly_pension_gross_total_ils": "0.10", "aggregate_fingerprint": "a" * 64,
        "comparison_basis": {"currency": "ILS", "income_basis": "GROSS",
                             "retirement_target_date": "2027-01-01",
                             "source_reference_date": "2026-12-01"},
        "blockers": [], "decision_results": [{
            "decision_id": "d", "result_state": "RESULT_READY",
            "monthly_estimate_gross_ils": "0.10", "statement_date": "2026-12-01",
            "retirement_target_date": "2027-01-01", "result_fingerprint": "b" * 64,
            "professional_admission_fingerprint": "c" * 64,
            "coefficient_provenance": {
                "factor_value": "200", "factor_evidence_type": "PLANNER_ASSUMPTION",
                "factor_evidence_reference": "explicit synthetic assumption",
                "admission_revision": 1,
            },
        }],
    }


def test_complete_stage6_evidence_allows_only_labeled_nonbinding_gross(monkeypatch):
    monkeypatch.setattr(service, "build_inert_manifest", lambda *_: {"mock": True})
    monkeypatch.setattr(service, "_partition_verified_manifest", lambda _: {"mock": True})
    monkeypatch.setattr(service, "_aggregate_extension", lambda **_: lambda *_: _complete())
    result = service.assess(_db(monkeypatch), 3, "s", gross_enabled=True)
    assert result["assessment_state"] == "gross_estimate_ready"
    assert result["blockers"] == []
    assert result["financial_result"]["result_type"] == "NONBINDING_GROSS_PENSION_FORECAST"
    assert result["financial_result"]["coefficient_provenance"][0]["factor_evidence_type"] == "PLANNER_ASSUMPTION"
    assert result["financial_result"]["tax_calculated"] is False
    assert result["financial_result"]["net_calculated"] is False
    assert result["warnings"] == ["TAX_NOT_EVALUATED", "NET_NOT_EVALUATED"]


def test_stale_source_blocks_before_engine_is_invoked(monkeypatch):
    monkeypatch.setattr(service, "build_inert_manifest", lambda *_: (_ for _ in ()).throw(AssertionError("engine called")))
    result = service.assess(_db(monkeypatch, source_version=2), 3, "s", gross_enabled=True)
    assert result["assessment_state"] == "blocked"
    assert result["financial_result"] is None
    assert "SOURCE_STALE" in [b["code"] for b in result["blockers"]]


def test_revalidation_status_blocks_even_when_sources_appear_unchanged(monkeypatch):
    db = _db(monkeypatch)
    db.scenario.status = "needs_revalidation"
    monkeypatch.setattr(service, "build_inert_manifest", lambda *_: (_ for _ in ()).throw(AssertionError("engine called")))
    result = service.assess(db, 3, "s", gross_enabled=True)
    assert result["financial_result"] is None
    assert "SCENARIO_NEEDS_REVALIDATION" in [row["code"] for row in result["blockers"]]


def test_non_pension_decision_never_becomes_pension_forecast(monkeypatch):
    result = service.assess(_db(monkeypatch, action="capital_asset"), 3, "s", gross_enabled=True)
    assert result["assessment_state"] == "blocked"
    assert "GROSS_FORECAST_NON_PENSION_DECISION" in [b["code"] for b in result["blockers"]]


def test_missing_coefficient_evidence_blocks_without_number(monkeypatch):
    aggregate = _complete()
    aggregate["decision_results"][0]["coefficient_provenance"]["factor_evidence_reference"] = ""
    monkeypatch.setattr(service, "build_inert_manifest", lambda *_: {})
    monkeypatch.setattr(service, "_partition_verified_manifest", lambda _: {})
    monkeypatch.setattr(service, "_aggregate_extension", lambda **_: lambda *_: aggregate)
    result = service.assess(_db(monkeypatch), 3, "s", gross_enabled=True)
    assert result["financial_result"] is None
    assert "GROSS_FORECAST_COEFFICIENT_PROVENANCE_MISSING" in [b["code"] for b in result["blockers"]]


def test_blocked_stage6_engine_is_not_promoted(monkeypatch):
    aggregate = _complete()
    aggregate.update(aggregation_state="BLOCKED", blockers=["FACTOR_ADMISSION_MISSING"],
                     monthly_pension_gross_total_ils=None)
    monkeypatch.setattr(service, "build_inert_manifest", lambda *_: {})
    monkeypatch.setattr(service, "_partition_verified_manifest", lambda _: {})
    monkeypatch.setattr(service, "_aggregate_extension", lambda **_: lambda *_: aggregate)
    result = service.assess(_db(monkeypatch), 3, "s", gross_enabled=True)
    assert result["assessment_state"] == "blocked"
    assert result["financial_result"] is None
    assert result["blockers"] == [{"code": "FACTOR_ADMISSION_MISSING", "decision_id": None}]
