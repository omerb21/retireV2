import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiTransportError } from "../api/clientsApi";
import * as m09 from "../api/m09CashflowApi";
import * as m10 from "../api/m10ComparisonApi";
import { AppRoutes } from "../routes/AppRoutes";
import { M10ComparisonScreen } from "./M10ComparisonScreen";

vi.mock("../api/m09CashflowApi", async () => {
  const actual = await vi.importActual<typeof import("../api/m09CashflowApi")>("../api/m09CashflowApi");
  return { ...actual, listM09Subjects: vi.fn(), listM09SubjectRuns: vi.fn() };
});

vi.mock("../api/m10ComparisonApi", async () => {
  const actual = await vi.importActual<typeof import("../api/m10ComparisonApi")>("../api/m10ComparisonApi");
  return { ...actual, compareM10Runs: vi.fn() };
});

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

function subject(
  id: string,
  type: "baseline" | "adjusted",
  createdAt = "2026-01-01T00:00:00.000000",
  label: string | null = type === "baseline" ? null : `Adjusted ${id}`,
): m09.M09ScenarioSubject {
  return {
    scenario_subject_id: id,
    client_id: 1,
    scenario_family: "declared_retirement_cashflow_adjustments",
    scenario_contract_version: "v1",
    combined_contract_identifier: "declared_retirement_cashflow_adjustments/v1",
    subject_type: type,
    display_label: label,
    adjustment_manifest: {},
    adjustment_manifest_fingerprint: `manifest-${id}`,
    calculation_semantic_fingerprint: `semantic-${id}`,
    integrity_fingerprint: `integrity-${id}`,
    provenance: "server",
    actor: "system",
    actor_is_authentication: false,
    created_at: createdAt,
    adjustments: [],
  };
}

function run(
  subjectId: string,
  runId = `${subjectId}-run`,
  eligible = true,
  current = true,
): m09.M09SubjectRunSummary {
  return {
    run_id: runId,
    scenario_subject_id: subjectId,
    run_sequence: 1,
    status: "completed",
    start_month: "2026-01",
    end_month: "2026-02",
    factual_baseline_material_fingerprint: "baseline-material",
    is_current: current,
    eligible_for_m10: eligible,
    created_at: "2026-02-01T00:00:00.000000",
  };
}

function metric(
  reference: string,
  compared: string,
  delta: string,
  relation: m10.M10MetricComparison["relation"],
): m10.M10MetricComparison {
  return { reference_value: reference, compared_value: compared, delta, relation };
}

function comparisonResult(
  marker = "new-comparison",
  clientId = 1,
  referenceRunId = "baseline-run",
  comparedRunId = "adjusted-run",
): m10.M10ComparisonResponse {
  const evidence = (runId: string, subjectType: "baseline" | "adjusted"): m10.M10RunEvidence => ({
    run_id: runId,
    scenario_subject_id: `${subjectType}-subject`,
    subject_type: subjectType,
    calculation_semantic_fingerprint: `${marker}-${subjectType}-calculation`,
    integrity_fingerprint: `${marker}-${subjectType}-integrity`,
    adjustment_manifest_fingerprint: `${marker}-${subjectType}-manifest`,
    factual_inventory_fingerprint: `${marker}-${subjectType}-inventory`,
    upstream_snapshot_fingerprint: `${marker}-${subjectType}-snapshot`,
    semantic_result_fingerprint: `${marker}-${subjectType}-semantic-result`,
    result_integrity_fingerprint: `${marker}-${subjectType}-result-integrity`,
  });
  return {
    comparison_contract_version: "m10-scenario-comparison-v2",
    pair_admission_contract: "m10-pair-admission-v2",
    comparison_result_schema: "m10-comparison-result-v2",
    comparison_fingerprint_schema: "m10-comparison-fingerprint-v2",
    comparison_fingerprint: `${marker}-fingerprint`,
    delta_direction: "compared_minus_reference",
    client_id: clientId,
    scenario_family: "declared_retirement_cashflow_adjustments",
    scenario_contract_version: "v1",
    horizon: { start_month: "2026-01", end_month: "2026-02" },
    factual_baseline_material_fingerprint: `${marker}-baseline-material`,
    component_domain_contract_version: "m09-component-domains-v1",
    versions: {
      factual_engine_version: "m09-aggregation-v1",
      factual_result_schema_version: "m09-result-v1",
      subject_engine_version: "m09-subject-aggregation-v1",
      subject_result_schema_version: "m09-subject-result-v1",
      upstream_snapshot_schema_version: "m09-subject-upstream-snapshot-v1",
      factual_inventory_schema_version: "m09-resolved-component-inventory-v1",
      factual_upstream_versions: [{
        domain_identity: "recurring_income",
        candidate_identity: "income-1",
        source_identity: "source-1",
        source_version: "source-v1",
        source_fingerprint: `${marker}-source-fingerprint`,
        handoff_contract_versions: ["handoff-v1"],
      }],
    },
    reference_run: evidence(referenceRunId, "baseline"),
    compared_run: evidence(comparedRunId, "adjusted"),
    monthly_comparisons: [{
      month: "2026-01",
      gross_inflow_total: metric("9007199254740993.00", "9007199254740992.99", "-0.01", "compared_lower_than_reference"),
      gross_outflow_total: metric("100.10", "100.10", "0.00", "equal"),
      period_net: metric("-50.00", "25.00", "75.00", "compared_greater_than_reference"),
    }],
    range_totals: {
      gross_inflow_total: metric("9007199254740993.00", "9007199254740992.99", "-0.01", "compared_lower_than_reference"),
      gross_outflow_total: metric("200.20", "200.20", "0.00", "equal"),
      period_net: metric("-100.00", "50.00", "150.00", "compared_greater_than_reference"),
    },
  };
}

function NavigationHarness() {
  const navigate = useNavigate();
  return <>
    <nav>
      <button type="button" onClick={() => navigate("/clients/1/scenario-comparison")}>Switch A</button>
      <button type="button" onClick={() => navigate("/clients/2/scenario-comparison")}>Switch B</button>
    </nav>
    <Routes>
      <Route path="/clients/:clientId/scenario-comparison" element={<M10ComparisonScreen />} />
    </Routes>
  </>;
}

function renderScreen(initialEntry = "/clients/1/scenario-comparison") {
  return render(<MemoryRouter initialEntries={[initialEntry]}><NavigationHarness /></MemoryRouter>);
}

function readyDiscovery(adjustedSubjects: m09.M09ScenarioSubject[] = [subject("adjusted", "adjusted")]) {
  const baseline = subject("baseline", "baseline");
  vi.mocked(m09.listM09Subjects).mockResolvedValue([baseline, ...adjustedSubjects]);
  vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => (
    Promise.resolve([run(subjectId)])
  ));
}

async function selectFirstCandidateAndCompare() {
  const candidate = await screen.findByRole("radio");
  await act(async () => {
    fireEvent.click(candidate);
    fireEvent.click(screen.getByRole("button", { name: "Compare selected pair" }));
    await Promise.resolve();
    await Promise.resolve();
  });
}

function structuredError(code: string, status?: number): ApiTransportError {
  return new ApiTransportError({
    status: status ?? (code === "comparison_run_unavailable" ? 404 : 409),
    statusText: status === 404 || code === "comparison_run_unavailable" ? "Not Found" : "Conflict",
    body: { detail: { code, message: `server-${code}` } },
  });
}

afterEach(() => {
  vi.resetAllMocks();
});

describe("M10ComparisonScreen", () => {
  it("is wired into the client-scoped application route", async () => {
    readyDiscovery();
    render(<MemoryRouter initialEntries={["/clients/1/scenario-comparison"]}><AppRoutes /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "M10 Scenario comparison" })).toBeInTheDocument();
    expect(await screen.findByRole("radio", { name: /Adjusted adjusted/ })).toBeInTheDocument();
  });

  it("rejects an invalid route client without issuing discovery", () => {
    renderScreen("/clients/0/scenario-comparison");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid client ID.");
    expect(m09.listM09Subjects).not.toHaveBeenCalled();
  });

  it("discovers one baseline and neutrally orders only server-evidenced adjusted candidates without auto-selection", async () => {
    const baseline = subject("baseline", "baseline", "2026-01-01T00:00:00.000000");
    const later = subject("z-adjusted", "adjusted", "2026-03-01T00:00:00.000000", "Later adjusted");
    const tieB = subject("b-adjusted", "adjusted", "2026-02-01T00:00:00.000000", "Tie B");
    const tieA = subject("a-adjusted", "adjusted", "2026-02-01T00:00:00.000000", "Tie A");
    const omitted = subject("omitted", "adjusted", "2026-01-15T00:00:00.000000", "Ineligible adjusted");
    vi.mocked(m09.listM09Subjects).mockResolvedValue([later, baseline, tieB, omitted, tieA]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => (
      Promise.resolve([run(subjectId, `${subjectId}-run`, subjectId !== "omitted")])
    ));

    renderScreen();

    expect(await screen.findByText("Run ID: baseline-run")).toBeInTheDocument();
    const labels = screen.getAllByRole("radio").map(input => input.parentElement?.textContent);
    expect(labels).toEqual([
      expect.stringContaining("Tie A"),
      expect.stringContaining("Tie B"),
      expect.stringContaining("Later adjusted"),
    ]);
    expect(screen.queryByText(/Ineligible adjusted/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare selected pair" })).toBeDisabled();
    expect(screen.getByText(/technical and neutral/)).toBeInTheDocument();
  });

  it("fails closed when no baseline subject is present", async () => {
    vi.mocked(m09.listM09Subjects).mockResolvedValue([subject("adjusted", "adjusted")]);
    vi.mocked(m09.listM09SubjectRuns).mockResolvedValue([run("adjusted")]);
    renderScreen();
    expect(await screen.findByText(/no eligible current baseline run/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare selected pair" })).toBeDisabled();
  });

  it("fails closed when two apparent baseline subjects are returned", async () => {
    vi.mocked(m09.listM09Subjects).mockResolvedValue([
      subject("baseline-1", "baseline"),
      subject("baseline-2", "baseline"),
      subject("adjusted", "adjusted"),
    ]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    expect(await screen.findByText(/baseline evidence is ambiguous/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("fails closed when the baseline subject has multiple eligible current runs", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      subjectId === "baseline" ? [run(subjectId, "baseline-1"), run(subjectId, "baseline-2")] : [run(subjectId)],
    ));
    renderScreen();
    expect(await screen.findByText(/baseline evidence is ambiguous/)).toBeInTheDocument();
  });

  it("shows the no-adjusted state when adjusted subjects have no eligible current run", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      [run(subjectId, `${subjectId}-run`, subjectId === "baseline")],
    ));
    renderScreen();
    expect(await screen.findByText(/No eligible current adjusted run/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("fails closed instead of choosing among multiple eligible runs for one adjusted subject", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      subjectId === "adjusted" ? [run(subjectId, "adjusted-1"), run(subjectId, "adjusted-2")] : [run(subjectId)],
    ));
    renderScreen();
    expect(await screen.findByText(/adjusted subject has ambiguous eligible run evidence/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("treats unexpected subject contract evidence as unavailable without reconstructing it", async () => {
    const invalid = { ...subject("unexpected", "adjusted"), scenario_contract_version: "v2" } as unknown as m09.M09ScenarioSubject;
    vi.mocked(m09.listM09Subjects).mockResolvedValue([subject("baseline", "baseline"), invalid]);
    renderScreen();
    expect(await screen.findByText(/unexpected scenario-subject contract evidence/)).toBeInTheDocument();
    expect(m09.listM09SubjectRuns).not.toHaveBeenCalled();
  });

  it("invokes the exact role-bound request and renders exact server strings, relations, versions, and evidence", async () => {
    readyDiscovery();
    const serverResult = comparisonResult();
    vi.mocked(m10.compareM10Runs).mockResolvedValue(serverResult);
    renderScreen();

    await selectFirstCandidateAndCompare();

    expect(m10.compareM10Runs).toHaveBeenCalledWith(1, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
    });
    const evidence = await screen.findByRole("region", { name: "Comparator success evidence" });
    expect(evidence).toHaveTextContent("new-comparison-fingerprint");
    expect(evidence).toHaveTextContent("m10-comparison-result-v2");
    expect(evidence).toHaveTextContent("compared_minus_reference");
    expect(evidence).toHaveTextContent("9007199254740993.00");
    expect(evidence).toHaveTextContent("9007199254740992.99");
    expect(evidence).toHaveTextContent("-0.01");
    expect(evidence).toHaveTextContent("0.00");
    expect(evidence).toHaveTextContent("75.00");
    expect(evidence).toHaveTextContent("compared_lower_than_reference");
    expect(evidence).toHaveTextContent("equal");
    expect(evidence).toHaveTextContent("compared_greater_than_reference");
    expect(evidence).toHaveTextContent("new-comparison-source-fingerprint");
    expect(evidence).toHaveTextContent("new-comparison-baseline-result-integrity");
    expect(evidence).toHaveTextContent("new-comparison-adjusted-result-integrity");
    expect(screen.queryByText(/percentage|improvement|winner|significant/i)).not.toBeInTheDocument();
  });

  it.each(m10.M10_COMPARATOR_BLOCKER_CODES)("renders accepted blocker %s one-to-one with its exact observable code", async code => {
    readyDiscovery();
    vi.mocked(m10.compareM10Runs).mockRejectedValue(structuredError(code));
    renderScreen();
    await selectFirstCandidateAndCompare();
    const blocker = await screen.findByRole("region", { name: "Accepted comparator blocker" });
    expect(within(blocker).getByText(code)).toBeInTheDocument();
    expect(blocker).toHaveTextContent(`server-${code}`);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Comparator success evidence" })).not.toBeInTheDocument();
  });

  it.each([
    ["unknown structured code", structuredError("comparison_unknown")],
    ["wrong status for accepted code", structuredError("comparison_run_not_current", 404)],
    ["ordinary transport failure", new Error("network unavailable")],
  ])("keeps %s outside accepted business-blocker rendering", async (_label, error) => {
    readyDiscovery();
    vi.mocked(m10.compareM10Runs).mockRejectedValue(error);
    renderScreen();
    await selectFirstCandidateAndCompare();
    expect(await screen.findByRole("alert")).toHaveTextContent("Comparator request failed");
    expect(screen.queryByRole("region", { name: "Accepted comparator blocker" })).not.toBeInTheDocument();
  });

  it("keeps discovery transport failure distinct from comparison blockers", async () => {
    vi.mocked(m09.listM09Subjects).mockRejectedValue(new Error("discovery offline"));
    renderScreen();
    expect(await screen.findByRole("alert")).toHaveTextContent("Eligible-run discovery failed: discovery offline");
    expect(screen.queryByText("Comparison blocked")).not.toBeInTheDocument();
  });

  it("hides prior-client candidates immediately while the next client discovery is pending", async () => {
    const pendingB = deferred<m09.M09ScenarioSubject[]>();
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => clientId === 1
      ? Promise.resolve([subject("A-baseline", "baseline"), subject("A-adjusted", "adjusted", undefined, "A adjusted")])
      : pendingB.promise);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    expect(await screen.findByRole("radio", { name: /A adjusted/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    expect(screen.queryByText(/A adjusted/)).not.toBeInTheDocument();
    expect(screen.getByText("Loading eligible M09 runs…")).toBeInTheDocument();
    await act(async () => pendingB.resolve([subject("B-baseline", "baseline")]));
    expect(await screen.findByText(/No eligible current adjusted run/)).toBeInTheDocument();
  });

  it("discards discovery A-old success after switching to B", async () => {
    const oldA = deferred<m09.M09ScenarioSubject[]>();
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => (
      clientId === 1 ? oldA.promise : Promise.resolve([subject("B-baseline", "baseline"), subject("B-adjusted", "adjusted", undefined, "B adjusted")])
    ));
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    expect(await screen.findByRole("radio", { name: /B adjusted/ })).toBeInTheDocument();
    await act(async () => oldA.resolve([subject("A-baseline", "baseline"), subject("A-adjusted", "adjusted", undefined, "A old adjusted")]));
    expect(screen.queryByText(/A old adjusted/)).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /B adjusted/ })).toBeInTheDocument();
  });

  it("keeps A-new discovery loading through A-old rejection and finally after A-to-B-to-A", async () => {
    const oldA = deferred<m09.M09ScenarioSubject[]>();
    const newA = deferred<m09.M09ScenarioSubject[]>();
    let aCalls = 0;
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => {
      if (clientId === 2) return Promise.resolve([subject("B-baseline", "baseline")]);
      aCalls += 1;
      return aCalls === 1 ? oldA.promise : newA.promise;
    });
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await screen.findByText(/No eligible current adjusted run/);
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    expect(screen.getByText("Loading eligible M09 runs…")).toBeInTheDocument();
    await act(async () => oldA.reject(new Error("A-old discovery failed")));
    expect(screen.getByText("Loading eligible M09 runs…")).toBeInTheDocument();
    expect(screen.queryByText(/A-old discovery failed/)).not.toBeInTheDocument();
    await act(async () => newA.resolve([subject("A-new-baseline", "baseline"), subject("A-new-adjusted", "adjusted", undefined, "A new adjusted")]));
    expect(await screen.findByRole("radio", { name: /A new adjusted/ })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("discards compare A-old success after switching to B", async () => {
    const oldCompare = deferred<m10.M10ComparisonResponse>();
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => Promise.resolve([
      subject(`${clientId}-baseline`, "baseline"),
      subject(`${clientId}-adjusted`, "adjusted", undefined, clientId === 1 ? "A adjusted" : "B adjusted"),
    ]));
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    vi.mocked(m10.compareM10Runs).mockReturnValue(oldCompare.promise);
    renderScreen();
    await selectFirstCandidateAndCompare();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    expect(await screen.findByRole("radio", { name: /B adjusted/ })).toBeInTheDocument();
    await act(async () => oldCompare.resolve(comparisonResult("A-old", 1, "1-baseline-run", "1-adjusted-run")));
    expect(screen.queryByText("A-old-fingerprint")).not.toBeInTheDocument();
    expect(screen.queryByText("Loading comparator evidence…")).not.toBeInTheDocument();
  });

  it("keeps A-new compare loading through A-old rejection and finally after A-to-B-to-A", async () => {
    const oldCompare = deferred<m10.M10ComparisonResponse>();
    const newCompare = deferred<m10.M10ComparisonResponse>();
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => Promise.resolve([
      subject(`${clientId}-baseline`, "baseline"),
      subject(`${clientId}-adjusted`, "adjusted", undefined, `${clientId === 1 ? "A" : "B"} adjusted`),
    ]));
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    vi.mocked(m10.compareM10Runs).mockImplementationOnce(() => oldCompare.promise).mockImplementationOnce(() => newCompare.promise);
    renderScreen();
    await selectFirstCandidateAndCompare();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await screen.findByRole("radio", { name: /B adjusted/ });
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    await selectFirstCandidateAndCompare();
    expect(screen.getByText("Loading comparator evidence…")).toBeInTheDocument();
    await act(async () => oldCompare.reject(new Error("A-old compare failed")));
    expect(screen.getByText("Loading comparator evidence…")).toBeInTheDocument();
    expect(screen.queryByText(/A-old compare failed/)).not.toBeInTheDocument();
    await act(async () => newCompare.resolve(comparisonResult("A-new")));
    expect(await screen.findByText("A-new-fingerprint")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("uses compare request ownership to prevent R1 from overwriting R2 in the same client generation", async () => {
    const first = subject("adjusted-1", "adjusted", "2026-01-02T00:00:00.000000", "Adjusted one");
    const second = subject("adjusted-2", "adjusted", "2026-01-03T00:00:00.000000", "Adjusted two");
    readyDiscovery([first, second]);
    const r1 = deferred<m10.M10ComparisonResponse>();
    const r2 = deferred<m10.M10ComparisonResponse>();
    vi.mocked(m10.compareM10Runs).mockImplementationOnce(() => r1.promise).mockImplementationOnce(() => r2.promise);
    renderScreen();
    const radios = await screen.findAllByRole("radio");
    fireEvent.click(radios[0]);
    fireEvent.click(screen.getByRole("button", { name: "Compare selected pair" }));
    fireEvent.click(radios[1]);
    fireEvent.click(screen.getByRole("button", { name: "Compare selected pair" }));
    await act(async () => r1.resolve(comparisonResult("R1-old", 1, "baseline-run", "adjusted-1-run")));
    expect(screen.queryByText("R1-old-fingerprint")).not.toBeInTheDocument();
    expect(screen.getByText("Loading comparator evidence…")).toBeInTheDocument();
    await act(async () => r2.resolve(comparisonResult("R2-new", 1, "baseline-run", "adjusted-2-run")));
    expect(await screen.findByText("R2-new-fingerprint")).toBeInTheDocument();
    expect(screen.queryByText("Loading comparator evidence…")).not.toBeInTheDocument();
  });

  it("makes stale same-generation rejection and finally a no-op for result, selection, error, and loading", async () => {
    const first = subject("adjusted-1", "adjusted", "2026-01-02T00:00:00.000000", "Adjusted one");
    const second = subject("adjusted-2", "adjusted", "2026-01-03T00:00:00.000000", "Adjusted two");
    readyDiscovery([first, second]);
    const r1 = deferred<m10.M10ComparisonResponse>();
    const r2 = deferred<m10.M10ComparisonResponse>();
    vi.mocked(m10.compareM10Runs).mockImplementationOnce(() => r1.promise).mockImplementationOnce(() => r2.promise);
    renderScreen();
    const radios = await screen.findAllByRole("radio");
    fireEvent.click(radios[0]);
    fireEvent.click(screen.getByRole("button", { name: "Compare selected pair" }));
    fireEvent.click(radios[1]);
    fireEvent.click(screen.getByRole("button", { name: "Compare selected pair" }));
    await act(async () => r1.reject(structuredError("comparison_run_not_current")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Accepted comparator blocker" })).not.toBeInTheDocument();
    expect(radios[1]).toBeChecked();
    expect(screen.getByText("Loading comparator evidence…")).toBeInTheDocument();
    await act(async () => r2.resolve(comparisonResult("R2-current", 1, "baseline-run", "adjusted-2-run")));
    expect(await screen.findByText("R2-current-fingerprint")).toBeInTheDocument();
  });
});
