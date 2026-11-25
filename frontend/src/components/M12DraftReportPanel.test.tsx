import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { M12DraftReportPanel } from "./M12DraftReportPanel";

const load = vi.fn();
vi.mock("../api/m12DraftReportApi", () => ({
  loadM12Draft: (...args: unknown[]) => load(...args),
  downloadM12DraftPdf: vi.fn(),
}));

afterEach(() => vi.clearAllMocks());

it("renders professional M12 values in Hebrew without changing their canonical API values", async () => {
  load.mockResolvedValue({
    document_kind: "M12_FIRST_STAGE_DRAFT", draft: true,
    generated_at: "2026-11-25T10:00:00Z",
    client: { name: "לקוח סינתטי", birth_date: "1960-01-02",
      employment_status: "not_currently_working", planned_retirement_date: "2027-03-04",
      planned_retirement_age: 67 },
    pension_products: [{ name: "קרן בדיקה", type: "pension_fund", provider: null,
      reported_total: "12345678901234567890.50", statement_date: "2026-10-01",
      verification: "unverified" }],
    capital_assets: [{ name: "נכס בדיקה", category: "real estate", value: "1000.00",
      value_date: "2026-09-01", verification: "collected - not yet reviewed" }],
    incomes: [{ name: "הכנסה", amount: "5000.00", frequency: "monthly",
      amount_basis: "gross", verification: "verified" }], expenses: [],
    scenarios: [{ name: "חלופה א", version: 2, status: "needs_revalidation", preferred: true,
      decisions: [{ component: "רכיב מקור", action: "pension", declared_amount: "100.00",
        effective_date: "2027-03-04", validation_state: "unverified", qualified_calculation: false }] }],
    preferred: null, assumptions: [],
    missing_information: [{ label: "מסמך חסר", status: "open" }], warnings: [],
    cashflow_results: null, calculation_traceability: "not_established",
  });

  render(<M12DraftReportPanel clientId={7} />);
  fireEvent.click(screen.getByRole("button", { name: "הפק טיוטת תכנון פרישה" }));

  expect(await screen.findByText(/אינו עובד כעת/)).toBeInTheDocument();
  expect(screen.getByText("קרן פנסיה")).toBeInTheDocument();
  expect(screen.getByText("טרם אומת")).toBeInTheDocument();
  expect(screen.getByText("מקרקעין")).toBeInTheDocument();
  expect(screen.getByText("חודשי")).toBeInTheDocument();
  expect(screen.getByText(/סטטוס חלופה: נדרשת בדיקה מחדש/)).toBeInTheDocument();
  expect(screen.getByText("קצבה")).toBeInTheDocument();
  expect(screen.getByText(/מסמך חסר \(פתוח\)/)).toBeInTheDocument();
  expect(screen.getByText("12,345,678,901,234,567,890.5 ₪")).toBeInTheDocument();
  expect(screen.queryByText(/not_currently_working|pension_fund|needs_revalidation|unverified/)).toBeNull();
});
