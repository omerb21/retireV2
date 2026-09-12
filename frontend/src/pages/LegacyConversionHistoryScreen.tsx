import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { LegacyRevision, listLegacyConversions, legacyConversionHistory } from "../api/legacyConversionHistoryApi";
import { formatIsoTimestamp } from "../utils/dateFormat";

function Archive({ clientId }: { clientId: number }) {
  const [rows, setRows] = useState<LegacyRevision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    listLegacyConversions(clientId).then(subjects => Promise.all(subjects.map(subject => legacyConversionHistory(clientId, subject.subject_id))))
      .then(histories => { if (active) setRows(histories.flat()); })
      .catch(() => { if (active) setError("לא ניתן לטעון את ארכיון ההמרות"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientId]);
  return <section dir="rtl"><h2>היסטוריית המרות ישנה — לקריאה בלבד</h2>
    <p>רשומות אלה הן ארכיון ואינן מקור לסמכות מקצועית נוכחית.</p>
    <Link to={`/clients/${clientId}/pension-products`}>מוצרים פנסיוניים והמרת רכיבים</Link>
    {loading && <p>טוען היסטוריה...</p>}{error && <p role="alert">{error}</p>}
    {!loading && !error && !rows.length && <p>אין המרות היסטוריות</p>}
    {rows.map(row => <article key={row.revision_id}><p>תאריך תיעוד: <bdi>{formatIsoTimestamp(row.created_at)}</bdi></p>
      <p>סכום מקור היסטורי: <bdi>{row.input_amount ?? "לא תועד"}</bdi></p><p>מקדם היסטורי: <bdi>{row.coefficient.coefficient}</bdi></p>
      <p>תוצאה היסטורית לתצוגה: <bdi>{row.manifest?.display_result ?? "לא תועדה"}</bdi></p></article>)}
  </section>;
}
export function LegacyConversionHistoryScreen() {
  const { clientId } = useParams();
  if (!clientId || !/^[1-9]\d*$/.test(clientId) || !Number.isSafeInteger(Number(clientId))) return <p role="alert">מזהה הלקוח אינו תקין</p>;
  return <Archive key={clientId} clientId={Number(clientId)} />;
}
