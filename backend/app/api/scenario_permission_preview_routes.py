from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.schemas.scenario_permission_preview import ScenarioPermissionPreviewRequest
from app.security.transport import NO_STORE, error
from app.services import scenario_permission_preview_service as preview_service


router = APIRouter(
    prefix="/api/clients/{client_id}/scenario-conversions",
    tags=["scenario-permission-preview"],
)


def get_preview_session_factory() -> sessionmaker[Session]:
    return get_session_factory()


@router.post("/permission-preview")
def permission_preview(
    request: Request,
    payload: ScenarioPermissionPreviewRequest,
    client_id: int = Path(gt=0),
    factory: sessionmaker[Session] = Depends(get_preview_session_factory),
):
    try:
        result = preview_service.preview(
            factory,
            client_id=client_id,
            product_id=payload.product_id,
            action=payload.action,
            effective_date=payload.effective_date,
        )
        return JSONResponse(content=result, headers=NO_STORE)
    except preview_service.ScenarioPermissionError as exc:
        return error(request, exc.status_code, exc.code, exc.field_paths)
