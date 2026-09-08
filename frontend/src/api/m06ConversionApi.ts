import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export type M06Mode = "balance_to_monthly_pension" | "monthly_pension_to_capital_equivalent";
export type M06Authority = "documentary" | "planner_declared";
export type M06State = "draft" | "resolved" | "warning_reviewed" | "blocked" | "superseded";

export interface M06Revision {
  revision_id: string; subject_id: string; predecessor_revision_id: string | null; revision_sequence: number;
  state: M06State; action_type: string; mode: M06Mode; formula_id: string; input_identity: string;
  input_amount: string | null; input_date: string | null; predecessor_snapshot: Record<string, unknown>;
  warnings: { warning_id: string; classification: string }[]; blocking_reasons: string[];
  informational_warnings: string[]; coefficient: { evidence_id: string; authority_class: M06Authority;
    coefficient: string; source_intake_id: string | null; source_locator: string | null; source_note: string | null;
    reason: string; effective_from: string | null; effective_to: string | null; applicability_declared: boolean;
    metadata: Record<string, unknown>; actor: string; actor_is_authentication: false; created_at: string };
  manifest: null | { manifest_id: string; fingerprint: string; raw_result_kind: string | null;
    raw_decimal: string | null; raw_numerator: string | null; raw_denominator: string | null;
    display_result: string | null; evidence: Record<string, unknown> };
  warning_dispositions: Record<string, unknown>[]; actor: string; actor_is_authentication: false; created_at: string;
}
export interface M06Eligibility { subject_id: string; assessed_revision_id: string; eligible_for_downstream: boolean; current_revision_id: string | null; exclusion_reasons: string[]; informational_warnings: string[]; meaning: string }
export interface M06Subject { subject_id: string; client_id: number; m05_subject_id: string; mode: M06Mode; input_identity: string; current_revision: M06Revision | null; eligibility: M06Eligibility }

async function request<T>(path: string, init: RequestInit = { method: "GET" }): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const body = (response.headers.get("content-type") ?? "").includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new ApiTransportError({ status: response.status, statusText: response.statusText, body });
  return body as T;
}
const root = (clientId: number) => `/clients/${clientId}/m06`;
const subject = (clientId: number, subjectId: string) => `${root(clientId)}/subjects/${encodeURIComponent(subjectId)}`;

export const listM06Subjects = (clientId: number) => request<M06Subject[]>(`${root(clientId)}/subjects`);
export const getM06Subject = (clientId: number, id: string) => request<M06Subject>(subject(clientId, id));
export const getM06History = (clientId: number, id: string) => request<M06Revision[]>(`${subject(clientId, id)}/history`);
export const getM06Eligibility = (clientId: number, id: string) => request<M06Eligibility>(`${subject(clientId, id)}/eligibility`);
