import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ScenarioDraft } from "../api/scenarioDraftsApi";
import { ScenarioFixationProfessionalReviewPanel } from "./ScenarioFixationProfessionalReviewPanel";
import { ReviewApiError, type ProfessionalReview } from "../api/scenarioFixationProfessionalReviewApi";

const mocks = vi.hoisted(() => ({
  read: vi.fn(), save: vi.fn(), history: vi.fn(), approve: vi.fn(),
}));
vi.mock("../api/scenarioFixationProfessionalReviewApi", async importOriginal => {
  const original = await importOriginal<typeof import("../api/scenarioFixationProfessionalReviewApi")>();
  return {
    ...original,
    readProfessionalReview: mocks.read,
    saveProfessionalReview: mocks.save,
    readProfessionalReviewHistory: mocks.history,
    requestProfessionalApproval: mocks.approve,
  };
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

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
};
function snapshot(scenario = "A", version = 0, choices: ProfessionalReview["decisions"] = []): ProfessionalReview {
  return {
    contract: "SCENARIO_FIXATION_PROFESSIONAL_APPROVAL_V1",
    client_id: 7, scenario_id: scenario, approval_id: version ? "approval-a" : null,
    approval_version: version, record_status: version ? "DRAFT" : "MISSING",
    validity_state: "BLOCKED", decisions: choices,
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
    decisions: [decision],
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
