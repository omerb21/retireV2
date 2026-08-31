import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PensionAnalysisRecordSection } from "./PensionAnalysisRecordSection";

function jsonResponse(body: unknown, status = 200, statusText = "OK") {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    headers: {
      get: () => "application/json"
    },
    json: async () => body
  };
}

function requestBody(call: unknown[]): Record<string, unknown> {
  const init = call[1] as RequestInit;
  return JSON.parse(String(init.body)) as Record<string, unknown>;
}

function requestMethod(call: unknown[]): string {
  return ((call[1] as RequestInit | undefined)?.method ?? "GET").toUpperCase();
}

function requestUrl(call: unknown[]): string {
  return String(call[0]);
}

const pensionHolding = {
  id: 17,
  client_id: 7,
  provider_name: "Existing Pension Provider",
  product_type: "pension fund",
  lifecycle_status: "current",
  source_status: "not recorded",
  verification_state: "collected - not yet reviewed",
  product_name: "Pension Product",
  account_reference: "ACC-17",
  known_balance_amount: "1000.00",
  balance_as_of_date: "2026-01-01",
  known_monthly_pension_amount: "200.00",
  pension_amount_as_of_date: "2026-01-02",
  source_type: "statement",
  source_date: "2026-01-03",
  source_note: "Existing source context",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z"
};

const existingRecord = {
  id: 31,
  client_id: 7,
  pension_holding_id: 17,
  analysis_record_text: "Existing analysis record text",
  created_at: "2026-01-04T00:00:00Z",
  updated_at: "2026-01-04T00:00:00Z"
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PensionAnalysisRecordSection", () => {
  it("loads current pension holdings and creates one separate analysis record with read-only fact context", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === "/api/clients/7/pension-holdings?lifecycle_status=current") {
        return Promise.resolve(jsonResponse([pensionHolding]));
      }
      if (url === "/api/clients/7/pension-holdings/17/analysis-record" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(jsonResponse(null));
      }
      if (url === "/api/clients/7/pension-holdings/17/analysis-record" && init?.method === "POST") {
        return Promise.resolve(jsonResponse({ ...existingRecord, analysis_record_text: "New analysis record text" }));
      }
      throw new Error(`Unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PensionAnalysisRecordSection clientId={7} />);

    expect(screen.getByText("טוען רשומות ניתוח פנסיוני…")).toBeInTheDocument();
    expect(
      await screen.findByText((_, element) => element?.textContent === "שם הגוף המנהל: Existing Pension Provider")
    ).toBeInTheDocument();
    expect(screen.getByText("סוג מוצר: קרן פנסיה")).toBeInTheDocument();
    expect(screen.getByText("קצבה חודשית ידועה: 200.00")).toBeInTheDocument();
    expect(screen.getByText("תאריך נכונות הקצבה: 02/01/2026")).toBeInTheDocument();
    expect(screen.getByText("מצב מקור: לא תועד")).toBeInTheDocument();
    expect(screen.getByText("מצב אימות: נאסף וטרם נבדק")).toBeInTheDocument();
    expect(screen.getByText("סוג מקור: statement")).toBeInTheDocument();
    expect(screen.getByText("תאריך מקור: 03/01/2026")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "הקשר עובדתי של אחזקה פנסיונית 17" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("תוכן רשומת הניתוח"), {
      target: { value: "New analysis record text" }
    });
    fireEvent.click(screen.getByRole("button", { name: "יצירת רשומת ניתוח פנסיוני" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/pension-holdings/17/analysis-record",
        expect.objectContaining({ method: "POST" })
      );
    });
    const postCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "POST") as unknown[];
    expect(requestBody(postCall)).toEqual({ analysis_record_text: "New analysis record text" });
    expect(requestBody(postCall)).not.toHaveProperty("source_status");
    expect(requestBody(postCall)).not.toHaveProperty("verification_state");
    expect(requestBody(postCall)).not.toHaveProperty("lifecycle_status");
    expect(await screen.findByText("רשומת הניתוח הפנסיוני נשמרה.")).toBeInTheDocument();

    expect(fetchMock.mock.calls.map(requestUrl)).toContain("/api/clients/7/pension-holdings?lifecycle_status=current");
    expect(fetchMock.mock.calls.some((call) => requestMethod(call) === "DELETE")).toBe(false);
    expect(fetchMock.mock.calls.some((call) => requestUrl(call).includes("supersede"))).toBe(false);
    expect(fetchMock.mock.calls.some((call) => requestUrl(call).includes("missing-items"))).toBe(false);
    expect(screen.queryByText(/classification|recommendation|readiness|workflow|priority|blocking/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete|supersede/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/lifecycle|status/i)).not.toBeInTheDocument();
  });

  it("loads an existing analysis record and updates only analysis record text", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === "/api/clients/7/pension-holdings?lifecycle_status=current") {
        return Promise.resolve(jsonResponse([pensionHolding]));
      }
      if (url === "/api/clients/7/pension-holdings/17/analysis-record" && (init?.method ?? "GET") === "GET") {
        return Promise.resolve(jsonResponse(existingRecord));
      }
      if (url === "/api/clients/7/pension-holdings/17/analysis-record" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse({ ...existingRecord, analysis_record_text: "Updated analysis record text" }));
      }
      throw new Error(`Unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PensionAnalysisRecordSection clientId={7} />);

    expect(await screen.findByDisplayValue("Existing analysis record text")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("תוכן רשומת הניתוח"), {
      target: { value: "Updated analysis record text" }
    });
    fireEvent.click(screen.getByRole("button", { name: "שמירת רשומת ניתוח פנסיוני" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/pension-holdings/17/analysis-record",
        expect.objectContaining({ method: "PUT" })
      );
    });
    const putCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "PUT") as unknown[];
    expect(requestBody(putCall)).toEqual({ analysis_record_text: "Updated analysis record text" });
  });

  it("displays empty and API error states", async () => {
    const emptyFetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", emptyFetchMock);
    const { unmount } = render(<PensionAnalysisRecordSection clientId={7} />);
    expect(await screen.findByText("לא נמצאו אחזקות פנסיוניות עדכניות לצורך רשומת ניתוח.")).toBeInTheDocument();

    unmount();
    vi.unstubAllGlobals();
    const failingFetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detail: { code: "LOAD_FAILED" } }, 500, "Error")
    );
    vi.stubGlobal("fetch", failingFetchMock);
    render(<PensionAnalysisRecordSection clientId={7} />);

    expect(await screen.findByText("לא ניתן לטעון את רשומות הניתוח הפנסיוני.")).toBeInTheDocument();
    expect(screen.getByText(/LOAD_FAILED/)).toBeInTheDocument();
  });
});
