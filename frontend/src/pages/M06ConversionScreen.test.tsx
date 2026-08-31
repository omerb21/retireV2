import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { M06Candidate, M06Revision, M06Subject } from "../api/m06ConversionApi";
import { M06ConversionScreen } from "./M06ConversionScreen";

const json = (body: unknown): Response => ({ ok: true, status: 200, statusText: "OK", headers: { get: () => "application/json" }, json: async () => body, text: async () => JSON.stringify(body) }) as unknown as Response;
const candidate = (id: number): M06Candidate => ({ candidate_id: `candidate-${id}`, m05_subject_id: `m05-${id}`, m05_revision_id: `m05r-${id}`, m02_intake_id: `m02-${id}`, provider_name: `Provider ${id}`, account_reference: `Account ${id}`, product_family: "pension_fund", mode: "balance_to_monthly_pension", input_identity: `component-${id}`, input_amount: "1000.00", input_date: "2026-01-31", formula_id: "m06.balance_to_monthly_pension.v1", eligible: true, exclusion_reasons: [], informational_warnings: [] });
const subject = (id: number): M06Subject => ({ subject_id: `subject-${id}`, client_id: id, m05_subject_id: `m05-${id}`, mode: "balance_to_monthly_pension", input_identity: `component-${id}`, current_revision: null, eligibility: { subject_id: `subject-${id}`, assessed_revision_id: "", eligible_for_downstream: false, current_revision_id: null, exclusion_reasons: ["conversion_draft"], informational_warnings: [], meaning: "technically eligible under the bounded PKG-011 M06 contract" } });
const revision = (overrides: Partial<M06Revision> = {}): M06Revision => ({ revision_id: "revision-1", subject_id: "subject-1", predecessor_revision_id: null, revision_sequence: 1, state: "resolved", action_type: "resolve", mode: "balance_to_monthly_pension", formula_id: "m06.balance_to_monthly_pension.v1", input_identity: "component-1", input_amount: "0.00", input_date: "2026-01-31", predecessor_snapshot: { m02_intake_id: "m02-1", m05_revision_id: "m05r-1" }, warnings: [], blocking_reasons: [], informational_warnings: ["stale_warning"], coefficient: { evidence_id: "coefficient-1", authority_class: "documentary", coefficient: "200.000", source_intake_id: "source-1", source_locator: "page 3", source_note: null, reason: "documented", effective_from: "2026-01-01", effective_to: "2026-12-31", applicability_declared: false, metadata: { pension_option: "option-a" }, actor: "system:m06-conversion-ui:M06 conversion workflow", actor_is_authentication: false, created_at: "2026-02-01T00:00:00Z" }, manifest: { manifest_id: "manifest-1", fingerprint: "f".repeat(64), raw_result_kind: "exact_ratio", raw_decimal: null, raw_numerator: "0.00", raw_denominator: "200.000", display_result: "0.00", evidence: { formula_id: "m06.balance_to_monthly_pension.v1", rounding: "ROUND_HALF_UP" } }, warning_dispositions: [], actor: "system:m06-conversion-ui:M06 conversion workflow", actor_is_authentication: false, created_at: "2026-02-01T00:00:00Z", ...overrides });
const detailedSubject = (current = revision(), id = 1): M06Subject => ({ ...subject(id), current_revision: current, eligibility: { subject_id: `subject-${id}`, assessed_revision_id: current.revision_id, eligible_for_downstream: current.state === "resolved" || current.state === "warning_reviewed", current_revision_id: current.revision_id, exclusion_reasons: current.state === "blocked" ? ["conversion_blocked"] : [], informational_warnings: current.informational_warnings, meaning: "technically eligible under the bounded PKG-011 M06 contract" } });
type Deferred<T> = { promise: Promise<T>; resolve(value: T): void; reject(reason: unknown): void };
const deferred = <T,>(): Deferred<T> => { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
function Navigation() { const navigate = useNavigate(); const location = useLocation(); return <><button onClick={() => navigate("/clients/2/pension-conversion")}>B</button><button onClick={() => navigate("/clients/1/pension-conversion", { state: { revisit: 1 } })}>A revisit</button><output aria-label="route generation">{location.key}</output></>; }
function page(navigable = false) { return render(<MemoryRouter initialEntries={["/clients/1/pension-conversion"]}>{navigable ? <Navigation /> : null}<Routes><Route path="/clients/:clientId/pension-conversion" element={<M06ConversionScreen />} /></Routes></MemoryRouter>); }

afterEach(() => vi.restoreAllMocks());
describe("PKG-011 M06 conversion screen", () => {
  it("shows bounded formula evidence and sends intent without actor, amount, result, or eligibility", async () => {
    let posted: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST") { posted = JSON.parse(String(init.body)); return json({}); }
      if (url.endsWith("/candidates")) return json([candidate(1)]);
      if (url.endsWith("/subjects")) return json([subject(1)]);
      throw new Error(url);
    }));
    page(); await screen.findByRole("button", { name: /Provider 1/ }); fireEvent.click(screen.getByRole("button", { name: /Provider 1/ }));
    fireEvent.change(screen.getByLabelText("מקדם מדויק"), { target: { value: "200.000" } });
    fireEvent.change(screen.getByLabelText("הערת מקור של המתכנן"), { target: { value: "planner evidence" } });
    fireEvent.change(screen.getByLabelText("נימוק לאסמכתת המקדם"), { target: { value: "bounded declaration" } });
    fireEvent.click(screen.getByLabelText(/הצהרה על תחולה/)); fireEvent.click(screen.getByRole("button", { name: "יצירת טיוטה בלתי ניתנת לשינוי" }));
    await waitFor(() => expect(posted).not.toBeNull());
    expect(posted).toMatchObject({ m05_subject_id: "m05-1", mode: "balance_to_monthly_pension", input_identity: "component-1", coefficient: { authority_class: "planner_declared", coefficient: "200.000", source_note: "planner evidence", applicability_declared: true } });
    expect(JSON.stringify(posted)).not.toMatch(/actor|input_amount|result|eligibility|fingerprint|timestamp/);
    expect(screen.getByText(/אינו סמכות מקצועית, פיננסית או מיסויית/)).toBeInTheDocument();
  });

  it("rejects stale A overview success and finally after A-to-B-to-A", async () => {
    const oldA = deferred<Response>(); let aCandidateCalls = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input); const id = url.includes("/clients/2/") ? 2 : 1;
      if (url.endsWith("/candidates")) {
        if (id === 1 && aCandidateCalls++ === 0) return oldA.promise;
        return Promise.resolve(json([candidate(id)]));
      }
      if (url.endsWith("/subjects")) return Promise.resolve(json([subject(id)]));
      throw new Error(url);
    }));
    page(true); fireEvent.click(screen.getByRole("button", { name: "B" })); await screen.findByText(/Provider 2/);
    const previous = screen.getByLabelText("route generation").textContent; fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
    await waitFor(() => expect(screen.getByLabelText("route generation").textContent).not.toBe(previous)); await screen.findByText(/Provider 1/);
    await act(async () => oldA.resolve(json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])));
    await waitFor(() => expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument());
    expect(screen.getByText(/Provider 1/)).toBeInTheDocument();
  });

  it("keeps newer overview loading owned when an older A request rejects after A-to-B", async () => {
    const oldA = deferred<Response>(); const currentB = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input); const id = url.includes("/clients/2/") ? 2 : 1;
      if (url.endsWith("/candidates")) return id === 1 ? oldA.promise : currentB.promise;
      if (url.endsWith("/subjects")) return Promise.resolve(json([subject(id)]));
      throw new Error(url);
    }));
    page(true); fireEvent.click(screen.getByRole("button", { name: "B" }));
    await act(async () => oldA.reject(new Error("stale overview rejection")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/טוען נתוני M06/)).toBeInTheDocument();
    await act(async () => currentB.resolve(json([candidate(2)])));
    expect(await screen.findByText(/Provider 2/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/טוען נתוני M06/)).not.toBeInTheDocument());
  });

  it("rejects stale detail and history success after A-to-B-to-A", async () => {
    const oldHistory = deferred<Response>(); let aHistoryCalls = 0;
    const currentA = revision(); const detailA = detailedSubject(currentA);
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input); const id = url.includes("/clients/2/") ? 2 : 1;
      if (url.endsWith("/candidates")) return Promise.resolve(json([candidate(id)]));
      if (url.endsWith(`/subjects/subject-${id}/history`)) {
        if (id === 1 && aHistoryCalls++ === 0) return oldHistory.promise;
        return Promise.resolve(json([currentA]));
      }
      if (url.endsWith(`/subjects/subject-${id}/eligibility`)) return Promise.resolve(json(id === 1 ? detailA.eligibility : subject(2).eligibility));
      if (url.endsWith(`/subjects/subject-${id}`)) return Promise.resolve(json(id === 1 ? detailA : subject(2)));
      if (url.endsWith("/subjects")) return Promise.resolve(json([id === 1 ? detailA : subject(2)]));
      throw new Error(url);
    }));
    page(true); fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    fireEvent.click(screen.getByRole("button", { name: "B" })); await screen.findByText(/component-2/);
    fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
    fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    expect(await screen.findByText(/גרסת ההמרה הנוכחית/)).toBeInTheDocument();
    await act(async () => oldHistory.resolve(json([revision({ revision_id: "STALE_DETAIL", revision_sequence: 99 })])));
    expect(screen.queryByText(/STALE_DETAIL/)).not.toBeInTheDocument();
    expect(screen.getByText(/revision-1/)).toBeInTheDocument();
  });

  it("keeps newer detail loading owned when an older detail rejects after A-to-B", async () => {
    const oldHistory = deferred<Response>(); const currentHistory = deferred<Response>();
    const detailA = detailedSubject(); const revisionB = revision({ revision_id: "revision-b", subject_id: "subject-2", input_identity: "component-2" }); const detailB = detailedSubject(revisionB, 2);
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input); const id = url.includes("/clients/2/") ? 2 : 1;
      if (url.endsWith("/candidates")) return Promise.resolve(json([candidate(id)]));
      if (url.endsWith(`/subjects/subject-${id}/history`)) return id === 1 ? oldHistory.promise : currentHistory.promise;
      if (url.endsWith(`/subjects/subject-${id}/eligibility`)) return Promise.resolve(json(id === 1 ? detailA.eligibility : detailB.eligibility));
      if (url.endsWith(`/subjects/subject-${id}`)) return Promise.resolve(json(id === 1 ? detailA : detailB));
      if (url.endsWith("/subjects")) return Promise.resolve(json([id === 1 ? detailA : detailB]));
      throw new Error(url);
    }));
    page(true); fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    fireEvent.click(screen.getByRole("button", { name: "B" }));
    fireEvent.click(await screen.findByRole("button", { name: /component-2/ }));
    await act(async () => oldHistory.reject(new Error("stale detail rejection")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/טוען נתוני M06/)).toBeInTheDocument();
    await act(async () => currentHistory.resolve(json([revisionB])));
    expect(await screen.findByText(/revision-b/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/טוען נתוני M06/)).not.toBeInTheDocument());
  });

  it("renders source provenance, exact zero, immutable history, and bounded eligibility", async () => {
    const current = revision(); const detail = detailedSubject(current);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/candidates")) return json([candidate(1)]);
      if (url.endsWith("/subjects/subject-1/history")) return json([current]);
      if (url.endsWith("/subjects/subject-1/eligibility")) return json(detail.eligibility);
      if (url.endsWith("/subjects/subject-1")) return json(detail);
      if (url.endsWith("/subjects")) return json([detail]);
      throw new Error(url);
    }));
    page();
    fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    expect(await screen.findByText(/ערך גולמי: 0.00\/200.000; מוצג: 0.00/)).toBeInTheDocument();
    expect(screen.getByText(/מקדם 200.000 \(אסמכתה תיעודית\)/)).toBeInTheDocument();
    expect(screen.getByText(/כשירות טכנית להמשך: כן/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "היסטוריה בלתי ניתנת לשינוי" })).toBeInTheDocument();
    expect(screen.getByText(/תיעוד תפעולי ולא אישור/)).toBeInTheDocument();
    for (const forbidden of [/recommendation/i, /tax control/i, /scenario/i, /result editor/i, /formula editor/i]) {
      expect(screen.queryByText(forbidden)).not.toBeInTheDocument();
    }
  });

  it("renders a blocked revision without a result", async () => {
    const current = revision({ state: "blocked", blocking_reasons: ["input_amount_negative"], manifest: null });
    const detail = detailedSubject(current);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/candidates")) return json([]);
      if (url.endsWith("/subjects/subject-1/history")) return json([current]);
      if (url.endsWith("/subjects/subject-1/eligibility")) return json(detail.eligibility);
      if (url.endsWith("/subjects/subject-1")) return json(detail);
      if (url.endsWith("/subjects")) return json([detail]);
      throw new Error(url);
    }));
    page(); fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    expect(await screen.findByText("לא קיימת תוצאת חישוב לגרסה זו.")).toBeInTheDocument();
    expect(screen.getByText(/input_amount_negative/)).toBeInTheDocument();
    expect(screen.getByText(/כשירות טכנית להמשך: לא/)).toBeInTheDocument();
  });

  it.each([
    { label: "פתרון הנוסחה המדויקת", current: revision({ state: "draft", action_type: "start", manifest: null }), suffix: "/resolve", needsReason: false },
    { label: "בדיקת קבוצת אזהרות החובה", current: revision({ state: "draft", action_type: "resolve", warnings: [{ warning_id: "planner_declared_coefficient_authority", classification: "mandatory" }] }), suffix: "/review-warning", needsReason: true },
    { label: "החלפת ההמרה הנוכחית", current: revision(), suffix: "/supersede", needsReason: true },
  ])("sends server-bound $label intent for the owned subject and revision", async ({ label, current, suffix, needsReason }) => {
    const detail = detailedSubject(current); let posted: { url: string; body: Record<string, unknown> } | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST") { posted = { url, body: JSON.parse(String(init.body)) }; return json(revision({ revision_id: "revision-2", predecessor_revision_id: current.revision_id, revision_sequence: 2 })); }
      if (url.endsWith("/candidates")) return json([candidate(1)]);
      if (url.endsWith("/subjects/subject-1/history")) return json([current]);
      if (url.endsWith("/subjects/subject-1/eligibility")) return json(detail.eligibility);
      if (url.endsWith("/subjects/subject-1")) return json(detail);
      if (url.endsWith("/subjects")) return json([detail]);
      throw new Error(url);
    }));
    page(); fireEvent.click(await screen.findByRole("button", { name: /component-1/ }));
    await screen.findByText(/גרסת ההמרה הנוכחית/);
    if (needsReason) fireEvent.change(screen.getByLabelText("נימוק לפעולה או הסבר לאזהרה"), { target: { value: "bounded action" } });
    fireEvent.click(screen.getByRole("button", { name: label }));
    await waitFor(() => expect(posted).not.toBeNull());
    expect(posted!.url).toContain(`/subjects/subject-1${suffix}`);
    expect(posted!.body).toMatchObject({ expected_current_revision_id: current.revision_id });
    expect(JSON.stringify(posted!.body)).not.toMatch(/actor|timestamp|input_amount|display_result|fingerprint|eligibility/);
  });

  it("sends a complete documentary coefficient replacement with typed dimensions", async () => {
    const current = revision(); const detail = detailedSubject(current); let posted: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST") { posted = JSON.parse(String(init.body)); return json(revision({ state: "draft", action_type: "correct_coefficient", revision_id: "revision-2", predecessor_revision_id: current.revision_id, revision_sequence: 2, manifest: null })); }
      if (url.endsWith("/candidates")) return json([candidate(1)]);
      if (url.endsWith("/subjects/subject-1/history")) return json([current]);
      if (url.endsWith("/subjects/subject-1/eligibility")) return json(detail.eligibility);
      if (url.endsWith("/subjects/subject-1")) return json(detail);
      if (url.endsWith("/subjects")) return json([detail]);
      throw new Error(url);
    }));
    page(); fireEvent.click(await screen.findByRole("button", { name: /Provider 1/ }));
    fireEvent.change(screen.getByLabelText("סוג סמכות"), { target: { value: "documentary" } });
    fireEvent.change(screen.getByLabelText("מקדם מדויק"), { target: { value: "201.2500" } });
    fireEvent.change(screen.getByLabelText("קליטת מקור מאושרת"), { target: { value: "source-1" } });
    fireEvent.change(screen.getByLabelText("מיקום מדויק במקור"), { target: { value: "page 4 table 2" } });
    fireEvent.change(screen.getByLabelText("נימוק לאסמכתת המקדם"), { target: { value: "documented coefficient" } });
    fireEvent.change(screen.getByLabelText("גיל"), { target: { value: "67" } });
    fireEvent.change(screen.getByLabelText("אפשרות קצבה"), { target: { value: "option-a" } });
    fireEvent.click(screen.getByRole("button", { name: /component-1/ }));
    await screen.findByText(/גרסת ההמרה הנוכחית/);
    fireEvent.change(screen.getByLabelText("נימוק לפעולה או הסבר לאזהרה"), { target: { value: "new evidence" } });
    fireEvent.click(screen.getByRole("button", { name: "הוספת טיוטת מקדם מתוקנת" }));
    await waitFor(() => expect(posted).not.toBeNull());
    expect(posted).toMatchObject({ expected_current_revision_id: "revision-1", correction_reason: "new evidence", coefficient: { authority_class: "documentary", coefficient: "201.2500", source_intake_id: "source-1", source_locator: "page 4 table 2", metadata: { age: 67, pension_option: "option-a" } } });
  });

  it.each(["resolve", "reject"])("isolates an old A mutation %s after A-to-B-to-A while a new A successor refresh remains owned", async (settlement) => {
    const oldMutation = deferred<Response>(); const successorHistory = deferred<Response>(); let postCalls = 0; let successorIssued = false;
    const successor = revision({ revision_id: "revision-2", predecessor_revision_id: null, revision_sequence: 1 }); const successorDetail = detailedSubject(successor);
    const requested: string[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); requested.push(url); const id = url.includes("/clients/2/") ? 2 : 1;
      if (init?.method === "POST") {
        postCalls++;
        if (postCalls === 1) return oldMutation.promise;
        successorIssued = true; return Promise.resolve(json(successor));
      }
      if (url.endsWith("/candidates")) return Promise.resolve(json([candidate(id)]));
      if (url.endsWith("/subjects/subject-1/history")) return successorHistory.promise;
      if (url.endsWith("/subjects/subject-1/eligibility")) return Promise.resolve(json(successorDetail.eligibility));
      if (url.endsWith("/subjects/subject-1")) return Promise.resolve(json(successorDetail));
      if (url.endsWith("/subjects")) return Promise.resolve(json(successorIssued && id === 1 ? [successorDetail] : [subject(id)]));
      throw new Error(url);
    }));
    page(true);
    const start = async () => {
      fireEvent.click(await screen.findByRole("button", { name: /Provider 1/ }));
      fireEvent.change(screen.getByLabelText("מקדם מדויק"), { target: { value: "200" } });
      fireEvent.change(screen.getByLabelText("הערת מקור של המתכנן"), { target: { value: "note" } });
      fireEvent.change(screen.getByLabelText("נימוק לאסמכתת המקדם"), { target: { value: "reason" } });
      fireEvent.click(screen.getByLabelText(/הצהרה על תחולה/));
      fireEvent.click(screen.getByRole("button", { name: "יצירת טיוטה בלתי ניתנת לשינוי" }));
    };
    await start(); fireEvent.click(screen.getByRole("button", { name: "B" })); await screen.findByText(/Provider 2/);
    fireEvent.click(screen.getByRole("button", { name: "A revisit" })); await screen.findByText(/Provider 1/); await start();
    await waitFor(() => expect(requested.some((url) => url.endsWith("/subjects/subject-1/history"))).toBe(true));
    if (settlement === "resolve") await act(async () => oldMutation.resolve(json(revision({ revision_id: "STALE_MUTATION" }))));
    else await act(async () => oldMutation.reject(new Error("stale mutation rejection")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/STALE_MUTATION/)).not.toBeInTheDocument();
    expect(screen.getByText(/טוען נתוני M06/)).toBeInTheDocument();
    await act(async () => successorHistory.resolve(json([successor])));
    expect(await screen.findByText(/גרסה 1: נפתר/)).toBeInTheDocument();
    expect(screen.getByText(/revision-2/)).toBeInTheDocument();
    expect(requested.filter((url) => url.endsWith("/subjects/subject-1")).length).toBeGreaterThan(0);
    expect(requested.filter((url) => url.endsWith("/subjects/subject-1/history")).length).toBeGreaterThan(0);
    expect(requested.filter((url) => url.endsWith("/subjects/subject-1/eligibility")).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.queryByText(/טוען נתוני M06/)).not.toBeInTheDocument());
  });

  it("suppresses a stale structured mutation error and stale finally after a client change", async () => {
    const pending = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const id = url.includes("/clients/2/") ? 2 : 1;
      if (init?.method === "POST") return pending.promise;
      if (url.endsWith("/candidates")) return Promise.resolve(json([candidate(id)]));
      if (url.endsWith("/subjects")) return Promise.resolve(json([subject(id)]));
      throw new Error(url);
    }));
    page(true); fireEvent.click(await screen.findByRole("button", { name: /Provider 1/ }));
    fireEvent.change(screen.getByLabelText("מקדם מדויק"), { target: { value: "200" } });
    fireEvent.change(screen.getByLabelText("הערת מקור של המתכנן"), { target: { value: "note" } });
    fireEvent.change(screen.getByLabelText("נימוק לאסמכתת המקדם"), { target: { value: "reason" } });
    fireEvent.click(screen.getByLabelText(/הצהרה על תחולה/));
    fireEvent.click(screen.getByRole("button", { name: "יצירת טיוטה בלתי ניתנת לשינוי" }));
    fireEvent.click(screen.getByRole("button", { name: "B" }));
    await screen.findByText(/Provider 2/);
    await act(async () => pending.resolve(({ ok: false, status: 409, statusText: "Conflict", headers: { get: () => "application/json" }, json: async () => ({ detail: { code: "STALE_ERROR", message: "must not surface" } }) }) as unknown as Response));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(screen.getByText(/Provider 2/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Provider 2/ })).not.toBeDisabled();
  });
});
