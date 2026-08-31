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
import { heLabel } from "../i18n/he";

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
  return <section aria-label="תרחיש בסיס שנקבע בשרת">
    <h3>תרחיש בסיס שנקבע בשרת</h3>
    {valid ? <>
      <p>אין התאמות תרחיש שהוגדרו על ידי המתכנן.</p>
      <p>מקור: <code>{BASELINE_PROVENANCE}</code></p>
    </> : <p>אסמכתת תרחיש הבסיס אינה זמינה.</p>}
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
    ? "הכנסה חודשית נוספת מוצהרת"
    : "הוצאה חודשית נוספת מוצהרת";
}

function SelectedAdjustmentEvidence({ candidate, clientId }: {
  candidate: Candidate;
  clientId: number;
}) {
  const adjustments = selectedAdjustmentEvidence(candidate, clientId);
  return <section aria-label="ראיות ההתאמה של התרחיש שנבחר">
    <h3>ראיות ההתאמה של התרחיש שנבחר</h3>
    <p>מזהה תרחיש: {candidate.subject.scenario_subject_id}</p>
    {adjustments === null ? <p>ראיות התאמת התרחיש אינן זמינות.</p> : <ol>
      {adjustments.map(adjustment => <li key={adjustment.adjustment_id}>
        <h4>{adjustmentTypeLabel(adjustment.adjustment_type)}</h4>
        <dl>
          <dt>מזהה מופע</dt><dd>{adjustment.adjustment_id}</dd>
          <dt>סדר</dt><dd>{adjustment.ordinal}</dd>
          <dt>סוג התאמה</dt><dd><code>{adjustment.adjustment_type}</code></dd>
          <dt>סכום</dt><dd>{adjustment.amount}</dd>
          <dt>חודש התחלה</dt><dd>{adjustment.start_month}</dd>
          <dt>חודש סיום</dt><dd>{adjustment.end_month}</dd>
          <dt>מקור</dt><dd><code>{adjustment.provenance}</code></dd>
        </dl>
      </li>)}
    </ol>}
  </section>;
}

const BLOCKER_TEXT: Record<M10ComparatorBlockerCode, string> = {
  comparison_run_unavailable: "הרצת ההשוואה המבוקשת אינה זמינה.",
  comparison_same_subject: "שתי ההרצות שייכות לאותו נושא תרחיש.",
  comparison_pair_role_invalid: "להרצות שנשלחו אין את תפקידי הבסיס והתרחיש המותאם הנדרשים.",
  comparison_scenario_contract_mismatch: "ראיות חוזה התרחיש אינן תואמות.",
  comparison_horizon_mismatch: "טווחי ההשוואה אינם תואמים.",
  comparison_factual_baseline_material_mismatch: "נתוני הבסיס העובדתיים אינם תואמים.",
  comparison_component_domain_contract_mismatch: "ראיות חוזה תחום הרכיבים אינן תואמות.",
  comparison_engine_version_mismatch: "ראיות גרסת מנוע החישוב אינן תואמות.",
  comparison_result_schema_version_mismatch: "ראיות סכמת התוצאה אינן תואמות.",
  comparison_factual_upstream_version_mismatch: "ראיות גרסת נתוני המקור העובדתיים אינן תואמות.",
  comparison_run_not_current: "אחת ההרצות שנשלחו אינה ההרצה הנוכחית.",
  comparison_run_not_eligible: "אחת ההרצות שנשלחו אינה כשירה להשוואת M10.",
  comparison_fingerprint_invalid: "ראיות טביעת האצבע של ההשוואה אינן תקינות.",
  comparison_semantically_identical_manifest: "מניפסטי ההתאמה זהים מבחינה סמנטית.",
  comparison_month_alignment_mismatch: "הראיות החודשיות שנשמרו אינן מיושרות.",
  comparison_numeric_domain_invalid: "הראיות המספריות שנשמרו חורגות מהתחום המאושר.",
};

const METRICS = [
  ["gross_inflow_total", "סך תקבולים ברוטו"],
  ["gross_outflow_total", "סך תשלומים ברוטו"],
  ["period_net", "נטו לתקופה"],
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
      <dt>מזהה הרצה</dt><dd>{evidence.run_id}</dd>
      <dt>מזהה נושא תרחיש</dt><dd>{evidence.scenario_subject_id}</dd>
      <dt>סוג נושא</dt><dd>{heLabel(evidence.subject_type)}</dd>
      <dt>טביעת אצבע סמנטית של החישוב</dt><dd>{evidence.calculation_semantic_fingerprint}</dd>
      <dt>טביעת אצבע לשלמות</dt><dd>{evidence.integrity_fingerprint}</dd>
      <dt>טביעת אצבע של מניפסט ההתאמות</dt><dd>{evidence.adjustment_manifest_fingerprint}</dd>
      <dt>טביעת אצבע של המלאי העובדתי</dt><dd>{evidence.factual_inventory_fingerprint}</dd>
      <dt>טביעת אצבע של תמונת מצב המקור</dt><dd>{evidence.upstream_snapshot_fingerprint}</dd>
      <dt>טביעת אצבע סמנטית של התוצאה</dt><dd>{evidence.semantic_result_fingerprint}</dd>
      <dt>טביעת אצבע לשלמות התוצאה</dt><dd>{evidence.result_integrity_fingerprint}</dd>
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
  return <section aria-label="ראיות לתוצאת ההשוואה">
    <h3>תוצאת השוואה</h3>
    <dl>
      <dt>חוזה ההשוואה</dt><dd>{result.comparison_contract_version}</dd>
      <dt>חוזה קבלת הזוג</dt><dd>{result.pair_admission_contract}</dd>
      <dt>סכמת תוצאה</dt><dd>{result.comparison_result_schema}</dd>
      <dt>סכמת טביעת אצבע</dt><dd>{result.comparison_fingerprint_schema}</dd>
      <dt>טביעת אצבע של ההשוואה</dt><dd>{result.comparison_fingerprint}</dd>
      <dt>כיוון ההפרש</dt><dd>{result.delta_direction}</dd>
      <dt>מזהה לקוח</dt><dd>{result.client_id}</dd>
      <dt>חוזה תרחיש</dt><dd>{result.scenario_family}/{result.scenario_contract_version}</dd>
      <dt>טווח</dt><dd>{result.horizon.start_month}–{result.horizon.end_month}</dd>
      <dt>טביעת אצבע של נתוני הבסיס העובדתיים</dt><dd>{result.factual_baseline_material_fingerprint}</dd>
      <dt>חוזה תחום הרכיבים</dt><dd>{result.component_domain_contract_version}</dd>
      <dt>גרסת מנוע עובדתי</dt><dd>{result.versions.factual_engine_version}</dd>
      <dt>סכמת תוצאה עובדתית</dt><dd>{result.versions.factual_result_schema_version}</dd>
      <dt>גרסת מנוע נושא</dt><dd>{result.versions.subject_engine_version}</dd>
      <dt>סכמת תוצאת נושא</dt><dd>{result.versions.subject_result_schema_version}</dd>
      <dt>סכמת תמונת מצב מקור</dt><dd>{result.versions.upstream_snapshot_schema_version}</dd>
      <dt>סכמת מלאי עובדתי</dt><dd>{result.versions.factual_inventory_schema_version}</dd>
    </dl>
    <section aria-label="גרסאות נתוני המקור העובדתיים">
      <h4>גרסאות נתוני המקור</h4>
      {result.versions.factual_upstream_versions.length ? <ol>{result.versions.factual_upstream_versions.map((version, index) => <li key={`${version.domain_identity}-${version.candidate_identity}-${index}`}>
        <dl>
          <dt>זהות תחום</dt><dd>{version.domain_identity}</dd>
          <dt>זהות רשומה</dt><dd>{version.candidate_identity}</dd>
          <dt>זהות מקור</dt><dd>{version.source_identity}</dd>
          <dt>גרסת מקור</dt><dd>{version.source_version}</dd>
          <dt>טביעת אצבע של המקור</dt><dd>{version.source_fingerprint}</dd>
          <dt>חוזי מסירה</dt><dd>{version.handoff_contract_versions.join(", ")}</dd>
        </dl>
      </li>)}</ol> : <p>לא הוחזרו שורות גרסה של נתוני מקור עובדתיים.</p>}
    </section>
    <RunEvidence title="ראיות הרצת הייחוס" evidence={result.reference_run} />
    <RunEvidence title="ראיות ההרצה המושווית" evidence={result.compared_run} />
    <h4>השוואה חודשית</h4>
    <table>
      <thead><tr><th>חודש</th><th>מדד</th><th>ייחוס</th><th>מושווה</th><th>מושווה פחות ייחוס</th><th>יחס</th></tr></thead>
      <tbody>{result.monthly_comparisons.flatMap(row => METRICS.map(([field, label]) => <tr key={`${row.month}-${field}`}>
        <td>{row.month}</td><th scope="row">{label}</th><MetricCells metric={row[field]} />
      </tr>))}</tbody>
    </table>
    <h4>סיכום לכל התקופה</h4>
    <table>
      <thead><tr><th>מדד</th><th>ייחוס</th><th>מושווה</th><th>מושווה פחות ייחוס</th><th>יחס</th></tr></thead>
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
        setDiscoveryUnavailableReason("ההשוואה אינה זמינה: ראיות חוזה התרחיש אינן תקינות.");
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
          setDiscoveryUnavailableReason("ההשוואה אינה זמינה: ראיות ההרצה הכשירה של תרחיש מותאם אינן חד־משמעיות.");
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
        setDiscoveryError(transportMessage(error, "איתור ההרצות הכשירות נכשל"));
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
      else setCompareError(transportMessage(error, "בקשת ההשוואה נכשלה"));
    } finally {
      if (owns(token, epoch, "compare")) setCompareLoading(false);
    }
  };

  if (clientId === null) return <main><h2>M10 — השוואת תרחישים</h2><p role="alert">מזהה הלקוח אינו תקין.</p><p><Link to="/clients">חזרה ללקוחות</Link></p></main>;

  const stateBelongsToCurrentContext = visibleContext !== null && isCurrentClientContext(visibleContext);
  const visibleBaseline = stateBelongsToCurrentContext ? baseline : null;
  const visibleCandidates = stateBelongsToCurrentContext ? adjustedCandidates : [];
  const visibleSelectedRunId = stateBelongsToCurrentContext ? selectedAdjustedRunId : null;
  const visibleSelectedCandidate = visibleSelectedRunId === null
    ? null
    : visibleCandidates.find(candidate => candidate.run.run_id === visibleSelectedRunId) ?? null;

  return <main>
    <h2>M10 — השוואת תרחישים</h2>
    <p>תצוגה לקריאה בלבד של השוואה שנוצרה בשרת. בחירת זוג תרחישים אינה המלצה, אישור או בחירה מקצועית שמורה.</p>
    <p><Link to={`/clients/${clientId}`}>חזרה ללקוח</Link></p>

    <section aria-label="איתור הרצות כשירות">
      <h3>איתור הרצות כשירות</h3>
      {!stateBelongsToCurrentContext || discoveryLoading ? <p role="status">טוען הרצות M09 כשירות…</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "no_baseline" ? <p>ההשוואה אינה זמינה: השרת לא סיפק הרצת בסיס עדכנית וכשירה.</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "ambiguous_baseline" ? <p>ההשוואה אינה זמינה: תרחיש הבסיס אינו חד־משמעי.</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "unavailable" ? <p>{discoveryUnavailableReason}</p> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "transport_error" && discoveryError ? <p role="alert">{discoveryError}</p> : null}
      {visibleBaseline ? <div>
        <h4>תרחיש בסיס</h4>
        <p>מזהה תרחיש: {visibleBaseline.subject.scenario_subject_id}</p>
        <p>מזהה הרצה: {visibleBaseline.run.run_id}</p>
        <p>טווח: {visibleBaseline.run.start_month}–{visibleBaseline.run.end_month}</p>
      </div> : null}
      {stateBelongsToCurrentContext && discoveryStatus === "no_adjusted" ? <p>השרת לא סיפק הרצה מותאמת עדכנית וכשירה.</p> : null}
      {visibleCandidates.length ? <fieldset>
        <legend>תרחישים מותאמים כשירים</legend>
        {visibleCandidates.map(candidate => <label key={candidate.subject.scenario_subject_id}>
          <input
            type="radio"
            name="adjusted-run"
            value={candidate.run.run_id}
            checked={visibleSelectedRunId === candidate.run.run_id}
            onChange={() => selectAdjusted(candidate.run.run_id)}
          />
          {candidate.subject.display_label ?? "תרחיש מותאם"} — נושא {candidate.subject.scenario_subject_id}; הרצה {candidate.run.run_id}; {candidate.run.start_month}–{candidate.run.end_month}
        </label>)}
        <p>סדר התרחישים טכני וניטרלי ואינו מבטא העדפה או דירוג.</p>
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

    <section aria-label="ביצוע השוואה">
      <h3>ביצוע השוואה</h3>
      <button type="button" aria-label="השוואת הזוג שנבחר" disabled={!visibleBaseline || !visibleSelectedRunId || compareLoading} onClick={() => void compare()}>השוואת הזוג שנבחר</button>
      {stateBelongsToCurrentContext && compareLoading ? <p role="status">טוען את נתוני ההשוואה…</p> : null}
      {stateBelongsToCurrentContext && blocker ? <section aria-label="חסם השוואה מוכר">
        <h4>לא ניתן לבצע את ההשוואה</h4>
        <p>קוד טכני: <code>{blocker.code}</code></p>
        <p>{BLOCKER_TEXT[blocker.code]}</p>
        <p>הודעת שרת: {blocker.message}</p>
      </section> : null}
      {stateBelongsToCurrentContext && compareError ? <p role="alert">{compareError}</p> : null}
    </section>

    {stateBelongsToCurrentContext && result ? <ComparisonResult result={result} /> : null}
  </main>;
}
