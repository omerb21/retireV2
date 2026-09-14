import { Link, useParams } from "react-router-dom";
import { ProfessionalSourceSnapshot } from "../components/ProfessionalSourceSnapshot";

export function ProfessionalSourceSnapshotScreen() {
  const id = Number(useParams().clientId);
  if (!Number.isSafeInteger(id) || id <= 0) return <p role="alert">מזהה לקוח לא תקין</p>;
  return <main dir="rtl"><Link to={`/clients/${id}`}>חזרה לפרטי הלקוח</Link>{" · "}<Link to={`/clients/${id}/planning-input`}>בדיקת קלט בסיס לתכנון</Link><ProfessionalSourceSnapshot clientId={id} /></main>;
}
