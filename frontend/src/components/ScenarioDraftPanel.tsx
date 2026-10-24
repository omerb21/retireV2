import { useEffect, useRef, useState, type FormEvent } from "react";
import type { PensionProduct } from "../api/pensionProductsApi";
import { preserveEditedDecisionId } from "./scenarioDraftEdit";
import { previewDraftDecision, type CheckedPermissionComponent } from "../api/scenarioDraftPermissionApi";
import {
  archiveScenarioDraft, createScenarioDraft, duplicateScenarioDraft, listScenarioDrafts,
  replaceScenarioDraft, type DraftDecisionInput, type ScenarioDraft,
} from "../api/scenarioDraftsApi";

interface Props { clientId: number; products: PensionProduct[] }
function message(error: unknown): string {
  return error instanceof Error ? error.message : "אירעה שגיאה בשמירת הטיוטה.";
}
const exactAmount = (value: string): boolean => /^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(value) && !/^0+(?:\.0{1,2})?$/.test(value);
function asCents(value: string): bigint | null {
  if (!/^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?$/.test(value)) return null;
  const [whole, decimals = ""] = value.split(".");
  return BigInt(whole) * 100n + BigInt(decimals.padEnd(2, "0"));
}
function displayCents(value: bigint): string {
  const abs = value < 0n ? -value : value;
  return (value < 0n ? "-" : "") + (abs / 100n).toString() + "." + (abs % 100n).toString().padStart(2, "0");
}
export function ScenarioDraftPanel({ clientId, products }: Props) {
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
  const [permissions, setPermissions] = useState<Record<string, { status: "ready" | "error"; component?: CheckedPermissionComponent; error?: string }>>({});
  const [checkingPermission, setCheckingPermission] = useState<string | null>(null);
  const permissionEpoch = useRef(0);
  // Invalidate already displayed permission evidence when the visible factual snapshot changes.
  const sourceSnapshot = JSON.stringify(products.map(product => ({
    id: product.product_id, version: product.version, type: product.product_type,
    kind: product.source_kind, components: product.conversion_components?.map(component => ({
      id: component.component_id, code: component.component_code, balance: component.balance,
    })),
  })));
  const sourceSnapshotRef = useRef(sourceSnapshot);
  if (sourceSnapshotRef.current !== sourceSnapshot) {
    sourceSnapshotRef.current = sourceSnapshot;
    permissionEpoch.current += 1;
  }
  const latestContext = useRef({ clientId, selected, products });
  latestContext.current = { clientId, selected, products };
  const active = drafts.find(item => item.scenario_id === selected) ?? null;
  useEffect(() => {
    setPermissions({});
    setCheckingPermission(null);
  }, [sourceSnapshot]);

  async function reload(prefer?: string) {
    const list = await listScenarioDrafts(clientId);
    if (list.some(item => item.client_id !== clientId)) throw Error("זוהתה חריגה בהקשר הלקוח.");
    setDrafts(list);
    permissionEpoch.current += 1;
    setPermissions({});
    setCheckingPermission(null);
    setSelected(current => prefer ?? (list.some(item => item.scenario_id === current) ? current : list[0]?.scenario_id ?? null));
  }
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setEditingDecisionId(null);
    setRename("");
    permissionEpoch.current += 1;
    setPermissions({});
    setCheckingPermission(null);
    void listScenarioDrafts(clientId).then(list => {
      if (!mounted) return;
      if (list.some(item => item.client_id !== clientId)) throw Error("זוהתה חריגה בהקשר הלקוח.");
      setDrafts(list);
      setSelected(list[0]?.scenario_id ?? null);
    }).catch(cause => { if (mounted) setError(message(cause)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; permissionEpoch.current += 1; };
  }, [clientId]);
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
    const decisions: DraftDecisionInput[] = active.decisions.map(item => ({
      decision_id: item.decision_id,
      source_product_id: item.source_product_id,
      source_component_id: item.source_component_id,
      component_code: item.component_code, amount: item.amount,
      action: item.action, effective_date: item.effective_date,
    }));
    if (await run(() => replaceScenarioDraft(clientId, active, decisions, rename.trim()))) setRename("");
  }
  function beginEdit(decision: ScenarioDraft["decisions"][number]) {
    setEditingDecisionId(decision.decision_id);
    setSource(decision.source_product_id + "|" + decision.source_component_id);
    setAmount(decision.amount);
    setAction(decision.action);
    setEffectiveDate(decision.effective_date);
    setError(null);
  }
  return <section aria-label="חלופות שמורות בשרת">
    <h2>חלופות תכנון שמורות</h2>
    <p className="professional-workspace__boundary">
      החלופות נשמרות בשרת בנפרד מנתוני תיק הלקוח. כל החלטה היא טיוטה לא מאומתת:
      לא בוצעה בדיקת זכאות, הרשאה מקצועית, מס, קצבה או המרה כספית.
    </p>
    {loading && <p>טוען טיוטות...</p>}
    {error && <p role="alert">{error}</p>}
    <form onSubmit={create}>
      <label>שם חלופה חדשה <input value={name} maxLength={255} onChange={event => setName(event.target.value)} /></label>
      <button type="submit" disabled={busy || !name.trim()}>צור ושמור חלופה</button>
    </form>
    <button type="button" disabled={busy} onClick={() => void reload().catch(cause => setError(message(cause)))}>רענן חלופות</button>
    <ul>{drafts.map(item => <li key={item.scenario_id}>
      <button type="button" onClick={() => { permissionEpoch.current += 1; setPermissions({}); setCheckingPermission(null); setSelected(item.scenario_id); setEditingDecisionId(null); setAmount(""); setRename(""); }} disabled={busy}>
        {item.name} — גרסה {item.version} {item.status === "archived" ? "(בארכיון)" : ""}
      </button>
    </li>)}</ul>
    {active && <div>
      <h3>{active.name}</h3>
      <p>גרסה: {active.version} · {active.decisions.length} החלטות בטיוטה · מצב: {active.status}</p>
      {active.status !== "archived" && <>
        <form onSubmit={renameActive}>
          <label>שינוי שם חלופה <input maxLength={255} value={rename} onChange={event => setRename(event.target.value)} placeholder={active.name}/></label>
          <button type="submit" disabled={busy || !rename.trim()}>שמור שם</button>
        </form>
        <button type="button" disabled={busy} onClick={() => void run(() => duplicateScenarioDraft(clientId, active.scenario_id, active.name + " — העתק"))}>שכפל חלופה</button>
        <button type="button" disabled={busy} onClick={() => void run(() => archiveScenarioDraft(clientId, active))}>העבר לארכיון</button>
        <form onSubmit={addDecision}>
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
          <button type="submit" disabled={busy || !source || !exactAmount(amount) || !effectiveDate}>{editingDecisionId ? "שמור עריכת טיוטה" : "שמור החלטה כטיוטה"}</button>
          {editingDecisionId && <button type="button" onClick={() => { setEditingDecisionId(null); setAmount(""); }}>בטל עריכה</button>}
        </form>
      </>}
      <ul>{active.decisions.map((decision, index) => <li key={decision.decision_id}>
        {decision.component_code} — {decision.amount} ₪ — {decision.action === "pension" ? "לקצבה" : "להון"} — לא מאומת
        {" "}— הרשאת בסיס: {(active.status === "needs_revalidation" || decision.validation_state === "needs_revalidation") ? "מקור השתנה — אימות מחדש נדרש"
          : permissions[decision.decision_id]?.status === "ready"
          ? permissions[decision.decision_id].component?.permission_status === "allowed" ? "מותר לפי מטריצת בסיס בלבד"
          : permissions[decision.decision_id].component?.permission_status === "blocked" ? "חסום לפי מטריצת בסיס"
          : "נדרש בירור מקור או כלל"
          : permissions[decision.decision_id]?.status === "error"
          ? permissions[decision.decision_id].error
          : "טרם נבדקה"}
        {" "}<button type="button" disabled={busy || checkingPermission !== null || active.status === "needs_revalidation" || decision.validation_state === "needs_revalidation"}
          onClick={() => {
            const currentClient = clientId;
            const currentDecision = decision.decision_id;
            const currentScenario = active.scenario_id;
            const expectedProduct = products.find(item => item.product_id === decision.source_product_id);
            const expectedComponent = expectedProduct?.conversion_components?.find(item => item.component_id === decision.source_component_id && item.component_code === decision.component_code);
            const epoch = ++permissionEpoch.current;
            setCheckingPermission(currentDecision);
            setPermissions(old => { const next = { ...old }; delete next[currentDecision]; return next; });
            void previewDraftDecision(currentClient, decision)
              .then(component => {
                const context = latestContext.current;
                const currentProduct = context.products.find(item => item.product_id === decision.source_product_id);
                const currentComponent = currentProduct?.conversion_components?.find(item => item.component_id === decision.source_component_id && item.component_code === decision.component_code);
                if (permissionEpoch.current !== epoch || context.clientId !== currentClient || context.selected !== currentScenario) return;
                if (!expectedProduct || !expectedComponent || !currentProduct || !currentComponent
                    || currentProduct.version !== expectedProduct.version || component.preview_product_version !== expectedProduct.version || currentComponent.balance !== expectedComponent.balance
                    || currentComponent.balance !== component.balance) {
                  setPermissions(old => ({ ...old, [currentDecision]: { status: "error", error: "נתוני המקור השתנו — יש לרענן את הטיוטה." } }));
                  return;
                }
                setPermissions(old => ({ ...old, [currentDecision]: { status: "ready", component } }));
              })
              .catch(cause => { if (permissionEpoch.current === epoch) setPermissions(old => ({ ...old, [currentDecision]: { status: "error", error: message(cause) } })); })
              .finally(() => { if (permissionEpoch.current === epoch) setCheckingPermission(null); });
          }}>בדוק הרשאת בסיס (קריאה בלבד)</button>
        {active.status !== "archived" && <>
          <button disabled={busy} type="button" onClick={() => beginEdit(decision)}>ערוך</button>
          <button disabled={busy} type="button" onClick={() => void remove(index)}>מחק החלטת טיוטה</button>
        </>}
      </li>)}</ul>
      <p className="professional-workspace__boundary">בדיקת הרשאת הבסיס אינה אישור זכאות, מס, סכום הקצאה או ביצוע המרה. התוצאה זמנית ונמחקת עם טעינת החלופה מחדש.</p>
      <h4>יתרות טיוטה לפי המקור שנטען</h4>
      <p className="professional-workspace__boundary">
        הנתונים מחושבים לתצוגה בלבד מתוך התיק שנטען כעת; אין כאן אימות מקור, הרשאה להמרה או אישור הקצאת יתר.
      </p>
      <ul>{[...new Set(active.decisions.map(item => item.source_product_id + "|" + item.source_component_id))].map(key => {
        const entry = sources.find(item => item.key === key);
        const base = entry ? asCents(entry.balance) : null;
        const assigned = active.decisions.filter(item => item.source_product_id + "|" + item.source_component_id === key)
          .reduce((sum, item) => sum + (asCents(item.amount) ?? 0n), 0n);
        return <li key={key}>
          {entry?.label ?? "מקור אינו נמצא עוד בתיק"}:
          {" "}הוקצה בטיוטה {displayCents(assigned)} ₪;
          {" "}יתרה זמינה לתצוגה {base === null ? "לא ידועה" : displayCents(base - assigned) + " ₪"}
          {(base === null || assigned > base) && <strong role="alert"> — נדרש אימות מחדש; אין אישור להקצאה</strong>}
        </li>;
      })}</ul>
    </div>}
  </section>;
}
