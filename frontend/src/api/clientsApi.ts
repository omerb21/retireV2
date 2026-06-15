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

export interface ClientListItem {
  client_id: number;
  full_name: string;
  id_number: string;
  birth_date: string | null;
}

export type ClientDetailItem = ClientListItem;

export interface ClientCreatePayload {
  full_name: string;
  id_number: string;
  birth_date: string | null;
}

export interface ClientProfileItem {
  client_profile_id: string;
  client_id: number;
  birth_date: string | null;
  gender: string | null;
  notes: string | null;
}

export interface ClientProfileResponse {
  profile: ClientProfileItem | null;
}

export interface ClientProfileUpdatePayload {
  birth_date: string | null;
  gender: string | null;
  notes: string | null;
}

export interface EmploymentRecordItem {
  employment_record_id: string;
  client_id: number;
  employer_name: string;
  work_start_date: string;
  work_end_date: string | null;
  is_current: boolean;
  notes: string | null;
}

export interface GrantItem {
  grant_id: string;
  client_id: number;
  employment_record_id: string | null;
  employer_name: string | null;
  nominal_amount: number | string | null;
  indexed_amount: number | string;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
  notes: string | null;
}

export interface ActualCapitalizationItem {
  capitalization_id: string;
  client_id: number;
  amount: number | string;
  capitalization_date: string;
  source_label: string | null;
  notes: string | null;
}

export interface ActualCapitalizationCreatePayload {
  amount: number;
  capitalization_date: string;
  source_label: string | null;
  notes: string | null;
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
      ...(init.headers ?? {})
    }
  });

  const body = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body
    });
  }

  return body as T;
}

export function getClients(): Promise<ClientListItem[]> {
  return requestJson<ClientListItem[]>("/clients", {
    method: "GET"
  });
}

export function getClient(clientId: number): Promise<ClientDetailItem> {
  return requestJson<ClientDetailItem>(`/clients/${clientId}`, {
    method: "GET"
  });
}

export function createClient(payload: ClientCreatePayload): Promise<ClientDetailItem> {
  return requestJson<ClientDetailItem>("/clients", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getClientProfile(clientId: number): Promise<ClientProfileResponse> {
  return requestJson<ClientProfileResponse>(`/clients/${clientId}/profile`, {
    method: "GET"
  });
}

export function updateClientProfile(
  clientId: number,
  payload: ClientProfileUpdatePayload
): Promise<ClientProfileResponse> {
  return requestJson<ClientProfileResponse>(`/clients/${clientId}/profile`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getEmploymentRecords(clientId: number): Promise<EmploymentRecordItem[]> {
  return requestJson<EmploymentRecordItem[]>(`/clients/${clientId}/employment-records`, {
    method: "GET"
  });
}

export function getGrants(clientId: number): Promise<GrantItem[]> {
  return requestJson<GrantItem[]>(`/clients/${clientId}/grants`, {
    method: "GET"
  });
}

export function getActualCapitalizations(clientId: number): Promise<ActualCapitalizationItem[]> {
  return requestJson<ActualCapitalizationItem[]>(`/clients/${clientId}/actual-capitalizations`, {
    method: "GET"
  });
}

export function createActualCapitalization(
  clientId: number,
  payload: ActualCapitalizationCreatePayload
): Promise<ActualCapitalizationItem> {
  return requestJson<ActualCapitalizationItem>(`/clients/${clientId}/actual-capitalizations`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
