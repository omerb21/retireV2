import { type FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type ClearinghouseSnapshotItem,
  type ClientDetailItem,
  createMissingDataItem,
  createClearinghouseSnapshot,
  createRetirementPlanningDocument,
  getClient,
  getClientProfile,
  getClearinghouseSnapshots,
  getMissingDataItems,
  getRetirementPlanningDocuments,
  type M01CaseItem,
  type M01EmploymentStatus,
  type M01LifecycleStatus,
  type MissingDataItem,
  type RetirementPlanningDocumentItem,
  transitionClientCase,
  updateClearinghouseSnapshotVerification,
  updateClientCase,
  updateClientProfile,
  updateRetirementPlanningDocumentVerification
} from "../api/clientsApi";
import {
  type ClientContextToken,
  useClientContextGeneration
} from "../hooks/useClientContextGeneration";
import { AdvisoryMissingInformationSection } from "./AdvisoryMissingInformationSection";
import { PensionAnalysisRecordSection } from "./PensionAnalysisRecordSection";
import { PlannerAssumptionsSection } from "./PlannerAssumptionsSection";
import { RetirementPlanningConsolidatedReviewSection } from "./RetirementPlanningConsolidatedReviewSection";
import { RetirementPlanningFactsSection } from "./RetirementPlanningFactsSection";

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

  return "Unable to load client details.";
}

export function ClientDetailScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const location = useLocation();
  const parsedClientId = Number(clientId);
  const validRouteClientId =
    Number.isInteger(parsedClientId) && parsedClientId > 0 ? parsedClientId : null;
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(validRouteClientId, location.key);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [idNumber, setIdNumber] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState("");
  const [contactMethod, setContactMethod] = useState("");
  const [contactDetails, setContactDetails] = useState("");
  const [notes, setNotes] = useState("");
  const [professionalIdentificationStatus, setProfessionalIdentificationStatus] = useState("identification_incomplete");
  const [profileExists, setProfileExists] = useState(false);
  const [profileLoadErrorMessage, setProfileLoadErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const [clearinghouseSnapshots, setClearinghouseSnapshots] = useState<ClearinghouseSnapshotItem[]>([]);
  const [retirementPlanningDocuments, setRetirementPlanningDocuments] = useState<RetirementPlanningDocumentItem[]>([]);
  const [missingDataItems, setMissingDataItems] = useState<MissingDataItem[]>([]);
  const [collectionLoadErrorMessage, setCollectionLoadErrorMessage] = useState<string | null>(null);
  const [snapshotImportDate, setSnapshotImportDate] = useState("");
  const [snapshotSourceType, setSnapshotSourceType] = useState("");
  const [snapshotSourceFile, setSnapshotSourceFile] = useState("");
  const [snapshotCollectionStatus, setSnapshotCollectionStatus] = useState("");
  const [snapshotCollectionNotes, setSnapshotCollectionNotes] = useState("");
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [snapshotSaveErrorMessage, setSnapshotSaveErrorMessage] = useState<string | null>(null);
  const [snapshotSaveSuccessMessage, setSnapshotSaveSuccessMessage] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState("");
  const [documentSourceType, setDocumentSourceType] = useState("");
  const [documentSourceFile, setDocumentSourceFile] = useState("");
  const [documentCollectionDate, setDocumentCollectionDate] = useState("");
  const [documentCollectionStatus, setDocumentCollectionStatus] = useState("");
  const [documentCollectionNotes, setDocumentCollectionNotes] = useState("");
  const [isSavingDocument, setIsSavingDocument] = useState(false);
  const [documentSaveErrorMessage, setDocumentSaveErrorMessage] = useState<string | null>(null);
  const [documentSaveSuccessMessage, setDocumentSaveSuccessMessage] = useState<string | null>(null);
  const [snapshotVerificationStatusById, setSnapshotVerificationStatusById] = useState<Record<string, string>>({});
  const [snapshotVerificationNotesById, setSnapshotVerificationNotesById] = useState<Record<string, string>>({});
  const [documentVerificationStatusById, setDocumentVerificationStatusById] = useState<Record<string, string>>({});
  const [documentVerificationNotesById, setDocumentVerificationNotesById] = useState<Record<string, string>>({});
  const [verificationSaveMessage, setVerificationSaveMessage] = useState<string | null>(null);
  const [verificationErrorMessage, setVerificationErrorMessage] = useState<string | null>(null);
  const [missingItemType, setMissingItemType] = useState("data");
  const [missingItemLabel, setMissingItemLabel] = useState("");
  const [missingStatus, setMissingStatus] = useState("");
  const [missingNotes, setMissingNotes] = useState("");
  const [isSavingMissingItem, setIsSavingMissingItem] = useState(false);
  const [missingSaveErrorMessage, setMissingSaveErrorMessage] = useState<string | null>(null);
  const [missingSaveSuccessMessage, setMissingSaveSuccessMessage] = useState<string | null>(null);
  const [m01Case, setM01Case] = useState<M01CaseItem | null>(null);
  const [caseDisplayName, setCaseDisplayName] = useState("");
  const [caseIdNumber, setCaseIdNumber] = useState("");
  const [caseBirthDate, setCaseBirthDate] = useState("");
  const [caseGender, setCaseGender] = useState("");
  const [caseEmploymentStatus, setCaseEmploymentStatus] =
    useState<M01EmploymentStatus | "">("");
  const [plannedRetirementMode, setPlannedRetirementMode] =
    useState<"age" | "date" | "">("");
  const [plannedRetirementAge, setPlannedRetirementAge] = useState("");
  const [plannedRetirementDate, setPlannedRetirementDate] = useState("");
  const [isSavingCase, setIsSavingCase] = useState(false);
  const [caseSaveMessage, setCaseSaveMessage] = useState<string | null>(null);
  const [caseErrorMessage, setCaseErrorMessage] = useState<string | null>(null);
  const [isTransitioningCase, setIsTransitioningCase] = useState(false);
  const [loadedClientContext, setLoadedClientContext] =
    useState<ClientContextToken | null>(null);

  function applyM01Case(nextCase: M01CaseItem) {
    setM01Case(nextCase);
    setCaseDisplayName(nextCase.display_name);
    setCaseIdNumber(nextCase.id_number);
    setCaseBirthDate(nextCase.birth_date ?? "");
    setCaseGender(nextCase.gender ?? "");
    setCaseEmploymentStatus(nextCase.employment_status ?? "");
    setPlannedRetirementMode(
      nextCase.planned_retirement_age !== null
        ? "age"
        : nextCase.planned_retirement_date !== null
          ? "date"
          : ""
    );
    setPlannedRetirementAge(
      nextCase.planned_retirement_age !== null
        ? String(nextCase.planned_retirement_age)
        : ""
    );
    setPlannedRetirementDate(nextCase.planned_retirement_date ?? "");
  }

  useEffect(() => {
    let isActive = true;
    const clientContext = captureClientContext();

    setClient(null);
    setLoadedClientContext(null);
    setIsLoading(true);
    setIsNotFound(false);
    setErrorMessage(null);
    setIdNumber("");
    setBirthDate("");
    setGender("");
    setContactMethod("");
    setContactDetails("");
    setNotes("");
    setProfessionalIdentificationStatus("identification_incomplete");
    setProfileExists(false);
    setProfileLoadErrorMessage(null);
    setIsSaving(false);
    setSaveErrorMessage(null);
    setSaveSuccessMessage(null);
    setClearinghouseSnapshots([]);
    setRetirementPlanningDocuments([]);
    setMissingDataItems([]);
    setCollectionLoadErrorMessage(null);
    setSnapshotImportDate("");
    setSnapshotSourceType("");
    setSnapshotSourceFile("");
    setSnapshotCollectionStatus("");
    setSnapshotCollectionNotes("");
    setIsSavingSnapshot(false);
    setSnapshotSaveErrorMessage(null);
    setSnapshotSaveSuccessMessage(null);
    setDocumentType("");
    setDocumentSourceType("");
    setDocumentSourceFile("");
    setDocumentCollectionDate("");
    setDocumentCollectionStatus("");
    setDocumentCollectionNotes("");
    setIsSavingDocument(false);
    setDocumentSaveErrorMessage(null);
    setDocumentSaveSuccessMessage(null);
    setSnapshotVerificationStatusById({});
    setSnapshotVerificationNotesById({});
    setDocumentVerificationStatusById({});
    setDocumentVerificationNotesById({});
    setVerificationSaveMessage(null);
    setVerificationErrorMessage(null);
    setMissingItemType("data");
    setMissingItemLabel("");
    setMissingStatus("");
    setMissingNotes("");
    setIsSavingMissingItem(false);
    setMissingSaveErrorMessage(null);
    setMissingSaveSuccessMessage(null);
    setM01Case(null);
    setCaseDisplayName("");
    setCaseIdNumber("");
    setCaseBirthDate("");
    setCaseGender("");
    setCaseEmploymentStatus("");
    setPlannedRetirementMode("");
    setPlannedRetirementAge("");
    setPlannedRetirementDate("");
    setIsSavingCase(false);
    setCaseSaveMessage(null);
    setCaseErrorMessage(null);
    setIsTransitioningCase(false);

    async function loadClient() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive && isCurrentClientContext(clientContext)) {
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextClient = await getClient(parsedClientId);
        if (!isActive || !isCurrentClientContext(clientContext)) {
          return;
        }
        setLoadedClientContext(clientContext);
        setClient(nextClient);
        if (nextClient.m01_case !== undefined) {
          applyM01Case(nextClient.m01_case);
        }
        setIdNumber(nextClient.id_number ?? "");
        setBirthDate(nextClient.birth_date ?? "");
        setProfessionalIdentificationStatus(nextClient.professional_identification_status);
        setIsNotFound(false);
        setErrorMessage(null);

        try {
          const profileResponse = await getClientProfile(parsedClientId);
          if (!isActive || !isCurrentClientContext(clientContext)) {
            return;
          }
          setIdNumber(profileResponse.profile?.id_number ?? nextClient.id_number ?? "");
          setBirthDate(profileResponse.profile?.birth_date ?? "");
          setGender(profileResponse.profile?.gender ?? "");
          setContactMethod(profileResponse.profile?.contact_method ?? "");
          setContactDetails(profileResponse.profile?.contact_details ?? "");
          setNotes(profileResponse.profile?.notes ?? "");
          setProfessionalIdentificationStatus(
            profileResponse.profile?.professional_identification_status
              ?? nextClient.professional_identification_status
          );
          setProfileExists(profileResponse.profile !== null);
          setProfileLoadErrorMessage(null);
        } catch (profileError) {
          if (!isActive || !isCurrentClientContext(clientContext)) {
            return;
          }
          setProfileLoadErrorMessage(getErrorMessage(profileError));
        }

        try {
          const [nextSnapshots, nextDocuments, nextMissingItems] = await Promise.all([
            getClearinghouseSnapshots(parsedClientId),
            getRetirementPlanningDocuments(parsedClientId),
            getMissingDataItems(parsedClientId)
          ]);
          if (!isActive || !isCurrentClientContext(clientContext)) {
            return;
          }
          setClearinghouseSnapshots(nextSnapshots);
          setRetirementPlanningDocuments(nextDocuments);
          setMissingDataItems(nextMissingItems);
          setCollectionLoadErrorMessage(null);
        } catch (collectionError) {
          if (!isActive || !isCurrentClientContext(clientContext)) {
            return;
          }
          setCollectionLoadErrorMessage(getErrorMessage(collectionError));
        }
      } catch (error) {
        if (!isActive || !isCurrentClientContext(clientContext)) {
          return;
        }
        if (error instanceof ApiTransportError && error.status === 404) {
          setClient(null);
          setIsNotFound(true);
          setErrorMessage(null);
        } else {
          setClient(null);
          setIsNotFound(false);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive && isCurrentClientContext(clientContext)) {
          setIsLoading(false);
        }
      }
    }

    void loadClient();

    return () => {
      isActive = false;
    };
  }, [
    captureClientContext,
    isCurrentClientContext,
    location.key,
    parsedClientId
  ]);

  async function handleSaveCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      client === null
      || m01Case === null
      || m01Case.lifecycle_status === "archived"
    ) {
      return;
    }

    const clientContext = captureClientContext();
    const requestClientId = client.client_id;
    setIsSavingCase(true);
    setCaseSaveMessage(null);
    setCaseErrorMessage(null);

    try {
      const nextCase = await updateClientCase(requestClientId, {
        display_name: caseDisplayName,
        id_number: caseIdNumber,
        birth_date: caseBirthDate || null,
        gender: caseGender || null,
        employment_status: caseEmploymentStatus || null,
        planned_retirement_age:
          plannedRetirementMode === "age" && plannedRetirementAge !== ""
            ? Number(plannedRetirementAge)
            : null,
        planned_retirement_date:
          plannedRetirementMode === "date" && plannedRetirementDate !== ""
            ? plannedRetirementDate
            : null
      });
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      applyM01Case(nextCase);
      setClient((current) =>
        current === null
          ? current
          : {
              ...current,
              full_name: nextCase.display_name,
              id_number: nextCase.id_number,
              birth_date: nextCase.birth_date,
              m01_case: nextCase
            }
      );
      setIdNumber(nextCase.id_number);
      setBirthDate(nextCase.birth_date ?? "");
      setGender(nextCase.gender ?? "");
      setProfileExists(true);
      setCaseSaveMessage("Client case facts saved.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setCaseErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsSavingCase(false);
      }
    }
  }

  async function handleLifecycleTransition(targetStatus: M01LifecycleStatus) {
    if (client === null || m01Case === null) {
      return;
    }

    const clientContext = captureClientContext();
    const requestClientId = client.client_id;
    setIsTransitioningCase(true);
    setCaseSaveMessage(null);
    setCaseErrorMessage(null);

    try {
      const nextCase = await transitionClientCase(requestClientId, targetStatus);
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      applyM01Case(nextCase);
      setClient((current) =>
        current === null ? current : { ...current, m01_case: nextCase }
      );
      setCaseSaveMessage(`Client case moved to ${nextCase.lifecycle_status}.`);
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setCaseErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsTransitioningCase(false);
      }
    }
  }

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null || m01Case?.lifecycle_status === "archived") {
      return;
    }

    const clientContext = captureClientContext();
    setIsSaving(true);
    setSaveErrorMessage(null);
    setSaveSuccessMessage(null);

    try {
      const response = await updateClientProfile(client.client_id, {
        id_number: idNumber || null,
        birth_date: birthDate || null,
        gender: gender || null,
        contact_method: contactMethod || null,
        contact_details: contactDetails || null,
        notes: notes || null
      });
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setIdNumber(response.profile?.id_number ?? "");
      setBirthDate(response.profile?.birth_date ?? "");
      setGender(response.profile?.gender ?? "");
      setContactMethod(response.profile?.contact_method ?? "");
      setContactDetails(response.profile?.contact_details ?? "");
      setNotes(response.profile?.notes ?? "");
      setProfessionalIdentificationStatus(
        response.profile?.professional_identification_status ?? "identification_incomplete"
      );
      if (response.profile?.m01_case !== undefined) {
        applyM01Case(response.profile.m01_case);
        setClient((current) =>
          current === null
            ? current
            : {
                ...current,
                full_name: response.profile?.m01_case?.display_name ?? current.full_name,
                id_number: response.profile?.m01_case?.id_number ?? current.id_number,
                birth_date: response.profile?.m01_case?.birth_date ?? current.birth_date,
                m01_case: response.profile?.m01_case
              }
        );
      }
      setProfileExists(response.profile !== null);
      setSaveSuccessMessage("Profile saved successfully.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setSaveErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsSaving(false);
      }
    }
  }

  async function handleCreateSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

    const clientContext = captureClientContext();
    setIsSavingSnapshot(true);
    setSnapshotSaveErrorMessage(null);
    setSnapshotSaveSuccessMessage(null);

    try {
      const snapshot = await createClearinghouseSnapshot(client.client_id, {
        import_date: snapshotImportDate,
        source_type: snapshotSourceType,
        source_file: snapshotSourceFile,
        collection_status: snapshotCollectionStatus,
        collection_notes: snapshotCollectionNotes || null
      });
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setClearinghouseSnapshots((current) => [snapshot, ...current]);
      setSnapshotVerificationStatusById((current) => ({
        ...current,
        [snapshot.clearinghouse_snapshot_id]: snapshot.verification_status
      }));
      setSnapshotVerificationNotesById((current) => ({
        ...current,
        [snapshot.clearinghouse_snapshot_id]: snapshot.verification_notes ?? ""
      }));
      setSnapshotImportDate("");
      setSnapshotSourceType("");
      setSnapshotSourceFile("");
      setSnapshotCollectionStatus("");
      setSnapshotCollectionNotes("");
      setSnapshotSaveSuccessMessage("Clearinghouse snapshot registered.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setSnapshotSaveErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsSavingSnapshot(false);
      }
    }
  }

  async function handleCreateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

    const clientContext = captureClientContext();
    setIsSavingDocument(true);
    setDocumentSaveErrorMessage(null);
    setDocumentSaveSuccessMessage(null);

    try {
      const document = await createRetirementPlanningDocument(client.client_id, {
        document_type: documentType,
        source_type: documentSourceType || null,
        source_file: documentSourceFile,
        collection_date: documentCollectionDate,
        collection_status: documentCollectionStatus,
        collection_notes: documentCollectionNotes || null
      });
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setRetirementPlanningDocuments((current) => [document, ...current]);
      setDocumentVerificationStatusById((current) => ({
        ...current,
        [document.document_id]: document.verification_status
      }));
      setDocumentVerificationNotesById((current) => ({
        ...current,
        [document.document_id]: document.verification_notes ?? ""
      }));
      setDocumentType("");
      setDocumentSourceType("");
      setDocumentSourceFile("");
      setDocumentCollectionDate("");
      setDocumentCollectionStatus("");
      setDocumentCollectionNotes("");
      setDocumentSaveSuccessMessage("Retirement planning document registered.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setDocumentSaveErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsSavingDocument(false);
      }
    }
  }

  async function handleUpdateSnapshotVerification(snapshot: ClearinghouseSnapshotItem) {
    if (client === null) {
      return;
    }

    const clientContext = captureClientContext();
    setVerificationSaveMessage(null);
    setVerificationErrorMessage(null);

    try {
      const updated = await updateClearinghouseSnapshotVerification(
        client.client_id,
        snapshot.clearinghouse_snapshot_id,
        {
          verification_status: snapshotVerificationStatusById[snapshot.clearinghouse_snapshot_id]
            ?? snapshot.verification_status,
          verification_notes: snapshotVerificationNotesById[snapshot.clearinghouse_snapshot_id] || null
        }
      );
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setClearinghouseSnapshots((current) => current.map((item) => (
        item.clearinghouse_snapshot_id === updated.clearinghouse_snapshot_id ? updated : item
      )));
      setVerificationSaveMessage("Verification status saved.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setVerificationErrorMessage(getErrorMessage(error));
      }
    }
  }

  async function handleUpdateDocumentVerification(document: RetirementPlanningDocumentItem) {
    if (client === null) {
      return;
    }

    const clientContext = captureClientContext();
    setVerificationSaveMessage(null);
    setVerificationErrorMessage(null);

    try {
      const updated = await updateRetirementPlanningDocumentVerification(
        client.client_id,
        document.document_id,
        {
          verification_status: documentVerificationStatusById[document.document_id] ?? document.verification_status,
          verification_notes: documentVerificationNotesById[document.document_id] || null
        }
      );
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setRetirementPlanningDocuments((current) => current.map((item) => (
        item.document_id === updated.document_id ? updated : item
      )));
      setVerificationSaveMessage("Verification status saved.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setVerificationErrorMessage(getErrorMessage(error));
      }
    }
  }

  async function handleCreateMissingItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

    const clientContext = captureClientContext();
    setIsSavingMissingItem(true);
    setMissingSaveErrorMessage(null);
    setMissingSaveSuccessMessage(null);

    try {
      const item = await createMissingDataItem(client.client_id, {
        missing_item_type: missingItemType,
        missing_item_label: missingItemLabel,
        missing_status: missingStatus,
        notes: missingNotes || null
      });
      if (!isCurrentClientContext(clientContext)) {
        return;
      }
      setMissingDataItems((current) => [item, ...current]);
      setMissingItemType("data");
      setMissingItemLabel("");
      setMissingStatus("");
      setMissingNotes("");
      setMissingSaveSuccessMessage("Missing item registered.");
    } catch (error) {
      if (isCurrentClientContext(clientContext)) {
        setMissingSaveErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (isCurrentClientContext(clientContext)) {
        setIsSavingMissingItem(false);
      }
    }
  }

  if (isLoading) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Loading client details...</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Client not found.</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Unable to load client details.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  const clientOwnsActiveRoute =
    client !== null
    && loadedClientContext !== null
    && validRouteClientId !== null
    && client.client_id === validRouteClientId
    && isCurrentClientContext(loadedClientContext);

  if (client === null || !clientOwnsActiveRoute) {
    return (
      <section>
        <h2>Client Detail</h2>
        <p>Client details are unavailable.</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>Client Detail</h2>
      <p>Client ID: {client.client_id}</p>
      <p>Full Name: {client.full_name}</p>
      <p>ID Number: {client.id_number ?? "Not provided"}</p>
      {m01Case !== null ? (
        <section aria-labelledby="m01-case-foundation-heading">
          <h3 id="m01-case-foundation-heading">Client Case Foundation</h3>
          <p>Lifecycle Status: {m01Case.lifecycle_status}</p>
          <p>Completeness Status: {m01Case.completeness.status}</p>
          {m01Case.completeness.missing_field_ids.length > 0 ? (
            <>
              <h4>Missing Minimum Facts</h4>
              <ul>
                {m01Case.completeness.missing_field_ids.map((fieldId) => (
                  <li key={fieldId}>{fieldId}</li>
                ))}
              </ul>
            </>
          ) : (
            <p>No minimum facts are missing.</p>
          )}
          {m01Case.completeness.conflicting_field_ids.length > 0 ? (
            <>
              <h4>Conflicting Minimum Facts</h4>
              <ul>
                {m01Case.completeness.conflicting_field_ids.map((fieldId) => (
                  <li key={fieldId}>{fieldId}</li>
                ))}
              </ul>
            </>
          ) : null}
          {m01Case.lifecycle_status === "archived" ? (
            <p>Archived client cases are read-only until explicitly reopened.</p>
          ) : null}
          <form onSubmit={handleSaveCase}>
            <fieldset disabled={m01Case.lifecycle_status === "archived" || isSavingCase}>
              <legend>Minimum Case Facts</legend>
              <p>
                <label htmlFor="m01-display-name">Name</label>
                <input
                  id="m01-display-name"
                  value={caseDisplayName}
                  onChange={(event) => {
                    setCaseDisplayName(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-id-number">Israeli ID or Client Identifier</label>
                <input
                  id="m01-id-number"
                  value={caseIdNumber}
                  onChange={(event) => {
                    setCaseIdNumber(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-birth-date">Birth Date</label>
                <input
                  id="m01-birth-date"
                  type="date"
                  value={caseBirthDate}
                  onChange={(event) => {
                    setCaseBirthDate(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-gender">Gender</label>
                <input
                  id="m01-gender"
                  value={caseGender}
                  onChange={(event) => {
                    setCaseGender(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-employment-status">Employment Status</label>
                <select
                  id="m01-employment-status"
                  value={caseEmploymentStatus}
                  onChange={(event) => {
                    setCaseEmploymentStatus(event.target.value as M01EmploymentStatus | "");
                    setCaseSaveMessage(null);
                  }}
                >
                  <option value="">Not recorded</option>
                  <option value="salaried_employee">salaried_employee</option>
                  <option value="self_employed">self_employed</option>
                  <option value="salaried_and_self_employed">
                    salaried_and_self_employed
                  </option>
                  <option value="not_currently_working">not_currently_working</option>
                  <option value="unknown">unknown</option>
                </select>
              </p>
              <p>
                <label htmlFor="m01-planned-retirement-mode">Planned Retirement Source</label>
                <select
                  id="m01-planned-retirement-mode"
                  value={plannedRetirementMode}
                  onChange={(event) => {
                    const mode = event.target.value as "age" | "date" | "";
                    setPlannedRetirementMode(mode);
                    if (mode !== "age") {
                      setPlannedRetirementAge("");
                    }
                    if (mode !== "date") {
                      setPlannedRetirementDate("");
                    }
                    setCaseSaveMessage(null);
                  }}
                >
                  <option value="">Not recorded</option>
                  <option value="age">Planned retirement age</option>
                  <option value="date">Planned retirement date</option>
                </select>
              </p>
              {plannedRetirementMode === "age" ? (
                <p>
                  <label htmlFor="m01-planned-retirement-age">Planned Retirement Age</label>
                  <input
                    id="m01-planned-retirement-age"
                    type="number"
                    min="18"
                    max="120"
                    value={plannedRetirementAge}
                    onChange={(event) => {
                      setPlannedRetirementAge(event.target.value);
                      setCaseSaveMessage(null);
                    }}
                  />
                </p>
              ) : null}
              {plannedRetirementMode === "date" ? (
                <p>
                  <label htmlFor="m01-planned-retirement-date">Planned Retirement Date</label>
                  <input
                    id="m01-planned-retirement-date"
                    type="date"
                    value={plannedRetirementDate}
                    onChange={(event) => {
                      setPlannedRetirementDate(event.target.value);
                      setCaseSaveMessage(null);
                    }}
                  />
                </p>
              ) : null}
              <button type="submit">
                {isSavingCase ? "Saving Case Facts..." : "Save Case Facts"}
              </button>
            </fieldset>
          </form>
          <h4>Allowed Lifecycle Transitions</h4>
          {m01Case.allowed_lifecycle_targets.length === 0 ? (
            <p>No lifecycle transition is currently available.</p>
          ) : (
            <ul>
              {m01Case.allowed_lifecycle_targets.map((targetStatus) => (
                <li key={targetStatus}>
                  <button
                    type="button"
                    disabled={isTransitioningCase}
                    onClick={() => {
                      void handleLifecycleTransition(targetStatus);
                    }}
                  >
                    Move to {targetStatus}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {caseSaveMessage ? <p>{caseSaveMessage}</p> : null}
          {caseErrorMessage ? (
            <>
              <p>Unable to update client case.</p>
              <pre>{caseErrorMessage}</pre>
            </>
          ) : null}
          <p>Intake module: Not available in PKG-006.</p>
        </section>
      ) : null}
      <section aria-labelledby="retirement-planning-file-heading">
        <h3 id="retirement-planning-file-heading">Retirement Planning File</h3>
        <p>File Status: {client.file_status}</p>
        <p>Professional Identification: {professionalIdentificationStatus}</p>
      </section>
      {!profileExists && profileLoadErrorMessage === null ? <p>No client profile has been saved yet.</p> : null}
      {profileLoadErrorMessage ? (
        <>
          <p>Unable to load client profile.</p>
          <pre>{profileLoadErrorMessage}</pre>
        </>
      ) : null}
      <form onSubmit={handleSaveProfile}>
        <fieldset disabled={m01Case?.lifecycle_status === "archived" || isSaving}>
          <legend>Client Profile</legend>
          <p>
            <label htmlFor="profile-id-number">ID Number</label>
            <input
              id="profile-id-number"
              value={idNumber}
              onChange={(event) => {
                setIdNumber(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-birth-date">Birth Date</label>
            <input
              id="profile-birth-date"
              type="date"
              value={birthDate}
              onChange={(event) => {
                setBirthDate(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-gender">Gender</label>
            <input
              id="profile-gender"
              value={gender}
              onChange={(event) => {
                setGender(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-contact-method">Contact Method</label>
            <input
              id="profile-contact-method"
              value={contactMethod}
              onChange={(event) => {
                setContactMethod(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-contact-details">Contact Details</label>
            <input
              id="profile-contact-details"
              value={contactDetails}
              onChange={(event) => {
                setContactDetails(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-notes">Notes</label>
            <textarea
              id="profile-notes"
              value={notes}
              onChange={(event) => {
                setNotes(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <button
            type="submit"
            disabled={
              isSaving
              || profileLoadErrorMessage !== null
              || m01Case?.lifecycle_status === "archived"
            }
          >
            {isSaving ? "Saving Profile..." : "Save Profile"}
          </button>
        </fieldset>
      </form>
      {saveSuccessMessage ? <p>{saveSuccessMessage}</p> : null}
      {saveErrorMessage ? (
        <>
          <p>Unable to save profile.</p>
          <pre>{saveErrorMessage}</pre>
        </>
      ) : null}
      <section aria-labelledby="retirement-planning-data-matrix-heading">
        <h3 id="retirement-planning-data-matrix-heading">Retirement Planning Data Matrix</h3>
        <ul>
          <li>
            <RetirementPlanningFactsSection clientId={parsedClientId} />
          </li>
          <li>
            <PensionAnalysisRecordSection clientId={parsedClientId} />
          </li>
          <li>
            <PlannerAssumptionsSection clientId={parsedClientId} />
          </li>
          <li>
            <AdvisoryMissingInformationSection clientId={parsedClientId} />
          </li>
          <li>
            <RetirementPlanningConsolidatedReviewSection clientId={parsedClientId} />
          </li>
          <li>Documents</li>
          <li>Calculated Artifacts</li>
          <li>Workflow Status</li>
        </ul>
      </section>
      <section aria-labelledby="clearinghouse-snapshots-heading">
        <h3 id="clearinghouse-snapshots-heading">Clearinghouse Snapshots</h3>
        {collectionLoadErrorMessage ? (
          <>
            <p>Unable to load collection metadata.</p>
            <pre>{collectionLoadErrorMessage}</pre>
          </>
        ) : null}
        <form onSubmit={handleCreateSnapshot}>
          <p>
            <label htmlFor="snapshot-import-date">Snapshot Import Date</label>
            <input
              id="snapshot-import-date"
              type="date"
              value={snapshotImportDate}
              onChange={(event) => {
                setSnapshotImportDate(event.target.value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="snapshot-source-type">Snapshot Source Type</label>
            <input
              id="snapshot-source-type"
              value={snapshotSourceType}
              onChange={(event) => {
                setSnapshotSourceType(event.target.value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="snapshot-source-file">Snapshot Source File</label>
            <input
              id="snapshot-source-file"
              value={snapshotSourceFile}
              onChange={(event) => {
                setSnapshotSourceFile(event.target.value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="snapshot-collection-status">Snapshot Collection Status</label>
            <input
              id="snapshot-collection-status"
              value={snapshotCollectionStatus}
              onChange={(event) => {
                setSnapshotCollectionStatus(event.target.value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="snapshot-collection-notes">Snapshot Collection Notes</label>
            <textarea
              id="snapshot-collection-notes"
              value={snapshotCollectionNotes}
              onChange={(event) => {
                setSnapshotCollectionNotes(event.target.value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <button type="submit" disabled={isSavingSnapshot || collectionLoadErrorMessage !== null}>
            {isSavingSnapshot ? "Registering Snapshot..." : "Register Snapshot"}
          </button>
        </form>
        {snapshotSaveSuccessMessage ? <p>{snapshotSaveSuccessMessage}</p> : null}
        {snapshotSaveErrorMessage ? (
          <>
            <p>Unable to register clearinghouse snapshot.</p>
            <pre>{snapshotSaveErrorMessage}</pre>
          </>
        ) : null}
        {clearinghouseSnapshots.length === 0 ? (
          <p>No clearinghouse snapshots registered.</p>
        ) : (
          <ul>
            {clearinghouseSnapshots.map((snapshot) => (
              <li key={snapshot.clearinghouse_snapshot_id}>
                {snapshot.import_date} - {snapshot.source_type} - {snapshot.source_file} -{" "}
                {snapshot.collection_status}
                {snapshot.collection_notes ? ` - ${snapshot.collection_notes}` : ""}
                <p>Verification Status: {snapshot.verification_status}</p>
                <p>
                  <label htmlFor={`snapshot-verification-status-${snapshot.clearinghouse_snapshot_id}`}>
                    Snapshot Verification Status
                  </label>
                  <input
                    id={`snapshot-verification-status-${snapshot.clearinghouse_snapshot_id}`}
                    value={snapshotVerificationStatusById[snapshot.clearinghouse_snapshot_id]
                      ?? snapshot.verification_status}
                    onChange={(event) => {
                      setSnapshotVerificationStatusById((current) => ({
                        ...current,
                        [snapshot.clearinghouse_snapshot_id]: event.target.value
                      }));
                      setVerificationSaveMessage(null);
                    }}
                  />
                </p>
                <p>
                  <label htmlFor={`snapshot-verification-notes-${snapshot.clearinghouse_snapshot_id}`}>
                    Snapshot Verification Notes
                  </label>
                  <textarea
                    id={`snapshot-verification-notes-${snapshot.clearinghouse_snapshot_id}`}
                    value={snapshotVerificationNotesById[snapshot.clearinghouse_snapshot_id]
                      ?? snapshot.verification_notes
                      ?? ""}
                    onChange={(event) => {
                      setSnapshotVerificationNotesById((current) => ({
                        ...current,
                        [snapshot.clearinghouse_snapshot_id]: event.target.value
                      }));
                      setVerificationSaveMessage(null);
                    }}
                  />
                </p>
                <button
                  type="button"
                  onClick={() => {
                    void handleUpdateSnapshotVerification(snapshot);
                  }}
                >
                  Save Snapshot Verification
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="retirement-documents-heading">
        <h3 id="retirement-documents-heading">Retirement Planning Documents</h3>
        <form onSubmit={handleCreateDocument}>
          <p>
            <label htmlFor="document-type">Document Type</label>
            <input
              id="document-type"
              value={documentType}
              onChange={(event) => {
                setDocumentType(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-source-type">Document Source Type</label>
            <input
              id="document-source-type"
              value={documentSourceType}
              onChange={(event) => {
                setDocumentSourceType(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-source-file">Document Source File</label>
            <input
              id="document-source-file"
              value={documentSourceFile}
              onChange={(event) => {
                setDocumentSourceFile(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-collection-date">Document Collection Date</label>
            <input
              id="document-collection-date"
              type="date"
              value={documentCollectionDate}
              onChange={(event) => {
                setDocumentCollectionDate(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-collection-status">Document Collection Status</label>
            <input
              id="document-collection-status"
              value={documentCollectionStatus}
              onChange={(event) => {
                setDocumentCollectionStatus(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-collection-notes">Document Collection Notes</label>
            <textarea
              id="document-collection-notes"
              value={documentCollectionNotes}
              onChange={(event) => {
                setDocumentCollectionNotes(event.target.value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <button type="submit" disabled={isSavingDocument || collectionLoadErrorMessage !== null}>
            {isSavingDocument ? "Registering Document..." : "Register Document"}
          </button>
        </form>
        {documentSaveSuccessMessage ? <p>{documentSaveSuccessMessage}</p> : null}
        {documentSaveErrorMessage ? (
          <>
            <p>Unable to register retirement planning document.</p>
            <pre>{documentSaveErrorMessage}</pre>
          </>
        ) : null}
        {retirementPlanningDocuments.length === 0 ? (
          <p>No retirement planning documents registered.</p>
        ) : (
          <ul>
            {retirementPlanningDocuments.map((document) => (
              <li key={document.document_id}>
                {document.collection_date} - {document.document_type} - {document.source_file} -{" "}
                {document.collection_status}
                {document.collection_notes ? ` - ${document.collection_notes}` : ""}
                <p>Verification Status: {document.verification_status}</p>
                <p>
                  <label htmlFor={`document-verification-status-${document.document_id}`}>
                    Document Verification Status
                  </label>
                  <input
                    id={`document-verification-status-${document.document_id}`}
                    value={documentVerificationStatusById[document.document_id] ?? document.verification_status}
                    onChange={(event) => {
                      setDocumentVerificationStatusById((current) => ({
                        ...current,
                        [document.document_id]: event.target.value
                      }));
                      setVerificationSaveMessage(null);
                    }}
                  />
                </p>
                <p>
                  <label htmlFor={`document-verification-notes-${document.document_id}`}>
                    Document Verification Notes
                  </label>
                  <textarea
                    id={`document-verification-notes-${document.document_id}`}
                    value={documentVerificationNotesById[document.document_id] ?? document.verification_notes ?? ""}
                    onChange={(event) => {
                      setDocumentVerificationNotesById((current) => ({
                        ...current,
                        [document.document_id]: event.target.value
                      }));
                      setVerificationSaveMessage(null);
                    }}
                  />
                </p>
                <button
                  type="button"
                  onClick={() => {
                    void handleUpdateDocumentVerification(document);
                  }}
                >
                  Save Document Verification
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      {verificationSaveMessage ? <p>{verificationSaveMessage}</p> : null}
      {verificationErrorMessage ? (
        <>
          <p>Unable to save verification status.</p>
          <pre>{verificationErrorMessage}</pre>
        </>
      ) : null}
      <section aria-labelledby="missing-data-heading">
        <h3 id="missing-data-heading">Missing Data Tracking</h3>
        <form onSubmit={handleCreateMissingItem}>
          <p>
            <label htmlFor="missing-item-type">Missing Item Type</label>
            <select
              id="missing-item-type"
              value={missingItemType}
              onChange={(event) => {
                setMissingItemType(event.target.value);
                setMissingSaveSuccessMessage(null);
              }}
            >
              <option value="data">data</option>
              <option value="document">document</option>
            </select>
          </p>
          <p>
            <label htmlFor="missing-item-label">Missing Item Label</label>
            <input
              id="missing-item-label"
              value={missingItemLabel}
              onChange={(event) => {
                setMissingItemLabel(event.target.value);
                setMissingSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="missing-status">Missing Status</label>
            <input
              id="missing-status"
              value={missingStatus}
              onChange={(event) => {
                setMissingStatus(event.target.value);
                setMissingSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="missing-notes">Missing Notes</label>
            <textarea
              id="missing-notes"
              value={missingNotes}
              onChange={(event) => {
                setMissingNotes(event.target.value);
                setMissingSaveSuccessMessage(null);
              }}
            />
          </p>
          <button type="submit" disabled={isSavingMissingItem || collectionLoadErrorMessage !== null}>
            {isSavingMissingItem ? "Registering Missing Item..." : "Register Missing Item"}
          </button>
        </form>
        {missingSaveSuccessMessage ? <p>{missingSaveSuccessMessage}</p> : null}
        {missingSaveErrorMessage ? (
          <>
            <p>Unable to register missing item.</p>
            <pre>{missingSaveErrorMessage}</pre>
          </>
        ) : null}
        {missingDataItems.length === 0 ? (
          <p>No missing items registered.</p>
        ) : (
          <ul>
            {missingDataItems.map((item) => (
              <li key={item.missing_data_item_id}>
                {item.missing_item_type} - {item.missing_item_label} - {item.missing_status}
                {item.notes ? ` - ${item.notes}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/fixation/workspace`}
          state={{ clientName: client.full_name }}
        >
          Fixation Activity Workspace
        </Link>
      </p>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/employment-history`}
          state={{ clientName: client.full_name }}
        >
          Employment History
        </Link>
      </p>
      <p>
        <Link to="/clients">Back to client list</Link>
      </p>
    </section>
  );
}
