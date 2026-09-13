import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RetirementPlanningConsolidatedReviewSection } from "./RetirementPlanningConsolidatedReviewSection";

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

function requestMethod(call: unknown[]): string {
  return ((call[1] as RequestInit | undefined)?.method ?? "GET").toUpperCase();
}

function requestUrl(call: unknown[]): string {
  return String(call[0]);
}

const approvedUrls = [
  "/api/clients/7/professional-source-snapshot",
  "/api/clients/7/recurring-incomes?lifecycle_status=current",
  "/api/clients/7/recurring-expenses?lifecycle_status=current",
  "/api/clients/7/retirement-timing-work-intentions?lifecycle_status=current",
  "/api/clients/7/planner-assumptions?lifecycle_status=current",
  "/api/clients/7/missing-items"
];

const groupHeadings = [
  "יתרות מקור שטרם הומרו",
  "מקורות הון נוכחיים",
  "הכנסות שוטפות",
  "הוצאות שוטפות",
  "עיתוי פרישה וכוונות עבודה",
  "הנחות מתכנן",
  "מידע חסר לייעוץ"
];

function rowsForUrl(url: string): unknown {
  switch (url) {
    case "/api/clients/7/professional-source-snapshot":
      return { ...emptySnapshot, pension_products: [{
        product_id: "p", product_name: "Pension Product", provider_name: "Existing Pension Provider",
        statement_date: "2026-01-01", account_reference: "A", components: [],
        reported_controls: { reported_product_total: "1000.00" }
      }], capital_sources: [{ source_id: "capital:2", asset_description: "Emergency reserve",
        known_value_amount: "2000.00", origin_kind: "manual", missing_or_blocking_facts: [] }] };
    case "/api/clients/7/recurring-incomes?lifecycle_status=current":
      return [{
        id: 3,
        client_id: 7,
        income_category: "salary",
        description: "Current salary",
        amount: "3000.00",
        amount_basis: "gross",
        frequency: "monthly",
        continuation_status: "ongoing",
        lifecycle_status: "current",
        source_status: "planner entered",
        verification_state: "unreviewed",
        start_date: null,
        end_date: null,
        source_type: null,
        source_date: null,
        source_note: null,
        created_at: "2026-01-03T00:00:00Z",
        updated_at: "2026-01-03T00:00:00Z"
      }];
    case "/api/clients/7/recurring-expenses?lifecycle_status=current":
      return [{
        id: 4,
        client_id: 7,
        expense_category: "housing",
        description: "Rent",
        amount: "1500.00",
        frequency: "monthly",
        expense_type: "mandatory",
        continuation_status: "ongoing",
        lifecycle_status: "current",
        source_status: "planner entered",
        verification_state: "unreviewed",
        start_date: null,
        end_date: null,
        source_type: null,
        source_date: null,
        source_note: null,
        created_at: "2026-01-04T00:00:00Z",
        updated_at: "2026-01-04T00:00:00Z"
      }];
    case "/api/clients/7/retirement-timing-work-intentions?lifecycle_status=current":
      return [{
        id: 5,
        client_id: 7,
        timing_confidence: "known",
        work_after_retirement_intention: "undecided",
        lifecycle_status: "current",
        source_status: "planner entered",
        verification_state: "unreviewed",
        planned_work_end_date: "2030-01-01",
        intended_pension_start_date: null,
        other_known_retirement_date: null,
        other_known_retirement_date_label: null,
        anticipated_work_end_date: null,
        work_intention_note: "Client is considering options",
        source_type: null,
        source_date: null,
        source_note: null,
        created_at: "2026-01-05T00:00:00Z",
        updated_at: "2026-01-05T00:00:00Z"
      }];
    case "/api/clients/7/planner-assumptions?lifecycle_status=current":
      return [{
        id: 6,
        client_id: 7,
        assumption_category: "income",
        title: "Salary assumption",
        assumption_value_text: "Salary continues",
        rationale: "Planner entered planning assumption",
        owner: "planner",
        lifecycle_status: "current",
        effective_start_date: "2026-01-01",
        effective_end_date: null,
        review_date: null,
        created_at: "2026-01-06T00:00:00Z",
        updated_at: "2026-01-06T00:00:00Z"
      }];
    case "/api/clients/7/missing-items":
      return [{
        missing_data_item_id: "MD-LEGACY",
        client_id: 7,
        missing_item_type: "data",
        missing_item_label: "Legacy row",
        missing_status: "missing",
        notes: "Hidden legacy note",
        planning_domain: null,
        related_record_type: "pension_holding",
        related_record_id: 1,
        advisory_status: null,
        neutral_reason: null,
        created_at: "2026-01-07T00:00:00Z"
      }];
    default:
      throw new Error(`Unexpected URL ${url}`);
  }
}

const emptySnapshot = { contract_version: "canonical-professional-source-snapshot-v1", client_id: 7, pension_products: [],
  pension_sources: [], capital_sources: [], client_fact_warnings: [], source_warnings: [], source_state_fingerprint: "test" };

function makeFetchMock() {
  return vi.fn((url: string) => Promise.resolve(jsonResponse(rowsForUrl(url))));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RetirementPlanningConsolidatedReviewSection", () => {
  it("renders one canonical snapshot and unrelated general facts with current lifecycle requests", async () => {
    const fetchMock = makeFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningConsolidatedReviewSection clientId={7} />);

    expect(await screen.findByText("Pension Product")).toBeVisible();
    for (const heading of groupHeadings) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }

    expect(await screen.findByText(/גוף מנהל: Existing Pension Provider/)).toBeInTheDocument();
    expect(await screen.findByText("Salary assumption")).toBeInTheDocument();
    expect(await screen.findByText(/לא תועד סיווג לתחום תכנון/)).toBeInTheDocument();
    expect(screen.getByText(/לא תועד מצב ייעוץ/)).toBeInTheDocument();
    expect(screen.getByText(/לא תועדה סיבה ניטרלית/)).toBeInTheDocument();
    expect(screen.getByText(/תאריך דוח: 01\/01\/2026/)).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(fetchMock.mock.calls.map(requestUrl)).toEqual(approvedUrls);
    expect(fetchMock.mock.calls.every((call) => requestMethod(call) === "GET")).toBe(true);
    expect(requestUrl(fetchMock.mock.calls[5])).toBe("/api/clients/7/missing-items");
    expect(requestUrl(fetchMock.mock.calls[5])).not.toContain("lifecycle_status");
    expect(requestUrl(fetchMock.mock.calls[5])).not.toContain("advisory_status");
    expect(requestUrl(fetchMock.mock.calls[5])).not.toContain("status=");

    expect(screen.queryByText("related_record_type")).not.toBeInTheDocument();
    expect(screen.queryByText("related_record_id")).not.toBeInTheDocument();
    expect(screen.queryByText("pension_holding")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden legacy note")).not.toBeInTheDocument();

    expect(screen.queryByRole("form")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(screen.getByRole("button", {name: "רענון תמונת המקורות"})).toBeVisible();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText(/create|edit|save|delete|supersede/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/lifecycle/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/\b(summary|count|complete|warning|priority|ready|recommend|workflow|action)\b/i)
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Fixation|evidence|source|verification/i)).not.toBeInTheDocument();
  });

  it("renders per-group empty states", async () => {
    const fetchMock = vi.fn((url: string) => Promise.resolve(jsonResponse(url.endsWith("professional-source-snapshot") ? emptySnapshot : [])));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningConsolidatedReviewSection clientId={7} />);

    expect(await screen.findByText("לא תועדו מוצרים פנסיוניים.")).toBeInTheDocument();
    expect(screen.getByText("לא תועדו נכסי הון נוכחיים.")).toBeInTheDocument();
    expect(screen.getByText("לא תועדו הכנסות שוטפות.")).toBeInTheDocument();
    expect(screen.getByText("לא תועדו הוצאות שוטפות.")).toBeInTheDocument();
    expect(screen.getByText("לא תועדו נתוני עיתוי פרישה וכוונות עבודה.")).toBeInTheDocument();
    expect(screen.getByText("לא תועדו הנחות מתכנן.")).toBeInTheDocument();
    expect(screen.getByText("לא תועד מידע חסר לייעוץ.")).toBeInTheDocument();
  });

  it("renders visible API error states", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: { code: "LOAD_FAILED" } }, 500, "Error"));
    vi.stubGlobal("fetch", fetchMock);

    render(<RetirementPlanningConsolidatedReviewSection clientId={7} />);

    expect(await screen.findByText("לא ניתן לטעון את תמונת המקורות. יש לנסות שוב.")).toBeInTheDocument();
    expect(screen.getAllByText(/LOAD_FAILED/)).toHaveLength(5);

  });
});
