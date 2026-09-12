import { FormEvent, useRef, useState, useEffect } from "react";
import { ConversionComponent, ConversionPreview, ConversionRequest, Destination, executeConversion, previewConversion, taxLabel } from "../api/canonicalConversionsApi";
import { HebrewDateInput } from "./HebrewDateInput";

export function CanonicalComponentConversionDialog({ clientId, productId, version, component, onDone, onClose }: {
  clientId: number; productId: string; version: number; component?: ConversionComponent; onDone: () => Promise<void>; onClose: () => void;
}) {
  const allowed = component ? Object.keys(component.allowed_destinations) as Destination[] : ["pension", "capital"] as Destination[];
  const [destination, setDestination] = useState<Destination>(allowed[0]);
  const [full, setFull] = useState(true);
  const [amount, setAmount] = useState("");
  const [effective, setEffective] = useState("");
  const [start, setStart] = useState("");
  const [pensionOptions, setPensionOptions] = useState({ company_name: "", option_name: "", survivors_option: "תקנוני", retirement_age: "", spouse_age_diff: "0", target_year: "" });
  const [preview, setPreview] = useState<ConversionPreview | null>(null);
  const [confirmed, setConfirmed] = useState<ConversionRequest | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const invalidate = () => { setPreview(null); setConfirmed(null); setError(null); };
  async function calculate(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    const body: ConversionRequest = { product_id: productId, expected_product_version: version, destination_type: destination,
      effective_date: effective, idempotency_key: crypto.randomUUID(), whole_product: !component,
      selections: component ? [{ component_id: component.component_id, component_code: component.component_code, amount: full ? null : amount }] : [],
      ...(destination === "pension" ? { pension: { pension_start_date: start,
        ...(pensionOptions.company_name ? { company_name: pensionOptions.company_name } : {}),
        ...(pensionOptions.option_name ? { option_name: pensionOptions.option_name } : {}),
        survivors_option: pensionOptions.survivors_option,
        spouse_age_diff: Number(pensionOptions.spouse_age_diff),
        ...(pensionOptions.retirement_age ? { retirement_age: Number(pensionOptions.retirement_age) } : {}),
        ...(pensionOptions.target_year ? { target_year: Number(pensionOptions.target_year) } : {}),
      } } : {}) };
    try { const result = await previewConversion(clientId, body); if (alive.current) { setPreview(result); setConfirmed(body); } }
    catch (error) { if (alive.current) setError(error instanceof Error ? error.message : "התצוגה המקדימה לא הושלמה"); }
    finally { if (alive.current) setBusy(false); }
  }
  async function execute() {
    if (!confirmed) return;
    setBusy(true); setError(null);
    try { await executeConversion(clientId, confirmed); if (alive.current) await onDone(); }
    catch (error) { if (alive.current) setError(error instanceof Error ? error.message : "ההמרה לא הושלמה"); }
    finally { if (alive.current) setBusy(false); }
  }
  return <section role="dialog" aria-label="המרת רכיבים" dir="rtl">
    <h4>{component ? `המרת ${component.component_code.replace(/_/g, " ")}` : "המרת רכיבים זכאים במוצר"}</h4>
    {component && <p>יתרה זמינה: <bdi>{component.balance}</bdi></p>}
    <form onInput={invalidate} onSubmit={event => void calculate(event)}><fieldset disabled={busy}><legend>פרטי ההמרה</legend>
      <label>יעד<select value={destination} onChange={event => { setDestination(event.target.value as Destination); invalidate(); }}>{allowed.map(value => <option key={value} value={value}>{value === "pension" ? "קצבה" : "הון"}</option>)}</select></label>
      {component && <><label><input type="checkbox" checked={full} onChange={event => { setFull(event.target.checked); invalidate(); }} />כל היתרה</label>
        {!full && <label>סכום חלקי<input dir="ltr" inputMode="decimal" required pattern="[0-9]+([.][0-9]{1,2})?" value={amount} onChange={event => { setAmount(event.target.value); invalidate(); }} /></label>}</>}
      <label>תאריך המרה<HebrewDateInput required value={effective} onChange={value => { setEffective(value); invalidate(); }} /></label>
      {destination === "pension" && <label>תאריך תחילת קצבה<HebrewDateInput required value={start} onChange={value => { setStart(value); invalidate(); }} /></label>}
      {destination === "pension" && <details><summary>פרטי חיפוש מקדם נוספים</summary>
        <p>כשקיים תאריך לידה, הגיל מחושב ממנו ומתאריך תחילת הקצבה. בהיעדר שנת יעד משתמשים בשנה הנוכחית.</p>
        {([ ["company_name", "חברת ביטוח"], ["option_name", "מסלול קצבה"], ["survivors_option", "מסלול שארים"], ["retirement_age", "גיל פרישה בהיעדר תאריך לידה"], ["spouse_age_diff", "הפרש גיל בן או בת זוג"], ["target_year", "שנת יעד למקדם"] ] as const).map(([key, label]) => <label key={key}>{label}<input value={pensionOptions[key]} onChange={event => { setPensionOptions({ ...pensionOptions, [key]: event.target.value }); invalidate(); }} /></label>)}
      </details>}
      <button type="submit">תצוגה מקדימה</button>
    </fieldset></form>
    {preview && <div aria-label="תוצאת ההמרה הצפויה">{preview.groups.map(group => <section key={group.tax_treatment}>
      <p>סכום יעד: <bdi>{group.amount}</bdi> — {taxLabel(group.tax_treatment)}</p>
      <ul>{group.allocations.map(item => <li key={item.component_id}>{item.component_code.replace(/_/g, " ")}: <bdi>{item.amount}</bdi>; יתרה לאחר המרה: <bdi>{item.after}</bdi></li>)}</ul>
      {group.coefficient && <><p>מקדם קצבה: <bdi>{group.coefficient.annuity_factor}</bdi></p><p>קצבה חודשית לתצוגה: <bdi>{group.monthly_display_amount}</bdi></p>
        <p>מקור המקדם: {({ pension_fund_coefficient: "טבלת קרנות פנסיה", company_annuity_coefficient: "טבלת חברה ומסלול", policy_generation_coefficient: "טבלת דור פוליסה" }[group.coefficient.source] ?? "ברירת מחדל")}</p>
        {group.coefficient.fallback_used && <p role="status">לא נמצא מקדם מתאים או שהחיפוש נכשל. נעשה שימוש במקדם ברירת מחדל 200.</p>}</>}
    </section>)}{!!preview.skipped.length && <><h5>רכיבים שלא יומרו</h5><ul>{preview.skipped.map(item => <li key={item.component_code}>{item.component_code.replace(/_/g, " ")} — היעד אינו מותר לרכיב</li>)}</ul></>}
      <button disabled={busy} onClick={() => void execute()}>אישור המרה</button></div>}
    {error && <p role="alert">{error}</p>}<button disabled={busy} onClick={onClose}>סגירה</button>
  </section>;
}
