import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CreateClientScreen } from "./CreateClientScreen";
import { ClientDetailScreen } from "./ClientDetailScreen";

function mockJsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Unprocessable Entity",
    headers: {
      get: () => "application/json",
    },
    json: async () => body,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CreateClientScreen", () => {
  it("creates a client and redirects to client detail after successful submit", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          mockJsonResponse({
            client_id: 42,
            full_name: "Dana Levi",
            id_number: "001234567",
            birth_date: "1970-01-01",
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse({
            client_id: 42,
            full_name: "Dana Levi",
            id_number: "001234567",
            birth_date: "1970-01-01",
          }),
        ),
    );

    render(
      <MemoryRouter initialEntries={["/clients/new"]}>
        <Routes>
          <Route path="/clients/new" element={<CreateClientScreen />} />
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Client Name"), { target: { value: "Dana Levi" } });
    fireEvent.change(screen.getByLabelText("ID Number"), { target: { value: "001234567" } });
    fireEvent.change(screen.getByLabelText("Birth Date"), { target: { value: "1970-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Client" }));

    expect(await screen.findByRole("heading", { name: "Client Detail" })).toBeInTheDocument();
    expect(await screen.findByText("Full Name: Dana Levi")).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/clients",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          full_name: "Dana Levi",
          id_number: "001234567",
          birth_date: "1970-01-01",
        }),
      }),
    );
  });

  it("shows client-side validation when required fields are missing", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/new"]}>
        <Routes>
          <Route path="/clients/new" element={<CreateClientScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save Client" }));

    expect(await screen.findByText("Client name is required.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("displays backend validation errors from the create endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        mockJsonResponse(
          {
            detail: [
              {
                type: "missing",
                loc: ["body", "id_number"],
                msg: "Field required",
              },
            ],
          },
          false,
          422,
        ),
      ),
    );

    render(
      <MemoryRouter initialEntries={["/clients/new"]}>
        <Routes>
          <Route path="/clients/new" element={<CreateClientScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Client Name"), { target: { value: "Dana Levi" } });
    fireEvent.change(screen.getByLabelText("ID Number"), { target: { value: "001234567" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Client" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to create client.")).toBeInTheDocument();
    });
    expect(screen.getByText(/Field required/)).toBeInTheDocument();
  });

  it("links cancel back to the client list", () => {
    render(
      <MemoryRouter initialEntries={["/clients/new"]}>
        <Routes>
          <Route path="/clients/new" element={<CreateClientScreen />} />
          <Route path="/clients" element={<div>Client List Placeholder</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Cancel" })).toHaveAttribute("href", "/clients");
  });
});
