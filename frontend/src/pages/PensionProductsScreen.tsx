import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createPensionProduct, deletePensionProduct, importPensionProducts, listPensionProducts, PensionProduct, PensionProductMetadata, savePensionProduct } from "../api/pensionProductsApi";
import { HebrewDateInput } from "../components/HebrewDateInput";
import { formatIsoDate, formatIsoTimestamp } from "../utils/dateFormat";

const emptyMetadata = (): PensionProductMetadata => ({ product_name: "", product_type: "קופת גמל", provider_name: null, provider_identifier: null, account_reference: null, start_date: null, statement_date: null, historical_employers: [], reported_product_total: "0.00", reported_rewards_total: null, reported_severance_total: null });
const metadataKeys = Object.keys(emptyMetadata()) as Array<keyof PensionProductMetadata>;
const metadataOf = (product: PensionProduct): PensionProductMetadata => Object.fromEntries(metadataKeys.map(key => [key, product[key]])) as unknown as PensionProductMetadata;
const errorMessage = (error: unknown) => error instanceof Error ? error.message : "הפעולה לא הושלמה";
const productTypeLabel = (value: string) => ({ "1": "פוליסת ביטוח חיים משולב חיסכון", "2": "פוליסת ביטוח חיים", "3": "קופת גמל", "4": "קרן פנסיה", "5": "פוליסת חיסכון טהור" }[value] ?? (/^[\dA-Za-z_ -]+$/.test(value) ? "סוג מוצר מהמקור" : value));

function MetadataFields({ value, onChange }: { value: PensionProductMetadata; onChange: (next: PensionProductMetadata) => void }) {
  const textFields = { product_name: "שם התכנית", product_type: "סוג המוצר", provider_name: "הגוף המנהל", provider_identifier: "מזהה הגוף המנהל", account_reference: "מספר חשבון או פוליסה" } as const;
  const totals = { reported_product_total: "סך המוצר המדווח", reported_rewards_total: "סך התגמולים המדווח", reported_severance_total: "סך הפיצויים המדווח" } as const;
  return <>
    {Object.entries(textFields).map(([key, label]) => <p key={key}><label>{label}<input value={value[key as keyof typeof textFields] ?? ""} required={key === "product_name" || key === "product_type"} maxLength={key === "provider_identifier" ? 128 : 255} onChange={event => onChange({ ...value, [key]: event.target.value || null })} /></label></p>)}
    <p><label>תאריך התחלה<HebrewDateInput value={value.start_date ?? ""} onChange={start_date => onChange({ ...value, start_date: start_date || null })} /></label></p>
    <p><label>תאריך נכונות היתרה<HebrewDateInput value={value.statement_date ?? ""} onChange={statement_date => onChange({ ...value, statement_date: statement_date || null })} /></label></p>
    <p><label>מעסיקים היסטוריים (שם בכל שורה)<textarea value={value.historical_employers.join("\n")} onChange={event => onChange({ ...value, historical_employers: event.target.value.split("\n") })} /></label></p>
    {Object.entries(totals).map(([key, label]) => <p key={key}><label>{label}<input dir="ltr" inputMode="decimal" pattern="-?[0-9]+([.][0-9]{1,2})?" value={value[key as keyof typeof totals] ?? ""} onChange={event => onChange({ ...value, [key]: event.target.value || null })} /></label></p>)}
  </>;
}

function ProductEditor({ product, clientId, onSaved, onDeleted }: { product: PensionProduct; clientId: number; onSaved: (product: PensionProduct) => void; onDeleted: () => void }) {
  const [metadata, setMetadata] = useState(() => metadataOf(product));
  const [components, setComponents] = useState(product.components);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try { onSaved(await savePensionProduct(clientId, product.product_id, { ...metadata, historical_employers: metadata.historical_employers.filter(name => name.trim()), expected_version: product.version, components })); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setError(null);
    try { await deletePensionProduct(clientId, product.product_id, product.version); onDeleted(); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  const totalsLabels: Record<string, string> = { rewards_component_sum: "סכום רכיבי התגמולים", severance_component_sum: "סכום רכיבי הפיצויים", product_component_sum: "סכום כל הרכיבים", rewards_discrepancy: "פער תגמולים", severance_discrepancy: "פער פיצויים", product_discrepancy: "פער המוצר" };
  return <section aria-label={`עריכת ${product.product_name}`}>
    <h3>{product.product_name}</h3>
    <p>סוג מוצר: {productTypeLabel(product.product_type)}</p>
    <p>עדכון אחרון: <bdi>{formatIsoTimestamp(product.updated_at)}</bdi></p>
    <form onSubmit={save}><fieldset disabled={busy}><legend>פרטי מוצר ורכיבים</legend>
      <MetadataFields value={metadata} onChange={setMetadata} />
      {Object.entries(components).map(([code, balance]) => <p key={code}><label>{code.replace(/_/g, " ")}<input dir="ltr" inputMode="decimal" required pattern="-?[0-9]+([.][0-9]{1,2})?" value={balance} onChange={event => setComponents({ ...components, [code]: event.target.value })} /></label></p>)}
      <button type="submit">שמירת מוצר</button>
      <button type="button" onClick={() => { setMetadata(metadataOf(product)); setComponents(product.components); setError(null); }}>ביטול עריכה</button>
    </fieldset></form>
    <h4>התאמות לפי הנתונים השמורים</h4>
    <p>פערים הם מידע לבקרה בלבד ואינם משנים את היתרות. עריכות ייכללו בחישוב לאחר שמירה.</p>
    <dl>{Object.entries(totalsLabels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd><bdi>{product.reconciliation[key] ?? "לא נמסר סך מדווח"}</bdi></dd></div>)}</dl>
    {!!product.source_history?.length && <details><summary>תיעוד מקור ואבחון טכני</summary>{product.source_history.map(source => <section key={source.checksum}><p>קובץ: <bdi>{source.filename ?? "לא נמסר"}</bdi></p><p>תאריך המקור: <bdi>{formatIsoDate(source.statement_date) || "לא נמסר"}</bdi></p><p>חתימת קובץ: <code dir="ltr">{source.checksum}</code></p><pre dir="ltr">{JSON.stringify(source.diagnostics, null, 2)}</pre></section>)}</details>}
    {error && <p role="alert">{error}</p>}
    {confirmDelete ? <div role="group" aria-label="אישור מחיקת מוצר"><p>למחוק את המוצר ואת רכיביו? תיעוד המקור יישמר.</p><button disabled={busy} onClick={() => void remove()}>אישור מחיקה</button><button disabled={busy} onClick={() => setConfirmDelete(false)}>ביטול מחיקה</button></div> : <button disabled={busy} onClick={() => setConfirmDelete(true)}>מחיקת מוצר</button>}
  </section>;
}

function ProductsForClient({ clientId }: { clientId: number }) {
  const [products, setProducts] = useState<PensionProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [manual, setManual] = useState(emptyMetadata);
  const [file, setFile] = useState<File | null>(null);
  useEffect(() => {
    let active = true;
    listPensionProducts(clientId).then(next => { if (active) setProducts(next); }).catch(error => { if (active) setError(errorMessage(error)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientId]);
  const replace = (next: PensionProduct) => { setProducts(current => [...current.filter(product => product.product_id !== next.product_id), next]); setMessage("המוצר נשמר"); };
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try { replace(await createPensionProduct(clientId, { ...manual, historical_employers: manual.historical_employers.filter(name => name.trim()) })); setManual(emptyMetadata()); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  async function ingest(event: FormEvent) {
    event.preventDefault(); if (!file) return; setBusy(true); setError(null); setMessage(null);
    try {
      const imported = await importPensionProducts(clientId, file);
      setProducts(current => [...current.filter(product => !imported.some(item => item.product_id === product.product_id)), ...imported]);
      setMessage("הייבוא הושלם. המוצרים והרכיבים זמינים בטבלה.");
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <section dir="rtl">
    <h2>מוצרים פנסיוניים</h2><p><Link to={`/clients/${clientId}`}>חזרה לפרטי הלקוח</Link></p>
    {loading && <p>טוען מוצרים...</p>}{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form onSubmit={ingest}><fieldset disabled={busy || loading}><legend>ייבוא מקור</legend><label>קובץ מקור<input type="file" accept=".xml,.dat" required onChange={event => setFile(event.target.files?.[0] ?? null)} /></label><button type="submit" disabled={!file}>ייבוא מוצרים</button></fieldset></form>
    <details><summary>יצירת מוצר ידנית</summary><form onSubmit={create}><fieldset disabled={busy || loading}><legend>מוצר חדש</legend><MetadataFields value={manual} onChange={setManual} /><p>כל אחד עשר הרכיבים ייווצרו ביתרה אפס. הסך המדווח לא יחולק בין הרכיבים.</p><button type="submit">יצירת מוצר</button></fieldset></form></details>
    {!loading && products.length === 0 && <p>אין מוצרים פנסיוניים. ניתן לייבא מקור או ליצור מוצר ידנית.</p>}
    {products.length > 0 && <table><caption>מוצרים פנסיוניים שמורים</caption><thead><tr><th>שם תכנית</th><th>גוף מנהל</th><th>חשבון</th><th>סך מדווח</th></tr></thead><tbody>{products.map(product => <tr key={product.product_id}><td>{product.product_name}</td><td>{product.provider_name ?? "לא נמסר"}</td><td><bdi>{product.account_reference}</bdi></td><td><bdi>{product.reported_product_total ?? "לא נמסר"}</bdi></td></tr>)}</tbody></table>}
    {products.map(product => <ProductEditor key={`${product.product_id}:${product.version}`} product={product} clientId={clientId} onSaved={replace} onDeleted={() => setProducts(current => current.filter(item => item.product_id !== product.product_id))} />)}
  </section>;
}

export function PensionProductsScreen() {
  const { clientId } = useParams();
  if (!clientId || !/^[1-9]\d*$/.test(clientId) || !Number.isSafeInteger(Number(clientId))) return <p role="alert">מזהה הלקוח אינו תקין</p>;
  // Keying the complete editor by client prevents pending requests or local
  // edits from leaking into another client's route during navigation.
  return <ProductsForClient key={clientId} clientId={Number(clientId)} />;
}
