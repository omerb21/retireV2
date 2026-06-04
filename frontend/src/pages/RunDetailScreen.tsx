import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type FixationHistoryEntry,
  type FixationRunDetailResponse,
  getFixationHistory,
  getFixationRunDetail,
} from "../api/fixationApi";

type ClientRouteState = {
  clientId?: number;
  clientName?: string;
};

type DisplayField = {
  label: string;
  value: unknown;
};

function stringifyValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return JSON.stringify(error.body, null, 2);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load fixation run detail.";
}

function resolveClientId(clientIdParam: string | undefined, routeState: ClientRouteState | null): number | null {
  const routeClientId = routeState?.clientId;
  const resolvedClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeClientId;

  return Number.isInteger(resolvedClientId) && Number(resolvedClientId) > 0 ? Number(resolvedClientId) : null;
}

function resolveRunId(runIdParam: string | undefined): number | null {
  const resolvedRunId = Number(runIdParam);
  return Number.isInteger(resolvedRunId) && resolvedRunId > 0 ? resolvedRunId : null;
}

function findLatestSuccessfulRunId(history: FixationHistoryEntry[]): number | null {
  const latestSuccessfulRun = history.find((entry) => entry.status === "success");
  return latestSuccessfulRun?.run_id ?? null;
}

function renderFields(title: string, fields: DisplayField[]) {
  const visibleFields = fields.filter((field) => field.value !== undefined && field.value !== null);

  if (visibleFields.length === 0) {
    return null;
  }

  return (
    <section>
      <h3>{title}</h3>
      <ul>
        {visibleFields.map((field) => (
          <li key={field.label}>
            <strong>{field.label}:</strong> {stringifyValue(field.value)}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function RunDetailScreen() {
  const { clientId: clientIdParam, runId: runIdParam } = useParams<{ clientId: string; runId: string }>();
  const location = useLocation();
  const routeState = location.state as ClientRouteState | null;
  const clientId = resolveClientId(clientIdParam, routeState);
  const runId = resolveRunId(runIdParam);
  const clientName = routeState?.clientName ?? null;
  const navigationState = clientName ? { clientId: clientId ?? undefined, clientName } : { clientId: clientId ?? undefined };

  const [detail, setDetail] = useState<FixationRunDetailResponse | null>(null);
  const [latestSuccessfulRunId, setLatestSuccessfulRunId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(clientId !== null && runId !== null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [clientMismatch, setClientMismatch] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function loadRunDetail() {
      if (clientId === null || runId === null) {
        if (isActive) {
          setDetail(null);
          setLatestSuccessfulRunId(null);
          setClientMismatch(false);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      setClientMismatch(false);
      setDetail(null);
      setLatestSuccessfulRunId(null);

      try {
        const [nextDetail, nextHistory] = await Promise.all([
          getFixationRunDetail(runId),
          getFixationHistory(clientId),
        ]);

        if (!isActive) {
          return;
        }

        const detailClientId = Number(nextDetail.run.client_id);
        if (!Number.isInteger(detailClientId) || detailClientId !== clientId) {
          setClientMismatch(true);
          setDetail(null);
          setLatestSuccessfulRunId(null);
          return;
        }

        setDetail(nextDetail);
        setLatestSuccessfulRunId(findLatestSuccessfulRunId(nextHistory));
      } catch (error) {
        if (!isActive) {
          return;
        }

        setDetail(null);
        setLatestSuccessfulRunId(null);
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadRunDetail();

    return () => {
      isActive = false;
    };
  }, [clientId, runId]);

  const result = detail?.result ?? null;
  const isLatestSuccessfulRun = useMemo(
    () => runId !== null && latestSuccessfulRunId !== null && runId === latestSuccessfulRunId,
    [latestSuccessfulRunId, runId],
  );

  const summaryFields: DisplayField[] = [
    { label: "Calculation ID", value: result?.calculation_id },
    { label: "Calculation Version", value: result?.calculation_version },
    { label: "Status", value: result?.status },
    { label: "Eligibility Date", value: result?.eligibility_date },
    { label: "Eligibility Year", value: result?.eligibility_year },
    { label: "Monthly Cap", value: result?.monthly_cap },
    { label: "Exemption Percentage", value: result?.exemption_percentage },
    { label: "Capital Multiplier", value: result?.capital_multiplier },
  ];
  const impactFields: DisplayField[] = [
    { label: "Initial Exempt Capital", value: result?.initial_exempt_capital },
    { label: "Grant Impact Total", value: result?.grant_impact_total },
    { label: "Future Grant Reserved", value: result?.future_grant_reserved },
    { label: "Future Grant Impact", value: result?.future_grant_impact },
    { label: "Actual Capitalization Impact", value: result?.actual_capitalization_impact },
    { label: "IDF Impact", value: result?.idf_impact },
    { label: "Total Impact", value: result?.total_impact },
    { label: "Remaining Exempt Capital", value: result?.remaining_exempt_capital },
    { label: "Monthly Exempt Pension", value: result?.monthly_exempt_pension },
    { label: "Capital Exemption Percentage", value: result?.capital_exemption_percentage },
    { label: "Pension Exemption Percentage", value: result?.pension_exemption_percentage },
  ];

  if (clientId === null || runId === null) {
    return (
      <section>
        <h2>Fixation Run Detail</h2>
        <p>BLOCKED</p>
        <p>Fixation run detail requires a valid client and run context.</p>
      </section>
    );
  }

  const historyPath = `/clients/${clientId}/fixation/history`;
  const fixationInputPath = `/clients/${clientId}/fixation/input`;

  if (clientMismatch) {
    return (
      <section>
        <h2>Fixation Run Detail</h2>
        <p>BLOCKED</p>
        <p>This run does not belong to the current client context. Saved run data cannot be displayed as trusted.</p>
        <p>
          <Link to={historyPath} state={navigationState}>
            Back to History
          </Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Fixation Run Detail</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p>Run ID: {runId}</p>
      <p>This is a saved historical calculation run. Source data verification is not available on this screen.</p>
      <p>
        <Link to={historyPath} state={navigationState}>
          Back to History
        </Link>
      </p>
      <p>
        <Link to={fixationInputPath} state={navigationState}>
          Start New Calculation
        </Link>
      </p>
      <p>
        <Link to={fixationInputPath} state={navigationState}>
          Back to Fixation Parameters
        </Link>
      </p>

      {isLoading ? <p>Loading fixation run detail...</p> : null}
      {errorMessage ? (
        <>
          <p>Unable to load fixation run detail.</p>
          <p>{errorMessage}</p>
        </>
      ) : null}

      {detail ? (
        <>
          {!isLatestSuccessfulRun && latestSuccessfulRunId !== null ? <p>Not latest successful run</p> : null}
          {renderFields("Run Metadata", [
            { label: "Run ID", value: detail.run.run_id },
            { label: "Client ID", value: detail.run.client_id },
            { label: "Status", value: detail.run.status },
            { label: "Calculation Version", value: detail.run.calculation_version },
            { label: "Created At", value: detail.run.created_at },
          ])}
          {result ? (
            <>
              {renderFields("Backend Calculation Summary", summaryFields)}
              {renderFields("Backend Impact Values", impactFields)}
            </>
          ) : null}
          {detail.audit_rows.length > 0 ? (
            <section>
              <h3>Audit Rows</h3>
              <pre>{stringifyValue(detail.audit_rows)}</pre>
            </section>
          ) : null}
          {detail.input_snapshot ? (
            <section>
              <h3>Input Snapshot</h3>
              <pre>{stringifyValue(detail.input_snapshot)}</pre>
            </section>
          ) : null}
          {detail.validation_errors.length > 0 ? (
            <section>
              <h3>Validation Errors</h3>
              <pre>{stringifyValue(detail.validation_errors)}</pre>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
