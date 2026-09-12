import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalComponentConversionDialog } from "./CanonicalComponentConversionDialog";
import * as api from "../api/canonicalConversionsApi";
vi.mock("../api/canonicalConversionsApi", async original => ({ ...await original<typeof api>(), previewConversion: vi.fn(), executeConversion: vi.fn() }));
const component = { component_id: "c", component_code: "תגמולי_עובד_אחרי_2000", balance: "100.00", allowed_destinations: { pension: "taxable" } };
const preview: api.ConversionPreview = { groups: [{ amount: "40.00", tax_treatment: "taxable", allocations: [{ component_id: "c", component_code: component.component_code, amount: "40.00", before: "100.00", after: "60.00" }], coefficient: { annuity_factor: "200.00", source: "default", fallback_used: true, notes: "", catalog_version: "v1", warnings: ["ANNUITY_COEFFICIENT_DEFAULT_200"] }, monthly_display_amount: "0.20" }], skipped: [] };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(api.previewConversion).mockResolvedValue(preview); vi.mocked(api.executeConversion).mockResolvedValue({ product_version: 3 }); });
function dates() {
  fireEvent.change(screen.getByLabelText("תאריך המרה"), { target: { value: "12/09/2026" } });
  fireEvent.change(screen.getByLabelText("תאריך תחילת קצבה"), { target: { value: "01/01/2030" } });
}
it("uses only server destinations, previews exact partial amount and warning, then executes same request and refreshes", async () => {
  const done = vi.fn(async () => {});
  render(<CanonicalComponentConversionDialog clientId={1} productId="p" version={2} component={component} onDone={done} onClose={vi.fn()} />);
  expect(screen.queryByRole("option", { name: "הון" })).toBeNull();
  fireEvent.click(screen.getByLabelText("כל היתרה"));
  fireEvent.change(screen.getByLabelText("סכום חלקי"), { target: { value: "40.00" } });
  dates(); fireEvent.click(screen.getByText("תצוגה מקדימה"));
  expect(await screen.findByRole("status")).toHaveTextContent("200");
  expect(screen.getByText(/חייב במס/)).toBeVisible();
  const req = vi.mocked(api.previewConversion).mock.calls[0][1];
  expect(req.selections).toEqual([{ component_id: "c", component_code: component.component_code, amount: "40.00" }]);
  expect(req.effective_date).toBe("2026-09-12");
  expect(req).not.toHaveProperty("tax_treatment");
  fireEvent.click(screen.getByText("אישור המרה"));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(api.executeConversion).toHaveBeenCalledWith(1, req);
});
it("whole product sends no totals, displays skipped components, and invalidates preview when destination changes", async () => {
  vi.mocked(api.previewConversion).mockResolvedValue({ ...preview, skipped: [{ component_code: "פיצויים_מעסיק_נוכחי", reason: "INVALID_COMPONENT_DESTINATION" }] });
  render(<CanonicalComponentConversionDialog clientId={1} productId="p" version={2} onDone={vi.fn()} onClose={vi.fn()} />);
  expect(screen.queryByLabelText("סכום חלקי")).toBeNull(); dates();
  fireEvent.click(screen.getByText("תצוגה מקדימה"));
  expect(await screen.findByText(/פיצויים מעסיק נוכחי — היעד אינו מותר/)).toBeVisible();
  expect(vi.mocked(api.previewConversion).mock.calls[0][1]).toMatchObject({ whole_product: true, selections: [] });
  fireEvent.change(screen.getByLabelText("יעד"), { target: { value: "capital" } });
  expect(screen.queryByText("אישור המרה")).toBeNull();
});
