import { buildApiUrl } from "./apiBase";

export type Destination = "pension" | "capital";
export interface ConversionComponent { component_id: string; component_code: string; balance: string; allowed_destinations: Partial<Record<Destination, string>> }
export interface ConversionRequest {
  product_id: string; expected_product_version: number; destination_type: Destination;
  effective_date: string; idempotency_key: string; whole_product: boolean;
  selections: Array<{ component_id: string; component_code: string; amount: string | null }>;
  pension?: { pension_start_date: string; retirement_age?: number; company_name?: string; option_name?: string; survivors_option?: string; spouse_age_diff?: number; target_year?: number };
}
export interface ConversionGroup {
  amount: string; tax_treatment: string; monthly_display_amount?: string;
  allocations: Array<{ component_id: string; component_code: string; amount: string; before: string; after: string }>;
  coefficient: null | { annuity_factor: string; source: string; fallback_used: boolean; notes: string; catalog_version: string; warnings: string[] };
}
export interface ConversionPreview { groups: ConversionGroup[]; skipped: Array<{ component_code: string; reason: string }> }
export interface ConversionHistoryItem {
  conversion_id: string; source_product_id: string; destination_type: Destination; tax_treatment: string;
  converted_amount: string; status: "active" | "reversed"; version: number; effective_date: string; actor: string;
  pension: null | { name: string; monthly_display_amount: string; annuity_factor_text: string; coefficient_fallback_used: boolean; pension_start_date: string };
  allocations: Array<{ component_code_snapshot: string; amount: string; source_balance_before: string; source_balance_after: string }>;
}

async function request<T>(clientId: number, path = "", body?: unknown): Promise<T> {
  let response: Response;
  try { response = await fetch(buildApiUrl(`/clients/${clientId}/canonical-conversions${path}`), body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }); } catch { throw new Error("לא ניתן להתחבר לשרת ההמרות. יש לנסות שוב."); }
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail?.message === "string" ? error.detail.message : "הפעולה לא הושלמה. יש לטעון מחדש ולנסות שוב.");
  }
  return response.json() as Promise<T>;
}
export const previewConversion = (clientId: number, body: ConversionRequest) => request<ConversionPreview>(clientId, "/preview", body);
export const executeConversion = (clientId: number, body: ConversionRequest) => request<{ product_version: number }>(clientId, "", body);
export const listConversions = (clientId: number, productId?: string) => request<ConversionHistoryItem[]>(clientId, productId ? `?product_id=${encodeURIComponent(productId)}` : "");
export const reverseConversion = (clientId: number, id: string, body: { expected_conversion_version: number; expected_product_version: number; idempotency_key: string; reason: string }) => request(clientId, `/${encodeURIComponent(id)}/reverse`, body);
export const taxLabel = (tax: string) => ({ taxable: "חייב במס", exempt: "פטור ממס", capital_gains: "מס רווחי הון" }[tax] ?? "סיווג מס לא מוכר");
