import { afterEach, expect, it, vi } from "vitest";
import {
  readCalculationAdmission, renameScenarioDraft, replaceScenarioDraft, type ScenarioDraft,
} from "./scenarioDraftsApi";

const network = vi.hoisted(() => ({ fetch: vi.fn(), url: vi.fn((path: string) => "/api" + path) }));
vi.mock("./apiBase", () => ({ apiFetch: network.fetch, buildApiUrl: network.url }));
afterEach(() => { vi.clearAllMocks(); });

const scenario: ScenarioDraft = {
  scenario_id: "scenario/id", client_id: 7, name: "Original", status: "draft",
  version: 4, created_by: "planner", updated_by: "planner",
  financial_validation: "not_evaluated", decisions: [],
};

it("renames through the metadata-only CAS route", async () => {
  network.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ ...scenario, name: "Renamed", version: 5 }) });
  await renameScenarioDraft(7, scenario, "Renamed");
  const [url, options] = network.fetch.mock.calls[0] as [string, RequestInit];
  expect(url).toBe("/api/clients/7/scenario-drafts/scenario%2Fid/rename");
  expect(options.method).toBe("POST");
  expect(JSON.parse(options.body as string)).toEqual({ expected_version: 4, name: "Renamed" });
});

it("accepts a sealed nonbinding gross forecast while requiring explicit no-tax/no-net warnings", async () => {
  const result = {
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: 7, scenario_id: "scenario/id",
    scenario_version: 4, assessment_state: "gross_estimate_ready", blockers: [],
    warnings: ["TAX_NOT_EVALUATED", "NET_NOT_EVALUATED"],
    financial_result: {
      result_type: "NONBINDING_GROSS_PENSION_FORECAST", monthly_pension_gross_ils: "100.00",
      comparison_basis: { currency: "ILS", income_basis: "GROSS", retirement_target_date: "2027-01-01", source_reference_date: "2026-12-01" },
      coefficient_provenance: [{ decision_id: "d", factor_value: "200", factor_evidence_type: "PLANNER_ASSUMPTION",
        factor_evidence_reference: "synthetic assumption", factor_admission_revision: 1,
        professional_admission_fingerprint: "c".repeat(64), result_fingerprint: "b".repeat(64),
        monthly_estimate_gross_ils: "100.00", source_reference_date: "2026-12-01", retirement_target_date: "2027-01-01" }],
      tax_calculated: false, net_calculated: false, aggregate_fingerprint: "a".repeat(64),
    },
  };
  network.fetch.mockResolvedValueOnce({ ok: true, json: async () => result });
  expect((await readCalculationAdmission(7, "scenario/id")).financial_result?.monthly_pension_gross_ils).toBe("100.00");
  network.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ ...result, warnings: [] }) });
  await expect(readCalculationAdmission(7, "scenario/id")).rejects.toThrow("ADMISSION_INVALID_RESPONSE");
});

it("never echoes read-only source authority evidence into a decision write", async () => {
  network.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ ...scenario, version: 5 }) });
  await replaceScenarioDraft(7, scenario, [{
    decision_id: "d", source_product_id: "p", source_component_id: "c",
    component_code: "תגמולי_עובד_עד_2000", amount: "10.00",
    action: "pension", effective_date: "2026-10-29",
    validation_state: "unverified", product_version_at_review: 99,
    source_fingerprint_at_review: "caller-supplied",
    ruleset_digest_at_review: "caller-supplied",
    permission_preview_id_at_review: "caller-supplied",
  } as never]);
  const [, options] = network.fetch.mock.calls[0] as [string, RequestInit];
  const payload = JSON.parse(options.body as string);
  expect(payload.decisions).toEqual([{
    decision_id: "d", source_product_id: "p", source_component_id: "c",
    component_code: "תגמולי_עובד_עד_2000", amount: "10.00",
    action: "pension", effective_date: "2026-10-29",
  }]);
});
