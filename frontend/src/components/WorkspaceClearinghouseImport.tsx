import { useEffect, useRef, useState, type FormEvent } from "react";
import { importPensionProducts, type PensionProduct } from "../api/pensionProductsApi";

type Props = { clientId: number; onImported: (products: PensionProduct[]) => Promise<void> };

export function WorkspaceClearinghouseImport({ clientId, onImported }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, [clientId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!files.length || busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await importPensionProducts(clientId, files);
      if (!mounted.current) return;
      if (result.products.some(product => product.client_id !== clientId)) {
        throw new Error("הייבוא החזיר מוצרים של לקוח אחר. הנתונים לא יוצגו.");
      }
      await onImported(result.products);
      if (!mounted.current) return;
      setFiles([]);
      setMessage(`הייבוא הושלם: ${result.file_count} קבצים, ${result.product_count} מוצרים. טבלת צבעי הכסף עודכנה.`);
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : "קליטת המסלקה נכשלה");
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  return <section className="professional-workspace__import" aria-label="ייבוא קובץ מסלקה">
    <h2>קליטת קובץ מסלקה</h2>
    <p className="professional-workspace__sub">העלאת קובצי XML מעדכנת את אותם המוצרים והרכיבים שמופיעים בטבלת צבעי הכסף. אין צורך ליצור מוצרים ידנית.</p>
    <form onSubmit={submit}>
      <label>קובצי מסלקה
        <input type="file" accept=".xml,.dat" multiple required disabled={busy} onChange={event => setFiles(Array.from(event.target.files ?? []))}/>
      </label>
      <span>{files.length ? `נבחרו ${files.length} קבצים` : "לא נבחרו קבצים"}</span>
      <button type="submit" disabled={!files.length || busy}>{busy ? "קולט נתונים..." : "ייבוא מסלקה ועדכון הטבלה"}</button>
    </form>
    {error && <p role="alert" className="professional-workspace__error">{error}</p>}
    {message && <p role="status">{message}</p>}
  </section>;
}
