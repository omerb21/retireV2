import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EmploymentHistoryScreen } from "./EmploymentHistoryScreen";

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

function renderScreen() {
  render(
    <MemoryRouter initialEntries={["/clients/7/employment-history"]}>
      <Routes>
        <Route path="/clients/:clientId/employment-history" element={<EmploymentHistoryScreen />} />
      </Routes>
    </MemoryRouter>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("EmploymentHistoryScreen", () => {
  it("adds, edits, deletes, and saves employment records without calculation calls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse([
          {
            employment_record_id: "ER-1",
            client_id: 7,
            employer_name: "Employer Inc",
            work_start_date: "2010-01-01",
            work_end_date: "2020-01-01",
            is_current: false,
            notes: "Former role"
          }
        ])
      )
      .mockResolvedValueOnce(jsonResponse({ employment_record_id: "ER-2" }))
      .mockResolvedValueOnce(
        jsonResponse([
          {
            employment_record_id: "ER-1",
            client_id: 7,
            employer_name: "Employer Inc",
            work_start_date: "2010-01-01",
            work_end_date: "2020-01-01",
            is_current: false,
            notes: "Former role"
          },
          {
            employment_record_id: "ER-2",
            client_id: 7,
            employer_name: "New Employer",
            work_start_date: "2021-01-01",
            work_end_date: null,
            is_current: true,
            notes: "Current role"
          }
        ])
      )
      .mockResolvedValueOnce(jsonResponse({ employment_record_id: "ER-1" }))
      .mockResolvedValueOnce(
        jsonResponse([
          {
            employment_record_id: "ER-1",
            client_id: 7,
            employer_name: "Updated Employer",
            work_start_date: "2011-01-01",
            work_end_date: null,
            is_current: true,
            notes: "Updated role"
          },
          {
            employment_record_id: "ER-2",
            client_id: 7,
            employer_name: "New Employer",
            work_start_date: "2021-01-01",
            work_end_date: null,
            is_current: true,
            notes: "Current role"
          }
        ])
      )
      .mockResolvedValueOnce(jsonResponse({ deleted: true }))
      .mockResolvedValueOnce(
        jsonResponse([
          {
            employment_record_id: "ER-2",
            client_id: 7,
            employer_name: "New Employer",
            work_start_date: "2021-01-01",
            work_end_date: null,
            is_current: true,
            notes: "Current role"
          }
        ])
      );

    vi.stubGlobal("fetch", fetchMock);
    renderScreen();

    expect(await screen.findByText("Employer Inc")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "New Employer" } });
    fireEvent.change(screen.getByLabelText("Work Start Date"), { target: { value: "2021-01-01" } });
    fireEvent.click(screen.getByLabelText("Current Employment"));
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Current role" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Employment Record" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/employment-records",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            employer_name: "New Employer",
            work_start_date: "2021-01-01",
            work_end_date: null,
            is_current: true,
            notes: "Current role"
          })
        })
      );
    });
    expect(await screen.findByText("New Employer")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit Employment Record" })[0]);
    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "Updated Employer" } });
    fireEvent.change(screen.getByLabelText("Work Start Date"), { target: { value: "2011-01-01" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Updated role" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Employment Record" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/api/clients/7/employment-records/ER-1",
        expect.objectContaining({ method: "PUT" })
      );
    });
    expect(await screen.findByText("Updated Employer")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete Employment Record" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        6,
        "/api/clients/7/employment-records/ER-1",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    const requestedUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(requestedUrls.every((url) => !url.includes("/fixation/validate") && !url.includes("/fixation/calculate"))).toBe(
      true
    );
    expect(screen.getByRole("link", { name: "Back to client detail" })).toHaveAttribute("href", "/clients/7");
  });
});
