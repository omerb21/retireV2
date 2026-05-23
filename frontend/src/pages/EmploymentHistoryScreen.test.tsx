import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EmploymentHistoryScreen } from "./EmploymentHistoryScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("EmploymentHistoryScreen", () => {
  it("renders employment records from the backend endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: {
          get: () => "application/json"
        },
        json: async () => [
          {
            employment_record_id: "ER-1",
            client_id: 7,
            employer_name: "Employer Inc",
            work_start_date: "2010-01-01",
            work_end_date: "2020-01-01",
            is_current: false,
            notes: "Former role"
          }
        ]
      })
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/employment-history"]}>
        <Routes>
          <Route path="/clients/:clientId/employment-history" element={<EmploymentHistoryScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Employment History" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Employer Inc")).toBeInTheDocument();
    expect(await screen.findByText("Employment Record ID: ER-1")).toBeInTheDocument();
    expect(await screen.findByText("Work Start Date: 2010-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Work End Date: 2020-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Current Employment: No")).toBeInTheDocument();
    expect(await screen.findByText("Notes: Former role")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to client detail" })).toHaveAttribute("href", "/clients/7");
  });
});
