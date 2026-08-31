import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiTransportError } from "../api/clientsApi";
import * as m09 from "../api/m09CashflowApi";
import * as m10 from "../api/m10ComparisonApi";
import { AppRoutes } from "../routes/AppRoutes";
import { M10ComparisonScreen } from "./M10ComparisonScreen";

const BASELINE_PROVENANCE = "server_resolved_no_scenario_adjustments";

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

function adjustment(
  id: string,
  ordinal = 1,
  type: m09.M09ScenarioSubject["adjustments"][number]["adjustment_type"] = "declared_additional_monthly_income",
  amount = "100.00",
  startMonth = "2026-01",
  endMonth = "2026-02",
): m09.M09ScenarioSubject["adjustments"][number] {
  return {
    adjustment_id: id,
    ordinal,
    adjustment_type: type,
    amount,
    start_month: startMonth,
    end_month: endMonth,
    provenance: "planner_declared_scenario_adjustment",
    semantic_fingerprint: "d".repeat(64),
    actor: "system:m09",
    created_at: "2026-01-01T00:00:00.000000",
  };
}

function subject(
  id: string,
  type: "baseline" | "adjusted",
  createdAt = "2026-01-01T00:00:00.000000",
  label: string | null = type === "baseline" ? null : `Adjusted ${id}`,
): m09.M09ScenarioSubject {
  const adjusted = type === "adjusted";
  return {
    scenario_subject_id: id,
    client_id: 1,
    scenario_family: "declared_retirement_cashflow_adjustments",
    scenario_contract_version: "v1",
    combined_contract_identifier: "declared_retirement_cashflow_adjustments/v1",
    subject_type: type,
    display_label: label,
    adjustment_manifest: adjusted ? {} : { baseline_evidence: BASELINE_PROVENANCE },
    adjustment_manifest_fingerprint: "a".repeat(64),
    calculation_semantic_fingerprint: "b".repeat(64),
    integrity_fingerprint: "c".repeat(64),
    provenance: adjusted ? "planner_declared_scenario_adjustment" : "server_resolved_no_scenario_adjustments",
    actor: "system:m09",
    actor_is_authentication: false,
    created_at: createdAt,
    adjustments: adjusted ? [adjustment(`${id}-adjustment`)] : [],
  };
}

function withAdjustments(
  value: m09.M09ScenarioSubject,
  adjustments: m09.M09ScenarioSubject["adjustments"],
  clientId = value.client_id,
): m09.M09ScenarioSubject {
  return { ...value, client_id: clientId, adjustments };
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
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
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
    expect(await screen.findByRole("heading", { name: "M10 — השוואת תרחישים" })).toBeInTheDocument();
    expect(await screen.findByRole("radio", { name: /Adjusted adjusted/ })).toBeInTheDocument();
  });

  it("rejects an invalid route client without issuing discovery", () => {
    renderScreen("/clients/0/scenario-comparison");
    expect(screen.getByRole("alert")).toHaveTextContent("מזהה הלקוח אינו תקין.");
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

    expect(await screen.findByText("מזהה הרצה: baseline-run")).toBeInTheDocument();
    const labels = screen.getAllByRole("radio").map(input => input.parentElement?.textContent);
    expect(labels).toEqual([
      expect.stringContaining("Tie A"),
      expect.stringContaining("Tie B"),
      expect.stringContaining("Later adjusted"),
    ]);
    expect(screen.queryByText(/Ineligible adjusted/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "השוואת הזוג שנבחר" })).toBeDisabled();
    expect(screen.getByText(/טכני וניטרלי/)).toBeInTheDocument();
  });

  it("fails closed when no baseline subject is present", async () => {
    vi.mocked(m09.listM09Subjects).mockResolvedValue([subject("adjusted", "adjusted")]);
    vi.mocked(m09.listM09SubjectRuns).mockResolvedValue([run("adjusted")]);
    renderScreen();
    expect(await screen.findByText(/לא סיפק הרצת בסיס עדכנית וכשירה/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "השוואת הזוג שנבחר" })).toBeDisabled();
    expect(screen.queryByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).not.toBeInTheDocument();
  });

  it("fails closed when two apparent baseline subjects are returned", async () => {
    vi.mocked(m09.listM09Subjects).mockResolvedValue([
      subject("baseline-1", "baseline"),
      subject("baseline-2", "baseline"),
      subject("adjusted", "adjusted"),
    ]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    expect(await screen.findByText(/תרחיש הבסיס אינו חד־משמעי/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("fails closed when the baseline subject has multiple eligible current runs", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      subjectId === "baseline" ? [run(subjectId, "baseline-1"), run(subjectId, "baseline-2")] : [run(subjectId)],
    ));
    renderScreen();
    expect(await screen.findByText(/תרחיש הבסיס אינו חד־משמעי/)).toBeInTheDocument();
  });

  it("shows the no-adjusted state when adjusted subjects have no eligible current run", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      [run(subjectId, `${subjectId}-run`, subjectId === "baseline")],
    ));
    renderScreen();
    expect(await screen.findByText(/לא סיפק הרצה מותאמת עדכנית וכשירה/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("fails closed instead of choosing among multiple eligible runs for one adjusted subject", async () => {
    readyDiscovery();
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve(
      subjectId === "adjusted" ? [run(subjectId, "adjusted-1"), run(subjectId, "adjusted-2")] : [run(subjectId)],
    ));
    renderScreen();
    expect(await screen.findByText(/תרחיש מותאם אינן חד־משמעיות/)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("treats unexpected subject contract evidence as unavailable without reconstructing it", async () => {
    const invalid = { ...subject("unexpected", "adjusted"), scenario_contract_version: "v2" } as unknown as m09.M09ScenarioSubject;
    vi.mocked(m09.listM09Subjects).mockResolvedValue([subject("baseline", "baseline"), invalid]);
    renderScreen();
    expect(await screen.findByText(/ראיות חוזה התרחיש אינן תקינות/)).toBeInTheDocument();
    expect(m09.listM09SubjectRuns).not.toHaveBeenCalled();
  });

  it("renders exact corroborated server-owned baseline evidence from the retained candidate without a new request", async () => {
    readyDiscovery();
    renderScreen();

    const evidence = await screen.findByRole("region", { name: "תרחיש בסיס שנקבע בשרת" });
    expect(screen.getByText("מזהה תרחיש: baseline")).toBeInTheDocument();
    expect(evidence).toHaveTextContent("אין התאמות תרחיש שהוגדרו על ידי המתכנן.");
    expect(evidence).toHaveTextContent(BASELINE_PROVENANCE);
    expect(evidence).not.toHaveTextContent("evidence unavailable");
    expect(m09.listM09Subjects).toHaveBeenCalledTimes(1);
    expect(m09.listM09SubjectRuns).toHaveBeenCalledTimes(2);
    expect(m10.compareM10Runs).not.toHaveBeenCalled();
  });

  it.each([
    ["missing subject provenance", (value: Record<string, unknown>) => { delete value.provenance; }],
    ["null subject provenance", (value: Record<string, unknown>) => { value.provenance = null; }],
    ["non-string subject provenance", (value: Record<string, unknown>) => { value.provenance = 7; }],
    ["wrong subject provenance", (value: Record<string, unknown>) => { value.provenance = "server_owned"; }],
    ["normalized subject provenance", (value: Record<string, unknown>) => { value.provenance = ` ${BASELINE_PROVENANCE} `; }],
    ["missing manifest marker", (value: Record<string, unknown>) => { value.adjustment_manifest = {}; }],
    ["null manifest marker", (value: Record<string, unknown>) => { value.adjustment_manifest = { baseline_evidence: null }; }],
    ["non-string manifest marker", (value: Record<string, unknown>) => { value.adjustment_manifest = { baseline_evidence: 7 }; }],
    ["wrong manifest marker", (value: Record<string, unknown>) => { value.adjustment_manifest = { baseline_evidence: "server_owned" }; }],
    ["case-changed manifest marker", (value: Record<string, unknown>) => { value.adjustment_manifest = { baseline_evidence: BASELINE_PROVENANCE.toUpperCase() }; }],
    ["null manifest", (value: Record<string, unknown>) => { value.adjustment_manifest = null; }],
    ["array manifest", (value: Record<string, unknown>) => { value.adjustment_manifest = []; }],
    ["primitive manifest", (value: Record<string, unknown>) => { value.adjustment_manifest = BASELINE_PROVENANCE; }],
  ])("fails the optional baseline presentation closed for %s", async (_label, mutate) => {
    const baseline = subject("baseline", "baseline") as unknown as Record<string, unknown>;
    mutate(baseline);
    vi.mocked(m09.listM09Subjects).mockResolvedValue([
      baseline as unknown as m09.M09ScenarioSubject,
      subject("adjusted", "adjusted"),
    ]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();

    const evidence = await screen.findByRole("region", { name: "תרחיש בסיס שנקבע בשרת" });
    expect(within(evidence).getByText("אסמכתת תרחיש הבסיס אינה זמינה.")).toBeInTheDocument();
    expect(evidence).not.toHaveTextContent("No planner-declared scenario adjustments.");
    expect(evidence.querySelector("code")).toBeNull();
  });

  it("never infers baseline meaning from an empty adjustment array", async () => {
    const baseline = subject("empty-only", "baseline") as unknown as Record<string, unknown>;
    delete baseline.provenance;
    baseline.adjustment_manifest = {};
    baseline.adjustments = [];
    vi.mocked(m09.listM09Subjects).mockResolvedValue([
      baseline as unknown as m09.M09ScenarioSubject,
      subject("adjusted", "adjusted"),
    ]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();

    const evidence = await screen.findByRole("region", { name: "תרחיש בסיס שנקבע בשרת" });
    expect(evidence).toHaveTextContent("אסמכתת תרחיש הבסיס אינה זמינה.");
    expect(evidence).not.toHaveTextContent("No planner-declared scenario adjustments.");
  });

  it.each([
    ["wrong client", (value: m09.M09ScenarioSubject) => ({ ...value, client_id: 2 }), run("baseline")],
    ["empty identifier", (value: m09.M09ScenarioSubject) => ({ ...value, scenario_subject_id: "" }), run("")],
    ["subject/run mismatch", (value: m09.M09ScenarioSubject) => value, run("other-subject", "baseline-run")],
  ])("fails the optional baseline presentation closed for reachable %s binding", async (_label, change, baselineRun) => {
    const baseline = change(subject("baseline", "baseline"));
    vi.mocked(m09.listM09Subjects).mockResolvedValue([baseline, subject("adjusted", "adjusted")]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([
      subjectId === baseline.scenario_subject_id ? baselineRun : run(subjectId),
    ]));
    renderScreen();

    const evidence = await screen.findByRole("region", { name: "תרחיש בסיס שנקבע בשרת" });
    expect(evidence).toHaveTextContent("אסמכתת תרחיש הבסיס אינה זמינה.");
  });

  it.each([
    ["wrong role", { subject_type: "adjusted" }],
    ["wrong family", { scenario_family: "other_family" }],
    ["wrong version", { scenario_contract_version: "v2" }],
    ["wrong combined identifier", { combined_contract_identifier: "declared_retirement_cashflow_adjustments/v2" }],
  ])("does not create a baseline-reference panel when discovery rejects %s", async (_label, override) => {
    const invalid = { ...subject("baseline", "baseline"), ...override } as unknown as m09.M09ScenarioSubject;
    vi.mocked(m09.listM09Subjects).mockResolvedValue([invalid, subject("adjusted", "adjusted")]);
    vi.mocked(m09.listM09SubjectRuns).mockResolvedValue([run("baseline")]);
    renderScreen();

    await screen.findByText(/ההשוואה אינה זמינה:/);
    expect(screen.queryByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).not.toBeInTheDocument();
  });

  it.each([
    ["non-current run", run("baseline", "baseline-run", true, false)],
    ["non-eligible run", run("baseline", "baseline-run", false, true)],
  ])("does not create a baseline-reference panel for %s under existing discovery", async (_label, baselineRun) => {
    vi.mocked(m09.listM09Subjects).mockResolvedValue([subject("baseline", "baseline"), subject("adjusted", "adjusted")]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([
      subjectId === "baseline" ? baselineRun : run(subjectId),
    ]));
    renderScreen();

    await screen.findByText(/לא סיפק הרצת בסיס עדכנית וכשירה/);
    expect(screen.queryByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).not.toBeInTheDocument();
  });

  it("keeps malformed optional baseline evidence separate from PKG-017 and comparator success", async () => {
    const baseline = subject("baseline", "baseline") as unknown as Record<string, unknown>;
    baseline.adjustment_manifest = {};
    vi.mocked(m09.listM09Subjects).mockResolvedValue([
      baseline as unknown as m09.M09ScenarioSubject,
      withAdjustments(subject("adjusted", "adjusted"), [adjustment("preserved-occurrence")]),
    ]);
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    vi.mocked(m10.compareM10Runs).mockResolvedValue(comparisonResult());
    renderScreen();

    await selectFirstCandidateAndCompare();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" }))
      .toHaveTextContent("אסמכתת תרחיש הבסיס אינה זמינה.");
    expect(screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" }))
      .toHaveTextContent("preserved-occurrence");
    expect(await screen.findByRole("region", { name: "ראיות לתוצאת ההשוואה" })).toBeInTheDocument();
    expect(m10.compareM10Runs).toHaveBeenCalledWith(1, {
      reference_run_id: "baseline-run",
      compared_run_id: "adjusted-run",
    });
  });

  it("renders both accepted adjustment types with exact literal identity, order, amounts, months, and provenance", async () => {
    const selected = withAdjustments(subject("literal", "adjusted"), [
      adjustment("occurrence-income", 1, "declared_additional_monthly_income", "9007199254740993.00", "2026-01", "2026-03"),
      adjustment("occurrence-expense", 2, "declared_additional_monthly_expense", "999999999999999999.99", "2027-10", "2027-12"),
    ]);
    readyDiscovery([selected]);
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));

    const evidence = screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" });
    expect(evidence).toHaveTextContent("מזהה תרחיש: literal");
    expect(evidence).toHaveTextContent("הכנסה חודשית נוספת מוצהרת");
    expect(evidence).toHaveTextContent("הוצאה חודשית נוספת מוצהרת");
    expect(evidence).toHaveTextContent("9007199254740993.00");
    expect(evidence).toHaveTextContent("999999999999999999.99");
    expect(evidence).toHaveTextContent("2026-01");
    expect(evidence).toHaveTextContent("2026-03");
    expect(evidence).toHaveTextContent("2027-10");
    expect(evidence).toHaveTextContent("2027-12");
    expect(evidence).toHaveTextContent("planner_declared_scenario_adjustment");
    const rows = within(evidence).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("occurrence-income");
    expect(rows[0]).toHaveTextContent("סדר1");
    expect(rows[1]).toHaveTextContent("occurrence-expense");
    expect(rows[1]).toHaveTextContent("סדר2");
  });

  it("preserves duplicate-looking occurrences and authoritative server array order without sorting", async () => {
    const selected = withAdjustments(subject("duplicates", "adjusted"), [
      adjustment("server-first", 1, "declared_additional_monthly_expense", "500.00", "2028-06", "2028-06"),
      adjustment("server-second", 2, "declared_additional_monthly_expense", "500.00", "2028-06", "2028-06"),
      adjustment("server-third", 3, "declared_additional_monthly_income", "0.01", "2025-01", "2025-01"),
    ]);
    readyDiscovery([selected]);
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));

    const rows = within(screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" })).getAllByRole("listitem");
    expect(rows).toHaveLength(3);
    expect(rows.map(row => row.textContent)).toEqual([
      expect.stringContaining("server-first"),
      expect.stringContaining("server-second"),
      expect.stringContaining("server-third"),
    ]);
    expect(rows[0]).toHaveTextContent("500.00");
    expect(rows[1]).toHaveTextContent("500.00");
  });

  it.each([
    ["missing adjustment_id", (row: Record<string, unknown>) => { delete row.adjustment_id; }],
    ["invalid ordinal", (row: Record<string, unknown>) => { row.ordinal = 1.5; }],
    ["unsupported adjustment type", (row: Record<string, unknown>) => { row.adjustment_type = "monthly_income"; }],
    ["invalid amount format", (row: Record<string, unknown>) => { row.amount = "1.0"; }],
    ["amount below minimum", (row: Record<string, unknown>) => { row.amount = "0.00"; }],
    ["amount above maximum", (row: Record<string, unknown>) => { row.amount = "1000000000000000000.00"; }],
    ["invalid start month", (row: Record<string, unknown>) => { row.start_month = "2026-1"; }],
    ["invalid end month", (row: Record<string, unknown>) => { row.end_month = "2026-13"; }],
    ["end before start", (row: Record<string, unknown>) => { row.start_month = "2026-03"; row.end_month = "2026-02"; }],
    ["wrong provenance", (row: Record<string, unknown>) => { row.provenance = "server"; }],
    ["missing required occurrence field", (row: Record<string, unknown>) => { delete row.actor; }],
    ["duplicate occurrence identity", (row: Record<string, unknown>) => { row.adjustment_id = "valid-first"; }],
    ["conflicting array order and ordinal", (row: Record<string, unknown>) => { row.ordinal = 3; }],
  ])("withholds the complete adjustment list for %s without creating a comparator blocker", async (_label, mutate) => {
    const rows = [adjustment("valid-first"), adjustment("malformed-second", 2)];
    mutate(rows[1] as unknown as Record<string, unknown>);
    readyDiscovery([withAdjustments(subject("malformed", "adjusted"), rows)]);
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));

    const evidence = screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" });
    expect(evidence).toHaveTextContent("ראיות התאמת התרחיש אינן זמינות.");
    expect(within(evidence).queryByRole("list")).not.toBeInTheDocument();
    expect(evidence).not.toHaveTextContent("valid-first");
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("withholds an empty adjusted occurrence set as malformed evidence", async () => {
    readyDiscovery([withAdjustments(subject("empty", "adjusted"), [])]);
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));
    const evidence = screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" });
    expect(evidence).toHaveTextContent("ראיות התאמת התרחיש אינן זמינות.");
    expect(within(evidence).queryByRole("list")).not.toBeInTheDocument();
  });

  it.each([
    ["foreign client identity", (value: Record<string, unknown>) => { value.client_id = 2; }],
    ["wrong adjusted-subject provenance", (value: Record<string, unknown>) => { value.provenance = "server"; }],
    ["missing manifest fingerprint", (value: Record<string, unknown>) => { value.adjustment_manifest_fingerprint = ""; }],
    ["missing calculation fingerprint", (value: Record<string, unknown>) => { value.calculation_semantic_fingerprint = null; }],
    ["malformed manifest evidence", (value: Record<string, unknown>) => { value.adjustment_manifest = []; }],
  ])("withholds selected adjustment rows for %s", async (_label, mutate) => {
    const selected = subject("invalid-subject", "adjusted") as unknown as Record<string, unknown>;
    mutate(selected);
    readyDiscovery([selected as unknown as m09.M09ScenarioSubject]);
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));
    const evidence = screen.getByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" });
    expect(evidence).toHaveTextContent("ראיות התאמת התרחיש אינן זמינות.");
    expect(within(evidence).queryByRole("list")).not.toBeInTheDocument();
  });

  it("replaces S1 evidence immediately with only S2 evidence without adding a clear-selection action", async () => {
    const s1 = withAdjustments(subject("S1", "adjusted", "2026-01-02T00:00:00.000000"), [adjustment("S1-occurrence", 1, "declared_additional_monthly_income", "111.11")]);
    const s2 = withAdjustments(subject("S2", "adjusted", "2026-01-03T00:00:00.000000"), [adjustment("S2-occurrence", 1, "declared_additional_monthly_expense", "222.22")]);
    readyDiscovery([s1, s2]);
    renderScreen();
    const radios = await screen.findAllByRole("radio");
    expect(screen.queryByRole("region", { name: "ראיות ההתאמה של התרחיש שנבחר" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear selected scenario" })).not.toBeInTheDocument();
    fireEvent.click(radios[0]);
    expect(screen.getByText("S1-occurrence")).toBeInTheDocument();
    fireEvent.click(radios[1]);
    expect(screen.queryByText("S1-occurrence")).not.toBeInTheDocument();
    expect(screen.getByText("S2-occurrence")).toBeInTheDocument();
    expect(radios[1]).toBeChecked();
    expect(screen.queryByRole("button", { name: "Clear selected scenario" })).not.toBeInTheDocument();
  });

  it("removes selected A evidence immediately when the current candidate is invalidated by A-to-B navigation", async () => {
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => Promise.resolve([
      { ...subject(`${clientId}-baseline`, "baseline"), client_id: clientId },
      withAdjustments(subject(`${clientId}-adjusted`, "adjusted"), [adjustment(`${clientId}-occurrence`, 1, "declared_additional_monthly_income", clientId === 1 ? "111.11" : "222.22")], clientId),
    ]));
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));
    expect(screen.getByText("1-occurrence")).toBeInTheDocument();
    expect(screen.getByText("מזהה תרחיש: 1-baseline")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    expect(screen.queryByText("1-occurrence")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("radio"));
    expect(screen.getByText("2-occurrence")).toBeInTheDocument();
    expect(screen.getByText("מזהה תרחיש: 2-baseline")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).toBeInTheDocument();
    expect(screen.queryByText("111.11")).not.toBeInTheDocument();
  });

  it("does not repopulate A-old evidence in a new A generation after A-to-B-to-A", async () => {
    const newA = deferred<m09.M09ScenarioSubject[]>();
    let aCalls = 0;
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => {
      if (clientId === 2) return Promise.resolve([{ ...subject("B-baseline", "baseline"), client_id: 2 }]);
      aCalls += 1;
      if (aCalls === 2) return newA.promise;
      return Promise.resolve([
        subject("A-old-baseline", "baseline"),
        withAdjustments(subject("A-old-adjusted", "adjusted"), [adjustment("A-old-occurrence", 1, "declared_additional_monthly_income", "9007199254740993.00", "2026-01", "2026-02")]),
      ]);
    });
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    renderScreen();
    fireEvent.click(await screen.findByRole("radio"));
    expect(screen.getByText("A-old-occurrence")).toBeInTheDocument();
    expect(screen.getByText("מזהה תרחיש: A-old-baseline")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await screen.findByText(/לא סיפק הרצה מותאמת עדכנית וכשירה/);
    expect(screen.getByText("מזהה תרחיש: B-baseline")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    expect(screen.queryByText("A-old-occurrence")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).not.toBeInTheDocument();
    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();
    await act(async () => newA.resolve([
      subject("A-new-baseline", "baseline"),
      withAdjustments(subject("A-new-adjusted", "adjusted"), [adjustment("A-new-occurrence", 1, "declared_additional_monthly_expense", "999999999999999999.99", "2028-11", "2028-12")]),
    ]));
    fireEvent.click(await screen.findByRole("radio"));
    expect(screen.getByText("A-new-occurrence")).toBeInTheDocument();
    expect(screen.getByText("מזהה תרחיש: A-new-baseline")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "תרחיש בסיס שנקבע בשרת" })).toBeInTheDocument();
    expect(screen.queryByText("מזהה תרחיש: A-old-baseline")).not.toBeInTheDocument();
    expect(screen.queryByText("A-old-occurrence")).not.toBeInTheDocument();
    expect(screen.queryByText("9007199254740993.00")).not.toBeInTheDocument();
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
    const evidence = await screen.findByRole("region", { name: "ראיות לתוצאת ההשוואה" });
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
    const blocker = await screen.findByRole("region", { name: "חסם השוואה מוכר" });
    expect(within(blocker).getByText(code)).toBeInTheDocument();
    expect(blocker).toHaveTextContent(`server-${code}`);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "ראיות לתוצאת ההשוואה" })).not.toBeInTheDocument();
  });

  it.each([
    ["absent detail", new ApiTransportError({ status: 409, statusText: "Conflict", body: {} })],
    ["non-object detail", new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: "bad" } })],
    ["missing blocker code", new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { message: "missing code" } } })],
    ["missing blocker message", new ApiTransportError({ status: 409, statusText: "Conflict", body: { detail: { code: "comparison_run_not_current" } } })],
    ["unknown structured code", structuredError("comparison_unknown")],
    ["wrong status for accepted code", structuredError("comparison_run_not_current", 404)],
    ["ordinary transport failure", new Error("network unavailable")],
  ])("keeps %s outside accepted business-blocker rendering", async (_label, error) => {
    readyDiscovery();
    vi.mocked(m10.compareM10Runs).mockRejectedValue(error);
    renderScreen();
    await selectFirstCandidateAndCompare();
    expect(await screen.findByRole("alert")).toHaveTextContent("בקשת ההשוואה נכשלה");
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
  });

  it("keeps discovery transport failure distinct from comparison blockers", async () => {
    vi.mocked(m09.listM09Subjects).mockRejectedValue(new Error("discovery offline"));
    renderScreen();
    expect(await screen.findByRole("alert")).toHaveTextContent("איתור ההרצות הכשירות נכשל: discovery offline");
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
    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();
    await act(async () => pendingB.resolve([subject("B-baseline", "baseline")]));
    expect(await screen.findByText(/לא סיפק הרצה מותאמת עדכנית וכשירה/)).toBeInTheDocument();
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
    await screen.findByText(/לא סיפק הרצה מותאמת עדכנית וכשירה/);
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();
    await act(async () => oldA.reject(new Error("A-old discovery failed")));
    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();
    expect(screen.queryByText(/A-old discovery failed/)).not.toBeInTheDocument();
    await act(async () => newA.resolve([subject("A-new-baseline", "baseline"), subject("A-new-adjusted", "adjusted", undefined, "A new adjusted")]));
    expect(await screen.findByRole("radio", { name: /A new adjusted/ })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("makes A-old discovery success a complete no-op during A-new discovery after A-to-B-to-A", async () => {
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
    await screen.findByText(/לא סיפק הרצה מותאמת עדכנית וכשירה/);
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();

    await act(async () => oldA.resolve([
      subject("A-old-baseline", "baseline"),
      subject("A-old-adjusted", "adjusted", undefined, "A old adjusted"),
    ]));

    expect(screen.getByText("טוען הרצות M09 כשירות…")).toBeInTheDocument();
    expect(screen.queryByText(/A old adjusted/)).not.toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "השוואת הזוג שנבחר" })).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "ראיות לתוצאת ההשוואה" })).not.toBeInTheDocument();

    await act(async () => newA.resolve([
      subject("A-new-baseline", "baseline"),
      subject("A-new-adjusted", "adjusted", undefined, "A new adjusted"),
    ]));
    expect(await screen.findByRole("radio", { name: /A new adjusted/ })).not.toBeChecked();
    expect(screen.queryByText(/A old adjusted/)).not.toBeInTheDocument();
    expect(screen.queryByText("טוען הרצות M09 כשירות…")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "השוואת הזוג שנבחר" })).toBeDisabled();
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
    expect(screen.queryByText("טוען את נתוני ההשוואה…")).not.toBeInTheDocument();
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
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();
    await act(async () => oldCompare.reject(new Error("A-old compare failed")));
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();
    expect(screen.queryByText(/A-old compare failed/)).not.toBeInTheDocument();
    await act(async () => newCompare.resolve(comparisonResult("A-new")));
    expect(await screen.findByText("A-new-fingerprint")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("makes A-old compare success a complete no-op during A-new compare after A-to-B-to-A", async () => {
    const oldCompare = deferred<m10.M10ComparisonResponse>();
    const newCompare = deferred<m10.M10ComparisonResponse>();
    let aDiscoveryCalls = 0;
    vi.mocked(m09.listM09Subjects).mockImplementation(clientId => {
      if (clientId === 2) return Promise.resolve([
        subject("B-baseline", "baseline"),
        subject("B-adjusted", "adjusted", undefined, "B adjusted"),
      ]);
      aDiscoveryCalls += 1;
      const marker = aDiscoveryCalls === 1 ? "old" : "new";
      return Promise.resolve([
        subject(`A-${marker}-baseline`, "baseline"),
        subject(`A-${marker}-adjusted`, "adjusted", undefined, `A ${marker} adjusted`),
      ]);
    });
    vi.mocked(m09.listM09SubjectRuns).mockImplementation((_clientId, subjectId) => Promise.resolve([run(subjectId)]));
    vi.mocked(m10.compareM10Runs).mockImplementationOnce(() => oldCompare.promise).mockImplementationOnce(() => newCompare.promise);
    renderScreen();
    await selectFirstCandidateAndCompare();
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await screen.findByRole("radio", { name: /B adjusted/ });
    fireEvent.click(screen.getByRole("button", { name: "Switch A" }));
    const newCandidate = await screen.findByRole("radio", { name: /A new adjusted/ });
    fireEvent.click(newCandidate);
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
    expect(newCandidate).toBeChecked();
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();

    const oldResult = comparisonResult("A-old", 1, "A-old-baseline-run", "A-old-adjusted-run");
    oldResult.monthly_comparisons[0].gross_inflow_total.reference_value = "111.11";
    await act(async () => oldCompare.resolve(oldResult));

    expect(newCandidate).toBeChecked();
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "השוואת הזוג שנבחר" })).toBeDisabled();
    expect(screen.queryByText("A-old-fingerprint")).not.toBeInTheDocument();
    expect(screen.queryByText("A-old-baseline-run")).not.toBeInTheDocument();
    expect(screen.queryByText("A-old-adjusted-run")).not.toBeInTheDocument();
    expect(screen.queryByText("111.11")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "ראיות לתוצאת ההשוואה" })).not.toBeInTheDocument();

    const newResult = comparisonResult("A-new", 1, "A-new-baseline-run", "A-new-adjusted-run");
    newResult.monthly_comparisons[0].gross_inflow_total.reference_value = "222.22";
    await act(async () => newCompare.resolve(newResult));
    const evidence = await screen.findByRole("region", { name: "ראיות לתוצאת ההשוואה" });
    expect(evidence).toHaveTextContent("A-new-fingerprint");
    expect(evidence).toHaveTextContent("A-new-baseline-run");
    expect(evidence).toHaveTextContent("A-new-adjusted-run");
    expect(evidence).toHaveTextContent("222.22");
    expect(newCandidate).toBeChecked();
    expect(screen.queryByText("טוען את נתוני ההשוואה…")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
    fireEvent.click(radios[1]);
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
    await act(async () => r1.resolve(comparisonResult("R1-old", 1, "baseline-run", "adjusted-1-run")));
    expect(screen.queryByText("R1-old-fingerprint")).not.toBeInTheDocument();
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();
    await act(async () => r2.resolve(comparisonResult("R2-new", 1, "baseline-run", "adjusted-2-run")));
    expect(await screen.findByText("R2-new-fingerprint")).toBeInTheDocument();
    expect(screen.queryByText("טוען את נתוני ההשוואה…")).not.toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
    fireEvent.click(radios[1]);
    fireEvent.click(screen.getByRole("button", { name: "השוואת הזוג שנבחר" }));
    await act(async () => r1.reject(structuredError("comparison_run_not_current")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "חסם השוואה מוכר" })).not.toBeInTheDocument();
    expect(radios[1]).toBeChecked();
    expect(screen.getByText("טוען את נתוני ההשוואה…")).toBeInTheDocument();
    await act(async () => r2.resolve(comparisonResult("R2-current", 1, "baseline-run", "adjusted-2-run")));
    expect(await screen.findByText("R2-current-fingerprint")).toBeInTheDocument();
  });
});
