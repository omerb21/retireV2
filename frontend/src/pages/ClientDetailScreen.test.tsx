import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDetailScreen } from "./ClientDetailScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ClientDetailScreen", () => {
  it("renders client detail data from the backend endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: {
          get: () => "application/json"
        },
        json: async () => ({
          client_id: 7,
          full_name: "Dana Levi",
          id_number: "123456789",
          birth_date: "1985-02-03"
        })
      })
    );

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Client Detail" })).toBeInTheDocument();
    expect(await screen.findByText("Client ID: 7")).toBeInTheDocument();
    expect(await screen.findByText("Full Name: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText("ID Number: 123456789")).toBeInTheDocument();
    expect(await screen.findByText("Birth Date: 1985-02-03")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to client list" })).toHaveAttribute("href", "/clients");
  });

  it("renders a not-found state when the backend returns 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        headers: {
          get: () => "application/json"
        },
        json: async () => ({
          detail: {
            code: "CLIENT_NOT_FOUND",
            message: "Client 999 was not found"
          }
        })
      })
    );

    render(
      <MemoryRouter initialEntries={["/clients/999"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("Client not found.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to client list" })).toHaveAttribute("href", "/clients");
  });
});
