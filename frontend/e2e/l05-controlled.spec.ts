import { test, expect } from "@playwright/test";

/** Instruction 284: real Chromium, loopback backend, disposable PostgreSQL. */
const ROOT = "http://127.0.0.1:5174";
const marker = "L05-284-UNSAVED-UNIQUE";
const persisted = "L05-284-SAVED-UNIQUE";

test("L05: native beforeunload cancel/accept, then saved data survives navigation", async ({ page, request }, info) => {
  test.setTimeout(120_000);
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    return url.origin === ROOT ? route.continue() : route.abort("blockedbyclient");
  });
  await page.goto(`${ROOT}/clients/new`);
  await page.getByLabel("שם הלקוח").fill("L05 synthetic 284");
  await page.getByLabel("מספר זהות").fill("192000084");
  await page.getByRole("button", { name: "שמירת לקוח" }).click();
  await expect(page).toHaveURL(/\/clients\/\d+\/workspace/);
  const id = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
  expect(id).toBeGreaterThan(0);
  const base = `${ROOT}/clients/${id}/workspace`;
  const assets = page.locator('section[aria-labelledby="capital-assets-heading"]');
  await page.goto(`${base}?step=supplement`);
  await expect(assets.getByRole("heading", { name: "נכסי הון", exact: true })).toBeVisible();
  await assets.getByLabel("תיאור הנכס").fill(marker);

  const observed: string[] = [];
  page.on("dialog", async dialog => {
    observed.push(`cancel:${dialog.type()}`);
    await dialog.dismiss();
  });
  await page.goto(`${base}?step=results`).catch(() => undefined);
  expect(observed, "Cancel must produce native beforeunload").toContain("cancel:beforeunload");
  await expect(assets.getByLabel("תיאור הנכס")).toHaveValue(marker);
  expect(new URL(page.url()).searchParams.get("step")).toBe("supplement");
  await page.screenshot({ path: info.outputPath("l05-cancel-keeps-draft.png") });

  page.removeAllListeners("dialog");
  page.on("dialog", async dialog => {
    observed.push(`accept:${dialog.type()}`);
    await dialog.accept();
  });
  await page.goto(`${base}?step=results`);
  expect(observed, "Accept must produce native beforeunload").toContain("accept:beforeunload");
  await expect(page.getByRole("heading", { name: "תוצאות והשוואה", exact: true })).toBeVisible();

  await page.goto(`${base}?step=supplement`);
  await assets.getByLabel("קטגוריית נכס").selectOption("bank deposit");
  await assets.getByLabel("תיאור הנכס").fill(persisted);
  await assets.getByLabel("שווי ידוע").fill("284.00");
  const post = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname === `/api/clients/${id}/capital-assets`);
  await assets.getByRole("button", { name: "הוספת נכס הון" }).click();
  expect((await post).status()).toBe(200);
  const savedResponse = await request.get(`${ROOT}/api/clients/${id}/capital-assets`);
  expect(savedResponse.status()).toBe(200);
  expect((await savedResponse.json()).some((row: { asset_description: string }) => row.asset_description === persisted)).toBe(true);
  await page.goto(`${base}?step=results`);
  await page.goto(`${base}?step=supplement`);
  await expect(page.getByRole("region", { name: "נכסי הון" })
    .getByRole("listitem").filter({ hasText: persisted })).toBeVisible();
  expect(observed.filter(item => item.startsWith("accept:")).length).toBe(1);
  await page.screenshot({ path: info.outputPath("l05-saved-and-restored.png") });
});
