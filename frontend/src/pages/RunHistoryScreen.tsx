import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type FixationHistoryEntry,
  getFixationHistory,
} from "../api/fixationApi";

type ClientRouteState = {
  clientId?: number;
  clientName?: string;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return JSON.stringify(error.body, null, 2);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load fixation history.";
}

function resolveClientId(clientIdParam: string | undefined, routeState: ClientRouteState | null): number | null {
  const routeClientId = routeState?.clientId;
  const resolvedClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeClientId;

  return Number.isInteger(resolvedClientId) && Number(resolvedClientId) > 0 ? Number(resolvedClientId) : null;
}

function findLatestSuccessfulRunId(history: FixationHistoryEntry[]): number | null {
  const latestSuccessfulRun = history.find((entry) => entry.status === "success");
  return latestSuccessfulRun?.run_id ?? null;
}

export function RunHistoryScreen() {
  const { clientId: clientIdParam } = useParams<{ clientId: string }>();
  const location = useLocation();
  const routeState = location.state as ClientRouteState | null;
  const clientId = resolveClientId(clientIdParam, routeState);
  const clientName = routeState?.clientName ?? null;
  const navigationState = clientName ? { clientId: clientId ?? undefined, clientName } : { clientId: clientId ?? undefined };

  const [history, setHistory] = useState<FixationHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(clientId !== null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadHistory() {
      if (clientId === null) {
        if (isActive) {
          setHistory([]);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const nextHistory = await getFixationHistory(clientId);

        if (!isActive) {
          return;
        }

        setHistory(nextHistory);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setHistory([]);
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadHistory();

    return () => {
      isActive = false;
    };
  }, [clientId]);

  const latestSuccessfulRunId = useMemo(() => findLatestSuccessfulRunId(history), [history]);

  if (clientId === null) {
    return (
      <section>
        <h2>Fixation History</h2>
        <p>BLOCKED</p>
        <p>Fixation history requires an existing client context.</p>
      </section>
    );
  }

  const fixationInputPath = `/clients/${clientId}/fixation/input`;
  const calculationResultPath = `/clients/${clientId}/fixation/result`;

  return (
    <section>
      <h2>Fixation History</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p>
        <Link to={fixationInputPath} state={navigationState}>
          Back to Fixation Parameters
        </Link>
      </p>
      <p>
        <Link to={calculationResultPath} state={navigationState}>
          Back to Calculation Result
        </Link>
      </p>
      <p>
        <Link to={fixationInputPath} state={navigationState}>
          Start New Calculation
        </Link>
      </p>

      {isLoading ? <p>Loading fixation history...</p> : null}
      {errorMessage ? (
        <>
          <p>Unable to load fixation history.</p>
          <p>{errorMessage}</p>
        </>
      ) : null}

      {!isLoading && !errorMessage && history.length === 0 ? (
        <>
          <p>No fixation calculations saved yet</p>
          <p>
            <Link to={fixationInputPath} state={navigationState}>
              Start New Calculation
            </Link>
          </p>
        </>
      ) : null}

      {!isLoading && !errorMessage && history.length > 0 ? (
        <section>
          <h3>Saved Runs</h3>
          <ul>
            {history.map((entry) => {
              const runDetailPath = `/clients/${clientId}/fixation/runs/${entry.run_id}`;
              const isLatestSuccessfulRun = entry.run_id === latestSuccessfulRunId;

              return (
                <li key={entry.run_id}>
                  <p>
                    <strong>Run ID:</strong> {entry.run_id}
                  </p>
                  <p>
                    <strong>Created At:</strong> {entry.created_at ?? "Unknown"}
                  </p>
                  <p>
                    <strong>Status:</strong> {entry.status}
                  </p>
                  <p>
                    <strong>Calculation Version:</strong> {entry.calculation_version ?? "Unknown"}
                  </p>
                  <p>
                    <strong>Summary:</strong> {entry.status} / {entry.calculation_version ?? "Unknown"} /{" "}
                    {entry.created_at ?? "Unknown"}
                  </p>
                  {isLatestSuccessfulRun ? <p>Latest successful run</p> : null}
                  <p>
                    <Link to={runDetailPath} state={navigationState}>
                      View Run
                    </Link>
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
