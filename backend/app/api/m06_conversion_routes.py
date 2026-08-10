from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m06_conversion import (
    M06CandidateResponse,
    M06CoefficientCorrectionRequest,
    M06EligibilityResponse,
    M06ResolveRequest,
    M06RevisionResponse,
    M06StartRequest,
    M06SubjectResponse,
    M06SupersedeRequest,
    M06WarningReviewRequest,
)
from app.services.m06_conversion_service import (
    M06ConversionError,
    correct_coefficient,
    eligibility,
    history,
    list_candidates,
    list_subjects,
    resolve_conversion,
    revision_eligibility,
    revision_response,
    start_conversion,
    subject_response,
    supersede_conversion,
    review_warnings,
)


router = APIRouter(prefix="/api/clients/{client_id}/m06", tags=["m06-conversion"])


def _run(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except M06ConversionError as error:
        raise HTTPException(
            error.status_code, detail={"code": error.code, "message": error.message}
        ) from error


@router.get("/candidates", response_model=list[M06CandidateResponse])
def candidates(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_candidates(db, client_id))


@router.get("/subjects", response_model=list[M06SubjectResponse])
def subjects(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_subjects(db, client_id))


@router.get("/subjects/{subject_id}", response_model=M06SubjectResponse)
def subject(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: subject_response(db, client_id, subject_id))


@router.get("/subjects/{subject_id}/history", response_model=list[M06RevisionResponse])
def subject_history(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: history(db, client_id, subject_id))


@router.get("/subjects/{subject_id}/eligibility", response_model=M06EligibilityResponse)
def downstream_eligibility(
    client_id: int, subject_id: str, db: Session = Depends(get_db)
):
    return _run(lambda: eligibility(db, client_id, subject_id))


@router.get(
    "/subjects/{subject_id}/revisions/{revision_id}/eligibility",
    response_model=M06EligibilityResponse,
)
def revision_downstream_eligibility(
    client_id: int,
    subject_id: str,
    revision_id: str,
    db: Session = Depends(get_db),
):
    return _run(lambda: revision_eligibility(db, client_id, subject_id, revision_id))


@router.post("/start", response_model=M06RevisionResponse, status_code=201)
def start(client_id: int, payload: M06StartRequest, db: Session = Depends(get_db)):
    return _run(lambda: revision_response(db, start_conversion(db, client_id, payload)))


@router.post(
    "/subjects/{subject_id}/resolve",
    response_model=M06RevisionResponse,
    status_code=201,
)
def resolve(
    client_id: int,
    subject_id: str,
    payload: M06ResolveRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db,
            resolve_conversion(
                db, client_id, subject_id, payload.expected_current_revision_id
            ),
        )
    )


@router.post(
    "/subjects/{subject_id}/review-warning",
    response_model=M06RevisionResponse,
    status_code=201,
)
def review_warning(
    client_id: int,
    subject_id: str,
    payload: M06WarningReviewRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, review_warnings(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/correct-coefficient",
    response_model=M06RevisionResponse,
    status_code=201,
)
def correct(
    client_id: int,
    subject_id: str,
    payload: M06CoefficientCorrectionRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, correct_coefficient(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/supersede",
    response_model=M06RevisionResponse,
    status_code=201,
)
def supersede(
    client_id: int,
    subject_id: str,
    payload: M06SupersedeRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, supersede_conversion(db, client_id, subject_id, payload)
        )
    )
