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
  it("shows יצירת לקוח in the empty state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(mockJsonResponse([])));

    render(
      <MemoryRouter>
        <ClientListScreen />
      </MemoryRouter>,
    );

    expect(await screen.findByText("טרם נוצרו לקוחות")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "יצירת לקוח" })).toHaveAttribute("href", "/clients/new");
  });

  it("shows יצירת לקוח when clients exist", async () => {
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
    expect(await screen.findByText("מצב תיק: התיק נוצר")).toBeInTheDocument();
    expect(await screen.findByText("מצב זיהוי מקצועי: זוהה מקצועית")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "יצירת לקוח" })).toHaveAttribute("href", "/clients/new");
  });

  it("shows an error instead of crashing when the client list response is not an array", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(mockJsonResponse({ clients: [] })));

    render(
      <MemoryRouter>
        <ClientListScreen />
      </MemoryRouter>,
    );

    expect(await screen.findByText("לא ניתן לטעון את רשימת הלקוחות.")).toBeInTheDocument();
    expect(await screen.findByText("Unexpected clients response shape.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "יצירת לקוח" })).toHaveAttribute("href", "/clients/new");
  });
});
