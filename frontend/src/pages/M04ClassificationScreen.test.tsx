import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
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
const component = (interpretation: "pension" | "capital" | "unresolved" = "unresolved") => ({
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
  action = state === "under_review" ? "start" : state,
) => ({
  revision_id: `r-${sequence}`,
  revision_sequence: sequence,
  predecessor_revision_id: sequence === 1 ? null : `r-${sequence - 1}`,
  historical_revision_id: null,
  state,
  action_type: action,
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
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
    expect(await screen.findByText(/no external source\/blob\/checksum evidence/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start classification" }));
    expect(await screen.findByText(/#1 start.*under_review/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview exact rules" }));
    expect(await screen.findByText(/Catalogue: m04-rules-v1/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create proposal" }));
    expect(await screen.findByRole("button", { name: "Accept proposal" })).toBeInTheDocument();
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
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
    expect(await screen.findByText(/Archived case: M04 is read-only/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Lifecycle actions" })).toBeDisabled();
    expect(screen.getByText(/#4 accept.*accepted/)).toBeInTheDocument();
  });

  it.each([
    ["under_review", ["Preview exact rules", "Create proposal", "Mark unresolved"]],
    ["proposed", ["Accept proposal", "Reject proposal", "Create override proposal", "Create undo proposal"]],
    ["accepted", ["Reopen classification", "Create override proposal", "Create undo proposal"]],
    ["unresolved", ["Reopen classification", "Create override proposal", "Create undo proposal"]],
    ["rejected", ["Reopen classification", "Create override proposal", "Create undo proposal"]],
  ] as const)("exposes the bounded action matrix for %s", async (state, buttons) => {
    const current = revision(state, 3, state);
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
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
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
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
    expect(await screen.findByRole("button", { name: "Start revalidation" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reopen classification" })).not.toBeInTheDocument();
  });

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
      await waitFor(() => expect(screen.queryByText(/Loading M04/)).not.toBeInTheDocument());
    },
  );

  it.each(["success", "rejected", "api-error"] as const)(
    "stale mutation %s launches zero follow-up refreshes",
    async (outcome) => {
    const mutation = deferred<Response>();
    let aTargetReads = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
      if (clientMatch) return json(client(Number(clientMatch[1])));
      const id = url.includes("/clients/2/") ? 2 : 1;
      if (url.endsWith("/m04/targets")) return json([target(id)]);
      if (url.endsWith("/manual-1/start")) return mutation.promise;
      if (url.endsWith(`/manual-${id}`)) {
        if (id === 1) aTargetReads += 1;
        return json(target(id));
      }
      if (url.endsWith("/history") || url.endsWith("/matched-rules")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(id).eligibility);
      throw new Error(`unexpected ${url}`);
    }));
    renderNavigable();
    fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
    await screen.findByRole("button", { name: "Start classification" });
    const readsBefore = aTargetReads;
    fireEvent.click(screen.getByRole("button", { name: "Start classification" }));
    fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
    expect(await screen.findByRole("button", { name: /manual-2/ })).toBeInTheDocument();
    await act(async () => {
      if (outcome === "success") mutation.resolve(json(revision("under_review", 1), 201));
      else if (outcome === "api-error") mutation.resolve(json({ detail: { code: "OLD" } }, 409));
      else mutation.reject(new Error("old mutation rejection"));
      try { await mutation.promise; } catch { /* expected */ }
    });
    await waitFor(() => expect(aTargetReads).toBe(readsBefore));
    expect(screen.queryByText(/#1 start/)).not.toBeInTheDocument();
    },
  );
});
