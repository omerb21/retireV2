import { apiFetch, buildApiUrl } from "./apiBase";

export interface RetirementCalculationContext {
  schema_version: "RTDIR_PLANNING_CONTEXT_V1";
  client_id: number;
  planning_calculation_input_fingerprint: string;
  planning_input_ready: boolean;
  retirement_target_date: string | null;
  retirement_target_ready: boolean;
  blocking_facts: Array<{ source_id: string | null; code: string }>;
}
/** Existing factual planning context, not a scenario financial result. */
export async function readRetirementCalculationContext(clientId: number): Promise<RetirementCalculationContext> {
  const response = await apiFetch(buildApiUrl(`/clients/${clientId}/retirement-income-readiness/context`));
  if (!response.ok) throw new Error("לא ניתן לטעון את מוכנות החישוב של תיק הלקוח.");
  const result = await response.json() as RetirementCalculationContext;
  if (result.schema_version !== "RTDIR_PLANNING_CONTEXT_V1" || result.client_id !== clientId
      || typeof result.planning_input_ready !== "boolean"
      || typeof result.retirement_target_ready !== "boolean"
      || !Array.isArray(result.blocking_facts)
      || typeof result.planning_calculation_input_fingerprint !== "string"
      || !/^[a-f0-9]{64}$/.test(result.planning_calculation_input_fingerprint)) {
    throw new Error("תשובת מוכנות החישוב אינה תואמת לתיק הלקוח.");
  }
  return result;
}
