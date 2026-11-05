import { describe, expect, it } from "vitest";
import type { PensionProduct } from "../api/pensionProductsApi";
import type { ScenarioDraft, ScenarioDraftDecision } from "../api/scenarioDraftsApi";
import { PORTFOLIO_COMPONENT_COLUMNS } from "./portfolioComponentColumns";
import {
  buildPlanDecisions, buildPlanRows, planCents, planMoney, selectPlanScope,
} from "./scenarioConversionPlan";

const severance = PORTFOLIO_COMPONENT_COLUMNS[0][0];
const reward = PORTFOLIO_COMPONENT_COLUMNS[6][0];
const makeProduct = (id: string, amounts: Record<string, string>): PensionProduct => ({
  product_id: id, product_name: "Program " + id,
  client_id: 1, version: 1, source_kind: "manual",
  product_type: "קרן פנסיה", provider_name: "Test", provider_identifier: null,
  account_reference: null, start_date: null, statement_date: "2026-10-31",
  historical_employers: [], reported_product_total: null,
  reported_rewards_total: null, reported_severance_total: null,
  components: amounts, reconciliation: {}, updated_at: "",
  conversion_components: Object.entries(amounts).map(([code, balance]) => ({
    component_id: id + "-" + code, component_code: code, balance, allowed_destinations: {},
  })),
});
const decision = (product: PensionProduct, code: string, amount: string,
  state: ScenarioDraftDecision["validation_state"] = "unverified"): ScenarioDraftDecision => ({
  decision_id: "id-" + product.product_id + "-" + code,
  source_product_id: product.product_id, source_component_id: product.product_id + "-" + code,
  component_code: code, amount, action: "pension", effective_date: "2027-01-01",
  validation_state: state, product_version_at_review: 1,
  source_fingerprint_at_review: "a".repeat(64), ruleset_digest_at_review: null,
  permission_preview_id_at_review: null,
});

describe("scenario portfolio-shaped conversion planning", () => {
  it("uses exactly the portfolio's 11 original component columns in the same order", () => {
    const rows = buildPlanRows([makeProduct("a", { [reward]: "200.00" })], []);
    expect(rows[0].cells.map(c => c.code)).toEqual(PORTFOLIO_COMPONENT_COLUMNS.map(([code]) => code));
    expect(rows[0].cells).toHaveLength(11);
  });

  it("keeps money in integer cents and never rounds", () => {
    expect(planCents("999999999999.99")).toBe(99999999999999n);
    expect(planMoney(99999999999999n)).toBe("999999999999.99");
    expect(planCents("1.999")).toBeNull();
    expect(planCents("-1")).toBeNull();
  });

  it("supports single component and partial conversion at a specific date", () => {
    const rows = buildPlanRows([makeProduct("a", { [reward]: "100.00" })], []);
    const selected = selectPlanScope(rows, { productId: "a", code: reward });
    const batch = buildPlanDecisions(rows, selected, "pension", "2028-02-29", "35.20");
    expect(batch).toEqual([{
      source_product_id: "a", source_component_id: "a-" + reward, component_code: reward,
      amount: "35.20", action: "pension", effective_date: "2028-02-29",
    }]);
  });

  it("selects the entire program without counting empty and zero cells", () => {
    const rows = buildPlanRows([makeProduct("a", { [severance]: "120.00", [reward]: "30.00" })], []);
    const keys = selectPlanScope(rows, { productId: "a" });
    expect(keys).toHaveLength(2);
    expect(buildPlanDecisions(rows, keys, "capital_asset", "2027-11-01")
      .map(x => x.amount)).toEqual(["120.00", "30.00"]);
  });

  it("selects the complete column across all programs", () => {
    const rows = buildPlanRows([
      makeProduct("a", { [reward]: "100.00" }),
      makeProduct("b", { [reward]: "200.00" }),
    ], []);
    const keys = selectPlanScope(rows, { code: reward });
    expect(keys).toHaveLength(2);
    expect(buildPlanDecisions(rows, keys, "pension", "2030-01-01")
      .map(x => x.amount)).toEqual(["100.00", "200.00"]);
  });

  it("allocates only the still-available amount without changing source balances", () => {
    const source = makeProduct("a", { [reward]: "100.00" });
    const rows = buildPlanRows([source], [decision(source, reward, "35.00")]);
    const keys = selectPlanScope(rows, { code: reward });
    expect(buildPlanDecisions(rows, keys, "pension", "2028-01-01")[0].amount).toBe("65.00");
    expect(source.components[reward]).toBe("100.00");
  });

  it("rejects an entire program if even one positive component lacks canonical mapping", () => {
    const source = makeProduct("a", { [severance]: "80.00", [reward]: "100.00" });
    source.conversion_components = source.conversion_components!.filter(x => x.component_code !== reward);
    const rows = buildPlanRows([source], []);
    expect(() => selectPlanScope(rows, { productId: "a" })).toThrow("חסרה מיפוי");
  });

  it("never silently converts a partial column with a stale source", () => {
    const a = makeProduct("a", { [reward]: "100.00" });
    const b = makeProduct("b", { [reward]: "200.00" });
    const rows = buildPlanRows([a, b], [decision(b, reward, "40.00", "needs_revalidation")]);
    expect(() => selectPlanScope(rows, { code: reward })).toThrow("לפחות יתרה אחת");
  });

  it("rejects over-allocated balances and a missing source component", () => {
    const a = makeProduct("a", { [reward]: "100.00" });
    const rows = buildPlanRows([a], [decision(a, reward, "101.00")]);
    expect(rows[0].cells.find(c => c.code === reward)?.blocked).toBe("הקצאת יתר בחלופה");
    expect(() => selectPlanScope(rows, { productId: "a" })).toThrow();
  });

  it("rejects excessive partial amount and invalid dates without saving", () => {
    const rows = buildPlanRows([makeProduct("a", { [reward]: "50.00" })], []);
    const keys = selectPlanScope(rows, { code: reward });
    expect(() => buildPlanDecisions(rows, keys, "pension", "2027-01-01", "50.01")).toThrow();
    expect(() => buildPlanDecisions(rows, keys, "pension", "2027-02-30")).toThrow();
    expect(() => buildPlanDecisions(rows, keys, "pension", "")).toThrow();
    expect(() => buildPlanDecisions(rows, [...keys, ...keys], "pension", "2027-01-01")).toThrow();
  });

  it("never chooses a fully allocated component again", () => {
    const p = makeProduct("a", { [reward]: "100.00" });
    expect(() => selectPlanScope(buildPlanRows([p], [decision(p, reward, "100.00")]),
      { productId: "a" })).toThrow("כבר הוקצו");
  });

  it("does not mutate the live product or decisions when generating a batch", () => {
    const p = makeProduct("a", { [reward]: "99.00" });
    const original = JSON.stringify(p);
    const rows = buildPlanRows([p], []);
    const batch = buildPlanDecisions(rows, selectPlanScope(rows, { code: reward }),
      "capital_asset", "2031-01-31");
    expect(batch).toHaveLength(1);
    expect(JSON.stringify(p)).toBe(original);
  });
});
