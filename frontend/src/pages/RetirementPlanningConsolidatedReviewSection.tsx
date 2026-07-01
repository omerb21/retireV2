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

  return "Unable to load retirement planning consolidated review.";
}

function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Not recorded";
  }

  return String(value);
}

function advisoryPlanningDomain(value: string | null): string {
  return value ?? "No planning-domain classification recorded";
}

function advisoryStatus(value: string | null): string {
  return value ?? "No advisory status recorded";
}

function advisoryNeutralReason(value: string | null): string {
  return value ?? "No neutral reason recorded";
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
        <p>Loading {heading.toLowerCase()}...</p>
      ) : state.errorMessage !== null ? (
        <>
          <p>Unable to load {heading.toLowerCase()}.</p>
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
      <h3 id="retirement-planning-consolidated-review-heading">Retirement Planning Consolidated Review</h3>
      <ReadOnlyGroup
        heading="Pension Holdings"
        state={pensionHoldings}
        emptyMessage="No pension holdings recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.provider_name)}</h5>
              <p>Product Type: {displayValue(item.product_type)}</p>
              <p>Product Name: {displayValue(item.product_name)}</p>
              <p>Account Reference: {displayValue(item.account_reference)}</p>
              <p>Known Balance Amount: {displayValue(item.known_balance_amount)}</p>
              <p>Balance As Of Date: {displayValue(item.balance_as_of_date)}</p>
              <p>Known Monthly Pension Amount: {displayValue(item.known_monthly_pension_amount)}</p>
              <p>Pension Amount As Of Date: {displayValue(item.pension_amount_as_of_date)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Capital Assets"
        state={capitalAssets}
        emptyMessage="No capital assets recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.asset_description)}</h5>
              <p>Asset Category: {displayValue(item.asset_category)}</p>
              <p>Known Value Amount: {displayValue(item.known_value_amount)}</p>
              <p>Value As Of Date: {displayValue(item.value_as_of_date)}</p>
              <p>Liquidity Note: {displayValue(item.liquidity_note)}</p>
              <p>Restriction Note: {displayValue(item.restriction_note)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Recurring Income"
        state={recurringIncomes}
        emptyMessage="No recurring income recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.description)}</h5>
              <p>Income Category: {displayValue(item.income_category)}</p>
              <p>Amount: {displayValue(item.amount)}</p>
              <p>Amount Basis: {displayValue(item.amount_basis)}</p>
              <p>Frequency: {displayValue(item.frequency)}</p>
              <p>Continuation Status: {displayValue(item.continuation_status)}</p>
              <p>Start Date: {displayValue(item.start_date)}</p>
              <p>End Date: {displayValue(item.end_date)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Recurring Expenses"
        state={recurringExpenses}
        emptyMessage="No recurring expenses recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.description)}</h5>
              <p>Expense Category: {displayValue(item.expense_category)}</p>
              <p>Amount: {displayValue(item.amount)}</p>
              <p>Frequency: {displayValue(item.frequency)}</p>
              <p>Expense Type: {displayValue(item.expense_type)}</p>
              <p>Continuation Status: {displayValue(item.continuation_status)}</p>
              <p>Start Date: {displayValue(item.start_date)}</p>
              <p>End Date: {displayValue(item.end_date)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Retirement Timing and Work Intentions"
        state={retirementTiming}
        emptyMessage="No retirement timing and work intentions recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.timing_confidence)}</h5>
              <p>Work After Retirement Intention: {displayValue(item.work_after_retirement_intention)}</p>
              <p>Planned Work End Date: {displayValue(item.planned_work_end_date)}</p>
              <p>Intended Pension Start Date: {displayValue(item.intended_pension_start_date)}</p>
              <p>Other Known Retirement Date: {displayValue(item.other_known_retirement_date)}</p>
              <p>Other Known Retirement Date Label: {displayValue(item.other_known_retirement_date_label)}</p>
              <p>Anticipated Work End Date: {displayValue(item.anticipated_work_end_date)}</p>
              <p>Work Intention Note: {displayValue(item.work_intention_note)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Planner Assumptions"
        state={plannerAssumptions}
        emptyMessage="No planner assumptions recorded."
        renderItem={(item) => (
          <li key={item.id}>
            <article>
              <h5>{displayValue(item.title)}</h5>
              <p>Assumption Category: {displayValue(item.assumption_category)}</p>
              <p>Assumption Value: {displayValue(item.assumption_value_text)}</p>
              <p>Rationale: {displayValue(item.rationale)}</p>
              <p>Owner: {displayValue(item.owner)}</p>
              <p>Effective Start Date: {displayValue(item.effective_start_date)}</p>
              <p>Effective End Date: {displayValue(item.effective_end_date)}</p>
              <p>Review Date: {displayValue(item.review_date)}</p>
            </article>
          </li>
        )}
      />
      <ReadOnlyGroup
        heading="Advisory Missing Information"
        state={advisoryMissingInformation}
        emptyMessage="No advisory missing information recorded."
        renderItem={(item) => (
          <li key={item.missing_data_item_id}>
            <article>
              <h5>{item.missing_data_item_id}</h5>
              <p>Planning Domain: {advisoryPlanningDomain(item.planning_domain)}</p>
              <p>Advisory Status: {advisoryStatus(item.advisory_status)}</p>
              <p>Neutral Reason: {advisoryNeutralReason(item.neutral_reason)}</p>
            </article>
          </li>
        )}
      />
    </section>
  );
}
