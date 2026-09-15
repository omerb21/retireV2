import { buildApiUrl } from "./apiBase";

export interface PlanningItem {
  source_id: string; id?: number; source_fingerprint?: string; description?: string; payer_name?: string;
  asset_description?: string; inclusion_state: string; applicability?: string; active_at_base?: boolean;
  amount?: string; amount_basis?: string; frequency?: string; known_value_amount?: string | null;
  value_as_of_date?: string | null; start_date?: string | null; end_date?: string | null;
  pension_start_date?: string | null; source_calculation_ready?: boolean;
  balance?: string; component_code?: string; blocking_facts?: string[];
  kind?: string; tax_treatment?: string | null; lifecycle_status?: string; product_name?: string;
  source_type?: string | null; source_date?: string | null; source_note?: string | null;
  provenance?: {source_reference?: string | null; conversion_id?: string; source_note?: string | null};
  monthly_equivalent_ratio?: {numerator: string; denominator: number} | null;
  amount_authority?: {amount?: string; numerator?: string; denominator?: string};
}
export interface PlanningInput {
  retirement_target?: {
    contract_version: string; retirement_target_date: string | null;
    decision_provenance: string; decision_actor: string | null; decided_at: string | null;
    relation_to_planning_base: string; retirement_target_ready: boolean;
    blockers: string[]; warnings: string[]; reference_fingerprint_at_decision: string | null;
    current_reference_fingerprint: string; decision_fingerprint: string;
  };
  target_reference_facts?: Array<{
    reference_id: string; source_id: string; source_kind: string; source_field: string;
    value_kind: "date" | "age"; date_value: string | null; age_value: number | null;
    source_semantic_fingerprint: string | null; source_version: number | null;
    lifecycle_state: string; unresolved_state: string[];
  }>;
  ready_for_next_planning_calculation?: boolean;
  planning_calculation_input_fingerprint?: string;
  contract_version: string; client_id: number; decision_version: number; planning_base_date: string | null;
  date_candidates: Array<{source_id: string; field: string; date: string}>;
  source_state_fingerprint: string; planning_input_fingerprint: string; planning_input_ready: boolean;
  pension_inputs: PlanningItem[]; general_income_inputs: PlanningItem[]; expense_inputs: PlanningItem[];
  capital_inputs: PlanningItem[]; reference_only: PlanningItem[]; excluded_sources: PlanningItem[];
  unresolved_items: Array<{source_id: string; reasons: string[]}>;
  warnings: Array<{code: string; source_id?: string; source_ids?: string[]}>;
  blocking_facts: Array<{source_id: string | null; code: string}>;
  client_reference_facts?: {birth_date: string | null; planned_retirement_age: number | null};
}
export async function planningCall<T>(id: number, path = "", body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(buildApiUrl(`/clients/${id}/retirement-planning-input${path}`), {
    method: body === undefined ? "GET" : "PUT", signal,
    ...(body === undefined ? {} : {headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail?.message ?? "הפעולה לא הושלמה. יש לרענן ולבדוק את הנתונים.");
  }
  return response.json() as Promise<T>;
}
