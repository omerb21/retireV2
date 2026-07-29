import { buildApiUrl } from "./apiBase";
import { ApiTransportError } from "./clientsApi";

export type M03ReviewState = "under_review" | "accepted" | "rejected";
export interface M03Revision {
  revision_id: string; revision_sequence: number; predecessor_revision_id: string | null;
  state: M03ReviewState; reason: string | null; actor: string;
  actor_is_authentication: false; decided_at: string;
}
export interface M03Target {
  client_id: number; intake_id: string;
  target_kind: "source_evidence_review" | "manual_record_review";
  m02_lifecycle_status: string; source_id: string | null; blob_id: string | null;
  sha256_checksum: string | null; current_revision: M03Revision | null;
  accepted_revision_id: string | null; eligible: boolean; exclusion_reason: string | null;
  eligibility_meaning: string;
}
export interface M03Annotation {
  annotation_id: string; review_revision_id: string; intake_id: string; source_id: string | null;
  topic: string; note: string; reason: string; actor: string; actor_is_authentication: false;
  supersedes_annotation_id: string | null; created_at: string;
}

async function request<T>(path: string, init: RequestInit = { method: "GET" }): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new ApiTransportError({ status: response.status, statusText: response.statusText, body });
  return body as T;
}
const json = (method: string, body?: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" },
  ...(body === undefined ? {} : { body: JSON.stringify(body) })
});
const root = (clientId: number, intakeId?: string) =>
  `/clients/${clientId}/m03${intakeId ? `/targets/${encodeURIComponent(intakeId)}` : ""}`;

export const listM03Candidates = (clientId: number) => request<M03Target[]>(`${root(clientId)}/candidates`);
export const getM03Target = (clientId: number, intakeId: string) => request<M03Target>(root(clientId, intakeId));
export const getM03Eligibility = (clientId: number, intakeId: string) => request<M03Target>(`${root(clientId, intakeId)}/eligibility`);
export const getM03History = (clientId: number, intakeId: string) => request<M03Revision[]>(`${root(clientId, intakeId)}/history`);
export const getM03Annotations = (clientId: number, intakeId: string) => request<M03Annotation[]>(`${root(clientId, intakeId)}/annotations`);
export const startM03Review = (clientId: number, intakeId: string) => request<M03Revision>(`${root(clientId, intakeId)}/start`, json("POST"));
export const decideM03Review = (clientId: number, intakeId: string, action: "accept" | "reject" | "reopen", reason: string, expected: string) =>
  request<M03Revision>(`${root(clientId, intakeId)}/${action}`, json("POST", { reason, expected_current_revision_id: expected }));
export const addM03Annotation = (clientId: number, intakeId: string, payload: {
  review_revision_id: string; topic: string; note: string; reason: string;
  supersedes_annotation_id?: string;
}) =>
  request<M03Annotation>(`${root(clientId, intakeId)}/annotations`, json("POST", payload));

export async function downloadM03Source(clientId: number, sourceId: string): Promise<void> {
  const response = await fetch(buildApiUrl(`/clients/${clientId}/m02/sources/${encodeURIComponent(sourceId)}/download`));
  if (!response.ok) throw new ApiTransportError({ status: response.status, statusText: response.statusText, body: await response.text() });
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = "m02-source"; anchor.click();
  URL.revokeObjectURL(url);
}
