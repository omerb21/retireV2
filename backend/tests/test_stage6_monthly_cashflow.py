"""Focused monthly cashflow projection tests; historical M09 remains unused."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.db.base import load_all_models
from app.models.retirement_facts import RecurringIncome
from app.services import scenario_stage6_monthly_cashflow_service as subject
from app.services import scenario_stage6_single_pension_estimate_service as estimate_service
from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError

load_all_models()


def ready(decision_id: str, amount: str = "5000.00", *,
          start: str = "2027-02-01", statement: str = "2026-09-30") -> dict:
    source_id = f"scenario-decision:scenario:{decision_id}"
    values = {
        "schema_version": "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
        "client_id": 1, "scenario_id": "scenario", "scenario_version": 2,
        "decision_id": decision_id, "source_id": source_id,
        "result_state": "RESULT_READY", "execution_allowed": True,
        "blockers": [],
        "coefficient_provenance": {
            "source_level": "MANUAL_PROFESSIONAL_OVERRIDE", "factor_value": "200",
            "factor_evidence_type": "PLANNER_ASSUMPTION",
            "factor_evidence_reference": "professional evidence",
            "payout_option_name": "standard", "admission_revision": 1,
        },
        "professional_admission_fingerprint": "1" * 64,
        "planning_calculation_input_fingerprint": "2" * 64,
        "monthly_basis_semantic_fingerprint": "3" * 64,
        "monthly_basis_source_fingerprint": "4" * 64,
        "temporal_semantic_fingerprint": "5" * 64,
        "temporal_source_fingerprint": "6" * 64,
        "pte_source_execution_fingerprint": "7" * 64,
        "pte_source_result_fingerprint": "8" * 64,
        "monthly_estimate_gross_ils": amount,
        "retirement_target_date": start, "statement_date": statement,
    }
    return estimate_service._seal(values)


def decision(decision_id: str, product: str, component: str) -> dict:
    return {
        "decision_id": decision_id, "product_id": product,
        "component_id": component, "component_code": component,
        "action": "pension",
    }


def pair(*decisions: dict) -> dict:
    return {
        "manifest": {
            "client_id": 1, "scenario_id": "scenario", "scenario_version": 2,
            "manifest_fingerprint": "a" * 64, "decisions": list(decisions),
        },
        "candidate": {},
    }


class FakeDb:
    def __init__(self, *, elections=(), incomes=(), resolutions=()):
        self.values = [list(elections), list(incomes), list(resolutions)]

    def scalars(self, _statement):
        return self.values.pop(0)


def run(monkeypatch, evidence, results, *, incomes=(), resolutions=(),
        start_month="2027-01", end_month="2027-03"):
    def extension(*, decision_id, **_kwargs):
        value = results[decision_id]
        if isinstance(value, BaseException):
            return lambda _db, _pair: (_ for _ in ()).throw(value)
        return lambda _db, _pair: value
    monkeypatch.setattr(subject, "_stage6_identity_extension", extension)
    return subject._cashflow_extension(
        client_id=1, scenario_id="scenario",
        start_month=start_month, end_month=end_month,
    )(FakeDb(incomes=incomes, resolutions=resolutions), evidence)


def recurring(**overrides) -> RecurringIncome:
    values = {
        "id": 11, "client_id": 1, "income_category": "rental",
        "description": "שכירות", "amount": Decimal("1200.00"),
        "amount_basis": "gross", "frequency": "monthly",
        "continuation_status": "ongoing", "lifecycle_status": "current",
        "source_status": "planner entered", "verification_state": "reviewed",
        "start_date": date(2027, 1, 1), "end_date": None,
        "source_type": None, "source_date": date(2026, 12, 31),
        "source_note": None,
    }
    values.update(overrides)
    return RecurringIncome(**values)


def test_one_pension_activates_in_its_start_month(monkeypatch):
    result = run(
        monkeypatch, pair(decision("d1", "p1", "c1")),
        {"d1": ready("d1")},
    )
    assert result["cashflow_state"] == "COMPLETE"
    assert [row["gross_income_total_ils"] for row in result["monthly_rows"]] == [
        "0.00", "5000.00", "5000.00",
    ]
    assert result["monthly_rows"][1]["contributions"] == [{
        "source_id": "scenario-decision:scenario:d1",
        "source_kind": "CALCULATED_PENSION",
        "amount_monthly_gross_ils": "5000.00",
        "contribution_state": "CALCULATED",
    }]


def test_two_pensions_start_in_different_months(monkeypatch):
    result = run(
        monkeypatch,
        pair(decision("d1", "p1", "c1"), decision("d2", "p2", "c2")),
        {"d1": ready("d1", "5000.00", start="2027-01-01"),
         "d2": ready("d2", "2500.50", start="2027-03-01")},
    )
    assert [row["gross_income_total_ils"] for row in result["monthly_rows"]] == [
        "5000.00", "5000.00", "7500.50",
    ]
    assert [len(row["contributions"]) for row in result["monthly_rows"]] == [1, 1, 2]


def test_valid_known_recurring_income_is_separate_and_included(monkeypatch):
    result = run(
        monkeypatch, pair(decision("d1", "p1", "c1")),
        {"d1": ready("d1", start="2027-02-01")}, incomes=[recurring()],
    )
    assert [row["gross_income_total_ils"] for row in result["monthly_rows"]] == [
        "1200.00", "6200.00", "6200.00",
    ]
    february = result["monthly_rows"][1]
    assert february["known_income_subtotal_ils"] == "1200.00"
    assert february["calculated_pension_subtotal_ils"] == "5000.00"
    assert {row["contribution_state"] for row in february["contributions"]} == {
        "KNOWN", "CALCULATED",
    }


def test_blocked_recurring_source_makes_active_months_partial_without_total(monkeypatch):
    result = run(
        monkeypatch, pair(decision("d1", "p1", "c1")),
        {"d1": ready("d1", start="2027-01-01")},
        incomes=[recurring(amount_basis="net")],
    )
    assert result["cashflow_state"] == "PARTIAL"
    assert all(row["cashflow_state"] == "PARTIAL" for row in result["monthly_rows"])
    assert all(row["gross_income_total_ils"] is None for row in result["monthly_rows"])
    assert all(row["calculated_pension_subtotal_ils"] == "5000.00"
               for row in result["monthly_rows"])
    assert any("GROSS_BASIS_REQUIRED" in code for code in result["blocker_codes"])


def test_duplicate_pension_source_never_counts_twice(monkeypatch):
    result = run(
        monkeypatch,
        pair(decision("d1", "p1", "c1"), decision("d2", "p1", "c1")),
        {"d1": ready("d1", start="2027-01-01"),
         "d2": ready("d2", start="2027-01-01")},
    )
    assert result["cashflow_state"] == "BLOCKED"
    assert all(row["gross_income_total_ils"] is None for row in result["monthly_rows"])
    assert all(source["source_state"] == "BLOCKED" for source in result["sources"])
    assert any("DUPLICATE_PENSION_SOURCE" in code for code in result["blocker_codes"])


def test_partial_start_month_is_blocked_instead_of_prorated(monkeypatch):
    result = run(
        monkeypatch, pair(decision("d1", "p1", "c1")),
        {"d1": ready("d1", start="2027-02-15")},
    )
    assert result["monthly_rows"][1]["cashflow_state"] == "BLOCKED"
    assert result["monthly_rows"][1]["gross_income_total_ils"] is None
    assert "PARTIAL_MONTH_PRORATION_UNDEFINED" in result["monthly_rows"][1]["blocker_codes"][0]
    assert result["monthly_rows"][2]["gross_income_total_ils"] == "5000.00"


def test_forged_pension_result_fingerprint_is_blocked(monkeypatch):
    forged = ready("d1", start="2027-01-01")
    forged["monthly_estimate_gross_ils"] = "9999.99"
    result = run(
        monkeypatch, pair(decision("d1", "p1", "c1")), {"d1": forged},
    )
    assert result["cashflow_state"] == "BLOCKED"
    assert all(row["gross_income_total_ils"] is None for row in result["monthly_rows"])


@pytest.mark.parametrize(("start", "end", "code"), [
    ("2027-13", "2027-12", "STAGE6_CASHFLOW_MONTH_INVALID"),
    ("2027-02", "2027-01", "STAGE6_CASHFLOW_RANGE_INVALID"),
])
def test_closed_timeline_range(start, end, code):
    with pytest.raises(ValueError, match=code):
        subject._months(start, end)


def test_cashflow_owner_uses_one_canonical_snapshot(monkeypatch):
    seen = []
    def owner(factory, *, client_id, scenario_id, _snapshot_extension):
        seen.append((factory, client_id, scenario_id))
        return {"cashflow_state": "COMPLETE"}
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", owner)
    token = object()
    result = subject.build_scenario_monthly_cashflow(
        token, client_id=1, scenario_id="scenario",
        start_month="2027-01", end_month="2027-03",
    )
    assert result == {"cashflow_state": "COMPLETE"}
    assert seen == [(token, 1, "scenario")]


def test_snapshot_failure_is_sealed_blocked_timeline(monkeypatch):
    monkeypatch.setattr(
        subject, "build_manifest_candidate_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ScenarioSnapshotError("SCENARIO_SNAPSHOT_DATABASE_UNAVAILABLE")
        ),
    )
    result = subject.build_scenario_monthly_cashflow(
        object(), client_id=1, scenario_id="scenario",
        start_month="2027-01", end_month="2027-02",
    )
    assert result["cashflow_state"] == "BLOCKED"
    assert len(result["monthly_rows"]) == 2
    assert result["cashflow_fingerprint"]
