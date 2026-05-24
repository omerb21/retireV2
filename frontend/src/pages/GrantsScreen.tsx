import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiTransportError, type GrantItem, getGrants } from "../api/clientsApi";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return `Request failed: ${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load grants.";
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

  if (errorMessage !== null) {
    return (
      <section>
        <h2>Grants</h2>
        <p>Client ID: {parsedClientId}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Unable to load grants.</p>
        <p>{errorMessage}</p>
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

  if (grants.length === 0) {
    return (
      <section>
        <h2>Grants</h2>
        <p>Client ID: {parsedClientId}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>No grants found.</p>
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
            </article>
          </li>
        ))}
      </ul>
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
