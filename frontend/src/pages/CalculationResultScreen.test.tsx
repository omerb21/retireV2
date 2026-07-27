import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";

import { CalculationResultScreen } from "./CalculationResultScreen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const acceptedInput = {
  calculation_id: "calc-005",
  calculation_version: "pkg005-v1",
  m07_input_reference: {
    b1_evidence_revision_id: "m07rev-1",
    selections: [{
      field_code: "eligibility_date",
      candidate_identity: "fact:selected",
      b1_evidence_revision_id: "m07rev-1",
    }],
  },
  parameter_set: {
    parameter_set_id: "params-2026",
    client_id: 7,
    tax_year: 2026,
  },
  grants_collection_state: "confirmed_none",
  grants: [],
  future_grant_reservation: null,
  actual_capitalizations_collection_state: "confirmed_none",
  actual_capitalizations: [],
  idf: null,
};

const admittedSnapshot = {
  ...acceptedInput,
  eligibility_date: "2026-02-01",
  eligibility_year: 2026,
  m07_resolution: {
    calculation_scope: "m08a_fixation",
    manifest_version: "1",
    b1_evidence_revision_id: "m07rev-1",
    normalized_selected_values: { eligibility_date: "2026-02-01" },
    source_references: { eligibility_date: [{ source_kind: "fact_evidence", source_id: "fact:selected" }] },
    outcome: "resolved",
    fingerprint: "resolver-fingerprint",
  },
};

const successResult = {
  calculation_id: "calc-005",
  calculation_version: "pkg005-v1",
  status: "success",
  validation_errors: [],
  eligibility_date: "2026-02-01",
  eligibility_year: 2026,
  initial_exempt_capital: 100000,
  grant_impact_total: 1000,
  future_grant_impact: 0,
  actual_capitalization_impact: 500,
  total_impact: 1500,
  remaining_exempt_capital: 98500,
  monthly_exempt_pension: 547.22,
  grant_results: [{ grant_id: "G-1", impact_amount: 1000 }],
  actual_capitalization_results: [{ capitalization_id: "C-1", impact_amount: 500 }],
  audit_rows: [{ label: "Base", output_amount: 100000, impact_amount: 0 }],
};

function renderCurrent() {
  render(
    <MemoryRouter
      initialEntries={[{
        pathname: "/clients/7/fixation/result",
        state: {
          clientId: 7,
          clientName: "Dana Levi",
          inputData: acceptedInput,
          result: successResult,
          fixationInputPath: "/clients/7/fixation/input",
        },
      }]}
    >
      <Routes>
        <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderSaved() {
  render(
    <MemoryRouter initialEntries={["/clients/7/fixation/result"]}>
      <Routes>
        <Route path="/clients/:clientId/fixation/result" element={<CalculationResultScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

function ResultTransitionHarness() {
  const navigate = useNavigate();
  return (
    <>
      <button
        type="button"
        onClick={() =>
          navigate("/clients/8/fixation/result", {
            state: {
              clientId: 7,
              clientName: "Dana Levi",
              inputData: acceptedInput,
              result: successResult,
            },
          })
        }
      >
        Switch client
      </button>
      <CalculationResultScreen />
    </>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PKG-005 calculation result and saved-run workflow", () => {
  it("presents the real result, selected revision, effects and audit evidence", () => {
    renderCurrent();

    expect(screen.getByText("Normalized eligibility date: 2026-02-01")).toBeInTheDocument();
    expect(screen.getByText("Eligibility year: 2026")).toBeInTheDocument();
    expect(screen.getByText("Selected B1 revision: m07rev-1")).toBeInTheDocument();
    expect(screen.getByText(/Explicit eligibility selection:.*fact:selected/)).toBeInTheDocument();
    expect(screen.getByText(/Grant effects:.*G-1/)).toBeInTheDocument();
    expect(screen.getByText(/Capitalization effects:.*C-1/)).toBeInTheDocument();
    expect(screen.getByText(/Audit evidence:.*Base/)).toBeInTheDocument();
  });

  it("saves through the real route and exposes direct reopen navigation", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({
      run_id: 42,
      status: "success",
      created_at: "2026-03-01T10:00:00Z",
    }));
    vi.stubGlobal("fetch", fetchMock);
    renderCurrent();

    fireEvent.click(screen.getByRole("button", { name: "Save Result" }));
    expect(
      await screen.findByText(/Run saved. Run ID: 42; status: success; saved at: 2026-03-01T10:00:00Z/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reopen saved run" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/runs/42",
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/fixation/save");
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body).toEqual({ client_id: 7, input_data: acceptedInput });
  });

  it("clears stale route and save state, then loads the new client through its own route", async () => {
    const clientEightSnapshot = {
      ...admittedSnapshot,
      m07_input_reference: {
        b1_evidence_revision_id: "m07rev-client-8",
        selections: [],
      },
      eligibility_date: "2027-04-01",
      eligibility_year: 2027,
    };
    const clientEightResult = {
      ...successResult,
      eligibility_date: "2027-04-01",
      eligibility_year: 2027,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({
        run_id: 42,
        status: "success",
        created_at: "2026-03-01T10:00:00Z",
      }))
      .mockResolvedValueOnce(jsonResponse([
        { run_id: 88, status: "success", calculation_version: "pkg005-v1", created_at: "2027-04-02T10:00:00Z" },
      ]))
      .mockResolvedValueOnce(jsonResponse({
        run: { run_id: 88, client_id: 8, status: "success", created_at: "2027-04-02T10:00:00Z" },
        input_snapshot: clientEightSnapshot,
        result: clientEightResult,
        audit_rows: [],
        validation_errors: [],
      }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[{
          pathname: "/clients/7/fixation/result",
          state: {
            clientId: 7,
            clientName: "Dana Levi",
            inputData: acceptedInput,
            result: successResult,
          },
        }]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/result" element={<ResultTransitionHarness />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save Result" }));
    expect(await screen.findByRole("link", { name: "Reopen saved run" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch client" }));

    expect(screen.queryByText("Normalized eligibility date: 2026-02-01")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Reopen saved run" })).not.toBeInTheDocument();
    expect(await screen.findByText("Normalized eligibility date: 2027-04-01")).toBeInTheDocument();
    expect(screen.getByText("Selected B1 revision: m07rev-client-8")).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/clients/8/fixation/history");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/clients/8/fixation/runs/88");
  });

  it("reopens the latest successful run with resolver provenance and saved date", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([
        { run_id: 42, status: "success", calculation_version: "pkg005-v1", created_at: "2026-03-01T10:00:00Z" },
      ]))
      .mockResolvedValueOnce(jsonResponse({
        run: { run_id: 42, client_id: 7, status: "success", created_at: "2026-03-01T10:00:00Z" },
        input_snapshot: admittedSnapshot,
        result: successResult,
        audit_rows: successResult.audit_rows,
        validation_errors: [],
      }));
    vi.stubGlobal("fetch", fetchMock);
    renderSaved();

    expect(await screen.findByText(/Reopened saved run: 42; saved at: 2026-03-01T10:00:00Z/)).toBeInTheDocument();
    expect(screen.getByText("Selected B1 revision: m07rev-1")).toBeInTheDocument();
    expect(screen.getByText("Resolver scope/version: m08a_fixation / 1")).toBeInTheDocument();
    expect(screen.getByText("Resolver fingerprint: resolver-fingerprint")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Result" })).toBeDisabled();
  });

  it("shows safe load and save failures", async () => {
    const noRunFetch = vi.fn().mockResolvedValueOnce(jsonResponse([
      { run_id: 8, status: "validation_failed", calculation_version: "pkg005-v1", created_at: null },
    ]));
    vi.stubGlobal("fetch", noRunFetch);
    renderSaved();
    expect(await screen.findByText("No successful saved run is available for this client.")).toBeInTheDocument();
  });

  it("shows backend error detail when save fails", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({ detail: { code: "SAVE_FAILED", message: "save rejected" } }, 422),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderCurrent();
    fireEvent.click(screen.getByRole("button", { name: "Save Result" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("SAVE_FAILED"));
  });
});
