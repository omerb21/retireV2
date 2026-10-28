import { apiFetch, buildApiUrl } from "./apiBase";

export interface ScenarioPensionElection {
  decision_id: string;
  pension_start_date: string;
  target_year: number;
  survivors_option: string;
  spouse_age_diff: number;
  coefficient_selection: "manual_review_required" | "catalog_candidate";
  company_name: string | null;
  option_name: string | null;
}
export interface ScenarioGrossEstimate {
  schema_version: "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1";
  client_id: number;
  scenario_id: string;
  scenario_version: number | null;
  decision_id: string;
  source_id: string | null;
  result_fingerprint: string;
  professional_admission_fingerprint: string | null;
  result_state: "RESULT_READY" | "BLOCKED";
  execution_allowed: boolean;
  blockers: string[];
  monthly_estimate_gross_ils: string | null;
  coefficient_provenance: {
    source_level: "MANUAL_PROFESSIONAL_OVERRIDE";
    factor_value: string;
    factor_evidence_type: string;
    factor_evidence_reference: string;
    payout_option_name: string;
    admission_revision: number;
  } | null;
  planning_calculation_input_fingerprint: string | null;
  monthly_basis_semantic_fingerprint: string | null;
  monthly_basis_source_fingerprint: string | null;
  temporal_semantic_fingerprint: string | null;
  temporal_source_fingerprint: string | null;
  pte_source_execution_fingerprint: string | null;
  pte_source_result_fingerprint: string | null;
  retirement_target_date: string | null;
  statement_date: string | null;
}

async function read<T>(clientId: number, scenarioId: string, suffix: string,
                       options: RequestInit = {}): Promise<T> {
  const url = buildApiUrl(`/clients/${clientId}/scenario-drafts/${encodeURIComponent(scenarioId)}${suffix}`);
  const response = await apiFetch(url, options);
  if (!response.ok) {
    const parsed = await response.json().catch(() => null);
    throw Error(typeof parsed?.code === "string" ? parsed.code : "STAGE6_WORKFLOW_UNAVAILABLE");
  }
  return response.json() as Promise<T>;
}

export async function listScenarioPensionElections(clientId: number, scenarioId: string):
  Promise<ScenarioPensionElection[]> {
  const response = await read<{ elections: ScenarioPensionElection[] }>(clientId, scenarioId, "/pension-elections");
  // The read projection contains "authority_state" for display only. Never
  // send it back: the SC-05C writer uses an exact extra=forbid schema.
  return response.elections.map(row => ({
    decision_id: row.decision_id,
    pension_start_date: row.pension_start_date,
    target_year: row.target_year,
    survivors_option: row.survivors_option,
    spouse_age_diff: row.spouse_age_diff,
    coefficient_selection: row.coefficient_selection,
    company_name: row.company_name,
    option_name: row.option_name,
  }));
}

export async function saveScenarioPensionElections(clientId: number, scenarioId: string,
  expectedScenarioVersion: number, elections: ScenarioPensionElection[]): Promise<unknown> {
  return read(clientId, scenarioId, "/pension-elections", {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_scenario_version: expectedScenarioVersion, elections }),
  });
}

export async function readScenarioGrossEstimate(
  clientId: number, scenarioId: string, decisionId: string): Promise<ScenarioGrossEstimate> {
  return read(clientId, scenarioId,
    `/pension-decisions/${encodeURIComponent(decisionId)}/gross-estimate`);
}


export type FactorEvidenceType = "INSURER_QUOTE" | "POLICY_CONTRACT" | "PLANNER_ASSUMPTION";
export interface FactorAdmissionCursor {
  scenario_version: number;
  latest_admission_revision: number;
  authority_state: "NOT_EVALUATED";
}
export interface FactorAdmissionReceipt {
  admission_revision: number;
  professional_admission_fingerprint: string;
  execution_allowed: false;
}

export function readFactorAdmissionCursor(
  clientId: number, scenarioId: string, decisionId: string): Promise<FactorAdmissionCursor> {
  return read(clientId, scenarioId,
    `/pension-decisions/${encodeURIComponent(decisionId)}/factor-admissions/revision`);
}
export function submitProfessionalFactorAdmission(
  clientId: number, scenarioId: string, decisionId: string,
  payload: {
    expected_scenario_version: number;
    expected_admission_revision: number;
    factor_value: string;
    factor_evidence_type: FactorEvidenceType;
    factor_evidence_reference: string;
  }): Promise<FactorAdmissionReceipt> {
  return read(clientId, scenarioId,
    `/pension-decisions/${encodeURIComponent(decisionId)}/factor-admissions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
}


/** Read-only structural allocation evidence; never a financial result. */
export interface ScenarioAllocationEvidence {
  manifest_fingerprint: string;
  candidate_evidence_state: string;
  candidate_blockers: string[];
  overall_status: "BLOCKED" | "STRUCTURAL_ONLY";
  allocation_evidence: {
    schema_version: "SCENARIO_ALLOCATION_EVIDENCE_V1";
    client_id: number;
    scenario_id: string;
    scenario_version: number;
    manifest_fingerprint: string;
    overall_status: "BLOCKED" | "STRUCTURAL_ONLY";
    blocker_codes: string[];
    evidence_fingerprint: string;
    sources: Array<{
      product_id: string;
      component_id: string;
      component_code: string | null;
      balance: string | null;
      allocated: string;
      unallocated: string | null;
      status: "BLOCKED" | "STRUCTURAL_ONLY";
      blocker_codes: string[];
      decision_ids: string[];
    }>;
    financial_result: null;
    execution_allowed: false;
  };
  financial_result: null;
  execution_allowed: false;
}

export function readScenarioAllocationEvidence(
  clientId: number, scenarioId: string): Promise<ScenarioAllocationEvidence> {
  return read(clientId, scenarioId, "/allocation-evidence");
}

/** Validate the exact informational result before presenting financial-looking amounts.
 * This is UI response integrity only, not proof of server-side authority. */
export function validScenarioAllocationEvidence(
  value: ScenarioAllocationEvidence, clientId: number, scenarioId: string,
  scenarioVersion: number): boolean {
  const sha = (x: unknown): x is string => typeof x === "string" && /^[0-9a-f]{64}$/.test(x);
  const money = (x: unknown): x is string => typeof x === "string"
    && /^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(x);
  if (!value || !value.allocation_evidence
      || value.execution_allowed !== false || value.financial_result !== null
      || value.allocation_evidence.execution_allowed !== false
      || value.allocation_evidence.financial_result !== null
      || value.allocation_evidence.schema_version !== "SCENARIO_ALLOCATION_EVIDENCE_V1"
      || value.allocation_evidence.client_id !== clientId
      || value.allocation_evidence.scenario_id !== scenarioId
      || value.allocation_evidence.scenario_version !== scenarioVersion
      || !sha(value.manifest_fingerprint)
      || value.manifest_fingerprint !== value.allocation_evidence.manifest_fingerprint
      || !sha(value.allocation_evidence.evidence_fingerprint)
      || !["BLOCKED", "STRUCTURAL_ONLY"].includes(value.overall_status)
      || !["BLOCKED", "STRUCTURAL_ONLY"].includes(value.allocation_evidence.overall_status)
      || !["BLOCKED", "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"].includes(value.candidate_evidence_state)
      || !Array.isArray(value.candidate_blockers)
      || !Array.isArray(value.allocation_evidence.blocker_codes)
      || !Array.isArray(value.allocation_evidence.sources)
      || (value.overall_status === "STRUCTURAL_ONLY"
          && (value.candidate_evidence_state !== "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
              || value.candidate_blockers.length !== 0
              || value.allocation_evidence.overall_status !== "STRUCTURAL_ONLY"))
      || (value.allocation_evidence.overall_status === "BLOCKED"
          && value.overall_status !== "BLOCKED")) return false;
  if (value.allocation_evidence.sources.some(row =>
      !row || typeof row.product_id !== "string" || !row.product_id
      || typeof row.component_id !== "string" || !row.component_id
      || !money(row.allocated)
      || (row.balance !== null && !money(row.balance))
      || (row.unallocated !== null && !money(row.unallocated))
      || (row.status !== "BLOCKED" && row.status !== "STRUCTURAL_ONLY")
      || !Array.isArray(row.blocker_codes)
      || row.blocker_codes.some(code => typeof code !== "string")
      || !Array.isArray(row.decision_ids)
      || row.decision_ids.some(id => typeof id !== "string" || !id)
      || (row.status === "BLOCKED" && row.unallocated !== null)
      || (row.status === "STRUCTURAL_ONLY" && (row.unallocated === null || row.blocker_codes.length > 0))
  )) return false;
  return true;
}
