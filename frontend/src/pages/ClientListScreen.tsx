import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiTransportError, type ClientListItem, getClients } from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load clients.";
}

export function ClientListScreen() {
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadClients() {
      try {
        const nextClients = await getClients();
        if (!isActive) {
          return;
        }
        setClients(nextClients);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadClients();

    return () => {
      isActive = false;
    };
  }, []);

  if (isLoading) {
    return <section><h2>Client List</h2><p>Loading clients...</p></section>;
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>Client List</h2>
        <p>Unable to load clients.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to="/clients/new">Create Client</Link>
        </p>
      </section>
    );
  }

  if (clients.length === 0) {
    return (
      <section>
        <h2>Client List</h2>
        <p>No clients yet</p>
        <p>
          <Link to="/clients/new">Create Client</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Client List</h2>
      <p>
        <Link to="/clients/new">Create Client</Link>
      </p>
      <ul>
        {clients.map((client) => (
          <li key={client.client_id}>
            <article>
              <h3>
                <Link to={`/clients/${client.client_id}`}>{client.full_name}</Link>
              </h3>
              <p>ID Number: {client.id_number ?? "Not provided"}</p>
              {client.birth_date ? <p>Birth Date: {client.birth_date}</p> : null}
              <p>File Status: {client.file_status}</p>
              <p>Professional Identification: {client.professional_identification_status}</p>
              <p>
                <Link to={`/clients/${client.client_id}`}>Open client details</Link>
              </p>
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}
