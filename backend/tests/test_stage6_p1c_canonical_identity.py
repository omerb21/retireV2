"""P1C canonical-owner five identity fixtures: no PTE or financial execution."""
import pytest
from app.services.pension_monthly_basis_service import (
    scenario_decision_monthly_identity, semantic, fingerprint as monthly_hash)
from app.services.pension_temporal_basis_service import (
    scenario_decision_temporal_identity, semantic_fingerprint)
from app.services.planning_input_service import (
    scenario_decision_calculation_identity, scenario_decision_one_source_planning_result,
    fingerprint as planning_hash)


def authority():
    return {
        "client_id":1,"scenario_id":"s:one","scenario_version":2,
        "decision_id":"d/two","manifest_fingerprint":"a"*64,
        "partition_fingerprint":"b"*64,"source_product_id":"p",
        "source_product_version":3,"source_component_id":"c",
        "component_code":"standard-component-02","source_fingerprint":"c"*64,
        "amount":"1000000.00","statement_date":"2026-09-30",
        "election_fingerprint":"d"*64,"professional_admission_revision":1,
        "professional_admission_fingerprint":"e"*64,"factor_value":"200",
    }


def result(override=None):
    src=authority()
    src.update(override or {})
    monthly=scenario_decision_monthly_identity(src)
    temporal=scenario_decision_temporal_identity({
        "source_id":monthly["source_id"],"client_id":src["client_id"],
        "scenario_id":src["scenario_id"],"scenario_version":src["scenario_version"],
        "decision_id":src["decision_id"],"statement_date":src["statement_date"],
        "retirement_target_date":"2027-09-30",
        "monthly_source_fingerprint":monthly["monthly_source_fingerprint"],
        "professional_admission_fingerprint":src["professional_admission_fingerprint"],
    })
    planning={
        "client_id":src["client_id"],"scenario_id":src["scenario_id"],
        "scenario_version":src["scenario_version"],"decision_id":src["decision_id"],
        "source_id":monthly["source_id"],
        "manifest_fingerprint":src["manifest_fingerprint"],
        "partition_fingerprint":src["partition_fingerprint"],
        "source_fingerprint":src["source_fingerprint"],
        "statement_date":src["statement_date"],"amount":src["amount"],"action":"pension",
        "election_fingerprint":src["election_fingerprint"],
        "retirement_target_date":"2027-09-30",
        "monthly_semantic_fingerprint":monthly["monthly_semantic_fingerprint"],
        "monthly_source_fingerprint":monthly["monthly_source_fingerprint"],
        "temporal_semantic_fingerprint":temporal["temporal_semantic_fingerprint"],
        "temporal_source_fingerprint":temporal["temporal_source_fingerprint"],
        "professional_admission_revision":src["professional_admission_revision"],
        "professional_admission_fingerprint":src["professional_admission_fingerprint"],
        "ruleset_digest":"f"*64,"permission_admission_fingerprint":"0"*64,
    }
    return src,monthly,temporal,planning


def test_five_fingerprints_match_canonical_owners():
    src,m,t,p=result()
    assert m["source_id"]=="scenario-decision:s%3Aone:d%2Ftwo"
    assert m["monthly_semantic_fingerprint"]==semantic(
        "scenario_decision_balance_ratio",m["representation"],src["statement_date"])
    assert m["monthly_source_fingerprint"]==monthly_hash(m["monthly_source_preimage"])
    assert t["temporal_semantic_fingerprint"]==semantic_fingerprint("none",src["statement_date"],None,None)
    assert t["temporal_source_fingerprint"]==monthly_hash(t["temporal_source_preimage"])
    assert scenario_decision_calculation_identity(p)["planning_calculation_input_fingerprint"]==planning_hash({
        "contract":"canonical-scenario-pension-planning-calculation-input-v1",**p})
    one=scenario_decision_one_source_planning_result(
        facts=p,monthly=m,temporal=t,factor_value=src["factor_value"])
    assert one["contract_version"]=="SCENARIO_PENSION_PLANNING_RESULT_V1"
    assert len(one["pension_inputs"])==1
    assert one["pension_inputs"][0]["temporal_authority"]["annual_rate"] is None


@pytest.mark.parametrize("change", [
    {"factor_value":"201"},
    {"amount":"1000001.00"},
    {"statement_date":"2026-10-01"},
    {"professional_admission_fingerprint":"1"*64},
    {"source_product_version":4},
    {"manifest_fingerprint":"2"*64},
    {"election_fingerprint":"3"*64},
    {"scenario_version":3},
])
def test_m2_invalidates_on_current_authority_change(change):
    a=scenario_decision_monthly_identity(authority())["monthly_source_fingerprint"]
    b=scenario_decision_monthly_identity({**authority(),**change})["monthly_source_fingerprint"]
    assert a!=b


def test_temporal_origin_target_not_mixed():
    src,m,t,p=result()
    assert t["temporal_source_preimage"]["retirement_target_date"]=="2027-09-30"
    assert "retirement_target_date" not in m["monthly_source_preimage"]
    assert t["temporal_source_preimage"]["monthly_source_fingerprint"]==m["monthly_source_fingerprint"]


def test_planning_fingerprint_permission_staleness():
    _,_,_,p=result()
    original=scenario_decision_calculation_identity(p)["planning_calculation_input_fingerprint"]
    modified={**p,"permission_admission_fingerprint":"4"*64}
    assert original!=scenario_decision_calculation_identity(modified)["planning_calculation_input_fingerprint"]


def test_no_silent_fallback_for_invalid_amount_or_factor():
    for field,value in (("amount","0.00"),("factor_value","0"),("factor_value","200.00")):
        with pytest.raises(ValueError):
            scenario_decision_monthly_identity({**authority(),field:value})


def test_reject_injected_fifth_hash_or_source():
    src,m,t,p=result()
    with pytest.raises(ValueError):
        scenario_decision_calculation_identity({**p,"injected":True})
    with pytest.raises(ValueError):
        scenario_decision_one_source_planning_result(
            facts={**p,"source_id":"manual:1"},monthly=m,temporal=t,factor_value=src["factor_value"])
