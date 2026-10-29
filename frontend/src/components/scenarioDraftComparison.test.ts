import { expect, it } from "vitest";
import { formatScenarioCents, summarizeScenarioDraft } from "./scenarioDraftComparison";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

const product = [{
  product_id: "p", conversion_components: [
    { component_id: "c", component_code: "standard-component-02", balance: "100.01" },
  ],
}] as unknown as PensionProduct[];
function scenario(decisions: ScenarioDraft["decisions"], status: ScenarioDraft["status"] = "draft"): ScenarioDraft {
  return { scenario_id: "s", client_id: 1, name: "חלופה", status, version: 1,
    created_by: "test", updated_by: "test", financial_validation: "not_evaluated", decisions };
}
function decision(id: string, amount: string, componentId = "c", action: "pension" | "capital_asset" = "pension"): ScenarioDraft["decisions"][number] {
  return { decision_id: id, source_product_id: "p", source_component_id: componentId,
    component_code: "standard-component-02", amount, action, effective_date: "2026-10-24",
    validation_state: "unverified", product_version_at_review: 1,
    source_fingerprint_at_review: "a".repeat(64), ruleset_digest_at_review: null,
    permission_preview_id_at_review: null };
}
it("sums amounts in exact cents separately for pension and capital", () => {
  const result = summarizeScenarioDraft(scenario([
    decision("1", "0.01"), decision("2", "10.10"),
    decision("3", "90.00", "c", "capital_asset"),
  ]), product);
  expect(formatScenarioCents(result.pensionCents)).toBe("10.11");
  expect(formatScenarioCents(result.capitalCents)).toBe("90.00");
  expect(result.overAllocatedSources).toBe(1);
});
it("flags missing sources and stale decisions without granting financial approval", () => {
  const draft = scenario([decision("1", "12.00", "missing")], "needs_revalidation");
  draft.decisions[0].validation_state = "needs_revalidation";
  const result = summarizeScenarioDraft(draft, product);
  expect(result.missingSources).toBe(1);
  expect(result.staleDecisions).toBe(1);
  expect(result.status).toBe("needs_revalidation");
});
it("keeps independent scenarios independent and rejects malformed amounts", () => {
  const first = summarizeScenarioDraft(scenario([decision("1", "99.99")]), product);
  const second = summarizeScenarioDraft(scenario([decision("2", "1.00"), decision("3", "5.001")]), product);
  expect(first.overAllocatedSources).toBe(0);
  expect(second.overAllocatedSources).toBe(0);
  expect(second.invalidAmounts).toBe(1);
});
