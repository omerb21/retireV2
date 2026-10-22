import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { getClient, type ClientDetailItem } from "../api/clientsApi";
import { listPensionProducts, savePensionProduct, type PensionProduct } from "../api/pensionProductsApi";
import "./RetirementWorkspaceScreen.css";

const FIXED_CODES: Array<[string, string, "פיצויים" | "תגמולים"]> = [
  ["פיצויים_מעסיק_נוכחי", "פיצויים מעסיק נוכחי", "פיצויים"],
  ["פיצויים_לאחר_התחשבנות", "פיצויים לאחר התחשבנות", "פיצויים"],
  ["פיצויים_שלא_עברו_התחשבנות", "פיצויים שלא עברו התחשבנות", "פיצויים"],
  ["פיצויים_ממעסיקים_קודמים_רצף_זכויות", "פיצויים קודמים — רצף זכויות", "פיצויים"],
  ["פיצויים_ממעסיקים_קודמים_רצף_קצבה", "פיצויים קודמים — רצף קצבה", "פיצויים"],
  ["תגמולי_עובד_עד_2000", "תגמולי עובד עד 2000", "תגמולים"],
  ["תגמולי_עובד_אחרי_2000", "תגמולי עובד אחרי 2000", "תגמולים"],
  ["תגמולי_עובד_אחרי_2008_לא_משלמת", "תגמולי עובד אחרי 2008 — לא משלמת", "תגמולים"],
  ["תגמולי_מעביד_עד_2000", "תגמולי מעביד עד 2000", "תגמולים"],
  ["תגמולי_מעביד_אחרי_2000", "תגמולי מעביד אחרי 2000", "תגמולים"],
  ["תגמולי_מעביד_אחרי_2008_לא_משלמת", "תגמולי מעביד אחרי 2008 — לא משלמת", "תגמולים"],
];
type Step = "client" | "portfolio" | "supplement" | "scenario" | "results";
type Selection = { productId: string; code: string };
type Draft = { productId: string; version: number; components: Record<string, string> };
type ReadState =
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; client: ClientDetailItem; products: PensionProduct[] };

const STEPS: Array<{ key: Step; label: string }> = [
  { key: "client", label: "לקוח ותיק" },
  { key: "portfolio", label: "תיק פנסיוני" },
  { key: "supplement", label: "נתונים משלימים" },
  { key: "scenario", label: "תכנון תרחישים" },
  { key: "results", label: "תוצאות והשוואה" },
];

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "לא ניתן להשלים את הפעולה";
}
function money(value: string | null | undefined): string {
  if (value == null || value === "") return "לא נמסר";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed.toLocaleString("he-IL", { maximumFractionDigits: 2 })
    : "נתון לא תקין";
}
function completeAmount(value: string): boolean {
  return /^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$/.test(value);
}
function uniqueProductSelection(items: Selection[]): string | null {
  if (!items.length) return null;
  return items.every(item => item.productId === items[0].productId)
    ? items[0].productId : null;
}

export function RetirementWorkspaceScreen() {
  const { clientId: rawClientId } = useParams();
  const clientId = rawClientId && /^[1-9][0-9]*$/.test(rawClientId) ? Number(rawClientId) : NaN;
  const validClient = Number.isSafeInteger(clientId);
  const activeClient = useRef(clientId);
  activeClient.current = clientId;
  const [read, setRead] = useState<ReadState>({ state: "loading" });
  const [step, setStep] = useState<Step>("portfolio");
  const [search, setSearch] = useState("");
  const [hideEmptyColumns, setHideEmptyColumns] = useState(false);
  const [discrepancyOnly, setDiscrepancyOnly] = useState(false);
  const [selection, setSelection] = useState<Selection[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRead({ state: "loading" });
    setStep("portfolio");
    setSearch("");
    setHideEmptyColumns(false);
    setDiscrepancyOnly(false);
    setSelection([]);
    setDraft(null);
    setError(null);
    setSaveState("idle");
    if (!validClient) {
      setRead({ state: "error", message: "מזהה לקוח לא תקין" });
      return;
    }
    let active = true;
    void Promise.all([getClient(clientId), listPensionProducts(clientId)]).then(([client, products]) => {
      if (!active) return;
      if (client.client_id !== clientId || products.some(product => product.client_id !== clientId)) {
        setRead({ state: "error", message: "זוהתה אי־התאמה בהקשר הלקוח; הנתונים לא יוצגו" });
        return;
      }
      setRead({ state: "ready", client, products });
    }).catch(reason => {
      if (active) setRead({ state: "error", message: errorText(reason) });
    });
    return () => { active = false; };
  }, [clientId, validClient]);

  const products = read.state === "ready" ? read.products : [];
  const columns = useMemo(() => {
    const present = new Set(products.flatMap(product => Object.keys(product.components)));
    const known = FIXED_CODES.filter(([code]) => present.has(code));
    const extra = [...present].filter(code => !FIXED_CODES.some(([knownCode]) => knownCode === code));
    return [...known, ...extra.map(code => [code, code.replace(/_/g, " "), "תגמולים"] as const)]
      .filter(([code]) => !hideEmptyColumns || products.some(product => {
        const value = product.components[code];
        return value != null && Number(value) !== 0;
      }));
  }, [products, hideEmptyColumns]);
  const shownProducts = useMemo(() => {
    const q = search.trim().toLocaleLowerCase("he");
    return products.filter(product => {
      if (q && ![product.product_name, product.provider_name ?? "", product.account_reference ?? ""]
        .join(" ").toLocaleLowerCase("he").includes(q)) return false;
      if (discrepancyOnly && (!product.reconciliation.product_discrepancy
        || Number(product.reconciliation.product_discrepancy) === 0)) return false;
      return true;
    });
  }, [products, search, discrepancyOnly]);

  function switchStep(next: Step) {
    setSelection([]);
    setDraft(null);
    setError(null);
    setStep(next);
  }
  function toggleCell(productId: string, code: string) {
    if (draft || saveState === "saving") return;
    setSelection(prev => prev.some(item => item.productId === productId && item.code === code)
      ? prev.filter(item => !(item.productId === productId && item.code === code))
      : [...prev, { productId, code }]);
    setError(null);
  }
  function startCorrection() {
    const productId = uniqueProductSelection(selection);
    const product = products.find(item => item.product_id === productId);
    if (!product) {
      setError("לתיקון נתונים יש לבחור רכיב אחד או כמה רכיבים מאותו מוצר.");
      return;
    }
    setDraft({ productId: product.product_id, version: product.version, components: { ...product.components } });
    setError(null);
  }
  async function saveCorrection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || read.state !== "ready" || saveState === "saving") return;
    const product = read.products.find(item => item.product_id === draft.productId);
    if (!product || product.version !== draft.version) {
      setError("גרסת המוצר השתנתה. יש לסגור את העריכה ולרענן את הנתונים.");
      return;
    }
    if (Object.values(draft.components).some(value => !completeAmount(value))) {
      setError("סכומים חייבים להיות לא שליליים, עם עד שתי ספרות אחרי הנקודה.");
      return;
    }
    if (Object.keys(product.components).every(code => product.components[code] === draft.components[code])) {
      setDraft(null);
      setSelection([]);
      return;
    }
    setSaveState("saving");
    setError(null);
    const capturedClient = clientId;
    try {
      const saved = await savePensionProduct(clientId, product.product_id, {
        product_name: product.product_name,
        product_type: product.product_type,
        provider_name: product.provider_name,
        provider_identifier: product.provider_identifier,
        account_reference: product.account_reference,
        start_date: product.start_date,
        statement_date: product.statement_date,
        historical_employers: product.historical_employers,
        reported_product_total: product.reported_product_total,
        reported_rewards_total: product.reported_rewards_total,
        reported_severance_total: product.reported_severance_total,
        expected_version: draft.version,
        components: { ...draft.components },
      });
      if (activeClient.current !== capturedClient) return;
      if (saved.client_id !== capturedClient || saved.product_id !== product.product_id) {
        setError("השרת החזיר נתונים שאינם תואמים את המוצר המבוקש.");
        return;
      }
      setRead(current => current.state === "ready" && current.client.client_id === capturedClient
        ? { ...current, products: current.products.map(item => item.product_id === saved.product_id ? saved : item) }
        : current);
      setDraft(null);
      setSelection([]);
    } catch (reason) {
      if (activeClient.current === capturedClient) setError(errorText(reason));
    } finally {
      if (activeClient.current === capturedClient) setSaveState("idle");
    }
  }

  if (!validClient) return <main dir="rtl"><h1>מזהה לקוח לא תקין</h1><Link to="/clients">בחזרה ללקוחות</Link></main>;
  if (read.state === "loading") return <main dir="rtl"><p>טוען סביבת עבודה...</p></main>;
  if (read.state === "error") return <main dir="rtl"><h1>לא ניתן להציג את התיק</h1><p role="alert">{read.message}</p><Link to="/clients">בחזרה ללקוחות</Link></main>;

  const client = read.client;
  return <main dir="rtl" className="professional-workspace">
    <header className="professional-workspace__header">
      <div>
        <strong>בן־צבי · סביבת תכנון פרישה</strong>
        <p>תיק פעיל: {client.full_name} · מזהה תיק {client.client_id}</p>
      </div>
      <Link to="/clients">החלפת לקוח</Link>
    </header>
    <nav aria-label="שלבי תכנון פרישה" className="professional-workspace__steps">
      {STEPS.map(({ key, label }, index) => <button type="button" key={key}
        className={step === key ? "is-active" : ""}
        aria-current={step === key ? "step" : undefined}
        onClick={() => switchStep(key)}>{index + 1}. {label}</button>)}
    </nav>
    <div className="professional-workspace__body">
      {step === "client" && <section aria-label="פרטי תיק">
        <h1>תיק לקוח</h1>
        <p className="professional-workspace__sub">פרטים הדרושים להתמצאות בעבודה. מידע בקרה מפורט נשאר במסכים הייעודיים.</p>
        <dl className="professional-workspace__identity">
          <div><dt>שם</dt><dd>{client.full_name}</dd></div>
          <div><dt>תאריך לידה</dt><dd>{client.birth_date ?? "לא נמסר"}</dd></div>
          <div><dt>מספר מוצרים בתיק</dt><dd>{products.length}</dd></div>
        </dl>
        <div className="professional-workspace__actions">
          <button type="button" onClick={() => switchStep("portfolio")}>פתח את התיק הפנסיוני</button>
          <Link to={"/clients/" + clientId}>פרטי תיק נוספים</Link>
        </div>
      </section>}
      {step === "portfolio" && <section aria-label="טבלת התיק הפנסיוני">
        <h1>התיק הפנסיוני</h1>
        <p className="professional-workspace__sub">טבלת עבודה אחת: בחירת רכיבים, בדיקת התאמות ותיקון נתוני אמת.</p>
        <p className="professional-workspace__boundary">
          <strong>מצב נתוני אמת.</strong> תיקון יתרה או סיווג משנה את הנתון העובד לאחר שמירה מפורשת.
          זו אינה המרה לקצבה או לנכס הון. בחירות תרחיש אינן מבוצעות כאן.
        </p>
        <div className="professional-workspace__toolbar">
          <label>חיפוש <input type="search" value={search} onChange={event => {
            setSearch(event.target.value); setSelection([]); setDraft(null);
          }} placeholder="תוכנית, גוף מנהל או חשבון" disabled={saveState === "saving"} /></label>
          <label><input type="checkbox" checked={hideEmptyColumns} disabled={saveState === "saving"} onChange={event => { setHideEmptyColumns(event.target.checked); setSelection([]); setDraft(null); }}/> הסתר טורים ללא יתרה</label>
          <label><input type="checkbox" checked={discrepancyOnly} disabled={saveState === "saving"} onChange={event => { setDiscrepancyOnly(event.target.checked); setSelection([]); setDraft(null); }}/> הצג רק פערי התאמה</label>
          <span>{shownProducts.length} מתוך {products.length} מוצרים</span>
        </div>
        <div className="professional-workspace__ledger" role="region" aria-label="טבלת רכיבים נגללת" tabIndex={0}>
          <table>
            <thead>
              <tr><th scope="col">תוכנית / פוליסה</th><th scope="col">גוף מנהל</th><th scope="col">יתרה מדווחת</th>
                {columns.map(([code, label]) => <th key={code} scope="col" title={label}>{label}</th>)}
                <th scope="col">פער</th>
              </tr>
            </thead>
            <tbody>
              {shownProducts.map(product => <tr key={product.product_id}>
                <th scope="row"><strong>{product.product_name}</strong><small>חשבון {product.account_reference ?? "לא נמסר"}</small></th>
                <td>{product.provider_name ?? "לא נמסר"}</td>
                <td><bdi>{money(product.reported_product_total)}</bdi></td>
                {columns.map(([code, label]) => {
                  const value = product.components[code];
                  const selected = selection.some(item => item.productId === product.product_id && item.code === code);
                  return <td key={code}>{value == null ? "—" : <button type="button"
                    disabled={draft !== null || saveState === "saving"}
                    aria-pressed={selected}
                    className={"professional-workspace__cell" + (selected ? " is-selected" : "")}
                    title={label} aria-label={label + " — " + product.product_name}
                    onClick={() => toggleCell(product.product_id, code)}>
                    <bdi>{money(value)}</bdi>
                  </button>}</td>;
                })}
                <td><bdi>{money(product.reconciliation.product_discrepancy)}</bdi></td>
              </tr>)}
              {shownProducts.length === 0 && <tr><td colSpan={columns.length + 4}>אין מוצרים התואמים לסינון.</td></tr>}
            </tbody>
          </table>
        </div>
        <section className="professional-workspace__selection-panel" aria-label="פעולות על רכיבים שנבחרו">
          <strong>{selection.length ? selection.length + " רכיבים נבחרו" : "בחר יתרה או מספר יתרות בטבלה"}</strong>
          <p>תיקון כמה רכיבים באותו מוצר נשמר בפעולה אחת עם בקרת גרסה. שינוי הסיווג אינו המרה.</p>
          <div className="professional-workspace__actions">
            <button type="button" disabled={!selection.length || draft !== null || saveState === "saving"} onClick={startCorrection}>תיקון יתרות נבחרות</button>
            <button type="button" disabled={!selection.length || draft !== null || saveState === "saving"} onClick={() => setSelection([])}>בטל בחירה</button>
            <Link to={"/clients/" + clientId + "/pension-products"}>ייבוא מסלקה ופרטי מוצר מורחבים</Link>
          </div>
        </section>
        {draft && <form className="professional-workspace__editor" onSubmit={event => void saveCorrection(event)}>
          <h2>תיקון נתוני אמת — {products.find(p => p.product_id === draft.productId)?.product_name}</h2>
          <p>רק רכיבים שנבחרו פתוחים לעריכה. רכיבים אחרים יישמרו ללא שינוי.</p>
          <div className="professional-workspace__edit-grid">
            {selection.filter(item => item.productId === draft.productId).map(item => {
              const label = FIXED_CODES.find(([code]) => code === item.code)?.[1] ?? item.code;
              return <label key={item.code}>{label}
                <input dir="ltr" inputMode="decimal" required disabled={saveState === "saving"}
                  value={draft.components[item.code] ?? ""}
                  onChange={event => setDraft({ ...draft, components: { ...draft.components, [item.code]: event.target.value } })} />
              </label>;
            })}
          </div>
          <div className="professional-workspace__actions">
            <button type="submit" disabled={saveState === "saving"}>{saveState === "saving" ? "שומר..." : "שמור תיקון נתונים"}</button>
            <button type="button" disabled={saveState === "saving"} onClick={() => { setDraft(null); setError(null); }}>ביטול ללא שמירה</button>
          </div>
        </form>}
        {error && <p role="alert" className="professional-workspace__error">{error}</p>}
      </section>}
      {step === "supplement" && <section>
        <h1>נתונים משלימים</h1>
        <p className="professional-workspace__sub">המידע המקצועי ממשיך להישמר במנגנונים הקיימים. בשלב זה פותחים את המסכים המאושרים במקום לשכפל אותם.</p>
        <div className="professional-workspace__links">
          <Link to={"/clients/" + clientId + "/grants"}>מענקים היסטוריים</Link>
          <Link to={"/clients/" + clientId + "/employment-history"}>תעסוקה ומעסיקים</Link>
          <Link to={"/clients/" + clientId + "/actual-capitalizations"}>היוונים שבוצעו בפועל</Link>
          <Link to={"/clients/" + clientId + "/planning-input"}>נתוני תכנון פרישה</Link>
        </div>
      </section>}
      {step === "scenario" && <section>
        <h1>תכנון תרחישים</h1>
        <p className="professional-workspace__boundary">
          שלב החיבור למנוע התרחישים עדיין לא בוצע. ההמרה הקנונית הקיימת ב־V2 מעדכנת יתרות אמת,
          ולכן היא לא תופעל מכאן בתור החלטת תרחיש.
        </p>
        <p>בשלב הבא יתווספו חלופות עצמאיות עם הקצאות לקצבה ולהון, שינוי החלטות וביטולן — בלי שינוי בתיק המקור.</p>
      </section>}
      {step === "results" && <section>
        <h1>תוצאות והשוואה</h1>
        <p className="professional-workspace__boundary">
          אין עדיין השוואת חלופות מחושבת בממשק זה. לא יוצגו מספרי קצבה, פטורים, מס או NPV שלא חושבו ואושרו במנוע V2.
        </p>
        <Link to={"/clients/" + clientId + "/retirement-income-readiness"}>מעבר למסך מוכנות ההכנסה הקיים</Link>
      </section>}
    </div>
  </main>;
}
