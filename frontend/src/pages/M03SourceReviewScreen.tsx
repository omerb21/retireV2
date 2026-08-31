import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getClient, type ClientDetailItem } from "../api/clientsApi";
import {
  addM03Annotation, decideM03Review, downloadM03Source, getM03Annotations,
  getM03Eligibility, getM03History, getM03Target, listM03Candidates, startM03Review,
  type M03Annotation, type M03Revision, type M03Target
} from "../api/m03ReviewApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { heLabel, technicalCode } from "../i18n/he";

const message = (error: unknown) => error instanceof Error ? error.message : "בקשת M03 נכשלה";

export function M03SourceReviewScreen() {
  const { clientId: raw } = useParams();
  const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [candidates, setCandidates] = useState<M03Target[]>([]);
  const [target, setTarget] = useState<M03Target | null>(null);
  const [history, setHistory] = useState<M03Revision[]>([]);
  const [annotations, setAnnotations] = useState<M03Annotation[]>([]);
  const [reason, setReason] = useState("");
  const [topic, setTopic] = useState("");
  const [note, setNote] = useState("");
  const [supersedesAnnotationId, setSupersedesAnnotationId] = useState("");
  const [retainedIntakeId, setRetainedIntakeId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setClient(null); setCandidates([]); setTarget(null); setHistory([]); setAnnotations([]);
    setError(null); setLoading(false); setSubmitting(false); setReason(""); setTopic(""); setNote("");
    setSupersedesAnnotationId("");
    setRetainedIntakeId("");
  }, [clientId, location.key]);

  const loadCandidates = useCallback(async () => {
    if (clientId === null) return;
    const token = captureClientContext(); setLoading(true); setError(null);
    try {
      const [nextClient, rows] = await Promise.all([getClient(clientId), listM03Candidates(clientId)]);
      if (!isCurrentClientContext(token)) return;
      setClient(nextClient); setCandidates(rows);
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setLoading(false);
    }
  }, [clientId, captureClientContext, isCurrentClientContext]);

  useEffect(() => { void loadCandidates(); }, [loadCandidates]);

  const loadTarget = async (intakeId: string) => {
    if (clientId === null) return;
    const token = captureClientContext(); setLoading(true); setError(null);
    try {
      const [next, revisions, notes, eligibility] = await Promise.all([
        getM03Target(clientId, intakeId), getM03History(clientId, intakeId),
        getM03Annotations(clientId, intakeId), getM03Eligibility(clientId, intakeId)
      ]);
      if (!isCurrentClientContext(token)) return;
      setTarget({ ...next, ...eligibility }); setHistory(revisions); setAnnotations(notes);
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setLoading(false);
    }
  };

  const mutate = async (operation: () => Promise<unknown>) => {
    if (clientId === null || target === null) return;
    const token = captureClientContext(); setSubmitting(true); setError(null);
    try {
      await operation();
      if (!isCurrentClientContext(token)) return;
      const refreshToken = captureClientContext();
      const [next, revisions, notes, eligibility] = await Promise.all([
        getM03Target(clientId, target.intake_id), getM03History(clientId, target.intake_id),
        getM03Annotations(clientId, target.intake_id), getM03Eligibility(clientId, target.intake_id)
      ]);
      if (!isCurrentClientContext(refreshToken)) return;
      setTarget({ ...next, ...eligibility }); setHistory(revisions); setAnnotations(notes); setReason(""); setTopic(""); setNote("");
      setSupersedesAnnotationId("");
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setSubmitting(false);
    }
  };

  if (clientId === null) return <p>מזהה הלקוח אינו תקין.</p>;
  const archived = client?.m01_case?.lifecycle_status === "archived";
  const current = target?.current_revision ?? null;
  return (
    <section>
      <h2>M03 — בדיקת מקור</h2>
      <p>בדיקת המקור היא שלב טכני בלבד ואינה סיווג, אישור מקצועי או מוכנות לחישוב.</p>
      {archived ? <p>התיק בארכיון: הבדיקה וההערות זמינות לקריאה בלבד.</p> : null}
      {loading ? <p>טוען את בדיקת M03...</p> : null}
      {error ? <pre>{error}</pre> : null}
      <h3>רשומות הממתינות לבדיקה</h3>
      {candidates.length === 0 ? <p>אין כרגע רשומות M02 שהתקבלו לבדיקה.</p> : (
        <ul>{candidates.map((row) => <li key={row.intake_id}>
          <button type="button" aria-label={`${row.target_kind === "manual_record_review" ? "רשומה ידנית" : "מקור שהועלה"} — ${row.intake_id}`} onClick={() => void loadTarget(row.intake_id)}>
            {heLabel(row.target_kind)} — {row.intake_id}
          </button>
        </li>)}</ul>
      )}
      <label>פתיחת בדיקה היסטורית לפי מזהה קליטת M02
        <input aria-label="פתיחת בדיקה שמורה לפי מזהה קליטת M02" value={retainedIntakeId} onChange={(event) => setRetainedIntakeId(event.target.value)} />
      </label>
      <button type="button" aria-label="פתיחת בדיקה שמורה" disabled={!retainedIntakeId.trim()} onClick={() => void loadTarget(retainedIntakeId.trim())}>
        פתיחת בדיקה היסטורית
      </button>
      {target ? <section>
        <h3>פרטי הרשומה הנבדקת</h3>
        <p>סוג: {heLabel(target.target_kind)}; מצב M02: {heLabel(target.m02_lifecycle_status)}</p>
        {target.target_kind === "manual_record_review"
          ? <p>רשומה ידנית: אין קובץ מקור חיצוני או checksum.</p>
          : <><p>מקור: {target.source_id}; קובץ נתונים: {target.blob_id}; checksum: {target.sha256_checksum}</p>
            <button type="button" onClick={() => target.source_id && void downloadM03Source(clientId, target.source_id)}>הורדת מקור M02 השמור</button></>}
        <p>מצב נוכחי: {target.eligible ? "הבדיקה אושרה והיא עדכנית" : heLabel(target.exclusion_reason)}
        </p>
        {!target.eligible && target.exclusion_reason ? <small>{technicalCode(target.exclusion_reason)}</small> : null}
        <fieldset disabled={archived || submitting}>
          {!current ? <button type="button" aria-label="התחלת בדיקה" onClick={() => void mutate(() => startM03Review(clientId, target.intake_id))}>התחלת בדיקה</button> : null}
          <label>נימוק להחלטה או לפתיחה מחדש <textarea aria-label="נימוק להחלטה או לפתיחה מחדש" value={reason} onChange={(event) => setReason(event.target.value)} /></label>
          {current?.state === "under_review" ? <>
            <button type="button" aria-label="אישור הבדיקה" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "accept", reason, current.revision_id))}>אישור הבדיקה</button>
            <button type="button" aria-label="דחיית הבדיקה" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "reject", reason, current.revision_id))}>דחיית הבדיקה</button>
          </> : null}
          {current && current.state !== "under_review" ? <button type="button" aria-label="פתיחת הבדיקה מחדש" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "reopen", reason, current.revision_id))}>פתיחת הבדיקה מחדש</button> : null}
          {current ? <>
            <h4>הוספת הערה</h4>
            <label>נושא <input aria-label="נושא" value={topic} onChange={(event) => setTopic(event.target.value)} /></label>
            <label>הערה <textarea aria-label="הערה" value={note} onChange={(event) => setNote(event.target.value)} /></label>
            <label>נימוק <textarea aria-label="נימוק" value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <label>החלפת הערה קיימת
              <select aria-label="החלפת הערה קיימת" value={supersedesAnnotationId} onChange={(event) => setSupersedesAnnotationId(event.target.value)}>
                <option value="">ללא — הוספת הערה חדשה</option>
                {annotations.map((row) => (
                  <option key={row.annotation_id} value={row.annotation_id}>
                    {row.topic}: {row.annotation_id}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" disabled={!topic.trim() || !note.trim() || !reason.trim()} onClick={() => void mutate(() => addM03Annotation(clientId, target.intake_id, {
              review_revision_id: current.revision_id,
              topic,
              note,
              reason,
              ...(supersedesAnnotationId ? { supersedes_annotation_id: supersedesAnnotationId } : {}),
            }))} aria-label="שמירת הערה">שמירת הערה</button>
          </> : null}
        </fieldset>
        <h4>היסטוריית בדיקה בלתי ניתנת לשינוי</h4>
        <ol>{history.map((row) => <li key={row.revision_id}>#{row.revision_sequence} {heLabel(row.state)} — {row.reason ?? "התחלה"} — {row.actor}</li>)}</ol>
        <h4>היסטוריית הערות</h4>
        <ul>{annotations.map((row) => <li key={row.annotation_id}>
          {row.topic}: {row.note} — {row.reason}
          {row.supersedes_annotation_id ? ` — מחליפה את ${row.supersedes_annotation_id}` : ""}
        </li>)}</ul>
      </section> : null}
      <p><Link to={`/clients/${clientId}`}>חזרה לתיק הלקוח M01</Link></p>
    </section>
  );
}
