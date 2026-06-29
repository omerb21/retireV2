import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FixationInputReviewPayload } from "../api/fixationApi";
import { FixationInputScreen } from "./FixationInputScreen";

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

function renderScreen() {
  render(
    <MemoryRouter initialEntries={["/clients/1/fixation/input"]}>
      <Routes>
        <Route path="/clients/:clientId/fixation/input" element={<FixationInputScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Calculation Version"), { target: { value: "v1" } });
  fireEvent.change(screen.getByLabelText("Eligibility Date"), { target: { value: "2025-01-01" } });
  fireEvent.change(screen.getByLabelText("Eligibility Year"), { target: { value: "2025" } });
  fireEvent.change(screen.getByLabelText("Monthly Cap"), { target: { value: "1000" } });
  fireEvent.change(screen.getByLabelText("Exemption Percentage"), { target: { value: "0.5" } });
  fireEvent.change(screen.getByLabelText("Capital Multiplier"), { target: { value: "180" } });
  fireEvent.change(screen.getByLabelText("Future Grant Reserved"), { target: { value: "0" } });
}

const grantItems = [
  {
    grant_id: "GR-1",
    client_id: 1,
    employment_record_id: null,
    employer_name: "Employer One",
    nominal_amount: "100.00",
    indexed_amount: "120.00",
    grant_date: "2020-01-01",
    work_start_date: "2010-01-01",
    work_end_date: "2020-01-01",
    notes: null,
  },
  {
    grant_id: "GR-2",
    client_id: 1,
    employment_record_id: null,
    employer_name: "Employer Two",
    nominal_amount: null,
    indexed_amount: "220.00",
    grant_date: "2021-01-01",
    work_start_date: "2011-01-01",
    work_end_date: "2021-01-01",
    notes: null,
  },
];

const capitalizationItems = [
  {
    capitalization_id: "AC-1",
    client_id: 1,
    amount: "50.00",
    capitalization_date: "2022-01-01",
    source_label: "Manual",
    source_basis: "capitalization certificate",
    planner_assertion: "advisor confirmed amount",
    planner_assertion_basis: "reviewed certificate",
    notes: "review context",
  },
];

const convertedInput = {
  calculation_id: null,
  calculation_version: "v1",
  eligibility_date: "2025-01-01",
  eligibility_year: 2025,
  monthly_cap: 1000,
  exemption_percentage: 0.5,
  capital_multiplier: 180,
  grants: [
    {
      grant_id: "GR-1",
      employer_name: "Employer One",
      nominal_amount: 100,
      indexed_amount: 120,
      grant_date: "2020-01-01",
      work_start_date: "2010-01-01",
      work_end_date: "2020-01-01",
    },
  ],
  future_grant_reserved: 0,
  actual_capitalizations: [],
  idf: null,
};

function requestPayload(fetchMock: ReturnType<typeof vi.fn>, callIndex: number) {
  const request = fetchMock.mock.calls[callIndex][1] as RequestInit;
  return JSON.parse(String(request.body)) as Record<string, unknown>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("FixationInputScreen contract payload", () => {
  it("validates review state before conversion and shows backend blocking errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse(grantItems))
      .mockResolvedValueOnce(mockJsonResponse(capitalizationItems))
      .mockResolvedValueOnce(
        mockJsonResponse({
          valid: false,
          errors: [
            {
              code: "UNSUPPORTED_OR_UNAPPROVED_VALUE",
              path: "grants.collection_state",
              message: "grants collection_state 'unknown' blocks calculation until source facts are explicitly reviewed",
              severity: "error",
              source_id: null,
            },
          ],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitFor(() => expect(screen.getByText(/Current Input Readiness Status:/)).toBeInTheDocument());
    expect(screen.getByLabelText("Eligibility Date")).toHaveAttribute("type", "text");
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/fixation/review/validate");
    const payload = requestPayload(fetchMock, 2);
    expect(payload.grants).toEqual({ collection_state: "unknown", items: [] });
    expect(payload.actual_capitalizations).toEqual({ collection_state: "unknown", items: [] });
    expect(await screen.findByText(/grants.collection_state/)).toBeInTheDocument();
    expect(payload).not.toHaveProperty("idf_relevant");
  });

  it("requires explicit dispositions and uses converted payload for calculation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse(grantItems))
      .mockResolvedValueOnce(mockJsonResponse(capitalizationItems))
      .mockResolvedValueOnce(mockJsonResponse({ valid: true, errors: [] }))
      .mockResolvedValueOnce(mockJsonResponse(convertedInput))
      .mockResolvedValueOnce(mockJsonResponse({ status: "success", validation_errors: [], calculation_id: "calc-ok" }));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitFor(() => expect(screen.getByText(/Current Input Readiness Status:/)).toBeInTheDocument());
    fillRequiredFields();

    fireEvent.change(screen.getByLabelText("Grant Collection State"), { target: { value: "items_recorded" } });
    fireEvent.change(screen.getByLabelText("Actual Capitalization Collection State"), {
      target: { value: "items_recorded" },
    });

    expect(await screen.findByText("Source Item ID: GR-1")).toBeInTheDocument();
    expect(await screen.findByText("Source Item ID: GR-2")).toBeInTheDocument();
    expect(await screen.findByText("Source Basis: capitalization certificate")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Grant Disposition").map((input) => (input as HTMLSelectElement).value)).toEqual([
      "",
      "",
    ]);
    expect((screen.getByLabelText("Actual Capitalization Disposition") as HTMLSelectElement).value).toBe("");

    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));
    expect(await screen.findByText(/Every loaded grant requires an explicit include or exclude disposition\./)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    const grantDispositions = screen.getAllByLabelText("Grant Disposition");
    fireEvent.change(grantDispositions[0], { target: { value: "include" } });
    fireEvent.change(grantDispositions[1], { target: { value: "exclude" } });
    fireEvent.change(screen.getByLabelText("Actual Capitalization Disposition"), { target: { value: "exclude" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/fixation/review/validate");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/fixation/review/convert");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/fixation/calculate");
    const reviewPayload = requestPayload(fetchMock, 2) as unknown as FixationInputReviewPayload;
    expect(reviewPayload.grants.items.map((item) => item.source_item_id)).toEqual(["GR-1", "GR-2"]);
    expect(reviewPayload.grants.items.map((item) => item.disposition)).toEqual([
      "include",
      "exclude",
    ]);
    expect(reviewPayload.actual_capitalizations.items[0]).toMatchObject({
      source_item_id: "AC-1",
      source_basis: "capitalization certificate",
      planner_assertion: "advisor confirmed amount",
      planner_assertion_basis: "reviewed certificate",
      disposition: "exclude",
    });
    const calculatePayload = requestPayload(fetchMock, 4);
    expect(calculatePayload).toEqual(convertedInput);
    expect(calculatePayload.actual_capitalizations).toEqual([]);
    expect(JSON.stringify(calculatePayload)).not.toContain("source_basis");
    expect(JSON.stringify(calculatePayload)).not.toContain("planner_assertion");
  });

  it("converts confirmed none as explicit empty review collections", async () => {
    const confirmedNoneInput = {
      ...convertedInput,
      grants: [],
      actual_capitalizations: [],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse({ valid: true, errors: [] }))
      .mockResolvedValueOnce(mockJsonResponse(confirmedNoneInput))
      .mockResolvedValueOnce(mockJsonResponse({ status: "success", validation_errors: [] }));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitFor(() => expect(screen.getByText(/Current Input Readiness Status:/)).toBeInTheDocument());
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Grant Collection State"), { target: { value: "confirmed_none" } });
    fireEvent.change(screen.getByLabelText("Actual Capitalization Collection State"), {
      target: { value: "confirmed_none" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5));
    const reviewPayload = requestPayload(fetchMock, 2);
    expect(reviewPayload.grants).toEqual({ collection_state: "confirmed_none", items: [] });
    expect(reviewPayload.actual_capitalizations).toEqual({ collection_state: "confirmed_none", items: [] });
    expect(requestPayload(fetchMock, 4)).toEqual(confirmedNoneInput);
  });
});
