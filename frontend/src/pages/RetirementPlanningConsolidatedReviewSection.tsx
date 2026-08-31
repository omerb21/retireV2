import { useEffect, useState } from "react";

import {
  ApiTransportError,
  type CapitalAssetItem,
  getCapitalAssets,
  getMissingDataItems,
  getPensionHoldings,
  getPlannerAssumptions,
  getRecurringExpenses,
  getRecurringIncomes,
  getRetirementTimingWorkIntentions,
  type MissingDataItem,
  type PensionHoldingItem,
  type PlannerAssumptionItem,
  type RecurringExpenseItem,
  type RecurringIncomeItem,
  type RetirementTimingWorkIntentionItem
} from "../api/clientsApi";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";

type RetirementPlanningConsolidatedReviewSectionProps = {
  clientId: number;
};

type GroupState<T> = {
  items: T[];
  isLoading: boolean;
  errorMessage: string | null;
};

const emptyGroupState = <T,>(): GroupState<T> => ({
  items: [],
  isLoading: true,
  errorMessage: null
});

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

  return "לא ניתן לטעון את הסקירה המאוחדת לתכנון פרישה.";
}

function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "לא תועד";
  }

  return String(value);
}

function advisoryPlanningDomain(value: string | null): string {
  return value === null ? "לא תועד סיווג לתחום תכנון" : heLabel(value);
}

function advisoryStatus(value: string | null): string {
  return value === null ? "לא תועד מצב ייעוץ" : heLabel(value);
}

function advisoryNeutralReason(value: string | null): string {
  return value ?? "לא תועדה סיבה ניטרלית";
}

function headingId(heading: string): string {
  return `${heading.toLowerCase().replace(/\s+/g, "-")}-package-e-heading`;
}

function ReadOnlyGroup<T>({
  heading,
  state,
  emptyMessage,
  renderItem
}: {
  heading: string;
  state: GroupState<T>;
  emptyMessage: string;
  renderItem: (item: T) => JSX.Element;
}) {
  const id = headingId(heading);

  return (
    <section aria-labelledby={id}>
      <h4 id={id}>{heading}</h4>
      {state.isLoading ? (
        <p>טוען {heading}…</p>
      ) : state.errorMessage !== null ? (
        <>
          <p>לא ניתן לטעון {heading}.</p>
          <pre>{state.errorMessage}</pre>
        </>
      ) : state.items.length === 0 ? (
        <p>{emptyMessage}</p>
      ) : (
        <ul>{state.items.map(renderItem)}</ul>
      )}
    </section>
  );
}

export function RetirementPlanningConsolidatedReviewSection({
  clientId
}: RetirementPlanningConsolidatedReviewSectionProps) {
  const [pensionHoldings, setPensionHoldings] = useState<GroupState<PensionHoldingItem>>(
    emptyGroupState<PensionHoldingItem>()
  );
  const [capitalAssets, setCapitalAssets] = useState<GroupState<CapitalAssetItem>>(
    emptyGroupState<CapitalAssetItem>()
  );
  const [recurringIncomes, setRecurringIncomes] = useState<GroupState<RecurringIncomeItem>>(
    emptyGroupState<RecurringIncomeItem>()
  );
  const [recurringExpenses, setRecurringExpenses] = useState<GroupState<RecurringExpenseItem>>(
    emptyGroupState<RecurringExpenseItem>()
  );
  const [retirementTiming, setRetirementTiming] = useState<GroupState<RetirementTimingWorkIntentionItem>>(
    emptyGroupState<RetirementTimingWorkIntentionItem>()
  );
  const [plannerAssumptions, setPlannerAssumptions] = useState<GroupState<PlannerAssumptionItem>>(
    emptyGroupState<PlannerAssumptionItem>()
  );
  const [advisoryMissingInformation, setAdvisoryMissingInformation] = useState<GroupState<MissingDataItem>>(
    emptyGroupState<MissingDataItem>()
  );

  useEffect(() => {
    let isActive = true;

    async function loadGroup<T>(loadItems: () => Promise<T[]>, setState: (state: GroupState<T>) => void) {
      setState(emptyGroupState<T>());

      try {
        const items = await loadItems();
        if (isActive) {
          setState({ items, isLoading: false, errorMessage: null });
        }
      } catch (error) {
        if (isActive) {
          setState({ items: [], isLoading: false, errorMessage: getErrorMessage(error) });
        }
      }
    }

    void loadGroup(() => getPensionHoldings(clientId, "current"), setPensionHoldings);
    void loadGroup(() => getCapitalAssets(clientId, "current"), setCapitalAssets);
    void loadGroup(() => getRecurringIncomes(clientId, "current"), setRecurringIncomes);
    void loadGroup(() => getRecurringExpenses(clientId, "current"), setRecurringExpenses);
    void loadGroup(() => getRetirementTimingWorkIntentions(clientId, "current"), setRetirementTiming);
    void loadGroup(() => getPlannerAssumptions(clientId, "current"), setPlannerAssumptions);
    void loadGroup(() => getMissingDataItems(clientId), setAdvisoryMissingInformation);

    return () => {
      isActive = false;
    };
  }, [clientId]);

  return (
    <section aria-labelledby="retirement-planning-consolidated-review-heading">
      <h3 id="retirement-planning-consolidated-review-heading">סקירה מאוחדת לתכנון פרישה</h3>
      <ReadOnlyGroup
        heading="אחזקות פנסיוניות"
        state={pensionHoldings}
        emptyMessage="לא תועדו אחזקות פנסיוניות."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.provider_name)}</h5>
              <p>סוג מוצר: {heLabel(item.product_type)}</p>
              <p>שם מוצר: {displayValue(item.product_name)}</p>
              <p>אסמכתת חשבון: {displayValue(item.account_reference)}</p>
              <p>יתרה ידועה: {displayValue(item.known_balance_amount)}</p>
              <p>תאריך נכונות היתרה: {formatIsoDate(item.balance_as_of_date) || "לא תועד"}</p>
              <p>קצבה חודשית ידועה: {displayValue(item.known_monthly_pension_amount)}</p>
              <p>תאריך נכונות הקצבה: {formatIsoDate(item.pension_amount_as_of_date) || "לא תועד"}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="נכסי הון"
        state={capitalAssets}
        emptyMessage="לא תועדו נכסי הון."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.asset_description)}</h5>
              <p>קטגוריית נכס: {heLabel(item.asset_category)}</p>
              <p>שווי ידוע: {displayValue(item.known_value_amount)}</p>
              <p>תאריך נכונות השווי: {formatIsoDate(item.value_as_of_date) || "לא תועד"}</p>
              <p>הערת נזילות: {displayValue(item.liquidity_note)}</p>
              <p>הערת מגבלה: {displayValue(item.restriction_note)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="הכנסות שוטפות"
        state={recurringIncomes}
        emptyMessage="לא תועדו הכנסות שוטפות."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.description)}</h5>
              <p>קטגוריית הכנסה: {heLabel(item.income_category)}</p>
              <p>סכום: {displayValue(item.amount)}</p>
              <p>בסיס הסכום: {heLabel(item.amount_basis)}</p>
              <p>תדירות: {heLabel(item.frequency)}</p>
              <p>מצב המשכיות: {heLabel(item.continuation_status)}</p>
              <p>תאריך התחלה: {formatIsoDate(item.start_date) || "לא תועד"}</p>
              <p>תאריך סיום: {formatIsoDate(item.end_date) || "לא תועד"}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="הוצאות שוטפות"
        state={recurringExpenses}
        emptyMessage="לא תועדו הוצאות שוטפות."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.description)}</h5>
              <p>קטגוריית הוצאה: {heLabel(item.expense_category)}</p>
              <p>סכום: {displayValue(item.amount)}</p>
              <p>תדירות: {heLabel(item.frequency)}</p>
              <p>סוג הוצאה: {heLabel(item.expense_type)}</p>
              <p>מצב המשכיות: {heLabel(item.continuation_status)}</p>
              <p>תאריך התחלה: {formatIsoDate(item.start_date) || "לא תועד"}</p>
              <p>תאריך סיום: {formatIsoDate(item.end_date) || "לא תועד"}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="עיתוי פרישה וכוונות עבודה"
        state={retirementTiming}
        emptyMessage="לא תועדו נתוני עיתוי פרישה וכוונות עבודה."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{heLabel(item.timing_confidence)}</h5>
              <p>כוונת עבודה לאחר הפרישה: {heLabel(item.work_after_retirement_intention)}</p>
              <p>תאריך מתוכנן לסיום העבודה: {formatIsoDate(item.planned_work_end_date) || "לא תועד"}</p>
              <p>תאריך מיועד לתחילת הקצבה: {formatIsoDate(item.intended_pension_start_date) || "לא תועד"}</p>
              <p>תאריך פרישה ידוע נוסף: {formatIsoDate(item.other_known_retirement_date) || "לא תועד"}</p>
              <p>תיאור תאריך הפרישה הידוע הנוסף: {displayValue(item.other_known_retirement_date_label)}</p>
              <p>תאריך משוער לסיום העבודה: {formatIsoDate(item.anticipated_work_end_date) || "לא תועד"}</p>
              <p>הערת כוונת עבודה: {displayValue(item.work_intention_note)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="הנחות מתכנן"
        state={plannerAssumptions}
        emptyMessage="לא תועדו הנחות מתכנן."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.title)}</h5>
              <p>קטגוריית הנחה: {heLabel(item.assumption_category)}</p>
              <p>ערך ההנחה: {displayValue(item.assumption_value_text)}</p>
              <p>נימוק: {displayValue(item.rationale)}</p>
              <p>אחראי: {heLabel(item.owner)}</p>
              <p>תאריך תחילת תוקף: {formatIsoDate(item.effective_start_date) || "לא תועד"}</p>
              <p>תאריך סיום תוקף: {formatIsoDate(item.effective_end_date) || "לא תועד"}</p>
              <p>תאריך בדיקה: {formatIsoDate(item.review_date) || "לא תועד"}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="מידע חסר לייעוץ"
        state={advisoryMissingInformation}
        emptyMessage="לא תועד מידע חסר לייעוץ."
        renderItem={(item) => (
          <li key={item.missing_data_item_id}>
            <article>
              <h5>{item.missing_data_item_id}</h5>
              <p>תחום תכנון: {advisoryPlanningDomain(item.planning_domain)}</p>
              <p>מצב ייעוץ: {advisoryStatus(item.advisory_status)}</p>
              <p>סיבה ניטרלית: {advisoryNeutralReason(item.neutral_reason)}</p>
            </article>
          </li>
        )}
      />
    </section>
  );
}
