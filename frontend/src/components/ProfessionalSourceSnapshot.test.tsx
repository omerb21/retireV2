import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProfessionalSourceSnapshot } from "./ProfessionalSourceSnapshot";
import type { SourceSnapshot, PensionSource } from "../api/professionalSourceApi";

const view = (client_id = 1, pension_sources: PensionSource[] = []): SourceSnapshot => ({
  client_id, contract_version: "canonical-professional-source-snapshot-v1", source_state_fingerprint: "fingerprint",
  pension_products: [], pension_sources, capital_sources: [], client_fact_warnings: [], source_warnings: [],
});
const source = (kind: "manual" | "conversion" = "manual"): PensionSource => ({
  source_id: kind + ":1", kind, manual_pension_source_id: kind === "manual" ? "1" : undefined,
  input_mode: "calculated", version: 3, lifecycle_status: "current", payer_name: "משלם בדיקה",
  balance: "1.00", annuity_factor: "3", pension_start_date: "2040-01-02", tax_treatment: "exempt",
  indexation_method: "none", visible: true, calculation_ready: true, has_started: false,
  missing_or_blocking_facts: [], provenance: {source_reference: "אסמכתה"},
  amount_authority: {authority_kind: kind === "manual" ? "manual_balance_ratio" : "persisted_conversion_ratio", numerator: "1.00", denominator: "3"},
});
const response = (body: unknown, ok = true) => ({ok, json: async () => body});
afterEach(() => vi.unstubAllGlobals());

describe("canonical professional sources", () => {
  it("shows exact ratios, future date, provenance and no conversion edit path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(1, [source("conversion")]))));
    const {container} = render(<ProfessionalSourceSnapshot clientId={1} />);
    expect(await screen.findByText("1.00 / 3")).toBeVisible();
    expect(screen.getByText(/02\/01\/2040/)).toBeVisible();
    expect(screen.getByText(/טרם הגיע מועד התחילה/)).toBeVisible();
    expect(screen.queryByText("0.33")).toBeNull();
    expect(screen.queryByRole("button", {name:"עריכת קצבה ידנית"})).toBeNull();
    expect(container.querySelector('section[dir="rtl"]')).not.toBeNull();
    expect(container.querySelector('input[type="date"]')).toBeNull();
  });
  it("creates incomplete entered facts without guessed date, tax, balance or rate", async () => {
    const fetcher = vi.fn().mockResolvedValue(response(view()));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    await screen.findByText("לא תועדו מקורות קצבה נוכחיים.");
    fireEvent.click(screen.getByRole("button", {name:"הוספת קצבה ידנית"}));
    fireEvent.change(screen.getByLabelText("סכום חודשי מדויק"), {target:{value:"123.45"}});
    fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    const [,init] = fetcher.mock.calls[1];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toMatchObject({monthly_amount:"123.45", balance:null, annuity_factor:null,
      pension_start_date:null, tax_treatment:null, fixed_indexation_rate:null});
  });
  it("sends calculated facts and Israeli date, not a rounded monthly authority", async () => {
    const fetcher = vi.fn().mockResolvedValue(response(view()));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    await screen.findByText("לא תועדו מקורות קצבה נוכחיים.");
    fireEvent.click(screen.getByRole("button", {name:"הוספת קצבה ידנית"}));
    fireEvent.change(screen.getByLabelText("מצב קלט"), {target:{value:"calculated"}});
    fireEvent.change(screen.getByLabelText("יתרת מקור"), {target:{value:"1.00"}});
    fireEvent.change(screen.getByLabelText("מקדם חיובי"), {target:{value:"3"}});
    fireEvent.change(screen.getByLabelText("תאריך תחילת קצבה"), {target:{value:"02/01/2040"}});
    fireEvent.change(screen.getByLabelText("שיטת הצמדה"), {target:{value:"fixed"}});
    fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      input_mode:"calculated", balance:"1.00", annuity_factor:"3", monthly_amount:null,
      pension_start_date:"2040-01-02", fixed_indexation_rate:null});
  });
  it.each(["edit", "supersede"])("versions manual %s and refreshes after mutation", async operation => {
    const fetcher = vi.fn().mockResolvedValue(response(view(1, [source()])));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    await screen.findByText("1.00 / 3");
    if (operation === "edit") {
      fireEvent.click(screen.getByRole("button", {name:"עריכת קצבה ידנית"}));
      expect(screen.getByLabelText("תאריך תחילת קצבה")).toHaveValue("02/01/2040");
      fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    } else fireEvent.click(screen.getByRole("button", {name:"הוצאה מהמקורות הנוכחיים"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(fetcher.mock.calls[1][0]).toBe("/api/clients/1/canonical-pension-sources/manual/1");
    expect(fetcher.mock.calls[1][1].method).toBe(operation === "edit" ? "PUT" : "DELETE");
    expect(JSON.parse(fetcher.mock.calls[1][1].body).expected_version).toBe(3);
  });
  it("shows incomplete/duplicate blockers without hiding sources or guessing tax", async () => {
    const row = {...source(), calculation_ready:false, tax_treatment:"capital_gains",
      missing_or_blocking_facts:["potential_duplicate_source","fixed_indexation_rate_missing"]};
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(1, [row]))));
    render(<ProfessionalSourceSnapshot clientId={1} />);
    expect(await screen.findByText(/חשד לכפילות מקור/)).toBeVisible();
    expect(screen.getByText("חסר שיעור הצמדה קבוע")).toBeVisible();
    expect(screen.getByText(/מס רווחי הון/)).toBeVisible();
  });
  it("does not expose manual actions in the consolidated read-only view", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(1, [source()]))));
    render(<ProfessionalSourceSnapshot clientId={1} readOnly />);
    await screen.findByText("1.00 / 3");
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });
  it("discards old client results even after A to B to A", async () => {
    const pending: Array<(value: unknown) => void> = [];
    vi.stubGlobal("fetch", vi.fn(() => new Promise(resolve => pending.push(resolve))));
    const {rerender} = render(<ProfessionalSourceSnapshot clientId={1} />);
    rerender(<ProfessionalSourceSnapshot clientId={2} />);
    rerender(<ProfessionalSourceSnapshot clientId={1} />);
    await act(async () => pending[2](response(view(1))));
    await act(async () => pending[0](response(view(1, [source()]))));
    await act(async () => pending[1](response(view(2, [source()]))));
    expect(screen.queryByText(/משלם בדיקה/)).toBeNull();
    expect(screen.getByText("לא תועדו מקורות קצבה נוכחיים.")).toBeVisible();
  });
  it("surfaces failed reads and refuses cross-client responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(2))));
    render(<ProfessionalSourceSnapshot clientId={1} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("שיוך תמונת המקורות ללקוח אינו תקין");
    expect(screen.queryByText("לא תועדו מקורות קצבה נוכחיים.")).toBeNull();
  });
});
