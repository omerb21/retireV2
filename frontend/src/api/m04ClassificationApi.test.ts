import { afterEach, describe, expect, it, vi } from "vitest";
import {
  actOnM04,
  createM04Proposal,
  overrideM04,
  startM04,
  undoM04,
} from "./m04ClassificationApi";

const json = (body: unknown): Response => ({
  ok: true,
  status: 201,
  statusText: "Created",
  headers: { get: () => "application/json" },
  json: async () => body,
  text: async () => JSON.stringify(body),
}) as unknown as Response;
const response = { revision_id: "r-new" };
const reason = {
  expected_current_revision_id: "r-current",
  reason_code: "planner_decision",
  explanation: "explicit planner action",
};

afterEach(() => vi.restoreAllMocks());

describe("m04ClassificationApi lifecycle intent boundary", () => {
  it("maps all nine actions to distinct endpoints with user-intent-only payloads", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({
        url: String(input),
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
      });
      return json(response);
    }));

    await startM04(7, "intake");
    await createM04Proposal(7, "intake", "r-current");
    await actOnM04(7, "intake", "unresolved", reason);
    await actOnM04(7, "intake", "accept", reason);
    await actOnM04(7, "intake", "reject", reason);
    await actOnM04(7, "intake", "reopen", reason);
    await overrideM04(7, "intake", {
      ...reason,
      confirmed: true,
      product_family: "provident_fund",
      pension_subtype: null,
      components: [{
        evidence_identity: "component:0:abc",
        component_kind: "contribution_component",
        interpretation: "pension",
        current_employer_related: "unknown",
        explanation: "bounded planner classification",
      }],
    });
    await undoM04(7, "intake", {
      ...reason,
      confirmed: true,
      historical_revision_id: "r-history",
    });
    await actOnM04(7, "intake", "start-revalidation", reason);

    expect(calls.map((call) => call.url.split("/").pop())).toEqual([
      "start", "proposal", "unresolved", "accept", "reject",
      "reopen", "override", "undo", "start-revalidation",
    ]);
    expect(calls[0].body).toBeUndefined();
    expect(calls[1].body).toEqual({
      expected_current_revision_id: "r-current",
    });
    for (const index of [2, 3, 4, 5, 8]) {
      expect(calls[index].body).toEqual(reason);
    }
    for (const call of calls) {
      expect(JSON.stringify(call.body) ?? "").not.toMatch(
        /actor|timestamp|catalogue_version|matched_rule|eligible_for_m05|client_id|accepted_status/,
      );
    }
  });
});
