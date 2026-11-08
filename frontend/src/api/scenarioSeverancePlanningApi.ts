import { apiFetch, buildApiUrl } from "./apiBase";

export type SeveranceChoiceKind =
  | "UNDECIDED" | "PLANNED_WITHDRAWAL"
  | "PLANNED_PENSION_CONTINUITY" | "PLANNED_SEVERANCE_CONTINUITY";

export interface SeveranceChoiceInput {
  source_kind: "grant" | "pension_component";
  source_id: string;
  choice: SeveranceChoiceKind;
  planned_amount_ils: string | null;
}

export interface SavedSeveranceChoice extends SeveranceChoiceInput {
  client_id: number;
  scenario_id: string;
  current_scenario_version: number;
  saved_from_scenario_version: number;
  source_fingerprint: string;
  state: string;
  execution_allowed: false;
  professional_authority: false;
  actual_paid_amount_ils: null;
  future_payable_amount_ils: null;
  exempt_amount_ils: null;
  net_amount_ils: null;
}

export interface SeverancePlanningSnapshot {
  client_id: number;
  scenario_id: string;
  scenario_version: number;
  choices: SavedSeveranceChoice[];
  authority_state: "DRAFT_ONLY";
  execution_allowed: false;
}

async function request(
  clientId: number, scenarioId: string, body?: { expected_version: number; choices: SeveranceChoiceInput[] },
): Promise<SeverancePlanningSnapshot> {
  const response = await apiFetch(
    buildApiUrl(`/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/severance-planning`),
    body ? {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    } : { method: "GET" },
  );
  if (!response.ok) {
    const details = await response.json().catch(() => null);
    const code = details?.code ?? details?.detail?.code ?? "UNKNOWN_ERROR";
    throw new Error(code === "SCENARIO_VERSION_CONFLICT"
      ? "החלופה השתנתה. יש לרענן אותה לפני שמירת החלטות הפיצויים."
      : `לא ניתן לטעון או לשמור החלטות פיצויים (${code}).`);
  }
  const result = await response.json() as SeverancePlanningSnapshot;
  if (result.client_id !== clientId || result.scenario_id !== scenarioId) {
    throw new Error("השרת החזיר החלטות פיצויים מחלופה או מלקוח אחרים.");
  }
  return result;
}
export const readSeverancePlanning = (clientId: number, scenarioId: string) =>
  request(clientId, scenarioId);
export const saveSeverancePlanning = (
  clientId: number, scenarioId: string, expected_version: number, choices: SeveranceChoiceInput[],
) => request(clientId, scenarioId, { expected_version, choices });
