import { useEffect, useMemo, useRef, useState } from "react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import {
  readScenarioMonthlyComparison, type ScenarioMonthlyComparison,
} from "../api/scenarioStage6Api";

interface Props { clientId: number; scenarios: ScenarioDraft[] }
const HASH = /^[0-9a-f]{64}$/;
const MONTH = /^\d{4}-(?:0[1-9]|1[0-2])$/;
const AMOUNT = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/;

const blockerText: Record<string, string> = {
  STAGE6_COMPARISON_SCENARIO_A_INCOMPLETE: "חלופה א׳ אינה מלאה בחודש זה.",
  STAGE6_COMPARISON_SCENARIO_B_INCOMPLETE: "חלופה ב׳ אינה מלאה בחודש זה.",
  STAGE6_COMPARISON_NET_TARGET_NOT_COMPARABLE: "יעד ההכנסה הוא נטו ולכן אינו בר־השוואה לתזרים ברוטו.",
  STAGE6_COMPARISON_TARGET_PRICE_BASIS_NOT_COMPARABLE: "בסיס המחירים של היעד אינו תואם לתזרים ללא מנגנון הצמדה מוסמך.",
  STAGE6_COMPARISON_TARGET_OUTSIDE_COMPARABLE_MONTH: "פער מול היעד מוצג רק בחודש היעד הקנוני.",
  STAGE6_COMPARISON_TARGET_MONTH_INCOMPLETE: "חודש היעד חסום באחת החלופות.",
  STAGE6_COMPARISON_TARGET_NOT_READY: "יעד ההכנסה טרם אושר או התיישן.",
};

function months(start: string, end: string): string[] {
  if (!MONTH.test(start) || !MONTH.test(end)) return [];
  let year = Number(start.slice(0, 4));
  let month = Number(start.slice(5));
  const final = Number(end.replace("-", ""));
  const result: string[] = [];
  while (year * 100 + month <= final && result.length <= 600) {
    result.push(`${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`);
    if (++month === 13) { month = 1; year += 1; }
  }
  return result.length <= 600 ? result : [];
}

function validIdentity(value: ScenarioMonthlyComparison["scenario_a"], id: string, version: number): boolean {
  return value?.scenario_id === id && value.scenario_version === version
    && HASH.test(value.manifest_fingerprint) && HASH.test(value.cashflow_fingerprint)
    && Array.isArray(value.sources) && value.sources.every(source => source && source.source_id
      && ["CALCULATED_PENSION", "KNOWN_RECURRING_INCOME"].includes(source.source_kind)
      && HASH.test(source.authority_fingerprint) && ["READY", "BLOCKED"].includes(source.source_state));
}

function validEnvelope(value: ScenarioMonthlyComparison, clientId: number,
  a: ScenarioDraft, b: ScenarioDraft, start: string, end: string): boolean {
  const expectedMonths = months(start, end);
  if (!value || value.schema_version !== "STAGE6_SCENARIO_MONTHLY_COMPARISON_V1"
      || value.client_id !== clientId || value.start_month !== start || value.end_month !== end
      || value.execution_allowed !== false || !HASH.test(value.comparison_fingerprint)
      || !validIdentity(value.scenario_a, a.scenario_id, a.version)
      || !validIdentity(value.scenario_b, b.scenario_id, b.version)
      || !Array.isArray(value.monthly_rows) || expectedMonths.length === 0
      || value.monthly_rows.map(row => row.month).join("|") !== expectedMonths.join("|")) return false;
  const validRows = value.monthly_rows.every(row => {
    if (!row || !Array.isArray(row.blocker_codes) || !row.blocker_codes.every(code => typeof code === "string")
        || row.blocker_codes.join("|") !== [...new Set(row.blocker_codes)].sort().join("|")
        || !row.change_events || Object.values(row.change_events).some(ids => !Array.isArray(ids)
          || !ids.every(id => typeof id === "string") || ids.join("|") !== [...new Set(ids)].sort().join("|"))) return false;
    const amounts = [row.scenario_a_gross_income_ils, row.scenario_b_gross_income_ils,
      row.scenario_b_minus_a_gross_ils];
    if (row.comparison_state === "COMPLETE") {
      if (amounts.some(amount => typeof amount !== "string" || !AMOUNT.test(amount))) return false;
    } else if (row.comparison_state !== "BLOCKED" || amounts.some(amount => amount !== null)) return false;
    const goalAmounts = [row.target_gross_income_ils, row.scenario_a_minus_target_gross_ils,
      row.scenario_b_minus_target_gross_ils];
    return row.target_comparison_state === "COMPLETE"
      ? goalAmounts.every(amount => typeof amount === "string" && AMOUNT.test(amount))
      : row.target_comparison_state === "BLOCKED" && goalAmounts.every(amount => amount === null);
  });
  if (!validRows || !HASH.test(value.target.target_result_fingerprint)
      || (value.target.target_semantic_fingerprint !== null
        && !HASH.test(value.target.target_semantic_fingerprint))) return false;
  const completeRows = value.monthly_rows.filter(row => row.comparison_state === "COMPLETE").length;
  const expectedState = completeRows === value.monthly_rows.length ? "COMPLETE"
    : completeRows > 0 ? "PARTIAL" : "BLOCKED";
  const expectedTargetState = value.monthly_rows.some(row => row.target_comparison_state === "COMPLETE")
    ? "COMPLETE" : "BLOCKED";
  const shared = value.scenario_a.sources.map(source => source.source_id)
    .filter(id => value.scenario_b.sources.some(source => source.source_id === id)).sort();
  return value.comparison_state === expectedState
    && value.target_comparison_state === expectedTargetState
    && Array.isArray(value.shared_source_ids)
    && value.shared_source_ids.join("|") === shared.join("|");
}

function signed(value: string | null): string {
  if (value === null) return "לא זמין";
  if (/^-?0(?:\.0+)?$/.test(value)) return `${value} ₪ (איזון)`;
  return value.startsWith("-") ? `${value} ₪ (חוסר)` : `${value} ₪ (עודף)`;
}

function changes(value: ScenarioMonthlyComparison["monthly_rows"][number]["change_events"]): string {
  const entries: Array<[string, string[]]> = [
    ["התחלה א׳", value.scenario_a_started_source_ids],
    ["סיום א׳", value.scenario_a_ended_source_ids],
    ["התחלה ב׳", value.scenario_b_started_source_ids],
    ["סיום ב׳", value.scenario_b_ended_source_ids],
  ];
  const parts = entries.filter(([, ids]) => ids.length > 0)
    .map(([label, ids]) => `${label}: ${ids.join(", ")}`);
  return parts.length ? parts.join("; ") : "ללא שינוי במקורות";
}

export function ScenarioMonthlyComparisonPanel({ clientId, scenarios }: Props) {
  const available = useMemo(() => scenarios.filter(item => item.status !== "archived"), [scenarios]);
  const [scenarioA, setScenarioA] = useState("");
  const [scenarioB, setScenarioB] = useState("");
  const [startMonth, setStartMonth] = useState("");
  const [endMonth, setEndMonth] = useState("");
  const [result, setResult] = useState<ScenarioMonthlyComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const scenarioRevision = available.map(item => `${item.scenario_id}:${item.version}`).join("|");

  useEffect(() => {
    generation.current += 1;
    controller.current?.abort();
    setResult(null); setError(null); setBusy(false);
    setScenarioA(available[0]?.scenario_id ?? "");
    setScenarioB(available[1]?.scenario_id ?? "");
    setStartMonth(""); setEndMonth("");
    return () => { generation.current += 1; controller.current?.abort(); };
  }, [clientId, scenarioRevision]); // eslint-disable-line react-hooks/exhaustive-deps

  function invalidate(change: () => void) {
    generation.current += 1;
    controller.current?.abort();
    setResult(null); setError(null); setBusy(false); change();
  }

  async function compare() {
    const a = available.find(item => item.scenario_id === scenarioA);
    const b = available.find(item => item.scenario_id === scenarioB);
    if (!a || !b || a.scenario_id === b.scenario_id || !startMonth || !endMonth || busy) return;
    const epoch = ++generation.current;
    const abort = new AbortController();
    controller.current?.abort(); controller.current = abort;
    setBusy(true); setError(null); setResult(null);
    try {
      const value = await readScenarioMonthlyComparison(clientId, {
        scenario_a_id: a.scenario_id, scenario_a_version: a.version,
        scenario_b_id: b.scenario_id, scenario_b_version: b.version,
        start_month: startMonth, end_month: endMonth,
      }, abort.signal);
      if (generation.current !== epoch) return;
      if (!validEnvelope(value, clientId, a, b, startMonth, endMonth)) {
        throw Error("STAGE6_COMPARISON_RESPONSE_INVALID");
      }
      setResult(value);
    } catch (cause) {
      if (generation.current === epoch && !abort.signal.aborted) {
        setError(cause instanceof Error ? cause.message : "STAGE6_COMPARISON_UNAVAILABLE");
      }
    } finally {
      if (generation.current === epoch) setBusy(false);
    }
  }

  if (available.length < 2) return <section aria-label="השוואת תזרים בין חלופות">
    <h3>השוואת תזרים חודשי</h3><p>נדרשות לפחות שתי חלופות פעילות שמורות.</p>
  </section>;

  const aName = available.find(item => item.scenario_id === scenarioA)?.name ?? "חלופה א׳";
  const bName = available.find(item => item.scenario_id === scenarioB)?.name ?? "חלופה ב׳";
  return <section aria-label="השוואת תזרים בין חלופות">
    <h3>השוואת תזרים חודשי בין חלופות</h3>
    <p className="professional-workspace__boundary">ההשוואה היא ברוטו בלבד ומחושבת בשרת מתוך Snapshot קנוני אחד.
      היא אינה כוללת מס, נטו, NPV, תשואה, הצמדה, המלצה או בדיקת מימון.</p>
    <div className="professional-workspace__grid">
      <label>חלופה א׳ <select value={scenarioA} disabled={busy}
        onChange={event => invalidate(() => setScenarioA(event.target.value))}>
        {available.map(item => <option key={item.scenario_id} value={item.scenario_id}>{item.name} — גרסה {item.version}</option>)}
      </select></label>
      <label>חלופה ב׳ <select value={scenarioB} disabled={busy}
        onChange={event => invalidate(() => setScenarioB(event.target.value))}>
        {available.map(item => <option key={item.scenario_id} value={item.scenario_id}>{item.name} — גרסה {item.version}</option>)}
      </select></label>
      <label>חודש התחלה <input type="month" value={startMonth} disabled={busy}
        onChange={event => invalidate(() => setStartMonth(event.target.value))}/></label>
      <label>חודש סיום <input type="month" value={endMonth} disabled={busy}
        onChange={event => invalidate(() => setEndMonth(event.target.value))}/></label>
    </div>
    {scenarioA === scenarioB && <p role="alert">יש לבחור שתי חלופות שונות של אותו לקוח.</p>}
    <button type="button" disabled={busy || scenarioA === scenarioB || !startMonth || !endMonth}
      onClick={() => void compare()}>{busy ? "מחשב השוואה..." : "השווה תזרים חודשי"}</button>
    {error && <p role="alert">ההשוואה נחסמה: {blockerText[error] ?? error}</p>}
    {result && <>
      <p role="status">{result.comparison_state === "COMPLETE"
        ? "השוואת החלופות הושלמה לכל החודשים."
        : result.comparison_state === "PARTIAL"
          ? "ההשוואה חלקית; חודשים חסומים אינם מציגים סכומים השוואתיים."
          : "ההשוואה חסומה לכל הטווח."}</p>
      <p>{result.target.target_state === "GROSS_NOMINAL_TARGET_MONTH_ONLY"
        ? "פער מול יעד ברוטו מוצג רק בחודש יעד הפרישה הקנוני."
        : result.target.target_state === "NET_NOT_COMPARABLE"
          ? "יעד ההכנסה הוא נטו; ללא מנוע מס לא ניתן להשוות אותו לתזרים ברוטו."
          : result.target.target_state === "PRICE_BASIS_NOT_COMPARABLE"
            ? "בסיס המחירים של היעד אינו בר־השוואה ללא מנגנון הצמדה מוסמך."
            : "יעד ההכנסה אינו מוכן להשוואה."}</p>
      <div className="table-wrap"><table>
        <caption>{aName} מול {bName}</caption>
        <thead><tr><th>חודש</th><th>{aName} — ברוטו</th><th>{bName} — ברוטו</th>
          <th>הפרש ב׳ פחות א׳</th><th>יעד ברוטו</th><th>{aName} מול יעד</th><th>{bName} מול יעד</th><th>שינוי במקורות</th><th>סטטוס</th></tr></thead>
        <tbody>{result.monthly_rows.map(row => <tr key={row.month}>
          <td>{row.month}</td>
          <td>{row.scenario_a_gross_income_ils === null ? "לא זמין" : `${row.scenario_a_gross_income_ils} ₪`}</td>
          <td>{row.scenario_b_gross_income_ils === null ? "לא זמין" : `${row.scenario_b_gross_income_ils} ₪`}</td>
          <td>{row.scenario_b_minus_a_gross_ils === null ? "לא זמין" : `${row.scenario_b_minus_a_gross_ils} ₪`}</td>
          <td>{row.target_gross_income_ils === null ? "לא בר־השוואה" : `${row.target_gross_income_ils} ₪`}</td>
          <td>{signed(row.scenario_a_minus_target_gross_ils)}</td>
          <td>{signed(row.scenario_b_minus_target_gross_ils)}</td>
          <td>{changes(row.change_events)}</td>
          <td>{row.comparison_state === "COMPLETE" ? "תקין"
            : row.blocker_codes.map(code => blockerText[code] ?? code).join(" ")}</td>
        </tr>)}</tbody>
      </table></div>
      <details><summary>זהויות מקור ואימות לשחזור</summary>
        <p>{aName}: גרסה {result.scenario_a.scenario_version}; Manifest <bdi>{result.scenario_a.manifest_fingerprint}</bdi>; Cashflow <bdi>{result.scenario_a.cashflow_fingerprint}</bdi>.</p>
        <p>{bName}: גרסה {result.scenario_b.scenario_version}; Manifest <bdi>{result.scenario_b.manifest_fingerprint}</bdi>; Cashflow <bdi>{result.scenario_b.cashflow_fingerprint}</bdi>.</p>
        <p>מקורות משותפים: {result.shared_source_ids.length ? result.shared_source_ids.join(", ") : "אין"}.</p>
        <p>חותמת השוואה: <bdi>{result.comparison_fingerprint}</bdi>.</p>
      </details>
    </>}
  </section>;
}
