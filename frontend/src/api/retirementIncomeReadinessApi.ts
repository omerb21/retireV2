import { apiFetch, buildApiUrl } from "./apiBase";

export interface ReadinessContext {
  schema_version: "RTDIR_PLANNING_CONTEXT_V1"; client_id: number;
  planning_calculation_input_fingerprint: string; planning_input_ready: boolean;
  retirement_target_date: string | null; retirement_target_ready: boolean;
  blocking_facts: Array<{source_id: string | null; code: string}>;
}
export interface TargetResult {
  client_id: number | null; planning_calculation_input_fingerprint: string | null;
  retirement_target_date: string | null; target: null | {monthly_amount: string; income_basis: string; price_basis: string; price_reference_date: string | null};
  authority: null | {record_version: number; source_kind: string; confirmation_actor: string; confirmed_at: string; lifecycle_state: string};
  authority_state: string; target_readiness_state: string; target_ready: boolean; blockers: string[];
  target_semantic_fingerprint: string | null; target_result_fingerprint: string;
}
export type SourceBasisDecisionState =
  | "CURRENT"
  | "NOT_APPLICABLE_NOT_ADMITTED"
  | "NOT_APPLICABLE_DELEGATED"
  | "MISSING"
  | "INVALID"
  | "STALE"
  | "CLEARED"
  | "UPSTREAM_UNRESOLVED"
  | "DELEGATION_UNRESOLVED"
  | "DELEGATION_STALE";
export type SourceIncomeBasis = "GROSS" | "NET" | "UNKNOWN";
export type SourcePriceBasis = "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE" | "UNKNOWN";
export type IncomeBasisProvenance = "EXPLICIT_PROFESSIONAL" | "UPSTREAM_RECURRING_AMOUNT_BASIS";
export type PriceBasisProvenance = "DERIVED_ACCEPTED_PENSION_TARGET_AMOUNT" | "EXPLICIT_PROFESSIONAL";
export interface ComparisonEntryV2 {
  source_id: string;
  source_kind: "PENSION" | "RECURRING_INCOME";
  source_category: string;
  admission_state: "INCLUDED" | "EXCLUDED" | "UNRESOLVED";
  rtisa_reason_codes: string[];
  decision_state: SourceBasisDecisionState;
  source_version: number | string | null;
  source_fingerprint: string;
  amount_authority_fingerprint: string | null;
  decision_version: number | null;
  decision_fingerprint: string | null;
  income_basis: SourceIncomeBasis | null;
  income_basis_provenance: IncomeBasisProvenance | null;
  price_basis: SourcePriceBasis | null;
  price_reference_date: string | null;
  price_basis_provenance: PriceBasisProvenance | null;
  target_income_basis: "GROSS" | "NET";
  target_price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE";
  target_price_reference_date: string | null;
  comparison_state: "DIRECTLY_COMPARABLE" | "NORMALIZATION_REQUIRED" | "BASIS_UNRESOLVED" | "NOT_ADMITTED";
  reason_codes: string[];
  source_comparison_fingerprint: string;
}
export interface ComparisonSuccessV2 {
  schema_version: "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2";
  client_id: number;
  planning_calculation_input_fingerprint: string;
  retirement_target_date: string;
  target_result_fingerprint: string;
  target_semantic_fingerprint: string;
  crtisba_result_fingerprint: string;
  comparison_input_fingerprint: string;
  source_comparisons: ComparisonEntryV2[];
  classification_state: "COMPLETE";
  classification_complete: true;
  direct_comparison_state: "READY" | "NOT_READY";
  direct_comparison_ready: boolean;
  blockers: string[];
  comparison_result_fingerprint: string;
  result_state?: never;
}
export interface ComparisonFailureV2 {
  schema_version: "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2";
  client_id: number | null;
  supplied_planning_calculation_input_fingerprint: string | null;
  supplied_retirement_target_date: string | null;
  observed_target_planning_calculation_input_fingerprint: string | null;
  observed_target_retirement_target_date: string | null;
  observed_target_result_fingerprint: string | null;
  observed_crtisba_planning_calculation_input_fingerprint: string | null;
  observed_crtisba_retirement_target_date: string | null;
  observed_crtisba_result_fingerprint: string | null;
  observed_crtisba_failure_fingerprint: string | null;
  observed_crtisba_failure_stage: string | null;
  observed_crtisba_failure_detail_code: string | null;
  result_state: "block_no_result";
  failure_stage: string;
  failure_detail_code: string;
  result_fingerprint: string;
}
export type ComparisonResult = ComparisonSuccessV2 | ComparisonFailureV2;

async function call<T>(clientId: number, path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(buildApiUrl(`/clients/${clientId}/retirement-income-readiness${path}`), init);
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.code ?? "REQUEST_FAILED");
  if (data?.client_id !== null && data?.client_id !== clientId) throw new Error("RESPONSE_CLIENT_MISMATCH");
  return data as T;
}
export const readContext = (clientId: number, signal?: AbortSignal) => call<ReadinessContext>(clientId, "/context", {signal});
export const readTarget = (clientId: number, signal?: AbortSignal) => call<TargetResult>(clientId, "/target", {signal});
export const confirmTarget = (clientId: number, body: unknown, signal?: AbortSignal) => call<TargetResult>(clientId, "/target", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body), signal});
export const compareIncome = (clientId: number, body: unknown, signal?: AbortSignal) => call<ComparisonResult>(clientId, "/comparison", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body), signal});
