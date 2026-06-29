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
  type FixationReviewCollectionState,
  type PlannerReviewContextPayload,
  getFixationHistory,
  getFixationRunDetail,
  saveFixation,
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
  activeSessionReviewContext?: ActiveSessionReviewContext;
};

type DisplayField = {
  label: string;
  value: unknown;
};

type SavedCalculationRecordIdentifiers = {
  runId: number;
  createdAt: string | null;
};

type ActiveSessionSourceReference = {
  domain: "grants" | "actual_capitalizations";
  source_item_id: string;
  record_id: string;
  label: string | null;
  disposition: "include" | "exclude";
};

type ActiveSessionSourceMetadata = {
  domain: "actual_capitalizations";
  source_item_id: string;
  record_id: string;
  source_basis: string | null;
  planner_assertion: string | null;
  planner_assertion_basis: string | null;
};

type ActiveSessionReviewContext = {
  grants_collection_state: FixationReviewCollectionState;
  actual_capitalizations_collection_state: FixationReviewCollectionState;
  included_source_references: ActiveSessionSourceReference[];
  excluded_source_references: ActiveSessionSourceReference[];
  source_metadata_context: ActiveSessionSourceMetadata[];
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

function renderConvertedInputSummary(inputData: FixationInputPayload | null) {
  if (inputData === null) {
    return null;
  }

  return (
    <section>
      <h3>Converted Input Used For Calculation</h3>
      <p>This summary is based only on the converted calculation input used for this calculation.</p>
      <ul>
        <li>Calculation Version: {inputData.calculation_version}</li>
        <li>Eligibility Date: {inputData.eligibility_date}</li>
        <li>Eligibility Year: {inputData.eligibility_year}</li>
        <li>Monthly Cap: {inputData.monthly_cap}</li>
        <li>Future Grant Reserved: {inputData.future_grant_reserved}</li>
        <li>Grant Inputs: {inputData.grants.length}</li>
        <li>Actual Capitalization Inputs: {inputData.actual_capitalizations.length}</li>
        <li>IDF Input: {inputData.idf === null ? "none" : "provided"}</li>
      </ul>
    </section>
  );
}

function renderSourceReferences(title: string, references: ActiveSessionSourceReference[]) {
  if (references.length === 0) {
    return null;
  }

  return (
    <section>
      <h4>{title}</h4>
      <ul>
        {references.map((reference) => (
          <li key={`${reference.domain}-${reference.source_item_id}-${reference.disposition}`}>
            <strong>{reference.source_item_id}</strong> ({reference.domain}, record {reference.record_id})
            {reference.label ? ` - ${reference.label}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

function renderSourceMetadataContext(metadata: ActiveSessionSourceMetadata[]) {
  if (metadata.length === 0) {
    return null;
  }

  return (
    <section>
      <h4>Source And Planner Context</h4>
      <ul>
        {metadata.map((entry) => (
          <li key={`${entry.domain}-${entry.source_item_id}`}>
            <p>Source Item ID: {entry.source_item_id}</p>
            {entry.source_basis ? <p>Source Basis: {entry.source_basis}</p> : null}
            {entry.planner_assertion ? <p>Planner Assertion: {entry.planner_assertion}</p> : null}
            {entry.planner_assertion_basis ? <p>Planner Assertion Basis: {entry.planner_assertion_basis}</p> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function renderActiveSessionReviewContext(context: ActiveSessionReviewContext | undefined) {
  if (context === undefined) {
    return null;
  }

  return (
    <section>
      <h3>Current Workflow Review Context</h3>
      <p>This context is available only in the current active workflow.</p>
      <ul>
        <li>Grants Collection State: {context.grants_collection_state}</li>
        <li>Actual Capitalizations Collection State: {context.actual_capitalizations_collection_state}</li>
      </ul>
      {renderSourceReferences("Included Records", context.included_source_references)}
      {renderSourceReferences("Excluded Records", context.excluded_source_references)}
      {renderSourceMetadataContext(context.source_metadata_context)}
    </section>
  );
}

function buildSavedPlannerReviewContext(
  context: ActiveSessionReviewContext | undefined,
): PlannerReviewContextPayload | undefined {
  if (context === undefined) {
    return undefined;
  }

  return {
    grants: {
      collection_state: context.grants_collection_state,
      included_source_reference_ids: context.included_source_references
        .filter((reference) => reference.domain === "grants")
        .map((reference) => reference.source_item_id),
      excluded_source_reference_ids: context.excluded_source_references
        .filter((reference) => reference.domain === "grants")
        .map((reference) => reference.source_item_id),
    },
    actual_capitalizations: {
      collection_state: context.actual_capitalizations_collection_state,
      included_source_reference_ids: context.included_source_references
        .filter((reference) => reference.domain === "actual_capitalizations")
        .map((reference) => reference.source_item_id),
      excluded_source_reference_ids: context.excluded_source_references
        .filter((reference) => reference.domain === "actual_capitalizations")
        .map((reference) => reference.source_item_id),
    },
  };
}

function renderReferenceIds(ids: string[]) {
  if (ids.length === 0) {
    return "none";
  }

  return ids.join(", ");
}

function renderSavedPlannerReviewContext(context: PlannerReviewContextPayload | null) {
  if (context === null) {
    return <p>לא נשמר הקשר בדיקה עבור רשומת חישוב זו.</p>;
  }

  return (
    <section>
      <h3>הקשר בדיקה שנשמר עם רשומת החישוב</h3>
      <p>מידע זה מוצג כהקשר בדיקה בלבד</p>
      <h4>מצב איסוף נתונים בעת השמירה</h4>
      <ul>
        <li>grants: {context.grants.collection_state}</li>
        <li>actual_capitalizations: {context.actual_capitalizations.collection_state}</li>
      </ul>
      <h4>רשומות שסומנו לכלילה</h4>
      <ul>
        <li>grants: {renderReferenceIds(context.grants.included_source_reference_ids)}</li>
        <li>actual_capitalizations: {renderReferenceIds(context.actual_capitalizations.included_source_reference_ids)}</li>
      </ul>
      <h4>רשומות שסומנו להחרגה</h4>
      <ul>
        <li>grants: {renderReferenceIds(context.grants.excluded_source_reference_ids)}</li>
        <li>actual_capitalizations: {renderReferenceIds(context.actual_capitalizations.excluded_source_reference_ids)}</li>
      </ul>
    </section>
  );
}

function renderSavedCalculationRecordIdentifiers(identifiers: SavedCalculationRecordIdentifiers | null) {
  if (identifiers === null) {
    return null;
  }

  return (
    <section>
      <h3>רשומת חישוב שמורה</h3>
      <ul>
        <li>מזהה רשומה: {identifiers.runId}</li>
        {identifiers.createdAt ? <li>נוצרה בתאריך: {identifiers.createdAt}</li> : null}
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
  const activeSessionReviewContext = routeState?.activeSessionReviewContext;
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
  const [savedPlannerReviewContext, setSavedPlannerReviewContext] = useState<PlannerReviewContextPayload | null>(null);
  const [savedCalculationRecordIdentifiers, setSavedCalculationRecordIdentifiers] =
    useState<SavedCalculationRecordIdentifiers | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [savedRunId, setSavedRunId] = useState<number | null>(null);

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
          setSavedPlannerReviewContext(null);
          setSavedCalculationRecordIdentifiers(null);
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
          setSavedPlannerReviewContext(null);
          setSavedCalculationRecordIdentifiers(null);
          setResultSource(null);
          setResultMessage("Latest successful calculation result could not be loaded.");
          return;
        }

        setResolvedResult(detail.result as FixationResultResponse);
        setResolvedInputData(detail.input_snapshot as unknown as FixationInputPayload);
        setSavedPlannerReviewContext(detail.planner_review_context ?? null);
        setSavedCalculationRecordIdentifiers({
          runId: Number(detail.run.run_id),
          createdAt: typeof detail.run.created_at === "string" ? detail.run.created_at : null,
        });
        setResultSource("latest");
        setResultMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setResolvedResult(null);
        setResolvedInputData(null);
        setSavedPlannerReviewContext(null);
        setSavedCalculationRecordIdentifiers(null);
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
  const canSaveCurrentResult =
    resultSource === "current" &&
    resolvedInputData !== null &&
    resolvedResult?.status === "success" &&
    !isSourceLoading &&
    sourceErrorMessage === null &&
    !sourceDataChanged;
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

  async function handleSaveResult() {
    if (clientId === null || resolvedInputData === null || !canSaveCurrentResult) {
      return;
    }

    setIsSaving(true);
    setSaveErrorMessage(null);
    setSavedRunId(null);

    try {
      const plannerReviewContext = buildSavedPlannerReviewContext(activeSessionReviewContext);
      const response = await saveFixation({
        client_id: clientId,
        input_data: resolvedInputData as unknown as Record<string, unknown>,
        ...(plannerReviewContext === undefined ? {} : { planner_review_context: plannerReviewContext }),
      });
      setSavedRunId(response.run_id);
    } catch (error) {
      setSaveErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

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
          פתח רשומת חישוב שמורה
        </Link>
      </p>
      <p>
        <button type="button" disabled={!canSaveCurrentResult || isSaving} onClick={() => void handleSaveResult()}>
          {isSaving ? "Saving Result..." : "Save Result"}
        </button>
      </p>
      {savedRunId !== null ? (
        <>
          <p>Result saved successfully. Run ID: {savedRunId}</p>
          <p>
            <Link to={`/clients/${clientId}/fixation/history`} state={fixationInputState}>
              פתח רשומת חישוב שמורה
            </Link>
          </p>
        </>
      ) : null}
      {saveErrorMessage ? (
        <>
          <p>Unable to save the current calculation result.</p>
          <p>{saveErrorMessage}</p>
        </>
      ) : null}
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
          <h3>Calculation Outcome</h3>
          <p>
            Result Source: {resultSource === "current" ? "Current backend calculation response" : "תוצאת החישוב השמורה"}
          </p>
          {renderSavedCalculationRecordIdentifiers(savedCalculationRecordIdentifiers)}
          {trustedResultStatus ? <p>Trusted Result Status: {trustedResultStatus}</p> : null}
          {sourceDataChanged ? <p>Current grants or actual capitalizations differ from the calculation input snapshot. Rerun is required.</p> : null}
          {sourceErrorMessage ? <p>{sourceErrorMessage}</p> : null}
          {renderFields("Backend Calculation Summary", summaryFields)}
          {renderFields("Backend Impact Values", impactFields)}
          {renderConvertedInputSummary(resolvedInputData)}
          {resultSource === "latest" ? renderSavedPlannerReviewContext(savedPlannerReviewContext) : null}
          {renderActiveSessionReviewContext(activeSessionReviewContext)}
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
