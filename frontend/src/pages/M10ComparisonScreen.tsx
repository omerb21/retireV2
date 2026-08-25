import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiTransportError } from "../api/clientsApi";
import {
  M09_SUBJECT_FAMILY,
  listM09SubjectRuns,
  listM09Subjects,
  type M09ScenarioSubject,
  type M09SubjectRunSummary,
} from "../api/m09CashflowApi";
import {
  M10_COMPARATOR_BLOCKER_CODES,
  compareM10Runs,
  type M10ComparatorBlockerCode,
  type M10ComparisonResponse,
  type M10MetricComparison,
  type M10RunEvidence,
} from "../api/m10ComparisonApi";
import { useClientContextGeneration, type ClientContextToken } from "../hooks/useClientContextGeneration";

type DiscoveryStatus =
  | "initial"
  | "ready"
  | "no_baseline"
  | "ambiguous_baseline"
  | "no_adjusted"
  | "unavailable"
  | "transport_error";

type Candidate = {
  subject: M09ScenarioSubject;
  run: M09SubjectRunSummary;
};

type ComparatorBlocker = {
  code: M10ComparatorBlockerCode;
  message: string;
};

type AdjustmentEvidence = M09ScenarioSubject["adjustments"][number];

const ADJUSTMENT_AMOUNT = /^(?:0\.(?:0[1-9]|[1-9]\d)|[1-9]\d{0,17}\.\d{2})$/;
const ADJUSTMENT_MONTH = /^\d{4}-(?:0[1-9]|1[0-2])$/;
const ADJUSTMENT_PROVENANCE = "planner_declared_scenario_adjustment";
const BASELINE_PROVENANCE = "server_resolved_no_scenario_adjustments";

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function hasServerOwnedBaselineEvidence(candidate: Candidate, clientId: number): boolean {
  const { run, subject } = candidate;
  return isNonEmptyString(subject.scenario_subject_id)
    && subject.scenario_subject_id === run.scenario_subject_id
    && subject.client_id === clientId
    && subject.scenario_family === M09_SUBJECT_FAMILY
    && subject.scenario_contract_version === "v1"
    && subject.combined_contract_identifier === "declared_retirement_cashflow_adjustments/v1"
    && subject.subject_type === "baseline"
    && run.is_current === true
    && run.eligible_for_m10 === true
    && subject.provenance === BASELINE_PROVENANCE
    && typeof subject.adjustment_manifest === "object"
    && subject.adjustment_manifest !== null
    && !Array.isArray(subject.adjustment_manifest)
    && subject.adjustment_manifest.baseline_evidence === BASELINE_PROVENANCE;
}

function ServerOwnedBaselineReference({ candidate, clientId }: {
  candidate: Candidate;
  clientId: number;
}) {
  const valid = hasServerOwnedBaselineEvidence(candidate, clientId);
  return <section aria-label="Server-owned baseline reference">
    <h3>Server-owned baseline reference</h3>
    {valid ? <>
      <p>No planner-declared scenario adjustments.</p>
      <p>Provenance: <code>{BASELINE_PROVENANCE}</code></p>
    </> : <p>Server-owned baseline reference evidence unavailable.</p>}
  </section>;
}

function selectedAdjustmentEvidence(candidate: Candidate | null, clientId: number): AdjustmentEvidence[] | null {
  if (candidate === null) return null;
  const { run, subject } = candidate;
  if (!isNonEmptyString(subject.scenario_subject_id)
    || subject.scenario_subject_id !== run.scenario_subject_id
    || subject.client_id !== clientId
    || subject.scenario_family !== M09_SUBJECT_FAMILY
    || subject.scenario_contract_version !== "v1"
    || subject.combined_contract_identifier !== "declared_retirement_cashflow_adjustments/v1"
    || subject.subject_type !== "adjusted"
    || subject.provenance !== ADJUSTMENT_PROVENANCE
    || typeof subject.adjustment_manifest !== "object"
    || subject.adjustment_manifest === null
    || Array.isArray(subject.adjustment_manifest)
    || !isNonEmptyString(subject.adjustment_manifest_fingerprint)
    || !isNonEmptyString(subject.calculation_semantic_fingerprint)
    || !isNonEmptyString(subject.integrity_fingerprint)
    || !isNonEmptyString(subject.actor)
    || subject.actor_is_authentication !== false
    || !isNonEmptyString(subject.created_at)
    || !Array.isArray(subject.adjustments)
    || subject.adjustments.length === 0
    || run.is_current !== true
    || run.eligible_for_m10 !== true) return null;

  const adjustmentIds = new Set<string>();
  for (let index = 0; index < subject.adjustments.length; index += 1) {
    const adjustment = subject.adjustments[index] as unknown as Record<string, unknown>;
    if (typeof adjustment !== "object" || adjustment === null
      || !isNonEmptyString(adjustment.adjustment_id)
      || adjustmentIds.has(adjustment.adjustment_id)
      || typeof adjustment.ordinal !== "number"
      || !Number.isInteger(adjustment.ordinal)
      || adjustment.ordinal !== index + 1
      || (adjustment.adjustment_type !== "declared_additional_monthly_income"
        && adjustment.adjustment_type !== "declared_additional_monthly_expense")
      || typeof adjustment.amount !== "string"
      || !ADJUSTMENT_AMOUNT.test(adjustment.amount)
      || typeof adjustment.start_month !== "string"
      || !ADJUSTMENT_MONTH.test(adjustment.start_month)
      || typeof adjustment.end_month !== "string"
      || !ADJUSTMENT_MONTH.test(adjustment.end_month)
      || adjustment.end_month < adjustment.start_month
      || adjustment.provenance !== ADJUSTMENT_PROVENANCE
      || !isNonEmptyString(adjustment.semantic_fingerprint)
      || !isNonEmptyString(adjustment.actor)
      || !isNonEmptyString(adjustment.created_at)) return null;
    adjustmentIds.add(adjustment.adjustment_id);
  }
  return subject.adjustments;
}

function adjustmentTypeLabel(type: AdjustmentEvidence["adjustment_type"]): string {
  return type === "declared_additional_monthly_income"
    ? "Declared additional monthly income"
    : "Declared additional monthly expense";
}

function SelectedAdjustmentEvidence({ candidate, clientId }: {
  candidate: Candidate;
  clientId: number;
}) {
  const adjustments = selectedAdjustmentEvidence(candidate, clientId);
  return <section aria-label="Selected scenario adjustment evidence">
    <h3>Selected scenario adjustment evidence</h3>
    <p>Scenario subject ID: {candidate.subject.scenario_subject_id}</p>
    {adjustments === null ? <p>Selected scenario adjustment evidence unavailable.</p> : <ol>
      {adjustments.map(adjustment => <li key={adjustment.adjustment_id}>
        <h4>{adjustmentTypeLabel(adjustment.adjustment_type)}</h4>
        <dl>
          <dt>Occurrence ID</dt><dd>{adjustment.adjustment_id}</dd>
          <dt>Ordinal</dt><dd>{adjustment.ordinal}</dd>
          <dt>Adjustment type</dt><dd><code>{adjustment.adjustment_type}</code></dd>
          <dt>Amount</dt><dd>{adjustment.amount}</dd>
          <dt>Start month</dt><dd>{adjustment.start_month}</dd>
          <dt>End month</dt><dd>{adjustment.end_month}</dd>
          <dt>Provenance</dt><dd><code>{adjustment.provenance}</code></dd>
        </dl>
      </li>)}
    </ol>}
  </section>;
}

const BLOCKER_TEXT: Record<M10ComparatorBlockerCode, string> = {
  comparison_run_unavailable: "A requested comparison run is unavailable.",
  comparison_same_subject: "The two runs belong to the same scenario subject.",
  comparison_pair_role_invalid: "The submitted runs do not have the required baseline and adjusted roles.",
  comparison_scenario_contract_mismatch: "The scenario contract evidence does not match.",
  comparison_horizon_mismatch: "The comparison horizons do not match.",
  comparison_factual_baseline_material_mismatch: "The factual baseline material does not match.",
  comparison_component_domain_contract_mismatch: "The component-domain contract evidence does not match.",
  comparison_engine_version_mismatch: "The engine-version evidence does not match.",
  comparison_result_schema_version_mismatch: "The result-schema evidence does not match.",
  comparison_factual_upstream_version_mismatch: "The factual upstream-version evidence does not match.",
  comparison_run_not_current: "A submitted run is not current.",
  comparison_run_not_eligible: "A submitted run is not eligible for M10 comparison.",
  comparison_fingerprint_invalid: "Comparison fingerprint evidence is invalid.",
  comparison_semantically_identical_manifest: "The adjustment manifests are semantically identical.",
  comparison_month_alignment_mismatch: "The persisted monthly evidence is not aligned.",
  comparison_numeric_domain_invalid: "Persisted numeric evidence is outside the accepted domain.",
};

const METRICS = [
  ["gross_inflow_total", "Gross inflow total"],
  ["gross_outflow_total", "Gross outflow total"],
  ["period_net", "Period net"],
] as const;

function transportMessage(error: unknown, context: string): string {
  if (error instanceof ApiTransportError) {
    return `${context}: HTTP ${error.status} ${error.statusText}`.trim();
  }
  if (error instanceof Error) return `${context}: ${error.message}`;
  return `${context}: request failed`;
}

function comparatorBlocker(error: unknown): ComparatorBlocker | null {
  if (!(error instanceof ApiTransportError)) return null;
  if (typeof error.body !== "object" || error.body === null) return null;
  const detail = (error.body as { detail?: unknown }).detail;
  if (typeof detail !== "object" || detail === null) return null;
  const code = (detail as { code?: unknown }).code;
  const message = (detail as { message?: unknown }).message;
  if (typeof code !== "string" || typeof message !== "string") return null;
  if (!M10_COMPARATOR_BLOCKER_CODES.includes(code as M10ComparatorBlockerCode)) return null;
  if (code === "comparison_run_unavailable" ? error.status !== 404 : error.status !== 409) return null;
  return { code: code as M10ComparatorBlockerCode, message };
}

function hasAcceptedSubjectContract(subject: M09ScenarioSubject): boolean {
  return subject.scenario_family === M09_SUBJECT_FAMILY
    && subject.scenario_contract_version === "v1"
    && subject.combined_contract_identifier === "declared_retirement_cashflow_adjustments/v1"
    && (subject.subject_type === "baseline" || subject.subject_type === "adjusted");
}

function eligibleRuns(runs: M09SubjectRunSummary[]): M09SubjectRunSummary[] {
  return runs.filter(run => run.is_current === true && run.eligible_for_m10 === true);
}

function compareText(left: string, right: string): number {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function RunEvidence({ title, evidence }: { title: string; evidence: M10RunEvidence }) {
  return <section aria-label={title}>
    <h4>{title}</h4>
    <dl>
      <dt>Run ID</dt><dd>{evidence.run_id}</dd>
      <dt>Scenario subject ID</dt><dd>{evidence.scenario_subject_id}</dd>
      <dt>Subject type</dt><dd>{evidence.subject_type}</dd>
      <dt>Calculation semantic fingerprint</dt><dd>{evidence.calculation_semantic_fingerprint}</dd>
      <dt>Integrity fingerprint</dt><dd>{evidence.integrity_fingerprint}</dd>
      <dt>Adjustment manifest fingerprint</dt><dd>{evidence.adjustment_manifest_fingerprint}</dd>
      <dt>Factual inventory fingerprint</dt><dd>{evidence.factual_inventory_fingerprint}</dd>
      <dt>Upstream snapshot fingerprint</dt><dd>{evidence.upstream_snapshot_fingerprint}</dd>
      <dt>Semantic result fingerprint</dt><dd>{evidence.semantic_result_fingerprint}</dd>
      <dt>Result integrity fingerprint</dt><dd>{evidence.result_integrity_fingerprint}</dd>
    </dl>
  </section>;
}

function MetricCells({ metric }: { metric: M10MetricComparison }) {
  return <>
    <td>{metric.reference_value}</td>
    <td>{metric.compared_value}</td>
    <td>{metric.delta}</td>
    <td>{metric.relation}</td>
  </>;
}

function ComparisonResult({ result }: { result: M10ComparisonResponse }) {
  return <section aria-label="Comparator success evidence">
    <h3>Comparator success evidence</h3>
    <dl>
      <dt>Comparison contract</dt><dd>{result.comparison_contract_version}</dd>
      <dt>Pair admission contract</dt><dd>{result.pair_admission_contract}</dd>
      <dt>Result schema</dt><dd>{result.comparison_result_schema}</dd>
      <dt>Fingerprint schema</dt><dd>{result.comparison_fingerprint_schema}</dd>
      <dt>Comparison fingerprint</dt><dd>{result.comparison_fingerprint}</dd>
      <dt>Delta direction</dt><dd>{result.delta_direction}</dd>
      <dt>Client ID</dt><dd>{result.client_id}</dd>
      <dt>Scenario contract</dt><dd>{result.scenario_family}/{result.scenario_contract_version}</dd>
      <dt>Horizon</dt><dd>{result.horizon.start_month}–{result.horizon.end_month}</dd>
      <dt>Factual baseline material fingerprint</dt><dd>{result.factual_baseline_material_fingerprint}</dd>
      <dt>Component-domain contract</dt><dd>{result.component_domain_contract_version}</dd>
      <dt>Factual engine version</dt><dd>{result.versions.factual_engine_version}</dd>
      <dt>Factual result schema</dt><dd>{result.versions.factual_result_schema_version}</dd>
      <dt>Subject engine version</dt><dd>{result.versions.subject_engine_version}</dd>
      <dt>Subject result schema</dt><dd>{result.versions.subject_result_schema_version}</dd>
      <dt>Upstream snapshot schema</dt><dd>{result.versions.upstream_snapshot_schema_version}</dd>
      <dt>Factual inventory schema</dt><dd>{result.versions.factual_inventory_schema_version}</dd>
    </dl>
    <section aria-label="Factual upstream versions">
      <h4>Factual upstream versions</h4>
      {result.versions.factual_upstream_versions.length ? <ol>{result.versions.factual_upstream_versions.map((version, index) => <li key={`${version.domain_identity}-${version.candidate_identity}-${index}`}>
        <dl>
          <dt>Domain identity</dt><dd>{version.domain_identity}</dd>
          <dt>Candidate identity</dt><dd>{version.candidate_identity}</dd>
          <dt>Source identity</dt><dd>{version.source_identity}</dd>
          <dt>Source version</dt><dd>{version.source_version}</dd>
          <dt>Source fingerprint</dt><dd>{version.source_fingerprint}</dd>
          <dt>Handoff contracts</dt><dd>{version.handoff_contract_versions.join(", ")}</dd>
        </dl>
      </li>)}</ol> : <p>No factual upstream version rows were returned.</p>}
    </section>
    <RunEvidence title="Reference run evidence" evidence={result.reference_run} />
    <RunEvidence title="Compared run evidence" evidence={result.compared_run} />
    <h4>Monthly comparisons</h4>
    <table>
      <thead><tr><th>Month</th><th>Metric</th><th>Reference</th><th>Compared</th><th>Compared minus reference</th><th>Relation</th></tr></thead>
      <tbody>{result.monthly_comparisons.flatMap(row => METRICS.map(([field, label]) => <tr key={`${row.month}-${field}`}>
        <td>{row.month}</td><th scope="row">{label}</th><MetricCells metric={row[field]} />
      </tr>))}</tbody>
    </table>
    <h4>Range totals</h4>
    <table>
      <thead><tr><th>Metric</th><th>Reference</th><th>Compared</th><th>Compared minus reference</th><th>Relation</th></tr></thead>
      <tbody>{METRICS.map(([field, label]) => <tr key={field}><th scope="row">{label}</th><MetricCells metric={result.range_totals[field]} /></tr>)}</tbody>
    </table>
  </section>;
}

export function M10ComparisonScreen() {
  const { clientId: rawClientId } = useParams();
  const location = useLocation();
  const clientId = rawClientId && /^[1-9]\d*$/.test(rawClientId) ? Number(rawClientId) : null;
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);

  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryStatus>("initial");
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [discoveryUnavailableReason, setDiscoveryUnavailableReason] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<Candidate | null>(null);
  const [adjustedCandidates, setAdjustedCandidates] = useState<Candidate[]>([]);
  const [selectedAdjustedRunId, setSelectedAdjustedRunId] = useState<string | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [result, setResult] = useState<M10ComparisonResponse | null>(null);
  const [blocker, setBlocker] = useState<ComparatorBlocker | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [visibleContext, setVisibleContext] = useState<ClientContextToken | null>(null);

  const mounted = useRef(false);
  const discoveryEpoch = useRef(0);
  const compareEpoch = useRef(0);

  const owns = useCallback((token: ClientContextToken, epoch: number, channel: "discovery" | "compare") => (
    mounted.current
    && isCurrentClientContext(token)
    && (channel === "discovery" ? discoveryEpoch.current === epoch : compareEpoch.current === epoch)
  ), [isCurrentClientContext]);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; discoveryEpoch.current += 1; compareEpoch.current += 1; };
  }, []);

  const discover = useCallback(async () => {
    if (clientId === null) return;
    const token = captureClientContext();
    const epoch = ++discoveryEpoch.current;
    setDiscoveryLoading(true);
    try {
      const subjects = await listM09Subjects(clientId);
      if (!owns(token, epoch, "discovery")) return;
      if (!subjects.every(hasAcceptedSubjectContract)) {
        setDiscoveryStatus("unavailable");
        setDiscoveryUnavailableReason("Comparison unavailable: unexpected scenario-subject contract evidence.");
        return;
      }
      const histories = await Promise.all(subjects.map(async subject => ({
        subject,
        runs: await listM09SubjectRuns(clientId, subject.scenario_subject_id),
      })));
      if (!owns(token, epoch, "discovery")) return;

      const baselineSubjects = histories.filter(item => item.subject.subject_type === "baseline");
      if (baselineSubjects.length === 0) {
        setDiscoveryStatus("no_baseline");
        return;
      }
      if (baselineSubjects.length > 1) {
        setDiscoveryStatus("ambiguous_baseline");
        return;
      }
      const baselineRuns = eligibleRuns(baselineSubjects[0].runs);
      if (baselineRuns.length === 0) {
        setDiscoveryStatus("no_baseline");
        return;
      }
      if (baselineRuns.length > 1) {
        setDiscoveryStatus("ambiguous_baseline");
        return;
      }

      const nextCandidates: Candidate[] = [];
      for (const item of histories.filter(value => value.subject.subject_type === "adjusted")) {
        const runs = eligibleRuns(item.runs);
        if (runs.length > 1) {
          setDiscoveryStatus("unavailable");
          setDiscoveryUnavailableReason("Comparison unavailable: an adjusted subject has ambiguous eligible run evidence.");
          return;
        }
        if (runs.length === 1) nextCandidates.push({ subject: item.subject, run: runs[0] });
      }
      nextCandidates.sort((left, right) => (
        compareText(left.subject.created_at, right.subject.created_at)
        || compareText(left.subject.scenario_subject_id, right.subject.scenario_subject_id)
      ));
      setBaseline({ subject: baselineSubjects[0].subject, run: baselineRuns[0] });
      setAdjustedCandidates(nextCandidates);
      setDiscoveryStatus(nextCandidates.length ? "ready" : "no_adjusted");
    } catch (error) {
      if (owns(token, epoch, "discovery")) {
        setDiscoveryStatus("transport_error");
        setDiscoveryError(transportMessage(error, "Eligible-run discovery failed"));
      }
    } finally {
      if (owns(token, epoch, "discovery")) setDiscoveryLoading(false);
    }
  }, [captureClientContext, clientId, owns]);

  useEffect(() => {
    setVisibleContext(captureClientContext());
    discoveryEpoch.current += 1;
    compareEpoch.current += 1;
    setDiscoveryStatus("initial");
    setDiscoveryLoading(false);
    setDiscoveryError(null);
    setDiscoveryUnavailableReason(null);
    setBaseline(null);
    setAdjustedCandidates([]);
    setSelectedAdjustedRunId(null);
    setCompareLoading(false);
    setResult(null);
    setBlocker(null);
    setCompareError(null);
    if (clientId !== null) void discover();
  }, [clientId, discover, location.key]);

  const selectAdjusted = (runId: string) => {
    compareEpoch.current += 1;
    setSelectedAdjustedRunId(runId);
    setCompareLoading(false);
    setResult(null);
    setBlocker(null);
    setCompareError(null);
  };

  const compare = async () => {
    if (clientId === null || baseline === null || selectedAdjustedRunId === null) return;
    const selected = adjustedCandidates.find(candidate => candidate.run.run_id === selectedAdjustedRunId);
    if (!selected) return;
    const token = captureClientContext();
    const epoch = ++compareEpoch.current;
    setCompareLoading(true);
    setResult(null);
    setBlocker(null);
    setCompareError(null);
    try {
      const next = await compareM10Runs(clientId, {
        reference_run_id: baseline.run.run_id,
        compared_run_id: selected.run.run_id,
      });
      if (owns(token, epoch, "compare")) setResult(next);
    } catch (error) {
      if (!owns(token, epoch, "compare")) return;
      const acceptedBlocker = comparatorBlocker(error);
      if (acceptedBlocker) setBlocker(acceptedBlocker);
      else setCompareError(transportMessage(error, "Comparator request failed"));
    } finally {
      if (owns(token, epoch, "compare")) setCompareLoading(false);
    }
  };

  if (clientId === null) return <main><h2>M10 Scenario comparison</h2><p role="alert">Invalid client ID.</p><p><Link to="/clients">Back to clients</Link></p></main>;

  const stateBelongsToCurrentContext = visibleContext !== null && isCurrentClientContext(visibleContext);
  const visibleBaseline = stateBelongsToCurrentContext ? baseline : null;
  const visibleCandidates = stateBelongsToCurrentContext ? adjustedCandidates : [];
  const visibleSelectedRunId = stateBelongsToCurrentContext ? selectedAdjustedRunId : null;
  const visibleSelectedCandidate = visibleSelectedRunId === null
    ? null
    : visibleCandidates.find(candidate => candidate.run.run_id === visibleSelectedRunId) ?? null;

  return <main>
    <h2>M10 Scenario comparison</h2>
    <p>Read-only presentation of server comparison evidence. Pair choice constructs one request only and is not a preference, approval, review, recommendation, or saved selection.</p>
    <p><Link to={`/clients/${clientId}`}>Back to client</Link></p>

    <section aria-label="Eligible run discovery">
      <h3>Eligible run discovery</h3>
      {!stateBelongsToCurrentContext || discoveryLoading ? <p role="status">Loading eligible M09 runs…</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "no_baseline" ? <p>Comparison unavailable: no eligible current baseline run was provided by the server.</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "ambiguous_baseline" ? <p>Comparison unavailable: baseline evidence is ambiguous.</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "unavailable" ? <p>{discoveryUnavailableReason}</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "transport_error" && discoveryError ? <p role="alert">{discoveryError}</p> : null}
      {visibleBaseline ? <div>
        <h4>Baseline reference</h4>
        <p>Subject ID: {visibleBaseline.subject.scenario_subject_id}</p>
        <p>Run ID: {visibleBaseline.run.run_id}</p>
        <p>Horizon: {visibleBaseline.run.start_month}–{visibleBaseline.run.end_month}</p>
      </div> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "no_adjusted" ? <p>No eligible current adjusted run was provided by the server.</p> : null}
      {visibleCandidates.length ? <fieldset>
        <legend>Eligible adjusted candidates</legend>
        {visibleCandidates.map(candidate => <label key={candidate.subject.scenario_subject_id}>
          <input
            type="radio"
            name="adjusted-run"
            value={candidate.run.run_id}
            checked={visibleSelectedRunId === candidate.run.run_id}
            onChange={() => selectAdjusted(candidate.run.run_id)}
          />
          {candidate.subject.display_label ?? "Adjusted scenario"} — subject {candidate.subject.scenario_subject_id}; run {candidate.run.run_id}; {candidate.run.start_month}–{candidate.run.end_month}
        </label>)}
        <p>Candidate order is technical and neutral; it does not express preference or ranking.</p>
      </fieldset> : null}
    </section>

    {visibleBaseline ? <ServerOwnedBaselineReference
      candidate={visibleBaseline}
      clientId={clientId}
    /> : null}

    {visibleSelectedCandidate ? <SelectedAdjustmentEvidence
      candidate={visibleSelectedCandidate}
      clientId={clientId}
    /> : null}

    <section aria-label="Comparator invocation">
      <h3>Comparator invocation</h3>
      <button type="button" disabled={!visibleBaseline || !visibleSelectedRunId || compareLoading} onClick={() => void compare()}>Compare selected pair</button>
      {stateBelongsToCurrentContext && compareLoading ? <p role="status">Loading comparator evidence…</p> : null}
      {stateBelongsToCurrentContext && blocker ? <section aria-label="Accepted comparator blocker">
        <h4>Comparison blocked</h4>
        <p>Code: <code>{blocker.code}</code></p>
        <p>{BLOCKER_TEXT[blocker.code]}</p>
        <p>Server message: {blocker.message}</p>
      </section> : null}
      {stateBelongsToCurrentContext && compareError ? <p role="alert">{compareError}</p> : null}
    </section>

    {stateBelongsToCurrentContext && result ? <ComparisonResult result={result} /> : null}
  </main>;
}
