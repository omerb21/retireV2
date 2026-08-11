import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { M09CashflowScreen } from "./M09CashflowScreen";
import type { M09Currentness, M09Eligibility, M09Inventory, M09Run, M09RunSummary } from "../api/m09CashflowApi";
import * as api from "../api/m09CashflowApi";
import { ApiTransportError } from "../api/clientsApi";

vi.mock("../api/m09CashflowApi", async () => {
  const actual = await vi.importActual<typeof import("../api/m09CashflowApi")>("../api/m09CashflowApi");
  return { ...actual, assessM09Inventory: vi.fn(), executeM09Run: vi.fn(), listM09Runs: vi.fn(), getM09Run: vi.fn(), getM09Currentness: vi.fn(), getM09Eligibility: vi.fn() };
});

type Deferred<T> = { promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void };
function deferred<T>(): Deferred<T> { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
const mock = <T extends (...args: never[]) => unknown>(value: T) => vi.mocked(value);

function inventory(clientId: number, marker: string): M09Inventory {
  return { inventory_id: `inventory-${marker}`, client_id: clientId, scenario_family: "deterministic_monthly_cashflow", scenario_contract_version: "v1", start_month: "2026-01", end_month: "2026-02", component_domain_contract_version: "m09-component-domains-v1", assessment_timestamp: "2026-08-11T00:00:00Z", actor: "system:m09-cashflow:M09 cashflow workflow", actor_is_authentication: false, domains: [{ domain: marker }], complete: true, blocker_codes: [], inventory_fingerprint: `fingerprint-${marker}` };
}
function currentness(id: string): M09Currentness { return { run_id: id, current_run_id: id, is_current: true, reason_codes: [], assessment_timestamp: "2026-08-11T00:00:00Z", assessment_contract_version: "m09-currentness-v1" }; }
function eligibility(id: string): M09Eligibility { return { assessed_scenario_run_id: id, current_scenario_run_id: id, eligible_for_m10: true, reason_codes: [], informational_warnings: [], assessment_timestamp: "2026-08-11T00:00:00Z", eligibility_contract_version: "m09-to-m10-eligibility-v1" }; }
function run(clientId: number, marker: string): M09Run {
  const id = `run-${marker}`; return { run_id: id, client_id: clientId, predecessor_run_id: null, run_sequence: 1, scenario_family: "deterministic_monthly_cashflow", scenario_contract_version: "v1", start_month: "2026-01", end_month: "2026-02", inventory: inventory(clientId, marker), status: "success_complete", assumption_manifest: {}, assumption_manifest_fingerprint: "a", upstream_snapshot: {}, upstream_snapshot_fingerprint: "b", warnings: [], blocker_codes: [], monthly_results: [{ monthly_result_id: `month-${marker}`, month: "2026-01", gross_inflow_total: "100.00", gross_outflow_total: "40.00", period_net: "60.00", component_evidence: [], result_fingerprint: "c" }], range_totals: { gross_inflow_total: "100.00", gross_outflow_total: "40.00", period_net: "60.00" }, semantic_result_fingerprint: `semantic-${marker}`, result_integrity_fingerprint: "d", currentness: currentness(id), m10_eligibility: eligibility(id), actor: "system:m09-cashflow:M09 cashflow workflow", actor_is_authentication: false, created_at: "2026-08-11T00:00:00Z" };
}
function summary(clientId: number, marker: string): M09RunSummary { const value = run(clientId, marker); return { run_id: value.run_id, predecessor_run_id: null, run_sequence: 1, status: value.status, start_month: value.start_month, end_month: value.end_month, inventory_id: value.inventory.inventory_id, blocker_codes: [], semantic_result_fingerprint: value.semantic_result_fingerprint, is_current: true, eligible_for_m10: true, created_at: value.created_at }; }

function Navigation() { const navigate = useNavigate(); const location = useLocation(); return <><button onClick={() => navigate("/clients/2/monthly-cashflow")}>B</button><button onClick={() => navigate("/clients/1/monthly-cashflow", { state: { revisit: Math.random() } })}>A revisit</button><output aria-label="route generation">{location.key}</output></>; }
function renderScreen() { return render(<MemoryRouter initialEntries={["/clients/1/monthly-cashflow"]}><Navigation /><Routes><Route path="/clients/:clientId/monthly-cashflow" element={<M09CashflowScreen />} /></Routes></MemoryRouter>); }
function horizon() { fireEvent.change(screen.getByLabelText("Start month"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("End month"), { target: { value: "2026-02" } }); }
async function settled() { await waitFor(() => expect(screen.queryByText("Loading M09 evidence…")).not.toBeInTheDocument()); }
async function switchClient(name: "B" | "A revisit", clientId: number) { const previous = screen.getByLabelText("route generation").textContent; fireEvent.click(screen.getByRole("button", { name })); await waitFor(() => expect(screen.getByLabelText("route generation").textContent).not.toBe(previous)); await waitFor(() => expect(screen.getByRole("link", { name: "Back to client" })).toHaveAttribute("href", `/clients/${clientId}`)); }
async function navigate(name: "B" | "A revisit", clientId: number) { await switchClient(name, clientId); await settled(); }
const structuredError = (marker: string) => new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { code: marker } } });

describe("M09CashflowScreen client-generation isolation", () => {
  beforeEach(() => { vi.clearAllMocks(); mock(api.listM09Runs).mockResolvedValue([]); });

  it("ignores inventory A-to-B stale success and stale finally while B remains pending", async () => {
    const oldA = deferred<M09Inventory>(); const activeB = deferred<M09Inventory>();
    mock(api.assessM09Inventory).mockImplementation((clientId) => clientId === 1 ? oldA.promise : activeB.promise);
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" }));
    await navigate("B", 2); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" }));
    await act(async () => oldA.resolve(inventory(1, "old-a"))); expect(screen.queryByText(/fingerprint-old-a/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve(inventory(2, "active-b"))); expect(await screen.findByText(/fingerprint-active-b/)).toBeInTheDocument(); await settled();
  });

  it("ignores stale execution rejection/structured error and accepts the new owner result", async () => {
    const oldA = deferred<M09Run>(); const activeB = deferred<M09Run>(); mock(api.executeM09Run).mockImplementation((clientId) => clientId === 1 ? oldA.promise : activeB.promise);
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" })); await navigate("B", 2); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" }));
    await act(async () => oldA.reject(new Error("structured stale A error"))); expect(screen.queryByText(/structured stale A error/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve(run(2, "active-b"))); expect(await screen.findByText(/Range totals: inflows 100.00/)).toBeInTheDocument(); expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps old-A work stale after A-to-B-to-A and lets the new-A request succeed", async () => {
    const oldA = deferred<M09Inventory>(); const newA = deferred<M09Inventory>(); let aCalls = 0;
    mock(api.assessM09Inventory).mockImplementation((clientId) => clientId === 1 ? (++aCalls === 1 ? oldA.promise : newA.promise) : Promise.resolve(inventory(2, "b")));
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" })); await navigate("B", 2); await navigate("A revisit", 1); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" }));
    await act(async () => oldA.resolve(inventory(1, "old-a"))); expect(screen.queryByText(/fingerprint-old-a/)).not.toBeInTheDocument(); await act(async () => newA.resolve(inventory(1, "new-a"))); expect(await screen.findByText(/fingerprint-new-a/)).toBeInTheDocument();
  });

  it("isolates history and saved-result loads across clients", async () => {
    const oldHistory = deferred<M09RunSummary[]>(); const oldResult = deferred<M09Run>();
    mock(api.listM09Runs).mockImplementation((clientId) => clientId === 1 ? oldHistory.promise : Promise.resolve([summary(2, "b")]));
    mock(api.getM09Run).mockImplementation((clientId) => clientId === 1 ? oldResult.promise : Promise.resolve(run(2, "b")));
    mock(api.getM09Currentness).mockResolvedValue(currentness("run-b")); mock(api.getM09Eligibility).mockResolvedValue(eligibility("run-b"));
    renderScreen(); await navigate("B", 2); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Load run 1" }));
    await act(async () => { oldHistory.resolve([summary(1, "old-a")]); oldResult.resolve(run(1, "old-a")); }); expect(screen.queryByText(/old-a/)).not.toBeInTheDocument(); expect(await screen.findByText(/Range totals: inflows 100.00/)).toBeInTheDocument();
  });

  it("ignores inventory stale structured rejection without clearing B loading", async () => {
    const oldA = deferred<M09Inventory>(); const activeB = deferred<M09Inventory>();
    mock(api.assessM09Inventory).mockImplementation((clientId) => clientId === 1 ? oldA.promise : activeB.promise);
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" }));
    await navigate("B", 2); horizon(); fireEvent.click(screen.getByRole("button", { name: "Assess server inventory" }));
    await act(async () => oldA.reject(structuredError("stale_inventory"))); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve(inventory(2, "inventory-b"))); expect(await screen.findByText(/fingerprint-inventory-b/)).toBeInTheDocument();
  });

  it("ignores execute A-to-B stale success and stale finally while B is pending", async () => {
    const oldA = deferred<M09Run>(); const activeB = deferred<M09Run>();
    mock(api.executeM09Run).mockImplementation((clientId) => clientId === 1 ? oldA.promise : activeB.promise);
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" }));
    await navigate("B", 2); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" }));
    await act(async () => oldA.resolve(run(1, "execute-old-a"))); expect(screen.queryByText(/execute-old-a/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve(run(2, "execute-b"))); expect(await screen.findByText(/Range totals: inflows 100.00/)).toBeInTheDocument();
  });

  it("distinguishes execute old-A from new-A after A-to-B-to-A", async () => {
    const oldA = deferred<M09Run>(); const newA = deferred<M09Run>(); let calls = 0;
    mock(api.executeM09Run).mockImplementation((clientId) => clientId === 1 ? (++calls === 1 ? oldA.promise : newA.promise) : Promise.resolve(run(2, "execute-b")));
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" })); await navigate("B", 2); await navigate("A revisit", 1); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" }));
    await act(async () => oldA.reject(new Error("stale execute rejection"))); expect(screen.queryByText(/stale execute rejection/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => newA.resolve(run(1, "execute-new-a"))); expect((await screen.findAllByText(/execute-new-a/)).length).toBeGreaterThan(0);
  });

  it("ignores a separately structured stale execute API error", async () => {
    const oldA = deferred<M09Run>(); mock(api.executeM09Run).mockImplementation((clientId) => clientId === 1 ? oldA.promise : Promise.resolve(run(2, "b")));
    renderScreen(); await settled(); horizon(); fireEvent.click(screen.getByRole("button", { name: "Execute complete inventory" })); await navigate("B", 2);
    await act(async () => oldA.reject(structuredError("stale_execute_structured"))); expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("protects history from stale rejection/error/finally while new owner is pending", async () => {
    const oldA = deferred<M09RunSummary[]>(); const activeB = deferred<M09RunSummary[]>();
    mock(api.listM09Runs).mockImplementation((clientId) => clientId === 1 ? oldA.promise : activeB.promise);
    renderScreen(); await switchClient("B", 2); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => oldA.reject(structuredError("stale_history"))); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve([summary(2, "history-b")])); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); await settled();
  });

  it("distinguishes history old-A from pending new-A after A-to-B-to-A", async () => {
    const oldA = deferred<M09RunSummary[]>(); const newA = deferred<M09RunSummary[]>(); let calls = 0;
    mock(api.listM09Runs).mockImplementation((clientId) => clientId === 1 ? (++calls === 1 ? oldA.promise : newA.promise) : Promise.resolve([]));
    renderScreen(); await navigate("B", 2); await switchClient("A revisit", 1);
    await act(async () => oldA.resolve([summary(1, "history-old-a")])); expect(screen.queryByText(/history-old-a/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => newA.resolve([summary(1, "history-new-a")])); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); await settled();
  });

  it("starts old-A composite load before navigation and rejects its success/finally", async () => {
    const oldRun = deferred<M09Run>(); const oldCurrent = deferred<M09Currentness>(); const oldEligibility = deferred<M09Eligibility>();
    const bRun = deferred<M09Run>(); const bCurrent = deferred<M09Currentness>(); const bEligibility = deferred<M09Eligibility>();
    mock(api.listM09Runs).mockImplementation((clientId) => Promise.resolve([summary(clientId, clientId === 1 ? "a" : "b")]));
    mock(api.getM09Run).mockImplementation((clientId) => clientId === 1 ? oldRun.promise : bRun.promise);
    mock(api.getM09Currentness).mockImplementation((clientId) => clientId === 1 ? oldCurrent.promise : bCurrent.promise);
    mock(api.getM09Eligibility).mockImplementation((clientId) => clientId === 1 ? oldEligibility.promise : bEligibility.promise);
    renderScreen(); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Load run 1" }));
    await navigate("B", 2); fireEvent.click(screen.getByRole("button", { name: "Load run 1" }));
    await act(async () => { oldRun.resolve(run(1, "composite-old-a")); oldCurrent.resolve(currentness("run-a")); oldEligibility.resolve(eligibility("run-a")); });
    expect(screen.queryByText(/composite-old-a/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => { bRun.resolve(run(2, "composite-b")); bCurrent.resolve(currentness("run-b")); bEligibility.resolve(eligibility("run-b")); });
    expect(await screen.findByText(/Range totals: inflows 100.00/)).toBeInTheDocument();
  });

  it("ignores old-A composite structured rejection while B remains owned", async () => {
    const oldRun = deferred<M09Run>(); const activeB = deferred<M09Run>();
    mock(api.listM09Runs).mockImplementation((clientId) => Promise.resolve([summary(clientId, clientId === 1 ? "a" : "b")]));
    mock(api.getM09Run).mockImplementation((clientId) => clientId === 1 ? oldRun.promise : activeB.promise);
    mock(api.getM09Currentness).mockImplementation((_clientId, id) => Promise.resolve(currentness(id)));
    mock(api.getM09Eligibility).mockImplementation((_clientId, id) => Promise.resolve(eligibility(id)));
    renderScreen(); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Load run 1" })); await navigate("B", 2); fireEvent.click(screen.getByRole("button", { name: "Load run 1" }));
    await act(async () => oldRun.reject(structuredError("stale_composite"))); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => activeB.resolve(run(2, "composite-active-b"))); expect(await screen.findByText(/Range totals: inflows 100.00/)).toBeInTheDocument();
  });

  it("distinguishes composite old-A from new-A after A-to-B-to-A", async () => {
    const oldA = deferred<M09Run>(); const newA = deferred<M09Run>(); let aCalls = 0;
    mock(api.listM09Runs).mockImplementation((clientId) => Promise.resolve([summary(clientId, clientId === 1 ? "a" : "b")]));
    mock(api.getM09Run).mockImplementation((clientId) => clientId === 1 ? (++aCalls === 1 ? oldA.promise : newA.promise) : Promise.resolve(run(2, "b")));
    mock(api.getM09Currentness).mockImplementation((_clientId, id) => Promise.resolve(currentness(id)));
    mock(api.getM09Eligibility).mockImplementation((_clientId, id) => Promise.resolve(eligibility(id)));
    renderScreen(); expect(await screen.findByRole("button", { name: "Load run 1" })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: "Load run 1" })); await navigate("B", 2); await navigate("A revisit", 1); fireEvent.click(screen.getByRole("button", { name: "Load run 1" }));
    await act(async () => oldA.resolve(run(1, "composite-old-a"))); expect(screen.queryByText(/composite-old-a/)).not.toBeInTheDocument(); expect(screen.getByText("Loading M09 evidence…")).toBeInTheDocument();
    await act(async () => newA.resolve(run(1, "composite-new-a"))); expect((await screen.findAllByText(/composite-new-a/)).length).toBeGreaterThan(0);
  });

  it("offers no component omission or run-anyway control", async () => { renderScreen(); await settled(); expect(screen.queryByRole("checkbox")).not.toBeInTheDocument(); expect(screen.queryByText(/run anyway/i)).not.toBeInTheDocument(); });
});
