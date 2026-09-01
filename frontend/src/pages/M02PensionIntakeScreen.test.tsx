import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { M02Intake } from "../api/m02IntakeApi";
import { M02PensionIntakeScreen } from "./M02PensionIntakeScreen";

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

function clientResponse(
  clientId: number,
  name: string,
  lifecycleStatus?: "delivered" | "archived"
): Response {
  return jsonResponse({
    client_id: clientId,
    full_name: name,
    id_number: `ID-${clientId}`,
    birth_date: "1980-01-01",
    file_status: "file_created",
    professional_identification_status: "identification_incomplete",
    ...(lifecycleStatus
      ? {
          m01_case: {
            client_id: clientId,
            display_name: name,
            id_number: `ID-${clientId}`,
            birth_date: "1980-01-01",
            gender: "other",
            employment_status: "not_currently_working",
            planned_retirement_date: null,
            planned_retirement_age: 67,
            lifecycle_status: lifecycleStatus,
            completeness: {
              status: "complete",
              missing_field_ids: [],
              conflicting_field_ids: []
            },
            allowed_lifecycle_targets:
              lifecycleStatus === "archived" ? ["delivered"] : ["review", "archived"],
            updated_at: "2026-07-28T00:00:00Z"
          }
        }
      : {})
  });
}

function downloadResponse(content = "opaque"): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    headers: new Headers({
      "content-type": "application/octet-stream",
      "content-disposition": "attachment; filename*=UTF-8''opaque.dat"
    }),
    blob: async () => new Blob([content])
  } as unknown as Response;
}

function intake(
  clientId: number,
  id: string,
  overrides: Partial<M02Intake> = {}
): M02Intake {
  return {
    intake_id: id,
    client_id: clientId,
    record_kind: "manual",
    declared_provider_name: null,
    product_name: "Declared Fund",
    product_identifier: null,
    declared_account_reference: null,
    manual_technical_reference: `M02-MANUAL-${id}`,
    manual_technical_reference_is_account: false,
    declared_total_balance_amount: "100.00",
    declared_monthly_pension_amount: null,
    declared_component_values: null,
    declared_statement_date: "2026-01-01",
    declared_start_date: "2000-01-01",
    declared_product_type: "declared product",
    source_type: "manual",
    declared_basis: null,
    notes: null,
    lifecycle_status: "metadata_review",
    preservation_status: "not_applicable",
    preservation_failure_code: null,
    rejection_reason_code: null,
    duplicate_candidate: false,
    duplicate_of_intake_id: null,
    superseding_candidate: false,
    superseding_intake_id: null,
    allowed_lifecycle_targets: ["accepted_for_review", "rejected"],
    diagnostics: ["M02_PROVIDER_MISSING", "M02_DECLARED_ACCOUNT_MISSING"],
    source: null,
    created_by_actor: "system:m02-intake:M02 intake workflow",
    updated_by_actor: "system:m02-intake:M02 intake workflow",
    lifecycle_decided_by_actor: "system:m02-intake:M02 intake workflow",
    lifecycle_decided_at: "2026-07-28T00:00:00Z",
    actor_is_authentication: false,
    created_at: "2026-07-28T00:00:00Z",
    updated_at: "2026-07-28T00:00:00Z",
    ...overrides
  };
}

function NavigationHarness() {
  const navigate = useNavigate();
  return (
    <>
      <button type="button" onClick={() => navigate("/clients/1/pension-intake")}>Go A</button>
      <button type="button" onClick={() => navigate("/clients/2/pension-intake")}>Go B</button>
      <Routes>
        <Route path="/clients/:clientId/pension-intake" element={<M02PensionIntakeScreen />} />
      </Routes>
    </>
  );
}

function renderHarness(initialClient = 1) {
  render(
    <MemoryRouter initialEntries={[`/clients/${initialClient}/pension-intake`]}>
      <NavigationHarness />
    </MemoryRouter>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PKG-007 M02 controlled pension intake", () => {
  it("renders retained state, user responsibility, direct M05 next step, and no delete or preview", async () => {
    const existing = intake(1, "I-1", {
      source: {
        source_id: "S-1",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "application/octet-stream",
        validated_media_type: "text/plain",
        detected_text_encoding: "windows-1255",
        sha256_checksum: "a".repeat(64),
        byte_size: 42,
        source_type: "clearinghouse",
        declared_statement_date: "2026-01-01",
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      },
      manual_technical_reference: null,
      record_kind: "uploaded_source",
      lifecycle_status: "uploaded",
      preservation_status: "preserved",
      duplicate_candidate: true,
      duplicate_of_intake_id: "I-0",
      superseding_candidate: true,
      superseding_intake_id: "I-0",
      allowed_lifecycle_targets: ["metadata_review", "rejected"]
    });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/1/m02/intakes") return Promise.resolve(jsonResponse([existing]));
      throw new Error(`Unexpected request: ${url}`);
    }));

    renderHarness();

    expect(await screen.findByText("לקוח פעיל: Client A (#1)")).toBeInTheDocument();
    expect(screen.getByText(/האחריות לנכונות הנתונים.*של המשתמש/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /המשך לכרטסת.*M05/ })).toHaveAttribute("href", "/clients/1/pension-ledger");
    expect(screen.getByText(/opaque.dat; 42 בתים/)).toBeInTheDocument();
    expect(screen.getByText(`SHA-256: ${"a".repeat(64)}`)).toBeInTheDocument();
    expect(screen.getByText(/מועמדת לכפילות בלבד/)).toBeInTheDocument();
    expect(screen.getByText(/מועמדת להחלפה בלבד/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "מעבר למצב בדיקת מטא־נתונים" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /preview/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "חזרה לתיק הלקוח M01" })).toHaveAttribute(
      "href",
      "/clients/1"
    );
  });

  it("explicitly selects and submits DAT in a multi-file opaque batch", async () => {
    const uploadedDat = intake(1, "I-DAT", {
      manual_technical_reference: null,
      record_kind: "uploaded_source",
      lifecycle_status: "uploaded",
      preservation_status: "preserved"
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/1/m02/intakes" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/clients/1/m02/intakes/upload" && init?.method === "POST") {
        const body = init.body as FormData;
        const files = body.getAll("files") as File[];
        expect(files.map((file) => file.name)).toEqual(["source.dat", "statement.pdf"]);
        expect(body.has("checksum")).toBe(false);
        expect(body.has("actor")).toBe(false);
        return Promise.resolve(jsonResponse({
          results: [
            {
              selection_index: 0,
              original_filename: "source.dat",
              status: "preserved",
              intake: uploadedDat,
              error_code: null,
              error_message: null
            },
            {
              selection_index: 1,
              original_filename: "statement.pdf",
              status: "failed",
              intake: null,
              error_code: "M02_SIGNATURE_MISMATCH",
              error_message: "Invalid PDF"
            }
          ],
          request_error: {
            code: "M02_STORAGE_CLEANUP_FAILED",
            message: "Managed upload cleanup could not be completed"
          }
        }));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    const chooser = screen.getByLabelText("קובצי מקור לשמירה");
    expect(chooser).toHaveAttribute("accept", ".pdf,.xml,.dat,.csv,.xlsx");
    const dat = new File(["opaque"], "source.dat", { type: "application/octet-stream" });
    const pdf = new File(["bad"], "statement.pdf", { type: "application/pdf" });
    fireEvent.change(chooser, { target: { files: [dat, pdf] } });
    expect(screen.getByText(/source.dat — 6 בתים/)).toBeInTheDocument();
    expect(screen.getByText(/statement.pdf — 3 בתים/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("סוג מקור"), {
      target: { value: "clearinghouse" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת הקבצים שנבחרו" }));

    expect(await screen.findByText("source.dat: נשמר")).toBeInTheDocument();
    expect(screen.getByText(/M02_STORAGE_CLEANUP_FAILED/)).toBeInTheDocument();
    expect(screen.getByText(/statement.pdf: נכשל — M02_SIGNATURE_MISMATCH/)).toBeInTheDocument();
    expect(screen.getByText(/תוכן הקובץ אינו מפוענח ב־M02/)).toBeInTheDocument();
  });

  it("creates manual declared facts without a human identity or account claim", async () => {
    const created = intake(1, "I-MANUAL");
    let listCount = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/1/m02/intakes" && (init?.method ?? "GET") === "GET") {
        listCount += 1;
        return Promise.resolve(jsonResponse(listCount === 1 ? [] : [created]));
      }
      if (url === "/api/clients/1/m02/intakes/manual" && init?.method === "POST") {
        expect(String(init.body)).toContain('"declared_start_date":"2000-01-01"');
        expect(String(init.body)).toContain('"declared_product_type":"declared product"');
        expect(String(init.body)).not.toContain("created_by_actor");
        return Promise.resolve(jsonResponse(created, 201));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.change(screen.getByLabelText("סוג מקור"), { target: { value: "manual" } });
    fireEvent.change(screen.getByLabelText("שם מוצר או קרן"), { target: { value: "Declared Fund" } });
    fireEvent.change(screen.getByLabelText("תאריך התחלה מוצהר"), { target: { value: "01/01/2000" } });
    fireEvent.change(screen.getByLabelText("תיאור סוג מוצר מוצהר"), { target: { value: "declared product" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת קליטה ידנית" }));

    expect(await screen.findByText("הקליטה הידנית נשמרה.")).toBeInTheDocument();
    expect(screen.getByText(/אסמכתה תפעולית טכנית \(אינה חשבון\)/)).toBeInTheDocument();
  });

  it("resets A immediately and ignores stale A load after switching to B", async () => {
    const oldAHistory = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/1/m02/intakes") return oldAHistory.promise;
      if (url === "/api/clients/2") return Promise.resolve(clientResponse(2, "Client B"));
      if (url === "/api/clients/2/m02/intakes") return Promise.resolve(jsonResponse([]));
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    expect(screen.getByText("טוען היסטוריית קליטה...")).toBeInTheDocument();
    expect(await screen.findByText("לקוח פעיל: Client B (#2)")).toBeInTheDocument();
    oldAHistory.resolve(jsonResponse([intake(1, "STALE-A")]));

    await waitFor(() => expect(screen.queryByText(/STALE-A/)).not.toBeInTheDocument());
    expect(screen.getByText("לקוח פעיל: Client B (#2)")).toBeInTheDocument();
  });

  it("ignores stale DAT batch success, error, and finally after A-to-B-to-A", async () => {
    const oldUpload = deferred<Response>();
    const newUpload = deferred<Response>();
    let uploadCount = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/clients/1" || url === "/api/clients/2") {
        const id = url.endsWith("/1") ? 1 : 2;
        return Promise.resolve(clientResponse(id, id === 1 ? "Client A" : "Client B"));
      }
      if (url.endsWith("/m02/intakes") && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/clients/1/m02/intakes/upload") {
        uploadCount += 1;
        return uploadCount === 1 ? oldUpload.promise : newUpload.promise;
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    const firstDat = new File(["old"], "old.dat", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("קובצי מקור לשמירה"), {
      target: { files: [firstDat] }
    });
    fireEvent.change(screen.getByLabelText("סוג מקור"), { target: { value: "manual" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת הקבצים שנבחרו" }));
    expect(screen.getByRole("button", { name: "שומר קבצים..." })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("לקוח פעיל: Client B (#2)");
    fireEvent.click(screen.getByRole("button", { name: "Go A" }));
    await screen.findByText("לקוח פעיל: Client A (#1)");

    const newDat = new File(["new"], "new.dat", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("קובצי מקור לשמירה"), {
      target: { files: [newDat] }
    });
    fireEvent.change(screen.getByLabelText("סוג מקור"), { target: { value: "manual" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת הקבצים שנבחרו" }));
    expect(screen.getByRole("button", { name: "שומר קבצים..." })).toBeDisabled();

    oldUpload.resolve(jsonResponse({
      results: [{
        selection_index: 0,
        original_filename: "STALE-old.dat",
        status: "preserved",
        intake: intake(1, "STALE-I"),
        error_code: null,
        error_message: null
      }],
      request_error: { code: "STALE_ERROR", message: "old request" }
    }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "שומר קבצים..." })).toBeDisabled();
      expect(screen.queryByText(/STALE-old|STALE_ERROR|STALE-I/)).not.toBeInTheDocument();
    });

    newUpload.resolve(jsonResponse({
      results: [{
        selection_index: 0,
        original_filename: "new.dat",
        status: "failed",
        intake: null,
        error_code: "M02_UNSUPPORTED_BINARY_TEXT",
        error_message: "not text"
      }],
      request_error: null
    }));
    expect(await screen.findByText(/new.dat: נכשל — M02_UNSUPPORTED_BINARY_TEXT/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "שמירת הקבצים שנבחרו" })).toBeEnabled();
  });

  it("keeps archived M02 history and download readable while hiding mutation controls", async () => {
    const existing = intake(1, "I-ARCHIVED", {
      source: {
        source_id: "S-ARCHIVED",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "text/plain",
        validated_media_type: "text/plain",
        detected_text_encoding: "utf-8",
        sha256_checksum: "a".repeat(64),
        byte_size: 6,
        source_type: "manual",
        declared_statement_date: "2026-01-01",
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      },
      allowed_lifecycle_targets: ["accepted_for_review", "rejected"]
    });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") {
        return Promise.resolve(clientResponse(1, "Archived Client", "archived"));
      }
      if (url === "/api/clients/1/m02/intakes") {
        return Promise.resolve(jsonResponse([existing]));
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    expect(await screen.findByText(/נתוני M02 לקריאה בלבד/)).toBeInTheDocument();
    expect(screen.getByText("מזהה קליטה: I-ARCHIVED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "הורדת קובץ מצורף" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "תיקון מטא־נתונים" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Move to/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "שמירת קליטה ידנית" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "שמירת הקבצים שנבחרו" })).toBeDisabled();
  });

  it("performs browser download effects only for the current client generation", async () => {
    const oldDownload = deferred<Response>();
    let downloadCount = 0;
    const existingA = intake(1, "I-A", {
      source: {
        source_id: "S-A",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "text/plain",
        validated_media_type: "text/plain",
        detected_text_encoding: "utf-8",
        sha256_checksum: "a".repeat(64),
        byte_size: 6,
        source_type: "manual",
        declared_statement_date: null,
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      }
    });
    const createObjectURL = vi.fn(() => "blob:current");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", {
      createObjectURL,
      revokeObjectURL
    });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/2") return Promise.resolve(clientResponse(2, "Client B"));
      if (url === "/api/clients/1/m02/intakes") return Promise.resolve(jsonResponse([existingA]));
      if (url === "/api/clients/2/m02/intakes") return Promise.resolve(jsonResponse([]));
      if (url === "/api/clients/1/m02/sources/S-A/download") {
        downloadCount += 1;
        return downloadCount === 1 ? oldDownload.promise : Promise.resolve(downloadResponse("new"));
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("לקוח פעיל: Client B (#2)");
    fireEvent.click(screen.getByRole("button", { name: "Go A" }));
    await screen.findByText("לקוח פעיל: Client A (#1)");
    oldDownload.resolve(downloadResponse("old"));
    await waitFor(() => {
      expect(createObjectURL).not.toHaveBeenCalled();
      expect(click).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "הורדת קובץ מצורף" })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:current");
    click.mockRestore();
  });

  it("ignores a rejected A download after switching to B", async () => {
    const oldDownload = deferred<Response>();
    const existingA = intake(1, "I-A-REJECT", {
      source: {
        source_id: "S-A-REJECT",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "text/plain",
        validated_media_type: "text/plain",
        detected_text_encoding: "utf-8",
        sha256_checksum: "b".repeat(64),
        byte_size: 6,
        source_type: "manual",
        declared_statement_date: null,
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      }
    });
    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/2") return Promise.resolve(clientResponse(2, "Client B"));
      if (url === "/api/clients/1/m02/intakes") return Promise.resolve(jsonResponse([existingA]));
      if (url === "/api/clients/2/m02/intakes") return Promise.resolve(jsonResponse([]));
      if (url === "/api/clients/1/m02/sources/S-A-REJECT/download") {
        return oldDownload.promise;
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("לקוח פעיל: Client B (#2)");
    oldDownload.reject(new Error("STALE DOWNLOAD REJECTION"));

    await waitFor(() => {
      expect(screen.getByText("לקוח פעיל: Client B (#2)")).toBeInTheDocument();
      expect(screen.queryByText(/STALE DOWNLOAD REJECTION/)).not.toBeInTheDocument();
      expect(createObjectURL).not.toHaveBeenCalled();
      expect(click).not.toHaveBeenCalled();
      expect(revokeObjectURL).not.toHaveBeenCalled();
    });
    click.mockRestore();
  });

  it("keeps a new A download owned when the old A rejection and finally settle", async () => {
    const oldDownload = deferred<Response>();
    const newDownload = deferred<Response>();
    let downloadCount = 0;
    const existingA = intake(1, "I-A-NEW", {
      source: {
        source_id: "S-A-NEW",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "text/plain",
        validated_media_type: "text/plain",
        detected_text_encoding: "utf-8",
        sha256_checksum: "c".repeat(64),
        byte_size: 6,
        source_type: "manual",
        declared_statement_date: null,
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      }
    });
    const createObjectURL = vi.fn(() => "blob:new-a");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/2") return Promise.resolve(clientResponse(2, "Client B"));
      if (url === "/api/clients/1/m02/intakes") return Promise.resolve(jsonResponse([existingA]));
      if (url === "/api/clients/2/m02/intakes") return Promise.resolve(jsonResponse([]));
      if (url === "/api/clients/1/m02/sources/S-A-NEW/download") {
        downloadCount += 1;
        return downloadCount === 1 ? oldDownload.promise : newDownload.promise;
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("לקוח פעיל: Client B (#2)");
    fireEvent.click(screen.getByRole("button", { name: "Go A" }));
    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    expect(screen.getByRole("button", { name: "מכין קובץ להורדה..." })).toBeDisabled();

    oldDownload.reject(new Error("STALE OLD A REJECTION"));
    await waitFor(() => {
      expect(screen.queryByText(/STALE OLD A REJECTION/)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "מכין קובץ להורדה..." })).toBeDisabled();
      expect(createObjectURL).not.toHaveBeenCalled();
      expect(click).not.toHaveBeenCalled();
    });

    newDownload.resolve(downloadResponse("new-a"));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:new-a");
    expect(screen.getByRole("button", { name: "הורדת קובץ מצורף" })).toBeEnabled();
    click.mockRestore();
  });

  it("shows a current download rejection and resets without browser side effects", async () => {
    const currentDownload = deferred<Response>();
    const existing = intake(1, "I-CURRENT-REJECT", {
      source: {
        source_id: "S-CURRENT-REJECT",
        original_filename: "opaque.dat",
        sanitized_download_filename: "opaque.dat",
        normalized_extension: ".dat",
        declared_mime_type: "text/plain",
        validated_media_type: "text/plain",
        detected_text_encoding: "utf-8",
        sha256_checksum: "d".repeat(64),
        byte_size: 6,
        source_type: "manual",
        declared_statement_date: null,
        preservation_status: "preserved",
        validation_diagnostics: [],
        uploaded_at: "2026-07-28T00:00:00Z"
      }
    });
    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/clients/1") return Promise.resolve(clientResponse(1, "Client A"));
      if (url === "/api/clients/1/m02/intakes") return Promise.resolve(jsonResponse([existing]));
      if (url === "/api/clients/1/m02/sources/S-CURRENT-REJECT/download") {
        return currentDownload.promise;
      }
      throw new Error(`Unexpected request: ${url}`);
    }));
    renderHarness();

    await screen.findByText("לקוח פעיל: Client A (#1)");
    fireEvent.click(screen.getByRole("button", { name: "הורדת קובץ מצורף" }));
    currentDownload.reject(new Error("CURRENT DOWNLOAD REJECTION"));
    expect(await screen.findByText(/CURRENT DOWNLOAD REJECTION/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "הורדת קובץ מצורף" })).toBeEnabled();
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(click).not.toHaveBeenCalled();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    click.mockRestore();
  });
});
