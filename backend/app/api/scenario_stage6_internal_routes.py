"""Stage 6 internal nonbinding estimate preview.

Not mounted in production. Even for a local development app it requires the
trusted actor installed by existing security middleware, never request input.
No request-controlled coefficients, identity hashes or financial authority.
"""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.security.transport import NO_STORE, error
from app.services.scenario_stage6_single_pension_estimate_service import (
    estimate_single_pension_decision,
)

router = APIRouter(
    prefix="/api/clients/{client_id}/scenario-drafts",
    tags=["stage6-internal-estimate"],
)


def get_stage6_factory() -> sessionmaker[Session]:
    return get_session_factory()


@router.get("/{scenario_id}/pension-decisions/{decision_id}/gross-estimate")
def internal_gross_estimate(
    request: Request,
    scenario_id: str,
    decision_id: str,
    client_id: int = Path(gt=0),
    factory: sessionmaker[Session] = Depends(get_stage6_factory),
):
    actor=getattr(request.state,"trusted_professional_actor",None)
    if not isinstance(actor,str) or not actor.strip():
        return error(request,401,"AUTHENTICATION_REQUIRED")
    if request.app.state.auth_config.production:
        return error(request,404,"ROUTE_NOT_FOUND")
    if (not scenario_id or len(scenario_id)>64
            or not decision_id or len(decision_id)>64):
        return error(request,422,"STAGE6_P1D_ROUTE_INVALID")
    result=estimate_single_pension_decision(
        factory,client_id=client_id,scenario_id=scenario_id,decision_id=decision_id)
    return JSONResponse(content=result,headers=NO_STORE)
