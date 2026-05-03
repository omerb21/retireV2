import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  ApiTransportError,
  FixationInputPayload,
  FixationResultResponse,
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
};

type FixationInputRouteState = {
  clientId?: number;
};

type CalculationResultRouteState = {
  clientId: number;
  inputData: FixationInputPayload;
  result: FixationResultResponse;
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
};

function stringifyValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function buildPayload(formState: FormState): FixationInputPayload {
  return {
    calculation_id: formState.calculationId || null,
    calculation_version: formState.calculationVersion,
    eligibility_date: formState.eligibilityDate,
    eligibility_year: Number(formState.eligibilityYear),
    monthly_cap: Number(formState.monthlyCap),
    exemption_percentage: Number(formState.exemptionPercentage),
    capital_multiplier: Number(formState.capitalMultiplier),
    grants: [],
    future_grant_reserved: Number(formState.futureGrantReserved),
    actual_capitalizations: [],
    idf: null,
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

  if (Number.isNaN(Date.parse(formState.eligibilityDate))) {
    return "Eligibility date must be a valid date.";
  }

  const numericValues = [
    formState.eligibilityYear,
    formState.monthlyCap,
    formState.exemptionPercentage,
    formState.capitalMultiplier,
    formState.futureGrantReserved,
  ];

  if (numericValues.some((value) => Number.isNaN(Number(value)))) {
    return "Numeric fields must contain valid numbers.";
  }

  return null;
}

export function FixationInputScreen() {
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as FixationInputRouteState | null;
  const clientId = routeState?.clientId;
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [responseData, setResponseData] = useState<FixationResultResponse | null>(null);
  const [responseSource, setResponseSource] = useState<"calculate" | "validate" | null>(null);

  async function submitForm(action: "calculate" | "validate") {
    const validationError = validateForm(formState);
    if (validationError) {
      setErrorMessage(validationError);
      setResponseData(null);
      setResponseSource(null);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const payload = buildPayload(formState);
      const response = action === "calculate" ? await calculateFixation(payload) : await validateFixation(payload);
      if (action === "calculate") {
        const routeClientId = clientId;
        if (typeof routeClientId !== "number") {
          throw new Error("Fixation flow requires an existing client context in route state.");
        }
        const resultRouteState: CalculationResultRouteState = {
          clientId: routeClientId,
          inputData: payload,
          result: response,
        };
        navigate("/fixation/result", { state: resultRouteState });
        return;
      }
      setResponseData(response);
      setResponseSource(action);
    } catch (error) {
      if (error instanceof ApiTransportError) {
        setErrorMessage(stringifyValue(error.body));
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unexpected transport error.");
      }
      setResponseData(null);
      setResponseSource(null);
    } finally {
      setIsLoading(false);
    }
  }

  if (typeof clientId !== "number") {
    return (
      <section>
        <h2>Fixation Input Screen</h2>
        <p>BLOCKED</p>
        <p>Fixation flow requires an existing client context in route state.</p>
      </section>
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitForm("calculate");
  }

  return (
    <section>
      <h2>Fixation Input Screen</h2>
      <p>Enter fixation input values and submit them to the existing backend endpoint.</p>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="calculation-id">Calculation ID</label>
          <input
            id="calculation-id"
            type="text"
            value={formState.calculationId}
            onChange={(event) => setFormState((current) => ({ ...current, calculationId: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="calculation-version">Calculation Version</label>
          <input
            id="calculation-version"
            type="text"
            value={formState.calculationVersion}
            onChange={(event) => setFormState((current) => ({ ...current, calculationVersion: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="eligibility-date">Eligibility Date</label>
          <input
            id="eligibility-date"
            type="date"
            value={formState.eligibilityDate}
            onChange={(event) => setFormState((current) => ({ ...current, eligibilityDate: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="eligibility-year">Eligibility Year</label>
          <input
            id="eligibility-year"
            type="number"
            value={formState.eligibilityYear}
            onChange={(event) => setFormState((current) => ({ ...current, eligibilityYear: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="monthly-cap">Monthly Cap</label>
          <input
            id="monthly-cap"
            type="number"
            value={formState.monthlyCap}
            onChange={(event) => setFormState((current) => ({ ...current, monthlyCap: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="exemption-percentage">Exemption Percentage</label>
          <input
            id="exemption-percentage"
            type="number"
            step="any"
            value={formState.exemptionPercentage}
            onChange={(event) => setFormState((current) => ({ ...current, exemptionPercentage: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="capital-multiplier">Capital Multiplier</label>
          <input
            id="capital-multiplier"
            type="number"
            step="any"
            value={formState.capitalMultiplier}
            onChange={(event) => setFormState((current) => ({ ...current, capitalMultiplier: event.target.value }))}
          />
        </div>
        <div>
          <label htmlFor="future-grant-reserved">Future Grant Reserved</label>
          <input
            id="future-grant-reserved"
            type="number"
            step="any"
            value={formState.futureGrantReserved}
            onChange={(event) => setFormState((current) => ({ ...current, futureGrantReserved: event.target.value }))}
          />
        </div>
        <div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Submitting..." : "Calculate"}
          </button>
          <button type="button" disabled={isLoading} onClick={() => void submitForm("validate")}>
            {isLoading ? "Submitting..." : "Validate"}
          </button>
        </div>
      </form>
      {errorMessage ? <p>{errorMessage}</p> : null}
      {responseData ? (
        <section>
          <h3>{responseSource === "validate" ? "Validate Response" : "Calculate Response"}</h3>
          <pre>{stringifyValue(responseData)}</pre>
        </section>
      ) : null}
    </section>
  );
}
