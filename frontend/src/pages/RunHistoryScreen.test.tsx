import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunHistoryScreen } from "./RunHistoryScreen";

function mockJsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    headers: {
      get: () => "application/json",
    },
    json: async () => body,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RunHistoryScreen", () => {
  it("loads mocked history and renders rows with latest successful run marker", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        mockJsonResponse([
          {
            run_id: 21,
            status: "success",
            calculation_version: "v1",
            created_at: "2026-06-01T00:00:00",
          },
          {
            run_id: 20,
            status: "validation_failed",
            calculation_version: "v1",
            created_at: "2026-05-31T00:00:00",
          },
          {
            run_id: 19,
            status: "success",
            calculation_version: "v1",
            created_at: "2026-05-30T00:00:00",
          },
        ]),
      ),
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/fixation/history", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/history" element={<RunHistoryScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Fixation History" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Client Name: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText((_, node) => node?.textContent === "Run ID: 21")).toBeInTheDocument();
    expect(screen.getByText((_, node) => node?.textContent === "Run ID: 20")).toBeInTheDocument();
    expect(screen.getByText("Latest successful run")).toBeInTheDocument();
  });

  it("renders empty state message and Start New Calculation link", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(mockJsonResponse([])));

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/history"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/history" element={<RunHistoryScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("No fixation calculations saved yet")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Start New Calculation" })[0]).toHaveAttribute(
      "href",
      "/clients/7/fixation/input",
    );
  });

  it("renders BLOCKED for invalid client without requiring successful fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/0/fixation/history"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/history" element={<RunHistoryScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText("Fixation history requires an existing client context.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("links View Run to the client-scoped detail route", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        mockJsonResponse([
          {
            run_id: 42,
            status: "success",
            calculation_version: "v1",
            created_at: "2026-06-01T00:00:00",
          },
        ]),
      ),
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/history"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/history" element={<RunHistoryScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("link", { name: "View Run" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/runs/42",
    );
  });
});
