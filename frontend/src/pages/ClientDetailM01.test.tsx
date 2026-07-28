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

    expect(await screen.findByRole("heading", { name: "Client Case Foundation" })).toBeInTheDocument();
    expect(screen.getByText("Completeness Status: complete")).toBeInTheDocument();
    expect(screen.getByText("Lifecycle Status: draft")).toBeInTheDocument();
    expect(screen.getByLabelText("Employment Status")).toHaveValue("salaried_employee");
    expect(screen.getByLabelText("Planned Retirement Age")).toHaveValue(67);

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated Client" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    expect(await screen.findByText("Client case facts saved.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients/1/case",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining('"employment_status":"salaried_employee"')
      })
    );

    fireEvent.click(screen.getByRole("button", { name: "Move to intake" }));
    expect(await screen.findByText("Lifecycle Status: intake")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move to draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move to analysis" })).toBeInTheDocument();
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
    expect(await screen.findByText("Full Name: Client B")).toBeInTheDocument();
    oldA.resolve(clientResponse(1, "Stale Client A"));

    await waitFor(() => expect(screen.queryByText(/Stale Client A/)).not.toBeInTheDocument());
    expect(screen.getByText("Full Name: Client B")).toBeInTheDocument();
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
    expect(await screen.findByText("Full Name: Client B")).toBeInTheDocument();
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
      expect(screen.getByText("Loading client details...")).toBeInTheDocument();
    });
    currentB.resolve(clientResponse(2, "Client B"));
    expect(await screen.findByText("Full Name: Client B")).toBeInTheDocument();
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

    await screen.findByText("Full Name: Client A");
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("Full Name: Client B");
    fireEvent.click(screen.getByRole("button", { name: "Go A" }));
    await screen.findByText("Full Name: Client A Revisited");
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    newMutation.resolve(jsonResponse(m01Case(1, "New A Mutation Result")));
    expect(await screen.findByText("Full Name: New A Mutation Result")).toBeInTheDocument();

    oldMutation.resolve(jsonResponse(m01Case(1, "Stale A Mutation Result")));
    await waitFor(() => expect(screen.queryByText(/Stale A Mutation Result/)).not.toBeInTheDocument());
    expect(screen.getByText("Full Name: New A Mutation Result")).toBeInTheDocument();
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

    await screen.findByText("Full Name: Client A");
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("Full Name: Client B");
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

    await screen.findByText("Full Name: Client A");
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    fireEvent.click(screen.getByRole("button", { name: "Go B" }));
    await screen.findByText("Full Name: Client B");
    fireEvent.click(screen.getByRole("button", { name: "Save Case Facts" }));
    expect(screen.getByRole("button", { name: "Saving Case Facts..." })).toBeDisabled();

    oldMutation.resolve(jsonResponse(m01Case(1, "Old A Result")));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Saving Case Facts..." })).toBeDisabled();
    });

    currentMutation.resolve(jsonResponse(m01Case(2, "Current B Result")));
    expect(await screen.findByText("Full Name: Current B Result")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Case Facts" })).toBeEnabled();
  });
});
