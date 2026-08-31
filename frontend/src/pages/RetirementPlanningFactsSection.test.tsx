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
    heading: "אחזקות פנסיוניות",
    addButton: "הוספת אחזקה פנסיונית",
    editButton: "עריכת אחזקה פנסיונית",
    saveButton: "שמירת אחזקה פנסיונית",
    rowId: 11,
    rowText: "שם הגוף המנהל: Existing Pension Provider",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("שם הגוף המנהל"), { target: { value: "Migdal" } });
      fireEvent.change(section.getByLabelText("סוג מוצר"), { target: { value: "pension fund" } });
      fireEvent.change(section.getByLabelText("יתרה ידועה"), { target: { value: "123.45" } });
      fireEvent.change(section.getByLabelText("תאריך נכונות היתרה"), { target: { value: "01/02/2026" } });
    },
    createPayload: {
      provider_name: "Migdal",
      product_type: "pension fund",
      known_balance_amount: "123.45",
      balance_as_of_date: "2026-02-01"
    },
    firstEditLabel: "שם הגוף המנהל",
    firstEditValue: "Existing Pension Provider",
    changedEditLabel: "שם הגוף המנהל",
    changedEditValue: "Updated Provider",
    blankEditLabel: "שם מוצר",
    updatePayload: {
      provider_name: "Updated Provider",
      product_name: null
    },
    amountField: "known_balance_amount"
  },
  {
    resourceName: "capital-assets",
    heading: "נכסי הון",
    addButton: "הוספת נכס הון",
    editButton: "עריכת נכס הון",
    saveButton: "שמירת נכס הון",
    rowId: 21,
    rowText: "תיאור הנכס: Existing deposit",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("קטגוריית נכס"), { target: { value: "bank deposit" } });
      fireEvent.change(section.getByLabelText("תיאור הנכס"), { target: { value: "Savings account" } });
      fireEvent.change(section.getByLabelText("שווי ידוע"), { target: { value: "456.78" } });
      fireEvent.change(section.getByLabelText("תאריך נכונות השווי"), { target: { value: "02/02/2026" } });
    },
    createPayload: {
      asset_category: "bank deposit",
      asset_description: "Savings account",
      known_value_amount: "456.78",
      value_as_of_date: "2026-02-02"
    },
    firstEditLabel: "תיאור הנכס",
    firstEditValue: "Existing deposit",
    changedEditLabel: "תיאור הנכס",
    changedEditValue: "Updated deposit",
    blankEditLabel: "הערת נזילות",
    updatePayload: {
      asset_description: "Updated deposit",
      liquidity_note: null
    },
    amountField: "known_value_amount"
  },
  {
    resourceName: "recurring-incomes",
    heading: "הכנסות שוטפות",
    addButton: "הוספת הכנסה שוטפת",
    editButton: "עריכת הכנסה שוטפת",
    saveButton: "שמירת הכנסה שוטפת",
    rowId: 31,
    rowText: "תיאור: Existing income",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("קטגוריית הכנסה"), { target: { value: "employment" } });
      fireEvent.change(section.getByLabelText("תיאור"), { target: { value: "Salary" } });
      fireEvent.change(section.getByLabelText("סכום"), { target: { value: "1000.00" } });
      fireEvent.change(section.getByLabelText("בסיס הסכום"), { target: { value: "gross" } });
      fireEvent.change(section.getByLabelText("תדירות"), { target: { value: "monthly" } });
      fireEvent.change(section.getByLabelText("מצב המשכיות"), { target: { value: "ongoing" } });
    },
    createPayload: {
      income_category: "employment",
      description: "Salary",
      amount: "1000.00",
      amount_basis: "gross",
      frequency: "monthly",
      continuation_status: "ongoing"
    },
    firstEditLabel: "תיאור",
    firstEditValue: "Existing income",
    changedEditLabel: "תיאור",
    changedEditValue: "Updated income",
    blankEditLabel: "תאריך התחלה",
    updatePayload: {
      description: "Updated income",
      start_date: null
    },
    amountField: "amount"
  },
  {
    resourceName: "recurring-expenses",
    heading: "הוצאות שוטפות",
    addButton: "הוספת הוצאה שוטפת",
    editButton: "עריכת הוצאה שוטפת",
    saveButton: "שמירת הוצאה שוטפת",
    rowId: 41,
    rowText: "תיאור: Existing expense",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("קטגוריית הוצאה"), { target: { value: "housing" } });
      fireEvent.change(section.getByLabelText("תיאור"), { target: { value: "Rent" } });
      fireEvent.change(section.getByLabelText("סכום"), { target: { value: "200.00" } });
      fireEvent.change(section.getByLabelText("תדירות"), { target: { value: "monthly" } });
      fireEvent.change(section.getByLabelText("סוג הוצאה"), { target: { value: "mandatory" } });
      fireEvent.change(section.getByLabelText("מצב המשכיות"), { target: { value: "ongoing" } });
    },
    createPayload: {
      expense_category: "housing",
      description: "Rent",
      amount: "200.00",
      frequency: "monthly",
      expense_type: "mandatory",
      continuation_status: "ongoing"
    },
    firstEditLabel: "תיאור",
    firstEditValue: "Existing expense",
    changedEditLabel: "תיאור",
    changedEditValue: "Updated expense",
    blankEditLabel: "תאריך התחלה",
    updatePayload: {
      description: "Updated expense",
      start_date: null
    },
    amountField: "amount"
  },
  {
    resourceName: "retirement-timing-work-intentions",
    heading: "עיתוי פרישה וכוונות עבודה",
    addButton: "הוספת עיתוי פרישה וכוונת עבודה",
    editButton: "עריכת עיתוי פרישה וכוונת עבודה",
    saveButton: "שמירת עיתוי פרישה וכוונת עבודה",
    rowId: 51,
    rowText: "כוונת עבודה לאחר הפרישה: טרם הוחלט",
    fillCreate: (section) => {
      fireEvent.change(section.getByLabelText("ודאות העיתוי"), { target: { value: "known" } });
      fireEvent.change(section.getByLabelText("כוונת עבודה לאחר הפרישה"), {
        target: { value: "continue working" }
      });
      fireEvent.change(section.getByLabelText("תאריך פרישה ידוע נוסף"), { target: { value: "01/01/2030" } });
      fireEvent.change(section.getByLabelText("תיאור תאריך הפרישה הידוע הנוסף"), {
        target: { value: "Client target" }
      });
    },
    createPayload: {
      timing_confidence: "known",
      work_after_retirement_intention: "continue working",
      other_known_retirement_date: "2030-01-01",
      other_known_retirement_date_label: "Client target"
    },
    firstEditLabel: "כוונת עבודה לאחר הפרישה",
    firstEditValue: "undecided",
    changedEditLabel: "הערת כוונת עבודה",
    changedEditValue: "Updated timing note",
    blankEditLabel: "תאריך מתוכנן לסיום העבודה",
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

    expect(await screen.findByRole("heading", { name: "עובדות תכנון פרישה" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clients/7/pension-holdings?lifecycle_status=current",
        expect.objectContaining({ method: "GET" })
      );
    });

    const retirementPlanningFactsRegion = screen.getByRole("region", { name: "עובדות תכנון פרישה" });
    for (const config of resourceConfigs) {
      expect(within(retirementPlanningFactsRegion).getByRole("heading", { name: config.heading })).toBeInTheDocument();
    }
    expect(within(retirementPlanningFactsRegion).getAllByLabelText("סינון לפי מצב מחזור חיים")).toHaveLength(resourceConfigs.length);
    expect(screen.getByRole("heading", { name: "רשומות ניתוח פנסיוני", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "הנחות מתכנן", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "מידע חסר לייעוץ", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "סקירה מאוחדת לתכנון פרישה", level: 3 })).toBeInTheDocument();
    expect(document.querySelector('input[type="date"]')).not.toBeInTheDocument();
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

    expect(screen.getByText("טוען אחזקות פנסיוניות…")).toBeInTheDocument();
    expect(screen.getByText("טוען נכסי הון…")).toBeInTheDocument();
    expect(screen.getByText("טוען הכנסות שוטפות…")).toBeInTheDocument();
    expect(screen.getByText("טוען הוצאות שוטפות…")).toBeInTheDocument();
    expect(screen.getByText("טוען נתוני עיתוי פרישה וכוונות עבודה…")).toBeInTheDocument();

    for (const resolveRequest of pendingRequests) {
      resolveRequest();
    }

    expect(await screen.findByText("לא נמצאו אחזקות פנסיוניות עבור מסנן מחזור החיים שנבחר.")).toBeInTheDocument();
    expect(await screen.findByText("לא נמצאו נכסי הון עבור מסנן מחזור החיים שנבחר.")).toBeInTheDocument();
    expect(await screen.findByText("לא נמצאו הכנסות שוטפות עבור מסנן מחזור החיים שנבחר.")).toBeInTheDocument();
    expect(await screen.findByText("לא נמצאו הוצאות שוטפות עבור מסנן מחזור החיים שנבחר.")).toBeInTheDocument();
    expect(
      await screen.findByText("לא נמצאו נתוני עיתוי פרישה וכוונות עבודה עבור מסנן מחזור החיים שנבחר.")
    ).toBeInTheDocument();
  });

  it("proves default current loading and local lifecycle filtering for all five resources", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    await screen.findByText("לא נמצאו אחזקות פנסיוניות עבור מסנן מחזור החיים שנבחר.");

    for (const config of resourceConfigs) {
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/clients/7/${config.resourceName}?lifecycle_status=current`,
        expect.objectContaining({ method: "GET" })
      );
      const lifecycleSelect = sectionQueries(config.heading).getByLabelText("סינון לפי מצב מחזור חיים") as HTMLSelectElement;
      expect(Array.from(lifecycleSelect.options).map((option) => option.value)).toEqual([
        "current",
        "superseded",
        "all"
      ]);
    }

    const callsAfterInitialLoad = fetchMock.mock.calls.length;
    fireEvent.change(sectionQueries("אחזקות פנסיוניות").getByLabelText("סינון לפי מצב מחזור חיים"), {
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
    fireEvent.change(sectionQueries("נכסי הון").getByLabelText("סינון לפי מצב מחזור חיים"), {
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
    fireEvent.click(section.getByRole("button", { name: "ביטול העריכה" }));
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
    await screen.findByText("לא נמצאו אחזקות פנסיוניות עבור מסנן מחזור החיים שנבחר.");
    fireEvent.click(sectionQueries("אחזקות פנסיוניות").getByRole("button", { name: "הוספת אחזקה פנסיונית" }));

    expect(await screen.findByText("לא ניתן לשמור את הרשומה.")).toBeInTheDocument();
    expect(await screen.findByText(/provider_name is required/)).toBeInTheDocument();
  });

  it("proves approved conditional fields appear only after paired values are populated", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    await screen.findByText("לא נמצאו אחזקות פנסיוניות עבור מסנן מחזור החיים שנבחר.");

    const pension = sectionQueries("אחזקות פנסיוניות");
    expect(pension.queryByLabelText("תאריך נכונות היתרה")).not.toBeInTheDocument();
    expect(pension.queryByLabelText("תאריך נכונות הקצבה")).not.toBeInTheDocument();
    fireEvent.change(pension.getByLabelText("יתרה ידועה"), { target: { value: "123.45" } });
    fireEvent.change(pension.getByLabelText("קצבה חודשית ידועה"), { target: { value: "67.89" } });
    expect(pension.getByLabelText("תאריך נכונות היתרה")).toBeInTheDocument();
    expect(pension.getByLabelText("תאריך נכונות הקצבה")).toBeInTheDocument();

    const capital = sectionQueries("נכסי הון");
    expect(capital.queryByLabelText("תאריך נכונות השווי")).not.toBeInTheDocument();
    fireEvent.change(capital.getByLabelText("שווי ידוע"), { target: { value: "456.78" } });
    expect(capital.getByLabelText("תאריך נכונות השווי")).toBeInTheDocument();

    const timing = sectionQueries("עיתוי פרישה וכוונות עבודה");
    expect(timing.queryByLabelText("תיאור תאריך הפרישה הידוע הנוסף")).not.toBeInTheDocument();
    fireEvent.change(timing.getByLabelText("תאריך פרישה ידוע נוסף"), { target: { value: "01/01/2030" } });
    expect(timing.getByLabelText("תיאור תאריך הפרישה הידוע הנוסף")).toBeInTheDocument();
  });

  it("proves source and verification metadata are included only when explicitly changed and use neutral wording", async () => {
    const fetchMock = makeFetchMockWithRows();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningFactsSection clientId={7} />);
    expect(await screen.findByText("שם הגוף המנהל: Existing Pension Provider")).toBeInTheDocument();
    expect(sectionQueries("אחזקות פנסיוניות").getByText("מצב אימות: נבדק")).toBeInTheDocument();
    expect(sectionQueries("נכסי הון").getByText("מצב אימות: אומת")).toBeInTheDocument();
    expect(screen.queryByText(/legally verified|legal conclusion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/tax verified|tax conclusion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/regulatory compliance|compliance approved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/readiness approved|recommendation approved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/suitability approved|professional correctness/i)).not.toBeInTheDocument();

    const pension = sectionQueries("אחזקות פנסיוניות");
    fireEvent.change(pension.getByLabelText("שם הגוף המנהל"), { target: { value: "Metadata Untouched" } });
    fireEvent.click(pension.getByRole("button", { name: "הוספת אחזקה פנסיונית" }));
    await waitFor(() => {
      expect(callsFor(fetchMock, "pension-holdings", "POST")).toHaveLength(1);
    });
    const untouchedMetadataBody = requestBody(callsFor(fetchMock, "pension-holdings", "POST")[0]);
    expect(untouchedMetadataBody).not.toHaveProperty("source_status");
    expect(untouchedMetadataBody).not.toHaveProperty("verification_state");

    const capital = sectionQueries("נכסי הון");
    fireEvent.change(capital.getByLabelText("קטגוריית נכס"), { target: { value: "bank deposit" } });
    fireEvent.change(capital.getByLabelText("תיאור הנכס"), { target: { value: "Metadata selected" } });
    fireEvent.change(capital.getByLabelText("מצב מקור"), { target: { value: "external statement" } });
    fireEvent.change(capital.getByLabelText("מצב אימות"), { target: { value: "verified" } });
    fireEvent.click(capital.getByRole("button", { name: "הוספת נכס הון" }));
    await waitFor(() => {
      expect(callsFor(fetchMock, "capital-assets", "POST")).toHaveLength(1);
    });
    const selectedMetadataBody = requestBody(callsFor(fetchMock, "capital-assets", "POST")[0]);
    expect(selectedMetadataBody).toMatchObject({
      source_status: "external statement",
      verification_state: "verified"
    });

    fireEvent.click(sectionQueries("הכנסות שוטפות").getByRole("button", { name: "עריכת הכנסה שוטפת" }));
    fireEvent.change(sectionQueries("הכנסות שוטפות").getByLabelText("מצב מקור"), {
      target: { value: "planner entered" }
    });
    fireEvent.change(sectionQueries("הכנסות שוטפות").getByLabelText("מצב אימות"), {
      target: { value: "reviewed" }
    });
    fireEvent.click(sectionQueries("הכנסות שוטפות").getByRole("button", { name: "שמירת הכנסה שוטפת" }));
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
    expect(await screen.findByText("שם הגוף המנהל: Existing Pension Provider")).toBeInTheDocument();

    for (const config of resourceConfigs) {
      fireEvent.click(sectionQueries(config.heading).getByRole("button", { name: config.editButton }));
      fireEvent.click(sectionQueries(config.heading).getByRole("button", { name: "ביטול העריכה" }));
    }

    expectNoGetOneRequests(fetchMock);
    expectNoProhibitedPackageCRequests(fetchMock);
  });
});
