import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ActualCapitalizationsScreen } from "./ActualCapitalizationsScreen";

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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ActualCapitalizationsScreen", () => {
  it("preserves unsaved capitalization edits after CAS 409 and prevents automatic retry", async () => {
    const row = { capitalization_id: "AC-1", version: 1, client_id: 7, amount: 500, capitalization_date: "2023-01-01", source_label: "Manual", source_basis: null, planner_assertion: null, planner_assertion_basis: null, notes: "Original" };
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => Promise.resolve(init?.method === "PUT"
      ? { ...jsonResponse({ detail: { code: "RECORD_VERSION_CONFLICT" } }), ok: false, status: 409, statusText: "Conflict" }
      : jsonResponse([row])));
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/clients/7/actual-capitalizations"]}><Routes><Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("מזהה היוון: AC-1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "עריכת היוון בפועל" }));
    fireEvent.change(screen.getByLabelText("הערות"), { target: { value: "Draft kept" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת היוון בפועל" }));
    expect(await screen.findByText(/השמירה לא בוצעה/)).toBeInTheDocument();
    expect(screen.getByLabelText("הערות")).toHaveValue("Draft kept");
    expect(screen.getByRole("button", { name: "שמירת היוון בפועל" })).toBeDisabled();
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === "PUT")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /רענון רשומות להשוואה/ }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(screen.getByLabelText("הערות")).toHaveValue("Draft kept");
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === "PUT")).toHaveLength(1);
  });
  it("adds, edits, deletes, and saves capitalizations without calculation calls", async () => {
    vi.stubGlobal("confirm", vi.fn(() => true));
    const firstCapitalization = {
      capitalization_id: "AC-1",
      version: 1,
      client_id: 7,
      amount: 500,
      capitalization_date: "2023-01-01",
      source_label: "Manual",
      source_basis: null,
      planner_assertion: null,
      planner_assertion_basis: null,
      notes: "Existing capitalization"
    };
    const secondCapitalization = {
      capitalization_id: "AC-2",
      version: 1,
      client_id: 7,
      amount: 750,
      capitalization_date: "2024-02-01",
      source_label: "Imported",
      source_basis: "capitalization certificate",
      planner_assertion: "advisor confirmed amount",
      planner_assertion_basis: "reviewed certificate",
      notes: "Created capitalization"
    };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([firstCapitalization]))
      .mockResolvedValueOnce(jsonResponse(secondCapitalization))
      .mockResolvedValueOnce(jsonResponse([firstCapitalization, secondCapitalization]))
      .mockResolvedValueOnce(jsonResponse([firstCapitalization, secondCapitalization]))
      .mockResolvedValueOnce(jsonResponse({ ...firstCapitalization, version: 2, amount: 650, source_label: "Updated" }))
      .mockResolvedValueOnce(jsonResponse([{ ...firstCapitalization, version: 2, amount: 650, source_label: "Updated" }, secondCapitalization]))
      .mockResolvedValueOnce(jsonResponse({ deleted: true }))
      .mockResolvedValueOnce(jsonResponse([secondCapitalization]));

    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[
          { pathname: "/clients/7/actual-capitalizations", state: { clientName: "Dana Levi" } }
        ]}
      >
        <Routes>
          <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("מזהה היוון: AC-1")).toBeInTheDocument();
    expect(screen.queryByText("Edit and delete are unavailable in this workflow.")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("סכום"), { target: { value: "750" } });
    fireEvent.change(screen.getByLabelText("תאריך היוון"), { target: { value: "2024-02-01" } });
    fireEvent.change(screen.getByLabelText("תיאור המקור"), { target: { value: "Imported" } });
    fireEvent.change(screen.getByLabelText("בסיס המקור"), { target: { value: "capitalization certificate" } });
    fireEvent.change(screen.getByLabelText("הצהרת המתכנן"), { target: { value: "advisor confirmed amount" } });
    fireEvent.change(screen.getByLabelText("בסיס הצהרת המתכנן"), { target: { value: "reviewed certificate" } });
    fireEvent.change(screen.getByLabelText("הערות"), { target: { value: "Created capitalization" } });
    fireEvent.click(screen.getByRole("button", { name: "הוספת היוון בפועל" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/actual-capitalizations",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            amount: "750",
            capitalization_date: "2024-02-01",
            source_label: "Imported",
            source_basis: "capitalization certificate",
            planner_assertion: "advisor confirmed amount",
            planner_assertion_basis: "reviewed certificate",
            notes: "Created capitalization"
          })
        })
      );
    });
    expect(await screen.findByText("מזהה היוון: AC-2")).toBeInTheDocument();
    expect(await screen.findByText("בסיס המקור: capitalization certificate")).toBeInTheDocument();
    expect(await screen.findByText("הצהרת המתכנן: advisor confirmed amount")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "עריכת היוון בפועל" })[0]);
    fireEvent.change(screen.getByLabelText("סכום"), { target: { value: "650" } });
    fireEvent.change(screen.getByLabelText("תיאור המקור"), { target: { value: "Updated" } });
    fireEvent.click(screen.getByRole("button", { name: "שמירת היוון בפועל" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        5,
        "/api/clients/7/actual-capitalizations/AC-1",
        expect.objectContaining({ method: "PUT" })
      );
    });
    expect(await screen.findByText("סכום: 650")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "מחיקת היוון בפועל" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        7,
        "/api/clients/7/actual-capitalizations/AC-1?expected_version=2",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    const requestedUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(requestedUrls.every((url) => !url.includes("/fixation/validate") && !url.includes("/fixation/calculate"))).toBe(
      true
    );
    expect(screen.getByRole("link", { name: "חזרה למענקים" })).toHaveAttribute("href", "/clients/7/grants");
    expect(screen.getByRole("link", { name: "המשך לנתוני קיבוע זכויות" })).toHaveAttribute(
      "href",
      "/clients/7/fixation/input"
    );
  });

  it("preserves blank numeric input for backend validation instead of coercing it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ detail: [{ msg: "amount must be numeric" }] }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7/actual-capitalizations"]}>
        <Routes>
          <Route path="/clients/:clientId/actual-capitalizations" element={<ActualCapitalizationsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("לא נמצאו היוונים בפועל.");
    fireEvent.change(screen.getByLabelText("תאריך היוון"), { target: { value: "2024-02-01" } });
    fireEvent.submit(
      screen.getByRole("button", { name: "הוספת היוון בפועל" }).closest("form") as HTMLFormElement
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/actual-capitalizations",
        expect.objectContaining({
          body: JSON.stringify({
            amount: "",
            capitalization_date: "2024-02-01",
            source_label: null,
            source_basis: null,
            planner_assertion: null,
            planner_assertion_basis: null,
            notes: null
          })
        })
      );
    });
  });
});
