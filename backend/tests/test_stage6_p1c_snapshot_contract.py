"""Stage 6 P1C same-snapshot wiring; no PTE, no financial execution."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.services import scenario_snapshot_candidate_service as snapshot


class FakeDB:
    def __init__(self, global_target=None):
        self.global_target = global_target
        self.queries = 0

    def scalar(self, query):
        self.queries += 1
        if self.queries == 1:
            return SimpleNamespace(version=3, statement_date=date(2026,9,30))
        if self.queries == 2:
            return SimpleNamespace(
                pension_start_date=date(2027,9,30),
                coefficient_selection="manual_review_required",
                option_name="STANDARD")
        raise AssertionError("Unexpected DB query")

    def get(self, model, client_id):
        return (SimpleNamespace(retirement_target_date=self.global_target)
                if self.global_target else None)


MANIFEST = {
    "scenario_version":2,"manifest_fingerprint":"a"*64,
    "decisions":[{
        "decision_id":"decision","action":"pension","product_id":"p",
        "component_id":"c","component_code":"standard-component-02",
        "amount":"1000.00",
        "source":{"source_fingerprint":"b"*64,"product_version":3}
    }],
}
PARTITION = {"evidence_state":"STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
             "partition_fingerprint":"c"*64}
APPROVAL={"admission_revision":1,"professional_admission_fingerprint":"d"*64,
          "factor_value":"200"}
PERMISSION={"ruleset_digest":"e"*64,"permission_admission_fingerprint":"f"*64}
REVIEW={"manifest_fingerprint":"a"*64,"election_fingerprint":"1"*64}


def _derive(global_target=None):
    db=FakeDB(global_target)
    def snapshot_owner(factory, *, client_id, scenario_id, _snapshot_extension):
        assert client_id==1 and scenario_id=="scenario"
        assert db.queries==0
        # Explicitly execute extension only inside mocked original owner.
        return _snapshot_extension(db, {"manifest":MANIFEST,"candidate":PARTITION})
    with patch.object(snapshot,"build_manifest_candidate_snapshot",side_effect=snapshot_owner),patch(
        "app.services.scenario_pension_factor_admission_read_service.read_current_admission",
        return_value=APPROVAL),patch(
        "app.services.scenario_permission_preview_service.derive_pension_action_permission_admission",
        return_value=PERMISSION),patch(
        "app.services.scenario_coefficient_review_context_service.derive_documentary_review_context",
        return_value=REVIEW):
        return snapshot.build_stage6_p1c_planning_snapshot(
            None,client_id=1,scenario_id="scenario",decision_id="decision")


def test_returns_exact_five_hashes_one_source_and_no_execution():
    out=_derive()
    assert out["schema_version"]=="STAGE6_P1C_IDENTITY_ONLY_V1"
    for key in ("monthly_semantic_fingerprint","monthly_source_fingerprint",
                "temporal_semantic_fingerprint","temporal_source_fingerprint",
                "planning_calculation_input_fingerprint"):
        assert len(out[key])==64
    assert out["execution_allowed"] is False
    assert out["financial_result"] is None
    assert len(out["planning_result"]["pension_inputs"])==1
    assert out["planning_result"]["pension_inputs"][0]["source_id"]=="scenario-decision:scenario:decision"


def test_global_target_conflict_blocks():
    with pytest.raises(snapshot.ScenarioSnapshotError,match="SCENARIO_GLOBAL_TARGET_CONFLICT"):
        _derive(date(2028,9,30))


def test_global_target_matching_does_not_replace_scenario_date():
    out=_derive(date(2027,9,30))
    assert out["planning_result"]["retirement_target"]["retirement_target_date"]=="2027-09-30"


def test_missing_approval_is_not_silently_recovered():
    with patch.object(snapshot,"build_manifest_candidate_snapshot") as owner:
        def raise_missing(*args,**kwargs):
            raise RuntimeError("no current admission")
        owner.side_effect=raise_missing
        with pytest.raises(RuntimeError,match="no current admission"):
            snapshot.build_stage6_p1c_planning_snapshot(
                None,client_id=1,scenario_id="scenario",decision_id="decision")


def test_blocked_partition_never_reaches_admission():
    def snapshot_owner(factory, *, client_id, scenario_id, _snapshot_extension):
        return _snapshot_extension(FakeDB(), {
            "manifest":MANIFEST,
            "candidate":{"evidence_state":"BLOCKED","partition_fingerprint":"c"*64},
        })
    with patch.object(snapshot,"build_manifest_candidate_snapshot",side_effect=snapshot_owner):
        with pytest.raises(snapshot.ScenarioSnapshotError,match="STAGE6_P1C_SOURCE_BLOCKED"):
            snapshot.build_stage6_p1c_planning_snapshot(
                None,client_id=1,scenario_id="scenario",decision_id="decision")


def test_expired_approval_is_a_blocker_not_database_unavailable():
    from app.services.scenario_pension_factor_admission_read_service import FactorAdmissionBlocked
    def snapshot_owner(factory, *, client_id, scenario_id, _snapshot_extension):
        return _snapshot_extension(FakeDB(), {"manifest":MANIFEST,"candidate":PARTITION})
    with patch.object(snapshot,"build_manifest_candidate_snapshot",side_effect=snapshot_owner),patch(
        "app.services.scenario_pension_factor_admission_read_service.read_current_admission",
        side_effect=FactorAdmissionBlocked("FACTOR_ADMISSION_STALE")):
        with pytest.raises(snapshot.ScenarioSnapshotError,match="STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"):
            snapshot.build_stage6_p1c_planning_snapshot(
                None,client_id=1,scenario_id="scenario",decision_id="decision")


def test_invalid_decision_fails_before_snapshot():
    with patch.object(snapshot,"build_manifest_candidate_snapshot") as owner:
        with pytest.raises(snapshot.ScenarioSnapshotError,match="STAGE6_P1C_DECISION_INVALID"):
            snapshot.build_stage6_p1c_planning_snapshot(
                None,client_id=1,scenario_id="scenario",decision_id="")
        owner.assert_not_called()
