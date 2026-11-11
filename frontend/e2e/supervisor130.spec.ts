/** Supervisor 130: synthetic full workspace journey using the existing guarded
 * localhost PG16 backend and accepted clearinghouse XML fixture vocabulary.
 * No mocked routes, external hosts or calculation permissions.
 */
import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";

const ROOT = "http://127.0.0.1:5174";
const xml = `<Root><SHEM-YATZRAN>מנהל סינתטי</SHEM-YATZRAN>
<Account><MISPAR-HESHBON>SUPERVISOR-130</MISPAR-HESHBON>
<SHEM-TOCHNIT>תכנית מסלקה 130</SHEM-TOCHNIT><SUG-MUTZAR>3</SUG-MUTZAR>
<TAARICH-NECHONUT-YITROT>20260901</TAARICH-NECHONUT-YITROT>
<BlockItrot><Yitrot>
<PerutYitraLeTkufa><REKIV-ITRA-LETKUFA>2</REKIV-ITRA-LETKUFA><KOD-TECHULAT-SHICHVA>1</KOD-TECHULAT-SHICHVA><SACH-ITRA-LESHICHVA-BESHACH>100</SACH-ITRA-LESHICHVA-BESHACH></PerutYitraLeTkufa>
<PerutYitrot><TOTAL-CHISACHON-MTZBR>100</TOTAL-CHISACHON-MTZBR></PerutYitrot>
</Yitrot></BlockItrot></Account></Root>`;

test("supervisor 130: create client, import synthetic source, five steps, return and isolation", async ({ page, request }, info) => {
  test.setTimeout(180_000);
  const apiLog: Array<{ method: string; path: string; status: number }> = [];
  const pageErrors: string[] = [];
  page.on("pageerror", err => pageErrors.push(err.message));
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    return url.protocol === "http:" && url.hostname === "127.0.0.1" && url.port === "5174"
      ? route.continue() : route.abort("blockedbyclient");
  });
  page.on("response", response => {
    const u = new URL(response.url());
    if (u.pathname.startsWith("/api/")) apiLog.push({
      method: response.request().method(), path: u.pathname, status: response.status(),
    });
  });
  const screenshot = async (index: number, title: string) =>
    page.screenshot({ path: info.outputPath(`${String(index).padStart(2, "0")}-${title}.png`), fullPage: true });
  try {
    await page.goto(ROOT + "/clients/new", { waitUntil: "domcontentloaded" });
    await page.getByLabel("שם הלקוח").fill("לקוח סינתטי 130");
    await page.getByLabel("מספר זהות").fill("123456782");
    await page.getByRole("button", { name: "שמירת לקוח" }).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace\?step=client/);
    const match = new URL(page.url()).pathname.match(/^\/clients\/(\d+)\/workspace$/);
    expect(match).not.toBeNull();
    const id = Number(match![1]);
    const base = `/clients/${id}/workspace`;
    await expect(page.getByRole("region", { name: "פרטי הלקוח ותכנון פרישה" })).toBeVisible();
    await screenshot(1, "client");

    await page.getByRole("button", { name: /2\. תיק פנסיוני/ }).click();
    const money = page.getByRole("region", { name: "טבלת רכיבים נגללת" });
    await expect(money).toBeVisible();
    await page.getByLabel("קובצי מסלקה").setInputFiles({
      name: "supervisor130.xml", mimeType: "application/xml", buffer: Buffer.from(xml, "utf8"),
    });
    const imported = page.waitForResponse(r =>
      r.request().method() === "POST" && new URL(r.url()).pathname ===
      `/api/clients/${id}/pension-products/imports`);
    await page.getByRole("button", { name: "ייבוא מסלקה ועדכון הטבלה" }).click();
    const importedResponse = await imported;
    expect(importedResponse.status(), await importedResponse.text()).toBe(200);
    const batch = await importedResponse.json();
    expect(batch.product_count).toBe(1);
    expect(batch.products).toHaveLength(1);
    expect(batch.products[0].client_id).toBe(id);
    await expect(money.getByText("תכנית מסלקה 130")).toBeVisible();
    await expect(money.getByRole("columnheader", { name: "מצב מקור וקליטה" })).toBeVisible();
    await screenshot(2, "portfolio");

    await page.getByRole("button", { name: /3\. נתונים משלימים/ }).click();
    await expect(page.getByRole("heading", { name: "נתונים משלימים" })).toBeVisible();
    await screenshot(3, "supplement");

    await page.getByRole("button", { name: /4\. תכנון תרחישים/ }).click();
    await expect(page.getByRole("heading", { name: "תכנון תרחישים" })).toBeVisible();
    await screenshot(4, "scenario");

    await page.getByRole("button", { name: /5\. תוצאות והשוואה/ }).click();
    await expect(page.getByRole("heading", { name: "תוצאות והשוואה" })).toBeVisible();
    await screenshot(5, "results");

    // Specialist page is still inside the same client's workspace frame.
    await page.goto(ROOT + `/clients/${id}/pension-products`, { waitUntil: "domcontentloaded" });
    const nav = page.getByRole("navigation", { name: "שלבי תיק הלקוח" });
    await expect(nav).toBeVisible();
    await expect(page.getByText(`מזהה תיק ${id}`)).toBeVisible();
    await nav.getByRole("link", { name: /2\. תיק פנסיוני/ }).click();
    await expect(page).toHaveURL(new RegExp(`/clients/${id}/workspace\\?step=portfolio`));
    await expect(page.getByRole("region", { name: "טבלת רכיבים נגללת" })).toBeVisible();
    await expect(page.getByRole("region", { name: "טבלת רכיבים נגללת" })
      .getByText("תכנית מסלקה 130")).toBeVisible();

    // Existing independent synthetic client cannot see newly imported source.
    await page.goto(ROOT + "/clients/410078/workspace?step=portfolio", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("region", { name: "טבלת רכיבים נגללת" })).toBeVisible();
    await expect(page.getByText("תכנית מסלקה 130")).toHaveCount(0);
    await page.goto(ROOT + base + "?step=portfolio", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("region", { name: "טבלת רכיבים נגללת" })
      .getByText("תכנית מסלקה 130")).toBeVisible();

    expect(apiLog.some(row => row.method === "POST" && row.path.endsWith("/pension-products/imports")
      && row.status === 200)).toBe(true);
    expect(pageErrors).toEqual([]);
  } finally {
    writeFileSync(info.outputPath("api-evidence.json"), JSON.stringify(apiLog, null, 2));
    writeFileSync(info.outputPath("page-errors.json"), JSON.stringify(pageErrors, null, 2));
  }
});
