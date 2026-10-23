import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getClient, getEmploymentRecords, getGrants, getActualCapitalizations, getCapitalAssets, getRecurringIncomes, getRecurringExpenses, updateEmploymentRecord, createEmploymentRecord, createHistoricalEmploymentSettlement, updateGrant, createGrantForEmployment, linkGrantToEmployment, type ClientDetailItem } from "../api/clientsApi";
import { listPensionProducts, savePensionProduct, type PensionProduct } from "../api/pensionProductsApi";
import { RetirementWorkspaceScreen } from "./RetirementWorkspaceScreen";

vi.mock("../api/clientsApi", () => ({
  getClient: vi.fn(),
  getEmploymentRecords: vi.fn(), getGrants: vi.fn(), getActualCapitalizations: vi.fn(),
  getCapitalAssets: vi.fn(), getRecurringIncomes: vi.fn(), getRecurringExpenses: vi.fn(), updateEmploymentRecord: vi.fn(), createEmploymentRecord: vi.fn(), createHistoricalEmploymentSettlement: vi.fn(), updateGrant: vi.fn(), createGrantForEmployment: vi.fn(), linkGrantToEmployment: vi.fn(),
}));
vi.mock("../api/pensionProductsApi", () => ({
  listPensionProducts: vi.fn(),
  savePensionProduct: vi.fn(),
}));

function client(id = 1): ClientDetailItem {
  return {
    client_id: id,
    full_name: id === 1 ? "לקוח א" : "לקוח ב",
    id_number: id === 1 ? "000000001" : "000000002",
    birth_date: "1963-01-01",
    file_status: "file_created",
    professional_identification_status: "professionally_identified",
  };
}

function product(id = 1): PensionProduct {
  return {
    product_id: "p" + id, client_id: id, version: 1,
    product_name: "קרן פנסיה " + (id === 1 ? "א" : "ב"),
    source_kind: "imported", product_type: "קרן פנסיה",
    provider_name: "חברת ניהול", provider_identifier: null,
    account_reference: "123", start_date: null, statement_date: "2026-09-30",
    historical_employers: [], reported_product_total: "150.00",
    reported_rewards_total: null, reported_severance_total: null,
    components: {
      "פיצויים_מעסיק_נוכחי": "100.00",
      "פיצויים_לאחר_התחשבנות": "50.00",
    },
    reconciliation: {
      rewards_component_sum: "0.00", severance_component_sum: "150.00",
      product_component_sum: "150.00", product_discrepancy: "0.00",
    },
    updated_at: "2026-09-30T12:00:00Z",
  };
}

function SwitchClient() {
  const navigate = useNavigate();
  return <button type="button" onClick={() => navigate("/clients/2/workspace")}>עבור ללקוח ב</button>;
}

function open() {
  return render(<MemoryRouter initialEntries={["/clients/1/workspace"]}>
    <SwitchClient />
    <Routes>
      <Route path="/clients/:clientId/workspace" element={<RetirementWorkspaceScreen />} />
    </Routes>
  </MemoryRouter>);
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getClient).mockImplementation(id => Promise.resolve(client(id)));
  vi.mocked(getEmploymentRecords).mockResolvedValue([]);
  vi.mocked(getGrants).mockResolvedValue([]);
  vi.mocked(getActualCapitalizations).mockResolvedValue([]);
  vi.mocked(getCapitalAssets).mockResolvedValue([]);
  vi.mocked(getRecurringIncomes).mockResolvedValue([]);
  vi.mocked(getRecurringExpenses).mockResolvedValue([]);
  vi.mocked(listPensionProducts).mockImplementation(id => Promise.resolve([product(id)]));
});

describe("סביבת העבודה המקצועית החדשה", () => {
  it("loads a single ledger from authoritative client/product APIs and never writes on selection", async () => {
    open();
    const region = await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    expect(within(region).getAllByRole("row")).toHaveLength(2);
    expect(within(region).getByText("קרן פנסיה א")).toBeInTheDocument();
    fireEvent.click(within(region).getByRole("button", { name: "פיצויים מעסיק נוכחי — קרן פנסיה א" }));
    expect(screen.getByText("1 רכיבים נבחרו")).toBeInTheDocument();
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("corrects two selected factual components with one versioned PUT, preserving metadata", async () => {
    const result = { ...product(), version: 2,
      components: { ...product().components,
        "פיצויים_מעסיק_נוכחי": "90.00", "פיצויים_לאחר_התחשבנות": "60.00" } };
    vi.mocked(savePensionProduct).mockResolvedValue(result);
    open();
    const region = await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(within(region).getByRole("button", { name: "פיצויים מעסיק נוכחי — קרן פנסיה א" }));
    fireEvent.click(within(region).getByRole("button", { name: "פיצויים לאחר התחשבנות — קרן פנסיה א" }));
    fireEvent.click(screen.getByRole("button", { name: "תיקון יתרות נבחרות" }));
    fireEvent.change(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" }),
      { target: { value: "90.00" } });
    fireEvent.change(screen.getByRole("textbox", { name: "פיצויים לאחר התחשבנות" }),
      { target: { value: "60.00" } });
    expect(savePensionProduct).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון נתונים" }));
    await waitFor(() => expect(savePensionProduct).toHaveBeenCalledWith(
      1, "p1", expect.objectContaining({
        expected_version: 1,
        product_name: "קרן פנסיה א",
        components: {
          "פיצויים_מעסיק_נוכחי": "90.00",
          "פיצויים_לאחר_התחשבנות": "60.00",
        },
      }),
    ));
    expect(savePensionProduct).toHaveBeenCalledTimes(1);
    expect(await within(region).findByText("90")).toBeInTheDocument();
  });

  it("does not claim success or discard a correction when the backend rejects the write", async () => {
    vi.mocked(savePensionProduct).mockRejectedValue(new Error("המוצר השתנה. יש לטעון מחדש לפני שמירה"));
    open();
    const region = await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(within(region).getByRole("button", { name: "פיצויים מעסיק נוכחי — קרן פנסיה א" }));
    fireEvent.click(screen.getByRole("button", { name: "תיקון יתרות נבחרות" }));
    fireEvent.change(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" }),
      { target: { value: "90.00" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון נתונים" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("המוצר השתנה");
    expect(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" })).toHaveValue("90.00");
    expect(within(region).getByText("100")).toBeInTheDocument();
  });

  it("does not write any balance or call conversions from scenario and results navigation", async () => {
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "4. תכנון תרחישים" }));
    expect(screen.getByText(/ההמרה הקנונית הקיימת ב־V2 מעדכנת יתרות אמת/))
      .toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "לוח עבודה לתרחישים — המחשת UX, ללא שמירה" })).toBeInTheDocument();
    expect(screen.getAllByText("טרם נוצרה")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "5. תוצאות והשוואה" }));
    expect(screen.getByText(/לא יוצגו מספרי קצבה/)).toBeInTheDocument();
    const comparison = screen.getByRole("region", { name: "מבנה השוואת חלופות ללא תוצאות" });
    expect(within(comparison).getAllByText("לא חושב")).toHaveLength(21);
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("keeps mock scenario decisions transient and never saves them to financial APIs", async () => {
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "4. תכנון תרחישים" }));
    fireEvent.click(screen.getByRole("button", { name: "צור חלופת הדמיה" }));
    expect(screen.getByRole("option", { name: "חלופת בדיקה 1" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /קרן פנסיה א — פיצויים מעסיק נוכחי/ })).toHaveValue("p1|פיצויים_מעסיק_נוכחי");
    fireEvent.change(screen.getByRole("combobox", { name: "רכיב כספי לדוגמה" }), {
      target: { value: "p1|פיצויים_מעסיק_נוכחי" },
    });
    fireEvent.click(screen.getByRole("button", { name: "הוסף החלטת הדמיה" }));
    expect(screen.getByRole("button", { name: "בטל החלטת הדמיה" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "שכפל חלופת הדמיה" }));
    expect(screen.getByRole("option", { name: "חלופת בדיקה 1 — העתק" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "בטל החלטת הדמיה" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "בטל החלטת הדמיה" }));
    expect(screen.queryByRole("button", { name: "בטל החלטת הדמיה" })).not.toBeInTheDocument();
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("keeps an unsaved correction open when a workflow stage is clicked", async () => {
    open();
    const ledger = await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(within(ledger).getByRole("button", { name: "פיצויים מעסיק נוכחי — קרן פנסיה א" }));
    fireEvent.click(screen.getByRole("button", { name: "תיקון יתרות נבחרות" }));
    fireEvent.change(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" }),
      { target: { value: "89.00" } });
    fireEvent.click(screen.getByRole("button", { name: "4. תכנון תרחישים" }));
    expect(screen.getByRole("alert")).toHaveTextContent("יש לשמור או לבטל");
    expect(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" })).toHaveValue("89.00");
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("rejects malformed monetary input before calling the factual write endpoint", async () => {
    open();
    const ledger = await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(within(ledger).getByRole("button", { name: "פיצויים מעסיק נוכחי — קרן פנסיה א" }));
    fireEvent.click(screen.getByRole("button", { name: "תיקון יתרות נבחרות" }));
    fireEvent.change(screen.getByRole("textbox", { name: "פיצויים מעסיק נוכחי" }),
      { target: { value: "-10" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון נתונים" }));
    expect(screen.getByRole("alert")).toHaveTextContent("לא שליליים");
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("rejects a previous client's late response and clears old data on route change", async () => {
    let resolveFirst!: (value: ClientDetailItem) => void;
    const first = new Promise<ClientDetailItem>(resolve => { resolveFirst = resolve; });
    vi.mocked(getClient).mockImplementation(id => id === 1 ? first : Promise.resolve(client(id)));
    open();
    fireEvent.click(screen.getByRole("button", { name: "עבור ללקוח ב" }));
    expect(await screen.findByText("קרן פנסיה ב")).toBeInTheDocument();
    await act(async () => { resolveFirst(client(1)); await first; });
    expect(screen.queryByText("קרן פנסיה א")).toBeNull();
    expect(screen.queryByText("לקוח א")).toBeNull();
    expect(screen.getByText("קרן פנסיה ב")).toBeInTheDocument();
  });
  it("shows read-only supplementary counts from actual scoped GET responses", async () => {
    vi.mocked(getEmploymentRecords).mockResolvedValue([{
      employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null,
    }]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    expect(await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("טוען נתונים משלימים...")).toBeNull());
    expect(screen.getByText("מעסיק")).toBeInTheDocument();
    expect(getEmploymentRecords).toHaveBeenCalledWith(1);
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("uses workspace employment editing and labels legacy grant fallback explicitly", async () => {
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (0)" });
    expect(screen.queryByRole("link", { name: "פתיחת עריכה: רשומות תעסוקה" })).not.toBeInTheDocument();
    expect(screen.getByText(/עריכת תקופות תעסוקה והתחשבנות מתבצעת כאן/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "פעולות מענקים נוספות בממשק הוותיק" }))
      .toHaveAttribute("href", "/clients/1/grants");
    const expected = [
      ["היוונים בפועל", "/clients/1/actual-capitalizations"],
      ["נכסי הון", "/clients/1/planning-input"],
      ["הכנסות נוספות", "/clients/1/planning-input"],
      ["הוצאות שוטפות", "/clients/1/planning-input"],
    ];
    for (const [label, destination] of expected) {
      expect(screen.getByRole("link", { name: "פתיחת עריכה: " + label }))
        .toHaveAttribute("href", destination);
    }
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("edits an existing employment record in the workspace using its accepted PUT API", async () => {
    const initial = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק קודם",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null };
    vi.mocked(getEmploymentRecords).mockResolvedValueOnce([initial])
      .mockResolvedValueOnce([{ ...initial, employer_name: "מעסיק מתוקן" }]);
    vi.mocked(updateEmploymentRecord).mockResolvedValue({ ...initial, employer_name: "מעסיק מתוקן" });
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByText("מעסיק קודם");
    fireEvent.click(screen.getByRole("button", { name: "תקן רשומת תעסוקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), {
      target: { value: "מעסיק מתוקן" },
    });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון תעסוקה" }));
    await screen.findByText("מעסיק מתוקן");
    expect(updateEmploymentRecord).toHaveBeenCalledWith(1, "e1", {
      employer_name: "מעסיק מתוקן", work_start_date: "2000-01-01",
      work_end_date: null, is_current: true, notes: null,
    });
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("rejects an employment end date before its start without a PUT", async () => {
    const initial = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2020-01-01", work_end_date: "2021-01-01", is_current: false, notes: null };
    vi.mocked(getEmploymentRecords).mockResolvedValue([initial]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByText("מעסיק");
    fireEvent.click(screen.getByRole("button", { name: "תקן רשומת תעסוקה" }));
    fireEvent.change(screen.getByLabelText("תאריך סיום"), { target: { value: "2019-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון תעסוקה" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("תאריך הסיום");
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("does not apply an old client's employment save after switching client", async () => {
    const initial = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null };
    vi.mocked(getEmploymentRecords).mockImplementation(id => Promise.resolve(id === 1 ? [initial] : []));
    let resolveSave!: (record: typeof initial) => void;
    const pendingSave = new Promise<typeof initial>(resolve => { resolveSave = resolve; });
    vi.mocked(updateEmploymentRecord).mockReturnValue(pendingSave);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByText("מעסיק");
    fireEvent.click(screen.getByRole("button", { name: "תקן רשומת תעסוקה" }));
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון תעסוקה" }));
    fireEvent.click(screen.getByRole("button", { name: "עבור ללקוח ב" }));
    await screen.findByText("קרן פנסיה ב");
    await act(async () => { resolveSave(initial); await pendingSave; });
    expect(screen.queryByText("מעסיק")).toBeNull();
    expect(getEmploymentRecords).toHaveBeenCalledTimes(1);
  });

  it("updates an existing historical grant through its authorized API only", async () => {
    const record = {
      grant_id: "g1", client_id: 1, employer_name: "מעסיק קודם",
      employer_withholding_file_number: "123456789", employment_start_date: "2000-01-01",
      employment_end_date: "2010-01-01", grant_receipt_date: "2010-02-01",
      exempt_grant_amount: "1000.00",
    };
    vi.mocked(getGrants).mockResolvedValueOnce([record])
      .mockResolvedValueOnce([{ ...record, exempt_grant_amount: "1200.00" }]);
    vi.mocked(updateGrant).mockResolvedValue({ ...record, exempt_grant_amount: "1200.00" });
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "מענקים (1)" });
    fireEvent.click(screen.getByRole("button", { name: "תקן מענק" }));
    fireEvent.change(screen.getByRole("textbox", { name: "סכום מענק פטור מדווח" }), {
      target: { value: "1200.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון מענק" }));
    await screen.findByText(/1200.00/);
    expect(updateGrant).toHaveBeenCalledWith(1, "g1", {
      employer_name: "מעסיק קודם", employer_withholding_file_number: "123456789",
      employment_start_date: "2000-01-01", employment_end_date: "2010-01-01",
      grant_receipt_date: "2010-02-01", exempt_grant_amount: "1200.00",
    });
    expect(savePensionProduct).not.toHaveBeenCalled();
  });

  it("rejects negative historical grant values without writing", async () => {
    const record = {
      grant_id: "g1", client_id: 1, employer_name: "מעסיק קודם",
      employer_withholding_file_number: "123456789", employment_start_date: "2000-01-01",
      employment_end_date: "2010-01-01", grant_receipt_date: "2010-02-01",
      exempt_grant_amount: "1000.00",
    };
    vi.mocked(getGrants).mockResolvedValue([record]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "מענקים (1)" });
    fireEvent.click(screen.getByRole("button", { name: "תקן מענק" }));
    fireEvent.change(screen.getByRole("textbox", { name: "סכום מענק פטור מדווח" }), {
      target: { value: "-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "שמור תיקון מענק" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("סכום מענק פטור");
    expect(updateGrant).not.toHaveBeenCalled();
  });

  it("keeps an unsaved supplementary employment edit when switching workflow stages", async () => {
    const record = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null };
    vi.mocked(getEmploymentRecords).mockResolvedValue([record]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByText("מעסיק");
    fireEvent.click(screen.getByRole("button", { name: "תקן רשומת תעסוקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), { target: { value: "עריכה שטרם נשמרה" } });
    fireEvent.click(screen.getByRole("button", { name: "4. תכנון תרחישים" }));
    expect(screen.getByRole("alert")).toHaveTextContent("יש לשמור או לבטל");
    expect(screen.getByRole("textbox", { name: "שם מעסיק" })).toHaveValue("עריכה שטרם נשמרה");
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("preserves an unsaved employment edit when another supplementary record is opened", async () => {
    vi.mocked(getEmploymentRecords).mockResolvedValue([
      { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק ראשון",
        work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null },
      { employment_record_id: "e2", client_id: 1, employer_name: "מעסיק שני",
        work_start_date: "2010-01-01", work_end_date: null, is_current: true, notes: null },
    ]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (2)" });
    fireEvent.click(screen.getAllByRole("button", { name: "תקן רשומת תעסוקה" })[0]);
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), { target: { value: "טיוטה שלא נשמרה" } });
    fireEvent.click(screen.getAllByRole("button", { name: "תקן רשומת תעסוקה" })[1]);
    expect(screen.getByRole("alert")).toHaveTextContent("יש לשמור או לבטל");
    expect(screen.getByRole("textbox", { name: "שם מעסיק" })).toHaveValue("טיוטה שלא נשמרה");
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("filters supplementary categories without changing stored facts", async () => {
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "מענקים (0)" });
    const filter = screen.getByRole("navigation", { name: "סינון נתונים משלימים" });
    fireEvent.click(within(filter).getByRole("button", { name: "מענקים (0)" }));
    expect(screen.getByRole("heading", { name: "מענקים (0)" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "רשומות תעסוקה (0)" })).toBeNull();
    fireEvent.click(within(filter).getByRole("button", { name: "כל הנתונים" }));
    expect(screen.getByRole("heading", { name: "רשומות תעסוקה (0)" })).toBeInTheDocument();
    expect(updateGrant).not.toHaveBeenCalled();
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("guards return to all supplementary data while an employment edit is open", async () => {
    vi.mocked(getEmploymentRecords).mockResolvedValue([{
      employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null,
    }]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" });
    const filters = screen.getByRole("navigation", { name: "סינון נתונים משלימים" });
    fireEvent.click(within(filters).getByRole("button", { name: "רשומות תעסוקה (1)" }));
    fireEvent.click(screen.getByRole("button", { name: "תקן רשומת תעסוקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), { target: { value: "טיוטה" } });
    fireEvent.click(within(filters).getByRole("button", { name: "כל הנתונים" }));
    expect(screen.getByRole("alert")).toHaveTextContent("יש לשמור או לבטל");
    expect(within(filters).getByRole("button", { name: "רשומות תעסוקה (1)" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox", { name: "שם מעסיק" })).toHaveValue("טיוטה");
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("marks populated and empty supplementary categories without writing facts", async () => {
    vi.mocked(getEmploymentRecords).mockResolvedValue([{
      employment_record_id: "e1", client_id: 1, employer_name: "מעסיק",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null,
    }]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" });
    expect(screen.getByRole("heading", { name: "רשומות תעסוקה (1)" }).closest("section")).toHaveClass("has-records");
    expect(screen.getByRole("heading", { name: "מענקים (0)" }).closest("section")).toHaveClass("is-empty");
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
    expect(updateGrant).not.toHaveBeenCalled();
  });

  it("creates a new employment record through the existing POST API and refetches", async () => {
    const created = { employment_record_id: "new-e", client_id: 1, employer_name: "מעסיק חדש",
      work_start_date: "2020-01-01", work_end_date: null, is_current: true, notes: null };
    vi.mocked(createEmploymentRecord).mockResolvedValue(created);
    vi.mocked(getEmploymentRecords).mockResolvedValueOnce([]).mockResolvedValueOnce([created]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (0)" });
    fireEvent.click(screen.getByRole("button", { name: "הוסף רשומת תעסוקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), { target: { value: "מעסיק חדש" } });
    fireEvent.change(screen.getByLabelText("תאריך תחילה"), { target: { value: "2020-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור רשומת תעסוקה חדשה" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" });
    expect(createEmploymentRecord).toHaveBeenCalledWith(1, {
      employer_name: "מעסיק חדש", work_start_date: "2020-01-01",
      work_end_date: null, is_current: true, notes: null,
    });
    expect(updateEmploymentRecord).not.toHaveBeenCalled();
  });

  it("creates a historical employment period and its recorded exempt grant in one request", async () => {
    const created = { employment_record_id: "historical-1", client_id: 1,
      employer_name: "מעסיק היסטורי", work_start_date: "2000-01-01",
      work_end_date: "2020-01-01", is_current: false, notes: null };
    const grant = { grant_id: "one-grant", client_id: 1, employment_record_id: "historical-1",
      employer_name: "מעסיק היסטורי", employer_withholding_file_number: "12345",
      employment_start_date: "2000-01-01", employment_end_date: "2020-01-01",
      grant_receipt_date: "2020-02-01", exempt_grant_amount: "1200" };
    vi.mocked(createHistoricalEmploymentSettlement).mockResolvedValue({
      employment_record_id: "historical-1", client_id: 1, exempt_grant_status: "recorded", grant_id: "one-grant",
    });
    vi.mocked(getEmploymentRecords).mockResolvedValueOnce([]).mockResolvedValueOnce([created]);
    vi.mocked(getGrants).mockResolvedValueOnce([]).mockResolvedValueOnce([grant]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (0)" });
    fireEvent.click(screen.getByRole("button", { name: "הוסף רשומת תעסוקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "שם מעסיק" }), { target: { value: "מעסיק היסטורי" } });
    fireEvent.change(screen.getByLabelText("תאריך תחילה"), { target: { value: "2000-01-01" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "מועסק כיום" }));
    fireEvent.change(screen.getByLabelText("תאריך סיום"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("מצב מענק הפיצויים הפטור"), { target: { value: "recorded" } });
    fireEvent.change(screen.getByRole("textbox", { name: "מספר תיק ניכויים" }), { target: { value: "12345" } });
    fireEvent.change(screen.getByLabelText("מועד קבלת מענק"), { target: { value: "2020-02-01" } });
    fireEvent.change(screen.getByRole("textbox", { name: "מענק פיצויים פטור מדווח" }), { target: { value: "1200" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור רשומת תעסוקה חדשה" }));
    await waitFor(() => expect(createHistoricalEmploymentSettlement).toHaveBeenCalledWith(1, {
      employment: { employer_name: "מעסיק היסטורי", work_start_date: "2000-01-01",
        work_end_date: "2020-01-01", is_current: false, notes: null },
      exempt_grant_status: "recorded", employer_withholding_file_number: "12345",
      grant_receipt_date: "2020-02-01", exempt_grant_amount: "1200",
    }));
    expect(createEmploymentRecord).not.toHaveBeenCalled();
  });

  it("creates a grant within its historical employment period atomically", async () => {
    const period = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק קודם",
      work_start_date: "2000-01-01", work_end_date: "2020-01-01", is_current: false, notes: null };
    const created = { grant_id: "new-grant", client_id: 1, employment_record_id: "e1",
      employer_name: "מעסיק קודם", employer_withholding_file_number: "123456789",
      employment_start_date: "2000-01-01", employment_end_date: "2020-01-01",
      grant_receipt_date: "2020-02-01", exempt_grant_amount: "1200.00" };
    vi.mocked(getEmploymentRecords).mockResolvedValue([period]);
    vi.mocked(createGrantForEmployment).mockResolvedValue(created);
    vi.mocked(getGrants).mockResolvedValueOnce([]).mockResolvedValueOnce([created]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" });
    fireEvent.click(screen.getByRole("button", { name: "הוסף מענק לתקופת העסקה" }));
    fireEvent.change(screen.getByRole("textbox", { name: "מספר תיק ניכויים" }), { target: { value: "123456789" } });
    fireEvent.change(screen.getByLabelText("מועד קבלת מענק"), { target: { value: "2020-02-01" } });
    fireEvent.change(screen.getByRole("textbox", { name: "סכום מענק פטור מדווח" }), { target: { value: "1200.00" } });
    fireEvent.click(screen.getByRole("button", { name: "שמור מענק חדש" }));
    await screen.findByText(/מענק משויך: מעסיק קודם/);
    expect(createGrantForEmployment).toHaveBeenCalledWith(1, "e1", {
      employer_name: "מעסיק קודם", employer_withholding_file_number: "123456789",
      employment_start_date: "2000-01-01", employment_end_date: "2020-01-01",
      grant_receipt_date: "2020-02-01", exempt_grant_amount: "1200.00",
    });
    expect(updateGrant).not.toHaveBeenCalled();
  });

  it("links a grant to its ended employment period only after explicit confirmation", async () => {
    const period = { employment_record_id: "e1", client_id: 1, employer_name: "מעסיק קודם",
      work_start_date: "2010-01-01", work_end_date: "2020-01-01", is_current: false, notes: null };
    const grant = { grant_id: "g1", client_id: 1, employment_record_id: null, employer_name: "מעסיק קודם",
      employer_withholding_file_number: "123", employment_start_date: "2010-01-01",
      employment_end_date: "2020-01-01", grant_receipt_date: "2020-01-15", exempt_grant_amount: "1000" };
    vi.mocked(getEmploymentRecords).mockResolvedValue([period]);
    vi.mocked(getGrants).mockResolvedValueOnce([grant]).mockResolvedValueOnce([{ ...grant, employment_record_id: "e1" }]);
    vi.mocked(linkGrantToEmployment).mockResolvedValue({ ...grant, employment_record_id: "e1" });
    const confirmation = vi.spyOn(window, "confirm").mockReturnValue(true);
    try {
      open();
      await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
      fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
      await screen.findByRole("heading", { name: "רשומות תעסוקה (1)" });
      fireEvent.click(screen.getByRole("button", { name: /שייך מענק לא מקושר/ }));
      await waitFor(() => expect(linkGrantToEmployment).toHaveBeenCalledWith(1, "g1", "e1"));
      await screen.findByText(/מענק משויך: מעסיק קודם/);
      expect(confirmation).toHaveBeenCalledOnce();
    } finally {
      confirmation.mockRestore();
    }
  });

  it("fails closed when supplementary API returns another client's record", async () => {
    vi.mocked(getEmploymentRecords).mockResolvedValue([{
      employment_record_id: "e2", client_id: 2, employer_name: "לא שייך",
      work_start_date: "2000-01-01", work_end_date: null, is_current: true, notes: null,
    }]);
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("אינם תואמים");
    expect(screen.queryByRole("heading", { name: /רשומות תעסוקה/ })).toBeNull();
  });

});
