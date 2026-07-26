from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ResolutionOutcome = Literal[
    "resolved",
    "missing_inputs",
    "ambiguous_inputs",
]


class CalculationInputResolutionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalculationInputSelection(CalculationInputResolutionCommand):
    field_code: str = Field(min_length=1, max_length=128)
    candidate_identity: str | None = Field(default=None, max_length=160)
    selected_normalized_value: Any | None = None
    b1_evidence_revision_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def require_one_selection_identity(self) -> "CalculationInputSelection":
        normalized_supplied = (
            "selected_normalized_value" in self.model_fields_set
        )
        if (self.candidate_identity is not None) == normalized_supplied:
            raise ValueError(
                "selection requires exactly one candidate identity or "
                "normalized value"
            )
        return self


class CalculationInputResolutionRequest(CalculationInputResolutionCommand):
    calculation_scope: str = Field(min_length=1, max_length=128)
    manifest_version: str = Field(min_length=1, max_length=128)
    b1_evidence_revision_id: str = Field(min_length=1, max_length=64)
    selections: list[CalculationInputSelection] = Field(default_factory=list)


class CalculationInputSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_kind: Literal["fact_evidence", "planner_assertion"]
    source_id: str
    source_type: str | None = None
    source_record_type: str | None = None
    source_record_id: str | None = None
    source_document_reference: str | None = None
    assertion_id: str | None = None


class AmbiguousInputCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    normalized_value: Any
    candidate_identities: list[str]
    source_references: list[CalculationInputSourceReference]


class AmbiguousInputField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_code: str
    candidates: list[AmbiguousInputCandidate]


class CalculationReadyInputPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: int
    calculation_scope: str
    manifest_version: str
    b1_evidence_revision_id: str
    normalized_selected_values: dict[str, Any]
    source_references: dict[str, list[CalculationInputSourceReference]]
    resolution_fingerprint: str


class CalculationInputResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: int
    calculation_scope: str
    manifest_version: str
    b1_evidence_revision_id: str
    normalized_selected_values: dict[str, Any]
    source_references: dict[str, list[CalculationInputSourceReference]]
    missing_fields: list[str]
    ambiguous_fields: list[AmbiguousInputField]
    outcome: ResolutionOutcome
    canonical_result: dict[str, Any]
    fingerprint: str
    calculation_payload: CalculationReadyInputPayload | None
