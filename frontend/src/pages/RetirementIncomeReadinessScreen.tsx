import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { compareIncome, confirmTarget, readContext, readTarget, type ComparisonResult, type ReadinessContext, type TargetResult } from "../api/retirementIncomeReadinessApi";
import { formatIsoDate } from "../utils/dateFormat";
import { HebrewDateInput } from "../components/HebrewDateInput";

const labels: Record<string, string> = {
  READY: "מוכן", NOT_READY: "אינו מוכן", CURRENT: "נוכחי", STALE: "מיושן ונדרש אישור מחדש",
  MISSING: "חסר", INVALID: "אינו תקין", UNAVAILABLE: "אינו זמין", AMBIGUOUS: "אינו חד-משמעי",
  DIRECTLY_COMPARABLE: "בר-השוואה ישירה", NORMALIZATION_REQUIRED: "נדרשת התאמת בסיס",
  BASIS_UNRESOLVED: "בסיס ההשוואה אינו פתור", NOT_ADMITTED: "לא התקבל להשוואה",
};
const describe = (code: string) => labels[code] ?? "נדרש טיפול מקצועי";

function Workspace({clientId}: {clientId: number}) {
  const generation = useRef(0);
  const activeMutation = useRef<AbortController | null>(null);
  const [context, setContext] = useState<ReadinessContext | null>(null);
  const [target, setTarget] = useState<TargetResult | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [amount, setAmount] = useState("");
  const [incomeBasis, setIncomeBasis] = useState<"GROSS" | "NET">("GROSS");
  const [priceBasis, setPriceBasis] = useState<"NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE">("NOMINAL_AT_RETIREMENT_TARGET_DATE");
  const [referenceDate, setReferenceDate] = useState("");
  const [sourceKind, setSourceKind] = useState<"CLIENT_SUPPLIED" | "PLANNER_SUPPLIED" | "CLIENT_SUPPLIED_PLANNER_CONFIRMED">("PLANNER_SUPPLIED");

  async function load(signal?: AbortSignal) {
    if (!signal) {
      activeMutation.current?.abort();
      const controller = new AbortController();
      activeMutation.current = controller;
      signal = controller.signal;
    }
    const active = ++generation.current;
    setError(""); setComparison(null);
    try {
      const nextContext = await readContext(clientId, signal);
      const nextTarget = await readTarget(clientId, signal);
      if (active !== generation.current) return;
      setContext(nextContext); setTarget(nextTarget);
      if (nextTarget.target) {
        setAmount(nextTarget.target.monthly_amount); setIncomeBasis(nextTarget.target.income_basis as "GROSS" | "NET");
        setPriceBasis(nextTarget.target.price_basis as typeof priceBasis); setReferenceDate(nextTarget.target.price_reference_date ?? "");
      }
    } catch (reason) {
      if (active === generation.current && !(reason instanceof DOMException && reason.name === "AbortError")) setError("טעינת מצב המוכנות נכשלה. יש לרענן במפורש.");
    }
  }
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => { generation.current += 1; controller.abort(); activeMutation.current?.abort(); }; }, [clientId]);

  async function save(event: FormEvent) {
    event.preventDefault(); if (!context || !target) return;
    activeMutation.current?.abort(); const controller = new AbortController(); activeMutation.current = controller;
    const active = ++generation.current;
    setBusy(true); setError("");
    try {
      await confirmTarget(clientId, {
        expected_record_version: target.authority?.record_version ?? 0,
        expected_planning_calculation_input_fingerprint: context.planning_calculation_input_fingerprint,
        expected_retirement_target_date: context.retirement_target_date,
        monthly_amount: amount, income_basis: incomeBasis, price_basis: priceBasis,
        price_reference_date: priceBasis === "REAL_AT_REFERENCE_DATE" ? referenceDate : null,
        source_kind: sourceKind,
      }, controller.signal);
      if (active !== generation.current) return;
      setBusy(false); setContext(null); setTarget(null); setComparison(null); await load();
    } catch (reason) { if (active === generation.current && !(reason instanceof DOMException && reason.name === "AbortError")) setError("האישור לא נשמר. במקרה של שינוי מקביל יש לרענן לפני ניסיון נוסף."); }
    finally { if (active === generation.current) setBusy(false); }
  }

  async function compare() {
    if (!context?.retirement_target_date) return;
    activeMutation.current?.abort(); const controller = new AbortController(); activeMutation.current = controller;
    const active = ++generation.current;
    setBusy(true); setError("");
    try { const result = await compareIncome(clientId, {expected_planning_calculation_input_fingerprint: context.planning_calculation_input_fingerprint, expected_retirement_target_date: context.retirement_target_date}, controller.signal); if (active === generation.current) setComparison(result); }
    catch (reason) { if (active === generation.current && !(reason instanceof DOMException && reason.name === "AbortError")) setError("בדיקת בסיס ההשוואה נכשלה. יש לנסות שוב במפורש לאחר רענון."); }
    finally { if (active === generation.current) setBusy(false); }
  }

  return <main dir="rtl"><h1>מוכנות הכנסה במועד היעד לפרישה</h1>
    <p>בדיקת סמכויות ובסיסי השוואה בלבד — ללא סכימה, פער, מימון, מס או תרחיש.</p>
    <Link to={`/clients/${clientId}/planning-input`}>חזרה לקלט התכנון</Link>
    {error && <p role="alert">{error}</p>}<button disabled={busy} onClick={() => void load()}>רענון מפורש</button>
    {!context || !target ? <p>טוען נתונים…</p> : <>
      <section><h2>הקשר התכנון</h2><p>{context.planning_input_ready ? "קלט התכנון מוכן" : "קלט התכנון אינו מוכן"}</p>
        <p>תאריך יעד: {formatIsoDate(context.retirement_target_date) || "לא נקבע"}</p>
        {context.blocking_facts.map((item, index) => <p key={`${item.source_id}:${item.code}:${index}`}>{describe(item.code)} <small>{item.source_id}</small></p>)}</section>
      <section><h2>יעד הכנסה חודשי</h2><p>מצב סמכות: {describe(target.authority_state)} · {describe(target.target_readiness_state)}</p>
        {target.blockers.map(code => <p key={code}>{describe(code)} <small>{code}</small></p>)}
        <form onSubmit={save}><label>סכום חודשי<input dir="ltr" required value={amount} onChange={e => setAmount(e.target.value)} /></label>
          <label>בסיס הכנסה<select value={incomeBasis} onChange={e => setIncomeBasis(e.target.value as typeof incomeBasis)}><option value="GROSS">ברוטו</option><option value="NET">נטו</option></select></label>
          <label>בסיס מחירים<select value={priceBasis} onChange={e => setPriceBasis(e.target.value as typeof priceBasis)}><option value="NOMINAL_AT_RETIREMENT_TARGET_DATE">נומינלי במועד היעד</option><option value="REAL_AT_REFERENCE_DATE">ריאלי במועד ייחוס</option></select></label>
          {priceBasis === "REAL_AT_REFERENCE_DATE" && <label>תאריך ייחוס<HebrewDateInput required value={referenceDate} onChange={setReferenceDate} /></label>}
          <label>מקור האישור<select value={sourceKind} onChange={e => setSourceKind(e.target.value as typeof sourceKind)}><option value="PLANNER_SUPPLIED">הוזן בידי המתכנן</option><option value="CLIENT_SUPPLIED">נמסר בידי הלקוח</option><option value="CLIENT_SUPPLIED_PLANNER_CONFIRMED">נמסר ואושר בידי המתכנן</option></select></label>
          <button disabled={busy || !context.retirement_target_date} type="submit">אישור מפורש של היעד</button></form>
        <button disabled={busy || !target.target_ready} onClick={() => void compare()}>בדיקת בסיסי ההשוואה</button></section>
      {comparison && <section><h2>תוצאת בדיקת בסיסי השוואה</h2>{comparison.result_state === "block_no_result" ? <p>לא הופקה תוצאה: {comparison.failure_stage} · <bdi>{comparison.failure_detail_code}</bdi></p> : <>
        <p>{comparison.direct_comparison_ready ? "בסיס ההשוואה מוכן" : "בסיס ההשוואה אינו מוכן"}</p>
        {comparison.blockers?.map(code => <p key={code}>{describe(code)} <small>{code}</small></p>)}
        {comparison.source_comparisons?.map(item => <article key={item.source_id}><h3><bdi>{item.source_id}</bdi></h3><p>{describe(item.comparison_state)} · {describe(item.rtisa_admission_state)}</p>{item.reason_codes.map(code => <p key={code}>{describe(code)} <small>{code}</small></p>)}</article>)}</>}</section>}
    </>}
  </main>;
}

export function RetirementIncomeReadinessScreen() {
  const clientId = Number(useParams().clientId);
  return Number.isSafeInteger(clientId) && clientId > 0 ? <Workspace key={clientId} clientId={clientId} /> : <p role="alert">מזהה לקוח אינו תקין</p>;
}
