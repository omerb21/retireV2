from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)


OFFICIAL_PARAMETER_SCHEMA_VERSION = "pkg004a.official-parameter-set.v1"
OFFICIAL_PARAMETER_FINGERPRINT_ALGORITHM = "sha256-canonical-json-v1"
OFFICIAL_PARAMETER_RESOLVER_VERSION = "pkg004a.official-parameter-resolver.v1"

OfficialParameterStatus = Literal["draft", "verified", "active", "superseded", "rejected"]
OfficialParameterResolutionStatus = Literal["resolved", "unavailable", "ambiguous"]


def _non_empty(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    return value


class OfficialParameterValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_cap: Decimal
    exemption_percentage: Decimal
    capital_multiplier: Decimal
    grant_impact_multiplier: Decimal

    @field_validator("monthly_cap", "capital_multiplier", "grant_impact_multiplier")
    @classmethod
    def validate_positive(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("parameter value must be finite and > 0")
        return value

    @field_validator("exemption_percentage")
    @classmethod
    def validate_percentage(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0 or value > 1:
            raise ValueError("exemption_percentage must be finite and between 0 and 1")
        return value


class OfficialParameterSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_set_id: str | None = Field(default=None, max_length=64)
    tax_year: int = Field(ge=1900, le=9999)
    effective_from: date
    effective_to: date | None = None
    parameter_set_version: str = Field(max_length=64)
    values: OfficialParameterValues
    source_type: str = Field(max_length=64)
    source_title: str = Field(max_length=512)
    official_source_reference: str = Field(max_length=2048)
    source_publication_date: date | None = None
    source_recorded_at: datetime | None = None
    source_evidence_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_by: str = Field(max_length=128)
    schema_version: Literal["pkg004a.official-parameter-set.v1"] = (
        OFFICIAL_PARAMETER_SCHEMA_VERSION
    )

    @field_validator(
        "parameter_set_id",
        "parameter_set_version",
        "source_type",
        "source_title",
        "official_source_reference",
        "created_by",
    )
    @classmethod
    def validate_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _non_empty(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_period(self) -> "OfficialParameterSetCreate":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not be before effective_from")
        return self


class OfficialParameterVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_by: str = Field(max_length=128)
    verification_note: str | None = Field(default=None, max_length=4000)

    @field_validator("verified_by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _non_empty(value, "verified_by")


class OfficialParameterActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activated_by: str = Field(max_length=128)

    @field_validator("activated_by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _non_empty(value, "activated_by")


class OfficialParameterRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejected_by: str = Field(max_length=128)
    rejection_note: str = Field(max_length=4000)

    @field_validator("rejected_by", "rejection_note")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))


class OfficialParameterSupersessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    superseded_by: str = Field(max_length=128)

    @field_validator("superseded_by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _non_empty(value, "superseded_by")


class OfficialParameterSetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    parameter_set_id: str
    tax_year: int
    effective_from: date
    effective_to: date | None
    schema_version: str
    parameter_set_version: str
    status: OfficialParameterStatus
    values: OfficialParameterValues
    source_type: str
    source_title: str
    official_source_reference: str
    source_publication_date: date | None
    source_recorded_at: datetime
    source_evidence_metadata: dict[str, Any]
    verification_note: str | None
    content_fingerprint: str
    fingerprint_algorithm_version: str
    created_at: datetime
    created_by: str
    verified_at: datetime | None
    verified_by: str | None
    activated_at: datetime | None
    activated_by: str | None
    rejected_at: datetime | None
    rejected_by: str | None
    rejection_note: str | None
    superseded_at: datetime | None
    superseded_by: str | None


class OfficialParameterEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    source_title: str
    official_source_reference: str
    source_publication_date: date | None
    source_recorded_at: datetime
    content_fingerprint: str
    fingerprint_algorithm_version: str


class OfficialParameterResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: OfficialParameterResolutionStatus
    requested_tax_year: int
    requested_effective_date: date
    selected_parameter_set_id: str | None = None
    values: OfficialParameterValues | None = None
    evidence: OfficialParameterEvidenceSummary | None = None
    parameter_set_version: str | None = None
    schema_version: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    resolution_timestamp: datetime
    resolver_contract_version: Literal["pkg004a.official-parameter-resolver.v1"] = (
        OFFICIAL_PARAMETER_RESOLVER_VERSION
    )


class OfficialParameterAdmissionContext(BaseModel):
    """Response-only mapping for a future server-side admission integration."""

    model_config = ConfigDict(extra="forbid")

    parameter_set_id: str
    tax_year: int
    effective_from: date
    effective_to: date | None
    values: OfficialParameterValues
    source_basis: str
    schema_version: str
    parameter_set_version: str
    content_fingerprint: str
    resolver_contract_version: str
