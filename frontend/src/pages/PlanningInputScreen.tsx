import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { planningCall, type PlanningInput, type PlanningItem } from "../api/planningInputApi";
import { HebrewDateInput } from "../components/HebrewDateInput";
import { formatIsoDate } from "../utils/dateFormat";
import { taxLabel } from "../api/canonicalConversionsApi";

const labels: Record<string, string> = {
  retirement_target_date_missing: "לא נבחר תאריך יעד לפרישה", retirement_target_before_planning_base_date: "תאריך היעד קודם למועד הבסיס",
  base_and_target_missing: "חסרים מועד בסיס ותאריך יעד", base_missing: "חסר מועד בסיס", target_missing: "חסר תאריך יעד",
  before_base: "היעד קודם למועד הבסיס", equal_to_base: "היעד שווה למועד הבסיס — אופק באורך אפס", after_base: "היעד אחרי מועד הבסיס",
  target_reference_dates_conflict: "קיימים תאריכי ייחוס שונים — ללא עדיפות אוטומטית",
  retirement_target_differs_from_reference_dates: "תאריך היעד שונה מתאריכי ייחוס",
  target_reference_state_changed_since_decision: "עובדות הייחוס השתנו מאז ההחלטה — היעד לא שונה",
  planned_retirement_age: "גיל פרישה שנמסר — ללא המרה לתאריך",
  planning_base_date_missing: "לא נבחר מועד בסיס לתכנון", frequency_unsupported: "תדירות אינה נתמכת לנרמול",
  amount_invalid: "סכום אינו תקין", start_date_missing: "חסר תאריך התחלה", end_date_missing: "חסר תאריך סיום ידוע",
  continuation_unknown: "מצב ההמשכיות אינו ידוע", date_range_contradictory: "תאריכי התחולה סותרים",
  amount_basis_unknown: "לא ידוע אם הסכום הוא ברוטו או נטו", capital_value_missing: "חסר שווי הון",
  capital_valuation_date_missing: "חסר תאריך שווי הון", identity_resolution_required: "נדרשת הכרעה מפורשת בזהות הכנסת הקצבה",
  identity_resolution_stale: "הכרעת הזהות אינה עדכנית; נדרש אישור מחדש", potential_duplicate_warning: "דמיון בין הכנסות — אזהרה בלבד, ללא איחוד או חסימה",
  future_start: "תחילה עתידית — לא פעיל במועד הבסיס", ended: "הסתיים לפני מועד הבסיס", active_at_base: "חל במועד הבסיס",
  base_date_missing: "טרם נבחר מועד בסיס", included: "כלול בקלט", excluded: "לא נכלל", unresolved: "נדרש בירור", reference_only: "לעיון בלבד",
  gross: "ברוטו", net: "נטו", unknown: "לא ידוע", monthly: "חודשי", quarterly: "רבעוני", annual: "שנתי", other: "אחר",
  planned_retirement_date: "תאריך פרישה שנמסר", planned_work_end_date: "סיום עבודה מתוכנן", intended_pension_start_date: "תחילת קצבה מיועדת",
  other_known_retirement_date: "מועד פרישה אחר שנמסר", anticipated_work_end_date: "סיום עבודה צפוי", pension_start_date: "תחילת מקור קצבה",
};
const label = (code: string) => labels[code] ?? "עובדת מקור דורשת בדיקה";

function Items({title, items}: {title: string; items: PlanningItem[]}) {
  return <section><h2>{title}</h2>{items.length === 0 ? <p>לא תועדו פריטים.</p> : items.map(item => <article key={item.source_id}>
    <h3>{item.payer_name ?? item.asset_description ?? item.description ?? item.product_name ?? "מקור מתועד"}</h3>
    <small>מזהה מקור: {item.source_id}</small>
    {item.component_code && <p>רכיב: {item.component_code.replace(/_/g, " ")}</p>}
    {item.kind && <p>{item.kind === "manual" ? "קצבה ידנית" : "קצבה מהמרה"}</p>}
    {item.source_calculation_ready !== undefined && <p>{item.source_calculation_ready ? "עובדת המקור מוכנה" : "עובדת המקור אינה מוכנה"}</p>}
    {item.tax_treatment && <p>זהות מס: {taxLabel(item.tax_treatment)}</p>}
    {(item.source_note || item.provenance?.source_note) && <p>הערת מקור: {item.source_note ?? item.provenance?.source_note}</p>}
    {item.provenance?.source_reference && <p>אסמכתת מקור: {item.provenance.source_reference}</p>}
    {item.provenance?.conversion_id && <small>קישור המרה: {item.provenance.conversion_id}</small>}
    {item.source_date && <p>תאריך מקור: {formatIsoDate(item.source_date)}</p>}
    <p>{label(item.inclusion_state)}{item.applicability ? ` — ${label(item.applicability)}` : ""}</p>
    {item.amount_basis && <p>בסיס סכום: {label(item.amount_basis)}</p>}
    {item.amount !== undefined && <p>סכום מקור מדויק: <bdi>{item.amount}</bdi> · תדירות: {label(item.frequency ?? "unknown")}</p>}
    {item.monthly_equivalent_ratio && <p>יחס מקבילה חודשית מדויק: <bdi>{item.monthly_equivalent_ratio.numerator} / {item.monthly_equivalent_ratio.denominator}</bdi> — אינו לוח תשלומים</p>}
    {item.amount_authority && <p>סמכות סכום קצבה: <bdi>{item.amount_authority.amount ?? `${item.amount_authority.numerator} / ${item.amount_authority.denominator}`}</bdi></p>}
    {item.known_value_amount !== undefined && <p>שווי מקור: <bdi>{item.known_value_amount ?? "לא תועד"}</bdi> · תאריך שווי: {formatIsoDate(item.value_as_of_date) || "לא תועד"}</p>}
    {item.balance !== undefined && <p>יתרה שטרם הומרה: <bdi>{item.balance}</bdi></p>}
    {(item.start_date || item.end_date || item.pension_start_date) && <p>תחילה: {formatIsoDate(item.start_date ?? item.pension_start_date) || "לא תועד"} · סיום: {formatIsoDate(item.end_date) || "לא תועד"}</p>}
    {item.blocking_facts?.map(code => <p key={code}>{label(code)}</p>)}
  </article>)}</section>;
}

function Resolution({item, data, save}: {item: PlanningItem; data: PlanningInput; save: (path: string, body: unknown) => Promise<void>}) {
  const [kind, setKind] = useState("SAME_CANONICAL_PENSION");
  const [target, setTarget] = useState("");
  const [category, setCategory] = useState("rental");
  const [reference, setReference] = useState("");
  const pension = data.pension_inputs.find(p => p.source_id === target);
  async function submit(event: FormEvent) {
    event.preventDefault();
    await save(`/income-resolutions/${item.id}`, {
      expected_version: data.decision_version, expected_income_fingerprint: item.source_fingerprint,
      decision_kind: kind, reference,
      ...(kind === "MISCLASSIFIED_GENERAL_INCOME" ? {income_category: category} : {
        canonical_source_id: target, expected_canonical_fingerprint: pension?.source_fingerprint}),
    });
  }
  return <form onSubmit={submit}><fieldset><legend>הכרעת זהות: {item.description ?? item.source_id}</legend>
    <label>סוג הכרעה<select value={kind} onChange={e => setKind(e.target.value)}>
      <option value="SAME_CANONICAL_PENSION">אותה קצבה שכבר קנונית</option>
      <option value="PENSION_NOT_YET_CANONICAL">קצבה ידנית שנוצרה בנפרד</option>
      <option value="MISCLASSIFIED_GENERAL_INCOME">הכנסה שאינה קצבה — תיקון סיווג</option>
    </select></label>
    {kind === "MISCLASSIFIED_GENERAL_INCOME" ? <label>קטגוריה מתוקנת<select value={category} onChange={e => setCategory(e.target.value)}>
      <option value="rental">שכירות</option><option value="employment">עבודה</option><option value="business">עסק</option><option value="benefit">גמלה</option><option value="other">אחר</option>
    </select></label> : <><label>מקור קצבה לקישור<select required value={target} onChange={e => setTarget(e.target.value)}>
      <option value="">יש לבחור מקור קיים</option>{data.pension_inputs.filter(p => kind !== "PENSION_NOT_YET_CANONICAL" || p.kind === "manual").map(p => <option key={p.source_id} value={p.source_id}>{p.payer_name ?? "מקור קצבה"} — {p.source_id}</option>)}
    </select></label><p>אם המקור חסר, יש ליצור קצבה ידנית בתמונת המקורות ולחזור לכאן. אין העתקה אוטומטית.</p></>}
    <label>אסמכתה להכרעה<input required maxLength={512} value={reference} onChange={e => setReference(e.target.value)} /></label>
    <button type="submit">אישור הכרעת זהות</button>
  </fieldset></form>;
}

function Workspace({id}: {id: number}) {
  const [data, setData] = useState<PlanningInput | null>(null);
  const [error, setError] = useState("");
  const [date, setDate] = useState("");
  const [generation, setGeneration] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setData(null); setError("");
    planningCall<PlanningInput>(id, "", undefined, controller.signal).then(result => {
      if (!active) return;
      if (result.client_id !== id) throw new Error("שיוך הקלט ללקוח אינו תקין");
      setData(result); setDate(result.planning_base_date ?? "");
    }).catch(reason => {if (active) setError(reason instanceof Error ? reason.message : "טעינת הקלט נכשלה");});
    return () => {active = false; controller.abort();};
  }, [id, generation]);
  async function save(path: string, body: unknown) {
    setBusy(true); setError("");
    try {await planningCall(id, path, body); setGeneration(n => n + 1);}
    catch (reason) {setError(reason instanceof Error ? reason.message : "השמירה נכשלה");}
    finally {setBusy(false);}
  }
  return <main dir="rtl"><h1>קלט בסיס לתכנון פרישה</h1>
    <Link to={`/clients/${id}/professional-sources`}>תמונת המקורות ותיקון עובדות</Link>{" · "}<Link to={`/clients/${id}`}>פרטי הלקוח</Link>
    <p>קלט בלבד — ללא חישוב תזרים, תחזית או מס.</p>
    {error && <p role="alert">{error}</p>}
    <button onClick={() => setGeneration(n => n + 1)} disabled={busy}>רענון הקלט</button>
    {!data && !error && <p>טוען קלט תכנון…</p>}
    {data && <fieldset disabled={busy}><legend>בדיקת קלט בסיס</legend>
      <p>{data.planning_input_ready ? "קלט הבסיס מוכן לשכבת תכנון עתידית" : "קלט הבסיס אינו מוכן — נדרשת השלמת החלטות או עובדות"}</p>
      <p>מועד בסיס מאושר: {formatIsoDate(data.planning_base_date) || "לא נבחר"}</p>
      <form onSubmit={e => {e.preventDefault(); void save("/base-date", {expected_version: data.decision_version, planning_base_date: date || null});}}>
        <label>מועד בסיס מפורש<HebrewDateInput value={date} onChange={setDate} /></label>
        <button type="submit">אישור מועד הבסיס</button>
      </form>
      <TargetAuthority key={`${id}:${data.decision_version}:${data.retirement_target?.current_reference_fingerprint}`} data={data} save={save} />
      <h2>מועדים לעיון — אין בחירה אוטומטית</h2>
      {data.client_reference_facts && <p>תאריך לידה שנמסר: {formatIsoDate(data.client_reference_facts.birth_date) || "לא תועד"} · גיל פרישה שנמסר: {data.client_reference_facts.planned_retirement_age ?? "לא תועד"} — אינו בחירת מועד בסיס</p>}
      {data.date_candidates.map((c, i) => <p key={`${c.source_id}:${c.field}:${i}`}>{label(c.field)}: {formatIsoDate(c.date)} <button onClick={() => setDate(c.date)}>בחירת מועד זה לאישור</button></p>)}
      <h2>חסמים ואזהרות</h2>
      {data.blocking_facts.map((b, i) => <p key={`b${i}`}>{label(b.code)}{b.source_id && <small> — {b.source_id}</small>}</p>)}
      {data.warnings.map((w, i) => <p key={`w${i}`}>{label(w.code)}</p>)}
      {data.excluded_sources.filter(i => i.inclusion_state === "unresolved").map(item => <Resolution key={`${item.source_id}:${data.decision_version}`} item={item} data={data} save={save} />)}
      <Items title="קצבאות" items={data.pension_inputs} /><Items title="הכנסות כלליות" items={data.general_income_inputs} />
      <Items title="הוצאות" items={data.expense_inputs} /><Items title="נכסי הון" items={data.capital_inputs} />
      <Items title="מקורות שאינם נכללים" items={data.excluded_sources} /><Items title="יתרות ומידע לעיון בלבד" items={data.reference_only} />
    </fieldset>}
  </main>;
}

function TargetAuthority({data, save}: {data: PlanningInput; save: (path: string, body: unknown) => Promise<void>}) {
  const authority = data.retirement_target;
  const [target, setTarget] = useState(authority?.retirement_target_date ?? "");
  if (!authority) return <p role="alert">סמכות תאריך היעד אינה זמינה; יש לרענן את הקלט.</p>;
  const write = (value: string | null) => save("/target-date", {
    expected_version: data.decision_version,
    expected_target_reference_fingerprint: authority.current_reference_fingerprint,
    retirement_target_date: value,
  });
  return <section><h2>תאריך יעד מפורש לפרישה</h2>
    <p>מועד בסיס התכנון: {formatIsoDate(data.planning_base_date) || "לא נבחר"}</p>
    <p>תאריך יעד שמור: {formatIsoDate(authority.retirement_target_date) || "לא נבחר"}</p>
    <p>{label(authority.relation_to_planning_base)}</p>
    <p>{authority.retirement_target_ready ? "תאריך היעד תקף" : "תאריך היעד אינו מוכן"}</p>
    <p>{data.ready_for_next_planning_calculation ? "הקלט והיעד מוכנים לשכבת חישוב עתידית" : "הקלט והיעד טרם מוכנים יחד"}</p>
    {authority.blockers.map(code => <p key={code}>{label(code)}</p>)}
    {authority.warnings.map(code => <p key={code}>{label(code)}</p>)}
    <h3>עובדות ייחוס — אינן המלצה או החלטה</h3>
    {(data.target_reference_facts ?? []).map(fact => <article key={fact.reference_id}>
      <p>{label(fact.source_field)}: {fact.value_kind === "age" ? `גיל ${fact.age_value}` : formatIsoDate(fact.date_value)}</p>
      <small>מזהה מקור: {fact.source_id}</small>
      <p>{fact.lifecycle_state === "current" ? "מקור נוכחי" : "יש לבדוק את מצב המקור"}</p>
      {fact.unresolved_state.map(code => <p key={code}>{label(code)}</p>)}
      {fact.value_kind === "date" && fact.date_value && <button type="button" onClick={() => setTarget(fact.date_value!)}>העתקת תאריך הייחוס לשדה היעד</button>}
    </article>)}
    <form onSubmit={event => {event.preventDefault(); if (target) void write(target);}}>
      <label>תאריך יעד לפרישה<HebrewDateInput value={target} onChange={setTarget} /></label>
      <button type="submit" disabled={!target}>שמירת תאריך היעד</button>
      <button type="button" onClick={() => {void write(null);}}>ניקוי מפורש של תאריך היעד</button>
    </form>
  </section>;
}
export function PlanningInputScreen() {
  const id = Number(useParams().clientId);
  return Number.isSafeInteger(id) && id > 0 ? <Workspace key={id} id={id} /> : <p role="alert">מזהה לקוח אינו תקין</p>;
}
