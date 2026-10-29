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
export interface ScenarioPensionAggregate {
  schema_version: "STAGE6_PENSION_DECISION_AGGREGATE_V1";
  client_id: number;
  scenario_id: string;
  scenario_version: number | null;
  aggregation_state: "COMPLETE" | "PARTIAL" | "BLOCKED";
  blockers: string[];
  decision_results: ScenarioGrossEstimate[];
  monthly_pension_gross_total_ils: string | null;
  comparison_basis: {
    currency: "ILS";
    income_basis: "GROSS";
    price_basis: "NOMINAL_UNINDEXED";
    retirement_target_date: string;
    source_reference_date: string;
  } | null;
  execution_allowed: false;
  aggregate_fingerprint: string;
}
export interface ScenarioMonthlyCashflow {
  schema_version: "STAGE6_MONTHLY_RETIREMENT_CASHFLOW_V1";
  client_id: number;
  scenario_id: string;
  scenario_version: number | null;
  manifest_fingerprint: string | null;
  start_month: string;
  end_month: string;
  cashflow_state: "COMPLETE" | "PARTIAL" | "BLOCKED";
  blocker_codes: string[];
  sources: Array<{
    source_id: string;
    source_kind: "CALCULATED_PENSION" | "KNOWN_RECURRING_INCOME";
    decision_id: string | null;
    recurring_income_id: number | null;
    label: string;
    monthly_amount_gross_ils: string | null;
    income_basis: "GROSS" | null;
    price_basis: "NOMINAL_UNINDEXED" | "STATED_NOMINAL_NO_INDEXATION" | null;
    start_date: string | null;
    end_date: string | null;
    source_reference_date: string | null;
    authority_fingerprint: string;
    source_state: "READY" | "BLOCKED";
    blocker_codes: string[];
  }>;
  monthly_rows: Array<{
    month: string;
    cashflow_state: "COMPLETE" | "PARTIAL" | "BLOCKED";
    contributions: Array<{
      source_id: string;
      source_kind: "CALCULATED_PENSION" | "KNOWN_RECURRING_INCOME";
      amount_monthly_gross_ils: string;
      contribution_state: "KNOWN" | "CALCULATED";
    }>;
    known_income_subtotal_ils: string;
    calculated_pension_subtotal_ils: string;
    gross_income_total_ils: string | null;
    blocker_codes: string[];
  }>;
  execution_allowed: false;
  cashflow_fingerprint: string;
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

export async function readScenarioPensionAggregate(
  clientId: number, scenarioId: string): Promise<ScenarioPensionAggregate> {
  return read(clientId, scenarioId, "/pension-gross-summary");
}

export async function readScenarioMonthlyCashflow(
  clientId: number, scenarioId: string, startMonth: string, endMonth: string,
): Promise<ScenarioMonthlyCashflow> {
  const query = new URLSearchParams({ start_month: startMonth, end_month: endMonth });
  return read(clientId, scenarioId, `/monthly-income-cashflow?${query.toString()}`);
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
      source_fingerprint: string | null;
      balance: string | null;
      allocated: string;
      allocation_by_action: { pension: string; capital_asset: string };
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
      || value.candidate_blockers.some(code => typeof code !== "string" || !code)
      || value.allocation_evidence.blocker_codes.some(code => typeof code !== "string" || !code)
      || (value.allocation_evidence.overall_status === "STRUCTURAL_ONLY"
          && value.allocation_evidence.blocker_codes.length !== 0)
      || (value.overall_status === "STRUCTURAL_ONLY"
          && (value.candidate_evidence_state !== "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
              || value.candidate_blockers.length !== 0
              || value.allocation_evidence.overall_status !== "STRUCTURAL_ONLY"))
      || (value.allocation_evidence.overall_status === "BLOCKED"
          && value.overall_status !== "BLOCKED")) return false;
  const sortedUnique = (codes: string[]): boolean =>
    codes.every((code, index) => typeof code === "string" && code.length > 0
      && (index === 0 || codes[index - 1] < code));
  if (!sortedUnique(value.candidate_blockers)
      || !sortedUnique(value.allocation_evidence.blocker_codes)) return false;
  const cents = (amount: string): bigint => {
    const [whole, fraction] = amount.split(".");
    return BigInt(whole) * 100n + BigInt(fraction);
  };
  const seenSources = new Set<string>();
  const seenDecisions = new Set<string>();
  if (value.allocation_evidence.sources.some(row =>
      !row || typeof row.product_id !== "string" || !row.product_id
      || typeof row.component_id !== "string" || !row.component_id
      || (row.component_code !== null && (typeof row.component_code !== "string" || !row.component_code))
      || (row.source_fingerprint !== null && !sha(row.source_fingerprint))
      || !money(row.allocated)
      || !row.allocation_by_action
      || !money(row.allocation_by_action.pension)
      || !money(row.allocation_by_action.capital_asset)
      || (row.balance !== null && !money(row.balance))
      || (row.unallocated !== null && !money(row.unallocated))
      || (row.status !== "BLOCKED" && row.status !== "STRUCTURAL_ONLY")
      || !Array.isArray(row.blocker_codes)
      || !sortedUnique(row.blocker_codes)
      || !Array.isArray(row.decision_ids)
      || row.decision_ids.some(id => typeof id !== "string" || !id)
      || row.decision_ids.length === 0
      || (row.status === "BLOCKED" && row.unallocated !== null)
      || (row.status === "STRUCTURAL_ONLY" && (row.unallocated === null || row.blocker_codes.length > 0))
  )) return false;
  let priorKey = "";
  for (const row of value.allocation_evidence.sources) {
    // Source identity is a tuple; JSON encoding avoids concatenation collisions.
    const key = JSON.stringify([row.product_id, row.component_id]);
    if (seenSources.has(key) || (priorKey && key <= priorKey)) return false;
    priorKey = key;
    seenSources.add(key);
    for (const id of row.decision_ids) {
      if (seenDecisions.has(id)) return false;
      seenDecisions.add(id);
    }
    if (cents(row.allocated) !== cents(row.allocation_by_action.pension)
        + cents(row.allocation_by_action.capital_asset)) return false;
    if (row.status === "BLOCKED"
        && value.allocation_evidence.overall_status !== "BLOCKED") return false;
    if (row.status === "STRUCTURAL_ONLY") {
      if (row.balance === null || row.unallocated === null) return false;
      if (cents(row.balance) !== cents(row.allocated) + cents(row.unallocated)) return false;
    }
  }
  if (value.allocation_evidence.overall_status === "STRUCTURAL_ONLY"
      && value.allocation_evidence.sources.length === 0) return false;
  return true;
}
