import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ActualCapitalizationsScreen } from "./ActualCapitalizationsScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ActualCapitalizationsScreen", () => {
  it("renders existing capitalizations and adds a new capitalization through the backend endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: {
          get: () => "application/json"
        },
        json: async () => [
          {
            capitalization_id: "AC-1",
            client_id: 7,
            amount: 500,
            capitalization_date: "2023-01-01",
            source_label: "Manual",
            notes: "Existing capitalization"
          }
        ]
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: {
          get: () => "application/json"
        },
        json: async () => ({
          capitalization_id: "AC-2",
          client_id: 7,
          amount: 750,
          capitalization_date: "2024-02-01",
          source_label: "Imported",
          notes: "Created capitalization"
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: {
          get: () => "application/json"
        },
        json: async () => [
          {
            capitalization_id: "AC-1",
            client_id: 7,
            amount: 500,
            capitalization_date: "2023-01-01",
            source_label: "Manual",
            notes: "Existing capitalization"
          },
          {
            capitalization_id: "AC-2",
            client_id: 7,
            amount: 750,
            capitalization_date: "2024-02-01",
            source_label: "Imported",
            notes: "Created capitalization"
          }
        ]
      });

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

    expect(await screen.findByRole("heading", { name: "Actual Capitalizations" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Client Name: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText("Capitalization ID: AC-1")).toBeInTheDocument();
    expect(await screen.findByText("Amount: 500")).toBeInTheDocument();
    expect(await screen.findByText("Capitalization Date: 2023-01-01")).toBeInTheDocument();
    expect(await screen.findByText("Source Label: Manual")).toBeInTheDocument();
    expect(await screen.findByText("Notes: Existing capitalization")).toBeInTheDocument();
    expect(await screen.findByText("Edit and delete are unavailable in this workflow.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "750" } });
    fireEvent.change(screen.getByLabelText("Capitalization Date"), { target: { value: "2024-02-01" } });
    fireEvent.change(screen.getByLabelText("Source Label"), { target: { value: "Imported" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Created capitalization" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Actual Capitalization" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/actual-capitalizations",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            amount: 750,
            capitalization_date: "2024-02-01",
            source_label: "Imported",
            notes: "Created capitalization"
          })
        })
      );
    });

    expect(await screen.findByText("Capitalization ID: AC-2")).toBeInTheDocument();
    expect(await screen.findByText("Amount: 750")).toBeInTheDocument();
    expect(await screen.findByText("Capitalization Date: 2024-02-01")).toBeInTheDocument();
    expect(await screen.findByText("Source Label: Imported")).toBeInTheDocument();
    expect(await screen.findByText("Notes: Created capitalization")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to grants" })).toHaveAttribute("href", "/clients/7/grants");
    expect(screen.getByRole("link", { name: "Continue to Fixation Parameters" })).toHaveAttribute("href", "/fixation/input");
  });
});
