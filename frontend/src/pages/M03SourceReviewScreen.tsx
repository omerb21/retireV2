import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getClient, type ClientDetailItem } from "../api/clientsApi";
import {
  addM03Annotation, decideM03Review, downloadM03Source, getM03Annotations,
  getM03Eligibility, getM03History, getM03Target, listM03Candidates, startM03Review,
  type M03Annotation, type M03Revision, type M03Target
} from "../api/m03ReviewApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";

const message = (error: unknown) => error instanceof Error ? error.message : "M03 request failed";

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
      const [next, revisions, notes, eligibility] = await Promise.all([
        getM03Target(clientId, target.intake_id), getM03History(clientId, target.intake_id),
        getM03Annotations(clientId, target.intake_id), getM03Eligibility(clientId, target.intake_id)
      ]);
      if (!isCurrentClientContext(token)) return;
      setTarget({ ...next, ...eligibility }); setHistory(revisions); setAnnotations(notes); setReason(""); setTopic(""); setNote("");
      setSupersedesAnnotationId("");
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setSubmitting(false);
    }
  };

  if (clientId === null) return <p>Invalid client ID.</p>;
  const archived = client?.m01_case?.lifecycle_status === "archived";
  const current = target?.current_revision ?? null;
  return (
    <section>
      <h2>M03 Source Review</h2>
      <p>Review eligibility is technical only. It is not parsing, classification, professional authority, calculation readiness, M04 acceptance, or M05 readiness.</p>
      {archived ? <p>Archived case: review and annotation history are read-only.</p> : null}
      {loading ? <p>Loading M03 review...</p> : null}
      {error ? <pre>{error}</pre> : null}
      <h3>Review candidates</h3>
      {candidates.length === 0 ? <p>No M02 records currently accepted for review.</p> : (
        <ul>{candidates.map((row) => <li key={row.intake_id}>
          <button type="button" onClick={() => void loadTarget(row.intake_id)}>
            {row.target_kind === "manual_record_review" ? "Manual record" : "Uploaded source"} — {row.intake_id}
          </button>
        </li>)}</ul>
      )}
      <label>Open retained review by M02 intake ID
        <input value={retainedIntakeId} onChange={(event) => setRetainedIntakeId(event.target.value)} />
      </label>
      <button type="button" disabled={!retainedIntakeId.trim()} onClick={() => void loadTarget(retainedIntakeId.trim())}>
        Open retained review
      </button>
      {target ? <section>
        <h3>Review target</h3>
        <p>Kind: {target.target_kind}; M02 lifecycle: {target.m02_lifecycle_status}</p>
        {target.target_kind === "manual_record_review"
          ? <p>Manual record: no external source, blob, or checksum evidence.</p>
          : <><p>Source: {target.source_id}; blob: {target.blob_id}; checksum: {target.sha256_checksum}</p>
            <button type="button" onClick={() => target.source_id && void downloadM03Source(clientId, target.source_id)}>Download preserved M02 source</button></>}
        <p>Eligibility: {target.eligible ? "eligible for a separately authorized downstream transformation" : `not eligible — ${target.exclusion_reason}`}</p>
        <fieldset disabled={archived || submitting}>
          {!current ? <button type="button" onClick={() => void mutate(() => startM03Review(clientId, target.intake_id))}>Start review</button> : null}
          <label>Decision/reopen reason <textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label>
          {current?.state === "under_review" ? <>
            <button type="button" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "accept", reason, current.revision_id))}>Accept review</button>
            <button type="button" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "reject", reason, current.revision_id))}>Reject review</button>
          </> : null}
          {current && current.state !== "under_review" ? <button type="button" disabled={!reason.trim()} onClick={() => void mutate(() => decideM03Review(clientId, target.intake_id, "reopen", reason, current.revision_id))}>Reopen review</button> : null}
          {current ? <>
            <h4>Add annotation</h4>
            <label>Topic <input value={topic} onChange={(event) => setTopic(event.target.value)} /></label>
            <label>Note <textarea value={note} onChange={(event) => setNote(event.target.value)} /></label>
            <label>Reason <textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <label>Supersede existing annotation
              <select value={supersedesAnnotationId} onChange={(event) => setSupersedesAnnotationId(event.target.value)}>
                <option value="">None — add a new annotation</option>
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
            }))}>Save annotation</button>
          </> : null}
        </fieldset>
        <h4>Immutable review history</h4>
        <ol>{history.map((row) => <li key={row.revision_id}>#{row.revision_sequence} {row.state} — {row.reason ?? "started"} — {row.actor}</li>)}</ol>
        <h4>Annotation history</h4>
        <ul>{annotations.map((row) => <li key={row.annotation_id}>
          {row.topic}: {row.note} — {row.reason}
          {row.supersedes_annotation_id ? ` — supersedes ${row.supersedes_annotation_id}` : ""}
        </li>)}</ul>
      </section> : null}
      <p><Link to={`/clients/${clientId}`}>Back to M01 client case</Link></p>
    </section>
  );
}
