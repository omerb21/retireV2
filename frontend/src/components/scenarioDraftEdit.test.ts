import { expect, it } from "vitest";
import { preserveEditedDecisionId } from "./scenarioDraftEdit";

it("keeps the same decision id when changing amount and destination", () => {
  const edited = preserveEditedDecisionId({
    source_product_id: "p", source_component_id: "c",
    component_code: "תגמולי_עובד_עד_2000",
    amount: "22.50", action: "capital_asset", effective_date: "2026-10-24",
  }, "original-decision");
  expect(edited.decision_id).toBe("original-decision");
  expect(edited.amount).toBe("22.50");
  expect(edited.action).toBe("capital_asset");
});
