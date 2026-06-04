import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError as ClientApiTransportError,
  type ActualCapitalizationItem,
  type GrantItem,
  getActualCapitalizations,
  getGrants,
} from "../api/clientsApi";
import {
  ApiTransportError,
  type FixationActualCapitalizationInputPayload,
  type FixationGrantInputPayload,
  type FixationInputPayload,
  type FixationResultResponse,
  getFixationHistory,
  getFixationRunDetail,
} from "../api/fixationApi";

type FixationInputRouteState = {
  clientId?: number;
  clientName?: string;
};

type ResultRouteState = {
  clientId?: number;
  clientName?: string;
  inputData?: FixationInputPayload;
  result?: FixationResultResponse;
  fixationInputPath?: string;
  fixationInputState?: FixationInputRouteState;
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

function parseNumber(value: number | string | null): number | null {
  if (value === null) {
    return null;
  }

  const parsedValue = typeof value === "number" ? value : Number(value);
  return Number.isNaN(parsedValue) ? null : parsedValue;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError || error instanceof ClientApiTransportError) {
    return stringifyValue(error.body);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected transport error.";
}

function mapGrantToPayload(grant: GrantItem): FixationGrantInputPayload {
  return {
    grant_id: grant.grant_id,
    employer_name: grant.employer_name,
    nominal_amount: parseNumber(grant.nominal_amount),
    indexed_amount: Number(grant.indexed_amount),
    grant_date: grant.grant_date,
    work_start_date: grant.work_start_date,
    work_end_date: grant.work_end_date,
  };
}

function mapActualCapitalizationToPayload(
  capitalization: ActualCapitalizationItem,
): FixationActualCapitalizationInputPayload {
  return {
    capitalization_id: capitalization.capitalization_id,
    amount: Number(capitalization.amount),
    capitalization_date: capitalization.capitalization_date,
    source_label: capitalization.source_label,
    notes: capitalization.notes,
  };
}

function normalizeFixationInput(payload: FixationInputPayload): Record<string, unknown> {
  return {
    calculation_id: payload.calculation_id ?? null,
    calculation_version: payload.calculation_version,
    eligibility_date: payload.eligibility_date,
    eligibility_year: payload.eligibility_year,
    monthly_cap: payload.monthly_cap,
    exemption_percentage: payload.exemption_percentage,
    capital_multiplier: payload.capital_multiplier,
    grants: payload.grants.map((grant) => ({
      grant_id: grant.grant_id,
      employer_name: grant.employer_name,
      nominal_amount: grant.nominal_amount,
      indexed_amount: grant.indexed_amount,
      grant_date: grant.grant_date,
      work_start_date: grant.work_start_date,
      work_end_date: grant.work_end_date,
    })),
    future_grant_reserved: payload.future_grant_reserved,
    actual_capitalizations: payload.actual_capitalizations.map((capitalization) => ({
      capitalization_id: capitalization.capitalization_id,
      amount: capitalization.amount,
      capitalization_date: capitalization.capitalization_date,
      source_label: capitalization.source_label,
      notes: capitalization.notes,
    })),
    idf_relevant: payload.idf_relevant,
    idf:
      payload.idf === null
        ? null
        : {
            idf_id: payload.idf.idf_id,
            reduction_amount: payload.idf.reduction_amount,
            original_commutation_percent: payload.idf.original_commutation_percent,
            current_commutation_percent: payload.idf.current_commutation_percent,
            commutation_date: payload.idf.commutation_date,
            promoter_age_date: payload.idf.promoter_age_date,
            source_label: payload.idf.source_label,
          },
  };
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

export function CalculationResultScreen() {
  const { clientId: clientIdParam } = useParams<{ clientId: string }>();
  const location = useLocation();
  const routeState = location.state as ResultRouteState | null;
  const routeClientId = routeState?.clientId;
  const resolvedClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeClientId;
  const clientId = Number.isInteger(resolvedClientId) && Number(resolvedClientId) > 0 ? Number(resolvedClientId) : null;
  const clientName = routeState?.clientName ?? routeState?.fixationInputState?.clientName ?? null;
  const fixationInputPath =
    routeState?.fixationInputPath ?? (clientId !== null ? `/clients/${clientId}/fixation/input` : "/fixation/input");
  const fixationInputState =
    routeState?.fixationInputState ??
    (clientName ? { clientId: clientId ?? undefined, clientName } : { clientId: clientId ?? undefined });
  const hasCurrentCalculation = routeState?.result !== undefined && routeState?.inputData !== undefined;
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [actualCapitalizations, setActualCapitalizations] = useState<ActualCapitalizationItem[]>([]);
  const [isSourceLoading, setIsSourceLoading] = useState(clientId !== null);
  const [sourceErrorMessage, setSourceErrorMessage] = useState<string | null>(null);
  const [isResultLoading, setIsResultLoading] = useState(clientId !== null && !hasCurrentCalculation);
  const [resultErrorMessage, setResultErrorMessage] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [resultSource, setResultSource] = useState<"current" | "latest" | null>(hasCurrentCalculation ? "current" : null);
  const [resolvedInputData, setResolvedInputData] = useState<FixationInputPayload | null>(routeState?.inputData ?? null);
  const [resolvedResult, setResolvedResult] = useState<FixationResultResponse | null>(routeState?.result ?? null);

  useEffect(() => {
    let isActive = true;

    async function loadCurrentSourceData() {
      if (clientId === null) {
        if (isActive) {
          setGrants([]);
          setActualCapitalizations([]);
          setSourceErrorMessage("Calculation Result requires an existing client context.");
          setIsSourceLoading(false);
        }
        return;
      }

      setIsSourceLoading(true);

      try {
        const [nextGrants, nextActualCapitalizations] = await Promise.all([
          getGrants(clientId),
          getActualCapitalizations(clientId),
        ]);

        if (!isActive) {
          return;
        }

        setGrants(nextGrants);
        setActualCapitalizations(nextActualCapitalizations);
        setSourceErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setGrants([]);
        setActualCapitalizations([]);
        setSourceErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsSourceLoading(false);
        }
      }
    }

    void loadCurrentSourceData();

    return () => {
      isActive = false;
    };
  }, [clientId]);

  useEffect(() => {
    let isActive = true;

    async function loadLatestSuccessfulResult() {
      if (clientId === null || hasCurrentCalculation) {
        if (isActive) {
          setIsResultLoading(false);
        }
        return;
      }

      setIsResultLoading(true);
      setResultErrorMessage(null);
      setResultMessage(null);

      try {
        const history = await getFixationHistory(clientId);
        const latestSuccessfulRun = history.find((entry) => entry.status === "success");

        if (!isActive) {
          return;
        }

        if (latestSuccessfulRun === undefined) {
          setResolvedResult(null);
          setResolvedInputData(null);
          setResultSource(null);
          setResultMessage(
            history.length === 0
              ? "No successful calculation result is available for this client."
              : "No successful calculation result is available. Latest saved calculation did not succeed.",
          );
          return;
        }

        const detail = await getFixationRunDetail(latestSuccessfulRun.run_id);

        if (!isActive) {
          return;
        }

        if (detail.result === null || detail.input_snapshot === null) {
          setResolvedResult(null);
          setResolvedInputData(null);
          setResultSource(null);
          setResultMessage("Latest successful calculation result could not be loaded.");
          return;
        }

        setResolvedResult(detail.result as FixationResultResponse);
        setResolvedInputData(detail.input_snapshot as unknown as FixationInputPayload);
        setResultSource("latest");
        setResultMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setResolvedResult(null);
        setResolvedInputData(null);
        setResultSource(null);
        setResultErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsResultLoading(false);
        }
      }
    }

    void loadLatestSuccessfulResult();

    return () => {
      isActive = false;
    };
  }, [clientId, hasCurrentCalculation]);

  const sourceDataChanged = useMemo(() => {
    if (resolvedInputData === null) {
      return false;
    }

    const snapshotSignature = JSON.stringify(normalizeFixationInput(resolvedInputData));
    const currentSignature = JSON.stringify(
      normalizeFixationInput({
        ...resolvedInputData,
        grants: grants.map(mapGrantToPayload),
        actual_capitalizations: actualCapitalizations.map(mapActualCapitalizationToPayload),
      }),
    );

    return snapshotSignature !== currentSignature;
  }, [actualCapitalizations, grants, resolvedInputData]);

  const trustedResultStatus =
    resolvedResult === null
      ? null
      : isSourceLoading
        ? "Verifying current source data before trusting this result."
        : sourceErrorMessage !== null
          ? "Unable to verify because current source data could not be loaded."
          : sourceDataChanged
            ? "Blocked until rerun."
            : "Current source data matches the calculation input snapshot.";
  const summaryFields: DisplayField[] = [
    { label: "Calculation ID", value: resolvedResult?.calculation_id },
    { label: "Calculation Version", value: resolvedResult?.calculation_version },
    { label: "Status", value: resolvedResult?.status },
    { label: "Eligibility Date", value: resolvedResult?.eligibility_date },
    { label: "Eligibility Year", value: resolvedResult?.eligibility_year },
    { label: "Monthly Cap", value: resolvedResult?.monthly_cap },
    { label: "Exemption Percentage", value: resolvedResult?.exemption_percentage },
    { label: "Capital Multiplier", value: resolvedResult?.capital_multiplier },
  ];
  const impactFields: DisplayField[] = [
    { label: "Initial Exempt Capital", value: resolvedResult?.initial_exempt_capital },
    { label: "Grant Impact Total", value: resolvedResult?.grant_impact_total },
    { label: "Future Grant Reserved", value: resolvedResult?.future_grant_reserved },
    { label: "Future Grant Impact", value: resolvedResult?.future_grant_impact },
    { label: "Actual Capitalization Impact", value: resolvedResult?.actual_capitalization_impact },
    { label: "IDF Impact", value: resolvedResult?.idf_impact },
    { label: "Total Impact", value: resolvedResult?.total_impact },
    { label: "Remaining Exempt Capital", value: resolvedResult?.remaining_exempt_capital },
    { label: "Monthly Exempt Pension", value: resolvedResult?.monthly_exempt_pension },
    { label: "Capital Exemption Percentage", value: resolvedResult?.capital_exemption_percentage },
    { label: "Pension Exemption Percentage", value: resolvedResult?.pension_exemption_percentage },
  ];
  const validationErrors = Array.isArray(resolvedResult?.validation_errors)
    ? (resolvedResult.validation_errors as unknown[])
    : [];
  const grantResults = Array.isArray(resolvedResult?.grant_results)
    ? (resolvedResult.grant_results as Array<Record<string, unknown>>)
    : null;
  const actualCapitalizationResults = Array.isArray(resolvedResult?.actual_capitalization_results)
    ? (resolvedResult.actual_capitalization_results as Array<Record<string, unknown>>)
    : null;
  const auditRows = Array.isArray(resolvedResult?.audit_rows)
    ? (resolvedResult.audit_rows as Array<Record<string, unknown>>)
    : null;
  const idfResult =
    resolvedResult !== null && typeof resolvedResult.idf_result === "object" && resolvedResult.idf_result !== null
      ? (resolvedResult.idf_result as Record<string, unknown>)
      : null;

  if (clientId === null) {
    return (
      <section>
        <h2>Calculation Result</h2>
        <p>BLOCKED</p>
        <p>Calculation Result requires an existing client context.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Calculation Result</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p>
        <Link to={fixationInputPath} state={fixationInputState}>
          Back to Fixation Parameters
        </Link>
      </p>
      <p>
        <Link to={fixationInputPath} state={fixationInputState}>
          Rerun from Fixation Parameters
        </Link>
      </p>
      <p>
        <Link to={`/clients/${clientId}/fixation/history`} state={fixationInputState}>
          View History
        </Link>
      </p>
      {isResultLoading ? <p>Loading latest successful calculation result...</p> : null}
      {resultErrorMessage ? (
        <>
          <p>Unable to load the latest successful calculation result.</p>
          <p>{resultErrorMessage}</p>
        </>
      ) : null}
      {resultMessage ? <p>{resultMessage}</p> : null}
      {resolvedResult ? (
        <>
          <p>
            Result Source: {resultSource === "current" ? "Current backend calculation response" : "Latest saved successful result"}
          </p>
          {trustedResultStatus ? <p>Trusted Result Status: {trustedResultStatus}</p> : null}
          {sourceDataChanged ? <p>Current grants or actual capitalizations differ from the calculation input snapshot. Rerun is required.</p> : null}
          {sourceErrorMessage ? <p>{sourceErrorMessage}</p> : null}
          {renderFields("Backend Calculation Summary", summaryFields)}
          {renderFields("Backend Impact Values", impactFields)}
          {grantResults ? (
            <section>
              <h3>Grant Results</h3>
              <pre>{stringifyValue(grantResults)}</pre>
            </section>
          ) : null}
          {actualCapitalizationResults ? (
            <section>
              <h3>Actual Capitalization Results</h3>
              <pre>{stringifyValue(actualCapitalizationResults)}</pre>
            </section>
          ) : null}
          {idfResult ? (
            <section>
              <h3>IDF Result</h3>
              <pre>{stringifyValue(idfResult)}</pre>
            </section>
          ) : null}
          {validationErrors.length > 0 ? (
            <section>
              <h3>Validation Errors</h3>
              <pre>{stringifyValue(validationErrors)}</pre>
            </section>
          ) : null}
          {auditRows ? (
            <section>
              <h3>Audit Rows</h3>
              <pre>{stringifyValue(auditRows)}</pre>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
