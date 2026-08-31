import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlannerAssumptionsSection } from "./PlannerAssumptionsSection";

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

function sectionQueries(): ReturnType<typeof within> {
  return within(screen.getByRole("heading", { name: "הנחות מתכנן" }).closest("section") as HTMLElement);
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

const assumptionRow = {
  id: 17,
  client_id: 7,
  assumption_category: "income",
  title: "Existing assumption",
  assumption_value_text: "Existing value",
  rationale: "Existing rationale",
  owner: "planner",
  lifecycle_status: "current",
  effective_start_date: "2026-01-01",
  effective_end_date: null,
  review_date: "2026-06-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z"
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PlannerAssumptionsSection", () => {
  it("uses client ID, default current loading, local lifecycle filters, and empty state", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<PlannerAssumptionsSection clientId={7} />);

    expect(screen.getByText("טוען הנחות מתכנן…")).toBeInTheDocument();
    expect(await screen.findByText("לא נמצאו הנחות מתכנן עבור מסנן מחזור החיים שנבחר.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/planner-assumptions?lifecycle_status=current",
      expect.objectContaining({ method: "GET" })
    );

    const lifecycleSelect = sectionQueries().getByLabelText("סינון לפי מצב מחזור חיים") as HTMLSelectElement;
    expect(Array.from(lifecycleSelect.options).map((option) => option.value)).toEqual([
      "current",
      "superseded",
      "all"
    ]);

    const callsAfterInitialLoad = fetchMock.mock.calls.length;
    fireEvent.change(lifecycleSelect, { target: { value: "superseded" } });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/planner-assumptions?lifecycle_status=superseded",
        expect.objectContaining({ method: "GET" })
      );
    });
    expect(fetchMock.mock.calls.slice(callsAfterInitialLoad).map(requestUrl)).toEqual([
      "/api/clients/7/planner-assumptions?lifecycle_status=superseded"
    ]);

    const callsAfterSuperseded = fetchMock.mock.calls.length;
    fireEvent.change(lifecycleSelect, { target: { value: "all" } });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/planner-assumptions?lifecycle_status=all",
        expect.objectContaining({ method: "GET" })
      );
    });
    expect(fetchMock.mock.calls.slice(callsAfterSuperseded).map(requestUrl)).toEqual([
      "/api/clients/7/planner-assumptions?lifecycle_status=all"
    ]);
  });

  it("creates with approved fields only and displays API 422 errors", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ ...assumptionRow, title: "Created assumption" }));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<PlannerAssumptionsSection clientId={7} />);
    await screen.findByText("לא נמצאו הנחות מתכנן עבור מסנן מחזור החיים שנבחר.");

    const section = sectionQueries();
    fireEvent.change(section.getByLabelText("קטגוריית הנחה"), { target: { value: "income" } });
    fireEvent.change(section.getByLabelText("כותרת"), { target: { value: "Created assumption" } });
    fireEvent.change(section.getByLabelText("ערך ההנחה"), { target: { value: "Value text" } });
    fireEvent.change(section.getByLabelText("נימוק"), { target: { value: "Rationale text" } });
    fireEvent.change(section.getByLabelText("אחראי"), { target: { value: "planner" } });
    const effectiveStart = section.getByLabelText("תאריך תחילת תוקף");
    expect(effectiveStart).not.toHaveAttribute("type", "date");
    fireEvent.change(effectiveStart, { target: { value: "01/01/2026" } });
    fireEvent.click(section.getByRole("button", { name: "הוספת הנחת מתכנן" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/planner-assumptions",
        expect.objectContaining({ method: "POST" })
      );
    });
    const postCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "POST") as unknown[];
    expect(requestBody(postCall)).toEqual({
      assumption_category: "income",
      title: "Created assumption",
      assumption_value_text: "Value text",
      rationale: "Rationale text",
      owner: "planner",
      effective_start_date: "2026-01-01"
    });
    expect(requestBody(postCall)).not.toHaveProperty("lifecycle_status");
    expect(requestBody(postCall)).not.toHaveProperty("source_status");
    expect(requestBody(postCall)).not.toHaveProperty("verification_state");

    unmount();
    vi.unstubAllGlobals();
    const failingFetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ detail: [{ msg: "assumption_category is required" }] }, 422, "Unprocessable Entity"));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", failingFetchMock);
    render(<PlannerAssumptionsSection clientId={7} />);
    await screen.findByText("לא נמצאו הנחות מתכנן עבור מסנן מחזור החיים שנבחר.");
    fireEvent.click(sectionQueries().getByRole("button", { name: "הוספת הנחת מתכנן" }));
    expect(await screen.findByText("לא ניתן לשמור את הנחת המתכנן.")).toBeInTheDocument();
    expect(await screen.findByText(/assumption_category is required/)).toBeInTheDocument();
  });

  it("edits from loaded rows with partial PUT and no GET-one browser request", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return Promise.resolve(jsonResponse({ ...assumptionRow, title: "Updated assumption" }));
      }
      return Promise.resolve(jsonResponse([assumptionRow]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PlannerAssumptionsSection clientId={7} />);
    expect(await screen.findByText("Existing assumption")).toBeInTheDocument();

    const section = sectionQueries();
    expect(section.getByText("תאריך תחילת תוקף: 01/01/2026")).toBeInTheDocument();
    expect(section.getByText("תאריך בדיקה: 01/06/2026")).toBeInTheDocument();
    fireEvent.click(section.getByRole("button", { name: "עריכת הנחת מתכנן" }));
    expect(section.getByLabelText("כותרת")).toHaveValue("Existing assumption");
    expect(section.getByLabelText("ערך ההנחה")).toHaveValue("Existing value");
    expect(section.getByLabelText("תאריך תחילת תוקף")).toHaveValue("01/01/2026");
    expect(section.getByLabelText("תאריך בדיקה")).toHaveValue("01/06/2026");
    expect(section.getByLabelText("תאריך תחילת תוקף")).not.toHaveAttribute("type", "date");
    fireEvent.change(section.getByLabelText("כותרת"), { target: { value: "Canceled assumption" } });
    fireEvent.click(section.getByRole("button", { name: "ביטול העריכה" }));
    expect(fetchMock.mock.calls.some((call) => requestMethod(call) === "PUT")).toBe(false);
    fireEvent.click(section.getByRole("button", { name: "עריכת הנחת מתכנן" }));
    fireEvent.change(section.getByLabelText("כותרת"), { target: { value: "Updated assumption" } });
    fireEvent.change(section.getByLabelText("תאריך בדיקה"), { target: { value: "" } });
    fireEvent.click(section.getByRole("button", { name: "שמירת הנחת מתכנן" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/planner-assumptions/17",
        expect.objectContaining({ method: "PUT" })
      );
    });
    const putCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "PUT") as unknown[];
    expect(requestBody(putCall)).toEqual({
      title: "Updated assumption",
      review_date: null
    });
    expect(requestBody(putCall)).not.toHaveProperty("lifecycle_status");

    const getOneCalls = fetchMock.mock.calls.filter((call) => (
      requestUrl(call) === "/api/clients/7/planner-assumptions/17" && requestMethod(call) === "GET"
    ));
    expect(getOneCalls).toHaveLength(0);
  });

  it("does not render prohibited planner assumption controls", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([assumptionRow]));
    vi.stubGlobal("fetch", fetchMock);

    render(<PlannerAssumptionsSection clientId={7} />);
    expect(await screen.findByText("Existing assumption")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /supersede/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /change lifecycle/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("מצב מחזור חיים")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("מצב מקור")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("מצב אימות")).not.toBeInTheDocument();
  });
});
