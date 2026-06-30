import { buildApiUrl } from "./apiBase";

export interface ApiTransportErrorShape {
  status: number;
  statusText: string;
  body: unknown;
}

export class ApiTransportError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor({ status, statusText, body }: ApiTransportErrorShape) {
    super(`HTTP ${status} ${statusText}`.trim());
    this.name = "ApiTransportError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export interface FixationGrantInputPayload {
  grant_id: string;
  employer_name: string | null;
  nominal_amount: number | null;
  indexed_amount: number;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
}

export interface FixationActualCapitalizationInputPayload {
  capitalization_id: string;
  amount: number;
  capitalization_date: string;
  source_label: string | null;
  notes: string | null;
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
  eligibility_date: string;
  eligibility_year: number;
  monthly_cap: number;
  exemption_percentage: number;
  capital_multiplier: number;
  grants: FixationGrantInputPayload[];
  future_grant_reserved: number;
  actual_capitalizations: FixationActualCapitalizationInputPayload[];
  idf: FixationIdfInputPayload | null;
  metadata?: Record<string, unknown> | null;
}

export type FixationReviewCollectionState = "unknown" | "not_collected" | "confirmed_none" | "items_recorded";
export type FixationReviewDisposition = "include" | "exclude";

export interface FixationGrantReviewItemPayload extends FixationGrantInputPayload {
  source_item_id: string;
  disposition: FixationReviewDisposition;
}

export interface FixationActualCapitalizationReviewItemPayload extends FixationActualCapitalizationInputPayload {
  source_item_id: string;
  source_basis: string | null;
  planner_assertion: string | null;
  planner_assertion_basis: string | null;
  disposition: FixationReviewDisposition;
}

export interface FixationReviewDomainPayload<TItem> {
  collection_state: FixationReviewCollectionState;
  items: TItem[];
}

export interface FixationInputReviewPayload {
  calculation_id?: string | null;
  calculation_version: string;
  eligibility_date: string;
  eligibility_year: number;
  monthly_cap: number;
  exemption_percentage: number;
  capital_multiplier: number;
  grants: FixationReviewDomainPayload<FixationGrantReviewItemPayload>;
  future_grant_reserved: number;
  actual_capitalizations: FixationReviewDomainPayload<FixationActualCapitalizationReviewItemPayload>;
  idf: FixationIdfInputPayload | null;
  metadata?: Record<string, unknown> | null;
}

export interface FixationValidationErrorPayload {
  code: string;
  path: string;
  message: string;
  severity: "error";
  source_id: string | null;
}

export interface FixationReviewValidationResponse {
  valid: boolean;
  errors: FixationValidationErrorPayload[];
}

export interface FixationResultResponse {
  [key: string]: unknown;
}

export interface PlannerReviewContextDomainPayload {
  collection_state: FixationReviewCollectionState;
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
  input_data: Record<string, unknown>;
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

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
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

export function calculateFixation(payload: FixationInputPayload): Promise<FixationResultResponse> {
  return requestJson<FixationResultResponse>("/fixation/calculate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function validateFixation(payload: FixationInputPayload): Promise<FixationResultResponse> {
  return requestJson<FixationResultResponse>("/fixation/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function validateFixationReview(payload: FixationInputReviewPayload): Promise<FixationReviewValidationResponse> {
  return requestJson<FixationReviewValidationResponse>("/fixation/review/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function convertFixationReview(payload: FixationInputReviewPayload): Promise<FixationInputPayload> {
  return requestJson<FixationInputPayload>("/fixation/review/convert", {
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

export function getFixationRunDetail(runId: number): Promise<FixationRunDetailResponse> {
  return requestJson<FixationRunDetailResponse>(`/fixation/runs/${runId}`, {
    method: "GET",
  });
}

export function createInternalPlannerJudgment(
  runId: number,
  payload: InternalPlannerJudgmentCreatePayload,
): Promise<InternalPlannerJudgmentPayload> {
  return requestJson<InternalPlannerJudgmentPayload>(`/fixation/runs/${runId}/internal-planner-judgment`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
