import { useEffect, useState } from "react";
import type { FixationAdmissionControls, CollectionState } from "../api/scenarioFixationProfessionalReviewApi";

interface Props {
  value: FixationAdmissionControls | null;
  onChange: (next: FixationAdmissionControls | null) => void;
  disabled: boolean;
}
const STATES: { value: CollectionState; label: string }[] = [
  { value: "unknown", label: "טרם הוכרע" },
  { value: "not_collected", label: "לא נאספו נתונים" },
  { value: "confirmed_none", label: "נבדק והוכח שאין פריטים" },
  { value: "items_recorded", label: "נרשמו פריטים" },
];
export const defaultControls = (): FixationAdmissionControls => ({
  calculation_version: "pkg-012-m08d-v1",
  grants_collection: { state: "unknown", evidence_references: [] },
  actual_capitalizations_collection: { state: "unknown", evidence_references: [] },
  idf: { applicability: "NOT_REVIEWED", evidence_references: [], input: null },
});
const parseRefs = (text: string) => text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
export function ReferenceListInput({ label, refs, onChange, disabled }: {
  label: string; refs: string[]; onChange: (next: string[]) => void; disabled: boolean;
}) {
  const signature = refs.join("\n");
  const [text, setText] = useState(signature);
  useEffect(() => { setText(signature); }, [signature]);
  return <label>{label}
    <textarea disabled={disabled} value={text} onChange={event => {
      setText(event.target.value);
      onChange(parseRefs(event.target.value));
    }}/>
  </label>;
}
export function controlsValidation(value: FixationAdmissionControls | null): string | null {
  if (!value) return null; // Legacy records remain without controls.
  if (value.calculation_version !== "pkg-012-m08d-v1") return "גרסת החישוב אינה נתמכת.";
  for (const [name, part] of [
    ["מענקים", value.grants_collection],
    ["היוונים היסטוריים", value.actual_capitalizations_collection],
  ] as const) {
    if (!STATES.some(s => s.value === part.state)) return `מצב איסוף ${name} אינו תקין.`;
    if (part.state === "confirmed_none" && !part.evidence_references.length)
      return `יש לצרף אסמכתאות להצהרה שאין ${name}.`;
    if (part.evidence_references.length > 32 || part.evidence_references.some(s => !s.trim() || s.length > 256))
      return `אסמכתאות ${name} אינן תקינות.`;
  }
  const idf = value.idf;
  if (idf.applicability === "NOT_REVIEWED" && (idf.input || idf.evidence_references.length))
    return "IDF שלא נבדק אינו יכול להכיל נתונים או אסמכתאות.";
  if (idf.applicability === "NOT_APPLICABLE" && (idf.input || !idf.evidence_references.length))
    return "ל-IDF שאינו חל נדרשת אסמכתה, ללא קלט היוון.";
  if (idf.applicability === "APPLICABLE") {
    if (!idf.input || !idf.evidence_references.length) return "יש להזין את כל נתוני IDF ואסמכתה.";
    if (!idf.input.idf_id.trim() || !idf.input.commutation_date || !idf.input.promoter_age_date
        || !Number.isFinite(idf.input.reduction_amount) || idf.input.reduction_amount <= 0
        || !Number.isFinite(idf.input.original_commutation_percent)
        || idf.input.original_commutation_percent < 1
        || !Number.isFinite(idf.input.current_commutation_percent)
        || idf.input.current_commutation_percent < 1)
      return "נתוני IDF אינם תקינים. יש להזין סכום חיובי, אחוזים תקינים ותאריכים.";
  }
  if (idf.evidence_references.length > 32 || idf.evidence_references.some(s => !s.trim() || s.length > 256))
    return "אסמכתאות IDF אינן תקינות.";
  return null;
}
export function ScenarioFixationAdmissionControls({ value, onChange, disabled }: Props) {
  const set = (next: FixationAdmissionControls) => onChange(next);
  const collections = ([
    ["grants_collection", "מענקים היסטוריים"],
    ["actual_capitalizations_collection", "היוונים היסטוריים"],
  ] as const);
  return <fieldset dir="rtl" disabled={disabled} aria-label="בקרות הכנת קלט קיבוע זכויות">
    <legend>בקרות להכנת קלט Admission</legend>
    {!value ? <div>
      <p>לרשומה זו טרם הוגדרו בקרות Admission. לא נבחרו ברירות מחדל מקצועיות.</p>
      <button type="button" onClick={() => set(defaultControls())}>
        התחל הזנת בקרות חדשה
      </button>
    </div> : <>
      <button type="button" onClick={() => onChange(null)}>נקה בקרות טיוטה (ללא החלטה מקצועית)</button>
      <label>גרסת חישוב נתמכת
        <select value={value.calculation_version} onChange={() => {}}>
          <option value="pkg-012-m08d-v1">pkg-012-m08d-v1</option>
        </select>
      </label>
      {collections.map(([key, title]) => <div key={key}>
        <label>מצב איסוף {title}
          <select value={value[key].state} onChange={event => set({
            ...value, [key]: { ...value[key], state: event.target.value as CollectionState },
          })}>
            {STATES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <ReferenceListInput label={`אסמכתאות ${title}, שורה לכל אסמכתה`}
          refs={value[key].evidence_references} disabled={disabled}
          onChange={refs => set({
            ...value, [key]: { ...value[key], evidence_references: refs },
          })}/>
      </div>)}
      <label>תחולת היוון IDF
        <select value={value.idf.applicability} onChange={event => {
          const applicability = event.target.value as typeof value.idf.applicability;
          set({ ...value, idf: { applicability, evidence_references: [],
            input: applicability === "APPLICABLE" ? {
              idf_id: "", reduction_amount: 0, original_commutation_percent: 0,
              current_commutation_percent: 0, commutation_date: "", promoter_age_date: "",
              source_label: null,
            } : null,
          } });
        }}>
          <option value="NOT_REVIEWED">טרם נבדק</option>
          <option value="NOT_APPLICABLE">אינו חל, עם אסמכתה</option>
          <option value="APPLICABLE">חל, נדרש קלט מלא</option>
        </select>
      </label>
      {value.idf.applicability !== "NOT_REVIEWED" && <ReferenceListInput
        label="אסמכתאות לתחולת IDF" refs={value.idf.evidence_references}
        disabled={disabled} onChange={refs => set({ ...value, idf: {
          ...value.idf, evidence_references: refs,
        } })}/>} 
      {value.idf.applicability === "APPLICABLE" && value.idf.input && <div>
        {([
          ["idf_id", "מזהה נתון IDF"],
          ["source_label", "תיאור מקור IDF"],
        ] as const).map(([key, title]) => <label key={key}>{title}
          <input value={value.idf.input?.[key] ?? ""} onChange={event => set({
            ...value, idf: { ...value.idf, input: {
              ...value.idf.input!, [key]: event.target.value || (key === "source_label" ? null : ""),
            } },
          })}/>
        </label>)}
        {([
          ["reduction_amount", "סכום הפחתה"],
          ["original_commutation_percent", "שיעור היוון מקורי, באחוזים"],
          ["current_commutation_percent", "שיעור היוון נוכחי, באחוזים"],
        ] as const).map(([key, title]) => <label key={key}>{title}
          <input type="number" step="any" value={value.idf.input?.[key] ?? ""}
            onChange={event => set({ ...value, idf: { ...value.idf, input: {
              ...value.idf.input!, [key]: event.target.value === "" ? NaN : Number(event.target.value),
            } } })}/>
        </label>)}
        {([
          ["commutation_date", "מועד היוון"],
          ["promoter_age_date", "מועד בסיס גיל"],
        ] as const).map(([key, title]) => <label key={key}>{title}
          <input type="date" value={value.idf.input?.[key] ?? ""}
            onChange={event => set({ ...value, idf: { ...value.idf, input: {
              ...value.idf.input!, [key]: event.target.value,
            } } })}/>
        </label>)}
      </div>}
    </>}
  </fieldset>;
}
