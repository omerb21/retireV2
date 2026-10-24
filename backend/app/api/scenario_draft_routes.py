"""Client-scoped scenario drafts; every write is non-authoritative."""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.schemas.scenario_draft import DraftWrite, DraftReplace, DraftVersion
from app.security.transport import NO_STORE, error
from app.services import scenario_draft_service as service
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


@router.post("/{scenario_id}/archive")
def archive_scenario(request: Request, payload: DraftVersion, scenario_id: str, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _run(request, db, lambda: service.archive(db, client_id, scenario_id, payload.expected_version, _actor(request)))
