import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  ApiTransportError as ClientApiTransportError,
  type ActualCapitalizationItem,
  type GrantItem,
  getActualCapitalizations,
  getGrants,
} from "../api/clientsApi";
import {
  ApiTransportError,
  type AdmissibleActualCapitalizationPayload,
  type AdmissibleGrantPayload,
  type FixationCollectionState,
  type FixationEligibilityRevision,
  type FixationInclusionDecision,
  type FixationInputPayload,
  type FixationResultResponse,
  type FixationSupportStatus,
  type M07CalculationInputSelection,
  calculateFixation,
  createFixationEligibilityRevision,
  listFixationEligibilityRevisions,
  validateFixation,
} from "../api/fixationApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";

type FixationInputRouteState = {
  clientId?: number;
  clientName?: string;
};

type CalculationResultRouteState = {
  clientId: number;
  clientName?: string;
  inputData: FixationInputPayload;
  result: FixationResultResponse;
  fixationInputPath: string;
  fixationInputState?: FixationInputRouteState;
};

type FormState = {
  calculationId: string;
  calculationVersion: string;
  newEligibilityDate: string;
  parameterSetId: string;
  parameterTaxYear: string;
  parameterEffectiveFrom: string;
  parameterEffectiveTo: string;
  monthlyCap: string;
  exemptionPercentage: string;
  capitalMultiplier: string;
  grantImpactMultiplier: string;
  parameterSourceBasis: string;
  parameterStatus: "" | "accepted" | "rejected";
  parameterAcceptedForUse: boolean;
  parameterAcceptedBy: string;
  parameterDecisionTimestamp: string;
  futureReservationEnabled: boolean;
  futureReservationAmount: string;
  futureReservationSourceBasis: string;
  futureReservationStatus: string;
  futureReservationAcceptedForUse: boolean;
  futureReservationActor: string;
  futureReservationDecisionTimestamp: string;
  idfRelevant: boolean;
  idfId: string;
  idfReductionAmount: string;
  idfOriginalCommutationPercent: string;
  idfCurrentCommutationPercent: string;
  idfCommutationDate: string;
  idfPromoterAgeDate: string;
  idfSourceLabel: string;
};

type ItemDecision = {
  inclusion: "" | FixationInclusionDecision;
  support: "" | FixationSupportStatus;
  sourceBasis: string;
  status: string;
  acceptedForUse: boolean;
  actor: string;
  decisionTimestamp: string;
  conflict: boolean;
  acceptedValue: string;
  indexationMode: "" | "asserted_indexed_amount" | "cbs_system_calculation_required";
  recordedMeaning: string;
};

const initialFormState: FormState = {
  calculationId: "",
  calculationVersion: "",
  newEligibilityDate: "",
  parameterSetId: "",
  parameterTaxYear: "",
  parameterEffectiveFrom: "",
  parameterEffectiveTo: "",
  monthlyCap: "",
  exemptionPercentage: "",
  capitalMultiplier: "",
  grantImpactMultiplier: "",
  parameterSourceBasis: "",
  parameterStatus: "",
  parameterAcceptedForUse: false,
  parameterAcceptedBy: "",
  parameterDecisionTimestamp: "",
  futureReservationEnabled: false,
  futureReservationAmount: "",
  futureReservationSourceBasis: "",
  futureReservationStatus: "",
  futureReservationAcceptedForUse: false,
  futureReservationActor: "",
  futureReservationDecisionTimestamp: "",
  idfRelevant: false,
  idfId: "",
  idfReductionAmount: "",
  idfOriginalCommutationPercent: "",
  idfCurrentCommutationPercent: "",
  idfCommutationDate: "",
  idfPromoterAgeDate: "",
  idfSourceLabel: "",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError || error instanceof ClientApiTransportError) {
    return typeof error.body === "string" ? error.body : JSON.stringify(error.body);
  }
  return error instanceof Error ? error.message : "Unexpected transport error.";
}

function initialDecision(sourceBasis: string | null, recordedMeaning = ""): ItemDecision {
  return {
    inclusion: "",
    support: "",
    sourceBasis: sourceBasis ?? "",
    status: "",
    acceptedForUse: false,
    actor: "",
    decisionTimestamp: "",
    conflict: false,
    acceptedValue: "",
    indexationMode: "",
    recordedMeaning,
  };
}

function finiteNumber(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function exactDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function requiredDecisionError(decision: ItemDecision, label: string): string | null {
  if (!decision.inclusion || !decision.support) {
    return `${label} requires explicit inclusion and support decisions.`;
  }
  if (
    !decision.sourceBasis.trim() ||
    !decision.status.trim() ||
    !decision.actor.trim() ||
    !decision.decisionTimestamp
  ) {
    return `${label} requires source, status, actor and decision timestamp evidence.`;
  }
  if (decision.inclusion === "include" && !decision.acceptedForUse) {
    return `${label} is included but not accepted for use.`;
  }
  if (decision.conflict && finiteNumber(decision.acceptedValue) === null) {
    return `${label} conflict requires an accepted value.`;
  }
  return null;
}

function ResultDiagnostics({
  result,
  selectedRevisionId,
  selection,
  onSelection,
}: {
  result: FixationResultResponse;
  selectedRevisionId: string;
  selection: M07CalculationInputSelection | null;
  onSelection: (selection: M07CalculationInputSelection) => void;
}) {
  const ambiguous = result.m07_resolution?.ambiguous_fields ?? [];
  return (
    <section aria-label="Fixation response">
      <h3>Server Response</h3>
      <p>Calculation status: {result.status}</p>
      {result.status === "success" ? (
        <>
          <p>Normalized eligibility date: {result.eligibility_date}</p>
          <p>Eligibility year: {result.eligibility_year}</p>
          <p>Remaining exempt capital: {result.remaining_exempt_capital}</p>
          <p>Monthly exempt pension: {result.monthly_exempt_pension}</p>
          <p>Grant impact: {result.grant_impact_total}</p>
          <p>Capitalization impact: {result.actual_capitalization_impact}</p>
        </>
      ) : null}
      {result.validation_errors.length > 0 ? (
        <ul aria-label="Validation failures">
          {result.validation_errors.map((error, index) => (
            <li key={`${error.path}-${error.code}-${index}`}>
              {error.path}: {error.message} ({error.code})
            </li>
          ))}
        </ul>
      ) : null}
      {(result.m07_resolution?.missing_fields ?? []).map((field) => (
        <p key={field}>Missing input: {field}. Calculation did not run. Add the date below and retry validation.</p>
      ))}
      {ambiguous.map((field) => (
        <fieldset key={field.field_code}>
          <legend>Ambiguous input: {field.field_code}. Select one candidate; no automatic choice is made.</legend>
          {field.candidates.map((candidate) => {
            const candidateIdentity = candidate.candidate_identities[0];
            return (
              <label key={candidateIdentity}>
                <input
                  type="radio"
                  name={`candidate-${field.field_code}`}
                  checked={selection?.candidate_identity === candidateIdentity}
                  onChange={() =>
                    onSelection({
                      field_code: "eligibility_date",
                      candidate_identity: candidateIdentity,
                      b1_evidence_revision_id: selectedRevisionId,
                    })
                  }
                />
                {candidate.normalized_value} ({candidateIdentity})
              </label>
            );
          })}
        </fieldset>
      ))}
    </section>
  );
}

export function FixationInputScreen() {
  const { clientId: clientIdParam } = useParams<{ clientId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as FixationInputRouteState | null;
  const resolvedClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeState?.clientId;
  const clientId = Number.isInteger(resolvedClientId) && Number(resolvedClientId) > 0 ? Number(resolvedClientId) : null;
  const clientName = routeState?.clientName;
  const [form, setForm] = useState<FormState>(initialFormState);
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [capitalizations, setCapitalizations] = useState<ActualCapitalizationItem[]>([]);
  const [revisions, setRevisions] = useState<FixationEligibilityRevision[]>([]);
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [selection, setSelection] = useState<M07CalculationInputSelection | null>(null);
  const [grantCollectionState, setGrantCollectionState] = useState<FixationCollectionState>("unknown");
  const [capitalizationCollectionState, setCapitalizationCollectionState] = useState<FixationCollectionState>("unknown");
  const [grantDecisions, setGrantDecisions] = useState<Record<string, ItemDecision>>({});
  const [capitalizationDecisions, setCapitalizationDecisions] = useState<Record<string, ItemDecision>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadedClientId, setLoadedClientId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCreatingDate, setIsCreatingDate] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<FixationResultResponse | null>(null);
  const [validatedSignature, setValidatedSignature] = useState<string | null>(null);
  const [calculated, setCalculated] = useState<{ input: FixationInputPayload; result: FixationResultResponse } | null>(null);
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(clientId, location.key);

  useEffect(() => {
    let active = true;
    const clientContext = captureClientContext();
    setForm(initialFormState);
    setGrants([]);
    setCapitalizations([]);
    setRevisions([]);
    setSelectedRevisionId("");
    setSelection(null);
    setGrantCollectionState("unknown");
    setCapitalizationCollectionState("unknown");
    setGrantDecisions({});
    setCapitalizationDecisions({});
    setIsLoading(clientId !== null);
    setLoadedClientId(null);
    setIsSubmitting(false);
    setIsCreatingDate(false);
    setMessage(null);
    setResponse(null);
    setValidatedSignature(null);
    setCalculated(null);

    async function load() {
      if (clientId === null) {
        setMessage("Fixation flow requires an existing client context.");
        setIsLoading(false);
        return;
      }
      try {
        const [loadedGrants, loadedCapitalizations, revisionList] = await Promise.all([
          getGrants(clientId),
          getActualCapitalizations(clientId),
          listFixationEligibilityRevisions(clientId),
        ]);
        if (!active || !isCurrentClientContext(clientContext)) return;
        setGrants(loadedGrants);
        setCapitalizations(loadedCapitalizations);
        setRevisions(revisionList.items);
        setGrantDecisions(
          Object.fromEntries(loadedGrants.map((grant) => [grant.grant_id, initialDecision(grant.notes)])),
        );
        setCapitalizationDecisions(
          Object.fromEntries(
            loadedCapitalizations.map((item) => [
              item.capitalization_id,
              initialDecision(item.source_basis, item.source_label ?? ""),
            ]),
          ),
        );
        setLoadedClientId(clientId);
      } catch (error) {
        if (active && isCurrentClientContext(clientContext)) {
          setLoadedClientId(clientId);
          setMessage(getErrorMessage(error));
        }
      } finally {
        if (active && isCurrentClientContext(clientContext)) setIsLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [captureClientContext, clientId, isCurrentClientContext, location.key]);

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateGrant(grantId: string, patch: Partial<ItemDecision>) {
    setGrantDecisions((current) => ({
      ...current,
      [grantId]: { ...current[grantId], ...patch },
    }));
  }

  function updateCapitalization(capitalizationId: string, patch: Partial<ItemDecision>) {
    setCapitalizationDecisions((current) => ({
      ...current,
      [capitalizationId]: { ...current[capitalizationId], ...patch },
    }));
  }

  function localError(): string | null {
    if (!selectedRevisionId) return "Select an exact finalized B1 revision.";
    if (!form.calculationVersion.trim()) return "Calculation version is required.";
    const parameterText = [
      form.parameterSetId,
      form.parameterTaxYear,
      form.monthlyCap,
      form.exemptionPercentage,
      form.capitalMultiplier,
      form.grantImpactMultiplier,
      form.parameterSourceBasis,
      form.parameterStatus,
      form.parameterAcceptedBy,
      form.parameterDecisionTimestamp,
    ];
    if (parameterText.some((value) => !value.trim())) return "Complete the parameter-set evidence.";
    const numeric = [
      form.parameterTaxYear,
      form.monthlyCap,
      form.exemptionPercentage,
      form.capitalMultiplier,
      form.grantImpactMultiplier,
    ];
    if (numeric.some((value) => finiteNumber(value) === null)) return "Parameter values must be valid numbers.";
    if (grantCollectionState === "items_recorded") {
      if (grants.length === 0) return "Grant collection says items recorded but no grants were loaded.";
      for (const grant of grants) {
        const decision = grantDecisions[grant.grant_id];
        const error = requiredDecisionError(decision, `Grant ${grant.grant_id}`);
        if (error) return error;
        if (!decision.indexationMode) return `Grant ${grant.grant_id} requires an explicit indexation mode.`;
      }
    }
    if (capitalizationCollectionState === "items_recorded") {
      if (capitalizations.length === 0) return "Capitalization collection says items recorded but no items were loaded.";
      for (const item of capitalizations) {
        const decision = capitalizationDecisions[item.capitalization_id];
        const error = requiredDecisionError(decision, `Capitalization ${item.capitalization_id}`);
        if (error) return error;
        if (!decision.recordedMeaning.trim()) return `Capitalization ${item.capitalization_id} requires recorded meaning.`;
      }
    }
    if (form.futureReservationEnabled) {
      const required = [
        form.futureReservationAmount,
        form.futureReservationSourceBasis,
        form.futureReservationStatus,
        form.futureReservationActor,
        form.futureReservationDecisionTimestamp,
      ];
      if (required.some((value) => !value.trim()) || finiteNumber(form.futureReservationAmount) === null) {
        return "Complete the future grant reservation evidence.";
      }
    }
    return null;
  }

  function buildPayload(): FixationInputPayload {
    const grantPayloads: AdmissibleGrantPayload[] =
      grantCollectionState === "items_recorded"
        ? grants.map((grant) => {
            const decision = grantDecisions[grant.grant_id];
            return {
              grant_id: grant.grant_id,
              client_id: clientId as number,
              item_type: "grant",
              employer_name: grant.employer_name,
              nominal_amount: grant.nominal_amount === null ? null : Number(grant.nominal_amount),
              indexed_amount: grant.indexed_amount === null ? null : Number(grant.indexed_amount),
              grant_date: grant.grant_date,
              work_start_date: grant.work_start_date,
              work_end_date: grant.work_end_date,
              inclusion_decision: decision.inclusion as FixationInclusionDecision,
              support_status: decision.support as FixationSupportStatus,
              conflict_indicator: decision.conflict,
              accepted_value: decision.conflict ? Number(decision.acceptedValue) : null,
              indexation_mode: decision.indexationMode as AdmissibleGrantPayload["indexation_mode"],
              source_basis: decision.sourceBasis,
              status: decision.status,
              accepted_for_use: decision.acceptedForUse,
              actor: decision.actor,
              decision_timestamp: decision.decisionTimestamp,
            };
          })
        : [];
    const capitalizationPayloads: AdmissibleActualCapitalizationPayload[] =
      capitalizationCollectionState === "items_recorded"
        ? capitalizations.map((item) => {
            const decision = capitalizationDecisions[item.capitalization_id];
            return {
              capitalization_id: item.capitalization_id,
              item_type: "actual_capitalization",
              amount: Number(item.amount),
              capitalization_date: item.capitalization_date,
              recorded_meaning: decision.recordedMeaning,
              inclusion_decision: decision.inclusion as FixationInclusionDecision,
              support_status: decision.support as FixationSupportStatus,
              conflict_indicator: decision.conflict,
              accepted_value: decision.conflict ? Number(decision.acceptedValue) : null,
              notes: item.notes,
              source_basis: decision.sourceBasis,
              status: decision.status,
              accepted_for_use: decision.acceptedForUse,
              actor: decision.actor,
              decision_timestamp: decision.decisionTimestamp,
            };
          })
        : [];
    return {
      calculation_id: form.calculationId.trim() || null,
      calculation_version: form.calculationVersion,
      m07_input_reference: {
        b1_evidence_revision_id: selectedRevisionId,
        selections: selection ? [selection] : [],
      },
      parameter_set: {
        parameter_set_id: form.parameterSetId,
        client_id: clientId as number,
        tax_year: Number(form.parameterTaxYear),
        effective_from: form.parameterEffectiveFrom || null,
        effective_to: form.parameterEffectiveTo || null,
        values: {
          monthly_cap: Number(form.monthlyCap),
          exemption_percentage: Number(form.exemptionPercentage),
          capital_multiplier: Number(form.capitalMultiplier),
          grant_impact_multiplier: Number(form.grantImpactMultiplier),
        },
        source_basis: form.parameterSourceBasis,
        status: form.parameterStatus as "accepted" | "rejected",
        accepted_for_use: form.parameterAcceptedForUse,
        accepted_by: form.parameterAcceptedBy,
        decision_timestamp: form.parameterDecisionTimestamp,
      },
      grants_collection_state: grantCollectionState,
      grants: grantPayloads,
      future_grant_reservation: form.futureReservationEnabled
        ? {
            amount: Number(form.futureReservationAmount),
            source_basis: form.futureReservationSourceBasis,
            status: form.futureReservationStatus,
            accepted_for_use: form.futureReservationAcceptedForUse,
            actor: form.futureReservationActor,
            decision_timestamp: form.futureReservationDecisionTimestamp,
          }
        : null,
      actual_capitalizations_collection_state: capitalizationCollectionState,
      actual_capitalizations: capitalizationPayloads,
      idf: form.idfRelevant
        ? {
            idf_id: form.idfId,
            reduction_amount: Number(form.idfReductionAmount),
            original_commutation_percent: Number(form.idfOriginalCommutationPercent),
            current_commutation_percent: Number(form.idfCurrentCommutationPercent),
            commutation_date: form.idfCommutationDate,
            promoter_age_date: form.idfPromoterAgeDate,
            source_label: form.idfSourceLabel || null,
          }
        : null,
      metadata: { source_data_version_label: "pkg005-fixation-ui" },
    };
  }

  const payloadSignature = useMemo(() => {
    if (clientId === null) return "";
    return JSON.stringify(buildPayload());
    // buildPayload is a pure projection of these state values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    clientId,
    form,
    selectedRevisionId,
    selection,
    grantCollectionState,
    capitalizationCollectionState,
    grants,
    capitalizations,
    grantDecisions,
    capitalizationDecisions,
  ]);

  async function handleCreateDate(event: FormEvent) {
    event.preventDefault();
    if (clientId === null || loadedClientId !== clientId || !exactDate(form.newEligibilityDate)) {
      setMessage("Eligibility date must be an exact valid YYYY-MM-DD date.");
      return;
    }
    setIsCreatingDate(true);
    setMessage(null);
    const clientContext = captureClientContext();
    try {
      const created = await createFixationEligibilityRevision(clientId, form.newEligibilityDate);
      if (!isCurrentClientContext(clientContext)) return;
      const refreshed = await listFixationEligibilityRevisions(clientId);
      if (!isCurrentClientContext(clientContext)) return;
      setRevisions(refreshed.items);
      setSelectedRevisionId(created.revision_id);
      setSelection(null);
      setValidatedSignature(null);
      setCalculated(null);
      setMessage(`Finalized B1 revision created and selected: ${created.revision_id}`);
    } catch (error) {
      if (isCurrentClientContext(clientContext)) setMessage(getErrorMessage(error));
    } finally {
      if (isCurrentClientContext(clientContext)) setIsCreatingDate(false);
    }
  }

  async function submit(action: "validate" | "calculate") {
    if (clientId === null || loadedClientId !== clientId) return;
    const validationMessage = localError();
    if (validationMessage) {
      setMessage(validationMessage);
      return;
    }
    const payload = buildPayload();
    const signature = JSON.stringify(payload);
    if (action === "calculate" && validatedSignature !== signature) {
      setMessage("Validate the current request successfully before calculation.");
      return;
    }
    setIsSubmitting(true);
    setMessage(null);
    const clientContext = captureClientContext();
    try {
      const result =
        action === "validate"
          ? await validateFixation(clientId, payload)
          : await calculateFixation(clientId, payload);
      if (!isCurrentClientContext(clientContext)) return;
      setResponse(result);
      if (action === "validate") {
        setValidatedSignature(result.status === "success" ? signature : null);
        setMessage(result.status === "success" ? "Server validation passed. Calculation is enabled." : "Server validation failed.");
      } else if (result.status === "success") {
        setCalculated({ input: payload, result });
        setMessage("Calculation succeeded. Continue to the result to save it.");
      } else {
        setCalculated(null);
        setMessage("Calculation failed.");
      }
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setMessage(getErrorMessage(error));
        setValidatedSignature(null);
        setCalculated(null);
      }
    } finally {
      if (isCurrentClientContext(clientContext)) setIsSubmitting(false);
    }
  }

  function selectRevision(revisionId: string) {
    setSelectedRevisionId(revisionId);
    setSelection(null);
    setValidatedSignature(null);
    setCalculated(null);
    setResponse(null);
  }

  function continueToResult() {
    if (
      clientId === null ||
      loadedClientId !== clientId ||
      calculated === null ||
      JSON.stringify(calculated.input) !== payloadSignature
    ) return;
    const fixationInputPath = `/clients/${clientId}/fixation/input`;
    const state: CalculationResultRouteState = {
      clientId,
      clientName,
      inputData: calculated.input,
      result: calculated.result,
      fixationInputPath,
      fixationInputState: { clientId, clientName },
    };
    navigate(`/clients/${clientId}/fixation/result`, { state });
  }

  if (clientId === null) return <section><h2>Fixation Parameters</h2><p>BLOCKED: client context is required.</p></section>;
  if (isLoading || loadedClientId !== clientId) {
    return <section><h2>Fixation Parameters</h2><p>Loading client fixation data...</p></section>;
  }

  const selectedRevision = revisions.find((revision) => revision.revision_id === selectedRevisionId);
  return (
    <section>
      <h2>Fixation Parameters</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p><Link to={`/clients/${clientId}/fixation/workspace`} state={{ clientName }}>Back to fixation workspace</Link></p>

      <section>
        <h3>Eligibility-date B1 evidence</h3>
        <label>
          Finalized B1 revision
          <select value={selectedRevisionId} onChange={(event) => selectRevision(event.target.value)}>
            <option value="">Select an exact revision</option>
            {revisions.map((revision) => (
              <option key={revision.revision_id} value={revision.revision_id}>
                {revision.revision_id} — {revision.status} — {revision.eligibility_outcome}
                {revision.eligibility_dates.length ? ` — ${revision.eligibility_dates.join(", ")}` : ""}
              </option>
            ))}
          </select>
        </label>
        {selectedRevision ? (
          <p>
            Selected revision: {selectedRevision.revision_id}; status: {selectedRevision.status};
            eligibility evidence: {selectedRevision.eligibility_dates.join(", ") || "missing"}.
          </p>
        ) : <p>No revision is selected. The system does not choose latest or current automatically.</p>}
        <form onSubmit={handleCreateDate}>
          <label>
            יום זכאות
            <input
              aria-label="Eligibility Date Evidence"
              type="date"
              value={form.newEligibilityDate}
              onChange={(event) => updateForm("newEligibilityDate", event.target.value)}
            />
          </label>
          <button type="submit" disabled={isCreatingDate}>
            {isCreatingDate ? "Creating finalized revision..." : "Create finalized B1 revision"}
          </button>
        </form>
        <p>The server records the fixed technical workflow actor; the browser supplies no authoritative actor.</p>
      </section>

      <section>
        <h3>M08B accepted parameter set</h3>
        <label>Calculation ID <input value={form.calculationId} onChange={(event) => updateForm("calculationId", event.target.value)} /></label>
        <label>Calculation Version <input value={form.calculationVersion} onChange={(event) => updateForm("calculationVersion", event.target.value)} /></label>
        <label>Parameter Set ID <input value={form.parameterSetId} onChange={(event) => updateForm("parameterSetId", event.target.value)} /></label>
        <label>Parameter Tax Year <input type="number" value={form.parameterTaxYear} onChange={(event) => updateForm("parameterTaxYear", event.target.value)} /></label>
        <label>Effective From <input type="date" value={form.parameterEffectiveFrom} onChange={(event) => updateForm("parameterEffectiveFrom", event.target.value)} /></label>
        <label>Effective To <input type="date" value={form.parameterEffectiveTo} onChange={(event) => updateForm("parameterEffectiveTo", event.target.value)} /></label>
        <label>Monthly Cap <input type="number" step="any" value={form.monthlyCap} onChange={(event) => updateForm("monthlyCap", event.target.value)} /></label>
        <label>Exemption Percentage <input type="number" step="any" value={form.exemptionPercentage} onChange={(event) => updateForm("exemptionPercentage", event.target.value)} /></label>
        <label>Capital Multiplier <input type="number" step="any" value={form.capitalMultiplier} onChange={(event) => updateForm("capitalMultiplier", event.target.value)} /></label>
        <label>Grant Impact Multiplier <input type="number" step="any" value={form.grantImpactMultiplier} onChange={(event) => updateForm("grantImpactMultiplier", event.target.value)} /></label>
        <label>Parameter Source Basis <input value={form.parameterSourceBasis} onChange={(event) => updateForm("parameterSourceBasis", event.target.value)} /></label>
        <label>Parameter Status
          <select value={form.parameterStatus} onChange={(event) => updateForm("parameterStatus", event.target.value as FormState["parameterStatus"])}>
            <option value="">Select</option><option value="accepted">accepted</option><option value="rejected">rejected</option>
          </select>
        </label>
        <label><input type="checkbox" checked={form.parameterAcceptedForUse} onChange={(event) => updateForm("parameterAcceptedForUse", event.target.checked)} /> Parameter accepted for use</label>
        <label>Parameter Accepted By <input value={form.parameterAcceptedBy} onChange={(event) => updateForm("parameterAcceptedBy", event.target.value)} /></label>
        <label>Parameter Decision Timestamp <input type="datetime-local" value={form.parameterDecisionTimestamp} onChange={(event) => updateForm("parameterDecisionTimestamp", event.target.value)} /></label>
      </section>

      <section>
        <h3>M08C grants</h3>
        <label>Grant Collection State
          <select value={grantCollectionState} onChange={(event) => setGrantCollectionState(event.target.value as FixationCollectionState)}>
            <option value="unknown">unknown</option><option value="not_collected">not_collected</option>
            <option value="confirmed_none">confirmed_none</option><option value="items_recorded">items_recorded</option>
          </select>
        </label>
        {grantCollectionState === "items_recorded" ? grants.map((grant) => {
          const decision = grantDecisions[grant.grant_id];
          return <fieldset key={grant.grant_id}><legend>Grant {grant.grant_id}</legend>
            <p>{grant.employer_name} — indexed amount {grant.indexed_amount}</p>
            <label>Grant Inclusion <select value={decision.inclusion} onChange={(event) => updateGrant(grant.grant_id, { inclusion: event.target.value as ItemDecision["inclusion"] })}><option value="">Select</option><option value="include">include</option><option value="exclude">exclude</option></select></label>
            <label>Grant Support <select value={decision.support} onChange={(event) => updateGrant(grant.grant_id, { support: event.target.value as ItemDecision["support"] })}><option value="">Select</option><option value="supported">supported</option><option value="unsupported">unsupported</option><option value="requires_special_handling">requires_special_handling</option></select></label>
            <label>Indexation Mode <select value={decision.indexationMode} onChange={(event) => updateGrant(grant.grant_id, { indexationMode: event.target.value as ItemDecision["indexationMode"] })}><option value="">Select mode</option><option value="asserted_indexed_amount">asserted indexed amount</option><option value="cbs_system_calculation_required">CBS system calculation required</option></select></label>
            <label>Source Basis <input value={decision.sourceBasis} onChange={(event) => updateGrant(grant.grant_id, { sourceBasis: event.target.value })} /></label>
            <label>Evidence Status <input value={decision.status} onChange={(event) => updateGrant(grant.grant_id, { status: event.target.value })} /></label>
            <label>Decision Actor <input value={decision.actor} onChange={(event) => updateGrant(grant.grant_id, { actor: event.target.value })} /></label>
            <label>Decision Timestamp <input type="datetime-local" value={decision.decisionTimestamp} onChange={(event) => updateGrant(grant.grant_id, { decisionTimestamp: event.target.value })} /></label>
            <label><input type="checkbox" checked={decision.acceptedForUse} onChange={(event) => updateGrant(grant.grant_id, { acceptedForUse: event.target.checked })} /> Accepted for use</label>
            <label><input type="checkbox" checked={decision.conflict} onChange={(event) => updateGrant(grant.grant_id, { conflict: event.target.checked })} /> Conflict</label>
            {decision.conflict ? <label>Accepted Value <input type="number" step="any" value={decision.acceptedValue} onChange={(event) => updateGrant(grant.grant_id, { acceptedValue: event.target.value })} /></label> : null}
          </fieldset>;
        }) : null}
      </section>

      <section>
        <h3>M08C actual capitalizations</h3>
        <label>Actual Capitalization Collection State
          <select value={capitalizationCollectionState} onChange={(event) => setCapitalizationCollectionState(event.target.value as FixationCollectionState)}>
            <option value="unknown">unknown</option><option value="not_collected">not_collected</option>
            <option value="confirmed_none">confirmed_none</option><option value="items_recorded">items_recorded</option>
          </select>
        </label>
        {capitalizationCollectionState === "items_recorded" ? capitalizations.map((item) => {
          const decision = capitalizationDecisions[item.capitalization_id];
          return <fieldset key={item.capitalization_id}><legend>Capitalization {item.capitalization_id}</legend>
            <p>Amount {item.amount} — {item.capitalization_date}</p>
            <label>Capitalization Inclusion <select value={decision.inclusion} onChange={(event) => updateCapitalization(item.capitalization_id, { inclusion: event.target.value as ItemDecision["inclusion"] })}><option value="">Select</option><option value="include">include</option><option value="exclude">exclude</option></select></label>
            <label>Capitalization Support <select value={decision.support} onChange={(event) => updateCapitalization(item.capitalization_id, { support: event.target.value as ItemDecision["support"] })}><option value="">Select</option><option value="supported">supported</option><option value="unsupported">unsupported</option><option value="requires_special_handling">requires_special_handling</option></select></label>
            <label>Recorded Meaning <input value={decision.recordedMeaning} onChange={(event) => updateCapitalization(item.capitalization_id, { recordedMeaning: event.target.value })} /></label>
            <label>Source Basis <input value={decision.sourceBasis} onChange={(event) => updateCapitalization(item.capitalization_id, { sourceBasis: event.target.value })} /></label>
            <label>Evidence Status <input value={decision.status} onChange={(event) => updateCapitalization(item.capitalization_id, { status: event.target.value })} /></label>
            <label>Decision Actor <input value={decision.actor} onChange={(event) => updateCapitalization(item.capitalization_id, { actor: event.target.value })} /></label>
            <label>Decision Timestamp <input type="datetime-local" value={decision.decisionTimestamp} onChange={(event) => updateCapitalization(item.capitalization_id, { decisionTimestamp: event.target.value })} /></label>
            <label><input type="checkbox" checked={decision.acceptedForUse} onChange={(event) => updateCapitalization(item.capitalization_id, { acceptedForUse: event.target.checked })} /> Accepted for use</label>
            <label><input type="checkbox" checked={decision.conflict} onChange={(event) => updateCapitalization(item.capitalization_id, { conflict: event.target.checked })} /> Conflict</label>
            {decision.conflict ? <label>Accepted Value <input type="number" step="any" value={decision.acceptedValue} onChange={(event) => updateCapitalization(item.capitalization_id, { acceptedValue: event.target.value })} /></label> : null}
          </fieldset>;
        }) : null}
      </section>

      <section>
        <h3>Future grant reservation</h3>
        <label><input type="checkbox" checked={form.futureReservationEnabled} onChange={(event) => updateForm("futureReservationEnabled", event.target.checked)} /> Include future grant reservation</label>
        {form.futureReservationEnabled ? <>
          <label>Reservation Amount <input type="number" step="any" value={form.futureReservationAmount} onChange={(event) => updateForm("futureReservationAmount", event.target.value)} /></label>
          <label>Reservation Source Basis <input value={form.futureReservationSourceBasis} onChange={(event) => updateForm("futureReservationSourceBasis", event.target.value)} /></label>
          <label>Reservation Status <input value={form.futureReservationStatus} onChange={(event) => updateForm("futureReservationStatus", event.target.value)} /></label>
          <label>Reservation Actor <input value={form.futureReservationActor} onChange={(event) => updateForm("futureReservationActor", event.target.value)} /></label>
          <label>Reservation Decision Timestamp <input type="datetime-local" value={form.futureReservationDecisionTimestamp} onChange={(event) => updateForm("futureReservationDecisionTimestamp", event.target.value)} /></label>
          <label><input type="checkbox" checked={form.futureReservationAcceptedForUse} onChange={(event) => updateForm("futureReservationAcceptedForUse", event.target.checked)} /> Reservation accepted for use</label>
        </> : null}
      </section>

      <p>
        <button type="button" disabled={isSubmitting} onClick={() => void submit("validate")}>Validate Inputs</button>
        <button type="button" disabled={isSubmitting || validatedSignature !== payloadSignature} onClick={() => void submit("calculate")}>Run Calculation</button>
        <button type="button" disabled={calculated === null || JSON.stringify(calculated.input) !== payloadSignature} onClick={continueToResult}>Continue to Result</button>
      </p>
      {message ? <p role="status">{message}</p> : null}
      {response ? (
        <ResultDiagnostics
          result={response}
          selectedRevisionId={selectedRevisionId}
          selection={selection}
          onSelection={(next) => {
            setSelection(next);
            setValidatedSignature(null);
            setCalculated(null);
          }}
        />
      ) : null}
    </section>
  );
}
