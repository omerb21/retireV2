from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.m02_intake import (
    M02IntakeRecord,
    M02PreservedBlob,
    M02PreservedSource,
)
from app.schemas.m02_intake import (
    M02IntakeResponse,
    M02IntakeUpdateRequest,
    M02ManualIntakeRequest,
    M02SourceResponse,
)
from app.services.m02_storage import ManagedLocalStorage, M02FileError, StagedUpload


M02_ACTOR = "system:m02-intake:M02 intake workflow"
ALLOWED_TRANSITIONS = {
    "uploaded": {"metadata_review", "rejected"},
    "metadata_review": {"accepted_for_review", "rejected"},
    "accepted_for_review": {"metadata_review", "rejected", "superseded"},
    "rejected": set(),
    "superseded": set(),
}
EDITABLE_STATUSES = {"uploaded", "metadata_review"}
METADATA_FIELDS = {
    "declared_provider_name",
    "product_name",
    "product_identifier",
    "declared_account_reference",
    "declared_total_balance_amount",
    "declared_monthly_pension_amount",
    "declared_component_values",
    "declared_statement_date",
    "declared_start_date",
    "declared_product_type",
    "source_type",
    "declared_basis",
    "notes",
}


def require_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "M02_RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )
    return client


def require_intake(db: Session, client_id: int, intake_id: str) -> M02IntakeRecord:
    row = db.scalar(
        select(M02IntakeRecord).where(
            M02IntakeRecord.client_id == client_id,
            M02IntakeRecord.intake_id == intake_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "M02_RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )
    return row


def require_source(db: Session, client_id: int, source_id: str) -> M02PreservedSource:
    row = db.scalar(
        select(M02PreservedSource).where(
            M02PreservedSource.client_id == client_id,
            M02PreservedSource.source_id == source_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "M02_RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )
    return row


def create_manual_intake(
    db: Session, client_id: int, payload: M02ManualIntakeRequest
) -> M02IntakeRecord:
    require_client(db, client_id)
    values = _normalized_payload(payload.model_dump())
    row = M02IntakeRecord(
        intake_id=f"M02I-{uuid4().hex}",
        client_id=client_id,
        manual_technical_reference=f"M02-MANUAL-{uuid4().hex}",
        lifecycle_status="metadata_review",
        preservation_status="not_applicable",
        duplicate_candidate=False,
        superseding_candidate=False,
        created_by_actor=M02_ACTOR,
        updated_by_actor=M02_ACTOR,
        **values,
    )
    _apply_superseding_candidate(db, row)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_intake(
    db: Session,
    client_id: int,
    intake_id: str,
    payload: M02IntakeUpdateRequest,
) -> M02IntakeRecord:
    require_client(db, client_id)
    row = require_intake(db, client_id, intake_id)
    if row.lifecycle_status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "M02_TERMINAL_OR_LOCKED_RECORD",
                "message": "The intake must be in an editable lifecycle state",
            },
        )
    values = _normalized_payload(
        {field: getattr(payload, field) for field in payload.model_fields_set}
    )
    for field, value in values.items():
        if field in METADATA_FIELDS:
            setattr(row, field, value)
    row.updated_by_actor = M02_ACTOR
    row.superseding_candidate = False
    row.superseding_intake_id = None
    _apply_superseding_candidate(db, row)
    db.commit()
    db.refresh(row)
    return row


def transition_intake(
    db: Session,
    client_id: int,
    intake_id: str,
    target_status: str,
    rejection_reason_code: str | None,
) -> M02IntakeRecord:
    require_client(db, client_id)
    row = require_intake(db, client_id, intake_id)
    if target_status not in ALLOWED_TRANSITIONS.get(row.lifecycle_status, set()):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "M02_INVALID_LIFECYCLE_TRANSITION",
                "message": "The lifecycle transition is not allowed",
            },
        )
    if target_status == "rejected":
        reason = (rejection_reason_code or "").strip()
        if not reason or not re.fullmatch(r"[A-Z0-9_]{2,64}", reason):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "M02_REJECTION_REASON_REQUIRED",
                    "message": "A stable rejection reason code is required",
                },
            )
    if target_status in {"metadata_review", "accepted_for_review"}:
        blocking = _blocking_diagnostics(row, target_status)
        if blocking:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "M02_METADATA_INCOMPLETE",
                    "message": "Required M02 metadata is incomplete",
                    "diagnostics": blocking,
                },
            )
    if target_status == "superseded" and not _has_newer_candidate(db, row):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "M02_INVALID_SUPERSEDING_TARGET",
                "message": "No valid same-client newer intake exists",
            },
        )
    row.lifecycle_status = target_status
    row.updated_by_actor = M02_ACTOR
    db.commit()
    db.refresh(row)
    return row


def preserve_staged_upload(
    db: Session,
    storage: ManagedLocalStorage,
    client_id: int,
    staged: StagedUpload,
    *,
    source_type: str,
    declared_provider_name: str | None,
    product_name: str | None,
    product_identifier: str | None,
    declared_account_reference: str | None,
    declared_statement_date: date | None,
    declared_start_date: date | None,
    declared_product_type: str | None,
    declared_basis: str | None,
    notes: str | None,
) -> M02IntakeRecord:
    require_client(db, client_id)
    source_type = _required_text(source_type, "source_type")
    prior = db.execute(
        select(M02PreservedBlob, M02PreservedSource)
        .join(
            M02PreservedSource,
            M02PreservedSource.blob_id == M02PreservedBlob.blob_id,
        )
        .where(
            M02PreservedBlob.client_id == client_id,
            M02PreservedBlob.sha256_checksum == staged.sha256_checksum,
            M02PreservedSource.client_id == client_id,
        )
        .order_by(M02PreservedSource.uploaded_at, M02PreservedSource.source_id)
    ).first()
    duplicate_blob = prior[0] if prior else None
    duplicate_source = prior[1] if prior else None
    final_storage_key: str | None = None
    try:
        if duplicate_blob is None:
            final_storage_key = storage.place(staged.temporary_path)
            blob = M02PreservedBlob(
                blob_id=f"M02B-{uuid4().hex}",
                client_id=client_id,
                storage_key=final_storage_key,
                sha256_checksum=staged.sha256_checksum,
                byte_size=staged.byte_size,
                validated_media_type=staged.validated_media_type,
            )
            db.add(blob)
        else:
            blob = duplicate_blob

        row = M02IntakeRecord(
            intake_id=f"M02I-{uuid4().hex}",
            client_id=client_id,
            declared_provider_name=_optional_text(declared_provider_name),
            product_name=_optional_text(product_name),
            product_identifier=_optional_text(product_identifier),
            declared_account_reference=_optional_text(declared_account_reference),
            manual_technical_reference=None,
            declared_statement_date=declared_statement_date,
            declared_start_date=declared_start_date,
            declared_product_type=_optional_text(declared_product_type),
            source_type=source_type,
            declared_basis=_optional_text(declared_basis),
            notes=_optional_text(notes),
            lifecycle_status="uploaded",
            preservation_status="preserved",
            duplicate_candidate=duplicate_blob is not None,
            duplicate_of_intake_id=duplicate_source.intake_id if duplicate_source else None,
            superseding_candidate=False,
            created_by_actor=M02_ACTOR,
            updated_by_actor=M02_ACTOR,
        )
        _apply_superseding_candidate(db, row)
        source = M02PreservedSource(
            source_id=f"M02S-{uuid4().hex}",
            client_id=client_id,
            intake_id=row.intake_id,
            blob_id=blob.blob_id,
            original_filename=staged.original_filename,
            normalized_extension=staged.extension,
            declared_mime_type=staged.declared_mime_type,
            validated_media_type=staged.validated_media_type,
            detected_text_encoding=staged.detected_text_encoding,
        )
        db.add_all([row, source])
        db.commit()
        db.refresh(row)
        return row
    except SQLAlchemyError as error:
        db.rollback()
        if final_storage_key is not None:
            storage.delete_key(final_storage_key)
        raise M02FileError(
            "M02_PERSISTENCE_FAILED", "The source metadata could not be persisted"
        ) from error
    except BaseException:
        db.rollback()
        if final_storage_key is not None:
            storage.delete_key(final_storage_key)
        raise
    finally:
        storage.cleanup_temporary(staged.temporary_path)


def record_preservation_failure(
    db: Session,
    client_id: int,
    *,
    source_type: str,
    failure_code: str,
    declared_provider_name: str | None = None,
    product_name: str | None = None,
    product_identifier: str | None = None,
    declared_account_reference: str | None = None,
    declared_statement_date: date | None = None,
) -> M02IntakeRecord:
    row = M02IntakeRecord(
        intake_id=f"M02I-{uuid4().hex}",
        client_id=client_id,
        source_type=_required_text(source_type, "source_type"),
        declared_provider_name=_optional_text(declared_provider_name),
        product_name=_optional_text(product_name),
        product_identifier=_optional_text(product_identifier),
        declared_account_reference=_optional_text(declared_account_reference),
        declared_statement_date=declared_statement_date,
        manual_technical_reference=None,
        lifecycle_status="metadata_review",
        preservation_status="failed",
        preservation_failure_code=failure_code,
        duplicate_candidate=False,
        superseding_candidate=False,
        created_by_actor=M02_ACTOR,
        updated_by_actor=M02_ACTOR,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_response(db: Session, row: M02IntakeRecord) -> M02IntakeResponse:
    source = row.preserved_source
    source_response = None
    if source is not None:
        blob = source.blob
        source_response = M02SourceResponse(
            source_id=source.source_id,
            original_filename=source.original_filename,
            normalized_extension=source.normalized_extension,
            declared_mime_type=source.declared_mime_type,
            validated_media_type=source.validated_media_type,
            detected_text_encoding=source.detected_text_encoding,
            sha256_checksum=blob.sha256_checksum,
            byte_size=blob.byte_size,
            uploaded_at=source.uploaded_at,
        )
    return M02IntakeResponse(
        intake_id=row.intake_id,
        client_id=row.client_id,
        declared_provider_name=row.declared_provider_name,
        product_name=row.product_name,
        product_identifier=row.product_identifier,
        declared_account_reference=row.declared_account_reference,
        manual_technical_reference=row.manual_technical_reference,
        declared_total_balance_amount=row.declared_total_balance_amount,
        declared_monthly_pension_amount=row.declared_monthly_pension_amount,
        declared_component_values=row.declared_component_values,
        declared_statement_date=row.declared_statement_date,
        declared_start_date=row.declared_start_date,
        declared_product_type=row.declared_product_type,
        source_type=row.source_type,
        declared_basis=row.declared_basis,
        notes=row.notes,
        lifecycle_status=row.lifecycle_status,
        preservation_status=row.preservation_status,
        preservation_failure_code=row.preservation_failure_code,
        duplicate_candidate=row.duplicate_candidate,
        duplicate_of_intake_id=row.duplicate_of_intake_id,
        superseding_candidate=row.superseding_candidate,
        superseding_intake_id=row.superseding_intake_id,
        allowed_lifecycle_targets=_allowed_targets(db, row),
        diagnostics=_diagnostics(row),
        source=source_response,
        created_by_actor=row.created_by_actor,
        updated_by_actor=row.updated_by_actor,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _normalized_payload(values: dict) -> dict:
    normalized: dict = {}
    for field, value in values.items():
        if field in {
            "declared_provider_name",
            "product_name",
            "product_identifier",
            "declared_account_reference",
            "declared_product_type",
            "declared_basis",
            "notes",
        }:
            normalized[field] = _optional_text(value)
        elif field == "source_type":
            normalized[field] = _required_text(value, field)
        elif field == "declared_component_values" and value is not None:
            components = []
            for component in value:
                item = component.model_dump() if hasattr(component, "model_dump") else component
                label = _required_text(item["label"], "component label")
                raw_value = item["value"].strip()
                try:
                    Decimal(raw_value)
                except InvalidOperation as error:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "M02_INVALID_DECLARED_DECIMAL",
                            "message": "Declared component values must be exact decimals",
                        },
                    ) from error
                components.append({"label": label, "value": raw_value})
            normalized[field] = components
        else:
            normalized[field] = value
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _required_text(value: str | None, field: str) -> str:
    trimmed = _optional_text(value)
    if trimmed is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "M02_REQUIRED_METADATA",
                "message": f"{field} is required",
            },
        )
    return trimmed


def _is_manual(row: M02IntakeRecord) -> bool:
    return row.manual_technical_reference is not None


def _diagnostics(row: M02IntakeRecord) -> list[str]:
    diagnostics: list[str] = []
    if not row.declared_provider_name:
        diagnostics.append("M02_PROVIDER_MISSING")
    if not row.declared_account_reference:
        diagnostics.append("M02_DECLARED_ACCOUNT_MISSING")
    if not (row.product_name or row.product_identifier or row.declared_product_type):
        diagnostics.append("M02_PRODUCT_IDENTITY_MISSING")
    if row.preservation_status == "failed":
        diagnostics.append("M02_PRESERVATION_UNRESOLVED")
    return diagnostics


def _blocking_diagnostics(row: M02IntakeRecord, target: str) -> list[str]:
    diagnostics = _diagnostics(row)
    if target == "metadata_review" and not _is_manual(row):
        return [
            code
            for code in diagnostics
            if code
            in {
                "M02_PROVIDER_MISSING",
                "M02_DECLARED_ACCOUNT_MISSING",
                "M02_PRODUCT_IDENTITY_MISSING",
                "M02_PRESERVATION_UNRESOLVED",
            }
        ]
    if target == "accepted_for_review":
        if _is_manual(row):
            return [
                code
                for code in diagnostics
                if code in {"M02_PRODUCT_IDENTITY_MISSING", "M02_PRESERVATION_UNRESOLVED"}
            ]
        return diagnostics
    return []


def _allowed_targets(db: Session, row: M02IntakeRecord) -> list[str]:
    targets = set(ALLOWED_TRANSITIONS.get(row.lifecycle_status, set()))
    if "metadata_review" in targets and _blocking_diagnostics(row, "metadata_review"):
        targets.remove("metadata_review")
    if "accepted_for_review" in targets and _blocking_diagnostics(
        row, "accepted_for_review"
    ):
        targets.remove("accepted_for_review")
    if "superseded" in targets and not _has_newer_candidate(db, row):
        targets.remove("superseded")
    return sorted(targets)


def _apply_superseding_candidate(db: Session, row: M02IntakeRecord) -> None:
    if row.declared_statement_date is None:
        return
    older = db.scalar(
        select(M02IntakeRecord)
        .where(
            M02IntakeRecord.client_id == row.client_id,
            M02IntakeRecord.source_type == row.source_type,
            M02IntakeRecord.declared_statement_date < row.declared_statement_date,
            M02IntakeRecord.lifecycle_status != "superseded",
        )
        .order_by(
            M02IntakeRecord.declared_statement_date.desc(),
            M02IntakeRecord.created_at.desc(),
        )
    )
    if older is not None and older.intake_id != row.intake_id:
        row.superseding_candidate = True
        row.superseding_intake_id = older.intake_id


def _has_newer_candidate(db: Session, row: M02IntakeRecord) -> bool:
    if row.declared_statement_date is None:
        return False
    return (
        db.scalar(
            select(M02IntakeRecord.intake_id).where(
                M02IntakeRecord.client_id == row.client_id,
                M02IntakeRecord.source_type == row.source_type,
                M02IntakeRecord.declared_statement_date > row.declared_statement_date,
                M02IntakeRecord.superseding_intake_id == row.intake_id,
            )
        )
        is not None
    )
