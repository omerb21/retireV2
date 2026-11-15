"""Minimal M11 client-scoped preferred scenario API."""
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.transport import NO_STORE, error
from app.services import m11_preferred_scenario_service as service
from app.services.scenario_draft_service import DraftError

router = APIRouter(prefix="/api/clients/{client_id}/preferred-scenario", tags=["m11-preferred-scenario"])

class SavePreferredScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=64)
    expected_scenario_version: int = Field(gt=0)
    expected_selection_revision: int = Field(ge=0)
    rationale: str = Field(default="", max_length=5000)

@router.get("")
def get_preferred_scenario(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        return JSONResponse(service.read(db, client_id), headers=NO_STORE)
    except DraftError as exc:
        return error(request, exc.status, exc.code)
    finally:
        db.rollback()

@router.put("")
def set_preferred_scenario(request: Request, payload: SavePreferredScenario,
                           client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    actor = getattr(request.state, "trusted_professional_actor", None)
    if not isinstance(actor, str) or not actor:
        if request.app.state.auth_config.production:
            return error(request, 401, "AUTHENTICATION_REQUIRED")
        actor = "local-development-only"
    try:
        value = service.save(
            db, client_id=client_id, scenario_id=payload.scenario_id,
            expected_scenario_version=payload.expected_scenario_version,
            expected_selection_revision=payload.expected_selection_revision,
            rationale=payload.rationale, actor_id=actor,
        )
        db.commit()
        return JSONResponse(value, headers=NO_STORE)
    except DraftError as exc:
        db.rollback()
        return error(request, exc.status, exc.code)
    except Exception:
        db.rollback()
        raise
