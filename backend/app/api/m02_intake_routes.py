from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.m02_intake import M02IntakeRecord
from app.schemas.m02_intake import (
    M02IntakeResponse,
    M02IntakeUpdateRequest,
    M02LifecycleRequest,
    M02ManualIntakeRequest,
    M02UploadBatchResponse,
    M02UploadFileResult,
)
from app.services.m02_intake_service import (
    create_manual_intake,
    preserve_staged_upload,
    record_preservation_failure,
    require_client,
    require_mutable_client,
    require_intake,
    require_source,
    to_response,
    transition_intake,
    update_intake,
)
from app.services.m02_storage import (
    M02FileError,
    M02StorageCleanupError,
    M02StorageConfigurationError,
    ManagedLocalStorage,
    safe_original_filename,
    stage_and_validate_upload,
)


router = APIRouter(prefix="/api/clients/{client_id}/m02", tags=["m02-intake"])


def _storage() -> ManagedLocalStorage:
    try:
        return ManagedLocalStorage.from_environment()
    except M02StorageConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "M02_STORAGE_UNAVAILABLE",
                "message": "Managed source storage is unavailable",
            },
        ) from error


@router.post("/intakes/manual", response_model=M02IntakeResponse, status_code=201)
def post_manual_intake(
    client_id: int,
    payload: M02ManualIntakeRequest,
    db: Session = Depends(get_db),
) -> M02IntakeResponse:
    return to_response(db, create_manual_intake(db, client_id, payload))


@router.get("/intakes", response_model=list[M02IntakeResponse])
def list_intakes(
    client_id: int, db: Session = Depends(get_db)
) -> list[M02IntakeResponse]:
    require_client(db, client_id)
    rows = db.scalars(
        select(M02IntakeRecord)
        .where(M02IntakeRecord.client_id == client_id)
        .order_by(M02IntakeRecord.created_at.desc(), M02IntakeRecord.intake_id.desc())
    ).all()
    return [to_response(db, row) for row in rows]


@router.get("/intakes/{intake_id}", response_model=M02IntakeResponse)
def get_intake(
    client_id: int, intake_id: str, db: Session = Depends(get_db)
) -> M02IntakeResponse:
    require_client(db, client_id)
    return to_response(db, require_intake(db, client_id, intake_id))


@router.put("/intakes/{intake_id}", response_model=M02IntakeResponse)
def put_intake(
    client_id: int,
    intake_id: str,
    payload: M02IntakeUpdateRequest,
    db: Session = Depends(get_db),
) -> M02IntakeResponse:
    return to_response(db, update_intake(db, client_id, intake_id, payload))


@router.post("/intakes/{intake_id}/lifecycle", response_model=M02IntakeResponse)
def post_intake_lifecycle(
    client_id: int,
    intake_id: str,
    payload: M02LifecycleRequest,
    db: Session = Depends(get_db),
) -> M02IntakeResponse:
    row = transition_intake(
        db,
        client_id,
        intake_id,
        payload.target_status,
        payload.rejection_reason_code,
        payload.notes,
    )
    return to_response(db, row)


@router.post("/intakes/upload", response_model=M02UploadBatchResponse)
async def post_upload_intakes(
    client_id: int,
    files: list[UploadFile] = File(...),
    source_type: str = Form(...),
    declared_provider_name: str | None = Form(default=None),
    product_name: str | None = Form(default=None),
    product_identifier: str | None = Form(default=None),
    declared_account_reference: str | None = Form(default=None),
    declared_statement_date: date | None = Form(default=None),
    declared_start_date: date | None = Form(default=None),
    declared_product_type: str | None = Form(default=None),
    declared_basis: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> M02UploadBatchResponse:
    require_mutable_client(db, client_id)
    if not files:
        raise HTTPException(
            status_code=422,
            detail={"code": "M02_FILES_REQUIRED", "message": "At least one file is required"},
        )
    storage = _storage()
    results: list[M02UploadFileResult] = []
    request_error: dict[str, str] | None = None
    for index, upload in enumerate(files):
        display_filename = "unnamed-source"
        staged = None
        try:
            display_filename = safe_original_filename(upload.filename)
            staged = await stage_and_validate_upload(storage, upload)
            row = preserve_staged_upload(
                db,
                storage,
                client_id,
                staged,
                source_type=source_type,
                declared_provider_name=declared_provider_name,
                product_name=product_name,
                product_identifier=product_identifier,
                declared_account_reference=declared_account_reference,
                declared_statement_date=declared_statement_date,
                declared_start_date=declared_start_date,
                declared_product_type=declared_product_type,
                declared_basis=declared_basis,
                notes=notes,
            )
            storage.cleanup_temporary(staged.temporary_path)
            staged = None
            results.append(
                M02UploadFileResult(
                    selection_index=index,
                    original_filename=display_filename,
                    status="preserved",
                    intake=to_response(db, row),
                )
            )
        except M02FileError as error:
            if staged is not None:
                try:
                    storage.cleanup_temporary(staged.temporary_path)
                except M02StorageCleanupError:
                    request_error = {
                        "code": "M02_BATCH_CLEANUP_FAILED",
                        "message": "The upload request cleanup could not be completed",
                    }
                    break
            failed_intake = None
            if error.code == "M02_PRESERVATION_FAILED":
                failed_intake = to_response(
                    db,
                    record_preservation_failure(
                        db,
                        client_id,
                        source_type=source_type,
                        failure_code=error.code,
                        declared_provider_name=declared_provider_name,
                        product_name=product_name,
                        product_identifier=product_identifier,
                        declared_account_reference=declared_account_reference,
                        declared_statement_date=declared_statement_date,
                    ),
                )
            results.append(
                M02UploadFileResult(
                    selection_index=index,
                    original_filename=display_filename,
                    status="failed",
                    intake=failed_intake,
                    error_code=error.code,
                    error_message=error.message,
                )
            )
        except Exception:
            db.rollback()
            if staged is not None:
                try:
                    storage.cleanup_temporary(staged.temporary_path)
                except M02StorageCleanupError:
                    request_error = {
                        "code": "M02_BATCH_CLEANUP_FAILED",
                        "message": "The upload request cleanup could not be completed",
                    }
                    break
            request_error = {
                "code": "M02_BATCH_REQUEST_FAILED",
                "message": "The upload request could not be completed",
            }
            break
    if request_error is not None and not results:
        raise HTTPException(status_code=400, detail=request_error)
    return M02UploadBatchResponse(results=results, request_error=request_error)


@router.get("/sources/{source_id}/download")
def download_source(
    client_id: int,
    source_id: str,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_client(db, client_id)
    source = require_source(db, client_id, source_id)
    if source.blob.client_id != client_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "M02_RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )
    storage = _storage()
    try:
        opened = storage.open_key(source.blob.storage_key)
    except (OSError, M02StorageConfigurationError):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "M02_PRESERVED_SOURCE_UNAVAILABLE",
                "message": "The preserved source is unavailable",
            },
        )
    def stream_opened_file():
        try:
            while chunk := opened.read(1024 * 1024):
                yield chunk
        finally:
            opened.close()

    encoded_filename = quote(source.sanitized_download_filename, safe="")
    return StreamingResponse(
        stream_opened_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                "attachment; filename=\"m02-source\"; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
