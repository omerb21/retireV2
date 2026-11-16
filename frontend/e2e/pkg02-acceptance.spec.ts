import { test, expect, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";

/** PKG-02: localhost-only synthetic browser/API tests using real backend + PG16.
 * Error injection (when explicit) is never used for persistence or authorization checks.
 */
const ROOT = "http://127.0.0.1:5174";
const API = ROOT + "/api/clients";
const A_NAME = "לקוח סינתטי PKG02 א";
const B_NAME = "לקוח סינתטי PKG02 ב";
let a = 0, b = 0, cap = "", asset = 0, income = 0, expense = 0;
const assets = (page: Page) => page.locator('section[aria-labelledby="capital-assets-heading"]');
const incomes = (page: Page) => page.locator('section[aria-labelledby="recurring-incomes-heading"]');
const expenses = (page: Page) => page.locator('section[aria-labelledby="recurring-expenses-heading"]');
const caps = (page: Page) => page.locator("section").filter({has: page.getByRole("heading", {name:"Actual Capitalizations",exact:true})}).last();
const workspace = (id: number) => ROOT + `/clients/${id}/workspace?step=supplement`;
async function getRows(request: any, id: number, route: string) {
  const response = await request.get(API + `/${id}/${route}`);
  expect(response.status()).toBe(200);
  return response.json();
}
test.describe.serial("PKG02 real-browser real-PostgreSQL acceptance", () => {
  test.setTimeout(120000);
  test.beforeEach(async ({ page }) => {
    await page.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.protocol === "http:" && url.hostname === "127.0.0.1" && url.port === "5174") return route.continue();
      return route.abort("blockedbyclient");
    });
  });

  test("01 creates synthetic client and opens step 3", async ({page}, info) => {
    await page.goto(ROOT + "/clients/new");
    await page.getByLabel("שם הלקוח").fill(A_NAME);
    await page.getByLabel("מספר זהות").fill("192000001");
    await page.getByRole("button", {name:"שמירת לקוח"}).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace\?step=client/);
    a = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
    expect(a).toBeGreaterThan(0);
    await page.goto(workspace(a));
    await expect(page.getByRole("heading", {name:"נתונים משלימים",exact:true})).toBeVisible();
    await expect(page.getByRole("region", {name:"עורכי נתונים משלימים PKG-02"})).toBeVisible();
    await page.screenshot({path:info.outputPath("01-step3.png"),fullPage:true});
  });

  test("02 creates actual capitalization from embedded editor", async ({page,request},info) => {
    await page.goto(workspace(a));
    const section = caps(page);
    await expect(section.getByRole("heading", {name:"Actual Capitalizations",exact:true})).toBeVisible();
    await section.getByLabel("Amount").fill("500.25");
    await section.getByLabel("Capitalization Date").fill("2026-01-15");
    await section.getByLabel("Source Label").fill("PKG02 synthetic capital");
    const pending=page.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname===`/api/clients/${a}/actual-capitalizations`);
    await section.getByRole("button",{name:"Add Actual Capitalization"}).click();
    const response=await pending; expect(response.status()).toBe(200);
    const rows=await getRows(request,a,"actual-capitalizations");
    const row=rows.find((x:any)=>x.source_label==="PKG02 synthetic capital");
    expect(row?.amount).toBeDefined();
    expect(String(row.amount)).toMatch(/^500\.25/);
    cap=row.capitalization_id;
    await page.screenshot({path:info.outputPath("02-capital-created.png"),fullPage:true});
  });

  test("03 creates capital asset with existing factual editor",async ({page,request},info)=>{
    await page.goto(workspace(a));
    const section=assets(page);
    await expect(section.getByRole("heading",{name:"נכסי הון",exact:true})).toBeVisible();
    await section.getByLabel("קטגוריית נכס").selectOption("bank deposit");
    await section.getByLabel("תיאור הנכס").fill("PKG02 bank deposit");
    await section.getByLabel("שווי ידוע").fill("8000.00");
    const pending=page.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname===`/api/clients/${a}/capital-assets`);
    await section.getByRole("button",{name:"הוספת נכס הון"}).click();
    expect((await pending).status()).toBe(200);
    const rows=await getRows(request,a,"capital-assets");
    asset=rows.find((x:any)=>x.asset_description==="PKG02 bank deposit")?.id;
    expect(asset).toBeGreaterThan(0);
    await page.screenshot({path:info.outputPath("03-capital-asset.png"),fullPage:true});
  });

  test("04 creates recurring income with amount basis and frequency",async ({page,request},info)=>{
    await page.goto(workspace(a));const section=incomes(page);
    await section.getByLabel("קטגוריית הכנסה").selectOption("rental");
    await section.getByLabel("תיאור").fill("PKG02 rental income");
    await section.getByLabel("סכום", {exact:true}).fill("1200.00");
    await section.getByLabel("בסיס הסכום").selectOption("gross");
    await section.getByLabel("תדירות").selectOption("monthly");
    await section.getByLabel("מצב המשכיות").selectOption("ongoing");
    const pending=page.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname===`/api/clients/${a}/recurring-incomes`);
    await section.getByRole("button",{name:"הוספת הכנסה שוטפת"}).click();
    expect((await pending).status()).toBe(200);
    const rows=await getRows(request,a,"recurring-incomes");
    const row=rows.find((x:any)=>x.description==="PKG02 rental income");
    expect(row?.amount_basis).toBe("gross");expect(row?.frequency).toBe("monthly");
    income=row.id;
    await page.screenshot({path:info.outputPath("04-income-created.png"),fullPage:true});
  });

  test("05 creates recurring expense without converting frequency",async ({page,request},info)=>{
    await page.goto(workspace(a));const section=expenses(page);
    await section.getByLabel("קטגוריית הוצאה").selectOption("housing");
    await section.getByLabel("תיאור").fill("PKG02 housing expense");
    await section.getByLabel("סכום").fill("800.00");
    await section.getByLabel("תדירות").selectOption("quarterly");
    await section.getByLabel("סוג הוצאה").selectOption("mandatory");
    await section.getByLabel("מצב המשכיות").selectOption("ongoing");
    const pending=page.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname===`/api/clients/${a}/recurring-expenses`);
    await section.getByRole("button",{name:"הוספת הוצאה שוטפת"}).click();
    expect((await pending).status()).toBe(200);
    const rows=await getRows(request,a,"recurring-expenses");
    const row=rows.find((x:any)=>x.description==="PKG02 housing expense");
    expect(row?.frequency).toBe("quarterly");expect(String(row.amount)).toMatch(/^800/);
    expense=row.id;
    await page.screenshot({path:info.outputPath("05-expense-created.png"),fullPage:true});
  });

  test("06 edits all four facts using PUT preflight and verifies persisted DB data",async ({page,request},info)=>{
    await page.goto(workspace(a));
    await caps(page).getByRole("button",{name:"Edit Actual Capitalization"}).first().click();
    await caps(page).getByLabel("Amount").fill("501.25");
    await caps(page).getByRole("button",{name:"Save Actual Capitalization"}).click();
    await expect.poll(async()=>String((await getRows(request,a,"actual-capitalizations")).find((x:any)=>x.capitalization_id===cap)?.amount)).toMatch(/^501\.25/);

    await assets(page).getByRole("button",{name:"עריכת נכס הון"}).click();
    await assets(page).getByLabel("תיאור הנכס").fill("PKG02 bank deposit edited");
    await assets(page).getByRole("button",{name:"שמירת נכס הון"}).click();
    await expect.poll(async()=>(await getRows(request,a,"capital-assets")).find((x:any)=>x.id===asset)?.asset_description).toBe("PKG02 bank deposit edited");

    await incomes(page).getByRole("button",{name:"עריכת הכנסה שוטפת"}).click();
    await incomes(page).getByLabel("תיאור").fill("PKG02 rental edited");
    await incomes(page).getByRole("button",{name:"שמירת הכנסה שוטפת"}).click();
    await expect.poll(async()=>(await getRows(request,a,"recurring-incomes")).find((x:any)=>x.id===income)?.description).toBe("PKG02 rental edited");

    await expenses(page).getByRole("button",{name:"עריכת הוצאה שוטפת"}).click();
    await expenses(page).getByLabel("תיאור").fill("PKG02 housing edited");
    await expenses(page).getByRole("button",{name:"שמירת הוצאה שוטפת"}).click();
    await expect.poll(async()=>(await getRows(request,a,"recurring-expenses")).find((x:any)=>x.id===expense)?.description).toBe("PKG02 housing edited");
    await page.reload();
    await expect(page.getByText("PKG02 bank deposit edited",{exact:true})).toBeVisible();
    await page.screenshot({path:info.outputPath("06-all-four-after-reload.png"),fullPage:true});
  });

  test("07 blocks step navigation while editor draft exists",async ({page},info)=>{
    await page.goto(workspace(a));
    await assets(page).getByLabel("תיאור הנכס").fill("PKG02 unsaved draft");
    await page.getByRole("button",{name:/4\. תכנון תרחישים/}).click();
    await expect(page.getByRole("heading",{name:"נתונים משלימים",exact:true})).toBeVisible();
    await expect(assets(page).getByLabel("תיאור הנכס")).toHaveValue("PKG02 unsaved draft");
    await page.screenshot({path:info.outputPath("07-draft-preserved.png"),fullPage:true});
    await assets(page).getByRole("button",{name:"ביטול העריכה"}).click();
    await page.getByRole("button",{name:/4\. תכנון תרחישים/}).click();
    await expect(page.getByRole("heading",{name:"תכנון תרחישים",exact:true})).toBeVisible();
    await page.getByRole("button",{name:/3\. נתונים משלימים/}).click();
  });

  test("08 rejects externally changed source before PUT and retains draft",async ({page,request},info)=>{
    await page.goto(workspace(a));
    await assets(page).getByRole("button",{name:"עריכת נכס הון"}).click();
    await assets(page).getByLabel("תיאור הנכס").fill("UNSAVED_DRAFT_SHOULD_REMAIN");
    const server=await request.put(API+`/${a}/capital-assets/${asset}`,{data:{asset_description:"PKG02 external update"}});
    expect(server.status()).toBe(200);
    await assets(page).getByRole("button",{name:"שמירת נכס הון"}).click();
    await expect(assets(page).getByText(/PKG02-CONCURRENCY-001/)).toBeVisible();
    await expect(assets(page).getByLabel("תיאור הנכס")).toHaveValue("UNSAVED_DRAFT_SHOULD_REMAIN");
    expect((await getRows(request,a,"capital-assets")).find((x:any)=>x.id===asset)?.asset_description).toBe("PKG02 external update");
    await page.screenshot({path:info.outputPath("08-preflight-conflict.png"),fullPage:true});
  });

  test("09 creates B, verifies A-B-A UI and database isolation",async ({page,request},info)=>{
    await page.goto(ROOT+"/clients/new");
    await page.getByLabel("שם הלקוח").fill(B_NAME);
    await page.getByLabel("מספר זהות").fill("192000002");
    await page.getByRole("button",{name:"שמירת לקוח"}).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace\?step=client/);
    b=Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
    expect(b).toBeGreaterThan(0);expect(b).not.toBe(a);
    await page.goto(workspace(b));
    await expect(assets(page).getByText("PKG02 external update")).toHaveCount(0);
    for(const route of ["actual-capitalizations","capital-assets","recurring-incomes","recurring-expenses"])expect(await getRows(request,b,route)).toEqual([]);
    await page.screenshot({path:info.outputPath("09-client-b-isolation.png"),fullPage:true});
    await page.goto(workspace(a));
    await expect(page.getByText("PKG02 external update",{exact:true})).toBeVisible();
    await page.screenshot({path:info.outputPath("09-return-client-a.png"),fullPage:true});
  });

  test("10 cross-client API read/write rejected by backend",async ({request},info)=>{
    const resources=[["actual-capitalizations",cap],["capital-assets",asset],["recurring-incomes",income],["recurring-expenses",expense]] as const;
    const evidence:any[]=[];
    for(const [route,id] of resources){
      const read=route==="actual-capitalizations" ? null : await request.get(API+`/${b}/${route}/${id}`);
      const put=await request.put(API+`/${b}/${route}/${id}`,{data:route==="actual-capitalizations"?{amount:"1",capitalization_date:"2026-01-15"}:{description:"FOREIGN_OVERWRITE"}});
      if(read) expect(read.status()).toBe(404); else expect((await getRows(request,b,route)).some((r:any)=>r.capitalization_id===id)).toBe(false);
      expect(put.status()).toBe(404);
      evidence.push({route,id,read:read?.status()??"scoped-list-empty",update:put.status()});
    }
    for(const [route,id] of resources)expect((await getRows(request,a,route)).some((r:any)=>(r.capitalization_id??r.id)===id)).toBe(true);
    writeFileSync(info.outputPath("10-api-isolation.json"),JSON.stringify({clientA:a,clientB:b,evidence},null,2));
  });

  test("11 legacy editors read same persisted records",async ({page},info)=>{
    await page.goto(ROOT+`/clients/${a}/actual-capitalizations`);
    await expect(page.getByText("PKG02 synthetic capital",{exact:true})).toBeVisible();
    await page.goto(ROOT+`/clients/${a}`);
    await expect(page.getByText("PKG02 external update",{exact:true})).toBeVisible();
    await expect(page.getByText("PKG02 rental edited",{exact:true})).toBeVisible();
    await expect(page.getByText("PKG02 housing edited",{exact:true})).toBeVisible();
    await page.screenshot({path:info.outputPath("11-legacy-parity.png"),fullPage:true});
  });

  test("12 backend validation and dependency-fingerprint regression evidence",async ({request},info)=>{
    const input=await request.get(API+`/${a}/retirement-planning-input`);
    expect(input.status()).toBe(200);
    const current=await input.json();
    const invalid=await request.post(API+`/${a}/recurring-expenses`,{data:{
      expense_category:"NOT_ALLOWED",description:"bad",amount:"100.00",frequency:"monthly",expense_type:"mandatory",continuation_status:"ongoing"
    }});
    expect(invalid.status()).toBe(422);
    const changed=await request.put(API+`/${a}/recurring-expenses/${expense}`,{data:{amount:"810.00"}});
    expect(changed.status()).toBe(200);
    const after=await request.get(API+`/${a}/retirement-planning-input`);
    expect(after.status()).toBe(200);
    const next=await after.json();
    expect(next.source_state_fingerprint).not.toBe(current.source_state_fingerprint);
    writeFileSync(info.outputPath("12-fingerprint-regression.json"),JSON.stringify({
      before:current.source_state_fingerprint,after:next.source_state_fingerprint,
      changed:true,invalidInputStatus:invalid.status(),
      caveat:"A changed fingerprint does not prove invalidation of every downstream scenario/result"
    },null,2));
  });
});
