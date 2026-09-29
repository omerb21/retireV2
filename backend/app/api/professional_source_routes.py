from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pension_product_routes import _write
from app.schemas.canonical_manual_pension_source import (
    ConversionTemporalDecisionWrite, ManualPensionInput, ManualPensionUpdate, ManualPensionSupersede,
)
from app.services import canonical_manual_pension_service as manual
from app.services import pension_temporal_basis_service as temporal
from app.services.professional_source_snapshot_service import snapshot
from app.services.pension_product_service import PensionProductError

router = APIRouter(prefix="/api/clients/{client_id}", tags=["professional-source-snapshot"])


@router.get("/professional-source-snapshot")
def read_snapshot(client_id: int, db: Session = Depends(get_db)):
    try:
        return snapshot(db, client_id)
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error
    finally:
        db.rollback()


@router.post("/canonical-pension-sources/manual")
def create_manual(client_id: int, payload: ManualPensionInput, db: Session = Depends(get_db)):
    return _write(db, lambda: manual.create(db, client_id, payload))


@router.put("/canonical-pension-sources/manual/{source_id}")
def update_manual(client_id: int, source_id: str, payload: ManualPensionUpdate, db: Session = Depends(get_db)):
    return _write(db, lambda: manual.change(db, client_id, source_id, payload))


@router.delete("/canonical-pension-sources/manual/{source_id}")
def supersede_manual(client_id: int, source_id: str, payload: ManualPensionSupersede, db: Session = Depends(get_db)):
    return _write(db, lambda: manual.change(db, client_id, source_id, payload, supersede=True))


@router.put("/canonical-pension-sources/conversion/{destination_id}/temporal-authority")
def write_conversion_temporal(client_id: int, destination_id: str, payload: ConversionTemporalDecisionWrite,
                              db: Session = Depends(get_db)):
    return _write(db, lambda: temporal.write_conversion(db, client_id, destination_id, payload))
