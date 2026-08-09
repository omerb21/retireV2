import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import {
  correctM06Coefficient, getM06History, getM06Subject, listM06Candidates, listM06Subjects,
  resolveM06, reviewM06Warnings, startM06, supersedeM06, type CoefficientIntent,
  type M06Authority, type M06Candidate, type M06Revision, type M06Subject,
} from "../api/m06ConversionApi";

const message = (error: unknown) => error instanceof Error ? error.message : "M06 request failed";

export function M06ConversionScreen() {
  const { clientId: raw } = useParams(); const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [candidates, setCandidates] = useState<M06Candidate[]>([]); const [subjects, setSubjects] = useState<M06Subject[]>([]);
  const [selected, setSelected] = useState<M06Candidate | null>(null); const [detail, setDetail] = useState<M06Subject | null>(null);
  const [history, setHistory] = useState<M06Revision[]>([]); const [authority, setAuthority] = useState<M06Authority>("planner_declared");
  const [coefficient, setCoefficient] = useState(""); const [sourceIntake, setSourceIntake] = useState(""); const [locator, setLocator] = useState("");
  const [note, setNote] = useState(""); const [reason, setReason] = useState(""); const [effectiveFrom, setEffectiveFrom] = useState(""); const [effectiveTo, setEffectiveTo] = useState("");
  const [actionReason, setActionReason] = useState("");
  const [sourceVersion, setSourceVersion] = useState(""); const [issuerProvider, setIssuerProvider] = useState(""); const [age, setAge] = useState("");
  const [gender, setGender] = useState(""); const [pensionOption, setPensionOption] = useState(""); const [guaranteePeriod, setGuaranteePeriod] = useState(""); const [survivorOption, setSurvivorOption] = useState("");
  const [applies, setApplies] = useState(false); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const mounted = useRef(false); const overviewEpoch = useRef(0); const detailEpoch = useRef(0); const mutationEpoch = useRef(0);
  const selectedSubject = useRef<string | null>(null); const selectedRevision = useRef<string | null>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; overviewEpoch.current++; detailEpoch.current++; mutationEpoch.current++; }; }, []);
  useEffect(() => { overviewEpoch.current++; detailEpoch.current++; mutationEpoch.current++; selectedSubject.current = null; selectedRevision.current = null; setCandidates([]); setSubjects([]); setSelected(null); setDetail(null); setHistory([]); setAuthority("planner_declared"); setCoefficient(""); setSourceIntake(""); setLocator(""); setNote(""); setReason(""); setActionReason(""); setEffectiveFrom(""); setEffectiveTo(""); setApplies(false); setSourceVersion(""); setIssuerProvider(""); setAge(""); setGender(""); setPensionOption(""); setGuaranteePeriod(""); setSurvivorOption(""); setError(null); setBusy(false); }, [clientId, location.key]);

  const loadOverview = useCallback(async () => {
    if (clientId === null) return; const token = captureClientContext(); const epoch = ++overviewEpoch.current;
    const owned = () => mounted.current && epoch === overviewEpoch.current && isCurrentClientContext(token);
    setBusy(true); try { const [nextCandidates, nextSubjects] = await Promise.all([listM06Candidates(clientId), listM06Subjects(clientId)]); if (owned()) { setCandidates(nextCandidates); setSubjects(nextSubjects); } } catch (cause) { if (owned()) setError(message(cause)); } finally { if (owned()) setBusy(false); }
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadOverview(); }, [loadOverview]);

  const loadDetail = useCallback(async (id: string) => {
    if (clientId === null) return; const token = captureClientContext(); const epoch = ++detailEpoch.current; mutationEpoch.current++; selectedSubject.current = id; selectedRevision.current = null;
    const owned = () => mounted.current && epoch === detailEpoch.current && selectedSubject.current === id && isCurrentClientContext(token);
    setBusy(true); try { const [next, trail] = await Promise.all([getM06Subject(clientId, id), getM06History(clientId, id)]); if (owned()) { selectedRevision.current = next.current_revision?.revision_id ?? null; setDetail(next); setHistory(trail); } } catch (cause) { if (owned()) setError(message(cause)); } finally { if (owned()) setBusy(false); }
  }, [captureClientContext, clientId, isCurrentClientContext]);

  const intent = (): CoefficientIntent => ({ authority_class: authority, coefficient, ...(authority === "documentary" ? { source_intake_id: sourceIntake, source_locator: locator } : { source_note: note }), reason, ...(effectiveFrom ? { effective_from: effectiveFrom } : {}), ...(effectiveTo ? { effective_to: effectiveTo } : {}), applicability_declared: applies, metadata: { ...(sourceVersion ? { source_version: sourceVersion } : {}), ...(issuerProvider ? { issuer_provider: issuerProvider } : {}), ...(age ? { age: Number(age) } : {}), ...(gender ? { gender } : {}), ...(pensionOption ? { pension_option: pensionOption } : {}), ...(guaranteePeriod ? { guarantee_period: guaranteePeriod } : {}), ...(survivorOption ? { survivor_option: survivorOption } : {}) } });
  const mutate = async (operation: () => Promise<M06Revision>) => {
    if (clientId === null) return; const token = captureClientContext(); const subjectId = selectedSubject.current; const revisionId = selectedRevision.current; const epoch = ++mutationEpoch.current;
    const owned = () => mounted.current && epoch === mutationEpoch.current && selectedSubject.current === subjectId && selectedRevision.current === revisionId && isCurrentClientContext(token);
    setBusy(true); setError(null); try { const result = await operation(); if (!owned()) return; selectedSubject.current = result.subject_id; selectedRevision.current = result.revision_id; await loadOverview(); if (owned()) await loadDetail(result.subject_id); } catch (cause) { if (owned()) setError(message(cause)); } finally { if (owned()) setBusy(false); }
  };
  if (clientId === null) return <p role="alert">Invalid client ID.</p>;
  const current = detail?.current_revision ?? null; const warningIds = current?.warnings.filter((item) => item.classification === "mandatory").map((item) => item.warning_id) ?? [];
  return <main><h2>M06 First-stage pension/capital conversion</h2>
    <p>This is bounded technical conversion evidence. It is not professional, financial, tax or downstream execution authority.</p><p><Link to={`/clients/${clientId}`}>Back to client</Link></p>
    {error ? <p role="alert">{error}</p> : null}{busy ? <p>Loading M06 evidence…</p> : null}
    <section><h3>Eligible predecessor inputs</h3>{candidates.length ? <ul>{candidates.map((row) => <li key={row.candidate_id}><button type="button" onClick={() => setSelected(row)}>{row.provider_name} / {row.account_reference} / {row.mode}</button> — {row.formula_id}; amount {row.input_amount ?? "missing"}; date {row.input_date ?? "missing"}; eligible {String(row.eligible)}</li>)}</ul> : <p>No M06 candidates.</p>}
      {selected ? <div><h4>Coefficient evidence and applicability</h4><p>Formula: {selected.formula_id}. Input and result are server-derived and cannot be edited.</p>
        <label>Authority <select value={authority} onChange={(e) => setAuthority(e.target.value as M06Authority)}><option value="planner_declared">planner_declared</option><option value="documentary">documentary</option></select></label>
        <label>Exact coefficient string <input aria-label="Exact coefficient string" value={coefficient} onChange={(e) => setCoefficient(e.target.value)} /></label>
        {authority === "documentary" ? <><label>Accepted source intake <input value={sourceIntake} onChange={(e) => setSourceIntake(e.target.value)} /></label><label>Exact source locator <input value={locator} onChange={(e) => setLocator(e.target.value)} /></label></> : <label>Planner source note <textarea value={note} onChange={(e) => setNote(e.target.value)} /></label>}
        <label>Coefficient evidence reason <textarea value={reason} onChange={(e) => setReason(e.target.value)} /></label><label>Effective from <input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></label><label>Effective to <input type="date" value={effectiveTo} onChange={(e) => setEffectiveTo(e.target.value)} /></label>
        <fieldset><legend>Coefficient dimensions actually used (optional)</legend><label>Source version <input value={sourceVersion} onChange={(e) => setSourceVersion(e.target.value)} /></label><label>Issuer/provider <input value={issuerProvider} onChange={(e) => setIssuerProvider(e.target.value)} /></label><label>Age <input type="number" min="0" max="130" value={age} onChange={(e) => setAge(e.target.value)} /></label><label>Gender dimension <input value={gender} onChange={(e) => setGender(e.target.value)} /></label><label>Pension option <input value={pensionOption} onChange={(e) => setPensionOption(e.target.value)} /></label><label>Guarantee period <input value={guaranteePeriod} onChange={(e) => setGuaranteePeriod(e.target.value)} /></label><label>Survivor option <input value={survivorOption} onChange={(e) => setSurvivorOption(e.target.value)} /></label></fieldset>
        <label><input type="checkbox" checked={applies} onChange={(e) => setApplies(e.target.checked)} /> Declare applicability to the displayed input date</label>
        <button disabled={busy || !coefficient || !reason} onClick={() => void mutate(() => startM06(clientId, selected, intent()))}>Start immutable draft</button></div> : null}</section>
    <section><h3>Conversion subjects</h3>{subjects.length ? <ul>{subjects.map((row) => <li key={row.subject_id}><button onClick={() => void loadDetail(row.subject_id)}>{row.mode} / {row.input_identity}</button> — {row.current_revision?.state}; downstream eligible {String(row.eligibility.eligible_for_downstream)}</li>)}</ul> : <p>No conversion subjects.</p>}</section>
    {current ? <section><h3>Current conversion revision</h3><p>Revision {current.revision_sequence}: {current.state}; {current.formula_id}; input {current.input_amount ?? "missing"}; coefficient {current.coefficient.coefficient} ({current.coefficient.authority_class}).</p><p>Actor {current.actor} is operational provenance, not authentication or approval.</p><p>Warnings: {warningIds.join(", ") || "none"}; blockers: {current.blocking_reasons.join(", ") || "none"}.</p>
      {current.manifest ? <><p>Raw: {current.manifest.raw_result_kind === "exact_ratio" ? `${current.manifest.raw_numerator}/${current.manifest.raw_denominator}` : current.manifest.raw_decimal}; displayed: {current.manifest.display_result}; fingerprint: {current.manifest.fingerprint}.</p><details><summary>Immutable provenance manifest</summary><pre>{JSON.stringify(current.manifest.evidence, null, 2)}</pre></details></> : <p>No calculation result exists for this revision.</p>}
      <p>Technical downstream eligibility: {String(detail?.eligibility.eligible_for_downstream)}; exclusions: {detail?.eligibility.exclusion_reasons.join(", ") || "none"}.</p>
      <label>Action reason / warning explanation <textarea value={actionReason} onChange={(e) => setActionReason(e.target.value)} /></label>
      <button disabled={busy || current.state !== "draft" || current.action_type === "resolve"} onClick={() => void mutate(() => resolveM06(clientId, current.subject_id, current.revision_id))}>Resolve exact formula</button>
      <button disabled={busy || current.state !== "draft" || current.action_type !== "resolve" || warningIds.length === 0 || !actionReason} onClick={() => void mutate(() => reviewM06Warnings(clientId, current.subject_id, current.revision_id, warningIds, actionReason))}>Review exact mandatory warning set</button>
      <button disabled={busy || !coefficient || !reason || !actionReason || current.state === "superseded"} onClick={() => void mutate(() => correctM06Coefficient(clientId, current.subject_id, current.revision_id, intent(), actionReason))}>Append corrected coefficient draft</button>
      <button disabled={busy || !actionReason || current.state === "superseded"} onClick={() => void mutate(() => supersedeM06(clientId, current.subject_id, current.revision_id, actionReason))}>Supersede current conversion</button>
    </section> : null}
    {history.length ? <section><h3>Immutable history</h3><ol>{history.map((row) => <li key={row.revision_id}>#{row.revision_sequence} {row.state}; {row.action_type}; {row.revision_id}; result {row.manifest?.display_result ?? "none"}</li>)}</ol></section> : null}
  </main>;
}
