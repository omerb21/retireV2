import { render, screen } from "@testing-library/react";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";


const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    headers: {
      get: () => "application/json"
    },
    json: async () => [
      {
        client_id: 1,
        full_name: "Jane Doe",
        id_number: "001234567",
        birth_date: "1970-01-01",
        file_status: "file_created",
        professional_identification_status: "professionally_identified"
      }
    ]
  });
  vi.stubGlobal("fetch", fetchMock);
});


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("App", () => {
  it("keeps the same client-scoped workspace navigation on a specialist route", async () => {
    render(<MemoryRouter initialEntries={["/clients/1/pension-products"]}><App /></MemoryRouter>);
    const nav = await screen.findByRole("navigation", { name: "שלבי תיק הלקוח" });
    expect(nav).toBeInTheDocument();
    expect(nav.querySelectorAll("a")).toHaveLength(5);
    expect(nav.querySelector('a[href="/clients/1/workspace?step=portfolio"]')).not.toBeNull();
    expect(screen.getByText(/כלי מקצועי משני בתיק הלקוח הפעיל/)).toBeInTheDocument();
    expect(screen.getByText(/מזהה תיק 1/)).toBeInTheDocument();
  });

  it("renders frontend shell heading and client list screen", async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    expect(screen.getByText("מערכת תכנון פרישה")).toBeInTheDocument();
    expect(screen.getByText("מערכת תכנון פרישה").closest("div")).toHaveAttribute("dir", "rtl");
    expect(await screen.findByRole("heading", { name: "רשימת לקוחות" })).toBeInTheDocument();
    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
  });
});
