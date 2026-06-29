import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CalculationResultScreen } from "./CalculationResultScreen";

function mockJsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    headers: {
      get: () => "application/json"
    },
    json: async () => body
  };
}

function mockErrorResponse(body: unknown) {
  return {
    ok: false,
    status: 422,
    statusText: "Unprocessable Entity",
    headers: {
      get: () => "application/json"
    },
    json: async () => body
  };
}

function buildInputSnapshot(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    calculation_id: "calc-1",
    calculation_version: "v1",
    eligibility_date: "2025-01-01",
    eligibility_year: 2025,
    monthly_cap: 1000,
    exemption_percentage: 0.35,
    capital_multiplier: 180,
    grants: [
      {
        grant_id: "GR-1",
        employer_name: "Employer Inc",
        nominal_amount: 100,
        indexed_amount: 120,
        grant_date: "2020-01-01",
        work_start_date: "2010-01-01",
        work_end_date: "2020-01-01"
      }
    ],
    future_grant_reserved: 25,
    actual_capitalizations: [
      {
        capitalization_id: "AC-1",
        amount: 50,
        capitalization_date: "2021-01-01",
        source_label: "Imported",
        notes: null
      }
    ],
    idf: null,
    ...overrides
  };
}

function buildResult(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    calculation_id: "calc-1",
    calculation_version: "v1",
    status: "success",
    validation_errors: [],
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
    grant_results: [
      {
        grant_id: "GR-1",
        impact_amount: 120
      }
    ],
    actual_capitalization_results: [
      {
        capitalization_id: "AC-1",
        impact_amount: 50
      }
    ],
    idf_result: {
      impact_amount: 0
    },
    audit_rows: [
      {
        row_order: 1,
        label: "Base",
        output_amount: 10000,
        impact_amount: 0
      }
    ],
    ...overrides
  };
}

function buildActiveSessionReviewContext() {
  return {
    grants_collection_state: "items_recorded",
    actual_capitalizations_collection_state: "items_recorded",
    included_source_references: [
      {
        domain: "grants",
        source_item_id: "GR-1",
        record_id: "GR-1",
        label: "Employer Inc",
        disposition: "include"
      },
      {
        domain: "actual_capitalizations",
        source_item_id: "AC-1",
        record_id: "AC-1",
        label: "Imported",
        disposition: "include"
      }
    ],
    excluded_source_references: [
      {
        domain: "grants",
        source_item_id: "GR-2",
        record_id: "GR-2",
        label: "Prior Employer",
        disposition: "exclude"
      }
    ],
    source_metadata_context: [
      {
        domain: "actual_capitalizations",
        source_item_id: "AC-1",
        record_id: "AC-1",
        source_basis: "capitalization certificate",
        planner_assertion: "advisor confirmed amount",
        planner_assertion_basis: "reviewed certificate"
      }
    ]
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CalculationResultScreen", () => {
  it("loads and renders the latest successful backend calculation result with client-scoped back navigation", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(mockJsonResponse([]))
        .mockResolvedValueOnce(mockJsonResponse([]))
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 11,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-05-26T00:00:00"
            }
          ])
        )
        .mockResolvedValueOnce(
          mockJsonResponse({
            run: {
              run_id: 11,
              client_id: 7,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-05-26T00:00:00"
            },
            input_snapshot: buildInputSnapshot({ grants: [], actual_capitalizations: [] }),
            result: buildResult(),
            audit_rows: [],
            validation_errors: []
          })
        )
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/fixation/result", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Calculation Result" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Client Name: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText(/Result Source: תוצאת החישוב השמורה/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "רשומת חישוב שמורה" })).toBeInTheDocument();
    expect(await screen.findByText("מזהה רשומה: 11")).toBeInTheDocument();
    expect(await screen.findByText("נוצרה בתאריך: 2026-05-26T00:00:00")).toBeInTheDocument();
    expect(await screen.findByText(/Trusted Result Status: Current source data matches the calculation input snapshot\./)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Current Workflow Review Context" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Latest saved successful result/)).not.toBeInTheDocument();
    expect(screen.queryByText("View History")).not.toBeInTheDocument();
    expect(screen.queryByText("View Fixation Audit / History")).not.toBeInTheDocument();
    expect((await screen.findAllByText(/Calculation Version:/)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Monthly Cap:/)).length).toBeGreaterThan(0);
    expect(await screen.findByText(/Total Impact:/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Fixation Parameters" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/input"
    );
    expect(screen.getByRole("link", { name: "פתח רשומת חישוב שמורה" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/history"
    );
    expect(screen.getByRole("button", { name: "Save Result" })).toBeDisabled();
  });

  it("marks the displayed result as stale and enforces rerun when source data changed", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              grant_id: "GR-1",
              client_id: 7,
              employment_record_id: null,
              employer_name: "Employer Inc",
              nominal_amount: 100,
              indexed_amount: 999,
              grant_date: "2020-01-01",
              work_start_date: "2010-01-01",
              work_end_date: "2020-01-01",
              notes: null
            }
          ])
        )
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              capitalization_id: "AC-1",
              client_id: 7,
              amount: 50,
              capitalization_date: "2021-01-01",
              source_label: "Imported",
              notes: null
            }
          ])
        )
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 12,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-05-26T00:00:00"
            }
          ])
        )
        .mockResolvedValueOnce(
          mockJsonResponse({
            run: {
              run_id: 12,
              client_id: 7,
              status: "success",
              calculation_version: "v1",
              created_at: "2026-05-26T00:00:00"
            },
            input_snapshot: buildInputSnapshot(),
            result: buildResult(),
            audit_rows: [],
            validation_errors: []
          })
        )
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/fixation/result", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText(/Trusted Result Status: Blocked until rerun\./)).toBeInTheDocument();
    expect(
      await screen.findByText(/Current grants or actual capitalizations differ from the calculation input snapshot\. Rerun is required\./)
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rerun from Fixation Parameters" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/input"
    );
    expect(screen.getByRole("button", { name: "Save Result" })).toBeDisabled();
  });

  it("renders a clear failure state when no successful calculation result exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(mockJsonResponse([]))
        .mockResolvedValueOnce(mockJsonResponse([]))
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              run_id: 13,
              status: "validation_failed",
              calculation_version: "v1",
              created_at: "2026-05-26T00:00:00"
            }
          ])
        )
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/fixation/result", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      await screen.findByText(/No successful calculation result is available\. Latest saved calculation did not succeed\./)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Result" })).toBeDisabled();
  });

  it("renders the current backend calculation response without deriving financial values in the frontend", async () => {
    const inputData = buildInputSnapshot();
    const result = buildResult({
      initial_exempt_capital: 4321,
      total_impact: 222,
      monthly_exempt_pension: 777
    });

    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              grant_id: "GR-1",
              client_id: 7,
              employment_record_id: null,
              employer_name: "Employer Inc",
              nominal_amount: 100,
              indexed_amount: 120,
              grant_date: "2020-01-01",
              work_start_date: "2010-01-01",
              work_end_date: "2020-01-01",
              notes: null
            }
          ])
        )
        .mockResolvedValueOnce(
          mockJsonResponse([
            {
              capitalization_id: "AC-1",
              client_id: 7,
              amount: 50,
              capitalization_date: "2021-01-01",
              source_label: "Imported",
              notes: null
            }
          ])
        )
    );

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/clients/7/fixation/result",
            state: {
              clientId: 7,
              clientName: "Dana Levi",
              inputData,
              result,
              fixationInputPath: "/clients/7/fixation/input",
              fixationInputState: { clientId: 7, clientName: "Dana Levi" },
              activeSessionReviewContext: buildActiveSessionReviewContext()
            }
          }
        ]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText(/Result Source: Current backend calculation response/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Calculation Outcome" })).toBeInTheDocument();
    expect(await screen.findByText(/Initial Exempt Capital:/)).toBeInTheDocument();
    expect(await screen.findByText(/Total Impact:/)).toBeInTheDocument();
    expect(await screen.findByText(/Monthly Exempt Pension:/)).toBeInTheDocument();
    expect(screen.getByText((content, node) => node?.textContent === "Initial Exempt Capital: 4321")).toBeInTheDocument();
    expect(screen.getByText((content, node) => node?.textContent === "Total Impact: 222")).toBeInTheDocument();
    expect(screen.getByText((content, node) => node?.textContent === "Monthly Exempt Pension: 777")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Converted Input Used For Calculation" })).toBeInTheDocument();
    expect(screen.getByText("Grant Inputs: 1")).toBeInTheDocument();
    expect(screen.getByText("Actual Capitalization Inputs: 1")).toBeInTheDocument();
    const contextSection = screen.getByRole("heading", { name: "Current Workflow Review Context" }).closest("section");
    expect(contextSection).not.toBeNull();
    expect(within(contextSection as HTMLElement).getByText("Grants Collection State: items_recorded")).toBeInTheDocument();
    expect(
      within(contextSection as HTMLElement).getByText("Actual Capitalizations Collection State: items_recorded")
    ).toBeInTheDocument();
    expect(within(contextSection as HTMLElement).getByRole("heading", { name: "Included Records" })).toBeInTheDocument();
    expect(within(contextSection as HTMLElement).getByRole("heading", { name: "Excluded Records" })).toBeInTheDocument();
    expect(within(contextSection as HTMLElement).getAllByText(/GR-1/).length).toBeGreaterThan(0);
    expect(within(contextSection as HTMLElement).getAllByText(/AC-1/).length).toBeGreaterThan(0);
    expect(within(contextSection as HTMLElement).getAllByText(/GR-2/).length).toBeGreaterThan(0);
    expect(within(contextSection as HTMLElement).getByRole("heading", { name: "Source And Planner Context" })).toBeInTheDocument();
    expect(within(contextSection as HTMLElement).getByText("Source Basis: capitalization certificate")).toBeInTheDocument();
    expect(within(contextSection as HTMLElement).getByText("Planner Assertion: advisor confirmed amount")).toBeInTheDocument();
    expect(
      within(contextSection as HTMLElement).queryByText(/history|audit|documentation|traceability|saved|readiness|eligibility|recommendation/i)
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Result" })).toBeEnabled();
  });

  it("saves only the current successful calculation input snapshot and links to history", async () => {
    const inputData = buildInputSnapshot();
    const result = buildResult();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse(inputData.grants))
      .mockResolvedValueOnce(mockJsonResponse(inputData.actual_capitalizations))
      .mockResolvedValueOnce(mockJsonResponse({ run_id: 41, status: "success" }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/clients/7/fixation/result",
            state: {
              clientId: 7,
              clientName: "Dana Levi",
              inputData,
              result,
              fixationInputPath: "/clients/7/fixation/input",
              fixationInputState: { clientId: 7, clientName: "Dana Levi" }
            }
          }
        ]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    const saveButton = await screen.findByRole("button", { name: "Save Result" });
    await waitFor(() => expect(saveButton).toBeEnabled());
    fireEvent.click(saveButton);

    expect(await screen.findByText("Result saved successfully. Run ID: 41")).toBeInTheDocument();
    const savedRecordLinks = screen.getAllByRole("link", { name: "פתח רשומת חישוב שמורה" });
    expect(savedRecordLinks).toHaveLength(2);
    expect(savedRecordLinks[1]).toHaveAttribute(
      "href",
      "/clients/7/fixation/history"
    );
    expect(screen.queryByText("View History")).not.toBeInTheDocument();
    expect(screen.queryByText("View Fixation Audit / History")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/fixation/save",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ client_id: 7, input_data: inputData })
      })
    );
  });

  it("displays backend errors when saving the current result fails", async () => {
    const inputData = buildInputSnapshot();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse(inputData.grants))
      .mockResolvedValueOnce(mockJsonResponse(inputData.actual_capitalizations))
      .mockResolvedValueOnce(mockErrorResponse({ detail: { code: "SAVE_FAILED", message: "Unable to save run" } }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/clients/7/fixation/result",
            state: {
              clientId: 7,
              inputData,
              result: buildResult(),
              fixationInputPath: "/clients/7/fixation/input",
              fixationInputState: { clientId: 7 }
            }
          }
        ]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
        </Routes>
      </MemoryRouter>
    );

    const saveButton = await screen.findByRole("button", { name: "Save Result" });
    await waitFor(() => expect(saveButton).toBeEnabled());
    fireEvent.click(saveButton);

    expect(await screen.findByText("Unable to save the current calculation result.")).toBeInTheDocument();
    expect(await screen.findByText(/SAVE_FAILED/)).toBeInTheDocument();
  });
});
