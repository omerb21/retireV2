import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FixationWorkspaceScreen } from "./FixationWorkspaceScreen";

afterEach(() => {
  vi.unstubAllGlobals();
});

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

describe("FixationWorkspaceScreen", () => {
  it("renders consolidated Package 1 through Package 3 and fixation workflow information", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({
          client_id: 7,
          full_name: "Dana Levi",
          id_number: "123456789",
          birth_date: "1985-02-03",
          file_status: "file_created",
          professional_identification_status: "professionally_identified"
        }))
        .mockResolvedValueOnce(jsonResponse({
          profile: {
            client_profile_id: "CP-7",
            client_id: 7,
            id_number: "123456789",
            birth_date: "1985-02-03",
            gender: "female",
            contact_method: "email",
            contact_details: "dana@example.com",
            notes: "Existing note",
            file_status: "file_created",
            professional_identification_status: "professionally_identified"
          }
        }))
        .mockResolvedValueOnce(jsonResponse([
          {
            employment_record_id: "EMP-1",
            client_id: 7,
            employer_name: "Acme",
            work_start_date: "2020-01-01",
            work_end_date: null,
            is_current: true,
            notes: null
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            grant_id: "GR-1",
            client_id: 7,
            employment_record_id: "EMP-1",
            employer_name: "Acme",
            nominal_amount: "10000.00",
            indexed_amount: "12000.00",
            grant_date: "2024-01-01",
            work_start_date: "2020-01-01",
            work_end_date: "2023-12-31",
            notes: null
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            capitalization_id: "AC-1",
            client_id: 7,
            amount: "5000.00",
            capitalization_date: "2024-06-01",
            source_label: "Capitalization",
            notes: null
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            run_id: 42,
            status: "success",
            calculation_version: "v1",
            created_at: "2026-06-03T00:00:00"
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            clearinghouse_snapshot_id: "CHS-1",
            client_id: 7,
            import_date: "2026-06-01",
            source_type: "clearinghouse",
            source_file: "clearinghouse.csv",
            collection_status: "collected",
            collection_notes: "source metadata only",
            verification_status: "verified",
            verification_notes: "advisor checked",
            verified_at: "2026-06-04T00:00:00",
            created_at: "2026-06-01T00:00:00"
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            document_id: "DOC-1",
            client_id: 7,
            document_type: "161",
            source_type: "document",
            source_file: "161.pdf",
            collection_date: "2026-06-02",
            collection_status: "collected",
            collection_notes: "document metadata only",
            verification_status: "requires_review",
            verification_notes: "check employer detail",
            verified_at: "2026-06-05T00:00:00",
            created_at: "2026-06-02T00:00:00"
          }
        ]))
        .mockResolvedValueOnce(jsonResponse([
          {
            missing_data_item_id: "MD-1",
            client_id: 7,
            missing_item_type: "document",
            missing_item_label: "Pension proof",
            missing_status: "requested",
            notes: "client to provide",
            created_at: "2026-06-06T00:00:00"
          }
        ]))
    );

    render(
      <MemoryRouter initialEntries={["/clients/7/fixation/workspace"]}>
        <Routes>
          <Route path="/clients/:clientId/fixation/workspace" element={<FixationWorkspaceScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Fixation Activity Workspace" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "File Foundation" })).toBeInTheDocument();
    expect(screen.getByText("Client Name: Dana Levi")).toBeInTheDocument();
    expect(screen.getByText("ID Number: 123456789")).toBeInTheDocument();
    expect(screen.getByText("Retirement Planning File Status: file_created")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Professional Identification" })).toBeInTheDocument();
    expect(screen.getByText("Birth Date: 1985-02-03")).toBeInTheDocument();
    expect(screen.getByText("Contact Method: email")).toBeInTheDocument();
    expect(screen.getByText("Contact Details: dana@example.com")).toBeInTheDocument();
    expect(screen.getByText("Professional Identification Status: professionally_identified")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fixation Activity Source Data" })).toBeInTheDocument();
    expect(screen.getByText("Employment Records: 1")).toBeInTheDocument();
    expect(screen.getByText("Grants: 1")).toBeInTheDocument();
    expect(screen.getByText("Actual Capitalizations: 1")).toBeInTheDocument();
    expect(screen.getByText("Saved Fixation Runs: 1")).toBeInTheDocument();
    expect(screen.getByText("Latest Fixation Run: success / 2026-06-03T00:00:00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Collected Evidence" })).toBeInTheDocument();
    expect(screen.getByText("Clearinghouse Snapshots: 1")).toBeInTheDocument();
    expect(screen.getByText("Snapshot Collection Status: collected: 1")).toBeInTheDocument();
    expect(screen.getByText("Retirement Planning Documents: 1")).toBeInTheDocument();
    expect(screen.getByText("Document Collection Status: collected: 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Verification State" })).toBeInTheDocument();
    expect(screen.getByText("Snapshot Verification Status: verified: 1")).toBeInTheDocument();
    expect(screen.getByText("Document Verification Status: requires_review: 1")).toBeInTheDocument();
    expect(screen.getByText("Snapshot clearinghouse.csv: verified - advisor checked - 2026-06-04T00:00:00")).toBeInTheDocument();
    expect(screen.getByText("Document 161: requires_review - check employer detail - 2026-06-05T00:00:00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Missing Information" })).toBeInTheDocument();
    expect(screen.getByText("Missing Data Items: 0")).toBeInTheDocument();
    expect(screen.getByText("Missing Document Items: 1")).toBeInTheDocument();
    expect(screen.getByText("document - Pension proof - requested - client to provide")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Employment History" })).toHaveAttribute("href", "/clients/7/employment-history");
    expect(screen.getByRole("link", { name: "Open Fixation Parameters" })).toHaveAttribute("href", "/clients/7/fixation/input");
    expect(screen.getByRole("link", { name: "Open Collection Tools" })).toHaveAttribute("href", "/clients/7");
    expect(screen.getByRole("link", { name: "Open Missing Information Tools" })).toHaveAttribute("href", "/clients/7");
  });
});
