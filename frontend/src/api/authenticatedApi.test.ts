import { apiFetch, configureAuthenticatedApi } from "./apiBase";
import { expect, test, vi } from "vitest";

test("adds credentials and the in-memory CSRF token only to unsafe requests", async () => {
  const mocked = vi.fn().mockResolvedValue(new Response("{}", {status: 200}));
  vi.stubGlobal("fetch", mocked); configureAuthenticatedApi("A".repeat(43));
  await apiFetch("/api/read"); await apiFetch("/api/write", {method: "POST"});
  expect(mocked.mock.calls[0][1].credentials).toBe("include");
  expect((mocked.mock.calls[0][1].headers as Headers | undefined)?.has("X-RTDIR-CSRF") ?? false).toBe(false);
  expect((mocked.mock.calls[1][1].headers as Headers).get("X-RTDIR-CSRF")).toBe("A".repeat(43));
  configureAuthenticatedApi(null);
});
