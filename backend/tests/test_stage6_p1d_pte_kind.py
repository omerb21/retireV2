"""P1D narrow PTE scenario-kind contract. No route, DB write, or production execution."""
from app.services.pension_target_date_execution_service import execute_source

H={str(i):str(i)*64 for i in range(1,6)}

def execute(source="scenario-decision:sc:decision",kind="scenario_decision_balance_ratio",
            representation=None, supplied_monthly=None):
    return execute_source(
        source_id=source,source_current_state="current",
        monthly_basis={
            "authority_kind":kind,
            "base_amount_representation":representation or {
                "representation_kind":"exact_ratio","numerator":"1000000.00","denominator":"200"},
            "base_amount_semantic_fingerprint":H["1"],
            "base_amount_source_fingerprint":H["2"],
            "basis_authority_ready":True,"basis_blockers":[]},
        temporal_authority={
            "temporal_authority_kind":"none","temporal_origin_date":"2026-09-30",
            "annual_rate":None,"temporal_semantic_fingerprint":H["4"],
            "temporal_source_fingerprint":H["5"],
            "temporal_authority_ready":True,"temporal_blockers":[]},
        retirement_target={"retirement_target_date":"2027-09-30","retirement_target_ready":True},
        current_planning_calculation_input_fingerprint=H["3"],
        supplied_planning_calculation_input_fingerprint=H["3"],
        supplied_monthly_basis_semantic_fingerprint=supplied_monthly or H["1"],
        supplied_monthly_basis_source_fingerprint=H["2"],
        supplied_temporal_semantic_fingerprint=H["4"],
        supplied_temporal_source_fingerprint=H["5"],
        pension_start_date="2027-09-30",currency="ILS")


def test_canonical_pte_accepts_exact_scenario_decision_ratio():
    result=execute()
    assert result["result_state"]=="result_ready"
    assert result["final_monthly_amount"]=="5000.00"


def test_wrong_source_namespace_blocks_scenario_kind():
    result=execute(source="manual:7")
    assert result["result_state"]=="block_no_result"
    assert "MONTHLY_BASIS_NOT_READY" in result["blockers"]
    assert result["final_monthly_amount"] is None


def test_scenario_kind_requires_exact_ratio():
    result=execute(representation={"representation_kind":"exact_money","amount":"5000"})
    assert result["result_state"]=="block_no_result"
    assert "MONTHLY_BASIS_NOT_READY" in result["blockers"]


def test_stale_monthly_hash_blocks():
    result=execute(supplied_monthly="a"*64)
    assert result["result_state"]=="block_no_result"
    assert "MONTHLY_BASIS_IDENTITY_STALE" in result["blockers"]
