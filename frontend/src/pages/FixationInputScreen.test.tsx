import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

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

function requestPayload(fetchMock: ReturnType<typeof vi.fn>, callIndex: number) {
  const request = fetchMock.mock.calls[callIndex][1] as RequestInit;
  return JSON.parse(String(request.body)) as Record<string, unknown>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("FixationInputScreen contract payload", () => {
  it("validates a non-IDF scenario with required idf null and no retired relevance marker", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse({ status: "success", validation_errors: [] }));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitFor(() => expect(screen.getByText(/Current Input Readiness Status:/)).toBeInTheDocument());
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Validate Inputs" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/fixation/validate");
    const payload = requestPayload(fetchMock, 2);
    expect(payload).toHaveProperty("idf", null);
    expect(payload).not.toHaveProperty("idf_relevant");
  });

  it("calculates an IDF scenario with an idf object and no retired relevance marker", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(mockJsonResponse({ status: "success", validation_errors: [] }));
    vi.stubGlobal("fetch", fetchMock);

    renderScreen();
    await waitFor(() => expect(screen.getByText(/Current Input Readiness Status:/)).toBeInTheDocument());
    fillRequiredFields();
    fireEvent.click(screen.getByLabelText("IDF applicable"));
    fireEvent.change(screen.getByLabelText("IDF ID"), { target: { value: "IDF-1" } });
    fireEvent.change(screen.getByLabelText("IDF Reduction Amount"), { target: { value: "100" } });
    fireEvent.change(screen.getByLabelText("IDF Original Commutation Percent"), { target: { value: "25" } });
    fireEvent.change(screen.getByLabelText("IDF Current Commutation Percent"), { target: { value: "20" } });
    fireEvent.change(screen.getByLabelText("IDF Commutation Date"), { target: { value: "2025-01-01" } });
    fireEvent.change(screen.getByLabelText("IDF Promoter Age Date"), { target: { value: "2026-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Calculation" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/fixation/calculate");
    const payload = requestPayload(fetchMock, 2);
    expect(payload).not.toHaveProperty("idf_relevant");
    expect(payload.idf).toEqual({
      idf_id: "IDF-1",
      reduction_amount: 100,
      original_commutation_percent: 25,
      current_commutation_percent: 20,
      commutation_date: "2025-01-01",
      promoter_age_date: "2026-01-01",
      source_label: null,
    });
  });
});
