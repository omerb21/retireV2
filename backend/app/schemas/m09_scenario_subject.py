from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.m09_cashflow import M09RangeTotalsResponse


MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MONEY = re.compile(r"^(0|[1-9]\d*)\.\d{2}$")


class AdjustmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    adjustment_type: Literal["declared_additional_monthly_income", "declared_additional_monthly_expense"]
    amount: str
    start_month: str
    end_month: str

    @field_validator("amount")
    @classmethod
    def canonical_amount(cls, value: str) -> str:
        if MONEY.fullmatch(value) is None:
            raise ValueError("amount must be canonical positive Decimal with two places")
        if value == "0.00":
            raise ValueError("amount must be at least 0.01")
        if len(value.split(".")[0]) > 18:
            raise ValueError("amount exceeds Numeric(20,2)")
        return value

    @field_validator("start_month", "end_month")
    @classmethod
    def month(cls, value: str) -> str:
        if MONTH.fullmatch(value) is None:
            raise ValueError("month must use canonical YYYY-MM")
        return value

    @model_validator(mode="after")
    def ordered(self):
        if self.end_month < self.start_month:
            raise ValueError("adjustment start_month must not follow end_month")
        return self


class CreateAdjustedSubjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_family: Literal["declared_retirement_cashflow_adjustments"]
    scenario_contract_version: Literal["v1"]
    display_label: str | None = Field(default=None, max_length=160)
    adjustments: list[AdjustmentInput]

    @field_validator("adjustments")
    @classmethod
    def nonempty(cls, value):
        if not value:
            raise ValueError("adjusted subject requires at least one adjustment")
        return value


class SubjectExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_month: str
    end_month: str

    @field_validator("start_month", "end_month")
    @classmethod
    def month(cls, value: str) -> str:
        if MONTH.fullmatch(value) is None:
            raise ValueError("month must use canonical YYYY-MM")
        return value

    @model_validator(mode="after")
    def ordered(self):
        if self.end_month < self.start_month:
            raise ValueError("start_month must not follow end_month")
        return self


class AdjustmentResponse(BaseModel):
    adjustment_id: str
    ordinal: int
    adjustment_type: str
    amount: str
    start_month: str
    end_month: str
    provenance: str
    semantic_fingerprint: str
    actor: str
    created_at: datetime


class ScenarioSubjectResponse(BaseModel):
    scenario_subject_id: str
    client_id: int
    scenario_family: Literal["declared_retirement_cashflow_adjustments"]
    scenario_contract_version: Literal["v1"]
    combined_contract_identifier: Literal["declared_retirement_cashflow_adjustments/v1"] = "declared_retirement_cashflow_adjustments/v1"
    subject_type: Literal["baseline", "adjusted"]
    display_label: str | None
    adjustment_manifest: dict[str, Any]
    adjustment_manifest_fingerprint: str
    calculation_semantic_fingerprint: str
    integrity_fingerprint: str
    provenance: str
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime
    adjustments: list[AdjustmentResponse]


class SubjectMonthlyResultResponse(BaseModel):
    monthly_result_id: str
    month: str
    gross_inflow_total: str
    gross_outflow_total: str
    period_net: str
    component_evidence: list[dict[str, Any]]
    result_fingerprint: str


class SubjectCurrentnessResponse(BaseModel):
    run_id: str
    current_run_id: str
    scenario_subject_id: str
    is_current: bool
    reason_codes: list[str]
    assessment_timestamp: datetime
    assessment_contract_version: Literal["m09-subject-currentness-v1"] = "m09-subject-currentness-v1"


class SubjectM10EligibilityResponse(BaseModel):
    assessed_scenario_run_id: str
    current_scenario_run_id: str
    scenario_subject_id: str
    eligible_for_m10: bool
    reason_codes: list[str]
    informational_warnings: list[str]
    factual_baseline_material_fingerprint: str
    assessment_timestamp: datetime
    eligibility_contract_version: Literal["m09-to-m10-eligibility-v2"] = "m09-to-m10-eligibility-v2"


class SubjectRunResponse(BaseModel):
    run_id: str
    scenario_subject_id: str
    client_id: int
    predecessor_run_id: str | None
    run_sequence: int
    scenario_family: str
    scenario_contract_version: str
    start_month: str
    end_month: str
    status: str
    factual_inventory: dict[str, Any]
    factual_inventory_fingerprint: str
    factual_baseline_material_fingerprint: str
    adjustment_manifest: dict[str, Any]
    adjustment_manifest_fingerprint: str
    upstream_snapshot: dict[str, Any]
    upstream_snapshot_fingerprint: str
    warnings: list[dict[str, Any]]
    blocker_codes: list[str]
    monthly_results: list[SubjectMonthlyResultResponse]
    range_totals: M09RangeTotalsResponse | None
    semantic_result_fingerprint: str | None
    result_integrity_fingerprint: str | None
    currentness: SubjectCurrentnessResponse
    m10_eligibility: SubjectM10EligibilityResponse
    actor: str
    created_at: datetime


class SubjectRunSummaryResponse(BaseModel):
    run_id: str
    scenario_subject_id: str
    run_sequence: int
    status: str
    start_month: str
    end_month: str
    factual_baseline_material_fingerprint: str
    is_current: bool
    eligible_for_m10: bool
    created_at: datetime
