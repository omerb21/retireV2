from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.retirement_income_readiness import ComparisonBody, TargetConfirmationBody
from app.security.transport import error
from app.services import planning_input_service
from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as comparison_service
from app.services.pension_product_service import PensionProductError
from app.services.retirement_target_date_income_source_admission_service import RetirementTargetIncomeSourceAdmissionTechnicalError

router = APIRouter(
    prefix="/api/clients/{client_id}/retirement-income-readiness",
    tags=["retirement-income-readiness"],
)
SHA = re.compile(r"^[0-9a-f]{64}$")


def _transport(request: Request, exc: PensionProductError, *, target_operation: str | None = None):
    code, status, fields = exc.code, exc.status_code, []
    if code in {"CLIENT_NOT_FOUND", "RIT_CLIENT_ID_INVALID"}:
        return error(request, 404, "CLIENT_NOT_FOUND", ["/path/client_id"])
    target_fields = {
        "RIT_AMOUNT_INVALID": ["/monthly_amount"],
        "RIT_AMOUNT_PRECISION_UNSUPPORTED": ["/monthly_amount"],
        "RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL": ["/price_reference_date"],
        "RIT_PRICE_REFERENCE_DATE_MISSING": ["/price_reference_date"],
        "RIT_CONFIRMATION_CONTEXT_STALE": ["/expected_planning_calculation_input_fingerprint", "/expected_retirement_target_date"],
        "RIT_RECORD_VERSION_CONFLICT": ["/expected_record_version"],
    }
    fields = target_fields.get(code, [])
    if code == "RIT_RECORD_UNAVAILABLE":
        code = "RIT_UNSUPPORTED_DATABASE" if status == 503 else code
    return error(request, status, code, fields)


def _producer_identity(request: Request, result: object, client_id: int):
    if not isinstance(result, dict):
        return error(request, 500, "PRODUCER_RESPONSE_INVALID")
    returned = result.get("client_id")
    if returned is not None and returned != client_id:
        return error(request, 500, "RESPONSE_CLIENT_MISMATCH")
    return None


@router.get("/context")
def context(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        result = planning_input_service.read(db, client_id)
        target = result.get("retirement_target")
        fingerprint = result.get("planning_calculation_input_fingerprint")
        blockers = result.get("blocking_facts")
        if (
            result.get("client_id") != client_id
            or not isinstance(fingerprint, str)
            or not SHA.fullmatch(fingerprint)
            or not isinstance(target, dict)
            or not isinstance(blockers, list)
            or not all(isinstance(item, dict) and set(item) == {"source_id", "code"} for item in blockers)
        ):
            return error(request, 500, "PRODUCER_RESPONSE_INVALID")
        return {
            "schema_version": "RTDIR_PLANNING_CONTEXT_V1",
            "client_id": client_id,
            "planning_calculation_input_fingerprint": fingerprint,
            "planning_input_ready": result.get("planning_input_ready") is True,
            "retirement_target_date": target.get("retirement_target_date"),
            "retirement_target_ready": target.get("retirement_target_ready") is True,
            "blocking_facts": blockers,
        }
    except PensionProductError as exc:
        return _transport(request, exc)
    except (OperationalError, IntegrityError, DBAPIError):
        return error(request, 503, "CONTEXT_DATABASE_FAILURE")
    finally:
        db.rollback()


@router.get("/target")
def target(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        result = target_service.assess(db, client_id)
        return _producer_identity(request, result, client_id) or result
    except PensionProductError as exc:
        return _transport(request, exc, target_operation="assess")
    except (OperationalError, IntegrityError, DBAPIError) as exc:
        code = "RIT_ASSESS_DATABASE_RETRY_EXHAUSTED" if target_service._retryable(exc) else "RIT_ASSESS_DATABASE_FAILURE"
        return error(request, 503, code)
    except target_service.TargetResultFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")


@router.put("/target")
def confirm_target(request: Request, payload: TargetConfirmationBody, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    command = {"client_id": client_id, **payload.model_dump()}
    try:
        actor = getattr(request.state, "trusted_professional_actor", None)
        if actor is None and not request.app.state.auth_config.production:
            actor = "development-professional"
        result = target_service.confirm(db, command, actor)
        return _producer_identity(request, result, client_id) or result
    except PensionProductError as exc:
        return _transport(request, exc, target_operation="confirm")
    except (OperationalError, IntegrityError, DBAPIError) as exc:
        code = "RIT_CONFIRM_DATABASE_RETRY_EXHAUSTED" if target_service._retryable(exc) else "RIT_CONFIRM_DATABASE_FAILURE"
        return error(request, 503, code)
    except target_service.TargetResultFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")


@router.post("/comparison")
def comparison(request: Request, payload: ComparisonBody, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    command = {"client_id": client_id, **payload.model_dump()}
    try:
        result = comparison_service.assess(db, command)
        return _producer_identity(request, result, client_id) or result
    except RetirementTargetIncomeSourceAdmissionTechnicalError:
        return error(request, 503, "RTICB_UPSTREAM_TECHNICAL_FAILURE")
    except (OperationalError, IntegrityError, DBAPIError):
        return error(request, 503, "RTICB_DATABASE_FAILURE")
    except PensionProductError as exc:
        return _transport(request, exc)
    except comparison_service.RTICBFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")
