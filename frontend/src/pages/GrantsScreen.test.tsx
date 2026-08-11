import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GrantsScreen } from "./GrantsScreen";

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

function deferredResponse() {
  let resolve!: (value: ReturnType<typeof jsonResponse>) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<ReturnType<typeof jsonResponse>>((next, fail) => {
    resolve = next;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function TransitionHarness() {
  const navigate = useNavigate();
  return <>
    <button type="button" onClick={() => navigate("/clients/8/grants")}>Switch B</button>
    <button type="button" onClick={() => navigate("/clients/7/grants")}>Return A</button>
    <GrantsScreen />
  </>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GrantsScreen", () => {
  it("rejects stale A-to-B-to-A success and finally state", async () => {
    const oldA = deferredResponse();
    const grant = (id: string, employer: string) => ({
      grant_id: id, client_id: id === "B" ? 8 : 7, employer_name: employer,
      employer_withholding_file_number: "WF", exempt_grant_amount: 1,
      grant_receipt_date: "2020-01-01", employment_start_date: "2010-01-01",
      employment_end_date: "2020-01-01",
    });
    const fetchMock = vi.fn()
      .mockReturnValueOnce(oldA.promise)
      .mockResolvedValueOnce(jsonResponse([grant("B", "Client B Grant")]))
      .mockResolvedValueOnce(jsonResponse([grant("A-new", "New A Grant")]));
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/clients/7/grants"]}><Routes>
      <Route path="/clients/:clientId/grants" element={<TransitionHarness />} />
    </Routes></MemoryRouter>);

    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    expect(await screen.findByText("Client B Grant")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Return A" }));
    expect(await screen.findByText("New A Grant")).toBeInTheDocument();
    await act(async () => oldA.resolve(jsonResponse([grant("A-old", "Old A Grant")])));
    expect(screen.queryByText("Old A Grant")).not.toBeInTheDocument();
    expect(screen.getByText("New A Grant")).toBeInTheDocument();
    expect(screen.queryByText("Loading grants...")).not.toBeInTheDocument();
  });

  it("rejects stale mutation rejection and finally after client change", async () => {
    const mutation = deferredResponse();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockReturnValueOnce(mutation.promise)
      .mockResolvedValueOnce(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter initialEntries={["/clients/7/grants"]}><Routes>
      <Route path="/clients/:clientId/grants" element={<TransitionHarness />} />
    </Routes></MemoryRouter>);
    await screen.findByText("No grants found.");
    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "Employer" } });
    fireEvent.change(screen.getByLabelText("Employer Withholding File Number"), { target: { value: "WF" } });
    fireEvent.change(screen.getByLabelText("Exempt Grant Amount"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Grant Receipt Date"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment Start Date"), { target: { value: "2010-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment End Date"), { target: { value: "2020-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch B" }));
    await screen.findByText("No grants found.");
    await act(async () => mutation.reject(new Error("stale A failure")));
    expect(screen.queryByText("stale A failure")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Grant" })).toBeEnabled();
  });

  it("adds, edits, deletes, and saves grants without calculation calls", async () => {
    const firstGrant = {
      grant_id: "GR-1",
      client_id: 7,
      employer_name: "Employer Inc",
      employer_withholding_file_number: "WF-1",
      exempt_grant_amount: 10000,
      grant_receipt_date: "2020-01-01",
      employment_start_date: "2010-01-01",
      employment_end_date: "2020-01-01"
    };
    const secondGrant = {
      grant_id: "GR-2",
      client_id: 7,
      employer_name: "New Employer",
      employer_withholding_file_number: "WF-2",
      exempt_grant_amount: 9000,
      grant_receipt_date: "2022-01-01",
      employment_start_date: "2021-01-01",
      employment_end_date: "2022-01-01"
    };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([firstGrant]))
      .mockResolvedValueOnce(jsonResponse(secondGrant))
      .mockResolvedValueOnce(jsonResponse([firstGrant, secondGrant]))
      .mockResolvedValueOnce(jsonResponse({ ...firstGrant, employer_name: "Updated Employer", exempt_grant_amount: 16000 }))
      .mockResolvedValueOnce(
        jsonResponse([{ ...firstGrant, employer_name: "Updated Employer", exempt_grant_amount: 16000 }, secondGrant])
      )
      .mockResolvedValueOnce(jsonResponse({ deleted: true }))
      .mockResolvedValueOnce(jsonResponse([secondGrant]));

    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={[{ pathname: "/clients/7/grants", state: { clientName: "Dana Levi" } }]}>
        <Routes>
          <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("Grant ID: GR-1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "New Employer" } });
    fireEvent.change(screen.getByLabelText("Employer Withholding File Number"), { target: { value: "WF-2" } });
    fireEvent.change(screen.getByLabelText("Exempt Grant Amount"), { target: { value: "9000" } });
    fireEvent.change(screen.getByLabelText("Grant Receipt Date"), { target: { value: "2022-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment Start Date"), { target: { value: "2021-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment End Date"), { target: { value: "2022-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Grant" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/grants",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            employer_name: "New Employer",
            employer_withholding_file_number: "WF-2",
            employment_start_date: "2021-01-01",
            employment_end_date: "2022-01-01",
            grant_receipt_date: "2022-01-01",
            exempt_grant_amount: "9000"
          })
        })
      );
    });
    expect(await screen.findByText("Grant ID: GR-2")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Edit Grant" })[0]);
    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "Updated Employer" } });
    fireEvent.change(screen.getByLabelText("Exempt Grant Amount"), { target: { value: "16000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Grant" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/api/clients/7/grants/GR-1",
        expect.objectContaining({ method: "PUT" })
      );
    });
    expect(await screen.findByText("Exempt Grant Amount: 16000")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete Grant" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        6,
        "/api/clients/7/grants/GR-1",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    const requestedUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(requestedUrls.every((url) => !url.includes("/fixation/validate") && !url.includes("/fixation/calculate"))).toBe(
      true
    );
    expect(screen.getByRole("link", { name: "Back to employment history" })).toHaveAttribute(
      "href",
      "/clients/7/employment-history"
    );
    expect(screen.getByRole("link", { name: "Back to client detail" })).toHaveAttribute("href", "/clients/7");
  });

  it("preserves blank numeric input for backend validation instead of coercing it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ detail: [{ msg: "exempt_grant_amount must be numeric" }] }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7/grants"]}>
        <Routes>
          <Route path="/clients/:clientId/grants" element={<GrantsScreen />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("No grants found.");
    fireEvent.change(screen.getByLabelText("Employer Name"), { target: { value: "Employer" } });
    fireEvent.change(screen.getByLabelText("Employer Withholding File Number"), { target: { value: "WF" } });
    fireEvent.change(screen.getByLabelText("Grant Receipt Date"), { target: { value: "2022-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment Start Date"), { target: { value: "2021-01-01" } });
    fireEvent.change(screen.getByLabelText("Employment End Date"), { target: { value: "2022-01-01" } });
    fireEvent.submit(screen.getByRole("button", { name: "Add Grant" }).closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "/api/clients/7/grants",
        expect.objectContaining({
          body: JSON.stringify({
            employer_name: "Employer",
            employer_withholding_file_number: "WF",
            employment_start_date: "2021-01-01",
            employment_end_date: "2022-01-01",
            grant_receipt_date: "2022-01-01",
            exempt_grant_amount: ""
          })
        })
      );
    });
  });
});
