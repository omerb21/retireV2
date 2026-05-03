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

export interface FixationInputPayload {
  calculation_id?: string | null;
  calculation_version: string;
  eligibility_date: string;
  eligibility_year: number;
  monthly_cap: number;
  exemption_percentage: number;
  capital_multiplier: number;
  grants: Array<Record<string, unknown>>;
  future_grant_reserved: number;
  actual_capitalizations: Array<Record<string, unknown>>;
  idf: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}

export interface FixationResultResponse {
  [key: string]: unknown;
}

export interface SaveFixationPayload {
  client_id: number;
  input_data: Record<string, unknown>;
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
  result: Record<string, unknown> | null;
  audit_rows: Array<Record<string, unknown>>;
  validation_errors: Array<Record<string, unknown>>;
}

const API_PREFIX = "/api";

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
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
