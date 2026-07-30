import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export type M04State = "under_review" | "proposed" | "accepted" | "unresolved" | "rejected";
export type M04ProductFamily =
  | "insurance_policy" | "savings_policy" | "provident_fund"
  | "investment_provident_fund" | "education_fund" | "pension_fund"
  | "unknown_or_unresolved";
export type M04ComponentKind =
  | "severance_component" | "contribution_component" | "unknown_component";
export type M04Interpretation = "pension" | "capital" | "mixed" | "unresolved";
export type M04ComponentInterpretation = "pension" | "capital" | "unresolved";

export interface M04Component {
  component_decision_id: string;
  evidence_identity: string;
  original_label: string | null;
  original_code: string | null;
  component_kind: M04ComponentKind;
  interpretation: M04ComponentInterpretation;
  matched_rule_evidence: Record<string, unknown>[];
  explanation: string;
  current_employer_related: "yes" | "no" | "unknown";
}

export interface M04Revision {
  revision_id: string;
  revision_sequence: number;
  predecessor_revision_id: string | null;
  historical_revision_id: string | null;
  state: M04State;
  action_type: "start" | "proposal" | "unresolved" | "accept" | "reject"
    | "reopen" | "override" | "undo" | "start_revalidation";
  product_family: M04ProductFamily | null;
  pension_subtype: string | null;
  aggregate_interpretation: M04Interpretation | null;
  explanation: string | null;
  reason_code: string | null;
  reason: string | null;
  catalogue_version: "m04-rules-v1";
  matched_rule_evidence: Record<string, unknown>[];
  match_basis: string;
  action_evidence: Record<string, unknown>;
  input_snapshot: Record<string, unknown>;
  actor: string;
  actor_is_authentication: false;
  created_at: string;
  components: M04Component[];
}

export interface M04Eligibility {
  eligible_for_m05: boolean;
  exclusion_reason: string | null;
  current_revision_id: string | null;
  accepted_revision_id: string | null;
  m03_revision_id: string | null;
  meaning: string;
}

export interface M04Target {
  client_id: number;
  intake_id: string;
  target_kind: "source_evidence_review" | "manual_record_review";
  record_kind: "manual" | "uploaded_source";
  m01_lifecycle_status: string;
  m02_lifecycle_status: string;
  m03_eligible: boolean;
  m03_exclusion_reason: string | null;
  m03_accepted_revision_id: string | null;
  source_id: string | null;
  declared_provider_name: string | null;
  product_name: string | null;
  declared_product_type: string | null;
  product_identifier: string | null;
  declared_account_reference: string | null;
  declared_component_values: Record<string, unknown>[];
  current_revision: M04Revision | null;
  eligibility: M04Eligibility;
}

export interface M04RulePreview {
  catalogue_version: "m04-rules-v1";
  product_family: M04ProductFamily;
  aggregate_interpretation: M04Interpretation;
  components: M04Component[];
  matched_rule_evidence: Record<string, unknown>[];
  conflicts: string[];
  unresolved_reasons: string[];
  persists_revision: false;
}

async function request<T>(path: string, init: RequestInit = { method: "GET" }): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body,
    });
  }
  return body as T;
}

const json = (body?: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
});

const root = (clientId: number, intakeId?: string) =>
  `/clients/${clientId}/m04${intakeId ? `/targets/${encodeURIComponent(intakeId)}` : ""}`;

export const listM04Targets = (clientId: number) =>
  request<M04Target[]>(`${root(clientId)}/targets`);
export const getM04Target = (clientId: number, intakeId: string) =>
  request<M04Target>(root(clientId, intakeId));
export const getM04History = (clientId: number, intakeId: string) =>
  request<M04Revision[]>(`${root(clientId, intakeId)}/history`);
export const previewM04Rules = (clientId: number, intakeId: string) =>
  request<M04RulePreview>(`${root(clientId, intakeId)}/preview`);
export const getM04Eligibility = (clientId: number, intakeId: string) =>
  request<M04Eligibility>(`${root(clientId, intakeId)}/eligibility`);
export const getM04MatchedRules = (clientId: number, intakeId: string) =>
  request<Record<string, unknown>[]>(`${root(clientId, intakeId)}/matched-rules`);

export const startM04 = (clientId: number, intakeId: string) =>
  request<M04Revision>(`${root(clientId, intakeId)}/start`, json());
export const createM04Proposal = (clientId: number, intakeId: string, expected: string) =>
  request<M04Revision>(`${root(clientId, intakeId)}/proposal`, json({
    expected_current_revision_id: expected,
  }));

export type M04ReasonPayload = {
  expected_current_revision_id: string;
  reason_code: string;
  explanation: string;
};
export const actOnM04 = (
  clientId: number,
  intakeId: string,
  action: "unresolved" | "accept" | "reject" | "reopen" | "start-revalidation",
  payload: M04ReasonPayload,
) => request<M04Revision>(`${root(clientId, intakeId)}/${action}`, json(payload));

export type M04OverridePayload = M04ReasonPayload & {
  confirmed: true;
  product_family: M04ProductFamily;
  pension_subtype: null;
  components: {
    evidence_identity: string;
    component_kind: M04ComponentKind;
    interpretation: M04ComponentInterpretation;
    current_employer_related: "yes" | "no" | "unknown";
    explanation: string;
  }[];
};
export const overrideM04 = (
  clientId: number,
  intakeId: string,
  payload: M04OverridePayload,
) => request<M04Revision>(`${root(clientId, intakeId)}/override`, json(payload));

export const undoM04 = (
  clientId: number,
  intakeId: string,
  payload: M04ReasonPayload & { confirmed: true; historical_revision_id: string },
) => request<M04Revision>(`${root(clientId, intakeId)}/undo`, json(payload));
