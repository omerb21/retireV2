"""Stage 6 P1D: nonbinding one-decision gross estimate, canonical PTE only.

No database writes. No automatic coefficient selection. All financial execution
is gated inside the existing REPEATABLE READ READ ONLY snapshot owner.
"""
from __future__ import annotations
from app.services.pension_monthly_basis_service import fingerprint
from app.services.scenario_snapshot_candidate_service import (
    ScenarioSnapshotError, _STAGE6_P1D_EXECUTION_CAPABILITY,
    build_stage6_p1c_planning_snapshot,
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
_PLANNING_FIELDS={
    "contract_version", "client_id", "scenario_id", "scenario_version",
    "decision_id", "planning_calculation_input_fingerprint",
    "retirement_target", "pension_inputs",
}
_MONTHLY_FIELDS={
    "contract_version", "source_id", "source_kind", "authority_kind",
    "base_amount_representation", "base_amount_effective_date",
    "basis_authority_ready", "basis_blockers",
    "base_amount_semantic_fingerprint", "base_amount_source_fingerprint",
}
_TEMPORAL_FIELDS={
    "contract_version", "source_id", "source_kind", "temporal_authority_kind",
    "temporal_origin_date", "annual_rate", "rate_basis",
    "temporal_authority_ready", "temporal_blockers",
    "temporal_semantic_fingerprint", "temporal_source_fingerprint",
}


def _is_hash(value) -> bool:
    return (type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


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
    sources=planning_result.get("pension_inputs")
    if (set(planning_result)!=_PLANNING_FIELDS
            or planning_result.get("contract_version")!="SCENARIO_PENSION_PLANNING_RESULT_V1"
            or type(sources) is not list or len(sources)!=1
            or set(sources[0])!={"source_id","pension_start_date","currency",
                                "monthly_amount_basis","temporal_authority"}
            or sources[0].get("source_id")!=source_id
            or sources[0].get("pension_start_date")!=retirement_target_date
            or sources[0].get("currency")!="ILS"
            or planning_result.get("client_id")!=identities.get("client_id")
            or planning_result.get("scenario_id")!=identities.get("scenario_id")
            or planning_result.get("scenario_version")!=identities.get("scenario_version")
            or planning_result.get("decision_id")!=identities.get("decision_id")
            or planning_result["retirement_target"]!={"retirement_target_date":retirement_target_date,
                                                      "retirement_target_ready":True}):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_RESULT_INVALID")
    # Reject missing or malformed authority before comparing nested producer data.
    for key in ("planning_calculation_input_fingerprint",
                "professional_admission_fingerprint",
                "monthly_semantic_fingerprint", "monthly_source_fingerprint",
                "temporal_semantic_fingerprint", "temporal_source_fingerprint"):
        if not _is_hash(identities.get(key)):
            raise ScenarioSnapshotError("STAGE6_P1D_IDENTITY_INVALID")
    monthly=sources[0].get("monthly_amount_basis")
    temporal=sources[0].get("temporal_authority")
    if (type(monthly) is not dict or set(monthly)!=_MONTHLY_FIELDS
            or monthly.get("contract_version")!="canonical-pension-monthly-amount-basis-v1"
            or monthly.get("source_id")!=source_id
            or monthly.get("source_kind")!="scenario_decision"
            or monthly.get("authority_kind")!="scenario_decision_balance_ratio"
            or monthly.get("base_amount_representation")!={
                "representation_kind":"exact_ratio",
                "numerator":identities.get("amount"),
                "denominator":approval.get("factor_value"),
            }
            or monthly.get("base_amount_effective_date")!=statement_date
            or monthly.get("basis_authority_ready") is not True
            or monthly.get("basis_blockers")!=[]
            or monthly.get("base_amount_semantic_fingerprint")
                !=identities.get("monthly_semantic_fingerprint")
            or monthly.get("base_amount_source_fingerprint")
                !=identities.get("monthly_source_fingerprint")):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_RESULT_INVALID")
    if (type(temporal) is not dict or set(temporal)!=_TEMPORAL_FIELDS
            or temporal.get("contract_version")!="canonical-pension-temporal-indexation-basis-v1"
            or temporal.get("source_id")!=source_id
            or temporal.get("source_kind")!="scenario_decision"
            or temporal.get("temporal_authority_kind")!="none"
            or temporal.get("temporal_origin_date")!=statement_date
            or temporal.get("annual_rate") is not None
            or temporal.get("rate_basis") is not None
            or temporal.get("temporal_authority_ready") is not True
            or temporal.get("temporal_blockers")!=[]
            or temporal.get("temporal_semantic_fingerprint")
                !=identities.get("temporal_semantic_fingerprint")
            or temporal.get("temporal_source_fingerprint")
                !=identities.get("temporal_source_fingerprint")):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_RESULT_INVALID")
    if (planning_result.get("planning_calculation_input_fingerprint")
            != identities.get("planning_calculation_input_fingerprint")):
        raise ScenarioSnapshotError("STAGE6_P1D_PLANNING_IDENTITY_MISMATCH")
    if (approval.get("source_id")!=source_id
            or approval.get("professional_admission_fingerprint")
                !=identities.get("professional_admission_fingerprint")):
        raise ScenarioSnapshotError("STAGE6_P1D_PROFESSIONAL_ADMISSION_MISMATCH")
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
            or any(not _is_hash(pte.get(k))
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
            _stage6_executor=_execute_verified,
            _stage6_capability=_STAGE6_P1D_EXECUTION_CAPABILITY)
    except ScenarioSnapshotError as exc:
        code=str(exc)
        if not code.startswith(("STAGE6_","SCENARIO_GLOBAL_TARGET_CONFLICT")):
            code="STAGE6_P1D_SNAPSHOT_UNAVAILABLE"
        return _blocked(client_id,scenario_id,decision_id,code)
