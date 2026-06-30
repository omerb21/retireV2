from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.actual_capitalization import ActualCapitalization
from app.models.clearinghouse_snapshot import ClearinghouseSnapshot
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.missing_data_item import MissingDataItem
from app.models.retirement_fact_contracts import (
    ADVISORY_STATUSES,
    AMOUNT_BASES,
    CAPITAL_ASSET_CATEGORIES,
    CONTINUATION_STATUSES,
    EXPENSE_CATEGORIES,
    EXPENSE_TYPES,
    FREQUENCIES,
    INCOME_CATEGORIES,
    PENSION_PRODUCT_TYPES,
    PLANNING_DOMAINS,
    SOURCE_STATUSES,
    TIMING_CONFIDENCES,
    VERIFICATION_STATES,
    WORK_AFTER_RETIREMENT_INTENTIONS,
)
from app.models.retirement_facts import (
    CapitalAsset,
    PensionHolding,
    RecurringExpense,
    RecurringIncome,
    RetirementTimingWorkIntention,
)
from app.models.retirement_planning_document import RetirementPlanningDocument

router = APIRouter(prefix="/api/clients", tags=["clients"])
LifecycleFilter = Literal["current", "superseded", "all"]


class ApiError(BaseModel):
    code: str
    message: str


class ClientCreateRequest(BaseModel):
    full_name: str
    id_number: str
    birth_date: date | None = None


class ClientResponse(BaseModel):
    client_id: int
    full_name: str
    id_number: str
    birth_date: date | None = None
    file_status: str
    professional_identification_status: str


class ProfileUpsertRequest(BaseModel):
    id_number: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    contact_method: str | None = None
    contact_details: str | None = None
    notes: str | None = None


class ProfileResponse(BaseModel):
    client_profile_id: str
    client_id: int
    id_number: str | None
    birth_date: date | None
    gender: str | None
    contact_method: str | None
    contact_details: str | None
    notes: str | None
    file_status: str
    professional_identification_status: str


class EmploymentRecordRequest(BaseModel):
    employer_name: str
    work_start_date: date
    work_end_date: date | None = None
    is_current: bool
    notes: str | None = None


class EmploymentRecordResponse(BaseModel):
    employment_record_id: str
    client_id: int
    employer_name: str
    work_start_date: date
    work_end_date: date | None
    is_current: bool
    notes: str | None


class GrantRequest(BaseModel):
    employment_record_id: str | None = None
    employer_name: str | None = None
    nominal_amount: Decimal | None = None
    indexed_amount: Decimal
    grant_date: date
    work_start_date: date
    work_end_date: date
    notes: str | None = None

    @field_validator("nominal_amount", "indexed_amount", mode="before")
    @classmethod
    def reject_blank_numeric_values(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            raise ValueError("numeric value must not be blank")
        return value

    @field_validator("nominal_amount", "indexed_amount")
    @classmethod
    def reject_negative_numeric_values(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("numeric value must be non-negative")
        return value


class GrantResponse(BaseModel):
    grant_id: str
    client_id: int
    employment_record_id: str | None
    employer_name: str | None
    nominal_amount: Decimal | None
    indexed_amount: Decimal
    grant_date: date
    work_start_date: date
    work_end_date: date
    notes: str | None


class ActualCapitalizationRequest(BaseModel):
    amount: Decimal
    capitalization_date: date
    source_label: str | None = None
    source_basis: str | None = None
    planner_assertion: str | None = None
    planner_assertion_basis: str | None = None
    notes: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def reject_blank_amount(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            raise ValueError("amount must not be blank")
        return value

    @field_validator("amount")
    @classmethod
    def reject_negative_amount(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("amount must be non-negative")
        return value

    @field_validator("source_label", "source_basis", "planner_assertion", "planner_assertion_basis", "notes")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @model_validator(mode="after")
    def require_planner_assertion_basis(self) -> "ActualCapitalizationRequest":
        if self.planner_assertion is not None and self.planner_assertion_basis is None:
            raise ValueError("planner_assertion_basis is required when planner_assertion is supplied")
        return self


class ActualCapitalizationResponse(BaseModel):
    capitalization_id: str
    client_id: int
    amount: Decimal
    capitalization_date: date
    source_label: str | None
    source_basis: str | None
    planner_assertion: str | None
    planner_assertion_basis: str | None
    notes: str | None


class ClearinghouseSnapshotRequest(BaseModel):
    import_date: date
    source_type: str
    source_file: str
    collection_status: str
    collection_notes: str | None = None


class ClearinghouseSnapshotResponse(BaseModel):
    clearinghouse_snapshot_id: str
    client_id: int
    import_date: date
    source_type: str
    source_file: str
    collection_status: str
    collection_notes: str | None
    verification_status: str
    verification_notes: str | None
    verified_at: datetime | None
    created_at: datetime


class RetirementPlanningDocumentRequest(BaseModel):
    document_type: str
    source_type: str | None = None
    source_file: str
    collection_date: date
    collection_status: str
    collection_notes: str | None = None


class RetirementPlanningDocumentResponse(BaseModel):
    document_id: str
    client_id: int
    document_type: str
    source_type: str | None
    source_file: str
    collection_date: date
    collection_status: str
    collection_notes: str | None
    verification_status: str
    verification_notes: str | None
    verified_at: datetime | None
    created_at: datetime


class VerificationUpdateRequest(BaseModel):
    verification_status: str
    verification_notes: str | None = None


class MissingDataItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_item_type: str
    missing_item_label: str
    missing_status: str
    notes: str | None = None
    planning_domain: str | None = None
    related_record_type: str | None = None
    related_record_id: int | None = None
    advisory_status: str | None = None
    neutral_reason: str | None = None

    @field_validator("planning_domain")
    @classmethod
    def validate_planning_domain(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, PLANNING_DOMAINS, "planning_domain")

    @field_validator("advisory_status")
    @classmethod
    def validate_advisory_status(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, ADVISORY_STATUSES, "advisory_status")


class MissingDataItemResponse(BaseModel):
    missing_data_item_id: str
    client_id: int
    missing_item_type: str
    missing_item_label: str
    missing_status: str
    notes: str | None
    planning_domain: str | None
    related_record_type: str | None
    related_record_id: int | None
    advisory_status: str | None
    neutral_reason: str | None
    created_at: datetime


def _validate_allowed_value(value: str | None, allowed_values: tuple[str, ...], field_name: str) -> str | None:
    if value is not None and value not in allowed_values:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed_values)}")
    return value


def _validate_source_status(value: str | None) -> str | None:
    return _validate_allowed_value(value, SOURCE_STATUSES, "source_status")


def _validate_verification_state(value: str | None) -> str | None:
    return _validate_allowed_value(value, VERIFICATION_STATES, "verification_state")


class PensionHoldingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str
    product_type: str
    product_name: str | None = None
    account_reference: str | None = None
    known_balance_amount: Decimal | None = None
    balance_as_of_date: date | None = None
    known_monthly_pension_amount: Decimal | None = None
    pension_amount_as_of_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, value: str) -> str:
        return _validate_allowed_value(value, PENSION_PRODUCT_TYPES, "product_type") or value

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)

    @model_validator(mode="after")
    def validate_required_dates(self) -> "PensionHoldingCreateRequest":
        if self.known_balance_amount is not None and self.balance_as_of_date is None:
            raise ValueError("balance_as_of_date is required when known_balance_amount is supplied")
        if self.known_monthly_pension_amount is not None and self.pension_amount_as_of_date is None:
            raise ValueError(
                "pension_amount_as_of_date is required when known_monthly_pension_amount is supplied"
            )
        return self


class PensionHoldingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str | None = None
    product_type: str | None = None
    product_name: str | None = None
    account_reference: str | None = None
    known_balance_amount: Decimal | None = None
    balance_as_of_date: date | None = None
    known_monthly_pension_amount: Decimal | None = None
    pension_amount_as_of_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, PENSION_PRODUCT_TYPES, "product_type")

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class PensionHoldingResponse(BaseModel):
    id: int
    client_id: int
    provider_name: str
    product_type: str
    lifecycle_status: str
    source_status: str
    verification_state: str
    product_name: str | None
    account_reference: str | None
    known_balance_amount: Decimal | None
    balance_as_of_date: date | None
    known_monthly_pension_amount: Decimal | None
    pension_amount_as_of_date: date | None
    source_type: str | None
    source_date: date | None
    source_note: str | None
    created_at: datetime
    updated_at: datetime


class CapitalAssetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_category: str
    asset_description: str
    known_value_amount: Decimal | None = None
    value_as_of_date: date | None = None
    liquidity_note: str | None = None
    restriction_note: str | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("asset_category")
    @classmethod
    def validate_asset_category(cls, value: str) -> str:
        return _validate_allowed_value(value, CAPITAL_ASSET_CATEGORIES, "asset_category") or value

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)

    @model_validator(mode="after")
    def validate_value_date(self) -> "CapitalAssetCreateRequest":
        if self.known_value_amount is not None and self.value_as_of_date is None:
            raise ValueError("value_as_of_date is required when known_value_amount is supplied")
        return self


class CapitalAssetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_category: str | None = None
    asset_description: str | None = None
    known_value_amount: Decimal | None = None
    value_as_of_date: date | None = None
    liquidity_note: str | None = None
    restriction_note: str | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("asset_category")
    @classmethod
    def validate_asset_category(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, CAPITAL_ASSET_CATEGORIES, "asset_category")

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class CapitalAssetResponse(BaseModel):
    id: int
    client_id: int
    asset_category: str
    asset_description: str
    lifecycle_status: str
    source_status: str
    verification_state: str
    known_value_amount: Decimal | None
    value_as_of_date: date | None
    liquidity_note: str | None
    restriction_note: str | None
    source_type: str | None
    source_date: date | None
    source_note: str | None
    created_at: datetime
    updated_at: datetime


class RecurringIncomeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income_category: str
    description: str
    amount: Decimal
    amount_basis: str
    frequency: str
    continuation_status: str
    start_date: date | None = None
    end_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("income_category")
    @classmethod
    def validate_income_category(cls, value: str) -> str:
        return _validate_allowed_value(value, INCOME_CATEGORIES, "income_category") or value

    @field_validator("amount_basis")
    @classmethod
    def validate_amount_basis(cls, value: str) -> str:
        return _validate_allowed_value(value, AMOUNT_BASES, "amount_basis") or value

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        return _validate_allowed_value(value, FREQUENCIES, "frequency") or value

    @field_validator("continuation_status")
    @classmethod
    def validate_continuation_status(cls, value: str) -> str:
        return _validate_allowed_value(value, CONTINUATION_STATUSES, "continuation_status") or value

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class RecurringIncomeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income_category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    amount_basis: str | None = None
    frequency: str | None = None
    continuation_status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("income_category")
    @classmethod
    def validate_income_category(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, INCOME_CATEGORIES, "income_category")

    @field_validator("amount_basis")
    @classmethod
    def validate_amount_basis(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, AMOUNT_BASES, "amount_basis")

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, FREQUENCIES, "frequency")

    @field_validator("continuation_status")
    @classmethod
    def validate_continuation_status(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, CONTINUATION_STATUSES, "continuation_status")

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class RecurringIncomeResponse(BaseModel):
    id: int
    client_id: int
    income_category: str
    description: str
    amount: Decimal
    amount_basis: str
    frequency: str
    continuation_status: str
    lifecycle_status: str
    source_status: str
    verification_state: str
    start_date: date | None
    end_date: date | None
    source_type: str | None
    source_date: date | None
    source_note: str | None
    created_at: datetime
    updated_at: datetime


class RecurringExpenseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_category: str
    description: str
    amount: Decimal
    frequency: str
    expense_type: str
    continuation_status: str
    start_date: date | None = None
    end_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("expense_category")
    @classmethod
    def validate_expense_category(cls, value: str) -> str:
        return _validate_allowed_value(value, EXPENSE_CATEGORIES, "expense_category") or value

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        return _validate_allowed_value(value, FREQUENCIES, "frequency") or value

    @field_validator("expense_type")
    @classmethod
    def validate_expense_type(cls, value: str) -> str:
        return _validate_allowed_value(value, EXPENSE_TYPES, "expense_type") or value

    @field_validator("continuation_status")
    @classmethod
    def validate_continuation_status(cls, value: str) -> str:
        return _validate_allowed_value(value, CONTINUATION_STATUSES, "continuation_status") or value

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class RecurringExpenseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    frequency: str | None = None
    expense_type: str | None = None
    continuation_status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("expense_category")
    @classmethod
    def validate_expense_category(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, EXPENSE_CATEGORIES, "expense_category")

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, FREQUENCIES, "frequency")

    @field_validator("expense_type")
    @classmethod
    def validate_expense_type(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, EXPENSE_TYPES, "expense_type")

    @field_validator("continuation_status")
    @classmethod
    def validate_continuation_status(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, CONTINUATION_STATUSES, "continuation_status")

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class RecurringExpenseResponse(BaseModel):
    id: int
    client_id: int
    expense_category: str
    description: str
    amount: Decimal
    frequency: str
    expense_type: str
    continuation_status: str
    lifecycle_status: str
    source_status: str
    verification_state: str
    start_date: date | None
    end_date: date | None
    source_type: str | None
    source_date: date | None
    source_note: str | None
    created_at: datetime
    updated_at: datetime


class RetirementTimingWorkIntentionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timing_confidence: str
    work_after_retirement_intention: str
    planned_work_end_date: date | None = None
    intended_pension_start_date: date | None = None
    other_known_retirement_date: date | None = None
    other_known_retirement_date_label: str | None = None
    anticipated_work_end_date: date | None = None
    work_intention_note: str | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("timing_confidence")
    @classmethod
    def validate_timing_confidence(cls, value: str) -> str:
        return _validate_allowed_value(value, TIMING_CONFIDENCES, "timing_confidence") or value

    @field_validator("work_after_retirement_intention")
    @classmethod
    def validate_work_after_retirement_intention(cls, value: str) -> str:
        return (
            _validate_allowed_value(
                value, WORK_AFTER_RETIREMENT_INTENTIONS, "work_after_retirement_intention"
            )
            or value
        )

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)

    @model_validator(mode="after")
    def validate_other_known_retirement_date_label(self) -> "RetirementTimingWorkIntentionCreateRequest":
        if self.other_known_retirement_date is not None and self.other_known_retirement_date_label is None:
            raise ValueError(
                "other_known_retirement_date_label is required when other_known_retirement_date is supplied"
            )
        return self


class RetirementTimingWorkIntentionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timing_confidence: str | None = None
    work_after_retirement_intention: str | None = None
    planned_work_end_date: date | None = None
    intended_pension_start_date: date | None = None
    other_known_retirement_date: date | None = None
    other_known_retirement_date_label: str | None = None
    anticipated_work_end_date: date | None = None
    work_intention_note: str | None = None
    source_type: str | None = None
    source_date: date | None = None
    source_note: str | None = None
    source_status: str | None = None
    verification_state: str | None = None

    @field_validator("timing_confidence")
    @classmethod
    def validate_timing_confidence(cls, value: str | None) -> str | None:
        return _validate_allowed_value(value, TIMING_CONFIDENCES, "timing_confidence")

    @field_validator("work_after_retirement_intention")
    @classmethod
    def validate_work_after_retirement_intention(cls, value: str | None) -> str | None:
        return _validate_allowed_value(
            value, WORK_AFTER_RETIREMENT_INTENTIONS, "work_after_retirement_intention"
        )

    @field_validator("source_status")
    @classmethod
    def validate_source_status(cls, value: str | None) -> str | None:
        return _validate_source_status(value)

    @field_validator("verification_state")
    @classmethod
    def validate_verification_state(cls, value: str | None) -> str | None:
        return _validate_verification_state(value)


class RetirementTimingWorkIntentionResponse(BaseModel):
    id: int
    client_id: int
    timing_confidence: str
    work_after_retirement_intention: str
    lifecycle_status: str
    source_status: str
    verification_state: str
    planned_work_end_date: date | None
    intended_pension_start_date: date | None
    other_known_retirement_date: date | None
    other_known_retirement_date_label: str | None
    anticipated_work_end_date: date | None
    work_intention_note: str | None
    source_type: str | None
    source_date: date | None
    source_note: str | None
    created_at: datetime
    updated_at: datetime


def _client_not_found(client_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "CLIENT_NOT_FOUND", "message": f"Client {client_id} was not found"},
    )


def _require_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise _client_not_found(client_id)
    return client


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _professional_identification_status(client: Client, profile: ClientProfile | None) -> str:
    has_required_fields = (
        _has_text(client.display_name)
        and _has_text(client.id_number)
        and client.birth_date is not None
        and profile is not None
        and _has_text(profile.contact_method)
        and _has_text(profile.contact_details)
    )
    return "professionally_identified" if has_required_fields else "identification_incomplete"


def _client_to_response(client: Client, profile: ClientProfile | None = None) -> ClientResponse:
    resolved_profile = profile if profile is not None else client.client_profile
    return ClientResponse(
        client_id=client.client_id,
        full_name=client.display_name,
        id_number=client.id_number,
        birth_date=client.birth_date,
        file_status="file_created",
        professional_identification_status=_professional_identification_status(client, resolved_profile),
    )


def _profile_to_response(client: Client, profile: ClientProfile) -> ProfileResponse:
    return ProfileResponse(
        client_profile_id=profile.client_profile_id,
        client_id=client.client_id,
        id_number=client.id_number,
        birth_date=client.birth_date,
        gender=profile.gender,
        contact_method=profile.contact_method,
        contact_details=profile.contact_details,
        notes=profile.notes,
        file_status="file_created",
        professional_identification_status=_professional_identification_status(client, profile),
    )


def _source_item_not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _employment_record_to_response(row: EmploymentRecord) -> EmploymentRecordResponse:
    return EmploymentRecordResponse(
        employment_record_id=row.employment_record_id,
        client_id=row.client_id,
        employer_name=row.employer_name,
        work_start_date=row.work_start_date,
        work_end_date=row.work_end_date,
        is_current=row.is_current,
        notes=row.notes,
    )


def _grant_to_response(row: Grant) -> GrantResponse:
    return GrantResponse(
        grant_id=row.grant_id,
        client_id=row.client_id,
        employment_record_id=row.employment_record_id,
        employer_name=row.employer_name,
        nominal_amount=row.nominal_amount,
        indexed_amount=row.indexed_amount,
        grant_date=row.grant_date,
        work_start_date=row.work_start_date,
        work_end_date=row.work_end_date,
        notes=row.notes,
    )


def _actual_capitalization_to_response(row: ActualCapitalization) -> ActualCapitalizationResponse:
    return ActualCapitalizationResponse(
        capitalization_id=row.capitalization_id,
        client_id=row.client_id,
        amount=row.amount,
        capitalization_date=row.capitalization_date,
        source_label=row.source_label,
        source_basis=row.source_basis,
        planner_assertion=row.planner_assertion,
        planner_assertion_basis=row.planner_assertion_basis,
        notes=row.notes,
    )


def _required_collection_text(value: str, field_name: str) -> str:
    if not _has_text(value):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COLLECTION_METADATA_REQUIRED",
                "message": f"{field_name} is required for collection metadata",
            },
        )
    return value.strip()


def _required_file_metadata_text(value: str, field_name: str) -> str:
    if not _has_text(value):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FILE_METADATA_REQUIRED",
                "message": f"{field_name} is required",
            },
        )
    return value.strip()


def _clearinghouse_snapshot_to_response(row: ClearinghouseSnapshot) -> ClearinghouseSnapshotResponse:
    return ClearinghouseSnapshotResponse(
        clearinghouse_snapshot_id=row.clearinghouse_snapshot_id,
        client_id=row.client_id,
        import_date=row.import_date,
        source_type=row.source_type,
        source_file=row.source_file,
        collection_status=row.collection_status,
        collection_notes=row.collection_notes,
        verification_status=row.verification_status,
        verification_notes=row.verification_notes,
        verified_at=row.verified_at,
        created_at=row.created_at,
    )


def _document_to_response(row: RetirementPlanningDocument) -> RetirementPlanningDocumentResponse:
    return RetirementPlanningDocumentResponse(
        document_id=row.document_id,
        client_id=row.client_id,
        document_type=row.document_type,
        source_type=row.source_type,
        source_file=row.source_file,
        collection_date=row.collection_date,
        collection_status=row.collection_status,
        collection_notes=row.collection_notes,
        verification_status=row.verification_status,
        verification_notes=row.verification_notes,
        verified_at=row.verified_at,
        created_at=row.created_at,
    )


def _missing_data_item_to_response(row: MissingDataItem) -> MissingDataItemResponse:
    return MissingDataItemResponse(
        missing_data_item_id=row.missing_data_item_id,
        client_id=row.client_id,
        missing_item_type=row.missing_item_type,
        missing_item_label=row.missing_item_label,
        missing_status=row.missing_status,
        notes=row.notes,
        planning_domain=row.planning_domain,
        related_record_type=row.related_record_type,
        related_record_id=row.related_record_id,
        advisory_status=row.advisory_status,
        neutral_reason=row.neutral_reason,
        created_at=row.created_at,
    )


def _pension_holding_to_response(row: PensionHolding) -> PensionHoldingResponse:
    return PensionHoldingResponse(
        id=row.id,
        client_id=row.client_id,
        provider_name=row.provider_name,
        product_type=row.product_type,
        lifecycle_status=row.lifecycle_status,
        source_status=row.source_status,
        verification_state=row.verification_state,
        product_name=row.product_name,
        account_reference=row.account_reference,
        known_balance_amount=row.known_balance_amount,
        balance_as_of_date=row.balance_as_of_date,
        known_monthly_pension_amount=row.known_monthly_pension_amount,
        pension_amount_as_of_date=row.pension_amount_as_of_date,
        source_type=row.source_type,
        source_date=row.source_date,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _capital_asset_to_response(row: CapitalAsset) -> CapitalAssetResponse:
    return CapitalAssetResponse(
        id=row.id,
        client_id=row.client_id,
        asset_category=row.asset_category,
        asset_description=row.asset_description,
        lifecycle_status=row.lifecycle_status,
        source_status=row.source_status,
        verification_state=row.verification_state,
        known_value_amount=row.known_value_amount,
        value_as_of_date=row.value_as_of_date,
        liquidity_note=row.liquidity_note,
        restriction_note=row.restriction_note,
        source_type=row.source_type,
        source_date=row.source_date,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recurring_income_to_response(row: RecurringIncome) -> RecurringIncomeResponse:
    return RecurringIncomeResponse(
        id=row.id,
        client_id=row.client_id,
        income_category=row.income_category,
        description=row.description,
        amount=row.amount,
        amount_basis=row.amount_basis,
        frequency=row.frequency,
        continuation_status=row.continuation_status,
        lifecycle_status=row.lifecycle_status,
        source_status=row.source_status,
        verification_state=row.verification_state,
        start_date=row.start_date,
        end_date=row.end_date,
        source_type=row.source_type,
        source_date=row.source_date,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recurring_expense_to_response(row: RecurringExpense) -> RecurringExpenseResponse:
    return RecurringExpenseResponse(
        id=row.id,
        client_id=row.client_id,
        expense_category=row.expense_category,
        description=row.description,
        amount=row.amount,
        frequency=row.frequency,
        expense_type=row.expense_type,
        continuation_status=row.continuation_status,
        lifecycle_status=row.lifecycle_status,
        source_status=row.source_status,
        verification_state=row.verification_state,
        start_date=row.start_date,
        end_date=row.end_date,
        source_type=row.source_type,
        source_date=row.source_date,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _retirement_timing_work_intention_to_response(
    row: RetirementTimingWorkIntention,
) -> RetirementTimingWorkIntentionResponse:
    return RetirementTimingWorkIntentionResponse(
        id=row.id,
        client_id=row.client_id,
        timing_confidence=row.timing_confidence,
        work_after_retirement_intention=row.work_after_retirement_intention,
        lifecycle_status=row.lifecycle_status,
        source_status=row.source_status,
        verification_state=row.verification_state,
        planned_work_end_date=row.planned_work_end_date,
        intended_pension_start_date=row.intended_pension_start_date,
        other_known_retirement_date=row.other_known_retirement_date,
        other_known_retirement_date_label=row.other_known_retirement_date_label,
        anticipated_work_end_date=row.anticipated_work_end_date,
        work_intention_note=row.work_intention_note,
        source_type=row.source_type,
        source_date=row.source_date,
        source_note=row.source_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply_fact_update(row: Any, payload: BaseModel) -> None:
    for field_name in payload.model_fields_set:
        setattr(row, field_name, getattr(payload, field_name))


def _validation_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": "PACKAGE_B_VALIDATION_ERROR", "message": message},
    )


def _validate_pension_holding_dates(row: PensionHolding) -> None:
    if row.known_balance_amount is not None and row.balance_as_of_date is None:
        raise _validation_error("balance_as_of_date is required when known_balance_amount is supplied")
    if row.known_monthly_pension_amount is not None and row.pension_amount_as_of_date is None:
        raise _validation_error(
            "pension_amount_as_of_date is required when known_monthly_pension_amount is supplied"
        )


def _validate_capital_asset_value_date(row: CapitalAsset) -> None:
    if row.known_value_amount is not None and row.value_as_of_date is None:
        raise _validation_error("value_as_of_date is required when known_value_amount is supplied")


def _validate_retirement_timing_work_intention_other_date(
    row: RetirementTimingWorkIntention,
) -> None:
    if row.other_known_retirement_date is not None and row.other_known_retirement_date_label is None:
        raise _validation_error(
            "other_known_retirement_date_label is required when other_known_retirement_date is supplied"
        )


def _apply_lifecycle_filter(statement: Any, model: Any, lifecycle_status: LifecycleFilter) -> Any:
    if lifecycle_status == "all":
        return statement
    return statement.where(model.lifecycle_status == lifecycle_status)


def _require_employment_record(db: Session, client_id: int, employment_record_id: str) -> EmploymentRecord:
    row = db.scalar(
        select(EmploymentRecord).where(
            EmploymentRecord.client_id == client_id,
            EmploymentRecord.employment_record_id == employment_record_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "EMPLOYMENT_RECORD_NOT_FOUND",
            f"Employment record {employment_record_id} was not found for client {client_id}",
        )
    return row


def _require_grant(db: Session, client_id: int, grant_id: str) -> Grant:
    row = db.scalar(select(Grant).where(Grant.client_id == client_id, Grant.grant_id == grant_id))
    if row is None:
        raise _source_item_not_found(
            "GRANT_NOT_FOUND",
            f"Grant {grant_id} was not found for client {client_id}",
        )
    return row


def _require_actual_capitalization(db: Session, client_id: int, capitalization_id: str) -> ActualCapitalization:
    row = db.scalar(
        select(ActualCapitalization).where(
            ActualCapitalization.client_id == client_id,
            ActualCapitalization.capitalization_id == capitalization_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "ACTUAL_CAPITALIZATION_NOT_FOUND",
            f"Actual capitalization {capitalization_id} was not found for client {client_id}",
        )
    return row


def _require_pension_holding(db: Session, client_id: int, pension_holding_id: int) -> PensionHolding:
    row = db.scalar(
        select(PensionHolding).where(
            PensionHolding.client_id == client_id,
            PensionHolding.id == pension_holding_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "PENSION_HOLDING_NOT_FOUND",
            f"Pension holding {pension_holding_id} was not found for client {client_id}",
        )
    return row


def _require_capital_asset(db: Session, client_id: int, capital_asset_id: int) -> CapitalAsset:
    row = db.scalar(
        select(CapitalAsset).where(
            CapitalAsset.client_id == client_id,
            CapitalAsset.id == capital_asset_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "CAPITAL_ASSET_NOT_FOUND",
            f"Capital asset {capital_asset_id} was not found for client {client_id}",
        )
    return row


def _require_recurring_income(db: Session, client_id: int, recurring_income_id: int) -> RecurringIncome:
    row = db.scalar(
        select(RecurringIncome).where(
            RecurringIncome.client_id == client_id,
            RecurringIncome.id == recurring_income_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "RECURRING_INCOME_NOT_FOUND",
            f"Recurring income {recurring_income_id} was not found for client {client_id}",
        )
    return row


def _require_recurring_expense(db: Session, client_id: int, recurring_expense_id: int) -> RecurringExpense:
    row = db.scalar(
        select(RecurringExpense).where(
            RecurringExpense.client_id == client_id,
            RecurringExpense.id == recurring_expense_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "RECURRING_EXPENSE_NOT_FOUND",
            f"Recurring expense {recurring_expense_id} was not found for client {client_id}",
        )
    return row


def _require_retirement_timing_work_intention(
    db: Session,
    client_id: int,
    retirement_timing_work_intention_id: int,
) -> RetirementTimingWorkIntention:
    row = db.scalar(
        select(RetirementTimingWorkIntention).where(
            RetirementTimingWorkIntention.client_id == client_id,
            RetirementTimingWorkIntention.id == retirement_timing_work_intention_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "RETIREMENT_TIMING_WORK_INTENTION_NOT_FOUND",
            "Retirement timing work intention "
            f"{retirement_timing_work_intention_id} was not found for client {client_id}",
        )
    return row


def _require_clearinghouse_snapshot(
    db: Session, client_id: int, clearinghouse_snapshot_id: str
) -> ClearinghouseSnapshot:
    row = db.scalar(
        select(ClearinghouseSnapshot).where(
            ClearinghouseSnapshot.client_id == client_id,
            ClearinghouseSnapshot.clearinghouse_snapshot_id == clearinghouse_snapshot_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "CLEARINGHOUSE_SNAPSHOT_NOT_FOUND",
            f"Clearinghouse snapshot {clearinghouse_snapshot_id} was not found for client {client_id}",
        )
    return row


def _require_retirement_planning_document(db: Session, client_id: int, document_id: str) -> RetirementPlanningDocument:
    row = db.scalar(
        select(RetirementPlanningDocument).where(
            RetirementPlanningDocument.client_id == client_id,
            RetirementPlanningDocument.document_id == document_id,
        )
    )
    if row is None:
        raise _source_item_not_found(
            "RETIREMENT_PLANNING_DOCUMENT_NOT_FOUND",
            f"Retirement planning document {document_id} was not found for client {client_id}",
        )
    return row


def _apply_verification_update(
    row: ClearinghouseSnapshot | RetirementPlanningDocument,
    payload: VerificationUpdateRequest,
) -> None:
    row.verification_status = _required_file_metadata_text(payload.verification_status, "Verification Status")
    row.verification_notes = payload.verification_notes
    row.verified_at = datetime.now(timezone.utc)


@router.get("", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)) -> list[ClientResponse]:
    clients = db.scalars(select(Client).order_by(Client.client_id.asc())).all()
    return [
        _client_to_response(client)
        for client in clients
    ]


@router.post("", response_model=ClientResponse)
def create_client(payload: ClientCreateRequest, db: Session = Depends(get_db)) -> ClientResponse:
    if not _has_text(payload.id_number):
        raise HTTPException(
            status_code=422,
            detail={"code": "ID_NUMBER_REQUIRED", "message": "ID Number is required for file creation"},
        )

    client = Client(
        display_name=payload.full_name,
        id_number=payload.id_number.strip(),
        birth_date=payload.birth_date,
        status=None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    return _client_to_response(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientResponse:
    client = _require_client(db, client_id)
    return _client_to_response(client)


@router.put("/{client_id}/profile")
def put_client_profile(
    client_id: int,
    payload: ProfileUpsertRequest,
    db: Session = Depends(get_db),
) -> dict:
    client = _require_client(db, client_id)
    client_key = client_id

    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_key))
    if profile is None:
        profile = ClientProfile(
            client_profile_id=f"CP-{client_id}",
            client_id=client_key,
            birth_date=None,
            gender=payload.gender,
            contact_method=payload.contact_method,
            contact_details=payload.contact_details,
            notes=payload.notes,
        )
        db.add(profile)
    else:
        profile.gender = payload.gender
        profile.contact_method = payload.contact_method
        profile.contact_details = payload.contact_details
        profile.notes = payload.notes

    if payload.id_number is not None:
        if not _has_text(payload.id_number):
            raise HTTPException(
                status_code=422,
                detail={"code": "ID_NUMBER_REQUIRED", "message": "ID Number is required for file creation"},
            )
        client.id_number = payload.id_number.strip()
    if "birth_date" in payload.model_fields_set:
        client.birth_date = payload.birth_date

    db.commit()
    db.refresh(client)
    db.refresh(profile)
    return {
        "profile": _profile_to_response(client, profile).model_dump(mode="json")
    }


@router.get("/{client_id}/profile")
def get_client_profile(client_id: int, db: Session = Depends(get_db)) -> dict:
    client = _require_client(db, client_id)
    profile = db.scalar(select(ClientProfile).where(ClientProfile.client_id == client_id))
    if profile is None:
        return {"profile": None}

    return {
        "profile": _profile_to_response(client, profile).model_dump(mode="json")
    }


@router.post("/{client_id}/clearinghouse-snapshots", response_model=ClearinghouseSnapshotResponse)
def create_clearinghouse_snapshot(
    client_id: int,
    payload: ClearinghouseSnapshotRequest,
    db: Session = Depends(get_db),
) -> ClearinghouseSnapshotResponse:
    _require_client(db, client_id)

    snapshot = ClearinghouseSnapshot(
        clearinghouse_snapshot_id=f"CHS-{uuid4().hex}",
        client_id=client_id,
        import_date=payload.import_date,
        source_type=_required_collection_text(payload.source_type, "Source Type"),
        source_file=_required_collection_text(payload.source_file, "Source File"),
        collection_status=_required_collection_text(payload.collection_status, "Collection Status"),
        collection_notes=payload.collection_notes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return _clearinghouse_snapshot_to_response(snapshot)


@router.get("/{client_id}/clearinghouse-snapshots", response_model=list[ClearinghouseSnapshotResponse])
def list_clearinghouse_snapshots(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[ClearinghouseSnapshotResponse]:
    _require_client(db, client_id)
    snapshots = db.scalars(
        select(ClearinghouseSnapshot)
        .where(ClearinghouseSnapshot.client_id == client_id)
        .order_by(ClearinghouseSnapshot.created_at.desc(), ClearinghouseSnapshot.clearinghouse_snapshot_id.desc())
    ).all()

    return [_clearinghouse_snapshot_to_response(row) for row in snapshots]


@router.get(
    "/{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id}",
    response_model=ClearinghouseSnapshotResponse,
)
def get_clearinghouse_snapshot(
    client_id: int,
    clearinghouse_snapshot_id: str,
    db: Session = Depends(get_db),
) -> ClearinghouseSnapshotResponse:
    _require_client(db, client_id)
    snapshot = _require_clearinghouse_snapshot(db, client_id, clearinghouse_snapshot_id)
    return _clearinghouse_snapshot_to_response(snapshot)


@router.put(
    "/{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id}/verification",
    response_model=ClearinghouseSnapshotResponse,
)
def update_clearinghouse_snapshot_verification(
    client_id: int,
    clearinghouse_snapshot_id: str,
    payload: VerificationUpdateRequest,
    db: Session = Depends(get_db),
) -> ClearinghouseSnapshotResponse:
    _require_client(db, client_id)
    snapshot = _require_clearinghouse_snapshot(db, client_id, clearinghouse_snapshot_id)
    _apply_verification_update(snapshot, payload)
    db.commit()
    db.refresh(snapshot)
    return _clearinghouse_snapshot_to_response(snapshot)


@router.post("/{client_id}/documents", response_model=RetirementPlanningDocumentResponse)
def create_retirement_planning_document(
    client_id: int,
    payload: RetirementPlanningDocumentRequest,
    db: Session = Depends(get_db),
) -> RetirementPlanningDocumentResponse:
    _require_client(db, client_id)

    document = RetirementPlanningDocument(
        document_id=f"DOC-{uuid4().hex}",
        client_id=client_id,
        document_type=_required_collection_text(payload.document_type, "Document Type"),
        source_type=payload.source_type.strip() if _has_text(payload.source_type) else None,
        source_file=_required_collection_text(payload.source_file, "Source File"),
        collection_date=payload.collection_date,
        collection_status=_required_collection_text(payload.collection_status, "Collection Status"),
        collection_notes=payload.collection_notes,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _document_to_response(document)


@router.get("/{client_id}/documents", response_model=list[RetirementPlanningDocumentResponse])
def list_retirement_planning_documents(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[RetirementPlanningDocumentResponse]:
    _require_client(db, client_id)
    documents = db.scalars(
        select(RetirementPlanningDocument)
        .where(RetirementPlanningDocument.client_id == client_id)
        .order_by(RetirementPlanningDocument.created_at.desc(), RetirementPlanningDocument.document_id.desc())
    ).all()

    return [_document_to_response(row) for row in documents]


@router.get("/{client_id}/documents/{document_id}", response_model=RetirementPlanningDocumentResponse)
def get_retirement_planning_document(
    client_id: int,
    document_id: str,
    db: Session = Depends(get_db),
) -> RetirementPlanningDocumentResponse:
    _require_client(db, client_id)
    document = _require_retirement_planning_document(db, client_id, document_id)
    return _document_to_response(document)


@router.put("/{client_id}/documents/{document_id}/verification", response_model=RetirementPlanningDocumentResponse)
def update_retirement_planning_document_verification(
    client_id: int,
    document_id: str,
    payload: VerificationUpdateRequest,
    db: Session = Depends(get_db),
) -> RetirementPlanningDocumentResponse:
    _require_client(db, client_id)
    document = _require_retirement_planning_document(db, client_id, document_id)
    _apply_verification_update(document, payload)
    db.commit()
    db.refresh(document)
    return _document_to_response(document)


@router.post("/{client_id}/pension-holdings", response_model=PensionHoldingResponse)
def create_pension_holding(
    client_id: int,
    payload: PensionHoldingCreateRequest,
    db: Session = Depends(get_db),
) -> PensionHoldingResponse:
    _require_client(db, client_id)
    row = PensionHolding(client_id=client_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _pension_holding_to_response(row)


@router.get("/{client_id}/pension-holdings", response_model=list[PensionHoldingResponse])
def list_pension_holdings(
    client_id: int,
    lifecycle_status: LifecycleFilter = "current",
    db: Session = Depends(get_db),
) -> list[PensionHoldingResponse]:
    _require_client(db, client_id)
    statement = select(PensionHolding).where(PensionHolding.client_id == client_id)
    statement = _apply_lifecycle_filter(statement, PensionHolding, lifecycle_status)
    rows = db.scalars(statement.order_by(PensionHolding.created_at.desc(), PensionHolding.id.desc())).all()
    return [_pension_holding_to_response(row) for row in rows]


@router.get("/{client_id}/pension-holdings/{pension_holding_id}", response_model=PensionHoldingResponse)
def get_pension_holding(
    client_id: int,
    pension_holding_id: int,
    db: Session = Depends(get_db),
) -> PensionHoldingResponse:
    _require_client(db, client_id)
    row = _require_pension_holding(db, client_id, pension_holding_id)
    return _pension_holding_to_response(row)


@router.put("/{client_id}/pension-holdings/{pension_holding_id}", response_model=PensionHoldingResponse)
def update_pension_holding(
    client_id: int,
    pension_holding_id: int,
    payload: PensionHoldingUpdateRequest,
    db: Session = Depends(get_db),
) -> PensionHoldingResponse:
    _require_client(db, client_id)
    row = _require_pension_holding(db, client_id, pension_holding_id)
    _apply_fact_update(row, payload)
    _validate_pension_holding_dates(row)
    db.commit()
    db.refresh(row)
    return _pension_holding_to_response(row)


@router.post("/{client_id}/capital-assets", response_model=CapitalAssetResponse)
def create_capital_asset(
    client_id: int,
    payload: CapitalAssetCreateRequest,
    db: Session = Depends(get_db),
) -> CapitalAssetResponse:
    _require_client(db, client_id)
    row = CapitalAsset(client_id=client_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _capital_asset_to_response(row)


@router.get("/{client_id}/capital-assets", response_model=list[CapitalAssetResponse])
def list_capital_assets(
    client_id: int,
    lifecycle_status: LifecycleFilter = "current",
    db: Session = Depends(get_db),
) -> list[CapitalAssetResponse]:
    _require_client(db, client_id)
    statement = select(CapitalAsset).where(CapitalAsset.client_id == client_id)
    statement = _apply_lifecycle_filter(statement, CapitalAsset, lifecycle_status)
    rows = db.scalars(statement.order_by(CapitalAsset.created_at.desc(), CapitalAsset.id.desc())).all()
    return [_capital_asset_to_response(row) for row in rows]


@router.get("/{client_id}/capital-assets/{capital_asset_id}", response_model=CapitalAssetResponse)
def get_capital_asset(
    client_id: int,
    capital_asset_id: int,
    db: Session = Depends(get_db),
) -> CapitalAssetResponse:
    _require_client(db, client_id)
    row = _require_capital_asset(db, client_id, capital_asset_id)
    return _capital_asset_to_response(row)


@router.put("/{client_id}/capital-assets/{capital_asset_id}", response_model=CapitalAssetResponse)
def update_capital_asset(
    client_id: int,
    capital_asset_id: int,
    payload: CapitalAssetUpdateRequest,
    db: Session = Depends(get_db),
) -> CapitalAssetResponse:
    _require_client(db, client_id)
    row = _require_capital_asset(db, client_id, capital_asset_id)
    _apply_fact_update(row, payload)
    _validate_capital_asset_value_date(row)
    db.commit()
    db.refresh(row)
    return _capital_asset_to_response(row)


@router.post("/{client_id}/recurring-incomes", response_model=RecurringIncomeResponse)
def create_recurring_income(
    client_id: int,
    payload: RecurringIncomeCreateRequest,
    db: Session = Depends(get_db),
) -> RecurringIncomeResponse:
    _require_client(db, client_id)
    row = RecurringIncome(client_id=client_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _recurring_income_to_response(row)


@router.get("/{client_id}/recurring-incomes", response_model=list[RecurringIncomeResponse])
def list_recurring_incomes(
    client_id: int,
    lifecycle_status: LifecycleFilter = "current",
    db: Session = Depends(get_db),
) -> list[RecurringIncomeResponse]:
    _require_client(db, client_id)
    statement = select(RecurringIncome).where(RecurringIncome.client_id == client_id)
    statement = _apply_lifecycle_filter(statement, RecurringIncome, lifecycle_status)
    rows = db.scalars(statement.order_by(RecurringIncome.created_at.desc(), RecurringIncome.id.desc())).all()
    return [_recurring_income_to_response(row) for row in rows]


@router.get("/{client_id}/recurring-incomes/{recurring_income_id}", response_model=RecurringIncomeResponse)
def get_recurring_income(
    client_id: int,
    recurring_income_id: int,
    db: Session = Depends(get_db),
) -> RecurringIncomeResponse:
    _require_client(db, client_id)
    row = _require_recurring_income(db, client_id, recurring_income_id)
    return _recurring_income_to_response(row)


@router.put("/{client_id}/recurring-incomes/{recurring_income_id}", response_model=RecurringIncomeResponse)
def update_recurring_income(
    client_id: int,
    recurring_income_id: int,
    payload: RecurringIncomeUpdateRequest,
    db: Session = Depends(get_db),
) -> RecurringIncomeResponse:
    _require_client(db, client_id)
    row = _require_recurring_income(db, client_id, recurring_income_id)
    _apply_fact_update(row, payload)
    db.commit()
    db.refresh(row)
    return _recurring_income_to_response(row)


@router.post("/{client_id}/recurring-expenses", response_model=RecurringExpenseResponse)
def create_recurring_expense(
    client_id: int,
    payload: RecurringExpenseCreateRequest,
    db: Session = Depends(get_db),
) -> RecurringExpenseResponse:
    _require_client(db, client_id)
    row = RecurringExpense(client_id=client_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _recurring_expense_to_response(row)


@router.get("/{client_id}/recurring-expenses", response_model=list[RecurringExpenseResponse])
def list_recurring_expenses(
    client_id: int,
    lifecycle_status: LifecycleFilter = "current",
    db: Session = Depends(get_db),
) -> list[RecurringExpenseResponse]:
    _require_client(db, client_id)
    statement = select(RecurringExpense).where(RecurringExpense.client_id == client_id)
    statement = _apply_lifecycle_filter(statement, RecurringExpense, lifecycle_status)
    rows = db.scalars(statement.order_by(RecurringExpense.created_at.desc(), RecurringExpense.id.desc())).all()
    return [_recurring_expense_to_response(row) for row in rows]


@router.get("/{client_id}/recurring-expenses/{recurring_expense_id}", response_model=RecurringExpenseResponse)
def get_recurring_expense(
    client_id: int,
    recurring_expense_id: int,
    db: Session = Depends(get_db),
) -> RecurringExpenseResponse:
    _require_client(db, client_id)
    row = _require_recurring_expense(db, client_id, recurring_expense_id)
    return _recurring_expense_to_response(row)


@router.put("/{client_id}/recurring-expenses/{recurring_expense_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(
    client_id: int,
    recurring_expense_id: int,
    payload: RecurringExpenseUpdateRequest,
    db: Session = Depends(get_db),
) -> RecurringExpenseResponse:
    _require_client(db, client_id)
    row = _require_recurring_expense(db, client_id, recurring_expense_id)
    _apply_fact_update(row, payload)
    db.commit()
    db.refresh(row)
    return _recurring_expense_to_response(row)


@router.post(
    "/{client_id}/retirement-timing-work-intentions",
    response_model=RetirementTimingWorkIntentionResponse,
)
def create_retirement_timing_work_intention(
    client_id: int,
    payload: RetirementTimingWorkIntentionCreateRequest,
    db: Session = Depends(get_db),
) -> RetirementTimingWorkIntentionResponse:
    _require_client(db, client_id)
    row = RetirementTimingWorkIntention(client_id=client_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _retirement_timing_work_intention_to_response(row)


@router.get(
    "/{client_id}/retirement-timing-work-intentions",
    response_model=list[RetirementTimingWorkIntentionResponse],
)
def list_retirement_timing_work_intentions(
    client_id: int,
    lifecycle_status: LifecycleFilter = "current",
    db: Session = Depends(get_db),
) -> list[RetirementTimingWorkIntentionResponse]:
    _require_client(db, client_id)
    statement = select(RetirementTimingWorkIntention).where(
        RetirementTimingWorkIntention.client_id == client_id
    )
    statement = _apply_lifecycle_filter(statement, RetirementTimingWorkIntention, lifecycle_status)
    rows = db.scalars(
        statement.order_by(
            RetirementTimingWorkIntention.created_at.desc(),
            RetirementTimingWorkIntention.id.desc(),
        )
    ).all()
    return [_retirement_timing_work_intention_to_response(row) for row in rows]


@router.get(
    "/{client_id}/retirement-timing-work-intentions/{retirement_timing_work_intention_id}",
    response_model=RetirementTimingWorkIntentionResponse,
)
def get_retirement_timing_work_intention(
    client_id: int,
    retirement_timing_work_intention_id: int,
    db: Session = Depends(get_db),
) -> RetirementTimingWorkIntentionResponse:
    _require_client(db, client_id)
    row = _require_retirement_timing_work_intention(
        db,
        client_id,
        retirement_timing_work_intention_id,
    )
    return _retirement_timing_work_intention_to_response(row)


@router.put(
    "/{client_id}/retirement-timing-work-intentions/{retirement_timing_work_intention_id}",
    response_model=RetirementTimingWorkIntentionResponse,
)
def update_retirement_timing_work_intention(
    client_id: int,
    retirement_timing_work_intention_id: int,
    payload: RetirementTimingWorkIntentionUpdateRequest,
    db: Session = Depends(get_db),
) -> RetirementTimingWorkIntentionResponse:
    _require_client(db, client_id)
    row = _require_retirement_timing_work_intention(
        db,
        client_id,
        retirement_timing_work_intention_id,
    )
    _apply_fact_update(row, payload)
    _validate_retirement_timing_work_intention_other_date(row)
    db.commit()
    db.refresh(row)
    return _retirement_timing_work_intention_to_response(row)


@router.post("/{client_id}/missing-items", response_model=MissingDataItemResponse)
def create_missing_data_item(
    client_id: int,
    payload: MissingDataItemRequest,
    db: Session = Depends(get_db),
) -> MissingDataItemResponse:
    _require_client(db, client_id)
    item_type = _required_file_metadata_text(payload.missing_item_type, "Missing Item Type")
    if item_type not in {"data", "document"}:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MISSING_ITEM_TYPE_INVALID",
                "message": "Missing Item Type must be data or document",
            },
        )
    v21_fields = {
        "planning_domain",
        "related_record_type",
        "related_record_id",
        "advisory_status",
        "neutral_reason",
    }
    is_v21_creation = bool(payload.model_fields_set & v21_fields)
    if is_v21_creation:
        if payload.planning_domain is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "PLANNING_DOMAIN_REQUIRED",
                    "message": "planning_domain is required for V2.1 missing information",
                },
            )
        if payload.advisory_status is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "ADVISORY_STATUS_REQUIRED",
                    "message": "advisory_status is required for V2.1 missing information",
                },
            )
        if payload.advisory_status != "open":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "ADVISORY_STATUS_INVALID",
                    "message": 'advisory_status must equal "open" for V2.1 missing information',
                },
            )

    missing_item = MissingDataItem(
        missing_data_item_id=f"MD-{uuid4().hex}",
        client_id=client_id,
        missing_item_type=item_type,
        missing_item_label=_required_file_metadata_text(payload.missing_item_label, "Missing Item Label"),
        missing_status=_required_file_metadata_text(payload.missing_status, "Missing Status"),
        notes=payload.notes,
        planning_domain=payload.planning_domain,
        related_record_type=payload.related_record_type,
        related_record_id=payload.related_record_id,
        advisory_status=payload.advisory_status,
        neutral_reason=payload.neutral_reason,
    )
    db.add(missing_item)
    db.commit()
    db.refresh(missing_item)

    return _missing_data_item_to_response(missing_item)


@router.get("/{client_id}/missing-items", response_model=list[MissingDataItemResponse])
def list_missing_data_items(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[MissingDataItemResponse]:
    _require_client(db, client_id)
    items = db.scalars(
        select(MissingDataItem)
        .where(MissingDataItem.client_id == client_id)
        .order_by(MissingDataItem.created_at.desc(), MissingDataItem.missing_data_item_id.desc())
    ).all()

    return [_missing_data_item_to_response(row) for row in items]


@router.post("/{client_id}/employment-records", response_model=EmploymentRecordResponse)
def create_employment_record(
    client_id: int,
    payload: EmploymentRecordRequest,
    db: Session = Depends(get_db),
) -> EmploymentRecordResponse:
    _require_client(db, client_id)

    record = EmploymentRecord(
        employment_record_id=f"ER-{uuid4().hex}",
        client_id=client_id,
        employer_name=payload.employer_name,
        work_start_date=payload.work_start_date,
        work_end_date=payload.work_end_date,
        is_current=payload.is_current,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()

    return _employment_record_to_response(record)


@router.get("/{client_id}/employment-records", response_model=list[EmploymentRecordResponse])
def list_employment_records(client_id: int, db: Session = Depends(get_db)) -> list[EmploymentRecordResponse]:
    _require_client(db, client_id)
    records = db.scalars(
        select(EmploymentRecord)
        .where(EmploymentRecord.client_id == client_id)
        .order_by(EmploymentRecord.employment_record_id)
    ).all()
    return [
        _employment_record_to_response(row)
        for row in records
    ]


@router.put(
    "/{client_id}/employment-records/{employment_record_id}",
    response_model=EmploymentRecordResponse,
)
def update_employment_record(
    client_id: int,
    employment_record_id: str,
    payload: EmploymentRecordRequest,
    db: Session = Depends(get_db),
) -> EmploymentRecordResponse:
    _require_client(db, client_id)
    record = _require_employment_record(db, client_id, employment_record_id)

    record.employer_name = payload.employer_name
    record.work_start_date = payload.work_start_date
    record.work_end_date = payload.work_end_date
    record.is_current = payload.is_current
    record.notes = payload.notes
    db.commit()
    db.refresh(record)

    return _employment_record_to_response(record)


@router.delete("/{client_id}/employment-records/{employment_record_id}")
def delete_employment_record(
    client_id: int,
    employment_record_id: str,
    db: Session = Depends(get_db),
) -> dict:
    _require_client(db, client_id)
    record = _require_employment_record(db, client_id, employment_record_id)

    db.delete(record)
    db.commit()
    return {"deleted": True, "employment_record_id": employment_record_id}


@router.post("/{client_id}/grants", response_model=GrantResponse)
def create_grant(client_id: int, payload: GrantRequest, db: Session = Depends(get_db)) -> GrantResponse:
    _require_client(db, client_id)
    if payload.employment_record_id is not None:
        _require_employment_record(db, client_id, payload.employment_record_id)

    grant = Grant(
        grant_id=f"GR-{uuid4().hex}",
        client_id=client_id,
        employment_record_id=payload.employment_record_id,
        employer_name=payload.employer_name,
        nominal_amount=payload.nominal_amount,
        indexed_amount=payload.indexed_amount,
        grant_date=payload.grant_date,
        work_start_date=payload.work_start_date,
        work_end_date=payload.work_end_date,
        notes=payload.notes,
    )
    db.add(grant)
    db.commit()

    return _grant_to_response(grant)


@router.get("/{client_id}/grants", response_model=list[GrantResponse])
def list_grants(client_id: int, db: Session = Depends(get_db)) -> list[GrantResponse]:
    _require_client(db, client_id)
    grants = db.scalars(
        select(Grant).where(Grant.client_id == client_id).order_by(Grant.grant_id)
    ).all()

    return [
        _grant_to_response(row)
        for row in grants
    ]


@router.put("/{client_id}/grants/{grant_id}", response_model=GrantResponse)
def update_grant(
    client_id: int,
    grant_id: str,
    payload: GrantRequest,
    db: Session = Depends(get_db),
) -> GrantResponse:
    _require_client(db, client_id)
    grant = _require_grant(db, client_id, grant_id)
    if payload.employment_record_id is not None:
        _require_employment_record(db, client_id, payload.employment_record_id)

    grant.employment_record_id = payload.employment_record_id
    grant.employer_name = payload.employer_name
    grant.nominal_amount = payload.nominal_amount
    grant.indexed_amount = payload.indexed_amount
    grant.grant_date = payload.grant_date
    grant.work_start_date = payload.work_start_date
    grant.work_end_date = payload.work_end_date
    grant.notes = payload.notes
    db.commit()
    db.refresh(grant)

    return _grant_to_response(grant)


@router.delete("/{client_id}/grants/{grant_id}")
def delete_grant(client_id: int, grant_id: str, db: Session = Depends(get_db)) -> dict:
    _require_client(db, client_id)
    grant = _require_grant(db, client_id, grant_id)

    db.delete(grant)
    db.commit()
    return {"deleted": True, "grant_id": grant_id}


@router.post("/{client_id}/actual-capitalizations", response_model=ActualCapitalizationResponse)
def create_actual_capitalization(
    client_id: int,
    payload: ActualCapitalizationRequest,
    db: Session = Depends(get_db),
) -> ActualCapitalizationResponse:
    _require_client(db, client_id)

    cap = ActualCapitalization(
        capitalization_id=f"AC-{uuid4().hex}",
        client_id=client_id,
        amount=payload.amount,
        capitalization_date=payload.capitalization_date,
        source_label=payload.source_label,
        source_basis=payload.source_basis,
        planner_assertion=payload.planner_assertion,
        planner_assertion_basis=payload.planner_assertion_basis,
        notes=payload.notes,
    )
    db.add(cap)
    db.commit()

    return _actual_capitalization_to_response(cap)


@router.get("/{client_id}/actual-capitalizations", response_model=list[ActualCapitalizationResponse])
def list_actual_capitalizations(
    client_id: int,
    db: Session = Depends(get_db),
) -> list[ActualCapitalizationResponse]:
    _require_client(db, client_id)
    capitalizations = db.scalars(
        select(ActualCapitalization)
        .where(ActualCapitalization.client_id == client_id)
        .order_by(ActualCapitalization.capitalization_id)
    ).all()

    return [
        _actual_capitalization_to_response(row)
        for row in capitalizations
    ]


@router.put(
    "/{client_id}/actual-capitalizations/{capitalization_id}",
    response_model=ActualCapitalizationResponse,
)
def update_actual_capitalization(
    client_id: int,
    capitalization_id: str,
    payload: ActualCapitalizationRequest,
    db: Session = Depends(get_db),
) -> ActualCapitalizationResponse:
    _require_client(db, client_id)
    cap = _require_actual_capitalization(db, client_id, capitalization_id)

    cap.amount = payload.amount
    cap.capitalization_date = payload.capitalization_date
    cap.source_label = payload.source_label
    cap.source_basis = payload.source_basis
    cap.planner_assertion = payload.planner_assertion
    cap.planner_assertion_basis = payload.planner_assertion_basis
    cap.notes = payload.notes
    db.commit()
    db.refresh(cap)

    return _actual_capitalization_to_response(cap)


@router.delete("/{client_id}/actual-capitalizations/{capitalization_id}")
def delete_actual_capitalization(
    client_id: int,
    capitalization_id: str,
    db: Session = Depends(get_db),
) -> dict:
    _require_client(db, client_id)
    cap = _require_actual_capitalization(db, client_id, capitalization_id)

    db.delete(cap)
    db.commit()
    return {"deleted": True, "capitalization_id": capitalization_id}
