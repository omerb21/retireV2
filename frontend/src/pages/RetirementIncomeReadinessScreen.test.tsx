import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { RetirementIncomeReadinessScreen } from "./RetirementIncomeReadinessScreen";

const context = {
  schema_version: "RTDIR_PLANNING_CONTEXT_V1", client_id: 7,
  planning_calculation_input_fingerprint: "a".repeat(64), planning_input_ready: true,
  retirement_target_date: "2035-04-01", retirement_target_ready: true,
  blocking_facts: [],
};
const target = {
  schema_version: "CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_V1",
  client_id: 7, planning_calculation_input_fingerprint: "a".repeat(64),
  retirement_target_date: "2035-04-01",
  target: {monthly_amount: "12000.00", income_basis: "GROSS", price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date: null},
  authority: {record_version: 3, source_kind: "PLANNER_SUPPLIED", confirmation_actor: "planner", confirmed_at: "2030-01-01T00:00:00Z", lifecycle_state: "CURRENT"},
  authority_state: "CURRENT", target_readiness_state: "READY", target_ready: true,
  blockers: [], target_semantic_fingerprint: "b".repeat(64), target_result_fingerprint: "c".repeat(64),
};
const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), {status: 200, headers: {"Content-Type": "application/json"}}));

function renderScreen() {
  return render(<MemoryRouter initialEntries={["/clients/7/retirement-income-readiness"]}><Routes>
    <Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} />
  </Routes></MemoryRouter>);
}

afterEach(() => vi.unstubAllGlobals());

test("renders exact readiness evidence and preserves block_no_result as a professional result", async () => {
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response({
      schema_version: "RTICB_RESULT_V1", client_id: 7, result_state: "block_no_result",
      failure_stage: "source_admission", failure_detail_code: "RTICB_SOURCE_ADMISSION_NOT_READY",
    }));
  vi.stubGlobal("fetch", fetcher);
  renderScreen();
  expect(await screen.findByText("קלט התכנון מוכן")).toBeInTheDocument();
  expect(screen.getByText(/01\/04\/2035/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText(/RTICB_SOURCE_ADMISSION_NOT_READY/)).toBeInTheDocument();
  const request = fetcher.mock.calls[2];
  expect(request[0]).toContain("/clients/7/retirement-income-readiness/comparison");
  expect(JSON.parse(request[1].body)).toEqual({
    expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_retirement_target_date: "2035-04-01",
  });
});

test("confirms only accepted fields, then discards and reloads context before target", async () => {
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target));
  vi.stubGlobal("fetch", fetcher);
  renderScreen();
  const amount = await screen.findByLabelText("סכום חודשי");
  fireEvent.change(amount, {target: {value: "13000.50"}});
  fireEvent.click(screen.getByRole("button", {name: "אישור מפורש של היעד"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
  const saved = JSON.parse(fetcher.mock.calls[2][1].body);
  expect(saved).toEqual({
    expected_record_version: 3,
    expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_retirement_target_date: "2035-04-01",
    monthly_amount: "13000.50", income_basis: "GROSS",
    price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date: null,
    source_kind: "PLANNER_SUPPLIED",
  });
  expect(saved).not.toHaveProperty("client_id");
  expect(saved).not.toHaveProperty("trusted_professional_actor");
  expect(fetcher.mock.calls[3][0]).toContain("/context");
  expect(fetcher.mock.calls[4][0]).toContain("/target");
});
