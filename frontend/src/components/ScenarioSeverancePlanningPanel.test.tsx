import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioSeverancePlanningPanel } from "./ScenarioSeverancePlanningPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { PensionProduct } from "../api/pensionProductsApi";

const mocks = vi.hoisted(() => ({
  read: vi.fn(), save: vi.fn(), grants: vi.fn(),
}));
vi.mock("../api/scenarioSeverancePlanningApi", () => ({
  readSeverancePlanning: mocks.read,
  saveSeverancePlanning: mocks.save,
}));
vi.mock("../api/clientsApi", () => ({
  getGrants: mocks.grants,
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
});
const grant = {
  grant_id: "g7", client_id: 7, employer_name: "Test employer",
};
it("loads source facts, saves nonbinding choices with scenario CAS, and shows saved result", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.grants.mockResolvedValue([grant]);
  mocks.save.mockImplementation(async (_client: number, _scenario: string, _version: number, choices: unknown[]) =>
    ({ ...snapshot(), scenario_version: 4, choices: choices.map((choice: object) => ({
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
  const amount = screen.getByRole("textbox");
  fireEvent.change(amount, { target: { value: "100.00" } });
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
  mocks.grants.mockResolvedValue([grant]);
  render(<ScenarioSeverancePlanningPanel clientId={7} scenario={scenario}
    products={[]} onSaved={vi.fn()}/>);
  expect(await screen.findByText(/פרטי המקור או ההעסקה השתנו/)).toBeTruthy();
  expect(mocks.save).not.toHaveBeenCalled();
});

it("never renders another client's grants and locks archived scenarios", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.grants.mockResolvedValue([{ ...grant, client_id: 8 }]);
  render(<ScenarioSeverancePlanningPanel clientId={7}
    scenario={{ ...scenario, status: "archived" }} products={[]} onSaved={vi.fn()}/>);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText(/מענק: Test employer/)).toBeNull();
  expect(mocks.save).not.toHaveBeenCalled();
});
