import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { M11PreferredScenarioPanel } from "./M11PreferredScenarioPanel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";

const mocks = vi.hoisted(() => ({ read: vi.fn(), save: vi.fn() }));
vi.mock("../api/m11PreferredScenarioApi", () => ({
  readM11Selection: mocks.read, saveM11Selection: mocks.save,
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const choices = [
  { scenario_id: "a", client_id: 101, name: "ראשונה", version: 2, status: "draft", decisions: [] },
  { scenario_id: "b", client_id: 101, name: "שנייה", version: 3, status: "needs_revalidation", decisions: [] },
] as unknown as ScenarioDraft[];
function state(selected = "a", version = 2, revision = 1) {
  const item = {
    selection_id: "selection", client_id: 101, scenario_id: selected,
    scenario_version: version, revision, rationale: "הסבר",
    saved_at: "2026-11-15T13:00:00Z", calculation_references: [],
    professional_approval: false as const,
  };
  return {
    client_id: 101, current: item, revision, history: [item], outdated: false,
    calculation_authorized: false as const, report_authorized: false as const,
  };
}
it("loads a previously saved preferred alternative and rationale", async () => {
  mocks.read.mockResolvedValue(state());
  render(<M11PreferredScenarioPanel clientId={101} scenarios={choices}/>);
  expect(await screen.findByDisplayValue("הסבר")).toBeTruthy();
  expect((screen.getByRole("combobox", { name: /חלופה מועדפת/ }) as HTMLSelectElement).value).toBe("a");
  expect(screen.getByText(/אינה מאשרת חישובים/)).toBeTruthy();
});
it("saves an alternative with explicit CAS versions and no calculation approval", async () => {
  mocks.read.mockResolvedValue(state());
  mocks.save.mockResolvedValue(state("b", 3, 2));
  render(<M11PreferredScenarioPanel clientId={101} scenarios={choices}/>);
  const dropdown = await screen.findByRole("combobox", { name: /חלופה מועדפת/ });
  fireEvent.change(dropdown, { target: { value: "b" } });
  fireEvent.change(screen.getByRole("textbox", { name: /נימוק מקצועי/ }), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור בחירה" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(101, {
    scenario_id: "b", expected_scenario_version: 3,
    expected_selection_revision: 1, rationale: "",
  }));
  expect(screen.getByText(/נתוני המקור של החלופה מחייבים בדיקה מחדש/)).toBeTruthy();
});
it("reports stale selections instead of silently treating them as valid", async () => {
  mocks.read.mockResolvedValue(state("a", 1));
  render(<M11PreferredScenarioPanel clientId={101} scenarios={choices}/>);
  expect(await screen.findByText(/החלופה השמורה השתנתה/)).toBeTruthy();
});
it("rejects a foreign-client response and does not display it", async () => {
  mocks.read.mockResolvedValue({ ...state(), client_id: 202 });
  render(<M11PreferredScenarioPanel clientId={101} scenarios={choices}/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("M11_CLIENT_CONTEXT_INVALID");
  expect(screen.queryByText(/בחירה שמורה:/)).toBeNull();
});
