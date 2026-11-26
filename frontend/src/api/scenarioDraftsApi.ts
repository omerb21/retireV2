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

/** Read-only, snapshot-scoped evidence. This contract never authorizes financial execution. */
export interface CalculationAdmissionEvidence {
  schema_version: "SCENARIO_CALCULATION_ADMISSION_V1";
  client_id: number;
  scenario_id: string;
  scenario_version: number;
  assessment_state: "blocked" | "gross_estimate_ready";
  financial_result: null | {
    result_type: "NONBINDING_GROSS_PENSION_FORECAST";
    monthly_pension_gross_ils: string;
    comparison_basis: { currency: "ILS"; income_basis: "GROSS"; retirement_target_date: string; source_reference_date: string };
    coefficient_provenance: Array<{
      decision_id: string; factor_value: string; factor_evidence_type: "INSURER_QUOTE" | "POLICY_CONTRACT" | "PLANNER_ASSUMPTION";
      factor_evidence_reference: string; factor_admission_revision: number;
      professional_admission_fingerprint: string; monthly_estimate_gross_ils: string;
      source_reference_date: string; retirement_target_date: string; result_fingerprint: string;
    }>;
    tax_calculated: false; net_calculated: false; aggregate_fingerprint: string;
  };
  warnings?: Array<"TAX_NOT_EVALUATED" | "NET_NOT_EVALUATED">;
  blockers: Array<{ code: string; decision_id: string | null }>;
}
export async function readCalculationAdmission(
  clientId: number, scenarioId: string, signal?: AbortSignal,
): Promise<CalculationAdmissionEvidence> {
  const response = await apiFetch(
    buildApiUrl(`/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/calculation-admission`),
    { method: "GET", signal, cache: "no-store" },
  );
  if (!response.ok) throw new Error(`ADMISSION_HTTP_${response.status}`);
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") throw new Error("ADMISSION_INVALID_RESPONSE");
  const value = body as Record<string, unknown>;
  if (value.schema_version !== "SCENARIO_CALCULATION_ADMISSION_V1"
      || value.client_id !== clientId || value.scenario_id !== scenarioId
      || !Number.isSafeInteger(value.scenario_version) || (value.scenario_version as number) < 1
      || (value.assessment_state !== "blocked" && value.assessment_state !== "gross_estimate_ready")
      || !Array.isArray(value.blockers)
      || !value.blockers.every(item => item && typeof item === "object"
        && typeof item.code === "string" && /^[A-Z0-9_]+$/.test(item.code)
        && (item.decision_id === null || typeof item.decision_id === "string"))) {
    throw new Error("ADMISSION_INVALID_RESPONSE");
  }
  const hash = (v: unknown) => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
  const money = (v: unknown) => typeof v === "string" && /^(?:0|[1-9]\d*)\.\d{2}$/.test(v);
  if (value.assessment_state === "blocked") {
    if (value.financial_result !== null) throw new Error("ADMISSION_INVALID_RESPONSE");
  } else {
    const result = value.financial_result as Record<string, unknown> | null;
    const basis = result?.comparison_basis as Record<string, unknown> | undefined;
    const rows = result?.coefficient_provenance;
    if (!result || value.blockers.length !== 0
        || result.result_type !== "NONBINDING_GROSS_PENSION_FORECAST"
        || !money(result.monthly_pension_gross_ils)
        || result.tax_calculated !== false || result.net_calculated !== false
        || !hash(result.aggregate_fingerprint)
        || basis?.currency !== "ILS" || basis.income_basis !== "GROSS"
        || typeof basis.retirement_target_date !== "string"
        || typeof basis.source_reference_date !== "string"
        || !Array.isArray(rows) || rows.length === 0
        || !rows.every(row => row && typeof row.decision_id === "string"
          && money(row.monthly_estimate_gross_ils) && hash(row.result_fingerprint)
          && hash(row.professional_admission_fingerprint)
          && typeof row.factor_evidence_reference === "string" && !!row.factor_evidence_reference
          && typeof row.factor_value === "string" && !!row.factor_value
          && ["INSURER_QUOTE", "POLICY_CONTRACT", "PLANNER_ASSUMPTION"].includes(row.factor_evidence_type)
          && Number.isSafeInteger(row.factor_admission_revision)
          && typeof row.source_reference_date === "string"
          && typeof row.retirement_target_date === "string")
        || !Array.isArray(value.warnings)
        || !value.warnings.includes("TAX_NOT_EVALUATED")
        || !value.warnings.includes("NET_NOT_EVALUATED")) {
      throw new Error("ADMISSION_INVALID_RESPONSE");
    }
  }
  return value as unknown as CalculationAdmissionEvidence;
}
