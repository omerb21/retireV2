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
  type FixationActualCapitalizationInputPayload,
  type FixationGrantInputPayload,
  type FixationIdfInputPayload,
  type FixationInputPayload,
  type FixationResultResponse,
  calculateFixation,
  validateFixation,
} from "../api/fixationApi";

type FormState = {
  calculationId: string;
  calculationVersion: string;
  eligibilityDate: string;
  eligibilityYear: string;
  monthlyCap: string;
  exemptionPercentage: string;
  capitalMultiplier: string;
  futureGrantReserved: string;
  idfRelevant: boolean;
  idfId: string;
  idfReductionAmount: string;
  idfOriginalCommutationPercent: string;
  idfCurrentCommutationPercent: string;
  idfCommutationDate: string;
  idfPromoterAgeDate: string;
  idfSourceLabel: string;
};

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

const initialFormState: FormState = {
  calculationId: "",
  calculationVersion: "",
  eligibilityDate: "",
  eligibilityYear: "",
  monthlyCap: "",
  exemptionPercentage: "",
  capitalMultiplier: "",
  futureGrantReserved: "",
  idfRelevant: false,
  idfId: "",
  idfReductionAmount: "",
  idfOriginalCommutationPercent: "",
  idfCurrentCommutationPercent: "",
  idfCommutationDate: "",
  idfPromoterAgeDate: "",
  idfSourceLabel: "",
};

function stringifyValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
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

function parseNumber(value: number | string | null): number | null {
  if (value === null) {
    return null;
  }

  const parsedValue = typeof value === "number" ? value : Number(value);
  return Number.isNaN(parsedValue) ? null : parsedValue;
}

function isValidDateValue(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

function getDateYear(value: string): number | null {
  if (!isValidDateValue(value)) {
    return null;
  }

  return Number(value.slice(0, 4));
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

function buildIdfPayload(formState: FormState): FixationIdfInputPayload | null {
  if (!formState.idfRelevant) {
    return null;
  }

  return {
    idf_id: formState.idfId,
    reduction_amount: Number(formState.idfReductionAmount),
    original_commutation_percent: Number(formState.idfOriginalCommutationPercent),
    current_commutation_percent: Number(formState.idfCurrentCommutationPercent),
    commutation_date: formState.idfCommutationDate,
    promoter_age_date: formState.idfPromoterAgeDate,
    source_label: formState.idfSourceLabel.trim() === "" ? null : formState.idfSourceLabel,
  };
}

function buildPayload(
  formState: FormState,
  grants: GrantItem[],
  actualCapitalizations: ActualCapitalizationItem[],
): FixationInputPayload {
  return {
    calculation_id: formState.calculationId.trim() === "" ? null : formState.calculationId,
    calculation_version: formState.calculationVersion,
    eligibility_date: formState.eligibilityDate,
    eligibility_year: Number(formState.eligibilityYear),
    monthly_cap: Number(formState.monthlyCap),
    exemption_percentage: Number(formState.exemptionPercentage),
    capital_multiplier: Number(formState.capitalMultiplier),
    grants: grants.map(mapGrantToPayload),
    future_grant_reserved: Number(formState.futureGrantReserved),
    actual_capitalizations: actualCapitalizations.map(mapActualCapitalizationToPayload),
    idf_relevant: formState.idfRelevant,
    idf: buildIdfPayload(formState),
  };
}

function validateForm(formState: FormState): string | null {
  const requiredFields: Array<[string, string]> = [
    [formState.calculationVersion, "Calculation version is required."],
    [formState.eligibilityDate, "Eligibility date is required."],
    [formState.eligibilityYear, "Eligibility year is required."],
    [formState.monthlyCap, "Monthly cap is required."],
    [formState.exemptionPercentage, "Exemption percentage is required."],
    [formState.capitalMultiplier, "Capital multiplier is required."],
    [formState.futureGrantReserved, "Future grant reserved is required."],
  ];

  const missingField = requiredFields.find(([value]) => value.trim() === "");
  if (missingField) {
    return missingField[1];
  }

  if (!isValidDateValue(formState.eligibilityDate)) {
    return "Eligibility date must be a valid date.";
  }

  const eligibilityYear = Number(formState.eligibilityYear);
  const monthlyCap = Number(formState.monthlyCap);
  const exemptionPercentage = Number(formState.exemptionPercentage);
  const capitalMultiplier = Number(formState.capitalMultiplier);
  const futureGrantReserved = Number(formState.futureGrantReserved);
  const eligibilityDateYear = getDateYear(formState.eligibilityDate);

  if ([eligibilityYear, monthlyCap, exemptionPercentage, capitalMultiplier, futureGrantReserved].some(Number.isNaN)) {
    return "Numeric fields must contain valid numbers.";
  }

  if (!Number.isInteger(eligibilityYear)) {
    return "Eligibility year must be a whole number.";
  }

  if (eligibilityDateYear !== eligibilityYear) {
    return "Eligibility year must match the eligibility date year.";
  }

  if (monthlyCap <= 0) {
    return "Monthly cap must be greater than zero.";
  }

  if (exemptionPercentage < 0 || exemptionPercentage > 1) {
    return "Exemption percentage must be between 0 and 1.";
  }

  if (capitalMultiplier <= 0) {
    return "Capital multiplier must be greater than zero.";
  }

  if (futureGrantReserved < 0) {
    return "Future grant reserved must be non-negative.";
  }

  if (!formState.idfRelevant) {
    return null;
  }

  const idfRequiredFields: Array<[string, string]> = [
    [formState.idfId, "IDF ID is required when IDF is enabled."],
    [formState.idfReductionAmount, "IDF reduction amount is required when IDF is enabled."],
    [
      formState.idfOriginalCommutationPercent,
      "IDF original commutation percent is required when IDF is enabled.",
    ],
    [
      formState.idfCurrentCommutationPercent,
      "IDF current commutation percent is required when IDF is enabled.",
    ],
    [formState.idfCommutationDate, "IDF commutation date is required when IDF is enabled."],
    [formState.idfPromoterAgeDate, "IDF promoter age date is required when IDF is enabled."],
  ];

  const missingIdfField = idfRequiredFields.find(([value]) => value.trim() === "");
  if (missingIdfField) {
    return missingIdfField[1];
  }

  if (!isValidDateValue(formState.idfCommutationDate) || !isValidDateValue(formState.idfPromoterAgeDate)) {
    return "IDF dates must be valid dates.";
  }

  const idfReductionAmount = Number(formState.idfReductionAmount);
  const idfOriginalCommutationPercent = Number(formState.idfOriginalCommutationPercent);
  const idfCurrentCommutationPercent = Number(formState.idfCurrentCommutationPercent);

  if ([idfReductionAmount, idfOriginalCommutationPercent, idfCurrentCommutationPercent].some(Number.isNaN)) {
    return "IDF numeric fields must contain valid numbers.";
  }

  if (idfReductionAmount <= 0) {
    return "IDF reduction amount must be greater than zero.";
  }

  if (idfOriginalCommutationPercent <= 0 || idfCurrentCommutationPercent <= 0) {
    return "IDF percent values must be greater than zero.";
  }

  if (idfOriginalCommutationPercent < 1 || idfCurrentCommutationPercent < 1) {
    return "IDF percent values must be provided in percent points, not decimal format.";
  }

  const commutationDate = new Date(formState.idfCommutationDate);
  const promoterAgeDate = new Date(formState.idfPromoterAgeDate);
  const eligibilityDate = new Date(formState.eligibilityDate);
  const laterDate = commutationDate > eligibilityDate ? commutationDate : eligibilityDate;

  if (promoterAgeDate <= laterDate) {
    return "IDF promoter age date must be after the later of commutation date and eligibility date.";
  }

  return null;
}

export function FixationInputScreen() {
  const { clientId: clientIdParam } = useParams<{ clientId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as FixationInputRouteState | null;
  const routeStateClientId = routeState?.clientId;
  const resolvedClientId = clientIdParam !== undefined ? Number(clientIdParam) : routeStateClientId;
  const clientId = Number.isInteger(resolvedClientId) && Number(resolvedClientId) > 0 ? Number(resolvedClientId) : null;
  const clientName = routeState?.clientName ?? null;
  const actualCapitalizationsPath = clientId !== null ? `/clients/${clientId}/actual-capitalizations` : "/clients";
  const fixationInputPath = clientId !== null ? `/clients/${clientId}/fixation/input` : "/fixation/input";
  const calculationResultPath = clientId !== null ? `/clients/${clientId}/fixation/result` : "/fixation/result";
  const backState = clientName ? { clientName } : undefined;
  const fixationInputState = clientName ? { clientId: clientId ?? undefined, clientName } : { clientId: clientId ?? undefined };
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [actualCapitalizations, setActualCapitalizations] = useState<ActualCapitalizationItem[]>([]);
  const [isSourceLoading, setIsSourceLoading] = useState(true);
  const [sourceErrorMessage, setSourceErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [responseData, setResponseData] = useState<FixationResultResponse | null>(null);
  const [responseSource, setResponseSource] = useState<"calculate" | "validate" | null>(null);
  const [calculatedResult, setCalculatedResult] = useState<FixationResultResponse | null>(null);
  const [calculatedPayloadSignature, setCalculatedPayloadSignature] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadClientSourceData() {
      if (clientId === null) {
        if (isActive) {
          setGrants([]);
          setActualCapitalizations([]);
          setSourceErrorMessage("Fixation flow requires an existing client context.");
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

    void loadClientSourceData();

    return () => {
      isActive = false;
    };
  }, [clientId]);

  const currentPayload = useMemo(
    () => buildPayload(formState, grants, actualCapitalizations),
    [actualCapitalizations, formState, grants],
  );
  const currentPayloadSignature = useMemo(() => JSON.stringify(currentPayload), [currentPayload]);
  const frontendValidationMessage = useMemo(() => validateForm(formState), [formState]);
  const isCalculationStale = calculatedResult !== null && calculatedPayloadSignature !== currentPayloadSignature;
  const readinessStatus =
    clientId === null
      ? "Blocked: client context is required."
      : isSourceLoading
        ? "Loading source data."
        : sourceErrorMessage !== null
          ? "Blocked: source data could not be loaded."
          : frontendValidationMessage !== null
            ? "Not ready: required inputs are still missing or invalid."
            : "Ready to validate or run calculation.";

  function updateFormState<K extends keyof FormState>(field: K, value: FormState[K]) {
    setFormState((current) => ({ ...current, [field]: value }));
  }

  async function submitForm(action: "calculate" | "validate") {
    if (clientId === null) {
      setErrorMessage("Fixation flow requires an existing client context.");
      setResponseData(null);
      setResponseSource(null);
      return;
    }

    if (isSourceLoading) {
      setErrorMessage("Source data is still loading.");
      setResponseData(null);
      setResponseSource(null);
      return;
    }

    if (sourceErrorMessage !== null) {
      setErrorMessage("Fixation source data must load successfully before validation or calculation.");
      setResponseData(null);
      setResponseSource(null);
      return;
    }

    if (frontendValidationMessage !== null) {
      setErrorMessage(frontendValidationMessage);
      setResponseData(null);
      setResponseSource(null);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = action === "calculate" ? await calculateFixation(currentPayload) : await validateFixation(currentPayload);
      setResponseData(response);
      setResponseSource(action);

      if (action === "calculate") {
        setCalculatedResult(response);
        setCalculatedPayloadSignature(currentPayloadSignature);
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
      setResponseData(null);
      setResponseSource(null);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitForm("calculate");
  }

  function handleContinueToResult() {
    if (clientId === null || calculatedResult === null || isCalculationStale) {
      return;
    }

    const resultRouteState: CalculationResultRouteState = {
      clientId,
      clientName: clientName ?? undefined,
      inputData: currentPayload,
      result: calculatedResult,
      fixationInputPath,
      fixationInputState,
    };

    navigate(calculationResultPath, { state: resultRouteState });
  }

  if (clientId === null) {
    return (
      <section>
        <h2>Fixation Parameters</h2>
        <p>BLOCKED</p>
        <p>Fixation flow requires an existing client context.</p>
      </section>
    );
  }

  if (isSourceLoading) {
    return (
      <section>
        <h2>Fixation Parameters</h2>
        <p>Client ID: {clientId}</p>
        {clientName ? <p>Client Name: {clientName}</p> : null}
        <p>Loading client source data...</p>
        <p>
          <Link to={actualCapitalizationsPath} state={backState}>Back to Actual Capitalizations</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Fixation Parameters</h2>
      <p>Client ID: {clientId}</p>
      {clientName ? <p>Client Name: {clientName}</p> : null}
      <p>Grants Summary: {grants.length}</p>
      <p>Actual Capitalizations Summary: {actualCapitalizations.length}</p>
      <p>Current Input Readiness Status: {readinessStatus}</p>
      {sourceErrorMessage ? <p>{sourceErrorMessage}</p> : null}
      <p>
        <Link to={actualCapitalizationsPath} state={backState}>Back to Actual Capitalizations</Link>
      </p>
      <form onSubmit={handleSubmit}>
        <p>
          <label htmlFor="calculation-id">
            Calculation ID
            <input
              id="calculation-id"
              type="text"
              value={formState.calculationId}
              onChange={(event) => updateFormState("calculationId", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="calculation-version">
            Calculation Version
            <input
              id="calculation-version"
              type="text"
              value={formState.calculationVersion}
              onChange={(event) => updateFormState("calculationVersion", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="eligibility-date">
            Eligibility Date
            <input
              id="eligibility-date"
              type="date"
              value={formState.eligibilityDate}
              onChange={(event) => updateFormState("eligibilityDate", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="eligibility-year">
            Eligibility Year
            <input
              id="eligibility-year"
              type="number"
              value={formState.eligibilityYear}
              onChange={(event) => updateFormState("eligibilityYear", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="monthly-cap">
            Monthly Cap
            <input
              id="monthly-cap"
              type="number"
              step="any"
              value={formState.monthlyCap}
              onChange={(event) => updateFormState("monthlyCap", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="exemption-percentage">
            Exemption Percentage
            <input
              id="exemption-percentage"
              type="number"
              step="any"
              value={formState.exemptionPercentage}
              onChange={(event) => updateFormState("exemptionPercentage", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="capital-multiplier">
            Capital Multiplier
            <input
              id="capital-multiplier"
              type="number"
              step="any"
              value={formState.capitalMultiplier}
              onChange={(event) => updateFormState("capitalMultiplier", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="future-grant-reserved">
            Future Grant Reserved
            <input
              id="future-grant-reserved"
              type="number"
              step="any"
              min="0"
              value={formState.futureGrantReserved}
              onChange={(event) => updateFormState("futureGrantReserved", event.target.value)}
            />
          </label>
        </p>
        <p>
          <label htmlFor="idf-relevant">
            IDF applicable
            <input
              id="idf-relevant"
              type="checkbox"
              checked={formState.idfRelevant}
              onChange={(event) => updateFormState("idfRelevant", event.target.checked)}
            />
          </label>
        </p>
        {formState.idfRelevant ? (
          <>
            <p>
              <label htmlFor="idf-id">
                IDF ID
                <input
                  id="idf-id"
                  type="text"
                  value={formState.idfId}
                  onChange={(event) => updateFormState("idfId", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-reduction-amount">
                IDF Reduction Amount
                <input
                  id="idf-reduction-amount"
                  type="number"
                  step="any"
                  value={formState.idfReductionAmount}
                  onChange={(event) => updateFormState("idfReductionAmount", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-original-commutation-percent">
                IDF Original Commutation Percent
                <input
                  id="idf-original-commutation-percent"
                  type="number"
                  step="any"
                  value={formState.idfOriginalCommutationPercent}
                  onChange={(event) => updateFormState("idfOriginalCommutationPercent", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-current-commutation-percent">
                IDF Current Commutation Percent
                <input
                  id="idf-current-commutation-percent"
                  type="number"
                  step="any"
                  value={formState.idfCurrentCommutationPercent}
                  onChange={(event) => updateFormState("idfCurrentCommutationPercent", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-commutation-date">
                IDF Commutation Date
                <input
                  id="idf-commutation-date"
                  type="date"
                  value={formState.idfCommutationDate}
                  onChange={(event) => updateFormState("idfCommutationDate", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-promoter-age-date">
                IDF Promoter Age Date
                <input
                  id="idf-promoter-age-date"
                  type="date"
                  value={formState.idfPromoterAgeDate}
                  onChange={(event) => updateFormState("idfPromoterAgeDate", event.target.value)}
                />
              </label>
            </p>
            <p>
              <label htmlFor="idf-source-label">
                IDF Source Label
                <input
                  id="idf-source-label"
                  type="text"
                  value={formState.idfSourceLabel}
                  onChange={(event) => updateFormState("idfSourceLabel", event.target.value)}
                />
              </label>
            </p>
          </>
        ) : null}
        <p>
          <button type="button" disabled={isSubmitting || isSourceLoading || sourceErrorMessage !== null} onClick={() => void submitForm("validate")}>
            {isSubmitting ? "Submitting..." : "Validate Inputs"}
          </button>
          <button type="submit" disabled={isSubmitting || isSourceLoading || sourceErrorMessage !== null}>
            {isSubmitting ? "Submitting..." : "Run Calculation"}
          </button>
          <button type="button" disabled={calculatedResult === null || isCalculationStale} onClick={handleContinueToResult}>
            Continue to Result
          </button>
        </p>
      </form>
      {errorMessage ? <p>{errorMessage}</p> : null}
      {isCalculationStale ? <p>Calculation result is stale. Run calculation again to continue.</p> : null}
      {responseData ? (
        <section>
          <h3>{responseSource === "validate" ? "Validate Response" : "Calculation Response"}</h3>
          <pre>{stringifyValue(responseData)}</pre>
        </section>
      ) : null}
    </section>
  );
}
