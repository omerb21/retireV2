from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m10_comparison import M10ComparisonRequest, M10ComparisonResponse
from app.services.m09_cashflow_service import M09CashflowError
from app.services.m10_comparison_service import compare_runs


router = APIRouter(prefix="/api/clients/{client_id}/m10", tags=["m10-comparison"])


@router.post("/compare", response_model=M10ComparisonResponse)
def compare(
    client_id: int,
    payload: M10ComparisonRequest,
    db: Session = Depends(get_db),
):
    try:
        return compare_runs(db, client_id, payload)
    except M09CashflowError as error:
        raise HTTPException(
            error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
