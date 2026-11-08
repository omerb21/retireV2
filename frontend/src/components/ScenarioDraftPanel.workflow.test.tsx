import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioDraftPanel } from "./ScenarioDraftPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

const mocks = vi.hoisted(() => ({
  list: vi.fn(), preview: vi.fn(), create: vi.fn(), replace: vi.fn(), rename: vi.fn(), duplicate: vi.fn(),
  capability: vi.fn(),
}));
vi.mock("../api/scenarioDraftsApi", () => ({
  listScenarioDrafts: mocks.list,
  createScenarioDraft: mocks.create, duplicateScenarioDraft: mocks.duplicate,
  replaceScenarioDraft: mocks.replace, renameScenarioDraft: mocks.rename,
  archiveScenarioDraft: vi.fn(),
}));
vi.mock("../api/scenarioDraftPermissionApi", () => ({
  previewDraftDecision: mocks.preview,
}));
vi.mock("../api/scenarioStage6Api", () => ({
  readStage6GrossResultsCapability: mocks.capability,
}));
vi.mock("./ScenarioStage6Panel", () => ({
  ScenarioStage6Panel: () => <section aria-label="Stage 6 scenario result">Stage 6 enabled</section>,
}));
vi.mock("./ScenarioMonthlyComparisonPanel", () => ({
  ScenarioMonthlyComparisonPanel: () => <section aria-label="Stage 6 comparison">Comparison enabled</section>,
}));
vi.mock("./ScenarioSeverancePlanningPanel", () => ({
  ScenarioSeverancePlanningPanel: () => <section aria-label="Severance planning">Severance enabled</section>,
}));
mocks.capability.mockResolvedValue(false);
afterEach(() => { cleanup(); vi.resetAllMocks(); mocks.capability.mockResolvedValue(false); });

function draft(id: string, status: ScenarioDraft["status"] = "draft"): ScenarioDraft {
  return {
    scenario_id: id, client_id: 1, name: id, status, version: 2,
    created_by: "test", updated_by: "test", financial_validation: "not_evaluated",
    decisions: [{
      decision_id: "decision-" + id, source_product_id: "p1",
      source_component_id: "c1", component_code: "תגמולי_עובד_עד_2000",
      amount: "30.00", action: "pension", effective_date: "2026-10-24",
      validation_state: status === "needs_revalidation" ? "needs_revalidation" : "unverified",
      product_version_at_review: 1, source_fingerprint_at_review: "a".repeat(64),
      ruleset_digest_at_review: null, permission_preview_id_at_review: null,
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

it("shows Stage 6 only after an affirmative backend capability", async () => {
  mocks.list.mockResolvedValue([draft("approved")]);
  mocks.capability.mockResolvedValue(true);
  render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  expect(await screen.findByRole("region", { name: "Stage 6 scenario result" })).toBeTruthy();
  expect(screen.getByRole("region", { name: "Stage 6 comparison" })).toBeTruthy();
  expect(mocks.capability).toHaveBeenCalledWith(1, expect.any(AbortSignal));
});

it("revokes client A Stage 6 immediately while client B capability and drafts are pending", async () => {
  const pendingB = pending<boolean>();
  const pendingDraftsB = pending<ScenarioDraft[]>();
  mocks.capability.mockResolvedValueOnce(true).mockReturnValueOnce(pendingB.promise);
  mocks.list.mockImplementation((id: number) =>
    id === 1 ? Promise.resolve([draft("only-client-A")]) : pendingDraftsB.promise,
  );
  const view = render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  expect(await screen.findByRole("region", { name: "Stage 6 scenario result" })).toBeTruthy();
  expect(screen.getByRole("region", { name: "Stage 6 comparison" })).toBeTruthy();
  expect(screen.getByRole("button", { name: /only-client-A/ })).toBeTruthy();

  // B renders synchronously before its useEffect has cleared A's old approval.
  view.rerender(<ScenarioDraftPanel clientId={2} products={products} view="results" />);
  expect(screen.queryByRole("region", { name: "Stage 6 scenario result" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Stage 6 comparison" })).toBeNull();
  expect(screen.queryByRole("button", { name: /only-client-A/ })).toBeNull();
  await waitFor(() => expect(mocks.capability).toHaveBeenCalledWith(2, expect.any(AbortSignal)));

  // Even if B's draft list finishes first, Stage 6 must remain absent.
  pendingDraftsB.resolve([{ ...draft("only-client-B"), client_id: 2 }]);
  await screen.findByRole("button", { name: /only-client-B/ });
  expect(screen.queryByRole("region", { name: "Stage 6 scenario result" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Stage 6 comparison" })).toBeNull();
  pendingB.resolve(false);
  await waitFor(() => expect(screen.getByText("חישובי קצבה אינם מורשים בסביבה הזאת."))
    .toHaveTextContent("חישובי קצבה אינם מורשים בסביבה הזאת."));
  expect(screen.queryByRole("region", { name: "Stage 6 scenario result" })).toBeNull();
});

it("keeps Stage 6 hidden when capability is denied and drops a late prior-client approval", async () => {
  const oldClient = pending<boolean>();
  mocks.capability.mockReturnValueOnce(oldClient.promise).mockResolvedValueOnce(false);
  mocks.list.mockImplementation(async (clientId: number) => [{ ...draft("client-" + clientId), client_id: clientId }]);
  const view = render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  view.rerender(<ScenarioDraftPanel clientId={2} products={products} view="results" />);
  await waitFor(() => expect(mocks.capability).toHaveBeenCalledTimes(2));
  oldClient.resolve(true);
  await waitFor(() => expect(screen.getByText("חישובי קצבה אינם מורשים בסביבה הזאת."))
    .toHaveTextContent("חישובי קצבה אינם מורשים בסביבה הזאת."));
  expect(screen.queryByRole("region", { name: "Stage 6 scenario result" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Stage 6 comparison" })).toBeNull();
});

it("prefills the canonical component ID from the ledger selection without creating a second draft mechanism", async () => {
  mocks.list.mockResolvedValue([draft("saved")]);
  render(<ScenarioDraftPanel clientId={1} products={products}
    initialSource={{ productId: "p1", componentCode: "תגמולי_עובד_עד_2000" }} />);
  const chosen = await screen.findByRole("button", { name: "בחר יתרת תגמולי עובד עד 2000 בתוכנית Product" });
  await waitFor(() => expect(chosen.getAttribute("aria-pressed")).toBe("true"));
  expect(mocks.list).toHaveBeenCalledTimes(1);
});

it("uses one versioned saved-draft API for create, allocation, edit, clone and comparison", async () => {
  let revisions: ScenarioDraft[] = [];
  let counter = 0;
  const copy = (item: ScenarioDraft): ScenarioDraft => ({
    ...item, decisions: item.decisions.map(decision => ({ ...decision })),
  });
  mocks.list.mockImplementation(async () => revisions.map(copy));
  mocks.create.mockImplementation(async (clientId: number, name: string) => {
    const item = { ...draft("new-" + ++counter), client_id: clientId, name, version: 1, decisions: [] };
    revisions.push(item);
    return copy(item);
  });
  mocks.replace.mockImplementation(async (clientId: number, existing: ScenarioDraft, decisions: ScenarioDraft["decisions"]) => {
    expect(clientId).toBe(1);
    const index = revisions.findIndex(item => item.scenario_id === existing.scenario_id);
    expect(index).toBeGreaterThanOrEqual(0);
    expect(existing.version).toBe(revisions[index].version);
    revisions[index] = {
      ...revisions[index], version: existing.version + 1,
      decisions: decisions.map((item, position) => ({
        ...item, decision_id: item.decision_id ?? "added-" + position,
        validation_state: "unverified" as const,
      })),
    };
    return copy(revisions[index]);
  });
  mocks.duplicate.mockImplementation(async (_clientId: number, id: string, name: string) => {
    const original = revisions.find(item => item.scenario_id === id)!;
    const result = { ...copy(original), scenario_id: "clone-" + ++counter, name, version: 1 };
    revisions.push(result);
    return copy(result);
  });
  mocks.rename.mockImplementation(async (clientId: number, existing: ScenarioDraft, name: string) => {
    expect(clientId).toBe(1);
    const index = revisions.findIndex(item => item.scenario_id === existing.scenario_id);
    expect(index).toBeGreaterThanOrEqual(0);
    expect(existing.version).toBe(revisions[index].version);
    revisions[index] = { ...revisions[index], version: existing.version + 1, name };
    return copy(revisions[index]);
  });
  const view = render(<ScenarioDraftPanel clientId={1} products={products}
    initialSource={{ productId: "p1", componentCode: "תגמולי_עובד_עד_2000" }} />);
  fireEvent.change(screen.getByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "חלופה מקורית" } });
  fireEvent.click(screen.getByRole("button", { name: "צור ושמור חלופה" }));
  await screen.findByRole("button", { name: "חלופה מקורית" });
  fireEvent.click(screen.getByRole("button", { name: "בחר יתרת תגמולי עובד עד 2000 בתוכנית Product" }));
  fireEvent.change(screen.getByRole("textbox", { name: "סכום להמרה" }), { target: { value: "25.00" } });
  fireEvent.change(screen.getByLabelText("תאריך ביצוע מתוכנן"), { target: { value: "2026-10-26" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור המרה בחלופה" }));
  await waitFor(() => expect(revisions[0].decisions[0]?.amount).toBe("25.00"));
  fireEvent.click(await screen.findByRole("button", { name: "ערוך" }));
  expect(screen.queryByRole("combobox", { name: "רכיב מתוך התיק" })).toBeNull();
  fireEvent.change(screen.getByRole("textbox", { name: "סכום מתוכנן (₪)" }), { target: { value: "35.00" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור שינוי" }));
  await waitFor(() => expect(revisions[0].decisions[0]?.amount).toBe("35.00"));
  fireEvent.click(screen.getByText("ניהול חלופה: שינוי שם, שכפול וארכיון"));
  fireEvent.change(screen.getByRole("textbox", { name: "שינוי שם חלופה" }), { target: { value: "חלופה ששמה שונה" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור שם" }));
  await screen.findByRole("button", { name: "חלופה ששמה שונה" });
  expect(revisions[0].decisions[0].decision_id).toBe("added-0");
  fireEvent.click(await screen.findByRole("button", { name: "שכפל חלופה" }));
  await waitFor(() => expect(revisions).toHaveLength(2));
  expect(revisions[0].decisions[0].amount).toBe("35.00");
  // The cloned draft is selected after duplication; removing its decision
  // must preserve the original and survive a fresh server-backed reload.
  await screen.findByRole("button", { name: "חלופה ששמה שונה — העתק" });
  fireEvent.click(screen.getByRole("button", { name: "מחק המרה" }));
  await waitFor(() => expect(revisions[1].decisions).toHaveLength(0));
  expect(revisions[0].decisions).toHaveLength(1);
  expect(revisions[0].decisions[0].amount).toBe("35.00");
  expect(screen.getByRole("button", { name: "חלופה ששמה שונה" })).toBeTruthy();
  expect(mocks.create).toHaveBeenCalledTimes(1);
  expect(mocks.replace).toHaveBeenCalledTimes(3);
  expect(mocks.rename).toHaveBeenCalledTimes(1);
  expect(mocks.duplicate).toHaveBeenCalledTimes(1);
  view.unmount();
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  await screen.findByRole("button", { name: "חלופה ששמה שונה" });
  expect(await screen.findByRole("button", { name: "חלופה ששמה שונה — העתק" })).toBeTruthy();
});

it("keeps the selected alternative when moving from planning to results", async () => {
  mocks.list.mockResolvedValue([draft("alternative-a"), draft("alternative-b")]);
  const selected = vi.fn();
  const planning = render(<ScenarioDraftPanel clientId={1} products={products}
    onScenarioSelected={selected} />);
  fireEvent.click(await screen.findByRole("button", { name: "alternative-b" }));
  expect(selected).toHaveBeenCalledWith("alternative-b");
  planning.unmount();
  render(<ScenarioDraftPanel clientId={1} products={products}
    view="results" preferredScenarioId="alternative-b" />);
  expect(await screen.findByRole("heading", { name: "alternative-b" })).toBeInTheDocument();
});

it("never selects a stale alternative ID when the client changes", async () => {
  mocks.list.mockResolvedValue([{ ...draft("client-b-alternative"), client_id: 2 }]);
  render(<ScenarioDraftPanel clientId={2} products={products}
    view="results" preferredScenarioId="client-a-alternative" />);
  expect(await screen.findByRole("heading", { name: "client-b-alternative" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "client-a-alternative" })).toBeNull();
});

it("saves a whole-program conversion as one versioned draft replacement, keeping prior decisions", async () => {
  const prior = draft("batch-planning");
  mocks.list.mockResolvedValue([prior]);
  mocks.replace.mockResolvedValue(prior);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: "המר תוכנית Product" }));
  fireEvent.change(screen.getByLabelText("תאריך ביצוע מתוכנן"), {
    target: { value: "2028-01-15" },
  });
  fireEvent.click(screen.getByRole("button", { name: "שמור המרה בחלופה" }));
  await waitFor(() => expect(mocks.replace).toHaveBeenCalledOnce());
  const [id, expectedDraft, decisionBatch] = mocks.replace.mock.calls[0] as [
    number, ScenarioDraft, Array<{ decision_id?: string; amount: string; effective_date: string }>,
  ];
  expect(id).toBe(1);
  expect(expectedDraft.scenario_id).toBe("batch-planning");
  expect(decisionBatch).toHaveLength(2);
  expect(decisionBatch[0]).toEqual(expect.objectContaining({
    decision_id: "decision-batch-planning", amount: "30.00",
  }));
  expect(decisionBatch[1]).toEqual(expect.objectContaining({
    amount: "70.00", effective_date: "2028-01-15",
  }));
});

it("keeps professional diagnostics and authorization buttons out of routine scenario planning", async () => {
  mocks.list.mockResolvedValue([draft("clean-planning")]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  expect(await screen.findByRole("region", { name: "טבלת יתרות לתכנון המרות" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /בדוק הרשאת בסיס|בדוק מוכנות בסיס התיק/ })).toBeNull();
  expect(screen.queryByText("בדיקות מקצועיות ואבחון (לפי צורך)")).toBeNull();
  expect(screen.queryByText("יתרות מקורות ובדיקת הרשאות מפורטת")).toBeNull();
  expect(screen.queryByText("הזנת החלטה ידנית (אפשרות מתקדמת)")).toBeNull();
  expect(mocks.preview).not.toHaveBeenCalled();
});

it("keeps source-stale drafts noneditable without showing a permission workflow", async () => {
  mocks.list.mockResolvedValue([draft("stale", "needs_revalidation")]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  await screen.findByRole("button", { name: "stale" });
  expect((screen.getByRole("button", { name: "המר תוכנית Product" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByRole("button", { name: /בדוק הרשאת בסיס/ })).toBeNull();
  expect(mocks.replace).not.toHaveBeenCalled();
});

it("never displays a negative available balance for overallocated source decisions", async () => {
  const overallocated = draft("overallocated");
  overallocated.decisions[0].amount = "100.01";
  mocks.list.mockResolvedValue([overallocated]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const cell = await screen.findByRole("button", {
    name: "בחר יתרת תגמולי עובד עד 2000 בתוכנית Product",
  });
  expect((cell as HTMLButtonElement).disabled).toBe(true);
  expect(cell.textContent).not.toContain("-0.01");
});
