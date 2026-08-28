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

const errorMessage = (error: unknown) => {
  if (error instanceof ApiTransportError &&
    typeof error.body === "object" && error.body !== null) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
      const code = (detail as { code?: unknown }).code;
      const detailMessage = (detail as { message?: unknown }).message;
      if (typeof detailMessage === "string" || typeof code === "string") {
        return `${typeof detailMessage === "string" ? detailMessage : "M05 request failed"}${typeof code === "string" ? ` (Technical code: ${code})` : ""}`;
      }
    }
  }
  return error instanceof Error ? error.message : "M05 request failed";
};
const CANDIDATE_EXPLANATIONS: Record<string, string> = {
  archived_case: "The client case is archived and read-only.",
  ledger_chain_inconsistent: "The retained ledger history failed its integrity checks.",
  no_authoritative_candidate: "Another current record is authoritative for this provider and account.",
  authoritative_candidate_tie: "More than one record has the same authority rank; selection is blocked.",
  upstream_source_ineligible: "The M02 record is not a current eligible manual source.",
  m03_ineligible: "The source review is missing, stale, or not currently accepted.",
  m04_ineligible: "The classification is missing, stale, unresolved, or not currently accepted.",
  upstream_revalidation_required: "Upstream evidence changed and requires explicit revalidation.",
  required_value_missing: "A required provider, account, statement date, balance, or component value is missing.",
  currency_or_unit_invalid: "The required ILS currency confirmation is missing or invalid.",
  component_mapping_invalid: "The M02 component evidence does not match the accepted classification mapping.",
  component_set_incomplete: "A complete non-empty set of reconcilable components is required.",
  statement_date_invalid: "The statement date is missing, invalid, or in the future.",
};
const candidateExplanation = (candidate: M05Candidate) => candidate.exclusion_reason
  ? CANDIDATE_EXPLANATIONS[candidate.exclusion_reason] ??
    "This candidate is excluded by a technical eligibility gate."
  : candidate.authoritative_current
    ? "This is the current technically authoritative candidate."
    : "This candidate is not the current authoritative record.";
const text = (value: unknown) => value === null || value === undefined || value === ""
  ? "not present" : typeof value === "string" ? value : JSON.stringify(value);

function ProductContextView({ context, label }: { context: Record<string, unknown>; label: string }) {
  const entries = Object.entries(context).filter(([, value]) =>
    value !== null && value !== undefined && value !== ""
  );
  return <div aria-label={label}>
    <strong>Persisted product context (source values; no inference):</strong>
    {entries.length ? <dl>{entries.map(([key, value]) => <div key={key}>
      <dt>{key}</dt><dd>{text(value)}</dd>
    </div>)}</dl> : <p>Product context unavailable.</p>}
  </div>;
}

function RevisionView({ revision, current }: { revision: M05Revision; current: boolean }) {
  return <li>
    <h4>Revision #{revision.revision_sequence} — {current ? "current" : "historical"}</h4>
    <p>State: {revision.state}; action: {revision.action_type}; revision: {revision.revision_id}; predecessor: {revision.predecessor_revision_id ?? "root"}.</p>
    <p>Server actor: {revision.actor}; timestamp: {revision.created_at}. This is operational provenance, not authentication or professional approval.</p>
    <p>Candidate: {revision.candidate_id}; M02: {revision.intake_id}; M03: {revision.m03_revision_id}; M04: {revision.m04_revision_id}.</p>
    <ProductContextView context={revision.product_context} label={`Revision ${revision.revision_sequence} product context`} />
    <p>Statement date: {revision.statement_date}; evaluation date: {revision.evaluation_date}; stale: {String(revision.is_stale)}.</p>
    <p>Currency: {revision.currency}; explicit confirmation: {String(revision.currency_confirmed)}.</p>
    <p>Source total: {text(revision.source_total_value)} ({revision.source_total_state}); effective total: {text(revision.effective_total_value)} ({revision.effective_total_state}).</p>
    <p>Signed discrepancy: {text(revision.signed_discrepancy)}; absolute discrepancy: {text(revision.absolute_discrepancy)}; tolerance satisfied: {String(revision.tolerance_satisfied)}.</p>
    <p>Algorithm: {revision.algorithm_version}; source digest: {revision.source_snapshot_digest}; mapping digest: {revision.mapping_digest}.</p>
    <h5>Source and effective values</h5>
    <table><thead><tr><th>Identity</th><th>Kind</th><th>Source</th><th>Effective</th><th>Mapping</th></tr></thead>
      <tbody>{revision.values.map((value) => <tr key={value.value_id}>
        <td>{value.evidence_identity}<br />index {text(value.component_index)}; label {text(value.original_label)}; code {text(value.original_code)}</td>
        <td>{value.component_kind}</td>
        <td>{text(value.source_value)} ({value.source_state})</td>
        <td>{text(value.effective_value)} ({value.effective_state})</td>
        <td>{value.included_in_reconciliation ? "included exactly once" : `excluded: ${text(value.exclusion_reason)}`}</td>
      </tr>)}</tbody>
    </table>
    <p>Included evidence: {JSON.stringify(revision.included_evidence)}</p>
    <p>Excluded evidence: {JSON.stringify(revision.excluded_evidence)}</p>
    <p>Warnings: {JSON.stringify(revision.warnings)}; dispositions: {JSON.stringify(revision.warning_dispositions)}</p>
    <p>Provenance: {JSON.stringify(revision.provenance)}</p>
    {revision.adjustment ? <p>Adjustment: {revision.adjustment.evidence_identity}, {revision.adjustment.previous_effective_value} → {revision.adjustment.new_effective_value}; {revision.adjustment.reason_code}; {revision.adjustment.explanation}.</p> : null}
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

  if (clientId === null) return <p role="alert">Invalid client ID.</p>;
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
    <h2>M05 Manual Pension Balance Ledger</h2>
    <p>Client: {client?.full_name ?? clientId}. Manual records only. M06 remains separately unauthorized.</p>
    <p><Link to={`/clients/${clientId}`}>Back to client</Link></p>
    {error ? <p role="alert">{error}</p> : null}
    {loading ? <p>Loading M05 evidence…</p> : null}

    <section><h3>Manual candidates</h3>
      {candidates.length ? <ul>{candidates.map((candidate) => <li key={candidate.candidate_id}>
        <button type="button" onClick={() => chooseCandidate(candidate.candidate_id)}>
          {candidate.provider_name ?? "Provider unavailable"} / {candidate.account_reference ?? "Account unavailable"} / {candidate.statement_date ?? "Statement date unavailable"}
        </button>
        <span> — {candidateExplanation(candidate)}</span>
        <ProductContextView context={candidate.product_context} label={`Candidate ${candidate.candidate_id} product context`} />
      </li>)}</ul> : <p>No manual M05 candidates.</p>}
      {selectedCandidateRow ? <section aria-label="Selected candidate explanation">
        <h4>Why this candidate is or is not usable</h4>
        <p>{candidateExplanation(selectedCandidateRow)}</p>
        <p>Provider: {selectedCandidateRow.provider_name ?? "not supplied"}; account: {selectedCandidateRow.account_reference ?? "not supplied"}; statement date: {selectedCandidateRow.statement_date ?? "not supplied"}.</p>
        <p>Technical eligibility: {String(selectedCandidateRow.eligible)}; current authority: {String(selectedCandidateRow.authoritative_current)}.</p>
        {selectedCandidateRow.exclusion_reason
          ? <p><small>Technical exclusion code: {selectedCandidateRow.exclusion_reason}</small></p>
          : null}
        {selectedCandidateRow.informational_warnings.length
          ? <p>Technical informational warnings: {selectedCandidateRow.informational_warnings.join(", ")}</p>
          : null}
      </section> : null}
      <label><input type="checkbox" checked={confirmCurrency} onChange={(event) => setConfirmCurrency(event.target.checked)} /> Confirm currency ILS for this current candidate</label>
      <button type="button" disabled={!selectedCandidateRow?.eligible || !selectedCandidateRow.authoritative_current || submitting} onClick={() => void mutate(() => startM05(clientId, selectedCandidateId, confirmCurrency))}>Start ledger</button>
    </section>

    <section><h3>Ledger subjects</h3>
      {subjects.length ? <ul>{subjects.map((row) => <li key={row.subject_id}>
        <button type="button" onClick={() => void loadSubject(row.subject_id)}>{row.provider_name} / {row.account_reference}</button>
        <span> — {row.current_revision?.state ?? "no revision"}; M06 technical eligibility: {String(row.eligibility.eligible_for_m06)}</span>
      </li>)}</ul> : <p>No M05 ledger subjects.</p>}
    </section>

    {current ? <section><h3>Current ledger</h3>
      <RevisionView revision={current} current />
      <h4>Technical M06 eligibility</h4>
      <p>{currentEligibility?.meaning}. Eligible: {String(currentEligibility?.eligible_for_m06)}.</p>
      <p>Exclusions: {currentEligibility?.exclusion_reasons.join(", ") || "none"}; informational warnings: {currentEligibility?.informational_warnings.join(", ") || "none"}.</p>
      <p>This result does not authorize conversion, coefficients, tax, fixation, liquidity, withdrawal, pension commencement, or reports.</p>
      <h4>Action intent</h4>
      <label>Reason code <input value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} /></label>
      <label>Explanation <textarea value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
      <button type="button" disabled={submitting || current.state !== "draft"} onClick={() => void mutate(() => reconcileM05(clientId, current.subject_id, current.revision_id, confirmCurrency))}>Reconcile</button>
      <button type="button" disabled={submitting || !reasonPayload || current.state !== "draft" || !mandatory.length} onClick={() => reasonPayload && void mutate(() => reviewWarningsM05(clientId, current.subject_id, { ...reasonPayload, mandatory_warning_ids: mandatory, confirmed: true, ...(confirmCurrency ? { confirm_currency_ils: true as const } : {}) }))}>Review exact mandatory warning set</button>
      <button type="button" disabled={submitting || !reasonPayload || !["draft", "reconciled", "warning_reviewed"].includes(current.state)} onClick={() => reasonPayload && void mutate(() => reasonActionM05(clientId, current.subject_id, "mark-blocked", reasonPayload))}>Mark blocked</button>
      <button type="button" disabled={submitting || !reasonPayload || current.state === "superseded"} onClick={() => reasonPayload && void mutate(() => reasonActionM05(clientId, current.subject_id, "supersede", reasonPayload))}>Supersede</button>
      <h4>Single-value adjustment</h4>
      <select value={adjustIdentity} onChange={(event) => setAdjustIdentity(event.target.value)}><option value="">Select value</option>{current.values.map((value) => <option key={value.value_id} value={value.evidence_identity}>{value.evidence_identity}</option>)}</select>
      <input aria-label="New effective value" value={adjustValue} onChange={(event) => setAdjustValue(event.target.value)} placeholder="0.00" />
      <button type="button" disabled={submitting || !reasonPayload || current.state === "superseded" || !adjustIdentity || !adjustValue} onClick={() => reasonPayload && void mutate(() => adjustM05(clientId, current.subject_id, { ...reasonPayload, evidence_identity: adjustIdentity, new_effective_value: adjustValue, confirmed: true }))}>Adjust one value</button>
      <h4>Revalidate</h4>
      <button type="button" disabled={submitting || !reasonPayload || current.state === "superseded" || !selectedCandidateRow?.eligible || !selectedCandidateRow.authoritative_current} onClick={() => reasonPayload && void mutate(() => revalidateM05(clientId, current.subject_id, { ...reasonPayload, candidate_id: selectedCandidateId }))}>Revalidate against selected current candidate</button>
      <h4>Current provenance and warnings</h4><p>{JSON.stringify(provenance)}</p><p>{JSON.stringify(warnings)}</p>
    </section> : null}

    {history.length ? <section><h3>Immutable history</h3><ol>{history.map((revision) => <RevisionView key={revision.revision_id} revision={revision} current={revision.revision_id === current?.revision_id} />)}</ol></section> : null}
  </main>;
}
