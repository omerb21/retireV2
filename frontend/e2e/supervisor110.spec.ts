/** Supervisor 110: real synthetic localhost Chromium acceptance of internal approval.
 * Production routes + disposable PG16 seed. Approval requires explicit UI click.
 */
import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";

const ROOT = "http://127.0.0.1:5174";
const CLIENT = 410078;
const A = "supervisor78-scenario-a";
const B = "supervisor78-scenario-b";
const BASE = `/api/clients/${CLIENT}/scenario-drafts/`;
const REASON = "Synthetic planner reviewed verified M07 eligibility, source classifications and official parameters.";
const REFERENCE = "document://supervisor78/eligibility";

test("supervisor 110: explicit A approval, immutable history, B isolation, reload and late API response", async ({ page, request }, info) => {
  test.setTimeout(180_000);
  const events: Array<{ path: string; method: string; status: number }> = [];
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/*", route => {
    const u = new URL(route.request().url());
    return u.protocol === "http:" && u.hostname === "127.0.0.1" && u.port === "5174"
      ? route.continue() : route.abort("blockedbyclient");
  });
  page.on("response", response => {
    const u = new URL(response.url());
    if (u.pathname.includes("fixation-")) {
      events.push({ path: u.pathname, method: response.request().method(), status: response.status() });
    }
  });
  const get = async (id: string) => {
    const r = await request.get(ROOT + BASE + id + "/fixation-professional-review");
    expect(r.status(), await r.text()).toBe(200);
    return r.json();
  };
  try {
    const before = await get(A);
    expect(before.record_status).toBe("DRAFT");
    expect(before.execution_allowed).toBe(false);
    const bBefore = await get(B);
    expect(bBefore.decision_state).not.toBe("APPROVED_INTERNAL");

    await page.goto(ROOT + `/clients/${CLIENT}/workspace`, { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const choice = page.getByRole("group", { name: "בחירת חלופה" });
    await choice.getByRole("button", { name: "חלופת קבילות א" }).click();
    const panel = page.getByRole("region", { name: "קיבוע זכויות - הכרעות מקצועיות" });
    const decision = panel.getByRole("region", { name: "החלטת אישור מקצועית פנימית" });
    const review = panel.getByRole("region", { name: "Admission Review - בדיקת קבילות הקלט" });
    await expect(review.getByRole("button", { name: "בדוק קבילות קלט" })).toBeEnabled();
    await expect(decision.getByRole("button", { name: /אשר מקצועית את החלופה/ })).toBeDisabled();

    const admission = page.waitForResponse(r =>
      r.request().method() === "GET" && new URL(r.url()).pathname === BASE + A + "/fixation-admission-review");
    await review.getByRole("button", { name: "בדוק קבילות קלט" }).click();
    const admittedResponse = await admission;
    expect(admittedResponse.status(), await admittedResponse.text()).toBe(200);
    expect((await admittedResponse.json()).state).toBe("ADMITTED_FOR_REVIEW");

    await decision.getByLabel(/נימוק החלטה מקצועית/).fill(REASON);
    await decision.getByLabel(/אסמכתת מקור מאומתת שנבדקה/).selectOption(REFERENCE);
    const attestation = decision.getByRole("group", { name: /הצהרות המתכנן הנדרשות/ });
    const boxes = attestation.getByRole("checkbox");
    await expect(boxes).toHaveCount(6);
    for (let i = 0; i < 6; i++) await boxes.nth(i).check();
    const approve = decision.getByRole("button", { name: /אשר מקצועית את החלופה/ });
    await expect(approve).toBeEnabled();
    const approvalResponse = page.waitForResponse(r =>
      r.request().method() === "POST" && new URL(r.url()).pathname === BASE + A + "/fixation-professional-review/approve");
    await approve.click();
    const posted = await approvalResponse;
    expect(posted.status(), await posted.text()).toBe(200);
    const result = await posted.json();
    expect(result.approval_attempt_state).toBe("APPROVED_INTERNAL");
    expect(result.execution_allowed).toBe(false);
    expect(result.professional_authority).toBe(false);
    expect(result.tax_authority_approval).toBeNull();
    expect(result.authority_scope).toBe("FIXATION_INTERNAL_REVIEW_ONLY");

    const approved = await get(A);
    expect(approved.decision_state).toBe("APPROVED_INTERNAL");
    expect(approved.validity_state).toBe("CURRENT");
    expect(approved.internal_decision.decision_reason).toBe(REASON);
    expect(approved.internal_decision.review_reference).toBe(REFERENCE);
    expect(approved.actor_id).toBe("supervisor65-synthetic-planner");
    expect(approved.execution_allowed).toBe(false);
    await expect(decision.getByText(/APPROVED_INTERNAL/)).toBeVisible();
    await expect(decision.getByText(/CURRENT/)).toBeVisible();
    await expect(decision.getByText(REASON, { exact: false })).toBeVisible();
    await expect(decision.getByText(REFERENCE, { exact: false })).toBeVisible();
    await page.screenshot({ path: info.outputPath("01-approved-a.png"), fullPage: true });

    await panel.getByRole("button", { name: "הצג היסטוריית גרסאות" }).click();
    await expect(panel.getByText(/supervisor65-synthetic-planner/)).toBeVisible();
    await choice.getByRole("button", { name: "חלופת קבילות ב" }).click();
    await expect(decision.getByText(/APPROVED_INTERNAL/)).toHaveCount(0);
    await expect(decision.getByRole("button", { name: /אשר מקצועית את החלופה/ })).toBeDisabled();
    expect((await get(B)).decision_state).not.toBe("APPROVED_INTERNAL");
    await page.screenshot({ path: info.outputPath("02-isolated-b.png"), fullPage: true });

    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const reloadedChoice = page.getByRole("group", { name: "בחירת חלופה" });
    await reloadedChoice.getByRole("button", { name: "חלופת קבילות א" }).click();
    const reloadedPanel = page.getByRole("region", { name: "קיבוע זכויות - הכרעות מקצועיות" });
    await expect(reloadedPanel.getByText(/אישור מקצועי פנימי בתוקף/)).toBeVisible();
    await expect(reloadedPanel.getByText(/חישובי מס ממשיכים להיות חסומים/)).toBeVisible();

    // Delay one genuine API reply for A. Switch to B before releasing it.
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    let intercepted!: () => void;
    const seen = new Promise<void>(resolve => { intercepted = resolve; });
    let once = false;
    await page.route(`**${BASE}${A}/fixation-professional-review`, async route => {
      if (once || route.request().method() !== "GET") return route.continue();
      once = true;
      const response = await route.fetch();
      intercepted();
      await gate;
      await route.fulfill({ response });
    });
    await reloadedChoice.getByRole("button", { name: "חלופת קבילות ב" }).click();
    await reloadedChoice.getByRole("button", { name: "חלופת קבילות א" }).click();
    await seen;
    await reloadedChoice.getByRole("button", { name: "חלופת קבילות ב" }).click();
    release();
    await expect(reloadedPanel.getByText(/אישור מקצועי פנימי בתוקף/)).toHaveCount(0);
    expect((await get(B)).internal_professional_authority).toBe(false);
    expect(errors).toEqual([]);
  } finally {
    writeFileSync(info.outputPath("api-evidence.json"), JSON.stringify(events, null, 2));
    writeFileSync(info.outputPath("page-errors.json"), JSON.stringify(errors, null, 2));
  }
});
