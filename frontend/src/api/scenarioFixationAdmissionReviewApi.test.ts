import { beforeEach, expect, it, vi } from "vitest";
import {
  readFixationAdmissionReview,
  ReviewApiError,
} from "./scenarioFixationProfessionalReviewApi";

const mocks = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock("./apiBase", () => ({
  apiFetch: mocks.fetch,
  buildApiUrl: (path: string) => "/api" + path,
}));
beforeEach(() => { vi.clearAllMocks(); });

const preparation = "a".repeat(64);
const eligibility = "b".repeat(64);
const valid = {
  contract: "SCENARIO_FIXATION_ADMISSION_REVIEW_V1",
  client_id: 7,
  scenario_id: "A/B",
  state: "ADMITTED_FOR_REVIEW",
  preparation_fingerprint: preparation,
  eligibility_fingerprint: eligibility,
  admission_review_fingerprint: "c".repeat(64),
  reasons: [],
  admission_contract_validated: true,
  professional_authority: false,
  execution_allowed: false,
  tax_calculation_performed: false,
  tax_authority_approval: null,
};

function respond(payload: unknown, ok = true, status = 200) {
  mocks.fetch.mockResolvedValue({ ok, status, json: async () => payload });
}

it("reads a contract-valid admitted review with exact fingerprints and no authority", async () => {
  respond(valid);
  const result = await readFixationAdmissionReview(7, "A/B", preparation, eligibility);
  expect(result.state).toBe("ADMITTED_FOR_REVIEW");
  expect(result.admission_contract_validated).toBe(true);
  expect(result.professional_authority).toBe(false);
  expect(result.execution_allowed).toBe(false);
  expect(result.tax_calculation_performed).toBe(false);
  expect(mocks.fetch).toHaveBeenCalledWith(
    `/api/clients/7/scenario-drafts/A%2FB/fixation-admission-review?expected_preparation_fingerprint=${preparation}&expected_eligibility_fingerprint=${eligibility}`,
    { method: "GET" },
  );
});

it("accepts a contract-valid rejected review while preserving reasons and sources", async () => {
  respond({
    ...valid,
    state: "REJECTED",
    reasons: [{
      code: "UNSUPPORTED_OR_UNAPPROVED_VALUE",
      path: "parameter_set.values.grant_impact_multiplier",
      message: "unsupported multiplier",
      source_ids: ["parameter-set-2026"],
    }],
    admission_contract_validated: false,
  });
  const result = await readFixationAdmissionReview(7, "A/B", preparation, eligibility);
  expect(result.state).toBe("REJECTED");
  expect(result.reasons[0].source_ids).toEqual(["parameter-set-2026"]);
});

it("accepts a stale rejection carrying the server's current fingerprints", async () => {
  respond({
    ...valid,
    state: "REJECTED",
    preparation_fingerprint: "d".repeat(64),
    eligibility_fingerprint: "e".repeat(64),
    reasons: [{
      code: "FIXATION_ADMISSION_REVIEW_STALE",
      path: null,
      message: null,
      source_ids: [],
    }],
    admission_contract_validated: false,
  });
  const result = await readFixationAdmissionReview(7, "A/B", preparation, eligibility);
  expect(result.state).toBe("REJECTED");
  expect(result.preparation_fingerprint).toBe("d".repeat(64));
  expect(result.eligibility_fingerprint).toBe("e".repeat(64));
});

it.each([
  { ...valid, contract: "SCENARIO_FIXATION_ADMISSION_REVIEW_V2" },
  { ...valid, client_id: 8 },
  { ...valid, scenario_id: "B" },
  { ...valid, state: "APPROVED_INTERNAL" },
  { ...valid, preparation_fingerprint: "d".repeat(64) },
  { ...valid, eligibility_fingerprint: "d".repeat(64) },
  { ...valid, preparation_fingerprint: "invalid" },
  { ...valid, eligibility_fingerprint: "invalid" },
  { ...valid, admission_review_fingerprint: "invalid" },
  { ...valid, admission_contract_validated: false },
  { ...valid, professional_authority: true },
  { ...valid, execution_allowed: true },
  { ...valid, tax_calculation_performed: true },
  { ...valid, tax_authority_approval: {} },
  { ...valid, reasons: [{ code: "", path: null, message: null, source_ids: [] }] },
  { ...valid, reasons: [{ code: "ERROR", path: null, message: null, source_ids: [null] }] },
  { ...valid, state: "REJECTED", admission_contract_validated: false, reasons: [] },
  null,
])("rejects malformed, mismatched or falsely authoritative response %#", async payload => {
  respond(payload);
  await expect(readFixationAdmissionReview(7, "A/B", preparation, eligibility))
    .rejects.toMatchObject({
      status: 409,
      code: "FIXATION_ADMISSION_REVIEW_RESPONSE_INVALID",
    });
});

it.each([
  ["", eligibility],
  ["A".repeat(64), eligibility],
  ["a".repeat(63), eligibility],
  [preparation, undefined],
  [preparation, "not-a-fingerprint"],
] as const)("rejects missing or invalid fingerprints before fetch %#", async (prep, elig) => {
  await expect(readFixationAdmissionReview(
    7,
    "A/B",
    prep as string,
    elig as string,
  )).rejects.toEqual(new ReviewApiError(
    400,
    "FIXATION_ADMISSION_REVIEW_FINGERPRINT_INVALID",
    [],
  ));
  expect(mocks.fetch).not.toHaveBeenCalled();
});

it("preserves an HTTP rejection instead of treating it as admission", async () => {
  respond({ code: "FIXATION_ADMISSION_REVIEW_DENIED" }, false, 409);
  await expect(readFixationAdmissionReview(7, "A/B", preparation, eligibility))
    .rejects.toEqual(new ReviewApiError(409, "FIXATION_ADMISSION_REVIEW_DENIED", []));
});
