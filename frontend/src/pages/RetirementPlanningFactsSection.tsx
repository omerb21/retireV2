import { type FormEvent, useEffect, useState } from "react";

import {
  ApiTransportError,
  createCapitalAsset,
  createPensionHolding,
  createRecurringExpense,
  createRecurringIncome,
  createRetirementTimingWorkIntention,
  getCapitalAssets,
  getPensionHoldings,
  getRecurringExpenses,
  getRecurringIncomes,
  getRetirementTimingWorkIntentions,
  type CapitalAssetCreatePayload,
  type LifecycleStatusFilter,
  type PensionHoldingCreatePayload,
  type RecurringExpenseCreatePayload,
  type RecurringIncomeCreatePayload,
  type RetirementTimingWorkIntentionCreatePayload,
  updateCapitalAsset,
  updatePensionHolding,
  updateRecurringExpense,
  updateRecurringIncome,
  updateRetirementTimingWorkIntention
} from "../api/clientsApi";

export type RetirementPlanningFactsSectionProps = {
  clientId: number;
};

type FieldKind = "text" | "date" | "amount" | "select" | "textarea";
type FactPayloadValue = string | null;
type FactPayload = Record<string, FactPayloadValue>;
type FactItem = {
  id: number;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
};

type FieldConfig = {
  name: string;
  label: string;
  kind: FieldKind;
  optional: boolean;
  options?: string[];
  showWhen?: (formState: FormState) => boolean;
};

type FactSectionConfig = {
  key: string;
  heading: string;
  emptyMessage: string;
  loadingMessage: string;
  createHeading: string;
  editHeading: string;
  addButton: string;
  saveButton: string;
  editButton: string;
  fields: FieldConfig[];
  listFields: string[];
  list: (clientId: number, lifecycleStatus: LifecycleStatusFilter) => Promise<FactItem[]>;
  create: (clientId: number, payload: FactPayload) => Promise<FactItem>;
  update: (clientId: number, id: number, payload: FactPayload) => Promise<FactItem>;
};

type FormState = Record<string, string>;

const lifecycleOptions: LifecycleStatusFilter[] = ["current", "superseded", "all"];
const sourceStatusOptions = [
  "not recorded",
  "client stated",
  "planner entered",
  "external statement",
  "employer information",
  "institution information",
  "government or tax source",
  "other"
];
const verificationStateOptions = [
  "collected - not yet reviewed",
  "reviewed",
  "verified",
  "partially verified",
  "verification not applicable"
];

const metadataFields: FieldConfig[] = [
  { name: "source_status", label: "Source Status", kind: "select", optional: true, options: sourceStatusOptions },
  {
    name: "verification_state",
    label: "Verification State",
    kind: "select",
    optional: true,
    options: verificationStateOptions
  },
  { name: "source_type", label: "Source Type", kind: "text", optional: true },
  { name: "source_date", label: "Source Date", kind: "date", optional: true },
  { name: "source_note", label: "Source Note", kind: "textarea", optional: true }
];

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

  return "Unable to load retirement planning facts.";
}

function emptyFormState(fields: FieldConfig[]): FormState {
  return fields.reduce<FormState>((current, field) => ({ ...current, [field.name]: "" }), {});
}

function formStateFromItem(fields: FieldConfig[], item: FactItem): FormState {
  return fields.reduce<FormState>((current, field) => {
    const value = (item as Record<string, unknown>)[field.name];
    return {
      ...current,
      [field.name]: value === null || value === undefined ? "" : String(value)
    };
  }, {});
}

function payloadValue(field: FieldConfig, value: string): FactPayloadValue {
  if (!field.optional) {
    return value;
  }

  return value.trim() === "" ? null : value;
}

function payloadFromForm(fields: FieldConfig[], formState: FormState, touchedFields?: Set<string>): FactPayload {
  return fields.reduce<FactPayload>((current, field) => {
    if (touchedFields !== undefined && !touchedFields.has(field.name)) {
      return current;
    }

    const value = formState[field.name] ?? "";
    if (touchedFields === undefined && field.optional && value.trim() === "") {
      return current;
    }

    return {
      ...current,
      [field.name]: payloadValue(field, value)
    };
  }, {});
}

function fieldValue(item: FactItem, fieldName: string): string | null {
  const value = (item as Record<string, unknown>)[fieldName];
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return String(value);
}

function labelFromFieldName(fieldName: string): string {
  return fieldName
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function renderField(
  sectionKey: string,
  field: FieldConfig,
  formState: FormState,
  onFieldChange: (fieldName: string, value: string) => void
) {
  if (field.showWhen !== undefined && !field.showWhen(formState)) {
    return null;
  }

  const fieldId = `${sectionKey}-${field.name}`;
  const value = formState[field.name] ?? "";

  if (field.kind === "select") {
    return (
      <p key={field.name}>
        <label htmlFor={fieldId}>{field.label}</label>
        <select id={fieldId} value={value} onChange={(event) => onFieldChange(field.name, event.target.value)}>
          <option value="">Not selected</option>
          {(field.options ?? []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </p>
    );
  }

  if (field.kind === "textarea") {
    return (
      <p key={field.name}>
        <label htmlFor={fieldId}>{field.label}</label>
        <textarea id={fieldId} value={value} onChange={(event) => onFieldChange(field.name, event.target.value)} />
      </p>
    );
  }

  return (
    <p key={field.name}>
      <label htmlFor={fieldId}>{field.label}</label>
      <input
        id={fieldId}
        type={field.kind === "date" ? "date" : field.kind === "amount" ? "number" : "text"}
        step={field.kind === "amount" ? "0.01" : undefined}
        value={value}
        onChange={(event) => onFieldChange(field.name, event.target.value)}
      />
    </p>
  );
}

function FactMaintenanceSection({ clientId, config }: { clientId: number; config: FactSectionConfig }) {
  const [items, setItems] = useState<FactItem[]>([]);
  const [lifecycleStatus, setLifecycleStatus] = useState<LifecycleStatusFilter>("current");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [formState, setFormState] = useState<FormState>(() => emptyFormState(config.fields));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [touchedFields, setTouchedFields] = useState<Set<string>>(new Set());
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function refreshList(selectedLifecycleStatus = lifecycleStatus) {
    const nextItems = await config.list(clientId, selectedLifecycleStatus);
    setItems(nextItems);
    setErrorMessage(null);
  }

  useEffect(() => {
    let isActive = true;

    async function loadItems() {
      setIsLoading(true);

      try {
        const nextItems = await config.list(clientId, lifecycleStatus);
        if (!isActive) {
          return;
        }
        setItems(nextItems);
        setErrorMessage(null);
      } catch (error) {
        if (!isActive) {
          return;
        }
        setItems([]);
        setErrorMessage(getErrorMessage(error));
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadItems();

    return () => {
      isActive = false;
    };
  }, [clientId, config, lifecycleStatus]);

  function updateFormField(fieldName: string, value: string) {
    setFormState((current) => ({ ...current, [fieldName]: value }));
    setTouchedFields((current) => new Set(current).add(fieldName));
    setMutationErrorMessage(null);
  }

  function startEditing(item: FactItem) {
    setEditingId(item.id);
    setFormState(formStateFromItem(config.fields, item));
    setTouchedFields(new Set());
    setMutationErrorMessage(null);
  }

  function resetForm() {
    setEditingId(null);
    setFormState(emptyFormState(config.fields));
    setTouchedFields(new Set());
    setMutationErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMutationErrorMessage(null);

    try {
      if (editingId === null) {
        await config.create(clientId, payloadFromForm(config.fields, formState));
      } else {
        await config.update(clientId, editingId, payloadFromForm(config.fields, formState, touchedFields));
      }
      await refreshList();
      resetForm();
    } catch (error) {
      setMutationErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section aria-labelledby={`${config.key}-heading`}>
      <h4 id={`${config.key}-heading`}>{config.heading}</h4>
      <p>
        <label htmlFor={`${config.key}-lifecycle-filter`}>Lifecycle Filter</label>
        <select
          id={`${config.key}-lifecycle-filter`}
          value={lifecycleStatus}
          onChange={(event) => {
            setLifecycleStatus(event.target.value as LifecycleStatusFilter);
          }}
        >
          {lifecycleOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </p>
      {isLoading ? (
        <p>{config.loadingMessage}</p>
      ) : errorMessage !== null ? (
        <>
          <p>Unable to load {config.heading.toLowerCase()}.</p>
          <pre>{errorMessage}</pre>
        </>
      ) : items.length === 0 ? (
        <p>{config.emptyMessage}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <article>
                <h5>{config.heading} Record {item.id}</h5>
                <p>Lifecycle Status: {item.lifecycle_status}</p>
                <p>Source Status: {item.source_status}</p>
                <p>Verification State: {item.verification_state}</p>
                {config.listFields.map((fieldName) => {
                  const value = fieldValue(item, fieldName);
                  return value === null ? null : (
                    <p key={fieldName}>
                      {labelFromFieldName(fieldName)}: {value}
                    </p>
                  );
                })}
                <p>
                  <button type="button" onClick={() => startEditing(item)} disabled={isSubmitting}>
                    {config.editButton}
                  </button>
                </p>
              </article>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit}>
        <h5>{editingId === null ? config.createHeading : config.editHeading}</h5>
        {config.fields.map((field) => renderField(config.key, field, formState, updateFormField))}
        {mutationErrorMessage ? (
          <>
            <p>Unable to save {config.heading.toLowerCase()}.</p>
            <pre>{mutationErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : editingId === null ? config.addButton : config.saveButton}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              Cancel Edit
            </button>
          ) : null}
        </p>
      </form>
    </section>
  );
}

const factSectionConfigs: FactSectionConfig[] = [
  {
    key: "pension-holdings",
    heading: "Pension holdings",
    emptyMessage: "No pension holdings found for the selected lifecycle filter.",
    loadingMessage: "Loading pension holdings...",
    createHeading: "Add Pension Holding",
    editHeading: "Edit Pension Holding",
    addButton: "Add Pension Holding",
    saveButton: "Save Pension Holding",
    editButton: "Edit Pension Holding",
    fields: [
      { name: "provider_name", label: "Provider Name", kind: "text", optional: false },
      {
        name: "product_type",
        label: "Product Type",
        kind: "select",
        optional: false,
        options: ["pension fund", "provident fund", "insurance policy", "other"]
      },
      { name: "product_name", label: "Product Name", kind: "text", optional: true },
      { name: "account_reference", label: "Account Reference", kind: "text", optional: true },
      { name: "known_balance_amount", label: "Known Balance Amount", kind: "amount", optional: true },
      {
        name: "balance_as_of_date",
        label: "Balance As Of Date",
        kind: "date",
        optional: true,
        showWhen: (formState) => formState.known_balance_amount.trim() !== ""
      },
      {
        name: "known_monthly_pension_amount",
        label: "Known Monthly Pension Amount",
        kind: "amount",
        optional: true
      },
      {
        name: "pension_amount_as_of_date",
        label: "Pension Amount As Of Date",
        kind: "date",
        optional: true,
        showWhen: (formState) => formState.known_monthly_pension_amount.trim() !== ""
      },
      ...metadataFields
    ],
    listFields: [
      "provider_name",
      "product_type",
      "product_name",
      "account_reference",
      "known_balance_amount",
      "balance_as_of_date",
      "known_monthly_pension_amount",
      "pension_amount_as_of_date",
      "source_type",
      "source_date",
      "source_note"
    ],
    list: (clientId, lifecycleStatus) => getPensionHoldings(clientId, lifecycleStatus) as Promise<FactItem[]>,
    create: (clientId, payload) =>
      createPensionHolding(clientId, payload as unknown as PensionHoldingCreatePayload),
    update: (clientId, id, payload) => updatePensionHolding(clientId, id, payload)
  },
  {
    key: "capital-assets",
    heading: "Capital assets",
    emptyMessage: "No capital assets found for the selected lifecycle filter.",
    loadingMessage: "Loading capital assets...",
    createHeading: "Add Capital Asset",
    editHeading: "Edit Capital Asset",
    addButton: "Add Capital Asset",
    saveButton: "Save Capital Asset",
    editButton: "Edit Capital Asset",
    fields: [
      {
        name: "asset_category",
        label: "Asset Category",
        kind: "select",
        optional: false,
        options: ["bank deposit", "investment account", "securities", "real estate", "private asset", "other"]
      },
      { name: "asset_description", label: "Asset Description", kind: "text", optional: false },
      { name: "known_value_amount", label: "Known Value Amount", kind: "amount", optional: true },
      {
        name: "value_as_of_date",
        label: "Value As Of Date",
        kind: "date",
        optional: true,
        showWhen: (formState) => formState.known_value_amount.trim() !== ""
      },
      { name: "liquidity_note", label: "Liquidity Note", kind: "textarea", optional: true },
      { name: "restriction_note", label: "Restriction Note", kind: "textarea", optional: true },
      ...metadataFields
    ],
    listFields: [
      "asset_category",
      "asset_description",
      "known_value_amount",
      "value_as_of_date",
      "liquidity_note",
      "restriction_note",
      "source_type",
      "source_date",
      "source_note"
    ],
    list: (clientId, lifecycleStatus) => getCapitalAssets(clientId, lifecycleStatus) as Promise<FactItem[]>,
    create: (clientId, payload) => createCapitalAsset(clientId, payload as unknown as CapitalAssetCreatePayload),
    update: (clientId, id, payload) => updateCapitalAsset(clientId, id, payload)
  },
  {
    key: "recurring-incomes",
    heading: "Recurring incomes",
    emptyMessage: "No recurring incomes found for the selected lifecycle filter.",
    loadingMessage: "Loading recurring incomes...",
    createHeading: "Add Recurring Income",
    editHeading: "Edit Recurring Income",
    addButton: "Add Recurring Income",
    saveButton: "Save Recurring Income",
    editButton: "Edit Recurring Income",
    fields: [
      {
        name: "income_category",
        label: "Income Category",
        kind: "select",
        optional: false,
        options: ["employment", "pension", "rental", "business", "benefit", "other"]
      },
      { name: "description", label: "Description", kind: "text", optional: false },
      { name: "amount", label: "Amount", kind: "amount", optional: false },
      {
        name: "amount_basis",
        label: "Amount Basis",
        kind: "select",
        optional: false,
        options: ["gross", "net", "unknown"]
      },
      {
        name: "frequency",
        label: "Frequency",
        kind: "select",
        optional: false,
        options: ["monthly", "quarterly", "annual", "other"]
      },
      {
        name: "continuation_status",
        label: "Continuation Status",
        kind: "select",
        optional: false,
        options: ["ongoing", "known end date", "unknown"]
      },
      { name: "start_date", label: "Start Date", kind: "date", optional: true },
      { name: "end_date", label: "End Date", kind: "date", optional: true },
      ...metadataFields
    ],
    listFields: [
      "income_category",
      "description",
      "amount",
      "amount_basis",
      "frequency",
      "continuation_status",
      "start_date",
      "end_date",
      "source_type",
      "source_date",
      "source_note"
    ],
    list: (clientId, lifecycleStatus) => getRecurringIncomes(clientId, lifecycleStatus) as Promise<FactItem[]>,
    create: (clientId, payload) =>
      createRecurringIncome(clientId, payload as unknown as RecurringIncomeCreatePayload),
    update: (clientId, id, payload) => updateRecurringIncome(clientId, id, payload)
  },
  {
    key: "recurring-expenses",
    heading: "Recurring expenses",
    emptyMessage: "No recurring expenses found for the selected lifecycle filter.",
    loadingMessage: "Loading recurring expenses...",
    createHeading: "Add Recurring Expense",
    editHeading: "Edit Recurring Expense",
    addButton: "Add Recurring Expense",
    saveButton: "Save Recurring Expense",
    editButton: "Edit Recurring Expense",
    fields: [
      {
        name: "expense_category",
        label: "Expense Category",
        kind: "select",
        optional: false,
        options: ["housing", "health", "debt", "insurance", "living", "family support", "other"]
      },
      { name: "description", label: "Description", kind: "text", optional: false },
      { name: "amount", label: "Amount", kind: "amount", optional: false },
      {
        name: "frequency",
        label: "Frequency",
        kind: "select",
        optional: false,
        options: ["monthly", "quarterly", "annual", "other"]
      },
      {
        name: "expense_type",
        label: "Expense Type",
        kind: "select",
        optional: false,
        options: ["mandatory", "discretionary", "unknown"]
      },
      {
        name: "continuation_status",
        label: "Continuation Status",
        kind: "select",
        optional: false,
        options: ["ongoing", "known end date", "unknown"]
      },
      { name: "start_date", label: "Start Date", kind: "date", optional: true },
      { name: "end_date", label: "End Date", kind: "date", optional: true },
      ...metadataFields
    ],
    listFields: [
      "expense_category",
      "description",
      "amount",
      "frequency",
      "expense_type",
      "continuation_status",
      "start_date",
      "end_date",
      "source_type",
      "source_date",
      "source_note"
    ],
    list: (clientId, lifecycleStatus) => getRecurringExpenses(clientId, lifecycleStatus) as Promise<FactItem[]>,
    create: (clientId, payload) =>
      createRecurringExpense(clientId, payload as unknown as RecurringExpenseCreatePayload),
    update: (clientId, id, payload) => updateRecurringExpense(clientId, id, payload)
  },
  {
    key: "retirement-timing-work-intentions",
    heading: "Retirement timing and work intentions",
    emptyMessage: "No retirement timing and work intentions found for the selected lifecycle filter.",
    loadingMessage: "Loading retirement timing and work intentions...",
    createHeading: "Add Retirement Timing and Work Intention",
    editHeading: "Edit Retirement Timing and Work Intention",
    addButton: "Add Retirement Timing and Work Intention",
    saveButton: "Save Retirement Timing and Work Intention",
    editButton: "Edit Retirement Timing and Work Intention",
    fields: [
      {
        name: "timing_confidence",
        label: "Timing Confidence",
        kind: "select",
        optional: false,
        options: ["known", "stated intention", "uncertain", "not recorded"]
      },
      {
        name: "work_after_retirement_intention",
        label: "Work After Retirement Intention",
        kind: "select",
        optional: false,
        options: ["continue working", "stop working", "undecided", "not recorded"]
      },
      { name: "planned_work_end_date", label: "Planned Work End Date", kind: "date", optional: true },
      { name: "intended_pension_start_date", label: "Intended Pension Start Date", kind: "date", optional: true },
      { name: "other_known_retirement_date", label: "Other Known Retirement Date", kind: "date", optional: true },
      {
        name: "other_known_retirement_date_label",
        label: "Other Known Retirement Date Label",
        kind: "text",
        optional: true,
        showWhen: (formState) => formState.other_known_retirement_date.trim() !== ""
      },
      { name: "anticipated_work_end_date", label: "Anticipated Work End Date", kind: "date", optional: true },
      { name: "work_intention_note", label: "Work Intention Note", kind: "textarea", optional: true },
      ...metadataFields
    ],
    listFields: [
      "timing_confidence",
      "work_after_retirement_intention",
      "planned_work_end_date",
      "intended_pension_start_date",
      "other_known_retirement_date",
      "other_known_retirement_date_label",
      "anticipated_work_end_date",
      "work_intention_note",
      "source_type",
      "source_date",
      "source_note"
    ],
    list: (clientId, lifecycleStatus) =>
      getRetirementTimingWorkIntentions(clientId, lifecycleStatus) as Promise<FactItem[]>,
    create: (clientId, payload) =>
      createRetirementTimingWorkIntention(
        clientId,
        payload as unknown as RetirementTimingWorkIntentionCreatePayload
      ),
    update: (clientId, id, payload) => updateRetirementTimingWorkIntention(clientId, id, payload)
  }
];

export function RetirementPlanningFactsSection({ clientId }: RetirementPlanningFactsSectionProps) {
  return (
    <section aria-labelledby="retirement-planning-facts-heading">
      <h3 id="retirement-planning-facts-heading">Retirement Planning Facts</h3>
      {factSectionConfigs.map((config) => (
        <FactMaintenanceSection key={config.key} clientId={clientId} config={config} />
      ))}
    </section>
  );
}
