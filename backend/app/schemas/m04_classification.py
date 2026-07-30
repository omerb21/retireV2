from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


M04State = Literal[
    "under_review", "proposed", "accepted", "unresolved", "rejected"
]
M04ProductFamily = Literal[
    "insurance_policy",
    "savings_policy",
    "provident_fund",
    "investment_provident_fund",
    "education_fund",
    "pension_fund",
    "unknown_or_unresolved",
]
M04ComponentKind = Literal[
    "severance_component", "contribution_component", "unknown_component"
]
M04Interpretation = Literal["pension", "capital", "mixed", "unresolved"]
M04ComponentInterpretation = Literal["pension", "capital", "unresolved"]
M04EmployerRelated = Literal["yes", "no", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M04StartRequest(StrictModel):
    pass


class M04ExpectedRevisionRequest(StrictModel):
    expected_current_revision_id: str = Field(min_length=1, max_length=64)


class M04ReasonRequest(M04ExpectedRevisionRequest):
    reason_code: str = Field(min_length=1, max_length=128)
    explanation: str = Field(min_length=1, max_length=4096)

    @field_validator("reason_code", "explanation")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace characters")
        return normalized


class M04ConfirmedReasonRequest(M04ReasonRequest):
    confirmed: Literal[True]


class M04OverrideComponentInput(StrictModel):
    evidence_identity: str = Field(min_length=1, max_length=255)
    component_kind: M04ComponentKind
    interpretation: M04ComponentInterpretation
    current_employer_related: M04EmployerRelated = "unknown"
    explanation: str = Field(min_length=1, max_length=4096)

    @field_validator("evidence_identity", "explanation")
    @classmethod
    def normalize_component_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace characters")
        return normalized


class M04OverrideRequest(M04ConfirmedReasonRequest):
    product_family: M04ProductFamily
    pension_subtype: str | None = Field(default=None, max_length=128)
    components: list[M04OverrideComponentInput]

    @field_validator("pension_subtype")
    @classmethod
    def normalize_subtype(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class M04UndoRequest(M04ConfirmedReasonRequest):
    historical_revision_id: str = Field(min_length=1, max_length=64)


class M04ComponentResponse(BaseModel):
    component_decision_id: str
    evidence_identity: str
    original_label: str | None
    original_code: str | None
    component_kind: M04ComponentKind
    interpretation: M04ComponentInterpretation
    matched_rule_evidence: list[dict[str, Any]]
    explanation: str
    current_employer_related: M04EmployerRelated


class M04RevisionResponse(BaseModel):
    revision_id: str
    revision_sequence: int
    predecessor_revision_id: str | None
    historical_revision_id: str | None
    state: M04State
    action_type: Literal[
        "start",
        "proposal",
        "unresolved",
        "accept",
        "reject",
        "reopen",
        "override",
        "undo",
        "start_revalidation",
    ]
    product_family: M04ProductFamily | None
    pension_subtype: str | None
    aggregate_interpretation: M04Interpretation | None
    explanation: str | None
    reason_code: str | None
    reason: str | None
    catalogue_version: Literal["m04-rules-v1"]
    matched_rule_evidence: list[dict[str, Any]]
    match_basis: str
    action_evidence: dict[str, Any]
    input_snapshot: dict[str, Any]
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime
    components: list[M04ComponentResponse]


class M04RulePreviewResponse(BaseModel):
    catalogue_version: Literal["m04-rules-v1"]
    product_family: M04ProductFamily
    aggregate_interpretation: M04Interpretation
    components: list[M04ComponentResponse]
    matched_rule_evidence: list[dict[str, Any]]
    conflicts: list[str]
    unresolved_reasons: list[str]
    persists_revision: Literal[False] = False


class M04EligibilityResponse(BaseModel):
    eligible_for_m05: bool
    exclusion_reason: str | None
    current_revision_id: str | None
    accepted_revision_id: str | None
    m03_revision_id: str | None
    meaning: Literal[
        "accepted resolved M04 classification may be consumed only by a separately authorized M05 package"
    ] = (
        "accepted resolved M04 classification may be consumed only by a "
        "separately authorized M05 package"
    )


class M04TargetResponse(BaseModel):
    client_id: int
    intake_id: str
    target_kind: Literal["source_evidence_review", "manual_record_review"]
    record_kind: Literal["manual", "uploaded_source"]
    m01_lifecycle_status: str
    m02_lifecycle_status: str
    m03_eligible: bool
    m03_exclusion_reason: str | None
    m03_accepted_revision_id: str | None
    source_id: str | None
    declared_provider_name: str | None
    product_name: str | None
    declared_product_type: str | None
    product_identifier: str | None
    declared_account_reference: str | None
    declared_component_values: list[dict[str, Any]]
    current_revision: M04RevisionResponse | None
    eligibility: M04EligibilityResponse
