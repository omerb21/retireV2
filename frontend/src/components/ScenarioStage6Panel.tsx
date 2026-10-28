import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import { ScenarioFactorAdmissionPanel } from "./ScenarioFactorAdmissionPanel";
import {
  listScenarioPensionElections, saveScenarioPensionElections, readScenarioGrossEstimate,
  type ScenarioPensionElection, type ScenarioGrossEstimate,
} from "../api/scenarioStage6Api";

interface Props {
  clientId: number;
  scenario: ScenarioDraft;
  onSaved: (id: string) => Promise<void>;
}
function explain(error: unknown): string {
  return error instanceof Error ? error.message : "לא ניתן להשלים את הפעולה.";
}

/** Phase-1 internal workspace only; does NOT enter or approve factor values. */
export function ScenarioStage6Panel({ clientId, scenario, onSaved }: Props) {
  const [elections, setElections] = useState<ScenarioPensionElection[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [estimate, setEstimate] = useState<ScenarioGrossEstimate | null>(null);
  const epoch = useRef(0);
  const scenarioKey = `${clientId}|${scenario.scenario_id}|${scenario.version}`;

  useEffect(() => {
    const current = ++epoch.current;
    setLoaded(false);
    setBusy(false);
    setDirty(false);
    setError(null);
    setEstimate(null);
    setElections([]);
    void listScenarioPensionElections(clientId, scenario.scenario_id)
      .then(rows => {
        if (epoch.current !== current) return;
        setElections(rows);
        setLoaded(true);
      })
      .catch(cause => {
        if (epoch.current === current) setError(explain(cause));
      });
    return () => { epoch.current += 1; };
  }, [scenarioKey, clientId, scenario.scenario_id]);

  function modify(id: string, patch: Partial<ScenarioPensionElection>) {
    setEstimate(null);
    setDirty(true);
    setElections(current => current.map(row => row.decision_id === id ? { ...row, ...patch } : row));
  }

  const pensionDecisions = scenario.decisions.filter(d => d.action === "pension");
  function startEditing(id: string) {
    const decision = pensionDecisions.find(row => row.decision_id === id);
    if (!decision || elections.some(row => row.decision_id === id)) return;
    setEstimate(null);
    setDirty(true);
    setElections(current => [...current, {
      decision_id: id, pension_start_date: decision.effective_date,
      target_year: Number(decision.effective_date.slice(0, 4)),
      survivors_option: "לבדיקה מקצועית", spouse_age_diff: 0,
      coefficient_selection: "manual_review_required", company_name: null,
      option_name: null,
    }]);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy || !loaded || scenario.status !== "draft") return;
    const current = ++epoch.current;
    setBusy(true);
    setError(null);
    setEstimate(null);
    try {
      const rows = elections.map(row => ({
        ...row, target_year: Number(row.pension_start_date.slice(0, 4)),
      }));
      if (rows.some(row => !row.pension_start_date || !row.survivors_option.trim()
        || !row.option_name?.trim() || !row.company_name?.trim())) {
        throw Error("יש להשלים תאריך, זכויות שאירים, חברה ומסלול לפני השמירה.");
      }
      await saveScenarioPensionElections(clientId, scenario.scenario_id, scenario.version, rows);
      if (epoch.current === current) await onSaved(scenario.scenario_id);
    } catch (cause) {
      if (epoch.current === current) setError(explain(cause));
    } finally {
      if (epoch.current === current) setBusy(false);
    }
  }

  async function checkEstimate(decisionId: string) {
    if (busy || !loaded || dirty || scenario.status !== "draft") return;
    const current = ++epoch.current;
    setBusy(true);
    setEstimate(null);
    setError(null);
    try {
      const result = await readScenarioGrossEstimate(clientId, scenario.scenario_id, decisionId);
      if (epoch.current !== current) return;
      if (result.scenario_id !== scenario.scenario_id || result.decision_id !== decisionId
          || result.schema_version !== "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1"
          || !/^[0-9a-f]{64}$/.test(result.result_fingerprint)) {
        throw Error("STAGE6_CONTEXT_MISMATCH");
      }
      if (result.result_state === "RESULT_READY"
          && (result.scenario_version !== scenario.version
            || result.execution_allowed !== true
            || !/^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(result.monthly_estimate_gross_ils ?? "")
            || !result.coefficient_provenance
            || !/^[0-9a-f]{64}$/.test(result.professional_admission_fingerprint ?? ""))) {
        throw Error("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
      }
      setEstimate(result);
    } catch (cause) {
      if (epoch.current === current) setError(explain(cause));
    } finally {
      if (epoch.current === current) setBusy(false);
    }
  }

  return <section aria-label="בחירת קצבה ואומדן תרחיש פנימי">
    <h4>בחירת קצבה — סביבת בדיקות מאובטחת בלבד</h4>
    <p className="professional-workspace__boundary">
      בחירת הקצבה היא טיוטה. שמירתה מעדכנת את גרסת החלופה ומבטלת תוקף של אישורים קודמים.
      אין כאן אישור מקדם, זכאות או הבטחת קצבה.
    </p>
    {error && <p role="alert">{error}</p>}
    {!loaded && !error && <p>טוען בחירות קצבה...</p>}
    {loaded && <form onSubmit={event => void save(event)}>
      {pensionDecisions.map(decision => {
        const row = elections.find(item => item.decision_id === decision.decision_id);
        return <fieldset key={decision.decision_id} disabled={busy || scenario.status !== "draft"}>
          <legend>{decision.component_code} — {decision.amount} ₪</legend>
          {!row ? <button type="button" onClick={() => startEditing(decision.decision_id)}>
            הגדר בחירת קצבה
          </button> : <>
            <label>מועד תחילת הקצבה
              <input type="date" value={row.pension_start_date} min={decision.effective_date}
                onChange={event => modify(row.decision_id, {
                  pension_start_date: event.target.value, target_year: Number(event.target.value.slice(0, 4)),
                })}/>
            </label>
            <label>בחירת שאירים
              <input value={row.survivors_option} maxLength={128}
                onChange={event => modify(row.decision_id, { survivors_option: event.target.value })}/>
            </label>
            <label>פער גיל בן/בת זוג
              <input type="number" min={-100} max={100} value={row.spouse_age_diff}
                onChange={event => modify(row.decision_id, { spouse_age_diff: Number(event.target.value) })}/>
            </label>
            <label>חברה
              <input value={row.company_name ?? ""} maxLength={255}
                onChange={event => modify(row.decision_id, { company_name: event.target.value || null })}/>
            </label>
            <label>מסלול קצבה
              <input value={row.option_name ?? ""} maxLength={255}
                onChange={event => modify(row.decision_id, { option_name: event.target.value || null })}/>
            </label>
            <label>מקור מקדם
              <select value={row.coefficient_selection}
                onChange={event => modify(row.decision_id, {
                  coefficient_selection: event.target.value as ScenarioPensionElection["coefficient_selection"],
                })}>
                <option value="manual_review_required">מקדם ידני — מחייב אישור מקצועי נפרד</option>
                <option value="catalog_candidate">מועמד קטלוגי — חישוב אינו זמין בשלב זה</option>
              </select>
            </label>
            <p>מקדם: נדרש אישור מקצועי נפרד; אינו נגזר או מאושר על ידי טופס זה.</p>
            <button type="button" disabled={busy || dirty || row.coefficient_selection !== "manual_review_required"} onClick={() => void checkEstimate(decision.decision_id)}>
              בדוק אומדן קצבה מאושר
            </button>
          </>}
        </fieldset>;
      })}
      {dirty && <p>בחירות הקצבה שונו. שמור ורענן את החלופה לפני בדיקת אומדן.</p>}
      <button type="submit" disabled={busy || !dirty || scenario.status !== "draft" || !pensionDecisions.length}>
        שמור בחירות קצבה כטיוטה
      </button>
    </form>}
    {loaded && !dirty && scenario.status === "draft" &&
      elections.filter(row => row.coefficient_selection === "manual_review_required" &&
        pensionDecisions.some(d => d.decision_id === row.decision_id))
        .map(row => <ScenarioFactorAdmissionPanel
          key={row.decision_id} clientId={clientId} scenarioId={scenario.scenario_id}
          scenarioVersion={scenario.version} decisionId={row.decision_id}
          disabled={busy} onApproved={() => setEstimate(null)} />)}
    {estimate && <section aria-label="תוצאת אומדן לא מחייבת">
      {estimate.result_state === "RESULT_READY" && estimate.execution_allowed
        && estimate.monthly_estimate_gross_ils != null
        ? <>
          <p>אומדן קצבה חודשית ברוטו: {estimate.monthly_estimate_gross_ils} ₪</p>
          <p>לפי מקדם מקצועי מאושר — {estimate.coefficient_provenance?.factor_evidence_type ?? "מקור לא ידוע"}.
            אומדן נומינלי, ללא מס, הצמדה או הבטחת זכאות.</p>
        </>
        : <>
          <p role="status">לא ניתן להפיק אומדן קצבה מהנתונים המאושרים כעת.</p>
          <ul>{estimate.blockers.map(code => <li key={code}>{code}</li>)}</ul>
        </>}
    </section>}
  </section>;
}
