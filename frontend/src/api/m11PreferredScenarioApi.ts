import { apiFetch, buildApiUrl } from "./apiBase";

export interface M11Selection {
  selection_id: string;
  client_id: number;
  scenario_id: string;
  scenario_version: number;
  revision: number;
  rationale: string;
  saved_at: string | null;
  calculation_references: Array<{ kind: string; run_id: string; fingerprint?: string }>;
  professional_approval: false;
}
export interface M11SelectionState {
  client_id: number;
  current: M11Selection | null;
  revision: number;
  outdated: boolean;
  history: M11Selection[];
  calculation_authorized: false;
  report_authorized: false;
}
async function request(clientId: number, method = "GET", body?: unknown): Promise<M11SelectionState> {
  const response = await apiFetch(buildApiUrl(`/clients/${clientId}/preferred-scenario`), {
    method, ...(body === undefined ? {} : {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const code = error?.code ?? "UNKNOWN_ERROR";
    if (code === "M11_SCENARIO_VERSION_CONFLICT" || code === "M11_SELECTION_VERSION_CONFLICT")
      throw new Error("החלופה או הבחירה השתנו. יש לרענן את התיק לפני שמירה נוספת.");
    throw new Error(`שמירת הבחירה נכשלה (${code}).`);
  }
  return response.json() as Promise<M11SelectionState>;
}
export const readM11Selection = (clientId: number) => request(clientId);
export const saveM11Selection = (clientId: number, payload: {
  scenario_id: string; expected_scenario_version: number;
  expected_selection_revision: number; rationale: string;
}) => request(clientId, "PUT", payload);
