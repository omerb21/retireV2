"""Stage 6 P1D: nonbinding one-decision gross estimate, canonical PTE only.

No database writes. No automatic coefficient selection. All financial execution
is gated inside the existing REPEATABLE READ READ ONLY snapshot owner.
"""
from __future__ import annotations
from app.services.pension_monthly_basis_service import fingerprint
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, build_stage6_p1c_planning_snapshot,
)
from app.services.pension_target_date_execution_service import execute_from_planning_result

CONTRACT="STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1"
_HASHES=("planning_calculation_input_fingerprint","monthly_basis_semantic_fingerprint",
         "monthly_basis_source_fingerprint","temporal_semantic_fingerprint",
         "temporal_source_fingerprint")
_FIELDS=("schema_version","client_id","scenario_id","scenario_version","decision_id",
         "source_id","result_state","execution_allowed","blockers",
         "coefficient_provenance","professional_admission_fingerprint",
         *_HASHES,"pte_source_execution_fingerprint","pte_source_result_fingerprint",
         "monthly_estimate_gross_ils","retirement_target_date","statement_date",
         "result_fingerprint")


def _seal(data: dict) -> dict:
    if set(data)!=(set(_FIELDS)-{"result_fingerprint"}):
        raise ValueError("STAGE6_RESULT_FIELD_SET_INVALID")
    data["result_fingerprint"]=fingerprint({
        "contract_version":"STAGE6_SINGLE_PENSION_DECISION_RESULT_FINGERPRINT_V1",
        "result":dict(data),
    })
    return data


def _blocked(client_id: int, scenario_id: str, decision_id: str, code: str) -> dict:
    from urllib.parse import quote
    source_id="scenario-decision:"+quote(scenario_id,safe="")+":"+quote(decision_id,safe="")
    values=dict.fromkeys(_FIELDS,None)
    values.update(schema_version=CONTRACT,client_id=client_id,scenario_id=scenario_id,
                  scenario_version=None,decision_id=decision_id,source_id=source_id,
                  result_state="BLOCKED",execution_allowed=False,
                  blockers=[code])
    values.pop("result_fingerprint")
    return _seal(values)


def _execute_verified(*, planning_result: dict, approval: dict,
                      statement_date: str, retirement_target_date: str,
                      five_identities: dict) -> dict:
    """Called only as the trusted snapshot extension after all P1A/B/C gates."""
    identities=five_identities
    source_id=identities["source_id"]
    sources=planning_result["pension_inputs"]
    if (planning_result["contract_version"]!="SCENARIO_PENSION_PLANNING_RESULT_V1"
            or len(sources)!=1 or sources[0]["source_id"]!=source_id
            or sources[0]["pension_start_date"]!=retirement_target_date
            or sources[0]["monthly_amount_basis"]["authority_kind"]!="scenario_decision_balance_ratio"
            or sources[0]["temporal_authority"]["temporal_authority_kind"]!="none"
            or sources[0]["temporal_authority"]["annual_rate"] is not None
            or planning_result["retirement_target"]!={"retirement_target_date":retirement_target_date,
                                                      "retirement_target_ready":True}):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_RESULT_INVALID")
    if (planning_result.get("planning_calculation_input_fingerprint")
            != identities.get("planning_calculation_input_fingerprint")):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_IDENTITY_MISMATCH")
    # These are the already verified P1C identities from the DB-owned snapshot.
    for key in ("monthly_semantic_fingerprint", "monthly_source_fingerprint",
                "temporal_semantic_fingerprint", "temporal_source_fingerprint"):
        value=identities.get(key)
        if (type(value) is not str or len(value)!=64
                or any(ch not in "0123456789abcdef" for ch in value)):
            raise ScenarioSnapshotError("STAGE6_P1D_IDENTITY_INVALID")
    supplied=dict(
        supplied_planning_calculation_input_fingerprint=planning_result["planning_calculation_input_fingerprint"],
        supplied_monthly_basis_semantic_fingerprint=identities["monthly_semantic_fingerprint"],
        supplied_monthly_basis_source_fingerprint=identities["monthly_source_fingerprint"],
        supplied_temporal_semantic_fingerprint=identities["temporal_semantic_fingerprint"],
        supplied_temporal_source_fingerprint=identities["temporal_source_fingerprint"],
    )
    # Exactly ONE canonical PTE call; reject every blocked or mismatched outcome.
    pte=execute_from_planning_result(planning_result,source_id,**supplied)
    if (pte.get("result_state")!="result_ready"
            or pte.get("source_id")!=source_id
            or pte.get("retirement_target_date")!=retirement_target_date
            or any(type(pte.get(k)) is not str or len(pte[k])!=64
                   or any(ch not in "0123456789abcdef" for ch in pte[k])
                   for k in ("source_execution_fingerprint","source_result_fingerprint"))
            or pte.get("final_monthly_amount") is None):
        raise ScenarioSnapshotError("STAGE6_P1D_PTE_BLOCKED")
    for label,current in (
        ("current_planning_calculation_input_fingerprint",supplied["supplied_planning_calculation_input_fingerprint"]),
        ("current_monthly_basis_semantic_fingerprint",supplied["supplied_monthly_basis_semantic_fingerprint"]),
        ("current_monthly_basis_source_fingerprint",supplied["supplied_monthly_basis_source_fingerprint"]),
        ("current_temporal_semantic_fingerprint",supplied["supplied_temporal_semantic_fingerprint"]),
        ("current_temporal_source_fingerprint",supplied["supplied_temporal_source_fingerprint"]),
    ):
        if pte.get("execution_identity_evidence",{}).get(label)!=current:
            raise ScenarioSnapshotError("STAGE6_P1D_PTE_IDENTITY_MISMATCH")
    import re
    amount=pte["final_monthly_amount"]
    if not isinstance(amount,str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.[0-9]{2}",amount):
        raise ScenarioSnapshotError("STAGE6_P1D_RESULT_AMOUNT_INVALID")
    provenance={
        "source_level":"MANUAL_PROFESSIONAL_OVERRIDE",
        "factor_value":approval["factor_value"],
        "factor_evidence_type":approval["factor_evidence_type"],
        "factor_evidence_reference":approval["factor_evidence_reference"],
        "payout_option_name":approval["payout_option_name"],
        "admission_revision":approval["admission_revision"],
    }
    values=dict(
        schema_version=CONTRACT,
        client_id=identities["client_id"],scenario_id=identities["scenario_id"],
        scenario_version=identities["scenario_version"],decision_id=identities["decision_id"],
        source_id=source_id,result_state="RESULT_READY",execution_allowed=True,
        blockers=[],coefficient_provenance=provenance,
        professional_admission_fingerprint=identities["professional_admission_fingerprint"],
        planning_calculation_input_fingerprint=supplied["supplied_planning_calculation_input_fingerprint"],
        monthly_basis_semantic_fingerprint=supplied["supplied_monthly_basis_semantic_fingerprint"],
        monthly_basis_source_fingerprint=supplied["supplied_monthly_basis_source_fingerprint"],
        temporal_semantic_fingerprint=supplied["supplied_temporal_semantic_fingerprint"],
        temporal_source_fingerprint=supplied["supplied_temporal_source_fingerprint"],
        pte_source_execution_fingerprint=pte["source_execution_fingerprint"],
        pte_source_result_fingerprint=pte["source_result_fingerprint"],
        monthly_estimate_gross_ils=amount,
        retirement_target_date=retirement_target_date,statement_date=statement_date)
    return _seal(values)


def estimate_single_pension_decision(factory, *, client_id: int,
                                     scenario_id: str, decision_id: str) -> dict:
    """Restricted service boundary: no posted factor or supplied hashes."""
    if (type(client_id) is not int or client_id<=0 or type(scenario_id) is not str
            or not scenario_id or len(scenario_id)>64
            or type(decision_id) is not str or not decision_id or len(decision_id)>64):
        raise ValueError("STAGE6_P1D_ROUTE_INVALID")
    try:
        return build_stage6_p1c_planning_snapshot(
            factory,client_id=client_id,scenario_id=scenario_id,decision_id=decision_id,
            _stage6_executor=_execute_verified)
    except ScenarioSnapshotError as exc:
        code=str(exc)
        if not code.startswith(("STAGE6_","SCENARIO_GLOBAL_TARGET_CONFLICT")):
            code="STAGE6_P1D_SNAPSHOT_UNAVAILABLE"
        return _blocked(client_id,scenario_id,decision_id,code)
