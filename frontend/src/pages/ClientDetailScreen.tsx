import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiTransportError, type ClientDetailItem, getClient } from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
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
      {client.birth_date ? <p>Birth Date: {client.birth_date}</p> : null}
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
