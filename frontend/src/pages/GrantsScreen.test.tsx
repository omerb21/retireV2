import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GrantsScreen } from "./GrantsScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GrantsScreen", () => {
  it("renders grant data from the backend endpoint", async () => {
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
            grant_id: "GR-1",
            client_id: 7,
            employment_record_id: "ER-1",
            employer_name: "Employer Inc",
            nominal_amount: 10000.0,
            indexed_amount: 15000.0,
            grant_date: "2020-01-01",
            work_start_date: "2010-01-01",
            work_end_date: "2020-01-01",
            notes: "Grant note"
          }
        ]
      })
    );

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/grants", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Grants" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Client Name: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText("Grant ID: GR-1")).toBeInTheDocument();
    expect(await screen.findByText("Employment Record ID: ER-1")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Employer Inc" })).toBeInTheDocument();
    expect(await screen.findByText("Employer Name: Employer Inc")).toBeInTheDocument();
    expect(await screen.findByText("Nominal Amount: 10000")).toBeInTheDocument();
    expect(await screen.findByText("Indexed Amount: 15000")).toBeInTheDocument();
    expect(await screen.findByText("Grant Date: 2020-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Work Start Date: 2010-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Work End Date: 2020-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Notes: Grant note")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to employment history" })).toHaveAttribute("href", "/clients/7/employment-history");
    expect(screen.getByRole("link", { name: "Back to client detail" })).toHaveAttribute("href", "/clients/7");
  });
});
