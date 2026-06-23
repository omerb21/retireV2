import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  createEmploymentRecord,
  deleteEmploymentRecord,
  type EmploymentRecordItem,
  type EmploymentRecordPayload,
  getEmploymentRecords,
  updateEmploymentRecord
} from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load employment history.";
}

interface FormState {
  employerName: string;
  workStartDate: string;
  workEndDate: string;
  isCurrent: boolean;
  notes: string;
}

const emptyFormState: FormState = {
  employerName: "",
  workStartDate: "",
  workEndDate: "",
  isCurrent: false,
  notes: ""
};

function formStateFromRecord(record: EmploymentRecordItem): FormState {
  return {
    employerName: record.employer_name,
    workStartDate: record.work_start_date,
    workEndDate: record.work_end_date ?? "",
    isCurrent: record.is_current,
    notes: record.notes ?? ""
  };
}

function payloadFromForm(formState: FormState): EmploymentRecordPayload {
  return {
    employer_name: formState.employerName,
    work_start_date: formState.workStartDate,
    work_end_date: formState.workEndDate.trim() === "" ? null : formState.workEndDate,
    is_current: formState.isCurrent,
    notes: formState.notes.trim() === "" ? null : formState.notes
  };
}

export function EmploymentHistoryScreen() {
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
  const [records, setRecords] = useState<EmploymentRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [formState, setFormState] = useState<FormState>(emptyFormState);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshEmploymentHistory() {
    const nextRecords = await getEmploymentRecords(parsedClientId);
    setRecords(nextRecords);
    setIsNotFound(false);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadEmploymentHistory() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextRecords = await getEmploymentRecords(parsedClientId);
        if (!isActive) {
          return;
        }
        setRecords(nextRecords);
        setIsNotFound(false);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (error instanceof ApiTransportError && error.status === 404) {
          setRecords([]);
          setIsNotFound(true);
          setErrorMessage(null);
        } else {
          setRecords([]);
          setIsNotFound(false);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadEmploymentHistory();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  const detailPath = Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}` : "/clients";
  const grantsPath = Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}/grants` : "/clients";
  const backState = clientName ? { clientName } : undefined;

  function startEditing(record: EmploymentRecordItem) {
    setEditingId(record.employment_record_id);
    setFormState(formStateFromRecord(record));
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
      setMutationErrorMessage("Unable to save employment record for this client.");
      return;
    }

    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      const payload = payloadFromForm(formState);
      if (editingId === null) {
        await createEmploymentRecord(parsedClientId, payload);
      } else {
        await updateEmploymentRecord(parsedClientId, editingId, payload);
      }
      await refreshEmploymentHistory();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(record: EmploymentRecordItem) {
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      await deleteEmploymentRecord(parsedClientId, record.employment_record_id);
      await refreshEmploymentHistory();
      if (editingId === record.employment_record_id) {
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
        <h2>Employment History</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Loading employment history...</p>
        <p>
          <Link to={detailPath}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>Employment History</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Employment history is not available for this client.</p>
        <p>
          <Link to={grantsPath} state={backState}>
            Grants
          </Link>
        </p>
        <p>
          <Link to={detailPath}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Employment History</h2>
      <p>Client ID: {parsedClientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      {errorMessage !== null ? (
        <>
          <p>Unable to load employment history.</p>
          <p>{errorMessage}</p>
        </>
      ) : records.length === 0 ? (
        <p>No employment records found.</p>
      ) : (
        <ul>
          {records.map((record) => (
            <li key={record.employment_record_id}>
              <article>
                <h3>{record.employer_name}</h3>
                <p>Employment Record ID: {record.employment_record_id}</p>
                <p>Work Start Date: {record.work_start_date}</p>
                <p>Work End Date: {record.work_end_date ?? "Ongoing"}</p>
                <p>Current Employment: {record.is_current ? "Yes" : "No"}</p>
                {record.notes ? <p>Notes: {record.notes}</p> : null}
                <p>
                  <button type="button" onClick={() => startEditing(record)} disabled={isSubmitting}>
                    Edit Employment Record
                  </button>
                  <button type="button" onClick={() => void handleDelete(record)} disabled={isSubmitting}>
                    Delete Employment Record
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit}>
        <h3>{editingId === null ? "Add Employment Record" : "Edit Employment Record"}</h3>
        <p>
          <label>
            Employer Name
            <input
              type="text"
              value={formState.employerName}
              onChange={(event) => setFormState((current) => ({ ...current, employerName: event.target.value }))}
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
            />
          </label>
        </p>
        <p>
          <label>
            <input
              type="checkbox"
              checked={formState.isCurrent}
              onChange={(event) => setFormState((current) => ({ ...current, isCurrent: event.target.checked }))}
            />
            Current Employment
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
            {isSubmitting ? "Saving..." : editingId === null ? "Add Employment Record" : "Save Employment Record"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              Cancel Edit
            </button>
          ) : null}
        </p>
      </form>

      <p>
        <Link to={grantsPath} state={backState}>
          Grants
        </Link>
      </p>
      <p>
        <Link to={detailPath}>Back to client detail</Link>
      </p>
    </section>
  );
}
