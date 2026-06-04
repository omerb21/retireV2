import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunDetailScreen } from "./RunDetailScreen";

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

function buildRunDetail(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    run: {
      run_id: 11,
      client_id: 7,
      status: "success",
      calculation_version: "v1",
      created_at: "2026-06-01T00:00:00",
    },
    input_snapshot: {
      calculation_version: "v1",
      eligibility_date: "2025-01-01",
    },
    result: {
      calculation_id: "calc-1",
      calculation_version: "v1",
      status: "success",
      eligibility_date: "2025-01-01",
      eligibility_year: 2025,
      monthly_cap: 1000,
      exemption_percentage: 0.35,
      capital_multiplier: 180,
      initial_exempt_capital: 10000,
      grant_impact_total: 120,
      future_grant_reserved: 25,
      future_grant_impact: 5,
      actual_capitalization_impact: 50,
      idf_impact: 0,
      total_impact: 175,
      remaining_exempt_capital: 9825,
      monthly_exempt_pension: 300,
      capital_exemption_percentage: 0.6,
      pension_exemption_percentage: 0.4,
    },
    audit_rows: [
      {
        row_order: 1,
        label: "Base",
        output_amount: 10000,
        impact_amount: 0,
      },
    ],
    validation_errors: [],
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RunDetailScreen", () => {
  it("renders backend result summary and audit rows for a successful run", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(mockJsonResponse(buildRunDetail()))
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 11,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-06-01T00:00:00",
            },
          ]),
        ),
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/fixation/runs/11", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Fixation Run Detail" })).toBeInTheDocument();
    expect(await screen.findByText(/Monthly Cap:/)).toBeInTheDocument();
    expect(await screen.findByText(/Total Impact:/)).toBeInTheDocument();
    expect(await screen.findByText(/Audit Rows/)).toBeInTheDocument();
    expect(screen.getByText(/Base/)).toBeInTheDocument();
  });

  it("renders validation errors read-only for a validation_failed run", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse(
            buildRunDetail({
              run: {
                run_id: 12,
                client_id: 7,
                status: "validation_failed",
                calculation_version: "v1",
                created_at: "2026-06-01T00:00:00",
              },
              result: null,
              audit_rows: [],
              validation_errors: [
                {
                  error_order: 1,
                  code: "MISSING_FIELD",
                  path: "monthly_cap",
                  message: "Monthly cap is required",
                  severity: "error",
                  source_id: null,
                },
              ],
            }),
          ),
        )
        .mockResolvedValueOnce(mockJsonResponse([])),
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/runs/12"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Validation Errors" })).toBeInTheDocument();
    expect(await screen.findByText(/Monthly cap is required/)).toBeInTheDocument();
  });

  it("blocks trusted view when run client_id does not match route client", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse(
            buildRunDetail({
              run: {
                run_id: 13,
                client_id: 99,
                status: "success",
                calculation_version: "v1",
                created_at: "2026-06-01T00:00:00",
              },
            }),
          ),
        )
        .mockResolvedValueOnce(mockJsonResponse([])),
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/runs/13"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("BLOCKED")).toBeInTheDocument();
    expect(
      screen.getByText("This run does not belong to the current client context. Saved run data cannot be displayed as trusted."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Monthly Cap:/)).not.toBeInTheDocument();
  });

  it("shows non-latest indicator when a newer successful run exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse(
            buildRunDetail({
              run: {
                run_id: 10,
                client_id: 7,
                status: "success",
                calculation_version: "v1",
                created_at: "2026-05-30T00:00:00",
              },
            }),
          ),
        )
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 11,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-06-01T00:00:00",
            },
            {
              run_id: 10,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-05-30T00:00:00",
            },
          ]),
        ),
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/runs/10"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Not latest successful run")).toBeInTheDocument();
  });

  it("links back to the client history route", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(mockJsonResponse(buildRunDetail()))
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 11,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-06-01T00:00:00",
            },
          ]),
        ),
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/runs/11"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/runs/:runId" element={<RunDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("link", { name: "Back to History" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/history",
    );
  });
});
