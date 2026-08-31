import { type FormEvent, useEffect, useState } from "react";

import {
  ApiTransportError,
  createPensionAnalysisRecord,
  getPensionAnalysisRecord,
  getPensionHoldings,
  type PensionAnalysisRecordItem,
  type PensionHoldingItem,
  updatePensionAnalysisRecord
} from "../api/clientsApi";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";

type PensionAnalysisRecordSectionProps = {
  clientId: number;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    if (typeof error.body === "string") {
      return error.body;
    }

    return JSON.stringify(error.body, null, 2);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "לא ניתן לטעון את רשומות הניתוח הפנסיוני.";
}

function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "לא תועד";
  }

  return String(value);
}

function factContext(holding: PensionHoldingItem) {
  return (
    <section aria-label={`הקשר עובדתי של אחזקה פנסיונית ${holding.id}`}>
      <h5>הקשר עובדתי של אחזקה פנסיונית</h5>
      <p>שם הגוף המנהל: {displayValue(holding.provider_name)}</p>
      <p>סוג מוצר: {heLabel(holding.product_type)}</p>
      <p>שם מוצר: {displayValue(holding.product_name)}</p>
      <p>אסמכתת חשבון: {displayValue(holding.account_reference)}</p>
      <p>יתרה ידועה: {displayValue(holding.known_balance_amount)}</p>
      <p>תאריך נכונות היתרה: {formatIsoDate(holding.balance_as_of_date) || "לא תועד"}</p>
      <p>קצבה חודשית ידועה: {displayValue(holding.known_monthly_pension_amount)}</p>
      <p>תאריך נכונות הקצבה: {formatIsoDate(holding.pension_amount_as_of_date) || "לא תועד"}</p>
      <p>מצב מקור: {heLabel(holding.source_status)}</p>
      <p>מצב אימות: {heLabel(holding.verification_state)}</p>
      <p>סוג מקור: {displayValue(holding.source_type)}</p>
      <p>תאריך מקור: {formatIsoDate(holding.source_date) || "לא תועד"}</p>
      <p>הערת מקור: {displayValue(holding.source_note)}</p>
    </section>
  );
}

export function PensionAnalysisRecordSection({ clientId }: PensionAnalysisRecordSectionProps) {
  const [holdings, setHoldings] = useState<PensionHoldingItem[]>([]);
  const [recordsByHoldingId, setRecordsByHoldingId] = useState<Record<number, PensionAnalysisRecordItem | null>>({});
  const [textByHoldingId, setTextByHoldingId] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [savingHoldingId, setSavingHoldingId] = useState<number | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadRecords() {
      setIsLoading(true);
      setLoadErrorMessage(null);

      try {
        const nextHoldings = await getPensionHoldings(clientId, "current");
        const recordPairs = await Promise.all(
          nextHoldings.map(async (holding) => [holding.id, await getPensionAnalysisRecord(clientId, holding.id)] as const)
        );

        if (!isActive) {
          return;
        }

        const nextRecords = Object.fromEntries(recordPairs);
        setHoldings(nextHoldings);
        setRecordsByHoldingId(nextRecords);
        setTextByHoldingId(
          Object.fromEntries(recordPairs.map(([holdingId, record]) => [holdingId, record?.analysis_record_text ?? ""]))
        );
      } catch (error) {
        if (!isActive) {
          return;
        }
        setHoldings([]);
        setRecordsByHoldingId({});
        setTextByHoldingId({});
        setLoadErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadRecords();

    return () => {
      isActive = false;
    };
  }, [clientId]);

  function updateText(holdingId: number, value: string) {
    setTextByHoldingId((current) => ({ ...current, [holdingId]: value }));
    setSaveErrorMessage(null);
    setSaveSuccessMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>, holdingId: number) {
    event.preventDefault();
    setSavingHoldingId(holdingId);
    setSaveErrorMessage(null);
    setSaveSuccessMessage(null);

    try {
      const payload = { analysis_record_text: textByHoldingId[holdingId] ?? "" };
      const existing = recordsByHoldingId[holdingId];
      const saved = existing === null
        ? await createPensionAnalysisRecord(clientId, holdingId, payload)
        : await updatePensionAnalysisRecord(clientId, holdingId, payload);
      setRecordsByHoldingId((current) => ({ ...current, [holdingId]: saved }));
      setTextByHoldingId((current) => ({ ...current, [holdingId]: saved.analysis_record_text }));
      setSaveSuccessMessage("רשומת הניתוח הפנסיוני נשמרה.");
    } catch (error) {
      setSaveErrorMessage(getErrorMessage(error));
    } finally {
      setSavingHoldingId(null);
    }
  }

  return (
    <section aria-labelledby="pension-analysis-records-heading">
      <h3 id="pension-analysis-records-heading">רשומות ניתוח פנסיוני</h3>
      {isLoading ? (
        <p>טוען רשומות ניתוח פנסיוני…</p>
      ) : loadErrorMessage !== null ? (
        <>
          <p>לא ניתן לטעון את רשומות הניתוח הפנסיוני.</p>
          <pre>{loadErrorMessage}</pre>
        </>
      ) : holdings.length === 0 ? (
        <p>לא נמצאו אחזקות פנסיוניות עדכניות לצורך רשומת ניתוח.</p>
      ) : (
        <ul>
          {holdings.map((holding) => {
            const record = recordsByHoldingId[holding.id] ?? null;
            const isSaving = savingHoldingId === holding.id;
            return (
              <li key={holding.id}>
                <article>
                  <h4>אחזקה פנסיונית {holding.id}</h4>
                  {factContext(holding)}
                  <form onSubmit={(event) => handleSubmit(event, holding.id)}>
                    <p>
                      <label htmlFor={`pension-analysis-record-text-${holding.id}`}>תוכן רשומת הניתוח</label>
                      <textarea
                        id={`pension-analysis-record-text-${holding.id}`}
                        value={textByHoldingId[holding.id] ?? ""}
                        onChange={(event) => updateText(holding.id, event.target.value)}
                      />
                    </p>
                    <button type="submit" disabled={isSaving}>
                      {isSaving ? "שומר רשומת ניתוח פנסיוני…" : record === null ? "יצירת רשומת ניתוח פנסיוני" : "שמירת רשומת ניתוח פנסיוני"}
                    </button>
                  </form>
                </article>
              </li>
            );
          })}
        </ul>
      )}
      {saveSuccessMessage ? <p>{saveSuccessMessage}</p> : null}
      {saveErrorMessage ? (
        <>
          <p>לא ניתן לשמור את רשומת הניתוח הפנסיוני.</p>
          <pre>{saveErrorMessage}</pre>
        </>
      ) : null}
    </section>
  );
}
