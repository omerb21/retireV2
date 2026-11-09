"""Strictly structured planner assertions, NOT evidence admission or tax approval."""
from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.fixation_contracts import IDFInput


SUPPORTED_SCENARIO_FIXATION_CALCULATION_VERSIONS = ("pkg-012-m08d-v1",)


class FixationCollectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["unknown", "not_collected", "confirmed_none", "items_recorded"]
    evidence_references: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def confirmed_none_requires_evidence(self):
        if self.state == "confirmed_none" and not self.evidence_references:
            raise ValueError("FIXATION_CONFIRMED_NONE_EVIDENCE_REQUIRED")
        return self


class FixationIDFDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    applicability: Literal["NOT_REVIEWED", "NOT_APPLICABLE", "APPLICABLE"]
    evidence_references: list[str] = Field(default_factory=list, max_length=32)
    input: IDFInput | None = None

    @model_validator(mode="after")
    def closed_shape(self):
        if self.applicability == "NOT_REVIEWED" and (self.evidence_references or self.input):
            raise ValueError("FIXATION_IDF_NOT_REVIEWED_MUST_BE_EMPTY")
        if self.applicability == "NOT_APPLICABLE" and (not self.evidence_references or self.input):
            raise ValueError("FIXATION_IDF_NOT_APPLICABLE_EVIDENCE_REQUIRED")
        if self.applicability == "APPLICABLE" and (not self.evidence_references or self.input is None):
            raise ValueError("FIXATION_IDF_INPUT_REQUIRED")
        return self


class FixationAdmissionControls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calculation_version: Literal["pkg-012-m08d-v1"]
    grants_collection: FixationCollectionDecision
    actual_capitalizations_collection: FixationCollectionDecision
    idf: FixationIDFDecision


class FixationProfessionalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: Literal[
        "eligibility", "tax_year_and_parameters", "pension_classification",
        "historical_grant", "severance_continuity",
        "historical_capitalization", "planned_withdrawal_or_commutation",
    ]
    source_id: str = Field(min_length=1, max_length=128)
    determination: Literal["REQUIRES_REVIEW", "PLANNER_ASSERTED", "EXCLUDE_PROPOSED"]
    reason: str = Field(min_length=1, max_length=2048)
    evidence_references: list[str] = Field(default_factory=list, max_length=32)
    # Optional recorded assertions; neither is automatically an admitted fact.
    eligibility_date: date | None = None
    tax_year: int | None = Field(default=None, ge=1900, le=2200)
    parameter_set_id: str | None = Field(default=None, max_length=64)
    tax_classification: Literal[
        "QUALIFYING_PENSION_FOR_FIXATION", "NON_QUALIFYING_PENSION_FOR_FIXATION"
    ] | None = None
    inclusion_decision: Literal["include", "exclude"] | None = None
    support_status: Literal["supported", "unsupported", "requires_special_handling"] | None = None
    accepted_for_use: bool | None = None
    payment_status: Literal["PAID", "NOT_PAID", "UNKNOWN"] | None = None
    overlap_resolution: Literal[
        "NO_OVERLAP", "SAME_RIGHT_USE_GRANT", "SAME_RIGHT_USE_COMPONENT", "DISTINCT_RIGHTS"
    ] | None = None
    matched_source_ids: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("evidence_references")
    @classmethod
    def nonempty_unique_references(cls, refs: list[str]) -> list[str]:
        if any(not isinstance(x, str) or not x.strip() or len(x) > 256 for x in refs):
            raise ValueError("FIXATION_REVIEW_EVIDENCE_REFERENCE_INVALID")
        if len(refs) != len(set(refs)):
            raise ValueError("FIXATION_REVIEW_EVIDENCE_DUPLICATE")
        return refs

    @model_validator(mode="after")
    def restrict_fields(self):
        if self.eligibility_date is not None and self.group != "eligibility":
            raise ValueError("FIXATION_REVIEW_ELIGIBILITY_GROUP_REQUIRED")
        if ((self.tax_year is not None or self.parameter_set_id is not None)
                and self.group != "tax_year_and_parameters"):
            raise ValueError("FIXATION_REVIEW_TAX_PARAMETER_GROUP_REQUIRED")
        if self.tax_classification is not None and self.group != "pension_classification":
            raise ValueError("FIXATION_REVIEW_PENSION_GROUP_REQUIRED")
        item_groups = {"historical_grant", "historical_capitalization",
                       "planned_withdrawal_or_commutation"}
        structured = (self.inclusion_decision, self.support_status, self.accepted_for_use)
        if any(value is not None for value in structured) and self.group not in item_groups:
            raise ValueError("FIXATION_REVIEW_ITEM_GROUP_REQUIRED")
        if self.payment_status is not None and self.group != "historical_grant":
            raise ValueError("FIXATION_REVIEW_GRANT_GROUP_REQUIRED")
        if (self.overlap_resolution is not None or self.matched_source_ids) and self.group not in {
                "historical_grant", "severance_continuity"}:
            raise ValueError("FIXATION_REVIEW_OVERLAP_GROUP_REQUIRED")
        return self


class FixationProfessionalDraftReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_approval_version: int = Field(ge=0)
    expected_scenario_version: int = Field(gt=0)
    expected_manifest_fingerprint: str = Field(min_length=64, max_length=64)
    expected_readiness_fingerprint: str = Field(min_length=64, max_length=64)
    decisions: list[FixationProfessionalDecision] = Field(max_length=200)
    admission_controls: FixationAdmissionControls | None = None

    @model_validator(mode="after")
    def unique_keys(self):
        keys = [(x.group, x.source_id) for x in self.decisions]
        if len(keys) != len(set(keys)):
            raise ValueError("FIXATION_REVIEW_DUPLICATE_DECISION")
        return self


class FixationProfessionalApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_approval_version: int = Field(gt=0)
    expected_approval_fingerprint: str = Field(min_length=64, max_length=64)
