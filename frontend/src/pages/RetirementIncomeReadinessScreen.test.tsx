import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { RetirementIncomeReadinessScreen } from "./RetirementIncomeReadinessScreen";
import * as generationGuard from "./readinessGenerationGuard";

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
const comparisonEntry = (overrides: Record<string, unknown> = {}) => ({
  source_id: "income:1", source_kind: "RECURRING_INCOME", source_category: "RENTAL",
  admission_state: "INCLUDED", rtisa_reason_codes: [], decision_state: "CURRENT",
  source_version: "d".repeat(64), source_fingerprint: "d".repeat(64),
  amount_authority_fingerprint: "e".repeat(64), decision_version: 1,
  decision_fingerprint: "f".repeat(64), income_basis: "GROSS",
  income_basis_provenance: "UPSTREAM_RECURRING_AMOUNT_BASIS",
  price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date: null,
  price_basis_provenance: "EXPLICIT_PROFESSIONAL", target_income_basis: "GROSS",
  target_price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", target_price_reference_date: null,
  comparison_state: "DIRECTLY_COMPARABLE", reason_codes: [],
  source_comparison_fingerprint: "1".repeat(64), ...overrides,
});
const comparisonSuccess = (entries = [comparisonEntry()], overrides: Record<string, unknown> = {}) => ({
  schema_version: "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2",
  client_id: 7, planning_calculation_input_fingerprint: "a".repeat(64),
  retirement_target_date: "2035-04-01", target_result_fingerprint: "c".repeat(64),
  target_semantic_fingerprint: "b".repeat(64), crtisba_result_fingerprint: "2".repeat(64),
  comparison_input_fingerprint: "3".repeat(64), source_comparisons: entries,
  classification_state: "COMPLETE", classification_complete: true,
  direct_comparison_state: "READY", direct_comparison_ready: true, blockers: [],
  comparison_result_fingerprint: "4".repeat(64), ...overrides,
});
const comparisonFailure = {
  schema_version: "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2",
  client_id: 7, supplied_planning_calculation_input_fingerprint: "a".repeat(64),
  supplied_retirement_target_date: "2035-04-01",
  observed_target_planning_calculation_input_fingerprint: "a".repeat(64),
  observed_target_retirement_target_date: "2035-04-01",
  observed_target_result_fingerprint: "c".repeat(64),
  observed_crtisba_planning_calculation_input_fingerprint: "a".repeat(64),
  observed_crtisba_retirement_target_date: "2035-04-01",
  observed_crtisba_result_fingerprint: "2".repeat(64),
  observed_crtisba_failure_fingerprint: null, observed_crtisba_failure_stage: null,
  observed_crtisba_failure_detail_code: null, result_state: "block_no_result",
  failure_stage: "source_universe", failure_detail_code: "RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID",
  result_fingerprint: "5".repeat(64),
};
const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), {status: 200, headers: {"Content-Type": "application/json"}}));
const sourceEntry = (overrides: Record<string, unknown> = {}) => ({
  schema_version: "CRTISBA_SOURCE_BASIS_ENTRY_V1", source_id: "income:1",
  source_kind: "RECURRING_INCOME", source_category: "RENTAL", admission_state: "INCLUDED",
  rtisa_reason_codes: [], source_version: "d".repeat(64), source_fingerprint: "d".repeat(64),
  amount_authority_fingerprint: "e".repeat(64), decision_version: 1,
  decision_fingerprint: "f".repeat(64), decision_state: "CURRENT", income_basis: "GROSS",
  income_basis_provenance: "UPSTREAM_RECURRING_AMOUNT_BASIS",
  price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", price_reference_date: null,
  price_basis_provenance: "EXPLICIT_PROFESSIONAL", blockers: [], ...overrides,
});
const sourceCollection = (entries: unknown[] = [], clientId = 7) => ({
  schema_version: "CRTISBA_COLLECTION_RESULT_V1", client_id: clientId,
  planning_calculation_input_fingerprint: "a".repeat(64), retirement_target_date: "2035-04-01",
  rtisa_admission_result_fingerprint: "1".repeat(64), source_basis_entries: entries,
  partitions: {}, blockers: [], basis_readiness_state: "READY", basis_ready: true,
  result_fingerprint: "2".repeat(64),
});

function stubReadinessFetch(fetcher: ReturnType<typeof vi.fn>, sources = sourceCollection()) {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/source-bases") && (init?.method ?? "GET") === "GET") {
      const clientId = Number(url.match(/\/clients\/(\d+)\//)?.[1] ?? sources.client_id);
      return response({...sources, client_id: clientId});
    }
    return fetcher(input, init);
  }));
}

function stubDynamicSourceFetch(
  fetcher: ReturnType<typeof vi.fn>,
  readSources: (clientId: number) => Promise<Response>,
) {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/source-bases") && (init?.method ?? "GET") === "GET") {
      const clientId = Number(url.match(/\/clients\/(\d+)\//)?.[1]);
      return readSources(clientId);
    }
    return fetcher(input, init);
  }));
}

function renderScreen() {
  return render(<MemoryRouter initialEntries={["/clients/7/retirement-income-readiness"]}><Routes>
    <Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} />
  </Routes></MemoryRouter>);
}

const contextFor = (clientId: number, targetDate = "2035-04-01") => ({...context, client_id: clientId, retirement_target_date: targetDate});
const targetFor = (clientId: number, monthlyAmount = "12000.00") => ({
  ...target, client_id: clientId, target: {...target.target, monthly_amount: monthlyAmount},
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}

function NavigationControls() {
  const navigate = useNavigate();
  return <><button onClick={() => navigate("/clients/8/retirement-income-readiness")}>לקוח B</button>
    <button onClick={() => navigate("/clients/7/retirement-income-readiness")}>לקוח A</button></>;
}

afterEach(() => vi.unstubAllGlobals());

test("renders exact readiness evidence and preserves block_no_result as a professional result", async () => {
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparisonFailure));
  stubReadinessFetch(fetcher);
  renderScreen();
  expect(await screen.findByText("קלט התכנון מוכן")).toBeInTheDocument();
  expect(screen.getByText(/01\/04\/2035/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText(/RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID/)).toBeInTheDocument();
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
  stubReadinessFetch(fetcher);
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

test.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "rejects invalid client id %s before any readiness request", async clientId => {
    const fetcher = vi.fn(); stubReadinessFetch(fetcher);
    render(<MemoryRouter initialEntries={[`/clients/${clientId}/retirement-income-readiness`]}><Routes>
      <Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} />
    </Routes></MemoryRouter>);
    expect(screen.getByRole("alert")).toHaveTextContent("מזהה לקוח אינו תקין");
    expect(fetcher).not.toHaveBeenCalled();
  },
);

test("A-to-B-to-A aborts old reads and generation guard rejects their late response", async () => {
  const oldA = deferred<Response>();
  const fetcher = vi.fn()
    .mockImplementationOnce((_url, init) => { expect(init.signal).toBeInstanceOf(AbortSignal); return oldA.promise; })
    .mockImplementationOnce(() => response(contextFor(8, "2040-02-02")))
    .mockImplementationOnce(() => response(targetFor(8, "22000.00")))
    .mockImplementationOnce(() => response(contextFor(7, "2045-03-03")))
    .mockImplementationOnce(() => response(targetFor(7, "33000.00")));
  stubReadinessFetch(fetcher);
  render(<MemoryRouter initialEntries={["/clients/7/retirement-income-readiness"]}>
    <NavigationControls /><Routes><Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} /></Routes>
  </MemoryRouter>);
  const firstSignal = fetcher.mock.calls[0][1].signal as AbortSignal;
  fireEvent.click(screen.getByRole("button", {name: "לקוח B"}));
  expect(await screen.findByDisplayValue("22000.00")).toBeInTheDocument();
  expect(firstSignal.aborted).toBe(true);
  fireEvent.click(screen.getByRole("button", {name: "לקוח A"}));
  expect(await screen.findByDisplayValue("33000.00")).toBeInTheDocument();
  oldA.resolve(await response(contextFor(7, "1999-01-01")));
  await waitFor(() => expect(screen.queryByText(/01\/01\/1999/)).not.toBeInTheDocument());
  expect(screen.getByDisplayValue("33000.00")).toBeInTheDocument();
  expect(screen.getByText(/03\/03\/2045/)).toBeInTheDocument();
});

test("ordinary client-isolation oracle kills and restores disabled generation protection", async () => {
  const ordinary = async () => {
    const oldA = deferred<Response>();
    const fetcher = vi.fn()
      .mockImplementationOnce(() => oldA.promise)
      .mockImplementationOnce(() => response(contextFor(8, "2040-02-02")))
      .mockImplementationOnce(() => response(targetFor(8, "22000.00")))
      .mockImplementationOnce(() => response(targetFor(7, "99000.00")));
    stubReadinessFetch(fetcher);
    const view = render(<MemoryRouter initialEntries={["/clients/7/retirement-income-readiness"]}>
      <NavigationControls /><Routes><Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} /></Routes>
    </MemoryRouter>);
    try {
      fireEvent.click(screen.getByRole("button", {name: "לקוח B"}));
      expect(await screen.findByDisplayValue("22000.00")).toBeInTheDocument();
      oldA.resolve(await response(contextFor(7, "1999-01-01")));
      await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(4));
      await new Promise(resolve => setTimeout(resolve, 50));
      expect(screen.queryByText(/01\/01\/1999/)).not.toBeInTheDocument();
      expect(screen.getByDisplayValue("22000.00")).toBeInTheDocument();
    } finally {
      view.unmount();
    }
  };

  await ordinary();
  const currentMutation = vi.spyOn(generationGuard.generationPolicy, "isCurrent").mockReturnValue(true);
  const keyMutation = vi.spyOn(generationGuard.generationPolicy, "workspaceKey").mockReturnValue("shared");
  let killed = false;
  try {
    await ordinary();
  } catch {
    killed = true;
  } finally {
    currentMutation.mockRestore();
    keyMutation.mockRestore();
  }
  expect(killed).toBe(true);
  await ordinary();
});

test("CAS conflict is not retried and only explicit refresh requests fresh state", async () => {
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockResolvedValueOnce(new Response(JSON.stringify({code: "TARGET_VERSION_CONFLICT"}), {status: 409}))
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(targetFor(7, "14000.00")));
  stubReadinessFetch(fetcher); renderScreen();
  expect(await screen.findByDisplayValue("12000.00")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "אישור מפורש של היעד"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("יש לרענן לפני ניסיון נוסף");
  expect(fetcher).toHaveBeenCalledTimes(3);
  fireEvent.click(screen.getByRole("button", {name: "רענון מפורש"}));
  expect(await screen.findByDisplayValue("14000.00")).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(5);
});

test.each([
  ["MISSING", "MISSING", "חסר"],
  ["INVALID", "INVALID", "אינו תקין"],
  ["STALE", "STALE", "מיושן ונדרש אישור מחדש"],
  ["UNAVAILABLE", "UNAVAILABLE", "אינו זמין"],
  ["CURRENT", "READY", "נוכחי"],
])("renders distinct target authority state %s", async (authorityState, readinessState, label) => {
  stubReadinessFetch(vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response({...target, authority_state: authorityState, target_readiness_state: readinessState, target_ready: authorityState === "CURRENT"})));
  renderScreen();
  expect(await screen.findByText(new RegExp(label))).toBeInTheDocument();
  expect(screen.getByText(new RegExp(`מצב סמכות:`))).toHaveTextContent(labelsForTest(authorityState));
});

function labelsForTest(code: string) {
  return ({MISSING: "חסר", INVALID: "אינו תקין", STALE: "מיושן ונדרש אישור מחדש", UNAVAILABLE: "אינו זמין", CURRENT: "נוכחי"} as Record<string, string>)[code];
}

test("successful comparison preserves blocker source and reason order including excluded entries", async () => {
  const comparison = comparisonSuccess([
    comparisonEntry({source_id: "income:1", comparison_state: "NORMALIZATION_REQUIRED", reason_codes: ["NORMALIZE_A", "NORMALIZE_B"], income_basis: "NET"}),
    comparisonEntry({source_id: "income:2", admission_state: "EXCLUDED", decision_state: "NOT_APPLICABLE_NOT_ADMITTED", comparison_state: "NOT_ADMITTED", reason_codes: ["RTICB_SOURCE_NOT_ADMITTED"], income_basis: null, income_basis_provenance: null, price_basis: null, price_basis_provenance: null, amount_authority_fingerprint: null, decision_version: null, decision_fingerprint: null}),
  ], {direct_comparison_state: "NOT_READY", direct_comparison_ready: false, blockers: ["RTICB_NORMALIZATION_REQUIRED"]});
  stubReadinessFetch(vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  const result = await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"});
  const section = result.closest("section")!;
  const text = section.textContent ?? "";
  expect(text).toContain("RTICB_NORMALIZATION_REQUIRED");
  expect(text.indexOf("income:1")).toBeLessThan(text.indexOf("income:2"));
  expect(text.indexOf("NORMALIZE_A")).toBeLessThan(text.indexOf("NORMALIZE_B"));
  expect(text).toContain("EXCLUDED"); expect(text).toContain("NOT_ADMITTED");
  expect(text).toContain("NORMALIZATION_REQUIRED"); expect(text).toContain("NOT_APPLICABLE_NOT_ADMITTED");
});

test("direct comparability does not invent income availability funding or portfolio readiness", async () => {
  const comparison = comparisonSuccess();
  stubReadinessFetch(vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  const section = (await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).closest("section")!;
  expect(within(section).getByText("בסיס ההשוואה מוכן")).toBeInTheDocument();
  expect(section).not.toHaveTextContent(/הכנסה זמינה|מימון מוכן|תיק מוכן/);
});

test("renders delegated unresolved nullable and NOT_READY V2 evidence without inference", async () => {
  const nullBasis = {
    income_basis: null, income_basis_provenance: null, price_basis: null,
    price_reference_date: null, price_basis_provenance: null,
    amount_authority_fingerprint: null, decision_version: null, decision_fingerprint: null,
  };
  const comparison = comparisonSuccess([
    comparisonEntry({
      source_id: "income:delegated", source_category: "PENSION_REPRESENTATION",
      admission_state: "EXCLUDED", rtisa_reason_codes: ["RTISA_SAME_CANONICAL_PENSION"],
      decision_state: "NOT_APPLICABLE_DELEGATED", comparison_state: "NOT_ADMITTED",
      reason_codes: ["RTICB_SOURCE_NOT_ADMITTED"], ...nullBasis,
    }),
    comparisonEntry({
      source_id: "income:unresolved", source_category: "PENSION_REPRESENTATION",
      admission_state: "UNRESOLVED", rtisa_reason_codes: ["RTISA_SOURCE_IDENTITY_UNRESOLVED"],
      decision_state: "DELEGATION_UNRESOLVED", comparison_state: "BASIS_UNRESOLVED",
      reason_codes: ["RTICB_CRTISBA_DELEGATION_UNRESOLVED"], ...nullBasis,
    }),
  ], {
    direct_comparison_state: "NOT_READY", direct_comparison_ready: false,
    blockers: ["RTICB_BASIS_UNRESOLVED"],
  });
  stubReadinessFetch(vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText("RTICB_BASIS_UNRESOLVED")).toBeInTheDocument();
  const delegated = screen.getByRole("heading", {name: "income:delegated"}).closest("article")!;
  const unresolved = screen.getByRole("heading", {name: "income:unresolved"}).closest("article")!;
  expect(delegated).toHaveTextContent("NOT_APPLICABLE_DELEGATED");
  expect(delegated).toHaveTextContent("NOT_ADMITTED");
  expect(unresolved).toHaveTextContent("DELEGATION_UNRESOLVED");
  expect(unresolved).toHaveTextContent("BASIS_UNRESOLVED");
  expect(within(delegated).getAllByText("לא נקבע")).toHaveLength(5);
  expect(within(unresolved).getAllByText("לא נקבע")).toHaveLength(5);
  expect(delegated).not.toHaveTextContent(/GROSS|NET|NOMINAL|REAL/);
  expect(unresolved).not.toHaveTextContent(/GROSS|NET|NOMINAL|REAL/);
});

test("unknown technical and professional codes use neutral presentation and preserve exact codes", async () => {
  const comparison = comparisonSuccess([
    comparisonEntry({comparison_state: "BASIS_UNRESOLVED", reason_codes: ["UNKNOWN_REASON"]}),
  ], {direct_comparison_state: "NOT_READY", direct_comparison_ready: false, blockers: ["UNKNOWN_BLOCKER"]});
  stubReadinessFetch(vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  await screen.findByText("UNKNOWN_BLOCKER");
  for (const code of ["UNKNOWN_BLOCKER", "UNKNOWN_REASON"]) {
    expect(screen.getByText(code)).toBeInTheDocument();
  }
  const section = screen.getByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"}).closest("section")!;
  expect(section.textContent?.match(/נדרש טיפול מקצועי/g)?.length).toBeGreaterThanOrEqual(2);
});

test("ordinary comparison presentation oracle kills and restores ordering and visibility mapping mutation", async () => {
  const comparison = comparisonSuccess([
    comparisonEntry({source_id: "income:1", comparison_state: "NORMALIZATION_REQUIRED", reason_codes: ["NORMALIZE_A", "NORMALIZE_B"], income_basis: "NET"}),
    comparisonEntry({source_id: "income:2", admission_state: "EXCLUDED", decision_state: "NOT_APPLICABLE_NOT_ADMITTED", comparison_state: "NOT_ADMITTED", reason_codes: ["RTICB_SOURCE_NOT_ADMITTED"], income_basis: null, income_basis_provenance: null, price_basis: null, price_basis_provenance: null, amount_authority_fingerprint: null, decision_version: null, decision_fingerprint: null}),
  ], {direct_comparison_state: "NOT_READY", direct_comparison_ready: false, blockers: ["RTICB_NORMALIZATION_REQUIRED"]});

  const ordinary = async () => {
    stubReadinessFetch(vi.fn()
      .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
      .mockImplementationOnce(() => response(comparison)));
    const view = renderScreen();
    try {
      await screen.findByDisplayValue("12000.00");
      fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
      const section = (await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).closest("section")!;
      const text = section.textContent ?? "";
      expect(text.indexOf("income:1")).toBeLessThan(text.indexOf("income:2"));
      expect(text.indexOf("NORMALIZE_A")).toBeLessThan(text.indexOf("NORMALIZE_B"));
      expect(text).toContain("EXCLUDED");
      expect(text).toContain("NOT_ADMITTED");
      expect(text).not.toMatch(/הכנסה זמינה|מימון מוכן|תיק מוכן/);
    } finally {
      view.unmount();
    }
  };

  await ordinary();
  const originalMap = Array.prototype.map;
  let mutationReached = false;
  Array.prototype.map = function (this: unknown[], callback: unknown, thisArg?: unknown) {
    const values = this as unknown[];
    if (values[0] === "NORMALIZE_A") {
      mutationReached = true;
      return originalMap.call([...values].reverse(), callback as never, thisArg) as never;
    }
    if ((values[0] as {source_id?: string} | undefined)?.source_id === "income:1") {
      mutationReached = true;
      return originalMap.call(values.slice(1), callback as never, thisArg) as never;
    }
    return originalMap.call(values, callback as never, thisArg) as never;
  } as typeof Array.prototype.map;
  let killed = false;
  try {
    await ordinary();
  } catch {
    killed = true;
  } finally {
    Array.prototype.map = originalMap;
  }
  expect(mutationReached).toBe(true);
  expect(killed).toBe(true);
  await ordinary();
});


test("projects accepted UNKNOWN decision and missing income/price provenance without inference", async () => {
  const entry = comparisonEntry({
    decision_state: "UNKNOWN", income_basis: "UNKNOWN",
    income_basis_provenance: "MISSING", price_basis: "UNKNOWN",
    price_basis_provenance: "MISSING", price_reference_date: null,
    comparison_state: "BASIS_UNRESOLVED", reason_codes: ["RTICB_CRTISBA_DECISION_UNKNOWN"],
  });
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparisonSuccess([entry], {
      direct_comparison_state: "NOT_READY", direct_comparison_ready: false,
      blockers: ["RTICB_BASIS_UNRESOLVED"],
    })));
  stubReadinessFetch(fetcher);
  renderScreen();
  await screen.findByText("קלט התכנון מוכן");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText(/RTICB_CRTISBA_DECISION_UNKNOWN/)).toBeInTheDocument();
  expect(screen.getByText(/בסיס ההשוואה אינו מוכן/)).toBeInTheDocument();
  expect(screen.getByText(/בסיס הכנסה:/)).toHaveTextContent("UNKNOWN");
  expect(screen.getByText(/בסיס מחירים:/)).toHaveTextContent("MISSING");
});

test("renders accepted pension OWNER_DECISION_OD2 and empty missing provenance", async () => {
  const pension = comparisonEntry({
    source_id: "manual:1", source_kind: "PENSION",
    income_basis: "GROSS", income_basis_provenance: "EXPLICIT_PROFESSIONAL",
    price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE",
    price_basis_provenance: "OWNER_DECISION_OD2",
    decision_state: "CURRENT",
  });
  const missing = comparisonEntry({
    source_id: "income:2", decision_state: "MISSING",
    income_basis: "UNKNOWN", income_basis_provenance: "MISSING",
    price_basis: "UNKNOWN", price_basis_provenance: "MISSING",
    comparison_state: "BASIS_UNRESOLVED", reason_codes: ["RTICB_CRTISBA_DECISION_MISSING"],
  });
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context))
    .mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparisonSuccess([pension, missing], {
      direct_comparison_state: "NOT_READY", direct_comparison_ready: false,
      blockers: ["RTICB_BASIS_UNRESOLVED"],
    })));
  stubReadinessFetch(fetcher);
  renderScreen();
  await screen.findByText("קלט התכנון מוכן");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText(/RTICB_CRTISBA_DECISION_MISSING/)).toBeInTheDocument();
  expect(screen.getByText(/OWNER_DECISION_OD2/)).toBeInTheDocument();
  expect(screen.getByText(/בסיס ההשוואה אינו מוכן/)).toBeInTheDocument();
});

test("saves an exact pension CLASSIFY command with server CAS values and reloads authority", async () => {
  const pension = sourceEntry({
    source_id: "manual:9", source_kind: "PENSION", source_category: "PENSION",
    source_version: 5, source_fingerprint: "6".repeat(64), amount_authority_fingerprint: "7".repeat(64),
    decision_version: null, decision_fingerprint: null, decision_state: "MISSING",
    income_basis: null, income_basis_provenance: null,
    price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE", price_basis_provenance: "OWNER_DECISION_OD2",
  });
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response({client_id: 7, decision_state: "CURRENT"}))
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target));
  stubReadinessFetch(fetcher, sourceCollection([pension]));
  renderScreen();
  const article = (await screen.findByRole("heading", {name: "manual:9"})).closest("article")!;
  fireEvent.change(within(article).getByLabelText(/בסיס הכנסה למקור/), {target: {value: "NET"}});
  fireEvent.click(within(article).getByRole("button", {name: "שמירת החלטת בסיס עבור manual:9"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
  const request = fetcher.mock.calls[2];
  expect(request[0]).toContain("/source-bases/manual%3A9");
  expect(JSON.parse(request[1].body)).toEqual({
    schema_version: "CRTISBA_PENSION_CLASSIFY_COMMAND_V1", operation: "CLASSIFY", source_kind: "PENSION",
    expected_decision_version: 0, expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_source_version: 5, expected_source_fingerprint: "6".repeat(64),
    expected_amount_authority_fingerprint: "7".repeat(64), income_basis: "NET",
  });
});

test("saves exact recurring CLASSIFY and CLEAR commands without professional defaults", async () => {
  const recurring = sourceEntry({decision_state: "MISSING", decision_version: null, decision_fingerprint: null,
    price_basis: "UNKNOWN", price_basis_provenance: "MISSING"});
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response({client_id: 7, decision_state: "CURRENT"}))
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target));
  stubReadinessFetch(fetcher, sourceCollection([recurring]));
  const first = renderScreen();
  const article = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  const priceSelect = within(article).getByLabelText(/בסיס מחירים למקור/);
  expect(priceSelect).toHaveValue("");
  fireEvent.change(priceSelect, {target: {value: "REAL_AT_REFERENCE_DATE"}});
  fireEvent.change(within(article).getByLabelText(/תאריך ייחוס למקור/), {target: {value: "03/02/2030"}});
  fireEvent.click(within(article).getByRole("button", {name: "שמירת החלטת בסיס עבור income:1"}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(5));
  expect(JSON.parse(fetcher.mock.calls[2][1].body)).toEqual({
    schema_version: "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1", operation: "CLASSIFY", source_kind: "RECURRING_INCOME",
    expected_decision_version: 0, expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_source_version: "d".repeat(64), expected_source_fingerprint: "d".repeat(64),
    expected_amount_authority_fingerprint: "e".repeat(64), price_basis: "REAL_AT_REFERENCE_DATE",
    price_reference_date: "2030-02-03",
  });
  first.unmount();

  const clearFetcher = vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response({client_id: 7, decision_state: "UNKNOWN"}))
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target));
  stubReadinessFetch(clearFetcher, sourceCollection([sourceEntry()]));
  const second = renderScreen();
  const current = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  fireEvent.click(within(current).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:1"}));
  await waitFor(() => expect(clearFetcher).toHaveBeenCalledTimes(5));
  expect(JSON.parse(clearFetcher.mock.calls[2][1].body)).toEqual({
    schema_version: "CRTISBA_RECURRING_CLEAR_COMMAND_V1", operation: "CLEAR", source_kind: "RECURRING_INCOME",
    expected_decision_version: 1, expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_source_version: "d".repeat(64), expected_source_fingerprint: "d".repeat(64),
    expected_amount_authority_fingerprint: "e".repeat(64),
  });
  second.unmount();
});

test("forbidden source has no decision controls", async () => {
  const forbidden = sourceEntry({
    source_id: "income:delegated", source_category: "PENSION_REPRESENTATION", admission_state: "UNRESOLVED",
    decision_state: "DELEGATION_UNRESOLVED", amount_authority_fingerprint: null, decision_version: null,
  });
  const fetcher = vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target));
  stubReadinessFetch(fetcher, sourceCollection([forbidden]));
  renderScreen();
  const article = (await screen.findByRole("heading", {name: "income:delegated"})).closest("article")!;
  expect(within(article).getByText("לא ניתן לעדכן החלטה למקור זה לפי מצב הסמכות הנוכחי.")).toBeInTheDocument();
  expect(within(article).queryByRole("button")).not.toBeInTheDocument();
});

test("409 source conflict is never retried and refreshes authority before another explicit write", async () => {
  const fetcher = vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({code: "CRTISBA_SOURCE_VERSION_STALE"}), {status: 409})))
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target));
  stubReadinessFetch(fetcher, sourceCollection([sourceEntry()]));
  renderScreen();
  const article = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  fireEvent.click(within(article).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:1"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("CRTISBA_SOURCE_VERSION_STALE");
  expect(screen.getByRole("alert")).toHaveTextContent("נתוני הסמכות רועננו");
  expect(fetcher).toHaveBeenCalledTimes(5);
  expect(fetcher.mock.calls.filter(call => call[1]?.method === "PUT")).toHaveLength(1);
});

test("unknown commit outcome hides stale authority, never retries PUT, and uses only refreshed CAS", async () => {
  const refreshContext = deferred<Response>();
  let contextReads = 0;
  let sourceReads = 0;
  const putBodies: Array<Record<string, unknown>> = [];
  let comparisonCount = 0;
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/context")) {
      contextReads += 1;
      return contextReads === 2 ? refreshContext.promise : response(context);
    }
    if (url.endsWith("/target")) return response(target);
    if (url.endsWith("/comparison")) { comparisonCount += 1; return response(comparisonSuccess()); }
    if (url.includes("/source-bases/") && method === "PUT") {
      putBodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
      return putBodies.length === 1
        ? Promise.resolve(new Response(JSON.stringify({code: "CRTISBA_COMMIT_OUTCOME_UNKNOWN"}), {status: 503}))
        : response({client_id: 7, decision_state: "UNKNOWN"});
    }
    throw new Error(`Unexpected request ${method} ${url}`);
  });
  stubDynamicSourceFetch(fetcher, clientId => {
    sourceReads += 1;
    const entry = sourceReads === 1 ? sourceEntry() : sourceEntry({
      decision_version: 9, decision_fingerprint: "9".repeat(64),
      source_version: "8".repeat(64), source_fingerprint: "8".repeat(64),
      amount_authority_fingerprint: "7".repeat(64),
    });
    return response(sourceCollection([entry], clientId));
  });

  renderScreen();
  let article = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).toBeInTheDocument();
  fireEvent.click(within(article).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:1"}));
  await waitFor(() => expect(contextReads).toBe(2));
  expect(screen.queryByRole("heading", {name: "income:1"})).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).not.toBeInTheDocument();
  const blockedComparison = screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"});
  expect(blockedComparison).toBeDisabled();
  fireEvent.click(blockedComparison);
  expect(comparisonCount).toBe(1);
  expect(putBodies).toHaveLength(1);

  refreshContext.resolve(await response(context));
  expect(await screen.findByRole("alert")).toHaveTextContent("לא ניתן לקבוע אם ההחלטה נשמרה");
  article = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  expect(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"})).toBeEnabled();
  expect(putBodies).toHaveLength(1);
  fireEvent.click(within(article).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:1"}));
  await waitFor(() => expect(putBodies).toHaveLength(2));
  expect(putBodies[1]).toMatchObject({
    expected_decision_version: 9,
    expected_source_version: "8".repeat(64),
    expected_source_fingerprint: "8".repeat(64),
    expected_amount_authority_fingerprint: "7".repeat(64),
  });
});

test("network failure after PUT keeps authority blocked when refresh fails until explicit refresh succeeds", async () => {
  let sourceReads = 0;
  let putCount = 0;
  let comparisonCount = 0;
  const comparisonBodies: Array<Record<string, unknown>> = [];
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/context")) return response(context);
    if (url.endsWith("/target")) return response(target);
    if (url.endsWith("/comparison") && method === "POST") {
      comparisonCount += 1;
      comparisonBodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
      return response(comparisonSuccess());
    }
    if (url.includes("/source-bases/") && method === "PUT") {
      putCount += 1;
      return Promise.reject(new TypeError("network connection lost after request dispatch"));
    }
    throw new Error(`Unexpected request ${method} ${url}`);
  });
  stubDynamicSourceFetch(fetcher, clientId => {
    sourceReads += 1;
    if (sourceReads === 2) return Promise.reject(new TypeError("authority refresh unavailable"));
    return response(sourceCollection([sourceEntry()], clientId));
  });

  renderScreen();
  const article = (await screen.findByRole("heading", {name: "income:1"})).closest("article")!;
  fireEvent.click(within(article).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:1"}));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("לא ניתן לקבוע אם ההחלטה נשמרה");
  expect(alert).toHaveTextContent("נדרש רענון מפורש");
  expect(screen.queryByRole("heading", {name: "income:1"})).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).not.toBeInTheDocument();
  const blockedComparison = screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"});
  expect(blockedComparison).toBeDisabled();
  fireEvent.click(blockedComparison);
  expect(comparisonCount).toBe(0);
  expect(putCount).toBe(1);
  fireEvent.click(screen.getByRole("button", {name: "רענון מפורש"}));
  expect(await screen.findByRole("heading", {name: "income:1"})).toBeInTheDocument();
  const restoredComparison = screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"});
  expect(restoredComparison).toBeEnabled();
  fireEvent.click(restoredComparison);
  await waitFor(() => expect(comparisonCount).toBe(1));
  expect(comparisonBodies).toEqual([{
    expected_planning_calculation_input_fingerprint: "a".repeat(64),
    expected_retirement_target_date: "2035-04-01",
  }]);
  expect(putCount).toBe(1);
});

test("late unknown-outcome refresh from client A cannot alter client B authority or error state", async () => {
  const lateAContext = deferred<Response>();
  let aContextReads = 0;
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const clientId = Number(url.match(/\/clients\/(\d+)\//)?.[1]);
    const method = init?.method ?? "GET";
    if (url.endsWith("/context")) {
      if (clientId === 7) {
        aContextReads += 1;
        return aContextReads === 2 ? lateAContext.promise : response(contextFor(7));
      }
      return response(contextFor(8, "2040-02-02"));
    }
    if (url.endsWith("/target")) return response(targetFor(clientId, clientId === 8 ? "22000.00" : "12000.00"));
    if (url.includes("/source-bases/") && method === "PUT") {
      return Promise.resolve(new Response(JSON.stringify({code: "CRTISBA_COMMIT_OUTCOME_UNKNOWN"}), {status: 503}));
    }
    throw new Error(`Unexpected request ${method} ${url}`);
  });
  stubDynamicSourceFetch(fetcher, clientId => response(sourceCollection([
    sourceEntry({source_id: `income:${clientId}`}),
  ], clientId)));

  render(<MemoryRouter initialEntries={["/clients/7/retirement-income-readiness"]}>
    <NavigationControls /><Routes><Route path="/clients/:clientId/retirement-income-readiness" element={<RetirementIncomeReadinessScreen />} /></Routes>
  </MemoryRouter>);
  const articleA = (await screen.findByRole("heading", {name: "income:7"})).closest("article")!;
  fireEvent.click(within(articleA).getByRole("button", {name: "ניקוי החלטת בסיס עבור income:7"}));
  await waitFor(() => expect(aContextReads).toBe(2));
  fireEvent.click(screen.getByRole("button", {name: "לקוח B"}));
  expect(await screen.findByRole("heading", {name: "income:8"})).toBeInTheDocument();
  lateAContext.resolve(await response(contextFor(7, "1999-01-01")));
  await Promise.resolve();
  expect(screen.queryByText(/לא ניתן לקבוע אם ההחלטה נשמרה/)).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", {name: "income:7"})).not.toBeInTheDocument();
  expect(screen.getByRole("heading", {name: "income:8"})).toBeInTheDocument();
});
