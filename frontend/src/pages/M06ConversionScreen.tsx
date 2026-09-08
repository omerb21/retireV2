import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { formatIsoDate, formatIsoTimestamp } from "../utils/dateFormat";
import { heLabel } from "../i18n/he";
import { getM06History, getM06Subject, listM06Subjects, type M06Revision, type M06Subject } from "../api/m06ConversionApi";

function HistoricalSubject({ clientId, subjectId }: { clientId: number; subjectId: string }) {
  const [detail, setDetail] = useState<M06Subject | null>(null);
  const [history, setHistory] = useState<M06Revision[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([getM06Subject(clientId, subjectId), getM06History(clientId, subjectId)])
      .then(([item, trail]) => { if (active) { setDetail(item); setHistory(trail); } })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [clientId, subjectId]);
  if (failed) return <p role="alert">לא ניתן לטעון את התיעוד ההיסטורי.</p>;
  if (!detail) return <p>טוען תיעוד היסטורי…</p>;
  return <section aria-label="היסטוריית המרה לקריאה בלבד">
    <h3>היסטוריה בלתי ניתנת לשינוי</h3>
    <p>התיעוד אינו מקור ליתרות נוכחיות ואינו אישור לשימוש מקצועי חדש.</p>
    <ol>{history.map((row) => <li key={row.revision_id}>
      <p>גרסה {row.revision_sequence}: {heLabel(row.state)}; {formatIsoTimestamp(row.created_at)}</p>
      <p>קלט היסטורי: {row.input_amount ?? "חסר"}; תאריך: {formatIsoDate(row.input_date) || "לא תועד"}</p>
      <p>מקדם מתועד: {row.coefficient.coefficient}; תוצאה מתועדת: {row.manifest?.display_result ?? "אין"}</p>
      <details><summary>ראיות טכניות שמורות</summary><pre dir="ltr">{JSON.stringify(row, null, 2)}</pre></details>
    </li>)}</ol>
    {!history.length ? <p>אין גרסאות היסטוריות.</p> : null}
  </section>;
}

function Archive({ clientId }: { clientId: number }) {
  const [subjects, setSubjects] = useState<M06Subject[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    listM06Subjects(clientId).then((items) => { if (active) setSubjects(items); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [clientId]);
  return <main dir="rtl">
    <h2>M06 — תיעוד המרות היסטורי</h2>
    <p role="status">המרה חדשה ועדכון המרה אינם זמינים עד לאישור חוזה המרה למקור הקנוני.</p>
    <p><Link to={`/clients/${clientId}/pension-products`}>מוצרים פנסיוניים נוכחיים</Link></p>
    <p><Link to={`/clients/${clientId}`}>חזרה ללקוח</Link></p>
    {failed ? <p role="alert">לא ניתן לטעון את רשימת ההמרות ההיסטוריות.</p> :
      subjects === null ? <p>טוען רשומות היסטוריות…</p> :
      subjects.length ? <ul>{subjects.map((item, index) => <li key={item.subject_id}>
        <button onClick={() => setSelected(item.subject_id)}>תיעוד היסטורי {index + 1} — {heLabel(item.mode)}</button>
      </li>)}</ul> : <p>אין המרות היסטוריות.</p>}
    {selected ? <HistoricalSubject key={selected} clientId={clientId} subjectId={selected} /> : null}
  </main>;
}

export function M06ConversionScreen() {
  const { clientId } = useParams();
  const location = useLocation();
  if (!clientId || !/^\d+$/.test(clientId)) return <p role="alert">מזהה הלקוח אינו תקין.</p>;
  return <Archive key={location.key} clientId={Number(clientId)} />;
}
