import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  createActualCapitalization,
  deleteActualCapitalization,
  type ActualCapitalizationItem,
  type ActualCapitalizationPayload,
  getActualCapitalizations,
  updateActualCapitalization
} from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load actual capitalizations.";
}

interface FormState {
  amount: string;
  capitalizationDate: string;
  sourceLabel: string;
  sourceBasis: string;
  plannerAssertion: string;
  plannerAssertionBasis: string;
  notes: string;
}

const emptyFormState: FormState = {
  amount: "",
  capitalizationDate: "",
  sourceLabel: "",
  sourceBasis: "",
  plannerAssertion: "",
  plannerAssertionBasis: "",
  notes: ""
};

function formStateFromCapitalization(capitalization: ActualCapitalizationItem): FormState {
  return {
    amount: String(capitalization.amount),
    capitalizationDate: capitalization.capitalization_date,
    sourceLabel: capitalization.source_label ?? "",
    sourceBasis: capitalization.source_basis ?? "",
    plannerAssertion: capitalization.planner_assertion ?? "",
    plannerAssertionBasis: capitalization.planner_assertion_basis ?? "",
    notes: capitalization.notes ?? ""
  };
}

function payloadFromForm(formState: FormState): ActualCapitalizationPayload {
  return {
    amount: formState.amount,
    capitalization_date: formState.capitalizationDate,
    source_label: formState.sourceLabel.trim() === "" ? null : formState.sourceLabel,
    source_basis: formState.sourceBasis.trim() === "" ? null : formState.sourceBasis,
    planner_assertion: formState.plannerAssertion.trim() === "" ? null : formState.plannerAssertion,
    planner_assertion_basis: formState.plannerAssertionBasis.trim() === "" ? null : formState.plannerAssertionBasis,
    notes: formState.notes.trim() === "" ? null : formState.notes
  };
}

export function ActualCapitalizationsScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const location = useLocation();
  const parsedClientId = Number(clientId);
  const clientName =
    typeof location.state === "object" &&
    location.state !== null &&
    "clientName" in location.state &&
    typeof location.state.clientName === "string"
      ? location.state.clientName
      : null;

  const [capitalizations, setCapitalizations] = useState<ActualCapitalizationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [formState, setFormState] = useState<FormState>(emptyFormState);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshCapitalizations() {
    const nextCapitalizations = await getActualCapitalizations(parsedClientId);
    setCapitalizations(nextCapitalizations);
    setIsNotFound(false);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadActualCapitalizations() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setCapitalizations([]);
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextCapitalizations = await getActualCapitalizations(parsedClientId);
        if (!isActive) {
          return;
        }
        setCapitalizations(nextCapitalizations);
        setIsNotFound(false);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (error instanceof ApiTransportError && error.status === 404) {
          setCapitalizations([]);
          setIsNotFound(true);
          setErrorMessage(null);
        } else {
          setCapitalizations([]);
          setIsNotFound(false);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadActualCapitalizations();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  const detailPath = Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}` : "/clients";
  const grantsPath = Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}/grants` : "/clients";
  const fixationParametersPath =
    Number.isInteger(parsedClientId) && parsedClientId > 0
      ? `/clients/${parsedClientId}/fixation/input`
      : "/fixation/input";
  const backState = clientName ? { clientName } : undefined;

  function startEditing(capitalization: ActualCapitalizationItem) {
    setEditingId(capitalization.capitalization_id);
    setFormState(formStateFromCapitalization(capitalization));
    setMutationErrorMessage(null);
  }

  function resetForm() {
    setEditingId(null);
    setFormState(emptyFormState);
    setMutationErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
      setMutationErrorMessage("Unable to save actual capitalization for this client.");
      return;
    }

    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      const payload = payloadFromForm(formState);
      if (editingId === null) {
        await createActualCapitalization(parsedClientId, payload);
      } else {
        await updateActualCapitalization(parsedClientId, editingId, payload);
      }
      await refreshCapitalizations();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(capitalization: ActualCapitalizationItem) {
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      await deleteActualCapitalization(parsedClientId, capitalization.capitalization_id);
      await refreshCapitalizations();
      if (editingId === capitalization.capitalization_id) {
        resetForm();
      }
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <section>
        <h2>Actual Capitalizations</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Loading actual capitalizations...</p>
        <p>
          <Link to={grantsPath} state={backState}>Back to grants</Link>
        </p>
        <p>
          <Link to={fixationParametersPath} state={backState}>Continue to Fixation Parameters</Link>
        </p>
        <p>
          <Link to={detailPath}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>Actual Capitalizations</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Actual capitalizations are not available yet for this client.</p>
        <p>
          <Link to={grantsPath} state={backState}>Back to grants</Link>
        </p>
        <p>
          <Link to={fixationParametersPath} state={backState}>Continue to Fixation Parameters</Link>
        </p>
        <p>
          <Link to={detailPath}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Actual Capitalizations</h2>
      <p>Client ID: {parsedClientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      {errorMessage !== null ? (
        <>
          <p>Unable to load actual capitalizations.</p>
          <p>{errorMessage}</p>
        </>
      ) : capitalizations.length === 0 ? (
        <p>No actual capitalizations found.</p>
      ) : (
        <ul>
          {capitalizations.map((capitalization) => (
            <li key={capitalization.capitalization_id}>
              <article>
                <h3>{capitalization.source_label ?? capitalization.capitalization_id}</h3>
                <p>Capitalization ID: {capitalization.capitalization_id}</p>
                <p>Amount: {capitalization.amount}</p>
                <p>Capitalization Date: {capitalization.capitalization_date}</p>
                {capitalization.source_label ? <p>Source Label: {capitalization.source_label}</p> : null}
                {capitalization.source_basis ? <p>Source Basis: {capitalization.source_basis}</p> : null}
                {capitalization.planner_assertion ? <p>Planner Assertion: {capitalization.planner_assertion}</p> : null}
                {capitalization.planner_assertion_basis ? (
                  <p>Planner Assertion Basis: {capitalization.planner_assertion_basis}</p>
                ) : null}
                {capitalization.notes ? <p>Notes: {capitalization.notes}</p> : null}
                <p>
                  <button type="button" onClick={() => startEditing(capitalization)} disabled={isSubmitting}>
                    Edit Actual Capitalization
                  </button>
                  <button type="button" onClick={() => void handleDelete(capitalization)} disabled={isSubmitting}>
                    Delete Actual Capitalization
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit}>
        <h3>{editingId === null ? "Add Actual Capitalization" : "Edit Actual Capitalization"}</h3>
        <p>
          <label>
            Amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={formState.amount}
              onChange={(event) => setFormState((current) => ({ ...current, amount: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Capitalization Date
            <input
              type="date"
              value={formState.capitalizationDate}
              onChange={(event) =>
                setFormState((current) => ({ ...current, capitalizationDate: event.target.value }))
              }
              required
            />
          </label>
        </p>
        <p>
          <label>
            Source Label
            <input
              type="text"
              value={formState.sourceLabel}
              onChange={(event) => setFormState((current) => ({ ...current, sourceLabel: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Source Basis
            <input
              type="text"
              value={formState.sourceBasis}
              onChange={(event) => setFormState((current) => ({ ...current, sourceBasis: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Planner Assertion
            <input
              type="text"
              value={formState.plannerAssertion}
              onChange={(event) => setFormState((current) => ({ ...current, plannerAssertion: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Planner Assertion Basis
            <textarea
              value={formState.plannerAssertionBasis}
              onChange={(event) => (
                setFormState((current) => ({ ...current, plannerAssertionBasis: event.target.value }))
              )}
            />
          </label>
        </p>
        <p>
          <label>
            Notes
            <textarea
              value={formState.notes}
              onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>
        </p>
        {mutationErrorMessage ? <p>{mutationErrorMessage}</p> : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting
              ? "Saving..."
              : editingId === null
                ? "Add Actual Capitalization"
                : "Save Actual Capitalization"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              Cancel Edit
            </button>
          ) : null}
        </p>
      </form>

      <p>
        <Link to={grantsPath} state={backState}>Back to grants</Link>
      </p>
      <p>
        <Link to={fixationParametersPath} state={backState}>Continue to Fixation Parameters</Link>
      </p>
      <p>
        <Link to={detailPath}>Back to client detail</Link>
      </p>
    </section>
  );
}
