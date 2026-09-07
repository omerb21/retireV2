import { buildApiUrl } from "./apiBase";

export interface PensionProductMetadata {
  product_name: string;
  product_type: string;
  provider_name: string | null;
  provider_identifier: string | null;
  account_reference: string | null;
  start_date: string | null;
  statement_date: string | null;
  historical_employers: string[];
  reported_product_total: string | null;
  reported_rewards_total: string | null;
  reported_severance_total: string | null;
}

export interface PensionProduct extends PensionProductMetadata {
  product_id: string;
  client_id: number;
  version: number;
  source_kind: "manual" | "imported";
  components: Record<string, string>;
  reconciliation: Record<string, string | null>;
  updated_at: string;
  source_history?: Array<{ checksum: string; filename: string | null; statement_date: string | null; diagnostics: unknown[] }>;
}

export type ProductSave = PensionProductMetadata & {
  expected_version: number;
  components: Record<string, string>;
};

async function request<T>(clientId: number, path = "", init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildApiUrl(`/clients/${clientId}/pension-products${path}`), init);
  } catch {
    throw new Error("לא ניתן להתחבר לשרת. הנתונים לא נשמרו.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail?.message === "string" ? body.detail.message : "הפעולה לא הושלמה. יש לבדוק את הנתונים ולנסות שוב.");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const listPensionProducts = (clientId: number) => request<PensionProduct[]>(clientId);
export const createPensionProduct = (clientId: number, body: PensionProductMetadata) => request<PensionProduct>(clientId, "", json("POST", body));
export const savePensionProduct = (clientId: number, id: string, body: ProductSave) => request<PensionProduct>(clientId, `/${encodeURIComponent(id)}`, json("PUT", body));
export const saveSelectedPensionProducts = (clientId: number, products: Array<ProductSave & { product_id: string }>) => request<PensionProduct[]>(clientId, "/save-selected", json("POST", { products }));
export const deletePensionProduct = (clientId: number, id: string, version: number) => request<void>(clientId, `/${encodeURIComponent(id)}?expected_version=${version}`, { method: "DELETE" });
export const importPensionProducts = (clientId: number, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return request<PensionProduct[]>(clientId, "/imports", { method: "POST", body });
};
