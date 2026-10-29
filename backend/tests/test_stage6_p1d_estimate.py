"""Stage 6 P1D result contract and strict pre-PTE veto."""
from unittest.mock import patch
import pytest
from app.services import scenario_stage6_single_pension_estimate_service as subject
from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError
from app.services.pension_monthly_basis_service import fingerprint

H={str(i):str(i)*64 for i in range(1,6)}
P={"client_id":1,"scenario_id":"scenario","scenario_version":2,
   "decision_id":"decision","source_id":"scenario-decision:scenario:decision",
   "amount":"1000000.00",
   "professional_admission_fingerprint":"a"*64,
   "planning_calculation_input_fingerprint":H["3"],
   "monthly_semantic_fingerprint":H["1"],"monthly_source_fingerprint":H["2"],
   "temporal_semantic_fingerprint":H["4"],"temporal_source_fingerprint":H["5"]}
APPROVAL={"factor_value":"200","factor_evidence_type":"PLANNER_ASSUMPTION",
          "factor_evidence_reference":"manual professional estimate",
          "payout_option_name":"standard","admission_revision":1,
          "source_id":P["source_id"],
          "professional_admission_fingerprint":P["professional_admission_fingerprint"]}
SOURCE={"source_id":P["source_id"],"pension_start_date":"2027-09-30","currency":"ILS",
        "monthly_amount_basis":{
            "contract_version":"canonical-pension-monthly-amount-basis-v1",
            "source_id":P["source_id"],"source_kind":"scenario_decision",
            "authority_kind":"scenario_decision_balance_ratio",
            "base_amount_representation":{"representation_kind":"exact_ratio",
                                           "numerator":P["amount"],"denominator":"200"},
            "base_amount_effective_date":"2026-09-30",
            "basis_authority_ready":True,"basis_blockers":[],
            "base_amount_semantic_fingerprint":H["1"],
            "base_amount_source_fingerprint":H["2"]},
        "temporal_authority":{
            "contract_version":"canonical-pension-temporal-indexation-basis-v1",
            "source_id":P["source_id"],"source_kind":"scenario_decision",
            "temporal_authority_kind":"none","temporal_origin_date":"2026-09-30",
            "annual_rate":None,"rate_basis":None,"temporal_authority_ready":True,
            "temporal_blockers":[],"temporal_semantic_fingerprint":H["4"],
            "temporal_source_fingerprint":H["5"]}}
PLANNING={"contract_version":"SCENARIO_PENSION_PLANNING_RESULT_V1",
          "client_id":1,"scenario_id":"scenario","scenario_version":2,
          "decision_id":"decision",
          "pension_inputs":[SOURCE],
          "retirement_target":{"retirement_target_date":"2027-09-30",
                               "retirement_target_ready":True},
          "planning_calculation_input_fingerprint":H["3"]}
EVIDENCE={
  "current_planning_calculation_input_fingerprint":H["3"],
  "current_monthly_basis_semantic_fingerprint":H["1"],
  "current_monthly_basis_source_fingerprint":H["2"],
  "current_temporal_semantic_fingerprint":H["4"],
  "current_temporal_source_fingerprint":H["5"]}
PTE={"result_state":"result_ready","source_id":P["source_id"],
     "retirement_target_date":"2027-09-30","source_execution_fingerprint":"f"*64,
     "source_result_fingerprint":"e"*64,"final_monthly_amount":"5000.00",
     "execution_identity_evidence":EVIDENCE}

def run(planning=PLANNING,pte=PTE):
    with patch.object(subject,"execute_from_planning_result",return_value=pte) as engine:
        result=subject._execute_verified(planning_result=planning,approval=APPROVAL,
            statement_date="2026-09-30",retirement_target_date="2027-09-30",
            five_identities=P)
        engine.assert_called_once()
        return result

def test_ready_schema_and_sealed_hash():
    got=run()
    assert got["result_state"]=="RESULT_READY"
    assert got["monthly_estimate_gross_ils"]=="5000.00"
    assert got["coefficient_provenance"]["source_level"]=="MANUAL_PROFESSIONAL_OVERRIDE"
    assert got["result_fingerprint"]==fingerprint({
       "contract_version":"STAGE6_SINGLE_PENSION_DECISION_RESULT_FINGERPRINT_V1",
       "result":{k:v for k,v in got.items() if k!="result_fingerprint"}})
    assert got["result_fingerprint"] == (
        "79da432d43592b1cfbbd21a2771c054ff7b7dac627b4464208894ce555db9192"
    )
    assert len(got)==22

def test_blocked_schema_has_no_recycled_authority():
    got=subject._blocked(1,"scenario","decision","STAGE6_P1C_FACTOR_ADMISSION_BLOCKED")
    assert got["result_state"]=="BLOCKED" and got["execution_allowed"] is False
    assert got["monthly_estimate_gross_ils"] is None
    assert got["professional_admission_fingerprint"] is None
    assert all(got[k] is None for k in subject._HASHES)
    assert got["result_fingerprint"] == (
        "1a68c215815929905712e6dc97d36b39d9df5aea064c2fa6643872deb8d74973"
    )
    assert len(got)==22

def test_wrong_planning_source_prevents_pte():
    forged={**PLANNING,"pension_inputs":[{**SOURCE,"source_id":"manual:forged"}]}
    with patch.object(subject,"execute_from_planning_result") as engine:
        with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_PLANNING_RESULT_INVALID"):
            subject._execute_verified(planning_result=forged,approval=APPROVAL,
                statement_date="2026-09-30",retirement_target_date="2027-09-30",
                five_identities=P)
        engine.assert_not_called()

def test_pte_hash_mismatch_never_ready():
    bad={**PTE,"execution_identity_evidence":{**EVIDENCE,
         "current_temporal_source_fingerprint":"0"*64}}
    with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_PTE_IDENTITY_MISMATCH"):
        run(pte=bad)

def test_pte_block_never_recast_as_ready():
    with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_PTE_BLOCKED"):
        run(pte={**PTE,"result_state":"block_no_result"})

def test_snapshot_failure_is_sealed_blocked_result():
    with patch.object(subject,"build_stage6_p1c_planning_snapshot",
                      side_effect=ScenarioSnapshotError("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED")):
        got=subject.estimate_single_pension_decision(
            None,client_id=1,scenario_id="scenario",decision_id="decision")
    assert got["result_state"]=="BLOCKED"
    assert got["blockers"]==["STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"]

def test_mismatched_planning_identity_never_calls_pte():
    forged={**PLANNING,"planning_calculation_input_fingerprint":"0"*64}
    with patch.object(subject,"execute_from_planning_result") as engine:
        with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_PLANNING_IDENTITY_MISMATCH"):
            subject._execute_verified(
                planning_result=forged,approval=APPROVAL,
                statement_date="2026-09-30",retirement_target_date="2027-09-30",
                five_identities=P)
        engine.assert_not_called()


def test_missing_current_identity_blocks_before_pte():
    forged={**P,"monthly_source_fingerprint":None}
    with patch.object(subject,"execute_from_planning_result") as engine:
        with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_IDENTITY_INVALID"):
            subject._execute_verified(
                planning_result=PLANNING,approval=APPROVAL,
                statement_date="2026-09-30",retirement_target_date="2027-09-30",
                five_identities=forged)
        engine.assert_not_called()


def test_real_canonical_pte_one_source_gross_result():
    """Exercise P1C owners into real PTE (not a mocked PTE result)."""
    from test_stage6_p1c_canonical_identity import result
    from app.services.planning_input_service import scenario_decision_one_source_planning_result
    facts, monthly, temporal, planning_facts=result()
    actual_planning=scenario_decision_one_source_planning_result(
        facts=planning_facts,monthly=monthly,temporal=temporal,
        factor_value=facts["factor_value"])
    approval={
        **APPROVAL,
        "factor_value":facts["factor_value"],
        "source_id":planning_facts["source_id"],
        "professional_admission_fingerprint":planning_facts[
            "professional_admission_fingerprint"
        ],
    }
    out=subject._execute_verified(
        planning_result=actual_planning,
        approval=approval,
        statement_date=facts["statement_date"],
        retirement_target_date=planning_facts["retirement_target_date"],
        five_identities={
            **planning_facts,
            "planning_calculation_input_fingerprint": actual_planning[
                "planning_calculation_input_fingerprint"
            ],
        })
    assert out["result_state"]=="RESULT_READY"
    assert out["monthly_estimate_gross_ils"]=="5000.00"
    assert out["result_fingerprint"]
    assert out["pte_source_execution_fingerprint"]


def test_real_canonical_pte_never_runs_on_preflight_target_conflict():
    from test_stage6_p1c_canonical_identity import result
    from app.services.planning_input_service import scenario_decision_one_source_planning_result
    facts,monthly,temporal,planning_facts=result()
    built=scenario_decision_one_source_planning_result(
        facts=planning_facts,monthly=monthly,temporal=temporal,
        factor_value=facts["factor_value"])
    with patch.object(subject,"execute_from_planning_result") as engine:
        with pytest.raises(ScenarioSnapshotError,match="STAGE6_P1D_PLANNING_RESULT_INVALID"):
            subject._execute_verified(
                planning_result=built,approval=APPROVAL,
                statement_date=facts["statement_date"],
                retirement_target_date="2028-01-01",
                five_identities=planning_facts)
        engine.assert_not_called()


def aggregate_result(decision_id, amount="5000.00", *, target="2027-09-30",
                     statement="2026-09-30"):
    value = run()
    value.update(
        decision_id=decision_id,
        source_id=f"scenario-decision:scenario:{decision_id}",
        monthly_estimate_gross_ils=amount,
        retirement_target_date=target,
        statement_date=statement,
    )
    value.pop("result_fingerprint")
    return subject._seal(value)


def aggregate_pair(*rows):
    return {
        "manifest": {"scenario_version": 2, "decisions": list(rows)},
        "candidate": {"evidence_state": "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"},
    }


def decision(decision_id, product_id, component_id):
    return {
        "decision_id": decision_id, "product_id": product_id,
        "component_id": component_id, "action": "pension",
    }


def run_aggregate(monkeypatch, pair, results):
    def extension(*, decision_id, **_kwargs):
        value = results[decision_id]
        if isinstance(value, BaseException):
            return lambda _db, _pair: (_ for _ in ()).throw(value)
        return lambda _db, _pair: value
    monkeypatch.setattr(subject, "_stage6_identity_extension", extension)
    return subject._aggregate_extension(
        client_id=1, scenario_id="scenario",
    )(None, pair)


def test_single_decision_aggregate_is_complete_and_recomputable(monkeypatch):
    result = run_aggregate(
        monkeypatch, aggregate_pair(decision("d1", "p1", "c1")),
        {"d1": aggregate_result("d1")},
    )
    assert result["aggregation_state"] == "COMPLETE"
    assert result["monthly_pension_gross_total_ils"] == "5000.00"
    assert result["comparison_basis"] == {
        "currency": "ILS", "income_basis": "GROSS",
        "price_basis": "NOMINAL_UNINDEXED",
        "retirement_target_date": "2027-09-30",
        "source_reference_date": "2026-09-30",
    }
    preimage = {key: value for key, value in result.items()
                if key != "aggregate_fingerprint"}
    assert result["aggregate_fingerprint"] == fingerprint({
        "contract_version": "STAGE6_PENSION_DECISION_AGGREGATE_FINGERPRINT_V1",
        "result": preimage,
    })


def test_two_comparable_decisions_sum_exact_decimal_amounts(monkeypatch):
    result = run_aggregate(
        monkeypatch,
        aggregate_pair(decision("d1", "p1", "c1"), decision("d2", "p2", "c2")),
        {"d1": aggregate_result("d1", "5000.10"),
         "d2": aggregate_result("d2", "2500.55")},
    )
    assert result["aggregation_state"] == "COMPLETE"
    assert result["monthly_pension_gross_total_ils"] == "7500.65"
    assert [row["decision_id"] for row in result["decision_results"]] == ["d1", "d2"]


def test_aggregate_does_not_round_large_exact_money(monkeypatch):
    result = run_aggregate(
        monkeypatch,
        aggregate_pair(decision("d1", "p1", "c1"), decision("d2", "p2", "c2")),
        {"d1": aggregate_result("d1", "9999999999999999999999999999.99"),
         "d2": aggregate_result("d2", "0.02")},
    )
    assert result["monthly_pension_gross_total_ils"] == (
        "10000000000000000000000000000.01"
    )


@pytest.mark.parametrize(("changed", "blocker"), [
    ({"target": "2028-01-01"}, "STAGE6_AGGREGATE_RETIREMENT_TARGET_DATE_MISMATCH"),
    ({"statement": "2026-10-01"}, "STAGE6_AGGREGATE_REFERENCE_DATE_MISMATCH"),
])
def test_noncomparable_basis_blocks_total(monkeypatch, changed, blocker):
    result = run_aggregate(
        monkeypatch,
        aggregate_pair(decision("d1", "p1", "c1"), decision("d2", "p2", "c2")),
        {"d1": aggregate_result("d1"), "d2": aggregate_result("d2", **changed)},
    )
    assert result["aggregation_state"] == "BLOCKED"
    assert result["monthly_pension_gross_total_ils"] is None
    assert blocker in result["blockers"]


def test_one_ready_and_one_blocked_is_partial_without_total(monkeypatch):
    result = run_aggregate(
        monkeypatch,
        aggregate_pair(decision("d1", "p1", "c1"), decision("d2", "p2", "c2")),
        {"d1": aggregate_result("d1"),
         "d2": ScenarioSnapshotError("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED")},
    )
    assert result["aggregation_state"] == "PARTIAL"
    assert result["monthly_pension_gross_total_ils"] is None
    assert result["blockers"] == ["d2:STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"]
    assert result["decision_results"][0]["monthly_estimate_gross_ils"] == "5000.00"


def test_duplicate_source_blocks_total_even_when_each_result_is_ready(monkeypatch):
    result = run_aggregate(
        monkeypatch,
        aggregate_pair(decision("d1", "p1", "c1"), decision("d2", "p1", "c1")),
        {"d1": aggregate_result("d1"), "d2": aggregate_result("d2")},
    )
    assert result["aggregation_state"] == "BLOCKED"
    assert result["monthly_pension_gross_total_ils"] is None
    assert result["blockers"] == ["STAGE6_AGGREGATE_DUPLICATE_SOURCE"]


def test_coherently_shaped_result_with_bad_fingerprint_is_not_counted(monkeypatch):
    forged = aggregate_result("d1")
    forged["monthly_estimate_gross_ils"] = "999999.99"
    result = run_aggregate(
        monkeypatch, aggregate_pair(decision("d1", "p1", "c1")),
        {"d1": forged},
    )
    assert result["aggregation_state"] == "BLOCKED"
    assert result["monthly_pension_gross_total_ils"] is None
    assert result["decision_results"][0]["blockers"] == [
        "STAGE6_AGGREGATE_RESULT_INVALID",
    ]


def test_aggregate_owner_uses_one_snapshot_for_all_decisions(monkeypatch):
    observed = []
    def owner(factory, *, client_id, scenario_id, _snapshot_extension):
        observed.append((factory, client_id, scenario_id))
        return {"aggregation_state": "BLOCKED"}
    monkeypatch.setattr(subject, "build_manifest_candidate_snapshot", owner)
    token = object()
    assert subject.estimate_scenario_pension_aggregate(
        token, client_id=1, scenario_id="scenario",
    ) == {"aggregation_state": "BLOCKED"}
    assert observed == [(token, 1, "scenario")]
