"""Strictly structured planner assertions, NOT evidence admission or tax approval."""
from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    tax_classification: str | None = Field(default=None, max_length=128)

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
        return self


class FixationProfessionalDraftReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_approval_version: int = Field(ge=0)
    expected_scenario_version: int = Field(gt=0)
    expected_manifest_fingerprint: str = Field(min_length=64, max_length=64)
    expected_readiness_fingerprint: str = Field(min_length=64, max_length=64)
    decisions: list[FixationProfessionalDecision] = Field(max_length=200)

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
