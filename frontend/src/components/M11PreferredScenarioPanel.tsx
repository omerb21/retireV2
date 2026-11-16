import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import {
  readM11Selection, saveM11Selection, type M11SelectionState,
} from "../api/m11PreferredScenarioApi";

interface Props {
  clientId: number;
  scenarios: ScenarioDraft[];
  onChooseScenario?: (scenarioId: string) => void;
}
function safeState(value: M11SelectionState, clientId: number): boolean {
  return value.client_id === clientId && value.history.every(row => row.client_id === clientId)
    && (value.current === null || value.current.client_id === clientId);
}
export function M11PreferredScenarioPanel({ clientId, scenarios, onChooseScenario }: Props) {
  const [state, setState] = useState<M11SelectionState | null>(null);
  const [choice, setChoice] = useState("");
  const [rationale, setRationale] = useState("");
  const [loadedFor, setLoadedFor] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);
  const available = scenarios.filter(s => s.client_id === clientId && s.status !== "archived");
  const selected = available.find(s => s.scenario_id === choice) ?? null;
  const current = loadedFor === clientId ? state?.current : null;
  const selection = loadedFor === clientId ? state : null;
  useEffect(() => {
    const epoch = ++generation.current;
    setState(null);
    setChoice("");
    setRationale("");
    setLoadedFor(null);
    setError(null);
    setBusy(false);
    void readM11Selection(clientId).then(result => {
      if (epoch !== generation.current) return;
      if (!safeState(result, clientId)) throw Error("M11_CLIENT_CONTEXT_INVALID");
      setState(result);
      setLoadedFor(clientId);
      setChoice(result.current?.scenario_id ?? "");
      setRationale(result.current?.rationale ?? "");
    }).catch(e => {
      if (epoch === generation.current) setError(e instanceof Error ? e.message : "טעינת הבחירה נכשלה");
    });
    return () => { generation.current += 1; };
  }, [clientId]);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected || !selection || busy) return;
    const epoch = generation.current;
    setBusy(true);
    setError(null);
    try {
      const result = await saveM11Selection(clientId, {
        scenario_id: selected.scenario_id,
        expected_scenario_version: selected.version,
        expected_selection_revision: selection.revision,
        rationale,
      });
      if (generation.current !== epoch) return;
      if (!safeState(result, clientId)) throw Error("M11_CLIENT_CONTEXT_INVALID");
      setState(result);
      setRationale(result.current?.rationale ?? "");
    } catch(e) {
      if (generation.current === epoch)
        setError(e instanceof Error ? e.message : "שמירת הבחירה נכשלה");
    } finally {
      if (generation.current === epoch) setBusy(false);
    }
  }
  const stale = !!(current && (selection?.outdated || !available.some(s =>
    s.scenario_id === current.scenario_id && s.version === current.scenario_version && s.status === "draft"
  )));
  return <section aria-label="בחירת חלופה מועדפת M11" className="scenario-workflow">
    <h3>בחירת חלופה מועדפת לתכנון</h3>
    <p className="professional-workspace__boundary">בחירה זו מתעדת את החלטת המתכנן בלבד. היא אינה מאשרת חישובים או נתונים חסרים ואינה מפיקה דוח.</p>
    {!selection && <p role="status">טוען בחירה שמורה...</p>}
    {error && <p role="alert">{error}</p>}
    {current && <p role="status">
      בחירה שמורה: {available.find(s => s.scenario_id === current.scenario_id)?.name ?? current.scenario_id},
      גרסה {current.scenario_version}, שמירה {current.saved_at ?? "מועד טרם נקלט"}.
    </p>}
    {stale && <p role="status" className="professional-workspace__error">
      החלופה השמורה השתנתה או הועברה לארכיון. יש לבדוק את הנתונים לפני הסתמכות על הבחירה.
    </p>}
    {selected?.status === "needs_revalidation" && <p role="status" className="professional-workspace__error">
      נתוני המקור של החלופה מחייבים בדיקה מחדש. שמירת הבחירה לא תאשר אותם.
    </p>}
    {selected?.decisions.some(d => d.validation_state !== "unverified") && <p role="status">
      קיימות החלטות המחייבות אימות מחודש.
    </p>}
    <p>תוצאות חסרות או חסומות אינן מקבלות תוקף בעקבות בחירה. אין קשר מאומת לריצות M09/M10 או לתוצאות Stage 6 שמורות.</p>
    <form onSubmit={save}>
      <label>חלופה מועדפת
        <select value={selected?.scenario_id ?? ""} disabled={!selection || busy}
          onChange={e => { setChoice(e.target.value); onChooseScenario?.(e.target.value); }}>
          <option value="">בחר חלופה</option>
          {available.map(s => <option key={s.scenario_id} value={s.scenario_id}>{s.name} (גרסה {s.version})</option>)}
        </select>
      </label>
      <label>נימוק מקצועי (לא חובה)
        <textarea value={rationale} maxLength={5000} disabled={!selection || busy}
          onChange={e => setRationale(e.target.value)}/>
      </label>
      <button type="submit" disabled={!selection || !selected || busy}>שמור בחירה</button>
    </form>
    {selection && selection.history.length > 1 && <details>
      <summary>היסטוריית בחירות ({selection.history.length})</summary>
      <ul>{selection.history.map(item =>
        <li key={item.selection_id}>
          גרסה {item.revision}: {item.scenario_id}, חלופה {item.scenario_version},
          {item.saved_at ?? "מועד לא ידוע"}{item.rationale ? ` - ${item.rationale}` : ""}
        </li>)}</ul>
    </details>}
  </section>;
}
