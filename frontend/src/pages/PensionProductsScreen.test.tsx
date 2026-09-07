import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/pensionProductsApi";
import { PensionProductsScreen } from "./PensionProductsScreen";

vi.mock("../api/pensionProductsApi", () => ({ listPensionProducts: vi.fn(), createPensionProduct: vi.fn(), savePensionProduct: vi.fn(), importPensionProducts: vi.fn(), deletePensionProduct: vi.fn() }));
const codes = ["פיצויים_מעסיק_נוכחי", "פיצויים_לאחר_התחשבנות", "פיצויים_שלא_עברו_התחשבנות", "פיצויים_ממעסיקים_קודמים_רצף_זכויות", "פיצויים_ממעסיקים_קודמים_רצף_קצבה", "תגמולי_עובד_עד_2000", "תגמולי_עובד_אחרי_2000", "תגמולי_עובד_אחרי_2008_לא_משלמת", "תגמולי_מעביד_עד_2000", "תגמולי_מעביד_אחרי_2000", "תגמולי_מעביד_אחרי_2008_לא_משלמת"];
const product = (): api.PensionProduct => ({ product_id: "p1", client_id: 1, version: 1, source_kind: "manual", product_name: "תכנית א", product_type: "קופת גמל", provider_name: "גוף מנהל", provider_identifier: null, account_reference: "123", start_date: "2000-02-01", statement_date: "2026-09-01", historical_employers: [], reported_product_total: "123.45", reported_rewards_total: null, reported_severance_total: null, components: Object.fromEntries(codes.map(code => [code, "0.00"])), reconciliation: { rewards_component_sum: "0.00", severance_component_sum: "0.00", product_component_sum: "0.00", rewards_discrepancy: null, severance_discrepancy: null, product_discrepancy: "123.45" }, updated_at: "2026-09-01T10:00:00Z" });
function open(path = "/clients/1/pension-products") {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/clients/:clientId/pension-products" element={<PensionProductsScreen />} /></Routes></MemoryRouter>);
}
beforeEach(() => { vi.resetAllMocks(); vi.mocked(api.listPensionProducts).mockResolvedValue([product()]); });

describe("מוצרים פנסיוניים קנוניים", () => {
  it("opens directly and displays all eleven components with Hebrew names and Israeli dates", async () => {
    const { container } = open();
    const editor = await screen.findByRole("region", { name: "עריכת תכנית א" });
    for (const code of codes) expect(within(editor).getByLabelText(code.replace(/_/g, " "))).toHaveValue("0.00");
    expect(within(editor).getByLabelText("תאריך התחלה")).toHaveValue("01/02/2000");
    expect(within(editor).getByLabelText("תאריך נכונות היתרה")).toHaveValue("01/09/2026");
    expect(container.querySelector('input[type="date"]')).toBeNull();
    expect(container.querySelector('section[dir="rtl"]')).not.toBeNull();
    expect(api.listPensionProducts).toHaveBeenCalledWith(1);
    expect(screen.queryByText(/M0[1-5]/)).toBeNull();
  });

  it("edits decimal strings only on explicit save without an approval step", async () => {
    const saved = { ...product(), version: 2, components: { ...product().components, [codes[0]]: "99.99" } };
    vi.mocked(api.savePensionProduct).mockResolvedValue(saved);
    open();
    const editor = await screen.findByRole("region", { name: "עריכת תכנית א" });
    fireEvent.change(within(editor).getByLabelText("פיצויים מעסיק נוכחי"), { target: { value: "99.99" } });
    expect(api.savePensionProduct).not.toHaveBeenCalled();
    fireEvent.click(within(editor).getByRole("button", { name: "שמירת מוצר" }));
    await waitFor(() => expect(api.savePensionProduct).toHaveBeenCalledWith(1, "p1", expect.objectContaining({ expected_version: 1, components: expect.objectContaining({ [codes[0]]: "99.99" }) })));
    expect(await screen.findByRole("status")).toHaveTextContent("המוצר נשמר");
  });

  it("keeps stale edits visible and reports failed save in Hebrew", async () => {
    vi.mocked(api.savePensionProduct).mockRejectedValue(new Error("המוצר השתנה. יש לטעון מחדש לפני שמירה"));
    open();
    fireEvent.click(await screen.findByRole("button", { name: "שמירת מוצר" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("המוצר השתנה");
    expect(screen.queryByText("המוצר נשמר")).toBeNull();
  });

  it("requires confirmation before deleting with the exact current version", async () => {
    vi.mocked(api.deletePensionProduct).mockResolvedValue(undefined);
    open();
    fireEvent.click(await screen.findByRole("button", { name: "מחיקת מוצר" }));
    expect(api.deletePensionProduct).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "אישור מחיקה" }));
    await waitFor(() => expect(api.deletePensionProduct).toHaveBeenCalledWith(1, "p1", 1));
    expect(await screen.findByText(/אין מוצרים פנסיוניים/)).toBeInTheDocument();
  });

  it("creates a manual product without sending inferred components", async () => {
    vi.mocked(api.listPensionProducts).mockResolvedValue([]);
    vi.mocked(api.createPensionProduct).mockResolvedValue(product());
    open();
    await screen.findByText(/אין מוצרים פנסיוניים/);
    fireEvent.click(screen.getByText("יצירת מוצר ידנית"));
    fireEvent.change(screen.getByLabelText("שם התכנית"), { target: { value: "תכנית א" } });
    fireEvent.click(screen.getByRole("button", { name: "יצירת מוצר" }));
    await waitFor(() => expect(api.createPensionProduct).toHaveBeenCalledWith(1, expect.objectContaining({ product_name: "תכנית א", reported_product_total: "0.00", reported_rewards_total: null })));
    expect(vi.mocked(api.createPensionProduct).mock.calls[0][1]).not.toHaveProperty("components");
  });

  it("imports directly into the table", async () => {
    vi.mocked(api.listPensionProducts).mockResolvedValue([]);
    vi.mocked(api.importPensionProducts).mockResolvedValue([product()]);
    open();
    await screen.findByText(/אין מוצרים פנסיוניים/);
    const file = new File(["<Root />"], "source.xml", { type: "application/xml" });
    fireEvent.change(screen.getByLabelText("קובץ מקור"), { target: { files: [file] } });
    // jsdom's synthetic files assignment does not populate the native file
    // input value used by browser constraint validation. Submit the form.
    fireEvent.submit(screen.getByRole("button", { name: "ייבוא מוצרים" }).closest("form")!);
    expect(await screen.findByRole("region", { name: "עריכת תכנית א" })).toBeInTheDocument();
    expect(api.importPensionProducts).toHaveBeenCalledWith(1, file);
  });

  it("rejects malformed client routes without sending a request", () => {
    open("/clients/1x/pension-products");
    expect(screen.getByRole("alert")).toHaveTextContent("מזהה הלקוח אינו תקין");
    expect(api.listPensionProducts).not.toHaveBeenCalled();
  });
});
