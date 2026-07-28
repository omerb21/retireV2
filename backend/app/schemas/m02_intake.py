from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class DeclaredComponentValue(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1, max_length=128)


class M02ManualIntakeRequest(BaseModel):
    declared_provider_name: str | None = Field(default=None, max_length=255)
    product_name: str | None = Field(default=None, max_length=255)
    product_identifier: str | None = Field(default=None, max_length=128)
    declared_account_reference: str | None = Field(default=None, max_length=255)
    declared_total_balance_amount: Decimal | None = None
    declared_monthly_pension_amount: Decimal | None = None
    declared_component_values: list[DeclaredComponentValue] | None = None
    declared_statement_date: date | None = None
    declared_start_date: date | None = None
    declared_product_type: str | None = Field(default=None, max_length=255)
    source_type: str = Field(min_length=1, max_length=128)
    declared_basis: str | None = Field(default=None, max_length=4096)
    notes: str | None = Field(default=None, max_length=4096)


class M02IntakeUpdateRequest(BaseModel):
    declared_provider_name: str | None = Field(default=None, max_length=255)
    product_name: str | None = Field(default=None, max_length=255)
    product_identifier: str | None = Field(default=None, max_length=128)
    declared_account_reference: str | None = Field(default=None, max_length=255)
    declared_total_balance_amount: Decimal | None = None
    declared_monthly_pension_amount: Decimal | None = None
    declared_component_values: list[DeclaredComponentValue] | None = None
    declared_statement_date: date | None = None
    declared_start_date: date | None = None
    declared_product_type: str | None = Field(default=None, max_length=255)
    source_type: str | None = Field(default=None, max_length=128)
    declared_basis: str | None = Field(default=None, max_length=4096)
    notes: str | None = Field(default=None, max_length=4096)


class M02LifecycleRequest(BaseModel):
    target_status: Literal[
        "uploaded",
        "metadata_review",
        "accepted_for_review",
        "rejected",
        "superseded",
    ]
    rejection_reason_code: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4096)


class M02SourceResponse(BaseModel):
    source_id: str
    original_filename: str
    normalized_extension: str
    declared_mime_type: str
    validated_media_type: str
    detected_text_encoding: str | None
    sha256_checksum: str
    byte_size: int
    uploaded_at: datetime


class M02IntakeResponse(BaseModel):
    intake_id: str
    client_id: int
    declared_provider_name: str | None
    product_name: str | None
    product_identifier: str | None
    declared_account_reference: str | None
    manual_technical_reference: str | None
    manual_technical_reference_is_account: Literal[False] = False
    declared_total_balance_amount: Decimal | None
    declared_monthly_pension_amount: Decimal | None
    declared_component_values: list[dict[str, Any]] | None
    declared_statement_date: date | None
    declared_start_date: date | None
    declared_product_type: str | None
    source_type: str
    declared_basis: str | None
    notes: str | None
    lifecycle_status: str
    preservation_status: str
    preservation_failure_code: str | None
    duplicate_candidate: bool
    duplicate_of_intake_id: str | None
    superseding_candidate: bool
    superseding_intake_id: str | None
    allowed_lifecycle_targets: list[str]
    diagnostics: list[str]
    source: M02SourceResponse | None
    created_by_actor: str
    updated_by_actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime
    updated_at: datetime


class M02UploadFileResult(BaseModel):
    selection_index: int
    original_filename: str
    status: Literal["preserved", "failed"]
    intake: M02IntakeResponse | None = None
    error_code: str | None = None
    error_message: str | None = None


class M02UploadBatchResponse(BaseModel):
    results: list[M02UploadFileResult]
    request_error: dict[str, str] | None = None
