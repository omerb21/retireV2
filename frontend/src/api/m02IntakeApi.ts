import { ApiTransportError } from "./clientsApi";
import { buildApiUrl } from "./apiBase";

export type M02LifecycleStatus =
  | "uploaded"
  | "metadata_review"
  | "accepted_for_review"
  | "rejected"
  | "superseded";

export interface M02Source {
  source_id: string;
  original_filename: string;
  sanitized_download_filename: string;
  normalized_extension: string;
  declared_mime_type: string;
  validated_media_type: string;
  detected_text_encoding: string | null;
  sha256_checksum: string;
  byte_size: number;
  source_type: string;
  declared_statement_date: string | null;
  preservation_status: "preserved";
  validation_diagnostics: string[];
  uploaded_at: string;
}

export interface M02Intake {
  intake_id: string;
  client_id: number;
  record_kind: "manual" | "uploaded_source";
  declared_provider_name: string | null;
  product_name: string | null;
  product_identifier: string | null;
  declared_account_reference: string | null;
  manual_technical_reference: string | null;
  manual_technical_reference_is_account: false;
  declared_total_balance_amount: string | number | null;
  declared_monthly_pension_amount: string | number | null;
  declared_component_values: Array<{ label: string; value: string }> | null;
  declared_statement_date: string | null;
  declared_start_date: string | null;
  declared_product_type: string | null;
  source_type: string;
  declared_basis: string | null;
  notes: string | null;
  lifecycle_status: M02LifecycleStatus;
  preservation_status: "not_applicable" | "pending" | "preserved" | "failed";
  preservation_failure_code: string | null;
  rejection_reason_code: string | null;
  duplicate_candidate: boolean;
  duplicate_of_intake_id: string | null;
  superseding_candidate: boolean;
  superseding_intake_id: string | null;
  allowed_lifecycle_targets: M02LifecycleStatus[];
  diagnostics: string[];
  source: M02Source | null;
  created_by_actor: string;
  updated_by_actor: string;
  lifecycle_decided_by_actor: string;
  lifecycle_decided_at: string;
  actor_is_authentication: false;
  created_at: string;
  updated_at: string;
}

export interface M02ManualPayload {
  declared_provider_name: string | null;
  product_name: string | null;
  product_identifier: string | null;
  declared_account_reference: string | null;
  declared_total_balance_amount: string | null;
  declared_monthly_pension_amount: string | null;
  declared_component_values: Array<{ label: string; value: string }> | null;
  declared_statement_date: string | null;
  declared_start_date: string | null;
  declared_product_type: string | null;
  source_type: string;
  declared_basis: string | null;
  notes: string | null;
}

export interface M02UploadResult {
  selection_index: number;
  original_filename: string;
  status: "preserved" | "failed";
  intake: M02Intake | null;
  error_code: string | null;
  error_message: string | null;
}

export interface M02UploadBatch {
  results: M02UploadResult[];
  request_error: { code: string; message: string } | null;
}

export interface M02Download {
  blob: Blob;
  filename: string;
  headers: Headers;
}

async function responseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const body = await responseBody(response);
  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body
    });
  }
  return body as T;
}

function jsonInit(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) })
  };
}

export function listM02Intakes(clientId: number): Promise<M02Intake[]> {
  return request(`/clients/${clientId}/m02/intakes`, { method: "GET" });
}

export function createM02ManualIntake(
  clientId: number,
  payload: M02ManualPayload
): Promise<M02Intake> {
  return request(`/clients/${clientId}/m02/intakes/manual`, jsonInit("POST", payload));
}

export function updateM02Intake(
  clientId: number,
  intakeId: string,
  payload: Partial<M02ManualPayload>
): Promise<M02Intake> {
  return request(
    `/clients/${clientId}/m02/intakes/${encodeURIComponent(intakeId)}`,
    jsonInit("PUT", payload)
  );
}

export function transitionM02Intake(
  clientId: number,
  intakeId: string,
  targetStatus: M02LifecycleStatus
): Promise<M02Intake> {
  const payload =
    targetStatus === "rejected"
      ? { target_status: targetStatus, rejection_reason_code: "USER_REJECTED" }
      : { target_status: targetStatus };
  return request(
    `/clients/${clientId}/m02/intakes/${encodeURIComponent(intakeId)}/lifecycle`,
    jsonInit("POST", payload)
  );
}

export function uploadM02Sources(
  clientId: number,
  files: File[],
  metadata: {
    sourceType: string;
    declaredProviderName?: string;
    productName?: string;
    productIdentifier?: string;
    declaredAccountReference?: string;
    declaredStatementDate?: string;
    declaredStartDate?: string;
    declaredProductType?: string;
    declaredBasis?: string;
    notes?: string;
  }
): Promise<M02UploadBatch> {
  const body = new FormData();
  files.forEach((file) => body.append("files", file, file.name));
  body.append("source_type", metadata.sourceType);
  if (metadata.declaredProviderName) {
    body.append("declared_provider_name", metadata.declaredProviderName);
  }
  if (metadata.productName) {
    body.append("product_name", metadata.productName);
  }
  if (metadata.productIdentifier) {
    body.append("product_identifier", metadata.productIdentifier);
  }
  if (metadata.declaredAccountReference) {
    body.append("declared_account_reference", metadata.declaredAccountReference);
  }
  if (metadata.declaredStatementDate) {
    body.append("declared_statement_date", metadata.declaredStatementDate);
  }
  if (metadata.declaredStartDate) {
    body.append("declared_start_date", metadata.declaredStartDate);
  }
  if (metadata.declaredProductType) {
    body.append("declared_product_type", metadata.declaredProductType);
  }
  if (metadata.declaredBasis) {
    body.append("declared_basis", metadata.declaredBasis);
  }
  if (metadata.notes) {
    body.append("notes", metadata.notes);
  }
  return request(`/clients/${clientId}/m02/intakes/upload`, {
    method: "POST",
    body
  });
}

export async function downloadM02Source(
  clientId: number,
  source: M02Source
): Promise<M02Download> {
  const response = await fetch(
    buildApiUrl(
      `/clients/${clientId}/m02/sources/${encodeURIComponent(source.source_id)}/download`
    )
  );
  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body: await responseBody(response)
    });
  }
  const disposition = response.headers.get("content-disposition") ?? "";
  const encodedFilename = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  let filename = source.original_filename;
  if (encodedFilename) {
    try {
      filename = decodeURIComponent(encodedFilename);
    } catch {
      filename = source.original_filename;
    }
  }
  return {
    blob: await response.blob(),
    filename,
    headers: response.headers
  };
}
