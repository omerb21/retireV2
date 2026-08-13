import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/m09CashflowApi";
import { ApiTransportError } from "../api/clientsApi";
import { M09ScenarioSubjects } from "./M09ScenarioSubjects";

vi.mock("../api/m09CashflowApi", async () => {
  const actual = await vi.importActual<typeof import("../api/m09CashflowApi")>("../api/m09CashflowApi");
  return { ...actual, listM09Subjects: vi.fn(), resolveM09BaselineSubject: vi.fn(), createM09AdjustedSubject: vi.fn(), getM09Subject: vi.fn(), listM09SubjectRuns: vi.fn(), executeM09SubjectRun: vi.fn(), getM09SubjectRun: vi.fn(), getM09SubjectCurrentness: vi.fn(), getM09SubjectEligibility: vi.fn() };
});
const mocked = <T extends (...args: never[]) => unknown>(fn: T) => vi.mocked(fn);
const adjustment = (id: string, amount = "100.00"): api.M09ScenarioSubject["adjustments"][number] => ({ adjustment_id: id, ordinal: Number(id.replace(/\D/g, "")) || 1, adjustment_type: "declared_additional_monthly_income", amount, start_month: "2026-01", end_month: "2026-02", provenance: "planner_declared_scenario_adjustment", semantic_fingerprint: "d".repeat(64), actor: "system:m09", created_at: "2026-08-12T00:00:00Z" });
const subject = (id: string, clientId = 1, displayLabel = "Alternative", values: api.M09ScenarioSubject["adjustments"] = []): api.M09ScenarioSubject => ({ scenario_subject_id: id, client_id: clientId, scenario_family: api.M09_SUBJECT_FAMILY, scenario_contract_version: "v1", combined_contract_identifier: "declared_retirement_cashflow_adjustments/v1", subject_type: id === "base" ? "baseline" : "adjusted", display_label: id === "base" ? null : displayLabel, adjustment_manifest: {}, adjustment_manifest_fingerprint: "a".repeat(64), calculation_semantic_fingerprint: "b".repeat(64), integrity_fingerprint: "c".repeat(64), provenance: "planner_declared_scenario_adjustment", actor: "system:m09", actor_is_authentication: false, created_at: "2026-08-12T00:00:00Z", adjustments: values });
const currentness = (subjectId: string, runId = "run-1"): api.M09SubjectCurrentness => ({ run_id: runId, current_run_id: runId, scenario_subject_id: subjectId, is_current: true, reason_codes: [], assessment_timestamp: "2026-08-12T00:00:00Z", assessment_contract_version: "m09-subject-currentness-v1" });
const eligibility = (subjectId: string, runId = "run-1"): api.M09SubjectEligibility => ({ assessed_scenario_run_id: runId, current_scenario_run_id: runId, scenario_subject_id: subjectId, eligible_for_m10: true, reason_codes: [], informational_warnings: [], factual_baseline_material_fingerprint: "f".repeat(64), assessment_timestamp: "2026-08-12T00:00:00Z", eligibility_contract_version: "m09-to-m10-eligibility-v2" });
const run = (subjectId: string): api.M09SubjectRun => ({ run_id: "run-1", scenario_subject_id: subjectId, client_id: 1, predecessor_run_id: null, run_sequence: 1, scenario_family: api.M09_SUBJECT_FAMILY, scenario_contract_version: "v1", start_month: "2026-01", end_month: "2026-02", factual_inventory: { domains: [{ domain: "recurring_income", candidates: [{ component_id: "income-1", amount: "1000.00" }] }] }, factual_inventory_fingerprint: "e".repeat(64), factual_baseline_material_fingerprint: "f".repeat(64), adjustment_manifest: {}, adjustment_manifest_fingerprint: "a".repeat(64), upstream_snapshot: {}, upstream_snapshot_fingerprint: "b".repeat(64), status: "success_complete", warnings: [], blocker_codes: [], monthly_results: [{ monthly_result_id: "month-1", month: "2026-01", gross_inflow_total: "1100.00", gross_outflow_total: "0.00", period_net: "1100.00", component_evidence: [], result_fingerprint: "c".repeat(64) }], range_totals: { gross_inflow_total: "1100.00", gross_outflow_total: "0.00", period_net: "1100.00" }, semantic_result_fingerprint: "d".repeat(64), result_integrity_fingerprint: "e".repeat(64), currentness: currentness(subjectId), m10_eligibility: eligibility(subjectId), actor: "system:m09", actor_is_authentication: false, created_at: "2026-08-12T00:00:00Z" });
const summary = (subjectId: string): api.M09SubjectRunSummary => ({ run_id: "run-1", scenario_subject_id: subjectId, run_sequence: 1, status: "success_complete", start_month: "2026-01", end_month: "2026-02", factual_baseline_material_fingerprint: "f".repeat(64), is_current: true, eligible_for_m10: true, created_at: "2026-08-12T00:00:00Z" });
type Deferred<T> = { promise: Promise<T>; resolve: (v: T) => void; reject: (reason: unknown) => void };
const deferred = <T,>(): Deferred<T> => { let resolve!: (v: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
function Harness() { const navigate = useNavigate(); const { id } = useParams(); return <><button onClick={() => navigate("/clients/1/monthly-cashflow")}>Switch A</button><button onClick={() => navigate("/clients/2/monthly-cashflow")}>Switch B</button><M09ScenarioSubjects clientId={Number(id)} /></>; }
const renderPage = () => render(<MemoryRouter initialEntries={["/clients/1/monthly-cashflow"]}><Routes><Route path="/clients/:id/monthly-cashflow" element={<Harness />} /></Routes></MemoryRouter>);
const fillValidAdjustment = () => {
  fireEvent.change(screen.getByLabelText("Adjustment amount 1"), { target: { value: "100.00" } });
  fireEvent.change(screen.getByLabelText("Adjustment start month 1"), { target: { value: "2026-01" } });
  fireEvent.change(screen.getByLabelText("Adjustment end month 1"), { target: { value: "2026-02" } });
};
const fillExecutionRange = () => {
  fireEvent.change(screen.getByLabelText("Subject execution start"), { target: { value: "2026-01" } });
  fireEvent.change(screen.getByLabelText("Subject execution end"), { target: { value: "2026-02" } });
};
const structuredError = (code: string) => new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { code } } });
const markedRun = (subjectId: string, amount: string, runId = "run-1"): api.M09SubjectRun => {
  const value = run(subjectId);
  return { ...value, run_id: runId, monthly_results: value.monthly_results.map(row => ({ ...row, monthly_result_id: `${runId}-month`, gross_inflow_total: amount, period_net: amount })), currentness: currentness(subjectId, runId), m10_eligibility: eligibility(subjectId, runId) };
};
const markedSummary = (subjectId: string, sequence: number, runId: string): api.M09SubjectRunSummary => ({ ...summary(subjectId), run_id: runId, run_sequence: sequence });

describe("PKG-014 scenario subjects", () => {
  beforeEach(() => { vi.clearAllMocks(); mocked(api.listM09Subjects).mockResolvedValue([]); mocked(api.listM09SubjectRuns).mockResolvedValue([]); });

  it("shows the bounded meaning and resolves server baseline", async () => {
    mocked(api.resolveM09BaselineSubject).mockResolvedValue(subject("base")); renderPage();
    await waitFor(() => expect(screen.queryByText("Loading scenario evidenceג€¦")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" }));
    await screen.findByText(/Selected subject: Baseline/);
    expect(screen.getByText(/not forecasts, recommendations, professional authority, or M10 comparison/)).toBeInTheDocument();
  });

  it("preserves repeated adjustment occurrences in create input", async () => {
    mocked(api.createM09AdjustedSubject).mockResolvedValue(subject("adjusted")); renderPage();
    await waitFor(() => expect(screen.queryByText("Loading scenario evidenceג€¦")).not.toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Adjustment amount 1"), { target: { value: "100.00" } }); fireEvent.change(screen.getByLabelText("Adjustment start month 1"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Adjustment end month 1"), { target: { value: "2026-02" } });
    fireEvent.click(screen.getByRole("button", { name: "Add another adjustment" }));
    fireEvent.change(screen.getByLabelText("Adjustment amount 2"), { target: { value: "100.00" } }); fireEvent.change(screen.getByLabelText("Adjustment start month 2"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Adjustment end month 2"), { target: { value: "2026-02" } });
    fireEvent.click(screen.getByRole("button", { name: "Create adjusted subject" }));
    await waitFor(() => expect(api.createM09AdjustedSubject).toHaveBeenCalled());
    expect(mocked(api.createM09AdjustedSubject).mock.calls[0][2]).toHaveLength(2);
  });

  it("ignores stale candidate success after client switch", async () => {
    const a = deferred<api.M09ScenarioSubject[]>(); const b = deferred<api.M09ScenarioSubject[]>();
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 1 ? a.promise : b.promise); renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" })); await act(async () => a.resolve([subject("old-a")]));
    expect(screen.queryByText("Alternative")).not.toBeInTheDocument(); await act(async () => b.resolve([subject("new-b", 2)]));
    expect(await screen.findByRole("button", { name: "Alternative" })).toBeInTheDocument();
  });

  it("validates canonical amounts before create", async () => {
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument()); fireEvent.change(screen.getByLabelText("Adjustment amount 1"), { target: { value: "1e2" } }); fireEvent.change(screen.getByLabelText("Adjustment start month 1"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Adjustment end month 1"), { target: { value: "2026-02" } });
    expect(screen.getByRole("button", { name: "Create adjusted subject" })).toBeDisabled();
  });

  it("invalidates subject A detail success and finally immediately on A-to-B", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B");
    const aDetail = deferred<api.M09ScenarioSubject>(); const bDetail = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]);
    mocked(api.getM09Subject).mockImplementation((_client, id) => id === "A" ? aDetail.promise : bDetail.promise);
    renderPage(); await screen.findByRole("button", { name: "Subject A" });
    fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" }));
    await act(async () => aDetail.resolve(a));
    expect(screen.queryByText(/Selected subject: Subject A/)).not.toBeInTheDocument();
    expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bDetail.resolve(b));
    expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it("distinguishes old A rejection from new A after A-to-B-to-A", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B");
    const oldA = deferred<api.M09ScenarioSubject>(); const oldB = deferred<api.M09ScenarioSubject>(); const newA = deferred<api.M09ScenarioSubject>(); let aCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]);
    mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? oldB.promise : (++aCalls === 1 ? oldA.promise : newA.promise));
    renderPage(); await screen.findByRole("button", { name: "Subject A" });
    fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" })); fireEvent.click(screen.getByRole("button", { name: "Subject A" }));
    await act(async () => oldA.reject(new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { code: "old-a" } } })));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await act(async () => newA.resolve(a));
    expect(await screen.findByText(/Selected subject: Subject A/)).toBeInTheDocument();
    await act(async () => oldB.resolve(b));
    expect(screen.queryByText(/Selected subject: Subject B/)).not.toBeInTheDocument();
  });

  it("does not let stale subject execution write result or clear new-subject loading", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const execution = deferred<api.M09SubjectRun>(); const bDetail = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a));
    mocked(api.executeM09SubjectRun).mockReturnValue(execution.promise);
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/);
    fireEvent.change(screen.getByLabelText("Subject execution start"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Subject execution end"), { target: { value: "2026-02" } }); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await act(async () => execution.resolve(run("A")));
    expect(screen.queryByText("Subject result")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bDetail.resolve(b)); expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it("guards stale run composite rejection across subject A-to-B-to-A", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const oldRun = deferred<api.M09SubjectRun>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => Promise.resolve(id === "A" ? a : b)); mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => Promise.resolve(id === "A" ? [summary("A")] : []));
    mocked(api.getM09SubjectRun).mockReturnValue(oldRun.promise); mocked(api.getM09SubjectCurrentness).mockResolvedValue(currentness("A")); mocked(api.getM09SubjectEligibility).mockResolvedValue(eligibility("A"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByRole("button", { name: "Load subject run 1" }); fireEvent.click(screen.getByRole("button", { name: "Load subject run 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await screen.findByText(/Selected subject: Subject B/); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/);
    await act(async () => oldRun.reject(new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { code: "old-run" } } })));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.queryByText("Subject result")).not.toBeInTheDocument();
  });

  it("keeps stale create response from selecting a subject after client change", async () => {
    const creation = deferred<api.M09ScenarioSubject>(); mocked(api.createM09AdjustedSubject).mockReturnValue(creation.promise); renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Adjustment amount 1"), { target: { value: "100.00" } }); fireEvent.change(screen.getByLabelText("Adjustment start month 1"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Adjustment end month 1"), { target: { value: "2026-02" } }); fireEvent.click(screen.getByRole("button", { name: "Create adjusted subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch B" })); await act(async () => creation.resolve(subject("A", 1, "Old A")));
    expect(screen.queryByText(/Selected subject: Old A/)).not.toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-list")],
    ["structured rejection", () => structuredError("old-list")],
  ])("suppresses stale subject-list %s and preserves the newer client loading owner", async (_kind, makeError) => {
    const oldA = deferred<api.M09ScenarioSubject[]>(); const currentB = deferred<api.M09ScenarioSubject[]>();
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 1 ? oldA.promise : currentB.promise);
    renderPage(); fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await act(async () => oldA.reject(makeError()));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => currentB.resolve([subject("B", 2, "Current B")]));
    expect(await screen.findByRole("button", { name: "Current B" })).toBeInTheDocument();
  });

  it("keeps an old subject-list A result out of a new A client generation", async () => {
    const oldA = deferred<api.M09ScenarioSubject[]>(); const b = deferred<api.M09ScenarioSubject[]>(); const newA = deferred<api.M09ScenarioSubject[]>(); let aCalls = 0;
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 2 ? b.promise : (++aCalls === 1 ? oldA.promise : newA.promise));
    renderPage(); fireEvent.click(screen.getByRole("button", { name: "Switch B" })); fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    await act(async () => newA.resolve([subject("new-A", 1, "New A list")]));
    expect(await screen.findByRole("button", { name: "New A list" })).toBeInTheDocument();
    await act(async () => oldA.resolve([subject("old-A", 1, "Old A list")]));
    expect(screen.queryByRole("button", { name: "Old A list" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New A list" })).toBeInTheDocument();
    await act(async () => b.resolve([]));
  });

  it.each([
    ["plain rejection", () => new Error("old-baseline")],
    ["structured rejection", () => structuredError("old-baseline")],
  ])("suppresses stale baseline-resolution %s and preserves the newer client loading owner", async (_kind, makeError) => {
    const baseline = deferred<api.M09ScenarioSubject>(); const bList = deferred<api.M09ScenarioSubject[]>();
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 2 ? bList.promise : Promise.resolve([]));
    mocked(api.resolveM09BaselineSubject).mockReturnValue(baseline.promise);
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await act(async () => baseline.reject(makeError()));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bList.resolve([]));
  });

  it("suppresses stale baseline success after A-to-B and preserves the newer client loading owner", async () => {
    const baseline = deferred<api.M09ScenarioSubject>(); const bList = deferred<api.M09ScenarioSubject[]>();
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 2 ? bList.promise : Promise.resolve([])); mocked(api.resolveM09BaselineSubject).mockReturnValue(baseline.promise);
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument()); fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" })); fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await act(async () => baseline.resolve(subject("old-baseline", 1, "Old baseline")));
    expect(screen.queryByText(/Selected subject: Old baseline/)).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument(); await act(async () => bList.resolve([]));
  });

  it("keeps an old baseline success out of a new A client generation", async () => {
    const oldA = deferred<api.M09ScenarioSubject>(); const newA = deferred<api.M09ScenarioSubject>(); let calls = 0;
    mocked(api.resolveM09BaselineSubject).mockImplementation(() => ++calls === 1 ? oldA.promise : newA.promise);
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch B" })); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Switch A" })); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" }));
    await act(async () => newA.resolve(subject("base"))); expect(await screen.findByText(/Selected subject: Baseline/)).toBeInTheDocument();
    await act(async () => oldA.resolve(subject("old-baseline", 1, "Old baseline")));
    expect(screen.queryByText(/Selected subject: Old baseline/)).not.toBeInTheDocument();
    expect(screen.getByText(/Selected subject: Baseline/)).toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-create")],
    ["structured rejection", () => structuredError("old-create")],
  ])("suppresses stale subject-creation %s and preserves the newer client loading owner", async (_kind, makeError) => {
    const creation = deferred<api.M09ScenarioSubject>(); const bList = deferred<api.M09ScenarioSubject[]>();
    mocked(api.createM09AdjustedSubject).mockReturnValue(creation.promise);
    mocked(api.listM09Subjects).mockImplementation(clientId => clientId === 2 ? bList.promise : Promise.resolve([]));
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument()); fillValidAdjustment();
    fireEvent.click(screen.getByRole("button", { name: "Create adjusted subject" })); fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await act(async () => creation.reject(makeError()));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    expect(screen.queryByText(/Selected subject:/)).not.toBeInTheDocument(); await act(async () => bList.resolve([]));
  });

  it("keeps an old create success from appending or selecting into a new A client generation", async () => {
    const oldA = deferred<api.M09ScenarioSubject>(); const newA = deferred<api.M09ScenarioSubject>(); let calls = 0;
    mocked(api.createM09AdjustedSubject).mockImplementation(() => ++calls === 1 ? oldA.promise : newA.promise);
    renderPage(); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument()); fillValidAdjustment(); fireEvent.click(screen.getByRole("button", { name: "Create adjusted subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch B" })); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Switch A" })); await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument()); fillValidAdjustment(); fireEvent.click(screen.getByRole("button", { name: "Create adjusted subject" }));
    await act(async () => newA.resolve(subject("new-create", 1, "New create"))); expect(await screen.findByText(/Selected subject: New create/)).toBeInTheDocument();
    await act(async () => oldA.resolve(subject("old-create", 1, "Old create")));
    expect(screen.queryByText(/Selected subject: Old create/)).not.toBeInTheDocument(); expect(screen.getByText(/Selected subject: New create/)).toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-detail")],
    ["structured rejection", () => structuredError("old-detail")],
  ])("suppresses stale subject-detail %s and preserves the newer subject loading owner", async (_kind, makeError) => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const oldA = deferred<api.M09ScenarioSubject>(); const currentB = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "A" ? oldA.promise : currentB.promise);
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" }));
    await act(async () => oldA.reject(makeError())); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => currentB.resolve(b)); expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it("keeps an old subject-detail success out of a new A subject generation", async () => {
    const listedA = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const oldA = deferred<api.M09ScenarioSubject>(); const newA = deferred<api.M09ScenarioSubject>(); let aCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([listedA, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? Promise.resolve(b) : (++aCalls === 1 ? oldA.promise : newA.promise));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await screen.findByText(/Selected subject: Subject B/); fireEvent.click(screen.getByRole("button", { name: "Subject A" }));
    await act(async () => newA.resolve(subject("A", 1, "New A detail"))); expect(await screen.findByText(/Selected subject: New A detail/)).toBeInTheDocument();
    await act(async () => oldA.resolve(subject("A", 1, "Old A detail")));
    expect(screen.queryByText(/Selected subject: Old A detail/)).not.toBeInTheDocument(); expect(screen.getByText(/Selected subject: New A detail/)).toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-execution")],
    ["structured rejection", () => structuredError("old-execution")],
  ])("suppresses stale subject-execution %s and preserves the newer subject loading owner", async (_kind, makeError) => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const execution = deferred<api.M09SubjectRun>(); const bDetail = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a)); mocked(api.executeM09SubjectRun).mockReturnValue(execution.promise);
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fillExecutionRange(); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await act(async () => execution.reject(makeError()));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.queryByText("Subject result")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bDetail.resolve(b)); expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it("keeps an old execution success from overwriting a new A result after A-to-B-to-A", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const oldA = deferred<api.M09SubjectRun>(); const newA = deferred<api.M09SubjectRun>(); let calls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => Promise.resolve(id === "A" ? a : b)); mocked(api.executeM09SubjectRun).mockImplementation(() => ++calls === 1 ? oldA.promise : newA.promise);
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fillExecutionRange(); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" }));
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await screen.findByText(/Selected subject: Subject B/); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" }));
    await act(async () => newA.resolve(markedRun("A", "2222.00", "new-run"))); expect(await screen.findAllByText("2222.00")).toHaveLength(2);
    await act(async () => oldA.resolve(markedRun("A", "1111.00", "old-run")));
    expect(screen.queryAllByText("1111.00")).toHaveLength(0); expect(screen.getAllByText("2222.00")).toHaveLength(2);
  });

  it("keeps independently refreshed stale run history out of the next subject and preserves its loading", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const staleHistory = deferred<api.M09SubjectRunSummary[]>(); const bDetail = deferred<api.M09ScenarioSubject>(); const bHistory = deferred<api.M09SubjectRunSummary[]>(); let aHistoryCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a));
    mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => id === "B" ? bHistory.promise : (++aHistoryCalls === 1 ? Promise.resolve([]) : staleHistory.promise)); mocked(api.executeM09SubjectRun).mockResolvedValue(markedRun("A", "1234.00"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fillExecutionRange(); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" })); expect(await screen.findAllByText("1234.00")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await act(async () => staleHistory.resolve([markedSummary("A", 1, "stale-history")]));
    expect(screen.queryByRole("button", { name: "Load subject run 1" })).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => { bDetail.resolve(b); bHistory.resolve([]); }); expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-history")],
    ["structured rejection", () => structuredError("old-history")],
  ])("suppresses independently refreshed stale run-history %s and preserves newer loading", async (_kind, makeError) => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const staleHistory = deferred<api.M09SubjectRunSummary[]>(); const bDetail = deferred<api.M09ScenarioSubject>(); const bHistory = deferred<api.M09SubjectRunSummary[]>(); let aHistoryCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a)); mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => id === "B" ? bHistory.promise : (++aHistoryCalls === 1 ? Promise.resolve([]) : staleHistory.promise)); mocked(api.executeM09SubjectRun).mockResolvedValue(markedRun("A", "1234.00"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fillExecutionRange(); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" })); expect(await screen.findAllByText("1234.00")).toHaveLength(2); fireEvent.click(screen.getByRole("button", { name: "Subject B" }));
    await act(async () => staleHistory.reject(makeError())); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument(); await act(async () => { bDetail.resolve(b); bHistory.resolve([]); });
  });

  it("keeps independently refreshed old A history out of a new A subject generation", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const staleHistory = deferred<api.M09SubjectRunSummary[]>(); let aHistoryCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => Promise.resolve(id === "A" ? a : b));
    mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => {
      if (id === "B") return Promise.resolve([]);
      aHistoryCalls += 1; if (aHistoryCalls === 1) return Promise.resolve([]); if (aHistoryCalls === 2) return staleHistory.promise;
      return Promise.resolve([markedSummary("A", 2, "new-history")]);
    });
    mocked(api.executeM09SubjectRun).mockResolvedValue(markedRun("A", "1234.00"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/); fillExecutionRange(); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" })); expect(await screen.findAllByText("1234.00")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await screen.findByText(/Selected subject: Subject B/); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); expect(await screen.findByRole("button", { name: "Load subject run 2" })).toBeInTheDocument();
    await act(async () => staleHistory.resolve([markedSummary("A", 1, "old-history")]));
    expect(screen.queryByRole("button", { name: "Load subject run 1" })).not.toBeInTheDocument(); expect(screen.getByRole("button", { name: "Load subject run 2" })).toBeInTheDocument();
  });

  it.each([
    ["plain rejection", () => new Error("old-result")],
    ["structured rejection", () => structuredError("old-result")],
  ])("suppresses stale run-result %s and preserves the newer subject loading owner", async (_kind, makeError) => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const staleResult = deferred<api.M09SubjectRun>(); const bDetail = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a)); mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => Promise.resolve(id === "A" ? [summary("A")] : []));
    mocked(api.getM09SubjectRun).mockReturnValue(staleResult.promise); mocked(api.getM09SubjectCurrentness).mockResolvedValue(currentness("A")); mocked(api.getM09SubjectEligibility).mockResolvedValue(eligibility("A"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(await screen.findByRole("button", { name: "Load subject run 1" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" }));
    await act(async () => staleResult.reject(makeError())); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); expect(screen.queryByText("Subject result")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bDetail.resolve(b)); expect(await screen.findByText(/Selected subject: Subject B/)).toBeInTheDocument();
  });

  it("keeps a stale run-result success out of the next subject and preserves its loading", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const staleResult = deferred<api.M09SubjectRun>(); const bDetail = deferred<api.M09ScenarioSubject>();
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => id === "B" ? bDetail.promise : Promise.resolve(a)); mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => Promise.resolve(id === "A" ? [summary("A")] : []));
    mocked(api.getM09SubjectRun).mockReturnValue(staleResult.promise); mocked(api.getM09SubjectCurrentness).mockResolvedValue(currentness("A")); mocked(api.getM09SubjectEligibility).mockResolvedValue(eligibility("A"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(await screen.findByRole("button", { name: "Load subject run 1" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" }));
    await act(async () => staleResult.resolve(markedRun("A", "1111.00", "old-result"))); expect(screen.queryByText("1111.00")).not.toBeInTheDocument(); expect(screen.getByText("Loading scenario evidence…")).toBeInTheDocument();
    await act(async () => bDetail.resolve(b));
  });

  it("keeps an old run-result composite out of a new A subject generation", async () => {
    const a = subject("A", 1, "Subject A"); const b = subject("B", 1, "Subject B"); const oldResult = deferred<api.M09SubjectRun>(); const newResult = deferred<api.M09SubjectRun>(); let runCalls = 0;
    mocked(api.listM09Subjects).mockResolvedValue([a, b]); mocked(api.getM09Subject).mockImplementation((_client, id) => Promise.resolve(id === "A" ? a : b)); mocked(api.listM09SubjectRuns).mockImplementation((_client, id) => Promise.resolve(id === "A" ? [summary("A")] : []));
    mocked(api.getM09SubjectRun).mockImplementation(() => ++runCalls === 1 ? oldResult.promise : newResult.promise); mocked(api.getM09SubjectCurrentness).mockResolvedValue(currentness("A")); mocked(api.getM09SubjectEligibility).mockResolvedValue(eligibility("A"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(await screen.findByRole("button", { name: "Load subject run 1" })); fireEvent.click(screen.getByRole("button", { name: "Subject B" })); await screen.findByText(/Selected subject: Subject B/); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); fireEvent.click(await screen.findByRole("button", { name: "Load subject run 1" }));
    await act(async () => newResult.resolve(markedRun("A", "2222.00", "new-result"))); expect(await screen.findAllByText("2222.00")).toHaveLength(2);
    await act(async () => oldResult.resolve(markedRun("A", "1111.00", "old-result")));
    expect(screen.queryAllByText("1111.00")).toHaveLength(0); expect(screen.getAllByText("2222.00")).toHaveLength(2);
  });

  it("renders factual evidence separately from each declared occurrence without edit authority", async () => {
    const a = subject("A", 1, "Subject A", [adjustment("A1"), adjustment("A2")]); mocked(api.listM09Subjects).mockResolvedValue([a]); mocked(api.getM09Subject).mockResolvedValue(a); mocked(api.executeM09SubjectRun).mockResolvedValue(run("A"));
    renderPage(); await screen.findByRole("button", { name: "Subject A" }); fireEvent.click(screen.getByRole("button", { name: "Subject A" })); await screen.findByText(/Selected subject: Subject A/);
    expect(screen.getByRole("region", { name: "Declared scenario adjustments" }).querySelectorAll("li")).toHaveLength(2);
    expect(screen.getAllByText("100.00 ILS")).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Subject execution start"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Subject execution end"), { target: { value: "2026-02" } }); fireEvent.click(screen.getByRole("button", { name: "Execute selected subject" }));
    const factual = await screen.findByRole("region", { name: "Factual baseline" }); expect(factual).toHaveTextContent("recurring_income"); expect(factual).toHaveTextContent("income-1");
    expect(factual.querySelectorAll('input, button, select')).toHaveLength(0);
    expect(screen.queryByText(/suppress/i)).not.toBeInTheDocument();
  });
});

