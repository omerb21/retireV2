import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export type M06Mode = "balance_to_monthly_pension" | "monthly_pension_to_capital_equivalent";
export type M06Authority = "documentary" | "planner_declared";
export type M06State = "draft" | "resolved" | "warning_reviewed" | "blocked" | "superseded";

export interface M06Candidate {
  candidate_id: string; m05_subject_id: string; m05_revision_id: string; m02_intake_id: string;
  provider_name: string; account_reference: string; product_family: string; mode: M06Mode;
  input_identity: string; input_amount: string | null; input_date: string | null; formula_id: string;
  eligible: boolean; exclusion_reasons: string[]; informational_warnings: string[];
}
export interface CoefficientIntent {
  authority_class: M06Authority; coefficient: string; source_intake_id?: string;
  source_locator?: string; source_note?: string; reason: string; effective_from?: string;
  effective_to?: string; applicability_declared: boolean; metadata?: Record<string, unknown>;
}
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
const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const root = (clientId: number) => `/clients/${clientId}/m06`;
const subject = (clientId: number, subjectId: string) => `${root(clientId)}/subjects/${encodeURIComponent(subjectId)}`;

export const listM06Candidates = (clientId: number) => request<M06Candidate[]>(`${root(clientId)}/candidates`);
export const listM06Subjects = (clientId: number) => request<M06Subject[]>(`${root(clientId)}/subjects`);
export const getM06Subject = (clientId: number, id: string) => request<M06Subject>(subject(clientId, id));
export const getM06History = (clientId: number, id: string) => request<M06Revision[]>(`${subject(clientId, id)}/history`);
export const getM06Eligibility = (clientId: number, id: string) => request<M06Eligibility>(`${subject(clientId, id)}/eligibility`);
export const startM06 = (clientId: number, candidate: M06Candidate, coefficient: CoefficientIntent) => request<M06Revision>(`${root(clientId)}/start`, json({ m05_subject_id: candidate.m05_subject_id, mode: candidate.mode, input_identity: candidate.input_identity, coefficient }));
export const resolveM06 = (clientId: number, id: string, revision: string) => request<M06Revision>(`${subject(clientId, id)}/resolve`, json({ expected_current_revision_id: revision }));
export const reviewM06Warnings = (clientId: number, id: string, revision: string, warningIds: string[], explanation: string) => request<M06Revision>(`${subject(clientId, id)}/review-warning`, json({ expected_current_revision_id: revision, warning_ids: warningIds, reason_code: "planner_warning_review", explanation, confirmed: true }));
export const correctM06Coefficient = (clientId: number, id: string, revision: string, coefficient: CoefficientIntent, correctionReason: string) => request<M06Revision>(`${subject(clientId, id)}/correct-coefficient`, json({ expected_current_revision_id: revision, coefficient, correction_reason: correctionReason }));
export const supersedeM06 = (clientId: number, id: string, revision: string, reason: string) => request<M06Revision>(`${subject(clientId, id)}/supersede`, json({ expected_current_revision_id: revision, reason }));
