from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CollectionState = Literal[
    "recorded",
    "confirmed_none",
    "unknown",
    "not_collected",
    "unresolved",
    "not_applicable",
]
VerificationState = Literal[
    "unverified",
    "partly_verified",
    "verified",
    "planner_asserted",
    "source_conflict",
    "rejected",
    "superseded",
]
FindingKind = Literal[
    "missing_required_field",
    "not_collected",
    "unknown",
    "unresolved",
    "source_conflict",
    "rejected_evidence",
    "confirmed_none",
    "not_applicable",
    "incompatible_evidence",
    "technical_warning",
    "technical_rule_outcome",
]


class M07Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RevisionDraftCreate(M07Command):
    profile_id: str = Field(min_length=1, max_length=64)
    tax_year: int = Field(ge=1900, le=9999)
    event_year: int = Field(ge=1900, le=9999)
    event_type: str | None = Field(default=None, max_length=64)
    event_id: str | None = Field(default=None, max_length=64)
    schema_version: str = Field(min_length=1, max_length=64)
    rule_version: str = Field(min_length=1, max_length=64)


class FactEvidenceWrite(M07Command):
    fact_evidence_id: str | None = Field(default=None, max_length=64)
    field_code: str = Field(min_length=1, max_length=128)
    structured_value: Any | None = None
    collection_state: CollectionState
    collection_basis: str | None = None
    verification_state: VerificationState = "unverified"
    source_type: str | None = Field(default=None, max_length=64)
    source_record_type: str | None = Field(default=None, max_length=64)
    source_record_id: str | None = Field(default=None, max_length=128)
    source_document_reference: str | None = Field(default=None, max_length=512)
    source_date: date | None = None
    source_excerpt: str | None = Field(default=None, max_length=2048)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    collection_actor: str = Field(min_length=1, max_length=128)
    verification_actor: str | None = Field(default=None, max_length=128)
    verification_basis: str | None = None
    assertion_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_evidence_state(self) -> "FactEvidenceWrite":
        if self.collection_state == "recorded" and self.structured_value is None:
            raise ValueError("recorded evidence requires a structured value")
        if self.collection_state in {"confirmed_none", "not_applicable"} and not self.collection_basis:
            raise ValueError(f"{self.collection_state} requires a collection basis")
        if self.verification_state in {"verified", "partly_verified"}:
            if not self.verification_actor or not self.verification_basis:
                raise ValueError("verified evidence requires actor and basis")
        if self.verification_state == "planner_asserted" and not self.assertion_id:
            raise ValueError("planner_asserted evidence requires an assertion reference")
        return self


class PlannerAssertionAppend(M07Command):
    field_code: str = Field(min_length=1, max_length=128)
    asserted_value: Any
    assertion_basis: str = Field(min_length=1)
    assertion_reason: str = Field(min_length=1)
    source_note: str | None = Field(default=None, max_length=2048)
    predecessor_assertion_id: str | None = Field(default=None, max_length=64)


class AssessmentFindingWrite(M07Command):
    finding_id: str | None = Field(default=None, max_length=64)
    finding_kind: FindingKind
    finding_code: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=128)
    field_references: list[str] = Field(default_factory=list)
    fact_references: list[str] = Field(default_factory=list)
    assertion_references: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)
    technical_blocking_effect: bool = False


class AssessmentRun(M07Command):
    required_field_codes: list[str] = Field(default_factory=list)
    rule_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_required_fields(self) -> "AssessmentRun":
        if len(self.required_field_codes) != len(set(self.required_field_codes)):
            raise ValueError("required field codes must be unique")
        return self
