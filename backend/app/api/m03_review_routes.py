from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m03_review import M03AnnotationRequest, M03AnnotationResponse, M03ReasonRequest, M03RevisionResponse, M03TargetResponse
from app.services.m03_review_service import M03ReviewError, add_annotation, annotation_history, annotation_response, decide_review, list_candidates, review_history, start_review, target_response

router = APIRouter(prefix="/api/clients/{client_id}/m03", tags=["m03-review"])


def _run(operation):
    try:
        return operation()
    except M03ReviewError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from error


@router.get("/candidates", response_model=list[M03TargetResponse])
def candidates(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_candidates(db, client_id))


@router.get("/targets/{intake_id}", response_model=M03TargetResponse)
def target(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: target_response(db, client_id, intake_id))


@router.get("/targets/{intake_id}/history", response_model=list[M03RevisionResponse])
def history(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: review_history(db, client_id, intake_id))


@router.post("/targets/{intake_id}/start", response_model=M03RevisionResponse, status_code=201)
def start(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: start_review(db, client_id, intake_id))


def _decision(client_id: int, intake_id: str, payload: M03ReasonRequest, state: str, db: Session):
    return _run(lambda: decide_review(db, client_id, intake_id, state, payload.reason, payload.expected_current_revision_id))


@router.post("/targets/{intake_id}/accept", response_model=M03RevisionResponse, status_code=201)
def accept(client_id: int, intake_id: str, payload: M03ReasonRequest, db: Session = Depends(get_db)):
    return _decision(client_id, intake_id, payload, "accepted", db)


@router.post("/targets/{intake_id}/reject", response_model=M03RevisionResponse, status_code=201)
def reject(client_id: int, intake_id: str, payload: M03ReasonRequest, db: Session = Depends(get_db)):
    return _decision(client_id, intake_id, payload, "rejected", db)


@router.post("/targets/{intake_id}/reopen", response_model=M03RevisionResponse, status_code=201)
def reopen(client_id: int, intake_id: str, payload: M03ReasonRequest, db: Session = Depends(get_db)):
    return _decision(client_id, intake_id, payload, "reopen", db)


@router.get("/targets/{intake_id}/eligibility", response_model=M03TargetResponse)
def eligibility(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: target_response(db, client_id, intake_id))


@router.post("/targets/{intake_id}/annotations", response_model=M03AnnotationResponse, status_code=201)
def annotate(client_id: int, intake_id: str, payload: M03AnnotationRequest, db: Session = Depends(get_db)):
    return _run(lambda: annotation_response(add_annotation(db, client_id, intake_id, payload)))


@router.get("/targets/{intake_id}/annotations", response_model=list[M03AnnotationResponse])
def annotations(client_id: int, intake_id: str, db: Session = Depends(get_db)):
    return _run(lambda: annotation_history(db, client_id, intake_id))
