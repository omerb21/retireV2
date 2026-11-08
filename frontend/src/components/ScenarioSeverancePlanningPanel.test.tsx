import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioSeverancePlanningPanel } from "./ScenarioSeverancePlanningPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";
import type { SeveranceChoiceInput } from "../api/scenarioSeverancePlanningApi";

const mocks = vi.hoisted(() => ({
  read: vi.fn(), save: vi.fn(),
}));
vi.mock("../api/scenarioSeverancePlanningApi", () => ({
  readSeverancePlanning: mocks.read,
  saveSeverancePlanning: mocks.save,
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const scenario: ScenarioDraft = {
  scenario_id: "scenario-A", client_id: 7, name: "Alternate A",
  version: 3, status: "draft", created_by: "planner", updated_by: "planner",
  decisions: [], financial_validation: "not_evaluated",
};
const products = [{
  product_id: "p7", client_id: 7, product_name: "Pension source",
  conversion_components: [{
    component_id: "severance-c7", component_code: "פיצויים_מעסיק_נוכחי",
    balance: "200.00",
  }],
}] as unknown as PensionProduct[];

const snapshot = (choices: unknown[] = []) => ({
  client_id: 7, scenario_id: "scenario-A", scenario_version: 3,
  choices, authority_state: "DRAFT_ONLY", execution_allowed: false,
  source_evidence: {
    client_id: 7, scenario_id: "scenario-A", scenario_version: 3,
    authority_state: "FACTUAL_EVIDENCE_ONLY", blockers: [] as string[],
    facts: {
      grants: [{
        grant_id: "g7", employer_name: "Test employer",
        reported_nominal_amount_ils: "150.00",
        payment_classification: "UNKNOWN_NOT_VERIFIED",
      }],
      pension_severance_component_candidates: [{
        product_id: "p7", component_id: "severance-c7",
        component_code: "פיצויים_מעסיק_נוכחי",
        reported_balance_ils: "200.00",
      }],
    },
  },
});
it("loads source facts, saves nonbinding choices with scenario CAS, and shows saved result", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockImplementation(async (_client: number, _scenario: string, _version: number, choices: SeveranceChoiceInput[]) =>
    ({ ...snapshot(), scenario_version: 4,
      source_evidence: { ...snapshot().source_evidence, scenario_version: 4 },
      choices: choices.map(choice => ({
      ...choice, client_id: 7, scenario_id: "scenario-A",
      current_scenario_version: 4, saved_from_scenario_version: 4,
      source_fingerprint: "a".repeat(64), state: "DRAFT_ONLY",
      professional_authority: false, execution_allowed: false,
      actual_paid_amount_ils: null, future_payable_amount_ils: null,
      exempt_amount_ils: null, net_amount_ils: null,
    })) }));
  const onSaved = vi.fn().mockResolvedValue(undefined);
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={products} onSaved={onSaved}/>);
  expect(await screen.findByText(/מענק: Test employer/)).toBeTruthy();
  expect(screen.getByText(/Pension source/)).toBeTruthy();
  expect(screen.getByText(/אין כאן אישור רצף/)).toBeTruthy();
  const choices = screen.getAllByRole("combobox");
  fireEvent.change(choices[0], { target: { value: "PLANNED_WITHDRAWAL" } });
  fireEvent.change(choices[1], { target: { value: "PLANNED_SEVERANCE_CONTINUITY" } });
  const amounts = screen.getAllByRole("textbox");
  expect((amounts[0] as HTMLInputElement).disabled).toBe(false);
  fireEvent.change(amounts[1], { target: { value: "100.00" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(
    7, "scenario-A", 3, expect.arrayContaining([
      expect.objectContaining({ source_kind: "grant", choice: "PLANNED_WITHDRAWAL", planned_amount_ils: null }),
      expect.objectContaining({ source_kind: "pension_component", choice: "PLANNED_SEVERANCE_CONTINUITY", planned_amount_ils: "100.00" }),
    ]),
  ));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith("scenario-A"));
  expect(screen.getByText(/בחירות התכנון נשמרו/)).toBeTruthy();
});

it("shows stale-source blocker without turning it into financial authority", async () => {
  mocks.read.mockResolvedValue(snapshot([{
    source_kind: "grant", source_id: "g7", choice: "PLANNED_WITHDRAWAL",
    planned_amount_ils: null, state: "BLOCKED_SOURCE_STALE",
    client_id: 7, scenario_id: "scenario-A",
  }]));
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={[]} onSaved={vi.fn()}/>);
  expect(await screen.findByText(/פרטי המקור או ההעסקה השתנו/)).toBeTruthy();
  expect(mocks.save).not.toHaveBeenCalled();
});

it("never renders another client's grants and locks archived scenarios", async () => {
  mocks.read.mockResolvedValue({
    ...snapshot(), source_evidence: { ...snapshot().source_evidence, client_id: 8 },
  });
  render(<ScenarioSeverancePlanningPanel clientId={7}
    scenario={{ ...scenario, status: "archived" }} products={[]} onSaved={vi.fn()}/>);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText(/מענק: Test employer/)).toBeNull();
  expect(mocks.save).not.toHaveBeenCalled();
});

it("shows unresolved overlap and disables edits for an archived scenario", async () => {
  const current = snapshot([{
    source_kind: "grant", source_id: "g7", choice: "PLANNED_WITHDRAWAL",
    planned_amount_ils: null, state: "BLOCKED_GRANT_COMPONENT_OVERLAP_UNRECONCILED",
    client_id: 7, scenario_id: "scenario-A",
  }]);
  current.source_evidence.blockers.push("SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED");
  mocks.read.mockResolvedValue(current);
  render(<ScenarioSeverancePlanningPanel clientId={7}
    scenario={{ ...scenario, status: "archived" }} products={products} onSaved={vi.fn()}/>);
  expect(await screen.findByText(/קיימת חפיפה אפשרית בין מענקים לבין רכיבי פיצויים/)).toBeTruthy();
  expect(screen.getByText(/החלופה אינה פעילה לעריכה/)).toBeTruthy();
  expect((screen.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }) as HTMLButtonElement).disabled).toBe(true);
  expect(mocks.save).not.toHaveBeenCalled();
});

it.each([
  ["100", "100.00"],
  ["100.5", "100.50"],
  ["100.50", "100.50"],
])("normalizes a valid severance amount %s to %s before the API request", async (typed, expected) => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockImplementation(async (_client: number, _scenario: string, _version: number, choices: unknown[]) => ({
    ...snapshot(), scenario_version: 4,
    source_evidence: { ...snapshot().source_evidence, scenario_version: 4 },
    choices,
  }));
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={products} onSaved={vi.fn().mockResolvedValue(undefined)} />);
  expect(await screen.findByText(/Pension source/)).toBeTruthy();
  const selectors = screen.getAllByRole("combobox");
  fireEvent.change(selectors[1], { target: { value: "PLANNED_WITHDRAWAL" } });
  const amount = screen.getByRole("textbox") as HTMLInputElement;
  fireEvent.change(amount, { target: { value: typed } });
  expect(amount.value).toBe(typed);
  fireEvent.click(screen.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(
    7, "scenario-A", 3, [expect.objectContaining({
      source_kind: "pension_component",
      source_id: "severance-c7",
      planned_amount_ils: expected,
    })],
  ));
});

it("rejects sub-cent precision and a value above the exact source balance", async () => {
  mocks.read.mockResolvedValue(snapshot());
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={products} onSaved={vi.fn().mockResolvedValue(undefined)} />);
  expect(await screen.findByText(/Pension source/)).toBeTruthy();
  fireEvent.change(screen.getAllByRole("combobox")[1], {
    target: { value: "PLANNED_WITHDRAWAL" },
  });
  const amount = screen.getByRole("textbox") as HTMLInputElement;
  const save = screen.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }) as HTMLButtonElement;
  fireEvent.change(amount, { target: { value: "100.501" } });
  expect(save.disabled).toBe(true);
  fireEvent.click(save);
  expect(mocks.save).not.toHaveBeenCalled();
  fireEvent.change(amount, { target: { value: "200.01" } });
  expect(save.disabled).toBe(true);
  fireEvent.click(save);
  expect(mocks.save).not.toHaveBeenCalled();
});

it("preserves an empty planned amount as null in the API payload", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockImplementation(async () => ({
    ...snapshot(), scenario_version: 4,
    source_evidence: { ...snapshot().source_evidence, scenario_version: 4 },
  }));
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={products} onSaved={vi.fn().mockResolvedValue(undefined)} />);
  expect(await screen.findByText(/Pension source/)).toBeTruthy();
  fireEvent.change(screen.getAllByRole("combobox")[1], {
    target: { value: "PLANNED_WITHDRAWAL" },
  });
  fireEvent.click(screen.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(
    7, "scenario-A", 3, [expect.objectContaining({
      source_kind: "pension_component", planned_amount_ils: null,
    })],
  ));
});
