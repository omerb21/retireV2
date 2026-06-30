from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.client import Client
from app.models.fixation_run import FixationRun
from app.schemas.fixation_contracts import (
    FixationInputReview,
    FixationResult,
    InternalPlannerJudgmentCreateRequest,
    InternalPlannerJudgmentResponse,
    PlannerReviewContextEnvelope,
    ValidationError,
    map_contract_validation_errors,
)
from app.schemas.fixation_review import review_readiness_errors
from app.schemas.fixation_review import (
    FixationReviewConversionError,
    convert_review_to_fixation_input,
)
from app.services.fixation_service import (
    InternalPlannerJudgmentAlreadyExistsError,
    InternalPlannerJudgmentRunNotFoundError,
    calculate_fixation_payload,
    create_internal_planner_judgment,
    get_fixation_history,
    get_fixation_run_detail,
    get_latest_fixation_result,
    run_fixation,
)

router = APIRouter(prefix="/api", tags=["fixation"])


class FixationSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int
    input_data: dict[str, Any]
    planner_review_context: PlannerReviewContextEnvelope | None = None


class FixationSaveResponse(BaseModel):
    run_id: int
    status: str


class LatestResultResponse(BaseModel):
    result: dict[str, Any] | None


class FixationReviewValidationResponse(BaseModel):
    valid: bool
    errors: list[ValidationError]


def _client_not_found(client_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "CLIENT_NOT_FOUND", "message": f"Client {client_id} was not found"},
    )


def _run_not_found(run_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "FIXATION_RUN_NOT_FOUND", "message": f"Fixation run {run_id} was not found"},
    )


def _require_client(db: Session, client_id: int) -> None:
    if db.get(Client, client_id) is None:
        raise _client_not_found(client_id)


def _internal_planner_judgment_already_exists(run_id: int) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "INTERNAL_PLANNER_JUDGMENT_ALREADY_EXISTS",
            "message": f"Fixation run {run_id} already has an internal planner judgment",
        },
    )


def _serialize_internal_planner_judgment(judgment: Any) -> dict[str, Any] | None:
    if judgment is None:
        return None

    return {
        "saved_run_id": int(judgment.fixation_run_id),
        "handling_status": judgment.handling_status,
        "next_internal_action": judgment.next_internal_action,
        "internal_note": judgment.internal_note,
    }


@router.post("/fixation/review/validate", response_model=FixationReviewValidationResponse)
def validate_fixation_review(payload: dict[str, Any]) -> FixationReviewValidationResponse:
    try:
        review = FixationInputReview(**payload)
    except PydanticValidationError as exc:
        return FixationReviewValidationResponse(
            valid=False,
            errors=map_contract_validation_errors(exc),
        )

    errors = review_readiness_errors(review)
    return FixationReviewValidationResponse(valid=not errors, errors=errors)


@router.post("/fixation/review/convert", response_model=None)
def convert_fixation_review(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    try:
        review = FixationInputReview(**payload)
    except PydanticValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=[error.model_dump(mode="json") for error in map_contract_validation_errors(exc)],
        )

    readiness_errors = review_readiness_errors(review)
    if readiness_errors:
        return JSONResponse(
            status_code=422,
            content=[error.model_dump(mode="json") for error in readiness_errors],
        )

    try:
        converted = convert_review_to_fixation_input(review)
    except FixationReviewConversionError as exc:
        return JSONResponse(
            status_code=422,
            content=[
                ValidationError(
                    code="UNSUPPORTED_OR_UNAPPROVED_VALUE",
                    path="fixation_input",
                    message=str(exc),
                    severity="error",
                    source_id=None,
                ).model_dump(mode="json")
            ],
        )

    converted_payload = converted.model_dump(mode="json")
    converted_payload.pop("metadata", None)
    return converted_payload


@router.post("/fixation/validate", response_model=FixationResult)
def validate_fixation(payload: dict[str, Any]) -> FixationResult:
    return calculate_fixation_payload(payload)


@router.post("/fixation/calculate", response_model=FixationResult)
def calculate_fixation_endpoint(payload: dict[str, Any]) -> FixationResult:
    return calculate_fixation_payload(payload)


@router.post("/fixation/save", response_model=FixationSaveResponse)
def save_fixation(payload: FixationSaveRequest, db: Session = Depends(get_db)) -> FixationSaveResponse:
    _require_client(db, payload.client_id)
    run_id = run_fixation(
        client_id=payload.client_id,
        input_data=payload.input_data,
        db_session=db,
        planner_review_context=payload.planner_review_context,
    )
    run = db.get(FixationRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=500,
            detail={"code": "UNEXPECTED_ERROR", "message": "Saved run could not be loaded"},
        )

    return FixationSaveResponse(run_id=run_id, status=run.status)


@router.post(
    "/fixation/runs/{run_id}/internal-planner-judgment",
    response_model=InternalPlannerJudgmentResponse,
)
def create_fixation_run_internal_planner_judgment(
    run_id: int,
    payload: InternalPlannerJudgmentCreateRequest,
    db: Session = Depends(get_db),
) -> InternalPlannerJudgmentResponse:
    try:
        judgment = create_internal_planner_judgment(
            run_id=run_id,
            judgment_data=payload,
            db_session=db,
        )
    except InternalPlannerJudgmentRunNotFoundError:
        raise _run_not_found(run_id)
    except InternalPlannerJudgmentAlreadyExistsError:
        raise _internal_planner_judgment_already_exists(run_id)

    return InternalPlannerJudgmentResponse(**_serialize_internal_planner_judgment(judgment))


@router.get("/clients/{client_id}/fixation/latest", response_model=LatestResultResponse)
def latest_fixation_result(client_id: int, db: Session = Depends(get_db)) -> LatestResultResponse:
    _require_client(db, client_id)
    latest = get_latest_fixation_result(client_id=client_id, db_session=db)
    if latest is None or latest.fixation_result is None:
        return LatestResultResponse(result=None)
    return LatestResultResponse(result=latest.fixation_result.result_payload)


@router.get("/clients/{client_id}/fixation/history")
def fixation_history(client_id: int, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    _require_client(db, client_id)
    runs = get_fixation_history(client_id=client_id, db_session=db)
    return [
        {
            "run_id": run.id,
            "status": run.status,
            "calculation_version": run.calculation_version,
            "created_at": run.created_at.isoformat() if run.created_at is not None else None,
        }
        for run in runs
    ]


@router.get("/fixation/runs/{run_id}")
def fixation_run_detail(run_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    detail = get_fixation_run_detail(run_id=run_id, db_session=db)
    if detail is None:
        raise _run_not_found(run_id)

    return {
        "run": {
            "run_id": detail.id,
            "client_id": int(detail.client_id),
            "status": detail.status,
            "calculation_version": detail.calculation_version,
            "created_at": detail.created_at.isoformat() if detail.created_at is not None else None,
        },
        "input_snapshot": (
            detail.fixation_input_snapshot.input_payload
            if detail.fixation_input_snapshot is not None
            else None
        ),
        "planner_review_context": (
            detail.fixation_input_snapshot.planner_review_context
            if detail.fixation_input_snapshot is not None
            else None
        ),
        "internal_planner_judgment": _serialize_internal_planner_judgment(detail.internal_planner_judgment),
        "result": detail.fixation_result.result_payload if detail.fixation_result is not None else None,
        "audit_rows": [
            {
                "row_order": row.row_order,
                "category": row.category,
                "source_id": row.source_id,
                "label": row.label,
                "input_amount": float(row.input_amount) if row.input_amount is not None else None,
                "output_amount": float(row.output_amount),
                "impact_amount": float(row.impact_amount),
                "details": row.details_payload,
            }
            for row in detail.fixation_audit_rows
        ],
        "validation_errors": [
            {
                "error_order": err.error_order,
                "code": err.code,
                "path": err.path,
                "message": err.message,
                "severity": err.severity,
                "source_id": err.source_id,
            }
            for err in detail.fixation_validation_errors
        ],
    }
