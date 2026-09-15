from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pension_product_routes import _write
from app.schemas.planning_input import BaseDateDecision, IncomeResolutionDecision, TargetDateDecision
from sqlalchemy.exc import OperationalError
from app.services import planning_input_service as service
from app.services.pension_product_service import PensionProductError

router = APIRouter(prefix="/api/clients/{client_id}/retirement-planning-input", tags=["planning-input"])


@router.get("")
def read(client_id: int, db: Session = Depends(get_db)):
    try:
        return service.read(db, client_id)
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error
    finally:
        db.rollback()


@router.put("/base-date")
def set_base_date(client_id: int, payload: BaseDateDecision, db: Session = Depends(get_db)):
    return _write(db, lambda: service.set_base_date(db, client_id, payload))


@router.put("/income-resolutions/{income_id}")
def resolve_income(client_id: int, income_id: int, payload: IncomeResolutionDecision, db: Session = Depends(get_db)):
    return _write(db, lambda: service.resolve_income(db, client_id, income_id, payload))


@router.put("/target-date")
def set_target_date(client_id: int, payload: TargetDateDecision, db: Session = Depends(get_db)):
    from app.services.retirement_target_service import set_target
    try:
        result = set_target(db, client_id, payload)
        db.commit()
        return result
    except OperationalError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": "TARGET_DECISION_TRANSACTION_RETRY",
            "message": "ההחלטה לא נשמרה; יש לרענן ולנסות שוב במפורש"}) from error
    except PensionProductError as error:
        db.rollback()
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error
    except Exception:
        db.rollback()
        raise
