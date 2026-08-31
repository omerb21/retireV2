import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDetailScreen } from "./ClientDetailScreen";

vi.mock("./RetirementPlanningFactsSection", () => ({
  RetirementPlanningFactsSection: () => (
    <section aria-label="Retirement Planning Facts mock">Retirement Planning Facts</section>
  )
}));

vi.mock("./PensionAnalysisRecordSection", () => ({
  PensionAnalysisRecordSection: () => (
    <section aria-label="Pension Analysis Records mock">Pension Analysis Records</section>
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
    expect(screen.getByText("Pension Analysis Records")).toBeInTheDocument();
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
    expect(screen.getByRole("link", { name: "M10 — השוואת תרחישים" })).toHaveAttribute(
      "href",
      "/clients/7/scenario-comparison"
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
      "Pension Analysis Records",
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
});
