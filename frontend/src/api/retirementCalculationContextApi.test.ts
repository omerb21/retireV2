import { afterEach, expect, it, vi } from "vitest";
import { readRetirementCalculationContext } from "./retirementCalculationContextApi";

afterEach(() => { vi.unstubAllGlobals(); });
const valid = {
  schema_version: "RTDIR_PLANNING_CONTEXT_V1", client_id: 5,
  planning_calculation_input_fingerprint: "a".repeat(64),
  planning_input_ready: false, retirement_target_date: "2027-12-31",
  retirement_target_ready: true, blocking_facts: [{source_id: "income-1", code: "MISSING_BASIS"}],
};
it("reads existing factual readiness only over GET and keeps blockers", async () => {
  const mock = vi.fn().mockResolvedValue({ok: true, json: async () => valid});
  vi.stubGlobal("fetch", mock);
  const result = await readRetirementCalculationContext(5);
  expect(result.blocking_facts).toEqual(valid.blocking_facts);
  expect(mock.mock.calls[0][1].method).toBeUndefined();
});
it("fails closed when the response belongs to another client", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok: true, json: async () => ({...valid, client_id: 6})}));
  await expect(readRetirementCalculationContext(5)).rejects.toThrow("אינה תואמת");
});
