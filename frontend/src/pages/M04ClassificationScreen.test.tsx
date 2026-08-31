import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { M04Component, M04Revision } from "../api/m04ClassificationApi";
import { M04ClassificationScreen } from "./M04ClassificationScreen";

const json = (body: unknown, status = 200): Response => ({
  ok: status < 400,
  status,
  statusText: status < 400 ? "OK" : "Error",
  headers: { get: () => "application/json" },
  json: async () => body,
  text: async () => JSON.stringify(body),
}) as unknown as Response;
const client = (id = 1, status: "delivered" | "archived" = "delivered") => ({
  client_id: id,
  full_name: `Client ${id}`,
  id_number: `00${id}`,
  birth_date: null,
  file_status: "file_created",
  professional_identification_status: "identification_incomplete",
  m01_case: { lifecycle_status: status },
});
const component = (
  interpretation: "pension" | "capital" | "unresolved" = "unresolved",
): M04Component => ({
  component_decision_id: "component-1",
  evidence_identity: "component:0:abc",
  original_label: "תגמולים",
  original_code: "contribution_component",
  component_kind: "contribution_component" as const,
  interpretation,
  matched_rule_evidence: [],
  explanation: "component explanation",
  current_employer_related: "unknown" as const,
});
const revision = (
  state: "under_review" | "proposed" | "accepted" | "unresolved" | "rejected",
  sequence: number,
  action?: M04Revision["action_type"],
): M04Revision => ({
  revision_id: `r-${sequence}`,
  revision_sequence: sequence,
  predecessor_revision_id: sequence === 1 ? null : `r-${sequence - 1}`,
  historical_revision_id: null,
  state,
  action_type: action ?? ({
    under_review: "start", proposed: "proposal", accepted: "accept",
    unresolved: "unresolved", rejected: "reject",
  } as const)[state],
  product_family: state === "under_review" ? null : "provident_fund",
  pension_subtype: null,
  aggregate_interpretation:
    state === "under_review" ? null : state === "proposed" ? "unresolved" : "pension",
  explanation: "classification explanation",
  reason_code: sequence === 1 ? null : "planner_decision",
  reason: sequence === 1 ? null : "planner reason",
  catalogue_version: "m04-rules-v1" as const,
  matched_rule_evidence: [],
  match_basis: "workflow",
  action_evidence: {},
  input_snapshot: {},
  actor: "system:m04-classification-ui:M04 classification workflow",
  actor_is_authentication: false as const,
  created_at: "2026-07-31T00:00:00Z",
  components: state === "under_review" ? [] : [component(state === "accepted" ? "pension" : "unresolved")],
});
const target = (
  clientId = 1,
  current: ReturnType<typeof revision> | null = null,
  exclusion?: string | null,
) => ({
  client_id: clientId,
  intake_id: `manual-${clientId}`,
  target_kind: "manual_record_review" as const,
  record_kind: "manual" as const,
  m01_lifecycle_status: "delivered",
  m02_lifecycle_status: "accepted_for_review",
  m03_eligible: true,
  m03_exclusion_reason: null,
  m03_accepted_revision_id: `m03-${clientId}`,
  source_id: null,
  declared_provider_name: `Provider ${clientId}`,
  product_name: "Persisted product",
  declared_product_type: "provident_fund",
  product_identifier: null,
  declared_account_reference: null,
  declared_component_values: [{ label: "תגמולים", code: "contribution_component" }],
  current_revision: current,
  eligibility: {
    eligible_for_m05: current?.state === "accepted" && !exclusion,
    exclusion_reason: exclusion ?? (current ? `classification_${current.state}` : "no_classification"),
    current_revision_id: current?.revision_id ?? null,
    accepted_revision_id: current?.state === "accepted" && !exclusion ? current.revision_id : null,
    m03_revision_id: `m03-${clientId}`,
    meaning: "accepted resolved M04 classification may be consumed only by a separately authorized M05 package",
  },
});
const preview = {
  catalogue_version: "m04-rules-v1",
  product_family: "provident_fund",
  aggregate_interpretation: "unresolved",
  components: [component()],
  matched_rule_evidence: [{ rule_id: "m04.asset.product-type.provident_fund", rationale: "exact" }],
  conflicts: [],
  unresolved_reasons: ["component_interpretation_unresolved"],
  persists_revision: false,
};
const fullRule = (overrides: Record<string, unknown> = {}) => ({
  catalogue_version: "m04-rules-v1",
  rule_id: "m04.asset.product-type.provident_fund",
  matcher_type: "declared_product_type_exact",
  exact_matcher_value: "provident_fund",
  scope: "asset",
  provider_scope: "Persisted Provider",
  source_format_scope: "manual",
  output_product_family: "provident_fund",
  output_component_kind: null,
  output_interpretation: null,
  rationale: "Exact accepted token",
  authority_reference: "PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.1",
  conflict_behavior: "unresolved",
  ...overrides,
});
const ACTION_CASES = [
  { action: "start", state: null, button: "התחלת סיווג", endpoint: "/start" },
  { action: "proposal", state: "under_review", button: "יצירת הצעת סיווג", endpoint: "/proposal" },
  { action: "unresolved", state: "under_review", button: "סימון כלא מוכרע", endpoint: "/unresolved", reason: true },
  { action: "accept", state: "proposed", button: "אישור ההצעה", endpoint: "/accept", reason: true },
  { action: "reject", state: "proposed", button: "דחיית ההצעה", endpoint: "/reject", reason: true },
  { action: "reopen", state: "accepted", button: "פתיחת הסיווג מחדש", endpoint: "/reopen", reason: true },
  { action: "override", state: "proposed", button: "יצירת הצעת הכרעה ידנית", endpoint: "/override", reason: true },
  { action: "undo", state: "proposed", button: "יצירת הצעת ביטול", endpoint: "/undo", reason: true },
  { action: "start_revalidation", state: "accepted", button: "התחלת אימות מחדש", endpoint: "/start-revalidation", reason: true, revalidation: true },
] as const;

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};
const deferred = <T,>(): Deferred<T> => {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
};

function renderPage(status: "delivered" | "archived" = "delivered") {
  return render(
    <MemoryRouter initialEntries={[`/clients/1/classification?status=${status}`]}>
      <Routes>
        <Route path="/clients/:clientId/classification" element={<M04ClassificationScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}
function NavigationControls() {
  const navigate = useNavigate();
  return <>
    <button onClick={() => navigate("/clients/1/classification")}>Navigate A</button>
    <button onClick={() => navigate("/clients/2/classification")}>Navigate B</button>
  </>;
}
function renderNavigable() {
  return render(
    <MemoryRouter initialEntries={["/clients/1/classification"]}>
      <NavigationControls />
      <Routes>
        <Route path="/clients/:clientId/classification" element={<M04ClassificationScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}
afterEach(() => vi.restoreAllMocks());

describe("M04ClassificationScreen", () => {
  it("shows manual provenance, exact preview, and explicit lifecycle actions", async () => {
    let current: ReturnType<typeof revision> | null = null;
    let history: ReturnType<typeof revision>[] = [];
    const postedBodies: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets") && (init?.method ?? "GET") === "GET") {
        return json([target(1, current)]);
      }
      if (url.endsWith("/preview")) return json(preview);
      if (url.endsWith("/history")) return json(history);
      if (url.endsWith("/matched-rules")) return json(current?.matched_rule_evidence ?? []);
      if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
      if (
        url.endsWith("/m04/targets/manual-1") &&
        (init?.method ?? "GET") === "GET"
      ) return json(target(1, current));
      if (url.endsWith("/start")) {
        expect(init?.body).toBeUndefined();
        current = revision("under_review", 1); history = [current]; return json(current, 201);
      }
      if (url.endsWith("/proposal")) {
        const body = JSON.parse(String(init?.body)); postedBodies.push(body);
        expect(Object.keys(body)).toEqual(["expected_current_revision_id"]);
        current = revision("proposed", 2, "proposal"); history = [...history, current];
        return json(current, 201);
      }
      throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect(await screen.findByText(/ללא קובץ מקור או checksum/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "התחלת סיווג" }));
    expect(await screen.findByRole("heading", { name: /גרסה #1 — הגרסה הנוכחית/ })).toBeInTheDocument();
    expect(screen.getByText(/מצב: בבדיקה; פעולה: התחלת בדיקה/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
    expect(await screen.findByText(/קטלוג: m04-rules-v1/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "יצירת הצעת סיווג" }));
    expect(await screen.findByRole("button", { name: "אישור ההצעה" })).toBeInTheDocument();
    expect(postedBodies).toHaveLength(1);
  });

  it("keeps archived targets read-only with retained history", async () => {
    const accepted = revision("accepted", 4, "accept");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client(1, "archived"));
      if (url.endsWith("/m04/targets")) return json([{ ...target(1, accepted), m01_lifecycle_status: "archived" }]);
      if (url.endsWith("/history")) return json([accepted]);
      if (url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json({ ...target(1, accepted, "archived_case").eligibility });
      if (url.endsWith("/manual-1")) return json({ ...target(1, accepted), m01_lifecycle_status: "archived" });
      throw new Error(`unexpected ${url}`);
    }));
    renderPage("archived");
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect(await screen.findByText(/התיק בארכיון: M04 זמין לקריאה בלבד/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "פעולות זמינות" })).toBeDisabled();
    expect(screen.getByRole("heading", { name: /גרסה #4 — הגרסה הנוכחית/ })).toBeInTheDocument();
    expect(screen.getByText(/מצב: אושר; פעולה: אישור/)).toBeInTheDocument();
  });

  it("binds proposal decisions to the displayed revision and reloads structured conflicts", async () => {
    const displayed = {
      ...revision("proposed", 2, "proposal"),
      input_snapshot: { accepted_m03_revision_id: "m03-1" },
    };
    const refreshed = {
      ...revision("proposed", 3, "proposal"),
      input_snapshot: { accepted_m03_revision_id: "m03-1" },
    };
    let conflictReturned = false;
    let posted: Record<string, unknown> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const current = conflictReturned ? refreshed : displayed;
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets") && (init?.method ?? "GET") === "GET") {
        return json([target(1, current)]);
      }
      if (url.endsWith("/history")) return json([current]);
      if (url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
      if (url.endsWith("/manual-1") && (init?.method ?? "GET") === "GET") {
        return json(target(1, current));
      }
      if (url.endsWith("/accept") && init?.method === "POST") {
        posted = JSON.parse(String(init.body));
        conflictReturned = true;
        return json({
          detail: {
            code: "M04_STALE_CURRENT_REVISION",
            message: "Classification changed before this action",
          },
        }, 409);
      }
      throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    fireEvent.change(await screen.findByLabelText("הסבר"), {
      target: { value: "accept displayed proposal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "אישור ההצעה" }));
    await waitFor(() => expect(posted).toMatchObject({
      expected_current_revision_id: displayed.revision_id,
    }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /הצעת הסיווג השתנתה.*נטען מחדש.*M04_STALE_CURRENT_REVISION/i,
    );
    expect(screen.getByRole("heading", {
      name: /גרסה #3 — הגרסה הנוכחית — קשורה לראיות המקור העדכניות/,
    })).toBeInTheDocument();
  });

  it("renders complete persisted rule, component, revision, conflict, and authority evidence", async () => {
    const assetRule = fullRule();
    const componentRule = fullRule({
      rule_id: "m04.component.token.contribution",
      matcher_type: "component_code_exact",
      exact_matcher_value: "contribution_component",
      scope: "component",
      provider_scope: undefined,
      source_format_scope: undefined,
      output_product_family: null,
      output_component_kind: "contribution_component",
      rationale: "Exact bounded component token",
      authority_reference: "PKG_009_FINAL_PACKAGE_DEFINITION.md section 5.2",
    });
    const historical = revision("under_review", 1, "start");
    const current = {
      ...revision("unresolved", 2, "unresolved"),
      explanation: "Persisted unresolved explanation",
      reason: "Planner retained unresolved evidence",
      action_evidence: {
        unresolved_reasons: ["opaque_uploaded_facts_unavailable"],
        conflicts: ["conflicting-rule-a", "conflicting-rule-b"],
      },
      matched_rule_evidence: [assetRule],
      components: [{ ...component(), matched_rule_evidence: [componentRule] }],
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets")) return json([target(1, current)]);
      if (url.endsWith("/history")) return json([historical, current]);
      if (url.endsWith("/matched-rules")) return json([assetRule]);
      if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
      if (url.endsWith("/manual-1")) return json(target(1, current));
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect((await screen.findAllByText("declared_product_type_exact")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("provident_fund").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Persisted Provider").length).toBeGreaterThan(0);
    expect(screen.getAllByText("manual").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PKG_009_FINAL_PACKAGE_DEFINITION/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("unresolved").length).toBeGreaterThan(0);
    expect(screen.getByText("component_code_exact")).toBeInTheDocument();
    expect(screen.getAllByText("לא קיים").length).toBeGreaterThan(0);
    expect(screen.getByText(/Persisted unresolved explanation/)).toBeInTheDocument();
    expect(screen.getByText(/Planner retained unresolved evidence/)).toBeInTheDocument();
    expect(screen.getAllByText(/opaque_uploaded_facts_unavailable/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/conflicting-rule-a/).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /גרסה #1 — היסטורית/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /גרסה #2 — הגרסה הנוכחית/ })).toBeInTheDocument();
    expect(screen.getByText(/אין בו סמכות מקצועית, מיסויית, משפטית, נזילות, משיכה או סמכות M05/)).toBeInTheDocument();
  });

  it.each([
    ["under_review", ["תצוגה מקדימה של הכללים המדויקים", "יצירת הצעת סיווג", "סימון כלא מוכרע"]],
    ["proposed", ["אישור ההצעה", "דחיית ההצעה", "יצירת הצעת הכרעה ידנית", "יצירת הצעת ביטול"]],
    ["accepted", ["פתיחת הסיווג מחדש", "יצירת הצעת הכרעה ידנית", "יצירת הצעת ביטול"]],
    ["unresolved", ["פתיחת הסיווג מחדש", "יצירת הצעת הכרעה ידנית", "יצירת הצעת ביטול"]],
    ["rejected", ["פתיחת הסיווג מחדש", "יצירת הצעת הכרעה ידנית", "יצירת הצעת ביטול"]],
  ] as const)("exposes the bounded action matrix for %s", async (state, buttons) => {
    const current = revision(state, 3);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets")) return json([target(1, current)]);
      if (url.endsWith("/history")) return json([revision("under_review", 1), current]);
      if (url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
      if (url.endsWith("/manual-1")) return json(target(1, current));
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    for (const button of buttons) {
      expect(await screen.findByRole("button", { name: button })).toBeInTheDocument();
    }
  });

  it("shows only start_revalidation when post-archive revalidation is required", async () => {
    const accepted = revision("accepted", 4, "accept");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets")) return json([target(1, accepted, "m04_revalidation_required")]);
      if (url.endsWith("/history")) return json([accepted]);
      if (url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(1, accepted, "m04_revalidation_required").eligibility);
      if (url.endsWith("/manual-1")) return json(target(1, accepted, "m04_revalidation_required"));
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect(await screen.findByRole("button", { name: "התחלת אימות מחדש" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "פתיחת הסיווג מחדש" })).not.toBeInTheDocument();
  });

  it("shows explicit Hebrew revalidation for a stale proposed revision and disables stale decisions", async () => {
    const proposed = revision("proposed", 4, "proposal");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m04/targets")) return json([target(1, proposed, "m04_revalidation_required")]);
      if (url.endsWith("/history")) return json([proposed]);
      if (url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(1, proposed, "m04_revalidation_required").eligibility);
      if (url.endsWith("/manual-1")) return json(target(1, proposed, "m04_revalidation_required"));
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect((await screen.findAllByText("נדרש אימות מחדש של הסיווג")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "התחלת אימות מחדש" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "אישור ההצעה" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "דחיית ההצעה" })).toBeDisabled();
  });

  it.each(["success", "rejected", "api-error"] as const)(
    "same-generation target X-to-Y ignores stale X %s and finally",
    async (outcome) => {
      const oldX = deferred<Response>();
      const x = { ...target(1), intake_id: "target-x", declared_provider_name: "Provider X old" };
      const y = { ...target(1), intake_id: "target-y", declared_provider_name: "Provider Y current" };
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) return json([x, y]);
        if (url.endsWith("/target-x")) return oldX.promise;
        if (url.endsWith("/target-y")) return json(y);
        if (url.includes("/target-")) {
          if (url.endsWith("/history") || url.endsWith("/matched-rules")) return json([]);
          if (url.endsWith("/eligibility")) return json(target(1).eligibility);
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderPage();
      fireEvent.click(await screen.findByRole("button", { name: /target-x/ }));
      fireEvent.click(screen.getByRole("button", { name: /target-y/ }));
      expect(await screen.findByText(/גוף מנהל: Provider Y current/)).toBeInTheDocument();
      await act(async () => {
        if (outcome === "success") oldX.resolve(json(x));
        else if (outcome === "api-error") oldX.resolve(json({ detail: { code: "OLD_X" } }, 409));
        else oldX.reject(new Error("old X rejection"));
        try { await oldX.promise; } catch { /* expected */ }
      });
      expect(screen.getByText(/גוף מנהל: Provider Y current/)).toBeInTheDocument();
      expect(screen.queryByText(/Provider X old/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();
    },
  );

  it.each(["success", "rejected", "api-error"] as const)(
    "same-target overlapping preview keeps newer preview after old %s and finally",
    async (outcome) => {
      const oldPreview = deferred<Response>();
      let previewCalls = 0;
      const current = revision("under_review", 1);
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) return json([target(1, current)]);
        if (url.endsWith("/history")) return json([current]);
        if (url.endsWith("/matched-rules")) return json([]);
        if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
        if (url.endsWith("/manual-1")) return json(target(1, current));
        if (url.endsWith("/preview")) {
          previewCalls += 1;
          return previewCalls === 1 ? oldPreview.promise : json({
            ...preview, product_family: "education_fund",
            unresolved_reasons: ["NEW_PREVIEW_AUTHORITATIVE"],
          });
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderPage();
      fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
      const button = await screen.findByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" });
      fireEvent.click(button); fireEvent.click(button);
      expect(await screen.findByText(/NEW_PREVIEW_AUTHORITATIVE/)).toBeInTheDocument();
      await act(async () => {
        if (outcome === "success") oldPreview.resolve(json({
          ...preview, product_family: "savings_policy",
          unresolved_reasons: ["OLD_PREVIEW_STALE"],
        }));
        else if (outcome === "api-error") oldPreview.resolve(json({ detail: { code: "OLD" } }, 409));
        else oldPreview.reject(new Error("old preview rejection"));
        try { await oldPreview.promise; } catch { /* expected */ }
      });
      expect(screen.getByText(/NEW_PREVIEW_AUTHORITATIVE/)).toBeInTheDocument();
      expect(screen.queryByText(/OLD_PREVIEW_STALE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();
    },
  );

  it.each(
    (["target-list", "detail-bundle", "preview", "mutation"] as const).flatMap((unit) =>
      (["success", "rejected", "api-error"] as const).map(
        (outcome) => [unit, outcome] as const,
      ),
    ),
  )(
    "%s unmount invalidates pending %s, finally, and post-unmount refresh",
    async (unit, outcome) => {
      const pending = deferred<Response>();
      const urls: string[] = [];
      const current = unit === "mutation" ? null : revision("under_review", 1);
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input); urls.push(url);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) {
          return unit === "target-list" ? pending.promise : json([target(1, current)]);
        }
        if (url.endsWith("/manual-1/start")) return pending.promise;
        if (url.endsWith("/preview")) return pending.promise;
        if (url.endsWith("/history") || url.endsWith("/matched-rules")) return json(current ? [current] : []);
        if (url.endsWith("/eligibility")) return json(target(1, current).eligibility);
        if (url.endsWith("/manual-1")) {
          return unit === "detail-bundle" ? pending.promise : json(target(1, current));
        }
        throw new Error(`unexpected ${url}`);
      }));
      const view = renderPage();
      if (unit !== "target-list") {
        fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
        if (unit === "preview") {
          fireEvent.click(await screen.findByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
        } else if (unit === "mutation") {
          fireEvent.click(await screen.findByRole("button", { name: "התחלת סיווג" }));
        }
      } else {
        await waitFor(() => expect(urls.some((url) => url.endsWith("/m04/targets"))).toBe(true));
      }
      const callsAtUnmount = urls.length;
      view.unmount();
      await act(async () => {
        if (outcome === "success") pending.resolve(json(unit === "target-list" ? [target(1)] : {}));
        else if (outcome === "api-error") pending.resolve(json({ detail: { code: "POST_UNMOUNT" } }, 409));
        else pending.reject(new Error("post-unmount rejection"));
        try { await pending.promise; } catch { /* expected */ }
      });
      expect(urls).toHaveLength(callsAtUnmount);
      expect(view.container).toBeEmptyDOMElement();
    },
  );

  it.each(
    ACTION_CASES.flatMap((actionCase) =>
      (["success", "rejected", "api-error"] as const).map(
        (previewOutcome) => [actionCase.action, actionCase, previewOutcome] as const,
      ),
    ),
  )(
    "%s mutation invalidates an older preview %s and preserves post-mutation state",
    async (_actionName, actionCase, previewOutcome) => {
      const oldPreview = deferred<Response>();
      let mutationStarted = false;
      let detailCalls = 0;
      const source = actionCase.state
        ? revision(actionCase.state, actionCase.state === "under_review" ? 1 : 2)
        : null;
      const post = {
        ...revision(source?.state ?? "under_review", (source?.revision_sequence ?? 0) + 1),
        revision_id: "r-post-mutation",
        explanation: "POST_MUTATION_AUTHORITATIVE",
      };
      const sourceTarget = target(
        1, source,
        "revalidation" in actionCase && actionCase.revalidation
          ? "m04_revalidation_required" : undefined,
      );
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) return json([mutationStarted ? target(1, post) : sourceTarget]);
        if (url.endsWith("/preview")) return oldPreview.promise;
        if (url.endsWith(actionCase.endpoint)) {
          mutationStarted = true;
          return json(post, 201);
        }
        if (url.endsWith("/history")) return json(mutationStarted
          ? [post]
          : actionCase.action === "undo" && source
            ? [revision("under_review", 1), source]
            : source ? [source] : []);
        if (url.endsWith("/matched-rules")) return json([]);
        if (url.endsWith("/eligibility")) return json(
          (mutationStarted ? target(1, post) : sourceTarget).eligibility,
        );
        if (url.endsWith("/manual-1")) {
          detailCalls += 1;
          return json(mutationStarted ? target(1, post) : sourceTarget);
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderPage();
      fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      fireEvent.click(await screen.findByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
      if ("reason" in actionCase && actionCase.reason) {
        fireEvent.change(screen.getByLabelText("הסבר"), {
          target: { value: `${actionCase.action} explanation` },
        });
      }
      if (actionCase.action === "override") {
        fireEvent.change(screen.getByLabelText("פרשנות"), {
          target: { value: "pension" },
        });
      }
      if (actionCase.action === "undo") {
        const historySelect = screen.getByLabelText("גרסה היסטורית לביטול");
        fireEvent.change(historySelect, { target: { value: "r-1" } });
      }
      fireEvent.click(screen.getByRole("button", { name: actionCase.button }));
      expect(await screen.findByText(/POST_MUTATION_AUTHORITATIVE/)).toBeInTheDocument();
      const readsAfterMutation = detailCalls;
      await act(async () => {
        if (previewOutcome === "success") oldPreview.resolve(json({
          ...preview, unresolved_reasons: ["OLD_PREVIEW_MUST_NOT_APPLY"],
        }));
        else if (previewOutcome === "api-error") oldPreview.resolve(json({ detail: { code: "OLD_PREVIEW" } }, 409));
        else oldPreview.reject(new Error("old preview rejection"));
        try { await oldPreview.promise; } catch { /* expected */ }
      });
      expect(detailCalls).toBe(readsAfterMutation);
      expect(screen.getByText(/POST_MUTATION_AUTHORITATIVE/)).toBeInTheDocument();
      expect(screen.queryByText(/OLD_PREVIEW_MUST_NOT_APPLY/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();
    },
  );

  it.each(["success", "rejected", "api-error"] as const)(
    "preview bound to revision R1 is stale after detail refresh to R2: %s",
    async (outcome) => {
      const oldPreview = deferred<Response>();
      let detailCalls = 0;
      const r1 = revision("under_review", 1);
      const r2 = { ...revision("under_review", 2, "reopen"), explanation: "REVISION_R2_CURRENT" };
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) return json([target(1, r1)]);
        if (url.endsWith("/preview")) return oldPreview.promise;
        if (url.endsWith("/history")) return json(detailCalls > 1 ? [r1, r2] : [r1]);
        if (url.endsWith("/matched-rules")) return json([]);
        if (url.endsWith("/eligibility")) return json(target(1, detailCalls > 1 ? r2 : r1).eligibility);
        if (url.endsWith("/manual-1")) {
          detailCalls += 1;
          return json(target(1, detailCalls > 1 ? r2 : r1));
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderPage();
      const targetButton = await screen.findByRole("button", { name: /manual-1/ });
      fireEvent.click(targetButton);
      fireEvent.click(await screen.findByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
      fireEvent.click(targetButton);
      expect(await screen.findByText(/REVISION_R2_CURRENT/)).toBeInTheDocument();
      await act(async () => {
        if (outcome === "success") oldPreview.resolve(json({
          ...preview, unresolved_reasons: ["R1_PREVIEW_STALE"],
        }));
        else if (outcome === "api-error") oldPreview.resolve(json({ detail: { code: "R1_OLD" } }, 409));
        else oldPreview.reject(new Error("R1 preview rejection"));
        try { await oldPreview.promise; } catch { /* expected */ }
      });
      expect(screen.getByText(/REVISION_R2_CURRENT/)).toBeInTheDocument();
      expect(screen.queryByText(/R1_PREVIEW_STALE/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it.each(ACTION_CASES.map((actionCase) => [actionCase.action, actionCase] as const))(
    "%s post-mutation new preview succeeds with action-specific payload",
    async (_actionName, actionCase) => {
      const oldPreview = deferred<Response>();
      const mutation = deferred<Response>();
      const newPreview = deferred<Response>();
      let previewCalls = 0;
      let mutationCalls = 0;
      let mutationResolved = false;
      let mutationInit: RequestInit | undefined;
      const refreshUrls: string[] = [];
      const source = actionCase.state
        ? revision(actionCase.state, actionCase.state === "under_review" ? 1 : 2)
        : null;
      const postState = ({
        start: "under_review", proposal: "proposed", unresolved: "unresolved",
        accept: "accepted", reject: "rejected", reopen: "under_review",
        override: "proposed", undo: "proposed", start_revalidation: "under_review",
      } as const)[actionCase.action];
      const post = {
        ...revision(
          postState,
          (source?.revision_sequence ?? 0) + 1,
          actionCase.action,
        ),
        revision_id: `r-post-${actionCase.action}`,
        explanation: `POST_${actionCase.action.toUpperCase()}_REVISION`,
      };
      const sourceTarget = target(
        1,
        source,
        "revalidation" in actionCase && actionCase.revalidation
          ? "m04_revalidation_required" : undefined,
      );
      const historyBefore = actionCase.action === "undo" && source
        ? [revision("under_review", 1), source]
        : source ? [source] : [];
      const historyAfter = [...historyBefore, post];
      vi.stubGlobal("fetch", vi.fn(async (
        input: RequestInfo | URL,
        init?: RequestInit,
      ) => {
        const url = String(input);
        if (mutationResolved) refreshUrls.push(url);
        if (url.endsWith("/api/clients/1")) return json(client());
        if (url.endsWith("/m04/targets")) {
          return json([mutationResolved ? target(1, post) : sourceTarget]);
        }
        if (url.endsWith("/preview")) {
          previewCalls += 1;
          return previewCalls === 1 ? oldPreview.promise : newPreview.promise;
        }
        if (url.endsWith(actionCase.endpoint)) {
          mutationCalls += 1;
          mutationInit = init;
          return mutation.promise;
        }
        if (url.endsWith("/history")) return json(mutationResolved ? historyAfter : historyBefore);
        if (url.endsWith("/matched-rules")) return json([]);
        if (url.endsWith("/eligibility")) return json(
          (mutationResolved ? target(1, post) : sourceTarget).eligibility,
        );
        if (url.endsWith("/manual-1")) {
          return json(mutationResolved ? target(1, post) : sourceTarget);
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderPage();
      fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      fireEvent.click(await screen.findByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
      expect(previewCalls).toBe(1);
      expect(screen.getByText(/טוען את סיווג M04/)).toBeInTheDocument();
      if ("reason" in actionCase && actionCase.reason) {
        fireEvent.change(screen.getByLabelText("הסבר"), {
          target: { value: `${actionCase.action} explanation` },
        });
      }
      if (actionCase.action === "override") {
        fireEvent.change(screen.getByLabelText("פרשנות"), {
          target: { value: "pension" },
        });
      }
      if (actionCase.action === "undo") {
        fireEvent.change(screen.getByLabelText("גרסה היסטורית לביטול"), {
          target: { value: "r-1" },
        });
      }
      fireEvent.click(screen.getByRole("button", { name: actionCase.button }));
      expect(mutationCalls).toBe(1);
      await waitFor(() => expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument());

      const reasonPayload = source ? {
        expected_current_revision_id: source.revision_id,
        reason_code: "planner_decision",
        explanation: `${actionCase.action} explanation`,
      } : null;
      const expectedBody = actionCase.action === "start" ? undefined
        : actionCase.action === "proposal"
          ? { expected_current_revision_id: source?.revision_id }
          : actionCase.action === "override"
            ? {
              ...reasonPayload,
              confirmed: true,
              product_family: "provident_fund",
              pension_subtype: null,
              components: [{
                evidence_identity: "component:0:abc",
                component_kind: "contribution_component",
                interpretation: "pension",
                current_employer_related: "unknown",
                explanation: "component explanation",
              }],
            }
            : actionCase.action === "undo"
              ? { ...reasonPayload, confirmed: true, historical_revision_id: "r-1" }
              : reasonPayload;
      expect(mutationInit?.method).toBe("POST");
      expect(mutationInit?.body === undefined
        ? undefined : JSON.parse(String(mutationInit.body))).toEqual(expectedBody);

      mutationResolved = true;
      await act(async () => { mutation.resolve(json(post, 201)); });
      expect(await screen.findByText(new RegExp(`POST_${actionCase.action.toUpperCase()}_REVISION`)))
        .toBeInTheDocument();
      expect(refreshUrls.filter((url) => url.endsWith("/manual-1"))).toHaveLength(1);
      expect(refreshUrls.filter((url) => url.endsWith("/history"))).toHaveLength(1);
      expect(refreshUrls.filter((url) => url.endsWith("/eligibility"))).toHaveLength(1);
      expect(refreshUrls.filter((url) => url.endsWith("/matched-rules"))).toHaveLength(1);
      expect(refreshUrls.filter((url) => url.endsWith("/m04/targets"))).toHaveLength(1);

      fireEvent.click(screen.getByRole("button", { name: "תצוגה מקדימה של הכללים המדויקים" }));
      expect(previewCalls).toBe(2);
      expect(screen.getByText(/טוען את סיווג M04/)).toBeInTheDocument();
      await act(async () => { newPreview.resolve(json({
        ...preview,
        unresolved_reasons: [`NEW_PREVIEW_AFTER_${actionCase.action.toUpperCase()}`],
      })); });
      expect(await screen.findByText(
        new RegExp(`NEW_PREVIEW_AFTER_${actionCase.action.toUpperCase()}`),
      )).toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();

      await act(async () => { oldPreview.resolve(json({
        ...preview, unresolved_reasons: [`OLD_${actionCase.action.toUpperCase()}_PREVIEW_STALE`],
      })); });
      expect(screen.queryByText(
        new RegExp(`OLD_${actionCase.action.toUpperCase()}_PREVIEW_STALE`),
      )).not.toBeInTheDocument();
      expect(screen.getByText(
        new RegExp(`NEW_PREVIEW_AFTER_${actionCase.action.toUpperCase()}`),
      )).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();
      expect(mutationCalls).toBe(1);
    },
  );

  it.each(
    (["detail", "history", "matched-rules", "eligibility"] as const).flatMap((path) =>
      (["A-B", "A-B-A"] as const).flatMap((transition) =>
        (["success", "rejected", "api-error"] as const).map(
          (outcome) => [path, transition, outcome] as const,
        ),
      ),
    ),
  )(
    "%s bundle read %s stale %s cannot overwrite the current target bundle or finally",
    async (deferredPath, transition, outcome) => {
      const oldPart = deferred<Response>();
      let aBundle = 0;
      const bundleResponse = (kind: typeof deferredPath, id: number, marker: string) => {
        const current = { ...revision("under_review", 1), explanation: `${marker}-history` };
        if (kind === "detail") return json({
          ...target(id, current), declared_provider_name: `${marker}-detail`,
        });
        if (kind === "history") return json([current]);
        if (kind === "matched-rules") return json([
          fullRule({ rationale: `${marker}-matched-rules` }),
        ]);
        return json({
          ...target(id, current).eligibility,
          exclusion_reason: `${marker}-eligibility`,
        });
      };
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
        if (clientMatch) return json(client(Number(clientMatch[1])));
        const id = url.includes("/clients/2/") ? 2 : 1;
        if (url.endsWith("/m04/targets")) return json([target(id)]);
        let kind: typeof deferredPath | null = null;
        if (url.endsWith("/history")) kind = "history";
        else if (url.endsWith("/matched-rules")) kind = "matched-rules";
        else if (url.endsWith("/eligibility")) kind = "eligibility";
        else if (url.endsWith(`/manual-${id}`)) kind = "detail";
        if (kind) {
          if (id === 1 && kind === "detail") aBundle += 1;
          const marker = id === 2 ? "B-CURRENT" : aBundle === 1 ? "A-OLD" : "A-NEW";
          if (id === 1 && aBundle === 1 && kind === deferredPath) return oldPart.promise;
          return bundleResponse(kind, id, marker);
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderNavigable();
      fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      fireEvent.click(await screen.findByRole("button", { name: /manual-2/ }));
      const authoritative = transition === "A-B" ? "B-CURRENT" : "A-NEW";
      if (transition === "A-B-A") {
        fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
        fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      }
      const expectedMarker = deferredPath === "detail" ? `${authoritative}-detail`
        : deferredPath === "history" ? `${authoritative}-history`
          : deferredPath === "matched-rules" ? `${authoritative}-matched-rules`
            : `${authoritative}-eligibility`;
      if (deferredPath === "eligibility") {
        expect((await screen.findAllByText(new RegExp(expectedMarker))).length).toBeGreaterThan(0);
      } else {
        expect(await screen.findByText(new RegExp(expectedMarker))).toBeInTheDocument();
      }
      await act(async () => {
        if (outcome === "success") oldPart.resolve(
          bundleResponse(deferredPath, 1, "A-OLD"),
        );
        else if (outcome === "api-error") oldPart.resolve(json({ detail: { code: "OLD_BUNDLE" } }, 409));
        else oldPart.reject(new Error("old bundle rejection"));
        try { await oldPart.promise; } catch { /* expected */ }
      });
      if (deferredPath === "eligibility") {
        expect(screen.getAllByText(new RegExp(expectedMarker)).length).toBeGreaterThan(0);
      } else {
        expect(screen.getByText(new RegExp(expectedMarker))).toBeInTheDocument();
      }
      expect(screen.queryByText(/A-OLD-(detail|history|matched-rules|eligibility)/)).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument();
    },
  );

  it.each(
    (["A-B", "A-B-A"] as const).flatMap((transition) =>
      (["success", "rejected", "api-error"] as const).map(
        (outcome) => [transition, outcome] as const,
      ),
    ),
  )(
    "%s stale target-list %s cannot replace the current generation or finally state",
    async (transition, outcome) => {
      const oldA = deferred<Response>();
      let aCalls = 0;
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const match = url.match(/\/api\/clients\/(\d+)$/);
        if (match) return json(client(Number(match[1])));
        if (url.endsWith("/m04/targets")) {
          const id = url.includes("/clients/2/") ? 2 : 1;
          if (id === 1) aCalls += 1;
          if (id === 1 && aCalls === 1) return oldA.promise;
          return json([{
            ...target(id),
            intake_id: id === 1 ? "A-new-intake" : "B-current-intake",
            m02_lifecycle_status: id === 1 ? "A-new" : "B-current",
          }]);
        }
        throw new Error(`unexpected ${url}`);
      }));
      renderNavigable();
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      expect(await screen.findByRole("button", { name: /B-current-intake/ })).toBeInTheDocument();
      if (transition === "A-B-A") {
        fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
        expect(await screen.findByRole("button", { name: /A-new-intake/ })).toBeInTheDocument();
      }
      await act(async () => {
        if (outcome === "success") oldA.resolve(json([{ ...target(1), intake_id: "A-old-intake" }]));
        else if (outcome === "api-error") oldA.resolve(json({ detail: { code: "OLD" } }, 409));
        else oldA.reject(new Error("old rejection"));
        try { await oldA.promise; } catch { /* expected */ }
      });
      expect(screen.queryByText(/A-old-intake/)).not.toBeInTheDocument();
      expect(screen.getByRole("button", {
        name: transition === "A-B" ? /B-current-intake/ : /A-new-intake/,
      })).toBeInTheDocument();
      await waitFor(() => expect(screen.queryByText(/טוען את סיווג M04/)).not.toBeInTheDocument());
    },
  );

  it.each(
    ACTION_CASES.flatMap((actionCase) =>
      (["A-B", "A-B-A"] as const).flatMap((transition) =>
        (["success", "rejected", "api-error"] as const).map(
          (outcome) => [actionCase.action, actionCase, transition, outcome] as const,
        ),
      ),
    ),
  )(
    "%s mutation %s stale %s preserves current ownership and launches zero refreshes",
    async (_actionName, actionCase, transition, outcome) => {
      const oldMutation = deferred<Response>();
      const currentMutation = deferred<Response>();
      let mutationCalls = 0;
      let detailReads = 0;
      const currentRevision = actionCase.state
        ? revision(actionCase.state, actionCase.state === "under_review" ? 1 : 2)
        : null;
      const currentTarget = (id: number) => target(
        id,
        currentRevision,
        "revalidation" in actionCase && actionCase.revalidation
          ? "m04_revalidation_required" : undefined,
      );
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
        if (clientMatch) return json(client(Number(clientMatch[1])));
        const id = url.includes("/clients/2/") ? 2 : 1;
        if (url.endsWith("/m04/targets")) return json([currentTarget(id)]);
        if (url.endsWith(actionCase.endpoint)) {
          mutationCalls += 1;
          return mutationCalls === 1 ? oldMutation.promise : currentMutation.promise;
        }
        if (url.endsWith(`/manual-${id}`)) {
          detailReads += 1;
          return json(currentTarget(id));
        }
        if (url.endsWith("/history")) return json(currentRevision
          ? currentRevision.revision_id === "r-1"
            ? [currentRevision] : [revision("under_review", 1), currentRevision]
          : []);
        if (url.endsWith("/matched-rules")) return json([]);
        if (url.endsWith("/eligibility")) return json(currentTarget(id).eligibility);
        throw new Error(`unexpected ${url}`);
      }));
      const prepareAndClick = async (id: number) => {
        fireEvent.click(await screen.findByRole("button", { name: new RegExp(`manual-${id}`) }));
        const button = await screen.findByRole("button", { name: actionCase.button });
        if ("reason" in actionCase && actionCase.reason) {
          fireEvent.change(screen.getByLabelText("הסבר"), {
            target: { value: `current ${actionCase.action} explanation` },
          });
        }
        if (actionCase.action === "override") {
          fireEvent.change(screen.getByLabelText("פרשנות"), {
            target: { value: "pension" },
          });
        }
        if (actionCase.action === "undo") {
          fireEvent.change(screen.getByLabelText("גרסה היסטורית לביטול"), {
            target: { value: "r-1" },
          });
        }
        fireEvent.click(button);
      };

      renderNavigable();
      await prepareAndClick(1);
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      if (transition === "A-B-A") {
        await screen.findByRole("button", { name: /manual-2/ });
        fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
        await prepareAndClick(1);
      } else {
        await prepareAndClick(2);
      }
      const readsBeforeOldSettlement = detailReads;
      await act(async () => {
        if (outcome === "success") oldMutation.resolve(json({ old: true }, 201));
        else if (outcome === "api-error") oldMutation.resolve(json({ detail: { code: "OLD_MUTATION" } }, 409));
        else oldMutation.reject(new Error("old mutation rejection"));
        try { await oldMutation.promise; } catch { /* expected */ }
      });
      expect(detailReads).toBe(readsBeforeOldSettlement);
      expect(screen.getByRole("group", { name: "פעולות זמינות" })).toBeDisabled();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByText(new RegExp(`גוף מנהל: Provider ${transition === "A-B" ? 2 : 1}`))).toBeInTheDocument();

      await act(async () => { currentMutation.resolve(json({ current: true }, 201)); });
      await waitFor(() => expect(detailReads).toBeGreaterThan(readsBeforeOldSettlement));
      await waitFor(() => expect(screen.getByRole("group", { name: "פעולות זמינות" })).not.toBeDisabled());
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(mutationCalls).toBe(2);
    },
  );
});
