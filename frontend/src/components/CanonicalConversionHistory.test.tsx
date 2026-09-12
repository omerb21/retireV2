import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalConversionHistory } from "./CanonicalConversionHistory";
import * as api from "../api/canonicalConversionsApi";
vi.mock("../api/canonicalConversionsApi", async original => ({ ...await original<typeof api>(), listConversions: vi.fn(), reverseConversion: vi.fn() }));
const item: api.ConversionHistoryItem = { conversion_id: "c", source_product_id: "p", destination_type: "capital", tax_treatment: "exempt", converted_amount: "100.01", status: "active", version: 1, effective_date: "2026-09-12", actor: "test", pension: null, allocations: [] };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(api.listConversions).mockResolvedValue([item, { ...item, conversion_id: "old", status: "reversed", converted_amount: "999.00" }]); });
it("excludes reversed destinations from current read-only display", async () => {
  render(<CanonicalConversionHistory clientId={1} currentOnly />);
  expect(await screen.findByText("100.01")).toBeVisible();
  expect(screen.queryByText("999.00")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});
it("preserves history and reverses full conversion with current versions and reason", async () => {
  const done = vi.fn(async () => {});
  render(<CanonicalConversionHistory clientId={1} productId="p" version={3} onChanged={done} />);
  fireEvent.click(await screen.findByRole("button", { name: "ביטול המרה" }));
  fireEvent.change(screen.getByLabelText("סיבת ביטול"), { target: { value: "תיקון" } });
  fireEvent.click(screen.getByRole("button", { name: "אישור ביטול המרה" }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(api.reverseConversion).toHaveBeenCalledWith(1, "c", expect.objectContaining({ expected_product_version: 3, expected_conversion_version: 1, reason: "תיקון" }));
});
