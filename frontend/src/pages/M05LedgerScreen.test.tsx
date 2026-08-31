import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { M05Candidate, M05Revision, M05Subject } from "../api/m05LedgerApi";
import { M05LedgerScreen } from "./M05LedgerScreen";

const json = (body: unknown, status = 200, statusText = status < 400 ? "OK" : "Error"): Response => ({
  ok: status < 400, status, statusText,
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
function renderPage(locationKey = "default") {
  return render(<MemoryRouter initialEntries={[{ pathname: "/clients/1/pension-ledger", key: locationKey }]}><LocationProbe /><Routes>
    <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
  </Routes></MemoryRouter>);
}
function LocationProbe() {
  return <output aria-label="route generation">{useLocation().key}</output>;
}
function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  return <><button onClick={() => navigate("/clients/1/pension-ledger")}>A</button><button onClick={() => navigate("/clients/2/pension-ledger")}>B</button><button onClick={() => navigate("/clients/1/pension-ledger", { state: { revisit: Math.random() } })}>A revisit</button><output aria-label="route generation">{location.key}</output></>;
}
function renderNavigable() {
  return render(<MemoryRouter initialEntries={["/clients/1/pension-ledger"]}><Navigation /><Routes>
    <Route path="/clients/:clientId/pension-ledger" element={<M05LedgerScreen />} />
  </Routes></MemoryRouter>);
}
async function revisitRoute() {
  const previous = screen.getByLabelText("route generation").textContent;
  fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
  await waitFor(() => expect(screen.getByLabelText("route generation").textContent).not.toBe(previous));
}
const mutations = [
  ["התחלת כרטסת", "/m05/start"],
  ["התאמת יתרות", "/reconcile"],
  ["בדיקת קבוצת אזהרות החובה", "/review-warning"],
  ["סימון כחסום", "/mark-blocked"],
  ["תיקון ערך יחיד", "/adjust"],
  ["החלפת הגרסה הנוכחית", "/supersede"],
  ["אימות מחדש מול הרשומה העדכנית שנבחרה", "/revalidate"],
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
const ownedReadResponse = (unit: DetailUnit, marker = "ACTIVE_NEW_OWNER") => unit === "detail"
  ? json({
      ...subject(1), provider_name: marker,
      current_revision: {
        ...revision(1),
        provider_name: marker,
        product_context: { ...revision(1).product_context, active_owner_marker: marker },
      },
    })
  : unit === "history"
    ? json([{ ...revision(1), product_context: { product_name: marker } }])
    : unit === "provenance"
      ? json({ marker })
      : unit === "warnings"
        ? json([{ warning_id: marker, classification: "informational" }])
        : json({ ...subject(1).eligibility, exclusion_reasons: [marker] });
const settle = async (pending: Deferred<Response>, outcome: Settlement, response = json({ marker: "STALE_EVIDENCE" })) => {
  await act(async () => {
    if (outcome === "success") pending.resolve(response);
    else if (outcome === "api-error") pending.resolve(json({ detail: { code: "STALE_EVIDENCE" } }, 409, "STALE_EVIDENCE"));
    else pending.reject(new Error("STALE_EVIDENCE"));
  });
  await act(async () => Promise.resolve());
};
async function launchMutation(button: string, launch = true) {
  fireEvent.click(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ }));
  if (button === "התחלת כרטסת") {
    fireEvent.click(screen.getByLabelText(/אישור מטבע ש״ח/));
  } else {
    fireEvent.click(screen.getByRole("button", { name: "Provider 1 / Account 1" }));
    await screen.findByText(/כרטסת נוכחית/);
  }
  if (button === "תיקון ערך יחיד") {
    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "component:0" } });
    fireEvent.change(screen.getByLabelText("ערך אפקטיבי חדש"), { target: { value: "99.50" } });
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
    expect((await screen.findAllByText(/סך מקור: 100.00/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/תקציר מקור:/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/warning_not_reviewed/)).toBeInTheDocument();
    expect(screen.getByText(/אינה מאשרת המרה, מקדמים, מס, קיבוע זכויות/i)).toBeInTheDocument();
    expect(screen.getAllByText(/תיעוד תפעולי ולא אישור מקצועי/i).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("הקשר המוצר של רשומה candidate-1")).toHaveTextContent("product_nameProduct");
    expect(screen.getAllByLabelText("הקשר המוצר של גרסה 1")).toHaveLength(2);
    expect(screen.getAllByLabelText("הקשר המוצר של גרסה 1")[0]).toHaveTextContent("m04_product_familyprovident_fund");
    expect(screen.getAllByText(/ערכי מקור, ללא הסקה/i).length).toBeGreaterThan(0);
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
    expect(await screen.findByLabelText("הקשר המוצר של רשומה candidate-1")).toHaveTextContent("הקשר המוצר אינו זמין.");
    fireEvent.click(screen.getByRole("button", { name: "Provider 1 / Account 1" }));
    await waitFor(() => expect(screen.getAllByText("הקשר המוצר אינו זמין.")).toHaveLength(3));
    expect(screen.queryByText(/unknown product|assumed product/i)).not.toBeInTheDocument();
  });

  it("explains candidate exclusion in plain language with a secondary technical code", async () => {
    const excluded = {
      ...candidate(1),
      provider_name: null,
      statement_date: null,
      eligible: false,
      authoritative_current: false,
      exclusion_reason: "required_value_missing",
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/m05/candidates")) return json([excluded]);
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", {
      name: /גוף מנהל לא זמין.*תאריך דוח לא זמין/,
    }));
    const explanation = screen.getByLabelText("הסבר כשירות הרשומה שנבחרה");
    expect(explanation).toHaveTextContent(
      "חסר ערך חובה של גוף מנהל, חשבון, תאריך דוח, יתרה או רכיב.",
    );
    expect(explanation).toHaveTextContent(
      "קוד טכני: required_value_missing",
    );
    expect(explanation).toHaveTextContent("גוף מנהל: לא נמסר");
    expect(explanation).toHaveTextContent("תאריך דוח: לא נמסר");
  });

  it("shows structured API conflict detail instead of a raw HTTP status", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = path(input);
      if (url.endsWith("/m05/start")) {
        return json({
          detail: {
            code: "required_value_missing",
            message: "Statement date is required",
          },
        }, 409, "Conflict");
      }
      return defaultResponse(url);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", {
      name: /Provider 1 \/ Account 1 \/ 2026/,
    }));
    fireEvent.click(screen.getByLabelText(/אישור מטבע ש״ח/));
    fireEvent.click(screen.getByRole("button", { name: "התחלת כרטסת" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Statement date is required");
    expect(alert).toHaveTextContent("קוד טכני: required_value_missing");
    expect(alert).not.toHaveTextContent("HTTP 409 Conflict");
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
    expect(await screen.findByRole("button", { name: "התאמת יתרות" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "בדיקת קבוצת אזהרות החובה" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "סימון כחסום" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "החלפת הגרסה הנוכחית" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "תיקון ערך יחיד" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "אימות מחדש מול הרשומה העדכנית שנבחרה" })).toBeDisabled();
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
    fireEvent.click(screen.getByLabelText(/אישור מטבע ש״ח/));
    fireEvent.click(screen.getByRole("button", { name: "התחלת כרטסת" }));
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
    expect(screen.queryByText(/כרטסת נוכחית/)).toBeInTheDocument();
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
      expect(await screen.findByText(/לקוח: Client 2/)).toBeInTheDocument();
      if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
    }
    if (transition !== "direct A-B") {
      expect(await screen.findByText(/לקוח: Client 1/)).toBeInTheDocument();
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
        expect(await screen.findByText(/לקוח: Client 2/)).toBeInTheDocument();
        if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
      }
      if (transition !== "direct A-B") expect(await screen.findByText(/לקוח: Client 1/)).toBeInTheDocument();
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/כרטסת נוכחית/)).not.toBeInTheDocument();
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
      expect(await screen.findByText(/כרטסת נוכחית/)).toBeInTheDocument();
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
      expect(await screen.findByText(/לקוח: Client 2/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "A" }));
      expect(await screen.findByText(/לקוח: Client 1/)).toBeInTheDocument();
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/כרטסת נוכחית/)).not.toBeInTheDocument();
    },
  );

  it.each(settlements)(
    "keeps newer overview owner pending while stale candidate %s and finally settle",
    async (outcome) => {
      const old = deferred<Response>(); const current = deferred<Response>(); let calls = 0;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) {
          calls += 1;
          if (calls === 1) return old.promise;
          if (calls === 2) return current.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      await waitFor(() => expect(calls).toBe(1));
      await revisitRoute();
      await waitFor(() => expect(calls).toBe(2));
      await settle(old, outcome, json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }]));
      expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      await act(async () => current.resolve(json([{ ...candidate(1), provider_name: "ACTIVE_NEW_OWNER" }])));
      expect(await screen.findByRole("button", { name: /ACTIVE_NEW_OWNER/ })).toBeInTheDocument();
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
    },
  );

  it.each(
    detailUnits.flatMap((unit) => settlements.map((outcome) => [unit, outcome] as const)),
  )(
    "keeps newer %s read owner pending while stale %s and finally settle",
    async (unit, outcome) => {
      const old = deferred<Response>(); const current = deferred<Response>(); let calls = 0; let overviews = 0; let currentGeneration = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) overviews += 1;
        if (matchesDetailUnit(unit, url)) {
          calls += 1;
          return currentGeneration ? current.promise : old.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      await waitFor(() => expect(calls).toBe(1));
      currentGeneration = true;
      await revisitRoute();
      await waitFor(() => expect(overviews).toBe(2));
      fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      await waitFor(() => expect(calls).toBe(2));
      await settle(old, outcome, staleReadResponse(unit));
      expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      await act(async () => current.resolve(ownedReadResponse(unit)));
      expect((await screen.findAllByText(/ACTIVE_NEW_OWNER/)).length).toBeGreaterThan(0);
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(
    (["overview", ...detailUnits] as const).flatMap((unit) =>
      settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "keeps current %s pending through stale %s/finally, then owns its structured error",
    async (unit, outcome) => {
      const old = deferred<Response>(); const current = deferred<Response>();
      let calls = 0; let overviews = 0; let currentGeneration = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) overviews += 1;
        const matches = unit === "overview"
          ? url.endsWith("/m05/candidates") : matchesDetailUnit(unit, url);
        if (matches) {
          calls += 1;
          return currentGeneration ? current.promise : old.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      if (unit !== "overview") {
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      } else await waitFor(() => expect(calls).toBe(1));
      currentGeneration = true;
      await revisitRoute();
      if (unit !== "overview") {
        await waitFor(() => expect(overviews).toBe(2));
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      }
      await waitFor(() => expect(calls).toBe(2));
      const staleResponse = unit === "overview"
        ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])
        : staleReadResponse(unit);
      await settle(old, outcome, staleResponse);
      expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      await act(async () => current.resolve(
        json({ detail: { code: "ACTIVE_NEW_ERROR" } }, 409, "ACTIVE_NEW_ERROR"),
      ));
      expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_NEW_ERROR");
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
    },
  );

  it.each(
    (["overview", ...detailUnits] as const).flatMap((unit) =>
      settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "preserves newer %s structured error after an older %s and finally settle",
    async (unit, outcome) => {
      const old = deferred<Response>(); let calls = 0; let overviews = 0; let currentGeneration = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) overviews += 1;
        const matches = unit === "overview" ? url.endsWith("/m05/candidates") : matchesDetailUnit(unit, url);
        if (matches) {
          calls += 1;
          if (!currentGeneration) return old.promise;
          return json({ detail: { code: "ACTIVE_NEW_ERROR" } }, 409, "ACTIVE_NEW_ERROR");
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      if (unit !== "overview") {
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      } else await waitFor(() => expect(calls).toBe(1));
      currentGeneration = true;
      await revisitRoute();
      if (unit !== "overview") {
        await waitFor(() => expect(overviews).toBe(2));
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      }
      expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_NEW_ERROR");
      const response = unit === "overview"
        ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])
        : staleReadResponse(unit);
      await settle(old, outcome, response);
      expect(screen.getByRole("alert")).toHaveTextContent("ACTIVE_NEW_ERROR");
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
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
        expect(await screen.findByText(/לקוח: Client 2/)).toBeInTheDocument();
        if (transition === "A-B-A") fireEvent.click(screen.getByRole("button", { name: "A" }));
      }
      if (transition !== "direct A-B") expect(await screen.findByText(/לקוח: Client 1/)).toBeInTheDocument();
      const before = aGets;
      await settle(pending, outcome, json(revision(1), 201));
      expect(aGets).toBe(before);
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(
    mutations.flatMap(([button, endpoint]) =>
      settlements.map((outcome) => [button, endpoint, outcome] as const),
    ),
  )(
    "keeps newer %s mutation owner pending while stale %s settles on %s",
    async (button, endpoint, outcome) => {
      const old = deferred<Response>(); const current = deferred<Response>();
      let posts = 0; let gets = 0;
      const calls: string[] = [];
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input); const method = init?.method ?? "GET";
        calls.push(`${method} ${url}`);
        if (method === "GET") gets += 1;
        if (method === "POST" && url.endsWith(endpoint)) {
          posts += 1;
          return posts === 1 ? old.promise : current.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation(button);
      await revisitRoute();
      await launchMutation(button);
      expect(posts).toBe(2);
      const currentControl = screen.getByRole("button", { name: button });
      expect(currentControl).toBeDisabled();
      const beforeStale = gets;
      await settle(old, outcome, json(revision(1), 201));
      expect(gets).toBe(beforeStale);
      expect(currentControl).toBeDisabled();
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      calls.length = 0;
      await act(async () => current.resolve(json(revision(1, "reconciled"), 201)));
      for (const suffix of [
        "/api/clients/1", "/m05/candidates", "/m05/subjects",
        "/subjects/subject-1", "/history", "/provenance", "/warnings", "/m06-eligibility",
      ]) {
        await waitFor(() => expect(calls.some((call) => call.startsWith("GET ") && call.endsWith(suffix))).toBe(true));
      }
      await waitFor(() => expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument());
    },
  );

  it.each(
    mutations.flatMap(([button, endpoint]) =>
      settlements.map((outcome) => [button, outcome, endpoint] as const),
    ),
  )(
    "preserves newer %s mutation structured error when older %s/finally settles on %s",
    async (button, outcome, endpoint) => {
      const old = deferred<Response>(); const current = deferred<Response>();
      let posts = 0; let gets = 0;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input); const method = init?.method ?? "GET";
        if (method === "GET") gets += 1;
        if (method === "POST" && url.endsWith(endpoint)) {
          posts += 1;
          return posts === 1 ? old.promise : current.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation(button);
      await revisitRoute();
      await launchMutation(button);
      await act(async () => current.resolve(
        json({ detail: { code: "ACTIVE_NEW_ERROR" } }, 409, "ACTIVE_NEW_ERROR"),
      ));
      expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_NEW_ERROR");
      const beforeStale = gets;
      await settle(old, outcome, json(revision(1), 201));
      expect(gets).toBe(beforeStale);
      expect(screen.getByRole("alert")).toHaveTextContent("ACTIVE_NEW_ERROR");
      expect(screen.getByRole("button", { name: button })).not.toBeDisabled();
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
    expect(await screen.findByText(/כרטסת נוכחית/)).toBeInTheDocument();
    const before = aGets;
    await settle(pending, outcome, json(revision(1), 201));
    expect(aGets).toBe(before);
    expect(screen.getAllByText(/Provider Y/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each(
    mutations.flatMap(([button, endpoint]) =>
      settlements.flatMap((outcome) =>
        (["success", "api-error"] as const).map((currentOutcome) =>
          [button, endpoint, outcome, currentOutcome] as const,
        ),
      ),
    ),
  )("active remount owns pending %s mutation %s after old %s/finally; current %s", async (button, endpoint, outcome, currentOutcome) => {
    const old = deferred<Response>(); const current = deferred<Response>();
    let posts = 0; let gets = 0; const calls: string[] = [];
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = path(input); const method = init?.method ?? "GET";
      calls.push(`${method} ${url}`);
      if (method === "GET") gets += 1;
      if (method === "POST" && url.endsWith(endpoint)) {
        posts += 1;
        return posts === 1 ? old.promise : current.promise;
      }
      return defaultResponse(url);
    }));
    const view = renderPage("old-mount");
    await launchMutation(button);
    view.unmount();
    const remounted = renderPage("new-mount");
    await launchMutation(button);
    expect(posts).toBe(2);
    const currentControl = screen.getByRole("button", { name: button });
    expect(currentControl).toBeDisabled();
    const beforeStale = gets;
    await settle(old, outcome, json(revision(1), 201));
    expect(gets).toBe(beforeStale);
    expect(currentControl).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
    expect(consoleError).not.toHaveBeenCalled();
    calls.length = 0;
    if (currentOutcome === "success") {
      await act(async () => current.resolve(json(revision(1, "reconciled"), 201)));
      for (const suffix of [
        "/api/clients/1", "/m05/candidates", "/m05/subjects",
        "/subjects/subject-1", "/history", "/provenance", "/warnings", "/m06-eligibility",
      ]) {
        await waitFor(() => expect(
          calls.some((call) => call.startsWith("GET ") && call.endsWith(suffix)),
        ).toBe(true));
      }
      await waitFor(() => expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument());
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    } else {
      const beforeCurrent = gets;
      await act(async () => current.resolve(
        json({ detail: { code: "ACTIVE_REMOUNT_ERROR" } }, 409, "ACTIVE_REMOUNT_ERROR"),
      ));
      expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_REMOUNT_ERROR");
      expect(gets).toBe(beforeCurrent);
      expect(screen.getByRole("button", { name: button })).not.toBeDisabled();
    }
    remounted.unmount();
  });

  it.each(
    (["candidates", ...detailUnits] as const).flatMap((unit) =>
      settlements.flatMap((outcome) =>
        (["success", "api-error"] as const).map((currentOutcome) =>
          [unit, outcome, currentOutcome] as const,
        ),
      ),
    ),
  )(
    "active remount owns pending %s read after old %s/finally; current %s",
    async (unit, outcome, currentOutcome) => {
      const old = deferred<Response>(); const current = deferred<Response>(); let calls = 0;
      const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = path(input);
        const matches = unit === "candidates" ? url.endsWith("/m05/candidates")
          : matchesDetailUnit(unit, url);
        if (matches) {
          calls += 1;
          return calls === 1 ? old.promise : current.promise;
        }
        return defaultResponse(url);
      }));
      const view = renderPage("old-mount");
      const oldLocationKey = screen.getByLabelText("route generation").textContent;
      if (unit !== "candidates") {
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      } else {
        await waitFor(() => expect(calls).toBe(1));
      }
      view.unmount();
      const remounted = renderPage("new-mount");
      if (unit !== "candidates") {
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      } else {
        await waitFor(() => expect(calls).toBe(2));
      }
      await waitFor(() => expect(calls).toBe(2));
      const activeLocationKey = screen.getByLabelText("route generation").textContent;
      expect(oldLocationKey).toBe("old-mount");
      expect(activeLocationKey).toBe("new-mount");
      expect(activeLocationKey).not.toBe(oldLocationKey);
      const staleResponse = unit === "candidates"
        ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])
        : staleReadResponse(unit);
      await settle(old, outcome, staleResponse);
      expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
      expect(screen.getByText(/M05 — כרטסת יתרות פנסיה/)).toBeInTheDocument();
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(consoleError).not.toHaveBeenCalled();
      if (currentOutcome === "success") {
        const activeResponse = unit === "candidates"
          ? json([{ ...candidate(1), provider_name: "ACTIVE_REMOUNT_OWNER" }])
          : ownedReadResponse(unit, "ACTIVE_REMOUNT_OWNER");
        await act(async () => current.resolve(activeResponse));
        expect((await screen.findAllByText(/ACTIVE_REMOUNT_OWNER/)).length).toBeGreaterThan(0);
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      } else {
        await act(async () => current.resolve(
          json(
            { detail: { code: "ACTIVE_REMOUNT_PENDING_ERROR" } },
            409,
            "ACTIVE_REMOUNT_PENDING_ERROR",
          ),
        ));
        expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_REMOUNT_PENDING_ERROR");
        expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      }
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
      remounted.unmount();
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
      await launchMutation("התאמת יתרות");
      await waitFor(() => expect(delayed).toBe(true));
      fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
      expect(await screen.findByText(/לקוח: Client 1/)).toBeInTheDocument();
      expect(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ })).toBeInTheDocument();
      const response = unit === "overview" ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }]) : staleReadResponse(unit);
      await settle(pending, outcome, response);
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
    },
  );

  it.each(
    (["overview", ...detailUnits] as const).flatMap((unit) =>
      settlements.flatMap((outcome) =>
        (["success", "api-error"] as const).map((currentOutcome) =>
          [unit, outcome, currentOutcome] as const,
        ),
      ),
    ),
  )(
    "keeps newer %s refresh owner pending while stale refresh %s/finally settles; current %s",
    async (unit, outcome, currentOutcome) => {
      const old = deferred<Response>(); const current = deferred<Response>();
      let afterPost = false; let refreshCalls = 0; let overviewCalls = 0; let currentGeneration = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) overviewCalls += 1;
        if ((init?.method ?? "GET") === "POST" && url.endsWith("/reconcile")) {
          afterPost = true;
          return json(revision(1, "reconciled"), 201);
        }
        const matches = unit === "overview" ? url.endsWith("/m05/candidates") : matchesDetailUnit(unit, url);
        if (afterPost && matches) {
          refreshCalls += 1;
          return currentGeneration ? current.promise : old.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation("התאמת יתרות");
      await waitFor(() => expect(refreshCalls).toBe(1));
      currentGeneration = true;
      await revisitRoute();
      if (unit !== "overview") {
        await waitFor(() => expect(overviewCalls).toBe(3));
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      }
      await waitFor(() => expect(refreshCalls).toBe(2));
      const activeGeneration = screen.getByLabelText("route generation").textContent;
      const staleResponse = unit === "overview"
        ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])
        : staleReadResponse(unit);
      await settle(old, outcome, staleResponse);
      expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
      expect(screen.getByLabelText("route generation")).toHaveTextContent(activeGeneration ?? "");
      if (unit === "overview") {
        expect(screen.getByText(/לקוח: 1\./)).toBeInTheDocument();
        expect(screen.getByText("אין רשומות ידניות מועמדות ל־M05.")).toBeInTheDocument();
        expect(screen.getByText("אין כרטסות M05.")).toBeInTheDocument();
      } else {
        expect(screen.getByText(/לקוח: Client 1/)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Provider 1 / Account 1" })).toBeInTheDocument();
      }
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      if (currentOutcome === "success") {
        const activeResponse = unit === "overview"
          ? json([{ ...candidate(1), provider_name: "ACTIVE_REFRESH_OWNER" }])
          : ownedReadResponse(unit, "ACTIVE_REFRESH_OWNER");
        await act(async () => current.resolve(activeResponse));
        expect((await screen.findAllByText(/ACTIVE_REFRESH_OWNER/)).length).toBeGreaterThan(0);
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      } else {
        await act(async () => current.resolve(
          json(
            { detail: { code: "ACTIVE_REFRESH_PENDING_ERROR" } },
            409,
            "ACTIVE_REFRESH_PENDING_ERROR",
          ),
        ));
        expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_REFRESH_PENDING_ERROR");
        expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      }
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
      expect(screen.getByLabelText("route generation")).toHaveTextContent(activeGeneration ?? "");
    },
  );

  it.each(
    (["overview", ...detailUnits] as const).flatMap((unit) =>
      settlements.map((outcome) => [unit, outcome] as const),
    ),
  )(
    "preserves current %s refresh structured error after stale %s/finally settle",
    async (unit, outcome) => {
      const old = deferred<Response>(); const current = deferred<Response>();
      let afterPost = false; let refreshCalls = 0; let overviewCalls = 0;
      let currentGeneration = false;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = path(input);
        if (url.endsWith("/m05/candidates")) overviewCalls += 1;
        if ((init?.method ?? "GET") === "POST" && url.endsWith("/reconcile")) {
          afterPost = true;
          return json(revision(1, "reconciled"), 201);
        }
        const matches = unit === "overview"
          ? url.endsWith("/m05/candidates") : matchesDetailUnit(unit, url);
        if (afterPost && matches) {
          refreshCalls += 1;
          return currentGeneration ? current.promise : old.promise;
        }
        return defaultResponse(url);
      }));
      renderNavigable();
      await launchMutation("התאמת יתרות");
      await waitFor(() => expect(refreshCalls).toBe(1));
      currentGeneration = true;
      await revisitRoute();
      if (unit !== "overview") {
        await waitFor(() => expect(overviewCalls).toBe(3));
        fireEvent.click(await screen.findByRole("button", { name: "Provider 1 / Account 1" }));
      }
      await waitFor(() => expect(refreshCalls).toBe(2));
      await act(async () => current.resolve(
        json({ detail: { code: "ACTIVE_REFRESH_ERROR" } }, 409, "ACTIVE_REFRESH_ERROR"),
      ));
      expect(await screen.findByRole("alert")).toHaveTextContent("ACTIVE_REFRESH_ERROR");
      const staleResponse = unit === "overview"
        ? json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])
        : staleReadResponse(unit);
      await settle(old, outcome, staleResponse);
      expect(screen.getByRole("alert")).toHaveTextContent("ACTIVE_REFRESH_ERROR");
      expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
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
    await launchMutation("התאמת יתרות");
    await waitFor(() => expect(candidateCall).toBe(2));
    fireEvent.click(screen.getByRole("button", { name: "A revisit" }));
    await waitFor(() => expect(candidateCall).toBe(3));
    await act(async () => stale.resolve(json([{ ...candidate(1), provider_name: "STALE_EVIDENCE" }])));
    expect(screen.getByText(/טוען נתוני M05/)).toBeInTheDocument();
    await act(async () => current.resolve(json([candidate(1)])));
    expect(await screen.findByRole("button", { name: /Provider 1 \/ Account 1 \/ 2026/ })).toBeInTheDocument();
    expect(screen.queryByText(/STALE_EVIDENCE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/טוען נתוני M05/)).not.toBeInTheDocument();
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
