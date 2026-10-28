"""Stage 6 factor admission: authenticated, append-only, serializable write API.

No execution of pension result; only professional assumption acknowledgment.
The request does not contain an actor, option, source, or fingerprint authority.
"""
from typing import Literal
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.security.transport import NO_STORE, error
from app.services.scenario_pension_factor_admission_write_service import (
    PensionFactorWriteBlocked, append_authenticated_serializable_factor_admission,
)

router=APIRouter(prefix="/api/clients/{client_id}/scenario-drafts",
                 tags=["stage6-professional-admission"])


class ProfessionalFactorAdmissionRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    expected_scenario_version: int=Field(gt=0)
    expected_admission_revision: int=Field(ge=0)
    factor_value: str=Field(min_length=1,max_length=128)
    factor_evidence_type: Literal["INSURER_QUOTE","POLICY_CONTRACT","PLANNER_ASSUMPTION"]
    factor_evidence_reference: str=Field(min_length=1,max_length=512)


def get_stage6_admission_factory() -> sessionmaker[Session]:
    return get_session_factory()


@router.post("/{scenario_id}/pension-decisions/{decision_id}/factor-admissions")
def approve_professional_factor(
    request: Request,
    payload: ProfessionalFactorAdmissionRequest,
    scenario_id: str,
    decision_id: str,
    client_id: int=Path(gt=0),
    factory: sessionmaker[Session]=Depends(get_stage6_admission_factory),
):
    if (not getattr(request.app.state,"stage6_preview_enabled",False)
            or not request.app.state.auth_config.production):
        return error(request,404,"ROUTE_NOT_FOUND")
    if not scenario_id or len(scenario_id)>64 or not decision_id or len(decision_id)>64:
        return error(request,422,"FACTOR_ADMISSION_REQUEST_INVALID")
    try:
        result=append_authenticated_serializable_factor_admission(
            factory,request=request,client_id=client_id,
            scenario_id=scenario_id,decision_id=decision_id,
            expected_scenario_version=payload.expected_scenario_version,
            expected_admission_revision=payload.expected_admission_revision,
            factor_value=payload.factor_value,
            factor_evidence_type=payload.factor_evidence_type,
            factor_evidence_reference=payload.factor_evidence_reference,
        )
        return JSONResponse(content=result,headers=NO_STORE)
    except PensionFactorWriteBlocked as exc:
        return error(request,409,str(exc))


# Informational CAS cursor only: never an approval, permission, or executable state.
from sqlalchemy import func, select, text
from app.db.session import get_db
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission


@router.get("/{scenario_id}/pension-decisions/{decision_id}/factor-admissions/revision")
def current_admission_revision(
    request: Request,scenario_id: str,decision_id: str,
    client_id: int=Path(gt=0),db: Session=Depends(get_db),
):
    if not getattr(request.app.state,"stage6_preview_enabled",False):
        return error(request,404,"ROUTE_NOT_FOUND")
    session=getattr(request.state,"auth_session",None)
    actor=getattr(request.state,"trusted_professional_actor",None)
    if (type(session) is not dict or type(actor) is not str
            or not actor.strip() or actor!=session.get("actor_id")):
        return error(request,401,"AUTHENTICATION_REQUIRED")
    if not scenario_id or len(scenario_id)>64 or not decision_id or len(decision_id)>64:
        return error(request,422,"FACTOR_ADMISSION_REQUEST_INVALID")
    try:
        if db.in_transaction() or db.get_bind().dialect.name!="postgresql":
            return error(request,409,"FACTOR_ADMISSION_FRESH_SNAPSHOT_REQUIRED")
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        scenario=db.scalar(select(ScenarioDraft).where(
            ScenarioDraft.client_id==client_id,ScenarioDraft.scenario_id==scenario_id))
        if scenario is None or scenario.status!="draft":
            return error(request,409,"FACTOR_ADMISSION_SCENARIO_STALE")
        decision=db.scalar(select(ScenarioDraftDecision).where(
            ScenarioDraftDecision.scenario_id==scenario_id,
            ScenarioDraftDecision.decision_id==decision_id,
            ScenarioDraftDecision.action=="pension"))
        if decision is None:
            return error(request,404,"FACTOR_ADMISSION_DECISION_INVALID")
        revision=db.scalar(select(func.max(ScenarioPensionFactorAdmission.admission_revision)).where(
            ScenarioPensionFactorAdmission.client_id==client_id,
            ScenarioPensionFactorAdmission.scenario_id==scenario_id,
            ScenarioPensionFactorAdmission.decision_id==decision_id))
        return JSONResponse(content={
            "scenario_version":scenario.version,
            "latest_admission_revision":revision or 0,
            "authority_state":"NOT_EVALUATED",
        },headers=NO_STORE)
    finally:
        db.rollback()
