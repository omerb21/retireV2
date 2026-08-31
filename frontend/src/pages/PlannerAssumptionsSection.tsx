import { type FormEvent, useEffect, useState } from "react";

import {
  ApiTransportError,
  createPlannerAssumption,
  getPlannerAssumptions,
  type LifecycleStatusFilter,
  type PlannerAssumptionCreatePayload,
  type PlannerAssumptionItem,
  type PlannerAssumptionUpdatePayload,
  updatePlannerAssumption
} from "../api/clientsApi";
import { HebrewDateInput } from "../components/HebrewDateInput";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";

export type PlannerAssumptionsSectionProps = {
  clientId: number;
};

type PlannerAssumptionFormState = {
  assumption_category: string;
  title: string;
  assumption_value_text: string;
  rationale: string;
  owner: string;
  effective_start_date: string;
  effective_end_date: string;
  review_date: string;
};

const lifecycleOptions: LifecycleStatusFilter[] = ["current", "superseded", "all"];
const assumptionCategoryOptions = [
  "income",
  "expense",
  "retirement timing",
  "work intention",
  "asset value",
  "pension value",
  "other"
];
const ownerOptions = ["planner", "client stated", "other stated"];

const emptyFormState: PlannerAssumptionFormState = {
  assumption_category: "",
  title: "",
  assumption_value_text: "",
  rationale: "",
  owner: "",
  effective_start_date: "",
  effective_end_date: "",
  review_date: ""
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    if (typeof error.body === "string") {
      return error.body;
    }

    return JSON.stringify(error.body, null, 2);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "לא ניתן לטעון את הנחות המתכנן.";
}

function formStateFromAssumption(assumption: PlannerAssumptionItem): PlannerAssumptionFormState {
  return {
    assumption_category: assumption.assumption_category,
    title: assumption.title,
    assumption_value_text: assumption.assumption_value_text,
    rationale: assumption.rationale,
    owner: assumption.owner,
    effective_start_date: assumption.effective_start_date ?? "",
    effective_end_date: assumption.effective_end_date ?? "",
    review_date: assumption.review_date ?? ""
  };
}

function createPayloadFromForm(formState: PlannerAssumptionFormState): PlannerAssumptionCreatePayload {
  return {
    assumption_category: formState.assumption_category,
    title: formState.title,
    assumption_value_text: formState.assumption_value_text,
    rationale: formState.rationale,
    owner: formState.owner,
    ...(formState.effective_start_date.trim() === "" ? {} : { effective_start_date: formState.effective_start_date }),
    ...(formState.effective_end_date.trim() === "" ? {} : { effective_end_date: formState.effective_end_date }),
    ...(formState.review_date.trim() === "" ? {} : { review_date: formState.review_date })
  };
}

function updatePayloadFromForm(
  formState: PlannerAssumptionFormState,
  touchedFields: Set<keyof PlannerAssumptionFormState>
): PlannerAssumptionUpdatePayload {
  return Array.from(touchedFields).reduce<PlannerAssumptionUpdatePayload>((payload, fieldName) => ({
    ...payload,
    [fieldName]: formState[fieldName].trim() === "" ? null : formState[fieldName]
  }), {});
}

export function PlannerAssumptionsSection({ clientId }: PlannerAssumptionsSectionProps) {
  const [assumptions, setAssumptions] = useState<PlannerAssumptionItem[]>([]);
  const [lifecycleStatus, setLifecycleStatus] = useState<LifecycleStatusFilter>("current");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formState, setFormState] = useState<PlannerAssumptionFormState>(emptyFormState);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [touchedFields, setTouchedFields] = useState<Set<keyof PlannerAssumptionFormState>>(new Set());
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshAssumptions(selectedLifecycleStatus = lifecycleStatus) {
    const nextAssumptions = await getPlannerAssumptions(clientId, selectedLifecycleStatus);
    setAssumptions(nextAssumptions);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadAssumptions() {
      setIsLoading(true);

      try {
        const nextAssumptions = await getPlannerAssumptions(clientId, lifecycleStatus);
        if (!isActive) {
          return;
        }
        setAssumptions(nextAssumptions);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        setAssumptions([]);
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadAssumptions();

    return () => {
      isActive = false;
    };
  }, [clientId, lifecycleStatus]);

  function updateFormField(fieldName: keyof PlannerAssumptionFormState, value: string) {
    setFormState((current) => ({ ...current, [fieldName]: value }));
    setTouchedFields((current) => new Set(current).add(fieldName));
    setMutationErrorMessage(null);
  }

  function startEditing(assumption: PlannerAssumptionItem) {
    setEditingId(assumption.id);
    setFormState(formStateFromAssumption(assumption));
    setTouchedFields(new Set());
    setMutationErrorMessage(null);
  }

  function resetForm() {
    setEditingId(null);
    setFormState(emptyFormState);
    setTouchedFields(new Set());
    setMutationErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      if (editingId === null) {
        await createPlannerAssumption(clientId, createPayloadFromForm(formState));
      } else {
        await updatePlannerAssumption(clientId, editingId, updatePayloadFromForm(formState, touchedFields));
      }
      await refreshAssumptions();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section aria-labelledby="planner-assumptions-heading">
      <h3 id="planner-assumptions-heading">הנחות מתכנן</h3>
      <p>
        <label htmlFor="planner-assumptions-lifecycle-filter">סינון לפי מצב מחזור חיים</label>
        <select
          id="planner-assumptions-lifecycle-filter"
          value={lifecycleStatus}
          onChange={(event) => setLifecycleStatus(event.target.value as LifecycleStatusFilter)}
        >
          {lifecycleOptions.map((option) => (
            <option key={option} value={option}>
              {heLabel(option)}
            </option>
          ))}
        </select>
      </p>
      {isLoading ? (
        <p>טוען הנחות מתכנן…</p>
      ) : errorMessage !== null ? (
        <>
          <p>לא ניתן לטעון את הנחות המתכנן.</p>
          <pre>{errorMessage}</pre>
        </>
      ) : assumptions.length === 0 ? (
        <p>לא נמצאו הנחות מתכנן עבור מסנן מחזור החיים שנבחר.</p>
      ) : (
        <ul>
          {assumptions.map((assumption) => (
            <li key={assumption.id}>
              <article>
                <h4>{assumption.title}</h4>
                <p>קטגוריית הנחה: {heLabel(assumption.assumption_category)}</p>
                <p>ערך ההנחה: {assumption.assumption_value_text}</p>
                <p>נימוק: {assumption.rationale}</p>
                <p>אחראי: {heLabel(assumption.owner)}</p>
                <p>מצב מחזור חיים: {heLabel(assumption.lifecycle_status)}</p>
                {assumption.effective_start_date ? (
                  <p>תאריך תחילת תוקף: {formatIsoDate(assumption.effective_start_date)}</p>
                ) : null}
                {assumption.effective_end_date ? <p>תאריך סיום תוקף: {formatIsoDate(assumption.effective_end_date)}</p> : null}
                {assumption.review_date ? <p>תאריך בדיקה: {formatIsoDate(assumption.review_date)}</p> : null}
                <p>
                  <button type="button" onClick={() => startEditing(assumption)} disabled={isSubmitting}>
                    עריכת הנחת מתכנן
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit}>
        <h4>{editingId === null ? "הוספת הנחת מתכנן" : "עריכת הנחת מתכנן"}</h4>
        <p>
          <label htmlFor="planner-assumption-category">קטגוריית הנחה</label>
          <select
            id="planner-assumption-category"
            value={formState.assumption_category}
            onChange={(event) => updateFormField("assumption_category", event.target.value)}
          >
            <option value="">לא נבחר</option>
            {assumptionCategoryOptions.map((option) => (
              <option key={option} value={option}>
                {heLabel(option)}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="planner-assumption-title">כותרת</label>
          <input
            id="planner-assumption-title"
            value={formState.title}
            onChange={(event) => updateFormField("title", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-value">ערך ההנחה</label>
          <textarea
            id="planner-assumption-value"
            value={formState.assumption_value_text}
            onChange={(event) => updateFormField("assumption_value_text", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-rationale">נימוק</label>
          <textarea
            id="planner-assumption-rationale"
            value={formState.rationale}
            onChange={(event) => updateFormField("rationale", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-owner">אחראי</label>
          <select
            id="planner-assumption-owner"
            value={formState.owner}
            onChange={(event) => updateFormField("owner", event.target.value)}
          >
            <option value="">לא נבחר</option>
            {ownerOptions.map((option) => (
              <option key={option} value={option}>
                {heLabel(option)}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="planner-assumption-effective-start-date">תאריך תחילת תוקף</label>
          <HebrewDateInput
            id="planner-assumption-effective-start-date"
            value={formState.effective_start_date}
            onChange={(value) => updateFormField("effective_start_date", value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-effective-end-date">תאריך סיום תוקף</label>
          <HebrewDateInput
            id="planner-assumption-effective-end-date"
            value={formState.effective_end_date}
            onChange={(value) => updateFormField("effective_end_date", value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-review-date">תאריך בדיקה</label>
          <HebrewDateInput
            id="planner-assumption-review-date"
            value={formState.review_date}
            onChange={(value) => updateFormField("review_date", value)}
          />
        </p>
        {mutationErrorMessage ? (
          <>
            <p>לא ניתן לשמור את הנחת המתכנן.</p>
            <pre>{mutationErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "שומר…" : editingId === null ? "הוספת הנחת מתכנן" : "שמירת הנחת מתכנן"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              ביטול העריכה
            </button>
          ) : null}
        </p>
      </form>
    </section>
  );
}
