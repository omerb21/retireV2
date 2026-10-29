import { apiFetch, buildApiUrl } from "./apiBase";

export interface ScenarioDraftDecision {
  decision_id: string;
  source_product_id: string;
  source_component_id: string;
  component_code: string;
  amount: string;
  action: "pension" | "capital_asset";
  effective_date: string;
  validation_state: "unverified" | "needs_revalidation";
  product_version_at_review: number | null;
  source_fingerprint_at_review: string | null;
  ruleset_digest_at_review: string | null;
  permission_preview_id_at_review: string | null;
}
export interface ScenarioDraft {
  scenario_id: string;
  client_id: number;
  name: string;
  status: "draft" | "needs_revalidation" | "archived";
  version: number;
  created_by: string;
  updated_by: string;
  decisions: ScenarioDraftDecision[];
  financial_validation: "not_evaluated";
}
export interface DraftDecisionInput {
  decision_id?: string;
  source_product_id: string;
  source_component_id: string;
  component_code: string;
  amount: string;
  action: ScenarioDraftDecision["action"];
  effective_date: string;
}
async function request<T>(clientId: number, suffix: string, method = "GET", body?: unknown): Promise<T> {
  const response = await apiFetch(buildApiUrl(`/clients/${clientId}/scenario-drafts${suffix}`), {
    method, ...(body === undefined ? {} : {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const code = error?.code ?? error?.detail?.code ?? "UNKNOWN_ERROR";
    throw new Error(code === "SCENARIO_VERSION_CONFLICT"
      ? "החלופה השתנתה בינתיים. יש לטעון אותה מחדש לפני עריכה."
      : `שמירת החלופה נכשלה (${code}).`);
  }
  return response.json() as Promise<T>;
}
export const listScenarioDrafts = (clientId: number) => request<ScenarioDraft[]>(clientId, "");
export const createScenarioDraft = (clientId: number, name: string) =>
  request<ScenarioDraft>(clientId, "", "POST", { name });
export const duplicateScenarioDraft = (clientId: number, id: string, name: string) =>
  request<ScenarioDraft>(clientId, `/${encodeURIComponent(id)}/duplicate`, "POST", { name });
const writeDecision = (decision: DraftDecisionInput): DraftDecisionInput => ({
  ...(decision.decision_id === undefined ? {} : { decision_id: decision.decision_id }),
  source_product_id: decision.source_product_id,
  source_component_id: decision.source_component_id,
  component_code: decision.component_code,
  amount: decision.amount,
  action: decision.action,
  effective_date: decision.effective_date,
});
export const replaceScenarioDraft = (
  clientId: number, scenario: ScenarioDraft, decisions: DraftDecisionInput[], name = scenario.name,
) => request<ScenarioDraft>(clientId, `/${encodeURIComponent(scenario.scenario_id)}`, "PUT", {
  expected_version: scenario.version, name, decisions: decisions.map(writeDecision),
});
export const renameScenarioDraft = (clientId: number, scenario: ScenarioDraft, name: string) =>
  request<ScenarioDraft>(clientId, `/${encodeURIComponent(scenario.scenario_id)}/rename`, "POST", {
    expected_version: scenario.version, name,
  });
export const archiveScenarioDraft = (clientId: number, scenario: ScenarioDraft) =>
  request<ScenarioDraft>(clientId, `/${encodeURIComponent(scenario.scenario_id)}/archive`, "POST", {
    expected_version: scenario.version,
  });
