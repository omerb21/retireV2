import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { PensionProduct } from "../api/pensionProductsApi";
import type { DraftDecisionInput, ScenarioDraft } from "../api/scenarioDraftsApi";
import { PORTFOLIO_COMPONENT_COLUMNS } from "./portfolioComponentColumns";
import {
  buildPlanDecisions, buildPlanRows, planCents, planMoney, selectPlanScope,
  type PlanCell,
} from "./scenarioConversionPlan";

interface Props {
  products: PensionProduct[];
  scenario: ScenarioDraft;
  disabled: boolean;
  busy: boolean;
  initialSource?: { productId: string; componentCode: string } | null;
  onApply: (decisions: DraftDecisionInput[]) => Promise<boolean>;
}
const display = (value: string | null | undefined) =>
  value == null ? "לא דווח" : (planCents(value) === null ? "נתון לא תקין" : planMoney(planCents(value)!));

/** Portfolio-shaped planning only; conversion always remains in the scenario draft. */
export function ScenarioConversionMatrix({
  products, scenario, disabled, busy, initialSource, onApply,
}: Props) {
  const rows = useMemo(() => buildPlanRows(products, scenario.decisions), [products, scenario.decisions]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [scope, setScope] = useState("רכיב בודד");
  const [target, setTarget] = useState<DraftDecisionInput["action"]>("pension");
  const [when, setWhen] = useState("");
  const [partial, setPartial] = useState("");
  const [rowDates, setRowDates] = useState<Record<string, string>>({});
  const [rowAmounts, setRowAmounts] = useState<Record<string, string>>({});
  const [issue, setIssue] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const all = rows.flatMap(row => row.cells);
  const selectedCells = chosen.map(key => all.find(cell => cell.key === key)).filter(
    (cell): cell is PlanCell => cell !== undefined,
  );
  const total = selectedCells.reduce((sum, cell) => sum + (cell.available ?? 0n), 0n);
  const unable = disabled || busy || saving;
  const datesReady = chosen.length === 1 ? !!when : chosen.length > 1
    && chosen.every(key => !!(rowDates[key] ?? when));

  useEffect(() => {
    if (!initialSource) return;
    const cell = all.find(cell => cell.productId === initialSource.productId
      && cell.code === initialSource.componentCode && cell.available !== null && cell.available > 0n);
    if (!cell) return;
    setChosen([cell.key]);
    setScope("רכיב בודד");
    setPartial(planMoney(cell.available!));
    setRowDates({});
    setRowAmounts({});
  }, [initialSource?.productId, initialSource?.componentCode]);

  function chooseOne(cell: PlanCell) {
    if (unable) return;
    if (cell.blocked || cell.available === null || cell.available <= 0n || !cell.componentId) {
      setIssue(cell.blocked ?? "לא נותרה יתרה פנויה ברכיב הזה.");
      return;
    }
    setChosen([cell.key]);
    setScope("רכיב בודד");
    setPartial(planMoney(cell.available));
    setRowDates({});
    setRowAmounts({});
    setIssue(null);
  }

  function chooseScope(nextScope: { productId?: string; code?: string }, label: string) {
    if (unable) return;
    try {
      const keys = selectPlanScope(rows, nextScope);
      if (scenario.decisions.length + keys.length > 500) {
        throw Error("מספר ההחלטות בחלופה יחרוג מהמגבלה. יש לפצל את התכנון.");
      }
      setChosen(keys);
      setScope(label);
      setPartial("");
      setRowDates({});
      setRowAmounts({});
      setIssue(null);
    } catch (cause) {
      setIssue(cause instanceof Error ? cause.message : "לא ניתן לבחור את ההיקף.");
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (unable) return;
    try {
      // Each selected source may have its own amount and execution date.
      // A bulk plan remains a single atomic, versioned draft replacement.
      const decisions = chosen.length > 1
        ? chosen.flatMap(key => buildPlanDecisions(
            rows, [key], target, rowDates[key] ?? when, rowAmounts[key] ?? "",
          ))
        : buildPlanDecisions(rows, chosen, target, when, partial);
      if (scenario.decisions.length + decisions.length > 500) {
        throw Error("יותר מדי החלטות בחלופה זו.");
      }
      setIssue(null);
      setSaving(true);
      const saved = await onApply(decisions);
      if (saved) {
        setChosen([]);
        setPartial("");
        setRowDates({});
        setRowAmounts({});
        setScope("רכיב בודד");
      } else {
        setIssue("ההמרה לא נשמרה. יש לבדוק את הודעת השגיאה של החלופה.");
      }
    } catch (cause) {
      setIssue(cause instanceof Error ? cause.message : "לא ניתן לשמור את התכנון.");
    } finally {
      setSaving(false);
    }
  }

  return <section className="scenario-conversion" aria-label="תכנון המרות בטבלת היתרות">
    <div className="scenario-conversion__heading">
      <div>
        <h3>המרות מתוך טבלת היתרות</h3>
        <p>לחץ על יתרה להמרה פרטנית, על שם התוכנית להמרת תוכנית שלמה, או על כותרת טור להמרת כל הטור.</p>
      </div>
      <span>יתרות המקור נשארות ללא שינוי</span>
    </div>
    <div className="professional-workspace__ledger scenario-conversion__ledger"
      role="region" tabIndex={0} aria-label="טבלת יתרות לתכנון המרות">
      <table>
        <thead><tr>
          <th scope="col">תוכנית / פוליסה</th>
          <th scope="col">גוף מנהל</th>
          <th scope="col">יתרה מדווחת</th>
          {PORTFOLIO_COMPONENT_COLUMNS.map(([code, label]) => <th key={code} scope="col">
            <span>{label}</span>
            <button type="button" disabled={unable} title={`הקצה יתרות בכל התוכניות בטור ${label}`}
              aria-label={`המר טור ${label}`}
              onClick={() => chooseScope({ code }, `טור: ${label}`)}>
              המר טור
            </button>
          </th>)}
          <th scope="col">פער</th>
        </tr></thead>
        <tbody>
          {rows.map(({ product, cells }) => <tr key={product.product_id}>
            <th scope="row">
              <strong>{product.product_name}</strong>
              <small>חשבון {product.account_reference ?? "לא נמסר"}</small>
              <button type="button" disabled={unable}
                aria-label={`המר תוכנית ${product.product_name}`}
                onClick={() => chooseScope({ productId: product.product_id }, `תוכנית: ${product.product_name}`)}>
                המר תוכנית
              </button>
            </th>
            <td>{product.provider_name ?? "לא נמסר"}</td>
            <td><bdi>{display(product.reported_product_total)}</bdi></td>
            {cells.map(cell => <td key={cell.code}>
              {cell.balance === null ? "לא דווח" : cell.balance === 0n ? "0.00"
                : <button type="button"
                  disabled={unable || cell.available === null || cell.available <= 0n}
                  aria-pressed={chosen.includes(cell.key)}
                  aria-label={`בחר יתרת ${cell.label} בתוכנית ${product.product_name}`}
                  title={cell.blocked ?? `פנוי להקצאה: ${planMoney(cell.available ?? 0n)} ₪`}
                  className={"professional-workspace__cell" + (chosen.includes(cell.key) ? " is-selected" : "")}
                  onClick={() => chooseOne(cell)}>
                  <bdi>{planMoney(cell.balance)}</bdi>
                  {cell.allocated > 0n && <small>הוקצה: {planMoney(cell.allocated)}</small>}
                  {cell.blocked && <small>{cell.blocked}</small>}
                </button>}
            </td>)}
            <td><bdi>{display(product.reconciliation?.product_discrepancy)}</bdi></td>
          </tr>)}
          {rows.length === 0 && <tr><td colSpan={PORTFOLIO_COMPONENT_COLUMNS.length + 4}>
            אין תוכניות פנסיוניות בתיק זה.
          </td></tr>}
        </tbody>
      </table>
    </div>
    <form className="scenario-conversion__plan" onSubmit={event => void save(event)}>
      <div>
        <strong>{chosen.length ? `${scope} - ${chosen.length} רכיבים` : "בחר מה להמיר בטבלה"}</strong>
        <p>{chosen.length ? `יתרה פנויה נבחרת: ${planMoney(total)} ₪` : "בחירה אינה משנה את התיק. השמירה מוסיפה החלטות תכנון בלבד."}</p>
      </div>
      <label>יעד ההמרה
        <select value={target} disabled={unable} onChange={event => setTarget(event.target.value as DraftDecisionInput["action"])}>
          <option value="pension">לקצבה</option>
          <option value="capital_asset">להון</option>
        </select>
      </label>
      <label>{chosen.length > 1 ? "ברירת מחדל לתאריך ביצוע" : "תאריך ביצוע מתוכנן"}
        <input type="date" value={when} disabled={unable}
          onChange={event => setWhen(event.target.value)} />
      </label>
      {chosen.length === 1 && <label>סכום להמרה (₪)
        <input inputMode="decimal" value={partial} disabled={unable}
          onChange={event => setPartial(event.target.value)}
          aria-label="סכום להמרה" />
      </label>}
      {chosen.length > 1 && <div className="scenario-conversion__bulk-detail"
        aria-label="תזמון המרות לפי רכיב">
        <h4>סכומים ומועדים לכל רכיב</h4>
        <p>כל רכיב ניתן לתזמון בנפרד. התאריך הכללי חל רק על רכיבים ללא תאריך משלהם.</p>
        <table>
          <thead><tr><th>תוכנית</th><th>רכיב</th><th>יתרה פנויה (₪)</th>
            <th>סכום להמרה (₪)</th><th>תאריך ביצוע מתוכנן</th></tr></thead>
          <tbody>{selectedCells.map(cell => <tr key={cell.key}>
            <th scope="row">{cell.productName}</th>
            <td>{cell.label}</td><td>{planMoney(cell.available ?? 0n)}</td>
            <td><input inputMode="decimal" disabled={unable}
              aria-label={`סכום ${cell.label} ${cell.productName}`}
              value={rowAmounts[cell.key] ?? planMoney(cell.available ?? 0n)}
              onChange={event => setRowAmounts(old => ({ ...old, [cell.key]: event.target.value }))}/></td>
            <td><input type="date" disabled={unable}
              aria-label={`תאריך ${cell.label} ${cell.productName}`}
              value={rowDates[cell.key] ?? when}
              onChange={event => setRowDates(old => ({ ...old, [cell.key]: event.target.value }))}/></td>
          </tr>)}</tbody>
        </table>
      </div>}
      <button type="submit" disabled={unable || !chosen.length || !datesReady}>
        {saving ? "שומר..." : chosen.length > 1 ? `שמור ${chosen.length} המרות בחלופה` : "שמור המרה בחלופה"}
      </button>
      {chosen.length > 0 && <button type="button" disabled={unable} onClick={() => {
        setChosen([]); setPartial(""); setRowDates({}); setRowAmounts({}); setIssue(null);
      }}>בטל בחירה</button>}
      {issue && <p className="scenario-conversion__error" role="alert">{issue}</p>}
    </form>
  </section>;
}
