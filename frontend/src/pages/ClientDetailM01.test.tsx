import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { M01CaseItem, M01LifecycleStatus } from "../api/clientsApi";
import { ClientDetailScreen } from "./ClientDetailScreen";

vi.mock("./RetirementPlanningFactsSection", () => ({
  RetirementPlanningFactsSection: () => <div>Retirement facts</div>
}));
vi.mock("./PensionAnalysisRecordSection", () => ({
  PensionAnalysisRecordSection: () => <div>Pension analysis</div>
}));
vi.mock("./PlannerAssumptionsSection", () => ({
  PlannerAssumptionsSection: () => <div>Planner assumptions</div>
}));
vi.mock("./AdvisoryMissingInformationSection", () => ({
  AdvisoryMissingInformationSection: () => <div>Missing information</div>
}));
vi.mock("./RetirementPlanningConsolidatedReviewSection", () => ({
  RetirementPlanningConsolidatedReviewSection: () => <div>Consolidated review</div>
}));

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body)
  } as unknown as Response;
}

function m01Case(
  clientId: number,
  name: string,
  overrides: Partial<M01CaseItem> = {}
): M01CaseItem {
  return {
    client_id: clientId,
    display_name: name,
    id_number: `ID-${clientId}`,
    birth_date: "1980-01-01",
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
    allowed_lifecycle_targets: ["intake"],
    updated_at: "2026-07-28T00:00:00Z",
    ...overrides
  };
}

function clientResponse(
  clientId: number,
  name: string,
  overrides: Partial<M01CaseItem> = {}
): Response {
  const caseItem = m01Case(clientId, name, overrides);
  return jsonResponse({
    client_id: clientId,
    full_name: name,
    id_number: caseItem.id_number,
    birth_date: caseItem.birth_date,
    file_status: "file_created",
    professional_identification_status: "identification_incomplete",
    m01_case: caseItem
  });
}

function ancillaryResponse(url: string): Response | null {
  if (url.endsWith("/profile")) {
    return jsonResponse({ profile: null });
  }
  if (
    url.includes("/clearinghouse-snapshots") ||
    url.includes("/documents") ||
    url.includes("/missing-data")
  ) {
    return jsonResponse([]);
  }
  return null;
}

function NavigationHarness() {
  const navigate = useNavigate();
  return (
    <>
      <button type="button" onClick={() => navigate("/clients/1")}>Go A</button>
      <button type="button" onClick={() => navigate("/clients/2")}>Go B</button>
      <Routes>
        <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
      </Routes>
    </>
  );
}

function renderHarness(initialClient = 1) {
  render(
    <MemoryRouter initialEntries={[`/clients/${initialClient}`]}>
      <NavigationHarness />
    </MemoryRouter>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});
describe("PKG-006 M01 client case workspace", () => {
  it("renders, edits, and transitions from backend-authored case state", async () => {
    const updated = m01Case(1, "Updated Client", {
      lifecycle_status: "draft",
      allowed_lifecycle_targets: ["intake"]
    });
    const transitioned = {
      ...updated,
      lifecycle_status: "intake" as M01LifecycleStatus,
      allowed_lifecycle_targets: ["draft", "analysis"] as M01LifecycleStatus[]
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(1, "Client One"));
      }
      if (url === "/api/clients/1/case" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse(updated));
      }
      if (url === "/api/clients/1/case/lifecycle" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(transitioned));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderHarness();

    expect(await screen.findByRole("heading", { name: "תשתית תיק הלקוח" })).toBeInTheDocument();
    expect(screen.getByText("שלמות נתונים: שלם")).toBeInTheDocument();
    expect(screen.getByText("מצב נוכחי: טיוטה")).toBeInTheDocument();
    expect(screen.getByLabelText("מצב תעסוקה")).toHaveValue("salaried_employee");
    expect(screen.getByLabelText("גיל פרישה מתוכנן")).toHaveValue(67);

    fireEvent.change(screen.getByLabelText("שם"), { target: { value: "Updated Client" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(await screen.findByText("נתוני תיק הלקוח נשמרו.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/1/case",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining('"employment_status":"salaried_employee"')
      })
    );

    fireEvent.click(screen.getByRole("button", { name: "מעבר למצב קליטה" }));
    expect(await screen.findByText("מצב נוכחי: קליטה")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "מעבר למצב טיוטה" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "מעבר למצב ניתוח" })).toBeInTheDocument();
  });

  it("ignores a stale successful read after A to B", async () => {
    const oldA = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") return oldA.promise;
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    expect(await screen.findByText("שם מלא: Client B")).toBeInTheDocument();
    oldA.resolve(clientResponse(1, "Stale Client A"));

    await waitFor(() => expect(screen.queryByText(/Stale Client A/)).not.toBeInTheDocument());
    expect(screen.getByText("שם מלא: Client B")).toBeInTheDocument();
  });

  it("ignores a stale rejected read and its error after A to B", async () => {
    const oldA = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") return oldA.promise;
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    expect(await screen.findByText("שם מלא: Client B")).toBeInTheDocument();
    oldA.reject(new Error("old A failed"));

    await waitFor(() => expect(screen.queryByText(/old A failed/)).not.toBeInTheDocument());
    expect(screen.queryByText("Unable to load client details.")).not.toBeInTheDocument();
  });

  it("does not let a stale read finally clear the current loading state", async () => {
    const oldA = deferred<Response>();
    const currentB = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") return oldA.promise;
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") return currentB.promise;
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    oldA.reject(new Error("old A failed"));
    await waitFor(() => {
      expect(screen.getByText("טוען את פרטי הלקוח...")).toBeInTheDocument();
    });
    currentB.resolve(clientResponse(2, "Client B"));
    expect(await screen.findByText("שם מלא: Client B")).toBeInTheDocument();
  });

  it("ignores a stale successful mutation after A to B to A and accepts the new A mutation", async () => {
    const oldMutation = deferred<Response>();
    const newMutation = deferred<Response>();
    let aReadCount = 0;
    let mutationCount = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") {
        aReadCount += 1;
        return Promise.resolve(clientResponse(1, aReadCount === 1 ? "Client A" : "Client A Revisited"));
      }
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      if (url === "/api/clients/1/case" && init?.method === "PUT") {
        mutationCount += 1;
        return mutationCount === 1 ? oldMutation.promise : newMutation.promise;
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("שם מלא: Client A");
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("שם מלא: Client B");
    fireEvent.click(screen.getByRole("button", { name: "Go A" }));
    await screen.findByText("שם מלא: Client A Revisited");
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    newMutation.resolve(jsonResponse(m01Case(1, "New A Mutation Result")));
    expect(await screen.findByText("שם מלא: New A Mutation Result")).toBeInTheDocument();

    oldMutation.resolve(jsonResponse(m01Case(1, "Stale A Mutation Result")));
    await waitFor(() => expect(screen.queryByText(/Stale A Mutation Result/)).not.toBeInTheDocument());
    expect(screen.getByText("שם מלא: New A Mutation Result")).toBeInTheDocument();
  });

  it("ignores a stale rejected mutation and validation message after A to B", async () => {
    const oldMutation = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(1, "Client A"));
      }
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      if (url === "/api/clients/1/case" && init?.method === "PUT") return oldMutation.promise;
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("שם מלא: Client A");
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("שם מלא: Client B");
    oldMutation.resolve(jsonResponse({
      detail: {
        code: "OLD_A_VALIDATION",
        message: "old A validation failed"
      }
    }, 422));

    await waitFor(() => expect(screen.queryByText(/old A validation failed/)).not.toBeInTheDocument());
    expect(screen.queryByText("Unable to update client case.")).not.toBeInTheDocument();
  });

  it("does not let a stale mutation finally clear a newer mutation state", async () => {
    const oldMutation = deferred<Response>();
    const currentMutation = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(1, "Client A"));
      }
      if (url === "/api/clients/2" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      if (url === "/api/clients/1/case" && init?.method === "PUT") return oldMutation.promise;
      if (url === "/api/clients/2/case" && init?.method === "PUT") return currentMutation.promise;
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("שם מלא: Client A");
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("שם מלא: Client B");
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(screen.getByRole("button", { name: "שומר נתוני תיק..." })).toBeDisabled();

    oldMutation.resolve(jsonResponse(m01Case(1, "Old A Result")));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "שומר נתוני תיק..." })).toBeDisabled();
    });

    currentMutation.resolve(jsonResponse(m01Case(2, "Current B Result")));
    expect(await screen.findByText("שם מלא: Current B Result")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "שמירת נתוני התיק" })).toBeEnabled();
  });

  it("resets all visible A workspace state before B settles and fails B profile closed", async () => {
    const bRead = deferred<Response>();
    const bProfile = deferred<Response>();
    const oldAProfileMutation = deferred<Response>();
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/clients/1" && method === "GET") {
        return Promise.resolve(clientResponse(1, "Client A"));
      }
      if (url === "/api/clients/1/profile" && method === "GET") {
        return Promise.resolve(jsonResponse({
          profile: {
            client_profile_id: "CP-1",
            client_id: 1,
            id_number: "ID-1",
            birth_date: "1980-01-01",
            gender: "female",
            contact_method: "A-CONTACT-SECRET",
            contact_details: "A-DETAILS-SECRET",
            notes: "A-NOTES-SECRET",
            file_status: "file_created",
            professional_identification_status: "identification_incomplete",
            m01_case: m01Case(1, "Client A")
          }
        }));
      }
      if (url === "/api/clients/1/profile" && method === "PUT") {
        return oldAProfileMutation.promise;
      }
      if (url === "/api/clients/1/clearinghouse-snapshots" && method === "GET") {
        return Promise.resolve(jsonResponse([{
          clearinghouse_snapshot_id: "A-SNAPSHOT",
          client_id: 1,
          import_date: "2026-01-01",
          source_type: "A-SOURCE",
          source_file: "A-SNAPSHOT-SECRET",
          collection_status: "collected",
          collection_notes: "A-COLLECTION-NOTES",
          verification_status: "pending",
          verification_notes: "A-VERIFICATION-DRAFT",
          verified_at: null,
          created_at: "2026-01-01T00:00:00Z"
        }]));
      }
      if (
        (url === "/api/clients/1/documents" || url === "/api/clients/1/missing-items")
        && method === "GET"
      ) {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/clients/1/case" && method === "PUT") {
        return Promise.resolve(jsonResponse(m01Case(1, "Client A")));
      }
      if (url === "/api/clients/2" && method === "GET") return bRead.promise;
      if (url === "/api/clients/2/profile" && method === "GET") return bProfile.promise;
      if (
        (
          url === "/api/clients/2/clearinghouse-snapshots"
          || url === "/api/clients/2/documents"
          || url === "/api/clients/2/missing-items"
        )
        && method === "GET"
      ) {
        return Promise.resolve(jsonResponse([]));
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderHarness();

    expect(await screen.findByDisplayValue("A-CONTACT-SECRET")).toBeInTheDocument();
    expect(screen.getByText(/A-SNAPSHOT-SECRET/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("אמצעי קשר"), {
      target: { value: "A-CONTACT-DRAFT" }
    });
    fireEvent.change(screen.getByLabelText("קובץ המקור של תמונת המצב"), {
      target: { value: "A-SNAPSHOT-DRAFT" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(await screen.findByText("נתוני תיק הלקוח נשמרו.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "שמירת פרופיל" }));
    expect(screen.getByRole("button", { name: "שומר פרופיל..." })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));

    expect(screen.getByText("טוען את פרטי הלקוח...")).toBeInTheDocument();
    expect(screen.queryByText(/A-SNAPSHOT-SECRET/)).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("A-CONTACT-DRAFT")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("A-SNAPSHOT-DRAFT")).not.toBeInTheDocument();
    expect(screen.queryByText("נתוני תיק הלקוח נשמרו.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "שומר פרופיל..." })).not.toBeInTheDocument();

    bRead.resolve(clientResponse(2, "Client B"));
    bProfile.resolve(jsonResponse({ detail: { code: "B_PROFILE_FAILED" } }, 500));

    expect(await screen.findByText("שם מלא: Client B")).toBeInTheDocument();
    expect(screen.getByText("לא ניתן לטעון את פרופיל הלקוח.")).toBeInTheDocument();
    expect(screen.getByLabelText("אמצעי קשר")).toHaveValue("");
    expect(screen.getByLabelText("קובץ המקור של תמונת המצב")).toHaveValue("");
    expect(screen.queryByText(/A-SNAPSHOT-SECRET/)).not.toBeInTheDocument();
    expect(screen.queryByText(/A-CONTACT/)).not.toBeInTheDocument();
    expect(screen.queryByText("נתוני תיק הלקוח נשמרו.")).not.toBeInTheDocument();

    oldAProfileMutation.resolve(jsonResponse({
      profile: {
        client_profile_id: "CP-1",
        client_id: 1,
        id_number: "ID-1",
        birth_date: "1980-01-01",
        gender: "female",
        contact_method: "STALE-A-PROFILE",
        contact_details: null,
        notes: null,
        file_status: "file_created",
        professional_identification_status: "identification_incomplete",
        m01_case: m01Case(1, "Stale Client A")
      }
    }));
    await waitFor(() => {
      expect(screen.queryByText(/STALE-A-PROFILE|Stale Client A/)).not.toBeInTheDocument();
    });
    expect(screen.getByText("שם מלא: Client B")).toBeInTheDocument();
  });

  it("keeps archived M01 and profile mutation paths read-only until reopen", async () => {
    const archived = m01Case(1, "Archived Client", {
      lifecycle_status: "archived",
      allowed_lifecycle_targets: ["delivered"]
    });
    const reopened = m01Case(1, "Archived Client", {
      lifecycle_status: "delivered",
      allowed_lifecycle_targets: ["review", "archived"]
    });
    const updated = { ...reopened, display_name: "Reopened Client" };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/clients/1" && method === "GET") {
        return Promise.resolve(clientResponse(1, "Archived Client", archived));
      }
      if (url === "/api/clients/1/profile" && method === "GET") {
        return Promise.resolve(jsonResponse({ profile: null }));
      }
      if (
        (
          url === "/api/clients/1/clearinghouse-snapshots"
          || url === "/api/clients/1/documents"
          || url === "/api/clients/1/missing-items"
        )
        && method === "GET"
      ) {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/clients/1/case/lifecycle" && method === "POST") {
        return Promise.resolve(jsonResponse(reopened));
      }
      if (url === "/api/clients/1/case" && method === "PUT") {
        return Promise.resolve(jsonResponse(updated));
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderHarness();

    expect(await screen.findByText("מצב נוכחי: בארכיון")).toBeInTheDocument();
    expect(screen.getByText(/לקריאה בלבד עד לפתיחה מפורשת מחדש/)).toBeInTheDocument();
    expect(screen.getByLabelText("שם")).toBeDisabled();
    expect(screen.getByLabelText("מספר זהות ישראלי או מזהה לקוח")).toBeDisabled();
    expect(screen.getByLabelText("מצב תעסוקה")).toBeDisabled();
    expect(screen.getByLabelText("גיל פרישה מתוכנן")).toBeDisabled();
    for (const control of screen.getAllByLabelText("מספר זהות")) {
      expect(control).toBeDisabled();
    }
    for (const control of screen.getAllByLabelText("תאריך לידה")) {
      expect(control).toBeDisabled();
    }
    for (const control of screen.getAllByLabelText("מגדר")) {
      expect(control).toBeDisabled();
    }
    expect(screen.getByRole("button", { name: "שמירת נתוני התיק" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "שמירת פרופיל" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "מעבר למצב נמסר" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "מעבר למצב קליטה" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "מעבר למצב נמסר" }));

    expect(await screen.findByText("מצב נוכחי: נמסר")).toBeInTheDocument();
    expect(screen.getByLabelText("שם")).toBeEnabled();
    expect(screen.getByLabelText("מצב תעסוקה")).toBeEnabled();
    expect(screen.getByRole("button", { name: "שמירת נתוני התיק" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "שמירת פרופיל" })).toBeEnabled();

    fireEvent.change(screen.getByLabelText("שם"), {
      target: { value: "Reopened Client" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת נתוני התיק" }));
    expect(await screen.findByText("שם מלא: Reopened Client")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/1/case",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("does not apply a stale reopen result after switching clients", async () => {
    const reopen = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const ancillary = ancillaryResponse(url);
      if (ancillary !== null) return Promise.resolve(ancillary);
      if (url === "/api/clients/1" && method === "GET") {
        return Promise.resolve(clientResponse(1, "Archived A", {
          lifecycle_status: "archived",
          allowed_lifecycle_targets: ["delivered"]
        }));
      }
      if (url === "/api/clients/2" && method === "GET") {
        return Promise.resolve(clientResponse(2, "Client B"));
      }
      if (url === "/api/clients/1/case/lifecycle" && method === "POST") {
        return reopen.promise;
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    }));
    renderHarness();

    expect(await screen.findByText("מצב נוכחי: בארכיון")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "מעבר למצב נמסר" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    expect(await screen.findByText("שם מלא: Client B")).toBeInTheDocument();

    reopen.resolve(jsonResponse(m01Case(1, "Reopened A", {
      lifecycle_status: "delivered",
      allowed_lifecycle_targets: ["review", "archived"]
    })));

    await waitFor(() => {
      expect(screen.queryByText(/Reopened A/)).not.toBeInTheDocument();
    });
    expect(screen.getByText("שם מלא: Client B")).toBeInTheDocument();
    expect(screen.getByText("מצב נוכחי: טיוטה")).toBeInTheDocument();
  });
});
