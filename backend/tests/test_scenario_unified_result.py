"""Package 1 unified contract: invariants without promoting financial authority."""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import scenario_unified_result_service as subject
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, _build_pair_in_snapshot,
)
from tests.test_scenario_snapshot_candidate import verified_db


def pair(db=None):
    return _build_pair_in_snapshot(db or verified_db(), 7, "s", None)


class Rows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class ReadDb:
    def __init__(self, *, elections=None, assumptions=None, planning=None, target=None,
                 client_id=7):
        self.client_id = client_id
        self.elections = elections or []
        self.assumptions = assumptions or []
        self.planning = planning
        self.target = target
        self.scalar_calls = 0
        self.scalars_calls = 0

    def scalar(self, _query):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return SimpleNamespace(
                client_id=self.client_id, birth_date=date(1965, 1, 1),
                employment_status="salaried_employee",
                planned_retirement_date=date(2032, 1, 1),
                planned_retirement_age=None,
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        if self.scalar_calls == 2:
            return self.planning
        if self.scalar_calls == 3:
            return self.target
        raise AssertionError("Unexpected database query")

    def scalars(self, _query):
        self.scalars_calls += 1
        if self.scalars_calls == 1:
            return Rows(self.elections)
        if self.scalars_calls == 2:
            return Rows(self.assumptions)
        raise AssertionError("Unexpected database query")


def planning(version=1):
    return SimpleNamespace(
        version=version,
        planning_base_date=date(2026, 1, 1),
        retirement_target_date=date(2032, 1, 1),
        retirement_target_reference_fingerprint="a" * 64,
    )


def election(scenario_version=1):
    return SimpleNamespace(
        decision_id="d", scenario_version=scenario_version,
        pension_start_date=date(2032, 1, 1), target_year=2032,
        survivors_option="test_option", spouse_age_diff=0,
        coefficient_selection="manual_review_required",
        company_name=None, option_name=None,
    )


def build(source=None, **kwargs):
    return subject._assemble(
        ReadDb(planning=planning(), elections=[election()], **kwargs),
        pair(source), 7, "s",
    )


def test_a_identity_version_and_inert_result_contract():
    result = build()
    assert result["identity"] == {
        "client_id": 7, "scenario_id": "s",
        "scenario_version": 1, "scenario_status": "draft",
    }
    assert result["decisions"][0]["election_state"] == "CURRENT_DRAFT_ONLY"
    assert result["decisions"][0]["source_state"] == "CURRENT_STRUCTURAL_ONLY"
    assert result["reference_dates"]["retirement_target_date"] == "2032-01-01"
    assert result["execution_allowed"] is result["professional_authority"] is False
    for domain in subject.FINANCIAL_DOMAINS:
        assert result["financial_domains"][domain] == {
            "state": "NOT_CONNECTED",
            "result": None,
            "professional_authority": False,
            "result_fingerprint": None,
        }


def test_b_repeatability_and_detached_result():
    left = build()
    right = build()
    assert left == right
    left["decisions"][0]["decision"]["amount"] = "9000.00"
    assert right["decisions"][0]["decision"]["amount"] == "50.00"


def test_c_material_change_invalidates_full_fingerprint_and_preserves_unrelated():
    original = build()
    changed = verified_db()
    changed.decisions[0].amount = Decimal("55.00")
    edited = build(changed)
    assert edited["result_fingerprint"] != original["result_fingerprint"]
    assert edited["decisions"][0]["dependency_fingerprint"] != original["decisions"][0]["dependency_fingerprint"]
    assert edited["client_facts"] == original["client_facts"]


def test_c_source_drift_blocks_authority():
    original = build()
    changed = verified_db()
    changed.component.balance = Decimal("120.00")
    edited = build(changed)
    assert edited["result_fingerprint"] != original["result_fingerprint"]
    assert edited["source_candidate_state"] == "BLOCKED"
    assert edited["decisions"][0]["source_state"] == "BLOCKED_STALE"
    assert edited["financial_domains"]["pension_gross"]["state"] == "BLOCKED"


def test_d_wrong_client_or_scenario_rejected():
    with pytest.raises(ScenarioSnapshotError, match="UNIFIED_SCENARIO_IDENTITY_MISMATCH"):
        subject._assemble(ReadDb(planning=planning()), pair(), 8, "s")
    with pytest.raises(ScenarioSnapshotError, match="UNIFIED_SCENARIO_IDENTITY_MISMATCH"):
        subject._assemble(ReadDb(planning=planning()), pair(), 7, "other")


def test_e_missing_election_is_not_professional_approval():
    result = subject._assemble(ReadDb(planning=planning()), pair(), 7, "s")
    assert result["decisions"][0]["election_state"] == "MISSING"
    assert "UNIFIED_ELECTION_MISSING:d" in result["blockers"]
    assert result["financial_domains"]["pension_gross"]["result"] is None


def test_e_stale_election_is_blocked():
    result = subject._assemble(
        ReadDb(planning=planning(), elections=[election(scenario_version=2)]),
        pair(), 7, "s",
    )
    assert result["decisions"][0]["election_state"] == "BLOCKED_STALE"
    assert "UNIFIED_ELECTION_STALE:d" in result["blockers"]


def test_e_missing_planning_date_is_explicit():
    result = subject._assemble(ReadDb(elections=[election()]), pair(), 7, "s")
    assert result["reference_dates"]["retirement_target_date"] is None
    assert "UNIFIED_RETIREMENT_TARGET_DATE_MISSING" in result["blockers"]


def test_e_source_missing_remains_missing_not_zero():
    missing = verified_db()
    missing.product = None
    result = build(missing)
    assert result["decisions"][0]["source_state"] == "MISSING"
    assert result["decisions"][0]["decision"]["source"] is None
    assert result["financial_domains"]["capital"]["result"] is None


def test_assumption_change_invalidates_only_relevant_dependency_preimage():
    assumption = SimpleNamespace(
        id=1, assumption_category="income", title="Test",
        assumption_value_text="100", rationale="test-only", owner="planner",
        effective_start_date=None, effective_end_date=None, review_date=None,
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    first = subject._assemble(
        ReadDb(planning=planning(), elections=[election()], assumptions=[assumption]),
        pair(), 7, "s",
    )
    assumption.assumption_value_text = "101"
    second = subject._assemble(
        ReadDb(planning=planning(), elections=[election()], assumptions=[assumption]),
        pair(), 7, "s",
    )
    assert first["result_fingerprint"] != second["result_fingerprint"]
    assert first["decisions"][0]["dependency_fingerprint"] == second["decisions"][0]["dependency_fingerprint"]


def test_f_existing_snapshot_owner_used_without_new_writer(monkeypatch):
    called = []

    def snapshot(_factory, **kwargs):
        called.append(kwargs)
        return kwargs["_snapshot_extension"](
            ReadDb(planning=planning(), elections=[election()]), pair(),
        )

    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", snapshot)
    result = subject.build_unified_scenario_result(object(), client_id=7, scenario_id="s")
    assert result["identity"]["client_id"] == 7
    assert called[0]["client_id"] == 7
    assert called[0]["scenario_id"] == "s"
    assert subject.assert_unified_result_current(
        object(), client_id=7, scenario_id="s",
        expected_result_fingerprint=result["result_fingerprint"],
    )
    assert not subject.assert_unified_result_current(
        object(), client_id=7, scenario_id="s", expected_result_fingerprint="0" * 64,
    )
    assert not subject.assert_unified_result_current(
        object(), client_id=7, scenario_id="s", expected_result_fingerprint="malformed",
    )
