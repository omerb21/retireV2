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
  return <><button onClick={() => navigate("/clients/1/pension-ledger")}>A</button><button onClick={() => navigate("/clients/2/pension-ledger")}>B</button><button onClick={() => navigate("/clients/1/pension-ledger", { state: { revisit: Math.random() } })}>A revisit</button></>;
}
function renderNavigable() {
  return render(<MemoryRouter initialEntries={["/clients/1/pension-ledger"]}><Navigation /><Routes>
    <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
  </Routes></MemoryRouter>);
}
const mutations = [
  ["Start ledger", "/m05/start"],
  ["Reconcile", "/reconcile"],
  ["Review exact mandatory warning set", "/review-warning"],
  ["Mark blocked", "/mark-blocked"],
  ["Adjust one value", "/adjust"],
  ["Supersede", "/supersede"],
  ["Revalidate against selected current candidate", "/revalidate"],
] as const;
const settlements = ["success", "rejection", "api-error"] as const;
type Settlement = typeof settlements[number];
const detailUnits = ["detail", "history", "provenance", "warnings", "eligibility"] as const;
type DetailUnit = typeof detailUnits[number];
const transitions = ["direct A-B", "A-B-A", "same-context revisit"] as const;
const matchesDetailUnit = (unit: DetailUnit, url: string, subjectId = "subject-1") =>
  unit === "detail" ? url.endsWith(`/subjects/${subjectId}`)
    : unit === "history" ? url.endsWith(`/subjects/${subjectId}/history`)
    : unit === "provenance" ? url.endsWith(`/subjects/${subjectId}/provenance`)
    : unit === "warnings" ? url.endsWith(`/subjects/${subjectId}/warnings`)
    : url.endsWith(`/subjects/${subjectId}/m06-eligibility`);
const staleReadResponse = (unit: DetailUnit) => unit === "detail"
  ? json({ ...subject(1), provider_name: "STALE_EVIDENCE" })
  : unit === "history"
    ? json([{ ...revision(1), product_context: { product_name: "STALE_EVIDENCE" } }])
    : unit === "provenance"
      ? json({ marker: "STALE_EVIDENCE" })
      : unit === "warnings"
        ? json([{ warning_id: "STALE_EVIDENCE", classification: "informational" }])
        : json({ ...subject(1).eligibility, exclusion_reasons: ["STALE_EVIDENCE"] });
const settle = async (pending: Deferred<Response>, outcome: Settlement, response = json({ marker: "STALE_EVIDENCE" })) => {
  await act(async () => {
    if (outcome === "success") pending.resolve(response);
    else if (outcome === "api-error") pending.resolve(json({ detail: { code: "STALE_EVIDENCE" } }, 409));
    else pending.reject(new Error("STALE_EVIDENCE"));
  });
  await act(async () => Promise.resolve());
};
async function launchMutation(button: string, launch = true) {
  fireEvent.click(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ }));
  if (button === "Start ledger") {
    fireEvent.click(screen.getByLabelText(/Confirm currency ILS/));
  } else {
    fireEvent.click(screen.getByRole("button", { name: "Provider 1 / Account 1" }));
    await screen.findByText(/Current ledger/);
  }
  if (button === "Adjust one value") {
    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "component:0" } });
    fireEvent.change(screen.getByLabelText("New effective value"), { target: { value: "99.50" } });
  }
  const control = await screen.findByRole("button", { name: button });
  if (launch) fireEvent.click(control);
  return control;
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
    expect(screen.getByLabelText("Candidate candidate-1 product context")).toHaveTextContent("product_nameProduct");
    expect(screen.getAllByLabelText("Revision 1 product context")).toHaveLength(2);
    expect(screen.getAllByLabelText("Revision 1 product context")[0]).toHaveTextContent("m04_product_familyprovident_fund");
    expect(screen.getAllByText(/source values; no inference/i).length).toBeGreaterThan(0);
  });

  it("renders explicit unavailable product context without inventing a fallback", async () => {
    const missingCandidate = { ...candidate(1), product_context: {} };
    const missingRevision = { ...revision(1), product_context: {} };
    const missingSubject = { ...subject(1), current_revision: missingRevision };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/m05/candidates")) return json([missingCandidate]);
      if (url.endsWith("/m05/subjects")) return json([missingSubject]);
      if (url.endsWith("/subjects/subject-1")) return json(missingSubject);
      if (url.endsWith("/history")) return json([missingRevision]);
      return defaultResponse(url);
    }));
    renderPage();
    expect(await screen.findByLabelText("Candidate candidate-1 product context")).toHaveTextContent("Product context unavailable.");
    fireEvent.click(screen.getByRole("button", { name: "Provider 1 / Account 1" }));
    await waitFor(() => expect(screen.getAllByText("Product context unavailable.")).toHaveLength(3));
    expect(screen.queryByText(/unknown product|assumed product/i)).not.toBeInTheDocument();
  });

  it("disables lifecycle-invalid actions for a superseded revision", async () => {
    const terminalRevision = revision(1, "superseded");
    const terminalSubject = { ...subject(1), current_revision: terminalRevision };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/m05/subjects")) return json([terminalSubject]);
      if (url.endsWith("/subjects/subject-1")) return json(terminalSubject);
      if (url.endsWith("/history")) return json([terminalRevision]);
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
    expect(await screen.findByRole("button", { name: "Reconcile" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Review exact mandatory warning set" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Mark blocked" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Supersede" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Adjust one value" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Revalidate against selected current candidate" })).toBeDisabled();
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

  it.each(transitions.flatMap((transition) => settlements.map((outcome) => [transition, outcome] as const)))(
  "guards candidate-list stale settlement across %s: %s and finally", async (transition, outcome) => {
    const old = deferred<Response>(); let oldIssued = false;
    const staleCandidate = { ...candidate(1), provider_name: "STALE_EVIDENCE" };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.includes("/clients/1/") && url.endsWith("/m05/candidates") && !oldIssued) {
        oldIssued = true; return old.promise;
      }
      return defaultResponse(url);
    }));
    renderNavigable();
    if (transition === "same-context revisit") {
      fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
    } else {
      fireEvent.click(screen.getByRole("button", { name: "B" }));
      expect(await screen.findByText(/Client: Client 2/)).toBeInTheDocument();
      if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
    }
    if (transition !== "direct A-B") {
      expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      expect(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ })).toBeInTheDocument();
    }
    await settle(old, outcome, json([staleCandidate]));
    expect(screen.queryByText("STALE_EVIDENCE")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each(
    detailUnits.flatMap((unit) => transitions.flatMap(
      (transition) => settlements.map((outcome) => [unit, transition, outcome] as const),
    )),
  )(
    "guards stale %s read across %s: %s and finally",
    async (unit, transition, outcome) => {
      const old = deferred<Response>(); let delayed = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (matchesDetailUnit(unit, url) && !delayed) { delayed = true; return old.promise; }
        return defaultResponse(url);
      }));
      renderNavigable();
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      if (transition === "same-context revisit") {
        fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
      } else {
        fireEvent.click(screen.getByRole("button", { name: "B" }));
        expect(await screen.findByText(/Client: Client 2/)).toBeInTheDocument();
        if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
      }
      if (transition !== "direct A-B") expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Current ledger/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(
    detailUnits.flatMap((unit) => settlements.map((outcome) => [unit, outcome] as const)),
  )(
    "guards same-client subject X-Y stale %s read: %s and finally",
    async (unit, outcome) => {
      const old = deferred<Response>(); let delayed = false;
      const yRevision = { ...revision(2), subject_id: "subject-2", provider_name: "Provider Y", account_reference: "Account Y" };
      const ySubject = { ...subject(1), subject_id: "subject-2", provider_name: "Provider Y", account_reference: "Account Y", current_revision: yRevision };
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (url.endsWith("/m05/subjects")) return json([subject(1), ySubject]);
        if (matchesDetailUnit(unit, url) && !delayed) { delayed = true; return old.promise; }
        if (url.endsWith("/subjects/subject-2")) return json(ySubject);
        if (url.endsWith("/subjects/subject-2/history")) return json([yRevision]);
        if (url.endsWith("/subjects/subject-2/provenance")) return json({ marker: "CURRENT_Y" });
        if (url.endsWith("/subjects/subject-2/warnings")) return json([]);
        if (url.endsWith("/subjects/subject-2/m06-eligibility")) return json({ ...ySubject.eligibility, subject_id: "subject-2" });
        return defaultResponse(url);
      }));
      renderPage();
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      fireEvent.click(screen.getByRole("button", { name: "Provider Y / Account Y" }));
      expect(await screen.findByText(/Current ledger/)).toBeInTheDocument();
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.getAllByText(/Provider Y/).length).toBeGreaterThan(0);
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(
    detailUnits.flatMap(
      (unit) => settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "guards stale %s read %s after A-B-A including finally ownership (legacy explicit proof)",
    async (unit: DetailUnit, outcome: Settlement) => {
      const old = deferred<Response>(); let delayed = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        const matches = matchesDetailUnit(unit, url);
        if (matches && !delayed) { delayed = true; return old.promise; }
        return defaultResponse(url);
      }));
      renderNavigable();
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      fireEvent.click(screen.getByRole("button", { name: "B" }));
      expect(await screen.findByText(/Client: Client 2/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "A" }));
      expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Current ledger/)).not.toBeInTheDocument();
    },
  );

  it.each(mutations)("current %s launches every independently guarded refresh unit", async (button, endpoint) => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input); calls.push(`${init?.method ?? "GET"} ${url}`);
      if ((init?.method ?? "GET") === "POST" && url.endsWith(endpoint)) return json(revision(1, "reconciled"), 201);
      return defaultResponse(url);
    }));
    renderPage();
    const control = await launchMutation(button, false);
    calls.length = 0;
    fireEvent.click(control);
    await waitFor(() => expect(calls.some((call) => call.startsWith("POST ") && call.endsWith(endpoint))).toBe(true));
    for (const suffix of [
      "/api/clients/1", "/m05/candidates", "/m05/subjects",
      "/subjects/subject-1", "/history", "/provenance", "/warnings", "/m06-eligibility",
    ]) {
      await waitFor(() => expect(calls.some((call) => call.startsWith("GET ") && call.endsWith(suffix))).toBe(true));
    }
  });

  it.each(
    mutations.flatMap(([button, endpoint]) => transitions.flatMap((transition) =>
      settlements.map((outcome) => [button, endpoint, transition, outcome] as const),
    )),
  )(
    "%s mutation %s across %s with stale %s launches zero refresh and cannot change current context",
    async (button, endpoint, transition, outcome) => {
      const pending = deferred<Response>(); let aGets = 0;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input);
        if (url.includes("/clients/1/") && (init?.method ?? "GET") === "GET") aGets += 1;
        if ((init?.method ?? "GET") === "POST" && url.endsWith(endpoint)) return pending.promise;
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation(button);
      if (transition === "same-context revisit") {
        fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
      } else {
        fireEvent.click(screen.getByRole("button", { name: "B" }));
        expect(await screen.findByText(/Client: Client 2/)).toBeInTheDocument();
        if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
      }
      if (transition !== "direct A-B") expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      const before = aGets;
      await settle(pending, outcome, json(revision(1), 201));
      expect(aGets).toBe(before);
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(
    mutations.slice(1).flatMap(([button, endpoint]) =>
      settlements.map((outcome) => [button, endpoint, outcome] as const),
    ),
  )("same-client X-Y invalidates pending %s mutation %s: %s and finally", async (button, endpoint, outcome) => {
    const pending = deferred<Response>(); let aGets = 0;
    const yRevision = { ...revision(2), subject_id: "subject-2", provider_name: "Provider Y", account_reference: "Account Y" };
    const ySubject = { ...subject(1), subject_id: "subject-2", provider_name: "Provider Y", account_reference: "Account Y", current_revision: yRevision };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if ((init?.method ?? "GET") === "GET") aGets += 1;
      if ((init?.method ?? "GET") === "POST" && url.endsWith(endpoint)) return pending.promise;
      if (url.endsWith("/m05/subjects")) return json([subject(1), ySubject]);
      if (url.endsWith("/subjects/subject-2")) return json(ySubject);
      if (url.endsWith("/subjects/subject-2/history")) return json([yRevision]);
      if (url.endsWith("/subjects/subject-2/provenance")) return json({ marker: "CURRENT_Y" });
      if (url.endsWith("/subjects/subject-2/warnings")) return json([]);
      if (url.endsWith("/subjects/subject-2/m06-eligibility")) return json({ ...ySubject.eligibility, subject_id: "subject-2" });
      return defaultResponse(url);
    }));
    renderPage();
    await launchMutation(button);
    fireEvent.click(screen.getByRole("button", { name: "Provider Y / Account Y" }));
    expect(await screen.findByText(/Current ledger/)).toBeInTheDocument();
    const before = aGets;
    await settle(pending, outcome, json(revision(1), 201));
    expect(aGets).toBe(before);
    expect(screen.getAllByText(/Provider Y/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each(
    mutations.flatMap(([button, endpoint]) =>
      settlements.map((outcome) => [button, endpoint, outcome] as const),
    ),
  )("unmount invalidates pending %s mutation %s, %s and finally", async (button, endpoint, outcome) => {
    const pending = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if ((init?.method ?? "GET") === "POST" && url.endsWith(endpoint)) return pending.promise;
      return defaultResponse(url);
    }));
    const view = renderPage();
    await launchMutation(button);
    view.unmount();
    await settle(pending, outcome, json(revision(1), 201));
  });

  it.each(
    (["candidates", ...detailUnits] as const).flatMap((unit) =>
      settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "unmount invalidates pending %s read %s and finally",
    async (unit, outcome) => {
      const pending = deferred<Response>(); let delayed = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        const matches = unit === "candidates" ? url.endsWith("/m05/candidates")
          : matchesDetailUnit(unit, url);
        if (matches && !delayed) { delayed = true; return pending.promise; }
        return defaultResponse(url);
      }));
      const view = renderPage();
      if (unit !== "candidates") {
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      } else {
        await waitFor(() => expect(delayed).toBe(true));
      }
      view.unmount();
      const response = unit === "candidates" ? json([candidate(1)]) : staleReadResponse(unit);
      await settle(pending, outcome, response);
    },
  );

  it.each(
    (["overview", ...detailUnits] as const).flatMap((unit) =>
      settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "independently owns delayed stale %s refresh settlement: %s and finally",
    async (unit, outcome) => {
      const pending = deferred<Response>(); let mutationCompleted = false; let delayed = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input);
        if ((init?.method ?? "GET") === "POST" && url.endsWith("/reconcile")) {
          mutationCompleted = true; return json(revision(1, "reconciled"), 201);
        }
        const matches = unit === "overview" ? url.endsWith("/m05/candidates") : matchesDetailUnit(unit, url);
        if (mutationCompleted && matches && !delayed) { delayed = true; return pending.promise; }
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation("Reconcile");
      await waitFor(() => expect(delayed).toBe(true));
      fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
      expect(await screen.findByText(/Client: Client 1/)).toBeInTheDocument();
      expect(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ })).toBeInTheDocument();
      const response = unit === "overview" ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }]) : staleReadResponse(unit);
      await settle(pending, outcome, response);
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/Loading M05 evidence/)).not.toBeInTheDocument();
    },
  );

  it("a stale refresh cannot clear a newer generation's loading owner", async () => {
    const stale = deferred<Response>(); const current = deferred<Response>(); let candidateCall = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if ((init?.method ?? "GET") === "POST" && url.endsWith("/reconcile")) return json(revision(1, "reconciled"), 201);
      if (url.endsWith("/m05/candidates")) {
        candidateCall += 1;
        if (candidateCall === 2) return stale.promise;
        if (candidateCall === 3) return current.promise;
      }
      return defaultResponse(url);
    }));
    renderNavigable();
    await launchMutation("Reconcile");
    await waitFor(() => expect(candidateCall).toBe(2));
    fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
    await waitFor(() => expect(candidateCall).toBe(3));
    await act(async () => stale.resolve(json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])));
    expect(screen.getByText(/Loading M05 evidence/)).toBeInTheDocument();
    await act(async () => current.resolve(json([candidate(1)])));
    expect(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ })).toBeInTheDocument();
    expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Loading M05 evidence/)).not.toBeInTheDocument();
  });

  it.each(mutations)("%s mutation is current-context bound and uses %s", async (button, endpoint) => {
    const posts: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input);
      if ((init?.method ?? "GET") === "POST") { posts.push(url); return json(revision(1), 201); }
      return defaultResponse(url);
    }));
    renderPage();
    await launchMutation(button);
    await waitFor(() => expect(posts.some((url) => url.endsWith(endpoint))).toBe(true));
  });
});
