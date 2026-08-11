from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class M09ContractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_family: str
    scenario_contract_version: str
    start_month: str
    end_month: str

    @field_validator("start_month", "end_month")
    @classmethod
    def canonical_month(cls, value: str) -> str:
        if MONTH_PATTERN.fullmatch(value) is None:
            raise ValueError("month must use canonical YYYY-MM form")
        return value

    @model_validator(mode="after")
    def ordered_horizon(self) -> "M09ContractRequest":
        if self.end_month < self.start_month:
            raise ValueError("end_month must be greater than or equal to start_month")
        return self


class M09InventoryResponse(BaseModel):
    inventory_id: str
    client_id: int
    scenario_family: str
    scenario_contract_version: str
    start_month: str
    end_month: str
    component_domain_contract_version: str
    assessment_timestamp: datetime
    actor: str
    actor_is_authentication: Literal[False] = False
    domains: list[dict[str, Any]]
    complete: bool
    blocker_codes: list[str]
    inventory_fingerprint: str


class M09MonthlyResultResponse(BaseModel):
    monthly_result_id: str
    month: str
    gross_inflow_total: str
    gross_outflow_total: str
    period_net: str
    component_evidence: list[dict[str, Any]]
    result_fingerprint: str


class M09RangeTotalsResponse(BaseModel):
    gross_inflow_total: str
    gross_outflow_total: str
    period_net: str


class M09CurrentnessResponse(BaseModel):
    run_id: str
    current_run_id: str
    is_current: bool
    reason_codes: list[str]
    assessment_timestamp: datetime
    assessment_contract_version: Literal["m09-currentness-v1"] = (
        "m09-currentness-v1"
    )


class M09M10EligibilityResponse(BaseModel):
    assessed_scenario_run_id: str
    current_scenario_run_id: str
    eligible_for_m10: bool
    reason_codes: list[str]
    informational_warnings: list[str]
    assessment_timestamp: datetime
    eligibility_contract_version: Literal["m09-to-m10-eligibility-v1"] = (
        "m09-to-m10-eligibility-v1"
    )


class M09RunResponse(BaseModel):
    run_id: str
    client_id: int
    predecessor_run_id: str | None
    run_sequence: int
    scenario_family: str
    scenario_contract_version: str
    start_month: str
    end_month: str
    inventory: M09InventoryResponse
    status: Literal[
        "success_complete",
        "validation_failed",
        "dependency_failed",
        "calculation_failed",
        "unsupported",
    ]
    assumption_manifest: dict[str, Any]
    assumption_manifest_fingerprint: str
    upstream_snapshot: dict[str, Any]
    upstream_snapshot_fingerprint: str
    warnings: list[dict[str, Any]]
    blocker_codes: list[str]
    monthly_results: list[M09MonthlyResultResponse]
    range_totals: M09RangeTotalsResponse | None
    semantic_result_fingerprint: str | None
    result_integrity_fingerprint: str | None
    currentness: M09CurrentnessResponse
    m10_eligibility: M09M10EligibilityResponse
    actor: str
    actor_is_authentication: Literal[False] = False
    created_at: datetime


class M09RunSummaryResponse(BaseModel):
    run_id: str
    predecessor_run_id: str | None
    run_sequence: int
    status: str
    start_month: str
    end_month: str
    inventory_id: str
    blocker_codes: list[str]
    semantic_result_fingerprint: str | None
    is_current: bool
    eligible_for_m10: bool
    created_at: datetime
