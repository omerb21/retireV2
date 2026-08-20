import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export const M10_COMPARISON_CONTRACT_VERSION = "m10-scenario-comparison-v2" as const;
export const M10_PAIR_ADMISSION_CONTRACT = "m10-pair-admission-v2" as const;
export const M10_COMPARISON_RESULT_SCHEMA = "m10-comparison-result-v2" as const;
export const M10_COMPARISON_FINGERPRINT_SCHEMA = "m10-comparison-fingerprint-v2" as const;

export const M10_COMPARATOR_BLOCKER_CODES = [
  "comparison_run_unavailable",
  "comparison_same_subject",
  "comparison_pair_role_invalid",
  "comparison_scenario_contract_mismatch",
  "comparison_horizon_mismatch",
  "comparison_factual_baseline_material_mismatch",
  "comparison_component_domain_contract_mismatch",
  "comparison_engine_version_mismatch",
  "comparison_result_schema_version_mismatch",
  "comparison_factual_upstream_version_mismatch",
  "comparison_run_not_current",
  "comparison_run_not_eligible",
  "comparison_fingerprint_invalid",
  "comparison_semantically_identical_manifest",
  "comparison_month_alignment_mismatch",
  "comparison_numeric_domain_invalid",
] as const;

export type M10ComparatorBlockerCode = typeof M10_COMPARATOR_BLOCKER_CODES[number];

export interface M10ComparisonRequest {
  reference_run_id: string;
  compared_run_id: string;
}

export interface M10MetricComparison {
  reference_value: string;
  compared_value: string;
  delta: string;
  relation: "equal" | "compared_greater_than_reference" | "compared_lower_than_reference";
}

export interface M10MonthlyComparison {
  month: string;
  gross_inflow_total: M10MetricComparison;
  gross_outflow_total: M10MetricComparison;
  period_net: M10MetricComparison;
}

export interface M10RangeComparison {
  gross_inflow_total: M10MetricComparison;
  gross_outflow_total: M10MetricComparison;
  period_net: M10MetricComparison;
}

export interface M10UpstreamVersion {
  domain_identity: string;
  candidate_identity: string;
  source_identity: string;
  source_version: string;
  source_fingerprint: string;
  handoff_contract_versions: string[];
}

export interface M10Versions {
  factual_engine_version: "m09-aggregation-v1";
  factual_result_schema_version: "m09-result-v1";
  subject_engine_version: "m09-subject-aggregation-v1";
  subject_result_schema_version: "m09-subject-result-v1";
  upstream_snapshot_schema_version: "m09-subject-upstream-snapshot-v1";
  factual_inventory_schema_version: "m09-resolved-component-inventory-v1";
  factual_upstream_versions: M10UpstreamVersion[];
}

export interface M10RunEvidence {
  run_id: string;
  scenario_subject_id: string;
  subject_type: "baseline" | "adjusted";
  calculation_semantic_fingerprint: string;
  integrity_fingerprint: string;
  adjustment_manifest_fingerprint: string;
  factual_inventory_fingerprint: string;
  upstream_snapshot_fingerprint: string;
  semantic_result_fingerprint: string;
  result_integrity_fingerprint: string;
}

export interface M10ComparisonResponse {
  comparison_contract_version: typeof M10_COMPARISON_CONTRACT_VERSION;
  pair_admission_contract: typeof M10_PAIR_ADMISSION_CONTRACT;
  comparison_result_schema: typeof M10_COMPARISON_RESULT_SCHEMA;
  comparison_fingerprint_schema: typeof M10_COMPARISON_FINGERPRINT_SCHEMA;
  comparison_fingerprint: string;
  delta_direction: "compared_minus_reference";
  client_id: number;
  scenario_family: "declared_retirement_cashflow_adjustments";
  scenario_contract_version: "v1";
  horizon: { start_month: string; end_month: string };
  factual_baseline_material_fingerprint: string;
  component_domain_contract_version: "m09-component-domains-v1";
  versions: M10Versions;
  reference_run: M10RunEvidence;
  compared_run: M10RunEvidence;
  monthly_comparisons: M10MonthlyComparison[];
  range_totals: M10RangeComparison;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  return (response.headers.get("content-type") ?? "").includes("application/json")
    ? response.json()
    : response.text();
}

export async function compareM10Runs(
  clientId: number,
  payload: M10ComparisonRequest,
): Promise<M10ComparisonResponse> {
  const response = await fetch(buildApiUrl(`/clients/${clientId}/m10/compare`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reference_run_id: payload.reference_run_id,
      compared_run_id: payload.compared_run_id,
    }),
  });
  const body = await parseResponseBody(response);
  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body,
    });
  }
  return body as M10ComparisonResponse;
}
