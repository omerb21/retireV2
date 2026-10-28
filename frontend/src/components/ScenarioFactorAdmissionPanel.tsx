import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  readFactorAdmissionCursor, submitProfessionalFactorAdmission,
  type FactorEvidenceType, type FactorAdmissionCursor,
} from "../api/scenarioStage6Api";

interface Props {
  clientId: number;
  scenarioId: string;
  decisionId: string;
  scenarioVersion: number;
  disabled: boolean;
  onApproved: () => void;
}
const positiveDivisor = (value: string): boolean => value.length <= 128 && /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value) && /[1-9]/.test(value);

/** Dedicated professional acknowledgment, never a calculation or insurer quote. */
export function ScenarioFactorAdmissionPanel({
  clientId, scenarioId, decisionId, scenarioVersion, disabled, onApproved,
}: Props) {
  const [opened, setOpened] = useState(false);
  const [cursor, setCursor] = useState<FactorAdmissionCursor | null>(null);
  const [factorValue, setFactorValue] = useState("");
  const [evidenceType, setEvidenceType] = useState<FactorEvidenceType>("PLANNER_ASSUMPTION");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const epoch = useRef(0);

  useEffect(() => {
    ++epoch.current;
    setOpened(false);
    setBusy(false);
    setCursor(null);
    setFactorValue("");
    setEvidenceReference("");
    setSuccess(null);
    setError(null);
  }, [clientId, scenarioId, decisionId, scenarioVersion]);

  async function open() {
    if (disabled || busy) return;
    const current = ++epoch.current;
    setError(null);
    setSuccess(null);
    setCursor(null);
    setBusy(true);
    try {
      const response = await readFactorAdmissionCursor(clientId, scenarioId, decisionId);
      if (epoch.current !== current) return;
      if (response.scenario_version !== scenarioVersion
          || !Number.isInteger(response.latest_admission_revision)
          || response.latest_admission_revision < 0) {
        throw Error("FACTOR_ADMISSION_SCENARIO_STALE");
      }
      setCursor(response);
      setOpened(true);
    } catch (cause) {
      if (epoch.current === current) setError(cause instanceof Error ? cause.message : "FACTOR_ADMISSION_UNAVAILABLE");
    } finally {
      if (epoch.current === current) setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || disabled || !cursor || !positiveDivisor(factorValue)
        || !evidenceReference.trim()) return;
    const current = ++epoch.current;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const receipt=await submitProfessionalFactorAdmission(clientId,scenarioId,decisionId,{
        expected_scenario_version: scenarioVersion,
        expected_admission_revision:cursor.latest_admission_revision,
        factor_value:factorValue,
        factor_evidence_type:evidenceType,
        factor_evidence_reference:evidenceReference.trim(),
      });
      if (epoch.current !== current) return;
      if (receipt.execution_allowed !== false
          || receipt.admission_revision !== cursor.latest_admission_revision + 1
          || !/^[0-9a-f]{64}$/.test(receipt.professional_admission_fingerprint)) {
        throw Error("FACTOR_ADMISSION_RECEIPT_INVALID");
      }
      setOpened(false);
      setCursor(null);
      setFactorValue("");
      setEvidenceReference("");
      setSuccess("אישור המקדם נשמר. האומדן ייבדק מחדש מול נתוני המסד המעודכנים.");
      onApproved();
    } catch (cause) {
      if (epoch.current === current) {
        setCursor(null); // Every conflict requires rereading the authoritative CAS cursor.
        setOpened(false);
        setError(cause instanceof Error ? cause.message : "FACTOR_ADMISSION_REJECTED");
      }
    } finally {
      if (epoch.current === current) setBusy(false);
    }
  }

  return <section aria-label="אישור מקדם קצבה מקצועי">
    <button type="button" disabled={disabled || busy} onClick={() => void open()}>
      {busy ? "בודק גרסה..." : "הזן ואשר מקדם מקצועי"}
    </button>
    {error && <p role="alert">{error} — יש לרענן את האישור לפני ניסיון חוזר.</p>}
    {success && <p role="status">{success}</p>}
    {opened && cursor && <form onSubmit={event => void submit(event)}>
      <p>גרסת חלופה {scenarioVersion}; גרסת אישור אחרונה {cursor.latest_admission_revision}.
        הגרסה אינה ראיה שהאישור הקודם תקף.</p>
      <label>מקדם קצבה (מחלק, מספר חיובי מדויק)
        <input inputMode="decimal" value={factorValue} onChange={event => setFactorValue(event.target.value)}/>
      </label>
      <label>סוג מקור
        <select value={evidenceType} onChange={event => setEvidenceType(event.target.value as FactorEvidenceType)}>
          <option value="PLANNER_ASSUMPTION">הנחת מתכנן — לא אישור מבטח</option>
          <option value="INSURER_QUOTE">הצעת מבטח</option>
          <option value="POLICY_CONTRACT">מסמך פוליסה או חוזה</option>
        </select>
      </label>
      <label>אסמכתה ותנאי המסלול
        <textarea value={evidenceReference} maxLength={512} rows={3}
          onChange={event => setEvidenceReference(event.target.value)}/>
      </label>
      <p>האישור מתעד מקור ומקדם. הוא אינו מאשר זכאות, מס, התחייבות מבטח או ביצוע קצבה.</p>
      <button type="submit" disabled={disabled || busy || !positiveDivisor(factorValue) || !evidenceReference.trim()}>
        אשר את המקדם ושמור גרסת אישור
      </button>
      <button type="button" disabled={busy} onClick={() => { ++epoch.current; setOpened(false); setCursor(null); }}>
        בטל אישור
      </button>
    </form>}
  </section>;
}
