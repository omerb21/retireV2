import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/m09CashflowApi";
import { M09ScenarioSubjects } from "./M09ScenarioSubjects";

vi.mock("../api/m09CashflowApi", async () => {
  const actual = await vi.importActual<typeof import("../api/m09CashflowApi")>("../api/m09CashflowApi");
  return { ...actual, listM09Subjects: vi.fn(), resolveM09BaselineSubject: vi.fn(), createM09AdjustedSubject: vi.fn(), getM09Subject: vi.fn(), listM09SubjectRuns: vi.fn(), executeM09SubjectRun: vi.fn(), getM09SubjectRun: vi.fn(), getM09SubjectCurrentness: vi.fn(), getM09SubjectEligibility: vi.fn() };
});
const mocked = <T extends (...args: never[]) => unknown>(fn: T) => vi.mocked(fn);
const subject = (id: string, clientId = 1): api.M09ScenarioSubject => ({ scenario_subject_id: id, client_id: clientId, scenario_family: api.M09_SUBJECT_FAMILY, scenario_contract_version: "v1", combined_contract_identifier: "declared_retirement_cashflow_adjustments/v1", subject_type: id === "base" ? "baseline" : "adjusted", display_label: id === "base" ? null : "Alternative", adjustment_manifest: {}, adjustment_manifest_fingerprint: "a".repeat(64), calculation_semantic_fingerprint: "b".repeat(64), integrity_fingerprint: "c".repeat(64), provenance: "planner_declared_scenario_adjustment", actor: "system:m09", actor_is_authentication: false, created_at: "2026-08-12T00:00:00Z", adjustments: [] });
type Deferred<T> = { promise: Promise<T>; resolve: (v: T) => void };
const deferred = <T,>(): Deferred<T> => { let resolve!: (v: T) => void; const promise = new Promise<T>(yes => { resolve = yes; }); return { promise, resolve }; };
function Harness() { const navigate = useNavigate(); const { id } = useParams(); return <><button onClick={() => navigate("/clients/2/monthly-cashflow")}>Switch B</button><M09ScenarioSubjects clientId={Number(id)} /></>; }
const renderPage = () => render(<MemoryRouter initialEntries={["/clients/1/monthly-cashflow"]}><Routes><Route path="/clients/:id/monthly-cashflow" element={<Harness />} /></Routes></MemoryRouter>);

describe("PKG-014 scenario subjects", () => {
  beforeEach(() => { vi.clearAllMocks(); mocked(api.listM09Subjects).mockResolvedValue([]); mocked(api.listM09SubjectRuns).mockResolvedValue([]); });

  it("shows the bounded meaning and resolves server baseline", async () => {
    mocked(api.resolveM09BaselineSubject).mockResolvedValue(subject("base")); renderPage();
    await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Resolve server baseline subject" }));
    await screen.findByText(/Selected subject: Baseline/);
    expect(screen.getByText(/not forecasts, recommendations, professional authority, or M10 comparison/)).toBeInTheDocument();
  });

  it("preserves repeated adjustment occurrences in create input", async () => {
    mocked(api.createM09AdjustedSubject).mockResolvedValue(subject("adjusted")); renderPage();
    await waitFor(() => expect(screen.queryByText("Loading scenario evidence…")).not.toBeInTheDocument());
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
    renderPage(); fireEvent.change(screen.getByLabelText("Adjustment amount 1"), { target: { value: "1e2" } }); fireEvent.change(screen.getByLabelText("Adjustment start month 1"), { target: { value: "2026-01" } }); fireEvent.change(screen.getByLabelText("Adjustment end month 1"), { target: { value: "2026-02" } });
    expect(screen.getByRole("button", { name: "Create adjusted subject" })).toBeDisabled();
  });
});
