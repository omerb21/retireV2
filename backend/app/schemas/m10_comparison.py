from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class M10ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_run_id: str
    compared_run_id: str


class M10MetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_value: str
    compared_value: str
    delta: str
    relation: Literal[
        "equal",
        "compared_greater_than_reference",
        "compared_lower_than_reference",
    ]


class M10MonthlyComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str
    gross_inflow_total: M10MetricComparison
    gross_outflow_total: M10MetricComparison
    period_net: M10MetricComparison


class M10RangeComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gross_inflow_total: M10MetricComparison
    gross_outflow_total: M10MetricComparison
    period_net: M10MetricComparison


class M10UpstreamVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_identity: str
    candidate_identity: str
    source_identity: str
    source_version: str
    source_fingerprint: str
    handoff_contract_versions: list[str]


class M10Versions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factual_engine_version: Literal["m09-aggregation-v1"]
    factual_result_schema_version: Literal["m09-result-v1"]
    subject_engine_version: Literal["m09-subject-aggregation-v1"]
    subject_result_schema_version: Literal["m09-subject-result-v1"]
    upstream_snapshot_schema_version: Literal["m09-subject-upstream-snapshot-v1"]
    factual_inventory_schema_version: Literal["m09-resolved-component-inventory-v1"]
    factual_upstream_versions: list[M10UpstreamVersion]


class M10RunEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    scenario_subject_id: str
    subject_type: Literal["baseline", "adjusted"]
    calculation_semantic_fingerprint: str
    integrity_fingerprint: str
    adjustment_manifest_fingerprint: str
    factual_inventory_fingerprint: str
    upstream_snapshot_fingerprint: str
    semantic_result_fingerprint: str
    result_integrity_fingerprint: str


class M10Horizon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_month: str
    end_month: str


class M10ComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_contract_version: Literal["m10-scenario-comparison-v1"]
    pair_admission_contract: Literal["m10-pair-admission-v1"]
    comparison_result_schema: Literal["m10-comparison-result-v1"]
    comparison_fingerprint_schema: Literal["m10-comparison-fingerprint-v1"]
    comparison_fingerprint: str
    delta_direction: Literal["compared_minus_reference"]
    client_id: int
    scenario_family: Literal["declared_retirement_cashflow_adjustments"]
    scenario_contract_version: Literal["v1"]
    horizon: M10Horizon
    factual_baseline_material_fingerprint: str
    component_domain_contract_version: Literal["m09-component-domains-v1"]
    versions: M10Versions
    reference_run: M10RunEvidence
    compared_run: M10RunEvidence
    monthly_comparisons: list[M10MonthlyComparison]
    range_totals: M10RangeComparison
