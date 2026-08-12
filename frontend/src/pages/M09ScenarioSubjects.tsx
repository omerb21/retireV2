import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { createM09AdjustedSubject, executeM09SubjectRun, getM09Subject, getM09SubjectCurrentness, getM09SubjectEligibility, getM09SubjectRun, listM09SubjectRuns, listM09Subjects, resolveM09BaselineSubject, type M09AdjustmentInput, type M09ScenarioSubject, type M09SubjectRun, type M09SubjectRunSummary } from "../api/m09CashflowApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";

const blank = (): M09AdjustmentInput => ({ adjustment_type: "declared_additional_monthly_income", amount: "", start_month: "", end_month: "" });
const message = (error: unknown) => error instanceof Error ? error.message : "Scenario subject request failed";

export function M09ScenarioSubjects({ clientId }: { clientId: number }) {
  const location = useLocation();
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [subjects, setSubjects] = useState<M09ScenarioSubject[]>([]); const [selected, setSelected] = useState<M09ScenarioSubject | null>(null);
  const [runs, setRuns] = useState<M09SubjectRunSummary[]>([]); const [run, setRun] = useState<M09SubjectRun | null>(null);
  const [label, setLabel] = useState(""); const [adjustments, setAdjustments] = useState<M09AdjustmentInput[]>([blank()]);
  const [start, setStart] = useState(""); const [end, setEnd] = useState(""); const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(0); const mounted = useRef(false); const epochs = useRef<Record<string, number>>({}); const seq = useRef(0); const active = useRef(new Set<number>());
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current.clear(); }; }, []);
  useEffect(() => { epochs.current = {}; active.current.clear(); setBusy(0); setSubjects([]); setSelected(null); setRuns([]); setRun(null); setError(null); }, [clientId, location.key]);
  const begin = () => { const id = ++seq.current; active.current.add(id); setBusy(active.current.size); return id; };
  const finish = (id: number) => { if (active.current.delete(id) && mounted.current) setBusy(active.current.size); };
  const owner = (channel: string) => { const token = captureClientContext(); const epoch = (epochs.current[channel] ?? 0) + 1; epochs.current[channel] = epoch; return () => mounted.current && epochs.current[channel] === epoch && isCurrentClientContext(token); };
  const guarded = async <T,>(channel: string, operation: () => Promise<T>, success: (value: T) => void) => {
    const owns = owner(channel); const id = begin(); setError(null);
    try { const value = await operation(); if (owns()) success(value); } catch (cause) { if (owns()) setError(message(cause)); } finally { finish(id); }
  };
  const loadSubjects = useCallback(async () => {
    const owns = owner("candidate-load"); const id = begin();
    try { const value = await listM09Subjects(clientId); if (owns()) setSubjects(value); } catch (cause) { if (owns()) setError(message(cause)); } finally { finish(id); }
  // owner/begin/finish deliberately use generation refs.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadSubjects(); }, [loadSubjects]);
  const select = (subjectId: string) => void guarded("subject-detail", () => Promise.all([getM09Subject(clientId, subjectId), listM09SubjectRuns(clientId, subjectId)]), ([subject, history]) => { setSelected(subject); setRuns(history); setRun(null); });
  const valid = adjustments.length > 0 && adjustments.every(a => /^\d+\.\d{2}$/.test(a.amount) && a.amount !== "0.00" && /^\d{4}-(0[1-9]|1[0-2])$/.test(a.start_month) && a.end_month >= a.start_month);
  return <section><h3>Parallel declared-retirement scenario subjects</h3>
    <p>Planner-declared sensitivity alternatives only. They are not forecasts, recommendations, professional authority, or M10 comparison.</p>
    {error ? <p role="alert">{error}</p> : null}{busy ? <p>Loading scenario evidence…</p> : null}
    <button type="button" disabled={busy > 0} onClick={() => void guarded("baseline-resolve", () => resolveM09BaselineSubject(clientId), value => { setSelected(value); void loadSubjects(); })}>Resolve server baseline subject</button>
    <fieldset><legend>Create immutable adjusted subject</legend><label>Display label <input aria-label="Scenario display label" value={label} onChange={e => setLabel(e.target.value)} /></label>
      {adjustments.map((a, index) => <div key={index}><label>Adjustment type <select aria-label={`Adjustment type ${index + 1}`} value={a.adjustment_type} onChange={e => setAdjustments(values => values.map((v, i) => i === index ? { ...v, adjustment_type: e.target.value as M09AdjustmentInput["adjustment_type"] } : v))}><option value="declared_additional_monthly_income">Additional monthly income</option><option value="declared_additional_monthly_expense">Additional monthly expense</option></select></label>
        <label>Amount ILS <input aria-label={`Adjustment amount ${index + 1}`} value={a.amount} onChange={e => setAdjustments(values => values.map((v, i) => i === index ? { ...v, amount: e.target.value } : v))} /></label>
        <label>Adjustment from <input aria-label={`Adjustment start month ${index + 1}`} type="month" value={a.start_month} onChange={e => setAdjustments(values => values.map((v, i) => i === index ? { ...v, start_month: e.target.value } : v))} /></label>
        <label>Adjustment to <input aria-label={`Adjustment end month ${index + 1}`} type="month" value={a.end_month} onChange={e => setAdjustments(values => values.map((v, i) => i === index ? { ...v, end_month: e.target.value } : v))} /></label>
        {adjustments.length > 1 ? <button type="button" onClick={() => setAdjustments(values => values.filter((_, i) => i !== index))}>Remove adjustment {index + 1}</button> : null}</div>)}
      <button type="button" onClick={() => setAdjustments(values => [...values, blank()])}>Add another adjustment</button>
      <button type="button" disabled={!valid || busy > 0} onClick={() => void guarded("subject-create", () => createM09AdjustedSubject(clientId, label, adjustments), value => { setSelected(value); setAdjustments([blank()]); setLabel(""); void loadSubjects(); })}>Create adjusted subject</button>
    </fieldset>
    <h4>Subjects</h4>{subjects.length ? <ul>{subjects.map(subject => <li key={subject.scenario_subject_id}><button type="button" onClick={() => select(subject.scenario_subject_id)}>{subject.display_label ?? "Baseline"}</button> — {subject.subject_type}; {subject.adjustments.length} adjustment occurrence(s)</li>)}</ul> : <p>No scenario subjects.</p>}
    {selected ? <div><h4>Selected subject: {selected.display_label ?? "Baseline"}</h4><p>{selected.combined_contract_identifier}; immutable manifest {selected.adjustment_manifest_fingerprint}</p>
      <label>Execution start <input aria-label="Subject execution start" type="month" value={start} onChange={e => setStart(e.target.value)} /></label><label>Execution end <input aria-label="Subject execution end" type="month" value={end} onChange={e => setEnd(e.target.value)} /></label>
      <button type="button" disabled={!start || end < start || busy > 0} onClick={() => void guarded("subject-execute", () => executeM09SubjectRun(clientId, selected.scenario_subject_id, start, end), value => { setRun(value); void select(selected.scenario_subject_id); })}>Execute selected subject</button>
      <h4>Subject run history</h4>{runs.length ? <ul>{runs.map(item => <li key={item.run_id}><button type="button" onClick={() => void guarded("run-load", () => Promise.all([getM09SubjectRun(clientId, selected.scenario_subject_id, item.run_id), getM09SubjectCurrentness(clientId, selected.scenario_subject_id, item.run_id), getM09SubjectEligibility(clientId, selected.scenario_subject_id, item.run_id)]), ([value, currentness, eligibility]) => setRun({ ...value, currentness, m10_eligibility: eligibility }))}>Load subject run {item.run_sequence}</button> — current {String(item.is_current)}</li>)}</ul> : <p>No runs for this subject.</p>}</div> : null}
    {run ? <div><h4>Subject result</h4><p>Status {run.status}; independently current {String(run.currentness.is_current)}; per-run M10 technical eligibility {String(run.m10_eligibility.eligible_for_m10)}.</p><p>Factual baseline material: {run.factual_baseline_material_fingerprint}</p><table><thead><tr><th>Month</th><th>Inflows</th><th>Outflows</th><th>Net</th></tr></thead><tbody>{run.monthly_results.map(row => <tr key={row.monthly_result_id}><td>{row.month}</td><td>{row.gross_inflow_total}</td><td>{row.gross_outflow_total}</td><td>{row.period_net}</td></tr>)}</tbody></table></div> : null}
  </section>;
}
