import { test, expect } from "@playwright/test";

/** Synthetic localhost data; only admission GETs are intercepted. */
const ROOT = "http://127.0.0.1:5174";

test("PKG03 controlled 404, 409, network abort, stale source and blocked result", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.goto(`${ROOT}/clients/new`);
  await page.getByLabel("שם הלקוח").fill("PKG03 controlled HTTP 284");
  await page.getByLabel("מספר זהות").fill("192000085");
  await page.getByRole("button", { name: "שמירת לקוח" }).click();
  await expect(page).toHaveURL(/\/clients\/\d+\/workspace/);
  const client = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
  const created = await request.post(`${ROOT}/api/clients/${client}/scenario-drafts`, {
    data: { name: "PKG03 HTTP scenario" },
  });
  expect(created.status()).toBe(200);
  const draft = await created.json();
  const path = `/api/clients/${client}/scenario-drafts/${encodeURIComponent(draft.scenario_id)}/calculation-admission`;
  await page.goto(`${ROOT}/clients/${client}/workspace?step=results`);
  const panel = page.getByRole("region", { name: "ראיית קבלה לחישוב" });
  await expect(panel).toContainText("blocked (חסום)");

  for (const status of [404, 409]) {
    await page.route(`**${path}`, route => route.fulfill({ status, json: { code: `INJECTED_${status}` } }));
    await panel.getByRole("button", { name: /רענן ראיית קבלה/ }).click();
    await expect(panel).toContainText(`ADMISSION_HTTP_${status}`);
    await expect(panel).toContainText("אין אישור לחישוב");
    await page.unroute(`**${path}`);
  }

  await page.route(`**${path}`, route => route.abort("failed"));
  await panel.getByRole("button", { name: /רענן ראיית קבלה/ }).click();
  await expect(panel).toContainText("מצב הקבלה אינו ידוע");
  await expect(panel).toContainText("אין אישור לחישוב");
  await page.unroute(`**${path}`);

  await page.route(`**${path}`, route => route.fulfill({ json: {
    schema_version: "SCENARIO_CALCULATION_ADMISSION_V1",
    client_id: client, scenario_id: draft.scenario_id,
    scenario_version: draft.version, assessment_state: "blocked",
    financial_result: null, blockers: [{ code: "SOURCE_STALE", decision_id: null }],
  } }));
  await panel.getByRole("button", { name: /רענן ראיית קבלה/ }).click();
  await expect(panel).toContainText("SOURCE_STALE");
  await expect(panel).toContainText("מקור התיישן");
  await expect(panel).toContainText("אין תוצאה פיננסית מורשית");
});

test("PKG03 delayed response from client A never populates client B", async ({ page, request }) => {
  test.setTimeout(120_000);
  const ids: number[] = [];
  const drafts: Array<{ scenario_id: string; version: number }> = [];
  for (const [index, number] of ["192000086", "192000087"].entries()) {
    await page.goto(`${ROOT}/clients/new`);
    await page.getByLabel("שם הלקוח").fill(`PKG03 284 case ${index}`);
    await page.getByLabel("מספר זהות").fill(number);
    await page.getByRole("button", { name: "שמירת לקוח" }).click();
    await expect(page).toHaveURL(/\/clients\/\d+\/workspace/);
    const id = Number(new URL(page.url()).pathname.match(/\/clients\/(\d+)\/workspace/)?.[1]);
    ids.push(id);
    const response = await request.post(`${ROOT}/api/clients/${id}/scenario-drafts`, { data: { name: `scenario ${index}` } });
    expect(response.status()).toBe(200);
    drafts.push(await response.json());
  }
  const pathA = `/api/clients/${ids[0]}/scenario-drafts/${encodeURIComponent(drafts[0].scenario_id)}/calculation-admission`;
  let release!: () => void;
  const wait = new Promise<void>(resolve => { release = resolve; });
  let requested!: () => void;
  const seen = new Promise<void>(resolve => { requested = resolve; });
  await page.route(`**${pathA}`, async route => {
    requested();
    await wait;
    await route.fulfill({ json: {
      schema_version: "SCENARIO_CALCULATION_ADMISSION_V1",
      client_id: ids[0], scenario_id: drafts[0].scenario_id,
      scenario_version: drafts[0].version, assessment_state: "blocked",
      financial_result: null, blockers: [{ code: "SOURCE_STALE", decision_id: null }],
    }}).catch(() => undefined);
  });
  try {
    await page.goto(`${ROOT}/clients/${ids[0]}/workspace?step=results`);
    await seen;
    await page.getByRole("link", { name: "החלפת לקוח" }).click();
    await page.getByRole("link", { name: `PKG03 284 case 1`, exact: true }).first().click();
    await page.getByRole("button", { name: /5\. תוצאות והשוואה/ }).click();
    const panel = page.getByRole("region", { name: "ראיית קבלה לחישוב" });
    await expect(panel).toContainText("scenario 1");
    release();
    await expect(panel).toContainText("SCENARIO_EMPTY");
    await expect(panel).not.toContainText("SOURCE_STALE");
    await expect(panel).toContainText("אין תוצאה פיננסית מורשית");
  } finally {
    release();
  }
});
