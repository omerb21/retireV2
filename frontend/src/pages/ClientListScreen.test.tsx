import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientListScreen } from "./ClientListScreen";

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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ClientListScreen", () => {
  it("shows Create Client in the empty state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(mockJsonResponse([])));

    render(
      <MemoryRouter>
        <ClientListScreen />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No clients yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Client" })).toHaveAttribute("href", "/clients/new");
  });

  it("shows Create Client when clients exist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        mockJsonResponse([
          {
            client_id: 1,
            full_name: "Jane Doe",
            id_number: "001234567",
            birth_date: "1970-01-01",
            file_status: "file_created",
            professional_identification_status: "professionally_identified",
          },
        ]),
      ),
    );

    render(
      <MemoryRouter>
        <ClientListScreen />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
    expect(await screen.findByText("File Status: file_created")).toBeInTheDocument();
    expect(await screen.findByText("Professional Identification: professionally_identified")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Client" })).toHaveAttribute("href", "/clients/new");
  });

  it("shows an error instead of crashing when the client list response is not an array", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(mockJsonResponse({ clients: [] })));

    render(
      <MemoryRouter>
        <ClientListScreen />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Unable to load clients.")).toBeInTheDocument();
    expect(await screen.findByText("Unexpected clients response shape.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Client" })).toHaveAttribute("href", "/clients/new");
  });
});
