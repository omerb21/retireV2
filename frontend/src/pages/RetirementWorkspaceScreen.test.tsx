import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getClient, getEmploymentRecords, getGrants, getActualCapitalizations, getCapitalAssets, getRecurringIncomes, getRecurringExpenses, updateEmploymentRecord, type ClientDetailItem } from "../api/clientsApi";
import { listPensionProducts, savePensionProduct, type PensionProduct } from "../api/pensionProductsApi";
import { RetirementWorkspaceScreen } from "./RetirementWorkspaceScreen";

vi.mock("../api/clientsApi", () => ({
  getClient: vi.fn(),
  getEmploymentRecords: vi.fn(), getGrants: vi.fn(), getActualCapitalizations: vi.fn(),
  getCapitalAssets: vi.fn(), getRecurringIncomes: vi.fn(), getRecurringExpenses: vi.fn(), updateEmploymentRecord: vi.fn(),
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
    fireEvent.click(screen.getByRole("button", { name: "5. תוצאות והשוואה" }));
    expect(screen.getByText(/לא יוצגו מספרי קצבה/)).toBeInTheDocument();
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

  it("routes each supplementary category to its existing factual editor", async () => {
    open();
    await screen.findByRole("region", { name: "טבלת רכיבים נגללת" });
    fireEvent.click(screen.getByRole("button", { name: "3. נתונים משלימים" }));
    const expected = [
      ["רשומות תעסוקה", "/clients/1/employment-history"],
      ["מענקים", "/clients/1/grants"],
      ["היוונים בפועל", "/clients/1/actual-capitalizations"],
      ["נכסי הון", "/clients/1/planning-input"],
      ["הכנסות נוספות", "/clients/1/planning-input"],
      ["הוצאות שוטפות", "/clients/1/planning-input"],
    ];
    await screen.findByRole("heading", { name: "רשומות תעסוקה (0)" });
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
