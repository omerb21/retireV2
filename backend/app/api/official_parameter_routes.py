from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.official_parameter_sets import (
    OfficialParameterResolution,
    OfficialParameterSetResponse,
    OfficialParameterStatus,
)
from app.services.official_parameter_service import (
    OfficialParameterSetNotFoundError,
    get_official_parameter_set,
    list_official_parameter_sets,
    official_parameter_set_response,
    resolve_official_parameter_set,
)


# The repository has no production administrator/role infrastructure. PKG-004A
# therefore exposes read-only inventory and resolution endpoints; lifecycle
# writes remain explicit service operations for a future authenticated boundary.
router = APIRouter(prefix="/api/official-parameter-sets", tags=["official-parameter-sets"])


@router.get("/resolve", response_model=OfficialParameterResolution)
def resolve_official_parameters(
    tax_year: int = Query(ge=1900, le=9999),
    effective_date: date = Query(),
    db: Session = Depends(get_db),
) -> OfficialParameterResolution:
    return resolve_official_parameter_set(
        db_session=db,
        tax_year=tax_year,
        effective_date=effective_date,
    )


@router.get("", response_model=list[OfficialParameterSetResponse])
def list_official_parameters(
    tax_year: int | None = Query(default=None, ge=1900, le=9999),
    status: OfficialParameterStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[OfficialParameterSetResponse]:
    return [
        official_parameter_set_response(row)
        for row in list_official_parameter_sets(
            db_session=db,
            tax_year=tax_year,
            status=status,
        )
    ]


@router.get("/{parameter_set_id}", response_model=OfficialParameterSetResponse)
def read_official_parameters(
    parameter_set_id: str,
    db: Session = Depends(get_db),
) -> OfficialParameterSetResponse:
    try:
        row = get_official_parameter_set(
            db_session=db,
            parameter_set_id=parameter_set_id,
        )
    except OfficialParameterSetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="official parameter set not found") from exc
    return official_parameter_set_response(row)
