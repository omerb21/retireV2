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
  vi.stubGlobal("fetch", fetcher);
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

test.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "rejects invalid client id %s before any readiness request", async clientId => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
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
  vi.stubGlobal("fetch", fetcher);
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
    vi.stubGlobal("fetch", fetcher);
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
  vi.stubGlobal("fetch", fetcher); renderScreen();
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
  vi.stubGlobal("fetch", vi.fn()
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
  vi.stubGlobal("fetch", vi.fn()
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
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
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
  vi.stubGlobal("fetch", vi.fn()
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
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
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
    vi.stubGlobal("fetch", vi.fn()
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
  vi.stubGlobal("fetch", fetcher);
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
  vi.stubGlobal("fetch", fetcher);
  renderScreen();
  await screen.findByText("קלט התכנון מוכן");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  expect(await screen.findByText(/RTICB_CRTISBA_DECISION_MISSING/)).toBeInTheDocument();
  expect(screen.getByText(/OWNER_DECISION_OD2/)).toBeInTheDocument();
  expect(screen.getByText(/בסיס ההשוואה אינו מוכן/)).toBeInTheDocument();
});
