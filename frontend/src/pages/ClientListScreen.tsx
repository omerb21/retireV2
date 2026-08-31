import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiTransportError, type ClientListItem, getClients } from "../api/clientsApi";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `הבקשה נכשלה: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "לא ניתן לטעון את רשימת הלקוחות.";
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
    return <section><h2>רשימת לקוחות</h2><p>טוען לקוחות...</p></section>;
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>רשימת לקוחות</h2>
        <p>לא ניתן לטעון את רשימת הלקוחות.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to="/clients/new">יצירת לקוח</Link>
        </p>
      </section>
    );
  }

  if (clients.length === 0) {
    return (
      <section>
        <h2>רשימת לקוחות</h2>
        <p>טרם נוצרו לקוחות</p>
        <p>
          <Link to="/clients/new">יצירת לקוח</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>רשימת לקוחות</h2>
      <p>
        <Link to="/clients/new">יצירת לקוח</Link>
      </p>
      <ul>
        {clients.map((client) => (
          <li key={client.client_id}>
            <article>
              <h3>
                <Link to={`/clients/${client.client_id}`}>{client.full_name}</Link>
              </h3>
              <p>מספר זהות: {client.id_number ?? "לא נמסר"}</p>
              {client.birth_date ? <p>תאריך לידה: {formatIsoDate(client.birth_date)}</p> : null}
              <p>מצב תיק: {heLabel(client.file_status)}</p>
              <p>מצב זיהוי מקצועי: {heLabel(client.professional_identification_status)}</p>
              <p>
                <Link to={`/clients/${client.client_id}`}>פתיחת פרטי הלקוח</Link>
              </p>
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}
