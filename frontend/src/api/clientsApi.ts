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
