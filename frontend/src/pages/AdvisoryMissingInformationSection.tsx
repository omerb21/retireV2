import { type FormEvent, useEffect, useState } from "react";

import {
  ApiTransportError,
  createAdvisoryMissingInformation,
  getMissingDataItems,
  type AdvisoryMissingInformationCreatePayload,
  type AdvisoryMissingInformationUpdatePayload,
  type MissingDataItem,
  updateAdvisoryMissingInformation
} from "../api/clientsApi";

export type AdvisoryMissingInformationSectionProps = {
  clientId: number;
};

type AdvisoryFormState = {
  planning_domain: string;
  advisory_status: string;
  neutral_reason: string;
};

const planningDomainOptions = [
  "pension holdings",
  "capital assets",
  "recurring income",
  "recurring expenses",
  "retirement timing",
  "work intention",
  "planner assumptions",
  "other"
];
const advisoryStatusOptions = ["open", "resolved", "no longer relevant"];

const emptyFormState: AdvisoryFormState = {
  planning_domain: "",
  advisory_status: "open",
  neutral_reason: ""
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

  return "Unable to load advisory missing information.";
}

function formStateFromItem(item: MissingDataItem): AdvisoryFormState {
  return {
    planning_domain: item.planning_domain ?? "",
    advisory_status: item.advisory_status ?? "open",
    neutral_reason: item.neutral_reason ?? ""
  };
}

function createPayloadFromForm(formState: AdvisoryFormState): AdvisoryMissingInformationCreatePayload {
  return {
    missing_item_type: "data",
    missing_item_label: `Advisory missing information - ${formState.planning_domain || "not recorded"}`,
    missing_status: "missing",
    notes: null,
    planning_domain: formState.planning_domain,
    advisory_status: "open",
    ...(formState.neutral_reason.trim() === "" ? {} : { neutral_reason: formState.neutral_reason })
  };
}

function updatePayloadFromForm(
  formState: AdvisoryFormState,
  touchedFields: Set<keyof AdvisoryFormState>
): AdvisoryMissingInformationUpdatePayload {
  return Array.from(touchedFields).reduce<AdvisoryMissingInformationUpdatePayload>((payload, fieldName) => ({
    ...payload,
    [fieldName]: formState[fieldName].trim() === "" ? null : formState[fieldName]
  }), {});
}

export function AdvisoryMissingInformationSection({ clientId }: AdvisoryMissingInformationSectionProps) {
  const [items, setItems] = useState<MissingDataItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formState, setFormState] = useState<AdvisoryFormState>(emptyFormState);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [touchedFields, setTouchedFields] = useState<Set<keyof AdvisoryFormState>>(new Set());
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshItems() {
    const nextItems = await getMissingDataItems(clientId);
    setItems(nextItems);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadItems() {
      setIsLoading(true);

      try {
        const nextItems = await getMissingDataItems(clientId);
        if (!isActive) {
          return;
        }
        setItems(nextItems);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        setItems([]);
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadItems();

    return () => {
      isActive = false;
    };
  }, [clientId]);

  function updateFormField(fieldName: keyof AdvisoryFormState, value: string) {
    setFormState((current) => ({ ...current, [fieldName]: value }));
    setTouchedFields((current) => new Set(current).add(fieldName));
    setMutationErrorMessage(null);
  }

  function startEditing(item: MissingDataItem) {
    setEditingId(item.missing_data_item_id);
    setFormState(formStateFromItem(item));
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
        await createAdvisoryMissingInformation(clientId, createPayloadFromForm(formState));
      } else {
        await updateAdvisoryMissingInformation(clientId, editingId, updatePayloadFromForm(formState, touchedFields));
      }
      await refreshItems();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section aria-labelledby="advisory-missing-information-heading">
      <h3 id="advisory-missing-information-heading">Advisory Missing Information</h3>
      {isLoading ? (
        <p>Loading advisory missing information...</p>
      ) : errorMessage !== null ? (
        <>
          <p>Unable to load advisory missing information.</p>
          <pre>{errorMessage}</pre>
        </>
      ) : items.length === 0 ? (
        <p>No advisory missing information found.</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.missing_data_item_id}>
              <article>
                <h4>Advisory Missing Information Record {item.missing_data_item_id}</h4>
                <p>Planning Domain: {item.planning_domain ?? "Not recorded"}</p>
                <p>Advisory Status: {item.advisory_status ?? "Not recorded"}</p>
                <p>Neutral Reason: {item.neutral_reason ?? "Not recorded"}</p>
                <p>
                  <button type="button" onClick={() => startEditing(item)} disabled={isSubmitting}>
                    Edit Advisory Missing Information
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit}>
        <h4>{editingId === null ? "Add Advisory Missing Information" : "Edit Advisory Missing Information"}</h4>
        <p>
          <label htmlFor="advisory-planning-domain">Planning Domain</label>
          <select
            id="advisory-planning-domain"
            value={formState.planning_domain}
            onChange={(event) => updateFormField("planning_domain", event.target.value)}
          >
            <option value="">Not selected</option>
            {planningDomainOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="advisory-status">Advisory Status</label>
          <select
            id="advisory-status"
            value={editingId === null ? "open" : formState.advisory_status}
            onChange={(event) => updateFormField("advisory_status", event.target.value)}
            disabled={editingId === null}
          >
            {advisoryStatusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </p>
        <p>
          <label htmlFor="advisory-neutral-reason">Neutral Reason</label>
          <textarea
            id="advisory-neutral-reason"
            value={formState.neutral_reason}
            onChange={(event) => updateFormField("neutral_reason", event.target.value)}
          />
        </p>
        {mutationErrorMessage ? (
          <>
            <p>Unable to save advisory missing information.</p>
            <pre>{mutationErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting
              ? "Saving..."
              : editingId === null
                ? "Add Advisory Missing Information"
                : "Save Advisory Missing Information"}
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
