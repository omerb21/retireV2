import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";

/** PKG-01 CI ONLY: real localhost browser, backend and disposable PostgreSQL 16.
 * Never use remote URLs, authentication bypasses, route mocks or customer data.
 */
const ROOT = "http://127.0.0.1:5174";
const API = ROOT + "/api/clients";
const TAG = "PKG01-CI-189";
let clientA = 0;
let clientB = 0;
let missingId = "";
let assumptionId = 0;

test.describe.serial("PKG-01: 11 independent acceptance checkpoints on real PG16", () => {
  test.setTimeout(120_000);
  test.beforeEach(async ({ page }) => {
    page.on("pageerror", error => { throw error; });
    await page.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.protocol === "http:" && url.hostname === "127.0.0.1" && url.port === "5174")
        return route.continue();
      return route.abort("blockedbyclient");
    });
  });

  test("01 opens synthetic client A through the real UI", async ({ page }, info) => {
    await page.goto(ROOT + "/clients/new");
    await page.getByLabel("שם הלקוח").fill("לקוח סינתטי PKG01 א");
    await page.getByLabel("מספר זהות").fill("189000001");
    await page.getByRole("button", { name: "שמירת לקוח" }).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace\?step=client/);
    clientA = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
    expect(clientA).toBeGreaterThan(0);
    await expect(page.getByText("לקוח סינתטי PKG01 א", { exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath("01-client-a.png"), fullPage: true });
  });

  test("02 navigates to step 3", async ({ page }) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=client`);
    await page.getByRole("button", { name: /3\. נתונים משלימים/ }).click();
    await expect(page.getByRole("heading", { name: "נתונים משלימים", exact: true })).toBeVisible();
  });

  test("03 displays advisory missing information region", async ({ page }, info) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await expect(page.getByRole("heading", { name: "מידע חסר לייעוץ", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "הוספת מידע חסר לייעוץ" })).toBeVisible();
    await page.screenshot({ path: info.outputPath("03-missing-region.png"), fullPage: true });
  });

  test("04 creates missing information through UI and real API", async ({ page }, info) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await page.getByLabel("תחום תכנון").selectOption("pension holdings");
    await page.getByLabel("סיבה ניטרלית").fill(TAG + "-missing-a");
    const received = page.waitForResponse(r => r.request().method() === "POST"
      && new URL(r.url()).pathname === `/api/clients/${clientA}/missing-items`);
    await page.getByRole("button", { name: "הוספת מידע חסר לייעוץ" }).click();
    const res = await received;
    expect(res.status(), await res.text()).toBe(200);
    const json = await res.json();
    expect(json.client_id).toBe(clientA);
    missingId = json.missing_data_item_id;
    expect(missingId).toMatch(/^MD-/);
    await expect(page.getByText("סיבה ניטרלית: " + TAG + "-missing-a")).toBeVisible();
    await page.screenshot({ path: info.outputPath("04-missing-saved.png"), fullPage: true });
  });

  test("05 missing information survives reload and database GET", async ({ page, request }) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await page.reload();
    await expect(page.getByText("סיבה ניטרלית: " + TAG + "-missing-a")).toBeVisible();
    const res = await request.get(API + `/${clientA}/missing-items`);
    expect(res.status()).toBe(200);
    const rows = await res.json();
    expect(rows).toEqual(expect.arrayContaining([expect.objectContaining({
      client_id: clientA, missing_data_item_id: missingId, neutral_reason: TAG + "-missing-a"
    })]));
  });

  test("06 displays planner assumptions region", async ({ page }, info) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await expect(page.getByRole("heading", { name: "הנחות מתכנן", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "הוספת הנחת מתכנן" })).toBeVisible();
    await page.screenshot({ path: info.outputPath("06-assumptions-region.png"), fullPage: true });
  });

  test("07 creates and persists professional assumption through UI", async ({ page }, info) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await page.getByLabel("קטגוריית הנחה").selectOption("income");
    await page.getByLabel("כותרת").fill(TAG + "-assumption-a");
    await page.getByLabel("ערך ההנחה").fill("1000 synthetic monthly");
    await page.getByLabel("נימוק").fill("CI synthetic test, not professional advice");
    await page.getByLabel("אחראי").selectOption("planner");
    const received = page.waitForResponse(r => r.request().method() === "POST"
      && new URL(r.url()).pathname === `/api/clients/${clientA}/planner-assumptions`);
    await page.getByRole("button", { name: "הוספת הנחת מתכנן" }).click();
    const res = await received;
    expect(res.status(), await res.text()).toBe(200);
    const json = await res.json();
    expect(json.client_id).toBe(clientA);
    assumptionId = json.id;
    expect(assumptionId).toBeGreaterThan(0);
    await expect(page.getByRole("heading", { name: TAG + "-assumption-a" })).toBeVisible();
    await page.screenshot({ path: info.outputPath("07-assumption-saved.png"), fullPage: true });
  });

  test("08 changes workspace steps and returns to step 3", async ({ page }) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await page.getByRole("button", { name: /4\. תכנון תרחישים/ }).click();
    await expect(page.getByRole("heading", { name: "תכנון תרחישים" })).toBeVisible();
    await page.getByRole("button", { name: /3\. נתונים משלימים/ }).click();
    await expect(page.getByRole("heading", { name: "מידע חסר לייעוץ", exact: true })).toBeVisible();
  });

  test("09 both records persist across step navigation and refresh", async ({ page, request }, info) => {
    await page.goto(ROOT + `/clients/${clientA}/workspace?step=supplement`);
    await page.reload();
    await expect(page.getByText("סיבה ניטרלית: " + TAG + "-missing-a")).toBeVisible();
    await expect(page.getByRole("heading", { name: TAG + "-assumption-a" })).toBeVisible();
    const res = await request.get(API + `/${clientA}/planner-assumptions`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toEqual(expect.arrayContaining([expect.objectContaining({
      client_id: clientA, id: assumptionId, title: TAG + "-assumption-a"
    })]));
    await page.screenshot({ path: info.outputPath("09-after-reload.png"), fullPage: true });
  });

  test("10 creates second synthetic client and verifies record isolation", async ({ page, request }, info) => {
    await page.goto(ROOT + "/clients/new");
    await page.getByLabel("שם הלקוח").fill("לקוח סינתטי PKG01 ב");
    await page.getByLabel("מספר זהות").fill("189000002");
    await page.getByRole("button", { name: "שמירת לקוח" }).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace\?step=client/);
    clientB = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
    expect(clientB).toBeGreaterThan(0);
    expect(clientB).not.toBe(clientA);
    await page.getByRole("button", { name: /3\. נתונים משלימים/ }).click();
    await expect(page.getByText(TAG + "-missing-a")).toHaveCount(0);
    await expect(page.getByText(TAG + "-assumption-a")).toHaveCount(0);
    const missing = await request.get(API + `/${clientB}/missing-items`);
    const assumptions = await request.get(API + `/${clientB}/planner-assumptions`);
    expect(missing.status()).toBe(200);
    expect(assumptions.status()).toBe(200);
    expect(await missing.json()).toEqual([]);
    expect(await assumptions.json()).toEqual([]);
    await page.screenshot({ path: info.outputPath("10-isolated-client-b.png"), fullPage: true });
  });

  test("11 server rejects cross-client record ID access and mutation", async ({ request }, info) => {
    expect(clientA).toBeGreaterThan(0);
    expect(clientB).toBeGreaterThan(0);
    const crossAssumption = await request.get(API + `/${clientB}/planner-assumptions/${assumptionId}`);
    expect(crossAssumption.status()).toBe(404);
    const crossWrite = await request.put(API + `/${clientB}/missing-items/${missingId}`, {
      data: { neutral_reason: "UNAUTHORIZED_CROSS_CLIENT_MUTATION" }
    });
    expect(crossWrite.status()).toBe(404);
    const crossAssumptionWrite = await request.put(
      API + `/${clientB}/planner-assumptions/${assumptionId}`, {
      data: { rationale: "UNAUTHORIZED_CROSS_CLIENT_MUTATION" }
    });
    expect(crossAssumptionWrite.status()).toBe(404);
    const ownerMissing = await request.get(API + `/${clientA}/missing-items`);
    const ownerAssumptions = await request.get(API + `/${clientA}/planner-assumptions`);
    expect(ownerMissing.status()).toBe(200);
    expect(ownerAssumptions.status()).toBe(200);
    expect((await ownerMissing.json()).find((x: any) => x.missing_data_item_id === missingId)?.neutral_reason)
      .toBe(TAG + "-missing-a");
    expect((await ownerAssumptions.json()).find((x: any) => x.id === assumptionId)?.rationale)
      .toBe("CI synthetic test, not professional advice");
    writeFileSync(info.outputPath("11-cross-client-api.json"), JSON.stringify({
      clientA, clientB, missingId, assumptionId,
      crossAssumptionStatus: crossAssumption.status(), crossMissingWriteStatus: crossWrite.status(),
      crossAssumptionWriteStatus: crossAssumptionWrite.status(),
      ownerRecordsUnchanged: true,
      limitation: "Record ownership scoped to client ID, not a multi-actor authorization test"
    }, null, 2));
  });
});
