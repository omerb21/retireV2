import { useEffect, useState, type FormEvent } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import {
  readProfessionalReview, saveProfessionalReview, readProfessionalReviewHistory,
  ReviewApiError, type ProfessionalDecision, type ProfessionalReview,
  type ReviewGroup, type ReviewDetermination, type ReviewHistoryItem,
} from "../api/scenarioFixationProfessionalReviewApi";

interface Props { clientId: number; scenario: ScenarioDraft }
const GROUPS: Array<{ value: ReviewGroup; label: string }> = [
  { value: "eligibility", label: "מועד זכאות לקיבוע" },
  { value: "tax_year_and_parameters", label: "שנת מס ופרמטרים רשמיים" },
  { value: "pension_classification", label: "סיווג קצבה לצורכי מס" },
  { value: "historical_grant", label: "מענק היסטורי ומעמד תשלום" },
  { value: "severance_continuity", label: "פיצויים ורצפים מתוכננים" },
  { value: "historical_capitalization", label: "היוון היסטורי" },
  { value: "planned_withdrawal_or_commutation", label: "היוון או משיכת הון מתוכננים" },
];
const DETERMINATIONS: Array<{ value: ReviewDetermination; label: string }> = [
  { value: "REQUIRES_REVIEW", label: "נדרש בירור מקצועי" },
  { value: "PLANNER_ASSERTED", label: "הכרעת מתכנן לתיעוד, טרם אומתה לקיבוע" },
  { value: "EXCLUDE_PROPOSED", label: "החרגה מוצעת, טרם אושרה" },
];
const LABELS: Record<string, string> = {
  FIXATION_SCENARIO_TAX_YEAR_MISSING: "אין שנת מס מאומתת לחלופה.",
  FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING: "לא אומתה זכאות לקיבוע המשויכת לחלופה.",
  FIXATION_GRANTS_PAYMENT_AND_TAX_CLASSIFICATION_UNVERIFIED: "מעמד המענקים והתשלום לא אומת לצורכי מס.",
  FIXATION_PLANNED_SEVERANCE_NOT_ADMITTED: "החלטות רצף ומשיכה הן תכנון בלבד.",
  FIXATION_HISTORICAL_CAPITALIZATIONS_NOT_ADMITTED: "היוונים היסטוריים לא אושרו לקלט המס.",
  FIXATION_QUALIFYING_PENSION_CLASSIFICATION_MISSING: "לא בוצע סיווג מאומת של קצבה מזכה.",
  FIXATION_GRANT_COMPONENT_OVERLAP_UNRECONCILED: "קיימת חפיפה שלא הוכרעה בין מענק לפיצויים בקופה.",
  FIXATION_TAX_AUTHORITY_APPROVAL_NOT_ESTABLISHED: "אין אישור רשות המסים מאומת.",
  FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED: "שער האישור המקצועי טרם נפתח.",
  FIXATION_PROFESSIONAL_APPROVAL_STALE: "מקורות ההכרעה השתנו. יש לבדוק ולשמור מחדש.",
  FIXATION_REVIEW_M07_SOURCE_NOT_FINALIZED_OR_FOREIGN: "ראיית הזכאות אינה סופית או אינה שייכת ללקוח.",
  FIXATION_REVIEW_GRANT_SOURCE_NOT_FOUND: "המענק שנבחר אינו שייך ללקוח או אינו זמין.",
  FIXATION_REVIEW_CAPITALIZATION_SOURCE_NOT_FOUND: "ההיוון ההיסטורי אינו זמין.",
  FIXATION_REVIEW_SEVERANCE_SOURCE_NOT_FOUND: "בחירת הפיצויים שנבחרה אינה זמינה בחלופה.",
  FIXATION_REVIEW_SEVERANCE_SOURCE_BLOCKED: "בחירת הפיצויים אינה תקפה.",
  FIXATION_REVIEW_PENSION_SOURCE_NOT_FOUND: "רכיב הקצבה אינו נמצא בחלופה.",
  FIXATION_REVIEW_CAPITAL_SOURCE_NOT_FOUND: "רכיב ההון אינו נמצא בחלופה.",
  FIXATION_REVIEW_PARAMETER_SET_NOT_FOUND: "סט הפרמטרים הרשמי אינו זמין.",
  FIXATION_REVIEW_PARAMETER_SCOPE_NOT_ESTABLISHED: "שנת המס או מועד הזכאות אינם תואמים לפרמטרים.",
  FIXATION_REVIEW_PARAMETER_SET_NOT_APPLICABLE: "סט הפרמטרים אינו פעיל או אינו חל על המועד.",
  FIXATION_REVIEW_ELIGIBILITY_DATES_CONFLICT: "יש סתירה בין מועדי זכאות שנבחרו.",
};
function label(code: string) { return LABELS[code] ?? `חסם מקצועי: ${code}`; }
function groupName(group: ReviewGroup): string {
  return GROUPS.find(item => item.value === group)?.label ?? group;
}
function emptyDecision(): ProfessionalDecision {
  return {
    group: "eligibility", source_id: "", determination: "REQUIRES_REVIEW",
    reason: "", evidence_references: [], eligibility_date: null, tax_year: null,
    parameter_set_id: null, tax_classification: null,
  };
}
function message(error: unknown): string {
  if (error instanceof ReviewApiError) {
    return error.status === 409
      ? "התנגשות גרסה או שינוי מקור. הנתונים העדכניים נטענו, אך ההכרעות שהזנת נשמרו בטופס לבדיקה."
      : error.status === 422 ? "השרת חסם את הפעולה בשל תנאים מקצועיים שלא הושלמו."
        : `לא ניתן להשלים את הפעולה (${error.code}).`;
  }
  return error instanceof Error ? error.message : "אירעה תקלה בטעינת ההכרעות.";
}
function sourcesFor(group: ReviewGroup, review: ProfessionalReview, scenario: ScenarioDraft) {
  const evidence = review.current_readiness.source_evidence;
  switch (group) {
    case "eligibility":
      return evidence.m07.map(row => ({ id: row.revision_id, label: `ראיית זכאות M07: ${row.revision_id} (${row.status})` }));
    case "historical_grant":
      return evidence.grants.map(row => ({ id: row.grant_id, label: `מענק: ${row.grant_id} (${row.payment_classification})` }));
    case "severance_continuity":
      return evidence.severance_choice_source_ids.map(row => ({ id: row.source_id, label: `בחירת פיצויים: ${row.source_id} (${row.state})` }));
    case "historical_capitalization":
      return evidence.historical_capitalizations.map(row => ({
        id: row.capitalization_id, label: `היוון: ${row.source_label ?? row.capitalization_id} (${row.reported_amount_ils} ₪)`,
      }));
    case "pension_classification":
      return scenario.decisions.filter(row => row.action === "pension").map(row => ({
        id: row.decision_id, label: `קצבה מתוכננת: ${row.component_code} (${row.amount} ₪)`,
      }));
    case "planned_withdrawal_or_commutation":
      return scenario.decisions.filter(row => row.action === "capital_asset").map(row => ({
        id: row.decision_id, label: `הון מתוכנן: ${row.component_code} (${row.amount} ₪)`,
      }));
    case "tax_year_and_parameters":
      return []; // Explicit ID required; readiness does not supply approved parameters.
  }
}
const sameKey = (a: ProfessionalDecision, b: ProfessionalDecision) =>
  a.group === b.group && a.source_id === b.source_id;

export function ScenarioFixationProfessionalReviewPanel({ clientId, scenario }: Props) {
  const [review, setReview] = useState<ProfessionalReview | null>(null);
  const [draft, setDraft] = useState<ProfessionalDecision[]>([]);
  const [item, setItem] = useState<ProfessionalDecision>(emptyDecision);
  const [refsText, setRefsText] = useState("");
  const [history, setHistory] = useState<ReviewHistoryItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [serverBlockers, setServerBlockers] = useState<string[]>([]);

  useEffect(() => {
    let mounted = true;
    setReview(null); setDraft([]); setItem(emptyDecision()); setRefsText("");
    setHistory(null); setError(null); setNotice(null); setConflict(false);
    setServerBlockers([]); setLoading(true);
    void readProfessionalReview(clientId, scenario.scenario_id)
      .then(result => {
        if (!mounted) return;
        setReview(result);
        setDraft(result.decisions.map(row => ({ ...row, evidence_references: [...row.evidence_references] })));
      })
      .catch(cause => { if (mounted) setError(message(cause)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [clientId, scenario.scenario_id]);

  const sources = review ? sourcesFor(item.group, review, scenario) : [];
  const editable = scenario.status === "draft" && !loading && !busy && review !== null
    && review.current_readiness.scenario_version === scenario.version;
  function edit(row: ProfessionalDecision) {
    setItem({ ...row, evidence_references: [...row.evidence_references] });
    setRefsText(row.evidence_references.join("\n"));
    setNotice(null);
  }
  function add(event: FormEvent) {
    event.preventDefault();
    const parsed = refsText.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    if (!item.source_id.trim() || !item.reason.trim() ||
        parsed.some(value => value.length > 256) || new Set(parsed).size !== parsed.length) {
      setError("יש למלא מקור, הנמקה ואסמכתאות ללא כפילויות.");
      return;
    }
    const next: ProfessionalDecision = {
      ...item, source_id: item.source_id.trim(), reason: item.reason.trim(),
      evidence_references: parsed,
    };
    setDraft(current => [...current.filter(row => !sameKey(row, next)), next]);
    setItem(emptyDecision()); setRefsText(""); setError(null);
    setNotice("ההכרעה נוספה לטיוטת המסך. לשמירה בשרת יש ללחוץ על שמור טיוטה.");
  }
  async function reload({ preserve = false }: { preserve?: boolean } = {}) {
    const fresh = await readProfessionalReview(clientId, scenario.scenario_id);
    setReview(fresh);
    if (!preserve) {
      setDraft(fresh.decisions.map(row => ({ ...row, evidence_references: [...row.evidence_references] })));
      setItem(emptyDecision()); setRefsText(""); setConflict(false);
    }
    return fresh;
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editable || conflict || !review) return;
    setBusy(true); setError(null); setNotice(null); setServerBlockers([]);
    const token = review.current_readiness;
    try {
      const saved = await saveProfessionalReview(clientId, scenario.scenario_id, {
        expected_approval_version: review.approval_version,
        expected_scenario_version: token.scenario_version,
        expected_manifest_fingerprint: token.manifest_fingerprint,
        expected_readiness_fingerprint: token.readiness_fingerprint,
        decisions: draft,
      });
      setReview(saved);
      setDraft(saved.decisions.map(row => ({ ...row, evidence_references: [...row.evidence_references] })));
      setHistory(null);
      setNotice("טיוטת ההכרעות נשמרה. אין בכך אישור קיבוע זכויות או זכאות למס.");
    } catch (cause) {
      if (cause instanceof ReviewApiError) setServerBlockers(cause.blockers);
      if (cause instanceof ReviewApiError && cause.status === 409) {
        setConflict(true);
        try { await reload({ preserve: true }); }
        catch (reloadError) { setError(message(reloadError)); }
      }
      setError(message(cause));
    } finally { setBusy(false); }
  }
  async function loadHistory() {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const rows = await readProfessionalReviewHistory(clientId, scenario.scenario_id);
      setHistory(rows);
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  const blockers = [...new Set([...(review?.blockers ?? []), ...serverBlockers])];
  return <section dir="rtl" aria-label="קיבוע זכויות - הכרעות מקצועיות" className="scenario-workflow">
    <h4>קיבוע זכויות - הכרעות מקצועיות</h4>
    <p className="professional-workspace__boundary">
      הפרדה מחייבת: נתוני מקור אינם הכרעות מקצועיות, והכרעות שמורות הן טיוטות בלבד.
      אין אישור רשות המסים, פטור, מס לתשלום, משיכה מאושרת או תזרים נטו.
    </p>
    {loading && <p role="status">טוען מצב קיבוע זכויות...</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {review && <>
      <p role="status">מוכנות לחישוב: <strong>חסומה</strong>. מצב ההכרעות:
        {" "}<strong>{review.validity_state === "STALE" ? "מקור השתנה, נדרש אימות מחדש"
          : review.record_status === "MISSING" ? "טרם נשמרו הכרעות"
            : review.record_status === "DRAFT" ? "טיוטה שמורה, ללא אישור"
              : "חסום"}</strong>. גרסת הכרעות: {review.approval_version}.
      </p>
      {review.validity_state === "STALE" && <p role="alert">
        ראיות המקור או החלופה השתנו מאז השמירה. ההכרעות הישנות אינן תקפות.
        בדוק את ההכרעות ושמור גרסה חדשה לאחר בדיקה.
      </p>}
      {conflict && <div role="alert">
        יש התנגשות עם גרסת השרת. הטיוטה שהזנת נשמרה על המסך ואינה נדרסת.
        עיין במקורות ובגרסה העדכניים לפני אישור ניסיון שמירה חדש.
        <button type="button" onClick={() => { setConflict(false); setError(null); }}>
          בדקתי את הנתונים העדכניים, אפשר ניסיון שמירה חדש
        </button>
      </div>}
      <details>
        <summary>נתוני מקור ומוכנות לחישוב</summary>
        <p>ראיות זכאות M07: {review.current_readiness.source_evidence.m07.length}.
          מענקים: {review.current_readiness.source_evidence.grants.length}.
          היוונים היסטוריים: {review.current_readiness.source_evidence.historical_capitalizations.length}.
        </p>
        <ul>{Object.entries(review.current_readiness.mapping).map(([key, mapping]) =>
          <li key={key}>
            {({
              m07_input_reference: "מועד זכאות", parameter_set: "שנת מס ופרמטרים",
              grants_collection_state_and_grants: "מענקים ותשלום",
              future_grant_reservation: "רצפים ופיצויים מתוכננים",
              actual_capitalizations_collection_state_and_items: "היוונים היסטוריים",
              idf: "היוונים מיוחדים", calculation_version: "גרסת חישוב",
              pension_qualification: "סיווג קצבאות", planned_capital_and_commutations: "הון ומשיכות מתוכננות",
              tax_authority_approval: "אישור רשות המסים",
            } as Record<string, string>)[key] ?? key}: {mapping.present ? "מקור קיים" : "מקור חסר"},
            {" "}{mapping.verified ? "מאומת" : "לא מאומת"}
          </li>)}</ul>
      </details>
      <details open={review.validity_state === "STALE"}>
        <summary>חסמים מקצועיים ({blockers.length})</summary>
        <ul>{blockers.map(code => <li key={code}>{label(code)}</li>)}</ul>
      </details>
      <form onSubmit={add} aria-label="הזנת הכרעה מקצועית">
        <h5>הזנת הכרעה מקצועית</h5>
        <label>קבוצת הכרעה{" "}
          <select value={item.group} disabled={!editable}
            onChange={event => setItem(empty => ({
              ...emptyDecision(), group: event.target.value as ReviewGroup,
              determination: empty.determination,
            }))}>
            {GROUPS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </select>
        </label>
        <label>מקור ההכרעה{" "}
          <select value={sources.some(row => row.id === item.source_id) ? item.source_id : ""}
            disabled={!editable || sources.length === 0}
            onChange={event => setItem(current => ({ ...current, source_id: event.target.value,
              parameter_set_id: current.group === "tax_year_and_parameters" ? event.target.value : null }))}>
            <option value="">בחר מקור מהרשומות</option>
            {sources.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}
          </select>
        </label>
        {item.group === "tax_year_and_parameters" && <label>מזהה סט פרמטרים רשמי, לרישום הכרעה בלבד{" "}
          <input value={item.source_id} disabled={!editable} maxLength={64}
            onChange={event => setItem(current => ({
              ...current, source_id: event.target.value, parameter_set_id: event.target.value || null,
            }))}/>
        </label>}
        {item.group !== "tax_year_and_parameters" && sources.length === 0 && <p role="status">
          לא נמצאו מקורות בקבוצה זו. יש להשלים מקורות לפני רישום הכרעה.
        </p>}
        <label>מצב ההכרעה{" "}
          <select value={item.determination} disabled={!editable}
            onChange={event => setItem(current => ({
              ...current, determination: event.target.value as ReviewDetermination,
            }))}>
            {DETERMINATIONS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </select>
        </label>
        {item.group === "eligibility" && <label>תאריך זכאות שנבחן{" "}
          <input type="date" disabled={!editable} value={item.eligibility_date ?? ""}
            onChange={event => setItem(current => ({
              ...current, eligibility_date: event.target.value || null,
            }))}/>
        </label>}
        {item.group === "tax_year_and_parameters" && <label>שנת מס שנבחנה{" "}
          <input type="number" min="1900" max="2200" disabled={!editable}
            value={item.tax_year ?? ""} onChange={event => setItem(current => ({
              ...current, tax_year: event.target.value ? Number(event.target.value) : null,
            }))}/>
        </label>}
        {item.group === "pension_classification" && <label>סיווג מס לתיעוד, אינו מאושר{" "}
          <input value={item.tax_classification ?? ""} maxLength={128} disabled={!editable}
            onChange={event => setItem(current => ({
              ...current, tax_classification: event.target.value || null,
            }))}/>
        </label>}
        <label>הנמקה מקצועית{" "}
          <textarea value={item.reason} disabled={!editable} maxLength={2048}
            onChange={event => setItem(current => ({ ...current, reason: event.target.value }))}/>
        </label>
        <label>הפניות לאסמכתאות, אחת בכל שורה{" "}
          <textarea value={refsText} disabled={!editable}
            onChange={event => setRefsText(event.target.value)}/>
        </label>
        <button type="submit" disabled={!editable || !item.source_id.trim() || !item.reason.trim()}>
          הוסף או עדכן הכרעה בטיוטה
        </button>
      </form>
      <div aria-label="הכרעות בטיוטת המסך">
        <h5>הכרעות שהוזנו ({draft.length})</h5>
        {draft.length === 0 && <p>טרם הוזנו הכרעות בחלופה.</p>}
        <ul>{draft.map(row => <li key={row.group + ":" + row.source_id}>
          <strong>{groupName(row.group)}</strong>: {row.source_id}, {row.reason}
          <button type="button" disabled={!editable} onClick={() => edit(row)}>ערוך</button>
          <button type="button" disabled={!editable} onClick={() =>
            setDraft(current => current.filter(candidate => !sameKey(candidate, row)))}>הסר</button>
        </li>)}</ul>
      </div>
      <form onSubmit={event => void save(event)}>
        <button type="submit" disabled={!editable || conflict}>
          {busy ? "שומר טיוטת הכרעות..." : "שמור טיוטת הכרעות מקצועיות"}
        </button>
        <button type="button" disabled={busy || loading}
          onClick={() => void reload().catch(cause => setError(message(cause)))}>
          טען מחדש מהשרת (מחליף את הטיוטה על המסך)
        </button>
      </form>
      <button type="button" disabled={busy} onClick={() => void loadHistory()}>
        הצג היסטוריית גרסאות
      </button>
      {history && <div aria-label="היסטוריית הכרעות">
        <h5>היסטוריית גרסאות</h5>
        {history.length === 0 && <p>אין עדיין גרסאות שמורות.</p>}
        <ul>{history.map(row => <li key={row.revision_id}>
          <details>
            <summary>
              גרסה {row.approval_version}, {row.actor_id}, {new Date(row.occurred_at).toLocaleString("he-IL")},
              {" "}{row.decisions.length} הכרעות, טיוטה בלבד.
            </summary>
            <ul>{row.decisions.map(decision => <li key={decision.group + ":" + decision.source_id}>
              <strong>{groupName(decision.group)}</strong>: {decision.source_id}.
              {" "}{decision.reason}
              {decision.evidence_references.length > 0 &&
                <p>הפניות לאסמכתאות: {decision.evidence_references.join(", ")}</p>}
            </li>)}</ul>
            {row.blockers.length > 0 && <p>חסמים בעת השמירה: {row.blockers.map(label).join("; ")}</p>}
          </details>
        </li>)}</ul>
      </div>}
      <p className="professional-workspace__boundary" role="status">
        אישור מקצועי פנימי חסום עד להשלמת תנאי הסף ואימות הראיות בשרת.
        אין אפשרות לאשר קיבוע זכויות במסך זה.
      </p>
      {scenario.status !== "draft" && <p role="status">החלופה אינה פעילה לעריכת הכרעות.</p>}
    </>}
  </section>;
}
