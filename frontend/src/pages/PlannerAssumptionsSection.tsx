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

  return "Unable to load planner assumptions.";
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
      <h3 id="planner-assumptions-heading">Planner Assumptions</h3>
      <p>
        <label htmlFor="planner-assumptions-lifecycle-filter">Lifecycle Filter</label>
        <select
          id="planner-assumptions-lifecycle-filter"
          value={lifecycleStatus}
          onChange={(event) => setLifecycleStatus(event.target.value as LifecycleStatusFilter)}
        >
          {lifecycleOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </p>
      {isLoading ? (
        <p>Loading planner assumptions...</p>
      ) : errorMessage !== null ? (
        <>
          <p>Unable to load planner assumptions.</p>
          <pre>{errorMessage}</pre>
        </>
      ) : assumptions.length === 0 ? (
        <p>No planner assumptions found for the selected lifecycle filter.</p>
      ) : (
        <ul>
          {assumptions.map((assumption) => (
            <li key={assumption.id}>
              <article>
                <h4>{assumption.title}</h4>
                <p>Assumption Category: {assumption.assumption_category}</p>
                <p>Assumption Value: {assumption.assumption_value_text}</p>
                <p>Rationale: {assumption.rationale}</p>
                <p>Owner: {assumption.owner}</p>
                <p>Lifecycle Status: {assumption.lifecycle_status}</p>
                {assumption.effective_start_date ? (
                  <p>Effective Start Date: {assumption.effective_start_date}</p>
                ) : null}
                {assumption.effective_end_date ? <p>Effective End Date: {assumption.effective_end_date}</p> : null}
                {assumption.review_date ? <p>Review Date: {assumption.review_date}</p> : null}
                <p>
                  <button type="button" onClick={() => startEditing(assumption)} disabled={isSubmitting}>
                    Edit Planner Assumption
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit}>
        <h4>{editingId === null ? "Add Planner Assumption" : "Edit Planner Assumption"}</h4>
        <p>
          <label htmlFor="planner-assumption-category">Assumption Category</label>
          <select
            id="planner-assumption-category"
            value={formState.assumption_category}
            onChange={(event) => updateFormField("assumption_category", event.target.value)}
          >
            <option value="">Not selected</option>
            {assumptionCategoryOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="planner-assumption-title">Title</label>
          <input
            id="planner-assumption-title"
            value={formState.title}
            onChange={(event) => updateFormField("title", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-value">Assumption Value</label>
          <textarea
            id="planner-assumption-value"
            value={formState.assumption_value_text}
            onChange={(event) => updateFormField("assumption_value_text", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-rationale">Rationale</label>
          <textarea
            id="planner-assumption-rationale"
            value={formState.rationale}
            onChange={(event) => updateFormField("rationale", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-owner">Owner</label>
          <select
            id="planner-assumption-owner"
            value={formState.owner}
            onChange={(event) => updateFormField("owner", event.target.value)}
          >
            <option value="">Not selected</option>
            {ownerOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="planner-assumption-effective-start-date">Effective Start Date</label>
          <input
            id="planner-assumption-effective-start-date"
            type="date"
            value={formState.effective_start_date}
            onChange={(event) => updateFormField("effective_start_date", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-effective-end-date">Effective End Date</label>
          <input
            id="planner-assumption-effective-end-date"
            type="date"
            value={formState.effective_end_date}
            onChange={(event) => updateFormField("effective_end_date", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="planner-assumption-review-date">Review Date</label>
          <input
            id="planner-assumption-review-date"
            type="date"
            value={formState.review_date}
            onChange={(event) => updateFormField("review_date", event.target.value)}
          />
        </p>
        {mutationErrorMessage ? (
          <>
            <p>Unable to save planner assumption.</p>
            <pre>{mutationErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : editingId === null ? "Add Planner Assumption" : "Save Planner Assumption"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              Cancel Edit
            </button>
          ) : null}
        </p>
      </form>
    </section>
  );
}
