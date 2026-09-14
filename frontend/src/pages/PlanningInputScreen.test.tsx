import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useNavigate } from "react-router-dom";
import { afterEach, it, expect, vi } from "vitest";
import { PlanningInputScreen } from "./PlanningInputScreen";

const view = (client_id = 1) => ({client_id, decision_version: 0, planning_base_date: null, planning_input_ready: false,
  date_candidates: [{source_id: "client:1", field: "planned_retirement_date", date: "2040-01-02"}],
  pension_inputs: [], general_income_inputs: [], expense_inputs: [], capital_inputs: [], reference_only: [],
  excluded_sources: [], unresolved_items: [], warnings: [], blocking_facts: [{source_id: null, code: "planning_base_date_missing"}]});
const response = (body: unknown) => ({ok: true, json: async () => body});
function renderPage() {return render(<MemoryRouter initialEntries={["/clients/1/planning-input"]}><Routes>
  <Route path="/clients/:clientId/planning-input" element={<PlanningInputScreen />} /></Routes></MemoryRouter>);}
afterEach(() => vi.unstubAllGlobals());

it("requires explicit date confirmation and sends exact version", async () => {
  const fetcher = vi.fn().mockResolvedValue(response(view())); vi.stubGlobal("fetch", fetcher);
  const {container} = renderPage();
  await screen.findByText("לא נבחר מועד בסיס לתכנון");
  expect(screen.getByLabelText("מועד בסיס מפורש")).toHaveValue("");
  expect(container.querySelector('input[type="date"]')).toBeNull();
  fireEvent.click(screen.getByRole("button", {name: "בחירת מועד זה לאישור"}));
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("מועד בסיס מפורש")).toHaveValue("02/01/2040");
  fireEvent.click(screen.getByRole("button", {name: "אישור מועד הבסיס"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({expected_version: 0, planning_base_date: "2040-01-02"});
});

it("shows exact ratios and incomplete capital without defaults or totals", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({...view(),
    general_income_inputs: [{source_id: "income:1", description: "הכנסה", amount: "0.01", frequency: "quarterly", amount_basis: "gross", inclusion_state: "included", monthly_equivalent_ratio: {numerator: "0.01", denominator: 3}}],
    capital_inputs: [{source_id: "capital:1", asset_description: "נכס", known_value_amount: "123.45", value_as_of_date: null, inclusion_state: "unresolved", blocking_facts: ["capital_valuation_date_missing"]}]})));
  renderPage();
  expect(await screen.findByText("0.01 / 3")).toBeVisible();
  expect(screen.getByText("חסר תאריך שווי הון")).toBeVisible();
  expect(screen.queryByText("0.00")).toBeNull();
});

it("resolves a pension identity only with an explicit selected canonical source", async () => {
  const fetcher = vi.fn().mockResolvedValue(response({...view(),
    excluded_sources: [{source_id: "income:3", id: 3, description: "קצבה לבדיקה", inclusion_state: "unresolved", source_fingerprint: "a".repeat(64)}],
    pension_inputs: [{source_id: "manual:1", payer_name: "משלם", inclusion_state: "included", source_fingerprint: "b".repeat(64)}]}));
  vi.stubGlobal("fetch", fetcher); renderPage();
  await screen.findByLabelText("מקור קצבה לקישור");
  expect(screen.getByLabelText("מקור קצבה לקישור")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("מקור קצבה לקישור"), {target: {value: "manual:1"}});
  fireEvent.change(screen.getByLabelText("אסמכתה להכרעה"), {target: {value: "החלטה מפורשת"}});
  fireEvent.click(screen.getByRole("button", {name: "אישור הכרעת זהות"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({canonical_source_id: "manual:1", expected_income_fingerprint: "a".repeat(64), expected_canonical_fingerprint: "b".repeat(64)});
});

it("rejects wrong-client server responses", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(2)))); renderPage();
  expect(await screen.findByRole("alert")).toHaveTextContent("שיוך הקלט ללקוח אינו תקין");
});

it("discards late client A results after navigating to B", async () => {
  const pending: Array<(value: unknown) => void> = [];
  vi.stubGlobal("fetch", vi.fn(() => new Promise(resolve => pending.push(resolve))));
  function Nav() {const navigate = useNavigate(); return <button onClick={() => navigate("/clients/2/planning-input")}>לקוח אחר</button>;}
  render(<MemoryRouter initialEntries={["/clients/1/planning-input"]}><Nav /><Routes><Route path="/clients/:clientId/planning-input" element={<PlanningInputScreen />} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByText("לקוח אחר"));
  await act(async () => pending[1](response({...view(2), planning_base_date: "2030-01-01"})));
  await act(async () => pending[0](response({...view(1), planning_base_date: "2040-01-01"})));
  expect(screen.getByLabelText("מועד בסיס מפורש")).toHaveValue("01/01/2030");
});
