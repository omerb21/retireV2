import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { M06ConversionScreen } from "./M06ConversionScreen";

const json = (body: unknown) => ({ ok: true, headers: { get: () => "application/json" }, json: async () => body }) as unknown as Response;
const subject = (id: string) => ({ subject_id: id, mode: "balance_to_monthly_pension" });
const revision = (id = "archive-1") => ({
  revision_id: id, revision_sequence: 1, state: "resolved", created_at: "2026-01-31T10:00:00Z",
  input_date: "2020-01-02", input_amount: "999999999999.99",
  coefficient: { coefficient: "200.000" }, manifest: { display_result: "4999999999.99", fingerprint: "preserved-fingerprint" },
});
function Navigation() {
  const go = useNavigate();
  return <><button onClick={() => go("/clients/2/pension-conversion")}>לקוח ב</button>
    <button onClick={() => go("/clients/1/pension-conversion")}>חזרה לא</button></>;
}
function page() {
  render(<MemoryRouter initialEntries={["/clients/1/pension-conversion"]}><Navigation /><Routes>
    <Route path="/clients/:clientId/pension-conversion" element={<M06ConversionScreen />} />
  </Routes></MemoryRouter>);
}
afterEach(() => vi.unstubAllGlobals());

describe("M06 canonical cutover historical surface", () => {
  it("offers no conversion or legacy source actions", async () => {
    const fetch = vi.fn(async () => json([])); vi.stubGlobal("fetch", fetch); page();
    expect(await screen.findByText("אין המרות היסטוריות.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("אינם זמינים");
    expect(screen.getByRole("link", { name: "מוצרים פנסיוניים נוכחיים" })).toHaveAttribute("href", "/clients/1/pension-products");
    expect(fetch.mock.calls).toHaveLength(1);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("reads persisted history without recomputation or source candidates", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(url); expect(init?.method ?? "GET").toBe("GET");
      if (url.endsWith("/history")) return json([revision()]);
      if (url.endsWith("/subjects")) return json([subject("one")]);
      return json(subject("one"));
    }));
    page(); fireEvent.click(await screen.findByRole("button", { name: /תיעוד היסטורי 1/ }));
    expect(await screen.findByText(/קלט היסטורי: 999999999999.99/, { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText(/02\/01\/2020/)).toBeInTheDocument();
    expect(screen.getByText(/31\/01\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/200.000.*4999999999.99/, { selector: "p" })).toBeInTheDocument();
    expect(calls.some((url) => /candidates|pension-holdings|m02|m03|m04|m05/.test(url))).toBe(false);
    expect(screen.queryByRole("button", { name: /יצירת טיוטה|פתרון הנוסחה|מקדם מתוקן/ })).not.toBeInTheDocument();
  });

  it.each(["resolve", "reject"])("ignores stale overview %s after A to B to A", async (outcome) => {
    let resolve!: (value: Response) => void; let reject!: (value: Error) => void;
    const old = new Promise<Response>((yes, no) => { resolve = yes; reject = no; });
    let count = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/clients/1/") && count++ === 0) return old;
      return json([]);
    }));
    page(); fireEvent.click(screen.getByRole("button", { name: "לקוח ב" }));
    await screen.findByText("אין המרות היסטוריות.");
    fireEvent.click(screen.getByRole("button", { name: "חזרה לא" }));
    await screen.findByText("אין המרות היסטוריות.");
    await act(async () => { if (outcome === "resolve") resolve(json([subject("stale")])); else reject(new Error("stale")); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /תיעוד היסטורי 1/ })).not.toBeInTheDocument();
  });

  it("drops stale history when another subject is selected", async () => {
    let resolve!: (value: Response) => void;
    const old = new Promise<Response>((yes) => { resolve = yes; });
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/subjects")) return json([subject("one"), subject("two")]);
      if (url.endsWith("/one/history")) return old;
      if (url.endsWith("/history")) return json([revision("current-two")]);
      return json(subject(url.endsWith("/one") ? "one" : "two"));
    }));
    page(); fireEvent.click(await screen.findByRole("button", { name: /תיעוד היסטורי 1/ }));
    fireEvent.click(screen.getByRole("button", { name: /תיעוד היסטורי 2/ }));
    await screen.findByText(/current-two/);
    await act(async () => resolve(json([revision("stale-one")])));
    expect(screen.queryByText(/stale-one/)).not.toBeInTheDocument();
  });

  it("shows a Hebrew read error without opening a write path", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("network"); }));
    page(); expect(await screen.findByRole("alert")).toHaveTextContent("לא ניתן לטעון");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
