import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioStage6Panel } from "./ScenarioStage6Panel";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";

const mock = vi.hoisted(() => ({
  list: vi.fn(), save: vi.fn(), estimate: vi.fn(), aggregate: vi.fn(), allocation: vi.fn(),
}));
vi.mock("../api/scenarioStage6Api", () => ({
  listScenarioPensionElections: mock.list,
  saveScenarioPensionElections: mock.save,
  readScenarioGrossEstimate: mock.estimate,
  readScenarioPensionAggregate: mock.aggregate,
  readScenarioAllocationEvidence: mock.allocation,
  validScenarioAllocationEvidence: (value: any, clientId: number, scenarioId: string, version: number) =>
    value?.allocation_evidence?.client_id === clientId
    && value.allocation_evidence.scenario_id === scenarioId
    && value.allocation_evidence.scenario_version === version
    && value.allocation_evidence.execution_allowed === false
    && value.allocation_evidence.financial_result === null
    && value.execution_allowed === false && value.financial_result === null
    && value.manifest_fingerprint === value.allocation_evidence.manifest_fingerprint,
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
    product_version_at_review: 1, source_fingerprint_at_review: "a".repeat(64),
    ruleset_digest_at_review: "b".repeat(64), permission_preview_id_at_review: "c".repeat(64),
  }],
};
const election = {
  decision_id: "d1", pension_start_date: "2027-09-30", target_year: 2027,
  survivors_option: "spouse", spouse_age_diff: 0,
  coefficient_selection: "manual_review_required" as const,
  company_name: "Company", option_name: "Option",
};
const hashes = {
  planning_calculation_input_fingerprint: "1".repeat(64),
  monthly_basis_semantic_fingerprint: "2".repeat(64),
  monthly_basis_source_fingerprint: "3".repeat(64),
  temporal_semantic_fingerprint: "4".repeat(64),
  temporal_source_fingerprint: "5".repeat(64),
};
function blockedEstimate(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
    client_id: 1, scenario_id: "sc1", scenario_version: null,
    decision_id: "d1", source_id: "scenario-decision:sc1:d1",
    result_state: "BLOCKED", execution_allowed: false,
    blockers: ["STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"],
    coefficient_provenance: null, professional_admission_fingerprint: null,
    planning_calculation_input_fingerprint: null,
    monthly_basis_semantic_fingerprint: null, monthly_basis_source_fingerprint: null,
    temporal_semantic_fingerprint: null, temporal_source_fingerprint: null,
    pte_source_execution_fingerprint: null, pte_source_result_fingerprint: null,
    monthly_estimate_gross_ils: null, retirement_target_date: null,
    statement_date: null, result_fingerprint: "a".repeat(64), ...overrides,
  };
}
function readyEstimate(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
    client_id: 1, scenario_id: "sc1", scenario_version: 3,
    decision_id: "d1", source_id: "scenario-decision:sc1:d1",
    result_state: "RESULT_READY", execution_allowed: true, blockers: [],
    coefficient_provenance: {
      source_level: "MANUAL_PROFESSIONAL_OVERRIDE", factor_value: "200",
      factor_evidence_type: "PLANNER_ASSUMPTION", factor_evidence_reference: "reference",
      payout_option_name: "Option", admission_revision: 1,
    },
    professional_admission_fingerprint: "6".repeat(64), ...hashes,
    pte_source_execution_fingerprint: "7".repeat(64),
    pte_source_result_fingerprint: "8".repeat(64),
    monthly_estimate_gross_ils: "5.00", retirement_target_date: "2027-09-30",
    statement_date: "2026-09-30", result_fingerprint: "a".repeat(64), ...overrides,
  };
}
function aggregate(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: "STAGE6_PENSION_DECISION_AGGREGATE_V1",
    client_id: 1, scenario_id: "sc1", scenario_version: 3,
    aggregation_state: "COMPLETE", blockers: [],
    decision_results: [readyEstimate()],
    monthly_pension_gross_total_ils: "5.00",
    comparison_basis: {
      currency: "ILS", income_basis: "GROSS", price_basis: "NOMINAL_UNINDEXED",
      retirement_target_date: "2027-09-30", source_reference_date: "2026-09-30",
    },
    execution_allowed: false, aggregate_fingerprint: "f".repeat(64), ...overrides,
  };
}
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
  mock.estimate.mockResolvedValue(blockedEstimate());
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
  mock.estimate.mockResolvedValue(readyEstimate({
    coefficient_provenance: null, professional_admission_fingerprint: null,
  }));
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("rejects a coherently shaped READY result for another client", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue(readyEstimate({ client_id: 2 }));
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("rejects a coherently shaped READY result for another source", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue(readyEstimate({ source_id: "scenario-decision:sc1:other" }));
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_RESULT_AUTHORITY_INCOMPLETE");
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("renders a monthly amount only from the complete closed READY envelope", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue(readyEstimate());
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText(/אומדן קצבה חודשית ברוטו: 5.00/);
  expect(screen.getByLabelText("מצב חישוב החלופה")).toHaveTextContent(
    "טרם חושב סיכום קצבה מצרפי מאושר לחלופה",
  );
});

it("preserves per-decision results without representing them as an aggregate", async () => {
  const secondDecision = {
    ...scenario.decisions[0], decision_id: "d2", source_component_id: "c2",
    component_code: "fund-2",
  };
  const secondElection = { ...election, decision_id: "d2", option_name: "Option 2" };
  mock.list.mockResolvedValue([election, secondElection]);
  mock.estimate
    .mockResolvedValueOnce(readyEstimate())
    .mockResolvedValueOnce(blockedEstimate({
      decision_id: "d2", source_id: "scenario-decision:sc1:d2",
      blockers: ["STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"],
    }));
  render(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, decisions: [...scenario.decisions, secondDecision] }}
    onSaved={vi.fn()}/>);

  const buttons = await screen.findAllByRole("button", { name: "בדוק אומדן קצבה מאושר" });
  fireEvent.click(buttons[0]);
  await screen.findByText(/אומדן קצבה חודשית ברוטו: 5.00/);
  fireEvent.click(buttons[1]);
  await screen.findByText("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED");

  expect(screen.getByText(/אומדן קצבה חודשית ברוטו: 5.00/)).toBeInTheDocument();
  const status = screen.getByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("טרם חושב סיכום קצבה מצרפי");
  expect(status).toHaveTextContent("1 אומדנים הושלמו; 1 חסומים; 0 טרם נבדקו");
  expect(status).toHaveTextContent("לא מוצג סכום כולל");
  expect(status).not.toHaveTextContent("10.00");
});

it("does not infer aggregate blocked state from one independently blocked decision", async () => {
  mock.list.mockResolvedValue([election]);
  mock.estimate.mockResolvedValue(blockedEstimate());
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "בדוק אומדן קצבה מאושר" }));
  await screen.findByText("STAGE6_P1C_FACTOR_ADMISSION_BLOCKED");
  const status = screen.getByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("טרם חושב סיכום קצבה מצרפי");
  expect(status).not.toHaveTextContent("0.00 ₪");
});

it("shows a single-decision gross total only from a complete aggregate envelope", async () => {
  mock.list.mockResolvedValue([election]);
  mock.aggregate.mockResolvedValue(aggregate());
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  const status = await screen.findByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("החישוב הושלם");
  expect(status).toHaveTextContent("סך קצבה חודשית ברוטו: 5.00 ₪");
  expect(status).toHaveTextContent("מועד יעד 2027-09-30");
  expect(status).toHaveTextContent("אינו קצבה נטו, חישוב מס, תזרים או NPV");
});

it("shows the exact total for two comparable authorized decisions", async () => {
  const d2 = { ...scenario.decisions[0], decision_id: "d2", source_product_id: "p2",
    source_component_id: "c2", component_code: "fund-2" };
  const e2 = { ...election, decision_id: "d2" };
  const result2 = readyEstimate({
    decision_id: "d2", source_id: "scenario-decision:sc1:d2",
    monthly_estimate_gross_ils: "7.35",
  });
  mock.list.mockResolvedValue([election, e2]);
  mock.aggregate.mockResolvedValue(aggregate({
    decision_results: [readyEstimate(), result2],
    monthly_pension_gross_total_ils: "12.35",
  }));
  render(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, decisions: [...scenario.decisions, d2] }} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  const status = await screen.findByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("סך קצבה חודשית ברוטו: 12.35 ₪");
  expect(screen.getByText(/אומדן קצבה חודשית ברוטו: 5.00/)).toBeInTheDocument();
  expect(screen.getByText(/אומדן קצבה חודשית ברוטו: 7.35/)).toBeInTheDocument();
});

it("keeps one ready decision visible but never totals a partial aggregate", async () => {
  const d2 = { ...scenario.decisions[0], decision_id: "d2", source_product_id: "p2",
    source_component_id: "c2", component_code: "fund-2" };
  const e2 = { ...election, decision_id: "d2" };
  const blocked2 = blockedEstimate({
    decision_id: "d2", source_id: "scenario-decision:sc1:d2",
  });
  mock.list.mockResolvedValue([election, e2]);
  mock.aggregate.mockResolvedValue(aggregate({
    aggregation_state: "PARTIAL",
    blockers: ["d2:STAGE6_P1C_FACTOR_ADMISSION_BLOCKED"],
    decision_results: [readyEstimate(), blocked2],
    monthly_pension_gross_total_ils: null, comparison_basis: null,
  }));
  render(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, decisions: [...scenario.decisions, d2] }} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  const status = await screen.findByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("תוצאה חלקית");
  expect(status).toHaveTextContent("לא מוצג סכום כולל");
  expect(status).toHaveTextContent("d2:STAGE6_P1C_FACTOR_ADMISSION_BLOCKED");
  expect(status).not.toHaveTextContent("סך קצבה חודשית ברוטו");
});

it("blocks a total for different time bases", async () => {
  const d2 = { ...scenario.decisions[0], decision_id: "d2", source_product_id: "p2",
    source_component_id: "c2", component_code: "fund-2" };
  const e2 = { ...election, decision_id: "d2" };
  mock.list.mockResolvedValue([election, e2]);
  mock.aggregate.mockResolvedValue(aggregate({
    aggregation_state: "BLOCKED",
    blockers: ["STAGE6_AGGREGATE_RETIREMENT_TARGET_DATE_MISMATCH"],
    decision_results: [readyEstimate(), readyEstimate({
      decision_id: "d2", source_id: "scenario-decision:sc1:d2",
      retirement_target_date: "2028-09-30",
    })],
    monthly_pension_gross_total_ils: null, comparison_basis: null,
  }));
  render(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, decisions: [...scenario.decisions, d2] }} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  const status = await screen.findByLabelText("מצב חישוב החלופה");
  expect(status).toHaveTextContent("החישוב חסום");
  expect(status).toHaveTextContent("STAGE6_AGGREGATE_RETIREMENT_TARGET_DATE_MISMATCH");
  expect(status).not.toHaveTextContent("סך קצבה חודשית ברוטו");
});

it("rejects a malformed aggregate fingerprint without presenting its total", async () => {
  mock.list.mockResolvedValue([election]);
  mock.aggregate.mockResolvedValue(aggregate({ aggregate_fingerprint: "not-a-hash" }));
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  await screen.findByText("STAGE6_AGGREGATE_AUTHORITY_INCOMPLETE");
  expect(screen.queryByText(/סך קצבה חודשית ברוטו/)).toBeNull();
});

it("discards a late aggregate after the scenario version changes", async () => {
  mock.list.mockResolvedValue([election]);
  const waiting = deferred<any>();
  mock.aggregate.mockReturnValue(waiting.promise);
  const view = render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  view.rerender(<ScenarioStage6Panel clientId={1}
    scenario={{ ...scenario, version: 4 }} onSaved={vi.fn()}/>);
  waiting.resolve(aggregate());
  await waitFor(() => expect(mock.list).toHaveBeenCalledTimes(2));
  expect(screen.queryByText(/סך קצבה חודשית ברוטו/)).toBeNull();
});

it("immediately invalidates an aggregate after pension terms change", async () => {
  mock.list.mockResolvedValue([election]);
  mock.aggregate.mockResolvedValue(aggregate());
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "חשב סיכום קצבאות מאושר" }));
  await screen.findByText(/סך קצבה חודשית ברוטו: 5.00/);
  fireEvent.change(screen.getByLabelText("בחירת שאירים"), {
    target: { value: "changed terms" },
  });
  expect(screen.queryByText(/סך קצבה חודשית ברוטו/)).toBeNull();
  expect(screen.getByLabelText("מצב חישוב החלופה")).toHaveTextContent(
    "טרם חושב סיכום קצבה מצרפי",
  );
});


it("catalog candidate neither offers manual factor admission nor an executable estimate", async () => {
  mock.list.mockResolvedValue([{
    ...election, coefficient_selection: "catalog_candidate",
  }]);
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  const estimateButton=await screen.findByRole("button",{name:"בדוק אומדן קצבה מאושר"});
  expect((estimateButton as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByRole("button",{name:"הזן ואשר מקדם מקצועי"})).toBeNull();
  expect(mock.estimate).not.toHaveBeenCalled();
});


it("shows only structural allocation facts and explicitly avoids income claims", async () => {
  mock.list.mockResolvedValue([election]);
  mock.allocation.mockResolvedValue({
    manifest_fingerprint:"a".repeat(64),candidate_evidence_state:"STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
    candidate_blockers:[],overall_status:"STRUCTURAL_ONLY",
    allocation_evidence:{
      schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id:1,scenario_id:"sc1",scenario_version:3,
      manifest_fingerprint:"a".repeat(64),evidence_fingerprint:"b".repeat(64),
      overall_status:"STRUCTURAL_ONLY",blocker_codes:[],
      sources:[{
        product_id:"p1",component_id:"c1",component_code:"תגמולים",source_fingerprint:"c".repeat(64),
        balance:"100000.00",allocated:"40000.00",unallocated:"60000.00",
        allocation_by_action:{pension:"40000.00",capital_asset:"0.00"},
        decision_ids:["d1"],status:"STRUCTURAL_ONLY",blocker_codes:[],
      }],
      financial_result:null,execution_allowed:false,
    },
    financial_result:null,execution_allowed:false,
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}));
  await screen.findByText(/מוקצה 40000.00/);
  expect(screen.getByText(/לא מוקצה 60000.00/)).toBeTruthy();
  expect(screen.getByText(/בדיקה מבנית בלבד/)).toBeTruthy();
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});

it("does not present a cross-scenario allocation response", async () => {
  mock.list.mockResolvedValue([election]);
  mock.allocation.mockResolvedValue({
    manifest_fingerprint:"a".repeat(64),
    allocation_evidence:{client_id:1,scenario_id:"other",scenario_version:3,
      manifest_fingerprint:"a".repeat(64),
      financial_result:null,execution_allowed:false},
    financial_result:null,execution_allowed:false,
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}));
  await screen.findByText("SCENARIO_ALLOCATION_EVIDENCE_INCOMPLETE");
  expect(screen.queryByLabelText("תוצאות בקרת הקצאות")).toBeNull();
});

it("does not request allocation evidence after editing pension choice", async () => {
  mock.list.mockResolvedValue([election]);
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  const button=screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}) as HTMLButtonElement;
  fireEvent.change(await screen.findByLabelText("בחירת שאירים"),{target:{value:"changed"}});
  expect(button.disabled).toBe(true);
  expect(mock.allocation).not.toHaveBeenCalled();
});


it("discards an in-flight allocation read when the scenario version changes", async () => {
  mock.list.mockResolvedValue([election]);
  const pending=deferred<any>();
  mock.allocation.mockReturnValue(pending.promise);
  const view=render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}));
  await waitFor(() => expect(mock.allocation).toHaveBeenCalledTimes(1));
  view.rerender(<ScenarioStage6Panel clientId={1}
    scenario={{...scenario,version:4}} onSaved={vi.fn()}/>);
  pending.resolve({
    manifest_fingerprint:"a".repeat(64),overall_status:"STRUCTURAL_ONLY",
    allocation_evidence:{
      schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id:1,scenario_id:"sc1",scenario_version:3,
      manifest_fingerprint:"a".repeat(64),
      evidence_fingerprint:"b".repeat(64),
      overall_status:"STRUCTURAL_ONLY",sources:[],
      blocker_codes:[],financial_result:null,execution_allowed:false,
    },
    candidate_blockers:[],financial_result:null,execution_allowed:false,
  });
  await waitFor(() => expect(mock.list).toHaveBeenCalledTimes(2));
  expect(screen.queryByLabelText("תוצאות בקרת הקצאות")).toBeNull();
});

it("discards a pending allocation read after editing pension terms", async () => {
  mock.list.mockResolvedValue([election]);
  const pending=deferred<any>();
  mock.allocation.mockReturnValue(pending.promise);
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}));
  await waitFor(() => expect(mock.allocation).toHaveBeenCalledTimes(1));
  fireEvent.change(await screen.findByLabelText("בחירת שאירים"),{
    target:{value:"different coverage"},
  });
  pending.resolve({
    manifest_fingerprint:"a".repeat(64),overall_status:"STRUCTURAL_ONLY",
    candidate_blockers:[],financial_result:null,execution_allowed:false,
    allocation_evidence:{
      schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id:1,scenario_id:"sc1",scenario_version:3,
      manifest_fingerprint:"a".repeat(64),evidence_fingerprint:"b".repeat(64),
      overall_status:"STRUCTURAL_ONLY",blocker_codes:[],
      financial_result:null,execution_allowed:false,
      sources:[{
        product_id:"p1",component_id:"c1",component_code:"fund",source_fingerprint:"c".repeat(64),
        balance:"100.00",allocated:"50.00",unallocated:"50.00",
      allocation_by_action:{pension:"50.00",capital_asset:"0.00"},
        status:"STRUCTURAL_ONLY",blocker_codes:[],decision_ids:["d1"],
      }],
    },
  });
  await waitFor(() => expect(screen.getByText(/שמור ורענן את החלופה/)).toBeTruthy());
  expect(screen.queryByLabelText("תוצאות בקרת הקצאות")).toBeNull();
});


it("allows structural allocation review for capital-only draft without exposing pension elections", async () => {
  mock.list.mockResolvedValue([]);
  mock.allocation.mockResolvedValue({
    manifest_fingerprint:"a".repeat(64),candidate_evidence_state:"STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
    candidate_blockers:[],overall_status:"STRUCTURAL_ONLY",
    allocation_evidence:{
      schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id:1,scenario_id:"sc1",scenario_version:3,
      manifest_fingerprint:"a".repeat(64),evidence_fingerprint:"b".repeat(64),
      overall_status:"STRUCTURAL_ONLY",blocker_codes:[],
      sources:[{
        product_id:"p1",component_id:"c1",component_code:"fund",source_fingerprint:"c".repeat(64),
        balance:"100000.00",allocated:"40000.00",unallocated:"60000.00",
        allocation_by_action:{pension:"0.00",capital_asset:"40000.00"},
        decision_ids:["d1"],status:"STRUCTURAL_ONLY",blocker_codes:[],
      }],financial_result:null,execution_allowed:false,
    },financial_result:null,execution_allowed:false,
  });
  const capital={...scenario,decisions:scenario.decisions.map(d=>({...d,action:"capital_asset" as const}))};
  render(<ScenarioStage6Panel clientId={1} scenario={capital} onSaved={vi.fn()}/>);
  expect(screen.queryByRole("button",{name:"שמור בחירות קצבה כטיוטה"})).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"בדוק הקצאות ויתרות לא מוקצות"}));
  await screen.findByText(/לא מוקצה 60000.00/);
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו/)).toBeNull();
  expect(mock.estimate).not.toHaveBeenCalled();
});


it("loads current alternative allocation evidence within the workspace without a second click", async () => {
  mock.list.mockResolvedValue([election]);
  mock.allocation.mockResolvedValue({
    manifest_fingerprint: "a".repeat(64),
    candidate_evidence_state: "STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
    candidate_blockers: [],
    overall_status: "STRUCTURAL_ONLY",
    allocation_evidence: {
      schema_version: "SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id: 1, scenario_id: "sc1", scenario_version: 3,
      manifest_fingerprint: "a".repeat(64), evidence_fingerprint: "b".repeat(64),
      overall_status: "STRUCTURAL_ONLY", blocker_codes: [],
      sources: [{
        product_id: "p1", component_id: "c1", component_code: "fund",
        source_fingerprint: "c".repeat(64),
        balance: "100000.00", allocated: "40000.00", unallocated: "60000.00",
        allocation_by_action: { pension: "40000.00", capital_asset: "0.00" },
        decision_ids: ["d1"], status: "STRUCTURAL_ONLY", blocker_codes: [],
      }],
      financial_result: null, execution_allowed: false,
    },
    financial_result: null, execution_allowed: false,
  });
  render(<ScenarioStage6Panel clientId={1} scenario={scenario} onSaved={vi.fn()}
    autoInspectAllocations/>);
  await waitFor(() => expect(mock.allocation).toHaveBeenCalledWith(1, "sc1"));
  await screen.findByText(/לא מוקצה 60000.00/);
  expect(screen.queryByText(/אומדן קצבה חודשית ברוטו:/)).toBeNull();
});


it("opens a capital-only alternative without requesting pension elections", async () => {
  const capitalScenario: ScenarioDraft = {
    ...scenario,
    decisions: scenario.decisions.map(decision => ({
      ...decision, action: "capital_asset" as const,
    })),
  };
  mock.allocation.mockResolvedValue({
    manifest_fingerprint: "a".repeat(64),
    candidate_evidence_state: "STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
    candidate_blockers: [], overall_status: "STRUCTURAL_ONLY",
    allocation_evidence: {
      schema_version: "SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id: 1, scenario_id: "sc1", scenario_version: 3,
      manifest_fingerprint: "a".repeat(64),
      evidence_fingerprint: "b".repeat(64),
      overall_status: "STRUCTURAL_ONLY", blocker_codes: [],
      sources: [{
        product_id: "p1", component_id: "c1", component_code: "fund",
        source_fingerprint: "c".repeat(64), balance: "100000.00",
        allocated: "100000.00", unallocated: "0.00",
        allocation_by_action: { pension: "0.00", capital_asset: "100000.00" },
        status: "STRUCTURAL_ONLY", blocker_codes: [], decision_ids: ["d1"],
      }],
      financial_result: null, execution_allowed: false,
    },
    financial_result: null, execution_allowed: false,
  });
  render(<ScenarioStage6Panel clientId={1} scenario={capitalScenario}
    onSaved={vi.fn()} autoInspectAllocations/>);
  await screen.findByText(/לא מוקצה 0.00/);
  expect(mock.list).not.toHaveBeenCalled();
  expect(screen.queryByText("טוען בחירות קצבה...")).toBeNull();
  expect(screen.queryByRole("button", { name: "בדוק אומדן קצבה מאושר" })).toBeNull();
});
