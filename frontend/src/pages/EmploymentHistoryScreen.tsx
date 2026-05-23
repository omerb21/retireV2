import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiTransportError, type EmploymentRecordItem, getEmploymentRecords } from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load employment history.";
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

  if (isLoading) {
    return (
      <section>
        <h2>Employment History</h2>
        <p>Client ID: {Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : "Unknown"}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Loading employment history...</p>
        <p>
          <Link to={Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}` : "/clients"}>
            Back to client detail
          </Link>
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
          <Link to={Number.isInteger(parsedClientId) && parsedClientId > 0 ? `/clients/${parsedClientId}` : "/clients"}>
            Back to client detail
          </Link>
        </p>
      </section>
    );
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>Employment History</h2>
        <p>Client ID: {parsedClientId}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Unable to load employment history.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to={`/clients/${parsedClientId}`}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  if (records.length === 0) {
    return (
      <section>
        <h2>Employment History</h2>
        <p>Client ID: {parsedClientId}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>No employment records found.</p>
        <p>
          <Link to={`/clients/${parsedClientId}`}>Back to client detail</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Employment History</h2>
      <p>Client ID: {parsedClientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
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
            </article>
          </li>
        ))}
      </ul>
      <p>
        <Link to={`/clients/${parsedClientId}`}>Back to client detail</Link>
      </p>
    </section>
  );
}
