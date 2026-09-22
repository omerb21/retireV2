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

const targetView = (saved: string | null = null) => ({...view(), retirement_target: {
  contract_version: "canonical-retirement-target-date-authority-v1", retirement_target_date: saved,
  current_reference_fingerprint: "a".repeat(64), relation_to_planning_base: "base_missing",
  retirement_target_ready: false, blockers: [], warnings: ["target_reference_dates_conflict"],
}, target_reference_facts: [
  {reference_id: "client:1:planned_retirement_age", source_id: "client:1", source_field: "planned_retirement_age",
   value_kind: "age", age_value: 67, date_value: null, lifecycle_state: "current", unresolved_state: []},
  {reference_id: "client:1:planned_retirement_date", source_id: "client:1", source_field: "planned_retirement_date",
   value_kind: "date", date_value: "2040-01-02", age_value: null, lifecycle_state: "current", unresolved_state: []},
]});

it("target references never preselect, age is not converted, date helper is unsaved", async () => {
  const fetcher = vi.fn().mockResolvedValue(response(targetView())); vi.stubGlobal("fetch", fetcher);
  const {container} = renderPage();
  const input = await screen.findByLabelText("תאריך יעד לפרישה");
  expect(input).toHaveValue("");
  expect(screen.getByText(/גיל 67/)).toBeVisible();
  expect(screen.getByText("קיימים תאריכי ייחוס שונים — ללא עדיפות אוטומטית")).toBeVisible();
  expect(screen.getAllByRole("button", {name: "העתקת תאריך הייחוס לשדה היעד"})).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", {name: "העתקת תאריך הייחוס לשדה היעד"}));
  expect(input).toHaveValue("02/01/2040");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(container.querySelector('main')).toHaveAttribute('dir', 'rtl');
  expect(container.querySelector('input[type="date"]')).toBeNull();
  fireEvent.click(screen.getByRole("button", {name: "שמירת תאריך היעד"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  expect(fetcher.mock.calls[1][0]).toContain('/target-date');
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({expected_version: 0,
    expected_target_reference_fingerprint: "a".repeat(64), retirement_target_date: "2040-01-02"});
});

it("target explicit clear submits null and refreshes canonical input", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(response(targetView("2040-01-02")))
    .mockResolvedValueOnce(response({decision_version: 1})).mockResolvedValue(response({...targetView(), decision_version: 1}));
  vi.stubGlobal("fetch", fetcher); renderPage();
  expect(await screen.findByLabelText("תאריך יעד לפרישה")).toHaveValue("02/01/2040");
  fireEvent.click(screen.getByRole("button", {name: "ניקוי מפורש של תאריך היעד"}));
  await waitFor(() => expect(screen.getByLabelText("תאריך יעד לפרישה")).toHaveValue(""));
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({expected_version: 0,
    expected_target_reference_fingerprint: "a".repeat(64), retirement_target_date: null});
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it("does not automatically retry a stale target decision", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(response(targetView("2040-01-02")))
    .mockResolvedValue({ok: false, json: async () => ({detail: {code: "TARGET_REFERENCE_STATE_STALE", message: "עובדות הייחוס השתנו"}})});
  vi.stubGlobal("fetch", fetcher); renderPage();
  await screen.findByLabelText("תאריך יעד לפרישה");
  fireEvent.click(screen.getByRole("button", {name: "שמירת תאריך היעד"}));
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

const projectionView = (rate: string | null = null, version = 2) => ({...targetView(), decision_version: version,
  projection_basis: {client_id: 1, decision_version: version, planning_calculation_input_fingerprint: 'p'.repeat(64),
    projection_basis_ready: false, aggregate_blockers: ['RATE_MISSING'], noncurrent_or_historical_bound_decisions: [],
    covered_capital_sources: [1,2].map(id => ({source_id: `capital:${id}`, capital_asset_id: id,
      source_semantic_fingerprint: String(id).repeat(64), projection_timing_context_fingerprint: 't'.repeat(64),
      known_value_amount: id === 1 ? '100.00' : null, value_as_of_date: id === 1 ? '2026-09-01' : null,
      economic_projection_start_date: id === 1 ? '2026-09-01' : null, retirement_target_date: '2030-01-01',
      annual_rate: id === 1 ? rate : null, return_basis: id === 1 && rate !== null ? 'NET' : null,
      price_basis: id === 1 && rate !== null ? 'REAL' : null, projection_basis_source_readiness: false,
      blockers: id === 1 ? ['RATE_MISSING'] : ['SOURCE_VALUE_UNRESOLVED','VALUATION_DATE_MISSING'], warnings: []}))}});

it('covers incomplete capital sources without rate or basis defaults and preserves exact strings', async () => {
  const fetcher=vi.fn().mockResolvedValue(response(projectionView())); vi.stubGlobal('fetch',fetcher); renderPage();
  const rate=await screen.findByLabelText('שיעור שנתי למקור 1');
  expect(rate).toHaveValue(''); expect(screen.getByLabelText('שיעור שנתי למקור 2')).toHaveValue('');
  expect(screen.getByLabelText('בסיס תשואה למקור 1')).toHaveValue('');
  expect(screen.getByLabelText('בסיס מחירים למקור 1')).toHaveValue('');
  expect(screen.getByText('שווי המקור חסר או אינו תקין')).toBeVisible();
  expect(screen.getByText('חסר תאריך שווי')).toBeVisible();
  const exact='123456789012345678901234567890.1234567890123456789';
  fireEvent.change(rate,{target:{value:exact}});
  fireEvent.change(screen.getByLabelText('בסיס תשואה למקור 1'),{target:{value:'NET'}});
  fireEvent.change(screen.getByLabelText('בסיס מחירים למקור 1'),{target:{value:'REAL'}});
  fireEvent.click(screen.getByRole('button',{name:'שמירת הנחות למקור 1'}));
  await waitFor(()=>expect(fetcher).toHaveBeenCalledTimes(3));
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({expected_version:2,
    expected_planning_calculation_input_fingerprint:'p'.repeat(64),expected_source_semantic_fingerprint:'1'.repeat(64),
    expected_timing_context_fingerprint:'t'.repeat(64),annual_rate:exact,return_basis:'NET',price_basis:'REAL'});
  expect(fetcher.mock.calls[1][0]).toContain('/projection-basis/1');
});

it('projection clear is explicit, source-specific and refreshes to missing rather than default rate',async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce(response(projectionView('0')))
    .mockResolvedValueOnce(response({decision_version:3})).mockResolvedValue(response(projectionView(null,3)));
  vi.stubGlobal('fetch',fetcher); renderPage();
  expect(await screen.findByLabelText('שיעור שנתי למקור 1')).toHaveValue('0');
  fireEvent.click(screen.getByRole('button',{name:'ניקוי הנחות למקור 1'}));
  await waitFor(()=>expect(screen.getByLabelText('שיעור שנתי למקור 1')).toHaveValue(''));
  expect(fetcher.mock.calls[1][0]).toContain('/projection-basis/1/clear');
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).not.toHaveProperty('annual_rate');
});

it('projection input rejects noncanonical rates and allows explicit zero without automatic requests',async()=>{
  const fetcher=vi.fn().mockResolvedValue(response(projectionView())); vi.stubGlobal('fetch',fetcher); renderPage();
  const rate=await screen.findByLabelText('שיעור שנתי למקור 1');
  fireEvent.change(screen.getByLabelText('בסיס תשואה למקור 1'),{target:{value:'GROSS'}});
  fireEvent.change(screen.getByLabelText('בסיס מחירים למקור 1'),{target:{value:'NOMINAL'}});
  for(const bad of ['-1','1e2','NaN','0.00',' 0','+0.2','-0']) {
    fireEvent.change(rate,{target:{value:bad}});
    expect(screen.getByRole('button',{name:'שמירת הנחות למקור 1'})).toBeDisabled();
  }
  fireEvent.change(rate,{target:{value:'0'}});
  expect(screen.getByRole('button',{name:'שמירת הנחות למקור 1'})).toBeEnabled();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

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
