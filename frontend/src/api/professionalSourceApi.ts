import { buildApiUrl } from "./apiBase";

export interface ManualInput {
  input_mode: "entered" | "calculated";
  payer_name: string | null; description: string | null; source_reference: string | null;
  monthly_amount: string | null; balance: string | null; annuity_factor: string | null;
  pension_start_date: string | null; tax_treatment: string | null;
  indexation_method: string | null; fixed_indexation_rate: string | null; source_note: string | null;
}
export interface PensionSource extends Partial<ManualInput> {
  source_id: string; kind: "conversion" | "manual"; version: number;
  manual_pension_source_id?: string; lifecycle_status: string;
  visible: boolean; calculation_ready: boolean; missing_or_blocking_facts: string[];
  has_started: boolean | null;
  amount_authority: { authority_kind: string; amount?: string | null; numerator?: string | null; denominator?: string | null };
  provenance: { source_reference?: string | null; conversion_id?: string; pension_destination_id?: string;
    manual_pension_source_id?: string; coefficient_source?: string;
    allocations?: Array<{ source_component_id: string; component_code_snapshot: string; amount: string }> };
}
export interface SourceSnapshot {
  contract_version: string; client_id: number; source_state_fingerprint: string;
  pension_products: Array<{ product_id: string; product_name: string; product_type: string; provider_name: string | null;
    account_reference: string; statement_date: string | null; components: Array<{ component_id: string; component_code: string; balance: string }>;
    reported_controls: { authority: string; reported_product_total: string | null; reported_rewards_total: string | null; reported_severance_total: string | null } }>;
  pension_sources: PensionSource[];
  capital_sources: Array<{ source_id: string; id: number; asset_description: string; known_value_amount: string | null;
    value_as_of_date: string | null; origin_kind: string; conversion_id: string | null; calculation_ready: boolean; missing_or_blocking_facts: string[] }>;
  client_fact_warnings: string[];
  source_warnings: Array<{ code: string; source_id: string; related_sources: string[] }>;
}
async function call<T>(clientId: number, path: string, method: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildApiUrl(`/clients/${clientId}/${path}`), {
      method, signal, ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    });
  } catch {
    throw new Error("לא ניתן להתחבר לשרת המקורות. יש לרענן ולנסות שוב.");
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(typeof detail?.detail?.message === "string" ? detail.detail.message : "לא ניתן להשלים את הפעולה. יש לבדוק את הנתונים ולרענן.");
  }
  return response.json() as Promise<T>;
}
export const getSourceSnapshot = (id: number, signal?: AbortSignal) => call<SourceSnapshot>(id, "professional-source-snapshot", "GET", undefined, signal);
export const createManualPension = (id: number, body: ManualInput) => call(id, "canonical-pension-sources/manual", "POST", body);
export const updateManualPension = (id: number, source: string, body: ManualInput & { expected_version: number }) => call(id, `canonical-pension-sources/manual/${encodeURIComponent(source)}`, "PUT", body);
export const supersedeManualPension = (id: number, source: string, expected_version: number) => call(id, `canonical-pension-sources/manual/${encodeURIComponent(source)}`, "DELETE", { expected_version });
