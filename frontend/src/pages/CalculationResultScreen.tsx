import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type FixationInputPayload,
  type FixationResultResponse,
  getFixationHistory,
  getFixationRunDetail,
  saveFixation,
} from "../api/fixationApi";

type ResultRouteState = {
  clientId?: number;
  clientName?: string;
  inputData?: FixationInputPayload;
  result?: FixationResultResponse;
  fixationInputPath?: string;
  fixationInputState?: { clientId?: number; clientName?: string };
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return typeof error.body === "string" ? error.body : JSON.stringify(error.body);
  }
  return error instanceof Error ? error.message : "Unexpected transport error.";
}

function valueAt(record: Record<string, unknown> | null, key: string): unknown {
  return record?.[key];
}

function ResultPresentation({
  result,
  input,
  clientId,
}: {
  result: Record<string, unknown>;
  input: Record<string, unknown>;
  clientId: number;
}) {
  const reference = valueAt(input, "m07_input_reference") as Record<string, unknown> | undefined;
  const resolution = valueAt(input, "m07_resolution") as Record<string, unknown> | undefined;
  const parameterSet = valueAt(input, "parameter_set") as Record<string, unknown> | undefined;
  const selections = Array.isArray(reference?.selections) ? reference.selections : [];
  const warnings = [
    ...(Array.isArray(valueAt(result, "validation_errors")) ? valueAt(result, "validation_errors") as unknown[] : []),
    ...(Array.isArray(valueAt(result, "audit_rows"))
      ? (valueAt(result, "audit_rows") as Array<Record<string, unknown>>)
          .filter((row) => String(row.label ?? "").toLowerCase().includes("warning"))
      : []),
  ];
  return (
    <>
      <section>
        <h3>Calculation summary</h3>
        <ul>
          <li>Client ID: {clientId}</li>
          <li>Status: {String(valueAt(result, "status") ?? "unknown")}</li>
          <li>Calculation ID: {String(valueAt(result, "calculation_id") ?? "not provided")}</li>
          <li>Calculation version: {String(valueAt(result, "calculation_version") ?? "not provided")}</li>
          <li>Normalized eligibility date: {String(valueAt(result, "eligibility_date") ?? valueAt(input, "eligibility_date") ?? "unavailable")}</li>
          <li>Eligibility year: {String(valueAt(result, "eligibility_year") ?? valueAt(input, "eligibility_year") ?? "unavailable")}</li>
          <li>Selected B1 revision: {String(reference?.b1_evidence_revision_id ?? resolution?.b1_evidence_revision_id ?? "unavailable")}</li>
          <li>Resolver scope/version: {String(resolution?.calculation_scope ?? "m08a_fixation")} / {String(resolution?.manifest_version ?? "1")}</li>
          <li>Resolver fingerprint: {String(resolution?.fingerprint ?? "available after saved-run reopen")}</li>
          <li>Parameter set: {String(parameterSet?.parameter_set_id ?? "unavailable")}</li>
        </ul>
      </section>
      <section>
        <h3>Material result</h3>
        <ul>
          <li>Initial exempt capital: {String(valueAt(result, "initial_exempt_capital") ?? "unavailable")}</li>
          <li>Grant impact: {String(valueAt(result, "grant_impact_total") ?? "unavailable")}</li>
          <li>Future grant impact: {String(valueAt(result, "future_grant_impact") ?? "unavailable")}</li>
          <li>Capitalization impact: {String(valueAt(result, "actual_capitalization_impact") ?? "unavailable")}</li>
          <li>Total impact: {String(valueAt(result, "total_impact") ?? "unavailable")}</li>
          <li>Remaining exempt capital: {String(valueAt(result, "remaining_exempt_capital") ?? "unavailable")}</li>
          <li>Monthly exempt pension: {String(valueAt(result, "monthly_exempt_pension") ?? "unavailable")}</li>
        </ul>
      </section>
      <section>
        <h3>Selection, effects and audit</h3>
        <p>Explicit eligibility selection: {selections.length ? JSON.stringify(selections) : "not required"}</p>
        <p>Grant effects: {JSON.stringify(valueAt(result, "grant_results") ?? [])}</p>
        <p>Capitalization effects: {JSON.stringify(valueAt(result, "actual_capitalization_results") ?? [])}</p>
        <p>Warnings/failures: {warnings.length ? JSON.stringify(warnings) : "none"}</p>
        <p>Audit evidence: {JSON.stringify(valueAt(result, "audit_rows") ?? [])}</p>
      </section>
    </>
  );
}

export function CalculationResultScreen() {
  const { clientId: clientIdParam } = useParams<{ clientId: string }>();
  const location = useLocation();
  const routeState = location.state as ResultRouteState | null;
  const rawClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeState?.clientId;
  const clientId = Number.isInteger(rawClientId) && Number(rawClientId) > 0 ? Number(rawClientId) : null;
  const routeStateMatchesClient = clientId !== null && routeState?.clientId === clientId;
  const [input, setInput] = useState<Record<string, unknown> | null>(
    routeStateMatchesClient ? routeState?.inputData as unknown as Record<string, unknown> ?? null : null,
  );
  const [result, setResult] = useState<Record<string, unknown> | null>(
    routeStateMatchesClient ? routeState?.result as unknown as Record<string, unknown> ?? null : null,
  );
  const [stateClientId, setStateClientId] = useState<number | null>(
    routeStateMatchesClient ? clientId : null,
  );
  const [loadedRunId, setLoadedRunId] = useState<number | null>(null);
  const [loadedRunDate, setLoadedRunDate] = useState<string | null>(null);
  const [savedRunId, setSavedRunId] = useState<number | null>(null);
  const [savedStatus, setSavedStatus] = useState<string | null>(null);
  const [savedRunDate, setSavedRunDate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(clientId !== null && !routeStateMatchesClient);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const activeClientIdRef = useRef(clientId);
  activeClientIdRef.current = clientId;

  useEffect(() => {
    let active = true;
    setInput(null);
    setResult(null);
    setStateClientId(null);
    setLoadedRunId(null);
    setLoadedRunDate(null);
    setSavedRunId(null);
    setSavedStatus(null);
    setSavedRunDate(null);
    setIsSaving(false);
    setMessage(null);

    async function loadLatest() {
      if (clientId === null) {
        setIsLoading(false);
        return;
      }
      if (routeStateMatchesClient && routeState?.inputData && routeState.result) {
        setInput(routeState.inputData as unknown as Record<string, unknown>);
        setResult(routeState.result as unknown as Record<string, unknown>);
        setStateClientId(clientId);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const history = await getFixationHistory(clientId);
        const latest = history.find((entry) => entry.status === "success");
        if (!latest) {
          if (active) {
            setStateClientId(clientId);
            setMessage("No successful saved run is available for this client.");
          }
          return;
        }
        const detail = await getFixationRunDetail(clientId, latest.run_id);
        if (!active) return;
        setInput(detail.input_snapshot);
        setResult(detail.result);
        setLoadedRunId(latest.run_id);
        setLoadedRunDate(latest.created_at);
        setStateClientId(clientId);
      } catch (error) {
        if (active) {
          setStateClientId(clientId);
          setMessage(getErrorMessage(error));
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void loadLatest();
    return () => {
      active = false;
    };
  }, [clientId, routeStateMatchesClient, routeState?.inputData, routeState?.result]);

  async function handleSave() {
    if (clientId === null || stateClientId !== clientId || input === null || result?.status !== "success") return;
    setIsSaving(true);
    setMessage(null);
    try {
      const saved = await saveFixation({
        client_id: clientId,
        input_data: input as unknown as FixationInputPayload,
      });
      if (activeClientIdRef.current !== clientId) return;
      setSavedRunId(saved.run_id);
      setSavedStatus(saved.status);
      setSavedRunDate(saved.created_at);
    } catch (error) {
      if (activeClientIdRef.current === clientId) setMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  if (clientId === null) return <section><h2>Calculation Result</h2><p>BLOCKED: client context is required.</p></section>;
  if (stateClientId !== clientId) {
    return <section><h2>Calculation Result</h2><p>Loading latest successful saved run...</p></section>;
  }
  const inputPath = routeStateMatchesClient
    ? routeState?.fixationInputPath ?? `/clients/${clientId}/fixation/input`
    : `/clients/${clientId}/fixation/input`;
  const clientName = routeStateMatchesClient ? routeState?.clientName : undefined;
  const navigationState = { clientId, clientName };
  return (
    <section>
      <h2>Calculation Result</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p><Link to={inputPath} state={navigationState}>Back to Fixation Parameters</Link></p>
      <p><Link to={`/clients/${clientId}/fixation/history`} state={navigationState}>Saved run history</Link></p>
      {isLoading ? <p>Loading latest successful saved run...</p> : null}
      {loadedRunId !== null ? <p>Reopened saved run: {loadedRunId}; saved at: {loadedRunDate ?? "unknown"}.</p> : null}
      {result && input ? <ResultPresentation result={result} input={input} clientId={clientId} /> : null}
      <button type="button" disabled={isSaving || result?.status !== "success" || loadedRunId !== null} onClick={() => void handleSave()}>
        {isSaving ? "Saving Result..." : "Save Result"}
      </button>
      {savedRunId !== null ? (
        <section>
          <p>Run saved. Run ID: {savedRunId}; status: {savedStatus}; saved at: {savedRunDate}.</p>
          <Link to={`/clients/${clientId}/fixation/runs/${savedRunId}`} state={navigationState}>
            Reopen saved run
          </Link>
        </section>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
