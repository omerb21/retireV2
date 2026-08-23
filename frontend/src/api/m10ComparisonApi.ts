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

type JsonObject = Record<string, unknown>;

const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const SOURCE_MONEY_PATTERN = /^-?(0|[1-9][0-9]{0,17})\.[0-9]{2}$/;
const DELTA_MONEY_PATTERN = /^-?(0|[1-9][0-9]{0,17}|1[0-9]{18})\.[0-9]{2}$/;
const MAX_DELTA_INTEGER = "1999999999999999999";

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: JsonObject, keys: readonly string[]): boolean {
  const actualKeys = Object.keys(value);
  return actualKeys.length === keys.length && keys.every(key => Object.prototype.hasOwnProperty.call(value, key));
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isSha256(value: unknown): value is string {
  return isString(value) && SHA256_PATTERN.test(value);
}

function isMonth(value: unknown): value is string {
  return isString(value) && MONTH_PATTERN.test(value);
}

function isSourceMoney(value: unknown): value is string {
  return isString(value) && value !== "-0.00" && SOURCE_MONEY_PATTERN.test(value);
}

function isDeltaMoney(value: unknown): value is string {
  if (!isString(value) || value === "-0.00" || !DELTA_MONEY_PATTERN.test(value)) return false;
  const unsigned = value.startsWith("-") ? value.slice(1) : value;
  const [integer, fraction] = unsigned.split(".");
  return integer !== MAX_DELTA_INTEGER || fraction !== "99";
}

function isMetricComparison(value: unknown): value is M10MetricComparison {
  if (!isObject(value) || !hasExactKeys(value, ["reference_value", "compared_value", "delta", "relation"])) {
    return false;
  }
  return isSourceMoney(value.reference_value)
    && isSourceMoney(value.compared_value)
    && isDeltaMoney(value.delta)
    && (value.relation === "equal"
      || value.relation === "compared_greater_than_reference"
      || value.relation === "compared_lower_than_reference");
}

function isRangeComparison(value: unknown): value is M10RangeComparison {
  if (!isObject(value) || !hasExactKeys(value, ["gross_inflow_total", "gross_outflow_total", "period_net"])) {
    return false;
  }
  return isMetricComparison(value.gross_inflow_total)
    && isMetricComparison(value.gross_outflow_total)
    && isMetricComparison(value.period_net);
}

function isMonthlyComparison(value: unknown): value is M10MonthlyComparison {
  if (!isObject(value) || !hasExactKeys(value, ["month", "gross_inflow_total", "gross_outflow_total", "period_net"])) {
    return false;
  }
  return isMonth(value.month)
    && isMetricComparison(value.gross_inflow_total)
    && isMetricComparison(value.gross_outflow_total)
    && isMetricComparison(value.period_net);
}

function isUpstreamVersion(value: unknown): value is M10UpstreamVersion {
  if (!isObject(value) || !hasExactKeys(value, [
    "domain_identity", "candidate_identity", "source_identity", "source_version",
    "source_fingerprint", "handoff_contract_versions",
  ])) return false;
  const supportedDomain = value.domain_identity === "recurring_income"
    || value.domain_identity === "recurring_expense"
    || value.domain_identity === "m06_monthly_pension";
  const exactHandoffs = Array.isArray(value.handoff_contract_versions)
    && (value.domain_identity === "m06_monthly_pension"
      ? value.handoff_contract_versions.length === 1
        && value.handoff_contract_versions[0] === "m06-to-m09-monthly-amount-v1"
      : value.handoff_contract_versions.length === 0);
  return supportedDomain
    && isString(value.candidate_identity)
    && isString(value.source_identity)
    && isString(value.source_version)
    && isSha256(value.source_fingerprint)
    && exactHandoffs;
}

function isVersions(value: unknown): value is M10Versions {
  if (!isObject(value) || !hasExactKeys(value, [
    "factual_engine_version", "factual_result_schema_version", "subject_engine_version",
    "subject_result_schema_version", "upstream_snapshot_schema_version",
    "factual_inventory_schema_version", "factual_upstream_versions",
  ])) return false;
  return value.factual_engine_version === "m09-aggregation-v1"
    && value.factual_result_schema_version === "m09-result-v1"
    && value.subject_engine_version === "m09-subject-aggregation-v1"
    && value.subject_result_schema_version === "m09-subject-result-v1"
    && value.upstream_snapshot_schema_version === "m09-subject-upstream-snapshot-v1"
    && value.factual_inventory_schema_version === "m09-resolved-component-inventory-v1"
    && Array.isArray(value.factual_upstream_versions)
    && value.factual_upstream_versions.every(isUpstreamVersion);
}

function isRunEvidence(value: unknown, subjectType: "baseline" | "adjusted"): value is M10RunEvidence {
  if (!isObject(value) || !hasExactKeys(value, [
    "run_id", "scenario_subject_id", "subject_type", "calculation_semantic_fingerprint",
    "integrity_fingerprint", "adjustment_manifest_fingerprint", "factual_inventory_fingerprint",
    "upstream_snapshot_fingerprint", "semantic_result_fingerprint", "result_integrity_fingerprint",
  ])) return false;
  return isString(value.run_id)
    && isString(value.scenario_subject_id)
    && value.subject_type === subjectType
    && isSha256(value.calculation_semantic_fingerprint)
    && isSha256(value.integrity_fingerprint)
    && isSha256(value.adjustment_manifest_fingerprint)
    && isSha256(value.factual_inventory_fingerprint)
    && isSha256(value.upstream_snapshot_fingerprint)
    && isSha256(value.semantic_result_fingerprint)
    && isSha256(value.result_integrity_fingerprint);
}

function isHorizon(value: unknown): value is M10ComparisonResponse["horizon"] {
  return isObject(value)
    && hasExactKeys(value, ["start_month", "end_month"])
    && isMonth(value.start_month)
    && isMonth(value.end_month);
}

function isM10ComparisonResponse(value: unknown): value is M10ComparisonResponse {
  if (!isObject(value) || !hasExactKeys(value, [
    "comparison_contract_version", "pair_admission_contract", "comparison_result_schema",
    "comparison_fingerprint_schema", "comparison_fingerprint", "delta_direction", "client_id",
    "scenario_family", "scenario_contract_version", "horizon",
    "factual_baseline_material_fingerprint", "component_domain_contract_version", "versions",
    "reference_run", "compared_run", "monthly_comparisons", "range_totals",
  ])) return false;
  return value.comparison_contract_version === M10_COMPARISON_CONTRACT_VERSION
    && value.pair_admission_contract === M10_PAIR_ADMISSION_CONTRACT
    && value.comparison_result_schema === M10_COMPARISON_RESULT_SCHEMA
    && value.comparison_fingerprint_schema === M10_COMPARISON_FINGERPRINT_SCHEMA
    && isSha256(value.comparison_fingerprint)
    && value.delta_direction === "compared_minus_reference"
    && typeof value.client_id === "number"
    && value.client_id % 1 === 0
    && value.scenario_family === "declared_retirement_cashflow_adjustments"
    && value.scenario_contract_version === "v1"
    && isHorizon(value.horizon)
    && isSha256(value.factual_baseline_material_fingerprint)
    && value.component_domain_contract_version === "m09-component-domains-v1"
    && isVersions(value.versions)
    && isRunEvidence(value.reference_run, "baseline")
    && isRunEvidence(value.compared_run, "adjusted")
    && Array.isArray(value.monthly_comparisons)
    && value.monthly_comparisons.every(isMonthlyComparison)
    && isRangeComparison(value.range_totals);
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
  if (!isM10ComparisonResponse(body)) {
    throw new ApiTransportError({
      status: response.status,
      statusText: "Invalid M10 comparison response schema",
      body,
    });
  }
  return body;
}
