from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.cbs_indexation import (
    CbsIndexationFailureEvidence,
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    IndexationBaseDateSource,
)
from app.schemas.fixation_contracts import IDFInput
from app.schemas.m07_calculation_input_resolution import (
    CalculationInputResolutionResult,
    CalculationInputSelection,
)


def _non_empty(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    return value


class AcceptedParameterValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_cap: float
    exemption_percentage: float
    capital_multiplier: float
    grant_impact_multiplier: float

    @field_validator("monthly_cap", "capital_multiplier", "grant_impact_multiplier")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("parameter value must be > 0")
        return value

    @field_validator("exemption_percentage")
    @classmethod
    def validate_percentage(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("exemption_percentage must be between 0 and 1")
        return value


class AcceptedParameterSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_set_id: str
    client_id: int
    tax_year: int
    effective_from: date | None = None
    effective_to: date | None = None
    values: AcceptedParameterValues
    source_basis: str
    status: Literal["accepted", "rejected"]
    accepted_for_use: bool
    accepted_by: str
    decision_timestamp: datetime

    @field_validator("parameter_set_id", "source_basis", "accepted_by")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_effective_period(self) -> "AcceptedParameterSet":
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("effective_from must not be after effective_to")
        if self.status == "accepted" and not self.accepted_for_use:
            raise ValueError("accepted status requires accepted_for_use=true")
        if self.status == "rejected" and self.accepted_for_use:
            raise ValueError("rejected status requires accepted_for_use=false")
        return self


M07ProfileState = Literal["draft", "qualified", "warning_reviewed", "blocked", "superseded"]


class M07QualificationWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str

    @field_validator("code", "message")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))


class M07EntryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    client_id: int
    state: M07ProfileState
    warnings: list[M07QualificationWarning] | None = None
    review_reason: str | None = None
    reviewed_by: str | None = None
    review_timestamp: datetime | None = None
    qualification_trace_id: str | None = None

    @field_validator("profile_id", "review_reason", "reviewed_by", "qualification_trace_id")
    @classmethod
    def validate_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _non_empty(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_warning_review_evidence(self) -> "M07EntryContext":
        if self.state == "warning_reviewed":
            if not self.warnings:
                raise ValueError("warning_reviewed requires at least one structured warning")
            if self.review_reason is None:
                raise ValueError("warning_reviewed requires review_reason")
            if self.reviewed_by is None:
                raise ValueError("warning_reviewed requires reviewed_by")
            if self.review_timestamp is None:
                raise ValueError("warning_reviewed requires review_timestamp")
        return self


SupportStatus = Literal["supported", "unsupported", "requires_special_handling"]
CollectionState = Literal["unknown", "not_collected", "confirmed_none", "items_recorded"]


class AcceptedItemEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_basis: str
    status: str
    accepted_for_use: bool
    actor: str
    decision_timestamp: datetime

    @field_validator("source_basis", "status", "actor")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))


class AdmissibleGrantItem(AcceptedItemEvidence):
    grant_id: str
    client_id: int
    item_type: str
    employer_name: str | None = None
    nominal_amount: float | None = None
    indexed_amount: float | None = None
    grant_date: date
    work_start_date: date
    work_end_date: date
    inclusion_decision: Literal["include", "exclude"]
    support_status: SupportStatus
    conflict_indicator: bool
    accepted_value: float | None = None
    indexation_mode: Literal[
        "asserted_indexed_amount",
        "cbs_system_calculation_required",
        "cbs_system_calculated",
    ]
    asserted_indexed_amount: float | None = None
    system_calculated_amount: float | None = None
    selected_calculation_amount: float | None = None
    resolved_base_date: date | None = None
    base_date_source: IndexationBaseDateSource | None = None
    target_date: date | None = None
    cpi_code: Literal["120010"] | None = None
    cbs_request_evidence: CbsIndexationRequestEvidence | None = None
    cbs_response_evidence: CbsIndexationResponseEvidence | None = None
    indexation_warnings: list[str] = Field(default_factory=list)
    indexation_calculation_status: Literal[
        "pending", "asserted", "calculated", "failed", "unsupported"
    ] = "pending"
    indexation_failure_evidence: CbsIndexationFailureEvidence | None = None

    @field_validator("grant_id", "item_type")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))

    @field_validator(
        "nominal_amount",
        "indexed_amount",
        "accepted_value",
        "asserted_indexed_amount",
        "system_calculated_amount",
        "selected_calculation_amount",
    )
    @classmethod
    def validate_amount(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("amount must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_dates_and_conflict(self) -> "AdmissibleGrantItem":
        if self.work_start_date >= self.work_end_date:
            raise ValueError("work_start_date must be before work_end_date")
        if self.conflict_indicator and self.accepted_value is None:
            raise ValueError("accepted_value is required when conflict_indicator is true")
        if self.indexation_mode == "asserted_indexed_amount" and self.indexed_amount is None:
            raise ValueError("asserted_indexed_amount requires indexed_amount")
        if (
            self.indexation_mode == "cbs_system_calculation_required"
            and self.nominal_amount is None
            and not (self.conflict_indicator and self.accepted_value is not None)
        ):
            raise ValueError("CBS system calculation requires an accepted grant amount")
        return self


class AdmissibleActualCapitalizationItem(AcceptedItemEvidence):
    capitalization_id: str
    item_type: str
    amount: float
    capitalization_date: date
    recorded_meaning: str
    inclusion_decision: Literal["include", "exclude"]
    support_status: SupportStatus
    conflict_indicator: bool
    accepted_value: float | None = None
    notes: str | None = None

    @field_validator("capitalization_id", "item_type", "recorded_meaning")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:
        return _non_empty(value, str(info.field_name))

    @field_validator("amount", "accepted_value")
    @classmethod
    def validate_amount(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("amount must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_conflict(self) -> "AdmissibleActualCapitalizationItem":
        if self.conflict_indicator and self.accepted_value is None:
            raise ValueError("accepted_value is required when conflict_indicator is true")
        return self


class FutureGrantReservation(AcceptedItemEvidence):
    amount: float

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amount must be >= 0")
        return value


class AdmissibleFixationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: str | None = None
    calculation_version: str
    eligibility_date: date
    eligibility_year: int
    upstream_context: M07EntryContext
    parameter_set: AcceptedParameterSet
    grants_collection_state: CollectionState
    grants: list[AdmissibleGrantItem]
    future_grant_reservation: FutureGrantReservation | None
    actual_capitalizations_collection_state: CollectionState
    actual_capitalizations: list[AdmissibleActualCapitalizationItem]
    idf: IDFInput | None = None
    metadata: dict | None = None

    @field_validator("calculation_id")
    @classmethod
    def validate_calculation_id(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value, "calculation_id")

    @field_validator("calculation_version")
    @classmethod
    def validate_calculation_version(cls, value: str) -> str:
        return _non_empty(value, "calculation_version")

    @model_validator(mode="after")
    def validate_structural_consistency(self) -> "AdmissibleFixationInput":
        if self.eligibility_year != self.eligibility_date.year:
            raise ValueError("eligibility_year must match eligibility_date year")
        self._validate_collection(self.grants_collection_state, self.grants, "grants")
        self._validate_collection(
            self.actual_capitalizations_collection_state,
            self.actual_capitalizations,
            "actual_capitalizations",
        )
        return self

    @staticmethod
    def _validate_collection(state: CollectionState, items: list, field_name: str) -> None:
        if state in {"unknown", "not_collected", "confirmed_none"} and items:
            raise ValueError(f"{state} requires an empty {field_name} array")
        if state == "items_recorded" and not items:
            raise ValueError(f"items_recorded requires one or more {field_name} items")


class M07InputReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    b1_evidence_revision_id: str = Field(min_length=1, max_length=64)
    selections: list[CalculationInputSelection] = Field(default_factory=list)


class FixationAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: str | None = None
    calculation_version: str
    m07_input_reference: M07InputReference
    parameter_set: AcceptedParameterSet
    grants_collection_state: CollectionState
    grants: list[AdmissibleGrantItem]
    future_grant_reservation: FutureGrantReservation | None
    actual_capitalizations_collection_state: CollectionState
    actual_capitalizations: list[AdmissibleActualCapitalizationItem]
    idf: IDFInput | None = None
    metadata: dict | None = None

    @field_validator("calculation_id")
    @classmethod
    def validate_calculation_id(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value, "calculation_id")

    @field_validator("calculation_version")
    @classmethod
    def validate_calculation_version(cls, value: str) -> str:
        return _non_empty(value, "calculation_version")

    @model_validator(mode="after")
    def validate_collection_shapes(self) -> "FixationAdmissionRequest":
        AdmissibleFixationInput._validate_collection(
            self.grants_collection_state, self.grants, "grants"
        )
        AdmissibleFixationInput._validate_collection(
            self.actual_capitalizations_collection_state,
            self.actual_capitalizations,
            "actual_capitalizations",
        )
        return self


class ResolvedFixationAdmissionInput(FixationAdmissionRequest):
    eligibility_date: date
    eligibility_year: int
    m07_resolution: CalculationInputResolutionResult

    @model_validator(mode="after")
    def validate_resolved_m07_input(self) -> "ResolvedFixationAdmissionInput":
        if self.eligibility_year != self.eligibility_date.year:
            raise ValueError("eligibility_year must match eligibility_date year")
        if self.m07_resolution.outcome != "resolved":
            raise ValueError("resolved admission requires a resolved M07 outcome")
        if self.m07_resolution.calculation_payload is None:
            raise ValueError(
                "resolved admission requires an M07 calculation-ready payload"
            )
        return self
