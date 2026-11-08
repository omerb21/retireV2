/**
 * Live browser acceptance against localhost-only synthetic Supervisor 41 data.
 * Invoked exclusively by the isolated Windows harness; no remote endpoints.
 */
import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";

const CLIENT = 410041;
const A = "supervisor41-scenario-a";
const B = "supervisor41-scenario-b";
const GRANT = "supervisor41-grant";
const COMPONENT = "supervisor41-severance";
const API = "/api/clients/" + CLIENT;
const WORKSPACE = "/clients/" + CLIENT + "/workspace";
const BASE_URL = "http://127.0.0.1:5173";

test("supervisor 41: scenario severance decisions survive navigation and reject stale sources / overallocation", async ({
  page, request,
}, testInfo) => {
  test.setTimeout(150_000);
  // Browser access is restricted to the test-only Vite loopback origin.
  // Any unexpected external request is rejected rather than exfiltrating
  // even synthetic scenario data.
  await page.route("**/*", route => {
    const target = new URL(route.request().url());
    if (target.hostname !== "127.0.0.1" || target.port !== "5173"
        || target.protocol !== "http:") {
      return route.abort("blockedbyclient");
    }
    return route.continue();
  });
  const failures: string[] = [];
  const consoleErrors: string[] = [];
  const apiEvidence: Array<{ method: string; url: string; status: number; body: unknown }> = [];
  page.on("console", message => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", error => consoleErrors.push(error.message));
  page.on("requestfailed", req => failures.push(req.method() + " " + req.url() + " " + req.failure()?.errorText));
  page.on("response", async response => {
    const pathname = new URL(response.url()).pathname;
    if (!pathname.startsWith(API)) return;
    const method = response.request().method();
    if (pathname.includes("/severance-planning") || response.status() >= 400) {
      let body: unknown = null;
      try { body = await response.json(); } catch { /* may be empty */ }
      apiEvidence.push({ method, url: pathname, status: response.status(), body });
      const expectedOverAllocation = method === "PUT"
        && pathname === API + "/scenario-drafts/" + B + "/severance-planning"
        && response.status() === 422;
      if (response.status() >= 400 && !expectedOverAllocation) {
        failures.push(method + " " + pathname + " HTTP " + response.status());
      }
    }
  });
  async function capture(name: string) {
    await page.screenshot({ path: testInfo.outputPath(name + ".png"), fullPage: true });
  }
  try {
    // Vite --mode test disables only the local login gate. Backend APP_ENV=test
    // continues to execute real application routes against isolated PG16.
    await page.goto(BASE_URL + WORKSPACE, { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    await expect(page.getByRole("heading", { name: "תכנון תרחישים" })).toBeVisible();

    const region = page.getByRole("region", { name: "תכנון פיצויים ומענקים" });
    await expect(region.getByText("מענק: מעסיק סינתטי 41")).toBeVisible();
    await expect(region.getByText(/קרן פנסיה סינתטית 41/)).toBeVisible();
    await expect(region.getByText(/בחירות תכנון בלבד/)).toBeVisible();
    await capture("01-synthetic-sources");

    const group = page.getByRole("group", { name: "בחירת חלופה" });
    await group.getByRole("button", { name: "חלופה סינתטית א" }).click();
    const grantRow = region.locator(".scenario-conversion__saved").filter({
      hasText: "מענק: מעסיק סינתטי 41",
    });
    const pensionRow = region.locator(".scenario-conversion__saved").filter({
      hasText: "קרן פנסיה סינתטית 41",
    });
    await grantRow.getByRole("combobox").selectOption("PLANNED_PENSION_CONTINUITY");
    await pensionRow.getByRole("combobox").selectOption("PLANNED_WITHDRAWAL");
    await pensionRow.getByRole("textbox").fill("100.5");
    await region.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }).click();
    await expect(region.getByText(/בחירה שמורה|חפיפה אפשרית/).first()).toBeVisible();
    const savedA = await request.get(BASE_URL + API + "/scenario-drafts/" + A + "/severance-planning");
    expect(savedA.status()).toBe(200);
    const savedPayload = await savedA.json();
    expect(savedPayload.choices).toEqual(expect.arrayContaining([
      expect.objectContaining({ source_kind: "pension_component", source_id: COMPONENT,
        planned_amount_ils: "100.50", choice: "PLANNED_WITHDRAWAL" }),
      expect.objectContaining({ source_kind: "grant", source_id: GRANT,
        choice: "PLANNED_PENSION_CONTINUITY", actual_paid_amount_ils: null,
        exempt_amount_ils: null, net_amount_ils: null }),
    ]));
    await capture("02-saved-alternative-a");

    await group.getByRole("button", { name: "חלופה סינתטית ב" }).click();
    await expect(region.getByText("מענק: מעסיק סינתטי 41")).toBeVisible();
    await expect(region.getByText(/בחירה שמורה/)).toHaveCount(0);
    const emptyB = await request.get(BASE_URL + API + "/scenario-drafts/" + B + "/severance-planning");
    expect((await emptyB.json()).choices).toEqual([]);
    await group.getByRole("button", { name: "חלופה סינתטית א" }).click();
    await expect(pensionRow.getByRole("combobox")).toHaveValue("PLANNED_WITHDRAWAL");
    await expect(pensionRow.getByRole("textbox")).toHaveValue("100.50");
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const reloadedRegion = page.getByRole("region", { name: "תכנון פיצויים ומענקים" });
    await expect(reloadedRegion.getByText(/קרן פנסיה סינתטית 41/)).toBeVisible();
    const reloadedPension = reloadedRegion.locator(".scenario-conversion__saved").filter({
      hasText: "קרן פנסיה סינתטית 41",
    });
    await expect(reloadedPension.getByRole("textbox")).toHaveValue("100.50");
    await capture("03-reloaded-selection");

    // Mutate canonical grant through its *existing* real client API.
    // This is synthetic data only, no direct DB edit or test-only endpoint.
    const changedGrant = await request.put(BASE_URL + API + "/grants/" + GRANT, {
      data: {
        employer_name: "מעסיק סינתטי 41",
        employer_withholding_file_number: "SYNTHETIC41",
        employment_start_date: "2011-01-01",
        employment_end_date: "2025-12-31",
        grant_receipt_date: "2025-12-31",
        exempt_grant_amount: "160.00",
      },
    });
    expect(changedGrant.status(), await changedGrant.text()).toBe(200);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const staleRegion = page.getByRole("region", { name: "תכנון פיצויים ומענקים" });
    await expect(staleRegion.getByText(/פרטי המקור או ההעסקה השתנו/)).toBeVisible();
    await expect(staleRegion.getByText(/בחירות תכנון בלבד/)).toBeVisible();
    await capture("04-stale-grant-blocked");

    // Create an existing pension/capital allocation of 150 ILS in scenario B.
    // Saving another 100.50 ILS against the same 200 ILS component MUST be
    // rejected atomically by the real severance service (HTTP 422).
    const draftB = await request.get(BASE_URL + API + "/scenario-drafts/" + B);
    expect(draftB.status()).toBe(200);
    const currentB = await draftB.json();
    const allocation = await request.put(BASE_URL + API + "/scenario-drafts/" + B, {
      data: {
        name: currentB.name, expected_version: currentB.version,
        decisions: [{
          source_product_id: "supervisor41-product",
          source_component_id: COMPONENT, component_code: "פיצויים_מעסיק_נוכחי",
          amount: "150.00", action: "capital_asset", effective_date: "2027-01-01",
        }],
      },
    });
    expect(allocation.status(), await allocation.text()).toBe(200);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    await page.getByRole("group", { name: "בחירת חלופה" })
      .getByRole("button", { name: "חלופה סינתטית ב" }).click();
    const regionB = page.getByRole("region", { name: "תכנון פיצויים ומענקים" });
    const pensionB = regionB.locator(".scenario-conversion__saved").filter({
      hasText: "קרן פנסיה סינתטית 41",
    });
    await pensionB.getByRole("combobox").selectOption("PLANNED_WITHDRAWAL");
    await pensionB.getByRole("textbox").fill("100.5");
    const beforeB = await request.get(BASE_URL + API + "/scenario-drafts/" + B + "/severance-planning");
    const beforeBVersion = (await beforeB.json()).scenario_version;
    const rejectedResponse = page.waitForResponse(response =>
      response.url().includes("/scenario-drafts/" + B + "/severance-planning")
      && response.request().method() === "PUT");
    await regionB.getByRole("button", { name: "שמור החלטות פיצויים בחלופה" }).click();
    const rejected = await rejectedResponse;
    expect(rejected.status()).toBe(422);
    expect(JSON.stringify(await rejected.json())).toContain("SEVERANCE_COMPONENT_OVERALLOCATED");
    await expect(regionB.getByRole("alert")).toContainText("SEVERANCE_COMPONENT_OVERALLOCATED");
    const afterB = await request.get(BASE_URL + API + "/scenario-drafts/" + B + "/severance-planning");
    expect((await afterB.json()).scenario_version).toBe(beforeBVersion);
    expect((await afterB.json()).choices).toEqual([]);
    await capture("05-overallocation-rejected");

    // Chromium may log the single intentionally rejected HTTP 422 as a
    // resource error. Record it, but never mask other failures.
    const expected422Logs = consoleErrors.filter(message =>
      /Failed to load resource/.test(message) && /422/.test(message));
    expect(expected422Logs.length).toBeLessThanOrEqual(1);
    expect(consoleErrors.filter(message => !expected422Logs.includes(message)),
      "Unexpected browser console errors").toEqual([]);
    expect(failures, "Unexpected browser API failures").toEqual([]);
  } finally {
    writeFileSync(testInfo.outputPath("api-responses.json"), JSON.stringify(apiEvidence, null, 2), "utf8");
    writeFileSync(testInfo.outputPath("browser-errors.json"), JSON.stringify({ consoleErrors, failures }, null, 2), "utf8");
  }
});
