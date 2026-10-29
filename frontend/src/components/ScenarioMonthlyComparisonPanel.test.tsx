import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import type { ScenarioMonthlyComparison } from "../api/scenarioStage6Api";
import { ScenarioMonthlyComparisonPanel } from "./ScenarioMonthlyComparisonPanel";

const api = vi.hoisted(() => ({ read: vi.fn() }));
vi.mock("../api/scenarioStage6Api", async importOriginal => ({
  ...(await importOriginal<typeof import("../api/scenarioStage6Api")>()),
  readScenarioMonthlyComparison: api.read,
}));

const H = "a".repeat(64);
const drafts: ScenarioDraft[] = [
  { scenario_id: "a", client_id: 1, name: "שמרנית", status: "draft", version: 2,
    created_by: "planner", updated_by: "planner", decisions: [], financial_validation: "not_evaluated" },
  { scenario_id: "b", client_id: 1, name: "צמיחה", status: "draft", version: 3,
    created_by: "planner", updated_by: "planner", decisions: [], financial_validation: "not_evaluated" },
];

function result(overrides: Partial<ScenarioMonthlyComparison> = {}): ScenarioMonthlyComparison {
  const identity = (id: string, version: number) => ({
    scenario_id: id, scenario_version: version, manifest_fingerprint: H, cashflow_fingerprint: H,
    sources: [{ source_id: `recurring:${id}`, source_kind: "KNOWN_RECURRING_INCOME" as const,
      authority_fingerprint: H, source_state: "READY" as const }],
  });
  return {
    schema_version: "STAGE6_SCENARIO_MONTHLY_COMPARISON_V1", client_id: 1,
    start_month: "2030-01", end_month: "2030-02", comparison_state: "COMPLETE",
    target_comparison_state: "COMPLETE",
    scenario_a: identity("a", 2), scenario_b: identity("b", 3),
    shared_source_ids: [],
    target: { target_state: "GROSS_NOMINAL_TARGET_MONTH_ONLY", monthly_amount_ils: "6500",
      income_basis: "GROSS", price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE",
      retirement_target_date: "2030-01-15", target_semantic_fingerprint: H,
      target_result_fingerprint: H, blocker_codes: [] },
    monthly_rows: [
      { month: "2030-01", comparison_state: "COMPLETE", scenario_a_gross_income_ils: "5000",
        scenario_b_gross_income_ils: "7000", scenario_b_minus_a_gross_ils: "2000",
        target_comparison_state: "COMPLETE", target_gross_income_ils: "6500",
        scenario_a_minus_target_gross_ils: "-1500", scenario_b_minus_target_gross_ils: "500",
        change_events: { scenario_a_started_source_ids: ["recurring:a"], scenario_a_ended_source_ids: [],
          scenario_b_started_source_ids: ["recurring:b"], scenario_b_ended_source_ids: [] }, blocker_codes: [] },
      { month: "2030-02", comparison_state: "COMPLETE", scenario_a_gross_income_ils: "5000",
        scenario_b_gross_income_ils: "7000", scenario_b_minus_a_gross_ils: "2000",
        target_comparison_state: "BLOCKED", target_gross_income_ils: null,
        scenario_a_minus_target_gross_ils: null, scenario_b_minus_target_gross_ils: null,
        change_events: { scenario_a_started_source_ids: [], scenario_a_ended_source_ids: [],
          scenario_b_started_source_ids: [], scenario_b_ended_source_ids: [] },
        blocker_codes: ["STAGE6_COMPARISON_TARGET_OUTSIDE_COMPARABLE_MONTH"] },
    ], execution_allowed: false, comparison_fingerprint: H,
    ...overrides,
  };
}

async function submit() {
  await act(async () => {
    fireEvent.change(screen.getByLabelText("חודש התחלה"), { target: { value: "2030-01" } });
    fireEvent.change(screen.getByLabelText("חודש סיום"), { target: { value: "2030-02" } });
    fireEvent.click(screen.getByRole("button", { name: "השווה תזרים חודשי" }));
    await Promise.resolve();
  });
}

describe("ScenarioMonthlyComparisonPanel", () => {
  beforeEach(() => api.read.mockReset());

  it("renders server-authoritative gross comparison and target gap without frontend arithmetic", async () => {
    api.read.mockResolvedValue(result());
    render(<ScenarioMonthlyComparisonPanel clientId={1} scenarios={drafts}/>);
    await submit();
    expect(await screen.findByText("השוואת החלופות הושלמה לכל החודשים.")).toBeInTheDocument();
    expect(screen.getByText("-1500 ₪ (חוסר)")).toBeInTheDocument();
    expect(screen.getByText("500 ₪ (עודף)")).toBeInTheDocument();
    expect(screen.getAllByText("2000 ₪")).toHaveLength(2);
    expect(screen.getByText(/התחלה א׳: recurring:a.*התחלה ב׳: recurring:b/)).toBeInTheDocument();
    expect(api.read).toHaveBeenCalledWith(1, {
      scenario_a_id: "a", scenario_a_version: 2, scenario_b_id: "b", scenario_b_version: 3,
      start_month: "2030-01", end_month: "2030-02",
    }, expect.any(AbortSignal));
  });

  it("suppresses financial-looking amounts for a blocked month and explains a net target", async () => {
    const blocked = result({
      comparison_state: "PARTIAL",
      target_comparison_state: "BLOCKED",
      target: { ...result().target, target_state: "NET_NOT_COMPARABLE", income_basis: "NET",
        monthly_amount_ils: "6000", blocker_codes: ["STAGE6_COMPARISON_NET_TARGET_NOT_COMPARABLE"] },
      monthly_rows: [
        { ...result().monthly_rows[0], comparison_state: "BLOCKED",
          scenario_a_gross_income_ils: null, scenario_b_gross_income_ils: null,
          scenario_b_minus_a_gross_ils: null, target_comparison_state: "BLOCKED",
          target_gross_income_ils: null, scenario_a_minus_target_gross_ils: null,
          scenario_b_minus_target_gross_ils: null,
          blocker_codes: ["STAGE6_COMPARISON_SCENARIO_B_INCOMPLETE"] },
        { ...result().monthly_rows[1], target_comparison_state: "BLOCKED" },
      ],
    });
    api.read.mockResolvedValue(blocked);
    render(<ScenarioMonthlyComparisonPanel clientId={1} scenarios={drafts}/>);
    await submit();
    expect(await screen.findByText(/יעד ההכנסה הוא נטו/)).toBeInTheDocument();
    expect(screen.getAllByText("לא זמין").length).toBeGreaterThan(2);
    expect(screen.getByText("חלופה ב׳ אינה מלאה בחודש זה.")).toBeInTheDocument();
  });

  it("rejects a forged response-client identity and drops late responses after a version change", async () => {
    let resolveFirst!: (value: ScenarioMonthlyComparison) => void;
    api.read.mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve; }));
    const view = render(<ScenarioMonthlyComparisonPanel clientId={1} scenarios={drafts}/>);
    await submit();
    const revised = [{ ...drafts[0], version: 4 }, drafts[1]];
    view.rerender(<ScenarioMonthlyComparisonPanel clientId={1} scenarios={revised}/>);
    await act(async () => { resolveFirst(result()); await Promise.resolve(); });
    await waitFor(() => expect(screen.queryByText("השוואת החלופות הושלמה לכל החודשים.")).not.toBeInTheDocument());

    api.read.mockResolvedValueOnce(result({ client_id: 99,
      scenario_a: { ...result().scenario_a, scenario_version: 4 } }));
    await submit();
    expect(await screen.findByRole("alert")).toHaveTextContent("STAGE6_COMPARISON_RESPONSE_INVALID");
  });
});
