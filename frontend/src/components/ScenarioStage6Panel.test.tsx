import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioStage6Panel } from "./ScenarioStage6Panel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";

const mock = vi.hoisted(() => ({
  list: vi.fn(), save: vi.fn(), estimate: vi.fn(),
}));
vi.mock("../api/scenarioStage6Api", () => ({
  listScenarioPensionElections: mock.list,
  saveScenarioPensionElections: mock.save,
  readScenarioGrossEstimate: mock.estimate,
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const scenario: ScenarioDraft = {
  scenario_id: "sc1", client_id: 1, name: "First",
  status: "draft", version: 3, created_by: "planner", updated_by: "planner",
  financial_validation: "not_evaluated",
  decisions: [{
    decision_id: "d1", source_product_id: "p1", source_component_id: "c1",
    component_code: "fund", amount: "100000.00", action: "pension",
    effective_date: "2026-09-30", validation_state: "unverified",
  }],
};
const election = {
  decision_id: "d1", pension_start_date: "2027-09-30", target_year: 2027,
  survivors_option: "spouse", spouse_age_diff: 0,
  coefficient_selection: "manual_review_required" as const,
  company_name: "Company", option_name: "Option",
};
function deferred<T>() {
  let resolve!: (x: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}

it("saves versioned election through the canonical API without factor authority", async () => {
  mock.list.mockResolvedValue([election]);
  mock.save.mockResolvedValue({});
  const saved = vi.fn().mockResolvedValue(undefined);
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={saved}/>);
  fireEvent.change(await screen.findByLabelText("בחירת שאירים"), { target: { value: "spouse 75%" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור בחירות קצבה כטיוטה" }));
  await waitFor(() => expect(mock.save).toHaveBeenCalledTimes(1));
  expect(mock.save.mock.calls[0][0]).toBe(1);
  expect(mock.save.mock.calls[0][1]).toBe("sc1");
  expect(mock.save.mock.calls[0][2]).toBe(3);
  expect(mock.save.mock.calls[0][3][0].decision_id).toBe("d1");
  await waitFor(() => expect(saved).toHaveBeenCalledWith("sc1"));
});

it("never displays a ready amount from BLOCKED result", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue({
    schema_version: "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
    result_fingerprint: "a".repeat(64),scenario_version: null,
    scenario_id: "sc1", decision_id: "d1", result_state: "BLOCKED",
    execution_allowed: false, monthly_estimate_gross_ils: null,
    blockers: ["STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"],
    coefficient_provenance: null,
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("rejects another decision's result and hides any monthly amount", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue({
    scenario_id: "sc1", decision_id: "OTHER", result_state: "RESULT_READY",
    execution_allowed: true, monthly_estimate_gross_ils: "10000.00", blockers: [],
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_CONTEXT_MISMATCH");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("drops a late estimate after the scenario version changes", async () => {
  mock.list.mockResolvedValue([election]);
  const waiting=deferred<any>();
  mock.estimate.mockReturnValue(waiting.promise);
  const view=render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  view.rerender(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, version: 4 }} onSaved={vi.fn()}/>);
  waiting.resolve({
    scenario_id: "sc1", decision_id: "d1", result_state: "RESULT_READY",
    execution_allowed: true, monthly_estimate_gross_ils: "5000.00",
    blockers: [],
  });
  await waitFor(() => expect(mock.list).toHaveBeenCalledTimes(2));
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("invalidates old estimate and blocks request while election edits are unsaved", async () => {
  mock.list.mockResolvedValue([election]);
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  const check = await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" });
  expect((check as HTMLButtonElement).disabled).toBe(false);
  fireEvent.change(screen.getByLabelText("בחירת שאירים"), {
    target: { value: "different survivor terms" },
  });
  expect((check as HTMLButtonElement).disabled).toBe(true);
  expect(mock.estimate).not.toHaveBeenCalled();
  expect(screen.getByText(/שמור ורענן את החלופה לפני בדיקת אומדן/)).toBeTruthy();
});


it("fails closed if a READY response lacks professional authority provenance", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue({
    schema_version: "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
    result_fingerprint: "a".repeat(64),
    scenario_version: 3,scenario_id: "sc1",decision_id: "d1",
    result_state: "RESULT_READY",execution_allowed: true,
    monthly_estimate_gross_ils: "5000.00",
    coefficient_provenance: null,professional_admission_fingerprint: null,
    blockers: [],
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});
