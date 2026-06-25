import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type ClearinghouseSnapshotItem,
  type ClientDetailItem,
  createClearinghouseSnapshot,
  createRetirementPlanningDocument,
  getClient,
  getClientProfile,
  getClearinghouseSnapshots,
  getRetirementPlanningDocuments,
  type RetirementPlanningDocumentItem,
  updateClientProfile
} from "../api/clientsApi";

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
  const parsedClientId = Number(clientId);
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

  useEffect(() => {
    let isActive = true;

    async function loadClient() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setIsNotFound(true);
          setErrorMessage(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const nextClient = await getClient(parsedClientId);
        if (!isActive) {
          return;
        }
        setClient(nextClient);
        setIdNumber(nextClient.id_number ?? "");
        setBirthDate(nextClient.birth_date ?? "");
        setProfessionalIdentificationStatus(nextClient.professional_identification_status);
        setIsNotFound(false);
        setErrorMessage(null);

        try {
          const profileResponse = await getClientProfile(parsedClientId);
          if (!isActive) {
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
          if (!isActive) {
            return;
          }
          setProfileLoadErrorMessage(getErrorMessage(profileError));
        }

        try {
          const [nextSnapshots, nextDocuments] = await Promise.all([
            getClearinghouseSnapshots(parsedClientId),
            getRetirementPlanningDocuments(parsedClientId)
          ]);
          if (!isActive) {
            return;
          }
          setClearinghouseSnapshots(nextSnapshots);
          setRetirementPlanningDocuments(nextDocuments);
          setCollectionLoadErrorMessage(null);
        } catch (collectionError) {
          if (!isActive) {
            return;
          }
          setCollectionLoadErrorMessage(getErrorMessage(collectionError));
        }
      } catch (error) {
        if (!isActive) {
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
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadClient();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

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
      setIdNumber(response.profile?.id_number ?? "");
      setBirthDate(response.profile?.birth_date ?? "");
      setGender(response.profile?.gender ?? "");
      setContactMethod(response.profile?.contact_method ?? "");
      setContactDetails(response.profile?.contact_details ?? "");
      setNotes(response.profile?.notes ?? "");
      setProfessionalIdentificationStatus(
        response.profile?.professional_identification_status ?? "identification_incomplete"
      );
      setProfileExists(response.profile !== null);
      setSaveSuccessMessage("Profile saved successfully.");
    } catch (error) {
      setSaveErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

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
      setClearinghouseSnapshots((current) => [snapshot, ...current]);
      setSnapshotImportDate("");
      setSnapshotSourceType("");
      setSnapshotSourceFile("");
      setSnapshotCollectionStatus("");
      setSnapshotCollectionNotes("");
      setSnapshotSaveSuccessMessage("Clearinghouse snapshot registered.");
    } catch (error) {
      setSnapshotSaveErrorMessage(getErrorMessage(error));
    } finally {
      setIsSavingSnapshot(false);
    }
  }

  async function handleCreateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (client === null) {
      return;
    }

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
      setRetirementPlanningDocuments((current) => [document, ...current]);
      setDocumentType("");
      setDocumentSourceType("");
      setDocumentSourceFile("");
      setDocumentCollectionDate("");
      setDocumentCollectionStatus("");
      setDocumentCollectionNotes("");
      setDocumentSaveSuccessMessage("Retirement planning document registered.");
    } catch (error) {
      setDocumentSaveErrorMessage(getErrorMessage(error));
    } finally {
      setIsSavingDocument(false);
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

  if (client === null) {
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
        <button type="submit" disabled={isSaving || profileLoadErrorMessage !== null}>
          {isSaving ? "Saving Profile..." : "Save Profile"}
        </button>
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
          <li>Retirement Planning Facts</li>
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
              </li>
            ))}
          </ul>
        )}
      </section>
      <p>
        <Link
          to={`/clients/${client.client_id}/employment-history`}
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
