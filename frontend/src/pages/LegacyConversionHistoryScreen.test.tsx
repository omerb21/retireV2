import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { LegacyConversionHistoryScreen } from "./LegacyConversionHistoryScreen";
vi.mock("../api/legacyConversionHistoryApi", () => ({ listLegacyConversions: async () => [{ subject_id: "s" }], legacyConversionHistory: async () => [{ revision_id: "r", created_at: "2026-09-12T10:00:00Z", input_amount: "100.00", coefficient: { coefficient: "200" }, manifest: { display_result: "0.50" } }] }));
it("shows historical values and no professional actions", async () => {
  render(<MemoryRouter initialEntries={["/clients/1/legacy-conversion-history"]}><Routes><Route path="/clients/:clientId/legacy-conversion-history" element={<LegacyConversionHistoryScreen />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("100.00")).toBeVisible();
  expect(screen.getByRole("heading")).toHaveTextContent("לקריאה בלבד");
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByRole("link")).toHaveAttribute("href", "/clients/1/pension-products");
});
