"""Stage 6 internal nonbinding estimate preview.

Not mounted in production. Even for a local development app it requires the
trusted actor installed by existing security middleware, never request input.
No request-controlled coefficients, identity hashes or financial authority.
"""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.security.transport import NO_STORE, error, validate_session
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
    # Development middleware skips auth, so independently validate a genuine
    # signed session. Never invent a local-development planner identity.
    if not request.app.state.auth_config.production:
        rejected=validate_session(request, request.app.state.auth_config)
        if rejected is not None:
            return rejected
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


# SC-05C draft election management shares the same closed internal router.
# Production registration remains disabled pending complete release acceptance.
from app.schemas.scenario_pension_election import ScenarioPensionElectionSet
from app.services.scenario_pension_election_store_service import (
    current_elections, replace_elections,
)
from app.services.scenario_draft_service import DraftError
from app.db.session import get_db


def _verified_internal_actor(request: Request):
    if request.app.state.auth_config.production:
        return None
    if validate_session(request,request.app.state.auth_config) is not None:
        return None
    actor=getattr(request.state,"trusted_professional_actor",None)
    return actor if isinstance(actor,str) and actor.strip() else None


@router.get("/{scenario_id}/pension-elections")
def read_internal_pension_elections(
    request: Request,scenario_id: str,client_id: int=Path(gt=0),
    db: Session=Depends(get_db)):
    if _verified_internal_actor(request) is None:
        return error(request,401,"AUTHENTICATION_REQUIRED")
    try:
        return JSONResponse(content={"elections":current_elections(db,client_id,scenario_id)},
                            headers=NO_STORE)
    except DraftError as exc:
        return error(request,exc.status,exc.code)
    finally:
        db.rollback()


@router.put("/{scenario_id}/pension-elections")
def save_internal_pension_elections(
    request: Request,payload: ScenarioPensionElectionSet,scenario_id: str,
    client_id: int=Path(gt=0),db: Session=Depends(get_db)):
    actor=_verified_internal_actor(request)
    if actor is None:
        return error(request,401,"AUTHENTICATION_REQUIRED")
    try:
        result=replace_elections(db,client_id,scenario_id,payload,actor)
        db.commit()
        return JSONResponse(content=result,headers=NO_STORE)
    except DraftError as exc:
        db.rollback()
        return error(request,exc.status,exc.code)
    except Exception:
        db.rollback()
        raise
