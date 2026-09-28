import { useEffect, useRef, useState, type FormEvent } from "react";
import { createManualPension, getSourceSnapshot, supersedeManualPension, updateManualPension, type ManualInput, type PensionSource, type SourceSnapshot } from "../api/professionalSourceApi";
import { HebrewDateInput } from "./HebrewDateInput";
import { formatIsoDate } from "../utils/dateFormat";
import { taxLabel } from "../api/canonicalConversionsApi";

const factLabels: Record<string, string> = {
  BASE_AMOUNT_EFFECTIVE_DATE_MISSING: "חסר תאריך נכונות לסכום הבסיס החודשי",
  ENTERED_MONTHLY_AMOUNT_MISSING: "חסר סכום בסיס חודשי", ENTERED_MONTHLY_AMOUNT_NOT_POSITIVE: "נדרש סכום בסיס חודשי חיובי",
  MANUAL_BALANCE_MISSING: "חסרה יתרת בסיס", MANUAL_BALANCE_NOT_POSITIVE: "נדרשת יתרת בסיס חיובית",
  MANUAL_ANNUITY_FACTOR_MISSING: "חסר מקדם קצבה", MANUAL_ANNUITY_FACTOR_INVALID: "מקדם הקצבה אינו תקין",
  MANUAL_ANNUITY_FACTOR_NOT_POSITIVE: "נדרש מקדם קצבה חיובי",
  monthly_amount_not_positive: "נדרש סכום קצבה חודשי חיובי", balance_not_positive: "נדרשת יתרה חיובית",
  fixed_indexation_rate_not_positive: "נדרש שיעור הצמדה קבוע חיובי",
  monthly_amount_missing: "חסר סכום קצבה חודשי", balance_missing: "חסרה יתרה", annuity_factor_missing: "חסר מקדם קצבה",
  payer_name_missing: "חסר שם משלם", pension_start_date_missing: "חסר תאריך תחילת קצבה",
  tax_treatment_missing_or_unsupported: "זהות המס חסרה או אינה נתמכת לחישוב מס פנסיוני",
  indexation_method_missing_or_unsupported: "שיטת ההצמדה חסרה או אינה נתמכת", fixed_indexation_rate_missing: "חסר שיעור הצמדה קבוע",
  potential_duplicate_source: "חשד לכפילות מקור — נדרשת בדיקת אסמכתאות", known_value_missing: "חסר שווי ידוע",
  birth_date_missing: "חסר תאריך לידה לחישובי המשך", gender_missing: "חסר מגדר לחישובי המשך",
  employment_facts_missing: "חסרות עובדות תעסוקה לחישובי המשך", retirement_date_facts_missing: "חסרים תאריכי פרישה לחישובי המשך",
};
const empty: ManualInput = { input_mode: "entered", payer_name: null, description: null, source_reference: null,
  monthly_amount: null, balance: null, annuity_factor: null, pension_start_date: null, tax_treatment: null,
  base_amount_effective_date: null,
  indexation_method: null, fixed_indexation_rate: null, source_note: null };
const shown = (value: string | null | undefined) => value ?? "לא תועד";
function Facts({ codes }: { codes: string[] }) {
  return <ul>{codes.map(code => <li key={code}>{factLabels[code] ?? "נתון מקור דורש בדיקה"}</li>)}</ul>;
}

export function ProfessionalSourceSnapshot({ clientId, readOnly = false }: { clientId: number; readOnly?: boolean }) {
  return <SourceWorkspace key={clientId} clientId={clientId} readOnly={readOnly} />;
}

function SourceWorkspace({ clientId, readOnly }: { clientId: number; readOnly: boolean }) {
  const [data, setData] = useState<SourceSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [editing, setEditing] = useState<PensionSource | "new" | null>(null);
  const [draft, setDraft] = useState<ManualInput>(empty);
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    const controller = new AbortController(); let current = true;
    setLoading(true); setData(null); setError("");
    getSourceSnapshot(clientId, controller.signal).then(value => {
      if (current) {
        if (value.client_id !== clientId) { setError("שיוך תמונת המקורות ללקוח אינו תקין"); return; }
        setData(value);
      }
    }).catch(() => { if (current) setError("לא ניתן לטעון את תמונת המקורות. יש לנסות שוב."); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [clientId, refresh]);
  const begin = (source: PensionSource | "new") => {
    setEditing(source);
    setDraft(source === "new" ? { ...empty } : Object.fromEntries(Object.keys(empty).map(key => [key, source[key as keyof ManualInput] ?? null])) as unknown as ManualInput);
  };
  const mutate = async (operation: () => Promise<unknown>) => {
    setBusy(true); setError("");
    try { await operation(); if (alive.current) { setEditing(null); setRefresh(n => n + 1); } }
    catch (failure) { if (alive.current) setError(failure instanceof Error ? failure.message : "הפעולה נכשלה"); }
    finally { if (alive.current) setBusy(false); }
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    const payload = { ...draft, ...(draft.input_mode === "entered" ? { balance: null, annuity_factor: null } : { monthly_amount: null }) };
    void mutate(() => editing === "new" ? createManualPension(clientId, payload)
      : updateManualPension(clientId, editing.manual_pension_source_id!, { ...payload, expected_version: editing.version }));
  };
  const field = (key: keyof ManualInput, label: string) => <label>{label}<input aria-label={label} value={draft[key] ?? ""}
    onChange={event => setDraft(previous => ({ ...previous, [key]: event.target.value || null }))} /></label>;
  return <section dir="rtl" aria-label="תמונת מקורות פנסיוניים ופיננסיים">
    <h3>תמונת מקורות פנסיוניים ופיננסיים</h3>
    <p>מקורות נוכחיים בלבד — ללא תחזית, חישוב מס או סכום כספי מצטבר.</p>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">טוען תמונת מקורות…</p>}
    {!readOnly && <button disabled={busy || loading} onClick={() => begin("new")}>הוספת קצבה ידנית</button>}
    <button disabled={busy} onClick={() => setRefresh(n => n + 1)}>רענון תמונת המקורות</button>
    {editing && !readOnly && <form onSubmit={submit}>
      <fieldset disabled={busy}><legend>{editing === "new" ? "קצבה ידנית חדשה" : "עריכת קצבה ידנית"}</legend>
        <label>מצב קלט<select aria-label="מצב קלט" value={draft.input_mode} onChange={e => setDraft(v => ({ ...v, input_mode: e.target.value as ManualInput["input_mode"] }))}>
          <option value="entered">סכום חודשי מוזן</option><option value="calculated">יתרה חלקי מקדם</option></select></label>
        {field("payer_name", "שם משלם")}{field("description", "תיאור המקור")}{field("source_reference", "אסמכתת מקור")}
        {draft.input_mode === "entered" ? field("monthly_amount", "סכום חודשי מדויק") : <>{field("balance", "יתרת מקור")}{field("annuity_factor", "מקדם חיובי")}</>}
        <label>תאריך תחילת קצבה<HebrewDateInput ariaLabel="תאריך תחילת קצבה" value={draft.pension_start_date ?? ""} onChange={v => setDraft(p => ({ ...p, pension_start_date: v || null }))} /></label>
        <label>תאריך נכונות סכום הבסיס החודשי<HebrewDateInput ariaLabel="תאריך נכונות סכום הבסיס החודשי" value={draft.base_amount_effective_date ?? ""} onChange={v => setDraft(p => ({ ...p, base_amount_effective_date: v || null }))} /></label>
        <label>זהות מס<select aria-label="זהות מס" value={draft.tax_treatment ?? ""} onChange={e => setDraft(v => ({ ...v, tax_treatment: e.target.value || null }))}>
          <option value="">לא תועד</option><option value="taxable">חייב במס</option><option value="exempt">פטור ממס</option><option value="capital_gains">מס רווחי הון — לא מאושר לחישוב מס פנסיוני</option>
          {draft.tax_treatment && !["taxable", "exempt", "capital_gains"].includes(draft.tax_treatment) && <option value={draft.tax_treatment}>סיווג לא נתמך שנשמר במקור</option>}
        </select></label>
        <label>שיטת הצמדה<select aria-label="שיטת הצמדה" value={draft.indexation_method ?? ""} onChange={e => setDraft(v => ({ ...v, indexation_method: e.target.value || null }))}>
          <option value="">לא תועד</option><option value="none">ללא הצמדה</option><option value="cpi">מדד</option><option value="fixed">שיעור קבוע</option>
          {draft.indexation_method && !["none", "cpi", "fixed"].includes(draft.indexation_method) && <option value={draft.indexation_method}>שיטת הצמדה לא נתמכת שנשמרה במקור</option>}
        </select></label>
        {draft.indexation_method === "fixed" && field("fixed_indexation_rate", "שיעור הצמדה קבוע")}
        {field("source_note", "הערת מקור")}<p>אפשר לשמור מידע חסר; הוא לא יסומן כמוכן לחישוב.</p>
        <button type="submit">שמירת קצבה ידנית</button><button type="button" onClick={() => setEditing(null)}>ביטול עריכה</button>
      </fieldset>
    </form>}
    {data && <>
      <Facts codes={data.client_fact_warnings} />
      <h4>יתרות מקור שטרם הומרו</h4>
      {data.pension_products.length === 0 && <p>לא תועדו מוצרים פנסיוניים.</p>}
      {data.pension_products.map(p => <article key={p.product_id}><h5>{p.product_name}</h5>
        <p>גוף מנהל: {shown(p.provider_name)} · חשבון: {p.account_reference} · תאריך דוח: {formatIsoDate(p.statement_date) || "לא תועד"}</p>
        <ul>{p.components.map(c => <li key={c.component_id}>{c.component_code.replace(/_/g, " ")}: <bdi>{c.balance}</bdi></li>)}</ul>
        <p>נתוני בקרה והתאמה בלבד — אינם יתרה כספית נוכחית: סך מוצר מדווח {shown(p.reported_controls.reported_product_total)}; תגמולים {shown(p.reported_controls.reported_rewards_total)}; פיצויים {shown(p.reported_controls.reported_severance_total)}.</p>
      </article>)}
      <h4>מקורות קצבה נוכחיים</h4>
      {data.pension_sources.length === 0 && <p>לא תועדו מקורות קצבה נוכחיים.</p>}
      {data.pension_sources.map(s => <article key={s.source_id}><h5>{shown(s.payer_name)} — {s.kind === "manual" ? "קצבה ידנית" : "קצבה מהמרה"}</h5>
        <p>{s.calculation_ready ? "עובדות המקור מוכנות לחישוב" : "מקור לא שלם או חסום לחישוב"}</p><Facts codes={s.missing_or_blocking_facts} />
        <p>תחילת קצבה: {formatIsoDate(s.pension_start_date) || "לא תועד"} {s.has_started === false ? "— טרם הגיע מועד התחילה" : ""}</p>
        <p>נכונות סכום הבסיס החודשי: {formatIsoDate(s.monthly_amount_basis?.base_amount_effective_date ?? s.base_amount_effective_date) || "לא תועד — סמכות סכום הבסיס אינה מוכנה"}</p>
        {s.kind === "conversion" && <p>תאריך דוח המקור בעת ההמרה: {formatIsoDate(s.monthly_amount_basis?.source_statement_date) || "לא תועד"}</p>}
        <p>זהות מס: {s.tax_treatment ? taxLabel(s.tax_treatment) : "לא תועד"}</p>
        {s.kind === "manual" && <p>הצמדה כעובדת מקור בלבד: {s.indexation_method === "none" ? "ללא הצמדה" : s.indexation_method === "cpi" ? "מדד" : s.indexation_method === "fixed" ? "שיעור קבוע" : "לא תועד או אינו נתמך"}
          {s.indexation_method === "fixed" && <> · שיעור: <bdi>{shown(s.fixed_indexation_rate)}</bdi></>}</p>}
        <p>סמכות סכום מדויקת: <bdi>{s.amount_authority.authority_kind === "entered_monthly_amount" ? shown(s.amount_authority.amount)
          : `${shown(s.amount_authority.numerator)} / ${shown(s.amount_authority.denominator)}`}</bdi></p>
        <details><summary>מקוריות ואסמכתאות</summary><p>מזהה מקור: <bdi>{s.source_id}</bdi></p>
          <p>אסמכתה: {shown(s.provenance.source_reference)}</p>
          {s.kind === "manual" && <><p>תיאור המקור: {shown(s.description)}</p><p>הערת מקור: {shown(s.source_note)}</p></>}
          {s.tax_treatment && !["taxable", "exempt", "capital_gains"].includes(s.tax_treatment) && <p>סיווג מס טכני שנשמר: <bdi>{s.tax_treatment}</bdi></p>}
          {s.provenance.conversion_id && <p>מזהה המרה: <bdi>{s.provenance.conversion_id}</bdi></p>}
          <ul>{s.provenance.allocations?.map(a => <li key={a.source_component_id}>{a.component_code_snapshot.replace(/_/g, " ")}: <bdi>{a.amount}</bdi></li>)}</ul>
        </details>
        {!readOnly && s.kind === "manual" && <><button disabled={busy} onClick={() => begin(s)}>עריכת קצבה ידנית</button>
          <button disabled={busy} onClick={() => void mutate(() => supersedeManualPension(clientId, s.manual_pension_source_id!, s.version))}>הוצאה מהמקורות הנוכחיים</button></>}
      </article>)}
      <h4>מקורות הון נוכחיים</h4>{data.capital_sources.length === 0 && <p>לא תועדו נכסי הון נוכחיים.</p>}
      {data.capital_sources.map(a => <article key={a.source_id}><h5>{a.asset_description}</h5>
        <p>{a.origin_kind === "manual" ? "נכס ידני" : "יעד הון מהמרה"} · שווי ידוע: <bdi>{shown(a.known_value_amount)}</bdi> · תאריך נכונות: {formatIsoDate(a.value_as_of_date) || "לא תועד"}</p>
        <Facts codes={a.missing_or_blocking_facts} />
        <details><summary>אסמכתת נכס</summary><bdi>{a.source_id} {a.conversion_id}</bdi></details>
      </article>)}
      <details><summary>זהות טכנית של תמונת המקורות</summary><bdi>{data.source_state_fingerprint}</bdi></details>
    </>}
  </section>;
}
