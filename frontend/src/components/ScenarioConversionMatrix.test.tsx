import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PensionProduct } from "../api/pensionProductsApi";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import { PORTFOLIO_COMPONENT_COLUMNS } from "./portfolioComponentColumns";
import { ScenarioConversionMatrix } from "./ScenarioConversionMatrix";

const first = PORTFOLIO_COMPONENT_COLUMNS[0][0];
const second = PORTFOLIO_COMPONENT_COLUMNS[6][0];

const product = (id: string, name: string, balances: Record<string, string>): PensionProduct => ({
  product_id: id, product_name: name, product_type: "קרן פנסיה",
  client_id: 1, source_kind: "manual", version: 1,
  provider_name: "גוף בדיקה", provider_identifier: null, account_reference: "99",
  start_date: "2010-01-01", statement_date: "2026-10-31", historical_employers: [],
  reported_product_total: "300.00", reported_rewards_total: "200.00",
  reported_severance_total: "100.00", components: balances, updated_at: "",
  reconciliation: { product_discrepancy: "0.00" },
  conversion_components: Object.entries(balances).map(([code, balance]) => ({
    component_id: `${id}:${code}`, component_code: code, balance, allowed_destinations: {},
  })),
});
const scenario: ScenarioDraft = {
  scenario_id: "s1", client_id: 1, version: 2, name: "תרחיש בדיקה",
  status: "draft", created_by: "test", updated_by: "test",
  financial_validation: "not_evaluated", decisions: [],
};
afterEach(cleanup);

it("shows the complete portfolio grid with one button per component and effective date", async () => {
  const onApply = vi.fn().mockResolvedValue(true);
  const p = product("p1", "Program A", { [second]: "200.00" });
  render(<ScenarioConversionMatrix products={[p]} scenario={scenario}
    disabled={false} busy={false} onApply={onApply} />);
  expect(screen.getByRole("region", { name: "טבלת יתרות לתכנון המרות" })).toBeTruthy();
  expect(screen.getAllByRole("columnheader")).toHaveLength(15);
  fireEvent.click(screen.getByRole("button", { name: `בחר יתרת ${PORTFOLIO_COMPONENT_COLUMNS[6][1]} בתוכנית Program A` }));
  fireEvent.change(screen.getByLabelText("סכום להמרה"), { target: { value: "75.50" } });
  fireEvent.change(screen.getByLabelText("תאריך ביצוע מתוכנן"), { target: { value: "2028-05-01" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור המרה בחלופה" }));
  await waitFor(() => expect(onApply).toHaveBeenCalledOnce());
  expect(onApply).toHaveBeenCalledWith([expect.objectContaining({
    amount: "75.50", effective_date: "2028-05-01", action: "pension",
    source_product_id: "p1", component_code: second,
  })]);
  expect(p.components[second]).toBe("200.00");
});

it("saves an entire program with multiple components in one atomic draft call", async () => {
  const onApply = vi.fn().mockResolvedValue(true);
  const p = product("p1", "Program A", { [first]: "100.00", [second]: "200.00" });
  render(<ScenarioConversionMatrix products={[p]} scenario={scenario}
    disabled={false} busy={false} onApply={onApply} />);
  fireEvent.click(screen.getByRole("button", { name: "המר תוכנית Program A" }));
  fireEvent.change(screen.getByLabelText("יעד ההמרה"), { target: { value: "capital_asset" } });
  fireEvent.change(screen.getByLabelText("תאריך ביצוע מתוכנן"), { target: { value: "2029-01-01" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור 2 המרות בחלופה" }));
  await waitFor(() => expect(onApply).toHaveBeenCalledOnce());
  expect(onApply.mock.calls[0][0]).toEqual([
    expect.objectContaining({ amount: "100.00", action: "capital_asset", effective_date: "2029-01-01" }),
    expect.objectContaining({ amount: "200.00", action: "capital_asset", effective_date: "2029-01-01" }),
  ]);
});

it("saves an entire column spanning two distinct programs", async () => {
  const onApply = vi.fn().mockResolvedValue(true);
  render(<ScenarioConversionMatrix products={[
    product("p1", "Program A", { [second]: "180.00" }),
    product("p2", "Program B", { [second]: "90.00" }),
  ]} scenario={scenario} disabled={false} busy={false} onApply={onApply} />);
  fireEvent.click(screen.getByRole("button", { name: `המר טור ${PORTFOLIO_COMPONENT_COLUMNS[6][1]}` }));
  fireEvent.change(screen.getByLabelText("תאריך ביצוע מתוכנן"), { target: { value: "2030-04-02" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור 2 המרות בחלופה" }));
  await waitFor(() => expect(onApply).toHaveBeenCalledOnce());
  expect(onApply.mock.calls[0][0].map((row: { source_product_id: string }) => row.source_product_id))
    .toEqual(["p1", "p2"]);
});

it("blocks whole-program conversion if any positive component has no valid source ID", () => {
  const onApply = vi.fn().mockResolvedValue(true);
  const p = product("p1", "Program A", { [first]: "100.00", [second]: "200.00" });
  p.conversion_components = p.conversion_components!.filter(c => c.component_code !== second);
  render(<ScenarioConversionMatrix products={[p]} scenario={scenario}
    disabled={false} busy={false} onApply={onApply} />);
  fireEvent.click(screen.getByRole("button", { name: "המר תוכנית Program A" }));
  expect(screen.getByRole("alert").textContent).toContain("חסרה מיפוי");
  expect(onApply).not.toHaveBeenCalled();
});

it("never enables a conversion action for archived drafts", () => {
  const p = product("p1", "Program A", { [first]: "100.00" });
  render(<ScenarioConversionMatrix products={[p]} scenario={{ ...scenario, status: "archived" }}
    disabled busy={false} onApply={vi.fn()} />);
  expect((screen.getByRole("button", { name: "המר תוכנית Program A" }) as HTMLButtonElement).disabled).toBe(true);
});
