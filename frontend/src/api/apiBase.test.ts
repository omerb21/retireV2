import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./apiBase";

describe("apiBase", () => {
  it("uses the backend runtime origin by default outside tests", () => {
    expect(resolveApiBaseUrl({ MODE: "development" })).toBe("/api");
  });

  it("uses relative api paths in test mode", () => {
    expect(resolveApiBaseUrl({ MODE: "test" })).toBe("/api");
  });

  it("uses same-origin api paths in production and never defaults to localhost", () => {
    expect(resolveApiBaseUrl({ MODE: "production" })).toBe("/api");
    expect(resolveApiBaseUrl({ MODE: "production", VITE_API_BASE_URL: "https://hostile.example/api" })).toBe("/api");
    expect(resolveApiBaseUrl({ MODE: "production" })).not.toContain("localhost");
    expect(resolveApiBaseUrl({ MODE: "production" })).not.toContain("127.0.0.1");
  });

  it("uses a configured API base URL without a trailing slash", () => {
    expect(
      resolveApiBaseUrl({
        MODE: "development",
        VITE_API_BASE_URL: "http://127.0.0.1:9000/api/"
      })
    ).toBe("http://127.0.0.1:9000/api");
  });
});
