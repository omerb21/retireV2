import { apiFetch, buildApiUrl } from "./apiBase";
import type { ScenarioDraftDecision } from "./scenarioDraftsApi";

export interface PermissionComponent {
  component_id: string;
  component_code: string;
  balance: string;
  permission_status: "allowed" | "blocked" | "needs_source_reconciliation" | "unknown";
  reason_code: string;
  reason_he: string;
}
export interface ScenarioPermissionPreview {
  schema_version: "SCENARIO_PERMISSION_PREVIEW_V1";
  client_id: number;
  product_id: string;
  action: ScenarioDraftDecision["action"];
  effective_date: string;
  overall_status: string;
  professional_eligibility_status: "not_evaluated";
  tax_status: "not_evaluated";
  components: PermissionComponent[];
  source_fingerprint: string;
  ruleset_digest: string;
}

export async function previewDraftDecision(
  clientId: number,
  decision: ScenarioDraftDecision,
): Promise<PermissionComponent> {
  const response = await apiFetch(
    buildApiUrl(`/clients/${clientId}/scenario-conversions/permission-preview`),
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: decision.source_product_id,
        action: decision.action,
        effective_date: decision.effective_date,
      }),
    },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(`לא ניתן לבדוק הרשאה (${body?.code ?? "PREVIEW_UNAVAILABLE"}).`);
  }
  const result = await response.json() as ScenarioPermissionPreview;
  if (result.schema_version !== "SCENARIO_PERMISSION_PREVIEW_V1"
      || result.client_id !== clientId
      || result.product_id !== decision.source_product_id
      || result.action !== decision.action
      || result.effective_date !== decision.effective_date
      || result.professional_eligibility_status !== "not_evaluated"
      || result.tax_status !== "not_evaluated") {
    throw new Error("תשובת ההרשאות אינה תואמת להחלטת הטיוטה.");
  }
  const matching = result.components.filter(item =>
    item.component_id === decision.source_component_id
    && item.component_code === decision.component_code);
  if (matching.length !== 1) {
    throw new Error("רכיב המקור חסר או השתנה; נדרש אימות מחדש.");
  }
  return matching[0];
}
