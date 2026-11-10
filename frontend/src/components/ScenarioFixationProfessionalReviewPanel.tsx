import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import {
  readProfessionalReview, saveProfessionalReview, readProfessionalReviewHistory,
  ReviewApiError, type ProfessionalDecision, type ProfessionalReview,
  type ReviewGroup, type ReviewDetermination, type ReviewHistoryItem,
  type FixationAdmissionControls, type FixationPreparation, type FixationAdmissionEligibility,
  readFixationAdmissionPreparation, readFixationAdmissionEligibility,
} from "../api/scenarioFixationProfessionalReviewApi";
import { ScenarioFixationAdmissionControls, ReferenceListInput, controlsValidation } from "./ScenarioFixationAdmissionControls";

interface Props {
  clientId: number;
  scenario: ScenarioDraft;
  onScenarioRefresh?: () => Promise<void>;
}
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
  FIXATION_PREPARATION_CONTROLS_MISSING: "טרם מולאו בקרות איסוף הנתונים להכנת הקלט.",
  FIXATION_PREPARATION_PROFESSIONAL_REVIEW_STALE: "המקורות השתנו מאז ההכרעה. נדרש אימות מחדש.",
  FIXATION_PREPARATION_SOURCE_OVERLAP_UNRESOLVED: "קיימת חפיפה בלתי פתורה בין מענקים לרכיבי פיצויים.",
  FIXATION_PREPARATION_CALCULATION_VERSION_UNSUPPORTED: "גרסת החישוב אינה נתמכת.",
  FIXATION_PREPARATION_ELIGIBILITY_MISSING: "חסרה הכרעת מועד זכאות מתועדת.",
  FIXATION_PREPARATION_ELIGIBILITY_SOURCE_INVALID: "אסמכתת הזכאות אינה תקפה ללקוח.",
  FIXATION_PREPARATION_ELIGIBILITY_NOT_RESOLVED: "ראיות M07 לא נפתרו לקלט מתאים.",
  FIXATION_PREPARATION_ELIGIBILITY_MISMATCH: "מועד הזכאות אינו תואם לראיות M07.",
  FIXATION_PREPARATION_PARAMETER_SET_MISSING: "חסרים שנת מס או סט פרמטרים רשמי.",
  FIXATION_PREPARATION_PARAMETER_SET_NOT_APPLICABLE: "סט הפרמטרים אינו מתאים למועד ולשנת המס.",
  FIXATION_PREPARATION_PENSION_CLASSIFICATION_INCOMPLETE: "סיווג הקצבאות לצורכי קיבוע אינו שלם.",
  FIXATION_PREPARATION_PLANNED_CAPITAL_INCOMPLETE: "חסרות הכרעות להון ולמשיכות מתוכננות.",
  FIXATION_PREPARATION_GRANTS_NOT_COLLECTED: "נתוני המענקים טרם נאספו.",
  FIXATION_PREPARATION_CAPITALIZATIONS_NOT_COLLECTED: "נתוני ההיוונים ההיסטוריים טרם נאספו.",
  FIXATION_PREPARATION_GRANTS_CONFIRMED_NONE_CONTRADICTS_SOURCE: "סומן שאין מענקים, אך קיימת רשומת מענק.",
  FIXATION_PREPARATION_CAPITALIZATIONS_CONFIRMED_NONE_CONTRADICTS_SOURCE: "סומן שאין היוונים, אך קיימת רשומת היוון.",
  FIXATION_PREPARATION_GRANTS_ITEMS_MISSING: "סומן שקיימים מענקים, אך לא נמצאו רשומות.",
  FIXATION_PREPARATION_CAPITALIZATIONS_ITEMS_MISSING: "סומן שקיימים היוונים, אך לא נמצאו רשומות.",
  FIXATION_PREPARATION_GRANT_DECISION_MISSING: "חסרה הכרעה לגבי מענק.",
  FIXATION_PREPARATION_CAPITALIZATION_DECISION_MISSING: "חסרה הכרעה לגבי היוון היסטורי.",
  FIXATION_PREPARATION_GRANT_DECISION_OR_EVIDENCE_INCOMPLETE: "חסרים פרטי הכרעה או אסמכתה למענק.",
  FIXATION_PREPARATION_CAPITALIZATION_DECISION_OR_EVIDENCE_INCOMPLETE: "חסרים פרטי הכרעה או אסמכתה להיוון.",
  FIXATION_PREPARATION_GRANT_PAYMENT_UNKNOWN: "מעמד תשלום המענק אינו ידוע.",
  FIXATION_PREPARATION_GRANT_AMOUNT_MISSING: "חסר סכום מענק מתועד.",
  FIXATION_PREPARATION_GRANT_DATES_INVALID: "תאריכי תקופת העבודה של המענק אינם תקינים.",
  FIXATION_PREPARATION_GRANTS_COLLECTION_INCOMPLETE: "איסוף המענקים והכרעותיהם אינו שלם.",
  FIXATION_PREPARATION_CAPITALIZATIONS_COLLECTION_INCOMPLETE: "איסוף ההיוונים והכרעותיהם אינו שלם.",
  FIXATION_PREPARATION_IDF_NOT_REVIEWED: "טרם נבדקה תחולת IDF.",
  FIXATION_PREPARATION_IDF_INPUT_OR_EVIDENCE_MISSING: "IDF חל, אך חסרים נתונים או אסמכתאות.",
  FIXATION_PREPARATION_IDF_APPLICABILITY_CONTRADICTION: "קיימת סתירה בהכרעת תחולת IDF.",
  FIXATION_PREPARATION_GRANT_FOREIGN_OR_MISSING_SOURCE: "הכרעת המענק מתייחסת למקור חסר או ללקוח אחר.",
  FIXATION_PREPARATION_CAPITALIZATION_FOREIGN_OR_MISSING_SOURCE: "הכרעת ההיוון מתייחסת למקור חסר או ללקוח אחר.",
  FIXATION_PREPARATION_ADMISSION_CONTRACT_INVALID: "הקלט אינו עומד בחוזה Admission. נדרשת השלמת נתונים או תיקון סתירה.",
  FIXATION_ELIGIBILITY_PREPARED_CANDIDATE_INVALID: "מועמד הקלט אינו תואם לחוזה Admission.",
  FIXATION_ELIGIBILITY_IDF_UNSUPPORTED: "נתוני IDF עדיין אינם נתמכים במעבר לבדיקת Admission.",
  FIXATION_ELIGIBILITY_CBS_INDEXATION_REQUIRED: "נדרשת הצמדה חיצונית מאומתת של המענק לפני Admission.",
  FIXATION_ELIGIBILITY_CALCULATION_VERSION_UNSUPPORTED: "גרסת החישוב אינה נתמכת.",
  FIXATION_ELIGIBILITY_PARAMETER_CLIENT_MISMATCH: "סט הפרמטרים אינו שייך ללקוח.",
  FIXATION_ELIGIBILITY_PARAMETER_SET_NOT_ACCEPTED: "סט הפרמטרים טרם התקבל לשימוש.",
  FIXATION_ELIGIBILITY_DATE_NOT_BOUND: "תאריך הזכאות אינו משויך לראיות החלופה.",
  FIXATION_ELIGIBILITY_PARAMETER_TAX_YEAR_MISMATCH: "שנת המס אינה תואמת למועד הזכאות.",
  FIXATION_ELIGIBILITY_PARAMETER_NOT_YET_EFFECTIVE: "סט הפרמטרים עדיין אינו בתוקף במועד הזכאות.",
  FIXATION_ELIGIBILITY_PARAMETER_EXPIRED: "תוקף סט הפרמטרים הסתיים לפני מועד הזכאות.",
  FIXATION_ELIGIBILITY_GRANT_MULTIPLIER_UNSUPPORTED: "מקדם השפעת המענקים אינו נתמך.",
  FIXATION_ELIGIBILITY_GRANT_CLIENT_MISMATCH: "המענק אינו משויך ללקוח.",
  FIXATION_ELIGIBILITY_GRANT_EMPLOYER_MISSING: "חסר שם המעסיק של המענק.",
  FIXATION_ELIGIBILITY_GRANT_WITHHOLDING_FILE_MISSING: "חסר תיק ניכויים של המעסיק במענק.",
  FIXATION_ELIGIBILITY_GRANT_AFTER_ELIGIBILITY_DATE: "תאריך המענק מאוחר למועד הזכאות.",
  FIXATION_ELIGIBILITY_GRANT_NOT_ACCEPTED: "המענק לא התקבל לשימוש בקלט.",
  FIXATION_ELIGIBILITY_GRANT_SUPPORT_UNRESOLVED: "תמיכת הראיות למענק לא הוכרעה.",
  FIXATION_ELIGIBILITY_GRANT_AMOUNT_MISSING: "חסר סכום מענק שניתן להשתמש בו.",
  FIXATION_ELIGIBILITY_CAPITALIZATION_NOT_ACCEPTED: "ההיוון ההיסטורי לא התקבל לשימוש.",
  FIXATION_ELIGIBILITY_CAPITALIZATION_SUPPORT_UNRESOLVED: "תמיכת הראיות להיוון ההיסטורי אינה מספקת.",
  FIXATION_ELIGIBILITY_FUTURE_GRANT_NOT_REPRESENTED_BY_PREPARATION: "מענק עתידי אינו מיוצג בחוזה הכנת הקלט.",
  FIXATION_ELIGIBILITY_CONTINUITY_NOT_REPRESENTED_BY_ADMISSION: "הכרעת רצף אינה מיוצגת בקלט Admission.",
  FIXATION_ELIGIBILITY_PLANNED_WITHDRAWAL_NOT_REPRESENTED_BY_ADMISSION: "משיכה מתוכננת אינה מיוצגת בקלט Admission.",
};
function label(code: string) { return LABELS[code] ?? `חסם מקצועי: ${code}`; }
function groupName(group: ReviewGroup): string {
  return GROUPS.find(item => item.value === group)?.label ?? group;
}
function normalizeDecision(row: ProfessionalDecision): ProfessionalDecision {
  // Existing revisions may predate the closed admission-decision extension.
  // Missing fields remain undecided, never inferred as accepted.
  return {
    ...row,
    inclusion_decision: row.inclusion_decision ?? null,
    support_status: row.support_status ?? null,
    accepted_for_use: row.accepted_for_use ?? null,
    payment_status: row.payment_status ?? null,
    overlap_resolution: row.overlap_resolution ?? null,
    matched_source_ids: [...(row.matched_source_ids ?? [])],
    evidence_references: [...(row.evidence_references ?? [])],
  };
}
function emptyDecision(): ProfessionalDecision {
  return {
    group: "eligibility", source_id: "", determination: "REQUIRES_REVIEW",
    reason: "", evidence_references: [], eligibility_date: null, tax_year: null,
    parameter_set_id: null, tax_classification: null,
    inclusion_decision: null, support_status: null, accepted_for_use: null,
    payment_status: null, overlap_resolution: null, matched_source_ids: [],
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

export function ScenarioFixationProfessionalReviewPanel({
  clientId, scenario, onScenarioRefresh,
}: Props) {
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
  const [controls, setControls] = useState<FixationAdmissionControls | null>(null);
  const [preparation, setPreparation] = useState<FixationPreparation | null>(null);
  const [preparationError, setPreparationError] = useState<string | null>(null);
  const [eligibility, setEligibility] = useState<FixationAdmissionEligibility | null>(null);
  const [eligibilityError, setEligibilityError] = useState<string | null>(null);
  const statusRequest = useRef(0);
  const scenarioIdentity = useRef(`${clientId}:${scenario.scenario_id}`);
  scenarioIdentity.current = `${clientId}:${scenario.scenario_id}`;

  async function refreshStatuses() {
    const sequence = ++statusRequest.current;
    const identity = `${clientId}:${scenario.scenario_id}`;
    // Never display a previous positive state while current evidence is in flight.
    setPreparation(null); setEligibility(null);
    setPreparationError(null); setEligibilityError(null);
    const [prep, elig] = await Promise.allSettled([
      readFixationAdmissionPreparation(clientId, scenario.scenario_id),
      readFixationAdmissionEligibility(clientId, scenario.scenario_id),
    ]);
    if (sequence !== statusRequest.current || scenarioIdentity.current !== identity) return;
    if (prep.status === "fulfilled") setPreparation(prep.value);
    else setPreparationError(message(prep.reason));
    if (elig.status === "rejected") {
      setEligibilityError(message(elig.reason));
    } else if (prep.status !== "fulfilled"
        || elig.value.preparation_fingerprint !== prep.value.preparation_fingerprint
        || (prep.value.state === "INCOMPLETE" && elig.value.state !== "INCOMPLETE")
        || (prep.value.state === "BLOCKED" && elig.value.state !== "BLOCKED")
        || (prep.value.state === "PREPARED" && elig.value.state === "INCOMPLETE")
        || (prep.value.state !== "PREPARED" && (
          elig.value.state === "REQUIRES_EXTERNAL_VALIDATION"
          || elig.value.state === "ELIGIBLE_FOR_ADMISSION_REVIEW"
        ))) {
      // A source may change between the two GET transactions, or the
      // responses may be semantically inconsistent even with matching tokens.
      setEligibilityError("תוצאות הכשירות וההכנה אינן תואמות לאותם נתוני מקור. יש לרענן.");
    } else {
      setEligibility(elig.value);
    }
  }

  useEffect(() => {
    let mounted = true;
    setReview(null); setDraft([]); setItem(emptyDecision()); setRefsText("");
    setHistory(null); setError(null); setNotice(null); setConflict(false);
    setServerBlockers([]); setControls(null); setPreparation(null);
    setPreparationError(null); setEligibility(null); setEligibilityError(null);
    setLoading(true);
    void readProfessionalReview(clientId, scenario.scenario_id)
      .then(result => {
        if (!mounted) return;
        setReview(result);
        setControls(result.admission_controls ?? null);
        setDraft(result.decisions.map(normalizeDecision));
      })
      .catch(cause => { if (mounted) setError(message(cause)); })
      .finally(() => { if (mounted) setLoading(false); });
    void refreshStatuses();
    return () => { mounted = false; statusRequest.current += 1; };
  }, [clientId, scenario.scenario_id]);

  const sources = review ? sourcesFor(item.group, review, scenario) : [];
  const editable = scenario.status === "draft" && !loading && !busy && review !== null
    && review.current_readiness.scenario_version === scenario.version;
  function edit(row: ProfessionalDecision) {
    setItem(normalizeDecision(row));
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
    if (item.group === "historical_grant" || item.group === "historical_capitalization"
        || item.group === "planned_withdrawal_or_commutation") {
      if (item.determination === "PLANNER_ASSERTED"
          && (item.inclusion_decision === null || item.support_status === null
              || item.accepted_for_use === null)) {
        setError("נדרשת הכרעת הכללה, מצב תמיכה והחלטת שימוש מפורשים.");
        return;
      }
    }
    if (item.group === "historical_grant" && item.determination === "PLANNER_ASSERTED"
        && item.payment_status === null) {
      setError("יש להגדיר מעמד תשלום מענק, גם אם אינו ידוע.");
      return;
    }
    if (item.group === "pension_classification" && item.determination === "PLANNER_ASSERTED"
        && !item.tax_classification) {
      setError("יש לבחור סיווג קצבה מתוך הערכים המאושרים בחוזה.");
      return;
    }
    if ((item.overlap_resolution !== null || item.matched_source_ids.length > 0)
        && !parsed.length) {
      setError("הכרעת חפיפה מחייבת אסמכתה ואינה מבטלת חסמי מקור בלתי פתורים.");
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
      setDraft(fresh.decisions.map(normalizeDecision));
      setControls(fresh.admission_controls ?? null);
      setItem(emptyDecision()); setRefsText(""); setConflict(false);
    }
    return fresh;
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editable || conflict || !review) return;
    const validation = controlsValidation(controls);
    if (validation) { setError(validation); return; }
    setBusy(true); setError(null); setNotice(null); setServerBlockers([]);
    // Save invalidates any previously displayed eligibility or preparation.
    statusRequest.current += 1;
    setPreparation(null); setEligibility(null);
    setEligibilityError(null); setPreparationError(null);
    const token = review.current_readiness;
    try {
      const saved = await saveProfessionalReview(clientId, scenario.scenario_id, {
        expected_approval_version: review.approval_version,
        expected_scenario_version: token.scenario_version,
        expected_manifest_fingerprint: token.manifest_fingerprint,
        expected_readiness_fingerprint: token.readiness_fingerprint,
        decisions: draft,
        admission_controls: controls,
      });
      setReview(saved);
      setControls(saved.admission_controls ?? null);
      setDraft(saved.decisions.map(normalizeDecision));
      await refreshStatuses();
      setHistory(null);
      setNotice("טיוטת ההכרעות נשמרה. אין בכך אישור קיבוע זכויות או זכאות למס.");
    } catch (cause) {
      if (cause instanceof ReviewApiError) setServerBlockers(cause.blockers);
      if (cause instanceof ReviewApiError && cause.status === 409) {
        setConflict(true);
        statusRequest.current += 1;
        setPreparation(null); setEligibility(null);
        setEligibilityError("נתוני המקור השתנו. יש לבדוק מחדש לפני הצגת כשירות.");
        try {
          await reload({ preserve: true });
          await onScenarioRefresh?.();
        } catch (reloadError) {
          setError(message(reloadError));
        }
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
  // Even before useEffect cleanup runs, never render a previous client's or
  // scenario's state during a React parent transition.
  const activeReview = review?.client_id === clientId
    && review.scenario_id === scenario.scenario_id ? review : null;
  const blockers = [...new Set([...(activeReview?.blockers ?? []), ...serverBlockers])];
  const eligibilityIsCurrent = !conflict && activeReview?.validity_state !== "STALE"
    && activeReview?.current_readiness.scenario_version === scenario.version;
  const visibleEligibility = eligibilityIsCurrent ? eligibility : null;
  if (review && !activeReview) {
    return <section dir="rtl" aria-label="קיבוע זכויות - הכרעות מקצועיות">
      <p role="status">טוען נתוני קיבוע זכויות עבור החלופה שנבחרה...</p>
    </section>;
  }
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
      <section aria-label="מצב הכנת קלט Admission">
        <h5>מצב הכנת קלט Admission</h5>
        {preparation ? <>
          <p role="status">
            {preparation.state === "PREPARED"
              ? "PREPARED: הקלט הוכן לבדיקה. טרם ניתן אישור מקצועי לחישוב קיבוע זכויות."
              : preparation.state === "INCOMPLETE"
                ? "INCOMPLETE: חסרים נתונים או הכרעות להכנת הקלט."
                : "BLOCKED: נמצאו חסמים שמונעים הכנת קלט תקין."}
          </p>
          <ul>
            {preparation.incomplete_reasons.map(code => <li key={"missing:" + code}>{label(code)}</li>)}
            {preparation.blockers.map(code => <li key={"blocked:" + code}>{label(code)}</li>)}
          </ul>
        </> : <p role="status">מצב Admission Preparation טרם נטען.</p>}
        {preparationError && <p role="alert">{preparationError}</p>}
        <button type="button" disabled={busy}
          onClick={() => { void refreshStatuses(); }}>רענן מצב הכנת קלט וכשירות</button>
      </section>
      <section aria-label="כשירות לבדיקת Admission" dir="rtl">
        <h5>כשירות לבדיקת Admission (בדיקה סטטית בלבד)</h5>
        {visibleEligibility ? <>
          <p role="status">
            {visibleEligibility.state === "INCOMPLETE"
              ? "INCOMPLETE: חסרים נתונים להכנת הקלט."
              : visibleEligibility.state === "BLOCKED"
                ? "BLOCKED: קיימים חסמים המונעים מעבר לבדיקת Admission."
                : visibleEligibility.state === "REQUIRES_EXTERNAL_VALIDATION"
                  ? "REQUIRES_EXTERNAL_VALIDATION: נדרש אימות חיצוני לפני בדיקת Admission."
                  : "ELIGIBLE_FOR_ADMISSION_REVIEW: לא נמצאו חסמים סטטיים ידועים. נדרשת בדיקת Admission מלאה, ללא אישור מקצועי לחישוב."}
          </p>
          <ul>{visibleEligibility.reasons.map((reason, i) => <li key={reason.code + ":" + i}>
            {label(reason.code)} <code dir="ltr">{reason.code}</code>
            {reason.source_ids.length > 0 && <span> | מזהי מקורות:
              {" "}{reason.source_ids.map(id => <code key={id} dir="ltr">{id} </code>)}
            </span>}
          </li>)}</ul>
        </> : <p role="status">
          הכשירות אינה מאומתת כעת. יש לטעון תוצאות תואמות למקורות העדכניים.
        </p>}
        {eligibilityError && <p role="alert">{eligibilityError}</p>}
        <p>הכשירות אינה אישור מקצועי, אינה אישור רשות המסים ואינה מאפשרת חישוב מס.</p>
      </section>
      {review.validity_state === "STALE" && <p role="alert">
        ראיות המקור או החלופה השתנו מאז השמירה. ההכרעות הישנות אינן תקפות.
        בדוק את ההכרעות ושמור גרסה חדשה לאחר בדיקה.
      </p>}
      {review.current_readiness.scenario_version !== scenario.version && <div role="alert">
        גרסת החלופה השתנתה. שמירת ההכרעות נעולה עד לרענון נתוני השרת.
        <button type="button" disabled={busy} onClick={() => {
          setBusy(true); setError(null);
          void reload({ preserve: true }).then(() => {
            setConflict(true);
            setNotice("טיוטת העריכה נשמרה על המסך. בדוק את הגרסה העדכנית לפני ניסיון שמירה.");
          }).catch(cause => setError(message(cause))).finally(() => setBusy(false));
        }}>
          טען נתוני חלופה עדכניים בלי למחוק את הטיוטה
        </button>
      </div>}
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
      <details>
        <summary>החלטות תכנון בחלופה, ללא אישור מקצועי</summary>
        <p>החלטות אלה מתארות כוונת תכנון ולא אישור רצף, מענק ששולם או משיכה מותרת.</p>
        <ul>
          {review.current_readiness.source_evidence.severance_choice_source_ids.map(row =>
            <li key={row.source_kind + ":" + row.source_id}>
              פיצויים: {row.source_kind === "grant" ? "מענק" : "רכיב בקופה"},
              {" "}{row.source_id}, מצב: {row.state === "DRAFT_ONLY" ? "טיוטה בלבד" : "חסום"}
            </li>)}
          {scenario.decisions.map(row => <li key={row.decision_id}>
            {row.action === "pension" ? "קצבה מתוכננת" : "הון מתוכנן"}:
            {" "}{row.component_code}, {row.amount} ₪
          </li>)}
        </ul>
        {review.current_readiness.source_evidence.severance_choice_source_ids.length === 0 &&
          scenario.decisions.length === 0 && <p>לא נרשמו החלטות תכנון בחלופה.</p>}
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

        {item.group === "pension_classification" && <label>סיווג קצבה לפי חוזה סגור
          <select disabled={!editable} value={item.tax_classification ?? ""}
            onChange={event => setItem(current => ({ ...current,
              tax_classification: event.target.value === "" ? null
                : event.target.value as NonNullable<ProfessionalDecision["tax_classification"]>,
            }))}>
            <option value="">טרם הוכרע</option>
            <option value="QUALIFYING_PENSION_FOR_FIXATION">קצבה מזכה לצורך קיבוע, הכרעת מתכנן</option>
            <option value="NON_QUALIFYING_PENSION_FOR_FIXATION">קצבה שאינה מזכה לצורך קיבוע, הכרעת מתכנן</option>
          </select>
        </label>}
        {(["historical_grant", "historical_capitalization", "planned_withdrawal_or_commutation"] as ReviewGroup[])
          .includes(item.group) && <>
          <label>הכרעת הכללה
            <select disabled={!editable} value={item.inclusion_decision ?? ""}
              onChange={event => setItem(current => ({ ...current,
                inclusion_decision: event.target.value === "" ? null
                  : event.target.value as NonNullable<ProfessionalDecision["inclusion_decision"]>,
              }))}>
              <option value="">טרם הוכרע</option>
              <option value="include">לכלול בקלט המתוכנן</option>
              <option value="exclude">להחריג מהקלט המתוכנן</option>
            </select>
          </label>
          <label>מצב תמיכה מקצועית
            <select disabled={!editable} value={item.support_status ?? ""}
              onChange={event => setItem(current => ({ ...current,
                support_status: event.target.value === "" ? null
                  : event.target.value as NonNullable<ProfessionalDecision["support_status"]>,
              }))}>
              <option value="">טרם הוכרע</option>
              <option value="supported">נתמך בראיות, כפוף לאימות שרת</option>
              <option value="unsupported">אינו נתמך</option>
              <option value="requires_special_handling">דורש טיפול מיוחד</option>
            </select>
          </label>
          <label>הכרעת שימוש בקלט
            <select disabled={!editable} value={item.accepted_for_use === null ? ""
              : item.accepted_for_use ? "true" : "false"}
              onChange={event => setItem(current => ({ ...current,
                accepted_for_use: event.target.value === "" ? null : event.target.value === "true",
              }))}>
              <option value="">טרם הוכרע</option>
              <option value="true">מוצע לשימוש, לא אושר לחישוב</option>
              <option value="false">לא לשימוש</option>
            </select>
          </label>
        </>}
        {item.group === "historical_grant" && <label>מעמד תשלום המענק
          <select disabled={!editable} value={item.payment_status ?? ""}
            onChange={event => setItem(current => ({ ...current,
              payment_status: event.target.value === "" ? null
                : event.target.value as NonNullable<ProfessionalDecision["payment_status"]>,
            }))}>
            <option value="">טרם הוכרע</option>
            <option value="PAID">שולם לפי הכרעה מתועדת, טעון אימות</option>
            <option value="NOT_PAID">לא שולם לפי הכרעה מתועדת</option>
            <option value="UNKNOWN">לא ידוע</option>
          </select>
        </label>}
        {(["historical_grant", "severance_continuity"] as ReviewGroup[])
          .includes(item.group) && <>
          <label>הכרעת חפיפה מוצעת, אינה מסירה חסם מקור
            <select disabled={!editable} value={item.overlap_resolution ?? ""}
              onChange={event => setItem(current => ({ ...current,
                overlap_resolution: event.target.value === "" ? null
                  : event.target.value as NonNullable<ProfessionalDecision["overlap_resolution"]>,
              }))}>
              <option value="">חפיפה טרם הוכרעה</option>
              <option value="NO_OVERLAP">אין חפיפה, בכפוף לראיות</option>
              <option value="SAME_RIGHT_USE_GRANT">אותה זכות, שימוש במענק</option>
              <option value="SAME_RIGHT_USE_COMPONENT">אותה זכות, שימוש ברכיב הפיצויים</option>
              <option value="DISTINCT_RIGHTS">זכויות נפרדות, בכפוף לראיות</option>
            </select>
          </label>
          <ReferenceListInput label="מזהי מקורות תואמים לחפיפה, אחד בכל שורה"
            disabled={!editable} refs={item.matched_source_ids}
            onChange={refs => setItem(current => ({ ...current, matched_source_ids: refs }))}/>
        </>}
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
      <ScenarioFixationAdmissionControls value={controls}
        onChange={setControls} disabled={!editable}/>
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
