from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.client import Client
from app.schemas.fixation_m07 import (
    FixationEligibilityRevisionCreate,
    FixationEligibilityRevisionCreated,
    FixationEligibilityRevisionList,
)
from app.services.fixation_m07_service import (
    create_fixation_eligibility_revision,
    list_fixation_eligibility_revisions,
)


router = APIRouter(
    prefix="/api/clients/{client_id}/fixation/m07",
    tags=["fixation"],
)


def _require_client(db_session: Session, client_id: int) -> None:
    if db_session.get(Client, client_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CLIENT_NOT_FOUND",
                "message": f"Client {client_id} was not found",
            },
        )


@router.get(
    "/revisions",
    response_model=FixationEligibilityRevisionList,
)
def list_finalized_fixation_revisions(
    client_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> FixationEligibilityRevisionList:
    _require_client(db, client_id)
    return list_fixation_eligibility_revisions(
        db_session=db,
        client_id=client_id,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/eligibility-date-revisions",
    response_model=FixationEligibilityRevisionCreated,
    status_code=201,
)
def create_finalized_fixation_eligibility_revision(
    client_id: int,
    payload: FixationEligibilityRevisionCreate,
    db: Session = Depends(get_db),
) -> FixationEligibilityRevisionCreated:
    _require_client(db, client_id)
    return create_fixation_eligibility_revision(
        db_session=db,
        client_id=client_id,
        request=payload,
    )
