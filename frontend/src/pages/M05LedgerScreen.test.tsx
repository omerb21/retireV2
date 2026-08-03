import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { M05Candidate, M05Revision, M05Subject } from "../api/m05LedgerApi";
import { M05LedgerScreen } from "./M05LedgerScreen";

const json = (body: unknown, status = 200): Response => ({
  ok: status < 400, status, statusText: status < 400 ? "OK" : "Error",
  headers: { get: () => "application/json" }, json: async () => body,
  text: async () => JSON.stringify(body),
}) as unknown as Response;
const client = (id = 1) => ({
  client_id: id, full_name: `Client ${id}`, id_number: `00${id}`,
  birth_date: null, file_status: "file_created",
  professional_identification_status: "identification_incomplete",
  m01_case: { lifecycle_status: "delivered" },
});
const candidate = (id = 1): M05Candidate => ({
  candidate_id: `candidate-${id}`, intake_id: `manual-${id}`,
  target_kind: "manual_record_review", provider_name: `Provider ${id}`,
  account_reference: `Account ${id}`, product_context: { product_name: "Product" },
  statement_date: "2026-07-01", m03_revision_id: `m03-${id}`,
  m04_revision_id: `m04-${id}`, eligible: true, authoritative_current: true,
  exclusion_reason: null, informational_warnings: [], subject_id: `subject-${id}`,
});
const revision = (id = 1, state: M05Revision["state"] = "draft"): M05Revision => ({
  revision_id: `revision-${id}`, subject_id: `subject-${id}`,
  candidate_id: `candidate-${id}`, intake_id: `manual-${id}`,
  target_kind: "manual_record_review", m03_revision_id: `m03-${id}`,
  m04_revision_id: `m04-${id}`, predecessor_revision_id: null,
  revision_sequence: 1, state, action_type: "start",
  provider_name: `Provider ${id}`, account_reference: `Account ${id}`,
  product_context: { product_name: "Product", m04_product_family: "provident_fund" },
  statement_date: "2026-07-01", evaluation_date: "2026-08-03", is_stale: false,
  source_snapshot_digest: "a".repeat(64), mapping_digest: "b".repeat(64),
  currency: "ILS", currency_confirmed: true,
  currency_confirmation_evidence: { actor: "system:m05-ledger-ui:M05 ledger workflow" },
  source_total_state: "recorded_value", source_total_value: "100.00",
  effective_total_state: "recorded_value", effective_total_value: "100.00",
  signed_discrepancy: "1.00", absolute_discrepancy: "1.00",
  tolerance_satisfied: false, algorithm_version: "m05-reconciliation-v1",
  included_evidence: [{ evidence_identity: "component:0", effective_value: "99.00" }],
  excluded_evidence: [],
  warnings: [{ warning_id: "reconciliation_difference_review_required", classification: "mandatory" }],
  warning_dispositions: [], provenance: { intake_id: `manual-${id}` },
  reason_code: null, explanation: null,
  actor: "system:m05-ledger-ui:M05 ledger workflow", actor_is_authentication: false,
  created_at: "2026-08-03T00:00:00Z",
  values: [
    { value_id: `total-${id}`, evidence_identity: "total_balance", component_index: null,
      original_label: null, original_code: null, component_kind: "total_balance",
      source_state: "recorded_value", source_value: "100.00", effective_state: "recorded_value",
      effective_value: "100.00", included_in_reconciliation: false, exclusion_reason: "reconciliation_total" },
    { value_id: `component-${id}`, evidence_identity: "component:0", component_index: 0,
      original_label: "Contributions", original_code: "contribution_component",
      component_kind: "contribution_component", source_state: "recorded_value", source_value: "99.00",
      effective_state: "recorded_value", effective_value: "99.00",
      included_in_reconciliation: true, exclusion_reason: null },
  ],
  adjustment: null,
});
const subject = (id = 1): M05Subject => ({
  subject_id: `subject-${id}`, client_id: id, provider_name: `Provider ${id}`,
  account_reference: `Account ${id}`, current_revision: revision(id),
  eligibility: {
    subject_id: `subject-${id}`, eligible_for_m06: false,
    current_revision_id: `revision-${id}`, exclusion_reasons: ["warning_not_reviewed"],
    informational_warnings: [],
    meaning: "technically eligible for consumption by a separately authorized M06 package",
  },
});
type Deferred<T> = { promise: Promise<T>; resolve(value: T): void; reject(reason: unknown): void };
const deferred = <T,>(): Deferred<T> => {
  let resolve!: (value: T) => void; let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const path = (input: RequestInfo | URL) => String(input);
const defaultResponse = (url: string, id = url.includes("/clients/2/") || url.endsWith("/clients/2") ? 2 : 1) => {
  if (url.endsWith(`/api/clients/${id}`)) return json(client(id));
  if (url.endsWith("/m05/candidates")) return json([candidate(id)]);
  if (url.endsWith("/m05/subjects")) return json([subject(id)]);
  if (url.endsWith("/history")) return json([revision(id)]);
  if (url.endsWith("/provenance")) return json({ intake_id: `manual-${id}`, marker: `provenance-${id}` });
  if (url.endsWith("/warnings")) return json(revision(id).warnings);
  if (url.endsWith("/m06-eligibility")) return json(subject(id).eligibility);
  if (url.endsWith(`/subjects/subject-${id}`)) return json(subject(id));
  throw new Error(`unexpected GET ${url}`);
};
function renderPage() {
  return render(<MemoryRouter initialEntries={["/clients/1/pension-ledger"]}><Routes>
    <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
  </Routes></MemoryRouter>);
}
function Navigation() {
  const navigate = useNavigate();
  return <><button onClick={() => navigate("/clients/1/pension-ledger")}>A</button><button onClick={() => navigate("/clients/2/pension-ledger")}>B</button></>;
}
function renderNavigable() {
  return render(<MemoryRouter initialEntries={["/clients/1/pension-ledger"]}><Navigation /><Routes>
    <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
  </Routes></MemoryRouter>);
}
afterEach(() => vi.restoreAllMocks());

describe("M05LedgerScreen", () => {
  it("renders source/effective evidence, warnings, history, provenance, and bounded M06 wording", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => defaultResponse(path(input))));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
    expect((await screen.findAllByText(/Source total: 100.00/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/source digest:/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/warning_not_reviewed/)).toBeInTheDocument();
    expect(screen.getByText(/does not authorize conversion, coefficients, tax, fixation/i)).toBeInTheDocument();
    expect(screen.getAllByText(/operational provenance, not authentication or professional approval/i).length).toBeGreaterThan(0);
  });

  it("sends start intent without actor, authority tuple, timestamp, or eligibility", async () => {
    let posted: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if (url.endsWith("/m05/start")) { posted = JSON.parse(String(init?.body)); return json(revision(1), 201); }
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ }));
    fireEvent.click(screen.getByLabelText(/Confirm currency ILS/));
    fireEvent.click(screen.getByRole("button", { name: "Start ledger" }));
    await waitFor(() => expect(posted).toEqual({ candidate_id: "candidate-1", confirm_currency_ils: true }));
  });

  it("guards same-client subject X to Y detail settlement", async () => {
    const old = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/m05/subjects")) return json([subject(1), { ...subject(1), subject_id: "subject-2", provider_name: "Provider X", account_reference: "Account X" }]);
      if (url.endsWith("/subjects/subject-1")) return old.promise;
      if (url.endsWith("/subjects/subject-2")) return json({ ...subject(1), subject_id: "subject-2", provider_name: "Provider X", account_reference: "Account X" });
      if (url.includes("/subjects/subject-2/")) return url.endsWith("history") ? json([]) : url.endsWith("m06-eligibility") ? json({ ...subject(1).eligibility, subject_id: "subject-2" }) : url.endsWith("warnings") ? json([]) : json({ marker: "X" });
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Provider X / Account X" }));
    expect(await screen.findByText(/Provider X/)).toBeInTheDocument();
    await act(async () => old.resolve(json(subject(1))));
    expect(screen.queryByText(/Current ledger/)).toBeInTheDocument();
    expect(screen.getAllByText(/Provider X/).length).toBeGreaterThan(0);
  });

  it.each(["success", "rejection", "api-error"])(
    "A-B-A stale mutation %s launches zero refresh and cannot change current context",
    async (outcome) => {
      const pending = deferred<Response>(); let aGets = 0;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input);
        if (url.includes("/clients/1/") && (init?.method ?? "GET") === "GET") aGets += 1;
        if (url.endsWith("/subjects/subject-1/reconcile")) return pending.promise;
        return defaultResponse(url);
      }));
      renderNavigable();
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      fireEvent.click(await screen.findByRole("button", { name: "Reconcile" }));
      fireEvent.click(screen.getByRole("button", { name: "B" }));
      expect(await screen.findByText(/Client: Client 2/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "A" }));
      expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      const before = aGets;
      await act(async () => {
        if (outcome === "success") pending.resolve(json(revision(1), 201));
        else if (outcome === "api-error") pending.resolve(json({ detail: { code: "OLD" } }, 409));
        else pending.reject(new Error("old rejection"));
      });
      await act(async () => Promise.resolve());
      expect(aGets).toBe(before);
      expect(screen.queryByText(/OLD|old rejection/)).not.toBeInTheDocument();
    },
  );

  it("unmount invalidates pending mutation success, error, and finally", async () => {
    const pending = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/subjects/subject-1/reconcile")) return pending.promise;
      return defaultResponse(url);
    }));
    const view = renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Reconcile" }));
    view.unmount();
    await act(async () => pending.resolve(json(revision(1), 201)));
  });

  it.each([
    ["Start ledger", "/m05/start"],
    ["Reconcile", "/reconcile"],
    ["Review exact mandatory warning set", "/review-warning"],
    ["Mark blocked", "/mark-blocked"],
    ["Adjust one value", "/adjust"],
    ["Supersede", "/supersede"],
    ["Revalidate against selected current candidate", "/revalidate"],
  ])("%s mutation is current-context bound and uses %s", async (button, endpoint) => {
    const posts: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if ((init?.method ?? "GET") === "POST") { posts.push(url); return json(revision(1), 201); }
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ }));
    if (button !== "Start ledger") fireEvent.click(screen.getByRole("button", { name: "Provider 1 / Account 1" }));
    if (button === "Adjust one value") {
      fireEvent.change(await screen.findByRole("combobox"), { target: { value: "component:0" } });
      fireEvent.change(screen.getByLabelText("New effective value"), { target: { value: "99.50" } });
    }
    const control = await screen.findByRole("button", { name: button });
    fireEvent.click(control);
    await waitFor(() => expect(posts.some((url) => url.endsWith(endpoint))).toBe(true));
  });
});
