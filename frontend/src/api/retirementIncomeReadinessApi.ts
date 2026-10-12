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
export interface ComparisonResult {
  result_state?: "block_no_result"; failure_stage?: string; failure_detail_code?: string;
  client_id: number | null; direct_comparison_state?: string; direct_comparison_ready?: boolean;
  blockers?: string[]; source_comparisons?: Array<{source_id: string; comparison_state: string; reason_codes: string[]; rtisa_admission_state: string; source_income_basis: string; source_price_basis: string}>;
}

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
