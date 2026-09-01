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
import { HebrewDateInput } from "../components/HebrewDateInput";
import { heLabel } from "../i18n/he";
import { formatIsoDate } from "../utils/dateFormat";
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

  return "לא ניתן לטעון את פרטי הלקוח.";
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
      setCaseSaveMessage("נתוני תיק הלקוח נשמרו.");
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
      setCaseSaveMessage(`תיק הלקוח עבר למצב ${heLabel(nextCase.lifecycle_status)}.`);
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
      setSaveSuccessMessage("הפרופיל נשמר בהצלחה.");
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
      setSnapshotSaveSuccessMessage("תמונת המצב מהמסלקה נרשמה.");
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
      setDocumentSaveSuccessMessage("מסמך תכנון הפרישה נרשם.");
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
      setVerificationSaveMessage("מצב האימות נשמר.");
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
      setVerificationSaveMessage("מצב האימות נשמר.");
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
      setMissingSaveSuccessMessage("הפריט החסר נרשם.");
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
        <h2>פרטי לקוח — M01</h2>
        <p>טוען את פרטי הלקוח...</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
        </p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>פרטי לקוח — M01</h2>
        <p>הלקוח לא נמצא.</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
        </p>
      </section>
    );
  }

  if (errorMessage !== null) {
    return (
      <section>
        <h2>פרטי לקוח — M01</h2>
        <p>לא ניתן לטעון את פרטי הלקוח.</p>
        <p>{errorMessage}</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
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
        <h2>פרטי לקוח — M01</h2>
        <p>פרטי הלקוח אינם זמינים.</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2>פרטי לקוח — M01</h2>
      <p>מזהה לקוח: {client.client_id}</p>
      <p>שם מלא: {client.full_name}</p>
      <p>מספר זהות: {client.id_number ?? "לא נמסר"}</p>
      {m01Case !== null ? (
        <section aria-labelledby="m01-case-foundation-heading">
          <h3 id="m01-case-foundation-heading">תשתית תיק הלקוח</h3>
          <p>מצב נוכחי: {heLabel(m01Case.lifecycle_status)}</p>
          <p>שלמות נתונים: {heLabel(m01Case.completeness.status)}</p>
          {m01Case.completeness.missing_field_ids.length > 0 ? (
            <>
              <h4>נתוני חובה חסרים</h4>
              <ul>
                {m01Case.completeness.missing_field_ids.map((fieldId) => (
                  <li key={fieldId}>{fieldId}</li>
                ))}
              </ul>
            </>
          ) : (
            <p>כל נתוני החובה קיימים.</p>
          )}
          {m01Case.completeness.conflicting_field_ids.length > 0 ? (
            <>
              <h4>נתוני חובה סותרים</h4>
              <ul>
                {m01Case.completeness.conflicting_field_ids.map((fieldId) => (
                  <li key={fieldId}>{fieldId}</li>
                ))}
              </ul>
            </>
          ) : null}
          {m01Case.lifecycle_status === "archived" ? (
            <p>תיק בארכיון הוא לקריאה בלבד עד לפתיחה מפורשת מחדש.</p>
          ) : null}
          <form onSubmit={handleSaveCase}>
            <fieldset disabled={m01Case.lifecycle_status === "archived" || isSavingCase}>
              <legend>נתוני יסוד של התיק</legend>
              <p>
                <label htmlFor="m01-display-name">שם</label>
                <input
                  id="m01-display-name"
                  aria-label="שם"
                  value={caseDisplayName}
                  onChange={(event) => {
                    setCaseDisplayName(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-id-number">מספר זהות ישראלי או מזהה לקוח</label>
                <input
                  id="m01-id-number"
                  aria-label="מספר זהות ישראלי או מזהה לקוח"
                  value={caseIdNumber}
                  onChange={(event) => {
                    setCaseIdNumber(event.target.value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-birth-date">תאריך לידה</label>
                <HebrewDateInput
                  id="m01-birth-date"
                  value={caseBirthDate}
                  onChange={(value) => {
                    setCaseBirthDate(value);
                    setCaseSaveMessage(null);
                  }}
                />
              </p>
              <p>
                <label htmlFor="m01-gender">מגדר</label>
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
                <label htmlFor="m01-employment-status">מצב תעסוקה</label>
                <select
                  id="m01-employment-status"
                  aria-label="מצב תעסוקה"
                  value={caseEmploymentStatus}
                  onChange={(event) => {
                    setCaseEmploymentStatus(event.target.value as M01EmploymentStatus | "");
                    setCaseSaveMessage(null);
                  }}
                >
                  <option value="">לא תועד</option>
                  <option value="salaried_employee">שכיר/ה</option>
                  <option value="self_employed">עצמאי/ת</option>
                  <option value="salaried_and_self_employed">
                    שכיר/ה ועצמאי/ת
                  </option>
                  <option value="not_currently_working">אינו/ה עובד/ת כעת</option>
                  <option value="unknown">לא ידוע</option>
                </select>
              </p>
              <p>
                <label htmlFor="m01-planned-retirement-mode">אופן תכנון מועד הפרישה</label>
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
                  <option value="">לא תועד</option>
                  <option value="age">גיל פרישה מתוכנן</option>
                  <option value="date">תאריך פרישה מתוכנן</option>
                </select>
              </p>
              {plannedRetirementMode === "age" ? (
                <p>
                  <label htmlFor="m01-planned-retirement-age">גיל פרישה מתוכנן</label>
                  <input
                    id="m01-planned-retirement-age"
                    aria-label="גיל פרישה מתוכנן"
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
                  <label htmlFor="m01-planned-retirement-date">תאריך פרישה מתוכנן</label>
                  <HebrewDateInput
                    id="m01-planned-retirement-date"
                    value={plannedRetirementDate}
                    onChange={(value) => {
                      setPlannedRetirementDate(value);
                      setCaseSaveMessage(null);
                    }}
                  />
                </p>
              ) : null}
              <button type="submit" aria-label={isSavingCase ? "שומר נתוני תיק..." : "שמירת נתוני התיק"}>
                {isSavingCase ? "שומר נתוני תיק..." : "שמירת נתוני התיק"}
              </button>
            </fieldset>
          </form>
          <h4>הפעולה הבאה הזמינה</h4>
          {m01Case.allowed_lifecycle_targets.length === 0 ? (
            <p>אין כרגע מעבר מצב זמין.</p>
          ) : (
            <ul>
              {m01Case.allowed_lifecycle_targets.map((targetStatus) => (
                <li key={targetStatus}>
                  <button
                    type="button"
                    aria-label={`מעבר למצב ${heLabel(targetStatus)}`}
                    disabled={isTransitioningCase}
                    onClick={() => {
                      void handleLifecycleTransition(targetStatus);
                    }}
                  >
                    מעבר למצב {heLabel(targetStatus)}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {caseSaveMessage ? <p>{caseSaveMessage}</p> : null}
          {caseErrorMessage ? (
            <>
              <p>לא ניתן לעדכן את תיק הלקוח.</p>
              <pre>{caseErrorMessage}</pre>
            </>
          ) : null}
          <p>המשך התהליך: קליטת נתוני פנסיה ב־M02.</p>
        </section>
      ) : null}
      <section aria-labelledby="retirement-planning-file-heading">
        <h3 id="retirement-planning-file-heading">תיק תכנון הפרישה</h3>
        <p>מצב תיק: {heLabel(client.file_status)}</p>
        <p>זיהוי מקצועי: {heLabel(professionalIdentificationStatus)}</p>
      </section>
      {!profileExists && profileLoadErrorMessage === null ? <p>טרם נשמר פרופיל לקוח.</p> : null}
      {profileLoadErrorMessage ? (
        <>
          <p>לא ניתן לטעון את פרופיל הלקוח.</p>
          <pre>{profileLoadErrorMessage}</pre>
        </>
      ) : null}
      <form onSubmit={handleSaveProfile}>
        <fieldset disabled={m01Case?.lifecycle_status === "archived" || isSaving}>
          <legend>פרופיל לקוח</legend>
          <p>
            <label htmlFor="profile-id-number">מספר זהות</label>
            <input
              id="profile-id-number"
              aria-label="מספר זהות"
              value={idNumber}
              onChange={(event) => {
                setIdNumber(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-birth-date">תאריך לידה</label>
            <HebrewDateInput
              id="profile-birth-date"
              ariaLabel="תאריך לידה"
              value={birthDate}
              onChange={(value) => {
                setBirthDate(value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-gender">מגדר</label>
            <input
              id="profile-gender"
              aria-label="מגדר"
              value={gender}
              onChange={(event) => {
                setGender(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-contact-method">אמצעי קשר</label>
            <input
              id="profile-contact-method"
              aria-label="אמצעי קשר"
              value={contactMethod}
              onChange={(event) => {
                setContactMethod(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-contact-details">פרטי קשר</label>
            <input
              id="profile-contact-details"
              aria-label="פרטי קשר"
              value={contactDetails}
              onChange={(event) => {
                setContactDetails(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="profile-notes">הערות</label>
            <textarea
              id="profile-notes"
              aria-label="הערות"
              value={notes}
              onChange={(event) => {
                setNotes(event.target.value);
                setSaveSuccessMessage(null);
              }}
            />
          </p>
          <button aria-label={isSaving ? "שומר פרופיל..." : "שמירת פרופיל"}
            type="submit"
            disabled={
              isSaving
              || profileLoadErrorMessage !== null
              || m01Case?.lifecycle_status === "archived"
            }
          >
            {isSaving ? "שומר פרופיל..." : "שמירת פרופיל"}
          </button>
        </fieldset>
      </form>
      {saveSuccessMessage ? <p>{saveSuccessMessage}</p> : null}
      {saveErrorMessage ? (
        <>
          <p>לא ניתן לשמור את הפרופיל.</p>
          <pre>{saveErrorMessage}</pre>
        </>
      ) : null}
      <section aria-labelledby="retirement-planning-data-matrix-heading">
        <h3 id="retirement-planning-data-matrix-heading">מפת נתוני תכנון הפרישה</h3>
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
          <li>מסמכים</li>
          <li>תוצרים מחושבים</li>
          <li>מצב תהליך העבודה</li>
        </ul>
      </section>
      <section aria-labelledby="clearinghouse-snapshots-heading">
        <h3 id="clearinghouse-snapshots-heading">תמונות מצב מהמסלקה</h3>
        {collectionLoadErrorMessage ? (
          <>
            <p>לא ניתן לטעון את נתוני האיסוף.</p>
            <pre>{collectionLoadErrorMessage}</pre>
          </>
        ) : null}
        <form onSubmit={handleCreateSnapshot}>
          <p>
            <label htmlFor="snapshot-import-date">תאריך קליטת תמונת המצב</label>
            <HebrewDateInput
              id="snapshot-import-date"
              ariaLabel="תאריך קליטת תמונת המצב"
              value={snapshotImportDate}
              onChange={(value) => {
                setSnapshotImportDate(value);
                setSnapshotSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="snapshot-source-type">סוג מקור של תמונת המצב</label>
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
            <label htmlFor="snapshot-source-file">קובץ המקור של תמונת המצב</label>
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
            <label htmlFor="snapshot-collection-status">מצב איסוף תמונת המצב</label>
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
            <label htmlFor="snapshot-collection-notes">הערות לאיסוף תמונת המצב</label>
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
            {isSavingSnapshot ? "רושם תמונת מצב..." : "רישום תמונת מצב"}
          </button>
        </form>
        {snapshotSaveSuccessMessage ? <p>{snapshotSaveSuccessMessage}</p> : null}
        {snapshotSaveErrorMessage ? (
          <>
            <p>לא ניתן לרשום את תמונת המצב מהמסלקה.</p>
            <pre>{snapshotSaveErrorMessage}</pre>
          </>
        ) : null}
        {clearinghouseSnapshots.length === 0 ? (
          <p>לא נרשמו תמונות מצב מהמסלקה.</p>
        ) : (
          <ul>
            {clearinghouseSnapshots.map((snapshot) => (
              <li key={snapshot.clearinghouse_snapshot_id}>
                {formatIsoDate(snapshot.import_date)} - {snapshot.source_type} - {snapshot.source_file} -{" "}
                {heLabel(snapshot.collection_status)}
                {snapshot.collection_notes ? ` - ${snapshot.collection_notes}` : ""}
                <p>מצב אימות: {heLabel(snapshot.verification_status)}</p>
                <p>
                  <label htmlFor={`snapshot-verification-status-${snapshot.clearinghouse_snapshot_id}`}>
                    מצב אימות תמונת המצב
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
                    הערות אימות לתמונת המצב
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
                  שמירת אימות תמונת המצב
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="retirement-documents-heading">
        <h3 id="retirement-documents-heading">מסמכי תכנון פרישה</h3>
        <form onSubmit={handleCreateDocument}>
          <p>
            <label htmlFor="document-type">סוג מסמך</label>
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
            <label htmlFor="document-source-type">סוג מקור המסמך</label>
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
            <label htmlFor="document-source-file">קובץ מקור המסמך</label>
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
            <label htmlFor="document-collection-date">תאריך איסוף המסמך</label>
            <HebrewDateInput
              id="document-collection-date"
              ariaLabel="תאריך איסוף המסמך"
              value={documentCollectionDate}
              onChange={(value) => {
                setDocumentCollectionDate(value);
                setDocumentSaveSuccessMessage(null);
              }}
            />
          </p>
          <p>
            <label htmlFor="document-collection-status">מצב איסוף המסמך</label>
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
            <label htmlFor="document-collection-notes">הערות לאיסוף המסמך</label>
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
            {isSavingDocument ? "רושם מסמך..." : "רישום מסמך"}
          </button>
        </form>
        {documentSaveSuccessMessage ? <p>{documentSaveSuccessMessage}</p> : null}
        {documentSaveErrorMessage ? (
          <>
            <p>לא ניתן לרשום את מסמך תכנון הפרישה.</p>
            <pre>{documentSaveErrorMessage}</pre>
          </>
        ) : null}
        {retirementPlanningDocuments.length === 0 ? (
          <p>לא נרשמו מסמכי תכנון פרישה.</p>
        ) : (
          <ul>
            {retirementPlanningDocuments.map((document) => (
              <li key={document.document_id}>
                {formatIsoDate(document.collection_date)} - {document.document_type} - {document.source_file} -{" "}
                {heLabel(document.collection_status)}
                {document.collection_notes ? ` - ${document.collection_notes}` : ""}
                <p>מצב אימות: {heLabel(document.verification_status)}</p>
                <p>
                  <label htmlFor={`document-verification-status-${document.document_id}`}>
                    מצב אימות המסמך
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
                    הערות אימות למסמך
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
                  שמירת אימות המסמך
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      {verificationSaveMessage ? <p>{verificationSaveMessage}</p> : null}
      {verificationErrorMessage ? (
        <>
          <p>לא ניתן לשמור את מצב האימות.</p>
          <pre>{verificationErrorMessage}</pre>
        </>
      ) : null}
      <section aria-labelledby="missing-data-heading">
        <h3 id="missing-data-heading">מעקב אחר מידע חסר</h3>
        <form onSubmit={handleCreateMissingItem}>
          <p>
            <label htmlFor="missing-item-type">סוג פריט חסר</label>
            <select
              id="missing-item-type"
              value={missingItemType}
              onChange={(event) => {
                setMissingItemType(event.target.value);
                setMissingSaveSuccessMessage(null);
              }}
            >
              <option value="data">נתון</option>
              <option value="document">מסמך</option>
            </select>
          </p>
          <p>
            <label htmlFor="missing-item-label">תיאור הפריט החסר</label>
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
            <label htmlFor="missing-status">מצב הפריט החסר</label>
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
            <label htmlFor="missing-notes">הערות לפריט החסר</label>
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
            {isSavingMissingItem ? "רושם פריט חסר..." : "רישום פריט חסר"}
          </button>
        </form>
        {missingSaveSuccessMessage ? <p>{missingSaveSuccessMessage}</p> : null}
        {missingSaveErrorMessage ? (
          <>
            <p>לא ניתן לרשום את הפריט החסר.</p>
            <pre>{missingSaveErrorMessage}</pre>
          </>
        ) : null}
        {missingDataItems.length === 0 ? (
          <p>לא נרשמו פריטים חסרים.</p>
        ) : (
          <ul>
            {missingDataItems.map((item) => (
              <li key={item.missing_data_item_id}>
                {heLabel(item.missing_item_type)} - {item.missing_item_label} - {heLabel(item.missing_status)}
                {item.notes ? ` - ${item.notes}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/pension-intake`}
          state={{ clientName: client.full_name }}
        >
          M02 — קליטת נתוני פנסיה
        </Link>
      </p>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/pension-ledger`}
          state={{ clientName: client.full_name }}
        >
          M05 — כרטסת יתרות פנסיה
        </Link>
        <Link
          className="button-link"
          to={`/clients/${validRouteClientId}/pension-conversion`}
        >
          M06 — המרת פנסיה והון
        </Link>
        <Link
          className="button-link"
          to={`/clients/${validRouteClientId}/monthly-cashflow`}
          state={{ clientName: client.full_name }}
        >
          M09 — תזרים מזומנים חודשי
        </Link>
        <Link
          className="button-link"
          to={`/clients/${validRouteClientId}/scenario-comparison`}
          state={{ clientName: client.full_name }}
        >
          M10 — השוואת תרחישים
        </Link>
      </p>
      <details>
        <summary>כלי אבחון וסיווג חריג</summary>
        <p><Link to={`/clients/${validRouteClientId}/source-review`} state={{ clientName: client.full_name }}>M03 — מקור והיסטוריית ביקורת</Link></p>
        <p><Link to={`/clients/${validRouteClientId}/classification`} state={{ clientName: client.full_name }}>M04 — סיווג מקצועי</Link></p>
      </details>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/fixation/workspace`}
          state={{ clientName: client.full_name }}
        >
          סביבת עבודה לקיבוע זכויות
        </Link>
      </p>
      <p>
        <Link
          to={`/clients/${validRouteClientId}/employment-history`}
          state={{ clientName: client.full_name }}
        >
          היסטוריית תעסוקה
        </Link>
      </p>
      <p>
        <Link to="/clients">חזרה לרשימת הלקוחות</Link>
      </p>
    </section>
  );
}
