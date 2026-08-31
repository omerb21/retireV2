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
            birth_date: null,
            file_status: "file_created",
            professional_identification_status: "identification_incomplete",
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse({
            client_id: 42,
            full_name: "Dana Levi",
            id_number: "001234567",
            birth_date: null,
            file_status: "file_created",
            professional_identification_status: "identification_incomplete",
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

    fireEvent.change(screen.getByLabelText("שם הלקוח"), { target: { value: "Dana Levi" } });
    fireEvent.change(screen.getByLabelText("מספר זהות"), { target: { value: "001234567" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת לקוח" }));

    expect(await screen.findByRole("heading", { name: "פרטי לקוח — M01" })).toBeInTheDocument();
    expect(await screen.findByText("שם מלא: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText("מספר זהות: 001234567")).toBeInTheDocument();
    expect(await screen.findByText("זיהוי מקצועי: זיהוי לא הושלם")).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/clients",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          full_name: "Dana Levi",
          id_number: "001234567",
          birth_date: null,
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

    fireEvent.click(screen.getByRole("button", { name: "שמירת לקוח" }));

    expect(await screen.findByText("יש להזין שם לקוח.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows client-side validation when ID number is missing", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/new"]}>
        <Routes>
          <Route path="/clients/new" element={<CreateClientScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("שם הלקוח"), { target: { value: "Dana Levi" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת לקוח" }));

    expect(await screen.findByText("יש להזין מספר זהות.")).toBeInTheDocument();
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
                loc: ["body", "full_name"],
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

    fireEvent.change(screen.getByLabelText("שם הלקוח"), { target: { value: "Dana Levi" } });
    fireEvent.change(screen.getByLabelText("מספר זהות"), { target: { value: "001234567" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת לקוח" }));

    await waitFor(() => {
      expect(screen.getByText("לא ניתן ליצור את הלקוח.")).toBeInTheDocument();
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

    expect(screen.getByRole("link", { name: "ביטול וחזרה לרשימה" })).toHaveAttribute("href", "/clients");
  });
});
