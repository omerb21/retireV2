import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  createM09AdjustedSubject, executeM09SubjectRun, getM09Subject,
  getM09SubjectCurrentness, getM09SubjectEligibility, getM09SubjectRun,
  listM09SubjectRuns, listM09Subjects, resolveM09BaselineSubject,
  type M09AdjustmentInput, type M09ScenarioSubject, type M09SubjectRun,
  type M09SubjectRunSummary,
} from "../api/m09CashflowApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { heBoolean, heLabel } from "../i18n/he";

const blank = (): M09AdjustmentInput => ({ adjustment_type: "declared_additional_monthly_income", amount: "", start_month: "", end_month: "" });
const message = (error: unknown) => error instanceof Error ? error.message : "בקשת חלופת התרחיש נכשלה";
type LoadingOwner = { subjectGeneration: number | null };

export function M09ScenarioSubjects({ clientId }: { clientId: number }) {
  const location = useLocation();
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [subjects, setSubjects] = useState<M09ScenarioSubject[]>([]);
  const [selected, setSelected] = useState<M09ScenarioSubject | null>(null);
  const [runs, setRuns] = useState<M09SubjectRunSummary[]>([]);
  const [run, setRun] = useState<M09SubjectRun | null>(null);
  const [label, setLabel] = useState(""); const [adjustments, setAdjustments] = useState<M09AdjustmentInput[]>([blank()]);
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(0);
  const mounted = useRef(false); const channelEpochs = useRef<Record<string, number>>({});
  const subjectGeneration = useRef(0); const selectedSubjectId = useRef<string | null>(null);
  const sequence = useRef(0); const active = useRef(new Map<number, LoadingOwner>());

  const refreshBusy = () => {
    if (!mounted.current) return;
    setBusy([...active.current.values()].filter(owner => owner.subjectGeneration === null || owner.subjectGeneration === subjectGeneration.current).length);
  };
  const begin = (subjectBound: boolean) => {
    const id = ++sequence.current;
    active.current.set(id, { subjectGeneration: subjectBound ? subjectGeneration.current : null });
    refreshBusy(); return id;
  };
  const finish = (id: number) => { active.current.delete(id); refreshBusy(); };
  const invalidateSubjectContext = (nextSubjectId: string | null) => {
    subjectGeneration.current += 1; selectedSubjectId.current = nextSubjectId;
    setSelected(null); setRuns([]); setRun(null); setError(null); refreshBusy();
  };
  const owner = (channel: string, subjectId?: string) => {
    const clientToken = captureClientContext();
    const epoch = (channelEpochs.current[channel] ?? 0) + 1; channelEpochs.current[channel] = epoch;
    const capturedSubjectGeneration = subjectId === undefined ? null : subjectGeneration.current;
    return () => mounted.current
      && channelEpochs.current[channel] === epoch
      && isCurrentClientContext(clientToken)
      && (subjectId === undefined || (
        capturedSubjectGeneration === subjectGeneration.current
        && selectedSubjectId.current === subjectId
      ));
  };
  const guarded = async <T,>(channel: string, operation: () => Promise<T>, success: (value: T) => void, subjectId?: string) => {
    const owns = owner(channel, subjectId); const loading = begin(subjectId !== undefined); setError(null);
    try { const value = await operation(); if (owns()) success(value); }
    catch (cause) { if (owns()) setError(message(cause)); }
    finally { finish(loading); }
  };

  useEffect(() => { mounted.current = true; refreshBusy(); return () => { mounted.current = false; active.current.clear(); }; }, []);
  useEffect(() => {
    channelEpochs.current = {}; active.current.clear(); subjectGeneration.current += 1; selectedSubjectId.current = null;
    setBusy(0); setSubjects([]); setSelected(null); setRuns([]); setRun(null); setError(null);
  }, [clientId, location.key]);

  const loadSubjects = useCallback(async () => {
    const owns = owner("subject-list"); const loading = begin(false);
    try { const value = await listM09Subjects(clientId); if (owns()) setSubjects(value); }
    catch (cause) { if (owns()) setError(message(cause)); }
    finally { finish(loading); }
  // Ownership helpers deliberately use generation refs.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadSubjects(); }, [loadSubjects]);

  const adoptSubject = (subject: M09ScenarioSubject, history: M09SubjectRunSummary[] = []) => {
    invalidateSubjectContext(subject.scenario_subject_id);
    selectedSubjectId.current = subject.scenario_subject_id; setSelected(subject); setRuns(history);
  };
  const selectSubject = (subjectId: string) => {
    invalidateSubjectContext(subjectId);
    void guarded("subject-detail", () => Promise.all([getM09Subject(clientId, subjectId), listM09SubjectRuns(clientId, subjectId)]), ([subject, history]) => {
      setSelected(subject); setRuns(history);
    }, subjectId);
  };
  const refreshRuns = (subjectId: string) => void guarded("run-history", () => listM09SubjectRuns(clientId, subjectId), setRuns, subjectId);
  const valid = adjustments.length > 0 && adjustments.every(a => /^\d+\.\d{2}$/.test(a.amount) && a.amount !== "0.00" && /^\d{4}-(0[1-9]|1[0-2])$/.test(a.start_month) && a.end_month >= a.start_month);

  const factualDomains = run && Array.isArray(run.factual_inventory.domains) ? run.factual_inventory.domains as Array<Record<string, unknown>> : [];
  return <section><h3>חלופות מקבילות של תרחיש פרישה מוצהר</h3>
    <p>חלופות רגישות שהמתכנן הצהיר עליהן בלבד. הן אינן תחזית, המלצה, סמכות מקצועית או השוואת M10.</p>
    {error ? <p role="alert">{error}</p> : null}{busy ? <p>טעינת ראיות התרחיש…</p> : null}
    <button type="button" disabled={busy > 0} onClick={() => void guarded("baseline-resolution", () => resolveM09BaselineSubject(clientId), value => { adoptSubject(value); void loadSubjects(); })}>איתור תרחיש הבסיס בשרת</button>
    <fieldset><legend>יצירת חלופה מותאמת ובלתי ניתנת לשינוי</legend><label>שם תצוגה <input aria-label="שם תצוגת התרחיש" value={label} onChange={event => setLabel(event.target.value)} /></label>
      {adjustments.map((adjustment, index) => <div key={index} data-testid={`adjustment-input-${index + 1}`}><label>סוג התאמה <select aria-label={`סוג התאמה ${index + 1}`} value={adjustment.adjustment_type} onChange={event => setAdjustments(values => values.map((value, current) => current === index ? { ...value, adjustment_type: event.target.value as M09AdjustmentInput["adjustment_type"] } : value))}><option value="declared_additional_monthly_income">הכנסה חודשית נוספת</option><option value="declared_additional_monthly_expense">הוצאה חודשית נוספת</option></select></label>
        <label>סכום בש״ח <input aria-label={`סכום התאמה ${index + 1}`} value={adjustment.amount} onChange={event => setAdjustments(values => values.map((value, current) => current === index ? { ...value, amount: event.target.value } : value))} /></label>
        <label>התאמה מחודש <input aria-label={`חודש התחלת התאמה ${index + 1}`} type="month" value={adjustment.start_month} onChange={event => setAdjustments(values => values.map((value, current) => current === index ? { ...value, start_month: event.target.value } : value))} /></label>
        <label>התאמה עד חודש <input aria-label={`חודש סיום התאמה ${index + 1}`} type="month" value={adjustment.end_month} onChange={event => setAdjustments(values => values.map((value, current) => current === index ? { ...value, end_month: event.target.value } : value))} /></label>
        {adjustments.length > 1 ? <button type="button" onClick={() => setAdjustments(values => values.filter((_, current) => current !== index))}>הסרת התאמה {index + 1}</button> : null}</div>)}
      <button type="button" onClick={() => setAdjustments(values => [...values, blank()])}>הוספת התאמה נוספת</button>
      <button type="button" disabled={!valid || busy > 0} onClick={() => void guarded("subject-creation", () => createM09AdjustedSubject(clientId, label, adjustments), value => { adoptSubject(value); setAdjustments([blank()]); setLabel(""); void loadSubjects(); })}>יצירת חלופה מותאמת</button>
    </fieldset>
    <h4>חלופות</h4>{subjects.length ? <ul>{subjects.map(subject => <li key={subject.scenario_subject_id}><button type="button" onClick={() => selectSubject(subject.scenario_subject_id)}>{subject.display_label ?? "בסיס"}</button> — {heLabel(subject.subject_type)}; מספר התאמות: {subject.adjustments.length}</li>)}</ul> : <p>אין חלופות תרחיש.</p>}
    {selected ? <div><h4>חלופה נבחרת: {selected.display_label ?? "בסיס"}</h4><p>{selected.combined_contract_identifier}; טביעת אצבע בלתי ניתנת לשינוי {selected.adjustment_manifest_fingerprint}</p>
      <section aria-label="התאמות תרחיש מוצהרות"><h5>התאמות תרחיש מוצהרות</h5>
        {selected.subject_type === "baseline" ? <p>לחלופת הבסיס שבאחריות השרת אין התאמות: <small>server_resolved_no_scenario_adjustments</small>.</p> : <ol>{selected.adjustments.map(adjustment => <li key={adjustment.adjustment_id}><span>{heLabel(adjustment.adjustment_type)}</span>: <span>{adjustment.amount} ש״ח</span>, <span>{adjustment.start_month}</span>–<span>{adjustment.end_month}</span></li>)}</ol>}
      </section>
      <label>חודש התחלת הרצה <input aria-label="חודש התחלת הרצת החלופה" type="month" value={start} onChange={event => setStart(event.target.value)} /></label><label>חודש סיום הרצה <input aria-label="חודש סיום הרצת החלופה" type="month" value={end} onChange={event => setEnd(event.target.value)} /></label>
      <button type="button" disabled={!start || end < start || busy > 0} onClick={() => { const subjectId=selected.scenario_subject_id; void guarded("subject-execution", () => executeM09SubjectRun(clientId, subjectId, start, end), value => { setRun(value); refreshRuns(subjectId); }, subjectId); }}>הרצת החלופה הנבחרת</button>
      <h4>היסטוריית הרצות החלופה</h4>{runs.length ? <ul>{runs.map(item => <li key={item.run_id}><button type="button" onClick={() => { const subjectId=selected.scenario_subject_id; void guarded("run-result", () => Promise.all([getM09SubjectRun(clientId, subjectId, item.run_id), getM09SubjectCurrentness(clientId, subjectId, item.run_id), getM09SubjectEligibility(clientId, subjectId, item.run_id)]), ([value, currentness, eligibility]) => setRun({ ...value, currentness, m10_eligibility: eligibility }), subjectId); }}>טעינת הרצת חלופה {item.run_sequence}</button> — עדכנית {String(item.is_current)}</li>)}</ul> : <p>אין הרצות לחלופה זו.</p>}</div> : null}
    {run ? <div><h4>תוצאת החלופה</h4><p>מצב {heLabel(run.status)}; עדכנית באופן עצמאי {heBoolean(run.currentness.is_current)}; כשירות טכנית ל־M10 להרצה זו {heBoolean(run.m10_eligibility.eligible_for_m10)}.</p><p>טביעת אצבע של חומר הבסיס העובדתי: {run.factual_baseline_material_fingerprint}</p>
      <section aria-label="בסיס עובדתי"><h5>בסיס עובדתי</h5>{factualDomains.length ? <ul>{factualDomains.map((domain, index) => <li key={`${String(domain.domain ?? "domain")}-${index}`}><strong>{String(domain.domain ?? "domain")}</strong><pre>{JSON.stringify(domain, null, 2)}</pre></li>)}</ul> : <p>לא אותרו שורות רכיב עובדתי להרצה זו.</p>}</section>
      <table><thead><tr><th>חודש</th><th>תקבולים</th><th>תשלומים</th><th>נטו</th></tr></thead><tbody>{run.monthly_results.map(row => <tr key={row.monthly_result_id}><td>{row.month}</td><td>{row.gross_inflow_total}</td><td>{row.gross_outflow_total}</td><td>{row.period_net}</td></tr>)}</tbody></table></div> : null}
  </section>;
}
