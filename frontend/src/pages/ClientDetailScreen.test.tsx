import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDetailScreen } from "./ClientDetailScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ClientDetailScreen", () => {
  it("renders client detail and editable profile data from backend endpoints", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
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
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          statusText: "OK",
          headers: {
            get: () => "application/json"
          },
          json: async () => ({
            profile: {
              client_profile_id: "CP-7",
              client_id: 7,
              birth_date: "1985-02-03",
              gender: "female",
              notes: "Existing note"
            }
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
    expect(screen.getByLabelText("Birth Date")).toHaveValue("1985-02-03");
    expect(screen.getByLabelText("Gender")).toHaveValue("female");
    expect(screen.getByLabelText("Notes")).toHaveValue("Existing note");
    expect(screen.getByRole("button", { name: "Save Profile" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Employment History" })).toHaveAttribute(
      "href",
      "/clients/7/employment-history"
    );
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

  it("saves profile fields through the backend profile endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({
          client_id: 7,
          full_name: "Dana Levi",
          id_number: "123456789",
          birth_date: null
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({ profile: null })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({
          profile: {
            client_profile_id: "CP-7",
            client_id: 7,
            birth_date: "1985-02-03",
            gender: "female",
            notes: "Saved note"
          }
        })
      });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("No client profile has been saved yet.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Birth Date"), { target: { value: "1985-02-03" } });
    fireEvent.change(screen.getByLabelText("Gender"), { target: { value: "female" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Saved note" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Profile" }));

    expect(await screen.findByText("Profile saved successfully.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/clients/7/profile",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          birth_date: "1985-02-03",
          gender: "female",
          notes: "Saved note"
        })
      })
    );
  });

  it("displays backend profile save errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          statusText: "OK",
          headers: { get: () => "application/json" },
          json: async () => ({
            client_id: 7,
            full_name: "Dana Levi",
            id_number: "123456789",
            birth_date: null
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          statusText: "OK",
          headers: { get: () => "application/json" },
          json: async () => ({ profile: null })
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 422,
          statusText: "Unprocessable Entity",
          headers: { get: () => "application/json" },
          json: async () => ({ detail: [{ msg: "Invalid profile value" }] })
        })
    );

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByRole("button", { name: "Save Profile" });
    fireEvent.click(screen.getByRole("button", { name: "Save Profile" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to save profile.")).toBeInTheDocument();
    });
    expect(screen.getByText(/Invalid profile value/)).toBeInTheDocument();
  });
});
