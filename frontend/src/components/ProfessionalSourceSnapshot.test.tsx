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
  temporal_authority: {temporal_authority_kind:"none", temporal_origin_date:"2026-09-01", annual_rate:null,
    rate_basis:null, temporal_authority_ready:true, temporal_blockers:[], provenance: kind === "conversion"
      ? {pension_destination_id:"destination-1", decision_version:0, source_version_at_decision:null} : undefined},
  missing_or_blocking_facts: [], provenance: {source_reference: "אסמכתה"},
  amount_authority: {authority_kind: kind === "manual" ? "manual_balance_ratio" : "persisted_conversion_ratio", numerator: "1.00", denominator: "3"},
});
const response = (body: unknown, ok = true) => ({ok, json: async () => body});
afterEach(() => vi.unstubAllGlobals());

describe("canonical professional sources", () => {
  it.each([
    ["BASE_AMOUNT_EFFECTIVE_DATE_MISSING", "חסר תאריך נכונות לסכום הבסיס החודשי"],
    ["monthly_amount_not_positive", "נדרש סכום קצבה חודשי חיובי"],
    ["balance_not_positive", "נדרשת יתרה חיובית"],
    ["fixed_indexation_rate_not_positive", "נדרש שיעור הצמדה קבוע חיובי"],
  ])("explains %s in Hebrew without hiding the source", async (code, label) => {
    const row = {...source(), calculation_ready:false, missing_or_blocking_facts:[code]};
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(1, [row]))));
    render(<ProfessionalSourceSnapshot clientId={1} />);
    expect(await screen.findByText(label)).toBeVisible();
    expect(screen.getByText("מקור לא שלם או חסום לחישוב")).toBeVisible();
    expect(screen.getByText("1.00 / 3")).toBeVisible();
    expect(screen.queryByText("עובדות המקור מוכנות לחישוב")).toBeNull();
    expect(screen.queryByText(code)).toBeNull();
  });
  it("shows exact ratios, future date, provenance and the explicit conversion authority path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view(1, [source("conversion")]))));
    const {container} = render(<ProfessionalSourceSnapshot clientId={1} />);
    expect(await screen.findByText("1.00 / 3")).toBeVisible();
    expect(screen.getByText(/02\/01\/2040/)).toBeVisible();
    expect(screen.getByText(/טרם הגיע מועד התחילה/)).toBeVisible();
    expect(screen.queryByText("0.33")).toBeNull();
    expect(screen.queryByRole("button", {name:"עריכת קצבה ידנית"})).toBeNull();
    expect(screen.getByRole("button", {name:"עריכת סמכות יעד המרה"})).toBeVisible();
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
      pension_start_date:null, tax_treatment:null, temporal_authority:null});
    expect(JSON.parse(init.body).base_amount_effective_date).toBeNull();
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
    fireEvent.change(screen.getByLabelText("סמכות הצמדה מפורשת"), {target:{value:"fixed_manual"}});
    fireEvent.change(screen.getByLabelText("שיעור שנתי מדויק"), {target:{value:"0.02"}});
    fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      input_mode:"calculated", balance:"1.00", annuity_factor:"3", monthly_amount:null,
      pension_start_date:"2040-01-02", temporal_authority:{authority_kind:"fixed_manual", annual_rate:"0.02"}});
    expect(JSON.parse(fetcher.mock.calls[1][1].body).base_amount_effective_date).toBeNull();
  });
  it.each(["entered", "calculated"] as const)("edits and explicitly clears the independent base date in %s mode", async mode => {
    const row = {...source(), input_mode:mode, base_amount_effective_date:"2026-09-01"};
    const fetcher = vi.fn().mockResolvedValue(response(view(1, [row])));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    expect((await screen.findAllByText(/01\/09\/2026/)).length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByRole("button", {name:"עריכת קצבה ידנית"}));
    expect(screen.getByLabelText("תאריך נכונות סכום הבסיס החודשי")).toHaveValue("01/09/2026");
    fireEvent.change(screen.getByLabelText("תאריך תחילת קצבה"), {target:{value:"03/01/2040"}});
    expect(screen.getByLabelText("תאריך נכונות סכום הבסיס החודשי")).toHaveValue("01/09/2026");
    fireEvent.change(screen.getByLabelText("תאריך נכונות סכום הבסיס החודשי"), {target:{value:""}});
    fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      base_amount_effective_date:null, pension_start_date:"2040-01-03", expected_version:3});
  });
  it("sends an explicit base date without inheriting pension start", async () => {
    const fetcher = vi.fn().mockResolvedValue(response(view()));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    await screen.findByText("לא תועדו מקורות קצבה נוכחיים.");
    fireEvent.click(screen.getByRole("button", {name:"הוספת קצבה ידנית"}));
    expect(screen.getByLabelText("תאריך נכונות סכום הבסיס החודשי")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("תאריך נכונות סכום הבסיס החודשי"), {target:{value:"15/09/2026"}});
    expect(screen.getByLabelText("תאריך תחילת קצבה")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", {name:"שמירת קצבה ידנית"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      base_amount_effective_date:"2026-09-15", pension_start_date:null});
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
  it("writes conversion temporal authority with both expected versions", async () => {
    const fetcher = vi.fn().mockResolvedValue(response(view(1, [source("conversion")])));
    vi.stubGlobal("fetch", fetcher);
    render(<ProfessionalSourceSnapshot clientId={1} />);
    await screen.findByText("1.00 / 3");
    fireEvent.click(screen.getByRole("button", {name:"עריכת סמכות יעד המרה"}));
    fireEvent.change(screen.getByLabelText("סמכות הצמדה ליעד המרה"), {target:{value:"fixed_manual"}});
    fireEvent.change(screen.getByLabelText("שיעור שנתי מדויק ליעד המרה"), {target:{value:"2e-2"}});
    fireEvent.click(screen.getByRole("button", {name:"שמירת החלטת יעד המרה"}));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(fetcher.mock.calls[1][0]).toBe("/api/clients/1/canonical-pension-sources/conversion/destination-1/temporal-authority");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({expected_source_version:3,
      expected_decision_version:0, temporal_authority:{authority_kind:"fixed_manual",annual_rate:"2e-2"}, actor:"planner:ui"});
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
