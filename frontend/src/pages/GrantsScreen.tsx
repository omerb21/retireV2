import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  createGrant,
  deleteGrant,
  type GrantItem,
  type GrantPayload,
  getGrants,
  updateGrant
} from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load grants.";
}

interface FormState {
  employmentRecordId: string;
  employerName: string;
  nominalAmount: string;
  indexedAmount: string;
  grantDate: string;
  workStartDate: string;
  workEndDate: string;
  notes: string;
}

const emptyFormState: FormState = {
  employmentRecordId: "",
  employerName: "",
  nominalAmount: "",
  indexedAmount: "",
  grantDate: "",
  workStartDate: "",
  workEndDate: "",
  notes: ""
};

function formStateFromGrant(grant: GrantItem): FormState {
  return {
    employmentRecordId: grant.employment_record_id ?? "",
    employerName: grant.employer_name ?? "",
    nominalAmount: grant.nominal_amount === null ? "" : String(grant.nominal_amount),
    indexedAmount: String(grant.indexed_amount),
    grantDate: grant.grant_date,
    workStartDate: grant.work_start_date,
    workEndDate: grant.work_end_date,
    notes: grant.notes ?? ""
  };
}

function payloadFromForm(formState: FormState): GrantPayload {
  return {
    employment_record_id: formState.employmentRecordId.trim() === "" ? null : formState.employmentRecordId,
    employer_name: formState.employerName.trim() === "" ? null : formState.employerName,
    nominal_amount: formState.nominalAmount.trim() === "" ? null : formState.nominalAmount,
    indexed_amount: formState.indexedAmount,
    grant_date: formState.grantDate,
    work_start_date: formState.workStartDate,
    work_end_date: formState.workEndDate,
    notes: formState.notes.trim() === "" ? null : formState.notes
  };
}

export function GrantsScreen() {
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
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [formState, setFormState] = useState<FormState>(emptyFormState);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshGrants() {
    const nextGrants = await getGrants(parsedClientId);
    setGrants(nextGrants);
    setIsNotFound(false);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadGrants() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextGrants = await getGrants(parsedClientId);
        if (!isActive) {
          return;
        }
        setGrants(nextGrants);
        setIsNotFound(false);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (error instanceof ApiTransportError && error.status === 404) {
          setGrants([]);
          setIsNotFound(true);
          setErrorMessage(null);
        } else {
          setGrants([]);
          setIsNotFound(false);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadGrants();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  const detailPath = Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}` : "/clients";
  const employmentHistoryPath =
    Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}/employment-history` : "/clients";
  const actualCapitalizationsPath =
    Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}/actual-capitalizations` : "/clients";
  const backState = clientName ? { clientName } : undefined;

  function startEditing(grant: GrantItem) {
    setEditingId(grant.grant_id);
    setFormState(formStateFromGrant(grant));
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
      setMutationErrorMessage("Unable to save grant for this client.");
      return;
    }

    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      const payload = payloadFromForm(formState);
      if (editingId === null) {
        await createGrant(parsedClientId, payload);
      } else {
        await updateGrant(parsedClientId, editingId, payload);
      }
      await refreshGrants();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(grant: GrantItem) {
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      await deleteGrant(parsedClientId, grant.grant_id);
      await refreshGrants();
      if (editingId === grant.grant_id) {
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
        <h2>Grants</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Loading grants...</p>
        <p>
          <Link to={employmentHistoryPath} state={backState}>Back to employment history</Link>
        </p>
        <p>
          <Link to={actualCapitalizationsPath} state={backState}>Continue to Actual Capitalizations</Link>
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
        <h2>Grants</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Grants are not available yet for this client.</p>
        <p>
          <Link to={employmentHistoryPath} state={backState}>Back to employment history</Link>
        </p>
        <p>
          <Link to={actualCapitalizationsPath} state={backState}>Continue to Actual Capitalizations</Link>
        </p>
        <p>
          <Link to={detailPath}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Grants</h2>
      <p>Client ID: {parsedClientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      {errorMessage !== null ? (
        <>
          <p>Unable to load grants.</p>
          <p>{errorMessage}</p>
        </>
      ) : grants.length === 0 ? (
        <p>No grants found.</p>
      ) : (
        <ul>
          {grants.map((grant) => (
            <li key={grant.grant_id}>
              <article>
                <h3>{grant.employer_name ?? "Grant"}</h3>
                <p>Grant ID: {grant.grant_id}</p>
                {grant.employment_record_id ? <p>Employment Record ID: {grant.employment_record_id}</p> : null}
                {grant.employer_name ? <p>Employer Name: {grant.employer_name}</p> : null}
                {grant.nominal_amount !== null ? <p>Nominal Amount: {grant.nominal_amount}</p> : null}
                <p>Indexed Amount: {grant.indexed_amount}</p>
                <p>Grant Date: {grant.grant_date}</p>
                <p>Work Start Date: {grant.work_start_date}</p>
                <p>Work End Date: {grant.work_end_date}</p>
                {grant.notes ? <p>Notes: {grant.notes}</p> : null}
                <p>
                  <button type="button" onClick={() => startEditing(grant)} disabled={isSubmitting}>
                    Edit Grant
                  </button>
                  <button type="button" onClick={() => void handleDelete(grant)} disabled={isSubmitting}>
                    Delete Grant
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit}>
        <h3>{editingId === null ? "Add Grant" : "Edit Grant"}</h3>
        <p>
          <label>
            Employment Record ID
            <input
              type="text"
              value={formState.employmentRecordId}
              onChange={(event) => setFormState((current) => ({ ...current, employmentRecordId: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Employer Name
            <input
              type="text"
              value={formState.employerName}
              onChange={(event) => setFormState((current) => ({ ...current, employerName: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Nominal Amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={formState.nominalAmount}
              onChange={(event) => setFormState((current) => ({ ...current, nominalAmount: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label>
            Indexed Amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={formState.indexedAmount}
              onChange={(event) => setFormState((current) => ({ ...current, indexedAmount: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Grant Date
            <input
              type="date"
              value={formState.grantDate}
              onChange={(event) => setFormState((current) => ({ ...current, grantDate: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Work Start Date
            <input
              type="date"
              value={formState.workStartDate}
              onChange={(event) => setFormState((current) => ({ ...current, workStartDate: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Work End Date
            <input
              type="date"
              value={formState.workEndDate}
              onChange={(event) => setFormState((current) => ({ ...current, workEndDate: event.target.value }))}
              required
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
            {isSubmitting ? "Saving..." : editingId === null ? "Add Grant" : "Save Grant"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              Cancel Edit
            </button>
          ) : null}
        </p>
      </form>

      <p>
        <Link to={employmentHistoryPath} state={backState}>Back to employment history</Link>
      </p>
      <p>
        <Link to={actualCapitalizationsPath} state={backState}>Continue to Actual Capitalizations</Link>
      </p>
      <p>
        <Link to={detailPath}>Back to client detail</Link>
      </p>
    </section>
  );
}
