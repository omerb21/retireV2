import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdvisoryMissingInformationSection } from "./AdvisoryMissingInformationSection";

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
  return within(
    screen.getByRole("heading", { name: "Advisory Missing Information" }).closest("section") as HTMLElement
  );
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

const legacyRow = {
  missing_data_item_id: "MD-LEGACY",
  client_id: 7,
  missing_item_type: "data",
  missing_item_label: "Legacy missing item",
  missing_status: "missing",
  notes: null,
  planning_domain: null,
  related_record_type: null,
  related_record_id: null,
  advisory_status: null,
  neutral_reason: null,
  created_at: "2026-01-01T00:00:00Z"
};

const advisoryRow = {
  missing_data_item_id: "MD-V21",
  client_id: 7,
  missing_item_type: "data",
  missing_item_label: "Advisory item",
  missing_status: "missing",
  notes: null,
  planning_domain: "pension holdings",
  related_record_type: null,
  related_record_id: null,
  advisory_status: "open",
  neutral_reason: "Need current statement",
  created_at: "2026-01-02T00:00:00Z"
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AdvisoryMissingInformationSection", () => {
  it("uses client ID and displays loading, empty, and legacy rows neutrally", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse([])).mockResolvedValueOnce(jsonResponse([legacyRow]));
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<AdvisoryMissingInformationSection clientId={7} />);

    expect(screen.getByText("Loading advisory missing information...")).toBeInTheDocument();
    expect(await screen.findByText("No advisory missing information found.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/7/missing-items",
      expect.objectContaining({ method: "GET" })
    );

    unmount();
    render(<AdvisoryMissingInformationSection clientId={7} />);
    expect(await screen.findByText("Advisory Missing Information Record MD-LEGACY")).toBeInTheDocument();
    expect(screen.getAllByText("Planning Domain: Not recorded")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Advisory Status: Not recorded")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Neutral Reason: Not recorded")[0]).toBeInTheDocument();
  });

  it("creates explicit open advisory missing information without linkage fields and displays 422 errors", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ ...advisoryRow, neutral_reason: "Created reason" }));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<AdvisoryMissingInformationSection clientId={7} />);
    await screen.findByText("No advisory missing information found.");

    const section = sectionQueries();
    fireEvent.change(section.getByLabelText("Planning Domain"), { target: { value: "pension holdings" } });
    expect(section.getByLabelText("Advisory Status")).toHaveValue("open");
    fireEvent.change(section.getByLabelText("Neutral Reason"), { target: { value: "Created reason" } });
    fireEvent.click(section.getByRole("button", { name: "Add Advisory Missing Information" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/missing-items",
        expect.objectContaining({ method: "POST" })
      );
    });
    const postCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "POST") as unknown[];
    expect(requestBody(postCall)).toEqual({
      missing_item_type: "data",
      missing_item_label: "Advisory missing information - pension holdings",
      missing_status: "missing",
      notes: null,
      planning_domain: "pension holdings",
      advisory_status: "open",
      neutral_reason: "Created reason"
    });
    expect(requestBody(postCall)).not.toHaveProperty("related_record_type");
    expect(requestBody(postCall)).not.toHaveProperty("related_record_id");

    unmount();
    vi.unstubAllGlobals();
    const failingFetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ detail: { code: "PLANNING_DOMAIN_REQUIRED" } }, 422, "Unprocessable Entity"));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", failingFetchMock);
    render(<AdvisoryMissingInformationSection clientId={7} />);
    await screen.findByText("No advisory missing information found.");
    fireEvent.click(sectionQueries().getByRole("button", { name: "Add Advisory Missing Information" }));
    expect(await screen.findByText("Unable to save advisory missing information.")).toBeInTheDocument();
    expect(await screen.findByText(/PLANNING_DOMAIN_REQUIRED/)).toBeInTheDocument();
  });

  it("updates only changed editable fields and supports approved advisory statuses", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        return Promise.resolve(jsonResponse({ ...advisoryRow, advisory_status: "resolved" }));
      }
      return Promise.resolve(jsonResponse([advisoryRow]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AdvisoryMissingInformationSection clientId={7} />);
    expect(await screen.findByText("Advisory Missing Information Record MD-V21")).toBeInTheDocument();

    const section = sectionQueries();
    fireEvent.click(section.getByRole("button", { name: "Edit Advisory Missing Information" }));
    expect(section.getByLabelText("Planning Domain")).toHaveValue("pension holdings");
    const statusSelect = section.getByLabelText("Advisory Status") as HTMLSelectElement;
    expect(Array.from(statusSelect.options).map((option) => option.value)).toEqual([
      "open",
      "resolved",
      "no longer relevant"
    ]);
    fireEvent.change(statusSelect, { target: { value: "no longer relevant" } });
    fireEvent.click(section.getByRole("button", { name: "Cancel Edit" }));
    expect(fetchMock.mock.calls.some((call) => requestMethod(call) === "PUT")).toBe(false);
    fireEvent.click(section.getByRole("button", { name: "Edit Advisory Missing Information" }));
    const editStatusSelect = section.getByLabelText("Advisory Status") as HTMLSelectElement;
    fireEvent.change(editStatusSelect, { target: { value: "resolved" } });
    fireEvent.change(section.getByLabelText("Neutral Reason"), { target: { value: "" } });
    fireEvent.click(section.getByRole("button", { name: "Save Advisory Missing Information" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/missing-items/MD-V21",
        expect.objectContaining({ method: "PUT" })
      );
    });
    const putCall = fetchMock.mock.calls.find((call) => requestMethod(call) === "PUT") as unknown[];
    expect(requestBody(putCall)).toEqual({
      advisory_status: "resolved",
      neutral_reason: null
    });
    expect(requestBody(putCall)).not.toHaveProperty("related_record_type");
    expect(requestBody(putCall)).not.toHaveProperty("related_record_id");
  });

  it("does not render linkage fields or prohibited advisory behavior", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([advisoryRow]));
    vi.stubGlobal("fetch", fetchMock);

    render(<AdvisoryMissingInformationSection clientId={7} />);
    expect(await screen.findByText("Advisory Missing Information Record MD-V21")).toBeInTheDocument();

    expect(screen.queryByText("Related Record Type")).not.toBeInTheDocument();
    expect(screen.queryByText("Related Record ID")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/readiness/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/blocking/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recommendation/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/fixation/i)).not.toBeInTheDocument();

    const requestedUrls = fetchMock.mock.calls.map(requestUrl);
    expect(requestedUrls.some((url) => url.includes("related-record"))).toBe(false);
    expect(requestedUrls.some((url) => url.includes("package-e"))).toBe(false);
    expect(fetchMock.mock.calls.some((call) => requestMethod(call) === "DELETE")).toBe(false);
  });
});
