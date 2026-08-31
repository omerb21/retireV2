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
import { HebrewDateInput } from "../components/HebrewDateInput";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";

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
  recordHeading: string;
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
  { name: "source_status", label: "מצב מקור", kind: "select", optional: true, options: sourceStatusOptions },
  {
    name: "verification_state",
    label: "מצב אימות",
    kind: "select",
    optional: true,
    options: verificationStateOptions
  },
  { name: "source_type", label: "סוג מקור", kind: "text", optional: true },
  { name: "source_date", label: "תאריך מקור", kind: "date", optional: true },
  { name: "source_note", label: "הערת מקור", kind: "textarea", optional: true }
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

  return "לא ניתן לטעון את עובדות תכנון הפרישה.";
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

function fieldConfig(config: FactSectionConfig, fieldName: string): FieldConfig | undefined {
  return config.fields.find((field) => field.name === fieldName);
}

function displayedFieldValue(field: FieldConfig | undefined, value: string): string {
  if (field?.kind === "date") return formatIsoDate(value);
  if (field?.kind === "select") return heLabel(value);
  return value;
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
          <option value="">לא נבחר</option>
          {(field.options ?? []).map((option) => (
            <option key={option} value={option}>
              {heLabel(option)}
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

  if (field.kind === "date") {
    return (
      <p key={field.name}>
        <label htmlFor={fieldId}>{field.label}</label>
        <HebrewDateInput id={fieldId} value={value} onChange={(next) => onFieldChange(field.name, next)} />
      </p>
    );
  }

  return (
    <p key={field.name}>
      <label htmlFor={fieldId}>{field.label}</label>
      <input
        id={fieldId}
        type={field.kind === "amount" ? "number" : "text"}
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
        <label htmlFor={`${config.key}-lifecycle-filter`}>סינון לפי מצב מחזור חיים</label>
        <select
          id={`${config.key}-lifecycle-filter`}
          value={lifecycleStatus}
          onChange={(event) => {
            setLifecycleStatus(event.target.value as LifecycleStatusFilter);
          }}
        >
          {lifecycleOptions.map((option) => (
            <option key={option} value={option}>
              {heLabel(option)}
            </option>
          ))}
        </select>
      </p>
      {isLoading ? (
        <p>{config.loadingMessage}</p>
      ) : errorMessage !== null ? (
        <>
          <p>לא ניתן לטעון את הרשומות.</p>
          <pre>{errorMessage}</pre>
        </>
      ) : items.length === 0 ? (
        <p>{config.emptyMessage}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <article>
                <h5>{config.recordHeading} {item.id}</h5>
                <p>מצב מחזור חיים: {heLabel(item.lifecycle_status)}</p>
                <p>מצב מקור: {heLabel(item.source_status)}</p>
                <p>מצב אימות: {heLabel(item.verification_state)}</p>
                {config.listFields.map((fieldName) => {
                  const value = fieldValue(item, fieldName);
                  return value === null ? null : (
                    <p key={fieldName}>
                      {fieldConfig(config, fieldName)?.label ?? fieldName}: {displayedFieldValue(fieldConfig(config, fieldName), value)}
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
            <p>לא ניתן לשמור את הרשומה.</p>
            <pre>{mutationErrorMessage}</pre>
          </>
        ) : null}
        <p>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "שומר…" : editingId === null ? config.addButton : config.saveButton}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetForm} disabled={isSubmitting}>
              ביטול העריכה
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
    heading: "אחזקות פנסיוניות",
    recordHeading: "רשומת אחזקה פנסיונית",
    emptyMessage: "לא נמצאו אחזקות פנסיוניות עבור מסנן מחזור החיים שנבחר.",
    loadingMessage: "טוען אחזקות פנסיוניות…",
    createHeading: "הוספת אחזקה פנסיונית",
    editHeading: "עריכת אחזקה פנסיונית",
    addButton: "הוספת אחזקה פנסיונית",
    saveButton: "שמירת אחזקה פנסיונית",
    editButton: "עריכת אחזקה פנסיונית",
    fields: [
      { name: "provider_name", label: "שם הגוף המנהל", kind: "text", optional: false },
      {
        name: "product_type",
        label: "סוג מוצר",
        kind: "select",
        optional: false,
        options: ["pension fund", "provident fund", "insurance policy", "other"]
      },
      { name: "product_name", label: "שם מוצר", kind: "text", optional: true },
      { name: "account_reference", label: "אסמכתת חשבון", kind: "text", optional: true },
      { name: "known_balance_amount", label: "יתרה ידועה", kind: "amount", optional: true },
      {
        name: "balance_as_of_date",
        label: "תאריך נכונות היתרה",
        kind: "date",
        optional: true,
        showWhen: (formState) => formState.known_balance_amount.trim() !== ""
      },
      {
        name: "known_monthly_pension_amount",
        label: "קצבה חודשית ידועה",
        kind: "amount",
        optional: true
      },
      {
        name: "pension_amount_as_of_date",
        label: "תאריך נכונות הקצבה",
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
    heading: "נכסי הון",
    recordHeading: "רשומת נכס הון",
    emptyMessage: "לא נמצאו נכסי הון עבור מסנן מחזור החיים שנבחר.",
    loadingMessage: "טוען נכסי הון…",
    createHeading: "הוספת נכס הון",
    editHeading: "עריכת נכס הון",
    addButton: "הוספת נכס הון",
    saveButton: "שמירת נכס הון",
    editButton: "עריכת נכס הון",
    fields: [
      {
        name: "asset_category",
        label: "קטגוריית נכס",
        kind: "select",
        optional: false,
        options: ["bank deposit", "investment account", "securities", "real estate", "private asset", "other"]
      },
      { name: "asset_description", label: "תיאור הנכס", kind: "text", optional: false },
      { name: "known_value_amount", label: "שווי ידוע", kind: "amount", optional: true },
      {
        name: "value_as_of_date",
        label: "תאריך נכונות השווי",
        kind: "date",
        optional: true,
        showWhen: (formState) => formState.known_value_amount.trim() !== ""
      },
      { name: "liquidity_note", label: "הערת נזילות", kind: "textarea", optional: true },
      { name: "restriction_note", label: "הערת מגבלה", kind: "textarea", optional: true },
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
    heading: "הכנסות שוטפות",
    recordHeading: "רשומת הכנסה שוטפת",
    emptyMessage: "לא נמצאו הכנסות שוטפות עבור מסנן מחזור החיים שנבחר.",
    loadingMessage: "טוען הכנסות שוטפות…",
    createHeading: "הוספת הכנסה שוטפת",
    editHeading: "עריכת הכנסה שוטפת",
    addButton: "הוספת הכנסה שוטפת",
    saveButton: "שמירת הכנסה שוטפת",
    editButton: "עריכת הכנסה שוטפת",
    fields: [
      {
        name: "income_category",
        label: "קטגוריית הכנסה",
        kind: "select",
        optional: false,
        options: ["employment", "pension", "rental", "business", "benefit", "other"]
      },
      { name: "description", label: "תיאור", kind: "text", optional: false },
      { name: "amount", label: "סכום", kind: "amount", optional: false },
      {
        name: "amount_basis",
        label: "בסיס הסכום",
        kind: "select",
        optional: false,
        options: ["gross", "net", "unknown"]
      },
      {
        name: "frequency",
        label: "תדירות",
        kind: "select",
        optional: false,
        options: ["monthly", "quarterly", "annual", "other"]
      },
      {
        name: "continuation_status",
        label: "מצב המשכיות",
        kind: "select",
        optional: false,
        options: ["ongoing", "known end date", "unknown"]
      },
      { name: "start_date", label: "תאריך התחלה", kind: "date", optional: true },
      { name: "end_date", label: "תאריך סיום", kind: "date", optional: true },
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
    heading: "הוצאות שוטפות",
    recordHeading: "רשומת הוצאה שוטפת",
    emptyMessage: "לא נמצאו הוצאות שוטפות עבור מסנן מחזור החיים שנבחר.",
    loadingMessage: "טוען הוצאות שוטפות…",
    createHeading: "הוספת הוצאה שוטפת",
    editHeading: "עריכת הוצאה שוטפת",
    addButton: "הוספת הוצאה שוטפת",
    saveButton: "שמירת הוצאה שוטפת",
    editButton: "עריכת הוצאה שוטפת",
    fields: [
      {
        name: "expense_category",
        label: "קטגוריית הוצאה",
        kind: "select",
        optional: false,
        options: ["housing", "health", "debt", "insurance", "living", "family support", "other"]
      },
      { name: "description", label: "תיאור", kind: "text", optional: false },
      { name: "amount", label: "סכום", kind: "amount", optional: false },
      {
        name: "frequency",
        label: "תדירות",
        kind: "select",
        optional: false,
        options: ["monthly", "quarterly", "annual", "other"]
      },
      {
        name: "expense_type",
        label: "סוג הוצאה",
        kind: "select",
        optional: false,
        options: ["mandatory", "discretionary", "unknown"]
      },
      {
        name: "continuation_status",
        label: "מצב המשכיות",
        kind: "select",
        optional: false,
        options: ["ongoing", "known end date", "unknown"]
      },
      { name: "start_date", label: "תאריך התחלה", kind: "date", optional: true },
      { name: "end_date", label: "תאריך סיום", kind: "date", optional: true },
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
    heading: "עיתוי פרישה וכוונות עבודה",
    recordHeading: "רשומת עיתוי פרישה וכוונת עבודה",
    emptyMessage: "לא נמצאו נתוני עיתוי פרישה וכוונות עבודה עבור מסנן מחזור החיים שנבחר.",
    loadingMessage: "טוען נתוני עיתוי פרישה וכוונות עבודה…",
    createHeading: "הוספת עיתוי פרישה וכוונת עבודה",
    editHeading: "עריכת עיתוי פרישה וכוונת עבודה",
    addButton: "הוספת עיתוי פרישה וכוונת עבודה",
    saveButton: "שמירת עיתוי פרישה וכוונת עבודה",
    editButton: "עריכת עיתוי פרישה וכוונת עבודה",
    fields: [
      {
        name: "timing_confidence",
        label: "ודאות העיתוי",
        kind: "select",
        optional: false,
        options: ["known", "stated intention", "uncertain", "not recorded"]
      },
      {
        name: "work_after_retirement_intention",
        label: "כוונת עבודה לאחר הפרישה",
        kind: "select",
        optional: false,
        options: ["continue working", "stop working", "undecided", "not recorded"]
      },
      { name: "planned_work_end_date", label: "תאריך מתוכנן לסיום העבודה", kind: "date", optional: true },
      { name: "intended_pension_start_date", label: "תאריך מיועד לתחילת הקצבה", kind: "date", optional: true },
      { name: "other_known_retirement_date", label: "תאריך פרישה ידוע נוסף", kind: "date", optional: true },
      {
        name: "other_known_retirement_date_label",
        label: "תיאור תאריך הפרישה הידוע הנוסף",
        kind: "text",
        optional: true,
        showWhen: (formState) => formState.other_known_retirement_date.trim() !== ""
      },
      { name: "anticipated_work_end_date", label: "תאריך משוער לסיום העבודה", kind: "date", optional: true },
      { name: "work_intention_note", label: "הערת כוונת עבודה", kind: "textarea", optional: true },
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
      <h3 id="retirement-planning-facts-heading">עובדות תכנון פרישה</h3>
      {factSectionConfigs.map((config) => (
        <FactMaintenanceSection key={config.key} clientId={clientId} config={config} />
      ))}
    </section>
  );
}
