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
    return error.status === 422 ? "יש לבדוק את שדות החובה ולנסות שוב" : "הפעולה נכשלה. אפשר לנסות שוב בעוד רגע";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "לא ניתן לטעון את המענקים.";
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
      setMutationErrorMessage("לא ניתן לשמור מענק ללקוח זה.");
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
        <h2>מענקים</h2>
      <p><Link to={`/clients/${parsedClientId}/workspace`}>חזרה לסביבת התכנון החדשה</Link></p>
        <p>מזהה לקוח: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "לא ידוע"}</p>
        {clientName ? <p>שם הלקוח: {clientName}</p> : null}
        <p>טוען מענקים...</p>
        <p>
          <Link to={employmentHistoryPath} state={backState}>חזרה לתקופות העסקה</Link>
        </p>
        <p>
          <Link to={actualCapitalizationsPath} state={backState}>המשך להיוונים בפועל</Link>
        </p>
        <p>
          <Link to={detailPath}>חזרה לפרטי הלקוח</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>מענקים</h2>
        <p>מזהה לקוח: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "לא ידוע"}</p>
        {clientName ? <p>שם הלקוח: {clientName}</p> : null}
        <p>המענקים עדיין אינם זמינים ללקוח זה.</p>
        <p>
          <Link to={employmentHistoryPath} state={backState}>חזרה לתקופות העסקה</Link>
        </p>
        <p>
          <Link to={actualCapitalizationsPath} state={backState}>המשך להיוונים בפועל</Link>
        </p>
        <p>
          <Link to={detailPath}>חזרה לפרטי הלקוח</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>מענקים</h2>
      <p>מזהה לקוח: {parsedClientId}</p>
      {clientName ? <p>שם הלקוח: {clientName}</p> : null}
      {errorMessage !== null ? (
        <>
          <p>לא ניתן לטעון את המענקים.</p>
          <p>{errorMessage}</p>
        </>
      ) : grants.length === 0 ? (
        <p>לא נמצאו מענקים.</p>
      ) : (
        <ul>
          {grants.map((grant) => (
            <li key={grant.grant_id}>
              <article>
                <h3>{grant.employer_name ?? "מענק"}</h3>
                <p>מזהה מענק: {grant.grant_id}</p>
                {grant.employer_name ? <p>שם המעסיק: {grant.employer_name}</p> : null}
                <p>מספר תיק ניכויים: {grant.employer_withholding_file_number}</p>
                <p>סכום מענק פטור: {grant.exempt_grant_amount}</p>
                <p>תאריך קבלת המענק: {grant.grant_receipt_date}</p>
                <p>תחילת העסקה: {grant.employment_start_date}</p>
                <p>סיום העסקה: {grant.employment_end_date}</p>
                <p>
                  <button type="button" onClick={() => startEditing(grant)} disabled={isSubmitting}>
                    עריכת מענק
                  </button>
                  <button type="button" onClick={() => void handleDelete(grant)} disabled={isSubmitting}>
                    מחיקת מענק
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit}>
        <h3>{editingId === null ? "הוספת מענק" : "עריכת מענק"}</h3>
        <p>
          <label>
            שם המעסיק
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
            מספר תיק ניכויים של המעסיק
            <input type="text" value={formState.employerWithholdingFileNumber}
              onChange={(event) => setFormState((current) => ({ ...current, employerWithholdingFileNumber: event.target.value }))} required />
          </label>
        </p>
        <p>
          <label>
            סכום מענק פטור
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
            תאריך קבלת המענק
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
            תאריך תחילת העסקה
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
            תאריך סיום העסקה
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
            {isSubmitting ? "שומר..." : editingId === null ? "הוספת מענק" : "שמירת מענק"}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              ביטול העריכה
            </button>
          ) : null}
        </p>
      </form>

      <p>
        <Link to={employmentHistoryPath} state={backState}>חזרה לתקופות העסקה</Link>
      </p>
      <p>
        <Link to={actualCapitalizationsPath} state={backState}>המשך להיוונים בפועל</Link>
      </p>
      <p>
        <Link to={detailPath}>חזרה לפרטי הלקוח</Link>
      </p>
    </section>
  );
}
