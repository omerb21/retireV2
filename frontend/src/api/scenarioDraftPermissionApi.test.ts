import { afterEach, expect, it, vi } from "vitest";
import { previewDraftDecision } from "./scenarioDraftPermissionApi";
import type { ScenarioDraftDecision } from "./scenarioDraftsApi";

const sample: ScenarioDraftDecision = {
  decision_id: "d1", source_product_id: "p1", source_component_id: "c1",
  component_code: "תגמולי_עובד_עד_2000", amount: "25.00",
  action: "pension", effective_date: "2026-10-24", validation_state: "unverified",
};
const response = {
  schema_version: "SCENARIO_PERMISSION_PREVIEW_V1",
  client_id: 1, product_id: "p1", action: "pension", effective_date: "2026-10-24",
  overall_status: "mixed", professional_eligibility_status: "not_evaluated",
  tax_status: "not_evaluated", source_fingerprint: "source", ruleset_digest: "rules",
  components: [{ component_id: "c1", component_code: sample.component_code,
    balance: "50.00", permission_status: "blocked",
    reason_code: "BASE_PERMISSION_BLOCKED", reason_he: "חסום" }],
};
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
it("matches the exact saved component and action, without treating overall product status as approval", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => response, status: 200 });
  vi.stubGlobal("fetch", fetcher);
  const component = await previewDraftDecision(1, sample);
  expect(component.permission_status).toBe("blocked");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][1].method).toBe("POST");
  expect(JSON.parse(fetcher.mock.calls[0][1].body).product_id).toBe("p1");
});
it("rejects a mismatched client or missing component instead of showing permission", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...response, client_id: 2 }) }));
  await expect(previewDraftDecision(1, sample)).rejects.toThrow("אינה תואמת");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...response, components: [] }) }));
  await expect(previewDraftDecision(1, sample)).rejects.toThrow("חסר");
});
