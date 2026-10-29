import { afterEach, expect, it, vi } from "vitest";
import {
  renameScenarioDraft, replaceScenarioDraft, type ScenarioDraft,
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
