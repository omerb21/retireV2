import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { AppRoutes } from "./AppRoutes";
vi.mock("../api/legacyConversionHistoryApi", () => ({ listLegacyConversions: async () => [], legacyConversionHistory: async () => [] }));
it("registers the explicit read-only archive route, not a professional conversion screen", async () => {
  render(<MemoryRouter initialEntries={["/clients/1/legacy-conversion-history"]}><AppRoutes /></MemoryRouter>);
  expect(await screen.findByText("אין המרות היסטוריות")).toBeVisible();
  expect(screen.getByRole("heading")).toHaveTextContent("היסטוריית המרות ישנה — לקריאה בלבד");
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByRole("link")).toHaveAttribute("href", "/clients/1/pension-products");
});
