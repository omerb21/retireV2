from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M03ReasonRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=4096)
    expected_current_revision_id: str = Field(min_length=1, max_length=64)

    @field_validator("reason")
    @classmethod
    def normalize_required_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must contain non-whitespace characters")
        return normalized


class M03RevisionResponse(BaseModel):
    revision_id: str
    revision_sequence: int
    predecessor_revision_id: str | None
    state: Literal["under_review", "accepted", "rejected"]
    reason: str | None
    actor: str
    actor_is_authentication: Literal[False] = False
    decided_at: datetime


class M03AnnotationRequest(StrictModel):
    review_revision_id: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=255)
    note: str = Field(min_length=1, max_length=4096)
    reason: str = Field(min_length=1, max_length=4096)
    supersedes_annotation_id: str | None = Field(default=None, max_length=64)

    @field_validator("topic", "note", "reason")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace characters")
        return normalized


class M03AnnotationResponse(BaseModel):
    annotation_id: str
    review_revision_id: str
    intake_id: str
    source_id: str | None
    topic: str
    note: str
    reason: str
    actor: str
    actor_is_authentication: Literal[False] = False
    supersedes_annotation_id: str | None
    created_at: datetime


class M03TargetResponse(BaseModel):
    client_id: int
    intake_id: str
    target_kind: Literal["source_evidence_review", "manual_record_review"]
    m02_lifecycle_status: str
    source_id: str | None
    blob_id: str | None
    sha256_checksum: str | None
    current_revision: M03RevisionResponse | None
    accepted_revision_id: str | None
    eligible: bool
    exclusion_reason: str | None
    eligibility_meaning: Literal[
        "reviewed evidence may be consumed by a separately authorized downstream transformation"
    ] = "reviewed evidence may be consumed by a separately authorized downstream transformation"
