import { beforeEach, expect, it, vi } from "vitest";
import { readFixationAdmissionEligibility, ReviewApiError } from "./scenarioFixationProfessionalReviewApi";

const mocks = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock("./apiBase", () => ({
  apiFetch: mocks.fetch,
  buildApiUrl: (path: string) => "/api" + path,
}));
beforeEach(() => { vi.clearAllMocks(); });
const valid = {
  contract: "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1",
  client_id: 7, scenario_id: "A",
  preparation_fingerprint: "a".repeat(64),
  eligibility_fingerprint: "b".repeat(64),
  state: "ELIGIBLE_FOR_ADMISSION_REVIEW",
  reasons: [],
  admission_review_required: true,
  professional_authority: false,
  execution_allowed: false,
  tax_authority_approval: null,
};
function respond(payload: unknown, ok = true, status = 200) {
  mocks.fetch.mockResolvedValue({
    ok, status, json: async () => payload,
  });
}

it("reads valid static eligibility from the existing scenario API only", async () => {
  respond(valid);
  const result = await readFixationAdmissionEligibility(7, "A");
  expect(result.state).toBe("ELIGIBLE_FOR_ADMISSION_REVIEW");
  expect(result.professional_authority).toBe(false);
  expect(result.execution_allowed).toBe(false);
  expect(mocks.fetch).toHaveBeenCalledWith(
    "/api/clients/7/scenario-drafts/A/fixation-admission-eligibility",
    { method: "GET" },
  );
});

it.each([
  { ...valid, client_id: 8 },
  { ...valid, scenario_id: "B" },
  { ...valid, state: "APPROVED_INTERNAL" },
  { ...valid, admission_review_required: false },
  { ...valid, professional_authority: true },
  { ...valid, execution_allowed: true },
  { ...valid, tax_authority_approval: {} },
  { ...valid, eligibility_fingerprint: "wrong" },
  { ...valid, reasons: [{ code: "", source_ids: [] }] },
  { ...valid, reasons: [{ code: "MISSING", source_ids: [null] }] },
  { ...valid, reasons: [{ code: "MISSING", source_ids: ["grant-a"] }] },
  null,
])("rejects malformed, mismatched or falsely positive GET response %#", async payload => {
  respond(payload);
  await expect(readFixationAdmissionEligibility(7, "A"))
    .rejects.toMatchObject({ status: 409, code: "FIXATION_ELIGIBILITY_RESPONSE_INVALID" });
});

it("does not mask an HTTP 422 as a positive eligibility response", async () => {
  respond({ code: "FIXATION_ELIGIBILITY_DENIED" }, false, 422);
  await expect(readFixationAdmissionEligibility(7, "A"))
    .rejects.toEqual(new ReviewApiError(422, "FIXATION_ELIGIBILITY_DENIED", []));
});
