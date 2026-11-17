import { test, expect } from "@playwright/test";

const ROOT = "http://127.0.0.1:5174";
test("PKG-03: real PostgreSQL admission is read-only and visibly blocked in both workspace stages", async ({ page, request }, info) => {
  test.setTimeout(120000);
  await page.route("**/*", route => {
    const u = new URL(route.request().url());
    return u.protocol === "http:" && u.hostname === "127.0.0.1" && u.port === "5174"
      ? route.continue() : route.abort("blockedbyclient");
  });
  await page.goto(ROOT + "/clients/new");
  await page.getByLabel("שם הלקוח").fill("PKG03 synthetic planner client");
  await page.getByLabel("מספר זהות").fill("192000031");
  await page.getByRole("button", { name: "שמירת לקוח" }).click();
  await expect(page).toHaveURL(/\/clients\/\d+\/workspace/);
  const id = Number(page.url().match(/\/clients\/(\d+)\/workspace/)?.[1]);
  expect(id).toBeGreaterThan(0);

  const savedResponse = await request.post(ROOT + `/api/clients/${id}/scenario-drafts`, { data: { name: "PKG03 saved draft" } });
  expect(savedResponse.status()).toBe(200);
  const saved = await savedResponse.json();
  expect(saved.client_id).toBe(id);
  const admissionPath = `/api/clients/${id}/scenario-drafts/${encodeURIComponent(saved.scenario_id)}/calculation-admission`;
  const before = await request.get(ROOT + `/api/clients/${id}/scenario-drafts/${encodeURIComponent(saved.scenario_id)}`);
  expect(before.status()).toBe(200);
  const beforeDraft = await before.json();

  const methods: string[] = [];
  page.on("request", req => { if (req.url().includes("/calculation-admission")) methods.push(req.method()); });
  await page.goto(ROOT + `/clients/${id}/workspace?step=scenario`);
  const planning = page.getByRole("region", { name: "ראיית קבלה לחישוב" });
  await expect(planning).toContainText("blocked (חסום)");
  await expect(planning).toContainText("SCENARIO_EMPTY");
  await expect(planning).toContainText(`גרסה: ${saved.version}`);
  await planning.screenshot({ path: info.outputPath("planning-readiness.png") });
  await planning.getByRole("button", { name: /רענן ראיית קבלה/ }).click();
  await expect.poll(() => methods.length).toBeGreaterThanOrEqual(2);
  await page.goto(ROOT + `/clients/${id}/workspace?step=results`);
  const results = page.getByRole("region", { name: "ראיית קבלה לחישוב" });
  await expect(results).toContainText("blocked (חסום)");
  await expect(results).toContainText("אין תוצאה פיננסית מורשית");
  await results.screenshot({ path: info.outputPath("results-readiness.png") });
  expect(methods.length).toBeGreaterThanOrEqual(3);
  expect(methods.every(method => method === "GET")).toBe(true);

  const evidenceResponse = await request.get(ROOT + admissionPath);
  expect(evidenceResponse.status()).toBe(200);
  const evidence = await evidenceResponse.json();
  expect(evidence).toMatchObject({
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1", client_id: id,
    scenario_id: saved.scenario_id, scenario_version: saved.version,
    assessment_state: "blocked", financial_result: null,
  });
  expect(evidence.blockers.some((b: any) => b.code === "SCENARIO_EMPTY")).toBe(true);
  const after = await request.get(ROOT + `/api/clients/${id}/scenario-drafts/${encodeURIComponent(saved.scenario_id)}`);
  expect(after.status()).toBe(200);
  expect(await after.json()).toEqual(beforeDraft);

  const missing = await request.get(ROOT + `/api/clients/${id}/scenario-drafts/nonexistent-pkg03/calculation-admission`);
  expect(missing.status()).toBe(404);
  const missingClient = await request.get(ROOT + `/api/clients/${id + 999999}/scenario-drafts/${encodeURIComponent(saved.scenario_id)}/calculation-admission`);
  expect(missingClient.status()).toBe(404);
});
