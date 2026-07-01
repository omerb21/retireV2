import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClientDetailScreen } from "./ClientDetailScreen";
import { RetirementPlanningFactsSection } from "./RetirementPlanningFactsSection";

type ResourceName =
  | "pension-holdings"
  | "capital-assets"
  | "recurring-incomes"
  | "recurring-expenses"
  | "retirement-timing-work-intentions";

type ResourceConfig = {
  resourceName: ResourceName;
  heading: string;
  addButton: string;
  editButton: string;
  saveButton: string;
  rowId: number;
  rowText: string;
  fillCreate: (section: ReturnType<typeof within>) => void;
  createPayload: Record<string, unknown>;
  firstEditLabel: string;
  firstEditValue: string;
  changedEditLabel: string;
  changedEditValue: string;
  blankEditLabel?: string;
  updatePayload: Record<string, unknown>;
  amountField?: string;
};

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

function sectionByHeading(name: string): HTMLElement {
  return screen.getByRole("heading", { name }).closest("section") as HTMLElement;
}

function sectionQueries(name: string): ReturnType<typeof within> {
  return within(sectionByHeading(name));
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

function callsFor(fetchMock: ReturnType<typeof vi.fn>, resourceName: ResourceName, method?: string) {
  return fetchMock.mock.calls.filter((call) => {
    const matchesResource = requestUrl(call).includes(`/api/clients/7/${resourceName}`);
    return matchesResource && (method === undefined || requestMethod(call) === method);
  });
}

function expectNoForbiddenPayloadFields(body: Record<string, unknown>) {
  expect(body).not.toHaveProperty("id");
  expect(body).not.toHaveProperty("client_id");
  expect(body).not.toHaveProperty("created_at");
  expect(body).not.toHaveProperty("updated_at");
  expect(body).not.toHaveProperty("lifecycle_status");
}

function expectNoProhibitedPackageCRequests(fetchMock: ReturnType<typeof vi.fn>) {
  const urls = fetchMock.mock.calls.map(requestUrl);
  expect(urls.some((url) => url.includes("planner-assumption") || url.includes("planner-assumptions"))).toBe(false);
  expect(urls.some((url) => url.includes("missing-item") || url.includes("missing-items"))).toBe(false);
  expect(urls.some((url) => url.toLowerCase().includes("supersede"))).toBe(false);
  expect(urls.some((url) => url.toLowerCase().includes("lifecycle") && !url.includes("lifecycle_status="))).toBe(false);
  expect(fetchMock.mock.calls.some((call) => requestMethod(call) === "DELETE")).toBe(false);
}

function expectNoGetOneRequests(fetchMock: ReturnType<typeof vi.fn>) {
  for (const config of resourceConfigs) {
    const getOneCalls = fetchMock.mock.calls.filter((call) => (
      requestUrl(call) === `/api/clients/7/${config.resourceName}/${config.rowId}` &&
      requestMethod(call) === "GET"
    ));
    expect(getOneCalls).toHaveLength(0);
  }
}

function makeFetchMockWithRows() {
  return vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "POST" || method === "PUT") {
      return Promise.resolve(jsonResponse({ id: 99, lifecycle_status: "current", source_status: "not recorded", verification_state: "reviewed" }));
    }

    for (const config of resourceConfigs) {
      if (url.includes(`/${config.resourceName}?`)) {
        return Promise.resolve(jsonResponse(rowsByResource[config.resourceName]));
      }
    }

    return Promise.resolve(jsonResponse([]));
  });
}

const rowsByResource: Record<ResourceName, Record<string, unknown>[]> = {
  "pension-holdings": [
    {
      id: 11,
      client_id: 7,
      provider_name: "Existing Pension Provider",
      product_type: "pension fund",
      product_name: "Existing Product",
      account_reference: "ACC-1",
      known_balance_amount: "1000.50",
      balance_as_of_date: "2026-01-01",
      known_monthly_pension_amount: "250.75",
      pension_amount_as_of_date: "2026-01-02",
      lifecycle_status: "current",
      source_status: "client stated",
      verification_state: "reviewed",
      source_type: "statement",
      source_date: "2026-01-03",
      source_note: "Existing source",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z"
    }
  ],
  "capital-assets": [
    {
      id: 21,
      client_id: 7,
      asset_category: "bank deposit",
      asset_description: "Existing deposit",
      known_value_amount: "2000.25",
      value_as_of_date: "2026-01-02",
      liquidity_note: "Liquid",
      restriction_note: "No restriction",
      lifecycle_status: "current",
      source_status: "planner entered",
      verification_state: "verified",
      source_type: "bank statement",
      source_date: null,
      source_note: null,
      created_at: "2026-01-02T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z"
    }
  ],
  "recurring-incomes": [
    {
      id: 31,
      client_id: 7,
      income_category: "employment",
      description: "Existing income",
      amount: "300.10",
      amount_basis: "gross",
      frequency: "monthly",
      continuation_status: "ongoing",
      start_date: "2026-01-03",
      end_date: null,
      lifecycle_status: "current",
      source_status: "not recorded",
      verification_state: "collected - not yet reviewed",
      source_type: null,
      source_date: null,
      source_note: null,
      created_at: "2026-01-03T00:00:00Z",
      updated_at: "2026-01-03T00:00:00Z"
    }
  ],
  "recurring-expenses": [
    {
      id: 41,
      client_id: 7,
      expense_category: "housing",
      description: "Existing expense",
      amount: "400.20",
      frequency: "monthly",
      expense_type: "mandatory",
      continuation_status: "ongoing",
      start_date: "2026-01-04",
      end_date: null,
      lifecycle_status: "current",
      source_status: "not recorded",
      verification_state: "reviewed",
      source_type: null,
      source_date: null,
      source_note: null,
      created_at: "2026-01-04T00:00:00Z",
      updated_at: "2026-01-04T00:00:00Z"
    }
  ],
  "retirement-timing-work-intentions": [
    {
      id: 51,
      client_id: 7,
      timing_confidence: "stated intention",
      work_after_retirement_intention: "undecided",
      planned_work_end_date: "2029-12-31",
      intended_pension_start_date: null,
      other_known_retirement_date: "2030-01-01",
      other_known_retirement_date_label: "Target date",
      anticipated_work_end_date: null,
      work_intention_note: "Existing timing note",
      lifecycle_status: "current",
      source_status: "client stated",
      verification_state: "partially verified",
      source_type: null,
      source_date: null,
      source_note: null,
      created_at: "2026-01-05T00:00:00Z",
      updated_at: "2026-01-05T00:00:00Z"
    }
  ]
};

const resourceConfigs: ResourceConfig[] = [
  {
    resourceName: "pension-holdings",
    heading: "Pension holdings",
    addButton: "Add Pension Holding",
    editButton: "Edit Pension Holding",
    saveButton: "Save Pension Holding",
    rowId: 11,
    rowText: "Provider Name: Existing Pension Provider",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("Provider Name"), { target: { value: "Migdal" } });
      fireEvent.change(section.getByLabelText("Product Type"), { target: { value: "pension fund" } });
      fireEvent.change(section.getByLabelText("Known Balance Amount"), { target: { value: "123.45" } });
      fireEvent.change(section.getByLabelText("Balance As Of Date"), { target: { value: "2026-02-01" } });
    },
    createPayload: {
      provider_name: "Migdal",
      product_type: "pension fund",
      known_balance_amount: "123.45",
      balance_as_of_date: "2026-02-01"
    },
    firstEditLabel: "Provider Name",
    firstEditValue: "Existing Pension Provider",
    changedEditLabel: "Provider Name",
    changedEditValue: "Updated Provider",
    blankEditLabel: "Product Name",
    updatePayload: {
      provider_name: "Updated Provider",
      product_name: null
    },
    amountField: "known_balance_amount"
  },
  {
    resourceName: "capital-assets",
    heading: "Capital assets",
    addButton: "Add Capital Asset",
    editButton: "Edit Capital Asset",
    saveButton: "Save Capital Asset",
    rowId: 21,
    rowText: "Asset Description: Existing deposit",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("Asset Category"), { target: { value: "bank deposit" } });
      fireEvent.change(section.getByLabelText("Asset Description"), { target: { value: "Savings account" } });
      fireEvent.change(section.getByLabelText("Known Value Amount"), { target: { value: "456.78" } });
      fireEvent.change(section.getByLabelText("Value As Of Date"), { target: { value: "2026-02-02" } });
    },
    createPayload: {
      asset_category: "bank deposit",
      asset_description: "Savings account",
      known_value_amount: "456.78",
      value_as_of_date: "2026-02-02"
    },
    firstEditLabel: "Asset Description",
    firstEditValue: "Existing deposit",
    changedEditLabel: "Asset Description",
    changedEditValue: "Updated deposit",
    blankEditLabel: "Liquidity Note",
    updatePayload: {
      asset_description: "Updated deposit",
      liquidity_note: null
    },
    amountField: "known_value_amount"
  },
  {
    resourceName: "recurring-incomes",
    heading: "Recurring incomes",
    addButton: "Add Recurring Income",
    editButton: "Edit Recurring Income",
    saveButton: "Save Recurring Income",
    rowId: 31,
    rowText: "Description: Existing income",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("Income Category"), { target: { value: "employment" } });
      fireEvent.change(section.getByLabelText("Description"), { target: { value: "Salary" } });
      fireEvent.change(section.getByLabelText("Amount"), { target: { value: "1000.00" } });
      fireEvent.change(section.getByLabelText("Amount Basis"), { target: { value: "gross" } });
      fireEvent.change(section.getByLabelText("Frequency"), { target: { value: "monthly" } });
      fireEvent.change(section.getByLabelText("Continuation Status"), { target: { value: "ongoing" } });
    },
    createPayload: {
      income_category: "employment",
      description: "Salary",
      amount: "1000.00",
      amount_basis: "gross",
      frequency: "monthly",
      continuation_status: "ongoing"
    },
    firstEditLabel: "Description",
    firstEditValue: "Existing income",
    changedEditLabel: "Description",
    changedEditValue: "Updated income",
    blankEditLabel: "Start Date",
    updatePayload: {
      description: "Updated income",
      start_date: null
    },
    amountField: "amount"
  },
  {
    resourceName: "recurring-expenses",
    heading: "Recurring expenses",
    addButton: "Add Recurring Expense",
    editButton: "Edit Recurring Expense",
    saveButton: "Save Recurring Expense",
    rowId: 41,
    rowText: "Description: Existing expense",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("Expense Category"), { target: { value: "housing" } });
      fireEvent.change(section.getByLabelText("Description"), { target: { value: "Rent" } });
      fireEvent.change(section.getByLabelText("Amount"), { target: { value: "200.00" } });
      fireEvent.change(section.getByLabelText("Frequency"), { target: { value: "monthly" } });
      fireEvent.change(section.getByLabelText("Expense Type"), { target: { value: "mandatory" } });
      fireEvent.change(section.getByLabelText("Continuation Status"), { target: { value: "ongoing" } });
    },
    createPayload: {
      expense_category: "housing",
      description: "Rent",
      amount: "200.00",
      frequency: "monthly",
      expense_type: "mandatory",
      continuation_status: "ongoing"
    },
    firstEditLabel: "Description",
    firstEditValue: "Existing expense",
    changedEditLabel: "Description",
    changedEditValue: "Updated expense",
    blankEditLabel: "Start Date",
    updatePayload: {
      description: "Updated expense",
      start_date: null
    },
    amountField: "amount"
  },
  {
    resourceName: "retirement-timing-work-intentions",
    heading: "Retirement timing and work intentions",
    addButton: "Add Retirement Timing and Work Intention",
    editButton: "Edit Retirement Timing and Work Intention",
    saveButton: "Save Retirement Timing and Work Intention",
    rowId: 51,
    rowText: "Work After Retirement Intention: undecided",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("Timing Confidence"), { target: { value: "known" } });
      fireEvent.change(section.getByLabelText("Work After Retirement Intention"), {
        target: { value: "continue working" }
      });
      fireEvent.change(section.getByLabelText("Other Known Retirement Date"), { target: { value: "2030-01-01" } });
      fireEvent.change(section.getByLabelText("Other Known Retirement Date Label"), {
        target: { value: "Client target" }
      });
    },
    createPayload: {
      timing_confidence: "known",
      work_after_retirement_intention: "continue working",
      other_known_retirement_date: "2030-01-01",
      other_known_retirement_date_label: "Client target"
    },
    firstEditLabel: "Work After Retirement Intention",
    firstEditValue: "undecided",
    changedEditLabel: "Work Intention Note",
    changedEditValue: "Updated timing note",
    blankEditLabel: "Planned Work End Date",
    updatePayload: {
      work_intention_note: "Updated timing note",
      planned_work_end_date: null
    }
  }
];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RetirementPlanningFactsSection", () => {
  it("proves client-detail integration and allowed Package C UI boundary", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/clients/7") {
        return Promise.resolve(jsonResponse({
          client_id: 7,
          full_name: "Dana Levi",
          id_number: "123",
          birth_date: null,
          file_status: "open",
          professional_identification_status: "identification_incomplete"
        }));
      }
      if (url === "/api/clients/7/profile") {
        return Promise.resolve(jsonResponse({ profile: null }));
      }
      if (
        url === "/api/clients/7/clearinghouse-snapshots" ||
        url === "/api/clients/7/documents" ||
        url === "/api/clients/7/missing-items"
      ) {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter initialEntries={["/clients/7"]}>
        <Routes>
          <Route path="/clients/:clientId" element={<ClientDetailScreen />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Retirement Planning Facts" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/pension-holdings?lifecycle_status=current",
        expect.objectContaining({ method: "GET" })
      );
    });

    for (const config of resourceConfigs) {
      expect(screen.getByRole("heading", { name: config.heading })).toBeInTheDocument();
    }
    expect(screen.getAllByLabelText("Lifecycle Filter")).toHaveLength(5);
    expect(screen.queryByText("PlannerAssumption")).not.toBeInTheDocument();
    expect(screen.queryByText("Planner Assumption")).not.toBeInTheDocument();
    expect(screen.queryByText("MissingDataItem maintenance")).not.toBeInTheDocument();
    expect(screen.queryByText("Missing Data Item maintenance")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /supersede/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /change lifecycle/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /retirement planning facts/i })).not.toBeInTheDocument();
  });

  it("proves loading and empty states for each approved fact section", async () => {
    const pendingRequests: Array<() => void> = [];
    const fetchMock = vi.fn(() => new Promise((resolve) => {
      pendingRequests.push(() => resolve(jsonResponse([])));
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);

    expect(screen.getByText("Loading pension holdings...")).toBeInTheDocument();
    expect(screen.getByText("Loading capital assets...")).toBeInTheDocument();
    expect(screen.getByText("Loading recurring incomes...")).toBeInTheDocument();
    expect(screen.getByText("Loading recurring expenses...")).toBeInTheDocument();
    expect(screen.getByText("Loading retirement timing and work intentions...")).toBeInTheDocument();

    for (const resolveRequest of pendingRequests) {
      resolveRequest();
    }

    expect(await screen.findByText("No pension holdings found for the selected lifecycle filter.")).toBeInTheDocument();
    expect(await screen.findByText("No capital assets found for the selected lifecycle filter.")).toBeInTheDocument();
    expect(await screen.findByText("No recurring incomes found for the selected lifecycle filter.")).toBeInTheDocument();
    expect(await screen.findByText("No recurring expenses found for the selected lifecycle filter.")).toBeInTheDocument();
    expect(
      await screen.findByText("No retirement timing and work intentions found for the selected lifecycle filter.")
    ).toBeInTheDocument();
  });

  it("proves default current loading and local lifecycle filtering for all five resources", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    await screen.findByText("No pension holdings found for the selected lifecycle filter.");

    for (const config of resourceConfigs) {
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/clients/7/${config.resourceName}?lifecycle_status=current`,
        expect.objectContaining({ method: "GET" })
      );
      const lifecycleSelect = sectionQueries(config.heading).getByLabelText("Lifecycle Filter") as HTMLSelectElement;
      expect(Array.from(lifecycleSelect.options).map((option) => option.value)).toEqual([
        "current",
        "superseded",
        "all"
      ]);
    }

    const callsAfterInitialLoad = fetchMock.mock.calls.length;
    fireEvent.change(sectionQueries("Pension holdings").getByLabelText("Lifecycle Filter"), {
      target: { value: "superseded" }
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/pension-holdings?lifecycle_status=superseded",
        expect.objectContaining({ method: "GET" })
      );
    });
    expect(fetchMock.mock.calls.slice(callsAfterInitialLoad).map(requestUrl)).toEqual([
      "/api/clients/7/pension-holdings?lifecycle_status=superseded"
    ]);

    const callsAfterSuperseded = fetchMock.mock.calls.length;
    fireEvent.change(sectionQueries("Capital assets").getByLabelText("Lifecycle Filter"), {
      target: { value: "all" }
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/capital-assets?lifecycle_status=all",
        expect.objectContaining({ method: "GET" })
      );
    });
    expect(fetchMock.mock.calls.slice(callsAfterSuperseded).map(requestUrl)).toEqual([
      "/api/clients/7/capital-assets?lifecycle_status=all"
    ]);
  });

  it.each(resourceConfigs)("proves inline create payload and refresh behavior for $heading", async (config) => {
    const fetchMock = makeFetchMockWithRows();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    expect(await screen.findByText(config.rowText)).toBeInTheDocument();
    const initialResourceCalls = callsFor(fetchMock, config.resourceName, "GET").length;

    const section = sectionQueries(config.heading);
    config.fillCreate(section);
    fireEvent.click(section.getByRole("button", { name: config.addButton }));

    await waitFor(() => {
      expect(callsFor(fetchMock, config.resourceName, "POST")).toHaveLength(1);
    });
    const postCall = callsFor(fetchMock, config.resourceName, "POST")[0];
    expect(requestUrl(postCall)).toBe(`/api/clients/7/${config.resourceName}`);
    const body = requestBody(postCall);
    expect(body).toEqual(config.createPayload);
    expectNoForbiddenPayloadFields(body);
    if (config.amountField !== undefined) {
      expect(typeof body[config.amountField]).toBe("string");
    }
    expect(body).not.toHaveProperty("source_status");
    expect(body).not.toHaveProperty("verification_state");

    await waitFor(() => {
      expect(callsFor(fetchMock, config.resourceName, "GET")).toHaveLength(initialResourceCalls + 1);
    });
    const postCallIndex = fetchMock.mock.calls.findIndex((call) => call === postCall);
    const callsAfterPost = fetchMock.mock.calls.slice(postCallIndex + 1).map(requestUrl);
    expect(callsAfterPost).toEqual([`/api/clients/7/${config.resourceName}?lifecycle_status=current`]);
    expectNoProhibitedPackageCRequests(fetchMock);
  });

  it.each(resourceConfigs)("proves inline edit prefill, partial PUT, cancel, and no GET-one for $heading", async (config) => {
    const fetchMock = makeFetchMockWithRows();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    expect(await screen.findByText(config.rowText)).toBeInTheDocument();
    const section = sectionQueries(config.heading);
    const initialResourceCalls = callsFor(fetchMock, config.resourceName, "GET").length;

    fireEvent.click(section.getByRole("button", { name: config.editButton }));
    expect(section.getByLabelText(config.firstEditLabel)).toHaveValue(config.firstEditValue);
    fireEvent.click(section.getByRole("button", { name: "Cancel Edit" }));
    expect(callsFor(fetchMock, config.resourceName, "PUT")).toHaveLength(0);
    expect(callsFor(fetchMock, config.resourceName, "POST")).toHaveLength(0);

    fireEvent.click(section.getByRole("button", { name: config.editButton }));
    fireEvent.change(section.getByLabelText(config.changedEditLabel), {
      target: { value: config.changedEditValue }
    });
    if (config.blankEditLabel !== undefined) {
      fireEvent.change(section.getByLabelText(config.blankEditLabel), { target: { value: "" } });
    }
    fireEvent.click(section.getByRole("button", { name: config.saveButton }));

    await waitFor(() => {
      expect(callsFor(fetchMock, config.resourceName, "PUT")).toHaveLength(1);
    });
    const putCall = callsFor(fetchMock, config.resourceName, "PUT")[0];
    expect(requestUrl(putCall)).toBe(`/api/clients/7/${config.resourceName}/${config.rowId}`);
    const body = requestBody(putCall);
    expect(body).toEqual(config.updatePayload);
    expect(Object.keys(body).length).toBeLessThan(Object.keys(config.createPayload).length);
    expectNoForbiddenPayloadFields(body);

    await waitFor(() => {
      expect(callsFor(fetchMock, config.resourceName, "GET")).toHaveLength(initialResourceCalls + 1);
    });
    const putCallIndex = fetchMock.mock.calls.findIndex((call) => call === putCall);
    const callsAfterPut = fetchMock.mock.calls.slice(putCallIndex + 1).map(requestUrl);
    expect(callsAfterPut).toEqual([`/api/clients/7/${config.resourceName}?lifecycle_status=current`]);
    expectNoGetOneRequests(fetchMock);
    expectNoProhibitedPackageCRequests(fetchMock);
  });

  it("proves API 422 responses are visibly rendered through the existing error display pattern", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ detail: [{ msg: "provider_name is required" }] }, 422, "Unprocessable Entity"));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    await screen.findByText("No pension holdings found for the selected lifecycle filter.");
    fireEvent.click(sectionQueries("Pension holdings").getByRole("button", { name: "Add Pension Holding" }));

    expect(await screen.findByText("Unable to save pension holdings.")).toBeInTheDocument();
    expect(await screen.findByText(/provider_name is required/)).toBeInTheDocument();
  });

  it("proves approved conditional fields appear only after paired values are populated", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    await screen.findByText("No pension holdings found for the selected lifecycle filter.");

    const pension = sectionQueries("Pension holdings");
    expect(pension.queryByLabelText("Balance As Of Date")).not.toBeInTheDocument();
    expect(pension.queryByLabelText("Pension Amount As Of Date")).not.toBeInTheDocument();
    fireEvent.change(pension.getByLabelText("Known Balance Amount"), { target: { value: "123.45" } });
    fireEvent.change(pension.getByLabelText("Known Monthly Pension Amount"), { target: { value: "67.89" } });
    expect(pension.getByLabelText("Balance As Of Date")).toBeInTheDocument();
    expect(pension.getByLabelText("Pension Amount As Of Date")).toBeInTheDocument();

    const capital = sectionQueries("Capital assets");
    expect(capital.queryByLabelText("Value As Of Date")).not.toBeInTheDocument();
    fireEvent.change(capital.getByLabelText("Known Value Amount"), { target: { value: "456.78" } });
    expect(capital.getByLabelText("Value As Of Date")).toBeInTheDocument();

    const timing = sectionQueries("Retirement timing and work intentions");
    expect(timing.queryByLabelText("Other Known Retirement Date Label")).not.toBeInTheDocument();
    fireEvent.change(timing.getByLabelText("Other Known Retirement Date"), { target: { value: "2030-01-01" } });
    expect(timing.getByLabelText("Other Known Retirement Date Label")).toBeInTheDocument();
  });

  it("proves source and verification metadata are included only when explicitly changed and use neutral wording", async () => {
    const fetchMock = makeFetchMockWithRows();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    expect(await screen.findByText("Provider Name: Existing Pension Provider")).toBeInTheDocument();
    expect(sectionQueries("Pension holdings").getByText("Verification State: reviewed")).toBeInTheDocument();
    expect(sectionQueries("Capital assets").getByText("Verification State: verified")).toBeInTheDocument();
    expect(screen.queryByText(/legally verified|legal conclusion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/tax verified|tax conclusion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/regulatory compliance|compliance approved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/readiness approved|recommendation approved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/suitability approved|professional correctness/i)).not.toBeInTheDocument();

    const pension = sectionQueries("Pension holdings");
    fireEvent.change(pension.getByLabelText("Provider Name"), { target: { value: "Metadata Untouched" } });
    fireEvent.click(pension.getByRole("button", { name: "Add Pension Holding" }));
    await waitFor(() => {
      expect(callsFor(fetchMock, "pension-holdings", "POST")).toHaveLength(1);
    });
    const untouchedMetadataBody = requestBody(callsFor(fetchMock, "pension-holdings", "POST")[0]);
    expect(untouchedMetadataBody).not.toHaveProperty("source_status");
    expect(untouchedMetadataBody).not.toHaveProperty("verification_state");

    const capital = sectionQueries("Capital assets");
    fireEvent.change(capital.getByLabelText("Asset Category"), { target: { value: "bank deposit" } });
    fireEvent.change(capital.getByLabelText("Asset Description"), { target: { value: "Metadata selected" } });
    fireEvent.change(capital.getByLabelText("Source Status"), { target: { value: "external statement" } });
    fireEvent.change(capital.getByLabelText("Verification State"), { target: { value: "verified" } });
    fireEvent.click(capital.getByRole("button", { name: "Add Capital Asset" }));
    await waitFor(() => {
      expect(callsFor(fetchMock, "capital-assets", "POST")).toHaveLength(1);
    });
    const selectedMetadataBody = requestBody(callsFor(fetchMock, "capital-assets", "POST")[0]);
    expect(selectedMetadataBody).toMatchObject({
      source_status: "external statement",
      verification_state: "verified"
    });

    fireEvent.click(sectionQueries("Recurring incomes").getByRole("button", { name: "Edit Recurring Income" }));
    fireEvent.change(sectionQueries("Recurring incomes").getByLabelText("Source Status"), {
      target: { value: "planner entered" }
    });
    fireEvent.change(sectionQueries("Recurring incomes").getByLabelText("Verification State"), {
      target: { value: "reviewed" }
    });
    fireEvent.click(sectionQueries("Recurring incomes").getByRole("button", { name: "Save Recurring Income" }));
    await waitFor(() => {
      expect(callsFor(fetchMock, "recurring-incomes", "PUT")).toHaveLength(1);
    });
    expect(requestBody(callsFor(fetchMock, "recurring-incomes", "PUT")[0])).toEqual({
      source_status: "planner entered",
      verification_state: "reviewed"
    });
  });

  it("proves Package C does not issue prohibited API requests", async () => {
    const fetchMock = makeFetchMockWithRows();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    expect(await screen.findByText("Provider Name: Existing Pension Provider")).toBeInTheDocument();

    for (const config of resourceConfigs) {
      fireEvent.click(sectionQueries(config.heading).getByRole("button", { name: config.editButton }));
      fireEvent.click(sectionQueries(config.heading).getByRole("button", { name: "Cancel Edit" }));
    }

    expectNoGetOneRequests(fetchMock);
    expectNoProhibitedPackageCRequests(fetchMock);
  });
});
