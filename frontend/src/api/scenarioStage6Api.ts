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
  scenario_id: string;
  decision_id: string;
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
