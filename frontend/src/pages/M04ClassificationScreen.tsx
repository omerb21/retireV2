import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  ApiTransportError, getClient, type ClientDetailItem,
} from "../api/clientsApi";
import {
  actOnM04, getM04Eligibility, getM04History,
  getM04MatchedRules, getM04Target, listM04Targets, overrideM04,
  previewM04Rules, type M04Component,
  type M04ComponentInterpretation, type M04ComponentKind,
  type M04ProductFamily, type M04Revision, type M04RulePreview,
  type M04Target,
} from "../api/m04ClassificationApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { heLabel, technicalCode } from "../i18n/he";
import { formatIsoTimestamp } from "../utils/dateFormat";

const PRODUCT_FAMILIES: M04ProductFamily[] = [
  "insurance_policy", "savings_policy", "provident_fund",
  "investment_provident_fund", "education_fund", "pension_fund",
  "unknown_or_unresolved",
];
const COMPONENT_KINDS: M04ComponentKind[] = [
  "severance_component", "contribution_component", "unknown_component",
];
const INTERPRETATIONS: M04ComponentInterpretation[] = [
  "pension", "capital", "unresolved",
];
type ComponentDraft = {
  evidenceIdentity: string; originalLabel: string | null; originalCode: string | null;
  componentKind: M04ComponentKind; interpretation: M04ComponentInterpretation;
  currentEmployerRelated: "yes" | "no" | "unknown"; explanation: string;
};
const apiDetail = (error: unknown) => {
  if (!(error instanceof ApiTransportError) ||
    typeof error.body !== "object" || error.body === null) return null;
  const detail = (error.body as { detail?: unknown }).detail;
  if (typeof detail !== "object" || detail === null || Array.isArray(detail)) return null;
  const code = (detail as { code?: unknown }).code;
  const detailMessage = (detail as { message?: unknown }).message;
  return {
    code: typeof code === "string" ? code : null,
    message: typeof detailMessage === "string" ? detailMessage : null,
  };
};
const message = (error: unknown, refreshed = false) => {
  const detail = apiDetail(error);
  if (detail?.code === "M04_STALE_CURRENT_REVISION") {
    return `הצעת הסיווג השתנתה לפני הפעולה. ${refreshed ? "מצב הסיווג העדכני נטען מחדש. " : ""}${technicalCode(detail.code)}`;
  }
  if (detail?.message || detail?.code) {
    return `${detail.message ?? "בקשת M04 נכשלה"}${detail.code ? ` (${technicalCode(detail.code)})` : ""}${refreshed ? " מצב הסיווג העדכני נטען מחדש." : ""}`;
  }
  return error instanceof Error ? error.message : "בקשת M04 נכשלה";
};
const draftsFrom = (rows: M04Component[]): ComponentDraft[] => rows.map((row) => ({
  evidenceIdentity: row.evidence_identity,
  originalLabel: row.original_label,
  originalCode: row.original_code,
  componentKind: row.component_kind,
  interpretation: row.interpretation,
  currentEmployerRelated: row.current_employer_related,
  explanation: row.explanation || "נימוק הסיווג של המתכנן",
}));
const evidenceText = (value: unknown) => value === null || value === undefined || value === ""
  ? "לא קיים" : typeof value === "string" ? value : JSON.stringify(value);

function RuleEvidenceView({ rule }: { rule: Record<string, unknown> }) {
  return <dl className="m04-rule-evidence">
    <dt>גרסת קטלוג</dt><dd>{evidenceText(rule.catalogue_version)}</dd>
    <dt>מזהה כלל</dt><dd>{evidenceText(rule.rule_id)}</dd>
    <dt>סוג התאמה</dt><dd>{evidenceText(rule.matcher_type)}</dd>
    <dt>ערך התאמה מדויק</dt><dd>{evidenceText(rule.exact_matcher_value)}</dd>
    <dt>תחום הכלל</dt><dd>{evidenceText(rule.scope)}</dd>
    <dt>תחום הגוף המנהל</dt><dd>{evidenceText(rule.provider_scope)}</dd>
    <dt>תחום פורמט המקור</dt><dd>{evidenceText(rule.source_format_scope)}</dd>
    <dt>משפחת המוצר בפלט</dt><dd>{evidenceText(rule.output_product_family)}</dd>
    <dt>סוג הרכיב בפלט</dt><dd>{evidenceText(rule.output_component_kind)}</dd>
    <dt>פרשנות הפלט</dt><dd>{evidenceText(rule.output_interpretation)}</dd>
    <dt>נימוק</dt><dd>{evidenceText(rule.rationale)}</dd>
    <dt>אסמכתת ראיה או סמכות</dt><dd>{evidenceText(rule.authority_reference)}</dd>
    <dt>התנהגות בעת סתירה</dt><dd>{evidenceText(rule.conflict_behavior)}</dd>
  </dl>;
}

function ComponentEvidenceView({ component }: { component: M04Component }) {
  return <li>
    <p>זהות ראיה: {component.evidence_identity}; תיאור מקורי: {component.original_label ?? "אין"}; קוד מקורי: {component.original_code ?? "אין"}.</p>
    <p>החלטה: {component.component_kind}; פרשנות: {component.interpretation}; קשור למעסיק הנוכחי: {component.current_employer_related}.</p>
    <p>הסבר: {component.explanation}</p>
    <h6>כללים תואמים לרכיב</h6>
    {component.matched_rule_evidence.length
      ? component.matched_rule_evidence.map((rule, index) =>
        <RuleEvidenceView key={String(rule.rule_id ?? index)} rule={rule} />)
      : <p>לא נשמרו ראיות לכללי רכיב.</p>}
  </li>;
}

function RevisionEvidenceView({ revision, current, boundToCurrentEvidence }:
  { revision: M04Revision; current: boolean; boundToCurrentEvidence: boolean }) {
  const unresolved = revision.action_evidence.unresolved_reasons;
  const conflicts = revision.action_evidence.conflicts;
  return <li>
    <h5>גרסה #{revision.revision_sequence} — {current
      ? boundToCurrentEvidence
        ? "הגרסה הנוכחית — קשורה לראיות המקור העדכניות"
        : "הגרסה הנוכחית — אינה סמכותית לראיות המקור העדכניות"
      : "היסטורית"}</h5>
    <p>מצב: {heLabel(revision.state)}; פעולה: {heLabel(revision.action_type)}; גורם מבצע: {revision.actor}; מועד: {formatIsoTimestamp(revision.created_at)}.</p>
    <p>גרסה קודמת: {revision.predecessor_revision_id ?? "ראשונה"}; קטלוג: {revision.catalogue_version}; בסיס התאמה: {revision.match_basis}.</p>
    <p>קוד נימוק: {revision.reason_code ?? "אין"}; נימוק: {revision.reason ?? "אין"}; הסבר: {revision.explanation ?? "אין"}.</p>
    <p>החלטת משפחת מוצר: {revision.product_family ?? "אין"}; תת־סוג: {revision.pension_subtype ?? "אין"}; פרשנות מצרפית: {revision.aggregate_interpretation ?? "אין"}.</p>
    <p>ראיות פעולה: {JSON.stringify(revision.action_evidence)}</p>
    {unresolved ? <p>נימוקי אי־הכרעה שנשמרו: {evidenceText(unresolved)}</p> : null}
    {conflicts ? <p>סתירות שנשמרו: {evidenceText(conflicts)}</p> : null}
    <h6>כללים תואמים לגרסה</h6>
    {revision.matched_rule_evidence.length
      ? revision.matched_rule_evidence.map((rule, index) =>
        <RuleEvidenceView key={String(rule.rule_id ?? index)} rule={rule} />)
      : <p>לא נשמרו ראיות לכללים ברמת הגרסה.</p>}
    <h6>החלטות רכיב שנשמרו</h6>
    {revision.components.length
      ? <ul>{revision.components.map((component) =>
        <ComponentEvidenceView key={component.component_decision_id} component={component} />)}</ul>
      : <p>לא נשמרו החלטות רכיב לגרסה זו.</p>}
  </li>;
}

export function M04ClassificationScreen() {
  const { clientId: raw } = useParams();
  const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(clientId, location.key);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [targets, setTargets] = useState<M04Target[]>([]);
  const [target, setTarget] = useState<M04Target | null>(null);
  const [history, setHistory] = useState<M04Revision[]>([]);
  const [preview, setPreview] = useState<M04RulePreview | null>(null);
  const [rules, setRules] = useState<Record<string, unknown>[]>([]);
  const [retainedId, setRetainedId] = useState("");
  const [reasonCode, setReasonCode] = useState("planner_decision");
  const [explanation, setExplanation] = useState("");
  const [family, setFamily] = useState<M04ProductFamily>("unknown_or_unresolved");
  const [components, setComponents] = useState<ComponentDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const listEpoch = useRef(0);
  const detailEpoch = useRef(0);
  const previewEpoch = useRef(0);
  const mutationEpoch = useRef(0);
  const selectedTarget = useRef<string | null>(null);
  const selectedRevision = useRef<string | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      listEpoch.current += 1; detailEpoch.current += 1;
      previewEpoch.current += 1; mutationEpoch.current += 1;
      selectedTarget.current = null; selectedRevision.current = null;
    };
  }, []);

  useEffect(() => {
    listEpoch.current += 1; detailEpoch.current += 1;
    previewEpoch.current += 1; mutationEpoch.current += 1;
    selectedTarget.current = null; selectedRevision.current = null;
    setClient(null); setTargets([]); setTarget(null); setHistory([]);
    setPreview(null); setRules([]); setRetainedId(""); setExplanation("");
    setFamily("unknown_or_unresolved"); setComponents([]);
    setError(null); setLoading(false); setSubmitting(false);
  }, [clientId, location.key]);

  useEffect(() => {
    selectedRevision.current = target?.current_revision?.revision_id ?? null;
  }, [target?.current_revision?.revision_id]);

  const bindRevision = useCallback((revision: M04Revision | null) => {
    if (!revision) return;
    setFamily(revision.product_family ?? "unknown_or_unresolved");
    setComponents(draftsFrom(revision.components));
  }, []);

  const loadTargets = useCallback(async () => {
    if (clientId === null) return;
    const token = captureClientContext(); const request = ++listEpoch.current;
    const owned = () => mounted.current && request === listEpoch.current &&
      isCurrentClientContext(token);
    setLoading(true); setError(null);
    try {
      const [nextClient, rows] = await Promise.all([
        getClient(clientId), listM04Targets(clientId),
      ]);
      if (!owned()) return;
      setClient(nextClient); setTargets(rows);
    } catch (cause) {
      if (owned()) setError(message(cause));
    } finally {
      if (owned()) setLoading(false);
    }
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadTargets(); }, [loadTargets]);

  const loadTarget = useCallback(async (intakeId: string) => {
    if (clientId === null) return;
    const token = captureClientContext(); const request = ++detailEpoch.current;
    previewEpoch.current += 1; mutationEpoch.current += 1;
    selectedTarget.current = intakeId; selectedRevision.current = null;
    const owned = () => mounted.current && request === detailEpoch.current &&
      selectedTarget.current === intakeId && isCurrentClientContext(token);
    setLoading(true); setSubmitting(false); setError(null); setPreview(null);
    setTarget(null); setHistory([]); setRules([]); setComponents([]);
    try {
      const [next, revisions, eligibility, matched] = await Promise.all([
        getM04Target(clientId, intakeId), getM04History(clientId, intakeId),
        getM04Eligibility(clientId, intakeId), getM04MatchedRules(clientId, intakeId),
      ]);
      if (!owned()) return;
      const combined = { ...next, eligibility };
      selectedRevision.current = combined.current_revision?.revision_id ?? null;
      setTarget(combined); setHistory(revisions); setRules(matched);
      bindRevision(combined.current_revision);
    } catch (cause) {
      if (owned()) setError(message(cause));
    } finally {
      if (owned()) setLoading(false);
    }
  }, [bindRevision, captureClientContext, clientId, isCurrentClientContext]);

  const runPreview = async () => {
    if (clientId === null || !target) return;
    const token = captureClientContext(); const intakeId = target.intake_id;
    const revisionId = target.current_revision?.revision_id ?? null;
    const request = ++previewEpoch.current;
    const owned = () => mounted.current && request === previewEpoch.current &&
      selectedTarget.current === intakeId && selectedRevision.current === revisionId &&
      isCurrentClientContext(token);
    setLoading(true); setError(null);
    try {
      const next = await previewM04Rules(clientId, intakeId);
      if (!owned()) return;
      setPreview(next); setFamily(next.product_family);
      setComponents(draftsFrom(next.components));
    } catch (cause) {
      if (owned()) setError(message(cause));
    } finally {
      if (owned()) setLoading(false);
    }
  };

  const mutate = async (
    operation: (expectedRevisionId: string | null) => Promise<unknown>,
  ) => {
    if (clientId === null || !target) return;
    const token = captureClientContext(); const intakeId = target.intake_id;
    const currentRevisionId = target.current_revision?.revision_id ?? null;
    const request = ++mutationEpoch.current;
    previewEpoch.current += 1; setPreview(null); setLoading(false);
    const contextOwned = () => mounted.current && request === mutationEpoch.current &&
      selectedTarget.current === intakeId && isCurrentClientContext(token);
    const owned = () => contextOwned() &&
      selectedTarget.current === intakeId &&
      selectedRevision.current === currentRevisionId &&
      isCurrentClientContext(token);
    setSubmitting(true); setError(null);
    try {
      await operation(currentRevisionId);
      if (!owned()) return; // stale mutation launches zero refreshes
      const refreshToken = captureClientContext();
      const detailRequest = ++detailEpoch.current;
      const listRequest = ++listEpoch.current;
      const [next, revisions, eligibility, matched, rows] = await Promise.all([
        getM04Target(clientId, intakeId), getM04History(clientId, intakeId),
        getM04Eligibility(clientId, intakeId), getM04MatchedRules(clientId, intakeId),
        listM04Targets(clientId),
      ]);
      if (!owned() || !isCurrentClientContext(refreshToken) ||
        detailRequest !== detailEpoch.current || listRequest !== listEpoch.current) return;
      const combined = { ...next, eligibility };
      selectedRevision.current = combined.current_revision?.revision_id ?? null;
      setTarget(combined); setHistory(revisions); setRules(matched); setTargets(rows);
      setPreview(null); setExplanation(""); bindRevision(combined.current_revision);
    } catch (cause) {
      if (!owned()) return;
      let refreshed = false;
      if (cause instanceof ApiTransportError && cause.status === 409) {
        try {
          const [next, revisions, eligibility, matched, rows] = await Promise.all([
            getM04Target(clientId, intakeId), getM04History(clientId, intakeId),
            getM04Eligibility(clientId, intakeId), getM04MatchedRules(clientId, intakeId),
            listM04Targets(clientId),
          ]);
          if (contextOwned()) {
            const combined = { ...next, eligibility };
            selectedRevision.current = combined.current_revision?.revision_id ?? null;
            setTarget(combined); setHistory(revisions); setRules(matched); setTargets(rows);
            bindRevision(combined.current_revision);
            refreshed = true;
          }
        } catch {
          // Preserve the original structured conflict if a safe refresh is לא זמין.
        }
      }
      if (contextOwned()) setError(message(cause, refreshed));
    } finally {
      if (contextOwned()) setSubmitting(false);
    }
  };

  if (clientId === null) return <p>מזהה הלקוח אינו תקין.</p>;
  const current = target?.current_revision ?? null;
  const archived = target?.m01_lifecycle_status === "archived" ||
    client?.m01_case?.lifecycle_status === "archived";
  const reasonReady = Boolean(reasonCode.trim() && explanation.trim());
  const reasonPayload = current ? {
    expected_current_revision_id: current.revision_id,
    reason_code: reasonCode, explanation,
  } : null;
  const currentBoundToEvidence = Boolean(
    current && target?.m03_eligible &&
    current.input_snapshot.accepted_m03_revision_id ===
      target.m03_accepted_revision_id,
  );
  const overrideReady = reasonReady && family !== "unknown_or_unresolved" &&
    components.length > 0 && components.every((row) =>
      row.componentKind !== "unknown_component" && row.explanation.trim());
  const updateComponent = (id: string, patch: Partial<ComponentDraft>) =>
    setComponents((rows) => rows.map((row) =>
      row.evidenceIdentity === id ? { ...row, ...patch } : row));

  return <section>
    <h2>M04 — סיווג מקצועי</h2>
    <p>המערכת מסווגת אוטומטית כאשר הכללים חד־משמעיים. רק מקרה מקצועי לא מוכרע דורש החלטת מתכנן.</p>
    {archived ? <p>התיק בארכיון: M04 זמין לקריאה בלבד.</p> : null}
    {loading ? <p>טוען את סיווג M04...</p> : null}
    {error ? <pre role="alert">{error}</pre> : null}
    <h3>רשומות לסיווג</h3>
    {targets.length ? <ul>{targets.map((row) => <li key={row.intake_id}>
      <button type="button" aria-label={`${row.target_kind === "manual_record_review" ? "רשומה ידנית" : "מקור שהועלה"} — ${row.intake_id}`} onClick={() => void loadTarget(row.intake_id)}>
        {heLabel(row.target_kind)} — {row.intake_id}
      </button>
    </li>)}</ul> : <p>אין נתוני פנסיה שהתקבלו לסיווג.</p>}
    <label>פתיחת רשומה היסטורית לפי מזהה M02
      <input value={retainedId} onChange={(event) => setRetainedId(event.target.value)} />
    </label>
    <button type="button" disabled={!retainedId.trim()}
      onClick={() => void loadTarget(retainedId.trim())}>פתיחת רשומה היסטורית</button>

    {target ? <section>
      <h3>הרשומה הנבחרת לסיווג</h3>
      <p>גוף מנהל: {target.declared_provider_name ?? "לא נמסר"}; מוצר: {target.product_name ?? "לא נמסר"}; סוג: {target.declared_product_type ?? "לא נמסר"}.</p>
      <p>מצב מקצועי: {target.eligibility.eligible_for_m05
        ? "הסיווג הנוכחי הושלם ואפשר להמשיך לכרטסת M05."
        : current?.state === "unresolved"
          ? "נדרשת החלטה מקצועית לגבי סיווג המוצר והרכיבים."
          : "הסיווג הנוכחי טרם הושלם."}</p>
      {target.eligibility.eligible_for_m05 ? <p><Link to={`/clients/${clientId}/pension-ledger`}>המשך לכרטסת יתרות הפנסיה M05</Link></p> : null}
      {!target.eligibility.eligible_for_m05 && target.eligibility.exclusion_reason
        ? <small>{technicalCode(target.eligibility.exclusion_reason)}</small> : null}

      <fieldset disabled={archived || submitting}>
        <legend aria-label="החלטת סיווג מקצועית">החלטת סיווג מקצועית</legend>
        <button type="button" aria-label="תצוגה מקדימה של הכללים המדויקים" onClick={() => void runPreview()}>תצוגה מקדימה של הכללים המדויקים</button>
        <label>קוד נימוק
          <input aria-label="קוד נימוק" value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} />
        </label>
        <label>הסבר
          <textarea aria-label="הסבר" value={explanation} onChange={(event) => setExplanation(event.target.value)} />
        </label>
        {current && ["proposed", "unresolved", "rejected"].includes(current.state) ? <section>
          <h4>הכרעה מקצועית נדרשת</h4>
          <p>בחרו סיווג מלא עבור הנתונים הנוכחיים. השמירה משלימה את ההכרעה בפעולה אחת.</p>
          <label>משפחת מוצר
            <select value={family} onChange={(event) => setFamily(event.target.value as M04ProductFamily)}>
              {PRODUCT_FAMILIES.map((value) => <option key={value} value={value}>{heLabel(value)}</option>)}
            </select>
          </label>
          {components.map((row) => <fieldset key={row.evidenceIdentity}>
            <legend>{row.originalLabel ?? row.originalCode ?? row.evidenceIdentity}</legend>
            <label>סוג רכיב
              <select value={row.componentKind} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { componentKind: event.target.value as M04ComponentKind })}>
                {COMPONENT_KINDS.map((value) => <option key={value} value={value}>{heLabel(value)}</option>)}
              </select>
            </label>
            <label>פרשנות
              <select aria-label="פרשנות" value={row.interpretation} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { interpretation: event.target.value as M04ComponentInterpretation })}>
                {INTERPRETATIONS.map((value) => <option key={value} value={value}>{heLabel(value)}</option>)}
              </select>
            </label>
            <label>הסבר לרכיב
              <textarea value={row.explanation} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { explanation: event.target.value })} />
            </label>
          </fieldset>)}
          <button type="button" aria-label="שמירת ההכרעה המקצועית" disabled={!overrideReady}
            onClick={() => reasonPayload && void mutate(async () => {
              const proposal = await overrideM04(clientId, target.intake_id, {
                ...reasonPayload, confirmed: true, product_family: family,
                pension_subtype: null, components: components.map((row) => ({
                  evidence_identity: row.evidenceIdentity,
                  component_kind: row.componentKind,
                  interpretation: row.interpretation,
                  current_employer_related: row.currentEmployerRelated,
                  explanation: row.explanation,
                })),
              });
              return actOnM04(clientId, target.intake_id, "accept", {
                expected_current_revision_id: proposal.revision_id,
                reason_code: reasonCode,
                explanation,
              });
            })}>
            שמירת ההכרעה המקצועית
          </button>
        </section> : null}
      </fieldset>

      {preview ? <section>
        <h4>תצוגה מקדימה — ללא שמירה</h4>
        <p>קטלוג: {preview.catalogue_version}</p>
        <p>משפחה: {preview.product_family}</p>
        <p>נימוקי אי־הכרעה: {preview.unresolved_reasons.join(", ") || "אין"}</p>
        <p>סתירות: {preview.conflicts.join(", ") || "אין"}</p>
      </section> : null}
      <details>
        <summary>פרטים טכניים והיסטוריית ביקורת</summary>
        <p>{target.target_kind === "manual_record_review"
          ? "רשומה ידנית ללא קובץ מקור או checksum."
          : `מזהה המקור שהועלה: ${target.source_id ?? "לא זמין"}`}</p>
        <p>קוד מוצר: {target.product_identifier ?? "לא נמסר"}.</p>
        <p>נתוני הרכיב המקוריים: {target.declared_component_values.length
          ? JSON.stringify(target.declared_component_values) : "אין"}</p>
        <h4>ראיות הכללים התואמים הנוכחיים</h4>
        {rules.length ? rules.map((row, index) =>
          <RuleEvidenceView key={String(row.rule_id ?? index)} rule={row} />)
          : <p>לא נשמרו ראיות לכללים התואמים הנוכחיים.</p>}
        <h4>היסטוריית סיווג בלתי ניתנת לשינוי</h4>
        <ol>{history.map((row) => <RevisionEvidenceView key={row.revision_id}
          revision={row} current={row.revision_id === current?.revision_id}
          boundToCurrentEvidence={row.revision_id === current?.revision_id && currentBoundToEvidence} />)}</ol>
      </details>
    </section> : null}
    <p><Link to={`/clients/${clientId}`}>חזרה לתיק הלקוח M01</Link></p>
  </section>;
}
