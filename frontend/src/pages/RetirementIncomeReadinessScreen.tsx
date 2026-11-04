import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ReadinessApiError, compareIncome, confirmTarget, readContext, readSourceBases, readTarget,
  saveSourceBasis, type ComparisonResult, type ReadinessContext, type SourceBasisCollection,
  type SourceBasisCommand, type SourceBasisEntry, type TargetResult,
} from "../api/retirementIncomeReadinessApi";
import { formatIsoDate } from "../utils/dateFormat";
import { HebrewDateInput } from "../components/HebrewDateInput";
import * as generationGuard from "./readinessGenerationGuard";

const labels: Record<string, string> = {
  READY: "מוכן", NOT_READY: "אינו מוכן", CURRENT: "נוכחי", STALE: "מיושן ונדרש אישור מחדש",
  MISSING: "חסר", INVALID: "אינו תקין", UNAVAILABLE: "אינו זמין", AMBIGUOUS: "אינו חד-משמעי",
  DIRECTLY_COMPARABLE: "בר-השוואה ישירה", NORMALIZATION_REQUIRED: "נדרשת התאמת בסיס",
  BASIS_UNRESOLVED: "בסיס ההשוואה אינו פתור", NOT_ADMITTED: "לא התקבל להשוואה",
};
const describe = (code: string) => labels[code] ?? "נדרש טיפול מקצועי";

function sourceCanBeUpdated(entry: SourceBasisEntry) {
  if (entry.admission_state === "EXCLUDED" || entry.source_category === "PENSION_REPRESENTATION") return false;
  if (entry.decision_state === "INVALID" || entry.source_version === null) return false;
  if (!entry.source_fingerprint || !entry.amount_authority_fingerprint) return false;
  return entry.source_kind === "PENSION"
    ? typeof entry.source_version === "number"
    : typeof entry.source_version === "string" && entry.source_version === entry.source_fingerprint;
}

function SourceBasisEditor({entry, planningFingerprint, busy, onSave}: {
  entry: SourceBasisEntry;
  planningFingerprint: string;
  busy: boolean;
  onSave: (sourceId: string, command: SourceBasisCommand) => Promise<void>;
}) {
  const [incomeBasis, setIncomeBasis] = useState<"" | "GROSS" | "NET">(
    entry.source_kind === "PENSION" && (entry.income_basis === "GROSS" || entry.income_basis === "NET")
      ? entry.income_basis : "",
  );
  const [priceBasis, setPriceBasis] = useState<"" | "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE">(
    entry.source_kind === "RECURRING_INCOME" && entry.price_basis !== "UNKNOWN" && entry.price_basis !== null
      ? entry.price_basis : "",
  );
  const [referenceDate, setReferenceDate] = useState(entry.price_reference_date ?? "");
  const updatable = sourceCanBeUpdated(entry);
  const cas = updatable ? {
    source_kind: entry.source_kind,
    expected_decision_version: entry.decision_version ?? 0,
    expected_planning_calculation_input_fingerprint: planningFingerprint,
    expected_source_version: entry.source_version as number | string,
    expected_source_fingerprint: entry.source_fingerprint,
    expected_amount_authority_fingerprint: entry.amount_authority_fingerprint as string,
  } : null;

  async function classify(event: FormEvent) {
    event.preventDefault();
    if (!cas) return;
    if (entry.source_kind === "PENSION") {
      if (!incomeBasis) return;
      await onSave(entry.source_id, {
        ...cas, source_kind: "PENSION", schema_version: "CRTISBA_PENSION_CLASSIFY_COMMAND_V1",
        operation: "CLASSIFY", income_basis: incomeBasis,
      });
      return;
    }
    if (!priceBasis || (priceBasis === "REAL_AT_REFERENCE_DATE" && !referenceDate)) return;
    await onSave(entry.source_id, {
      ...cas, source_kind: "RECURRING_INCOME", schema_version: "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1",
      operation: "CLASSIFY", price_basis: priceBasis,
      price_reference_date: priceBasis === "REAL_AT_REFERENCE_DATE" ? referenceDate : null,
    });
  }

  async function clearDecision() {
    if (!cas) return;
    const command: SourceBasisCommand = entry.source_kind === "PENSION"
      ? {...cas, source_kind: "PENSION", schema_version: "CRTISBA_PENSION_CLEAR_COMMAND_V1", operation: "CLEAR"}
      : {...cas, source_kind: "RECURRING_INCOME", schema_version: "CRTISBA_RECURRING_CLEAR_COMMAND_V1", operation: "CLEAR"};
    await onSave(entry.source_id, command);
  }

  return <article aria-labelledby={`source-basis-${entry.source_id}`}>
    <h3 id={`source-basis-${entry.source_id}`}><bdi>{entry.source_id}</bdi></h3>
    <p>סוג מקור: <bdi>{entry.source_kind}</bdi> · קטגוריה: <bdi>{entry.source_category}</bdi></p>
    <p>מצב קבלה: <bdi>{entry.admission_state}</bdi> · מצב החלטה: <bdi>{entry.decision_state}</bdi></p>
    <p>בסיס הכנסה: <bdi>{entry.income_basis ?? "לא נקבע"}</bdi> · בסיס מחירים: <bdi>{entry.price_basis ?? "לא נקבע"}</bdi></p>
    {entry.blockers.map(code => <p key={code}>{describe(code)} <small>{code}</small></p>)}
    {!updatable ? <p>לא ניתן לעדכן החלטה למקור זה לפי מצב הסמכות הנוכחי.</p> :
      <form onSubmit={classify}>
        {entry.source_kind === "PENSION" ?
          <label>בסיס הכנסה למקור <bdi>{entry.source_id}</bdi><select required value={incomeBasis} onChange={event => setIncomeBasis(event.target.value as typeof incomeBasis)}>
            <option value="">יש לבחור</option><option value="GROSS">ברוטו</option><option value="NET">נטו</option>
          </select></label> : <>
          <label>בסיס מחירים למקור <bdi>{entry.source_id}</bdi><select required value={priceBasis} onChange={event => setPriceBasis(event.target.value as typeof priceBasis)}>
            <option value="">יש לבחור</option><option value="NOMINAL_AT_RETIREMENT_TARGET_DATE">נומינלי במועד היעד</option><option value="REAL_AT_REFERENCE_DATE">ריאלי במועד ייחוס</option>
          </select></label>
          {priceBasis === "REAL_AT_REFERENCE_DATE" && <label>תאריך ייחוס למקור <bdi>{entry.source_id}</bdi><HebrewDateInput required value={referenceDate} onChange={setReferenceDate} /></label>}
        </>}
        <button disabled={busy} type="submit">שמירת החלטת בסיס עבור {entry.source_id}</button>
        <button disabled={busy} type="button" onClick={() => void clearDecision()}>ניקוי החלטת בסיס עבור {entry.source_id}</button>
      </form>}
  </article>;
}

function Workspace({clientId}: {clientId: number}) {
  const generation = useRef(0);
  const activeMutation = useRef<AbortController | null>(null);
  const [context, setContext] = useState<ReadinessContext | null>(null);
  const [target, setTarget] = useState<TargetResult | null>(null);
  const [sourceBases, setSourceBases] = useState<SourceBasisCollection | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [amount, setAmount] = useState("");
  const [incomeBasis, setIncomeBasis] = useState<"GROSS" | "NET">("GROSS");
  const [priceBasis, setPriceBasis] = useState<"NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE">("NOMINAL_AT_RETIREMENT_TARGET_DATE");
  const [referenceDate, setReferenceDate] = useState("");
  const [sourceKind, setSourceKind] = useState<"CLIENT_SUPPLIED" | "PLANNER_SUPPLIED" | "CLIENT_SUPPLIED_PLANNER_CONFIRMED">("PLANNER_SUPPLIED");

  async function load(signal?: AbortSignal): Promise<boolean> {
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
      const nextSourceBases = await readSourceBases(clientId, signal);
      if (!generationGuard.generationPolicy.isCurrent(active, generation.current)) return false;
      if (!Array.isArray(nextSourceBases.source_basis_entries)) throw new Error("SOURCE_BASES_INVALID");
      setContext(nextContext); setTarget(nextTarget); setSourceBases(nextSourceBases);
      if (nextTarget.target) {
        setAmount(nextTarget.target.monthly_amount); setIncomeBasis(nextTarget.target.income_basis as "GROSS" | "NET");
        setPriceBasis(nextTarget.target.price_basis as typeof priceBasis); setReferenceDate(nextTarget.target.price_reference_date ?? "");
      }
      return true;
    } catch (reason) {
      if (generationGuard.generationPolicy.isCurrent(active, generation.current) && !(reason instanceof DOMException && reason.name === "AbortError")) setError("טעינת מצב המוכנות נכשלה. יש לרענן במפורש.");
      return false;
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
      if (!generationGuard.generationPolicy.isCurrent(active, generation.current)) return;
      setBusy(false); setContext(null); setTarget(null); setComparison(null); await load();
    } catch (reason) { if (generationGuard.generationPolicy.isCurrent(active, generation.current) && !(reason instanceof DOMException && reason.name === "AbortError")) setError("האישור לא נשמר. במקרה של שינוי מקביל יש לרענן לפני ניסיון נוסף."); }
    finally { if (generationGuard.generationPolicy.isCurrent(active, generation.current)) setBusy(false); }
  }

  async function compare() {
    if (!context?.retirement_target_date || !sourceBases) return;
    activeMutation.current?.abort(); const controller = new AbortController(); activeMutation.current = controller;
    const active = ++generation.current;
    setBusy(true); setError("");
    try { const result = await compareIncome(clientId, {expected_planning_calculation_input_fingerprint: context.planning_calculation_input_fingerprint, expected_retirement_target_date: context.retirement_target_date}, controller.signal); if (generationGuard.generationPolicy.isCurrent(active, generation.current)) setComparison(result); }
    catch (reason) { if (generationGuard.generationPolicy.isCurrent(active, generation.current) && !(reason instanceof DOMException && reason.name === "AbortError")) setError("בדיקת בסיסי ההשוואה נכשלה. יש לנסות שוב במפורש לאחר רענון."); }
    finally { if (generationGuard.generationPolicy.isCurrent(active, generation.current)) setBusy(false); }
  }

  async function saveBasis(sourceId: string, command: SourceBasisCommand) {
    activeMutation.current?.abort(); const controller = new AbortController(); activeMutation.current = controller;
    const active = ++generation.current;
    setBusy(true); setError("");
    try {
      await saveSourceBasis(clientId, sourceId, command, controller.signal);
      if (!generationGuard.generationPolicy.isCurrent(active, generation.current)) return;
      setComparison(null); setSourceBases(null); await load();
    } catch (reason) {
      if (!generationGuard.generationPolicy.isCurrent(active, generation.current) || (reason instanceof DOMException && reason.name === "AbortError")) return;
      const unknownOutcome = !(reason instanceof ReadinessApiError)
        || reason.code === "CRTISBA_COMMIT_OUTCOME_UNKNOWN";
      if (unknownOutcome) {
        setComparison(null); setSourceBases(null);
        const refresh = load();
        const refreshGeneration = generation.current;
        const refreshed = await refresh;
        if (!generationGuard.generationPolicy.isCurrent(refreshGeneration, generation.current)) return;
        setError(refreshed
          ? "לא ניתן לקבוע אם ההחלטה נשמרה. יש לרענן ולבדוק את מצב הסמכות לפני ניסיון נוסף."
          : "לא ניתן לקבוע אם ההחלטה נשמרה. יש לרענן ולבדוק את מצב הסמכות לפני ניסיון נוסף. רענון הסמכות נכשל; נדרש רענון מפורש.");
        return;
      }
      if (reason instanceof ReadinessApiError && reason.status === 409) {
        setComparison(null); setSourceBases(null);
        const refresh = load();
        const refreshGeneration = generation.current;
        const refreshed = await refresh;
        if (!generationGuard.generationPolicy.isCurrent(refreshGeneration, generation.current)) return;
        setError(refreshed
          ? `החלטת המקור לא נשמרה (${reason.code}). נתוני הסמכות רועננו; יש לבדוק אותם לפני ניסיון נוסף.`
          : `החלטת המקור לא נשמרה (${reason.code}). רענון הסמכות נכשל; נדרש רענון מפורש.`);
      } else {
        setError("החלטת המקור לא נשמרה. יש לרענן את נתוני הסמכות לפני ניסיון נוסף.");
      }
    } finally { setBusy(false); }
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
        <button disabled={busy || !target.target_ready || !sourceBases} onClick={() => void compare()}>בדיקת בסיסי ההשוואה</button></section>
      <section><h2>החלטות בסיס למקורות הכנסה</h2>
        {!sourceBases ? <p>טוען החלטות מקור…</p> : sourceBases.source_basis_entries.length === 0 ? <p>לא נמצאו מקורות הכנסה להחלטת בסיס.</p> :
          sourceBases.source_basis_entries.map(entry => <SourceBasisEditor
            key={`${entry.source_id}:${entry.decision_version}:${entry.decision_fingerprint}`}
            entry={entry} planningFingerprint={sourceBases.planning_calculation_input_fingerprint}
            busy={busy} onSave={saveBasis}
          />)}
      </section>
      {comparison && <section><h2>תוצאת בדיקת בסיסי השוואה</h2>{comparison.result_state === "block_no_result" ? <p>לא הופקה תוצאה: {comparison.failure_stage} · <bdi>{comparison.failure_detail_code}</bdi></p> : <>
        <p>{comparison.direct_comparison_ready ? "בסיס ההשוואה מוכן" : "בסיס ההשוואה אינו מוכן"}</p>
        {comparison.blockers?.map(code => <p key={code}>{describe(code)} <small>{code}</small></p>)}
        {comparison.source_comparisons.map(item => <article key={item.source_id}><h3><bdi>{item.source_id}</bdi></h3>
          <p>{describe(item.comparison_state)} <small>{item.comparison_state}</small> · {describe(item.admission_state)} <small>{item.admission_state}</small> · {describe(item.decision_state)} <small>{item.decision_state}</small></p>
          <p>סוג מקור: <bdi>{item.source_kind}</bdi> · קטגוריה: <bdi>{item.source_category}</bdi></p>
          <p>בסיס הכנסה: <bdi>{item.income_basis ?? "לא נקבע"}</bdi> · מקור סמכות: <bdi>{item.income_basis_provenance ?? "לא נקבע"}</bdi></p>
          <p>בסיס מחירים: <bdi>{item.price_basis ?? "לא נקבע"}</bdi> · תאריך ייחוס: <bdi>{item.price_reference_date ?? "לא נקבע"}</bdi> · מקור סמכות: <bdi>{item.price_basis_provenance ?? "לא נקבע"}</bdi></p>
          {item.reason_codes.map((code, index) => <p key={`${code}:${index}`}>{describe(code)} <small>{code}</small></p>)}</article>)}</>}</section>}
    </>}
  </main>;
}

export function RetirementIncomeReadinessScreen() {
  const clientId = Number(useParams().clientId);
  return Number.isSafeInteger(clientId) && clientId > 0 ? <Workspace key={generationGuard.generationPolicy.workspaceKey(clientId)} clientId={clientId} /> : <p role="alert">מזהה לקוח אינו תקין</p>;
}
