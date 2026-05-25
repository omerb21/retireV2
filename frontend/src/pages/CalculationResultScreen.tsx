import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import {
  ApiTransportError,
  FixationInputPayload,
  FixationResultResponse,
  SaveFixationResponse,
  saveFixation,
} from "../api/fixationApi";

type ResultRouteState = {
  clientId?: number;
  inputData?: FixationInputPayload;
  result?: FixationResultResponse;
  fixationInputPath?: string;
  fixationInputState?: {
    clientId?: number;
    clientName?: string;
  };
};

function stringifyValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

export function CalculationResultScreen() {
  const location = useLocation();
  const routeState = location.state as ResultRouteState | null;
  const clientId = routeState?.clientId;
  const inputData = routeState?.inputData;
  const result = routeState?.result;
  const fixationInputPath = routeState?.fixationInputPath ?? "/fixation/input";
  const fixationInputState = routeState?.fixationInputState ?? (typeof clientId === "number" ? { clientId } : undefined);
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [saveResponse, setSaveResponse] = useState<SaveFixationResponse | null>(null);

  async function handleSave() {
    if (typeof clientId !== "number" || inputData === undefined) {
      setSaveErrorMessage("Save is blocked because client context or input data is missing.");
      setSaveResponse(null);
      return;
    }

    setIsSaving(true);
    setSaveErrorMessage(null);

    try {
      const response = await saveFixation({
        client_id: clientId,
        input_data: inputData as unknown as Record<string, unknown>,
      });
      setSaveResponse(response);
    } catch (error) {
      if (error instanceof ApiTransportError) {
        setSaveErrorMessage(stringifyValue(error.body));
      } else if (error instanceof Error) {
        setSaveErrorMessage(error.message);
      } else {
        setSaveErrorMessage("Unexpected transport error.");
      }
      setSaveResponse(null);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section>
      <h2>Calculation Result Screen</h2>
      <p>Display-only backend calculation response.</p>
      <p>
        <Link to={fixationInputPath} state={fixationInputState}>
          Back to Fixation Input
        </Link>
      </p>
      {result ? (
        <section>
          <h3>Backend Response</h3>
          <pre>{stringifyValue(result)}</pre>
        </section>
      ) : (
        <p>No calculation result available.</p>
      )}
      <section>
        <h3>Save Run</h3>
        <button type="button" disabled={isSaving || !result} onClick={() => void handleSave()}>
          {isSaving ? "Saving..." : "Save"}
        </button>
        {saveErrorMessage ? <p>{saveErrorMessage}</p> : null}
        {saveResponse ? (
          <section>
            <h4>Save Response</h4>
            <pre>{stringifyValue(saveResponse)}</pre>
            <p>
              <Link to="/fixation/history" state={typeof clientId === "number" ? { clientId } : undefined}>
                Go to Run History
              </Link>
            </p>
          </section>
        ) : null}
        {!saveResponse && (typeof clientId !== "number" || inputData === undefined) ? (
          <p>Save is blocked because client context or input data is missing.</p>
        ) : null}
      </section>
    </section>
  );
}
