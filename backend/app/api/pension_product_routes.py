"""Canonical product endpoints; registered only with the atomic legacy cutover."""
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pension_product import ProductCreate, ProductUpdate, SaveSelected
from app.services.canonical_pension_source_reader import current_products
from app.services.pension_product_import_service import import_source
from app.services.pension_product_service import PensionProductError, create_product, delete_product, get_product, lock_client, product_response, save_selected, update_product


router = APIRouter(prefix="/api/clients/{client_id}/pension-products", tags=["pension-products"])
ACTOR = "planner:pension-products"


def _write(db: Session, operation: Callable):
    try:
        result = operation()
        db.commit()
        return result
    except PensionProductError as error:
        db.rollback()
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": "PRODUCT_INTEGRITY_CONFLICT", "message": "הפעולה לא בוצעה עקב תלות קיימת או התנגשות נתונים"}) from error
    except OperationalError as error:
        db.rollback()
        raise HTTPException(409, detail={"code": "PRODUCT_TRANSACTION_RETRY", "message": "הפעולה לא בוצעה. יש לטעון את הנתונים ולנסות שוב"}) from error
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, detail={"code": "INVALID_PRODUCT_SOURCE", "message": "נתוני המוצר או המקור אינם תקינים"}) from error
    except Exception:
        db.rollback()
        raise


@router.get("")
def list_products(client_id: int, db: Session = Depends(get_db)):
    try:
        return current_products(db, client_id)
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error


@router.post("", status_code=201)
def create(client_id: int, payload: ProductCreate, db: Session = Depends(get_db)):
    return _write(db, lambda: product_response(db, create_product(db, client_id, payload, ACTOR)))


@router.post("/imports")
async def import_products(client_id: int, file: UploadFile, db: Session = Depends(get_db)):
    try:
        # Read at most the accepted size plus one, before any database mutation.
        raw = await file.read(26_214_401)
        return _write(db, lambda: [product_response(db, product) for product in import_source(db, client_id, raw, (file.filename or "source.xml")[:255], ACTOR)])
    finally:
        await file.close()


@router.post("/save-selected")
def save(client_id: int, payload: SaveSelected, db: Session = Depends(get_db)):
    return _write(db, lambda: [product_response(db, product) for product in save_selected(db, client_id, payload, ACTOR)])


@router.get("/{product_id}")
def detail(client_id: int, product_id: str, db: Session = Depends(get_db)):
    try:
        lock_client(db, client_id)
        return product_response(db, get_product(db, client_id, product_id))
    except PensionProductError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error


@router.put("/{product_id}")
def update(client_id: int, product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    return _write(db, lambda: product_response(db, update_product(db, client_id, product_id, payload, ACTOR)))


@router.delete("/{product_id}", status_code=204)
def remove(client_id: int, product_id: str, expected_version: int = Query(ge=1), db: Session = Depends(get_db)):
    _write(db, lambda: delete_product(db, client_id, product_id, expected_version, ACTOR))
    return Response(status_code=204)
