import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type ClientDetailItem,
  getClient
} from "../api/clientsApi";
import {
  createM02ManualIntake,
  downloadM02Source,
  type M02Intake,
  type M02LifecycleStatus,
  type M02ManualPayload,
  type M02UploadResult,
  listM02Intakes,
  transitionM02Intake,
  updateM02Intake,
  uploadM02Sources
} from "../api/m02IntakeApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";

const ACCEPTED_FILE_TYPES = ".pdf,.xml,.dat,.csv,.xlsx";
const MAX_FILE_BYTES = 26_214_400;

type ManualForm = {
  declaredProviderName: string;
  productName: string;
  productIdentifier: string;
  declaredAccountReference: string;
  declaredTotalBalanceAmount: string;
  declaredMonthlyPensionAmount: string;
  declaredComponentsText: string;
  declaredStatementDate: string;
  declaredStartDate: string;
  declaredProductType: string;
  sourceType: string;
  declaredBasis: string;
  notes: string;
};

const emptyForm: ManualForm = {
  declaredProviderName: "",
  productName: "",
  productIdentifier: "",
  declaredAccountReference: "",
  declaredTotalBalanceAmount: "",
  declaredMonthlyPensionAmount: "",
  declaredComponentsText: "",
  declaredStatementDate: "",
  declaredStartDate: "",
  declaredProductType: "",
  sourceType: "",
  declaredBasis: "",
  notes: ""
};

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function payloadFromForm(form: ManualForm): M02ManualPayload {
  const components = form.declaredComponentsText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const separator = line.indexOf("=");
      return {
        label: separator < 0 ? line : line.slice(0, separator).trim(),
        value: separator < 0 ? "" : line.slice(separator + 1).trim()
      };
    });
  return {
    declared_provider_name: nullable(form.declaredProviderName),
    product_name: nullable(form.productName),
    product_identifier: nullable(form.productIdentifier),
    declared_account_reference: nullable(form.declaredAccountReference),
    declared_total_balance_amount: nullable(form.declaredTotalBalanceAmount),
    declared_monthly_pension_amount: nullable(form.declaredMonthlyPensionAmount),
    declared_component_values: components.length ? components : null,
    declared_statement_date: nullable(form.declaredStatementDate),
    declared_start_date: nullable(form.declaredStartDate),
    declared_product_type: nullable(form.declaredProductType),
    source_type: form.sourceType.trim(),
    declared_basis: nullable(form.declaredBasis),
    notes: nullable(form.notes)
  };
}

function formFromIntake(intake: M02Intake): ManualForm {
  return {
    declaredProviderName: intake.declared_provider_name ?? "",
    productName: intake.product_name ?? "",
    productIdentifier: intake.product_identifier ?? "",
    declaredAccountReference: intake.declared_account_reference ?? "",
    declaredTotalBalanceAmount:
      intake.declared_total_balance_amount === null
        ? ""
        : String(intake.declared_total_balance_amount),
    declaredMonthlyPensionAmount:
      intake.declared_monthly_pension_amount === null
        ? ""
        : String(intake.declared_monthly_pension_amount),
    declaredComponentsText: (intake.declared_component_values ?? [])
      .map((component) => `${component.label}=${component.value}`)
      .join("\n"),
    declaredStatementDate: intake.declared_statement_date ?? "",
    declaredStartDate: intake.declared_start_date ?? "",
    declaredProductType: intake.declared_product_type ?? "",
    sourceType: intake.source_type,
    declaredBasis: intake.declared_basis ?? "",
    notes: intake.notes ?? ""
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return typeof error.body === "string"
      ? error.body
      : JSON.stringify(error.body, null, 2);
  }
  return error instanceof Error ? error.message : "The M02 operation failed.";
}

export function M02PensionIntakeScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const location = useLocation();
  const parsedClientId = Number(clientId);
  const validClientId =
    Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : null;
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(validClientId, location.key);

  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [intakes, setIntakes] = useState<M02Intake[]>([]);
  const [form, setForm] = useState<ManualForm>(emptyForm);
  const [editingIntakeId, setEditingIntakeId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<M02UploadResult[]>([]);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [transitioningId, setTransitioningId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    const context = captureClientContext();
    setClient(null);
    setIntakes([]);
    setForm(emptyForm);
    setEditingIntakeId(null);
    setSelectedFiles([]);
    setUploadResults([]);
    setBatchError(null);
    setLoadError(null);
    setMutationError(null);
    setSuccessMessage(null);
    setIsLoading(true);
    setIsSaving(false);
    setIsUploading(false);
    setTransitioningId(null);
    setDownloadingId(null);

    async function load() {
      if (validClientId === null) {
        if (isCurrentClientContext(context)) {
          setLoadError("Client not found.");
          setIsLoading(false);
        }
        return;
      }
      try {
        const [nextClient, nextIntakes] = await Promise.all([
          getClient(validClientId),
          listM02Intakes(validClientId)
        ]);
        if (!isCurrentClientContext(context)) {
          return;
        }
        setClient(nextClient);
        setIntakes(nextIntakes);
      } catch (error) {
        if (isCurrentClientContext(context)) {
          setLoadError(errorMessage(error));
        }
      } finally {
        if (isCurrentClientContext(context)) {
          setIsLoading(false);
        }
      }
    }
    void load();
  }, [
    captureClientContext,
    isCurrentClientContext,
    location.key,
    validClientId
  ]);

  async function refresh(context = captureClientContext()) {
    if (validClientId === null) {
      return;
    }
    const next = await listM02Intakes(validClientId);
    if (isCurrentClientContext(context)) {
      setIntakes(next);
    }
  }

  function updateForm(field: keyof ManualForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setMutationError(null);
    setSuccessMessage(null);
  }

  async function saveManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = captureClientContext();
    if (validClientId === null || client?.m01_case?.lifecycle_status === "archived") {
      return;
    }
    setIsSaving(true);
    setMutationError(null);
    setSuccessMessage(null);
    try {
      const payload = payloadFromForm(form);
      if (editingIntakeId === null) {
        await createM02ManualIntake(validClientId, payload);
      } else {
        await updateM02Intake(validClientId, editingIntakeId, payload);
      }
      if (!isCurrentClientContext(context)) {
        return;
      }
      await refresh(context);
      if (isCurrentClientContext(context)) {
        setForm(emptyForm);
        setEditingIntakeId(null);
        setSuccessMessage(
          editingIntakeId === null ? "Manual intake saved." : "Intake metadata updated."
        );
      }
    } catch (error) {
      if (isCurrentClientContext(context)) {
        setMutationError(errorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(context)) {
        setIsSaving(false);
      }
    }
  }

  function selectFiles(event: ChangeEvent<HTMLInputElement>) {
    const next = Array.from(event.target.files ?? []);
    setSelectedFiles(next);
    setUploadResults([]);
    setBatchError(null);
    setMutationError(null);
  }

  async function uploadFiles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = captureClientContext();
    if (
      validClientId === null
      || client?.m01_case?.lifecycle_status === "archived"
      || selectedFiles.length === 0
    ) {
      setMutationError("Select at least one opaque source file.");
      return;
    }
    const oversized = selectedFiles.find((file) => file.size > MAX_FILE_BYTES);
    if (oversized) {
      setMutationError(`${oversized.name} exceeds the per-file 25 MiB limit.`);
      return;
    }
    setIsUploading(true);
    setUploadResults([]);
    setBatchError(null);
    setMutationError(null);
    try {
      const response = await uploadM02Sources(validClientId, selectedFiles, {
        sourceType: form.sourceType,
        declaredProviderName: form.declaredProviderName,
        productName: form.productName,
        productIdentifier: form.productIdentifier,
        declaredAccountReference: form.declaredAccountReference,
        declaredStatementDate: form.declaredStatementDate
        ,
        declaredStartDate: form.declaredStartDate,
        declaredProductType: form.declaredProductType,
        declaredBasis: form.declaredBasis,
        notes: form.notes
      });
      if (!isCurrentClientContext(context)) {
        return;
      }
      setUploadResults(response.results);
      setBatchError(
        response.request_error
          ? `${response.request_error.code}: ${response.request_error.message}`
          : null
      );
      await refresh(context);
      if (isCurrentClientContext(context)) {
        setSelectedFiles([]);
      }
    } catch (error) {
      if (isCurrentClientContext(context)) {
        setBatchError(errorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(context)) {
        setIsUploading(false);
      }
    }
  }

  async function transition(intake: M02Intake, target: M02LifecycleStatus) {
    const context = captureClientContext();
    if (validClientId === null || client?.m01_case?.lifecycle_status === "archived") {
      return;
    }
    setTransitioningId(intake.intake_id);
    setMutationError(null);
    try {
      await transitionM02Intake(validClientId, intake.intake_id, target);
      if (isCurrentClientContext(context)) {
        await refresh(context);
      }
    } catch (error) {
      if (isCurrentClientContext(context)) {
        setMutationError(errorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(context)) {
        setTransitioningId(null);
      }
    }
  }

  async function download(intake: M02Intake) {
    const context = captureClientContext();
    if (validClientId === null || intake.source === null) {
      return;
    }
    setDownloadingId(intake.intake_id);
    setMutationError(null);
    try {
      const prepared = await downloadM02Source(validClientId, intake.source);
      if (!isCurrentClientContext(context)) {
        return;
      }
      const objectUrl = URL.createObjectURL(prepared.blob);
      try {
        if (!isCurrentClientContext(context)) {
          return;
        }
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = prepared.filename;
        anchor.rel = "noopener";
        anchor.click();
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    } catch (error) {
      if (isCurrentClientContext(context)) {
        setMutationError(errorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(context)) {
        setDownloadingId(null);
      }
    }
  }

  if (isLoading) {
    return <section><h2>M02 Pension Intake</h2><p>Loading M02 intake history...</p></section>;
  }

  return (
    <section>
      <h2>M02 Controlled Pension Intake</h2>
      <p>
        Active client: {client ? `${client.full_name} (#${client.client_id})` : "Unavailable"}
      </p>
      <p>
        M02 preserves declared metadata and opaque bytes only. It does not parse,
        classify, approve, or make a source authoritative.
      </p>
      {loadError ? <pre>{loadError}</pre> : null}

      {client?.m01_case?.lifecycle_status === "archived" ? (
        <p>Archived client case: M02 intake is read-only until the M01 case is reopened.</p>
      ) : null}

      <form onSubmit={saveManual}>
        <fieldset
          disabled={
            isSaving
            || client === null
            || client.m01_case?.lifecycle_status === "archived"
          }
        >
          <legend>{editingIntakeId ? "Correct intake metadata" : "Manual pension intake"}</legend>
          <label>Source type <input value={form.sourceType} onChange={(event) => updateForm("sourceType", event.target.value)} required /></label>
          <label>Declared provider <input value={form.declaredProviderName} onChange={(event) => updateForm("declaredProviderName", event.target.value)} /></label>
          <label>Product/fund name <input value={form.productName} onChange={(event) => updateForm("productName", event.target.value)} /></label>
          <label>Product/fund identifier <input value={form.productIdentifier} onChange={(event) => updateForm("productIdentifier", event.target.value)} /></label>
          <label>Declared account/reference <input value={form.declaredAccountReference} onChange={(event) => updateForm("declaredAccountReference", event.target.value)} /></label>
          <label>Declared total balance <input inputMode="decimal" value={form.declaredTotalBalanceAmount} onChange={(event) => updateForm("declaredTotalBalanceAmount", event.target.value)} /></label>
          <label>Declared monthly pension <input inputMode="decimal" value={form.declaredMonthlyPensionAmount} onChange={(event) => updateForm("declaredMonthlyPensionAmount", event.target.value)} /></label>
          <label>Declared components (one label=value per line) <textarea value={form.declaredComponentsText} onChange={(event) => updateForm("declaredComponentsText", event.target.value)} /></label>
          <label>Declared statement/import date <input type="date" value={form.declaredStatementDate} onChange={(event) => updateForm("declaredStatementDate", event.target.value)} /></label>
          <label>Declared start date <input type="date" value={form.declaredStartDate} onChange={(event) => updateForm("declaredStartDate", event.target.value)} /></label>
          <label>Declared product-type text <input value={form.declaredProductType} onChange={(event) => updateForm("declaredProductType", event.target.value)} /></label>
          <label>Declared basis <textarea value={form.declaredBasis} onChange={(event) => updateForm("declaredBasis", event.target.value)} /></label>
          <label>Notes <textarea value={form.notes} onChange={(event) => updateForm("notes", event.target.value)} /></label>
          <button type="submit">{isSaving ? "Saving..." : editingIntakeId ? "Save metadata correction" : "Save manual intake"}</button>
          {editingIntakeId ? <button type="button" onClick={() => { setEditingIntakeId(null); setForm(emptyForm); }}>Cancel correction</button> : null}
        </fieldset>
      </form>

      <form onSubmit={uploadFiles}>
        <fieldset
          disabled={
            isUploading
            || client === null
            || client.m01_case?.lifecycle_status === "archived"
          }
        >
          <legend>Preserve opaque source files</legend>
          <p>Accepted: PDF, XML, DAT, CSV, XLSX. Maximum 25 MiB per file. No content is parsed in M02.</p>
          <input aria-label="Opaque source files" type="file" accept={ACCEPTED_FILE_TYPES} multiple onChange={selectFiles} />
          {selectedFiles.length ? (
            <ul aria-label="Selected opaque files">
              {selectedFiles.map((file, index) => <li key={`${file.name}-${index}`}>{file.name} — {file.size} bytes</li>)}
            </ul>
          ) : null}
          <button type="submit">{isUploading ? "Preserving files..." : "Preserve selected files"}</button>
        </fieldset>
      </form>

      {batchError ? <p>Batch request error: {batchError}</p> : null}
      {uploadResults.length ? (
        <section aria-labelledby="upload-results-heading">
          <h3 id="upload-results-heading">Per-file results</h3>
          <ul>
            {uploadResults.map((result) => (
              <li key={`${result.selection_index}-${result.original_filename}`}>
                {result.original_filename}: {result.status}
                {result.error_code ? ` — ${result.error_code}: ${result.error_message}` : ""}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {mutationError ? <pre>{mutationError}</pre> : null}
      {successMessage ? <p>{successMessage}</p> : null}

      <section aria-labelledby="m02-history-heading">
        <h3 id="m02-history-heading">Retained intake history</h3>
        {intakes.length === 0 ? <p>No M02 intake records.</p> : (
          <ul>
            {intakes.map((intake) => (
              <li key={intake.intake_id}>
                <h4>{intake.product_name ?? intake.declared_product_type ?? "Unclassified declared product"}</h4>
                <p>Intake: {intake.intake_id}</p>
                <p>Source type: {intake.source_type}</p>
                <p>Lifecycle: {intake.lifecycle_status}; preservation: {intake.preservation_status}</p>
                {intake.manual_technical_reference ? (
                  <p>Operational technical reference (not an account): {intake.manual_technical_reference}</p>
                ) : null}
                {intake.diagnostics.length ? <p>Diagnostics: {intake.diagnostics.join(", ")}</p> : null}
                {intake.duplicate_candidate ? <p>Duplicate candidate only; same-client preserved bytes reused. Prior intake: {intake.duplicate_of_intake_id}</p> : null}
                {intake.superseding_candidate ? <p>Superseding candidate only; no automatic authority or supersession. Older intake: {intake.superseding_intake_id}</p> : null}
                {intake.source ? (
                  <>
                    <p>File: {intake.source.original_filename}; {intake.source.byte_size} bytes</p>
                    <p>SHA-256: {intake.source.sha256_checksum}</p>
                    <p>Validated media: {intake.source.validated_media_type}; detected encoding: {intake.source.detected_text_encoding ?? "not applicable"}</p>
                    <p>Preserved at: {intake.source.uploaded_at}</p>
                    <button type="button" disabled={downloadingId === intake.intake_id} onClick={() => void download(intake)}>
                      {downloadingId === intake.intake_id ? "Preparing attachment..." : "Download attachment"}
                    </button>
                  </>
                ) : null}
                {client?.m01_case?.lifecycle_status !== "archived"
                  && (["uploaded", "metadata_review"] as M02LifecycleStatus[]).includes(intake.lifecycle_status) ? (
                  <button type="button" onClick={() => { setEditingIntakeId(intake.intake_id); setForm(formFromIntake(intake)); setMutationError(null); }}>
                    Correct metadata
                  </button>
                ) : null}
                {client?.m01_case?.lifecycle_status === "archived" ? null : intake.allowed_lifecycle_targets.map((target) => (
                  <button
                    key={target}
                    type="button"
                    disabled={transitioningId === intake.intake_id}
                    onClick={() => void transition(intake, target)}
                  >
                    Move to {target}
                  </button>
                ))}
              </li>
            ))}
          </ul>
        )}
      </section>
      <p><Link to={validClientId === null ? "/clients" : `/clients/${validClientId}`}>Back to M01 client case</Link></p>
    </section>
  );
}
