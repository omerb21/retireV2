import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type ClientDetailItem,
  getClient,
  getClientProfile,
  updateClientProfile
} from "../api/clientsApi";

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

  return "Unable to load client details.";
}

export function ClientDetailScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const parsedClientId = Number(clientId);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState("");
  const [notes, setNotes] = useState("");
  const [profileExists, setProfileExists] = useState(false);
  const [profileLoadErrorMessage, setProfileLoadErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadClient() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextClient = await getClient(parsedClientId);
        if (!isActive) {
          return;
        }
        setClient(nextClient);
        setIsNotFound(false);
        setErrorMessage(null);

        try {
          const profileResponse = await getClientProfile(parsedClientId);
          if (!isActive) {
            return;
          }
          setBirthDate(profileResponse.profile?.birth_date ?? "");
          setGender(profileResponse.profile?.gender ?? "");
          setNotes(profileResponse.profile?.notes ?? "");
          setProfileExists(profileResponse.profile !== null);
          setProfileLoadErrorMessage(null);
        } catch (profileError) {
          if (!isActive) {
            return;
          }
          setProfileLoadErrorMessage(getErrorMessage(profileError));
        }
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (error instanceof ApiTransportError && error.status === 404) {
          setClient(null);
          setIsNotFound(true);
          setErrorMessage(null);
        } else {
          setClient(null);
          setIsNotFound(false);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadClient();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

    setIsSaving(true);
    setSaveErrorMessage(null);
    setSaveSuccessMessage(null);

    try {
      const response = await updateClientProfile(client.client_id, {
        birth_date: birthDate || null,
        gender: gender || null,
        notes: notes || null
      });
      setBirthDate(response.profile?.birth_date ?? "");
      setGender(response.profile?.gender ?? "");
      setNotes(response.profile?.notes ?? "");
      setProfileExists(response.profile !== null);
      setSaveSuccessMessage("Profile saved successfully.");
    } catch (error) {
      setSaveErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Loading client details...</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Client not found.</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Unable to load client details.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (client === null) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Client details are unavailable.</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Client Detail</h2>
      <p>Client ID: {client.client_id}</p>
      <p>Full Name: {client.full_name}</p>
      <p>ID Number: {client.id_number}</p>
      {!profileExists && profileLoadErrorMessage === null ? <p>No client profile has been saved yet.</p> : null}
      {profileLoadErrorMessage ? (
        <>
          <p>Unable to load client profile.</p>
          <pre>{profileLoadErrorMessage}</pre>
        </>
      ) : null}
      <form onSubmit={handleSaveProfile}>
        <p>
          <label htmlFor="profile-birth-date">Birth Date</label>
          <input
            id="profile-birth-date"
            type="date"
            value={birthDate}
            onChange={(event) => {
              setBirthDate(event.target.value);
              setSaveSuccessMessage(null);
            }}
          />
        </p>
        <p>
          <label htmlFor="profile-gender">Gender</label>
          <input
            id="profile-gender"
            value={gender}
            onChange={(event) => {
              setGender(event.target.value);
              setSaveSuccessMessage(null);
            }}
          />
        </p>
        <p>
          <label htmlFor="profile-notes">Notes</label>
          <textarea
            id="profile-notes"
            value={notes}
            onChange={(event) => {
              setNotes(event.target.value);
              setSaveSuccessMessage(null);
            }}
          />
        </p>
        <button type="submit" disabled={isSaving || profileLoadErrorMessage !== null}>
          {isSaving ? "Saving Profile..." : "Save Profile"}
        </button>
      </form>
      {saveSuccessMessage ? <p>{saveSuccessMessage}</p> : null}
      {saveErrorMessage ? (
        <>
          <p>Unable to save profile.</p>
          <pre>{saveErrorMessage}</pre>
        </>
      ) : null}
      <p>
        <Link
          to={`/clients/${client.client_id}/employment-history`}
          state={{ clientName: client.full_name }}
        >
          Employment History
        </Link>
      </p>
      <p>
        <Link to="/clients">Back to client list</Link>
      </p>
    </section>
  );
}
