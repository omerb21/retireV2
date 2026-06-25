import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiTransportError, createClient } from "../api/clientsApi";

interface FormState {
  fullName: string;
  idNumber: string;
}

const emptyFormState: FormState = {
  fullName: "",
  idNumber: ""
};

function getSubmitErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return JSON.stringify(error.body, null, 2);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to create client.";
}

export function CreateClientScreen() {
  const navigate = useNavigate();
  const [formState, setFormState] = useState<FormState>(emptyFormState);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    setSubmitErrorMessage(null);

    const fullName = formState.fullName.trim();
    const idNumber = formState.idNumber.trim();

    if (fullName.length === 0) {
      setValidationMessage("Client name is required.");
      return;
    }

    if (idNumber.length === 0) {
      setValidationMessage("ID number is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      const createdClient = await createClient({
        full_name: fullName,
        id_number: idNumber,
        birth_date: null
      });

      navigate(`/clients/${createdClient.client_id}`, {
        state: { clientName: createdClient.full_name }
      });
    } catch (error) {
      setSubmitErrorMessage(getSubmitErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section>
      <h2>Create Client</h2>
      <p>
        <Link to="/clients">Cancel</Link>
      </p>
      <form onSubmit={handleSubmit}>
        <p>
          <label htmlFor="fullName">
            Client Name
            <input
              id="fullName"
              name="fullName"
              type="text"
              value={formState.fullName}
              onChange={(event) => setFormState((current) => ({ ...current, fullName: event.target.value }))}
            />
          </label>
        </p>
        <p>
          <label htmlFor="idNumber">
            ID Number
            <input
              id="idNumber"
              name="idNumber"
              type="text"
              value={formState.idNumber}
              onChange={(event) => setFormState((current) => ({ ...current, idNumber: event.target.value }))}
            />
          </label>
        </p>
        {validationMessage ? <p>{validationMessage}</p> : null}
        {submitErrorMessage ? (
          <>
            <p>Unable to create client.</p>
            <pre>{submitErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving client..." : "Save Client"}
          </button>
        </p>
      </form>
    </section>
  );
}
