import { apiFetch, buildApiUrl } from "./apiBase";

export interface M12ScenarioDecision {
  component: string; action: string; declared_amount: string;
  effective_date: string; validation_state: string; qualified_calculation: false;
}
export interface M12Draft {
  document_kind: "M12_FIRST_STAGE_DRAFT";
  draft: true; generated_at: string;
  client: { name: string; birth_date: string | null;
    employment_status: string | null; planned_retirement_date: string | null;
    planned_retirement_age: number | null };
  pension_products: Array<{name: string; type: string; provider: string | null;
    reported_total: string | null; statement_date: string | null; verification: string}>;
  capital_assets: Array<{name: string; category: string; value: string | null;
    value_date: string | null; verification: string}>;
  incomes: Array<{name: string; amount: string; frequency: string;
    amount_basis: string; verification: string}>;
  expenses: Array<{name: string; amount: string; frequency: string; verification: string}>;
  scenarios: Array<{name: string; version: number; status: string;
    preferred: boolean; decisions: M12ScenarioDecision[]}>;
  preferred: {name: string; version_at_selection: number;
    rationale: string; saved_at: string | null; outdated: boolean} | null;
  assumptions: Array<{title: string; value: string; rationale: string}>;
  missing_information: Array<{label: string; status: string}>;
  warnings: string[];
  cashflow_results: null;
  calculation_traceability: "not_established";
}
export async function loadM12Draft(clientId: number, signal?: AbortSignal): Promise<M12Draft> {
  const response = await apiFetch(buildApiUrl(`/clients/${clientId}/m12-draft`), {
    method: "GET", signal,
  });
  if (!response.ok) throw new Error("לא ניתן לטעון את טיוטת התכנון.");
  const result = await response.json() as M12Draft;
  if (result.document_kind !== "M12_FIRST_STAGE_DRAFT" || result.draft !== true
    || !result.client || result.calculation_traceability !== "not_established"
    || result.cashflow_results !== null) {
    throw new Error("תוכן הטיוטה אינו תואם לחוזה M12.");
  }
  return result;
}
