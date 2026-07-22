from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.cbs_indexation import (
    CbsIndexationFailureEvidence,
    CbsIndexationResponseEvidence,
    IndexationBaseDateSource,
)
from app.schemas.fixation_admissibility import M07QualificationWarning


MANIFEST_SCHEMA_VERSION = "pkg003.fixation-dependency-manifest.v1"
FINGERPRINT_ALGORITHM_VERSION = "sha256-canonical-json-v1"
FINGERPRINT_SCHEMA_VERSION = "pkg003.dependency-content.v1"
COMPARISON_ALGORITHM_VERSION = "pkg003.dependency-comparison.v1"
CBS_ADAPTER_CONTRACT_VERSION = "pkg002.cbs-indexation-adapter.v1"

AvailabilityState = Literal["available", "unavailable", "not_applicable"]
TechnicalComparisonResult = Literal["unchanged", "changed", "unknown"]


class ManifestContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class M07DependencyContent(ManifestContract):
    profile_id: str
    state: str
    qualification_trace_id: str | None
    warnings: list[M07QualificationWarning] | None
    review_reason: str | None
    reviewed_by: str | None
    review_timestamp: datetime | None


class CalculationContextDependencyContent(ManifestContract):
    eligibility_date: date
    eligibility_year: int
    calculation_version: str
    input_contract_version: str
    result_contract_version: str | None
    manifest_schema_version: Literal["pkg003.fixation-dependency-manifest.v1"] = (
        MANIFEST_SCHEMA_VERSION
    )
    fingerprint_algorithm_version: Literal["sha256-canonical-json-v1"] = (
        FINGERPRINT_ALGORITHM_VERSION
    )
    fingerprint_schema_version: Literal["pkg003.dependency-content.v1"] = (
        FINGERPRINT_SCHEMA_VERSION
    )
    comparison_algorithm_version: Literal["pkg003.dependency-comparison.v1"] = (
        COMPARISON_ALGORITHM_VERSION
    )


class ParameterValuesContent(ManifestContract):
    monthly_cap: Decimal
    exemption_percentage: Decimal
    capital_multiplier: Decimal
    grant_impact_multiplier: Decimal


class ParameterDependencyContent(ManifestContract):
    parameter_set_id: str
    tax_year: int
    effective_from: date | None
    effective_to: date | None
    values: ParameterValuesContent
    source_basis: str
    status: str
    accepted_for_use: bool
    accepted_by: str
    decision_timestamp: datetime


class GrantDependencyContent(ManifestContract):
    grant_id: str
    client_id: int
    nominal_amount: Decimal | None
    indexed_amount: Decimal | None
    asserted_indexed_amount: Decimal | None
    system_calculated_amount: Decimal | None
    selected_calculation_amount: Decimal | None
    grant_date: date
    work_start_date: date
    work_end_date: date
    inclusion_decision: str
    support_status: str
    accepted_for_use: bool
    source_basis: str
    status: str
    actor: str
    decision_timestamp: datetime
    conflict_indicator: bool
    accepted_value: Decimal | None
    indexation_mode: str
    cbs_dependency_identity: str | None


class CapitalizationDependencyContent(ManifestContract):
    capitalization_id: str
    amount: Decimal
    capitalization_date: date
    recorded_meaning: str
    inclusion_decision: str
    accepted_for_use: bool
    support_status: str
    source_basis: str
    status: str
    actor: str
    decision_timestamp: datetime
    conflict_indicator: bool
    accepted_value: Decimal | None


class FutureReserveDependencyContent(ManifestContract):
    amount: Decimal
    source_basis: str
    status: str
    accepted_for_use: bool
    actor: str
    decision_timestamp: datetime


class CbsDependencyContent(ManifestContract):
    grant_id: str
    cpi_code: str | None
    endpoint: str | None
    request_amount: Decimal | None
    resolved_base_date: date | None
    base_date_source: IndexationBaseDateSource | None
    target_date: date | None
    raw_official_value: Decimal | None
    rounded_application_value: Decimal | None
    response_evidence: CbsIndexationResponseEvidence | None
    calculation_timestamp: datetime | None
    missing_optional_fields: list[str]
    failure_evidence: CbsIndexationFailureEvidence | None
    adapter_contract_version: Literal["pkg002.cbs-indexation-adapter.v1"] = (
        CBS_ADAPTER_CONTRACT_VERSION
    )


class DependencyEntryBase(ManifestContract):
    stable_identity: str | None
    availability_state: AvailabilityState
    fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    fingerprint_algorithm: Literal["sha256-canonical-json-v1"] = FINGERPRINT_ALGORITHM_VERSION
    fingerprint_schema_version: Literal["pkg003.dependency-content.v1"] = (
        FINGERPRINT_SCHEMA_VERSION
    )
    reason_codes: list[str] = Field(default_factory=list)


class M07DependencyEntry(DependencyEntryBase):
    dependency_type: Literal["m07"] = "m07"
    canonical_content: M07DependencyContent | None


class CalculationContextDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["calculation_context"] = "calculation_context"
    canonical_content: CalculationContextDependencyContent | None


class ParameterDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["parameter_set"] = "parameter_set"
    canonical_content: ParameterDependencyContent | None


class GrantDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["grant"] = "grant"
    canonical_content: GrantDependencyContent | None


class CapitalizationDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["capitalization"] = "capitalization"
    canonical_content: CapitalizationDependencyContent | None


class FutureReserveDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["future_reserve"] = "future_reserve"
    canonical_content: FutureReserveDependencyContent | None


class CbsDependencyEntry(DependencyEntryBase):
    dependency_type: Literal["cbs"] = "cbs"
    canonical_content: CbsDependencyContent | None


DependencyEntry = Annotated[
    CalculationContextDependencyEntry
    | M07DependencyEntry
    | ParameterDependencyEntry
    | GrantDependencyEntry
    | CapitalizationDependencyEntry
    | FutureReserveDependencyEntry
    | CbsDependencyEntry,
    Field(discriminator="dependency_type"),
]


class FixationDependencyManifest(ManifestContract):
    run_id: int
    run_identity: str
    client_id: int
    calculation_version: str
    input_contract_version: str
    result_contract_version: str | None
    manifest_schema_version: Literal["pkg003.fixation-dependency-manifest.v1"] = (
        MANIFEST_SCHEMA_VERSION
    )
    fingerprint_algorithm_version: Literal["sha256-canonical-json-v1"] = (
        FINGERPRINT_ALGORITHM_VERSION
    )
    context_availability: Literal["available", "unavailable"] = Field(
        description=(
            "Whether dependency content could be parsed and stored; this does not assert "
            "professional acceptance, downstream eligibility, or lifecycle status."
        )
    )
    context_reason_codes: list[str] = Field(default_factory=list)
    dependencies: list[DependencyEntry]
    manifest_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_availability(self) -> "FixationDependencyManifest":
        if self.context_availability == "unavailable":
            if self.dependencies or self.manifest_fingerprint is not None:
                raise ValueError("unavailable dependency context cannot have dependencies or fingerprint")
        elif self.manifest_fingerprint is None:
            raise ValueError("available dependency context requires a manifest fingerprint")
        return self


class DependencyManifestRetrieval(ManifestContract):
    run_id: int
    client_id: int
    availability: Literal["available", "unavailable"]
    reason_codes: list[str]
    manifest: FixationDependencyManifest | None


class DependencyComparisonRequest(ManifestContract):
    current_context: dict[str, Any] | None = None
    current_input_contract_version: str | None = None
    current_result_contract_version: str | None = None


class PerDependencyComparison(ManifestContract):
    dependency_type: str
    stable_identity: str | None
    technical_result: TechnicalComparisonResult
    changed_fields: list[str]
    historical_fingerprint: str | None
    current_fingerprint: str | None
    reason_codes: list[str]


class DependencyComparisonResponse(ManifestContract):
    run_id: int
    client_id: int
    assessment_timestamp: datetime
    manifest_version: str | None
    technical_result: TechnicalComparisonResult
    per_dependency_results: list[PerDependencyComparison]
    changed_dependency_types: list[str]
    changed_fields: list[str]
    historical_fingerprint: str | None
    current_fingerprint: str | None
    reason_codes: list[str]
    unavailable_dependencies: list[str]
    comparison_algorithm_version: Literal["pkg003.dependency-comparison.v1"] = (
        COMPARISON_ALGORITHM_VERSION
    )
