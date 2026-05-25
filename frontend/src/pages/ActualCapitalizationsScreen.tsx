import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  createActualCapitalization,
  type ActualCapitalizationCreatePayload,
  type ActualCapitalizationItem,
  getActualCapitalizations
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
  notes: string;
}

const emptyFormState: FormState = {
  amount: "",
  capitalizationDate: "",
  sourceLabel: "",
  notes: ""
};

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
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  async function refreshCapitalizations() {
    const nextCapitalizations = await getActualCapitalizations(parsedClientId);
    setCapitalizations(nextCapitalizations);
    setIsNotFound(false);
    setErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
      setSubmitErrorMessage("Unable to add actual capitalization for this client.");
      return;
    }

    const payload: ActualCapitalizationCreatePayload = {
      amount: Number(formState.amount),
      capitalization_date: formState.capitalizationDate,
      source_label: formState.sourceLabel.trim() === "" ? null : formState.sourceLabel,
      notes: formState.notes.trim() === "" ? null : formState.notes
    };

    setIsSubmitting(true);
    setSubmitErrorMessage(null);

    try {
      await createActualCapitalization(parsedClientId, payload);
      await refreshCapitalizations();
      setFormState(emptyFormState);
    } catch (error) {
      setSubmitErrorMessage(getErrorMessage(error));
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
      <p>Edit and delete are unavailable in this workflow.</p>
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
                {capitalization.notes ? <p>Notes: {capitalization.notes}</p> : null}
              </article>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit}>
        <h3>Add Actual Capitalization</h3>
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
            Notes
            <textarea
              value={formState.notes}
              onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>
        </p>
        {submitErrorMessage ? <p>{submitErrorMessage}</p> : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Add Actual Capitalization"}
          </button>
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
