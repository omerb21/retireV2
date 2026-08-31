import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { HebrewDateInput } from "../components/HebrewDateInput";
import { formatIsoDate } from "../utils/dateFormat";
import { heBoolean, heLabel } from "../i18n/he";
import {
  correctM06Coefficient, getM06Eligibility, getM06History, getM06Subject, listM06Candidates, listM06Subjects,
  resolveM06, reviewM06Warnings, startM06, supersedeM06, type CoefficientIntent,
  type M06Authority, type M06Candidate, type M06Revision, type M06Subject,
} from "../api/m06ConversionApi";

const message = (error: unknown) => error instanceof Error ? error.message : "בקשת M06 נכשלה";

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
  const [applies, setApplies] = useState(false); const [error, setError] = useState<string | null>(null); const [busyCount, setBusyCount] = useState(0);
  const mounted = useRef(false); const overviewEpoch = useRef(0); const detailEpoch = useRef(0); const mutationEpoch = useRef(0); const requestSequence = useRef(0); const activeLoading = useRef(new Set<number>());
  const selectedSubject = useRef<string | null>(null); const selectedRevision = useRef<string | null>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; overviewEpoch.current++; detailEpoch.current++; mutationEpoch.current++; activeLoading.current.clear(); }; }, []);
  useEffect(() => { overviewEpoch.current++; detailEpoch.current++; mutationEpoch.current++; activeLoading.current.clear(); selectedSubject.current = null; selectedRevision.current = null; setCandidates([]); setSubjects([]); setSelected(null); setDetail(null); setHistory([]); setAuthority("planner_declared"); setCoefficient(""); setSourceIntake(""); setLocator(""); setNote(""); setReason(""); setActionReason(""); setEffectiveFrom(""); setEffectiveTo(""); setApplies(false); setSourceVersion(""); setIssuerProvider(""); setAge(""); setGender(""); setPensionOption(""); setGuaranteePeriod(""); setSurvivorOption(""); setError(null); setBusyCount(0); }, [clientId, location.key]);

  const beginLoading = () => { const id = ++requestSequence.current; activeLoading.current.add(id); setBusyCount(activeLoading.current.size); return id; };
  const finishLoading = (id: number) => { if (activeLoading.current.delete(id) && mounted.current) setBusyCount(activeLoading.current.size); };

  const loadOverview = useCallback(async () => {
    if (clientId === null) return; const token = captureClientContext(); const epoch = ++overviewEpoch.current;
    const owned = () => mounted.current && epoch === overviewEpoch.current && isCurrentClientContext(token);
    const loading = beginLoading(); try { const [nextCandidates, nextSubjects] = await Promise.all([listM06Candidates(clientId), listM06Subjects(clientId)]); if (owned()) { setCandidates(nextCandidates); setSubjects(nextSubjects); } } catch (cause) { if (owned()) setError(message(cause)); } finally { finishLoading(loading); }
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadOverview(); }, [loadOverview]);

  const loadDetail = useCallback(async (id: string, successorRevision?: string) => {
    if (clientId === null) return; const token = captureClientContext(); const epoch = ++detailEpoch.current; if (!successorRevision) mutationEpoch.current++; selectedSubject.current = id; if (!successorRevision) selectedRevision.current = null;
    const owned = () => mounted.current && epoch === detailEpoch.current && selectedSubject.current === id && isCurrentClientContext(token);
    const loading = beginLoading(); try { const [next, trail, nextEligibility] = await Promise.all([getM06Subject(clientId, id), getM06History(clientId, id), getM06Eligibility(clientId, id)]); if (owned() && (!successorRevision || next.current_revision?.revision_id === successorRevision)) { selectedRevision.current = next.current_revision?.revision_id ?? null; setDetail({ ...next, eligibility: nextEligibility }); setHistory(trail); } } catch (cause) { if (owned()) setError(message(cause)); } finally { finishLoading(loading); }
  }, [captureClientContext, clientId, isCurrentClientContext]);

  const intent = (): CoefficientIntent => ({ authority_class: authority, coefficient, ...(authority === "documentary" ? { source_intake_id: sourceIntake, source_locator: locator } : { source_note: note }), reason, ...(effectiveFrom ? { effective_from: effectiveFrom } : {}), ...(effectiveTo ? { effective_to: effectiveTo } : {}), applicability_declared: applies, metadata: { ...(sourceVersion ? { source_version: sourceVersion } : {}), ...(issuerProvider ? { issuer_provider: issuerProvider } : {}), ...(age ? { age: Number(age) } : {}), ...(gender ? { gender } : {}), ...(pensionOption ? { pension_option: pensionOption } : {}), ...(guaranteePeriod ? { guarantee_period: guaranteePeriod } : {}), ...(survivorOption ? { survivor_option: survivorOption } : {}) } });
  const mutate = async (operation: () => Promise<M06Revision>) => {
    if (clientId === null) return; const token = captureClientContext(); const subjectId = selectedSubject.current; const revisionId = selectedRevision.current; const epoch = ++mutationEpoch.current;
    const owned = () => mounted.current && epoch === mutationEpoch.current && selectedSubject.current === subjectId && selectedRevision.current === revisionId && isCurrentClientContext(token);
    const loading = beginLoading(); setError(null); try { const result = await operation(); if (!owned()) return; selectedSubject.current = result.subject_id; selectedRevision.current = result.revision_id; await Promise.all([loadOverview(), loadDetail(result.subject_id, result.revision_id)]); } catch (cause) { if (owned()) setError(message(cause)); } finally { finishLoading(loading); }
  };
  if (clientId === null) return <p role="alert">מזהה הלקוח אינו תקין.</p>;
  const current = detail?.current_revision ?? null; const warningIds = current?.warnings.filter((item) => item.classification === "mandatory").map((item) => item.warning_id) ?? [];
  return <main><h2>M06 — המרת פנסיה והון</h2>
    <p>זהו תיעוד המרה טכני תחום, ואינו סמכות מקצועית, פיננסית או מיסויית.</p><p><Link to={`/clients/${clientId}`}>חזרה ללקוח</Link></p>
    {error ? <p role="alert">{error}</p> : null}{busyCount > 0 ? <p>טוען נתוני M06…</p> : null}
    <section><h3>נתוני קלט כשירים מהשלב הקודם</h3>{candidates.length ? <ul>{candidates.map((row) => <li key={row.candidate_id}><button type="button" onClick={() => setSelected(row)}>{row.provider_name} / {row.account_reference} / {heLabel(row.mode)}</button> — {row.formula_id}; סכום {row.input_amount ?? "חסר"}; תאריך {formatIsoDate(row.input_date) || "חסר"}; כשיר {heBoolean(row.eligible)}</li>)}</ul> : <p>אין רשומות מועמדות ל־M06.</p>}
      {selected ? <div><h4>אסמכתה למקדם ותחולתו</h4><p>נוסחה: {selected.formula_id}. הקלט והתוצאה נגזרים בשרת ואינם ניתנים לעריכה.</p>
        <label>סוג סמכות <select aria-label="סוג סמכות" value={authority} onChange={(e) => setAuthority(e.target.value as M06Authority)}><option value="planner_declared">הצהרת מתכנן</option><option value="documentary">אסמכתה תיעודית</option></select></label>
        <label>מקדם מדויק <input aria-label="מקדם מדויק" value={coefficient} onChange={(e) => setCoefficient(e.target.value)} /></label>
        {authority === "documentary" ? <><label>קליטת מקור מאושרת <input aria-label="קליטת מקור מאושרת" value={sourceIntake} onChange={(e) => setSourceIntake(e.target.value)} /></label><label>מיקום מדויק במקור <input aria-label="מיקום מדויק במקור" value={locator} onChange={(e) => setLocator(e.target.value)} /></label></> : <label>הערת מקור של המתכנן <textarea aria-label="הערת מקור של המתכנן" value={note} onChange={(e) => setNote(e.target.value)} /></label>}
        <label>נימוק לאסמכתת המקדם <textarea aria-label="נימוק לאסמכתת המקדם" value={reason} onChange={(e) => setReason(e.target.value)} /></label><label>בתוקף מתאריך <HebrewDateInput value={effectiveFrom} onChange={setEffectiveFrom} /></label><label>בתוקף עד תאריך <HebrewDateInput value={effectiveTo} onChange={setEffectiveTo} /></label>
        <fieldset><legend>מאפייני המקדם שבהם נעשה שימוש בפועל (רשות)</legend><label>גרסת מקור <input value={sourceVersion} onChange={(e) => setSourceVersion(e.target.value)} /></label><label>מנפיק או גוף מנהל <input value={issuerProvider} onChange={(e) => setIssuerProvider(e.target.value)} /></label><label>גיל <input type="number" min="0" max="130" value={age} onChange={(e) => setAge(e.target.value)} /></label><label>מאפיין מגדר <input value={gender} onChange={(e) => setGender(e.target.value)} /></label><label>אפשרות קצבה <input value={pensionOption} onChange={(e) => setPensionOption(e.target.value)} /></label><label>תקופת הבטחה <input value={guaranteePeriod} onChange={(e) => setGuaranteePeriod(e.target.value)} /></label><label>אפשרות לשאירים <input value={survivorOption} onChange={(e) => setSurvivorOption(e.target.value)} /></label></fieldset>
        <label><input type="checkbox" checked={applies} onChange={(e) => setApplies(e.target.checked)} /> הצהרה על תחולה בתאריך הקלט המוצג</label>
        <button aria-label="יצירת טיוטה בלתי ניתנת לשינוי" disabled={busyCount > 0 || !coefficient || !reason} onClick={() => void mutate(() => startM06(clientId, selected, intent()))}>יצירת טיוטה בלתי ניתנת לשינוי</button></div> : null}</section>
    <section><h3>המרות קיימות</h3>{subjects.length ? <ul>{subjects.map((row) => <li key={row.subject_id}><button onClick={() => void loadDetail(row.subject_id)}>{heLabel(row.mode)} / {row.input_identity}</button> — {heLabel(row.current_revision?.state)}; כשירות להמשך {heBoolean(row.eligibility.eligible_for_downstream)}</li>)}</ul> : <p>אין המרות קיימות.</p>}</section>
    {current ? <section><h3>גרסת ההמרה הנוכחית</h3><p>גרסה {current.revision_sequence}: {heLabel(current.state)}; {current.formula_id}; קלט {current.input_amount ?? "חסר"}; מקדם {current.coefficient.coefficient} ({heLabel(current.coefficient.authority_class)}).</p><p>הגורם {current.actor} הוא תיעוד תפעולי ולא אישור.</p><p>אזהרות: {warningIds.join(", ") || "אין"}; חסמים: {current.blocking_reasons.join(", ") || "אין"}.</p>
      {current.manifest ? <><p>ערך גולמי: {current.manifest.raw_result_kind === "exact_ratio" ? `${current.manifest.raw_numerator}/${current.manifest.raw_denominator}` : current.manifest.raw_decimal}; מוצג: {current.manifest.display_result}; טביעת אצבע: {current.manifest.fingerprint}.</p><details><summary>מניפסט מקור בלתי ניתן לשינוי</summary><pre>{JSON.stringify(current.manifest.evidence, null, 2)}</pre></details></> : <p>לא קיימת תוצאת חישוב לגרסה זו.</p>}
      <p>כשירות טכנית להמשך: {heBoolean(detail?.eligibility.eligible_for_downstream ?? false)}; החרגות: {detail?.eligibility.exclusion_reasons.join(", ") || "אין"}.</p>
      <label>נימוק לפעולה או הסבר לאזהרה <textarea value={actionReason} onChange={(e) => setActionReason(e.target.value)} /></label>
      <button disabled={busyCount > 0 || current.state !== "draft" || current.action_type === "resolve"} onClick={() => void mutate(() => resolveM06(clientId, current.subject_id, current.revision_id))}>פתרון הנוסחה המדויקת</button>
      <button disabled={busyCount > 0 || current.state !== "draft" || current.action_type !== "resolve" || warningIds.length === 0 || !actionReason} onClick={() => void mutate(() => reviewM06Warnings(clientId, current.subject_id, current.revision_id, warningIds, actionReason))}>בדיקת קבוצת אזהרות החובה</button>
      <button aria-label="הוספת טיוטת מקדם מתוקנת" disabled={busyCount > 0 || !coefficient || !reason || !actionReason || current.state === "superseded"} onClick={() => void mutate(() => correctM06Coefficient(clientId, current.subject_id, current.revision_id, intent(), actionReason))}>הוספת טיוטת מקדם מתוקנת</button>
      <button disabled={busyCount > 0 || !actionReason || current.state === "superseded"} onClick={() => void mutate(() => supersedeM06(clientId, current.subject_id, current.revision_id, actionReason))}>החלפת ההמרה הנוכחית</button>
    </section> : null}
    {history.length ? <section><h3 aria-label="היסטוריה בלתי ניתנת לשינוי">היסטוריה בלתי ניתנת לשינוי</h3><ol>{history.map((row) => <li key={row.revision_id}>#{row.revision_sequence} {heLabel(row.state)}; {heLabel(row.action_type)}; {row.revision_id}; תוצאה {row.manifest?.display_result ?? "אין"}</li>)}</ol></section> : null}
  </main>;
}
