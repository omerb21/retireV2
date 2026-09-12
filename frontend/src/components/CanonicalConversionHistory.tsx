import { useEffect, useState } from "react";
import { ConversionHistoryItem, listConversions, reverseConversion, taxLabel } from "../api/canonicalConversionsApi";
import { formatIsoDate } from "../utils/dateFormat";

export function CanonicalConversionHistory({ clientId, productId, version, onChanged, currentOnly = false }: {
  clientId: number; productId?: string; version?: number; onChanged?: () => Promise<void>; currentOnly?: boolean;
}) {
  const [items, setItems] = useState<ConversionHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [undo, setUndo] = useState<{ item: ConversionHistoryItem; key: string; reason: string } | null>(null);
  useEffect(() => {
    let active = true;
    setItems([]); setError(null); setUndo(null);
    listConversions(clientId, productId).then(result => { if (active) setItems(result); }).catch(error => { if (active) setError(error instanceof Error ? error.message : "ההיסטוריה לא נטענה"); });
    return () => { active = false; };
  }, [clientId, productId, version]);
  async function reverse() {
    if (!undo || version === undefined || !onChanged) return;
    setBusy(true); setError(null);
    try {
      await reverseConversion(clientId, undo.item.conversion_id, { expected_conversion_version: undo.item.version, expected_product_version: version, idempotency_key: undo.key, reason: undo.reason });
      await onChanged();
    } catch (error) { setError(error instanceof Error ? error.message : "ביטול ההמרה לא הושלם"); }
    finally { setBusy(false); }
  }
  const visible = currentOnly ? items.filter(item => item.status === "active") : items;
  return <section dir="rtl" aria-label={currentOnly ? "יעדים פעילים מהמרות" : "היסטוריית המרות"}>
    <h4>{currentOnly ? "יעדים פעילים מהמרות — לקריאה בלבד" : "היסטוריית המרות"}</h4>
    {!visible.length && <p>אין המרות להצגה</p>}
    {visible.map(item => <section key={item.conversion_id}>
      <p>{item.destination_type === "pension" ? "יעד קצבה" : "נכס הון"}: <bdi>{item.converted_amount}</bdi> — {taxLabel(item.tax_treatment)}</p>
      <p>תאריך המרה: <bdi>{formatIsoDate(item.effective_date)}</bdi> — {item.status === "active" ? "פעילה" : "בוטלה"}</p>
      {item.pension && <><p>קצבה חודשית לתצוגה: <bdi>{item.pension.monthly_display_amount}</bdi>; מקדם: <bdi>{item.pension.annuity_factor_text}</bdi></p>
        {item.pension.coefficient_fallback_used && <p>נעשה שימוש במקדם ברירת מחדל 200</p>}</>}
      {!currentOnly && <details><summary>הקצאות מקור</summary><ul>{item.allocations.map(a => <li key={a.component_code_snapshot}>{a.component_code_snapshot.replace(/_/g, " ")} — הומרו <bdi>{a.amount}</bdi>; לפני <bdi>{a.source_balance_before}</bdi>; אחרי <bdi>{a.source_balance_after}</bdi></li>)}</ul></details>}
      {onChanged && item.status === "active" && <button disabled={busy} onClick={() => setUndo({ item, key: crypto.randomUUID(), reason: "" })}>ביטול המרה</button>}
    </section>)}
    {undo && <fieldset disabled={busy}><legend>ביטול מלא של ההמרה</legend><p>כל ההקצאות יוחזרו למקור. ההיסטוריה תישמר. שימוש בתהליך המשך עשוי למנוע ביטול.</p>
      <label>סיבת ביטול<textarea value={undo.reason} onChange={event => setUndo({ ...undo, key: crypto.randomUUID(), reason: event.target.value })} /></label>
      <button disabled={!undo.reason.trim()} onClick={() => void reverse()}>אישור ביטול המרה</button><button onClick={() => setUndo(null)}>חזרה</button></fieldset>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
