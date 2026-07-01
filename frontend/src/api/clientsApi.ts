import { buildApiUrl } from "./apiBase";

export interface ApiTransportErrorShape {
  status: number;
  statusText: string;
  body: unknown;
}

export class ApiTransportError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor({ status, statusText, body }: ApiTransportErrorShape) {
    super(`HTTP ${status} ${statusText}`.trim());
    this.name = "ApiTransportError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export interface ClientListItem {
  client_id: number;
  full_name: string;
  id_number: string;
  birth_date: string | null;
  file_status: string;
  professional_identification_status: string;
}

export type ClientDetailItem = ClientListItem;

export interface ClientCreatePayload {
  full_name: string;
  id_number: string;
  birth_date: string | null;
}

export interface ClientProfileItem {
  client_profile_id: string;
  client_id: number;
  id_number: string | null;
  birth_date: string | null;
  gender: string | null;
  contact_method: string | null;
  contact_details: string | null;
  notes: string | null;
  file_status: string;
  professional_identification_status: string;
}

export interface ClientProfileResponse {
  profile: ClientProfileItem | null;
}

export interface ClientProfileUpdatePayload {
  id_number: string | null;
  birth_date: string | null;
  gender: string | null;
  contact_method: string | null;
  contact_details: string | null;
  notes: string | null;
}

export interface EmploymentRecordItem {
  employment_record_id: string;
  client_id: number;
  employer_name: string;
  work_start_date: string;
  work_end_date: string | null;
  is_current: boolean;
  notes: string | null;
}

export interface EmploymentRecordPayload {
  employer_name: string;
  work_start_date: string;
  work_end_date: string | null;
  is_current: boolean;
  notes: string | null;
}

export interface GrantItem {
  grant_id: string;
  client_id: number;
  employment_record_id: string | null;
  employer_name: string | null;
  nominal_amount: number | string | null;
  indexed_amount: number | string;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
  notes: string | null;
}

export interface GrantPayload {
  employment_record_id: string | null;
  employer_name: string | null;
  nominal_amount: string | null;
  indexed_amount: string;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
  notes: string | null;
}

export interface ActualCapitalizationItem {
  capitalization_id: string;
  client_id: number;
  amount: number | string;
  capitalization_date: string;
  source_label: string | null;
  source_basis: string | null;
  planner_assertion: string | null;
  planner_assertion_basis: string | null;
  notes: string | null;
}

export interface ActualCapitalizationPayload {
  amount: string;
  capitalization_date: string;
  source_label: string | null;
  source_basis: string | null;
  planner_assertion: string | null;
  planner_assertion_basis: string | null;
  notes: string | null;
}

export interface ClearinghouseSnapshotItem {
  clearinghouse_snapshot_id: string;
  client_id: number;
  import_date: string;
  source_type: string;
  source_file: string;
  collection_status: string;
  collection_notes: string | null;
  verification_status: string;
  verification_notes: string | null;
  verified_at: string | null;
  created_at: string;
}

export interface ClearinghouseSnapshotPayload {
  import_date: string;
  source_type: string;
  source_file: string;
  collection_status: string;
  collection_notes: string | null;
}

export interface RetirementPlanningDocumentItem {
  document_id: string;
  client_id: number;
  document_type: string;
  source_type: string | null;
  source_file: string;
  collection_date: string;
  collection_status: string;
  collection_notes: string | null;
  verification_status: string;
  verification_notes: string | null;
  verified_at: string | null;
  created_at: string;
}

export interface RetirementPlanningDocumentPayload {
  document_type: string;
  source_type: string | null;
  source_file: string;
  collection_date: string;
  collection_status: string;
  collection_notes: string | null;
}

export interface VerificationUpdatePayload {
  verification_status: string;
  verification_notes: string | null;
}

export interface MissingDataItem {
  missing_data_item_id: string;
  client_id: number;
  missing_item_type: string;
  missing_item_label: string;
  missing_status: string;
  notes: string | null;
  planning_domain: string | null;
  related_record_type: string | null;
  related_record_id: number | null;
  advisory_status: string | null;
  neutral_reason: string | null;
  created_at: string;
}

export interface MissingDataItemPayload {
  missing_item_type: string;
  missing_item_label: string;
  missing_status: string;
  notes: string | null;
}

export type LifecycleStatusFilter = "current" | "superseded" | "all";

export interface AdvisoryMissingInformationCreatePayload {
  missing_item_type: string;
  missing_item_label: string;
  missing_status: string;
  notes: string | null;
  planning_domain: string;
  advisory_status: "open";
  neutral_reason?: string | null;
}

export interface AdvisoryMissingInformationUpdatePayload {
  planning_domain?: string | null;
  advisory_status?: "open" | "resolved" | "no longer relevant" | null;
  neutral_reason?: string | null;
}

export interface PlannerAssumptionItem {
  id: number;
  client_id: number;
  assumption_category: string;
  title: string;
  assumption_value_text: string;
  rationale: string;
  owner: string;
  lifecycle_status: string;
  effective_start_date: string | null;
  effective_end_date: string | null;
  review_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlannerAssumptionCreatePayload {
  assumption_category: string;
  title: string;
  assumption_value_text: string;
  rationale: string;
  owner: string;
  effective_start_date?: string | null;
  effective_end_date?: string | null;
  review_date?: string | null;
}

export type PlannerAssumptionUpdatePayload = Partial<PlannerAssumptionCreatePayload>;

export interface FactMetadataPayload {
  source_status?: string | null;
  verification_state?: string | null;
  source_type?: string | null;
  source_date?: string | null;
  source_note?: string | null;
}

export interface PensionHoldingItem {
  id: number;
  client_id: number;
  provider_name: string;
  product_type: string;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
  product_name: string | null;
  account_reference: string | null;
  known_balance_amount: number | string | null;
  balance_as_of_date: string | null;
  known_monthly_pension_amount: number | string | null;
  pension_amount_as_of_date: string | null;
  source_type: string | null;
  source_date: string | null;
  source_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface PensionHoldingCreatePayload extends FactMetadataPayload {
  provider_name: string;
  product_type: string;
  product_name?: string | null;
  account_reference?: string | null;
  known_balance_amount?: string | null;
  balance_as_of_date?: string | null;
  known_monthly_pension_amount?: string | null;
  pension_amount_as_of_date?: string | null;
}

export type PensionHoldingUpdatePayload = Partial<PensionHoldingCreatePayload>;

export interface CapitalAssetItem {
  id: number;
  client_id: number;
  asset_category: string;
  asset_description: string;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
  known_value_amount: number | string | null;
  value_as_of_date: string | null;
  liquidity_note: string | null;
  restriction_note: string | null;
  source_type: string | null;
  source_date: string | null;
  source_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CapitalAssetCreatePayload extends FactMetadataPayload {
  asset_category: string;
  asset_description: string;
  known_value_amount?: string | null;
  value_as_of_date?: string | null;
  liquidity_note?: string | null;
  restriction_note?: string | null;
}

export type CapitalAssetUpdatePayload = Partial<CapitalAssetCreatePayload>;

export interface RecurringIncomeItem {
  id: number;
  client_id: number;
  income_category: string;
  description: string;
  amount: number | string;
  amount_basis: string;
  frequency: string;
  continuation_status: string;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
  start_date: string | null;
  end_date: string | null;
  source_type: string | null;
  source_date: string | null;
  source_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecurringIncomeCreatePayload extends FactMetadataPayload {
  income_category: string;
  description: string;
  amount: string;
  amount_basis: string;
  frequency: string;
  continuation_status: string;
  start_date?: string | null;
  end_date?: string | null;
}

export type RecurringIncomeUpdatePayload = Partial<RecurringIncomeCreatePayload>;

export interface RecurringExpenseItem {
  id: number;
  client_id: number;
  expense_category: string;
  description: string;
  amount: number | string;
  frequency: string;
  expense_type: string;
  continuation_status: string;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
  start_date: string | null;
  end_date: string | null;
  source_type: string | null;
  source_date: string | null;
  source_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecurringExpenseCreatePayload extends FactMetadataPayload {
  expense_category: string;
  description: string;
  amount: string;
  frequency: string;
  expense_type: string;
  continuation_status: string;
  start_date?: string | null;
  end_date?: string | null;
}

export type RecurringExpenseUpdatePayload = Partial<RecurringExpenseCreatePayload>;

export interface RetirementTimingWorkIntentionItem {
  id: number;
  client_id: number;
  timing_confidence: string;
  work_after_retirement_intention: string;
  lifecycle_status: string;
  source_status: string;
  verification_state: string;
  planned_work_end_date: string | null;
  intended_pension_start_date: string | null;
  other_known_retirement_date: string | null;
  other_known_retirement_date_label: string | null;
  anticipated_work_end_date: string | null;
  work_intention_note: string | null;
  source_type: string | null;
  source_date: string | null;
  source_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface RetirementTimingWorkIntentionCreatePayload extends FactMetadataPayload {
  timing_confidence: string;
  work_after_retirement_intention: string;
  planned_work_end_date?: string | null;
  intended_pension_start_date?: string | null;
  other_known_retirement_date?: string | null;
  other_known_retirement_date_label?: string | null;
  anticipated_work_end_date?: string | null;
  work_intention_note?: string | null;
}

export type RetirementTimingWorkIntentionUpdatePayload = Partial<RetirementTimingWorkIntentionCreatePayload>;

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    }
  });

  const body = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiTransportError({
      status: response.status,
      statusText: response.statusText,
      body
    });
  }

  return body as T;
}

export function getClients(): Promise<ClientListItem[]> {
  return requestJson<unknown>("/clients", {
    method: "GET"
  }).then((body) => {
    if (!Array.isArray(body)) {
      throw new Error("Unexpected clients response shape.");
    }

    return body as ClientListItem[];
  });
}

export function getClient(clientId: number): Promise<ClientDetailItem> {
  return requestJson<ClientDetailItem>(`/clients/${clientId}`, {
    method: "GET"
  });
}

export function createClient(payload: ClientCreatePayload): Promise<ClientDetailItem> {
  return requestJson<ClientDetailItem>("/clients", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getClientProfile(clientId: number): Promise<ClientProfileResponse> {
  return requestJson<ClientProfileResponse>(`/clients/${clientId}/profile`, {
    method: "GET"
  });
}

export function updateClientProfile(
  clientId: number,
  payload: ClientProfileUpdatePayload
): Promise<ClientProfileResponse> {
  return requestJson<ClientProfileResponse>(`/clients/${clientId}/profile`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getEmploymentRecords(clientId: number): Promise<EmploymentRecordItem[]> {
  return requestJson<EmploymentRecordItem[]>(`/clients/${clientId}/employment-records`, {
    method: "GET"
  });
}

export function createEmploymentRecord(
  clientId: number,
  payload: EmploymentRecordPayload
): Promise<EmploymentRecordItem> {
  return requestJson<EmploymentRecordItem>(`/clients/${clientId}/employment-records`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateEmploymentRecord(
  clientId: number,
  employmentRecordId: string,
  payload: EmploymentRecordPayload
): Promise<EmploymentRecordItem> {
  return requestJson<EmploymentRecordItem>(`/clients/${clientId}/employment-records/${employmentRecordId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteEmploymentRecord(clientId: number, employmentRecordId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/employment-records/${employmentRecordId}`, {
    method: "DELETE"
  });
}

export function getGrants(clientId: number): Promise<GrantItem[]> {
  return requestJson<GrantItem[]>(`/clients/${clientId}/grants`, {
    method: "GET"
  });
}

export function createGrant(clientId: number, payload: GrantPayload): Promise<GrantItem> {
  return requestJson<GrantItem>(`/clients/${clientId}/grants`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateGrant(clientId: number, grantId: string, payload: GrantPayload): Promise<GrantItem> {
  return requestJson<GrantItem>(`/clients/${clientId}/grants/${grantId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteGrant(clientId: number, grantId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/grants/${grantId}`, {
    method: "DELETE"
  });
}

export function getActualCapitalizations(clientId: number): Promise<ActualCapitalizationItem[]> {
  return requestJson<ActualCapitalizationItem[]>(`/clients/${clientId}/actual-capitalizations`, {
    method: "GET"
  });
}

export function createActualCapitalization(
  clientId: number,
  payload: ActualCapitalizationPayload
): Promise<ActualCapitalizationItem> {
  return requestJson<ActualCapitalizationItem>(`/clients/${clientId}/actual-capitalizations`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateActualCapitalization(
  clientId: number,
  capitalizationId: string,
  payload: ActualCapitalizationPayload
): Promise<ActualCapitalizationItem> {
  return requestJson<ActualCapitalizationItem>(`/clients/${clientId}/actual-capitalizations/${capitalizationId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteActualCapitalization(clientId: number, capitalizationId: string): Promise<unknown> {
  return requestJson<unknown>(`/clients/${clientId}/actual-capitalizations/${capitalizationId}`, {
    method: "DELETE"
  });
}

export function getClearinghouseSnapshots(clientId: number): Promise<ClearinghouseSnapshotItem[]> {
  return requestJson<ClearinghouseSnapshotItem[]>(`/clients/${clientId}/clearinghouse-snapshots`, {
    method: "GET"
  });
}

export function createClearinghouseSnapshot(
  clientId: number,
  payload: ClearinghouseSnapshotPayload
): Promise<ClearinghouseSnapshotItem> {
  return requestJson<ClearinghouseSnapshotItem>(`/clients/${clientId}/clearinghouse-snapshots`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateClearinghouseSnapshotVerification(
  clientId: number,
  clearinghouseSnapshotId: string,
  payload: VerificationUpdatePayload
): Promise<ClearinghouseSnapshotItem> {
  return requestJson<ClearinghouseSnapshotItem>(
    `/clients/${clientId}/clearinghouse-snapshots/${clearinghouseSnapshotId}/verification`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    }
  );
}

export function getRetirementPlanningDocuments(clientId: number): Promise<RetirementPlanningDocumentItem[]> {
  return requestJson<RetirementPlanningDocumentItem[]>(`/clients/${clientId}/documents`, {
    method: "GET"
  });
}

export function createRetirementPlanningDocument(
  clientId: number,
  payload: RetirementPlanningDocumentPayload
): Promise<RetirementPlanningDocumentItem> {
  return requestJson<RetirementPlanningDocumentItem>(`/clients/${clientId}/documents`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRetirementPlanningDocumentVerification(
  clientId: number,
  documentId: string,
  payload: VerificationUpdatePayload
): Promise<RetirementPlanningDocumentItem> {
  return requestJson<RetirementPlanningDocumentItem>(`/clients/${clientId}/documents/${documentId}/verification`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getMissingDataItems(clientId: number): Promise<MissingDataItem[]> {
  return requestJson<MissingDataItem[]>(`/clients/${clientId}/missing-items`, {
    method: "GET"
  });
}

export function createMissingDataItem(
  clientId: number,
  payload: MissingDataItemPayload
): Promise<MissingDataItem> {
  return requestJson<MissingDataItem>(`/clients/${clientId}/missing-items`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createAdvisoryMissingInformation(
  clientId: number,
  payload: AdvisoryMissingInformationCreatePayload
): Promise<MissingDataItem> {
  return requestJson<MissingDataItem>(`/clients/${clientId}/missing-items`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateAdvisoryMissingInformation(
  clientId: number,
  missingDataItemId: string,
  payload: AdvisoryMissingInformationUpdatePayload
): Promise<MissingDataItem> {
  return requestJson<MissingDataItem>(`/clients/${clientId}/missing-items/${missingDataItemId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

function factListPath(clientId: number, resourcePath: string, lifecycleStatus: LifecycleStatusFilter): string {
  return `/clients/${clientId}/${resourcePath}?lifecycle_status=${encodeURIComponent(lifecycleStatus)}`;
}

export function getPlannerAssumptions(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<PlannerAssumptionItem[]> {
  return requestJson<PlannerAssumptionItem[]>(factListPath(clientId, "planner-assumptions", lifecycleStatus), {
    method: "GET"
  });
}

export function createPlannerAssumption(
  clientId: number,
  payload: PlannerAssumptionCreatePayload
): Promise<PlannerAssumptionItem> {
  return requestJson<PlannerAssumptionItem>(`/clients/${clientId}/planner-assumptions`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updatePlannerAssumption(
  clientId: number,
  plannerAssumptionId: number,
  payload: PlannerAssumptionUpdatePayload
): Promise<PlannerAssumptionItem> {
  return requestJson<PlannerAssumptionItem>(`/clients/${clientId}/planner-assumptions/${plannerAssumptionId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getPensionHoldings(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<PensionHoldingItem[]> {
  return requestJson<PensionHoldingItem[]>(factListPath(clientId, "pension-holdings", lifecycleStatus), {
    method: "GET"
  });
}

export function createPensionHolding(
  clientId: number,
  payload: PensionHoldingCreatePayload
): Promise<PensionHoldingItem> {
  return requestJson<PensionHoldingItem>(`/clients/${clientId}/pension-holdings`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updatePensionHolding(
  clientId: number,
  pensionHoldingId: number,
  payload: PensionHoldingUpdatePayload
): Promise<PensionHoldingItem> {
  return requestJson<PensionHoldingItem>(`/clients/${clientId}/pension-holdings/${pensionHoldingId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getCapitalAssets(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<CapitalAssetItem[]> {
  return requestJson<CapitalAssetItem[]>(factListPath(clientId, "capital-assets", lifecycleStatus), {
    method: "GET"
  });
}

export function createCapitalAsset(
  clientId: number,
  payload: CapitalAssetCreatePayload
): Promise<CapitalAssetItem> {
  return requestJson<CapitalAssetItem>(`/clients/${clientId}/capital-assets`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateCapitalAsset(
  clientId: number,
  capitalAssetId: number,
  payload: CapitalAssetUpdatePayload
): Promise<CapitalAssetItem> {
  return requestJson<CapitalAssetItem>(`/clients/${clientId}/capital-assets/${capitalAssetId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getRecurringIncomes(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<RecurringIncomeItem[]> {
  return requestJson<RecurringIncomeItem[]>(factListPath(clientId, "recurring-incomes", lifecycleStatus), {
    method: "GET"
  });
}

export function createRecurringIncome(
  clientId: number,
  payload: RecurringIncomeCreatePayload
): Promise<RecurringIncomeItem> {
  return requestJson<RecurringIncomeItem>(`/clients/${clientId}/recurring-incomes`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRecurringIncome(
  clientId: number,
  recurringIncomeId: number,
  payload: RecurringIncomeUpdatePayload
): Promise<RecurringIncomeItem> {
  return requestJson<RecurringIncomeItem>(`/clients/${clientId}/recurring-incomes/${recurringIncomeId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getRecurringExpenses(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<RecurringExpenseItem[]> {
  return requestJson<RecurringExpenseItem[]>(factListPath(clientId, "recurring-expenses", lifecycleStatus), {
    method: "GET"
  });
}

export function createRecurringExpense(
  clientId: number,
  payload: RecurringExpenseCreatePayload
): Promise<RecurringExpenseItem> {
  return requestJson<RecurringExpenseItem>(`/clients/${clientId}/recurring-expenses`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateRecurringExpense(
  clientId: number,
  recurringExpenseId: number,
  payload: RecurringExpenseUpdatePayload
): Promise<RecurringExpenseItem> {
  return requestJson<RecurringExpenseItem>(`/clients/${clientId}/recurring-expenses/${recurringExpenseId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getRetirementTimingWorkIntentions(
  clientId: number,
  lifecycleStatus: LifecycleStatusFilter = "current"
): Promise<RetirementTimingWorkIntentionItem[]> {
  return requestJson<RetirementTimingWorkIntentionItem[]>(
    factListPath(clientId, "retirement-timing-work-intentions", lifecycleStatus),
    {
      method: "GET"
    }
  );
}

export function createRetirementTimingWorkIntention(
  clientId: number,
  payload: RetirementTimingWorkIntentionCreatePayload
): Promise<RetirementTimingWorkIntentionItem> {
  return requestJson<RetirementTimingWorkIntentionItem>(
    `/clients/${clientId}/retirement-timing-work-intentions`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function updateRetirementTimingWorkIntention(
  clientId: number,
  retirementTimingWorkIntentionId: number,
  payload: RetirementTimingWorkIntentionUpdatePayload
): Promise<RetirementTimingWorkIntentionItem> {
  return requestJson<RetirementTimingWorkIntentionItem>(
    `/clients/${clientId}/retirement-timing-work-intentions/${retirementTimingWorkIntentionId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    }
  );
}
