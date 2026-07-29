import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

function renderPage() {
  return render(<MemoryRouter initialEntries={["/clients/1/source-review"]}>
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
});
