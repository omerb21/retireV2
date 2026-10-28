"""Stage 6 staging-only, signed-session workflow.

Not mounted by default or on the Railway production environment.
No request-controlled coefficients, identity hashes or financial authority.
"""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.security.transport import NO_STORE, error, validate_session, validate_csrf, validate_origin
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
    if not getattr(request.app.state,"stage6_preview_enabled",False):
        return error(request,404,"ROUTE_NOT_FOUND")
    actor=_verified_internal_actor(request)
    if actor is None:
        return error(request,401,"AUTHENTICATION_REQUIRED")
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
    if (not getattr(request.app.state,"stage6_preview_enabled",False)
            or request.app.state.auth_config.production is not True):
        return None
    # Require independently verified signed session; never trust a hand-set
    # request.state actor or a development authentication bypass.
    if validate_session(request,request.app.state.auth_config) is not None:
        return None
    actor=getattr(request.state,"trusted_professional_actor",None)
    session=getattr(request.state,"auth_session",None)
    return actor if (type(actor) is str and actor.strip()
                     and type(session) is dict
                     and session.get("actor_id")==actor) else None


@router.get("/{scenario_id}/pension-elections")
def read_internal_pension_elections(
    request: Request,scenario_id: str,client_id: int=Path(gt=0),
    db: Session=Depends(get_db)):
    if not getattr(request.app.state,"stage6_preview_enabled",False):
        return error(request,404,"ROUTE_NOT_FOUND")
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
    if not getattr(request.app.state,"stage6_preview_enabled",False):
        return error(request,404,"ROUTE_NOT_FOUND")
    actor=_verified_internal_actor(request)
    if actor is None:
        return error(request,401,"AUTHENTICATION_REQUIRED")
    # Defense-in-depth, in addition to production-mode middleware.
    rejected=validate_origin(request,request.app.state.auth_config) or validate_csrf(request)
    if rejected is not None:
        return rejected
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


# Read-only structural allocation evidence. This is NOT M09 execution, net
# income, fixation, permission approval or a Stage 6 aggregate estimate.
# The route inherits the existing staging-only mounting gate and signed session.
@router.get("/{scenario_id}/allocation-evidence")
def internal_allocation_evidence(
    request: Request,
    scenario_id: str,
    client_id: int = Path(gt=0),
    factory: sessionmaker[Session] = Depends(get_stage6_factory),
):
    if not getattr(request.app.state, "stage6_preview_enabled", False):
        return error(request, 404, "ROUTE_NOT_FOUND")
    if _verified_internal_actor(request) is None:
        return error(request, 401, "AUTHENTICATION_REQUIRED")
    if not scenario_id or len(scenario_id) > 64:
        return error(request, 422, "SCENARIO_ALLOCATION_ROUTE_INVALID")
    from app.services.scenario_allocation_snapshot_service import (
        build_readonly_allocation_snapshot,
    )
    from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError
    try:
        evidence = build_readonly_allocation_snapshot(
            factory, client_id=client_id, scenario_id=scenario_id,
        )
    except ScenarioSnapshotError:
        return error(request, 503, "SCENARIO_ALLOCATION_SNAPSHOT_UNAVAILABLE")
    except DraftError as exc:
        return error(request, exc.status, exc.code)
    return JSONResponse(content=evidence, headers=NO_STORE)
