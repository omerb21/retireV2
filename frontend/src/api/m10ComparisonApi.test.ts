import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiTransportError } from "./clientsApi";
import { compareM10Runs, type M10ComparisonResponse } from "./m10ComparisonApi";

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

const fingerprint = (digit: string) => digit.repeat(64);

function metric(
  reference_value: string,
  compared_value: string,
  delta: string,
  relation: "equal" | "compared_greater_than_reference" | "compared_lower_than_reference",
) {
  return { reference_value, compared_value, delta, relation };
}

function runEvidence(subject_type: "baseline" | "adjusted", digit: string) {
  return {
    run_id: `${subject_type}-run`,
    scenario_subject_id: `${subject_type}-subject`,
    subject_type,
    calculation_semantic_fingerprint: fingerprint(digit),
    integrity_fingerprint: fingerprint(digit),
    adjustment_manifest_fingerprint: fingerprint(digit),
    factual_inventory_fingerprint: fingerprint(digit),
    upstream_snapshot_fingerprint: fingerprint(digit),
    semantic_result_fingerprint: fingerprint(digit),
    result_integrity_fingerprint: fingerprint(digit),
  };
}

function validResponse(): M10ComparisonResponse {
  return {
    comparison_contract_version: "m10-scenario-comparison-v2",
    pair_admission_contract: "m10-pair-admission-v2",
    comparison_result_schema: "m10-comparison-result-v2",
    comparison_fingerprint_schema: "m10-comparison-fingerprint-v2",
    comparison_fingerprint: fingerprint("a"),
    delta_direction: "compared_minus_reference",
    client_id: 7,
    scenario_family: "declared_retirement_cashflow_adjustments",
    scenario_contract_version: "v1",
    horizon: { start_month: "2026-01", end_month: "2026-02" },
    factual_baseline_material_fingerprint: fingerprint("b"),
    component_domain_contract_version: "m09-component-domains-v1",
    versions: {
      factual_engine_version: "m09-aggregation-v1",
      factual_result_schema_version: "m09-result-v1",
      subject_engine_version: "m09-subject-aggregation-v1",
      subject_result_schema_version: "m09-subject-result-v1",
      upstream_snapshot_schema_version: "m09-subject-upstream-snapshot-v1",
      factual_inventory_schema_version: "m09-resolved-component-inventory-v1",
      factual_upstream_versions: [{
        domain_identity: "recurring_income",
        candidate_identity: "income-1",
        source_identity: "income-source",
        source_version: "unversioned",
        source_fingerprint: fingerprint("c"),
        handoff_contract_versions: [],
      }],
    },
    reference_run: runEvidence("baseline", "d"),
    compared_run: runEvidence("adjusted", "e"),
    monthly_comparisons: [{
      month: "2026-01",
      gross_inflow_total: metric("9007199254740993.00", "9007199254740993.10", "0.10", "compared_greater_than_reference"),
      gross_outflow_total: metric("100.00", "99.99", "-0.01", "compared_lower_than_reference"),
      period_net: metric("42.00", "42.00", "0.00", "equal"),
    }],
    range_totals: {
      gross_inflow_total: metric("999999999999999999.99", "0.00", "-999999999999999999.99", "compared_lower_than_reference"),
      gross_outflow_total: metric("0.00", "999999999999999999.99", "999999999999999999.99", "compared_greater_than_reference"),
      period_net: metric("0.00", "0.00", "0.00", "equal"),
    },
  };
}

async function expectMalformed(body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));
  const error = await compareM10Runs(7, {
    reference_run_id: "baseline-run",
    compared_run_id: "adjusted-run",
  }).catch(cause => cause);
  expect(error).toBeInstanceOf(ApiTransportError);
  expect(error).toMatchObject({ status: 200, statusText: "Invalid M10 comparison response schema", body });
}

afterEach(() => vi.restoreAllMocks());

describe("m10ComparisonApi", () => {
  it("posts to the exact client-scoped comparator route with only the two role-bound run IDs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(validResponse()));
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

  it("returns an exact complete response while preserving canonical monetary strings verbatim", async () => {
    const body = validResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));

    const result = await compareM10Runs(7, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
    });

    expect(result).toBe(body);
    expect(result.monthly_comparisons[0].gross_inflow_total.reference_value).toBe("9007199254740993.00");
    expect(result.monthly_comparisons[0].gross_outflow_total.delta).toBe("-0.01");
    expect(result.monthly_comparisons[0].period_net.delta).toBe("0.00");
    expect(result.range_totals.gross_inflow_total.reference_value).toBe("999999999999999999.99");
  });

  it.each([
    ["missing required top-level field", (body: Record<string, unknown>) => { delete body.comparison_fingerprint; }],
    ["null nested object", (body: Record<string, unknown>) => { body.horizon = null; }],
    ["wrong primitive type", (body: Record<string, unknown>) => { body.client_id = "7"; }],
    ["wrong contract version", (body: Record<string, unknown>) => { body.comparison_result_schema = "m10-comparison-result-v1"; }],
    ["malformed fingerprint", (body: Record<string, unknown>) => { body.comparison_fingerprint = "ABC123"; }],
    ["extra top-level key", (body: Record<string, unknown>) => { body.extra = true; }],
    ["extra nested key", (body: Record<string, unknown>) => { (body.horizon as Record<string, unknown>).timezone = "UTC"; }],
    ["missing required nested run evidence", (body: Record<string, unknown>) => { delete (body.reference_run as Record<string, unknown>).integrity_fingerprint; }],
    ["malformed monthly array member", (body: Record<string, unknown>) => { body.monthly_comparisons = [null]; }],
    ["malformed month", (body: Record<string, unknown>) => { (body.monthly_comparisons as Record<string, unknown>[])[0].month = "2026-13"; }],
    ["missing required monthly metric", (body: Record<string, unknown>) => { delete (body.monthly_comparisons as Record<string, unknown>[])[0].period_net; }],
    ["malformed range total", (body: Record<string, unknown>) => { (body.range_totals as Record<string, unknown>).gross_inflow_total = []; }],
    ["unknown relation", (body: Record<string, unknown>) => { ((body.range_totals as Record<string, unknown>).period_net as Record<string, unknown>).relation = "better"; }],
    ["non-string monetary value", (body: Record<string, unknown>) => { ((body.range_totals as Record<string, unknown>).period_net as Record<string, unknown>).delta = 0; }],
    ["non-canonical monetary string", (body: Record<string, unknown>) => { ((body.range_totals as Record<string, unknown>).period_net as Record<string, unknown>).delta = "-0.00"; }],
    ["out-of-domain source monetary string", (body: Record<string, unknown>) => { ((body.monthly_comparisons as Record<string, unknown>[])[0].period_net as Record<string, unknown>).reference_value = "1000000000000000000.00"; }],
    ["out-of-domain delta monetary string", (body: Record<string, unknown>) => { ((body.range_totals as Record<string, unknown>).period_net as Record<string, unknown>).delta = "1999999999999999999.99"; }],
    ["wrong run role", (body: Record<string, unknown>) => { (body.reference_run as Record<string, unknown>).subject_type = "adjusted"; }],
    ["wrong nested version", (body: Record<string, unknown>) => { (body.versions as Record<string, unknown>).factual_engine_version = "m09-aggregation-v2"; }],
    ["malformed upstream array", (body: Record<string, unknown>) => { (body.versions as Record<string, unknown>).factual_upstream_versions = {}; }],
    ["non-string handoff version", (body: Record<string, unknown>) => { ((body.versions as Record<string, unknown>).factual_upstream_versions as Record<string, unknown>[])[0].handoff_contract_versions = [1]; }],
    ["wrong exact M06 handoff version", (body: Record<string, unknown>) => {
      const upstream = ((body.versions as Record<string, unknown>).factual_upstream_versions as Record<string, unknown>[])[0];
      upstream.domain_identity = "m06_monthly_pension";
      upstream.handoff_contract_versions = ["m06-to-m09-monthly-amount-v2"];
    }],
  ])("rejects HTTP 200 with %s as a transport/API/schema failure", async (_label, mutate) => {
    const body = structuredClone(validResponse()) as unknown as Record<string, unknown>;
    mutate(body);
    await expectMalformed(body);
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
