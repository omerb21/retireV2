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
  const comparison = {
    schema_version: "RTICB_RESULT_V1", client_id: 7, direct_comparison_state: "NOT_READY", direct_comparison_ready: false,
    blockers: ["BLOCKER_Z", "BLOCKER_A"], source_comparisons: [
      {source_id: "income:2", comparison_state: "BASIS_UNRESOLVED", reason_codes: ["REASON_2", "REASON_1"], rtisa_admission_state: "EXCLUDED", source_income_basis: "GROSS", source_price_basis: "NOMINAL"},
      {source_id: "income:1", comparison_state: "NORMALIZATION_REQUIRED", reason_codes: ["NORMALIZE_B", "NORMALIZE_A"], rtisa_admission_state: "NOT_ADMITTED", source_income_basis: "NET", source_price_basis: "REAL"},
    ],
  };
  vi.stubGlobal("fetch", vi.fn()
    .mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target))
    .mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  const result = await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"});
  const section = result.closest("section")!;
  const text = section.textContent ?? "";
  expect(text.indexOf("BLOCKER_Z")).toBeLessThan(text.indexOf("BLOCKER_A"));
  expect(text.indexOf("income:2")).toBeLessThan(text.indexOf("income:1"));
  expect(text.indexOf("REASON_2")).toBeLessThan(text.indexOf("REASON_1"));
  expect(text).toContain("EXCLUDED"); expect(text).toContain("NOT_ADMITTED");
  expect(text).toContain("NORMALIZATION_REQUIRED"); expect(text).toContain("BASIS_UNRESOLVED");
});

test("direct comparability does not invent income availability funding or portfolio readiness", async () => {
  const comparison = {client_id: 7, direct_comparison_state: "DIRECTLY_COMPARABLE", direct_comparison_ready: true, blockers: [], source_comparisons: [
    {source_id: "income:1", comparison_state: "DIRECTLY_COMPARABLE", reason_codes: [], rtisa_admission_state: "READY", source_income_basis: "GROSS", source_price_basis: "NOMINAL"},
  ]};
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  const section = (await screen.findByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"})).closest("section")!;
  expect(within(section).getByText("בסיס ההשוואה מוכן")).toBeInTheDocument();
  expect(section).not.toHaveTextContent(/הכנסה זמינה|מימון מוכן|תיק מוכן/);
});

test("unknown technical and professional codes use neutral presentation and preserve exact codes", async () => {
  const comparison = {client_id: 7, direct_comparison_ready: false, blockers: ["UNKNOWN_BLOCKER"], source_comparisons: [
    {source_id: "income:1", comparison_state: "UNKNOWN_COMPARISON", reason_codes: ["UNKNOWN_REASON"], rtisa_admission_state: "UNKNOWN_ADMISSION", source_income_basis: "GROSS", source_price_basis: "NOMINAL"},
  ]};
  vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(context)).mockImplementationOnce(() => response(target)).mockImplementationOnce(() => response(comparison)));
  renderScreen(); await screen.findByDisplayValue("12000.00");
  fireEvent.click(screen.getByRole("button", {name: "בדיקת בסיסי ההשוואה"}));
  await screen.findByText("UNKNOWN_BLOCKER");
  for (const code of ["UNKNOWN_BLOCKER", "UNKNOWN_COMPARISON", "UNKNOWN_ADMISSION", "UNKNOWN_REASON"]) {
    expect(screen.getByText(code)).toBeInTheDocument();
  }
  const section = screen.getByRole("heading", {name: "תוצאת בדיקת בסיסי השוואה"}).closest("section")!;
  expect(section.textContent?.match(/נדרש טיפול מקצועי/g)).toHaveLength(4);
});

test("ordinary comparison presentation oracle kills and restores ordering and visibility mapping mutation", async () => {
  const comparison = {
    schema_version: "RTICB_RESULT_V1", client_id: 7, direct_comparison_state: "NOT_READY", direct_comparison_ready: false,
    blockers: ["BLOCKER_Z", "BLOCKER_A"], source_comparisons: [
      {source_id: "income:2", comparison_state: "BASIS_UNRESOLVED", reason_codes: ["REASON_2", "REASON_1"], rtisa_admission_state: "EXCLUDED", source_income_basis: "GROSS", source_price_basis: "NOMINAL"},
      {source_id: "income:1", comparison_state: "NORMALIZATION_REQUIRED", reason_codes: ["NORMALIZE_B", "NORMALIZE_A"], rtisa_admission_state: "NOT_ADMITTED", source_income_basis: "NET", source_price_basis: "REAL"},
    ],
  };

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
      expect(text.indexOf("BLOCKER_Z")).toBeLessThan(text.indexOf("BLOCKER_A"));
      expect(text.indexOf("income:2")).toBeLessThan(text.indexOf("income:1"));
      expect(text.indexOf("REASON_2")).toBeLessThan(text.indexOf("REASON_1"));
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
    if (values[0] === "BLOCKER_Z" || values[0] === "REASON_2") {
      mutationReached = true;
      return originalMap.call([...values].reverse(), callback as never, thisArg) as never;
    }
    if ((values[0] as {source_id?: string} | undefined)?.source_id === "income:2") {
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
