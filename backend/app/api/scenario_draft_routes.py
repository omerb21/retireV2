"""Client-scoped scenario drafts; every write is non-authoritative."""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.scenario_draft import DraftWrite, DraftReplace, DraftVersion
from app.security.transport import NO_STORE, error
from app.services import scenario_draft_service as service

router = APIRouter(prefix="/api/clients/{client_id}/scenario-drafts", tags=["scenario-drafts"])


def _actor(request: Request) -> str:
    return str(getattr(request.state, "trusted_professional_actor", "development"))


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
