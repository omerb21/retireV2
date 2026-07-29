import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { M03SourceReviewScreen } from "./M03SourceReviewScreen";

const json = (body: unknown, status = 200): Response => ({
  ok: status < 400, status, statusText: status < 400 ? "OK" : "Error",
  headers: { get: () => "application/json" }, json: async () => body,
  text: async () => JSON.stringify(body)
}) as unknown as Response;
const client = (status: "delivered" | "archived" = "delivered") => ({
  client_id: 1, full_name: "One", id_number: "001", birth_date: null,
  file_status: "file_created", professional_identification_status: "identification_incomplete",
  m01_case: { lifecycle_status: status }
});
const revision = (state: "under_review" | "accepted", sequence: number) => ({
  revision_id: `r-${sequence}`, revision_sequence: sequence,
  predecessor_revision_id: sequence === 1 ? null : `r-${sequence - 1}`,
  state, reason: sequence === 1 ? null : "reviewed", actor: "system:m03-review-ui:M03 review workflow",
  actor_is_authentication: false, decided_at: "2026-07-29T00:00:00Z"
});
const target = (current: ReturnType<typeof revision> | null = null) => ({
  client_id: 1, intake_id: "manual-1", target_kind: "manual_record_review",
  m02_lifecycle_status: "accepted_for_review", source_id: null, blob_id: null,
  sha256_checksum: null, current_revision: current,
  accepted_revision_id: current?.state === "accepted" ? current.revision_id : null,
  eligible: current?.state === "accepted", exclusion_reason: current ? `review_${current.state}` : "review_not_started",
  eligibility_meaning: "reviewed evidence may be consumed by a separately authorized downstream transformation"
});

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

function renderPage() {
  return render(<MemoryRouter initialEntries={["/clients/1/source-review"]}>
    <Routes><Route path="/clients/:clientId/source-review" element={<M03SourceReviewScreen />} /></Routes>
  </MemoryRouter>);
}

function NavigationControls() {
  const navigate = useNavigate();
  return <>
    <button type="button" onClick={() => navigate("/clients/1/source-review")}>Navigate A</button>
    <button type="button" onClick={() => navigate("/clients/2/source-review")}>Navigate B</button>
  </>;
}

function renderNavigablePage() {
  return render(<MemoryRouter initialEntries={["/clients/1/source-review"]}>
    <NavigationControls />
    <Routes><Route path="/clients/:clientId/source-review" element={<M03SourceReviewScreen />} /></Routes>
  </MemoryRouter>);
}

afterEach(() => vi.restoreAllMocks());

describe("M03SourceReviewScreen", () => {
  it("requires explicit start and presents manual targets without false provenance", async () => {
    let current: ReturnType<typeof revision> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m03/candidates")) return json([target(current)]);
      if (url.endsWith("/m03/targets/manual-1/start")) { current = revision("under_review", 1); return json(current, 201); }
      if (url.endsWith("/m03/targets/manual-1/history")) return json(current ? [current] : []);
      if (url.endsWith("/m03/targets/manual-1/annotations")) return json([]);
      if (url.endsWith("/m03/targets/manual-1/eligibility")) return json(target(current));
      if (url.endsWith("/m03/targets/manual-1")) return json(target(current));
      throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
    expect(await screen.findByText(/no external source, blob, or checksum evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/not eligible — review_not_started/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start review" }));
    expect(await screen.findByText(/#1 under_review/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept review" })).toBeInTheDocument();
  });

  it("disables every mutation in an archived case while retaining history", async () => {
    const current = revision("accepted", 2);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client("archived"));
      if (url.endsWith("/m03/candidates")) return json([target(current)]);
      if (url.endsWith("/history")) return json([revision("under_review", 1), current]);
      if (url.endsWith("/annotations")) return json([]);
      if (url.endsWith("/eligibility")) return json(target(current));
      if (url.endsWith("/m03/targets/manual-1")) return json(target(current));
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    expect(await screen.findByText(/Archived case/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Manual record/ }));
    await screen.findByText(/#2 accepted/);
    expect(screen.getByRole("button", { name: "Reopen review" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save annotation" })).toBeDisabled();
  });

  it("creates annotation supersession without replacing the retained annotation", async () => {
    const current = revision("accepted", 2);
    let notes = [{
      annotation_id: "a-1", review_revision_id: current.revision_id, intake_id: "manual-1",
      source_id: null, topic: "Original", note: "Retained note", reason: "Initial context",
      actor: "system:m03-review-ui:M03 review workflow", actor_is_authentication: false as const,
      supersedes_annotation_id: null, created_at: "2026-07-29T00:00:00Z",
    }];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m03/candidates")) return json([target(current)]);
      if (url.endsWith("/history")) return json([revision("under_review", 1), current]);
      if (url.endsWith("/eligibility")) return json(target(current));
      if (url.endsWith("/annotations") && init?.method === "POST") {
        const payload = JSON.parse(String(init.body));
        notes = [...notes, {
          annotation_id: "a-2", review_revision_id: payload.review_revision_id,
          intake_id: "manual-1", source_id: null, topic: payload.topic, note: payload.note,
          reason: payload.reason, actor: "system:m03-review-ui:M03 review workflow",
          actor_is_authentication: false, supersedes_annotation_id: payload.supersedes_annotation_id,
          created_at: "2026-07-29T00:00:01Z",
        }];
        return json(notes[1], 201);
      }
      if (url.endsWith("/annotations")) return json(notes);
      if (url.endsWith("/m03/targets/manual-1")) return json(target(current));
      throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
    }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Manual record/ }));
    await screen.findByText(/Retained note/);
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "Updated" } });
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "New note" } });
    fireEvent.change(screen.getAllByLabelText("Reason")[0] ?? screen.getByLabelText("Reason"), { target: { value: "Correction context" } });
    fireEvent.change(screen.getByLabelText(/Supersede existing annotation/), { target: { value: "a-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save annotation" }));
    expect(await screen.findByText(/New note.*supersedes a-1/)).toBeInTheDocument();
    expect(screen.getByText(/Retained note/)).toBeInTheDocument();
    expect(screen.getByText(/eligible for a separately authorized/)).toBeInTheDocument();
  });

  it("opens retained review history after a target leaves the candidate list", async () => {
    const current = revision("accepted", 2);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/clients/1")) return json(client());
      if (url.endsWith("/m03/candidates")) return json([]);
      if (url.endsWith("/history")) return json([revision("under_review", 1), current]);
      if (url.endsWith("/annotations")) return json([]);
      if (url.endsWith("/eligibility")) return json({
        ...target(current), m02_lifecycle_status: "superseded", eligible: false,
        accepted_revision_id: null, exclusion_reason: "m02_superseded",
      });
      if (url.endsWith("/m03/targets/manual-1")) return json({
        ...target(current), m02_lifecycle_status: "superseded",
      });
      throw new Error(`unexpected ${url}`);
    }));
    renderPage();
    expect(await screen.findByText(/No M02 records currently accepted/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Open retained review by M02 intake ID/), {
      target: { value: "manual-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open retained review" }));
    expect(await screen.findByText(/#2 accepted/)).toBeInTheDocument();
    expect(screen.getByText(/not eligible.*m02_superseded/)).toBeInTheDocument();
  });

  it("rejects stale candidate errors and finally across an immediate A-B-A transition", async () => {
    const firstCandidates = deferred<Response>();
    let aCandidateCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
      if (clientMatch) return json({ ...client(), client_id: Number(clientMatch[1]), full_name: `Client ${clientMatch[1]}` });
      if (url.endsWith("/api/clients/1/m03/candidates")) {
        aCandidateCalls += 1;
        return aCandidateCalls === 1 ? firstCandidates.promise : json([target()]);
      }
      if (url.endsWith("/api/clients/2/m03/candidates")) {
        return json([{ ...target(), client_id: 2, intake_id: "manual-2" }]);
      }
      throw new Error(`unexpected ${url}`);
    }));
    renderNavigablePage();
    fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
    expect(await screen.findByRole("button", { name: /manual-2/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
    expect(await screen.findByRole("button", { name: /manual-1/ })).toBeInTheDocument();
    firstCandidates.reject(new Error("stale candidate failure"));
    await waitFor(() => {
      expect(screen.queryByText(/stale candidate failure/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Loading M03 review/)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /manual-1/ })).toBeInTheDocument();
    });
  });

  it("protects detail, history, annotations, and eligibility from stale A-B-A success", async () => {
    const oldDetail = deferred<Response>();
    const oldHistory = deferred<Response>();
    const oldAnnotations = deferred<Response>();
    const oldEligibility = deferred<Response>();
    let aCandidateLoads = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
      if (clientMatch) return json({ ...client(), client_id: Number(clientMatch[1]) });
      if (url.endsWith("/m03/candidates")) {
        const id = url.includes("/clients/2/") ? 2 : 1;
        if (id === 1) aCandidateLoads += 1;
        return json([{ ...target(), client_id: id, intake_id: `manual-${id}` }]);
      }
      if (url.includes("/clients/1/m03/targets/manual-1")) {
        if (aCandidateLoads === 1) {
          if (url.endsWith("/history")) return oldHistory.promise;
          if (url.endsWith("/annotations")) return oldAnnotations.promise;
          if (url.endsWith("/eligibility")) return oldEligibility.promise;
          return oldDetail.promise;
        }
        const accepted = revision("accepted", 2);
        if (url.endsWith("/history")) return json([revision("under_review", 1), accepted]);
        if (url.endsWith("/annotations")) return json([]);
        return json(target(accepted));
      }
      throw new Error(`unexpected ${url}`);
    }));
    renderNavigablePage();
    fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
    await screen.findByRole("button", { name: /manual-2/ });
    fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
    fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
    expect(await screen.findByText(/#2 accepted/)).toBeInTheDocument();
    oldDetail.resolve(json(target()));
    oldHistory.resolve(json([]));
    oldAnnotations.resolve(json([{
      annotation_id: "stale", review_revision_id: "stale", intake_id: "manual-1",
      source_id: null, topic: "stale", note: "stale", reason: "stale", actor: "stale",
      actor_is_authentication: false, supersedes_annotation_id: null, created_at: "2026-07-29T00:00:00Z",
    }]));
    oldEligibility.resolve(json(target()));
    await waitFor(() => {
      expect(screen.getByText(/#2 accepted/)).toBeInTheDocument();
      expect(screen.queryByText(/^stale: stale/)).not.toBeInTheDocument();
      expect(screen.getByText(/eligible for a separately authorized/)).toBeInTheDocument();
    });
  });

  it.each(["start", "accept", "reject", "reopen", "annotation", "supersession"] as const)(
    "protects %s and its post-mutation refresh from stale A-B-A completion",
    async (action) => {
      const operation = deferred<Response>();
      const current = action === "start" ? null
        : action === "accept" || action === "reject" ? revision("under_review", 1)
          : revision("accepted", 2);
      const existingNote = {
        annotation_id: "a-1", review_revision_id: current?.revision_id ?? "r-1",
        intake_id: "manual-1", source_id: null, topic: "Existing", note: "Existing note",
        reason: "Existing reason", actor: "system:m03-review-ui:M03 review workflow",
        actor_is_authentication: false, supersedes_annotation_id: null,
        created_at: "2026-07-29T00:00:00Z",
      };
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
        if (clientMatch) return json({ ...client(), client_id: Number(clientMatch[1]) });
        if (url.endsWith("/m03/candidates")) {
          const id = url.includes("/clients/2/") ? 2 : 1;
          return json([{ ...target(current), client_id: id, intake_id: `manual-${id}` }]);
        }
        if (url.includes("/clients/1/m03/targets/manual-1")) {
          const isMutation = init?.method === "POST";
          if (isMutation) return operation.promise;
          if (url.endsWith("/history")) return json(current ? [current] : []);
          if (url.endsWith("/annotations")) return json(action === "supersession" ? [existingNote] : []);
          return json(target(current));
        }
        throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
      }));
      renderNavigablePage();
      fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      await screen.findByText(/Review target/);
      if (action === "start") {
        fireEvent.click(screen.getByRole("button", { name: "Start review" }));
      } else if (action === "accept" || action === "reject" || action === "reopen") {
        fireEvent.change(screen.getByLabelText(/Decision\/reopen reason/), { target: { value: "reason" } });
        const label = action === "accept" ? "Accept review" : action === "reject" ? "Reject review" : "Reopen review";
        fireEvent.click(screen.getByRole("button", { name: label }));
      } else {
        fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "Topic" } });
        fireEvent.change(screen.getByLabelText("Note"), { target: { value: "Note" } });
        fireEvent.change(screen.getAllByLabelText("Reason")[0] ?? screen.getByLabelText("Reason"), { target: { value: "Reason" } });
        if (action === "supersession") {
          fireEvent.change(screen.getByLabelText(/Supersede existing annotation/), { target: { value: "a-1" } });
        }
        fireEvent.click(screen.getByRole("button", { name: "Save annotation" }));
      }
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      await screen.findByRole("button", { name: /manual-2/ });
      fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
      await screen.findByRole("button", { name: /manual-1/ });
      operation.resolve(json(current ?? revision("under_review", 1), 201));
      await waitFor(() => {
        expect(screen.queryByText(/Review target/)).not.toBeInTheDocument();
        expect(screen.queryByText(/Loading M03 review/)).not.toBeInTheDocument();
        expect(screen.queryByText(/M03 request failed/)).not.toBeInTheDocument();
      });
    },
  );
});
