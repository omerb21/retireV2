import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiTransportError } from "./clientsApi";
import { compareM10Runs } from "./m10ComparisonApi";

function response(body: unknown, ok = true, status = 200, statusText = "OK"): Response {
  return {
    ok,
    status,
    statusText,
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

afterEach(() => vi.restoreAllMocks());

describe("m10ComparisonApi", () => {
  it("posts to the exact client-scoped comparator route with only the two role-bound run IDs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ comparison_fingerprint: "result-fingerprint" }));
    vi.stubGlobal("fetch", fetchMock);

    await compareM10Runs(7, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
      caller_forged_field: "not-authorized",
    } as never);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/clients/7/m10/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference_run_id: "baseline-run",
        compared_run_id: "adjusted-run",
      }),
    });
  });

  it("returns the server response without enrichment or arithmetic", async () => {
    const body = {
      comparison_result_schema: "m10-comparison-result-v2",
      monthly_comparisons: [{ period_net: { reference_value: "1000.00", compared_value: "999.99", delta: "-0.01" } }],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));

    await expect(compareM10Runs(7, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
    })).resolves.toBe(body);
  });

  it("preserves structured API failures in ApiTransportError", async () => {
    const body = { detail: { code: "comparison_run_not_current", message: "run is not current" } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body, false, 409, "Conflict")));

    const error = await compareM10Runs(7, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
    }).catch(cause => cause);

    expect(error).toBeInstanceOf(ApiTransportError);
    expect(error).toMatchObject({ status: 409, statusText: "Conflict", body });
  });
});
