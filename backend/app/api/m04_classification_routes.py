from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m04_classification import (
    M04EligibilityResponse,
    M04ExpectedRevisionRequest,
    M04OverrideRequest,
    M04ReasonRequest,
    M04RevisionResponse,
    M04RulePreviewResponse,
    M04StartRequest,
    M04TargetResponse,
    M04UndoRequest,
)
from app.services.m04_classification_service import (
    M04ClassificationError,
    create_proposal,
    decide_proposal,
    eligibility,
    list_targets,
    mark_unresolved,
    matched_rule_evidence,
    override_classification,
    preview_rules,
    reopen_classification,
    revision_history,
    revision_response,
    start_classification,
    start_revalidation,
    target_response,
    undo_classification,
)


router = APIRouter(
    prefix="/api/clients/{client_id}/m04",
    tags=["m04-classification"],
)


def _run(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except M04ClassificationError as error:
        raise HTTPException(
            error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error


@router.get("/targets", response_model=list[M04TargetResponse])
def targets(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_targets(db, client_id))


@router.get("/targets/{intake_id}", response_model=M04TargetResponse)
def target(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: target_response(db, client_id, intake_id))


@router.get(
    "/targets/{intake_id}/history",
    response_model=list[M04RevisionResponse],
)
def history(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: revision_history(db, client_id, intake_id))


@router.get(
    "/targets/{intake_id}/preview",
    response_model=M04RulePreviewResponse,
)
def preview(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: preview_rules(db, client_id, intake_id))


@router.get(
    "/targets/{intake_id}/matched-rules",
    response_model=list[dict[str, Any]],
)
def rules(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: matched_rule_evidence(db, client_id, intake_id))


@router.get(
    "/targets/{intake_id}/eligibility",
    response_model=M04EligibilityResponse,
)
def m05_eligibility(
    client_id: int, intake_id: str, db: Session = Depends(get_db)
):
    return _run(lambda: eligibility(db, client_id, intake_id))


@router.post(
    "/targets/{intake_id}/start",
    response_model=M04RevisionResponse,
    status_code=201,
)
def start(
    client_id: int,
    intake_id: str,
    payload: M04StartRequest | None = None,
    db: Session = Depends(get_db),
):
    _ = payload
    return _run(
        lambda: revision_response(
            db, start_classification(db, client_id, intake_id)
        )
    )


@router.post(
    "/targets/{intake_id}/proposal",
    response_model=M04RevisionResponse,
    status_code=201,
)
def proposal(
    client_id: int,
    intake_id: str,
    payload: M04ExpectedRevisionRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db,
            create_proposal(
                db, client_id, intake_id, payload.expected_current_revision_id
            ),
        )
    )


@router.post(
    "/targets/{intake_id}/unresolved",
    response_model=M04RevisionResponse,
    status_code=201,
)
def unresolved(
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, mark_unresolved(db, client_id, intake_id, payload)
        )
    )


def _decision(
    db: Session,
    client_id: int,
    intake_id: str,
    action: str,
    payload: M04ReasonRequest,
) -> M04RevisionResponse:
    return _run(
        lambda: revision_response(
            db,
            decide_proposal(db, client_id, intake_id, action, payload),
        )
    )


@router.post(
    "/targets/{intake_id}/accept",
    response_model=M04RevisionResponse,
    status_code=201,
)
def accept(
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
    db: Session = Depends(get_db),
):
    return _decision(db, client_id, intake_id, "accept", payload)


@router.post(
    "/targets/{intake_id}/reject",
    response_model=M04RevisionResponse,
    status_code=201,
)
def reject(
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
    db: Session = Depends(get_db),
):
    return _decision(db, client_id, intake_id, "reject", payload)


@router.post(
    "/targets/{intake_id}/reopen",
    response_model=M04RevisionResponse,
    status_code=201,
)
def reopen(
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, reopen_classification(db, client_id, intake_id, payload)
        )
    )


@router.post(
    "/targets/{intake_id}/override",
    response_model=M04RevisionResponse,
    status_code=201,
)
def override(
    client_id: int,
    intake_id: str,
    payload: M04OverrideRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, override_classification(db, client_id, intake_id, payload)
        )
    )


@router.post(
    "/targets/{intake_id}/undo",
    response_model=M04RevisionResponse,
    status_code=201,
)
def undo(
    client_id: int,
    intake_id: str,
    payload: M04UndoRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, undo_classification(db, client_id, intake_id, payload)
        )
    )


@router.post(
    "/targets/{intake_id}/start-revalidation",
    response_model=M04RevisionResponse,
    status_code=201,
)
def revalidate(
    client_id: int,
    intake_id: str,
    payload: M04ReasonRequest,
    db: Session = Depends(get_db),
):
    return _run(
        lambda: revision_response(
            db, start_revalidation(db, client_id, intake_id, payload)
        )
    )
