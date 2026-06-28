import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GrantsScreen } from "./GrantsScreen";

function jsonResponse(body: unknown) {
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GrantsScreen", () => {
  it("adds, edits, deletes, and saves grants without calculation calls", async () => {
    const firstGrant = {
      grant_id: "GR-1",
      client_id: 7,
      employment_record_id: "ER-1",
      employer_name: "Employer Inc",
      nominal_amount: 10000,
      indexed_amount: 15000,
      grant_date: "2020-01-01",
      work_start_date: "2010-01-01",
      work_end_date: "2020-01-01",
      notes: "Grant note"
    };
    const secondGrant = {
      grant_id: "GR-2",
      client_id: 7,
      employment_record_id: null,
      employer_name: "New Employer",
      nominal_amount: null,
      indexed_amount: 9000,
      grant_date: "2022-01-01",
      work_start_date: "2021-01-01",
      work_end_date: "2022-01-01",
      notes: "New grant"
    };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([firstGrant]))
      .mockResolvedValueOnce(jsonResponse(secondGrant))
      .mockResolvedValueOnce(jsonResponse([firstGrant, secondGrant]))
      .mockResolvedValueOnce(jsonResponse({ ...firstGrant, employer_name: "Updated Employer", indexed_amount: 16000 }))
      .mockResolvedValueOnce(
        jsonResponse([{ ...firstGrant, employer_name: "Updated Employer", indexed_amount: 16000 }, secondGrant])
      )
      .mockResolvedValueOnce(jsonResponse({ deleted: true }))
      .mockResolvedValueOnce(jsonResponse([secondGrant]));

    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/grants", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("Grant ID: GR-1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "New Employer" } });
    fireEvent.change(screen.getByLabelText("Indexed Amount"), { target: { value: "9000" } });
    fireEvent.change(screen.getByLabelText("Grant Date"), { target: { value: "2022-01-01" } });
    fireEvent.change(screen.getByLabelText("Work Start Date"), { target: { value: "2021-01-01" } });
    fireEvent.change(screen.getByLabelText("Work End Date"), { target: { value: "2022-01-01" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "New grant" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/grants",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            employment_record_id: null,
            employer_name: "New Employer",
            nominal_amount: null,
            indexed_amount: "9000",
            grant_date: "2022-01-01",
            work_start_date: "2021-01-01",
            work_end_date: "2022-01-01",
            notes: "New grant"
          })
        })
      );
    });
    expect(await screen.findByText("Grant ID: GR-2")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit Grant" })[0]);
    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "Updated Employer" } });
    fireEvent.change(screen.getByLabelText("Indexed Amount"), { target: { value: "16000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/api/clients/7/grants/GR-1",
        expect.objectContaining({ method: "PUT" })
      );
    });
    expect(await screen.findByText("Indexed Amount: 16000")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete Grant" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        6,
        "/api/clients/7/grants/GR-1",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    const requestedUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(requestedUrls.every((url) => !url.includes("/fixation/validate") && !url.includes("/fixation/calculate"))).toBe(
      true
    );
    expect(screen.getByRole("link", { name: "Back to employment history" })).toHaveAttribute(
      "href",
      "/clients/7/employment-history"
    );
    expect(screen.getByRole("link", { name: "Back to client detail" })).toHaveAttribute("href", "/clients/7");
  });

  it("preserves blank numeric input for backend validation instead of coercing it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ detail: [{ msg: "indexed_amount must be numeric" }] }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7/grants"]}>
        <Routes>
          <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("No grants found.");
    fireEvent.change(screen.getByLabelText("Grant Date"), { target: { value: "2022-01-01" } });
    fireEvent.change(screen.getByLabelText("Work Start Date"), { target: { value: "2021-01-01" } });
    fireEvent.change(screen.getByLabelText("Work End Date"), { target: { value: "2022-01-01" } });
    fireEvent.submit(screen.getByRole("button", { name: "Add Grant" }).closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/grants",
        expect.objectContaining({
          body: JSON.stringify({
            employment_record_id: null,
            employer_name: null,
            nominal_amount: null,
            indexed_amount: "",
            grant_date: "2022-01-01",
            work_start_date: "2021-01-01",
            work_end_date: "2022-01-01",
            notes: null
          })
        })
      );
    });
  });
});
