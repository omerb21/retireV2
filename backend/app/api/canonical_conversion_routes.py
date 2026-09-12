"""Canonical conversion operations, with one transaction per request."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pension_product_routes import _write
from app.schemas.canonical_conversion import ConversionRequest, ReversalRequest
from app.services import canonical_component_conversion_service as service
from app.services.pension_product_service import lock_client, PensionProductError

router = APIRouter(prefix="/api/clients/{client_id}/canonical-conversions", tags=["canonical-conversions"])
ACTOR = "planner:canonical-conversions"


def _read(db, operation):
    try:
        return operation()
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error
    finally:
        db.rollback()


@router.post("/preview")
def preview(client_id: int, payload: ConversionRequest, db: Session = Depends(get_db)):
    return _read(db, lambda: service.preview(db, client_id, payload))


@router.post("")
def execute(client_id: int, payload: ConversionRequest, db: Session = Depends(get_db)):
    return _write(db, lambda: service.execute(db, client_id, payload, ACTOR))


@router.get("")
def history(client_id: int, product_id: str | None = None, db: Session = Depends(get_db)):
    def operation():
        lock_client(db, client_id)
        return service.history(db, client_id, product_id)
    return _read(db, operation)


@router.post("/{conversion_id}/reverse")
def reverse(client_id: int, conversion_id: str, payload: ReversalRequest, db: Session = Depends(get_db)):
    return _write(db, lambda: service.reverse(db, client_id, conversion_id, payload, ACTOR))
