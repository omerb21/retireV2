import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
const targetFor = (
  clientId: number,
  intakeId: string,
  current: ReturnType<typeof revision> | null,
  label: string,
) => ({
  ...target(current),
  client_id: clientId,
  intake_id: intakeId,
  m02_lifecycle_status: label,
});
const annotationFor = (label: string, intakeId: string) => ({
  annotation_id: `${label}-annotation-id`,
  review_revision_id: `${label}-revision-id`,
  intake_id: intakeId,
  source_id: null,
  topic: `${label}-annotation-topic`,
  note: `${label}-annotation-note`,
  reason: `${label}-annotation-reason`,
  actor: "system:m03-review-ui:M03 review workflow",
  actor_is_authentication: false as const,
  supersedes_annotation_id: null,
  created_at: "2026-07-29T00:00:00Z",
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
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    expect(await screen.findByText(/אין קובץ מקור חיצוני או checksum/i)).toBeInTheDocument();
    expect(screen.getByText(/הבדיקה טרם התחילה/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "התחלת בדיקה" }));
    expect(await screen.findByText(/#1 בבדיקה/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "אישור הבדיקה" })).toBeInTheDocument();
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
    expect(await screen.findByText(/התיק בארכיון/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /רשומה ידנית/ }));
    await screen.findByText(/#2 אושר/);
    expect(screen.getByRole("button", { name: "פתיחת הבדיקה מחדש" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "שמירת הערה" })).toBeDisabled();
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
    fireEvent.click(await screen.findByRole("button", { name: /רשומה ידנית/ }));
    await screen.findByText(/Retained note/);
    fireEvent.change(screen.getByLabelText("נושא"), { target: { value: "Updated" } });
    fireEvent.change(screen.getByLabelText("הערה"), { target: { value: "New note" } });
    fireEvent.change(screen.getAllByLabelText("נימוק")[0] ?? screen.getByLabelText("נימוק"), { target: { value: "Correction context" } });
    fireEvent.change(screen.getByLabelText(/החלפת הערה קיימת/), { target: { value: "a-1" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת הערה" }));
    expect(await screen.findByText(/New note.*מחליפה את a-1/)).toBeInTheDocument();
    expect(screen.getByText(/Retained note/)).toBeInTheDocument();
    expect(screen.getByText(/הבדיקה אושרה והיא עדכנית/)).toBeInTheDocument();
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
    expect(await screen.findByText(/אין כרגע רשומות M02 שהתקבלו לבדיקה/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/פתיחת בדיקה שמורה לפי מזהה קליטת M02/), {
      target: { value: "manual-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "פתיחת בדיקה שמורה" }));
    expect(await screen.findByText(/#2 אושר/)).toBeInTheDocument();
    expect(screen.getByText(/רשומת M02 הוחלפה ואינה עדכנית/)).toBeInTheDocument();
  });

  it.each(
    (["candidates", "detail", "history", "annotations", "eligibility"] as const)
      .flatMap((readPath) => (["A-B", "A-B-A"] as const)
        .flatMap((transition) => (["success", "rejected", "api-error"] as const)
          .map((outcome) => [readPath, transition, outcome] as const))),
  )(
    "read race: %s A-old %s during %s preserves current generation and finally ownership",
    async (readPath, transition, outcome) => {
      const oldRead = deferred<Response>();
      const currentRead = deferred<Response>();
      let aCandidateCalls = 0;
      const currentLabel = transition === "A-B" ? "B-current" : "A-new";
      const currentClientId = transition === "A-B" ? 2 : 1;
      const currentIntakeId = transition === "A-B" ? "b-current-intake" : "a-new-intake";

      const pathFromUrl = (url: string) => url.endsWith("/history") ? "history"
        : url.endsWith("/annotations") ? "annotations"
          : url.endsWith("/eligibility") ? "eligibility" : "detail";
      const payloadFor = (
        path: "detail" | "history" | "annotations" | "eligibility",
        label: string,
        clientId: number,
        intakeId: string,
      ) => {
        const accepted = {
          ...revision("accepted", 2),
          reason: `${label}-history`,
        };
        if (path === "history") return [revision("under_review", 1), accepted];
        if (path === "annotations") return [annotationFor(label, intakeId)];
        if (path === "eligibility") {
          return {
            ...targetFor(clientId, intakeId, accepted, label),
            eligible: label !== "A-old",
            accepted_revision_id: label !== "A-old" ? accepted.revision_id : null,
            exclusion_reason: label === "A-old" ? "A-old-exclusion" : null,
          };
        }
        return targetFor(clientId, intakeId, accepted, label);
      };

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
        if (clientMatch) {
          const id = Number(clientMatch[1]);
          return json({ ...client(), client_id: id, full_name: `Client ${id}` });
        }
        if (url.endsWith("/m03/candidates")) {
          const id = url.includes("/clients/2/") ? 2 : 1;
          if (id === 1) aCandidateCalls += 1;
          if (readPath === "candidates") {
            if (id === 1 && aCandidateCalls === 1) return oldRead.promise;
            if (
              (transition === "A-B" && id === 2)
              || (transition === "A-B-A" && id === 1 && aCandidateCalls === 2)
            ) return currentRead.promise;
          }
          const label = id === 2 ? "B-current" : aCandidateCalls > 1 ? "A-new" : "A-old";
          const intakeId = id === 2 ? "b-current-intake" : aCandidateCalls > 1 ? "a-new-intake" : "a-old-intake";
          return json([targetFor(id, intakeId, null, label)]);
        }
        const targetMatch = url.match(/\/clients\/(\d+)\/m03\/targets\/([^/]+)/);
        if (targetMatch) {
          const id = Number(targetMatch[1]);
          const intakeId = decodeURIComponent(targetMatch[2]);
          const path = pathFromUrl(url);
          const label = intakeId === "a-old-intake" ? "A-old"
            : intakeId === "b-current-intake" ? "B-current" : "A-new";
          if (path === readPath && label === "A-old") return oldRead.promise;
          if (path === readPath && label === currentLabel) return currentRead.promise;
          return json(payloadFor(path, label, id, intakeId));
        }
        throw new Error(`unexpected ${url}`);
      }));

      renderNavigablePage();
      if (readPath !== "candidates") {
        fireEvent.click(await screen.findByRole("button", { name: /a-old-intake/ }));
      }
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      if (transition === "A-B-A") {
        await screen.findByRole("button", { name: /b-current-intake/ });
        fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
      }
      if (readPath !== "candidates") {
        fireEvent.click(await screen.findByRole("button", { name: new RegExp(currentIntakeId) }));
      }
      expect(await screen.findByText(/טוען את בדיקת M03/)).toBeInTheDocument();

      await act(async () => {
        if (outcome === "success") {
          const oldBody = readPath === "candidates"
            ? [targetFor(1, "A-old-stale-intake", null, "A-old")]
            : payloadFor(readPath, "A-old", 1, "a-old-intake");
          oldRead.resolve(json(oldBody));
        } else if (outcome === "api-error") {
          oldRead.resolve(json({ detail: { code: "A_OLD_API_ERROR" } }, 500));
        } else {
          oldRead.reject(new Error("A-old rejected promise"));
        }
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(screen.getByText(/טוען את בדיקת M03/)).toBeInTheDocument();
      expect(screen.queryByText(/A-old|A_OLD_API_ERROR|rejected promise/)).not.toBeInTheDocument();

      await act(async () => {
        const currentBody = readPath === "candidates"
          ? [targetFor(currentClientId, currentIntakeId, null, currentLabel)]
          : payloadFor(readPath, currentLabel, currentClientId, currentIntakeId);
        currentRead.resolve(json(currentBody));
        await Promise.resolve();
        await Promise.resolve();
      });

      if (readPath === "candidates") {
        expect(await screen.findByRole("button", { name: new RegExp(currentIntakeId) })).toBeEnabled();
      } else {
        expect(await screen.findByText(new RegExp(`${currentLabel}-history`))).toBeInTheDocument();
        expect(screen.getByText(new RegExp(`${currentLabel}-annotation-note`))).toBeInTheDocument();
        expect(screen.getByText(/הבדיקה אושרה והיא עדכנית/)).toBeInTheDocument();
        expect(screen.getByLabelText(/נימוק להחלטה או לפתיחה מחדש/)).toBeEnabled();
        expect(screen.getByLabelText(/החלפת הערה קיימת/)).toBeEnabled();
      }
      expect(screen.queryByText(/A-old|A_OLD_API_ERROR|rejected promise/)).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
      expect(screen.queryByRole("pre")).not.toBeInTheDocument();
    },
  );

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
      expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /manual-1/ })).toBeInTheDocument();
    });
  });

  it("rejects stale candidate success after returning to the original client", async () => {
    const firstCandidates = deferred<Response>();
    let aCandidateCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
      if (clientMatch) return json({ ...client(), client_id: Number(clientMatch[1]) });
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
    await screen.findByRole("button", { name: /manual-2/ });
    fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
    await screen.findByRole("button", { name: /manual-1/ });
    firstCandidates.resolve(json([{ ...target(), intake_id: "stale-candidate" }]));
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /stale-candidate/ })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /manual-1/ })).toBeEnabled();
      expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
    });
  });

  it.each([
    ["detail", "success"],
    ["detail", "error"],
    ["history", "success"],
    ["history", "error"],
    ["annotations", "success"],
    ["annotations", "error"],
    ["eligibility", "success"],
    ["eligibility", "error"],
  ] as const)("protects stale %s %s independently", async (readPath, outcome) => {
    const staleRead = deferred<Response>();
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
        const path = url.endsWith("/history") ? "history"
          : url.endsWith("/annotations") ? "annotations"
            : url.endsWith("/eligibility") ? "eligibility" : "detail";
        if (aCandidateLoads === 1 && path === readPath) return staleRead.promise;
        const accepted = aCandidateLoads > 1 ? revision("accepted", 2) : null;
        if (path === "history") return json(accepted ? [revision("under_review", 1), accepted] : []);
        if (path === "annotations") return json([]);
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
    expect(await screen.findByText(/#2 אושר/)).toBeInTheDocument();
    if (outcome === "success") {
      const response = readPath === "history" || readPath === "annotations"
        ? json([])
        : json(target());
      staleRead.resolve(response);
    } else {
      staleRead.resolve(json({ detail: "stale read error" }, 500));
    }
    await waitFor(() => {
      expect(screen.getByText(/#2 אושר/)).toBeInTheDocument();
      expect(screen.getByText(/הבדיקה אושרה והיא עדכנית/)).toBeInTheDocument();
      expect(screen.queryByText(/stale read error/)).not.toBeInTheDocument();
      expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
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
    expect(await screen.findByText(/#2 אושר/)).toBeInTheDocument();
    oldDetail.resolve(json(target()));
    oldHistory.resolve(json([]));
    oldAnnotations.resolve(json([{
      annotation_id: "stale", review_revision_id: "stale", intake_id: "manual-1",
      source_id: null, topic: "stale", note: "stale", reason: "stale", actor: "stale",
      actor_is_authentication: false, supersedes_annotation_id: null, created_at: "2026-07-29T00:00:00Z",
    }]));
    oldEligibility.resolve(json(target()));
    await waitFor(() => {
      expect(screen.getByText(/#2 אושר/)).toBeInTheDocument();
      expect(screen.queryByText(/^stale: stale/)).not.toBeInTheDocument();
      expect(screen.getByText(/הבדיקה אושרה והיא עדכנית/)).toBeInTheDocument();
    });
  });

  it.each(
    (["start", "accept", "reject", "reopen", "annotation", "supersession"] as const)
      .flatMap((action) => (["A-B", "A-B-A"] as const)
        .flatMap((transition) => (["success", "rejected", "api-error"] as const)
          .map((outcome) => [action, outcome, transition] as const))),
  )(
    "protects %s stale %s across %s without launching refresh",
    async (action, outcome, transition) => {
      const operation = deferred<Response>();
      let targetReadCalls = 0;
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
          targetReadCalls += 1;
          if (url.endsWith("/history")) return json(current ? [current] : []);
          if (url.endsWith("/annotations")) return json(action === "supersession" ? [existingNote] : []);
          return json(target(current));
        }
        throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
      }));
      renderNavigablePage();
      fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
      await screen.findByText(/פרטי הרשומה הנבדקת/);
      if (action === "start") {
        fireEvent.click(screen.getByRole("button", { name: "התחלת בדיקה" }));
      } else if (action === "accept" || action === "reject" || action === "reopen") {
        fireEvent.change(screen.getByLabelText(/נימוק להחלטה או לפתיחה מחדש/), { target: { value: "reason" } });
        const label = action === "accept" ? "אישור הבדיקה" : action === "reject" ? "דחיית הבדיקה" : "פתיחת הבדיקה מחדש";
        fireEvent.click(screen.getByRole("button", { name: label }));
      } else {
        fireEvent.change(screen.getByLabelText("נושא"), { target: { value: "Topic" } });
        fireEvent.change(screen.getByLabelText("הערה"), { target: { value: "Note" } });
        fireEvent.change(screen.getAllByLabelText("נימוק")[0] ?? screen.getByLabelText("נימוק"), { target: { value: "Reason" } });
        if (action === "supersession") {
          fireEvent.change(screen.getByLabelText(/החלפת הערה קיימת/), { target: { value: "a-1" } });
        }
        fireEvent.click(screen.getByRole("button", { name: "שמירת הערה" }));
      }
      fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
      await screen.findByRole("button", { name: /manual-2/ });
      if (transition === "A-B-A") {
        fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
        await screen.findByRole("button", { name: /manual-1/ });
      }
      if (outcome === "success") {
        operation.resolve(json(current ?? revision("under_review", 1), 201));
      } else if (outcome === "api-error") {
        operation.resolve(json({ detail: "stale mutation API error" }, 409));
      } else {
        operation.reject(new Error("stale mutation rejection"));
      }
      await waitFor(() => {
        expect(targetReadCalls).toBe(4);
        expect(screen.queryByText(/פרטי הרשומה הנבדקת/)).not.toBeInTheDocument();
        expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
        expect(screen.queryByText(/M03 request failed/)).not.toBeInTheDocument();
        expect(screen.queryByText(/stale mutation/)).not.toBeInTheDocument();
        const expectedCandidate = transition === "A-B-A" ? /manual-1/ : /manual-2/;
        expect(screen.getByRole("button", { name: expectedCandidate })).toBeEnabled();
      });
    },
  );

  it("keeps a new-context refresh independent when the original A mutation resolves after return", async () => {
    const oldMutation = deferred<Response>();
    const newMutation = deferred<Response>();
    let mutationCalls = 0;
    let targetReadCalls = 0;
    let current: ReturnType<typeof revision> | null = null;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const clientMatch = url.match(/\/api\/clients\/(\d+)$/);
      if (clientMatch) return json({ ...client(), client_id: Number(clientMatch[1]) });
      if (url.endsWith("/m03/candidates")) {
        const id = url.includes("/clients/2/") ? 2 : 1;
        return json([{ ...target(current), client_id: id, intake_id: `manual-${id}` }]);
      }
      if (url.includes("/clients/1/m03/targets/manual-1")) {
        if (init?.method === "POST") {
          mutationCalls += 1;
          return mutationCalls === 1 ? oldMutation.promise : newMutation.promise;
        }
        targetReadCalls += 1;
        if (url.endsWith("/history")) return json(current ? [current] : []);
        if (url.endsWith("/annotations")) return json([]);
        return json(target(current));
      }
      throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
    }));
    renderNavigablePage();
    fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
    await screen.findByText(/פרטי הרשומה הנבדקת/);
    fireEvent.click(screen.getByRole("button", { name: "התחלת בדיקה" }));
    fireEvent.click(screen.getByRole("button", { name: "Navigate B" }));
    await screen.findByRole("button", { name: /manual-2/ });
    fireEvent.click(screen.getByRole("button", { name: "Navigate A" }));
    fireEvent.click(await screen.findByRole("button", { name: /manual-1/ }));
    await screen.findByText(/פרטי הרשומה הנבדקת/);
    fireEvent.click(screen.getByRole("button", { name: "התחלת בדיקה" }));

    oldMutation.resolve(json(revision("under_review", 1), 201));
    await waitFor(() => {
      expect(targetReadCalls).toBe(8);
      expect(screen.getByRole("button", { name: "התחלת בדיקה" })).toBeDisabled();
    });

    current = revision("under_review", 1);
    newMutation.resolve(json(current, 201));
    await waitFor(() => {
      expect(targetReadCalls).toBe(12);
      expect(screen.getByText(/#1 בבדיקה/)).toBeInTheDocument();
      expect(screen.getByLabelText(/נימוק להחלטה או לפתיחה מחדש/)).toBeEnabled();
      expect(screen.getByRole("button", { name: "אישור הבדיקה" })).toBeDisabled();
      expect(screen.queryByText(/טוען את בדיקת M03/)).not.toBeInTheDocument();
    });
  });
});
