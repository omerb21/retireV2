import { useEffect, useState, type FormEvent } from "react";
import type { PensionProduct } from "../api/pensionProductsApi";
import { getGrants, type GrantItem } from "../api/clientsApi";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import {
  readSeverancePlanning, saveSeverancePlanning,
  type SeveranceChoiceInput, type SeveranceChoiceKind, type SavedSeveranceChoice,
  type SeverancePlanningSnapshot,
} from "../api/scenarioSeverancePlanningApi";

const SEVERANCE_CODES = new Set([
  "פיצויים_מעסיק_נוכחי",
  "פיצויים_לאחר_התחשבנות",
  "פיצויים_שלא_עברו_התחשבנות",
  "פיצויים_ממעסיקים_קודמים_רצף_זכויות",
  "פיצויים_ממעסיקים_קודמים_רצף_קצבה",
]);
const OPTIONS: Array<{ value: SeveranceChoiceKind; label: string }> = [
  { value: "UNDECIDED", label: "טרם הוכרע" },
  { value: "PLANNED_WITHDRAWAL", label: "משיכה מתוכננת" },
  { value: "PLANNED_PENSION_CONTINUITY", label: "ייעוד מתוכנן לרצף קצבה" },
  { value: "PLANNED_SEVERANCE_CONTINUITY", label: "ייעוד מתוכנן לרצף פיצויים" },
];
const BLOCKERS: Record<string, string> = {
  BLOCKED_SOURCE_STALE: "פרטי המקור או ההעסקה השתנו. יש לבדוק ולשמור מחדש.",
  BLOCKED_SCENARIO_VERSION_STALE: "החלופה השתנתה מהותית. נדרשת בחירה מחדש.",
  BLOCKED_SOURCE_MISSING_OR_FOREIGN: "מקור הבחירה אינו זמין או אינו שייך ללקוח.",
  BLOCKED_COMPONENT_OVERALLOCATED: "הסכומים שתוכננו חורגים מיתרת רכיב הפיצויים.",
  BLOCKED_GRANT_COMPONENT_OVERLAP_UNRECONCILED: "קיימת חפיפה אפשרית בין מענק לרכיב פיצויים. נדרש בירור מקצועי.",
  BLOCKED_SCENARIO_NOT_ACTIVE: "החלופה אינה פעילה. לא ניתן לבצע בה בחירות.",
};
type Source = { source_kind: SeveranceChoiceInput["source_kind"]; source_id: string; label: string; capacity: string | null };
interface Props {
  clientId: number;
  scenario: ScenarioDraft;
  products: PensionProduct[];
  onSaved: (scenarioId: string) => Promise<void>;
}
const key = (kind: string, id: string) => kind + ":" + id;
function validAmount(text: string): boolean {
  return /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(text)
    && Number(text) > 0;
}
function maxAllowed(text: string, capacity: string | null): boolean {
  if (!validAmount(text)) return false;
  if (capacity === null) return false;
  // Exact two-decimal integer arithmetic avoids floating-point comparisons.
  const cents = (value: string): bigint => {
    const [whole, fractional = ""] = value.split(".");
    return BigInt(whole) * 100n + BigInt((fractional + "00").slice(0, 2));
  };
  return cents(text) <= cents(capacity);
}

export function ScenarioSeverancePlanningPanel({ clientId, scenario, products, onSaved }: Props) {
  const [snapshot, setSnapshot] = useState<SeverancePlanningSnapshot | null>(null);
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [choices, setChoices] = useState<SeveranceChoiceInput[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setSnapshot(null);
    setChoices([]);
    setError(null);
    setNotice(null);
    void Promise.all([
      readSeverancePlanning(clientId, scenario.scenario_id),
      getGrants(clientId),
    ]).then(([fresh, sourceGrants]) => {
      if (!alive) return;
      if (sourceGrants.some(item => item.client_id !== clientId)) {
        throw Error("התקבלו מענקים בהקשר לקוח שגוי.");
      }
      setSnapshot(fresh);
      setGrants(sourceGrants);
      setChoices(fresh.choices.map(({ source_kind, source_id, choice, planned_amount_ils }) =>
        ({ source_kind, source_id, choice, planned_amount_ils })));
    }).catch(cause => {
      if (alive) setError(cause instanceof Error ? cause.message : "לא ניתן לטעון החלטות פיצויים.");
    }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [clientId, scenario.scenario_id, scenario.version]);

  const sources: Source[] = [
    ...grants.map(grant => ({
      source_kind: "grant" as const,
      source_id: grant.grant_id,
      label: "מענק: " + (grant.employer_name ?? grant.grant_id),
      // The existing client-grants DTO reports exempt grants, not a canonical
      // gross nominal ceiling. Never infer a planning limit from that field.
      capacity: null,
    })),
    ...products.filter(product => product.client_id === clientId).flatMap(product =>
      (product.conversion_components ?? [])
        .filter(component => SEVERANCE_CODES.has(component.component_code))
        .map(component => ({
          source_kind: "pension_component" as const,
          source_id: component.component_id,
          label: product.product_name + " - " + component.component_code,
          capacity: component.balance,
        }))),
  ];
  const uniqueSources = sources.filter((source, index) =>
    sources.findIndex(candidate => candidate.source_kind === source.source_kind &&
      candidate.source_id === source.source_id) === index);
  const savedMap = new Map<string, SavedSeveranceChoice>(
    (snapshot?.choices ?? []).map(item => [key(item.source_kind, item.source_id), item]),
  );
  const editable = scenario.status === "draft" && !loading && !saving &&
    snapshot?.scenario_version === scenario.version;
  function setChoice(source: Source, value: SeveranceChoiceKind) {
    setChoices(current => {
      const remaining = current.filter(item => key(item.source_kind, item.source_id) !==
        key(source.source_kind, source.source_id));
      return [...remaining, {
        source_kind: source.source_kind, source_id: source.source_id,
        choice: value, planned_amount_ils: null,
      }];
    });
    setNotice(null);
  }
  function setAmount(source: Source, amount: string) {
    setChoices(current => current.map(item =>
      key(item.source_kind, item.source_id) === key(source.source_kind, source.source_id)
        ? { ...item, planned_amount_ils: amount || null } : item));
    setNotice(null);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!editable || !snapshot) return;
    const invalid = choices.find(choice => {
      if (choice.choice === "UNDECIDED") return choice.planned_amount_ils !== null;
      if (choice.planned_amount_ils === null) return false;
      const source = uniqueSources.find(item => key(item.source_kind, item.source_id) ===
        key(choice.source_kind, choice.source_id));
      // A grant has no verified ceiling in the frontend DTO; its amount must
      // remain unspecified until authoritative backend evidence is checked.
      return !source || !maxAllowed(choice.planned_amount_ils, source.capacity);
    });
    if (invalid) {
      setError("הסכום המתוכנן חורג מהיתרה או אינו מבוסס על נתון מקור מאומת.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const saved = await saveSeverancePlanning(
        clientId, scenario.scenario_id, snapshot.scenario_version, choices,
      );
      setSnapshot(saved);
      setNotice("בחירות התכנון נשמרו. אין בכך אישור מס או תשלום.");
      await onSaved(scenario.scenario_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "לא ניתן לשמור בחירות פיצויים.");
    } finally {
      setSaving(false);
    }
  }
  const existingKeys = new Set(uniqueSources.map(source => key(source.source_kind, source.source_id)));
  const unavailable = (snapshot?.choices ?? []).filter(item =>
    !existingKeys.has(key(item.source_kind, item.source_id)));
  return <section aria-label="תכנון פיצויים ומענקים" className="scenario-workflow">
    <h4>פיצויים ומענקים - החלטות בחלופה</h4>
    <p className="professional-workspace__boundary">
      בחירות תכנון בלבד. אין כאן אישור רצף, פטור ממס, משיכה מותרת, תשלום בפועל או סכום נטו.
    </p>
    {loading && <p role="status">טוען מקורות ובחירות פיצויים...</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {snapshot && <form onSubmit={event => void submit(event)}>
      {uniqueSources.length === 0 && <p>לא נמצאו מענקים או רכיבי פיצויים בתיק.</p>}
      {uniqueSources.map(source => {
        const code = key(source.source_kind, source.source_id);
        const selected = choices.find(item => key(item.source_kind, item.source_id) === code);
        const saved = savedMap.get(code);
        const invalid = selected?.planned_amount_ils !== null &&
          selected?.planned_amount_ils !== undefined &&
          !maxAllowed(selected.planned_amount_ils, source.capacity);
        return <div key={code} className="scenario-conversion__saved">
          <strong>{source.label}</strong>
          <p>יתרת מקור להצגה: {source.capacity === null ? "לא אושרה בתצוגה" : source.capacity + " ₪"}</p>
          <label>החלטה בחלופה{" "}
            <select value={selected?.choice ?? "UNDECIDED"}
              disabled={!editable}
              onChange={event => setChoice(source, event.target.value as SeveranceChoiceKind)}>
              {OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          {selected && selected.choice !== "UNDECIDED" && <label>
            סכום מתוכנן (₪), לא חובה{" "}
            <input inputMode="decimal" value={selected.planned_amount_ils ?? ""}
              disabled={!editable || source.capacity === null}
              onChange={event => setAmount(source, event.target.value)}
              aria-invalid={invalid} />
          </label>}
          {saved && <p role="status">
            {saved.state === "DRAFT_ONLY" ? "בחירה שמורה - תכנון בלבד" :
              (BLOCKERS[saved.state] ?? "הבחירה חסומה: " + saved.state)}
          </p>}
        </div>;
      })}
      {unavailable.map(item => <p key={key(item.source_kind, item.source_id)} role="alert">
        מקור {item.source_id}: {BLOCKERS[item.state] ?? "המקור אינו זמין. הבחירה אינה מאושרת."}
      </p>)}
      <button type="submit" disabled={!editable || choices.some(item => item.planned_amount_ils !== null &&
        !maxAllowed(item.planned_amount_ils,
          uniqueSources.find(source => key(source.source_kind, source.source_id) ===
            key(item.source_kind, item.source_id))?.capacity ?? null))}>
        שמור החלטות פיצויים בחלופה
      </button>
      {scenario.status !== "draft" && <p role="status">החלופה אינה פעילה לעריכה.</p>}
    </form>}
  </section>;
}
