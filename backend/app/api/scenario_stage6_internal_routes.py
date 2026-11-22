"""Stage 6 staging-only, signed-session workflow.

Not mounted by default or on the Railway production environment.
No request-controlled coefficients, identity hashes or financial authority.
"""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.security.transport import NO_STORE, error, validate_session, validate_csrf, validate_origin
from app.services.scenario_stage6_single_pension_estimate_service import (
    estimate_scenario_pension_aggregate, estimate_single_pension_decision,
)
from app.services.scenario_stage6_monthly_cashflow_service import (
    build_scenario_monthly_cashflow,
)
from app.services.scenario_stage6_monthly_comparison_service import (
    compare_scenario_monthly_cashflows,
)
from app.services.scenario_snapshot_candidate_service import ScenarioSnapshotError
from app.services.scenario_pension_price_basis_service import save_explicit_decision

router = APIRouter(
    prefix="/api/clients/{client_id}/scenario-drafts",
    tags=["stage6-internal-estimate"],
)


def get_stage6_factory() -> sessionmaker[Session]:
    return get_session_factory()


class MonthlyComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scenario_a_id: str = Field(min_length=1, max_length=64)
    scenario_a_version: int = Field(gt=0)
    scenario_b_id: str = Field(min_length=1, max_length=64)
    scenario_b_version: int = Field(gt=0)
    start_month: str = Field(min_length=7, max_length=7)
    end_month: str = Field(min_length=7, max_length=7)


class ScenarioPensionPriceDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_scenario_version: int = Field(gt=0)
    expected_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_target_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    expected_revision: int = Field(ge=0)
    price_basis: Literal["NOMINAL_AT_RETIREMENT_TARGET_DATE", "UNKNOWN"]


@router.post("/{scenario_id}/pension-decisions/{decision_id}/price-basis")
def save_stage6_pension_price_basis(
    request: Request, payload: ScenarioPensionPriceDecisionRequest,
    scenario_id: str, decision_id: str,
    client_id: int = Path(gt=0), factory: sessionmaker[Session] = Depends(get_stage6_factory),
):
    if not getattr(request.app.state, "stage6_preview_enabled", False):
        return error(request, 404, "ROUTE_NOT_FOUND")
    actor = _verified_internal_actor(request)
    if actor is None:
        return error(request, 401, "AUTHENTICATION_REQUIRED")
    rejected = validate_origin(request, request.app.state.auth_config) or validate_csrf(request)
    if rejected is not None:
        return rejected
    if not scenario_id or len(scenario_id) > 64 or not decision_id or len(decision_id) > 64:
        return error(request, 422, "S6_PRICE_BASIS_ROUTE_INVALID")
    from app.services.scenario_draft_service import DraftError
    try:
        result = save_explicit_decision(
            factory, client_id=client_id, scenario_id=scenario_id, decision_id=decision_id,
            expected_scenario_version=payload.expected_scenario_version,
            expected_source_fingerprint=payload.expected_source_fingerprint,
            expected_target_fingerprint=payload.expected_target_fingerprint,
            expected_target_date=payload.expected_target_date,
            expected_revision=payload.expected_revision,
            price_basis=payload.price_basis, actor=actor,
        )
        return JSONResponse(content=result, headers=NO_STORE)
    except DraftError as exc:
        return error(request, exc.status, exc.code)


@router.get("/capabilities/gross-scenario-results")
def internal_gross_scenario_results_capability(request: Request):
    if not getattr(request.app.state, "stage6_preview_enabled", False):
        return error(request, 404, "ROUTE_NOT_FOUND")
    if _verified_internal_actor(request) is None:
        return error(request, 401, "AUTHENTICATION_REQUIRED")
    return JSONResponse(
        content={"stage6_gross_scenario_results": True}, headers=NO_STORE,
    )


@router.post("/monthly-income-comparison")
def internal_monthly_income_comparison(
    request: Request,
    payload: MonthlyComparisonRequest,
    client_id: int = Path(gt=0),
    factory: sessionmaker[Session] = Depends(get_stage6_factory),
):
    if not getattr(request.app.state, "stage6_preview_enabled", False):
        return error(request, 404, "ROUTE_NOT_FOUND")
    if _verified_internal_actor(request) is None:
        return error(request, 401, "AUTHENTICATION_REQUIRED")
    rejected = validate_origin(request, request.app.state.auth_config) or validate_csrf(request)
    if rejected is not None:
        return rejected
    try:
        result = compare_scenario_monthly_cashflows(
            factory, client_id=client_id, **payload.model_dump(),
        )
    except ValueError as exc:
        return error(request, 422, str(exc))
    except ScenarioSnapshotError as exc:
        status = 404 if exc.code == "SCENARIO_NOT_FOUND" else 503 if exc.code in {
            "STAGE6_COMPARISON_REQUIRES_POSTGRESQL",
            "STAGE6_COMPARISON_DATABASE_UNAVAILABLE",
            "STAGE6_COMPARISON_CLEANUP_FAILED",
        } else 409
        return error(request, status, exc.code)
    return JSONResponse(content=result, headers=NO_STORE)


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


@router.get("/{scenario_id}/pension-gross-summary")
def internal_pension_gross_summary(
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
        return error(request, 422, "STAGE6_AGGREGATE_ROUTE_INVALID")
    result = estimate_scenario_pension_aggregate(
        factory, client_id=client_id, scenario_id=scenario_id,
    )
    return JSONResponse(content=result, headers=NO_STORE)


@router.get("/{scenario_id}/monthly-income-cashflow")
def internal_monthly_income_cashflow(
    request: Request,
    scenario_id: str,
    start_month: str,
    end_month: str,
    client_id: int = Path(gt=0),
    factory: sessionmaker[Session] = Depends(get_stage6_factory),
):
    if not getattr(request.app.state, "stage6_preview_enabled", False):
        return error(request, 404, "ROUTE_NOT_FOUND")
    if _verified_internal_actor(request) is None:
        return error(request, 401, "AUTHENTICATION_REQUIRED")
    try:
        result = build_scenario_monthly_cashflow(
            factory, client_id=client_id, scenario_id=scenario_id,
            start_month=start_month, end_month=end_month,
        )
    except ValueError as exc:
        return error(request, 422, str(exc))
    return JSONResponse(content=result, headers=NO_STORE)


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
