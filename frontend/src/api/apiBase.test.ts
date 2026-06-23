import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./apiBase";

describe("apiBase", () => {
  it("uses the backend runtime origin by default outside tests", () => {
    expect(resolveApiBaseUrl({ MODE: "development" })).toBe("http://127.0.0.1:8000/api");
  });

  it("uses relative api paths in test mode", () => {
    expect(resolveApiBaseUrl({ MODE: "test" })).toBe("/api");
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
