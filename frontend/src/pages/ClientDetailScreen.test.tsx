import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDetailScreen } from "./ClientDetailScreen";
import {
  workflowLifecyclePolicy,
  workflowNavigationPolicy
} from "../components/ProfessionalWorkflowOverview";

vi.mock("./RetirementPlanningFactsSection", () => ({
  RetirementPlanningFactsSection: () => (
    <section aria-label="Retirement Planning Facts mock">Retirement Planning Facts</section>
  )
}));


vi.mock("./PlannerAssumptionsSection", () => ({
  PlannerAssumptionsSection: () => (
    <section aria-label="Planner Assumptions mock">Planner Assumptions</section>
  )
}));

vi.mock("./AdvisoryMissingInformationSection", () => ({
  AdvisoryMissingInformationSection: () => (
    <section aria-label="Advisory Missing Information mock">Advisory Missing Information</section>
  )
}));

vi.mock("./RetirementPlanningConsolidatedReviewSection", () => ({
  RetirementPlanningConsolidatedReviewSection: () => (
    <section aria-label="Retirement Planning Consolidated Review mock">
      Retirement Planning Consolidated Review
    </section>
  )
}));

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
              verification_status: "unverified",
              verification_notes: null,
              verified_at: null,
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
              verification_status: "unverified",
              verification_notes: null,
              verified_at: null,
              created_at: "2026-06-02T00:00:00"
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
              missing_data_item_id: "MD-1",
              client_id: 7,
              missing_item_type: "data",
              missing_item_label: "Tax credits",
              missing_status: "missing",
              notes: "interview required",
              created_at: "2026-06-03T00:00:00"
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

    expect(await screen.findByRole("heading", { name: "פרטי לקוח — M01" })).toBeInTheDocument();
    expect(await screen.findByText("מזהה לקוח: 7")).toBeInTheDocument();
    expect(await screen.findByText("שם מלא: Dana Levi")).toBeInTheDocument();
    expect(await screen.findByText("מספר זהות: 123456789")).toBeInTheDocument();
    expect(await screen.findByText("מצב תיק: התיק נוצר")).toBeInTheDocument();
    expect(await screen.findByText("זיהוי מקצועי: זוהה מקצועית")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "תיק תכנון הפרישה" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מפת נתוני תכנון הפרישה" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "תמונות מצב מהמסלקה" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מסמכי תכנון פרישה" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מעקב אחר מידע חסר" })).toBeInTheDocument();
    expect(screen.getByText("Retirement Planning Facts")).toBeInTheDocument();
    expect(screen.queryByText("Pension Analysis Records")).not.toBeInTheDocument();
    expect(screen.getByText("מסמכים")).toBeInTheDocument();
    expect(screen.getByText("תוצרים מחושבים")).toBeInTheDocument();
    expect(screen.getByText("מצב תהליך העבודה")).toBeInTheDocument();
    expect(screen.getByText("01/06/2026 - clearinghouse - clearinghouse.csv - נאסף - source metadata only")).toBeInTheDocument();
    expect(screen.getByText("02/06/2026 - 161 - 161.pdf - נאסף - document metadata only")).toBeInTheDocument();
    expect(screen.getAllByText("מצב אימות: טרם אומת")).toHaveLength(2);
    expect(screen.getByText("נתון - Tax credits - חסר - interview required")).toBeInTheDocument();
    expect(screen.getByLabelText("מספר זהות")).toHaveValue("123456789");
    expect(screen.getByLabelText("תאריך לידה")).toHaveValue("03/02/1985");
    expect(screen.getByLabelText("מגדר")).toHaveValue("female");
    expect(screen.getByLabelText("אמצעי קשר")).toHaveValue("email");
    expect(screen.getByLabelText("פרטי קשר")).toHaveValue("dana@example.com");
    expect(screen.getByLabelText("הערות")).toHaveValue("Existing note");
    expect(screen.getByRole("button", { name: "שמירת פרופיל" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "היסטוריית תעסוקה" })).toHaveAttribute(
      "href",
      "/clients/7/employment-history"
    );
    expect(screen.getByRole("link", { name: "תמונת מקורות פנסיוניים ופיננסיים" })).toHaveAttribute(
      "href",
      "/clients/7/professional-sources"
    );
    expect(screen.getByRole("link", { name: "חזרה לרשימת הלקוחות" })).toHaveAttribute("href", "/clients");
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

    expect(await screen.findByText("הלקוח לא נמצא.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "חזרה לרשימת הלקוחות" })).toHaveAttribute("href", "/clients");
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

    expect(await screen.findByText("טרם נשמר פרופיל לקוח.")).toBeInTheDocument();
    expect(screen.getByText("זיהוי מקצועי: זיהוי לא הושלם")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("מספר זהות"), { target: { value: "123456789" } });
    fireEvent.change(screen.getByLabelText("תאריך לידה"), { target: { value: "03/02/1985" } });
    fireEvent.change(screen.getByLabelText("מגדר"), { target: { value: "female" } });
    fireEvent.change(screen.getByLabelText("אמצעי קשר"), { target: { value: "email" } });
    fireEvent.change(screen.getByLabelText("פרטי קשר"), { target: { value: "dana@example.com" } });
    fireEvent.change(screen.getByLabelText("הערות"), { target: { value: "Saved note" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת פרופיל" }));

    expect(await screen.findByText("הפרופיל נשמר בהצלחה.")).toBeInTheDocument();
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
    expect(screen.getByText("זיהוי מקצועי: זוהה מקצועית")).toBeInTheDocument();
  });

  it("places the consolidated review inside the data matrix after maintenance sections and before documents", async () => {
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
          ok: true,
          status: 200,
          statusText: "OK",
          headers: { get: () => "application/json" },
          json: async () => []
        })
    );

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    const matrixHeading = await screen.findByRole("heading", { name: "מפת נתוני תכנון הפרישה" });
    const matrix = within(matrixHeading.closest("section") as HTMLElement);
    const entries = matrix.getAllByRole("listitem").map((item) => item.textContent);

    expect(entries).toEqual([
      "Retirement Planning Facts",
      "Planner Assumptions",
      "Advisory Missing Information",
      "Retirement Planning Consolidated Review",
      "מסמכים",
      "תוצרים מחושבים",
      "מצב תהליך העבודה"
    ]);
    expect(matrix.getByLabelText("Retirement Planning Consolidated Review mock")).toBeInTheDocument();
    expect(matrix.queryByRole("link", { name: /consolidated review/i })).not.toBeInTheDocument();
    expect(matrix.queryByRole("dialog")).not.toBeInTheDocument();
    expect(matrix.queryByText(/route-query|dedicated screen|drawer/i)).not.toBeInTheDocument();
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

    await screen.findByRole("button", { name: "שמירת פרופיל" });
    fireEvent.click(screen.getByRole("button", { name: "שמירת פרופיל" }));

    await waitFor(() => {
      expect(screen.getByText("לא ניתן לשמור את הפרופיל.")).toBeInTheDocument();
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
          verification_status: "unverified",
          verification_notes: null,
          verified_at: null,
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
          verification_status: "unverified",
          verification_notes: null,
          verified_at: null,
          created_at: "2026-06-02T00:00:00"
        })
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
          verification_status: "verified",
          verification_notes: "advisor checked source",
          verified_at: "2026-06-03T00:00:00",
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
          verification_status: "requires_review",
          verification_notes: "needs advisor review",
          verified_at: "2026-06-03T00:00:00",
          created_at: "2026-06-02T00:00:00"
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => ({
          missing_data_item_id: "MD-1",
          client_id: 7,
          missing_item_type: "document",
          missing_item_label: "Form 161",
          missing_status: "requested",
          notes: "client to provide",
          created_at: "2026-06-03T00:00:00"
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

    expect(await screen.findByText("לא נרשמו תמונות מצב מהמסלקה.")).toBeInTheDocument();
    expect(screen.getByText("לא נרשמו מסמכי תכנון פרישה.")).toBeInTheDocument();
    expect(screen.getByText("לא נרשמו פריטים חסרים.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("תאריך קליטת תמונת המצב"), { target: { value: "01/06/2026" } });
    fireEvent.change(screen.getByLabelText("סוג מקור של תמונת המצב"), { target: { value: "clearinghouse" } });
    fireEvent.change(screen.getByLabelText("קובץ המקור של תמונת המצב"), { target: { value: "clearinghouse.csv" } });
    fireEvent.change(screen.getByLabelText("מצב איסוף תמונת המצב"), { target: { value: "collected" } });
    fireEvent.change(screen.getByLabelText("הערות לאיסוף תמונת המצב"), {
      target: { value: "source metadata only" }
    });
    fireEvent.click(screen.getByRole("button", { name: "רישום תמונת מצב" }));

    expect(await screen.findByText("תמונת המצב מהמסלקה נרשמה.")).toBeInTheDocument();
    expect(screen.getByText("01/06/2026 - clearinghouse - clearinghouse.csv - נאסף - source metadata only")).toBeInTheDocument();
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

    fireEvent.change(screen.getByLabelText("סוג מסמך"), { target: { value: "161" } });
    fireEvent.change(screen.getByLabelText("סוג מקור המסמך"), { target: { value: "document" } });
    fireEvent.change(screen.getByLabelText("קובץ מקור המסמך"), { target: { value: "161.pdf" } });
    fireEvent.change(screen.getByLabelText("תאריך איסוף המסמך"), { target: { value: "02/06/2026" } });
    fireEvent.change(screen.getByLabelText("מצב איסוף המסמך"), { target: { value: "collected" } });
    fireEvent.change(screen.getByLabelText("הערות לאיסוף המסמך"), {
      target: { value: "document metadata only" }
    });
    fireEvent.click(screen.getByRole("button", { name: "רישום מסמך" }));

    expect(await screen.findByText("מסמך תכנון הפרישה נרשם.")).toBeInTheDocument();
    expect(screen.getByText("02/06/2026 - 161 - 161.pdf - נאסף - document metadata only")).toBeInTheDocument();
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

    fireEvent.change(screen.getByLabelText("מצב אימות תמונת המצב"), { target: { value: "verified" } });
    fireEvent.change(screen.getByLabelText("הערות אימות לתמונת המצב"), {
      target: { value: "advisor checked source" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת אימות תמונת המצב" }));

    expect(await screen.findByText("מצב האימות נשמר.")).toBeInTheDocument();
    expect(screen.getByText((_content, element) => (
      element?.textContent === "מצב אימות: אומת"
    ))).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/clearinghouse-snapshots/CHS-1/verification",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          verification_status: "verified",
          verification_notes: "advisor checked source"
        })
      })
    );

    fireEvent.change(screen.getByLabelText("מצב אימות המסמך"), { target: { value: "requires_review" } });
    fireEvent.change(screen.getByLabelText("הערות אימות למסמך"), {
      target: { value: "needs advisor review" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת אימות המסמך" }));

    expect(await screen.findByText("מצב אימות: נדרשת בדיקה")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/documents/DOC-1/verification",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          verification_status: "requires_review",
          verification_notes: "needs advisor review"
        })
      })
    );

    fireEvent.change(screen.getByLabelText("סוג פריט חסר"), { target: { value: "document" } });
    fireEvent.change(screen.getByLabelText("תיאור הפריט החסר"), { target: { value: "Form 161" } });
    fireEvent.change(screen.getByLabelText("מצב הפריט החסר"), { target: { value: "requested" } });
    fireEvent.change(screen.getByLabelText("הערות לפריט החסר"), { target: { value: "client to provide" } });
    fireEvent.click(screen.getByRole("button", { name: "רישום פריט חסר" }));

    expect(await screen.findByText("הפריט החסר נרשם.")).toBeInTheDocument();
    expect(screen.getByText("מסמך - Form 161 - התבקש - client to provide")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/missing-items",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          missing_item_type: "document",
          missing_item_label: "Form 161",
          missing_status: "requested",
          notes: "client to provide"
        })
      })
    );
  });

  it("invalidates readiness context after an M01 save and accepts exactly one fresh response", async () => {
    let resolveFreshContext!: (response: Response) => void;
    const freshContext = new Promise<Response>((resolve) => {
      resolveFreshContext = resolve;
    });
    let contextReads = 0;
    const response = (body: unknown): Response => ({
      ok: true,
      status: 200,
      statusText: "OK",
      headers: { get: () => "application/json" },
      json: async () => body,
      text: async () => JSON.stringify(body)
    }) as unknown as Response;
    const caseItem = {
      client_id: 7,
      display_name: "Dana Levi",
      id_number: "123456789",
      birth_date: "1985-02-03",
      gender: "female",
      employment_status: "salaried_employee",
      planned_retirement_date: null,
      planned_retirement_age: 67,
      lifecycle_status: "draft",
      completeness: {
        status: "complete",
        missing_field_ids: [],
        conflicting_field_ids: []
      },
      updated_at: "2026-10-21T00:00:00Z"
    };
    const readyContext = (code?: string) => ({
      schema_version: "RTDIR_PLANNING_CONTEXT_V1",
      client_id: 7,
      planning_calculation_input_fingerprint: "planning:7",
      planning_input_ready: code === undefined,
      retirement_target_date: "2047-01-01",
      retirement_target_ready: code === undefined,
      blocking_facts: code === undefined ? [] : [{ source_id: null, code }]
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/clients/7" && method === "GET") {
        return Promise.resolve(response({
          client_id: 7,
          full_name: "Dana Levi",
          id_number: "123456789",
          birth_date: "1985-02-03",
          file_status: "file_created",
          professional_identification_status: "professionally_identified",
          m01_case: caseItem
        }));
      }
      if (url === "/api/clients/7/profile" && method === "GET") {
        return Promise.resolve(response({ profile: null }));
      }
      if (
        method === "GET"
        && (
          url === "/api/clients/7/clearinghouse-snapshots"
          || url === "/api/clients/7/documents"
          || url === "/api/clients/7/missing-items"
        )
      ) {
        return Promise.resolve(response([]));
      }
      if (url === "/api/clients/7/retirement-income-readiness/context" && method === "GET") {
        contextReads += 1;
        return contextReads === 1
          ? Promise.resolve(response(readyContext()))
          : freshContext;
      }
      if (url === "/api/clients/7/case" && method === "PUT") {
        return Promise.resolve(response(caseItem));
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("שם מלא: Dana Levi")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/READY_TO_CONTINUE/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(await screen.findByText("נתוני תיק הלקוח נשמרו.")).toBeInTheDocument();
    await waitFor(() => expect(contextReads).toBe(2));
    expect(screen.getByText("טוען מצב מוכנות עדכני…")).toBeInTheDocument();
    expect(screen.getAllByText(/NOT_EVALUATED/).length).toBeGreaterThanOrEqual(2);

    await act(async () => {
      resolveFreshContext(response(readyContext("FRESH_POST_SAVE_BLOCKER")));
    });
    expect(await screen.findByText("FRESH_POST_SAVE_BLOCKER")).toBeInTheDocument();
    expect(contextReads).toBe(2);
  });

  it.each(["case", "profile"] as const)(
    "kills and restores the screen-owned revision increment after a successful %s save",
    async (saveKind) => {
      const runLifecycle = async () => {
        let resolveFreshContext!: (response: Response) => void;
        const freshContext = new Promise<Response>((resolve) => {
          resolveFreshContext = resolve;
        });
        const response = (body: unknown): Response => ({
          ok: true,
          status: 200,
          statusText: "OK",
          headers: { get: () => "application/json" },
          json: async () => body,
          text: async () => JSON.stringify(body)
        }) as unknown as Response;
        const caseItem = {
          client_id: 7,
          display_name: "Lifecycle Client",
          id_number: "123456789",
          birth_date: "1985-02-03",
          gender: "female",
          employment_status: "salaried_employee",
          planned_retirement_date: null,
          planned_retirement_age: 67,
          lifecycle_status: "draft",
          completeness: { status: "complete", missing_field_ids: [], conflicting_field_ids: [] },
          updated_at: "2026-10-21T00:00:00Z"
        };
        const profile = {
          client_profile_id: "CP-7",
          client_id: 7,
          id_number: "123456789",
          birth_date: "1985-02-03",
          gender: "female",
          contact_method: "email",
          contact_details: "planner@example.com",
          notes: null,
          file_status: "file_created",
          professional_identification_status: "professionally_identified",
          m01_case: caseItem
        };
        let contextReads = 0;
        let oldSignal: AbortSignal | undefined;
        const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
          const url = String(input);
          const method = init?.method ?? "GET";
          if (url === "/api/clients/7" && method === "GET") {
            return Promise.resolve(response({
              client_id: 7,
              full_name: caseItem.display_name,
              id_number: caseItem.id_number,
              birth_date: caseItem.birth_date,
              file_status: "file_created",
              professional_identification_status: "professionally_identified",
              m01_case: caseItem
            }));
          }
          if (url === "/api/clients/7/profile" && method === "GET") {
            return Promise.resolve(response({ profile }));
          }
          if (
            method === "GET"
            && ["clearinghouse-snapshots", "documents", "missing-items"].some((part) => url.endsWith(part))
          ) {
            return Promise.resolve(response([]));
          }
          if (url === "/api/clients/7/retirement-income-readiness/context" && method === "GET") {
            contextReads += 1;
            if (contextReads === 1) {
              oldSignal = init?.signal ?? undefined;
              return Promise.resolve(response({
                schema_version: "RTDIR_PLANNING_CONTEXT_V1",
                client_id: 7,
                planning_calculation_input_fingerprint: "before-save",
                planning_input_ready: true,
                retirement_target_date: "2047-01-01",
                retirement_target_ready: true,
                blocking_facts: []
              }));
            }
            return freshContext;
          }
          if (url === "/api/clients/7/case" && method === "PUT") {
            return Promise.resolve(response(caseItem));
          }
          if (url === "/api/clients/7/profile" && method === "PUT") {
            return Promise.resolve(response({ profile }));
          }
          throw new Error(`Unexpected request: ${method} ${url}`);
        });
        vi.stubGlobal("fetch", fetchMock);
        const view = render(
          <MemoryRouter initialEntries={["/clients/7"]}>
            <Routes><Route path="/clients/:clientId" element={<ClientDetailScreen />} /></Routes>
          </MemoryRouter>
        );
        try {
          expect(await screen.findByText("שם מלא: Lifecycle Client")).toBeInTheDocument();
          await waitFor(() => expect(contextReads).toBe(1));
          fireEvent.click(screen.getByRole("button", {
            name: saveKind === "case" ? "שמירת נתוני התיק" : "שמירת פרופיל"
          }));
          expect(await screen.findByText(
            saveKind === "case" ? "נתוני תיק הלקוח נשמרו." : "הפרופיל נשמר בהצלחה."
          )).toBeInTheDocument();
          await act(async () => Promise.resolve());
          const loadingVisible = screen.queryByText("טוען מצב מוכנות עדכני…") !== null;
          if (contextReads === 2) {
            resolveFreshContext(response({
              schema_version: "RTDIR_PLANNING_CONTEXT_V1",
              client_id: 7,
              planning_calculation_input_fingerprint: "after-save",
              planning_input_ready: false,
              retirement_target_date: "2047-01-01",
              retirement_target_ready: false,
              blocking_facts: [{ source_id: null, code: `FRESH_${saveKind.toUpperCase()}_BLOCKER` }]
            }));
            await screen.findByText(`FRESH_${saveKind.toUpperCase()}_BLOCKER`);
          }
          return { contextReads, loadingVisible, oldSignalAborted: oldSignal?.aborted === true };
        } finally {
          view.unmount();
        }
      };

      const ordinary = async () => {
        const facts = await runLifecycle();
        expect(facts.contextReads).toBe(2);
        expect(facts.loadingVisible).toBe(true);
        expect(facts.oldSignalAborted).toBe(true);
      };

      await ordinary();
      let revisionMutationReached = false;
      const mutation = vi.spyOn(workflowLifecyclePolicy, "nextReadinessContextRevision")
        .mockImplementation((current) => {
          revisionMutationReached = true;
          return current;
        });
      let killed = false;
      let failureReason = "";
      try {
        await ordinary();
      } catch (error) {
        killed = true;
        failureReason = String(error);
      } finally {
        mutation.mockRestore();
      }
      expect(revisionMutationReached).toBe(true);
      expect(killed).toBe(true);
      expect(failureReason).toContain("to be 2");
      await ordinary();
    }
  );

  it.each(["success", "failure"] as const)(
    "rejects a late obsolete readiness %s after a real successful profile save",
    async (lateOutcome) => {
      let resolveOld!: (response: Response) => void;
      let rejectOld!: (reason: unknown) => void;
      const oldContext = new Promise<Response>((resolve, reject) => {
        resolveOld = resolve;
        rejectOld = reject;
      });
      const response = (body: unknown): Response => ({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: { get: () => "application/json" },
        json: async () => body,
        text: async () => JSON.stringify(body)
      }) as unknown as Response;
      const caseItem = {
        client_id: 7,
        display_name: "Profile Client",
        id_number: "123456789",
        birth_date: "1985-02-03",
        gender: "female",
        employment_status: "salaried_employee",
        planned_retirement_date: null,
        planned_retirement_age: 67,
        lifecycle_status: "draft",
        completeness: { status: "complete", missing_field_ids: [], conflicting_field_ids: [] },
        updated_at: "2026-10-21T00:00:00Z"
      };
      const profile = {
        client_profile_id: "CP-7",
        client_id: 7,
        id_number: "123456789",
        birth_date: "1985-02-03",
        gender: "female",
        contact_method: "email",
        contact_details: "profile@example.com",
        notes: null,
        file_status: "file_created",
        professional_identification_status: "professionally_identified",
        m01_case: caseItem
      };
      let contextReads = 0;
      let oldSignal: AbortSignal | undefined;
      const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url === "/api/clients/7" && method === "GET") {
          return Promise.resolve(response({
            client_id: 7,
            full_name: caseItem.display_name,
            id_number: caseItem.id_number,
            birth_date: caseItem.birth_date,
            file_status: "file_created",
            professional_identification_status: "professionally_identified",
            m01_case: caseItem
          }));
        }
        if (url === "/api/clients/7/profile" && method === "GET") return Promise.resolve(response({ profile }));
        if (url === "/api/clients/7/profile" && method === "PUT") return Promise.resolve(response({ profile }));
        if (method === "GET" && ["clearinghouse-snapshots", "documents", "missing-items"].some((part) => url.endsWith(part))) {
          return Promise.resolve(response([]));
        }
        if (url === "/api/clients/7/retirement-income-readiness/context" && method === "GET") {
          contextReads += 1;
          if (contextReads === 1) {
            oldSignal = init?.signal ?? undefined;
            return oldContext;
          }
          return Promise.resolve(response({
            schema_version: "RTDIR_PLANNING_CONTEXT_V1",
            client_id: 7,
            planning_calculation_input_fingerprint: "fresh-profile",
            planning_input_ready: false,
            retirement_target_date: "2047-01-01",
            retirement_target_ready: false,
            blocking_facts: [{ source_id: null, code: "CURRENT_PROFILE_CONTEXT" }]
          }));
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      });
      vi.stubGlobal("fetch", fetchMock);
      render(
        <MemoryRouter initialEntries={["/clients/7"]}>
          <Routes><Route path="/clients/:clientId" element={<ClientDetailScreen />} /></Routes>
        </MemoryRouter>
      );

      expect(await screen.findByText("שם מלא: Profile Client")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "שמירת פרופיל" }));
      expect(await screen.findByText("הפרופיל נשמר בהצלחה.")).toBeInTheDocument();
      expect(await screen.findByText("CURRENT_PROFILE_CONTEXT")).toBeInTheDocument();
      expect(contextReads).toBe(2);
      expect(oldSignal?.aborted).toBe(true);
      if (lateOutcome === "success") {
        await act(async () => resolveOld(response({
          schema_version: "RTDIR_PLANNING_CONTEXT_V1",
          client_id: 7,
          planning_calculation_input_fingerprint: "obsolete-profile",
          planning_input_ready: false,
          retirement_target_date: "1999-01-01",
          retirement_target_ready: false,
          blocking_facts: [{ source_id: null, code: "OBSOLETE_PROFILE_SUCCESS" }]
        })));
      } else {
        await act(async () => rejectOld(new Error("OBSOLETE_PROFILE_FAILURE")));
      }
      await waitFor(() => {
        expect(screen.queryByText(/OBSOLETE_PROFILE_SUCCESS|OBSOLETE_PROFILE_FAILURE/)).not.toBeInTheDocument();
      });
      expect(screen.getByText("CURRENT_PROFILE_CONTEXT")).toBeInTheDocument();
    }
  );

  it("executes the integrated synthetic workflow journey without reload, stale state, comparison, or RMIGA calls", async () => {
    let resolveFreshContext!: (response: Response) => void;
    const freshContext = new Promise<Response>((resolve) => {
      resolveFreshContext = resolve;
    });
    const response = (body: unknown): Response => ({
      ok: true,
      status: 200,
      statusText: "OK",
      headers: { get: () => "application/json" },
      json: async () => body,
      text: async () => JSON.stringify(body)
    }) as unknown as Response;
    const incompleteCase = {
      client_id: 7,
      display_name: "Synthetic Client A",
      id_number: "123456789",
      birth_date: "1985-02-03",
      gender: "female",
      employment_status: null,
      planned_retirement_date: null,
      planned_retirement_age: 67,
      lifecycle_status: "draft",
      completeness: {
        status: "incomplete",
        missing_field_ids: ["employment_status"],
        conflicting_field_ids: []
      },
      updated_at: "2026-10-21T00:00:00Z"
    };
    const completeCase = {
      ...incompleteCase,
      display_name: "Unsaved Professional Edit",
      employment_status: "salaried_employee",
      completeness: { status: "complete", missing_field_ids: [], conflicting_field_ids: [] }
    };
    const snapshot = {
      clearinghouse_snapshot_id: "snapshot:journey",
      client_id: 7,
      import_date: "2026-10-01",
      source_type: "clearinghouse",
      source_file: "journey.xml",
      collection_status: "collected",
      collection_notes: null,
      verification_status: "verified",
      verification_notes: null,
      verified_at: "2026-10-02T00:00:00Z",
      created_at: "2026-10-01T00:00:00Z"
    };
    const documentItem = {
      document_id: "document:journey",
      client_id: 7,
      document_type: "161",
      source_type: "document",
      source_file: "journey.pdf",
      collection_date: "2026-10-02",
      collection_status: "collected",
      collection_notes: null,
      verification_status: "unverified",
      verification_notes: null,
      verified_at: null,
      created_at: "2026-10-02T00:00:00Z"
    };
    let clientReads = 0;
    let contextReads = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/clients/7" && method === "GET") {
        clientReads += 1;
        return Promise.resolve(response({
          client_id: 7,
          full_name: incompleteCase.display_name,
          id_number: incompleteCase.id_number,
          birth_date: incompleteCase.birth_date,
          file_status: "file_created",
          professional_identification_status: "professionally_identified",
          m01_case: incompleteCase
        }));
      }
      if (url === "/api/clients/7/profile" && method === "GET") return Promise.resolve(response({ profile: null }));
      if (url === "/api/clients/7/clearinghouse-snapshots" && method === "GET") return Promise.resolve(response([snapshot]));
      if (url === "/api/clients/7/documents" && method === "GET") return Promise.resolve(response([]));
      if (url === "/api/clients/7/missing-items" && method === "GET") return Promise.resolve(response([]));
      if (url === "/api/clients/7/case" && method === "PUT") return Promise.resolve(response(completeCase));
      if (url === "/api/clients/7/documents" && method === "POST") return Promise.resolve(response(documentItem));
      if (url === "/api/clients/7/retirement-income-readiness/context" && method === "GET") {
        contextReads += 1;
        return contextReads === 1
          ? Promise.resolve(response({
              schema_version: "RTDIR_PLANNING_CONTEXT_V1",
              client_id: 7,
              planning_calculation_input_fingerprint: "journey-before",
              planning_input_ready: false,
              retirement_target_date: null,
              retirement_target_ready: false,
              blocking_facts: [{ source_id: null, code: "OLD_JOURNEY_CONTEXT" }]
            }))
          : freshContext;
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes><Route path="/clients/:clientId" element={<ClientDetailScreen />} /></Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("שם מלא: Synthetic Client A")).toBeInTheDocument();
    await screen.findByText("OLD_JOURNEY_CONTEXT");
    const nameInput = screen.getByLabelText("שם");
    fireEvent.change(nameInput, { target: { value: "Unsaved Professional Edit" } });
    const nextAction = screen.getByRole("link", { name: "השלמת תשתית תיק הלקוח" });
    fireEvent.click(nextAction);
    expect(nameInput).toHaveValue("Unsaved Professional Edit");
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "תשתית תיק הלקוח" }));
    expect(clientReads).toBe(1);

    let navigationMutationReached = false;
    const navigationMutation = vi.spyOn(workflowNavigationPolicy, "focusAndScroll")
      .mockImplementation((target) => {
        navigationMutationReached = true;
        (nameInput as HTMLInputElement).value = "";
        target?.focus();
      });
    fireEvent.change(nameInput, { target: { value: "Unsaved Professional Edit" } });
    let navigationKilled = false;
    let navigationFailureReason = "";
    try {
      fireEvent.click(nextAction);
      expect(nameInput).toHaveValue("Unsaved Professional Edit");
      expect(clientReads).toBe(1);
    } catch (error) {
      navigationKilled = true;
      navigationFailureReason = String(error);
    } finally {
      navigationMutation.mockRestore();
    }
    expect(navigationMutationReached).toBe(true);
    expect(navigationKilled).toBe(true);
    expect(navigationFailureReason).toContain("Unsaved Professional Edit");
    fireEvent.change(nameInput, { target: { value: "Unsaved Professional Edit" } });
    fireEvent.click(nextAction);
    expect(nameInput).toHaveValue("Unsaved Professional Edit");
    expect(clientReads).toBe(1);

    fireEvent.change(screen.getByLabelText("מצב תעסוקה"), { target: { value: "salaried_employee" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(await screen.findByText("נתוני תיק הלקוח נשמרו.")).toBeInTheDocument();
    expect(screen.queryByText("OLD_JOURNEY_CONTEXT")).not.toBeInTheDocument();
    expect(screen.getByText("טוען מצב מוכנות עדכני…")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "רישום מסמך תכנון פרישה" })).toHaveAttribute(
      "href",
      "/clients/7#retirement-documents-heading"
    );

    fireEvent.change(screen.getByLabelText("סוג מסמך"), { target: { value: "161" } });
    fireEvent.change(screen.getByLabelText("סוג מקור המסמך"), { target: { value: "document" } });
    fireEvent.change(screen.getByLabelText("קובץ מקור המסמך"), { target: { value: "journey.pdf" } });
    fireEvent.change(screen.getByLabelText("תאריך איסוף המסמך"), { target: { value: "02/10/2026" } });
    fireEvent.change(screen.getByLabelText("מצב איסוף המסמך"), { target: { value: "collected" } });
    fireEvent.click(screen.getByRole("button", { name: "רישום מסמך" }));
    expect(await screen.findByText("מסמך תכנון הפרישה נרשם.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "המשך להכנת מקורות מקצועיים" })).toHaveAttribute(
      "href",
      "/clients/7/professional-sources"
    );

    await act(async () => resolveFreshContext(response({
      schema_version: "RTDIR_PLANNING_CONTEXT_V1",
      client_id: 7,
      planning_calculation_input_fingerprint: "journey-after",
      planning_input_ready: true,
      retirement_target_date: "2047-01-01",
      retirement_target_ready: true,
      blocking_facts: []
    })));
    expect(await screen.findByRole("link", { name: "המשך למוכנות הכנסה במועד היעד" })).toHaveAttribute(
      "href",
      "/clients/7/retirement-income-readiness"
    );
    expect(contextReads).toBe(2);
    expect(clientReads).toBe(1);
    expect(screen.queryByText(/Client B|לקוח B/)).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toEqual(
      expect.arrayContaining([expect.stringMatching(/comparison|gap/)]),
    );
  });
});
