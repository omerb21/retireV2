import { apiFetch, buildApiUrl } from "./apiBase";

export type ReviewGroup =
  | "eligibility" | "tax_year_and_parameters" | "pension_classification"
  | "historical_grant" | "severance_continuity"
  | "historical_capitalization" | "planned_withdrawal_or_commutation";
export type ReviewDetermination = "REQUIRES_REVIEW" | "PLANNER_ASSERTED" | "EXCLUDE_PROPOSED";

export type Inclusion = "include" | "exclude";
export type Support = "supported" | "unsupported" | "requires_special_handling";
export type CollectionState = "unknown" | "not_collected" | "confirmed_none" | "items_recorded";
export interface CollectionControl {
  state: CollectionState;
  evidence_references: string[];
}
export interface IDFControl {
  applicability: "NOT_REVIEWED" | "NOT_APPLICABLE" | "APPLICABLE";
  evidence_references: string[];
  input: {
    idf_id: string;
    reduction_amount: number;
    original_commutation_percent: number;
    current_commutation_percent: number;
    commutation_date: string;
    promoter_age_date: string;
    source_label: string | null;
  } | null;
}
export interface FixationAdmissionControls {
  calculation_version: "pkg-012-m08d-v1";
  grants_collection: CollectionControl;
  actual_capitalizations_collection: CollectionControl;
  idf: IDFControl;
}
export interface FixationPreparation {
  contract: "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1";
  client_id: number;
  scenario_id: string;
  state: "INCOMPLETE" | "BLOCKED" | "PREPARED";
  candidate: unknown | null;
  incomplete_reasons: string[];
  blockers: string[];
  preparation_fingerprint: string;
  professional_authority: false;
  execution_allowed: false;
  tax_authority_approval: null;
}
export interface ProfessionalDecision {
  group: ReviewGroup;
  source_id: string;
  determination: ReviewDetermination;
  reason: string;
  evidence_references: string[];
  eligibility_date: string | null;
  tax_year: number | null;
  parameter_set_id: string | null;
  tax_classification: "QUALIFYING_PENSION_FOR_FIXATION" | "NON_QUALIFYING_PENSION_FOR_FIXATION" | null;
  inclusion_decision: Inclusion | null;
  support_status: Support | null;
  accepted_for_use: boolean | null;
  payment_status: "PAID" | "NOT_PAID" | "UNKNOWN" | null;
  overlap_resolution: "NO_OVERLAP" | "SAME_RIGHT_USE_GRANT" | "SAME_RIGHT_USE_COMPONENT" | "DISTINCT_RIGHTS" | null;
  matched_source_ids: string[];
}

export interface ReadinessSourceEvidence {
  m07: Array<{ revision_id: string; status: string; evidence_fingerprint: string | null }>;
  grants: Array<{ grant_id: string; payment_classification: string; source_fingerprint: string }>;
  severance_choice_source_ids: Array<{
    source_kind: string; source_id: string; state: string; source_fingerprint: string;
  }>;
  historical_capitalizations: Array<{
    capitalization_id: string; reported_amount_ils: string;
    capitalization_date: string; source_label: string | null;
  }>;
  pension_gross_result_fingerprint: string | null;
  official_parameter_set: null;
  tax_year: null;
}
export interface ReviewReadiness {
  scenario_version: number;
  manifest_fingerprint: string;
  readiness_fingerprint: string;
  readiness_state: "BLOCKED";
  blockers: string[];
  mapping: Record<string, {
    source: string; present: boolean; verified: boolean;
    scenario_bound: boolean; professional_decision_required: boolean;
    blocker: string | null; references: string[];
  }>;
  source_evidence: ReadinessSourceEvidence;
  professional_authority: false;
  execution_allowed: false;
}
export interface ProfessionalReview {
  contract: "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1";
  client_id: number;
  scenario_id: string;
  approval_id: string | null;
  approval_version: number;
  record_status: "MISSING" | "DRAFT" | "BLOCKED";
  validity_state: "BLOCKED" | "STALE";
  decisions: ProfessionalDecision[];
  admission_controls?: FixationAdmissionControls | null;
  actor_id: string | null;
  approval_fingerprint: string | null;
  dependency_fingerprint: string | null;
  readiness_fingerprint_at_save: string | null;
  current_readiness: ReviewReadiness;
  blockers: string[];
  professional_authority: false;
  execution_allowed: false;
  tax_authority_approval: null;
}
export interface ReviewHistoryItem {
  revision_id: string;
  approval_version: number;
  scenario_version: number;
  decisions: ProfessionalDecision[];
  admission_controls?: FixationAdmissionControls | null;
  blockers: string[];
  action: string;
  actor_id: string;
  occurred_at: string;
  professional_authority: false;
  tax_authority_approval: null;
}
export interface ReviewSaveInput {
  expected_approval_version: number;
  expected_scenario_version: number;
  expected_manifest_fingerprint: string;
  expected_readiness_fingerprint: string;
  decisions: ProfessionalDecision[];
  admission_controls: FixationAdmissionControls | null;
}
export interface ApprovalDenial {
  approval_attempt_state: "BLOCKED";
  blockers: string[];
  professional_authority: false;
  execution_allowed: false;
  tax_authority_approval: null;
}

export class ReviewApiError extends Error {
  constructor(public status: number, public code: string, public blockers: string[] = []) {
    super(code);
  }
}

async function call<T>(clientId: number, scenarioId: string, suffix: string,
                       method = "GET", body?: unknown): Promise<T> {
  const url = buildApiUrl(
    `/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/fixation-professional-review${suffix}`,
  );
  const response = await apiFetch(url, {
    method,
    ...(body === undefined ? {} : {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  });
  const data: unknown = await response.json().catch(() => null);
  const obj = data && typeof data === "object" ? data as Record<string, unknown> : {};
  const code = typeof obj.code === "string" ? obj.code : `HTTP_${response.status}`;
  const blockers = Array.isArray(obj.blockers)
    ? obj.blockers.filter((value): value is string => typeof value === "string") : [];
  if (!response.ok) {
    // The existing approve route deliberately returns 422 plus structured blockers.
    if (response.status === 422 && obj.approval_attempt_state === "BLOCKED") {
      return data as T;
    }
    throw new ReviewApiError(response.status, code, blockers);
  }
  if (data === null) throw new ReviewApiError(response.status, "FIXATION_REVIEW_EMPTY_RESPONSE");
  return data as T;
}

function verify(read: ProfessionalReview, clientId: number, scenarioId: string): ProfessionalReview {
  const current = read.current_readiness;
  if (read.client_id !== clientId || read.scenario_id !== scenarioId
      || read.contract !== "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1"
      || current?.scenario_version === undefined
      || current.manifest_fingerprint?.length !== 64
      || current.readiness_fingerprint?.length !== 64
      || read.professional_authority !== false || read.execution_allowed !== false) {
    throw new ReviewApiError(409, "FIXATION_REVIEW_IDENTITY_INVALID");
  }
  return read;
}

export const readProfessionalReview = async (clientId: number, scenarioId: string) =>
  verify(await call<ProfessionalReview>(clientId, scenarioId, ""), clientId, scenarioId);
export const saveProfessionalReview = async (
  clientId: number, scenarioId: string, body: ReviewSaveInput,
) => verify(await call<ProfessionalReview>(clientId, scenarioId, "", "PUT", body), clientId, scenarioId);
export const readProfessionalReviewHistory = (clientId: number, scenarioId: string) =>
  call<ReviewHistoryItem[]>(clientId, scenarioId, "/history");
export const requestProfessionalApproval = (clientId: number, scenarioId: string,
                                            version: number, fingerprint: string) =>
  call<ApprovalDenial>(clientId, scenarioId, "/approve", "POST", {
    expected_approval_version: version, expected_approval_fingerprint: fingerprint,
  });

export async function readFixationAdmissionPreparation(clientId: number, scenarioId: string) {
  const url = buildApiUrl(
    `/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/fixation-admission-preparation`,
  );
  const response = await apiFetch(url, { method: "GET" });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const obj = data && typeof data === "object" ? data as Record<string, unknown> : {};
    throw new ReviewApiError(response.status,
      typeof obj.code === "string" ? obj.code : `HTTP_${response.status}`);
  }
  const result = data as FixationPreparation;
  if (result?.contract !== "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1"
      || result.client_id !== clientId || result.scenario_id !== scenarioId
      || result.professional_authority !== false || result.execution_allowed !== false) {
    throw new ReviewApiError(409, "FIXATION_PREPARATION_IDENTITY_INVALID");
  }
  return result;
}

export interface FixationAdmissionEligibilityReason {
  code: string;
  source_ids: string[];
}
export interface FixationAdmissionEligibility {
  contract: "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1";
  client_id: number;
  scenario_id: string;
  preparation_fingerprint: string;
  eligibility_fingerprint: string;
  state: "INCOMPLETE" | "BLOCKED" | "REQUIRES_EXTERNAL_VALIDATION" | "ELIGIBLE_FOR_ADMISSION_REVIEW";
  reasons: FixationAdmissionEligibilityReason[];
  professional_authority: false;
  execution_allowed: false;
  admission_review_required: boolean;
  tax_authority_approval: null;
}
export async function readFixationAdmissionEligibility(clientId: number, scenarioId: string): Promise<FixationAdmissionEligibility> {
  const url = buildApiUrl(
    `/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/fixation-admission-eligibility`,
  );
  const response = await apiFetch(url, { method: "GET" });
  const raw: unknown = await response.json().catch(() => null);
  const record = raw && typeof raw === "object" && !Array.isArray(raw)
    ? raw as Record<string, unknown> : {};
  if (!response.ok) {
    throw new ReviewApiError(response.status,
      typeof record.code === "string" ? record.code : `HTTP_${response.status}`);
  }
  const permitted = ["INCOMPLETE", "BLOCKED", "REQUIRES_EXTERNAL_VALIDATION", "ELIGIBLE_FOR_ADMISSION_REVIEW"];
  const reasons = record.reasons;
  const safe = record.contract === "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1"
    && record.client_id === clientId && record.scenario_id === scenarioId
    && permitted.includes(String(record.state))
    && typeof record.preparation_fingerprint === "string"
    && /^[0-9a-f]{64}$/.test(record.preparation_fingerprint)
    && typeof record.eligibility_fingerprint === "string"
    && /^[0-9a-f]{64}$/.test(record.eligibility_fingerprint)
    && Array.isArray(reasons)
    && reasons.every(item => item !== null && typeof item === "object"
      && typeof item.code === "string" && item.code.length > 0
      && Array.isArray(item.source_ids)
      && item.source_ids.every((id: unknown) => typeof id === "string"))
    && record.professional_authority === false && record.execution_allowed === false
    && record.tax_authority_approval === null
    && record.admission_review_required === (record.state === "ELIGIBLE_FOR_ADMISSION_REVIEW")
    && (record.state !== "ELIGIBLE_FOR_ADMISSION_REVIEW" || reasons.length === 0);
  if (!safe) throw new ReviewApiError(409, "FIXATION_ELIGIBILITY_RESPONSE_INVALID");
  return raw as FixationAdmissionEligibility;
}

export interface FixationAdmissionReviewReason {
  code: string;
  path: string | null;
  message: string | null;
  source_ids: string[];
}
export interface FixationAdmissionReview {
  contract: "SCENARIO_FIXATION_ADMISSION_REVIEW_V1";
  client_id: number;
  scenario_id: string;
  state: "ADMITTED_FOR_REVIEW" | "REJECTED";
  preparation_fingerprint: string;
  eligibility_fingerprint: string;
  admission_review_fingerprint: string;
  reasons: FixationAdmissionReviewReason[];
  admission_contract_validated: boolean;
  professional_authority: false;
  execution_allowed: false;
  tax_calculation_performed: false;
  tax_authority_approval: null;
}

const SHA256_HEX = /^[0-9a-f]{64}$/;

export async function readFixationAdmissionReview(
  clientId: number,
  scenarioId: string,
  expectedPreparationFingerprint: string,
  expectedEligibilityFingerprint: string,
): Promise<FixationAdmissionReview> {
  if (!SHA256_HEX.test(expectedPreparationFingerprint)
      || !SHA256_HEX.test(expectedEligibilityFingerprint)) {
    throw new ReviewApiError(400, "FIXATION_ADMISSION_REVIEW_FINGERPRINT_INVALID");
  }
  const query = new URLSearchParams({
    expected_preparation_fingerprint: expectedPreparationFingerprint,
    expected_eligibility_fingerprint: expectedEligibilityFingerprint,
  });
  const url = buildApiUrl(
    `/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}/fixation-admission-review?${query}`,
  );
  const response = await apiFetch(url, { method: "GET" });
  const raw: unknown = await response.json().catch(() => null);
  const record = raw && typeof raw === "object" && !Array.isArray(raw)
    ? raw as Record<string, unknown> : {};
  if (!response.ok) {
    throw new ReviewApiError(response.status,
      typeof record.code === "string" ? record.code : `HTTP_${response.status}`);
  }
  const reasons = record.reasons;
  const admitted = record.state === "ADMITTED_FOR_REVIEW";
  const rejected = record.state === "REJECTED";
  const safe = record.contract === "SCENARIO_FIXATION_ADMISSION_REVIEW_V1"
    && record.client_id === clientId && record.scenario_id === scenarioId
    && (admitted || rejected)
    && typeof record.preparation_fingerprint === "string"
    && SHA256_HEX.test(record.preparation_fingerprint)
    && typeof record.eligibility_fingerprint === "string"
    && SHA256_HEX.test(record.eligibility_fingerprint)
    && (!admitted || (
      record.preparation_fingerprint === expectedPreparationFingerprint
      && record.eligibility_fingerprint === expectedEligibilityFingerprint
    ))
    && typeof record.admission_review_fingerprint === "string"
    && SHA256_HEX.test(record.admission_review_fingerprint)
    && Array.isArray(reasons)
    && reasons.every(item => item !== null && typeof item === "object" && !Array.isArray(item)
      && typeof item.code === "string" && item.code.length > 0
      && (item.path === null || (typeof item.path === "string" && item.path.length > 0))
      && (item.message === null || (typeof item.message === "string" && item.message.length > 0))
      && Array.isArray(item.source_ids)
      && item.source_ids.every((id: unknown) => typeof id === "string" && id.length > 0))
    && record.admission_contract_validated === admitted
    && (admitted ? reasons.length === 0 : reasons.length > 0)
    && record.professional_authority === false
    && record.execution_allowed === false
    && record.tax_calculation_performed === false
    && record.tax_authority_approval === null;
  if (!safe) throw new ReviewApiError(409, "FIXATION_ADMISSION_REVIEW_RESPONSE_INVALID");
  return raw as FixationAdmissionReview;
}
