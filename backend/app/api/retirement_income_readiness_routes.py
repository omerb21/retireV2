from __future__ import annotations

import re

from fastapi import APIRouter, Body, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.retirement_income_readiness import ComparisonBody, TargetConfirmationBody
from app.schemas.retirement_income_source_basis import CRTISBACommand
from app.security.transport import NO_STORE, error
from app.services import planning_input_service
from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as comparison_service
from app.services import retirement_target_date_income_source_basis_service as source_basis_service
from app.services.pension_product_service import PensionProductError
from app.services.retirement_target_date_income_source_admission_service import RetirementTargetIncomeSourceAdmissionTechnicalError

router = APIRouter(
    prefix="/api/clients/{client_id}/retirement-income-readiness",
    tags=["retirement-income-readiness"],
)
SHA = re.compile(r"^[0-9a-f]{64}$")
CONTEXT_FIELDS = {
    "client_id", "planning_calculation_input_fingerprint", "planning_input_ready",
    "retirement_target", "blocking_facts",
}
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
    if code in {
        "RIT_AMOUNT_INVALID", "RIT_AMOUNT_PRECISION_UNSUPPORTED",
        "RIT_NOMINAL_PRICE_REFERENCE_DATE_NOT_NULL", "RIT_PRICE_REFERENCE_DATE_MISSING",
    }:
        status = 422
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


def _canonical_date(value: object) -> bool:
    from datetime import date
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _context_valid(result: object, client_id: int) -> bool:
    if not isinstance(result, dict) or not CONTEXT_FIELDS <= set(result):
        return False
    target, blockers = result["retirement_target"], result["blocking_facts"]
    return (
        result["client_id"] == client_id
        and isinstance(result["planning_calculation_input_fingerprint"], str)
        and SHA.fullmatch(result["planning_calculation_input_fingerprint"]) is not None
        and isinstance(result["planning_input_ready"], bool)
        and isinstance(target, dict)
        and set(target) >= {"retirement_target_date", "retirement_target_ready"}
        and (target["retirement_target_date"] is None or _canonical_date(target["retirement_target_date"]))
        and isinstance(target["retirement_target_ready"], bool)
        and isinstance(blockers, list)
        and all(
            isinstance(item, dict)
            and set(item) == {"source_id", "code"}
            and (item["source_id"] is None or isinstance(item["source_id"], str))
            and isinstance(item["code"], str) and bool(item["code"])
            for item in blockers
        )
    )


def _target_result_valid(result: object, client_id: int) -> bool:
    return (
        isinstance(result, dict)
        and result.get("client_id") == client_id
        and comparison_service._target_schema_valid(result)
        and comparison_service._target_fingerprints_valid(result)
    )


def _comparison_result_valid(result: object, client_id: int) -> bool:
    """Fail closed through the RTICB-owned complete V2 result validator."""
    return comparison_service.public_result_valid(result, client_id)


@router.get("/context")
def context(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        result = planning_input_service.read(db, client_id)
        if not _context_valid(result, client_id):
            return error(request, 500, "PRODUCER_RESPONSE_INVALID")
        target = result["retirement_target"]
        fingerprint = result["planning_calculation_input_fingerprint"]
        blockers = result["blocking_facts"]
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
        return result if _target_result_valid(result, client_id) else error(request, 500, "PRODUCER_RESPONSE_INVALID")
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
        return result if _target_result_valid(result, client_id) else error(request, 500, "PRODUCER_RESPONSE_INVALID")
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
        identity_error = _producer_identity(request, result, client_id)
        if identity_error is not None:
            return identity_error
        valid = comparison_service.public_result_valid(
            result,
            client_id,
            command["expected_planning_calculation_input_fingerprint"],
            command["expected_retirement_target_date"],
        )
        return result if valid else error(request, 500, "PRODUCER_RESPONSE_INVALID")
    except source_basis_service.CRTISBAError as exc:
        mapping = {
            ("CRTISBA_UPSTREAM_TECHNICAL_FAILURE", 503): (503, "RTICB_UPSTREAM_TECHNICAL_FAILURE", []),
            ("PRODUCER_RESPONSE_INVALID", 500): (500, "PRODUCER_RESPONSE_INVALID", []),
            ("RESPONSE_CLIENT_MISMATCH", 500): (500, "RESPONSE_CLIENT_MISMATCH", []),
            ("CLIENT_NOT_FOUND", 404): (404, "CLIENT_NOT_FOUND", ["/path/client_id"]),
        }
        status, code, fields = mapping.get((exc.code, exc.status_code), (500, "INTERNAL_ERROR", []))
        return error(request, status, code, fields)
    except RetirementTargetIncomeSourceAdmissionTechnicalError:
        return error(request, 503, "RTICB_UPSTREAM_TECHNICAL_FAILURE")
    except source_basis_service.CRTISBAFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")
    except (OperationalError, IntegrityError, DBAPIError):
        return error(request, 503, "RTICB_DATABASE_FAILURE")
    except PensionProductError as exc:
        return _transport(request, exc)
    except comparison_service.RTICBFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")
    except Exception:
        return error(request, 500, "INTERNAL_ERROR")


@router.get("/source-bases")
def source_bases(request: Request, client_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        return JSONResponse(content=source_basis_service.read(db, client_id), headers=NO_STORE)
    except source_basis_service.CRTISBAError as exc:
        return error(request, exc.status_code, exc.code, exc.field_paths)
    except source_basis_service.CRTISBAFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")


@router.put("/source-bases/{source_id}")
def put_source_basis(
    request: Request,
    payload: CRTISBACommand = Body(...),
    client_id: int = Path(gt=0),
    source_id: str = Path(min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    try:
        actor = getattr(request.state, "trusted_professional_actor", None)
        if actor is None and not request.app.state.auth_config.production:
            actor = "development-professional"
        return JSONResponse(content=source_basis_service.write(db, client_id, source_id, payload, actor), headers=NO_STORE)
    except source_basis_service.CRTISBAError as exc:
        return error(request, exc.status_code, exc.code, exc.field_paths)
    except source_basis_service.CRTISBAFingerprintConstructionError:
        return error(request, 500, "INTERNAL_ERROR")
