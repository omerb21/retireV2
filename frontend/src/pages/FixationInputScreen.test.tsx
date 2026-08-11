import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { FixationInputScreen } from "./FixationInputScreen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const resolvedRevision = {
  revision_id: "m07rev-resolved",
  profile_id: "fixation-ui",
  revision_number: 1,
  status: "finalized",
  finalized_at: "2026-01-01T08:00:00Z",
  eligibility_outcome: "resolved",
  eligibility_dates: ["2026-01-01"],
};

function revisionList(items = [resolvedRevision]) {
  return { items, offset: 0, limit: 100, total: items.length };
}

function deferredResponse() {
  let resolve!: (response: Response) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Response>((next, fail) => {
    resolve = next;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function ResultCapture() {
  const location = useLocation();
  return <pre data-testid="route-state">{JSON.stringify(location.state)}</pre>;
}

function InputTransitionHarness() {
  const navigate = useNavigate();
  return (
    <>
      <button
        type="button"
        onClick={() =>
          navigate("/clients/2/fixation/input", {
            state: { clientId: 2, clientName: "Client Two" },
          })
        }
      >
        Switch client
      </button>
      <button
        type="button"
        onClick={() =>
          navigate("/clients/1/fixation/input", {
            state: { clientId: 1, clientName: "Client One" },
          })
        }
      >
        Return to client A
      </button>
      <FixationInputScreen />
    </>
  );
}

function renderScreen(captureResult = false) {
  render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: "/clients/1/fixation/input",
          state: { clientName: "Client One" },
        },
      ]}
    >
      <Routes>
        <Route path="/clients/:clientId/fixation/input" element={<FixationInputScreen />} />
        {captureResult ? <Route path="/clients/:clientId/fixation/result" element={<ResultCapture />} /> : null}
      </Routes>
    </MemoryRouter>,
  );
}

function requestBody(fetchMock: ReturnType<typeof vi.fn>, index: number): Record<string, unknown> {
  return JSON.parse(String((fetchMock.mock.calls[index][1] as RequestInit).body)) as Record<string, unknown>;
}

async function waitForLoaded() {
  await screen.findByText(/Eligibility-date B1 evidence/);
  await waitFor(() => expect(screen.queryByText(/Loading client fixation data/)).not.toBeInTheDocument());
}

function fillValidM08Inputs() {
  fireEvent.change(screen.getByLabelText("Calculation Version"), { target: { value: "pkg005-v1" } });
  fireEvent.change(screen.getByLabelText("Parameter Set ID"), { target: { value: "params-2026" } });
  fireEvent.change(screen.getByLabelText("Parameter Tax Year"), { target: { value: "2026" } });
  fireEvent.change(screen.getByLabelText("Effective From"), { target: { value: "2026-01-01" } });
  fireEvent.change(screen.getByLabelText("Effective To"), { target: { value: "2026-12-31" } });
  fireEvent.change(screen.getByLabelText("Monthly Cap"), { target: { value: "1000" } });
  fireEvent.change(screen.getByLabelText("Exemption Percentage"), { target: { value: "0.5" } });
  fireEvent.change(screen.getByLabelText("Capital Multiplier"), { target: { value: "180" } });
  fireEvent.change(screen.getByLabelText("Grant Impact Multiplier"), { target: { value: "1.35" } });
  fireEvent.change(screen.getByLabelText("Parameter Source Basis"), { target: { value: "accepted fixture" } });
  fireEvent.change(screen.getByLabelText("Parameter Status"), { target: { value: "accepted" } });
  fireEvent.click(screen.getByLabelText("Parameter accepted for use"));
  fireEvent.change(screen.getByLabelText("Parameter Accepted By"), { target: { value: "planner" } });
  fireEvent.change(screen.getByLabelText("Parameter Decision Timestamp"), {
    target: { value: "2026-01-01T08:00" },
  });
  fireEvent.change(screen.getByLabelText("Actual Capitalization Collection State"), {
    target: { value: "confirmed_none" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PKG-005 fixation input workflow", () => {
  it("lists exact finalized revisions and never selects one implicitly", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();

    expect(screen.getByText(/does not choose latest or current automatically/)).toBeInTheDocument();
    expect((screen.getByLabelText("Finalized B1 revision") as HTMLSelectElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), {
      target: { value: "m07rev-resolved" },
    });
    expect(screen.getByText(/Selected revision: m07rev-resolved; status: finalized/)).toBeInTheDocument();
  });

  it("creates an eligibility-date revision without browser actor and selects only the returned ID", async () => {
    const created = {
      revision_id: "m07rev-created",
      status: "finalized",
      finalized_at: "2026-02-01T08:00:00Z",
      eligibility_date: "2026-02-01",
      technical_actor: "system:fixation-ui:Fixation workflow",
    };
    const createdSummary = {
      ...resolvedRevision,
      revision_id: created.revision_id,
      eligibility_dates: [created.eligibility_date],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockResolvedValueOnce(jsonResponse(created, 201))
      .mockResolvedValueOnce(jsonResponse(revisionList([resolvedRevision, createdSummary])));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Eligibility Date Evidence"), { target: { value: "2026-02-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Create finalized B1 revision" }));

    await screen.findByText(/Finalized B1 revision created and selected: m07rev-created/);
    expect(fetchMock.mock.calls[3][0]).toBe("/api/clients/1/fixation/m07/eligibility-date-revisions");
    expect(requestBody(fetchMock, 3)).toEqual({ eligibility_date: "2026-02-01" });
    expect(JSON.stringify(requestBody(fetchMock, 3))).not.toContain("actor");
    expect((screen.getByLabelText("Finalized B1 revision") as HTMLSelectElement).value).toBe("m07rev-created");
  });

  it("validates and calculates through the real admission request without legacy M07 fields", async () => {
    const success = {
      status: "success",
      validation_errors: [],
      eligibility_date: "2026-01-01",
      eligibility_year: 2026,
      remaining_exempt_capital: 90000,
      monthly_exempt_pension: 500,
      grant_impact_total: 0,
      actual_capitalization_impact: 0,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockResolvedValueOnce(jsonResponse(success))
      .mockResolvedValueOnce(jsonResponse(success));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen(true);
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Server validation passed/);

    const validatePayload = requestBody(fetchMock, 3);
    expect(validatePayload.m07_input_reference).toEqual({
      b1_evidence_revision_id: "m07rev-resolved",
      selections: [],
    });
    expect(validatePayload).not.toHaveProperty("eligibility_date");
    expect(validatePayload).not.toHaveProperty("eligibility_year");
    expect(validatePayload).not.toHaveProperty("upstream_context");
    expect(validatePayload.parameter_set).toMatchObject({
      parameter_set_id: "params-2026",
      tax_year: 2026,
      accepted_for_use: true,
      values: { grant_impact_multiplier: 1.35 },
    });
    expect(fetchMock.mock.calls.map((call) => call[0])).not.toContain("/api/fixation/review/convert");

    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
    await screen.findByText(/Calculation succeeded/);
    expect(fetchMock.mock.calls[4][0]).toBe("/api/clients/1/fixation/calculate");
    fireEvent.click(screen.getByRole("button", { name: "Continue to Result" }));
    const state = JSON.parse((await screen.findByTestId("route-state")).textContent ?? "{}");
    expect(state.inputData).toEqual(validatePayload);
    expect(state.result.status).toBe("success");
  });

  it("shows missing input and confirms calculation did not run", async () => {
    const missingRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-missing",
      eligibility_outcome: "missing_inputs",
      eligibility_dates: [],
    };
    const missing = {
      status: "validation_failed",
      validation_errors: [{
        code: "MISSING_REQUIRED_VALUE",
        path: "m07_input_reference.eligibility_date",
        message: "required calculation input is missing",
        severity: "error",
        source_id: null,
      }],
      m07_resolution: {
        client_id: 1,
        calculation_scope: "m08a_fixation",
        manifest_version: "1",
        b1_evidence_revision_id: "m07rev-missing",
        normalized_selected_values: {},
        source_references: {},
        missing_fields: ["eligibility_date"],
        ambiguous_fields: [],
        outcome: "missing_inputs",
        fingerprint: "missing-fingerprint",
      },
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([missingRevision])))
      .mockResolvedValueOnce(jsonResponse(missing));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-missing" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));

    expect(await screen.findByText(/Missing input: eligibility_date. Calculation did not run/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Calculation" })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("shows ambiguous candidates and sends only the explicit stable selection on retry", async () => {
    const ambiguousRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-ambiguous",
      eligibility_outcome: "ambiguous_inputs",
      eligibility_dates: ["2026-01-01", "2026-02-01"],
    };
    const ambiguous = {
      status: "validation_failed",
      validation_errors: [{
        code: "UNSUPPORTED_OR_UNAPPROVED_VALUE",
        path: "m07_input_reference.eligibility_date",
        message: "explicit selection required",
        severity: "error",
        source_id: null,
      }],
      m07_resolution: {
        client_id: 1,
        calculation_scope: "m08a_fixation",
        manifest_version: "1",
        b1_evidence_revision_id: "m07rev-ambiguous",
        normalized_selected_values: {},
        source_references: {},
        missing_fields: [],
        ambiguous_fields: [{
          field_code: "eligibility_date",
          candidates: [
            { normalized_value: "2026-01-01", candidate_identities: ["fact:first"], source_references: [] },
            { normalized_value: "2026-02-01", candidate_identities: ["fact:second"], source_references: [] },
          ],
        }],
        outcome: "ambiguous_inputs",
        fingerprint: "ambiguous-fingerprint",
      },
    };
    const success = { status: "success", validation_errors: [], eligibility_date: "2026-02-01", eligibility_year: 2026 };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([ambiguousRevision])))
      .mockResolvedValueOnce(jsonResponse(ambiguous))
      .mockResolvedValueOnce(jsonResponse(success));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-ambiguous" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Ambiguous input: eligibility_date/);
    fireEvent.click(screen.getByLabelText(/2026-02-01 \(fact:second\)/));
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Server validation passed/);

    expect((requestBody(fetchMock, 4).m07_input_reference as Record<string, unknown>).selections).toEqual([{
      field_code: "eligibility_date",
      candidate_identity: "fact:second",
      b1_evidence_revision_id: "m07rev-ambiguous",
    }]);
  });

  it("clears all client-bound evidence and actions before loading a different client", async () => {
    const ambiguousRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-client-1",
      eligibility_outcome: "ambiguous_inputs",
      eligibility_dates: ["2026-01-01", "2026-02-01"],
    };
    const clientTwoRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-client-2",
      eligibility_dates: ["2027-01-01"],
    };
    const ambiguous = {
      status: "validation_failed",
      validation_errors: [],
      m07_resolution: {
        ambiguous_fields: [{
          field_code: "eligibility_date",
          candidates: [
            { normalized_value: "2026-01-01", candidate_identities: ["fact:first"], source_references: [] },
            { normalized_value: "2026-02-01", candidate_identities: ["fact:second"], source_references: [] },
          ],
        }],
        missing_fields: [],
      },
    };
    const success = {
      status: "success",
      validation_errors: [],
      eligibility_date: "2026-02-01",
      eligibility_year: 2026,
      remaining_exempt_capital: 90000,
      monthly_exempt_pension: 500,
      grant_impact_total: 0,
      actual_capitalization_impact: 0,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([ambiguousRevision])))
      .mockResolvedValueOnce(jsonResponse(ambiguous))
      .mockResolvedValueOnce(jsonResponse(success))
      .mockResolvedValueOnce(jsonResponse(success))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([clientTwoRevision])));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[{
          pathname: "/clients/1/fixation/input",
          state: { clientId: 1, clientName: "Client One" },
        }]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/input" element={<InputTransitionHarness />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-client-1" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Ambiguous input: eligibility_date/);
    fireEvent.click(screen.getByLabelText(/2026-02-01 \(fact:second\)/));
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Server validation passed/);
    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
    await screen.findByText(/Calculation succeeded/);
    expect(screen.getByRole("button", { name: "Continue to Result" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Switch client" }));

    expect(screen.queryByText(/m07rev-client-1/)).not.toBeInTheDocument();
    expect(screen.queryByText(/fact:second/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Server validation passed/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Calculation succeeded/)).not.toBeInTheDocument();
    await waitForLoaded();
    expect(screen.getByText("Client ID: 2")).toBeInTheDocument();
    expect((screen.getByLabelText("Finalized B1 revision") as HTMLSelectElement).value).toBe("");
    expect(screen.getByRole("option", { name: /m07rev-client-2/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Calculation Version")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Run Calculation" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Continue to Result" })).toBeDisabled();
    expect(fetchMock.mock.calls.slice(6, 9).map((call) => call[0])).toEqual([
      "/api/clients/2/grants",
      "/api/clients/2/actual-capitalizations",
      "/api/clients/2/fixation/m07/revisions?limit=100",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    expect(await screen.findByText("Select an exact finalized B1 revision.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(9);
  });

  it("rejects an old A validation response after A to B to A and allows a new A validation", async () => {
    const pendingValidation = deferredResponse();
    const returnedRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-returned-a",
    };
    const staleSuccess = {
      status: "success",
      validation_errors: [],
      eligibility_date: "2026-01-01",
      eligibility_year: 2026,
    };
    const newSuccess = {
      ...staleSuccess,
      eligibility_date: "2027-01-01",
      eligibility_year: 2027,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockImplementationOnce(() => pendingValidation.promise)
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([])))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([returnedRevision])))
      .mockResolvedValueOnce(jsonResponse(newSuccess));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[{
          pathname: "/clients/1/fixation/input",
          state: { clientId: 1, clientName: "Client One" },
        }]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/input" element={<InputTransitionHarness />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));

    fireEvent.click(screen.getByRole("button", { name: "Switch client" }));
    expect(await screen.findByText("Client ID: 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Return to client A" }));
    expect(await screen.findByText("Client ID: 1")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /m07rev-returned-a/ })).toBeInTheDocument();

    await act(async () => {
      pendingValidation.resolve(jsonResponse(staleSuccess));
      await pendingValidation.promise;
    });

    expect(screen.queryByText(/Server validation passed/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Server Response" })).not.toBeInTheDocument();
    expect((screen.getByLabelText("Finalized B1 revision") as HTMLSelectElement).value).toBe("");
    expect(screen.getByRole("button", { name: "Run Calculation" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-returned-a" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    expect(await screen.findByText(/Server validation passed/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(11);
  });

  it("rejects an old A client load after A to B to A", async () => {
    const pendingOldRevisionLoad = deferredResponse();
    const oldRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-old-a-load",
    };
    const returnedRevision = {
      ...resolvedRevision,
      revision_id: "m07rev-new-a-load",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockImplementationOnce(() => pendingOldRevisionLoad.promise)
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([])))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([returnedRevision])));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[{
          pathname: "/clients/1/fixation/input",
          state: { clientId: 1, clientName: "Client One" },
        }]}
      >
        <Routes>
          <Route path="/clients/:clientId/fixation/input" element={<InputTransitionHarness />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Switch client" }));
    expect(await screen.findByText("Client ID: 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Return to client A" }));
    expect(await screen.findByText("Client ID: 1")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /m07rev-new-a-load/ })).toBeInTheDocument();

    await act(async () => {
      pendingOldRevisionLoad.resolve(jsonResponse(revisionList([oldRevision])));
      await pendingOldRevisionLoad.promise;
    });

    expect(screen.queryByRole("option", { name: /m07rev-old-a-load/ })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: /m07rev-new-a-load/ })).toBeInTheDocument();
    expect((screen.getByLabelText("Finalized B1 revision") as HTMLSelectElement).value).toBe("");
  });

  it.each([
    ["A-to-B", "success"], ["A-to-B", "structured error"], ["A-to-B", "rejection"],
    ["A-to-B-to-A", "success"], ["A-to-B-to-A", "structured error"], ["A-to-B-to-A", "rejection"],
  ] as const)("guards stale calculation %s %s including finally", async (transition, settlement) => {
    const pendingCalculation = deferredResponse();
    const success = {
      status: "success",
      validation_errors: [],
      eligibility_date: "2026-01-01",
      eligibility_year: 2026,
      grant_impact_total: "0.00",
      grant_results: [],
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockResolvedValueOnce(jsonResponse(success))
      .mockImplementationOnce(() => pendingCalculation.promise)
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList([])));
    if (transition === "A-to-B-to-A") {
      fetchMock
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse(revisionList()));
    }
    vi.stubGlobal("fetch", fetchMock);
    render(
      <MemoryRouter initialEntries={[{
        pathname: "/clients/1/fixation/input",
        state: { clientId: 1, clientName: "Client One" },
      }]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/input" element={<InputTransitionHarness />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Server validation passed/);
    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch client" }));
    expect(await screen.findByText("Client ID: 2")).toBeInTheDocument();
    if (transition === "A-to-B-to-A") {
      fireEvent.click(screen.getByRole("button", { name: "Return to client A" }));
      expect(await screen.findByText("Client ID: 1")).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /m07rev-resolved/ })).toBeInTheDocument();
    }
    await act(async () => {
      if (settlement === "rejection") pendingCalculation.reject(new Error("stale calculation rejection"));
      else if (settlement === "structured error") pendingCalculation.resolve(jsonResponse({ detail: "stale structured error" }, 422));
      else pendingCalculation.resolve(jsonResponse(success));
      await pendingCalculation.promise.catch(() => undefined);
    });
    expect(screen.queryByText(/Calculation succeeded|Calculation failed|stale calculation rejection|stale structured error/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Server Response" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Submitting/)).not.toBeInTheDocument();
  });

  it.each(["success", "structured error", "rejection"] as const)(
    "keeps the returned A calculation pending when old A settles with %s including finally",
    async (settlement) => {
      const oldCalculation = deferredResponse();
      const newCalculation = deferredResponse();
      const success = {
        status: "success",
        validation_errors: [],
        eligibility_date: "2026-01-01",
        eligibility_year: 2026,
        grant_impact_total: "0.00",
        grant_results: [],
      };
      const fetchMock = vi.fn()
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse(revisionList()))
        .mockResolvedValueOnce(jsonResponse(success))
        .mockImplementationOnce(() => oldCalculation.promise)
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse(revisionList([])))
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse(revisionList()))
        .mockResolvedValueOnce(jsonResponse(success))
        .mockImplementationOnce(() => newCalculation.promise);
      vi.stubGlobal("fetch", fetchMock);
      render(
        <MemoryRouter initialEntries={[{
          pathname: "/clients/1/fixation/input",
          state: { clientId: 1, clientName: "Client One" },
        }]}>
          <Routes>
            <Route path="/clients/:clientId/fixation/input" element={<InputTransitionHarness />} />
          </Routes>
        </MemoryRouter>,
      );

      await waitForLoaded();
      fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
      fillValidM08Inputs();
      fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
      expect(await screen.findByText(/Server validation passed/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5));

      fireEvent.click(screen.getByRole("button", { name: "Switch client" }));
      expect(await screen.findByText("Client ID: 2")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Return to client A" }));
      expect(await screen.findByText("Client ID: 1")).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /m07rev-resolved/ })).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
      fillValidM08Inputs();
      fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
      expect(await screen.findByText(/Server validation passed/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(13));

      await act(async () => {
        if (settlement === "rejection") oldCalculation.reject(new Error("stale calculation rejection"));
        else if (settlement === "structured error") oldCalculation.resolve(jsonResponse({ detail: "stale structured error" }, 422));
        else oldCalculation.resolve(jsonResponse(success));
        await oldCalculation.promise.catch(() => undefined);
      });

      expect(screen.getByRole("button", { name: "Validate Inputs" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Run Calculation" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Continue to Result" })).toBeDisabled();
      expect(screen.queryByText(/Calculation succeeded|Calculation failed|stale calculation rejection|stale structured error/)).not.toBeInTheDocument();

      await act(async () => newCalculation.resolve(jsonResponse(success)));
      expect(await screen.findByText(/Calculation succeeded/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Continue to Result" })).toBeEnabled();
    },
  );

  it("presents an existing M08 blocker without weakening it", async () => {
    const blocked = {
      status: "validation_failed",
      validation_errors: [{
        code: "UNSUPPORTED_OR_UNAPPROVED_VALUE",
        path: "parameter_set.accepted_for_use",
        message: "parameter set was not accepted for use",
        severity: "error",
        source_id: null,
      }],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockResolvedValueOnce(jsonResponse(blocked));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
    fillValidM08Inputs();
    fireEvent.click(screen.getByLabelText("Parameter accepted for use"));
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));

    expect(await screen.findByText(/parameter_set.accepted_for_use: parameter set was not accepted for use/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Calculation" })).toBeDisabled();
  });

  it("uses current direct M08C records without browser-supplied grant evidence", async () => {
    const grant = {
      grant_id: "G-1",
      client_id: 1,
      employer_name: "Employer",
      employer_withholding_file_number: "WF-1",
      exempt_grant_amount: "1000",
      grant_receipt_date: "2020-01-01",
      employment_start_date: "2010-01-01",
      employment_end_date: "2020-01-01",
    };
    const capitalization = {
      capitalization_id: "C-1",
      client_id: 1,
      amount: "500",
      capitalization_date: "2021-01-01",
      source_label: "actual withdrawal",
      source_basis: "capitalization record",
      planner_assertion: null,
      planner_assertion_basis: null,
      notes: null,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([grant]))
      .mockResolvedValueOnce(jsonResponse([capitalization]))
      .mockResolvedValueOnce(jsonResponse(revisionList()))
      .mockResolvedValueOnce(jsonResponse({
        status: "success",
        validation_errors: [],
        eligibility_date: "2026-01-01",
        eligibility_year: 2026,
      }));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitForLoaded();
    fireEvent.change(screen.getByLabelText("Finalized B1 revision"), { target: { value: "m07rev-resolved" } });
    fillValidM08Inputs();
    fireEvent.change(screen.getByLabelText("Actual Capitalization Collection State"), {
      target: { value: "items_recorded" },
    });

    const capitalizationGroup = screen.getByRole("group", { name: "Capitalization C-1" });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Capitalization Inclusion"), {
      target: { value: "include" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Capitalization Support"), {
      target: { value: "supported" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Recorded Meaning"), {
      target: { value: "actual capitalization" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Source Basis"), {
      target: { value: "capitalization record" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Evidence Status"), {
      target: { value: "accepted" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Decision Actor"), {
      target: { value: "planner" },
    });
    fireEvent.change(within(capitalizationGroup).getByLabelText("Decision Timestamp"), {
      target: { value: "2026-01-01T08:00" },
    });
    fireEvent.click(within(capitalizationGroup).getByLabelText("Accepted for use"));

    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));
    await screen.findByText(/Server validation passed/);
    const payload = requestBody(fetchMock, 3);
    expect(payload.grants).toEqual([]);
    expect(payload.grants_collection_state).toBe("confirmed_none");
    expect(payload.metadata).toEqual(expect.objectContaining({ grant_contract: "pkg-012-direct-v1" }));
    expect(payload.actual_capitalizations).toEqual([expect.objectContaining({
      capitalization_id: "C-1",
      recorded_meaning: "actual capitalization",
      inclusion_decision: "include",
      support_status: "supported",
      accepted_for_use: true,
    })]);
  });
});
