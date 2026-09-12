"""Historical conversion archive. No professional mutation or eligibility API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.m06_conversion import M06RevisionResponse, M06SubjectResponse
from app.services.m06_conversion_service import M06ConversionError, history, list_subjects, subject_response

router = APIRouter(prefix="/api/clients/{client_id}/m06", tags=["legacy-conversion-archive"])


def _read(operation):
    try:
        return operation()
    except M06ConversionError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error


@router.get("/subjects", response_model=list[M06SubjectResponse])
def subjects(client_id: int, db: Session = Depends(get_db)):
    return _read(lambda: list_subjects(db, client_id))


@router.get("/subjects/{subject_id}", response_model=M06SubjectResponse)
def subject(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _read(lambda: subject_response(db, client_id, subject_id))


@router.get("/subjects/{subject_id}/history", response_model=list[M06RevisionResponse])
def subject_history(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _read(lambda: history(db, client_id, subject_id))
