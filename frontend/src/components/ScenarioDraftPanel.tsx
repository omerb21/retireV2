import { useEffect, useRef, useState, type FormEvent } from "react";
import type { PensionProduct } from "../api/pensionProductsApi";
import { preserveEditedDecisionId } from "./scenarioDraftEdit";
import { ScenarioStage6Panel } from "./ScenarioStage6Panel";
import { ScenarioConversionMatrix } from "./ScenarioConversionMatrix";
import { ScenarioMonthlyComparisonPanel } from "./ScenarioMonthlyComparisonPanel";
import { readStage6GrossResultsCapability } from "../api/scenarioStage6Api";
import {
  archiveScenarioDraft, createScenarioDraft, duplicateScenarioDraft, listScenarioDrafts,
  renameScenarioDraft, replaceScenarioDraft, type DraftDecisionInput, type ScenarioDraft,
} from "../api/scenarioDraftsApi";

interface Props {
  clientId: number;
  products: PensionProduct[];
  initialSource?: { productId: string; componentCode: string } | null;
  view?: "planning" | "results";
  preferredScenarioId?: string | null;
  onScenarioSelected?: (scenarioId: string) => void;
}
function message(error: unknown): string {
  return error instanceof Error ? error.message : "אירעה שגיאה בשמירת הטיוטה.";
}
const exactAmount = (value: string): boolean => /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(value) && !/^0+(?:\.0{1,2})?$/.test(value);
export function ScenarioDraftPanel({
  clientId, products, initialSource, view = "planning",
  preferredScenarioId = null, onScenarioSelected,
}: Props) {
  const [drafts, setDrafts] = useState<ScenarioDraft[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [rename, setRename] = useState("");
  const [editingDecisionId, setEditingDecisionId] = useState<string | null>(null);
  const [source, setSource] = useState("");
  const [amount, setAmount] = useState("");
  const [action, setAction] = useState<DraftDecisionInput["action"]>("pension");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Store the client identity with the approval. A rerender for a different
  // client must fail closed before the capability-fetch effect can run.
  const [stage6Capability, setStage6Capability] = useState({
    clientId, enabled: false, loading: true,
  });
  const stage6Enabled = stage6Capability.clientId === clientId && stage6Capability.enabled;
  const stage6CapabilityLoading = stage6Capability.clientId !== clientId || stage6Capability.loading;
  const stage6CapabilityEpoch = useRef(0);
  // Client-scoped drafts remain isolated during an A/B transition.
  const visibleDrafts = drafts.filter(item => item.client_id === clientId);
  const active = visibleDrafts.find(item => item.scenario_id === selected) ?? null;
  function selectScenario(id: string) {
    setSelected(id);
    onScenarioSelected?.(id);
    setEditingDecisionId(null);
    setAmount("");
    setRename("");
  }
  async function reload(prefer?: string) {
    const list = await listScenarioDrafts(clientId);
    if (list.some(item => item.client_id !== clientId)) throw Error("זוהתה חריגה בהקשר הלקוח.");
    setDrafts(list);
    setSelected(current => prefer ?? (list.some(item => item.scenario_id === current) ? current : list[0]?.scenario_id ?? null));
    if (prefer && list.some(item => item.scenario_id === prefer)) onScenarioSelected?.(prefer);
  }
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setEditingDecisionId(null);
    setRename("");
    void listScenarioDrafts(clientId).then(list => {
      if (!mounted) return;
      if (list.some(item => item.client_id !== clientId)) throw Error("זוהתה חריגה בהקשר הלקוח.");
      setDrafts(list);
      setSelected(list.some(item => item.scenario_id === preferredScenarioId)
        ? preferredScenarioId : list[0]?.scenario_id ?? null);
    }).catch(cause => { if (mounted) setError(message(cause)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [clientId]);
  useEffect(() => {
    const epoch = ++stage6CapabilityEpoch.current;
    const controller = new AbortController();
    setStage6Capability({ clientId, enabled: false, loading: true });
    void readStage6GrossResultsCapability(clientId, controller.signal)
      .then(enabled => {
        if (stage6CapabilityEpoch.current === epoch && !controller.signal.aborted) {
          setStage6Capability({ clientId, enabled, loading: false });
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (stage6CapabilityEpoch.current === epoch && !controller.signal.aborted) {
          setStage6Capability(current =>
            current.clientId === clientId ? { ...current, loading: false } : current,
          );
        }
      });
    return () => {
      stage6CapabilityEpoch.current += 1;
      controller.abort();
    };
  }, [clientId]);
  useEffect(() => {
    if (!initialSource) return;
    const product = products.find(item => item.product_id === initialSource.productId);
    const component = product?.conversion_components?.find(
      item => item.component_code === initialSource.componentCode,
    );
    if (!component) return;
    setSource(initialSource.productId + "|" + component.component_id);
  }, [initialSource, products]);
  const sources = products.flatMap(product =>
    (product.conversion_components ?? []).map(component => ({
      key: product.product_id + "|" + component.component_id,
      productId: product.product_id, componentId: component.component_id,
      code: component.component_code,
      balance: component.balance,
      label: product.product_name + " — " + component.component_code,
    }))
  );
  async function run(fn: () => Promise<ScenarioDraft>) {
    if (busy) return false;
    setBusy(true);
    setError(null);
    try {
      const saved = await fn();
      if (saved.client_id !== clientId) throw Error("תוצאת שרת בהקשר לקוח שגוי.");
      await reload(saved.scenario_id);
      return true;
    } catch (cause) { setError(message(cause)); return false; }
    finally { setBusy(false); }
  }
  async function saveConversionBatch(batch: DraftDecisionInput[]): Promise<boolean> {
    if (!active || active.status !== "draft") return false;
    // One versioned API request for an entire program or column. It is a
    // planning draft, never a canonical conversion or a factual product write.
    const existing: DraftDecisionInput[] = active.decisions.map(decision => ({
      decision_id: decision.decision_id,
      source_product_id: decision.source_product_id,
      source_component_id: decision.source_component_id,
      component_code: decision.component_code,
      amount: decision.amount,
      action: decision.action,
      effective_date: decision.effective_date,
    }));
    return run(() => replaceScenarioDraft(clientId, active, [...existing, ...batch]));
  }
  async function create(event: FormEvent) {
    event.preventDefault();
    if (name.trim()) {
      if (await run(() => createScenarioDraft(clientId, name.trim()))) setName("");
    }
  }
  async function addDecision(event: FormEvent) {
    event.preventDefault();
    if (!active || active.status === "archived") return;
    const row = sources.find(item => item.key === source);
    if (!row || !exactAmount(amount) || !effectiveDate) {
      setError("בחר מקור, סכום חיובי בשתי ספרות עשרוניות לכל היותר ותאריך.");
      return;
    }
    const existing: DraftDecisionInput[] = active.decisions.map(item => ({
      decision_id: item.decision_id,
      source_product_id: item.source_product_id,
      source_component_id: item.source_component_id,
      component_code: item.component_code, amount: item.amount,
      action: item.action, effective_date: item.effective_date,
    }));
    const decision: DraftDecisionInput = preserveEditedDecisionId({
      source_product_id: row.productId, source_component_id: row.componentId,
      component_code: row.code, amount, action, effective_date: effectiveDate,
    }, editingDecisionId);
    const edited = editingDecisionId
      ? active.decisions.findIndex(item => item.decision_id === editingDecisionId) : -1;
    if (editingDecisionId && edited < 0) {
      setError("ההחלטה השתנתה. יש לטעון מחדש.");
      return;
    }
    const next = edited >= 0
      ? existing.map((item, i) => i === edited ? decision : item)
      : [...existing, decision];
    if (await run(() => replaceScenarioDraft(clientId, active, next))) {
      setEditingDecisionId(null);
      setAmount("");
    }
  }
  async function remove(index: number) {
    if (!active || active.status === "archived") return;
    const remaining = active.decisions.filter((_item, i) => i !== index).map(item => ({
      decision_id: item.decision_id,
      source_product_id: item.source_product_id,
      source_component_id: item.source_component_id,
      component_code: item.component_code, amount: item.amount,
      action: item.action, effective_date: item.effective_date,
    }));
    if (await run(() => replaceScenarioDraft(clientId, active, remaining))) {
      setEditingDecisionId(null);
      setAmount("");
    }
  }
  async function renameActive(event: FormEvent) {
    event.preventDefault();
    if (!active || active.status === "archived" || !rename.trim()) return;
    if (await run(() => renameScenarioDraft(clientId, active, rename.trim()))) setRename("");
  }
  function beginEdit(decision: ScenarioDraft["decisions"][number]) {
    setEditingDecisionId(decision.decision_id);
    setSource(decision.source_product_id + "|" + decision.source_component_id);
    setAmount(decision.amount);
    setAction(decision.action);
    setEffectiveDate(decision.effective_date);
    setError(null);
  }
  return <section aria-label="חלופות שמורות בשרת" className="scenario-workflow">
    <h2>{view === "planning" ? "בחר חלופה ותכנן" : "תוצאות החלופה"}</h2>
    {view === "results" && <p className="professional-workspace__boundary">
      חישוב קצבה חודשית ברוטו מוצג רק כאשר קיימים האישורים המקצועיים הדרושים.
    </p>}
    {loading && <p>טוען טיוטות...</p>}
    {error && <p role="alert">{error}</p>}
    {view === "planning" && <details open={visibleDrafts.length === 0}>
      <summary>יצירת חלופה חדשה</summary>
      <form onSubmit={create}>
        <label>שם חלופה חדשה <input value={name} maxLength={255} onChange={event => setName(event.target.value)} /></label>
        <button type="submit" disabled={busy || !name.trim()}>צור ושמור חלופה</button>
      </form>
    </details>}
    {visibleDrafts.length > 0 && <div role="group" aria-label="בחירת חלופה">
      <strong>חלופה פעילה: </strong>
      {visibleDrafts.map(item => <button type="button" key={item.scenario_id}
        aria-pressed={selected === item.scenario_id}
        onClick={() => selectScenario(item.scenario_id)} disabled={busy}>
        {item.name}{item.status === "archived" ? " (בארכיון)" : ""}
      </button>)}
    </div>}
    {active && <div>
      {view === "results" && <h3>{active.name}</h3>}
      {view === "planning" && <ScenarioConversionMatrix
        key={`${clientId}:${active.scenario_id}`}
        products={products} scenario={active} disabled={active.status !== "draft"}
        busy={busy} initialSource={initialSource}
        onApply={saveConversionBatch} />}
      {view === "results" && stage6Enabled && active.decisions.length > 0 &&
        <ScenarioStage6Panel key={`${clientId}:${active.scenario_id}:${active.version}:${active.status}`}
          clientId={clientId} scenario={active} onSaved={reload} autoInspectAllocations/>}
      {view === "results" && !stage6Enabled && <p role="status">
        {stage6CapabilityLoading ? "בודק אפשרות להצגת תוצאות..." : "חישובי קצבה אינם מורשים בסביבה הזאת."}
      </p>}
      {view === "planning" && <>
      {active.status !== "archived" && <>
        <details>
          <summary>ניהול חלופה: שינוי שם, שכפול וארכיון</summary>
        <form onSubmit={renameActive}>
          <label>שינוי שם חלופה <input maxLength={255} value={rename} onChange={event => setRename(event.target.value)} placeholder={active.name}/></label>
          <button type="submit" disabled={busy || !rename.trim()}>שמור שם</button>
        </form>
        <button type="button" disabled={busy} onClick={() => void run(() => duplicateScenarioDraft(clientId, active.scenario_id, active.name + " — העתק"))}>שכפל חלופה</button>
        <button type="button" disabled={busy} onClick={() => void run(() => archiveScenarioDraft(clientId, active))}>העבר לארכיון</button>
        </details>
        {editingDecisionId !== null && <form onSubmit={addDecision} aria-label="עריכת המרה מתוכננת">
          <h4>עריכת המרה</h4>
          <label>רכיב מתוך התיק
            <select value={source} onChange={event => setSource(event.target.value)}>
              <option value="">בחר מקור</option>
              {sources.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}
            </select>
          </label>
          <label>סכום מתוכנן (₪) <input inputMode="decimal" value={amount} onChange={event => setAmount(event.target.value)}/></label>
          <label>יעד <select value={action} onChange={event => setAction(event.target.value as DraftDecisionInput["action"])}>
            <option value="pension">קצבה — טיוטה</option>
            <option value="capital_asset">הון — טיוטה</option>
          </select></label>
          <label>תאריך תכנון <input type="date" value={effectiveDate} onChange={event => setEffectiveDate(event.target.value)}/></label>
          <button type="submit" disabled={busy || !source || !exactAmount(amount) || !effectiveDate}>שמור שינוי</button>
          <button type="button" onClick={() => { setEditingDecisionId(null); setAmount(""); }}>בטל עריכה</button>
        </form>}
      </>}
      <h4>המרות מתוכננות בחלופה ({active.decisions.length})</h4>
      <ul className="scenario-conversion__saved">{active.decisions.map((decision, index) => <li key={decision.decision_id}>
        <strong>{sources.find(item => item.componentId === decision.source_component_id)?.label ?? decision.component_code}</strong>
        {" "} - {decision.amount} ₪ {decision.action === "pension" ? "לקצבה" : "להון"}
        {" "} - ביצוע מתוכנן: {decision.effective_date}
        {active.status !== "archived" && <>
          <button disabled={busy} type="button" onClick={() => beginEdit(decision)}>ערוך</button>
          <button disabled={busy} type="button" onClick={() => void remove(index)}>מחק המרה</button>
        </>}
      </li>)}</ul>
      </>}
    </div>}
    {view === "results" && stage6Enabled &&
      <ScenarioMonthlyComparisonPanel clientId={clientId} scenarios={visibleDrafts}/>}
  </section>;
}
