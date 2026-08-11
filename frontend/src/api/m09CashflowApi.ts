import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export const M09_FAMILY = "deterministic_monthly_cashflow" as const;
export const M09_VERSION = "v1" as const;

export interface M09ContractRequest {
  scenario_family: typeof M09_FAMILY;
  scenario_contract_version: typeof M09_VERSION;
  start_month: string;
  end_month: string;
}

export interface M09Inventory {
  inventory_id: string; client_id: number; scenario_family: string; scenario_contract_version: string;
  start_month: string; end_month: string; component_domain_contract_version: string;
  assessment_timestamp: string; actor: string; actor_is_authentication: false;
  domains: Array<Record<string, unknown>>; complete: boolean; blocker_codes: string[]; inventory_fingerprint: string;
}

export interface M09Currentness {
  run_id: string; current_run_id: string; is_current: boolean; reason_codes: string[];
  assessment_timestamp: string; assessment_contract_version: "m09-currentness-v1";
}

export interface M09Eligibility {
  assessed_scenario_run_id: string; current_scenario_run_id: string; eligible_for_m10: boolean;
  reason_codes: string[]; informational_warnings: string[]; assessment_timestamp: string;
  eligibility_contract_version: "m09-to-m10-eligibility-v1";
}

export interface M09MonthlyResult {
  monthly_result_id: string; month: string; gross_inflow_total: string; gross_outflow_total: string;
  period_net: string; component_evidence: Array<Record<string, unknown>>; result_fingerprint: string;
}

export interface M09Run {
  run_id: string; client_id: number; predecessor_run_id: string | null; run_sequence: number;
  scenario_family: string; scenario_contract_version: string; start_month: string; end_month: string;
  inventory: M09Inventory; status: string; assumption_manifest: Record<string, unknown>;
  assumption_manifest_fingerprint: string; upstream_snapshot: Record<string, unknown>;
  upstream_snapshot_fingerprint: string; warnings: Array<Record<string, unknown>>; blocker_codes: string[];
  monthly_results: M09MonthlyResult[]; range_totals: null | { gross_inflow_total: string; gross_outflow_total: string; period_net: string };
  semantic_result_fingerprint: string | null; result_integrity_fingerprint: string | null;
  currentness: M09Currentness; m10_eligibility: M09Eligibility; actor: string; actor_is_authentication: false; created_at: string;
}

export interface M09RunSummary {
  run_id: string; predecessor_run_id: string | null; run_sequence: number; status: string;
  start_month: string; end_month: string; inventory_id: string; blocker_codes: string[];
  semantic_result_fingerprint: string | null; is_current: boolean; eligible_for_m10: boolean; created_at: string;
}

async function request<T>(path: string, init: RequestInit = { method: "GET" }): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const body = (response.headers.get("content-type") ?? "").includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new ApiTransportError({ status: response.status, statusText: response.statusText, body });
  return body as T;
}

const root = (clientId: number) => `/clients/${clientId}/m09`;
const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const assessM09Inventory = (clientId: number, payload: M09ContractRequest) => request<M09Inventory>(`${root(clientId)}/inventories`, json(payload));
export const executeM09Run = (clientId: number, payload: M09ContractRequest) => request<M09Run>(`${root(clientId)}/runs`, json(payload));
export const listM09Runs = (clientId: number) => request<M09RunSummary[]>(`${root(clientId)}/runs`);
export const getM09Run = (clientId: number, runId: string) => request<M09Run>(`${root(clientId)}/runs/${encodeURIComponent(runId)}`);
export const getM09Currentness = (clientId: number, runId: string) => request<M09Currentness>(`${root(clientId)}/runs/${encodeURIComponent(runId)}/currentness`);
export const getM09Eligibility = (clientId: number, runId: string) => request<M09Eligibility>(`${root(clientId)}/runs/${encodeURIComponent(runId)}/m10-eligibility`);
