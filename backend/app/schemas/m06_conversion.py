from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
Mode = Literal["balance_to_monthly_pension", "monthly_pension_to_capital_equivalent"]
Authority = Literal["documentary", "planner_declared"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M06CoefficientMetadata(StrictModel):
    source_date: date | None = None
    source_version: str | None = Field(default=None, min_length=1, max_length=255)
    issuer_provider: str | None = Field(default=None, min_length=1, max_length=255)
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = Field(default=None, min_length=1, max_length=64)
    pension_option: str | None = Field(default=None, min_length=1, max_length=255)
    guarantee_period: str | None = Field(default=None, min_length=1, max_length=255)
    survivor_option: str | None = Field(default=None, min_length=1, max_length=255)


class M06CoefficientIntent(StrictModel):
    authority_class: Authority
    coefficient: Any = None
    source_intake_id: str | None = Field(default=None, min_length=1, max_length=64)
    source_locator: str | None = Field(default=None, min_length=1, max_length=4096)
    source_note: str | None = Field(default=None, min_length=1, max_length=4096)
    reason: str = Field(min_length=1, max_length=4096)
    effective_from: date | None = None
    effective_to: date | None = None
    applicability_declared: bool = False
    metadata: M06CoefficientMetadata = Field(default_factory=M06CoefficientMetadata)

    @field_validator("reason", "source_locator", "source_note")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must contain non-whitespace characters")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def authority_shape(self):
        if self.authority_class == "documentary":
            if not self.source_intake_id or not (
                self.source_locator or self.source_note
            ):
                raise ValueError(
                    "documentary evidence requires source_intake_id and a precise locator or source note"
                )
        elif not self.source_note or not self.applicability_declared:
            raise ValueError(
                "planner declaration requires source_note and applicability_declared"
            )
        return self


class M06StartRequest(StrictModel):
    m05_subject_id: str = Field(min_length=1, max_length=64)
    mode: Mode
    input_identity: str = Field(min_length=1, max_length=255)
    coefficient: M06CoefficientIntent


class M06ExpectedRevision(StrictModel):
    expected_current_revision_id: str = Field(min_length=1, max_length=64)


class M06ResolveRequest(M06ExpectedRevision):
    pass


class M06WarningReviewRequest(M06ExpectedRevision):
    warning_ids: list[str]
    reason_code: str = Field(min_length=1, max_length=128)
    explanation: str = Field(min_length=1, max_length=4096)
    confirmed: Literal[True]


class M06CoefficientCorrectionRequest(M06ExpectedRevision):
    coefficient: M06CoefficientIntent
    correction_reason: str = Field(min_length=1, max_length=4096)


class M06SupersedeRequest(M06ExpectedRevision):
    reason: str = Field(min_length=1, max_length=4096)


class M06CandidateResponse(BaseModel):
    candidate_id: str
    m05_subject_id: str
    m05_revision_id: str
    m02_intake_id: str
    provider_name: str
    account_reference: str
    product_family: str
    mode: Mode
    input_identity: str
    input_amount: str | None
    input_date: date | None
    formula_id: str
    eligible: bool
    exclusion_reasons: list[str]
    informational_warnings: list[str]


class M06CoefficientResponse(BaseModel):
    evidence_id: str
    authority_class: Authority
    coefficient: str
    decimal_precision: int
    decimal_exponent: int
    source_intake_id: str | None
    source_locator: str | None
    source_note: str | None
    reason: str
    effective_from: date | None
    effective_to: date | None
    applicability_declared: bool
    metadata: dict[str, Any]
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M06ManifestResponse(BaseModel):
    manifest_id: str
    fingerprint: str
    raw_result_kind: str | None
    raw_decimal: str | None
    raw_numerator: str | None
    raw_denominator: str | None
    display_result: str | None
    evidence: dict[str, Any]


class M06RevisionResponse(BaseModel):
    revision_id: str
    subject_id: str
    predecessor_revision_id: str | None
    revision_sequence: int
    state: Literal["draft", "resolved", "warning_reviewed", "blocked", "superseded"]
    action_type: str
    mode: Mode
    formula_id: str
    input_identity: str
    input_amount: str | None
    input_date: date | None
    predecessor_snapshot: dict[str, Any]
    warnings: list[dict[str, Any]]
    blocking_reasons: list[str]
    informational_warnings: list[str]
    coefficient: M06CoefficientResponse
    manifest: M06ManifestResponse | None
    warning_dispositions: list[dict[str, Any]]
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M06EligibilityResponse(BaseModel):
    subject_id: str
    eligible_for_downstream: bool
    current_revision_id: str | None
    exclusion_reasons: list[str]
    informational_warnings: list[str]
    meaning: Literal["technically eligible under the bounded PKG-011 M06 contract"] = (
        "technically eligible under the bounded PKG-011 M06 contract"
    )


class M06SubjectResponse(BaseModel):
    subject_id: str
    client_id: int
    m05_subject_id: str
    mode: Mode
    input_identity: str
    current_revision: M06RevisionResponse | None
    eligibility: M06EligibilityResponse
