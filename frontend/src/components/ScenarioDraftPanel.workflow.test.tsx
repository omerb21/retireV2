import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioDraftPanel } from "./ScenarioDraftPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

const mocks = vi.hoisted(() => ({
  list: vi.fn(), preview: vi.fn(), create: vi.fn(), replace: vi.fn(), rename: vi.fn(), duplicate: vi.fn(),
  capability: vi.fn(), admission: vi.fn(),
}));
vi.mock("../api/scenarioDraftsApi", () => ({
  listScenarioDrafts: mocks.list,
  createScenarioDraft: mocks.create, duplicateScenarioDraft: mocks.duplicate,
  replaceScenarioDraft: mocks.replace, renameScenarioDraft: mocks.rename,
  archiveScenarioDraft: vi.fn(), readCalculationAdmission: mocks.admission,
}));
vi.mock("../api/scenarioDraftPermissionApi", () => ({
  previewDraftDecision: mocks.preview,
}));
vi.mock("../api/scenarioStage6Api", () => ({
  readStage6GrossResultsCapability: mocks.capability,
}));
vi.mock("./M11PreferredScenarioPanel", () => ({
  M11PreferredScenarioPanel: () => <section aria-label="M11 selection">M11</section>,
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
vi.mock("./ScenarioFixationProfessionalReviewPanel", () => ({
  ScenarioFixationProfessionalReviewPanel: () => (
    <section aria-label="Fixation professional review">הכרעות מקצועיות לקיבוע זכויות</section>
  ),
}));
mocks.capability.mockResolvedValue(false);
mocks.admission.mockImplementation(async (clientId: number, scenarioId: string) => ({
  schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: clientId,
  scenario_id: scenarioId, scenario_version: 2, assessment_state: "blocked",
  financial_result: null, blockers: [{ code: "PERMISSION_NOT_ADMITTED", decision_id: null }],
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); mocks.capability.mockResolvedValue(false);
  mocks.admission.mockImplementation(async (clientId: number, scenarioId: string) => ({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: clientId,
    scenario_id: scenarioId, scenario_version: 2, assessment_state: "blocked",
    financial_result: null, blockers: [{ code: "PERMISSION_NOT_ADMITTED", decision_id: null }],
  }));
});

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
  balance: "100.00", permission_status: "allowed", reason_code: "BASE_PERMISSION_ALLOWED", reason_he: "מותר",
  source_fingerprint: "a".repeat(64), ruleset_digest: "b".repeat(64) };
function pending<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}

it("registers edited scenario name and decision amounts as unsaved until cancelled", async () => {
  mocks.list.mockResolvedValue([draft("editable")]);
  const onDirtyChange = vi.fn();
  render(<ScenarioDraftPanel clientId={1} products={products} onDirtyChange={onDirtyChange} />);
  await screen.findByRole("button", { name: "editable" });
  fireEvent.change(screen.getByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "unsaved" } });
  expect(onDirtyChange).toHaveBeenLastCalledWith(true);
  fireEvent.change(screen.getByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "" } });
  expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  fireEvent.click(screen.getByRole("button", { name: "ערוך" }));
  fireEvent.change(screen.getByRole("textbox", { name: "סכום מתוכנן (₪)" }), { target: { value: "25.00" } });
  expect(onDirtyChange).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "בטל עריכה" }));
  expect(onDirtyChange).toHaveBeenLastCalledWith(false);
});

it("creates once and selects the saved server ID after a successful refresh", async () => {
  const saved = { ...draft("created-once"), name: "New plan", decisions: [] };
  mocks.list.mockResolvedValueOnce([]).mockResolvedValueOnce([saved]);
  mocks.create.mockResolvedValue(saved);
  const selected = vi.fn();
  render(<ScenarioDraftPanel clientId={1} products={products} onScenarioSelected={selected} />);
  await screen.findByRole("textbox", { name: "שם חלופה חדשה" });
  fireEvent.change(screen.getByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "New plan" } });
  fireEvent.click(screen.getByRole("button", { name: "צור ושמור חלופה" }));
  await waitFor(() => expect(mocks.list).toHaveBeenCalledTimes(2));
  expect(mocks.create).toHaveBeenCalledTimes(1);
  expect(mocks.create).toHaveBeenCalledWith(1, "New plan");
  expect(selected).toHaveBeenCalledWith("created-once");
  expect(screen.queryByRole("button", { name: "נסה לרענן חלופות" })).toBeNull();
});

it("does not claim success or retry when the creation POST fails", async () => {
  mocks.list.mockResolvedValue([]);
  mocks.create.mockRejectedValue(Error("POST failed"));
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.change(await screen.findByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "New plan" } });
  fireEvent.click(screen.getByRole("button", { name: "צור ושמור חלופה" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("POST failed");
  expect(mocks.create).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("button", { name: "נסה לרענן חלופות" })).toBeNull();
});

it("preserves a successful POST and retries only GET after refresh failure", async () => {
  const saved = { ...draft("saved-after-get-failure"), name: "New plan", decisions: [] };
  mocks.list.mockResolvedValueOnce([]).mockRejectedValueOnce(Error("GET failed"))
    .mockResolvedValueOnce([saved]);
  mocks.create.mockResolvedValue(saved);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.change(await screen.findByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "New plan" } });
  fireEvent.click(screen.getByRole("button", { name: "צור ושמור חלופה" }));
  const retry = await screen.findByRole("button", { name: "נסה לרענן חלופות" });
  expect(retry.parentElement).toHaveTextContent("saved-after-get-failure");
  expect(retry.parentElement).toHaveTextContent("GET failed");
  expect(screen.queryByRole("alert")).toBeNull();
  expect(mocks.create).toHaveBeenCalledTimes(1);
  fireEvent.click(retry);
  await waitFor(() => expect(screen.queryByRole("button", { name: "נסה לרענן חלופות" })).toBeNull());
  expect(mocks.list).toHaveBeenCalledTimes(3);
  expect(mocks.create).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "New plan" })).toHaveAttribute("aria-pressed", "true");
});

it("does not display a late client A creation on client B", async () => {
  const late = pending<ScenarioDraft>();
  mocks.list.mockImplementation(async (id: number) => id === 1 ? [] : [{ ...draft("client-B"), client_id: 2 }]);
  mocks.create.mockReturnValue(late.promise);
  const view = render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.change(await screen.findByRole("textbox", { name: "שם חלופה חדשה" }), { target: { value: "Client A plan" } });
  fireEvent.click(screen.getByRole("button", { name: "צור ושמור חלופה" }));
  await waitFor(() => expect(mocks.create).toHaveBeenCalledTimes(1));
  view.rerender(<ScenarioDraftPanel clientId={2} products={products} />);
  await screen.findByRole("button", { name: "client-B" });
  late.resolve({ ...draft("client-A"), name: "Client A plan" });
  await waitFor(() => expect(screen.queryByRole("button", { name: "Client A plan" })).toBeNull());
  expect(screen.queryByRole("button", { name: "נסה לרענן חלופות" })).toBeNull();
  expect(mocks.list).toHaveBeenCalledTimes(2);
});

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

it("uses one workspace-selected scenario when the parent changes A to B", async () => {
  mocks.list.mockResolvedValue([draft("alternative-a"), draft("alternative-b")]);
  const props = { clientId: 1, products, view: "results" as const };
  const view = render(<ScenarioDraftPanel {...props} preferredScenarioId="alternative-a" />);
  expect(await screen.findByRole("heading", { name: "alternative-a" })).toBeInTheDocument();
  view.rerender(<ScenarioDraftPanel {...props} preferredScenarioId="alternative-b" />);
  expect(await screen.findByRole("heading", { name: "alternative-b" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "alternative-a" })).toBeNull();
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

it("inspects saved decision source evidence without professional approval or any write", async () => {
  mocks.list.mockResolvedValue([draft("evidence")]);
  mocks.preview.mockResolvedValue({ ...allowed, permission_status: "blocked",
    reason_code: "DEPENDENCY_MISSING", reason_he: "חסרה אסמכתה" });
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const evidence = await screen.findByRole("region", { name: "ראיות החלטה decision-evidence" });
  expect(evidence).toHaveTextContent("UNKNOWN");
  fireEvent.click(screen.getByRole("button", { name: /בדוק ראיות להרשאת רכיב/ }));
  await waitFor(() => expect(evidence).toHaveTextContent("DEPENDENCY_MISSING"));
  expect(evidence).toHaveTextContent("חסרה אסמכתה");
  expect(evidence).toHaveTextContent("החסימה מתייחסת להחלטה זו");
  expect(evidence).toHaveTextContent("אישור כשירות מקצועית: לא זמין");
  expect(mocks.preview).toHaveBeenCalledWith(1, expect.objectContaining({ decision_id: "decision-evidence" }), expect.any(AbortSignal));
  expect(mocks.replace).not.toHaveBeenCalled();
});

it("reports changed source version as UNKNOWN even when permission says allowed", async () => {
  mocks.list.mockResolvedValue([draft("version-change")]);
  mocks.preview.mockResolvedValue({ ...allowed, preview_product_version: 2 });
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק ראיות להרשאת רכיב/ }));
  const evidence = screen.getByRole("region", { name: "ראיות החלטה decision-version-change" });
  await waitFor(() => expect(evidence).toHaveTextContent("UNKNOWN (המקור או גרסת הכללים"));
  expect(evidence).not.toHaveTextContent("אישור כשירות מקצועית: מאושר");
});

it("fails closed for unavailable/ambiguous source evidence and source revalidation", async () => {
  mocks.list.mockResolvedValue([draft("unknown", "needs_revalidation")]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const button = await screen.findByRole("button", { name: /בדוק ראיות להרשאת רכיב/ });
  fireEvent.click(button);
  const evidence = screen.getByRole("region", { name: "ראיות החלטה decision-unknown" });
  await waitFor(() => expect(evidence).toHaveTextContent("UNKNOWN: גרסת התרחיש או ראיית המקור השתנו"));
  expect(mocks.preview).not.toHaveBeenCalled();
  expect(mocks.replace).not.toHaveBeenCalled();
});

it("treats ambiguous product type from authoritative preview as UNKNOWN", async () => {
  mocks.list.mockResolvedValue([draft("ambiguous")]);
  mocks.preview.mockRejectedValue(new Error("UNKNOWN_PRODUCT_TYPE"));
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק ראיות להרשאת רכיב/ }));
  const evidence = screen.getByRole("region", { name: "ראיות החלטה decision-ambiguous" });
  await waitFor(() => expect(evidence).toHaveTextContent("UNKNOWN: UNKNOWN_PRODUCT_TYPE"));
});

it("rejects a source fingerprint change detected by fresh server reconciliation", async () => {
  const initial = draft("source-fingerprint");
  const changed = draft("source-fingerprint");
  changed.decisions[0].validation_state = "needs_revalidation";
  mocks.list.mockResolvedValueOnce([initial]).mockResolvedValueOnce([changed]);
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  fireEvent.click(await screen.findByRole("button", { name: /בדוק ראיות להרשאת רכיב/ }));
  const evidence = screen.getByRole("region", { name: "ראיות החלטה decision-source-fingerprint" });
  await waitFor(() => expect(evidence).toHaveTextContent("UNKNOWN: גרסת התרחיש או ראיית המקור השתנו"));
  expect(mocks.preview).not.toHaveBeenCalled();
});

it("keeps a blocked decision separate from an independent allowed-permission decision", async () => {
  const separate = draft("two-decisions");
  separate.decisions.push({ ...separate.decisions[0], decision_id: "independent",
    source_component_id: "c2", component_code: "תגמולי_מעביד_עד_2000",
    ruleset_digest_at_review: "b".repeat(64) });
  mocks.list.mockResolvedValue([separate]);
  mocks.preview.mockImplementation(async (_client: number, decision: ScenarioDraft["decisions"][number]) =>
    decision.decision_id === "independent"
      ? { ...allowed, component_id: "c2", component_code: decision.component_code }
      : { ...allowed, permission_status: "blocked", reason_code: "MISSING_EVIDENCE", reason_he: "חסרה ראיה" });
  render(<ScenarioDraftPanel clientId={1} products={products} />);
  const sections = await screen.findAllByRole("region", { name: /^ראיות החלטה/ });
  const buttons = screen.getAllByRole("button", { name: /בדוק ראיות להרשאת רכיב/ });
  fireEvent.click(buttons[0]);
  fireEvent.click(buttons[1]);
  await waitFor(() => expect(sections[0]).toHaveTextContent("MISSING_EVIDENCE"));
  await waitFor(() => expect(sections[1]).toHaveTextContent("הרשאת רכיב בלבד"));
  expect(sections[1]).not.toHaveTextContent("MISSING_EVIDENCE");
  expect(sections[1]).toHaveTextContent("אישור כשירות מקצועית: לא זמין");
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


it("embeds fixation professional review in the existing planning view, not a separate results page", async () => {
  mocks.list.mockResolvedValue([draft("alternative-a")]);
  const view = render(<ScenarioDraftPanel clientId={1} products={products} view="planning" />);
  expect(await screen.findByRole("region", { name: "Fixation professional review" })).toBeTruthy();
  expect(screen.getByRole("region", { name: "Severance planning" })).toBeTruthy();
  view.rerender(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  expect(screen.queryByRole("region", { name: "Fixation professional review" })).toBeNull();
});

it("shows blocked read-only admission for selected saved revision without creating a financial result", async () => {
  mocks.list.mockResolvedValue([draft("readiness")]);
  render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  const section = await screen.findByRole("region", { name: "ראיית קבלה לחישוב" });
  await waitFor(() => expect(section).toHaveTextContent("blocked (חסום)"));
  expect(section).toHaveTextContent("PERMISSION_NOT_ADMITTED");
  expect(section).toHaveTextContent("גרסה: 2");
  expect(section).toHaveTextContent("אין תוצאה פיננסית מורשית");
  expect(mocks.admission).toHaveBeenCalledWith(1, "readiness", expect.any(AbortSignal));
  expect(mocks.replace).not.toHaveBeenCalled();
});

it("fail-closes stale source evidence, HTTP errors and version mismatches", async () => {
  mocks.list.mockResolvedValue([draft("readiness")]);
  mocks.admission.mockResolvedValueOnce({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: 1,
    scenario_id: "readiness", scenario_version: 2, assessment_state: "blocked",
    financial_result: null, blockers: [{ code: "SOURCE_STALE", decision_id: "d1" }],
  }).mockRejectedValueOnce(new Error("ADMISSION_HTTP_409")).mockResolvedValueOnce({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: 1,
    scenario_id: "readiness", scenario_version: 999, assessment_state: "blocked",
    financial_result: null, blockers: [],
  });
  render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  const section = await screen.findByRole("region", { name: "ראיית קבלה לחישוב" });
  await waitFor(() => expect(section).toHaveTextContent("מקור התיישן"));
  fireEvent.click(screen.getByRole("button", { name: /רענן ראיית קבלה/ }));
  await waitFor(() => expect(section).toHaveTextContent("ADMISSION_HTTP_409"));
  expect(section).not.toHaveTextContent("blocked (חסום)");
  fireEvent.click(screen.getByRole("button", { name: /רענן ראיית קבלה/ }));
  await waitFor(() => expect(section).toHaveTextContent("גרסת החלופה השתנתה"));
  expect(mocks.replace).not.toHaveBeenCalled();
});

it("isolates A-B-A admission responses by client, scenario and epoch", async () => {
  const oldA = pending<unknown>();
  mocks.list.mockImplementation(async (id: number) => [{ ...draft("same-scenario"), client_id: id }]);
  mocks.admission.mockReturnValueOnce(oldA.promise).mockResolvedValueOnce({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: 2,
    scenario_id: "same-scenario", scenario_version: 2, assessment_state: "blocked",
    financial_result: null, blockers: [{ code: "SOURCE_STALE", decision_id: null }],
  });
  const view = render(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  await waitFor(() => expect(mocks.admission).toHaveBeenCalledWith(1, "same-scenario", expect.any(AbortSignal)));
  view.rerender(<ScenarioDraftPanel clientId={2} products={products} view="results" />);
  await waitFor(() => expect(mocks.admission).toHaveBeenCalledWith(2, "same-scenario", expect.any(AbortSignal)));
  const section = screen.getByRole("region", { name: "ראיית קבלה לחישוב" });
  await waitFor(() => expect(section).toHaveTextContent("SOURCE_STALE"));
  view.rerender(<ScenarioDraftPanel clientId={1} products={products} view="results" />);
  oldA.resolve({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: 1,
    scenario_id: "same-scenario", scenario_version: 2, assessment_state: "blocked",
    financial_result: null, blockers: [{ code: "SHOULD_NOT_APPEAR", decision_id: null }],
  });
  await waitFor(() => expect(mocks.admission).toHaveBeenCalledTimes(3));
  expect(screen.queryByText("SHOULD_NOT_APPEAR")).toBeNull();
  expect(screen.queryByText("SOURCE_STALE")).toBeNull();
});
