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
  const routeStateMatchesClient = clientId !== null && routeState?.clientId === clientId;
  const clientName = routeStateMatchesClient ? routeState?.clientName ?? null : null;
  const navigationState = clientName ? { clientId: clientId ?? undefined, clientName } : { clientId: clientId ?? undefined };
  const contextKey = clientId !== null && runId !== null ? `${clientId}:${runId}` : null;

  const [detail, setDetail] = useState<FixationRunDetailResponse | null>(null);
  const [loadedContextKey, setLoadedContextKey] = useState<string | null>(null);
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
          setLoadedContextKey(null);
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
      setLoadedContextKey(null);
      setLatestSuccessfulRunId(null);

      try {
        const [nextDetail, nextHistory] = await Promise.all([
          getFixationRunDetail(clientId, runId),
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
          setLoadedContextKey(`${clientId}:${runId}`);
          return;
        }

        setDetail(nextDetail);
        setLatestSuccessfulRunId(findLatestSuccessfulRunId(nextHistory));
        setLoadedContextKey(`${clientId}:${runId}`);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setDetail(null);
        setLatestSuccessfulRunId(null);
        setLoadedContextKey(`${clientId}:${runId}`);
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

  const visibleDetail = loadedContextKey === contextKey ? detail : null;
  const result = visibleDetail?.result ?? null;
  const inputSnapshot = visibleDetail?.input_snapshot ?? null;
  const m07Reference =
    inputSnapshot && typeof inputSnapshot.m07_input_reference === "object"
      ? (inputSnapshot.m07_input_reference as Record<string, unknown>)
      : null;
  const m07Resolution =
    inputSnapshot && typeof inputSnapshot.m07_resolution === "object"
      ? (inputSnapshot.m07_resolution as Record<string, unknown>)
      : null;
  const parameterSet =
    inputSnapshot && typeof inputSnapshot.parameter_set === "object"
      ? (inputSnapshot.parameter_set as Record<string, unknown>)
      : null;
  const parameterValues =
    parameterSet && typeof parameterSet.values === "object"
      ? (parameterSet.values as Record<string, unknown>)
      : null;
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

  if (loadedContextKey !== contextKey) {
    return (
      <section>
        <h2>Fixation Run Detail</h2>
        <p>Loading fixation run detail...</p>
      </section>
    );
  }

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

      {visibleDetail ? (
        <>
          {!isLatestSuccessfulRun && latestSuccessfulRunId !== null ? <p>Not latest successful run</p> : null}
          {renderFields("Run Metadata", [
            { label: "Run ID", value: visibleDetail.run.run_id },
            { label: "Client ID", value: visibleDetail.run.client_id },
            { label: "Status", value: visibleDetail.run.status },
            { label: "Calculation Version", value: visibleDetail.run.calculation_version },
            { label: "Created At", value: visibleDetail.run.created_at },
          ])}
          {result ? (
            <>
              {renderFields("Backend Calculation Summary", summaryFields)}
              {renderFields("Backend Impact Values", impactFields)}
            </>
          ) : null}
          {inputSnapshot ? (
            <>
              {renderFields("Saved Input and Resolver Provenance", [
                {
                  label: "Selected B1 Revision",
                  value:
                    m07Reference?.b1_evidence_revision_id ??
                    m07Resolution?.b1_evidence_revision_id,
                },
                {
                  label: "Explicit Candidate Selection",
                  value: m07Reference?.selections,
                },
                {
                  label: "Resolver Scope",
                  value: m07Resolution?.calculation_scope,
                },
                {
                  label: "Resolver Manifest Version",
                  value: m07Resolution?.manifest_version,
                },
                {
                  label: "Resolver Outcome",
                  value: m07Resolution?.outcome,
                },
                {
                  label: "Resolver Fingerprint",
                  value: m07Resolution?.fingerprint,
                },
                {
                  label: "Resolver Source References",
                  value: m07Resolution?.source_references,
                },
                {
                  label: "Normalized Selected Values",
                  value: m07Resolution?.normalized_selected_values,
                },
                {
                  label: "Parameter Set",
                  value: parameterSet?.parameter_set_id,
                },
                {
                  label: "Parameter Tax Year",
                  value: parameterSet?.tax_year,
                },
                {
                  label: "Parameter Effective From",
                  value: parameterSet?.effective_from,
                },
                {
                  label: "Parameter Effective To",
                  value: parameterSet?.effective_to,
                },
                {
                  label: "Parameter Monthly Cap",
                  value: parameterValues?.monthly_cap,
                },
                {
                  label: "Parameter Exemption Percentage",
                  value: parameterValues?.exemption_percentage,
                },
                {
                  label: "Parameter Capital Multiplier",
                  value: parameterValues?.capital_multiplier,
                },
                {
                  label: "Parameter Grant Impact Multiplier",
                  value: parameterValues?.grant_impact_multiplier,
                },
                {
                  label: "Parameter Source / Basis",
                  value: parameterSet?.source_basis,
                },
                {
                  label: "Parameter Status",
                  value: parameterSet?.status,
                },
                {
                  label: "Parameter Accepted For Use",
                  value: parameterSet?.accepted_for_use,
                },
                {
                  label: "Parameter Decision Actor",
                  value: parameterSet?.accepted_by,
                },
                {
                  label: "Parameter Decision Timestamp",
                  value: parameterSet?.decision_timestamp,
                },
                {
                  label: "Grant Collection State",
                  value: inputSnapshot.grants_collection_state,
                },
                {
                  label: "Capitalization Collection State",
                  value: inputSnapshot.actual_capitalizations_collection_state,
                },
              ])}
              {renderFields("Saved Material Inputs", [
                { label: "Grants", value: inputSnapshot.grants },
                {
                  label: "Future Grant Reservation",
                  value: inputSnapshot.future_grant_reservation,
                },
                {
                  label: "Actual Capitalizations",
                  value: inputSnapshot.actual_capitalizations,
                },
              ])}
            </>
          ) : null}
          {visibleDetail.audit_rows.length > 0 ? (
            <section>
              <h3>Audit Rows</h3>
              <pre>{stringifyValue(visibleDetail.audit_rows)}</pre>
            </section>
          ) : null}
          {visibleDetail.input_snapshot ? (
            <section>
              <h3>Input Snapshot</h3>
              <pre>{stringifyValue(visibleDetail.input_snapshot)}</pre>
            </section>
          ) : null}
          {visibleDetail.validation_errors.length > 0 ? (
            <section>
              <h3>Validation Errors</h3>
              <pre>{stringifyValue(visibleDetail.validation_errors)}</pre>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
