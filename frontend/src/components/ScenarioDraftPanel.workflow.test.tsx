import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioDraftPanel } from "./ScenarioDraftPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

const mocks = vi.hoisted(() => ({
  list: vi.fn(), preview: vi.fn(),
}));
vi.mock("../api/scenarioDraftsApi", () => ({
  listScenarioDrafts: mocks.list,
  createScenarioDraft: vi.fn(), duplicateScenarioDraft: vi.fn(),
  replaceScenarioDraft: vi.fn(), archiveScenarioDraft: vi.fn(),
}));
vi.mock("../api/scenarioDraftPermissionApi", () => ({
  previewDraftDecision: mocks.preview,
}));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function draft(id: string, status: ScenarioDraft["status"] = "draft"): ScenarioDraft {
  return {
    scenario_id: id, client_id: 1, name: id, status, version: 2,
    created_by: "test", updated_by: "test", financial_validation: "not_evaluated",
    decisions: [{
      decision_id: "decision-" + id, source_product_id: "p1",
      source_component_id: "c1", component_code: "תגמולי_עובד_עד_2000",
      amount: "30.00", action: "pension", effective_date: "2026-10-24",
      validation_state: status === "needs_revalidation" ? "needs_revalidation" : "unverified",
    }],
  };
}
const products = [{
  product_id: "p1", product_name: "Product", version: 1,
  conversion_components: [{ component_id: "c1", component_code: "תגמולי_עובד_עד_2000", balance: "100.00" }],
}] as unknown as PensionProduct[];
const allowed = { preview_product_version: 1, component_id: "c1", component_code: "תגמולי_עובד_עד_2000",
  balance: "100.00", permission_status: "allowed", reason_code: "BASE_PERMISSION_ALLOWED", reason_he: "מותר" };
function pending<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}

it("discards a late allowed preview after switching to another saved scenario", async () => {
  mocks.list.mockResolvedValue([draft("a"), draft("b")]);
  const deferred = pending<typeof allowed>();
  mocks.preview.mockReturnValue(deferred.promise);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק הרשאת בסיס/ }));
  fireEvent.click(screen.getByRole("button", { name: /b — גרסה/ }));
  deferred.resolve(allowed);
  await waitFor(() => expect(mocks.preview).toHaveBeenCalledTimes(1));
  expect(screen.queryByText("מותר לפי מטריצת בסיס בלבד")).toBeNull();
  expect(screen.getByText(/b — גרסה/)).toBeTruthy();
});
it("does not offer a permission check for a source-stale decision", async () => {
  mocks.list.mockResolvedValue([draft("stale", "needs_revalidation")]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const button = await screen.findByRole("button", { name: /בדוק הרשאת בסיס/ });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  expect(mocks.preview).not.toHaveBeenCalled();
});
it("renders blocked permission even when the product-level preview is mixed", async () => {
  mocks.list.mockResolvedValue([draft("allowed-view")]);
  mocks.preview.mockResolvedValue({ ...allowed, permission_status: "blocked" });
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק הרשאת בסיס/ }));
  await screen.findByText(/חסום לפי מטריצת בסיס/);
  expect(screen.queryByText("מותר לפי מטריצת בסיס בלבד")).toBeNull();
});

it("expires a displayed allowed preview when the canonical source snapshot changes", async () => {
  mocks.list.mockResolvedValue([draft("source-update")]);
  mocks.preview.mockResolvedValue(allowed);
  const view = render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק הרשאת בסיס/ }));
  await screen.findByText(/מותר לפי מטריצת בסיס בלבד/);
  const changed = products.map(product => ({
    ...product, version: product.version + 1,
    conversion_components: product.conversion_components?.map(component => ({
      ...component, balance: "101.00",
    })),
  }));
  view.rerender(<ScenarioDraftPanel clientId={1} products={changed} />);
  await waitFor(() => expect(screen.queryByText("מותר לפי מטריצת בסיס בלבד")).toBeNull());
  expect(screen.getByText(/טרם נבדקה/)).toBeTruthy();
});

it("rejects a late allowed result when product classification changes without version bump", async () => {
  mocks.list.mockResolvedValue([draft("classification")]);
  const deferred = pending<typeof allowed>();
  mocks.preview.mockReturnValue(deferred.promise);
  const view = render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק הרשאת בסיס/ }));
  const changed = products.map(product => ({ ...product, product_type: "קופת גמל" }));
  view.rerender(<ScenarioDraftPanel clientId={1} products={changed} />);
  deferred.resolve(allowed);
  await waitFor(() => expect(mocks.preview).toHaveBeenCalledTimes(1));
  expect(screen.queryByText("מותר לפי מטריצת בסיס בלבד")).toBeNull();
});

it("shows a read-only side-by-side summary for distinct saved scenarios", async () => {
  const first = draft("comparison-a");
  const second = draft("comparison-b");
  second.decisions[0].amount = "70.00";
  mocks.list.mockResolvedValue([first, second]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const table = await screen.findByRole("table");
  expect(table.textContent).toContain("comparison-a");
  expect(table.textContent).toContain("comparison-b");
  expect(table.textContent).toContain("30.00");
  expect(table.textContent).toContain("70.00");
  expect(table.textContent).toContain("מקצועי: זכאות, מס והרשאת ביצוע — לא נבדקו");
});

it("opens the selected scenario from comparison without altering saved data", async () => {
  mocks.list.mockResolvedValue([draft("compare-one"), draft("compare-two")]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const comparison = await screen.findByRole("region", { name: "השוואת חלופות טיוטה" });
  const buttons = Array.from(comparison.querySelectorAll("button"));
  expect(buttons).toHaveLength(2);
  fireEvent.click(buttons[1]);
  expect(screen.getByRole("heading", { name: "compare-two" })).toBeTruthy();
  expect(buttons[1].getAttribute("aria-current")).toBe("true");
  expect(mocks.list).toHaveBeenCalledTimes(1);
});
