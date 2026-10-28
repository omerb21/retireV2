"""Synthetic-only Stage 6 demonstration using the actual canonical P1C and PTE owners.

No database, no customer records, no admission state, no production authorization.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.pension_monthly_basis_service import scenario_decision_monthly_identity
from app.services.pension_temporal_basis_service import scenario_decision_temporal_identity
from app.services.planning_input_service import scenario_decision_one_source_planning_result
from app.services.scenario_stage6_single_pension_estimate_service import _execute_verified

router = APIRouter(prefix="/demo/stage6", tags=["synthetic"])

class SyntheticInput(BaseModel):
    balance: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,11})\\.[0-9]{2}$")
    divisor: str = Field(pattern=r"^[1-9][0-9]{0,4}$")

@router.post("/estimate")
def estimate(value: SyntheticInput):
    try:
        amount = Decimal(value.balance)
        divisor = Decimal(value.divisor)
        if amount <= 0 or divisor <= 0:
            raise ValueError("nonpositive")
        src = dict(
            client_id=1, scenario_id="synthetic", scenario_version=2,
            decision_id="pension", manifest_fingerprint="a"*64,
            partition_fingerprint="b"*64, source_product_id="synthetic-p",
            source_product_version=3, source_component_id="synthetic-c",
            component_code="synthetic-pension", source_fingerprint="c"*64,
            amount=value.balance, statement_date="2026-09-30",
            election_fingerprint="d"*64, professional_admission_revision=1,
            professional_admission_fingerprint="e"*64, factor_value=value.divisor,
        )
        monthly = scenario_decision_monthly_identity(src)
        temporal = scenario_decision_temporal_identity(dict(
            source_id=monthly["source_id"], client_id=src["client_id"],
            scenario_id=src["scenario_id"], scenario_version=src["scenario_version"],
            decision_id=src["decision_id"], statement_date=src["statement_date"],
            retirement_target_date="2027-09-30",
            monthly_source_fingerprint=monthly["monthly_source_fingerprint"],
            professional_admission_fingerprint=src["professional_admission_fingerprint"],
        ))
        facts = dict(
            client_id=src["client_id"], scenario_id=src["scenario_id"],
            scenario_version=src["scenario_version"], decision_id=src["decision_id"],
            source_id=monthly["source_id"], manifest_fingerprint=src["manifest_fingerprint"],
            partition_fingerprint=src["partition_fingerprint"],
            source_fingerprint=src["source_fingerprint"],
            statement_date=src["statement_date"], amount=src["amount"],
            action="pension", election_fingerprint=src["election_fingerprint"],
            retirement_target_date="2027-09-30",
            monthly_semantic_fingerprint=monthly["monthly_semantic_fingerprint"],
            monthly_source_fingerprint=monthly["monthly_source_fingerprint"],
            temporal_semantic_fingerprint=temporal["temporal_semantic_fingerprint"],
            temporal_source_fingerprint=temporal["temporal_source_fingerprint"],
            professional_admission_revision=1,
            professional_admission_fingerprint=src["professional_admission_fingerprint"],
            ruleset_digest="f"*64, permission_admission_fingerprint="0"*64,
        )
        planning = scenario_decision_one_source_planning_result(
            facts=facts, monthly=monthly, temporal=temporal, factor_value=value.divisor,
        )
        result = _execute_verified(
            planning_result=planning,
            approval=dict(
                factor_value=value.divisor,
                factor_evidence_type="PLANNER_ASSUMPTION",
                factor_evidence_reference="synthetic test input only",
                payout_option_name="synthetic",
                admission_revision=1,
                source_id=facts["source_id"],
                professional_admission_fingerprint=src["professional_admission_fingerprint"],
            ),
            statement_date=src["statement_date"],
            retirement_target_date=facts["retirement_target_date"],
            five_identities=dict(facts,
                planning_calculation_input_fingerprint=planning[
                    "planning_calculation_input_fingerprint"]),
        )
        return {"synthetic_only": True, "engine": "canonical_P1C_PTE_P1D",
                "result": result}
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail="SYNTHETIC_INPUT_INVALID") from exc
