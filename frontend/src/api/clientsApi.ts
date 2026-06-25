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

export interface ClientListItem {
  client_id: number;
  full_name: string;
  id_number: string;
  birth_date: string | null;
  file_status: string;
  professional_identification_status: string;
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
  id_number: string | null;
  birth_date: string | null;
  gender: string | null;
  contact_method: string | null;
  contact_details: string | null;
  notes: string | null;
  file_status: string;
  professional_identification_status: string;
}

export interface ClientProfileResponse {
  profile: ClientProfileItem | null;
}

export interface ClientProfileUpdatePayload {
  id_number: string | null;
  birth_date: string | null;
  gender: string | null;
  contact_method: string | null;
  contact_details: string | null;
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

export interface EmploymentRecordPayload {
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

export interface GrantPayload {
  employment_record_id: string | null;
  employer_name: string | null;
  nominal_amount: number | null;
  indexed_amount: number;
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

export interface ActualCapitalizationPayload {
  amount: number;
  capitalization_date: string;
  source_label: string | null;
  notes: string | null;
}

export interface ClearinghouseSnapshotItem {
  clearinghouse_snapshot_id: string;
  client_id: number;
  import_date: string;
  source_type: string;
  source_file: string;
  collection_status: string;
  collection_notes: string | null;
  verification_status: string;
  verification_notes: string | null;
  verified_at: string | null;
  created_at: string;
}

export interface ClearinghouseSnapshotPayload {
  import_date: string;
  source_type: string;
  source_file: string;
  collection_status: string;
  collection_notes: string | null;
}

export interface RetirementPlanningDocumentItem {
  document_id: string;
  client_id: number;
  document_type: string;
  source_type: string | null;
  source_file: string;
  collection_date: string;
  collection_status: string;
  collection_notes: string | null;
  verification_status: string;
  verification_notes: string | null;
  verified_at: string | null;
  created_at: string;
}

export interface RetirementPlanningDocumentPayload {
  document_type: string;
  source_type: string | null;
  source_file: string;
  collection_date: string;
  collection_status: string;
  collection_notes: string | null;
}

export interface VerificationUpdatePayload {
  verification_status: string;
  verification_notes: string | null;
}

export interface MissingDataItem {
  missing_data_item_id: string;
  client_id: number;
  missing_item_type: string;
  missing_item_label: string;
  missing_status: string;
  notes: string | null;
  created_at: string;
}

export interface MissingDataItemPayload {
  missing_item_type: string;
  missing_item_label: string;
  missing_status: string;
  notes: string | null;
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
  return requestJson<unknown>("/clients", {
    method: "GET"
  }).then((body) => {
    if (!Array.isArray(body)) {
      throw new Error("Unexpected clients response shape.");
    }

    return body as ClientListItem[];
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

export function createEmploymentRecord(
  clientId: number,
  payload: EmploymentRecordPayload
): Promise<EmploymentRecordItem> {
  return requestJson<EmploymentRecordItem>(`/clients/${clientId}/employment-records`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateEmploymentRecord(
  clientId: number,
  employmentRecordId: string,
  payload: EmploymentRecordPayload
): Promise<EmploymentRecordItem> {
  return requestJson<EmploymentRecordItem>(`/clients/${clientId}/employment-records/${employmentRecordId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteEmploymentRecord(clientId: number, employmentRecordId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/employment-records/${employmentRecordId}`, {
    method: "DELETE"
  });
}

export function getGrants(clientId: number): Promise<GrantItem[]> {
  return requestJson<GrantItem[]>(`/clients/${clientId}/grants`, {
    method: "GET"
  });
}

export function createGrant(clientId: number, payload: GrantPayload): Promise<GrantItem> {
  return requestJson<GrantItem>(`/clients/${clientId}/grants`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateGrant(clientId: number, grantId: string, payload: GrantPayload): Promise<GrantItem> {
  return requestJson<GrantItem>(`/clients/${clientId}/grants/${grantId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteGrant(clientId: number, grantId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/grants/${grantId}`, {
    method: "DELETE"
  });
}

export function getActualCapitalizations(clientId: number): Promise<ActualCapitalizationItem[]> {
  return requestJson<ActualCapitalizationItem[]>(`/clients/${clientId}/actual-capitalizations`, {
    method: "GET"
  });
}

export function createActualCapitalization(
  clientId: number,
  payload: ActualCapitalizationPayload
): Promise<ActualCapitalizationItem> {
  return requestJson<ActualCapitalizationItem>(`/clients/${clientId}/actual-capitalizations`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateActualCapitalization(
  clientId: number,
  capitalizationId: string,
  payload: ActualCapitalizationPayload
): Promise<ActualCapitalizationItem> {
  return requestJson<ActualCapitalizationItem>(`/clients/${clientId}/actual-capitalizations/${capitalizationId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteActualCapitalization(clientId: number, capitalizationId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/actual-capitalizations/${capitalizationId}`, {
    method: "DELETE"
  });
}

export function getClearinghouseSnapshots(clientId: number): Promise<ClearinghouseSnapshotItem[]> {
  return requestJson<ClearinghouseSnapshotItem[]>(`/clients/${clientId}/clearinghouse-snapshots`, {
    method: "GET"
  });
}

export function createClearinghouseSnapshot(
  clientId: number,
  payload: ClearinghouseSnapshotPayload
): Promise<ClearinghouseSnapshotItem> {
  return requestJson<ClearinghouseSnapshotItem>(`/clients/${clientId}/clearinghouse-snapshots`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateClearinghouseSnapshotVerification(
  clientId: number,
  clearinghouseSnapshotId: string,
  payload: VerificationUpdatePayload
): Promise<ClearinghouseSnapshotItem> {
  return requestJson<ClearinghouseSnapshotItem>(
    `/clients/${clientId}/clearinghouse-snapshots/${clearinghouseSnapshotId}/verification`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    }
  );
}

export function getRetirementPlanningDocuments(clientId: number): Promise<RetirementPlanningDocumentItem[]> {
  return requestJson<RetirementPlanningDocumentItem[]>(`/clients/${clientId}/documents`, {
    method: "GET"
  });
}

export function createRetirementPlanningDocument(
  clientId: number,
  payload: RetirementPlanningDocumentPayload
): Promise<RetirementPlanningDocumentItem> {
  return requestJson<RetirementPlanningDocumentItem>(`/clients/${clientId}/documents`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRetirementPlanningDocumentVerification(
  clientId: number,
  documentId: string,
  payload: VerificationUpdatePayload
): Promise<RetirementPlanningDocumentItem> {
  return requestJson<RetirementPlanningDocumentItem>(`/clients/${clientId}/documents/${documentId}/verification`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getMissingDataItems(clientId: number): Promise<MissingDataItem[]> {
  return requestJson<MissingDataItem[]>(`/clients/${clientId}/missing-items`, {
    method: "GET"
  });
}

export function createMissingDataItem(
  clientId: number,
  payload: MissingDataItemPayload
): Promise<MissingDataItem> {
  return requestJson<MissingDataItem>(`/clients/${clientId}/missing-items`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
