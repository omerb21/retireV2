import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ActualCapitalizationsScreen } from "./ActualCapitalizationsScreen";

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

describe("ActualCapitalizationsScreen", () => {
  it("adds, edits, deletes, and saves capitalizations without calculation calls", async () => {
    const firstCapitalization = {
      capitalization_id: "AC-1",
      client_id: 7,
      amount: 500,
      capitalization_date: "2023-01-01",
      source_label: "Manual",
      source_basis: null,
      planner_assertion: null,
      planner_assertion_basis: null,
      notes: "Existing capitalization"
    };
    const secondCapitalization = {
      capitalization_id: "AC-2",
      client_id: 7,
      amount: 750,
      capitalization_date: "2024-02-01",
      source_label: "Imported",
      source_basis: "capitalization certificate",
      planner_assertion: "advisor confirmed amount",
      planner_assertion_basis: "reviewed certificate",
      notes: "Created capitalization"
    };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([firstCapitalization]))
      .mockResolvedValueOnce(jsonResponse(secondCapitalization))
      .mockResolvedValueOnce(jsonResponse([firstCapitalization, secondCapitalization]))
      .mockResolvedValueOnce(jsonResponse({ ...firstCapitalization, amount: 650, source_label: "Updated" }))
      .mockResolvedValueOnce(jsonResponse([{ ...firstCapitalization, amount: 650, source_label: "Updated" }, secondCapitalization]))
      .mockResolvedValueOnce(jsonResponse({ deleted: true }))
      .mockResolvedValueOnce(jsonResponse([secondCapitalization]));

    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/clients/7/actual-capitalizations", state: { clientName: "Dana Levi" } }
        ]}
      >
        <Routes>
          <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("Capitalization ID: AC-1")).toBeInTheDocument();
    expect(screen.queryByText("Edit and delete are unavailable in this workflow.")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "750" } });
    fireEvent.change(screen.getByLabelText("Capitalization Date"), { target: { value: "2024-02-01" } });
    fireEvent.change(screen.getByLabelText("Source Label"), { target: { value: "Imported" } });
    fireEvent.change(screen.getByLabelText("Source Basis"), { target: { value: "capitalization certificate" } });
    fireEvent.change(screen.getByLabelText("Planner Assertion"), { target: { value: "advisor confirmed amount" } });
    fireEvent.change(screen.getByLabelText("Planner Assertion Basis"), { target: { value: "reviewed certificate" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Created capitalization" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Actual Capitalization" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/actual-capitalizations",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            amount: "750",
            capitalization_date: "2024-02-01",
            source_label: "Imported",
            source_basis: "capitalization certificate",
            planner_assertion: "advisor confirmed amount",
            planner_assertion_basis: "reviewed certificate",
            notes: "Created capitalization"
          })
        })
      );
    });
    expect(await screen.findByText("Capitalization ID: AC-2")).toBeInTheDocument();
    expect(await screen.findByText("Source Basis: capitalization certificate")).toBeInTheDocument();
    expect(await screen.findByText("Planner Assertion: advisor confirmed amount")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit Actual Capitalization" })[0]);
    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "650" } });
    fireEvent.change(screen.getByLabelText("Source Label"), { target: { value: "Updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Actual Capitalization" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/api/clients/7/actual-capitalizations/AC-1",
        expect.objectContaining({ method: "PUT" })
      );
    });
    expect(await screen.findByText("Amount: 650")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete Actual Capitalization" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        6,
        "/api/clients/7/actual-capitalizations/AC-1",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    const requestedUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(requestedUrls.every((url) => !url.includes("/fixation/validate") && !url.includes("/fixation/calculate"))).toBe(
      true
    );
    expect(screen.getByRole("link", { name: "Back to grants" })).toHaveAttribute("href", "/clients/7/grants");
    expect(screen.getByRole("link", { name: "Continue to Fixation Parameters" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/input"
    );
  });

  it("preserves blank numeric input for backend validation instead of coercing it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ detail: [{ msg: "amount must be numeric" }] }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7/actual-capitalizations"]}>
        <Routes>
          <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("No actual capitalizations found.");
    fireEvent.change(screen.getByLabelText("Capitalization Date"), { target: { value: "2024-02-01" } });
    fireEvent.submit(
      screen.getByRole("button", { name: "Add Actual Capitalization" }).closest("form") as HTMLFormElement
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/actual-capitalizations",
        expect.objectContaining({
          body: JSON.stringify({
            amount: "",
            capitalization_date: "2024-02-01",
            source_label: null,
            source_basis: null,
            planner_assertion: null,
            planner_assertion_basis: null,
            notes: null
          })
        })
      );
    });
  });
});
