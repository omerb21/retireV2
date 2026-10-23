import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { getClient, getEmploymentRecords, getGrants, getActualCapitalizations, getCapitalAssets, getRecurringIncomes, getRecurringExpenses, updateEmploymentRecord, createEmploymentRecord, createHistoricalEmploymentSettlement, type ExemptGrantStatus, updateGrant, createGrantForEmployment, linkGrantToEmployment, type GrantItem, type EmploymentRecordItem, type ClientDetailItem } from "../api/clientsApi";
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
  | { state: "error"; clientId: number; message: string }
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
  const parts = /^(-?)([0-9]+)(?:\.([0-9]+))?$/.exec(value);
  if (!parts) return "נתון לא תקין";
  const integer = BigInt(parts[2]).toLocaleString("he-IL");
  const fraction = (parts[3] ?? "").replace(/0+$/, "");
  return parts[1] + integer + (fraction ? "." + fraction : "");
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
  const employmentSaveGeneration = useRef(0);
  const grantSaveGeneration = useRef(0);
  activeClient.current = clientId;
  const [read, setRead] = useState<ReadState>({ state: "loading" });
  const [step, setStep] = useState<Step>("portfolio");
  const [supplement, setSupplement] = useState<{ clientId: number; groups: Array<Array<{ client_id: number; title: string; detail: string }>> } | null>(null);
  const [supplementError, setSupplementError] = useState<string | null>(null);
  const [supplementLoading, setSupplementLoading] = useState(false);
  const [employmentRecords, setEmploymentRecords] = useState<EmploymentRecordItem[]>([]);
  const [employmentEdit, setEmploymentEdit] = useState<EmploymentRecordItem | null>(null);
  const [employmentCreating, setEmploymentCreating] = useState(false);
  const [historicalGrantStatus, setHistoricalGrantStatus] = useState<ExemptGrantStatus>("not_reviewed");
  const [historicalGrantFile, setHistoricalGrantFile] = useState("");
  const [historicalGrantDate, setHistoricalGrantDate] = useState("");
  const [historicalGrantAmount, setHistoricalGrantAmount] = useState("");
  const [employmentSaving, setEmploymentSaving] = useState(false);
  const [employmentError, setEmploymentError] = useState<string | null>(null);
  const [grantRecords, setGrantRecords] = useState<GrantItem[]>([]);
  const [grantEdit, setGrantEdit] = useState<GrantItem | null>(null);
  const [grantSaving, setGrantSaving] = useState(false);
  const [grantCreating, setGrantCreating] = useState(false);
  const [grantCreatingForPeriod, setGrantCreatingForPeriod] = useState<string | null>(null);
  const [grantError, setGrantError] = useState<string | null>(null);
  const [linkingGrantId, setLinkingGrantId] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [supplementCategory, setSupplementCategory] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [hideEmptyColumns, setHideEmptyColumns] = useState(false);
  const [discrepancyOnly, setDiscrepancyOnly] = useState(false);
  const [selection, setSelection] = useState<Selection[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    employmentSaveGeneration.current += 1;
    grantSaveGeneration.current += 1;
    setRead({ state: "loading" });
    setStep("portfolio");
    setSupplement(null);
    setSupplementError(null);
    setSupplementLoading(false);
    setEmploymentRecords([]);
    setGrantRecords([]);
    setGrantEdit(null);
    setGrantCreating(false);
    setGrantCreatingForPeriod(null);
    setGrantError(null);
    setGrantSaving(false);
    setLinkingGrantId(null);
    setLinkError(null);
    setEmploymentEdit(null);
    setEmploymentCreating(false);
    setHistoricalGrantStatus("not_reviewed");
    setHistoricalGrantFile("");
    setHistoricalGrantDate("");
    setHistoricalGrantAmount("");
    setEmploymentError(null);
    setEmploymentSaving(false);
    setSupplementCategory(null);
    setSearch("");
    setHideEmptyColumns(false);
    setDiscrepancyOnly(false);
    setSelection([]);
    setDraft(null);
    setError(null);
    setSaveState("idle");
    if (!validClient) {
      setRead({ state: "error", clientId, message: "מזהה לקוח לא תקין" });
      return;
    }
    let active = true;
    void Promise.all([getClient(clientId), listPensionProducts(clientId)]).then(([client, products]) => {
      if (!active) return;
      if (client.client_id !== clientId || products.some(product => product.client_id !== clientId)) {
        setRead({ state: "error", clientId, message: "זוהתה אי־התאמה בהקשר הלקוח; הנתונים לא יוצגו" });
        return;
      }
      setRead({ state: "ready", client, products });
    }).catch(reason => {
      if (active) setRead({ state: "error", clientId, message: errorText(reason) });
    });
    return () => { active = false; };
  }, [clientId, validClient]);

  useEffect(() => {
    if (step !== "supplement" || !validClient || read.state !== "ready" || read.client.client_id !== clientId) return;
    let active = true;
    setSupplement(null);
    setSupplementError(null);
    setEmploymentRecords([]);
    setEmploymentEdit(null);
    setSupplementLoading(true);
    void Promise.all([
      getEmploymentRecords(clientId), getGrants(clientId), getActualCapitalizations(clientId),
      getCapitalAssets(clientId), getRecurringIncomes(clientId), getRecurringExpenses(clientId),
    ]).then(groups => {
      if (!active || activeClient.current !== clientId) return;
      if (groups.some(items => items.some(item => item.client_id !== clientId))) {
        setSupplementError("נתונים משלימים אינם תואמים ללקוח הנוכחי.");
        return;
      }
      const entries = [
        groups[0].map(item => ({ client_id: item.client_id, title: item.employer_name, detail: item.work_start_date + " עד " + (item.work_end_date ?? "כיום") })),
        groups[1].map(item => ({ client_id: item.client_id, title: item.employer_name ?? "מענק ללא שם מעסיק", detail: "מועד קבלה: " + item.grant_receipt_date + " · מענק פטור מדווח: " + (item.exempt_grant_amount ?? "לא נמסר") })),
        groups[2].map(item => ({ client_id: item.client_id, title: item.source_label ?? "היוון בפועל", detail: "מועד: " + item.capitalization_date + " · סכום: " + item.amount })),
        groups[3].map(item => ({ client_id: item.client_id, title: item.asset_description, detail: "שווי ידוע: " + (item.known_value_amount ?? "לא נמסר") + " · מצב: " + item.verification_state })),
        groups[4].map(item => ({ client_id: item.client_id, title: item.description, detail: "סכום מדווח: " + item.amount + " · " + item.frequency + " · " + item.amount_basis })),
        groups[5].map(item => ({ client_id: item.client_id, title: item.description, detail: "סכום מדווח: " + item.amount + " · " + item.frequency })),
      ];
      setEmploymentRecords(groups[0]);
      setGrantRecords(groups[1]);
      setSupplement({ clientId, groups: entries });
    }).catch(reason => {
      if (active && activeClient.current === clientId) setSupplementError(errorText(reason));
    }).finally(() => {
      if (active && activeClient.current === clientId) setSupplementLoading(false);
    });
    return () => { active = false; };
  }, [step, clientId, validClient, read.state === "ready" ? read.client.client_id : null]);

  async function saveEmployment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!employmentEdit || employmentSaving || activeClient.current !== clientId) return;
    const record = employmentEdit;
    if (!record.employer_name.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(record.work_start_date)
      || (!record.is_current && (!record.work_end_date || !/^\d{4}-\d{2}-\d{2}$/.test(record.work_end_date)
        || record.work_end_date < record.work_start_date))) {
      setEmploymentError("יש להזין שם מעסיק ותאריכי העסקה תקינים; תאריך הסיום אינו יכול להקדים את תאריך ההתחלה.");
      return;
    }
    if (employmentCreating && !record.is_current && historicalGrantStatus === "recorded"
      && (!historicalGrantFile.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(historicalGrantDate)
        || !completeAmount(historicalGrantAmount) || Number(historicalGrantAmount) <= 0)) {
      setEmploymentError("להזנת מענק פטור נדרשים תיק ניכויים, תאריך קבלה וסכום חיובי תקין.");
      return;
    }
    const generation = ++employmentSaveGeneration.current;
    setEmploymentSaving(true);
    setEmploymentError(null);
    try {
      const payload = {
        employer_name: record.employer_name.trim(), work_start_date: record.work_start_date,
        work_end_date: record.is_current ? null : record.work_end_date,
        is_current: record.is_current, notes: record.notes,
      };
      const settlement = employmentCreating && !record.is_current
        ? await createHistoricalEmploymentSettlement(clientId, {
            employment: payload, exempt_grant_status: historicalGrantStatus,
            ...(historicalGrantStatus === "recorded" ? {
              employer_withholding_file_number: historicalGrantFile.trim(),
              grant_receipt_date: historicalGrantDate,
              exempt_grant_amount: historicalGrantAmount,
            } : {}),
          }) : null;
      const saved = settlement
        ? { employment_record_id: settlement.employment_record_id, client_id: settlement.client_id }
        : employmentCreating
          ? await createEmploymentRecord(clientId, payload)
          : await updateEmploymentRecord(clientId, record.employment_record_id, {
              ...payload, ...(!record.is_current && grantRecords.every(grant => grant.employment_record_id !== record.employment_record_id)
                ? { exempt_grant_status: historicalGrantStatus } : {}),
            });
      if (activeClient.current !== clientId || employmentSaveGeneration.current !== generation) return;
      if (saved.client_id !== clientId || (!employmentCreating && saved.employment_record_id !== record.employment_record_id)) {
        setEmploymentError("תשובת שמירה אינה תואמת לתיק הנוכחי.");
        return;
      }
      const refreshed = await getEmploymentRecords(clientId);
      if (activeClient.current !== clientId || employmentSaveGeneration.current !== generation) return;
      if (refreshed.some(item => item.client_id !== clientId)) { setEmploymentError("התקבלו רשומות של לקוח אחר."); return; }
      if (settlement?.grant_id) {
        const updatedGrants = await getGrants(clientId);
        if (activeClient.current !== clientId || employmentSaveGeneration.current !== generation) return;
        if (updatedGrants.some(item => item.client_id !== clientId)) {
          setEmploymentError("התקבלו מענקים השייכים ללקוח אחר.");
          return;
        }
        setGrantRecords(updatedGrants);
        setSupplement(previous => previous?.clientId === clientId ? {
          ...previous, groups: previous.groups.map((group, index) => index === 1
            ? updatedGrants.map(item => ({
              client_id: item.client_id, title: item.employer_name ?? "מענק ללא שם מעסיק",
              detail: "מועד קבלה: " + item.grant_receipt_date + " · מענק פטור מדווח: " + (item.exempt_grant_amount ?? "לא נמסר"),
            })) : group),
        } : previous);
      }
      setEmploymentRecords(refreshed);
      setSupplement(previous => previous?.clientId === clientId ? {
        ...previous, groups: previous.groups.map((group, index) => index === 0
          ? refreshed.map(item => ({ client_id: item.client_id, title: item.employer_name,
            detail: item.work_start_date + " עד " + (item.work_end_date ?? "כיום") })) : group),
      } : previous);
      setEmploymentEdit(null);
      setEmploymentCreating(false);
    } catch (reason) {
      if (activeClient.current === clientId && employmentSaveGeneration.current === generation) setEmploymentError(errorText(reason));
    } finally {
      if (activeClient.current === clientId && employmentSaveGeneration.current === generation) setEmploymentSaving(false);
    }
  }

  async function saveGrant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!grantEdit || grantSaving || activeClient.current !== clientId) return;
    const record = grantEdit;
    const date = /^\d{4}-\d{2}-\d{2}$/;
    const amount = /^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$/;
    if (!record.employer_name?.trim() || !record.employer_withholding_file_number?.trim()
      || !date.test(record.employment_start_date) || !date.test(record.employment_end_date)
      || !date.test(record.grant_receipt_date)
      || record.employment_end_date < record.employment_start_date
      || record.exempt_grant_amount == null || !amount.test(String(record.exempt_grant_amount))) {
      setGrantError("נדרשים מעסיק, תיק ניכויים, תאריכים תקינים וסכום מענק פטור לא שלילי. יש לוודא שסיום העסקה אינו קודם לתחילתה.");
      return;
    }
    const generation = ++grantSaveGeneration.current;
    setGrantSaving(true);
    setGrantError(null);
    try {
      const payload = {
        employer_name: record.employer_name.trim(),
        employer_withholding_file_number: record.employer_withholding_file_number.trim(),
        employment_start_date: record.employment_start_date,
        employment_end_date: record.employment_end_date,
        grant_receipt_date: record.grant_receipt_date,
        exempt_grant_amount: String(record.exempt_grant_amount),
      };
      const saved = grantCreating && grantCreatingForPeriod
        ? await createGrantForEmployment(clientId, grantCreatingForPeriod, payload)
        : await updateGrant(clientId, record.grant_id, payload);
      if (activeClient.current !== clientId || grantSaveGeneration.current !== generation) return;
      if (saved.client_id !== clientId || (grantCreating && saved.employment_record_id !== grantCreatingForPeriod)
        || (!grantCreating && saved.grant_id !== record.grant_id)) {
        setGrantError("תשובת מענק אינה תואמת לרשומה וללקוח.");
        return;
      }
      const refreshed = await getGrants(clientId);
      if (activeClient.current !== clientId || grantSaveGeneration.current !== generation) return;
      if (refreshed.some(item => item.client_id !== clientId)) {
        setGrantError("התקבלו מענקים השייכים ללקוח אחר.");
        return;
      }
      setGrantRecords(refreshed);
      setSupplement(previous => previous?.clientId === clientId ? {
        ...previous, groups: previous.groups.map((group, index) => index === 1
          ? refreshed.map(item => ({ client_id: item.client_id,
            title: item.employer_name ?? "מענק ללא שם מעסיק",
            detail: "מועד קבלה: " + item.grant_receipt_date + " · מענק פטור מדווח: " + (item.exempt_grant_amount ?? "לא נמסר") }))
          : group),
      } : previous);
      setGrantEdit(null);
      setGrantCreating(false);
      setGrantCreatingForPeriod(null);
    } catch (reason) {
      if (activeClient.current === clientId && grantSaveGeneration.current === generation) setGrantError(errorText(reason));
    } finally {
      if (activeClient.current === clientId && grantSaveGeneration.current === generation) setGrantSaving(false);
    }
  }

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

  function chooseSupplementCategory(next: number | null) {
    if (next === supplementCategory) return;
    if (employmentEdit || grantEdit || employmentSaving || grantSaving) {
      setError("יש לשמור או לבטל את תיקון הנתונים לפני מעבר לקטגוריה אחרת.");
      return;
    }
    setError(null);
    setSupplementCategory(next);
  }

  async function confirmGrantLink(grant: GrantItem, period: EmploymentRecordItem) {
    if (activeClient.current !== clientId || linkingGrantId || grantSaving || employmentSaving || employmentEdit || grantEdit) return;
    if (grantRecords.some(item => item.employment_record_id === period.employment_record_id)) {
      setLinkError("כבר רשום מענק פטור לתקופת העסקה זו. יש לתקן את ההתחשבנות הקיימת ולא להוסיף מענק נוסף.");
      return;
    }
    if (grant.client_id !== clientId || period.client_id !== clientId || grant.employment_record_id
      || period.is_current || !period.work_end_date
      || grant.employment_start_date !== period.work_start_date
      || grant.employment_end_date !== period.work_end_date) {
      setLinkError("אפשר לשייך רק מענק לא מקושר לתקופת העסקה שהסתיימה, עם תאריכים תואמים.");
      return;
    }
    const approved = window.confirm("לשייך את המענק המדווח של " + (grant.employer_name ?? "מעסיק לא מזוהה")
      + " לתקופת ההעסקה " + period.employer_name + " (" + period.work_start_date + "–" + period.work_end_date + ")?");
    if (!approved) return;
    const capturedClient = clientId;
    setLinkingGrantId(grant.grant_id);
    setLinkError(null);
    try {
      const linked = await linkGrantToEmployment(clientId, grant.grant_id, period.employment_record_id);
      if (activeClient.current !== capturedClient) return;
      if (linked.client_id !== capturedClient || linked.grant_id !== grant.grant_id
        || linked.employment_record_id !== period.employment_record_id) {
        setLinkError("תשובת השיוך אינה תואמת למענק ולתקופת ההעסקה.");
        return;
      }
      const refreshed = await getGrants(clientId);
      if (activeClient.current !== capturedClient) return;
      if (refreshed.some(item => item.client_id !== capturedClient)) {
        setLinkError("התקבלו מענקים השייכים ללקוח אחר.");
        return;
      }
      setGrantRecords(refreshed);
      setSupplement(previous => previous?.clientId === clientId ? {
        ...previous, groups: previous.groups.map((group, index) => index === 1
          ? refreshed.map(item => ({ client_id: item.client_id,
            title: item.employer_name ?? "מענק ללא שם מעסיק",
            detail: "מועד קבלה: " + item.grant_receipt_date + " · מענק פטור מדווח: " + (item.exempt_grant_amount ?? "לא נמסר") }))
          : group),
      } : previous);
    } catch (reason) {
      if (activeClient.current === capturedClient) setLinkError(errorText(reason));
    } finally {
      if (activeClient.current === capturedClient) setLinkingGrantId(null);
    }
  }

  function openSupplementEditor(kind: "employment" | "grant", index: number) {
    if (employmentSaving || grantSaving || employmentEdit !== null || grantEdit !== null) {
      setError("יש לשמור או לבטל את תיקון הנתונים לפני מעבר לעריכת רשומה אחרת.");
      return;
    }
    setError(null);
    if (kind === "employment") {
      const record = employmentRecords[index];
      if (!record || record.client_id !== clientId) return;
      setEmploymentError(null);
      setEmploymentCreating(false);
      setEmploymentEdit({ ...record });
      setHistoricalGrantStatus(record.exempt_grant_status === "none" ? "none" : record.exempt_grant_status === "recorded" ? "recorded" : "not_reviewed");
    } else {
      const record = grantRecords[index];
      if (!record || record.client_id !== clientId) return;
      setGrantError(null);
      setGrantCreating(false);
      setGrantCreatingForPeriod(null);
      setGrantEdit({ ...record });
    }
  }

  function switchStep(next: Step) {
    if (draft !== null || saveState === "saving" || employmentEdit !== null || employmentSaving || grantEdit !== null || grantSaving) {
      setError("יש לשמור או לבטל את תיקון הנתונים לפני מעבר לשלב אחר.");
      return;
    }
    setSelection([]);
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
  if (read.state === "loading" || (read.state === "ready" && read.client.client_id !== clientId) || (read.state === "error" && read.clientId !== clientId)) {
    return <main dir="rtl"><p>טוען סביבת עבודה...</p></main>;
  }
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
      {error && <p role="alert" className="professional-workspace__error">{error}</p>}
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
            setSearch(event.target.value); setSelection([]);
          }} placeholder="תוכנית, גוף מנהל או חשבון" disabled={draft !== null || saveState === "saving"} /></label>
          <label><input type="checkbox" checked={hideEmptyColumns} disabled={draft !== null || saveState === "saving"} onChange={event => { setHideEmptyColumns(event.target.checked); setSelection([]); }}/> הסתר טורים ללא יתרה</label>
          <label><input type="checkbox" checked={discrepancyOnly} disabled={draft !== null || saveState === "saving"} onChange={event => { setDiscrepancyOnly(event.target.checked); setSelection([]); }}/> הצג רק פערי התאמה</label>
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
      </section>}
      {step === "supplement" && <section>
        <h1>נתונים משלימים</h1>
        <p className="professional-workspace__sub">נתוני הלקוח מוצגים כאן ממסד הנתונים. ניתן לתקן כאן תעסוקה ומענקים קיימים; הוספה, מחיקה ועריכת נתונים אחרים מתבצעות במסכים הייעודיים.</p>
        {supplementLoading && <p role="status">טוען נתונים משלימים...</p>}
        {supplementError && <p role="alert">{supplementError}</p>}
        {linkError && <p role="alert">{linkError}</p>}
        {supplement?.clientId === clientId && !supplementError && <>
          <nav aria-label="סינון נתונים משלימים" className="professional-workspace__supplement-filter">
            <button type="button" aria-pressed={supplementCategory === null} onClick={() => chooseSupplementCategory(null)}>כל הנתונים</button>
            {(["רשומות תעסוקה", "מענקים", "היוונים בפועל", "נכסי הון", "הכנסות נוספות", "הוצאות שוטפות"] as const).map((label, index) =>
              <button key={label} type="button" aria-pressed={supplementCategory === index} onClick={() => chooseSupplementCategory(index)}>{label} ({supplement.groups[index].length})</button>)}
          </nav>
          <div className="professional-workspace__identity">
          {(["רשומות תעסוקה", "מענקים", "היוונים בפועל", "נכסי הון", "הכנסות נוספות", "הוצאות שוטפות"] as const).map((label, index) =>
            (supplementCategory === null || supplementCategory === index) && <section key={label} className={supplement.groups[index].length ? "has-records" : "is-empty"}>
              <h2>{label} ({supplement.groups[index].length})</h2>
              {index === 0 && <p>אפשר להוסיף או לתקן רשומת תעסוקה כאן. מחיקה במסך המלא.
                <button type="button" disabled={employmentSaving || grantSaving} onClick={() => {
                  if (employmentEdit || grantEdit) {
                    setError("יש לשמור או לבטל את העריכה הפתוחה לפני הוספת רשומה.");
                    return;
                  }
                  setError(null);
                  setEmploymentError(null);
                  setEmploymentCreating(true);
                  setEmploymentEdit({
                    employment_record_id: "", client_id: clientId, employer_name: "",
                    work_start_date: "", work_end_date: null, is_current: true, notes: null,
                  });
                  setSupplementCategory(0);
                }}>הוסף רשומת תעסוקה</button></p>}
              {index === 1 && <p>ריכוז מענקים מדווחים לתצוגה ובקרה. יצירת מענק חדש מתבצעת מתוך תקופת העסקה היסטורית; מענקים ישנים שלא שויכו נשארים גלויים עד לשיוך מפורש.</p>}
              {index === 0 ? <p>עריכת תקופות תעסוקה והתחשבנות מתבצעת כאן, באמצעות כפתור "תקן רשומת תעסוקה" בכל תקופה.</p>
                : index === 1 ? <p>תיקון מענק מתבצע כאן. <Link to={"/clients/" + clientId + "/grants"}>פעולות מענקים נוספות בממשק הוותיק</Link></p>
                : <p><Link to={"/clients/" + clientId + "/" + (index === 2 ? "actual-capitalizations" : "planning-input")}>פתיחת עריכה: {label}</Link></p>}
              {supplement.groups[index].length === 0 ? <p>לא קיימות רשומות</p> : <ul>
                {supplement.groups[index].map((item, itemIndex) => <li key={itemIndex}>
                  <strong>{item.title}</strong> <span>{item.detail}</span>
                  {index === 1 && grantRecords[itemIndex] && <button type="button" disabled={grantSaving} onClick={() => openSupplementEditor("grant", itemIndex)}>תקן מענק</button>}
                  {index === 0 && employmentRecords[itemIndex] && <button type="button" disabled={employmentSaving} onClick={() => openSupplementEditor("employment", itemIndex)}>תקן רשומת תעסוקה</button>}
                  {index === 0 && employmentRecords[itemIndex] && !employmentRecords[itemIndex].is_current && <p>
                    מצב מענק פטור: {({
                      not_reviewed: "טרם נבדק", none: "לא התקבל מענק פטור",
                      recorded: "דווח מענק פטור", requires_reconciliation: "נדרשת בדיקת כפילות",
                    } as Record<string, string>)[employmentRecords[itemIndex].exempt_grant_status ?? "not_reviewed"]}
                  </p>}
                  {index === 0 && employmentRecords[itemIndex] && !employmentRecords[itemIndex].is_current && <>
                    <button type="button" disabled={grantRecords.some(grant => grant.employment_record_id === employmentRecords[itemIndex].employment_record_id) || !!linkingGrantId || grantSaving || employmentSaving || !!employmentEdit || !!grantEdit}
                      onClick={() => {
                        const period = employmentRecords[itemIndex];
                        if (!period || !period.work_end_date) return;
                        setGrantCreating(true);
                        setGrantCreatingForPeriod(period.employment_record_id);
                        setGrantError(null);
                        setError(null);
                        setGrantEdit({
                          grant_id: "", client_id: clientId, employer_name: period.employer_name,
                          employer_withholding_file_number: "", employment_start_date: period.work_start_date,
                          employment_end_date: period.work_end_date, grant_receipt_date: "",
                          exempt_grant_amount: "",
                        });
                        setSupplementCategory(0);
                      }}>הוסף מענק לתקופת העסקה</button>
                    {grantRecords.filter(grant => grant.employment_record_id === employmentRecords[itemIndex].employment_record_id).length > 1 && <p role="alert">קיימת כפילות מענקים פטורים לתקופת העסקה זו. נדרש בירור ותיקון נתונים, ללא מחיקה אוטומטית.</p>}
                    {grantRecords.filter(grant => grant.employment_record_id === employmentRecords[itemIndex].employment_record_id).map(grant =>
                      <p key={grant.grant_id}>מענק משויך: {grant.employer_name} — {grant.exempt_grant_amount} ₪ (מדווח)</p>)}
                    {grantRecords.filter(grant => !grant.employment_record_id
                      && grant.employment_start_date === employmentRecords[itemIndex].work_start_date
                      && grant.employment_end_date === employmentRecords[itemIndex].work_end_date).map(grant =>
                      <button type="button" key={grant.grant_id} disabled={grantRecords.some(row => row.employment_record_id === employmentRecords[itemIndex].employment_record_id) || !!linkingGrantId || grantSaving || employmentSaving || !!employmentEdit || !!grantEdit}
                        onClick={() => void confirmGrantLink(grant, employmentRecords[itemIndex])}>
                        שייך מענק לא מקושר: {grant.employer_name} — {grant.exempt_grant_amount} ₪
                      </button>)}
                  </>}
                  {index === 1 && grantRecords[itemIndex] && <small>{grantRecords[itemIndex].employment_record_id ? "משויך לתקופת העסקה" : "טרם שויך לתקופת העסקה"}</small>}
                </li>)}
              </ul>}
            </section>)}
        </div></>}
        {employmentEdit && supplement?.clientId === clientId && <form onSubmit={saveEmployment}>
          <h3>{employmentCreating ? "הוספת רשומת תעסוקה" : "תיקון רשומת תעסוקה"}</h3>
          <label>שם מעסיק <input required value={employmentEdit.employer_name} onChange={event => setEmploymentEdit(prev => prev && ({ ...prev, employer_name: event.target.value }))} /></label>
          <label>תאריך תחילה <input type="date" required value={employmentEdit.work_start_date} onChange={event => setEmploymentEdit(prev => prev && ({ ...prev, work_start_date: event.target.value }))} /></label>
          <label>מועסק כיום <input type="checkbox" checked={employmentEdit.is_current} onChange={event => setEmploymentEdit(prev => prev && ({ ...prev, is_current: event.target.checked, work_end_date: event.target.checked ? null : prev.work_end_date }))} /></label>
          {!employmentEdit.is_current && <fieldset>
            <legend>התחשבנות פיצויים בסיום העסקה</legend>
            {!employmentCreating && grantRecords.some(grant => grant.employment_record_id === employmentEdit.employment_record_id) ? (
              <p>מצב מענק: {employmentEdit.exempt_grant_status === "requires_reconciliation" ? "נדרשת בדיקת כפילות מענקים — אין לשנות סטטוס עד לבירור" : "קיים מענק פטור משויך — יש לתקן את הנתון במענק הקיים"}</p>
            ) : <label>מצב מענק הפיצויים הפטור
              <select value={historicalGrantStatus} onChange={event => setHistoricalGrantStatus(event.target.value as ExemptGrantStatus)}>
                <option value="not_reviewed">טרם נבדק</option>
                <option value="none">לא התקבל מענק פטור</option>
                {employmentCreating && <option value="recorded">התקבל מענק פטור</option>}
              </select>
            </label>}
            {(employmentCreating && historicalGrantStatus === "recorded") && <>
              <label>מספר תיק ניכויים <input required value={historicalGrantFile} onChange={event => setHistoricalGrantFile(event.target.value)} /></label>
              <label>מועד קבלת מענק <input required type="date" value={historicalGrantDate} onChange={event => setHistoricalGrantDate(event.target.value)} /></label>
              <label>מענק פיצויים פטור מדווח <input required inputMode="decimal" value={historicalGrantAmount} onChange={event => setHistoricalGrantAmount(event.target.value)} /></label>
            </>}
            <p>זהו רישום עובדתי בלבד. שדות רצפים, מענקים חייבים ואסמכתאות יתווספו לאחר אישור חוזה הנתונים המקצועי.</p>
          </fieldset>}
          {!employmentEdit.is_current && <label>תאריך סיום <input type="date" value={employmentEdit.work_end_date ?? ""} onChange={event => setEmploymentEdit(prev => prev && ({ ...prev, work_end_date: event.target.value || null }))} /></label>}
          <label>הערות <textarea value={employmentEdit.notes ?? ""} onChange={event => setEmploymentEdit(prev => prev && ({ ...prev, notes: event.target.value || null }))} /></label>
          {employmentError && <p role="alert">{employmentError}</p>}
          <button type="submit" disabled={employmentSaving || !employmentEdit.employer_name.trim() || (!employmentEdit.is_current && !employmentEdit.work_end_date)}>{employmentCreating ? "שמור רשומת תעסוקה חדשה" : "שמור תיקון תעסוקה"}</button>
          <button type="button" disabled={employmentSaving} onClick={() => { setEmploymentEdit(null); setEmploymentCreating(false); setEmploymentError(null); setError(null); }}>ביטול</button>
        </form>}
        {grantEdit && supplement?.clientId === clientId && <form onSubmit={saveGrant}>
          <h3>{grantCreating ? "הוספת מענק לתקופת העסקה" : "תיקון מענק היסטורי"}</h3>
          <label>שם מעסיק <input required value={grantEdit.employer_name ?? ""} onChange={e => setGrantEdit(prev => prev && ({ ...prev, employer_name: e.target.value }))} /></label>
          <label>מספר תיק ניכויים <input required value={grantEdit.employer_withholding_file_number ?? ""} onChange={e => setGrantEdit(prev => prev && ({ ...prev, employer_withholding_file_number: e.target.value }))} /></label>
          <label>תחילת העסקה <input type="date" required value={grantEdit.employment_start_date} onChange={e => setGrantEdit(prev => prev && ({ ...prev, employment_start_date: e.target.value }))} /></label>
          <label>סיום העסקה <input type="date" required value={grantEdit.employment_end_date} onChange={e => setGrantEdit(prev => prev && ({ ...prev, employment_end_date: e.target.value }))} /></label>
          <label>מועד קבלת מענק <input type="date" required value={grantEdit.grant_receipt_date} onChange={e => setGrantEdit(prev => prev && ({ ...prev, grant_receipt_date: e.target.value }))} /></label>
          <label>סכום מענק פטור מדווח <input required inputMode="decimal" value={grantEdit.exempt_grant_amount ?? ""} onChange={e => setGrantEdit(prev => prev && ({ ...prev, exempt_grant_amount: e.target.value }))} /></label>
          {grantError && <p role="alert">{grantError}</p>}
          <button type="submit" disabled={grantSaving}>{grantCreating ? "שמור מענק חדש" : "שמור תיקון מענק"}</button>
          <button type="button" disabled={grantSaving} onClick={() => { setGrantEdit(null); setGrantCreating(false); setGrantCreatingForPeriod(null); setGrantError(null); setError(null); }}>ביטול</button>
        </form>}
      </section>}
      {step === "scenario" && <section>
        <h1>תכנון תרחישים</h1>
        <p className="professional-workspace__boundary">
          שלב החיבור למנוע התרחישים עדיין לא בוצע. ההמרה הקנונית הקיימת ב־V2 מעדכנת יתרות אמת,
          ולכן היא לא תופעל מכאן בתור החלטת תרחיש.
        </p>
        <h2>לוח עבודה לתרחישים — המחשת UX, ללא שמירה</h2>
        <div className="professional-workspace__scenario-preview" aria-label="תצוגה תכנונית ללא נתוני תרחיש אמיתיים">
          <section>
            <h3>חלופות להשוואה</h3>
            <table><thead><tr><th scope="col">חלופה</th><th scope="col">תפקיד בתהליך</th><th scope="col">מצב</th></tr></thead>
              <tbody>
                <tr><th scope="row">מצב בסיס</th><td>צילום מצב עובדתי להשוואה</td><td>טרם הופק</td></tr>
                <tr><th scope="row">חלופה חדשה</th><td>החלטות עצמאיות שאינן משנות יתרות מקור</td><td>טרם נוצרה</td></tr>
                <tr><th scope="row">חלופה להשוואה</th><td>בחירת החלטות אחרות או העתקת חלופה</td><td>טרם נוצרה</td></tr>
              </tbody>
            </table>
          </section>
          <section>
            <h3>מהלך עבודה לכל חלופה</h3>
            <ol>
              <li>בחירת מקור עובדתי מאומת מתוך התיק הפנסיוני או הנתונים המשלימים.</li>
              <li>הגדרת החלטה בתרחיש בלבד: קצבה, הון, או השארת הכספים במעמדם הקיים, בכפוף לכללים מקצועיים.</li>
              <li>צפייה בהחלטות, תיקון או ביטול — בלי לשנות את המקור ובלי להשפיע על חלופה אחרת.</li>
              <li>הפעלה נפרדת של מנוע חישוב מורשה, ופסילת תוצאה שהתיישנה בעקבות שינוי נתוני אמת.</li>
            </ol>
          </section>
        </div>
        <p className="professional-workspace__boundary">השלבים לעיל הם אפיון UX בלבד: אין כפתורי פעולה מדומים, אין כתיבה למסד ואין חישוב מס או קצבה.</p>
      </section>}
      {step === "results" && <section>
        <h1>תוצאות והשוואה</h1>
        <p className="professional-workspace__boundary">
          אין עדיין השוואת חלופות מחושבת בממשק זה. לא יוצגו מספרי קצבה, פטורים, מס או NPV שלא חושבו ואושרו במנוע V2.
        </p>
        <h2>מבנה טבלת השוואה — דוגמת פריסה בלבד</h2>
        <div className="professional-workspace__ledger" role="region" aria-label="מבנה השוואת חלופות ללא תוצאות" tabIndex={0}>
          <table>
            <thead><tr><th scope="col">מדד</th><th scope="col">מצב בסיס</th><th scope="col">חלופה א׳</th><th scope="col">חלופה ב׳</th></tr></thead>
            <tbody>
              {["מועד פרישה", "החלטות והקצאות", "קצבה חודשית", "משיכות הוניות", "מסים ופטורים", "הנחות ומקורות", "עדכניות תוצאה"].map(label =>
                <tr key={label}><th scope="row">{label}</th><td>לא חושב</td><td>לא חושב</td><td>לא חושב</td></tr>)}
            </tbody>
          </table>
        </div>
        <p>בעתיד כל תוצאה תציג את ההחלטות, הבסיס המקצועי ומועד החישוב. שינוי בנתוני המקור ידרוש אימות מחודש ולא יוצג כתוצאה מעודכנת.</p>
        <p className="professional-workspace__boundary">אין עדיין תרחישים מחושבים להצגה או אישור מקצועי של ההשוואה.</p>
        <Link to={"/clients/" + clientId + "/retirement-income-readiness"}>מעבר למסך מוכנות ההכנסה הקיים</Link>
      </section>}
    </div>
  </main>;
}
