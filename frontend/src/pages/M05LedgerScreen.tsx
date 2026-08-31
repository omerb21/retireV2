import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  ApiTransportError, getClient, type ClientDetailItem,
} from "../api/clientsApi";
import {
  adjustM05, getM05Eligibility, getM05History, getM05Provenance,
  getM05Subject, getM05Warnings, listM05Candidates, listM05Subjects,
  reasonActionM05, reconcileM05, revalidateM05, reviewWarningsM05,
  startM05, type M05Candidate, type M05Revision, type M05Subject,
} from "../api/m05LedgerApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { heBoolean, heLabel, technicalCode } from "../i18n/he";
import { formatIsoDate, formatIsoTimestamp } from "../utils/dateFormat";

const errorMessage = (error: unknown) => {
  if (error instanceof ApiTransportError &&
    typeof error.body === "object" && error.body !== null) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
      const code = (detail as { code?: unknown }).code;
      const detailMessage = (detail as { message?: unknown }).message;
      if (typeof detailMessage === "string" || typeof code === "string") {
        return `${typeof detailMessage === "string" ? detailMessage : "בקשת M05 נכשלה"}${typeof code === "string" ? ` (קוד טכני: ${code})` : ""}`;
      }
    }
  }
  return error instanceof Error ? error.message : "בקשת M05 נכשלה";
};
const CANDIDATE_EXPLANATIONS: Record<string, string> = {
  archived_case: "תיק הלקוח בארכיון ולקריאה בלבד.",
  ledger_chain_inconsistent: "היסטוריית הכרטסת השמורה נכשלה בבדיקות התקינות.",
  no_authoritative_candidate: "רשומה עדכנית אחרת היא הסמכותית עבור הגוף המנהל והחשבון.",
  authoritative_candidate_tie: "ליותר מרשומה אחת אותה דרגת סמכות ולכן הבחירה חסומה.",
  upstream_source_ineligible: "רשומת M02 אינה מקור ידני עדכני וכשיר.",
  m03_ineligible: "בדיקת המקור M03 חסרה או אינה עדכנית.",
  m04_ineligible: "הסיווג M04 חסר, לא הוכרע או אינו מאושר.",
  upstream_revalidation_required: "נדרש אימות מחדש של הסיווג מול נתוני המקור העדכניים.",
  required_value_missing: "חסר ערך חובה של גוף מנהל, חשבון, תאריך דוח, יתרה או רכיב.",
  currency_or_unit_invalid: "אישור מטבע הש״ח הנדרש חסר או אינו תקין.",
  component_mapping_invalid: "ראיות רכיבי M02 אינן תואמות למיפוי הסיווג המאושר.",
  component_set_incomplete: "נדרשת קבוצה מלאה ולא ריקה של רכיבים הניתנים להתאמה.",
  statement_date_invalid: "תאריך הדוח חסר, אינו תקין או נמצא בעתיד.",
};
const candidateExplanation = (candidate: M05Candidate) => candidate.exclusion_reason
  ? CANDIDATE_EXPLANATIONS[candidate.exclusion_reason] ??
    "הרשומה חסומה על ידי שער כשירות טכני."
  : candidate.authoritative_current
    ? "זוהי הרשומה הטכנית העדכנית."
    : "רשומה זו אינה הרשומה העדכנית.";
const text = (value: unknown) => value === null || value === undefined || value === ""
  ? "לא קיים" : typeof value === "string" ? value : JSON.stringify(value);

function ProductContextView({ context, label }: { context: Record<string, unknown>; label: string }) {
  const entries = Object.entries(context).filter(([, value]) =>
    value !== null && value !== undefined && value !== ""
  );
  return <div aria-label={label}>
    <strong>הקשר מוצר שנשמר (ערכי מקור, ללא הסקה):</strong>
    {entries.length ? <dl>{entries.map(([key, value]) => <div key={key}>
      <dt>{key}</dt><dd>{text(value)}</dd>
    </div>)}</dl> : <p>הקשר המוצר אינו זמין.</p>}
  </div>;
}

function RevisionView({ revision, current }: { revision: M05Revision; current: boolean }) {
  return <li>
    <h4>גרסה #{revision.revision_sequence} — {current ? "נוכחית" : "היסטורית"}</h4>
    <p>מצב: {heLabel(revision.state)}; פעולה: {heLabel(revision.action_type)}; מזהה גרסה: {revision.revision_id}; גרסה קודמת: {revision.predecessor_revision_id ?? "ראשונה"}.</p>
    <p>גורם מערכת: {revision.actor}; מועד: {formatIsoTimestamp(revision.created_at)}. זהו תיעוד תפעולי ולא אישור מקצועי.</p>
    <p>רשומה: {revision.candidate_id}; M02: {revision.intake_id}; M03: {revision.m03_revision_id}; M04: {revision.m04_revision_id}.</p>
    <ProductContextView context={revision.product_context} label={`הקשר המוצר של גרסה ${revision.revision_sequence}`} />
    <p>תאריך דוח: {formatIsoDate(revision.statement_date)}; תאריך הערכה: {formatIsoDate(revision.evaluation_date)}; לא עדכני: {heBoolean(revision.is_stale)}.</p>
    <p>מטבע: {revision.currency}; אישור מפורש: {String(revision.currency_confirmed)}.</p>
    <p>סך מקור: {text(revision.source_total_value)} ({heLabel(revision.source_total_state)}); סך אפקטיבי: {text(revision.effective_total_value)} ({heLabel(revision.effective_total_state)}).</p>
    <p>פער עם סימן: {text(revision.signed_discrepancy)}; פער מוחלט: {text(revision.absolute_discrepancy)}; עמידה בסבילות: {String(revision.tolerance_satisfied)}.</p>
    <p>אלגוריתם: {revision.algorithm_version}; תקציר מקור: {revision.source_snapshot_digest}; תקציר מיפוי: {revision.mapping_digest}.</p>
    <h5>ערכי מקור וערכים אפקטיביים</h5>
    <table><thead><tr><th>זהות</th><th>סוג</th><th>מקור</th><th>אפקטיבי</th><th>מיפוי</th></tr></thead>
      <tbody>{revision.values.map((value) => <tr key={value.value_id}>
        <td>{value.evidence_identity}<br />אינדקס {text(value.component_index)}; תיאור {text(value.original_label)}; קוד {text(value.original_code)}</td>
        <td>{value.component_kind}</td>
        <td>{text(value.source_value)} ({heLabel(value.source_state)})</td>
        <td>{text(value.effective_value)} ({heLabel(value.effective_state)})</td>
        <td>{value.included_in_reconciliation ? "נכלל פעם אחת בדיוק" : `הוחרג: ${text(value.exclusion_reason)}`}</td>
      </tr>)}</tbody>
    </table>
    <p>ראיות שנכללו: {JSON.stringify(revision.included_evidence)}</p>
    <p>ראיות שהוחרגו: {JSON.stringify(revision.excluded_evidence)}</p>
    <p>אזהרות: {JSON.stringify(revision.warnings)}; החלטות: {JSON.stringify(revision.warning_dispositions)}</p>
    <p>מקור: {JSON.stringify(revision.provenance)}</p>
    {revision.adjustment ? <p>תיקון: {revision.adjustment.evidence_identity}, {revision.adjustment.previous_effective_value} → {revision.adjustment.new_effective_value}; {revision.adjustment.reason_code}; {revision.adjustment.explanation}.</p> : null}
  </li>;
}

export function M05LedgerScreen() {
  const { clientId: raw } = useParams();
  const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [candidates, setCandidates] = useState<M05Candidate[]>([]);
  const [subjects, setSubjects] = useState<M05Subject[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [subject, setSubject] = useState<M05Subject | null>(null);
  const [history, setHistory] = useState<M05Revision[]>([]);
  const [provenance, setProvenance] = useState<Record<string, unknown>>({});
  const [warnings, setWarnings] = useState<Record<string, unknown>[]>([]);
  const [reasonCode, setReasonCode] = useState("planner_decision");
  const [explanation, setExplanation] = useState("");
  const [adjustIdentity, setAdjustIdentity] = useState("");
  const [adjustValue, setAdjustValue] = useState("");
  const [confirmCurrency, setConfirmCurrency] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const mounted = useRef(false);
  const overviewEpoch = useRef(0);
  const detailEpoch = useRef(0);
  const mutationEpoch = useRef(0);
  const selectedCandidate = useRef<string | null>(null);
  const selectedSubject = useRef<string | null>(null);
  const selectedRevision = useRef<string | null>(null);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      overviewEpoch.current += 1; detailEpoch.current += 1; mutationEpoch.current += 1;
      selectedCandidate.current = null; selectedSubject.current = null; selectedRevision.current = null;
    };
  }, []);

  useEffect(() => {
    overviewEpoch.current += 1; detailEpoch.current += 1; mutationEpoch.current += 1;
    selectedCandidate.current = null; selectedSubject.current = null; selectedRevision.current = null;
    setClient(null); setCandidates([]); setSubjects([]); setSelectedCandidateId("");
    setSubject(null); setHistory([]); setProvenance({}); setWarnings([]);
    setError(null); setLoading(false); setSubmitting(false);
  }, [clientId, location.key]);

  const loadOverview = useCallback(async () => {
    if (clientId === null) return;
    const token = captureClientContext(); const request = ++overviewEpoch.current;
    const owned = () => mounted.current && request === overviewEpoch.current && isCurrentClientContext(token);
    setLoading(true); setError(null);
    try {
      const [nextClient, nextCandidates, nextSubjects] = await Promise.all([
        getClient(clientId), listM05Candidates(clientId), listM05Subjects(clientId),
      ]);
      if (!owned()) return;
      setClient(nextClient); setCandidates(nextCandidates); setSubjects(nextSubjects);
    } catch (cause) {
      if (owned()) setError(errorMessage(cause));
    } finally {
      if (owned()) setLoading(false);
    }
  }, [captureClientContext, clientId, isCurrentClientContext, location.key]);
  useEffect(() => { void loadOverview(); }, [loadOverview]);

  const loadSubject = useCallback(async (subjectId: string) => {
    if (clientId === null) return;
    const token = captureClientContext(); const request = ++detailEpoch.current;
    mutationEpoch.current += 1; selectedSubject.current = subjectId; selectedRevision.current = null;
    const owned = () => mounted.current && request === detailEpoch.current &&
      selectedSubject.current === subjectId && isCurrentClientContext(token);
    setLoading(true); setSubmitting(false); setError(null);
    setSubject(null); setHistory([]); setProvenance({}); setWarnings([]);
    try {
      const detailPromise = getM05Subject(clientId, subjectId).then((next) => {
        if (owned()) { selectedRevision.current = next.current_revision?.revision_id ?? null; setSubject(next); }
      });
      const historyPromise = getM05History(clientId, subjectId).then((next) => { if (owned()) setHistory(next); });
      const provenancePromise = getM05Provenance(clientId, subjectId).then((next) => { if (owned()) setProvenance(next); });
      const warningPromise = getM05Warnings(clientId, subjectId).then((next) => { if (owned()) setWarnings(next); });
      const eligibilityPromise = getM05Eligibility(clientId, subjectId).then((next) => {
        if (owned()) setSubject((current) => current ? { ...current, eligibility: next } : current);
      });
      await Promise.all([detailPromise, historyPromise, provenancePromise, warningPromise, eligibilityPromise]);
    } catch (cause) {
      if (owned()) setError(errorMessage(cause));
    } finally {
      if (owned()) setLoading(false);
    }
  }, [captureClientContext, clientId, isCurrentClientContext]);

  const chooseCandidate = (candidateId: string) => {
    mutationEpoch.current += 1; selectedCandidate.current = candidateId;
    setSelectedCandidateId(candidateId); setError(null);
  };

  const mutate = async (operation: () => Promise<unknown>) => {
    if (clientId === null) return;
    const token = captureClientContext(); const candidateId = selectedCandidate.current;
    const subjectId = selectedSubject.current; const revisionId = selectedRevision.current;
    const request = ++mutationEpoch.current;
    const owned = () => mounted.current && request === mutationEpoch.current &&
      selectedCandidate.current === candidateId && selectedSubject.current === subjectId &&
      selectedRevision.current === revisionId && isCurrentClientContext(token);
    setSubmitting(true); setError(null);
    try {
      const result = await operation();
      if (!owned()) return; // stale mutation launches zero refresh calls
      await loadOverview();
      if (!owned()) return;
      const next = result as M05Revision;
      selectedSubject.current = next.subject_id; selectedRevision.current = next.revision_id;
      await loadSubject(next.subject_id);
    } catch (cause) {
      if (owned()) setError(errorMessage(cause));
    } finally {
      if (owned()) setSubmitting(false);
    }
  };

  if (clientId === null) return <p role="alert">מזהה הלקוח אינו תקין.</p>;
  const current = subject?.current_revision ?? null;
  const currentEligibility = subject?.eligibility ?? null;
  const selectedCandidateRow = candidates.find((row) => row.candidate_id === selectedCandidateId) ?? null;
  const mandatory = current?.warnings.filter((item) => item.classification === "mandatory").map((item) => item.warning_id) ?? [];
  const reasonPayload = current ? {
    expected_current_revision_id: current.revision_id,
    reason_code: reasonCode,
    explanation,
  } : null;

  return <main>
    <h2>M05 — כרטסת יתרות פנסיה</h2>
    <p>לקוח: {client?.full_name ?? clientId}. מוצגות רשומות ידניות בלבד.</p>
    <p><Link to={`/clients/${clientId}`}>חזרה ללקוח</Link></p>
    {error ? <p role="alert">{error}</p> : null}
    {loading ? <p>טוען נתוני M05…</p> : null}

    <section><h3>רשומות ידניות מועמדות</h3>
      {candidates.length ? <ul>{candidates.map((candidate) => <li key={candidate.candidate_id}>
        <button type="button" aria-label={`${candidate.provider_name ?? "גוף מנהל לא זמין"} / ${candidate.account_reference ?? "חשבון לא זמין"} / ${candidate.statement_date ?? "תאריך דוח לא זמין"}`} onClick={() => chooseCandidate(candidate.candidate_id)}>
          {candidate.provider_name ?? "גוף מנהל לא זמין"} / {candidate.account_reference ?? "חשבון לא זמין"} / {formatIsoDate(candidate.statement_date) || "תאריך דוח לא זמין"}
        </button>
        <span> — {candidateExplanation(candidate)}</span>
        <ProductContextView context={candidate.product_context} label={`הקשר המוצר של רשומה ${candidate.candidate_id}`} />
      </li>)}</ul> : <p>אין רשומות ידניות מועמדות ל־M05.</p>}
      {selectedCandidateRow ? <section aria-label="הסבר כשירות הרשומה שנבחרה">
        <h4>כשירות הרשומה להמשך</h4>
        <p>{candidateExplanation(selectedCandidateRow)}</p>
        <p>גוף מנהל: {selectedCandidateRow.provider_name ?? "לא נמסר"}; חשבון: {selectedCandidateRow.account_reference ?? "לא נמסר"}; תאריך דוח: {formatIsoDate(selectedCandidateRow.statement_date) || "לא נמסר"}.</p>
        <p>כשירות טכנית: {heBoolean(selectedCandidateRow.eligible)}; רשומה נוכחית: {heBoolean(selectedCandidateRow.authoritative_current)}.</p>
        {selectedCandidateRow.exclusion_reason
          ? <p><small>{technicalCode(selectedCandidateRow.exclusion_reason)}</small></p>
          : null}
        {selectedCandidateRow.informational_warnings.length
          ? <p>אזהרות מידע טכניות: {selectedCandidateRow.informational_warnings.join(", ")}</p>
          : null}
      </section> : null}
      <label><input aria-label="אישור מטבע ש״ח" type="checkbox" checked={confirmCurrency} onChange={(event) => setConfirmCurrency(event.target.checked)} /> אישור שמטבע הרשומה הוא ש״ח</label>
      <button type="button" aria-label="התחלת כרטסת" disabled={!selectedCandidateRow?.eligible || !selectedCandidateRow.authoritative_current || submitting} onClick={() => void mutate(() => startM05(clientId, selectedCandidateId, confirmCurrency))}>התחלת כרטסת</button>
    </section>

    <section><h3>כרטסות קיימות</h3>
      {subjects.length ? <ul>{subjects.map((row) => <li key={row.subject_id}>
        <button type="button" onClick={() => void loadSubject(row.subject_id)}>{row.provider_name} / {row.account_reference}</button>
        <span> — {heLabel(row.current_revision?.state, "ללא גרסה")}; כשירות טכנית ל־M06: {heBoolean(row.eligibility.eligible_for_m06)}</span>
      </li>)}</ul> : <p>אין כרטסות M05.</p>}
    </section>

    {current ? <section><h3>כרטסת נוכחית</h3>
      <RevisionView revision={current} current />
      <h4>כשירות טכנית ל־M06</h4>
      <p>{currentEligibility?.meaning}. כשיר: {String(currentEligibility?.eligible_for_m06)}.</p>
      <p>החרגות: {currentEligibility?.exclusion_reasons.join(", ") || "אין"}; אזהרות מידע: {currentEligibility?.informational_warnings.join(", ") || "אין"}.</p>
      <p>תוצאה זו אינה מאשרת המרה, מקדמים, מס, קיבוע זכויות, נזילות, משיכה, תחילת קצבה או דוחות.</p>
      <h4>הפעולה הבאה</h4>
      <label>קוד נימוק <input value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} /></label>
      <label>הסבר <textarea value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
      <button type="button" aria-label="התאמת יתרות" disabled={submitting || current.state !== "draft"} onClick={() => void mutate(() => reconcileM05(clientId, current.subject_id, current.revision_id, confirmCurrency))}>התאמת יתרות</button>
      <button type="button" aria-label="בדיקת קבוצת אזהרות החובה" disabled={submitting || !reasonPayload || current.state !== "draft" || !mandatory.length} onClick={() => reasonPayload && void mutate(() => reviewWarningsM05(clientId, current.subject_id, { ...reasonPayload, mandatory_warning_ids: mandatory, confirmed: true, ...(confirmCurrency ? { confirm_currency_ils: true as const } : {}) }))}>בדיקת קבוצת אזהרות החובה</button>
      <button type="button" aria-label="סימון כחסום" disabled={submitting || !reasonPayload || !["draft", "reconciled", "warning_reviewed"].includes(current.state)} onClick={() => reasonPayload && void mutate(() => reasonActionM05(clientId, current.subject_id, "mark-blocked", reasonPayload))}>סימון כחסום</button>
      <button type="button" aria-label="החלפת הגרסה הנוכחית" disabled={submitting || !reasonPayload || current.state === "superseded"} onClick={() => reasonPayload && void mutate(() => reasonActionM05(clientId, current.subject_id, "supersede", reasonPayload))}>החלפת הגרסה הנוכחית</button>
      <h4>תיקון ערך יחיד</h4>
      <select value={adjustIdentity} onChange={(event) => setAdjustIdentity(event.target.value)}><option value="">בחירת ערך</option>{current.values.map((value) => <option key={value.value_id} value={value.evidence_identity}>{value.evidence_identity}</option>)}</select>
      <input aria-label="ערך אפקטיבי חדש" value={adjustValue} onChange={(event) => setAdjustValue(event.target.value)} placeholder="0.00" />
      <button type="button" aria-label="תיקון ערך יחיד" disabled={submitting || !reasonPayload || current.state === "superseded" || !adjustIdentity || !adjustValue} onClick={() => reasonPayload && void mutate(() => adjustM05(clientId, current.subject_id, { ...reasonPayload, evidence_identity: adjustIdentity, new_effective_value: adjustValue, confirmed: true }))}>תיקון ערך יחיד</button>
      <h4>אימות מחדש</h4>
      <button type="button" aria-label="אימות מחדש מול הרשומה העדכנית שנבחרה" disabled={submitting || !reasonPayload || current.state === "superseded" || !selectedCandidateRow?.eligible || !selectedCandidateRow.authoritative_current} onClick={() => reasonPayload && void mutate(() => revalidateM05(clientId, current.subject_id, { ...reasonPayload, candidate_id: selectedCandidateId }))}>אימות מחדש מול הרשומה העדכנית שנבחרה</button>
      <h4>מקור ואזהרות נוכחיים</h4><p>{JSON.stringify(provenance)}</p><p>{JSON.stringify(warnings)}</p>
    </section> : null}

    {history.length ? <section><h3>היסטוריה בלתי ניתנת לשינוי</h3><ol>{history.map((revision) => <RevisionView key={revision.revision_id} revision={revision} current={revision.revision_id === current?.revision_id} />)}</ol></section> : null}
  </main>;
}
