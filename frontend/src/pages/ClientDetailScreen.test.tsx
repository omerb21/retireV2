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
            birth_date: "1985-02-03",
            file_status: "file_created",
            professional_identification_status: "professionally_identified"
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
              id_number: "123456789",
              birth_date: "1985-02-03",
              gender: "female",
              contact_method: "email",
              contact_details: "dana@example.com",
              file_status: "file_created",
              professional_identification_status: "professionally_identified",
              notes: "Existing note"
            }
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
              clearinghouse_snapshot_id: "CHS-1",
              client_id: 7,
              import_date: "2026-06-01",
              source_type: "clearinghouse",
              source_file: "clearinghouse.csv",
              collection_status: "collected",
              collection_notes: "source metadata only",
              created_at: "2026-06-01T00:00:00"
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
          json: async () => [
            {
              document_id: "DOC-1",
              client_id: 7,
              document_type: "161",
              source_type: "document",
              source_file: "161.pdf",
              collection_date: "2026-06-02",
              collection_status: "collected",
              collection_notes: "document metadata only",
              created_at: "2026-06-02T00:00:00"
            }
          ]
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
    expect(await screen.findByText("File Status: file_created")).toBeInTheDocument();
    expect(await screen.findByText("Professional Identification: professionally_identified")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Retirement Planning File" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Retirement Planning Data Matrix" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clearinghouse Snapshots" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Retirement Planning Documents" })).toBeInTheDocument();
    expect(screen.getByText("Retirement Planning Facts")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Calculated Artifacts")).toBeInTheDocument();
    expect(screen.getByText("Workflow Status")).toBeInTheDocument();
    expect(screen.getByText("2026-06-01 - clearinghouse - clearinghouse.csv - collected - source metadata only")).toBeInTheDocument();
    expect(screen.getByText("2026-06-02 - 161 - 161.pdf - collected - document metadata only")).toBeInTheDocument();
    expect(screen.getByLabelText("ID Number")).toHaveValue("123456789");
    expect(screen.getByLabelText("Birth Date")).toHaveValue("1985-02-03");
    expect(screen.getByLabelText("Gender")).toHaveValue("female");
    expect(screen.getByLabelText("Contact Method")).toHaveValue("email");
    expect(screen.getByLabelText("Contact Details")).toHaveValue("dana@example.com");
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
          birth_date: null,
          file_status: "file_created",
          professional_identification_status: "identification_incomplete"
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
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => []
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
            id_number: "123456789",
            birth_date: "1985-02-03",
            gender: "female",
            contact_method: "email",
            contact_details: "dana@example.com",
            file_status: "file_created",
            professional_identification_status: "professionally_identified",
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
    expect(screen.getByText("Professional Identification: identification_incomplete")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("ID Number"), { target: { value: "123456789" } });
    fireEvent.change(screen.getByLabelText("Birth Date"), { target: { value: "1985-02-03" } });
    fireEvent.change(screen.getByLabelText("Gender"), { target: { value: "female" } });
    fireEvent.change(screen.getByLabelText("Contact Method"), { target: { value: "email" } });
    fireEvent.change(screen.getByLabelText("Contact Details"), { target: { value: "dana@example.com" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Saved note" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Profile" }));

    expect(await screen.findByText("Profile saved successfully.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/clients/7/profile",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          id_number: "123456789",
          birth_date: "1985-02-03",
          gender: "female",
          contact_method: "email",
          contact_details: "dana@example.com",
          notes: "Saved note"
        })
      })
    );
    expect(screen.getByText("Professional Identification: professionally_identified")).toBeInTheDocument();
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
            birth_date: null,
            file_status: "file_created",
            professional_identification_status: "identification_incomplete"
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
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => []
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

  it("registers clearinghouse snapshots and retirement planning documents", async () => {
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
          birth_date: null,
          file_status: "file_created",
          professional_identification_status: "identification_incomplete"
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
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => []
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({
          clearinghouse_snapshot_id: "CHS-1",
          client_id: 7,
          import_date: "2026-06-01",
          source_type: "clearinghouse",
          source_file: "clearinghouse.csv",
          collection_status: "collected",
          collection_notes: "source metadata only",
          created_at: "2026-06-01T00:00:00"
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({
          document_id: "DOC-1",
          client_id: 7,
          document_type: "161",
          source_type: "document",
          source_file: "161.pdf",
          collection_date: "2026-06-02",
          collection_status: "collected",
          collection_notes: "document metadata only",
          created_at: "2026-06-02T00:00:00"
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

    expect(await screen.findByText("No clearinghouse snapshots registered.")).toBeInTheDocument();
    expect(screen.getByText("No retirement planning documents registered.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Snapshot Import Date"), { target: { value: "2026-06-01" } });
    fireEvent.change(screen.getByLabelText("Snapshot Source Type"), { target: { value: "clearinghouse" } });
    fireEvent.change(screen.getByLabelText("Snapshot Source File"), { target: { value: "clearinghouse.csv" } });
    fireEvent.change(screen.getByLabelText("Snapshot Collection Status"), { target: { value: "collected" } });
    fireEvent.change(screen.getByLabelText("Snapshot Collection Notes"), {
      target: { value: "source metadata only" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Register Snapshot" }));

    expect(await screen.findByText("Clearinghouse snapshot registered.")).toBeInTheDocument();
    expect(screen.getByText("2026-06-01 - clearinghouse - clearinghouse.csv - collected - source metadata only")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/clearinghouse-snapshots",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          import_date: "2026-06-01",
          source_type: "clearinghouse",
          source_file: "clearinghouse.csv",
          collection_status: "collected",
          collection_notes: "source metadata only"
        })
      })
    );

    fireEvent.change(screen.getByLabelText("Document Type"), { target: { value: "161" } });
    fireEvent.change(screen.getByLabelText("Document Source Type"), { target: { value: "document" } });
    fireEvent.change(screen.getByLabelText("Document Source File"), { target: { value: "161.pdf" } });
    fireEvent.change(screen.getByLabelText("Document Collection Date"), { target: { value: "2026-06-02" } });
    fireEvent.change(screen.getByLabelText("Document Collection Status"), { target: { value: "collected" } });
    fireEvent.change(screen.getByLabelText("Document Collection Notes"), {
      target: { value: "document metadata only" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Register Document" }));

    expect(await screen.findByText("Retirement planning document registered.")).toBeInTheDocument();
    expect(screen.getByText("2026-06-02 - 161 - 161.pdf - collected - document metadata only")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/documents",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          document_type: "161",
          source_type: "document",
          source_file: "161.pdf",
          collection_date: "2026-06-02",
          collection_status: "collected",
          collection_notes: "document metadata only"
        })
      })
    );
  });
});
