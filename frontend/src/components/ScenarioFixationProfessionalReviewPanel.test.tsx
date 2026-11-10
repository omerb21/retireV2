import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import { ScenarioFixationProfessionalReviewPanel } from "./ScenarioFixationProfessionalReviewPanel";
import { ReviewApiError, type ProfessionalReview } from "../api/scenarioFixationProfessionalReviewApi";

const mocks = vi.hoisted(() => ({
  read: vi.fn(), save: vi.fn(), history: vi.fn(), approve: vi.fn(), preparation: vi.fn(), eligibility: vi.fn(),
}));
vi.mock("../api/scenarioFixationProfessionalReviewApi", async importOriginal => {
  const original = await importOriginal<typeof import("../api/scenarioFixationProfessionalReviewApi")>();
  return {
    ...original,
    readProfessionalReview: mocks.read,
    saveProfessionalReview: mocks.save,
    readProfessionalReviewHistory: mocks.history,
    requestProfessionalApproval: mocks.approve,
    readFixationAdmissionPreparation: mocks.preparation,
    readFixationAdmissionEligibility: mocks.eligibility,
  };
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });
beforeEach(() => {
  mocks.eligibility.mockImplementation(async (_client: number, scenario: string) => ({
    contract: "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1",
    client_id: 7, scenario_id: scenario, state: "INCOMPLETE",
    preparation_fingerprint: "f".repeat(64),
    eligibility_fingerprint: "e".repeat(64),
    reasons: [{ code: "FIXATION_PREPARATION_CONTROLS_MISSING", source_ids: [] }],
    professional_authority: false, execution_allowed: false,
    admission_review_required: false, tax_authority_approval: null,
  }));
  mocks.preparation.mockImplementation(async (_client: number, scenario: string) => ({
    contract: "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1",
    client_id: 7, scenario_id: scenario, state: "INCOMPLETE",
    candidate: null, incomplete_reasons: ["FIXATION_PREPARATION_CONTROLS_MISSING"],
    blockers: [], preparation_fingerprint: "f".repeat(64),
    professional_authority: false, execution_allowed: false, tax_authority_approval: null,
  }));
});

const draft: ScenarioDraft = {
  scenario_id: "A", client_id: 7, name: "חלופה א", status: "draft",
  version: 3, created_by: "planner", updated_by: "planner",
  decisions: [{
    decision_id: "pension-a", source_product_id: "p7", source_component_id: "c7",
    component_code: "תגמולי_עובד_עד_2000", amount: "100.00",
    action: "pension", effective_date: "2027-01-01",
    validation_state: "unverified", product_version_at_review: 1,
    source_fingerprint_at_review: "x".repeat(64),
    ruleset_digest_at_review: null, permission_preview_id_at_review: null,
  }], financial_validation: "not_evaluated",
};
const decision = {
  group: "historical_grant" as const, source_id: "grant-a",
  determination: "REQUIRES_REVIEW" as const, reason: "מעמד התשלום טרם אומת",
  evidence_references: ["document-A"], eligibility_date: null, tax_year: null,
  parameter_set_id: null, tax_classification: null,
  inclusion_decision: null, support_status: null, accepted_for_use: null,
  payment_status: null, overlap_resolution: null, matched_source_ids: [],
};
function snapshot(scenario = "A", version = 0, choices: ProfessionalReview["decisions"] = []): ProfessionalReview {
  return {
    contract: "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1",
    client_id: 7, scenario_id: scenario, approval_id: version ? "approval-a" : null,
    approval_version: version, record_status: version ? "DRAFT" : "MISSING",
    validity_state: "BLOCKED", decisions: choices,
    admission_controls: null,
    actor_id: version ? "planner" : null, approval_fingerprint: version ? "a".repeat(64) : null,
    dependency_fingerprint: version ? "b".repeat(64) : null,
    readiness_fingerprint_at_save: version ? "c".repeat(64) : null,
    current_readiness: {
      scenario_version: 3, manifest_fingerprint: "d".repeat(64),
      readiness_fingerprint: "e".repeat(64), readiness_state: "BLOCKED",
      blockers: ["FIXATION_SCENARIO_TAX_YEAR_MISSING"],
      mapping: {
        m07_input_reference: {
          source: "M07", present: false, verified: false, scenario_bound: false,
          professional_decision_required: true,
          blocker: "FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING", references: [],
        },
      },
      source_evidence: {
        m07: [], grants: [{
          grant_id: "grant-a", payment_classification: "UNKNOWN_NOT_VERIFIED",
          source_fingerprint: "f".repeat(64),
        }], severance_choice_source_ids: [],
        historical_capitalizations: [],
        pension_gross_result_fingerprint: null, official_parameter_set: null, tax_year: null,
      },
      professional_authority: false, execution_allowed: false,
    },
    blockers: ["FIXATION_SCENARIO_TAX_YEAR_MISSING", "FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED"],
    professional_authority: false, execution_allowed: false, tax_authority_approval: null,
  };
}
function display(scenario = draft) {
  return render(<ScenarioFixationProfessionalReviewPanel clientId={7} scenario={scenario} />);
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

it("loads the selected scenario, factual sources, blocked readiness and no approve button", async () => {
  mocks.read.mockResolvedValue(snapshot());
  display();
  expect(await screen.findByText(/טרם נשמרו הכרעות/)).toBeTruthy();
  expect(screen.getByText(/אישור מקצועי פנימי חסום/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: /אשר קיבוע/ })).toBeNull();
  expect(mocks.approve).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("נתוני מקור ומוכנות לחישוב"));
  expect(screen.getByText(/מענקים: 1/)).toBeTruthy();
  expect(screen.getByText(/ראיות זכאות M07: 0/)).toBeTruthy();
});

it("adds a structured grant decision and sends exact server CAS tokens", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockResolvedValue(snapshot("A", 1, [decision]));
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "historical_grant" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "grant-a" } });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), { target: { value: decision.reason } });
  fireEvent.change(screen.getByLabelText(/הפניות לאסמכתאות/), { target: { value: "document-A" } });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(7, "A", {
    expected_approval_version: 0,
    expected_scenario_version: 3,
    expected_manifest_fingerprint: "d".repeat(64),
    expected_readiness_fingerprint: "e".repeat(64),
    decisions: [decision], admission_controls: null,
  }));
  expect(await screen.findByText(/טיוטת ההכרעות נשמרה/)).toBeTruthy();
  expect(screen.getByText(/טיוטה שמורה, ללא אישור/)).toBeTruthy();
});

it("reloads persisted decisions and displays immutable version history", async () => {
  mocks.read.mockResolvedValue(snapshot("A", 2, [decision]));
  mocks.history.mockResolvedValue([{
    revision_id: "revision-1", approval_version: 1, scenario_version: 3,
    decisions: [decision], blockers: [], action: "SAVE_DRAFT",
    actor_id: "planner", occurred_at: "2026-11-09T09:00:00Z",
    professional_authority: false, tax_authority_approval: null,
  }]);
  display();
  expect(await screen.findByText(/טיוטה שמורה, ללא אישור/)).toBeTruthy();
  expect(screen.getByText(/מעמד התשלום טרם אומת/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "ערוך" }));
  expect((screen.getByLabelText(/הנמקה מקצועית/) as HTMLTextAreaElement).value).toBe(decision.reason);
  expect((screen.getByLabelText(/הפניות לאסמכתאות/) as HTMLTextAreaElement).value).toBe("document-A");
  fireEvent.click(screen.getByRole("button", { name: "הצג היסטוריית גרסאות" }));
  expect(await screen.findByText(/גרסה 1, planner/)).toBeTruthy();
  expect(mocks.approve).not.toHaveBeenCalled();
});

it("keeps unsaved decisions isolated between scenario A and B", async () => {
  mocks.read.mockImplementation(async (_client: number, id: string) => snapshot(id));
  const view = display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "historical_grant" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "grant-a" } });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), { target: { value: "טיוטה מקומית של א" } });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  expect(screen.getByText(/טיוטה מקומית של א/)).toBeTruthy();
  view.rerender(<ScenarioFixationProfessionalReviewPanel key="B" clientId={7}
    scenario={{ ...draft, scenario_id: "B", name: "חלופה ב" }}/>);
  await waitFor(() => expect(mocks.read).toHaveBeenCalledWith(7, "B"));
  await waitFor(() => expect(screen.queryByText(/טיוטה מקומית של א/)).toBeNull());
  expect(mocks.save).not.toHaveBeenCalled();
});

it("on 409 reloads CAS tokens without overwriting user draft and requires deliberate retry", async () => {
  mocks.read.mockResolvedValueOnce(snapshot()).mockResolvedValueOnce({
    ...snapshot("A", 1), current_readiness: {
      ...snapshot().current_readiness, readiness_fingerprint: "2".repeat(64),
    },
  });
  mocks.save.mockRejectedValue(new ReviewApiError(409, "FIXATION_APPROVAL_SOURCE_CONFLICT"));
  const refreshParent = vi.fn().mockResolvedValue(undefined);
  render(<ScenarioFixationProfessionalReviewPanel clientId={7} scenario={draft}
    onScenarioRefresh={refreshParent} />);
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "historical_grant" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "grant-a" } });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), { target: { value: "אל תמחק את ההכרעה" } });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  expect(await screen.findByText(/התנגשות גרסה או שינוי מקור/)).toBeTruthy();
  expect(screen.getByText(/אל תמחק את ההכרעה/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }).hasAttribute("disabled")).toBe(true);
  expect(mocks.read).toHaveBeenCalledTimes(2);
  expect(refreshParent).toHaveBeenCalledTimes(1);
  expect(mocks.save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: /בדקתי את הנתונים העדכניים/ }));
  expect(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }).hasAttribute("disabled")).toBe(false);
});

it("preserves form inputs and displays backend 422 blockers", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockRejectedValue(new ReviewApiError(422, "FIXATION_REVIEW_BLOCKED", [
    "FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING",
  ]));
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "historical_grant" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "grant-a" } });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), { target: { value: "לא אושר" } });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByText(/לא אושר/)).toBeTruthy();
  fireEvent.click(screen.getByText(/חסמים מקצועיים/));
  expect(screen.getByText(/לא אומתה זכאות לקיבוע/)).toBeTruthy();
});

it("shows stale source and blocks writes to archived scenarios", async () => {
  mocks.read.mockResolvedValue({ ...snapshot("A", 2, [decision]), validity_state: "STALE" });
  display({ ...draft, status: "archived" });
  expect(await screen.findByText(/ראיות המקור או החלופה השתנו מאז השמירה/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }).hasAttribute("disabled")).toBe(true);
  expect(mocks.approve).not.toHaveBeenCalled();
});


const admittedControls = {
  calculation_version: "pkg-012-m08d-v1" as const,
  grants_collection: { state: "confirmed_none" as const, evidence_references: ["grant-none-proof"] },
  actual_capitalizations_collection: {
    state: "items_recorded" as const, evidence_references: ["capitalization-record"],
  },
  idf: {
    applicability: "APPLICABLE" as const, evidence_references: ["idf-evidence"],
    input: {
      idf_id: "idf-1", reduction_amount: 100,
      original_commutation_percent: 25, current_commutation_percent: 20,
      commutation_date: "2025-01-01", promoter_age_date: "2026-10-01",
      source_label: "אישור היוון",
    },
  },
};

it("keeps previously saved admission controls when a different decision is edited and saved", async () => {
  mocks.read.mockResolvedValue({ ...snapshot("A", 2, [decision]), admission_controls: admittedControls });
  mocks.save.mockImplementation(async (_client: number, _scenario: string, payload: {
    admission_controls: unknown; decisions: unknown[];
  }) => ({ ...snapshot("A", 3, [decision]), admission_controls: payload.admission_controls }));
  display();
  expect(await screen.findByText(/טיוטה שמורה, ללא אישור/)).toBeTruthy();
  expect((screen.getByLabelText(/מצב איסוף מענקים היסטוריים/) as HTMLSelectElement).value).toBe("confirmed_none");
  expect((screen.getByLabelText(/תחולת היוון IDF/) as HTMLSelectElement).value).toBe("APPLICABLE");
  expect((screen.getByLabelText(/סכום הפחתה/) as HTMLInputElement).value).toBe("100");
  fireEvent.click(screen.getByRole("button", { name: "ערוך" }));
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), {
    target: { value: "הכרעה מעודכנת ללא מחיקת בקרות" },
  });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledTimes(1));
  const payload = mocks.save.mock.calls[0][2];
  expect(payload.admission_controls).toEqual(admittedControls);
  expect(payload.decisions[0].reason).toBe("הכרעה מעודכנת ללא מחיקת בקרות");
  expect(screen.getByText(/טיוטת ההכרעות נשמרה/)).toBeTruthy();
});

it("leaves legacy records without admission controls until explicitly started", async () => {
  const old = snapshot("A", 1, [decision]);
  delete (old as { admission_controls?: unknown }).admission_controls;
  mocks.read.mockResolvedValue(old);
  mocks.save.mockResolvedValue({ ...snapshot("A", 2, [decision]), admission_controls: null });
  display();
  expect(await screen.findByText(/לרשומה זו טרם הוגדרו בקרות Admission/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalled());
  expect(mocks.save.mock.calls[0][2].admission_controls).toBeNull();
  expect(screen.queryByLabelText(/מצב איסוף מענקים היסטוריים/)).toBeNull();
});

it("does not submit invalid confirmed-none evidence and keeps form data", async () => {
  mocks.read.mockResolvedValue(snapshot());
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.click(screen.getByRole("button", { name: "התחל הזנת בקרות חדשה" }));
  fireEvent.change(screen.getByLabelText(/מצב איסוף מענקים היסטוריים/), {
    target: { value: "confirmed_none" },
  });
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByText(/יש לצרף אסמכתאות להצהרה שאין מענקים/)).toBeTruthy();
  expect(mocks.save).not.toHaveBeenCalled();
  expect((screen.getByLabelText(/מצב איסוף מענקים היסטוריים/) as HTMLSelectElement).value)
    .toBe("confirmed_none");
});

it("shows all three admission preparation statuses without claiming approval", async () => {
  for (const state of ["INCOMPLETE", "BLOCKED", "PREPARED"] as const) {
    cleanup();
    mocks.read.mockResolvedValue(snapshot());
    mocks.preparation.mockResolvedValue({
      contract: "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1",
      client_id: 7, scenario_id: "A", state,
      candidate: state === "PREPARED" ? { metadata: { synthetic: true } } : null,
      incomplete_reasons: state === "INCOMPLETE" ? ["FIXATION_PREPARATION_CONTROLS_MISSING"] : [],
      blockers: state === "BLOCKED" ? ["FIXATION_PREPARATION_SOURCE_OVERLAP_UNRESOLVED"] : [],
      preparation_fingerprint: "f".repeat(64),
      professional_authority: false, execution_allowed: false, tax_authority_approval: null,
    });
    display();
    const preparationRegion = await screen.findByRole("region", {
      name: "מצב הכנת קלט Admission",
    });
    expect(await within(preparationRegion).findByText(new RegExp(state + ":"))).toBeTruthy();
    if (state === "PREPARED") {
      expect(screen.getByText(/טרם ניתן אישור מקצועי לחישוב קיבוע זכויות/)).toBeTruthy();
    }
    expect(screen.queryByRole("button", { name: /אשר קיבוע/ })).toBeNull();
  }
});

it("retains unsaved admission controls on 409 and isolates them across scenarios", async () => {
  mocks.read.mockImplementation(async (_client: number, id: string) => snapshot(id));
  mocks.save.mockRejectedValue(new ReviewApiError(409, "FIXATION_APPROVAL_SOURCE_CONFLICT"));
  const view = display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.click(screen.getByRole("button", { name: "התחל הזנת בקרות חדשה" }));
  fireEvent.change(screen.getByLabelText(/מצב איסוף מענקים היסטוריים/), {
    target: { value: "items_recorded" },
  });
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  expect(await screen.findByText(/התנגשות גרסה או שינוי מקור/)).toBeTruthy();
  expect((screen.getByLabelText(/מצב איסוף מענקים היסטוריים/) as HTMLSelectElement).value)
    .toBe("items_recorded");
  expect(mocks.save).toHaveBeenCalledTimes(1);
  view.rerender(<ScenarioFixationProfessionalReviewPanel key="B-admission" clientId={7}
    scenario={{ ...draft, scenario_id: "B", name: "חלופה ב" }}/>);
  await waitFor(() => expect(mocks.read).toHaveBeenCalledWith(7, "B"));
  await waitFor(() => expect(screen.queryByLabelText(/מצב איסוף מענקים היסטוריים/)).toBeNull());
  expect(screen.getByText(/לרשומה זו טרם הוגדרו בקרות Admission/)).toBeTruthy();
});


it("edits closed grant fields, payment status and overlap source IDs without granting authority", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockImplementation(async (_client: number, _scenario: string, body: {
    decisions: typeof decision[];
  }) => ({ ...snapshot("A", 1), decisions: body.decisions }));
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "historical_grant" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "grant-a" } });
  fireEvent.change(screen.getByLabelText(/מצב ההכרעה/), { target: { value: "PLANNER_ASSERTED" } });
  fireEvent.change(screen.getByLabelText(/הכרעת הכללה/), { target: { value: "include" } });
  fireEvent.change(screen.getByLabelText(/מצב תמיכה מקצועית/), { target: { value: "supported" } });
  fireEvent.change(screen.getByLabelText(/הכרעת שימוש בקלט/), { target: { value: "true" } });
  fireEvent.change(screen.getByLabelText(/מעמד תשלום המענק/), { target: { value: "PAID" } });
  fireEvent.change(screen.getByLabelText(/הכרעת חפיפה מוצעת/), {
    target: { value: "SAME_RIGHT_USE_GRANT" },
  });
  fireEvent.change(screen.getByLabelText(/מזהי מקורות תואמים לחפיפה/), {
    target: { value: "component-a\ncomponent-b" },
  });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), {
    target: { value: "בדיקת התאמה מקצועית עם אסמכתאות" },
  });
  fireEvent.change(screen.getByLabelText(/הפניות לאסמכתאות/), {
    target: { value: "document://grant-proof" },
  });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledTimes(1));
  const submitted = mocks.save.mock.calls[0][2].decisions[0];
  expect(submitted).toMatchObject({
    group: "historical_grant", source_id: "grant-a",
    inclusion_decision: "include", support_status: "supported",
    accepted_for_use: true, payment_status: "PAID",
    overlap_resolution: "SAME_RIGHT_USE_GRANT",
    matched_source_ids: ["component-a", "component-b"],
  });
  expect(mocks.approve).not.toHaveBeenCalled();
});

it("rejects a planner-asserted pension without a closed tax classification", async () => {
  mocks.read.mockResolvedValue(snapshot());
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.change(screen.getByLabelText(/קבוצת הכרעה/), { target: { value: "pension_classification" } });
  fireEvent.change(screen.getByLabelText(/מקור ההכרעה/), { target: { value: "pension-a" } });
  fireEvent.change(screen.getByLabelText(/מצב ההכרעה/), { target: { value: "PLANNER_ASSERTED" } });
  fireEvent.change(screen.getByLabelText(/הנמקה מקצועית/), { target: { value: "סיווג נדרש" } });
  fireEvent.click(screen.getByRole("button", { name: "הוסף או עדכן הכרעה בטיוטה" }));
  expect(await screen.findByText(/יש לבחור סיווג קצבה/)).toBeTruthy();
  expect(mocks.save).not.toHaveBeenCalled();
});

it("saves full applicable IDF values from the structured editor", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockImplementation(async (_client: number, _scenario: string, body: {
    admission_controls: unknown;
  }) => ({ ...snapshot("A", 1), admission_controls: body.admission_controls }));
  display();
  await screen.findByText(/טרם נשמרו הכרעות/);
  fireEvent.click(screen.getByRole("button", { name: "התחל הזנת בקרות חדשה" }));
  fireEvent.change(screen.getByLabelText(/תחולת היוון IDF/), { target: { value: "APPLICABLE" } });
  fireEvent.change(screen.getByLabelText(/אסמכתאות לתחולת IDF/), { target: { value: "document://idf-7" } });
  fireEvent.change(screen.getByLabelText(/מזהה נתון IDF/), { target: { value: "idf-7" } });
  fireEvent.change(screen.getByLabelText(/סכום הפחתה/), { target: { value: "120" } });
  fireEvent.change(screen.getByLabelText(/שיעור היוון מקורי/), { target: { value: "25" } });
  fireEvent.change(screen.getByLabelText(/שיעור היוון נוכחי/), { target: { value: "20" } });
  fireEvent.change(screen.getByLabelText(/מועד היוון/), { target: { value: "2024-01-01" } });
  fireEvent.change(screen.getByLabelText(/מועד בסיס גיל/), { target: { value: "2026-10-01" } });
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledTimes(1));
  expect(mocks.save.mock.calls[0][2].admission_controls.idf).toMatchObject({
    applicability: "APPLICABLE", evidence_references: ["document://idf-7"],
    input: { idf_id: "idf-7", reduction_amount: 120,
      original_commutation_percent: 25, current_commutation_percent: 20,
      commutation_date: "2024-01-01", promoter_age_date: "2026-10-01" },
  });
});


function prepareState(state: "INCOMPLETE" | "BLOCKED" | "PREPARED", scenario = "A") {
  return {
    contract: "SCENARIO_FIXATION_ADMISSION_PREPARATION_V1",
    client_id: 7, scenario_id: scenario, state,
    candidate: state === "PREPARED" ? { synthetic: true } : null,
    incomplete_reasons: state === "INCOMPLETE" ? ["FIXATION_PREPARATION_CONTROLS_MISSING"] : [],
    blockers: state === "BLOCKED" ? ["FIXATION_PREPARATION_SOURCE_OVERLAP_UNRESOLVED"] : [],
    preparation_fingerprint: "f".repeat(64),
    professional_authority: false, execution_allowed: false, tax_authority_approval: null,
  };
}
function prepForEligibility(state: string): "INCOMPLETE" | "BLOCKED" | "PREPARED" {
  return state === "INCOMPLETE" ? "INCOMPLETE" : state === "BLOCKED" ? "BLOCKED" : "PREPARED";
}
function eligibilityState(state: "INCOMPLETE" | "BLOCKED" | "REQUIRES_EXTERNAL_VALIDATION" | "ELIGIBLE_FOR_ADMISSION_REVIEW",
  scenario = "A", reasons: Array<{ code: string; source_ids: string[] }> = []) {
  return {
    contract: "SCENARIO_FIXATION_ADMISSION_ELIGIBILITY_V1",
    client_id: 7, scenario_id: scenario, state,
    preparation_fingerprint: "f".repeat(64),
    eligibility_fingerprint: "e".repeat(64),
    reasons, professional_authority: false, execution_allowed: false,
    admission_review_required: state === "ELIGIBLE_FOR_ADMISSION_REVIEW",
    tax_authority_approval: null,
  };
}

it.each([
  ["INCOMPLETE", "חסרים נתונים להכנת הקלט"],
  ["BLOCKED", "קיימים חסמים המונעים מעבר"],
  ["REQUIRES_EXTERNAL_VALIDATION", "נדרש אימות חיצוני"],
  ["ELIGIBLE_FOR_ADMISSION_REVIEW", "לא נמצאו חסמים סטטיים ידועים"],
] as const)("shows eligibility %s separately from admission preparation", async (state, description) => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.preparation.mockResolvedValue(prepareState(prepForEligibility(state)));
  mocks.eligibility.mockResolvedValue(eligibilityState(state));
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain(description));
  expect(region.textContent).toContain(state);
  expect(region.textContent).toContain("אינה אישור מקצועי");
  expect(mocks.approve).not.toHaveBeenCalled();
});

it("translates known eligibility reasons with exact source ids and keeps unknown codes visible", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.preparation.mockResolvedValue(prepareState("PREPARED"));
  mocks.eligibility.mockResolvedValue(eligibilityState("BLOCKED", "A", [
    { code: "FIXATION_ELIGIBILITY_IDF_UNSUPPORTED", source_ids: ["idf-synthetic-9"] },
    { code: "FIXATION_ELIGIBILITY_GRANT_WITHHOLDING_FILE_MISSING", source_ids: ["grant-15"] },
    { code: "FIXATION_ELIGIBILITY_FUTURE_UNKNOWN_CODE", source_ids: ["future-1"] },
  ]));
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("idf-synthetic-9"));
  expect(region.textContent).toContain("נתוני IDF עדיין אינם נתמכים");
  expect(region.textContent).toContain("חסר תיק ניכויים");
  expect(region.textContent).toContain("FIXATION_ELIGIBILITY_FUTURE_UNKNOWN_CODE");
  expect(region.textContent).toContain("future-1");
});

it("refreshes both preparation and eligibility after saving a review", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockResolvedValue(snapshot("A", 1));
  mocks.preparation.mockResolvedValueOnce(prepareState("INCOMPLETE"))
    .mockResolvedValueOnce(prepareState("PREPARED"));
  mocks.eligibility.mockResolvedValueOnce(eligibilityState("INCOMPLETE"))
    .mockResolvedValueOnce(eligibilityState("REQUIRES_EXTERNAL_VALIDATION", "A", [
      { code: "FIXATION_ELIGIBILITY_CBS_INDEXATION_REQUIRED", source_ids: ["grant-7"] },
    ]));
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("INCOMPLETE"));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(mocks.save).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(region.textContent).toContain("REQUIRES_EXTERNAL_VALIDATION"));
  expect(region.textContent).toContain("grant-7");
  expect(mocks.preparation).toHaveBeenCalledTimes(2);
  expect(mocks.eligibility).toHaveBeenCalledTimes(2);
});

it("clears previous eligibility and preserves unsaved user input after a 409 conflict", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.save.mockRejectedValue(new ReviewApiError(409, "FIXATION_APPROVAL_SOURCE_CONFLICT"));
  mocks.preparation.mockResolvedValue(prepareState("PREPARED"));
  mocks.eligibility.mockResolvedValue(eligibilityState("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  fireEvent.click(screen.getByRole("button", { name: "שמור טיוטת הכרעות מקצועיות" }));
  await waitFor(() => expect(screen.getByText(/התנגשות גרסה או שינוי מקור/)).toBeTruthy());
  expect(region.textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW");
  expect(region.textContent).toContain("הכשירות אינה מאומתת");
  expect(mocks.save).toHaveBeenCalledTimes(1);
});

it("does not show eligibility from a different preparation fingerprint or a failed GET", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.eligibility.mockResolvedValue({
    ...eligibilityState("ELIGIBLE_FOR_ADMISSION_REVIEW"),
    preparation_fingerprint: "1".repeat(64),
  });
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("הכשירות אינה מאומתת"));
  await waitFor(() => expect(region.parentElement?.textContent).toContain("אינן תואמות לאותם נתוני מקור"));
  expect(region.textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW");
});

it("isolates eligibility when switching between scenarios", async () => {
  mocks.read.mockImplementation(async (_client: number, id: string) => snapshot(id));
  mocks.preparation.mockImplementation(async (_client: number, id: string) =>
    prepareState(id === "A" ? "PREPARED" : "BLOCKED", id));
  mocks.eligibility.mockImplementation(async (_client: number, id: string) =>
    eligibilityState(id === "A" ? "ELIGIBLE_FOR_ADMISSION_REVIEW" : "BLOCKED", id));
  const view = display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  view.rerender(<ScenarioFixationProfessionalReviewPanel key="eligible-B" clientId={7}
    scenario={{ ...draft, scenario_id: "B" }} />);
  await waitFor(() => expect(mocks.eligibility).toHaveBeenCalledWith(7, "B"));
  await waitFor(() => expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).toContain("BLOCKED"));
  expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW");
});

it("rejects late positive eligibility from the previously selected scenario", async () => {
  const latePreparation = deferred<ReturnType<typeof prepareState>>();
  const lateEligibility = deferred<ReturnType<typeof eligibilityState>>();
  mocks.read.mockImplementation(async (_client: number, id: string) => snapshot(id));
  mocks.preparation.mockImplementation(async (_client: number, id: string) =>
    id === "A" ? latePreparation.promise : prepareState("BLOCKED", id));
  mocks.eligibility.mockImplementation(async (_client: number, id: string) =>
    id === "A" ? lateEligibility.promise : eligibilityState("BLOCKED", id));
  const view = display();
  await waitFor(() => expect(mocks.eligibility).toHaveBeenCalledWith(7, "A"));
  view.rerender(<ScenarioFixationProfessionalReviewPanel clientId={7}
    scenario={{ ...draft, scenario_id: "B", name: "חלופה ב" }} />);
  await waitFor(() => expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).toContain("BLOCKED"));
  latePreparation.resolve(prepareState("PREPARED", "A"));
  lateEligibility.resolve(eligibilityState("ELIGIBLE_FOR_ADMISSION_REVIEW", "A"));
  await waitFor(() => expect(mocks.eligibility).toHaveBeenCalledWith(7, "B"));
  expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).toContain("BLOCKED");
  expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW");
});


it("does not leak a positive eligibility state when changing clients", async () => {
  mocks.read.mockImplementation(async (client: number, id: string) => ({
    ...snapshot(id), client_id: client,
  }));
  mocks.preparation.mockImplementation(async (client: number, id: string) => ({
    ...prepareState(client === 7 ? "PREPARED" : "BLOCKED", id), client_id: client,
  }));
  mocks.eligibility.mockImplementation(async (client: number, id: string) => ({
    ...eligibilityState(client === 7 ? "ELIGIBLE_FOR_ADMISSION_REVIEW" : "BLOCKED", id),
    client_id: client,
  }));
  const view = display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  view.rerender(<ScenarioFixationProfessionalReviewPanel key="client-8" clientId={8}
    scenario={{ ...draft, client_id: 8 }}/>);
  await waitFor(() => expect(mocks.eligibility).toHaveBeenCalledWith(8, "A"));
  await waitFor(() => expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).toContain("BLOCKED"));
  expect(screen.getByRole("region", { name: "כשירות לבדיקת Admission" })
    .textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW");
});

it("does not retain positive eligibility after an invalid eligibility GET", async () => {
  mocks.read.mockResolvedValue(snapshot());
  mocks.preparation.mockResolvedValue(prepareState("PREPARED"));
  mocks.eligibility.mockResolvedValueOnce(eligibilityState("ELIGIBLE_FOR_ADMISSION_REVIEW"))
    .mockRejectedValueOnce(new ReviewApiError(409, "FIXATION_ELIGIBILITY_RESPONSE_INVALID"));
  display();
  const region = await screen.findByRole("region", { name: "כשירות לבדיקת Admission" });
  await waitFor(() => expect(region.textContent).toContain("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  fireEvent.click(screen.getByRole("button", { name: "רענן מצב הכנת קלט וכשירות" }));
  await waitFor(() => expect(region.textContent).not.toContain("ELIGIBLE_FOR_ADMISSION_REVIEW"));
  await waitFor(() => expect(region.textContent).toContain("הכשירות אינה מאומתת"));
  expect(mocks.eligibility).toHaveBeenCalledTimes(2);
});
