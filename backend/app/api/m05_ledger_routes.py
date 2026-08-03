from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m05_ledger import (
    M05AdjustmentRequest,
    M05CandidateResponse,
    M05EligibilityResponse,
    M05ReasonRequest,
    M05ReconcileRequest,
    M05RevalidateRequest,
    M05RevisionResponse,
    M05ReviewWarningRequest,
    M05StartRequest,
    M05SubjectResponse,
)
from app.services.m05_ledger_service import (
    M05LedgerError,
    adjust_ledger,
    eligibility,
    history,
    list_candidates,
    list_subjects,
    mark_blocked,
    reconcile_ledger,
    revalidate_ledger,
    review_warnings,
    revision_response,
    start_ledger,
    subject_response,
    supersede_ledger,
)


router = APIRouter(prefix="/api/clients/{client_id}/m05", tags=["m05-ledger"])


def _run(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except M05LedgerError as error:
        raise HTTPException(
            error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error


@router.get("/candidates", response_model=list[M05CandidateResponse])
def candidates(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_candidates(db, client_id))


@router.get("/subjects", response_model=list[M05SubjectResponse])
def subjects(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_subjects(db, client_id))


@router.get("/subjects/{subject_id}", response_model=M05SubjectResponse)
def subject(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: subject_response(db, client_id, subject_id))


@router.get(
    "/subjects/{subject_id}/history", response_model=list[M05RevisionResponse]
)
def subject_history(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: history(db, client_id, subject_id))


@router.get("/subjects/{subject_id}/provenance", response_model=dict[str, Any])
def provenance(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    def operation() -> dict[str, Any]:
        response = subject_response(db, client_id, subject_id)
        return response.current_revision.provenance if response.current_revision else {}

    return _run(operation)


@router.get("/subjects/{subject_id}/warnings", response_model=list[dict[str, Any]])
def warnings(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    def operation() -> list[dict[str, Any]]:
        response = subject_response(db, client_id, subject_id)
        return response.current_revision.warnings if response.current_revision else []

    return _run(operation)


@router.get(
    "/subjects/{subject_id}/m06-eligibility",
    response_model=M05EligibilityResponse,
)
def m06_eligibility(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: eligibility(db, client_id, subject_id))


@router.post("/start", response_model=M05RevisionResponse, status_code=201)
def start(client_id: int, payload: M05StartRequest, db: Session = Depends(get_db)):
    return _run(
        lambda: revision_response(
            db,
            start_ledger(
                db,
                client_id,
                payload.candidate_id,
                confirm_currency_ils=bool(payload.confirm_currency_ils),
            ),
        )
    )


@router.post(
    "/subjects/{subject_id}/reconcile",
    response_model=M05RevisionResponse,
    status_code=201,
)
def reconcile(
    client_id: int,
    subject_id: str,
    payload: M05ReconcileRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db,
            reconcile_ledger(
                db,
                client_id,
                subject_id,
                payload.expected_current_revision_id,
                bool(payload.confirm_currency_ils),
            ),
        )
    )


@router.post(
    "/subjects/{subject_id}/review-warning",
    response_model=M05RevisionResponse,
    status_code=201,
)
def review_warning(
    client_id: int,
    subject_id: str,
    payload: M05ReviewWarningRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, review_warnings(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/mark-blocked",
    response_model=M05RevisionResponse,
    status_code=201,
)
def block(
    client_id: int,
    subject_id: str,
    payload: M05ReasonRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, mark_blocked(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/adjust",
    response_model=M05RevisionResponse,
    status_code=201,
)
def adjust(
    client_id: int,
    subject_id: str,
    payload: M05AdjustmentRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, adjust_ledger(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/supersede",
    response_model=M05RevisionResponse,
    status_code=201,
)
def supersede(
    client_id: int,
    subject_id: str,
    payload: M05ReasonRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, supersede_ledger(db, client_id, subject_id, payload)
        )
    )


@router.post(
    "/subjects/{subject_id}/revalidate",
    response_model=M05RevisionResponse,
    status_code=201,
)
def revalidate(
    client_id: int,
    subject_id: str,
    payload: M05RevalidateRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db,
            revalidate_ledger(
                db, client_id, subject_id, payload.candidate_id, payload
            ),
        )
    )
