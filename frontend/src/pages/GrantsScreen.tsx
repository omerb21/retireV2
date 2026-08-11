import { FormEvent, useEffect, useRef, useState } from "react";
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
  employerName: string;
  employerWithholdingFileNumber: string;
  employmentStartDate: string;
  employmentEndDate: string;
  grantReceiptDate: string;
  exemptGrantAmount: string;
}

const emptyFormState: FormState = {
  employerName: "",
  employerWithholdingFileNumber: "",
  employmentStartDate: "",
  employmentEndDate: "",
  grantReceiptDate: "",
  exemptGrantAmount: ""
};

function formStateFromGrant(grant: GrantItem): FormState {
  return {
    employerName: grant.employer_name ?? "",
    employerWithholdingFileNumber: grant.employer_withholding_file_number ?? "",
    employmentStartDate: grant.employment_start_date,
    employmentEndDate: grant.employment_end_date,
    grantReceiptDate: grant.grant_receipt_date,
    exemptGrantAmount: grant.exempt_grant_amount === null ? "" : String(grant.exempt_grant_amount)
  };
}

function payloadFromForm(formState: FormState): GrantPayload {
  return {
    employer_name: formState.employerName.trim(),
    employer_withholding_file_number: formState.employerWithholdingFileNumber.trim(),
    employment_start_date: formState.employmentStartDate,
    employment_end_date: formState.employmentEndDate,
    grant_receipt_date: formState.grantReceiptDate,
    exempt_grant_amount: formState.exemptGrantAmount
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
  const generationRef = useRef(0);

  function ownsRequest(ownerClientId: number, generation: number): boolean {
    return parsedClientId === ownerClientId && generationRef.current === generation;
  }

  async function refreshGrants(ownerClientId: number, generation: number) {
    const nextGrants = await getGrants(ownerClientId);
    if (!ownsRequest(ownerClientId, generation)) return;
    setGrants(nextGrants);
    setIsNotFound(false);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;
    const generation = ++generationRef.current;
    const ownerClientId = parsedClientId;
    setGrants([]);
    setIsLoading(true);
    setIsNotFound(false);
    setErrorMessage(null);
    setFormState(emptyFormState);
    setEditingId(null);
    setMutationErrorMessage(null);
    setIsSubmitting(false);

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
        const nextGrants = await getGrants(ownerClientId);
        if (!isActive || !ownsRequest(ownerClientId, generation)) {
          return;
        }
        setGrants(nextGrants);
        setIsNotFound(false);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive || !ownsRequest(ownerClientId, generation)) {
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
        if (isActive && ownsRequest(ownerClientId, generation)) {
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

    const ownerClientId = parsedClientId;
    const generation = generationRef.current;

    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      const payload = payloadFromForm(formState);
      if (editingId === null) {
        await createGrant(ownerClientId, payload);
      } else {
        await updateGrant(ownerClientId, editingId, payload);
      }
      await refreshGrants(ownerClientId, generation);
      if (!ownsRequest(ownerClientId, generation)) return;
      resetForm();
    } catch (error) {
      if (!ownsRequest(ownerClientId, generation)) return;
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      if (ownsRequest(ownerClientId, generation)) setIsSubmitting(false);
    }
  }

  async function handleDelete(grant: GrantItem) {
    const ownerClientId = parsedClientId;
    const generation = generationRef.current;
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      await deleteGrant(ownerClientId, grant.grant_id);
      await refreshGrants(ownerClientId, generation);
      if (!ownsRequest(ownerClientId, generation)) return;
      if (editingId === grant.grant_id) {
        resetForm();
      }
    } catch (error) {
      if (!ownsRequest(ownerClientId, generation)) return;
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      if (ownsRequest(ownerClientId, generation)) setIsSubmitting(false);
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
                {grant.employer_name ? <p>Employer Name: {grant.employer_name}</p> : null}
                <p>Employer Withholding File Number: {grant.employer_withholding_file_number}</p>
                <p>Exempt Grant Amount: {grant.exempt_grant_amount}</p>
                <p>Grant Receipt Date: {grant.grant_receipt_date}</p>
                <p>Employment Start Date: {grant.employment_start_date}</p>
                <p>Employment End Date: {grant.employment_end_date}</p>
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
            Employer Withholding File Number
            <input type="text" value={formState.employerWithholdingFileNumber}
              onChange={(event) => setFormState((current) => ({ ...current, employerWithholdingFileNumber: event.target.value }))} required />
          </label>
        </p>
        <p>
          <label>
            Exempt Grant Amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={formState.exemptGrantAmount}
              onChange={(event) => setFormState((current) => ({ ...current, exemptGrantAmount: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Grant Receipt Date
            <input
              type="date"
              value={formState.grantReceiptDate}
              onChange={(event) => setFormState((current) => ({ ...current, grantReceiptDate: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Employment Start Date
            <input
              type="date"
              value={formState.employmentStartDate}
              onChange={(event) => setFormState((current) => ({ ...current, employmentStartDate: event.target.value }))}
              required
            />
          </label>
        </p>
        <p>
          <label>
            Employment End Date
            <input
              type="date"
              value={formState.employmentEndDate}
              onChange={(event) => setFormState((current) => ({ ...current, employmentEndDate: event.target.value }))}
              required
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
