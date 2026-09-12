import { afterEach, expect, it, vi } from "vitest";
import { executeConversion, previewConversion, listConversions, reverseConversion, ConversionRequest } from "./canonicalConversionsApi";
afterEach(() => vi.unstubAllGlobals());
it("sends exact money strings and versions without browser tax authority to canonical endpoints only", async () => {
  const fetch = vi.fn(async () => ({ ok: true, json: async () => ({}) }));
  vi.stubGlobal("fetch", fetch);
  const request: ConversionRequest = { product_id: "p", expected_product_version: 2, destination_type: "capital", effective_date: "2026-09-12", idempotency_key: "key", whole_product: false, selections: [{ component_id: "c", component_code: "תגמולי_עובד_עד_2000", amount: "999999999999999999.99" }] };
  await previewConversion(1, request); await executeConversion(1, request); await listConversions(1, "p");
  await reverseConversion(1, "c", { expected_conversion_version: 1, expected_product_version: 3, idempotency_key: "undo", reason: "תיקון" });
  const calls = fetch.mock.calls as unknown as Array<[string, RequestInit | undefined]>;
  expect(calls.map(call => call[0])).toEqual(["/api/clients/1/canonical-conversions/preview", "/api/clients/1/canonical-conversions", "/api/clients/1/canonical-conversions?product_id=p", "/api/clients/1/canonical-conversions/c/reverse"]);
  expect(JSON.parse(calls[1][1]!.body as string)).toEqual(request);
});
it("localizes connection failures instead of exposing native English errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  await expect(listConversions(1)).rejects.toThrow("לא ניתן להתחבר לשרת ההמרות");
});
