from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator(
        "profile_id", "event_type", "event_id", "schema_version", "rule_version"
    )
    @classmethod
    def reject_blank_identifiers(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be blank")
        return value


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
    verification_basis: str | None = None
    assertion_id: str | None = Field(default=None, max_length=64)

    @field_validator(
        "field_code",
        "source_type",
        "source_record_type",
        "source_record_id",
        "source_document_reference",
        "source_excerpt",
        "collection_basis",
        "verification_basis",
        "assertion_id",
    )
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("text evidence fields must not be blank")
        return value

    @model_validator(mode="after")
    def validate_evidence_state(self) -> "FactEvidenceWrite":
        if self.collection_state == "recorded" and self.structured_value is None:
            raise ValueError("recorded evidence requires a structured value")
        if self.collection_state in {"confirmed_none", "not_applicable"} and not self.collection_basis:
            raise ValueError(f"{self.collection_state} requires a collection basis")
        if self.verification_state in {"verified", "partly_verified"}:
            if not self.verification_basis:
                raise ValueError("verified evidence requires a basis")
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

    @field_validator(
        "field_code",
        "assertion_basis",
        "assertion_reason",
        "source_note",
        "predecessor_assertion_id",
    )
    @classmethod
    def reject_blank_assertion_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("assertion text must not be blank")
        return value

    @field_validator("asserted_value")
    @classmethod
    def reject_empty_asserted_value(cls, value: Any) -> Any:
        if value == {} or isinstance(value, str) and not value.strip():
            raise ValueError("asserted value must convey evidence")
        return value


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
    @field_validator("finding_code", "category", "description")
    @classmethod
    def reject_blank_finding_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("finding text must not be blank")
        return value

    @field_validator(
        "field_references",
        "fact_references",
        "assertion_references",
        "source_references",
    )
    @classmethod
    def reject_blank_references(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("finding references must not be blank")
        return values


class AssessmentRun(M07Command):
    """A narrow request to run the server-owned manifest for the revision."""
