/** Real localhost Chromium admission-control acceptance.
 * Uses existing synthetic Supervisor 41 seed and existing production routes.
 * Never connects to remote infrastructure or invokes tax admission/calculation.
 */
import { test, expect } from "@playwright/test";
import { writeFileSync } from "node:fs";

const CLIENT = 410041;
const A = "supervisor41-scenario-a";
const B = "supervisor41-scenario-b";
const ROOT = "http://127.0.0.1:5173";
const API = "/api/clients/" + CLIENT + "/scenario-drafts/";
const PATH = "/clients/" + CLIENT + "/workspace";

test("supervisor 65: persist and reload scenario admission controls without tax authority", async ({
  page, request,
}, testInfo) => {
  test.setTimeout(150_000);
  const evidence: Array<{ method: string; path: string; status: number }> = [];
  const failures: string[] = [];
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || url.port !== "5173") {
      return route.abort("blockedbyclient");
    }
    return route.continue();
  });
  page.on("pageerror", error => failures.push(error.message));
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.pathname.includes("fixation-professional-review")
        || url.pathname.includes("fixation-admission-preparation")) {
      evidence.push({ method: response.request().method(), path: url.pathname, status: response.status() });
    }
  });
  try {
    await page.goto(ROOT + PATH, { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const choice = page.getByRole("group", { name: "בחירת חלופה" });
    await choice.getByRole("button", { name: "חלופה סינתטית א" }).click();
    const region = page.getByRole("region", { name: "קיבוע זכויות - הכרעות מקצועיות" });
    await expect(region).toBeVisible();
    await expect(region.getByText(/לרשומה זו טרם הוגדרו בקרות Admission/)).toBeVisible();
    await expect(region.getByText(/INCOMPLETE:|BLOCKED:/)).toBeVisible();
    await region.getByRole("button", { name: "התחל הזנת בקרות חדשה" }).click();
    await region.getByLabel("מצב איסוף מענקים היסטוריים").selectOption("items_recorded");
    await region.getByLabel("אסמכתאות מענקים היסטוריים, שורה לכל אסמכתה")
      .fill("document://supervisor65/grant-collection");
    await region.getByLabel("מצב איסוף היוונים היסטוריים").selectOption("confirmed_none");
    await region.getByLabel("אסמכתאות היוונים היסטוריים, שורה לכל אסמכתה")
      .fill("document://supervisor65/no-capitalizations");
    await region.getByLabel("תחולת היוון IDF").selectOption("NOT_APPLICABLE");
    await region.getByLabel("אסמכתאות לתחולת IDF")
      .fill("document://supervisor65/idf-not-applicable");

    const putResponse = page.waitForResponse(response =>
      response.url().includes(API + A + "/fixation-professional-review")
      && response.request().method() === "PUT");
    await region.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }).click();
    const put = await putResponse;
    expect(put.status(), await put.text()).toBe(200);
    const saved = await put.json();
    expect(saved.admission_controls).toMatchObject({
      calculation_version: "pkg-012-m08d-v1",
      grants_collection: { state: "items_recorded" },
      actual_capitalizations_collection: {
        state: "confirmed_none",
        evidence_references: ["document://supervisor65/no-capitalizations"],
      },
      idf: {
        applicability: "NOT_APPLICABLE",
        evidence_references: ["document://supervisor65/idf-not-applicable"],
        input: null,
      },
    });
    expect(saved.professional_authority).toBe(false);
    expect(saved.execution_allowed).toBe(false);
    expect(saved.tax_authority_approval).toBeNull();
    await expect(region.getByText(/טיוטת ההכרעות נשמרה/)).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("01-saved-controls.png"), fullPage: true });

    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    await expect(region.getByLabel("מצב איסוף מענקים היסטוריים")).toHaveValue("items_recorded");
    await expect(region.getByLabel("מצב איסוף היוונים היסטוריים")).toHaveValue("confirmed_none");
    await expect(region.getByLabel("תחולת היוון IDF")).toHaveValue("NOT_APPLICABLE");
    await expect(region.getByLabel("אסמכתאות לתחולת IDF"))
      .toHaveValue("document://supervisor65/idf-not-applicable");
    const serverA = await request.get(ROOT + API + A + "/fixation-professional-review");
    expect(serverA.status(), await serverA.text()).toBe(200);
    expect((await serverA.json()).approval_version).toBe(1);

    await choice.getByRole("button", { name: "חלופה סינתטית ב" }).click();
    await expect(region.getByText(/לרשומה זו טרם הוגדרו בקרות Admission/)).toBeVisible();
    const serverB = await request.get(ROOT + API + B + "/fixation-professional-review");
    expect(serverB.status(), await serverB.text()).toBe(200);
    expect((await serverB.json()).admission_controls).toBeNull();
    await choice.getByRole("button", { name: "חלופה סינתטית א" }).click();
    await expect(region.getByLabel("מצב איסוף מענקים היסטוריים")).toHaveValue("items_recorded");

    const preparation = await request.get(ROOT + API + A + "/fixation-admission-preparation");
    expect(preparation.status(), await preparation.text()).toBe(200);
    const prepared = await preparation.json();
    expect(["INCOMPLETE", "BLOCKED"]).toContain(prepared.state);
    expect(prepared.professional_authority).toBe(false);
    expect(prepared.execution_allowed).toBe(false);
    expect(prepared.candidate).toBeNull();
    await expect(region.getByText(/אישור מקצועי פנימי חסום/)).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("02-isolated-scenario.png"), fullPage: true });
    expect(failures).toEqual([]);
  } finally {
    writeFileSync(testInfo.outputPath("admission-api-evidence.json"),
      JSON.stringify(evidence, null, 2), "utf8");
    writeFileSync(testInfo.outputPath("page-errors.json"),
      JSON.stringify(failures, null, 2), "utf8");
  }
});


test("supervisor 78: explicit Admission Review admitted and invalidated on scenario switch", async ({
  page, request,
}, testInfo) => {
  test.setTimeout(150_000);
  const reviewClient = 410078;
  const reviewA = "supervisor78-scenario-a";
  const reviewB = "supervisor78-scenario-b";
  const base = `/api/clients/${reviewClient}/scenario-drafts/`;
  const evidence: Array<{ method: string; path: string; status: number; state?: string }> = [];
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || url.port !== "5173") {
      return route.abort("blockedbyclient");
    }
    return route.continue();
  });
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.pathname.includes("fixation-admission-review")) {
      evidence.push({
        method: response.request().method(),
        path: url.pathname, status: response.status(),
      });
    }
  });
  try {
    // Initial state is sourced from real PostgreSQL, not a frontend fixture.
    const preparedResponse = await request.get(
      ROOT + base + reviewA + "/fixation-admission-preparation",
    );
    expect(preparedResponse.status(), await preparedResponse.text()).toBe(200);
    const prepared = await preparedResponse.json();
    expect(prepared.state).toBe("PREPARED");
    expect(prepared.professional_authority).toBe(false);
    expect(prepared.execution_allowed).toBe(false);

    const eligibilityResponse = await request.get(
      ROOT + base + reviewA + "/fixation-admission-eligibility",
    );
    expect(eligibilityResponse.status(), await eligibilityResponse.text()).toBe(200);
    const eligible = await eligibilityResponse.json();
    expect(eligible.state).toBe("ELIGIBLE_FOR_ADMISSION_REVIEW");
    expect(eligible.preparation_fingerprint).toBe(prepared.preparation_fingerprint);
    expect(eligible.professional_authority).toBe(false);
    expect(eligible.execution_allowed).toBe(false);

    await page.goto(ROOT + "/clients/" + reviewClient + "/workspace", {
      waitUntil: "domcontentloaded",
    });
    await page.getByRole("button", { name: /תכנון תרחישים/ }).click();
    const choice = page.getByRole("group", { name: "בחירת חלופה" });
    await choice.getByRole("button", { name: "חלופת קבילות א" }).click();
    const professional = page.getByRole("region", {
      name: "קיבוע זכויות - הכרעות מקצועיות",
    });
    const eligibilityRegion = professional.getByRole("region", {
      name: "כשירות לבדיקת Admission",
    });
    await expect(eligibilityRegion.getByText(/ELIGIBLE_FOR_ADMISSION_REVIEW:/)).toBeVisible();
    const reviewRegion = professional.getByRole("region", {
      name: "Admission Review - בדיקת קבילות הקלט",
    });
    const button = reviewRegion.getByRole("button", { name: "בדוק קבילות קלט" });
    await expect(button).toBeEnabled();
    expect(evidence).toEqual([]); // No implicit Admission Review GET.

    const responsePromise = page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === "GET"
        && url.pathname === base + reviewA + "/fixation-admission-review";
    });
    await button.click();
    const admissionResponse = await responsePromise;
    expect(admissionResponse.status(), await admissionResponse.text()).toBe(200);
    const url = new URL(admissionResponse.url());
    expect(url.searchParams.get("expected_preparation_fingerprint")).toBe(
      prepared.preparation_fingerprint,
    );
    expect(url.searchParams.get("expected_eligibility_fingerprint")).toBe(
      eligible.eligibility_fingerprint,
    );
    const admitted = await admissionResponse.json();
    expect(admitted.state).toBe("ADMITTED_FOR_REVIEW");
    expect(admitted.admission_contract_validated).toBe(true);
    expect(admitted.reasons).toEqual([]);
    expect(admitted.professional_authority).toBe(false);
    expect(admitted.execution_allowed).toBe(false);
    expect(admitted.tax_calculation_performed).toBe(false);
    expect(admitted.tax_authority_approval).toBeNull();
    await expect(reviewRegion.getByText(
      "הקלט עבר את בדיקת הקבילות. עדיין נדרש אישור מקצועי נפרד לפני כל חישוב.",
    )).toBeVisible();
    await expect(professional.getByText(/אישור מקצועי פנימי חסום/)).toBeVisible();
    expect(evidence).toHaveLength(1);
    evidence[0].state = admitted.state;
    await page.screenshot({
      path: testInfo.outputPath("01-supervisor78-admitted-for-review.png"), fullPage: true,
    });

    // The second scenario is deliberately unprepared. A's positive result
    // must disappear without calling Admission Review for B.
    await choice.getByRole("button", { name: "חלופת קבילות ב" }).click();
    await expect(reviewRegion.getByText(
      "הקלט עבר את בדיקת הקבילות. עדיין נדרש אישור מקצועי נפרד לפני כל חישוב.",
    )).toHaveCount(0);
    await expect(reviewRegion.getByRole("button", {
      name: "בדוק קבילות קלט",
    })).toBeDisabled();
    const bPrepResponse = await request.get(
      ROOT + base + reviewB + "/fixation-admission-preparation",
    );
    expect(bPrepResponse.status(), await bPrepResponse.text()).toBe(200);
    const bPrep = await bPrepResponse.json();
    expect(bPrep.state).not.toBe("PREPARED");
    expect(bPrep.professional_authority).toBe(false);
    expect(bPrep.execution_allowed).toBe(false);
    expect(evidence).toHaveLength(1); // Explicit click only; no GET for B.
    await page.screenshot({
      path: testInfo.outputPath("02-supervisor78-other-scenario-no-admission.png"),
      fullPage: true,
    });
    expect(pageErrors).toEqual([]);
  } finally {
    writeFileSync(testInfo.outputPath("supervisor78-api-evidence.json"),
      JSON.stringify(evidence, null, 2), "utf8");
    writeFileSync(testInfo.outputPath("supervisor78-page-errors.json"),
      JSON.stringify(pageErrors, null, 2), "utf8");
  }
});
