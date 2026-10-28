import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import { ScenarioFactorAdmissionPanel } from "./ScenarioFactorAdmissionPanel";
import {
  listScenarioPensionElections, saveScenarioPensionElections, readScenarioGrossEstimate,
  readScenarioAllocationEvidence, validScenarioAllocationEvidence, type ScenarioAllocationEvidence,
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

const estimateFields = [
  "schema_version", "client_id", "scenario_id", "scenario_version", "decision_id",
  "source_id", "result_state", "execution_allowed", "blockers",
  "coefficient_provenance", "professional_admission_fingerprint",
  "planning_calculation_input_fingerprint", "monthly_basis_semantic_fingerprint",
  "monthly_basis_source_fingerprint", "temporal_semantic_fingerprint",
  "temporal_source_fingerprint", "pte_source_execution_fingerprint",
  "pte_source_result_fingerprint", "monthly_estimate_gross_ils",
  "retirement_target_date", "statement_date", "result_fingerprint",
] as const;
const identityHashes = [
  "planning_calculation_input_fingerprint", "monthly_basis_semantic_fingerprint",
  "monthly_basis_source_fingerprint", "temporal_semantic_fingerprint",
  "temporal_source_fingerprint",
] as const;
const hash = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const optionalHash = (value: unknown): boolean => value === null || hash(value);
const scenarioSourceId = (scenarioId: string, decisionId: string): string =>
  `scenario-decision:${scenarioId.replace(/%/g, "%25").replace(/:/g, "%3A")}`
  + `:${decisionId.replace(/%/g, "%25").replace(/:/g, "%3A")}`;

function closedEstimateEnvelope(value: ScenarioGrossEstimate, clientId: number,
  scenarioId: string, decisionId: string, scenarioVersion: number): boolean {
  if (Object.keys(value).sort().join("|") !== [...estimateFields].sort().join("|")
      || value.schema_version !== "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1"
      || value.client_id !== clientId || value.scenario_id !== scenarioId
      || value.decision_id !== decisionId || !hash(value.result_fingerprint)
      || value.source_id !== scenarioSourceId(scenarioId, decisionId)
      || !Array.isArray(value.blockers)
      || value.blockers.some(code => typeof code !== "string" || !code)
      || value.blockers.join("|") !== [...new Set(value.blockers)].sort().join("|")) return false;
  if (value.result_state === "BLOCKED") {
    return value.execution_allowed === false && value.blockers.length > 0
      && value.monthly_estimate_gross_ils === null
      && value.pte_source_execution_fingerprint === null
      && value.pte_source_result_fingerprint === null
      && (value.scenario_version === null || Number.isInteger(value.scenario_version))
      && identityHashes.every(field => optionalHash(value[field]))
      && optionalHash(value.professional_admission_fingerprint)
      && (value.retirement_target_date === null || typeof value.retirement_target_date === "string")
      && (value.statement_date === null || typeof value.statement_date === "string");
  }
  const provenance=value.coefficient_provenance;
  return value.result_state === "RESULT_READY" && value.execution_allowed === true
    && value.scenario_version === scenarioVersion && value.blockers.length === 0
    && typeof value.source_id === "string" && value.source_id.length > 0
    && identityHashes.every(field => hash(value[field]))
    && hash(value.professional_admission_fingerprint)
    && hash(value.pte_source_execution_fingerprint) && hash(value.pte_source_result_fingerprint)
    && /^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(value.monthly_estimate_gross_ils ?? "")
    && typeof value.retirement_target_date === "string" && value.retirement_target_date.length > 0
    && typeof value.statement_date === "string" && value.statement_date.length > 0
    && provenance !== null
    && Object.keys(provenance).sort().join("|") === [
      "source_level", "factor_value", "factor_evidence_type", "factor_evidence_reference",
      "payout_option_name", "admission_revision",
    ].sort().join("|")
    && provenance.source_level === "MANUAL_PROFESSIONAL_OVERRIDE"
    && typeof provenance.factor_value === "string" && provenance.factor_value.length > 0
    && typeof provenance.factor_evidence_type === "string" && provenance.factor_evidence_type.length > 0
    && typeof provenance.factor_evidence_reference === "string" && provenance.factor_evidence_reference.length > 0
    && typeof provenance.payout_option_name === "string" && provenance.payout_option_name.length > 0
    && Number.isInteger(provenance.admission_revision) && provenance.admission_revision > 0;
}

/** Phase-1 internal workspace only; does NOT enter or approve factor values. */
export function ScenarioStage6Panel({ clientId, scenario, onSaved }: Props) {
  const [elections, setElections] = useState<ScenarioPensionElection[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [estimate, setEstimate] = useState<ScenarioGrossEstimate | null>(null);
  const [allocation, setAllocation] = useState<ScenarioAllocationEvidence | null>(null);
  const [allocationBusy, setAllocationBusy] = useState(false);
  const [allocationError, setAllocationError] = useState<string | null>(null);
  const epoch = useRef(0);
  const allocationEpoch = useRef(0);
  const scenarioKey = `${clientId}|${scenario.scenario_id}|${scenario.version}`;

  useEffect(() => {
    const current = ++epoch.current;
    setLoaded(false);
    setBusy(false);
    setDirty(false);
    setError(null);
    setEstimate(null);
    allocationEpoch.current += 1;
    setAllocation(null);
    setAllocationError(null);
    setAllocationBusy(false);
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
    return () => { epoch.current += 1; allocationEpoch.current += 1; };
  }, [scenarioKey, clientId, scenario.scenario_id]);

  function modify(id: string, patch: Partial<ScenarioPensionElection>) {
    allocationEpoch.current += 1;
    setAllocationBusy(false);
    setAllocation(null);
    setEstimate(null);
    setDirty(true);
    setElections(current => current.map(row => row.decision_id === id ? { ...row, ...patch } : row));
  }

  const pensionDecisions = scenario.decisions.filter(d => d.action === "pension");
  function startEditing(id: string) {
    allocationEpoch.current += 1;
    setAllocationBusy(false);
    setAllocation(null);
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
    allocationEpoch.current += 1;
    setAllocationBusy(false);
    setAllocation(null);
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
      if (!closedEstimateEnvelope(result, clientId, scenario.scenario_id,
          decisionId, scenario.version)) {
        throw Error("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
      }
      setEstimate(result);
    } catch (cause) {
      if (epoch.current === current) setError(explain(cause));
    } finally {
      if (epoch.current === current) setBusy(false);
    }
  }

  async function inspectAllocations() {
    if (allocationBusy || dirty || scenario.status !== "draft") return;
    const current = ++allocationEpoch.current;
    setAllocationBusy(true);
    setAllocation(null);
    setAllocationError(null);
    try {
      const result = await readScenarioAllocationEvidence(clientId, scenario.scenario_id);
      if (allocationEpoch.current !== current) return;
      if (!validScenarioAllocationEvidence(result, clientId, scenario.scenario_id, scenario.version)) {
        throw Error("SCENARIO_ALLOCATION_EVIDENCE_INCOMPLETE");
      }
      setAllocation(result);
    } catch (cause) {
      if (allocationEpoch.current === current) setAllocationError(explain(cause));
    } finally {
      if (allocationEpoch.current === current) setAllocationBusy(false);
    }
  }

  return <section aria-label="בחירת קצבה ואומדן תרחיש פנימי">
    <h4>בחירת קצבה — סביבת בדיקות מאובטחת בלבד</h4>
    <p className="professional-workspace__boundary">
      בחירת הקצבה היא טיוטה. שמירתה מעדכנת את גרסת החלופה ומבטלת תוקף של אישורים קודמים.
      אין כאן אישור מקדם, זכאות או הבטחת קצבה.
    </p>
    {error && <p role="alert">{error}</p>}
    <section aria-label="בדיקת הקצאות ללא חישוב פיננסי">
      <h5>בקרת הקצאות תרחיש</h5>
      <p>נתונים מבניים בלבד לרכיבים שהוקצו בהחלטות התרחיש. זו אינה סקירה של כל נכסי הלקוח, ואינה קצבה מחושבת, מס, תזרים או אישור מקצועי.</p>
      <button type="button" disabled={allocationBusy || dirty || scenario.status !== "draft"} onClick={() => void inspectAllocations()}>
        בדוק הקצאות ויתרות לא מוקצות
      </button>
      {allocationError && <p role="alert">{allocationError}</p>}
      {allocationBusy && <p role="status">מאמת נתוני הקצאה...</p>}
      {allocation && <section aria-label="תוצאות בקרת הקצאות">
        <p role="status">{allocation.overall_status === "BLOCKED" ? "קיימות חסימות בבקרת ההקצאות" : "בדיקה מבנית בלבד, אינה מאשרת חישוב"}</p>
        {allocation.candidate_blockers.length > 0 && <p role="alert">חסימות מבניות: {allocation.candidate_blockers.join(", ")}</p>}
        {allocation.allocation_evidence.blocker_codes.length > 0 && <p role="alert">חסימות הקצאה: {allocation.allocation_evidence.blocker_codes.join(", ")}</p>}
        {allocation.allocation_evidence.sources.length === 0 && <p>לא נמצאו החלטות הקצאה בתרחיש.</p>}
        {allocation.allocation_evidence.sources.map(row => <p key={`${row.product_id}:${row.component_id}`}>
          {row.component_code ?? row.component_id}: יתרה מקורית {row.balance ?? "לא זמינה"} ₪,
          מוקצה {row.allocated} ₪ (להחלטות קצבה {row.allocation_by_action.pension} ₪; להחלטות הון {row.allocation_by_action.capital_asset} ₪),
          לא מוקצה {row.unallocated ?? "חסום"} ₪.
          {row.blocker_codes.length > 0 && ` חסימות: ${row.blocker_codes.join(", ")}`}
        </p>)}
      </section>}
    </section>
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
          disabled={busy} onApproved={() => {
            setEstimate(null);
            allocationEpoch.current += 1;
            setAllocation(null);
            setAllocationBusy(false);
          }} />)}
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
