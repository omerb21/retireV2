import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export type M05State = "draft" | "reconciled" | "warning_reviewed" | "blocked" | "superseded";
export type M05ComponentKind = "total_balance" | "contribution_component" | "severance_component" | "unknown_component";

export interface M05Candidate {
  candidate_id: string;
  intake_id: string;
  target_kind: "manual_record_review";
  provider_name: string | null;
  account_reference: string | null;
  product_context: Record<string, unknown>;
  statement_date: string | null;
  m03_revision_id: string | null;
  m04_revision_id: string | null;
  eligible: boolean;
  authoritative_current: boolean;
  exclusion_reason: string | null;
  informational_warnings: string[];
  subject_id: string | null;
}

export interface M05Value {
  value_id: string;
  evidence_identity: string;
  component_index: number | null;
  original_label: string | null;
  original_code: string | null;
  component_kind: M05ComponentKind;
  source_state: string;
  source_value: string | null;
  effective_state: string;
  effective_value: string | null;
  included_in_reconciliation: boolean;
  exclusion_reason: string | null;
}

export interface M05Adjustment {
  adjustment_id: string;
  evidence_identity: string;
  previous_effective_value: string;
  new_effective_value: string;
  reason_code: string;
  explanation: string;
  confirmed: boolean;
  actor: string;
  actor_is_authentication: false;
  created_at: string;
}

export interface M05Revision {
  revision_id: string;
  subject_id: string;
  candidate_id: string;
  intake_id: string;
  target_kind: "manual_record_review";
  m03_revision_id: string;
  m04_revision_id: string;
  predecessor_revision_id: string | null;
  revision_sequence: number;
  state: M05State;
  action_type: "start" | "reconcile" | "review_warning" | "mark_blocked" | "adjust" | "supersede" | "revalidate";
  provider_name: string;
  account_reference: string;
  product_context: Record<string, unknown>;
  statement_date: string;
  evaluation_date: string;
  is_stale: boolean;
  source_snapshot_digest: string;
  mapping_digest: string;
  currency: "ILS";
  currency_confirmed: boolean;
  currency_confirmation_evidence: Record<string, unknown>;
  source_total_state: string;
  source_total_value: string | null;
  effective_total_state: string;
  effective_total_value: string | null;
  signed_discrepancy: string | null;
  absolute_discrepancy: string | null;
  tolerance_satisfied: boolean | null;
  algorithm_version: "m05-reconciliation-v1";
  included_evidence: Record<string, unknown>[];
  excluded_evidence: Record<string, unknown>[];
  warnings: { warning_id: string; classification: "mandatory" | "informational" }[];
  warning_dispositions: Record<string, unknown>[];
  provenance: Record<string, unknown>;
  reason_code: string | null;
  explanation: string | null;
  actor: string;
  actor_is_authentication: false;
  created_at: string;
  values: M05Value[];
  adjustment: M05Adjustment | null;
}

export interface M05Eligibility {
  subject_id: string;
  eligible_for_m06: boolean;
  current_revision_id: string | null;
  exclusion_reasons: string[];
  informational_warnings: string[];
  meaning: "technically eligible for consumption by a separately authorized M06 package";
}

export interface M05Subject {
  subject_id: string;
  client_id: number;
  provider_name: string;
  account_reference: string;
  current_revision: M05Revision | null;
  eligibility: M05Eligibility;
}

async function request<T>(path: string, init: RequestInit = { method: "GET" }): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new ApiTransportError({ status: response.status, statusText: response.statusText, body });
  }
  return body as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const root = (clientId: number) => `/clients/${clientId}/m05`;
const subjectRoot = (clientId: number, subjectId: string) =>
  `${root(clientId)}/subjects/${encodeURIComponent(subjectId)}`;

export const listM05Candidates = (clientId: number) => request<M05Candidate[]>(`${root(clientId)}/candidates`);
export const listM05Subjects = (clientId: number) => request<M05Subject[]>(`${root(clientId)}/subjects`);
export const getM05Subject = (clientId: number, subjectId: string) => request<M05Subject>(subjectRoot(clientId, subjectId));
export const getM05History = (clientId: number, subjectId: string) => request<M05Revision[]>(`${subjectRoot(clientId, subjectId)}/history`);
export const getM05Provenance = (clientId: number, subjectId: string) => request<Record<string, unknown>>(`${subjectRoot(clientId, subjectId)}/provenance`);
export const getM05Warnings = (clientId: number, subjectId: string) => request<Record<string, unknown>[]>(`${subjectRoot(clientId, subjectId)}/warnings`);
export const getM05Eligibility = (clientId: number, subjectId: string) => request<M05Eligibility>(`${subjectRoot(clientId, subjectId)}/m06-eligibility`);

export const startM05 = (clientId: number, candidateId: string, confirmCurrency: boolean) =>
  request<M05Revision>(`${root(clientId)}/start`, json({
    candidate_id: candidateId,
    ...(confirmCurrency ? { confirm_currency_ils: true } : {}),
  }));
export const reconcileM05 = (clientId: number, subjectId: string, expected: string, confirmCurrency: boolean) =>
  request<M05Revision>(`${subjectRoot(clientId, subjectId)}/reconcile`, json({
    expected_current_revision_id: expected,
    ...(confirmCurrency ? { confirm_currency_ils: true } : {}),
  }));

export type M05ReasonPayload = {
  expected_current_revision_id: string;
  reason_code: string;
  explanation: string;
};
export const reasonActionM05 = (
  clientId: number,
  subjectId: string,
  action: "mark-blocked" | "supersede",
  payload: M05ReasonPayload,
) => request<M05Revision>(`${subjectRoot(clientId, subjectId)}/${action}`, json(payload));
export const reviewWarningsM05 = (
  clientId: number,
  subjectId: string,
  payload: M05ReasonPayload & { mandatory_warning_ids: string[]; confirmed: true; confirm_currency_ils?: true },
) => request<M05Revision>(`${subjectRoot(clientId, subjectId)}/review-warning`, json(payload));
export const adjustM05 = (
  clientId: number,
  subjectId: string,
  payload: M05ReasonPayload & { evidence_identity: string; new_effective_value: string; confirmed: true },
) => request<M05Revision>(`${subjectRoot(clientId, subjectId)}/adjust`, json(payload));
export const revalidateM05 = (
  clientId: number,
  subjectId: string,
  payload: M05ReasonPayload & { candidate_id: string },
) => request<M05Revision>(`${subjectRoot(clientId, subjectId)}/revalidate`, json(payload));
