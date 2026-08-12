from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.m09_cashflow import (
    M09ContractRequest,
    M09CurrentnessResponse,
    M09InventoryResponse,
    M09M10EligibilityResponse,
    M09RunResponse,
    M09RunSummaryResponse,
)
from app.schemas.m09_scenario_subject import (
    CreateAdjustedSubjectRequest,
    ScenarioSubjectResponse,
    SubjectCurrentnessResponse,
    SubjectExecutionRequest,
    SubjectM10EligibilityResponse,
    SubjectRunResponse,
    SubjectRunSummaryResponse,
)
from app.services.m01_case_service import M01CaseError
from app.services.m09_cashflow_service import (
    M09CashflowError,
    assess_inventory,
    currentness,
    execute_run,
    get_inventory,
    list_runs,
    m10_eligibility,
    run_response,
)
from app.services.m09_scenario_subject_service import (
    create_adjusted_subject,
    execute_subject_run,
    get_subject,
    list_subject_runs,
    list_subjects,
    resolve_baseline,
    subject_currentness,
    subject_eligibility,
    subject_run_response,
)


router = APIRouter(prefix="/api/clients/{client_id}/m09", tags=["m09-cashflow"])


def _run(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except M09CashflowError as error:
        raise HTTPException(
            error.status_code, detail={"code": error.code, "message": error.message}
        ) from error
    except M01CaseError as error:
        raise HTTPException(
            error.status_code, detail={"code": error.code, "message": error.message}
        ) from error


@router.post("/inventories", response_model=M09InventoryResponse, status_code=201)
def create_inventory(
    client_id: int,
    payload: M09ContractRequest,
    db: Session = Depends(get_db),
):
    return _run(lambda: assess_inventory(db, client_id, payload))


@router.get("/inventories/{inventory_id}", response_model=M09InventoryResponse)
def inventory(
    client_id: int, inventory_id: str, db: Session = Depends(get_db)
):
    return _run(lambda: get_inventory(db, client_id, inventory_id))


@router.post("/runs", response_model=M09RunResponse, status_code=201)
def execute(
    client_id: int,
    payload: M09ContractRequest,
    db: Session = Depends(get_db),
):
    return _run(lambda: execute_run(db, client_id, payload))


@router.get("/runs", response_model=list[M09RunSummaryResponse])
def history(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_runs(db, client_id))


@router.get("/runs/{run_id}", response_model=M09RunResponse)
def result(client_id: int, run_id: str, db: Session = Depends(get_db)):
    return _run(lambda: run_response(db, client_id, run_id))


@router.get(
    "/runs/{run_id}/currentness", response_model=M09CurrentnessResponse
)
def run_currentness(
    client_id: int, run_id: str, db: Session = Depends(get_db)
):
    return _run(lambda: currentness(db, client_id, run_id))


@router.get(
    "/runs/{run_id}/m10-eligibility", response_model=M09M10EligibilityResponse
)
def run_m10_eligibility(
    client_id: int, run_id: str, db: Session = Depends(get_db)
):
    return _run(lambda: m10_eligibility(db, client_id, run_id))


@router.post("/subjects/baseline", response_model=ScenarioSubjectResponse)
def baseline_subject(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: resolve_baseline(db, client_id))


@router.post("/subjects", response_model=ScenarioSubjectResponse, status_code=201)
def create_subject(client_id: int, payload: CreateAdjustedSubjectRequest, db: Session = Depends(get_db)):
    return _run(lambda: create_adjusted_subject(db, client_id, payload))


@router.get("/subjects", response_model=list[ScenarioSubjectResponse])
def subjects(client_id: int, db: Session = Depends(get_db)):
    return _run(lambda: list_subjects(db, client_id))


@router.get("/subjects/{subject_id}", response_model=ScenarioSubjectResponse)
def subject(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: get_subject(db, client_id, subject_id))


@router.post("/subjects/{subject_id}/runs", response_model=SubjectRunResponse, status_code=201)
def execute_subject(client_id: int, subject_id: str, payload: SubjectExecutionRequest, db: Session = Depends(get_db)):
    return _run(lambda: execute_subject_run(db, client_id, subject_id, payload))


@router.get("/subjects/{subject_id}/runs", response_model=list[SubjectRunSummaryResponse])
def subject_runs(client_id: int, subject_id: str, db: Session = Depends(get_db)):
    return _run(lambda: list_subject_runs(db, client_id, subject_id))


@router.get("/subjects/{subject_id}/runs/{run_id}", response_model=SubjectRunResponse)
def subject_run(client_id: int, subject_id: str, run_id: str, db: Session = Depends(get_db)):
    return _run(lambda: subject_run_response(db, client_id, subject_id, run_id))


@router.get("/subjects/{subject_id}/runs/{run_id}/currentness", response_model=SubjectCurrentnessResponse)
def subject_run_currentness(client_id: int, subject_id: str, run_id: str, db: Session = Depends(get_db)):
    return _run(lambda: subject_currentness(db, client_id, subject_id, run_id))


@router.get("/subjects/{subject_id}/runs/{run_id}/m10-eligibility", response_model=SubjectM10EligibilityResponse)
def subject_run_eligibility(client_id: int, subject_id: str, run_id: str, db: Session = Depends(get_db)):
    return _run(lambda: subject_eligibility(db, client_id, subject_id, run_id))
