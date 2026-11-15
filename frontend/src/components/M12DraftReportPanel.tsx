import { useEffect, useRef, useState } from "react";
import { loadM12Draft, type M12Draft } from "../api/m12DraftReportApi";

interface Props { clientId: number; }
const missing = "לא תועד";
const cell = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? missing : String(value);
const amount = (value: string | null | undefined) =>
  value == null || value === "" ? missing : `${value} ₪`;

export function M12DraftReportPanel({ clientId }: Props) {
  const [draft, setDraft] = useState<M12Draft | null>(null);
  const [loadedFor, setLoadedFor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);
  useEffect(() => {
    ++generation.current;
    setDraft(null);
    setLoadedFor(null);
    setError(null);
    setLoading(false);
    return () => { ++generation.current; };
  }, [clientId]);
  async function open() {
    const epoch = ++generation.current;
    setLoading(true); setError(null); setDraft(null);
    const controller = new AbortController();
    try {
      const data = await loadM12Draft(clientId, controller.signal);
      if (epoch !== generation.current) return;
      setDraft(data); setLoadedFor(clientId);
    } catch (reason) {
      if (epoch === generation.current)
        setError(reason instanceof Error ? reason.message : "טעינת הטיוטה נכשלה");
    } finally {
      if (epoch === generation.current) setLoading(false);
    }
  }
  const current = loadedFor === clientId ? draft : null;
  return <section aria-label="M12 טיוטת תכנון פרישה" className="m12-draft-control">
    <button type="button" onClick={() => void open()} disabled={loading}>
      {loading ? "טוען טיוטה..." : "הפק טיוטת תכנון פרישה"}
    </button>
    {error && <p role="alert">{error}</p>}
    {current && <>
      <p>תצוגה מקדימה. המסמך הוא טיוטה בלבד ואינו מאשר חישובים.</p>
      <button type="button" onClick={() => window.print()}>
        שמור כ-PDF / הדפס
      </button>
      <style>{`
        .m12-draft-page { direction: rtl; text-align: right; font-family: Arial, "Noto Sans Hebrew", sans-serif;
          color: #172a39; max-width: 800px; margin: 20px auto; padding: 30px;
          background: white; line-height: 1.5; }
        .m12-draft-page h1 { border-bottom: 2px solid #1c526f; padding-bottom: 12px; }
        .m12-draft-page h2 { margin-top: 24px; color: #1c526f; }
        .m12-draft-page table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }
        .m12-draft-page th, .m12-draft-page td { padding: 8px; border: 1px solid #d7dfe5; text-align: right; }
        .m12-draft-page th { background: #f0f5f8; }
        .m12-draft-page .m12-warning { border-right: 3px solid #b67a27; padding: 8px 12px; background: #fff7eb; }
        .m12-draft-page .m12-draft-watermark { font-weight: bold; font-size: 19px; color: #8c4a4a; }
        @media print {
          @page { size: A4; margin: 15mm; }
          body * { visibility: hidden !important; }
          .m12-draft-page, .m12-draft-page * { visibility: visible !important; }
          .m12-draft-page { position: absolute; top: 0; right: 0; width: 100%; max-width: none;
            margin: 0; padding: 0; color: #111; }
          .m12-draft-page section, .m12-draft-page table { break-inside: avoid; }
          .m12-draft-page tr { break-inside: avoid; }
          .m12-draft-page .m12-warning { border: 1px solid #b67a27; }
        }
      `}</style>
      <article className="m12-draft-page" dir="rtl" lang="he" aria-label="תצוגה מקדימה של טיוטת תכנון פרישה">
        <p className="m12-draft-watermark">טיוטה - לא מסמך תכנון סופי</p>
        <h1>תכנון פרישה אישי</h1>
        <p>תאריך הפקה: {new Date(current.generated_at).toLocaleDateString("he-IL")}</p>
        <section>
          <h2>פרטי הלקוח</h2>
          <p><strong>שם:</strong> {cell(current.client.name)}</p>
          <p><strong>תאריך לידה:</strong> {cell(current.client.birth_date)}</p>
          <p><strong>מועד פרישה מתוכנן:</strong> {cell(current.client.planned_retirement_date)}
            {current.client.planned_retirement_age != null ? ` (גיל ${current.client.planned_retirement_age})` : ""}</p>
          <p><strong>מצב תעסוקה:</strong> {cell(current.client.employment_status)}</p>
        </section>
        <section><h2>מוצרים פנסיוניים</h2>
          <table><thead><tr><th>מוצר</th><th>גוף מנהל</th><th>סוג</th><th>יתרה מדווחת</th><th>תאריך</th><th>סטטוס</th></tr></thead>
            <tbody>{current.pension_products.length ? current.pension_products.map((p, i) =>
              <tr key={i}><td>{p.name}</td><td>{cell(p.provider)}</td><td>{p.type}</td>
                <td>{amount(p.reported_total)}</td><td>{cell(p.statement_date)}</td><td>{p.verification}</td></tr>) :
              <tr><td colSpan={6}>{missing}</td></tr>}</tbody></table>
        </section>
        <section><h2>נכסי הון</h2>
          <table><thead><tr><th>נכס</th><th>סוג</th><th>שווי מדווח</th><th>תאריך</th><th>אימות</th></tr></thead>
            <tbody>{current.capital_assets.length ? current.capital_assets.map((a,i)=>
              <tr key={i}><td>{a.name}</td><td>{a.category}</td><td>{amount(a.value)}</td>
                <td>{cell(a.value_date)}</td><td>{a.verification}</td></tr>) :
              <tr><td colSpan={5}>{missing}</td></tr>}</tbody></table>
        </section>
        <section><h2>הכנסות והוצאות שוטפות מדווחות</h2>
          <table><thead><tr><th>סוג</th><th>פריט</th><th>סכום מדווח</th><th>תדירות</th><th>אימות</th></tr></thead>
          <tbody>{[...current.incomes.map(i=>({kind:"הכנסה",name:i.name,amount:i.amount,frequency:i.frequency,verification:i.verification})),
            ...current.expenses.map(e=>({kind:"הוצאה",name:e.name,amount:e.amount,frequency:e.frequency,verification:e.verification}))].map((row,i)=>
              <tr key={i}><td>{row.kind}</td><td>{row.name}</td><td>{amount(row.amount)}</td><td>{row.frequency}</td><td>{row.verification}</td></tr>)}
          {!current.incomes.length && !current.expenses.length && <tr><td colSpan={5}>{missing}</td></tr>}</tbody></table>
          <p>הסכומים הם נתונים מדווחים, אינם תחזית ואינם מסוכמים לתזרים מחושב.</p>
        </section>
        <section><h2>חלופה מועדפת ונימוק</h2>
          {current.preferred ? <>
            <p><strong>חלופה:</strong> {current.preferred.name}</p>
            <p><strong>גרסה בעת הבחירה:</strong> {current.preferred.version_at_selection}</p>
            <p><strong>נימוק המתכנן:</strong> {cell(current.preferred.rationale)}</p>
            {current.preferred.outdated && <p className="m12-warning">הבחירה אינה עדכנית ודורשת בדיקה מחדש.</p>}
          </> : <p className="m12-warning">לא תועדה חלופה מועדפת.</p>}
        </section>
        <section><h2>חלופות והחלטות תכנון</h2>
          {current.scenarios.length ? current.scenarios.map((s,i)=><section key={i}>
            <h3>{s.name}{s.preferred ? " (מועדפת)" : ""} - גרסה {s.version}</h3>
            {s.status !== "draft" && <p className="m12-warning">סטטוס חלופה: {s.status}</p>}
            <table><thead><tr><th>רכיב</th><th>פעולה</th><th>סכום הצהרה</th><th>מועד</th><th>מצב אימות</th></tr></thead>
              <tbody>{s.decisions.length ? s.decisions.map((d,j)=><tr key={j}>
                <td>{d.component}</td><td>{d.action}</td><td>{amount(d.declared_amount)}</td>
                <td>{d.effective_date}</td><td>{d.validation_state} - לא תוצאת חישוב</td>
              </tr>) : <tr><td colSpan={5}>לא תועדו החלטות בחלופה.</td></tr>}</tbody></table>
          </section>) : <p>{missing}</p>}
        </section>
        <section><h2>הנחות מקצועיות</h2>
          {current.assumptions.length ? <ul>{current.assumptions.map((a,i)=>
            <li key={i}>{a.title}: {a.value}. {a.rationale}</li>)}</ul> : <p>{missing}</p>}
        </section>
        <section><h2>מידע חסר</h2>
          {current.missing_information.length ? <ul>{current.missing_information.map((a,i)=>
            <li key={i}>{a.label} ({a.status})</li>)}</ul> : <p>לא תועד מידע חסר ברשומות הרלוונטיות.</p>}
        </section>
        <section><h2>מגבלות ואזהרות</h2>
          {current.warnings.map((a,i)=><p key={i} className="m12-warning">{a}</p>)}
          <p>תוצאות M09, M10 ו-Stage 6 אינן משויכות באופן מאומת לבחירת M11.
            אין במסמך תחזית קצבה, מס, פטור או תזרים שנוצרה לצורך הפקתו.</p>
        </section>
        <footer><p>טיוטה למטרות בחינה מקצועית. אין להסתמך עליה כאישור לתוצאות חסומות או בלתי מאומתות.</p></footer>
      </article>
    </>}
  </section>;
}
