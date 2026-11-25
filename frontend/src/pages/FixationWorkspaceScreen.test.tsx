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

    expect(await screen.findByRole("heading", { name: "סביבת קיבוע זכויות" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "פרטי התיק" })).toBeInTheDocument();
    expect(screen.getByText("שם הלקוח: Dana Levi")).toBeInTheDocument();
    expect(screen.getByText("מספר זהות: 123456789")).toBeInTheDocument();
    expect(screen.getByText("מצב תיק תכנון הפרישה: התיק נוצר")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "זיהוי מקצועי" })).toBeInTheDocument();
    expect(screen.getByText("תאריך לידה: 1985-02-03")).toBeInTheDocument();
    expect(screen.getByText('אמצעי קשר: דוא"ל')).toBeInTheDocument();
    expect(screen.getByText("פרטי קשר: dana@example.com")).toBeInTheDocument();
    expect(screen.getByText("מצב זיהוי מקצועי: זוהה מקצועית")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "נתוני המקור לקיבוע זכויות" })).toBeInTheDocument();
    expect(screen.getByText("תקופות העסקה: 1")).toBeInTheDocument();
    expect(screen.getByText("מענקים: 1")).toBeInTheDocument();
    expect(screen.getByText("היוונים בפועל: 1")).toBeInTheDocument();
    expect(screen.getByText("חישובי קיבוע שנשמרו: 1")).toBeInTheDocument();
    expect(screen.getByText("חישוב קיבוע אחרון: הושלם בהצלחה / 2026-06-03T00:00:00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "אסמכתאות שנאספו" })).toBeInTheDocument();
    expect(screen.getByText("דוחות מסלקה: 1")).toBeInTheDocument();
    expect(screen.getByText("מצב איסוף דוחות: נאסף: 1")).toBeInTheDocument();
    expect(screen.getByText("מסמכי תכנון פרישה: 1")).toBeInTheDocument();
    expect(screen.getByText("מצב איסוף מסמכים: נאסף: 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מצב אימות" })).toBeInTheDocument();
    expect(screen.getByText("מצב אימות דוחות: אומת: 1")).toBeInTheDocument();
    expect(screen.getByText("מצב אימות מסמכים: נדרשת בדיקה: 1")).toBeInTheDocument();
    expect(screen.getByText("דוח clearinghouse.csv: אומת - advisor checked - 2026-06-04T00:00:00")).toBeInTheDocument();
    expect(screen.getByText("מסמך 161: נדרשת בדיקה - check employer detail - 2026-06-05T00:00:00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מידע חסר" })).toBeInTheDocument();
    expect(screen.getByText("נתונים חסרים: 0")).toBeInTheDocument();
    expect(screen.getByText("מסמכים חסרים: 1")).toBeInTheDocument();
    expect(screen.getByText("מסמך - Pension proof - התבקש - client to provide")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "פתיחת תקופות העסקה" })).toHaveAttribute("href", "/clients/7/employment-history");
    expect(screen.getByRole("link", { name: "פתיחת נתוני קיבוע זכויות" })).toHaveAttribute("href", "/clients/7/fixation/input");
    expect(screen.getByRole("link", { name: "פתיחת כלי איסוף המידע" })).toHaveAttribute("href", "/clients/7");
    expect(screen.getByRole("link", { name: "פתיחת כלי המידע החסר" })).toHaveAttribute("href", "/clients/7");
  });
});
