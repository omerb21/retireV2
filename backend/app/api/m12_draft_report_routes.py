"""Authenticated, non-mutating M12-P1 draft preview; no calculations or artifact storage."""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.transport import NO_STORE, error
from app.services.m12_draft_report_service import build
from app.services.scenario_draft_service import DraftError

router = APIRouter(prefix="/api/clients/{client_id}/m12-draft", tags=["m12-draft"])

@router.get("")
def read_draft(request: Request, client_id: int = Path(gt=0),
               db: Session = Depends(get_db)):
    try:
        return JSONResponse(build(db, client_id), headers=NO_STORE)
    except DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()
