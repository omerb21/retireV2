from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MONEY_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M05StartRequest(StrictModel):
    candidate_id: str = Field(min_length=1, max_length=72)
    confirm_currency_ils: Literal[True] | None = None


class M05ExpectedRevisionRequest(StrictModel):
    expected_current_revision_id: str = Field(min_length=1, max_length=64)


class M05ReasonRequest(M05ExpectedRevisionRequest):
    reason_code: str = Field(min_length=1, max_length=128)
    explanation: str = Field(min_length=1, max_length=4096)

    @field_validator("reason_code", "explanation")
    @classmethod
    def required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace characters")
        return normalized


class M05ReconcileRequest(M05ExpectedRevisionRequest):
    confirm_currency_ils: Literal[True] | None = None


class M05ReviewWarningRequest(M05ReasonRequest):
    mandatory_warning_ids: list[str]
    confirmed: Literal[True]
    confirm_currency_ils: Literal[True] | None = None


class M05AdjustmentRequest(M05ReasonRequest):
    evidence_identity: str = Field(min_length=1, max_length=255)
    new_effective_value: str = Field(min_length=1, max_length=32)
    confirmed: Literal[True]

    @field_validator("evidence_identity")
    @classmethod
    def exact_identity(cls, value: str) -> str:
        if not value:
            raise ValueError("evidence identity is required")
        return value

    @field_validator("new_effective_value", mode="before")
    @classmethod
    def strict_money(cls, value: Any) -> str:
        if not isinstance(value, str) or MONEY_PATTERN.fullmatch(value) is None:
            raise ValueError("value must be a plain scale-2 decimal string")
        return value


class M05RevalidateRequest(M05ReasonRequest):
    candidate_id: str = Field(min_length=1, max_length=72)


class M05CandidateResponse(BaseModel):
    candidate_id: str
    intake_id: str
    target_kind: Literal["manual_record_review"]
    provider_name: str | None
    account_reference: str | None
    product_context: dict[str, Any]
    statement_date: date | None
    m03_revision_id: str | None
    m04_revision_id: str | None
    eligible: bool
    authoritative_current: bool
    exclusion_reason: str | None
    informational_warnings: list[str]
    subject_id: str | None


class M05ValueResponse(BaseModel):
    value_id: str
    evidence_identity: str
    component_index: int | None
    original_label: str | None
    original_code: str | None
    component_kind: Literal[
        "total_balance",
        "contribution_component",
        "severance_component",
        "unknown_component",
    ]
    source_state: str
    source_value: Decimal | None
    effective_state: str
    effective_value: Decimal | None
    included_in_reconciliation: bool
    exclusion_reason: str | None


class M05AdjustmentResponse(BaseModel):
    adjustment_id: str
    evidence_identity: str
    previous_effective_value: Decimal
    new_effective_value: Decimal
    reason_code: str
    explanation: str
    confirmed: bool
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M05RevisionResponse(BaseModel):
    revision_id: str
    subject_id: str
    candidate_id: str
    intake_id: str
    target_kind: Literal["manual_record_review"]
    m03_revision_id: str
    m04_revision_id: str
    predecessor_revision_id: str | None
    revision_sequence: int
    state: Literal["draft", "reconciled", "warning_reviewed", "blocked", "superseded"]
    action_type: Literal[
        "start", "reconcile", "review_warning", "mark_blocked", "adjust",
        "supersede", "revalidate",
    ]
    provider_name: str
    account_reference: str
    product_context: dict[str, Any]
    statement_date: date
    evaluation_date: date
    is_stale: bool
    source_snapshot_digest: str
    mapping_digest: str
    currency: Literal["ILS"]
    currency_confirmed: bool
    currency_confirmation_evidence: dict[str, Any]
    source_total_state: str
    source_total_value: Decimal | None
    effective_total_state: str
    effective_total_value: Decimal | None
    signed_discrepancy: Decimal | None
    absolute_discrepancy: Decimal | None
    tolerance_satisfied: bool | None
    algorithm_version: Literal["m05-reconciliation-v1"]
    included_evidence: list[dict[str, Any]]
    excluded_evidence: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    warning_dispositions: list[dict[str, Any]]
    provenance: dict[str, Any]
    reason_code: str | None
    explanation: str | None
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime
    values: list[M05ValueResponse]
    adjustment: M05AdjustmentResponse | None


class M05EligibilityResponse(BaseModel):
    subject_id: str
    eligible_for_m06: bool
    current_revision_id: str | None
    exclusion_reasons: list[str]
    informational_warnings: list[str]
    meaning: Literal[
        "technically eligible for consumption by a separately authorized M06 package"
    ] = "technically eligible for consumption by a separately authorized M06 package"


class M05SubjectResponse(BaseModel):
    subject_id: str
    client_id: int
    provider_name: str
    account_reference: str
    current_revision: M05RevisionResponse | None
    eligibility: M05EligibilityResponse
