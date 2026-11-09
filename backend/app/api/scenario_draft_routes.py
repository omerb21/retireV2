"""Client-scoped scenario drafts; every write is non-authoritative."""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.schemas.scenario_draft import DraftWrite, DraftRename, DraftReplace, DraftVersion
from app.schemas.scenario_severance_planning import SeverancePlanningReplace
from app.schemas.scenario_fixation_approval import (
    FixationProfessionalDraftReplace, FixationProfessionalApprovalRequest,
)
from app.services import scenario_fixation_approval_service as fixation_review_service
from app.security.transport import NO_STORE, error
from app.services import scenario_draft_service as service
from app.services import scenario_severance_planning_service as severance_service
from app.services.scenario_financial_evidence_service import _severance as severance_evidence
from app.services import scenario_calculation_admission_service as admission

router = APIRouter(prefix="/api/clients/{client_id}/scenario-drafts", tags=["scenario-drafts"])


def _actor(request: Request) -> str:
    actor = getattr(request.state, "trusted_professional_actor", None)
    if isinstance(actor, str) and actor:
        return actor
    if not request.app.state.auth_config.production:
        return "local-development-only"
    raise service.DraftError("AUTHENTICATION_REQUIRED", 401)


def _run(request, db, fn):
    try:
        response = fn()
        db.commit()
        return JSONResponse(content=response, headers=NO_STORE)
    except service.DraftError as exc:
        db.rollback()
        return error(request, exc.status, exc.code)
    except Exception:
        db.rollback()
        raise


@router.get("")
def list_scenarios(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        return JSONResponse(content=service.list_drafts(db, client_id), headers=NO_STORE)
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.get("/{scenario_id}")
def get_scenario(request: Request, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        return JSONResponse(content=service.read(db, client_id, scenario_id), headers=NO_STORE)
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.get("/{scenario_id}/calculation-admission")
def calculation_admission(request: Request, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        # The isolation statement MUST precede any SELECT in this transaction.
        # Unsupported DBs fail closed rather than silently weakening snapshot semantics.
        if db.in_transaction() or db.new or db.dirty or db.deleted:
            return error(request, 409, "SCENARIO_ADMISSION_REQUIRES_FRESH_TRANSACTION")
        if db.get_bind().dialect.name != "postgresql":
            return error(request, 503, "SCENARIO_ADMISSION_REQUIRES_POSTGRESQL")
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        with db.no_autoflush:
            result = admission.assess(db, client_id, scenario_id)
        return JSONResponse(content=result, headers=NO_STORE)
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.post("")
def create_scenario(request: Request, payload: DraftWrite, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.create(db, client_id, payload.name, _actor(request)))


@router.post("/{scenario_id}/duplicate")
def duplicate_scenario(request: Request, payload: DraftWrite, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.duplicate(db, client_id, scenario_id, payload.name, _actor(request)))


@router.put("/{scenario_id}")
def replace_scenario(request: Request, payload: DraftReplace, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.replace(db, client_id, scenario_id, payload, _actor(request)))


@router.post("/{scenario_id}/rename")
def rename_scenario(request: Request, payload: DraftRename, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.rename(
        db, client_id, scenario_id, payload.name, payload.expected_version, _actor(request),
    ))


@router.post("/{scenario_id}/archive")
def archive_scenario(request: Request, payload: DraftVersion, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.archive(db, client_id, scenario_id, payload.expected_version, _actor(request)))


def _severance_response(db: Session, client_id: int, scenario_id: str) -> dict:
    choices = severance_service.read_choices(db, client_id, scenario_id)
    evidence = severance_evidence(db, {"identity": {
        "client_id": client_id, "scenario_id": scenario_id,
        "scenario_version": choices["scenario_version"],
    }})
    # Read-only, client-scoped, DB-derived facts. Historical grants are NOT
    # paid cash, liquidity, tax exemptions or permission to execute.
    return {**choices, "source_evidence": evidence}


@router.get("/{scenario_id}/severance-planning")
def read_severance_planning(
    request: Request, scenario_id: str,
    client_id: int = Path(gt=0), db: Session = Depends(get_db),
):
    """Read current draft decisions only for the addressed client and scenario."""
    try:
        return JSONResponse(
            content=_severance_response(db, client_id, scenario_id),
            headers=NO_STORE,
        )
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.put("/{scenario_id}/severance-planning")
def save_severance_planning(
    request: Request, payload: SeverancePlanningReplace, scenario_id: str,
    client_id: int = Path(gt=0), db: Session = Depends(get_db),
):
    """Reuse the existing CAS/revision writer and caller-owned transaction."""
    def save():
        severance_service.replace_choices(
            db, client_id, scenario_id,
            expected_version=payload.expected_version,
            choices=[item.model_dump() for item in payload.choices],
            actor=_actor(request),
        )
        # The draft Session may use autoflush=False. Make the new revision
        # visible to read_choices inside the same uncommitted transaction.
        db.flush()
        # After write/flush, return actual current validated choices rather
        # than raw unverified client input or a financial calculation.
        return _severance_response(db, client_id, scenario_id)
    return _run(request, db, save)



@router.get("/{scenario_id}/fixation-professional-review")
def get_fixation_professional_review(
    request: Request, scenario_id: str,
    client_id: int = Path(gt=0), db: Session = Depends(get_db),
):
    """Real database read with current dependency validation, no tax execution."""
    try:
        if db.get_bind().dialect.name != "postgresql":
            return error(request, 503, "FIXATION_APPROVAL_REQUIRES_POSTGRESQL")
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        return JSONResponse(
            content=fixation_review_service.read(db, client_id, scenario_id),
            headers=NO_STORE,
        )
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.get("/{scenario_id}/fixation-professional-review/history")
def get_fixation_professional_review_history(
    request: Request, scenario_id: str,
    client_id: int = Path(gt=0), db: Session = Depends(get_db),
):
    try:
        if db.get_bind().dialect.name != "postgresql":
            return error(request, 503, "FIXATION_APPROVAL_REQUIRES_POSTGRESQL")
        return JSONResponse(
            content=fixation_review_service.history(db, client_id, scenario_id),
            headers=NO_STORE,
        )
    except service.DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()


@router.put("/{scenario_id}/fixation-professional-review")
def save_fixation_professional_review(
    request: Request, payload: FixationProfessionalDraftReplace,
    scenario_id: str, client_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    return _run(request, db, lambda: fixation_review_service.save_draft(
        db, client_id, scenario_id, payload, _actor(request),
    ))


@router.post("/{scenario_id}/fixation-professional-review/approve")
def approve_fixation_professional_review(
    request: Request, payload: FixationProfessionalApprovalRequest,
    scenario_id: str, client_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    """Explicit request; never grants approval until admission is implemented."""
    return _run(request, db, lambda: fixation_review_service.request_internal_approval(
        db, client_id, scenario_id, payload.expected_approval_version,
        payload.expected_approval_fingerprint, _actor(request),
    ))
