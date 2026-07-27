import { buildApiUrl } from "./apiBase";

export class ApiTransportError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor({ status, statusText, body }: { status: number; statusText: string; body: unknown }) {
    super(`HTTP ${status} ${statusText}`.trim());
    this.name = "ApiTransportError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export type FixationCollectionState = "unknown" | "not_collected" | "confirmed_none" | "items_recorded";
export type FixationReviewCollectionState = FixationCollectionState;
export type FixationInclusionDecision = "include" | "exclude";
export type FixationSupportStatus = "supported" | "unsupported" | "requires_special_handling";

export interface M07CalculationInputSelection {
  field_code: "eligibility_date";
  candidate_identity: string;
  b1_evidence_revision_id: string;
}

export interface M07InputReference {
  b1_evidence_revision_id: string;
  selections: M07CalculationInputSelection[];
}

export interface AcceptedParameterSetPayload {
  parameter_set_id: string;
  client_id: number;
  tax_year: number;
  effective_from: string | null;
  effective_to: string | null;
  values: {
    monthly_cap: number;
    exemption_percentage: number;
    capital_multiplier: number;
    grant_impact_multiplier: number;
  };
  source_basis: string;
  status: "accepted" | "rejected";
  accepted_for_use: boolean;
  accepted_by: string;
  decision_timestamp: string;
}

export interface AcceptedItemEvidencePayload {
  source_basis: string;
  status: string;
  accepted_for_use: boolean;
  actor: string;
  decision_timestamp: string;
}

export interface AdmissibleGrantPayload extends AcceptedItemEvidencePayload {
  grant_id: string;
  client_id: number;
  item_type: string;
  employer_name: string | null;
  nominal_amount: number | null;
  indexed_amount: number | null;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
  inclusion_decision: FixationInclusionDecision;
  support_status: FixationSupportStatus;
  conflict_indicator: boolean;
  accepted_value: number | null;
  indexation_mode: "asserted_indexed_amount" | "cbs_system_calculation_required";
}

export interface AdmissibleActualCapitalizationPayload extends AcceptedItemEvidencePayload {
  capitalization_id: string;
  item_type: string;
  amount: number;
  capitalization_date: string;
  recorded_meaning: string;
  inclusion_decision: FixationInclusionDecision;
  support_status: FixationSupportStatus;
  conflict_indicator: boolean;
  accepted_value: number | null;
  notes: string | null;
}

export interface FutureGrantReservationPayload extends AcceptedItemEvidencePayload {
  amount: number;
}

export interface FixationIdfInputPayload {
  idf_id: string;
  reduction_amount: number;
  original_commutation_percent: number;
  current_commutation_percent: number;
  commutation_date: string;
  promoter_age_date: string;
  source_label: string | null;
}

export interface FixationInputPayload {
  calculation_id?: string | null;
  calculation_version: string;
  m07_input_reference: M07InputReference;
  parameter_set: AcceptedParameterSetPayload;
  grants_collection_state: FixationCollectionState;
  grants: AdmissibleGrantPayload[];
  future_grant_reservation: FutureGrantReservationPayload | null;
  actual_capitalizations_collection_state: FixationCollectionState;
  actual_capitalizations: AdmissibleActualCapitalizationPayload[];
  idf: FixationIdfInputPayload | null;
  metadata?: Record<string, unknown> | null;
}

export interface M07SourceReference {
  source_kind: "fact_evidence" | "planner_assertion";
  source_id: string;
  source_type?: string | null;
  assertion_id?: string | null;
}

export interface M07AmbiguousCandidate {
  normalized_value: string;
  candidate_identities: string[];
  source_references: M07SourceReference[];
}

export interface M07Resolution {
  client_id: number;
  calculation_scope: string;
  manifest_version: string;
  b1_evidence_revision_id: string;
  normalized_selected_values: Record<string, unknown>;
  source_references: Record<string, M07SourceReference[]>;
  missing_fields: string[];
  ambiguous_fields: Array<{
    field_code: string;
    candidates: M07AmbiguousCandidate[];
  }>;
  outcome: "resolved" | "missing_inputs" | "ambiguous_inputs";
  fingerprint: string;
}

export interface FixationValidationErrorPayload {
  code: string;
  path: string;
  message: string;
  severity: "error";
  source_id: string | null;
}

export interface FixationResultResponse {
  calculation_id?: string | null;
  calculation_version?: string | null;
  status:
    | "success"
    | "validation_failed"
    | "unsupported"
    | "requires_special_handling"
    | "calculation_failed"
    | "unsupported_calculation";
  validation_errors: FixationValidationErrorPayload[];
  m07_resolution?: M07Resolution | null;
  eligibility_date?: string;
  eligibility_year?: number;
  monthly_cap?: number;
  exemption_percentage?: number;
  capital_multiplier?: number;
  initial_exempt_capital?: number;
  grant_impact_total?: number;
  future_grant_reserved?: number;
  future_grant_impact?: number;
  actual_capitalization_impact?: number;
  idf_impact?: number;
  total_impact?: number;
  remaining_exempt_capital?: number;
  monthly_exempt_pension?: number;
  capital_exemption_percentage?: number;
  pension_exemption_percentage?: number;
  grant_results?: Array<Record<string, unknown>>;
  actual_capitalization_results?: Array<Record<string, unknown>>;
  audit_rows?: Array<Record<string, unknown>>;
}

export interface FixationEligibilityRevision {
  revision_id: string;
  profile_id: string;
  revision_number: number;
  status: "finalized";
  finalized_at: string;
  eligibility_outcome: "resolved" | "missing_inputs" | "ambiguous_inputs";
  eligibility_dates: string[];
}

export interface FixationEligibilityRevisionList {
  items: FixationEligibilityRevision[];
  offset: number;
  limit: number;
  total: number;
}

export interface FixationEligibilityRevisionCreated {
  revision_id: string;
  status: "finalized";
  finalized_at: string;
  eligibility_date: string;
  technical_actor: string;
}

export interface PlannerReviewContextDomainPayload {
  collection_state: FixationCollectionState;
  included_source_reference_ids: string[];
  excluded_source_reference_ids: string[];
}

export interface PlannerReviewContextPayload {
  grants: PlannerReviewContextDomainPayload;
  actual_capitalizations: PlannerReviewContextDomainPayload;
}

export type InternalPlannerHandlingStatus =
  | "not_used_for_decision"
  | "continue_internal_review"
  | "internal_action_identified";

export interface InternalPlannerJudgmentCreatePayload {
  handling_status: InternalPlannerHandlingStatus;
  next_internal_action: string;
  internal_note?: string | null;
}

export interface InternalPlannerJudgmentPayload extends InternalPlannerJudgmentCreatePayload {
  saved_run_id: number;
  internal_note: string | null;
}

export interface SaveFixationPayload {
  client_id: number;
  input_data: FixationInputPayload;
  planner_review_context?: PlannerReviewContextPayload;
}

export interface SaveFixationResponse {
  run_id: number;
  status: string;
}

export interface FixationHistoryEntry {
  run_id: number;
  status: string;
  calculation_version: string | null;
  created_at: string | null;
}

export interface FixationRunDetailResponse {
  run: Record<string, unknown>;
  input_snapshot: Record<string, unknown> | null;
  planner_review_context?: PlannerReviewContextPayload | null;
  internal_planner_judgment?: InternalPlannerJudgmentPayload | null;
  result: Record<string, unknown> | null;
  audit_rows: Array<Record<string, unknown>>;
  validation_errors: Array<Record<string, unknown>>;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  const body = await parseResponseBody(response);
  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body,
    });
  }
  return body as T;
}

export function listFixationEligibilityRevisions(clientId: number): Promise<FixationEligibilityRevisionList> {
  return requestJson<FixationEligibilityRevisionList>(`/clients/${clientId}/fixation/m07/revisions?limit=100`, {
    method: "GET",
  });
}

export function createFixationEligibilityRevision(
  clientId: number,
  eligibilityDate: string,
): Promise<FixationEligibilityRevisionCreated> {
  return requestJson<FixationEligibilityRevisionCreated>(
    `/clients/${clientId}/fixation/m07/eligibility-date-revisions`,
    {
      method: "POST",
      body: JSON.stringify({ eligibility_date: eligibilityDate }),
    },
  );
}

export function calculateFixation(clientId: number, payload: FixationInputPayload): Promise<FixationResultResponse> {
  return requestJson<FixationResultResponse>(`/clients/${clientId}/fixation/calculate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function validateFixation(clientId: number, payload: FixationInputPayload): Promise<FixationResultResponse> {
  return requestJson<FixationResultResponse>(`/clients/${clientId}/fixation/validate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveFixation(payload: SaveFixationPayload): Promise<SaveFixationResponse> {
  return requestJson<SaveFixationResponse>("/fixation/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFixationHistory(clientId: number): Promise<FixationHistoryEntry[]> {
  return requestJson<FixationHistoryEntry[]>(`/clients/${clientId}/fixation/history`, {
    method: "GET",
  });
}

export function getFixationRunDetail(clientId: number, runId: number): Promise<FixationRunDetailResponse> {
  return requestJson<FixationRunDetailResponse>(`/clients/${clientId}/fixation/runs/${runId}`, {
    method: "GET",
  });
}

export function createInternalPlannerJudgment(
  clientId: number,
  runId: number,
  payload: InternalPlannerJudgmentCreatePayload,
): Promise<InternalPlannerJudgmentPayload> {
  return requestJson<InternalPlannerJudgmentPayload>(
    `/clients/${clientId}/fixation/runs/${runId}/internal-planner-judgment`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
