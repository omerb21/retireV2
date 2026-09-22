from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pension_product_routes import _write
from app.schemas.planning_input import BaseDateDecision, IncomeResolutionDecision, TargetDateDecision
from sqlalchemy.exc import OperationalError
from app.services import planning_input_service as service
from app.services.pension_product_service import PensionProductError
from app.services import capital_projection_basis_service as projection
from app.schemas.capital_projection_basis import ProjectionDecisionWrite, ProjectionExpectations

router = APIRouter(prefix="/api/clients/{client_id}/retirement-planning-input", tags=["planning-input"])


@router.get("")
def read(client_id: int, db: Session = Depends(get_db)):
    try:
        result = service.read(db, client_id)
        result['projection_basis'] = projection.derive(db, client_id, result)
        return result
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


@router.get('/projection-basis')
def read_projection(client_id: int, db: Session = Depends(get_db)):
    try:
        return projection.read(db, client_id)
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={'code': error.code, 'message': error.message}) from error
    finally:
        db.rollback()


def projection_write(db, client_id, capital_asset_id, payload, *, clear=False):
    try:
        result = projection.write(db, client_id, capital_asset_id, payload, clear=clear)
        db.commit()
        return result
    except OperationalError as error:
        db.rollback()
        raise HTTPException(409, detail={'code': 'PROJECTION_TRANSACTION_RETRY',
            'message': 'ההחלטה לא נשמרה; יש לרענן ולנסות שוב במפורש'}) from error
    except PensionProductError as error:
        db.rollback()
        raise HTTPException(error.status_code, detail={'code': error.code, 'message': error.message}) from error
    except Exception:
        db.rollback()
        raise


@router.put('/projection-basis/{capital_asset_id}')
def save_projection(client_id: int, capital_asset_id: int, payload: ProjectionDecisionWrite, db: Session = Depends(get_db)):
    return projection_write(db, client_id, capital_asset_id, payload)


@router.put('/projection-basis/{capital_asset_id}/clear')
def clear_projection(client_id: int, capital_asset_id: int, payload: ProjectionExpectations, db: Session = Depends(get_db)):
    return projection_write(db, client_id, capital_asset_id, payload, clear=True)
