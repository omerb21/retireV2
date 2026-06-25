import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiTransportError,
  type ActualCapitalizationItem,
  type ClearinghouseSnapshotItem,
  type ClientDetailItem,
  type ClientProfileItem,
  type EmploymentRecordItem,
  type GrantItem,
  type MissingDataItem,
  type RetirementPlanningDocumentItem,
  getActualCapitalizations,
  getClearinghouseSnapshots,
  getClient,
  getClientProfile,
  getEmploymentRecords,
  getGrants,
  getMissingDataItems,
  getRetirementPlanningDocuments
} from "../api/clientsApi";
import { type FixationHistoryEntry, getFixationHistory } from "../api/fixationApi";

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

  return "Unable to load fixation workspace.";
}

function countByStatus<T>(items: T[], selectStatus: (item: T) => string): string {
  if (items.length === 0) {
    return "none";
  }

  const counts = items.reduce<Record<string, number>>((current, item) => {
    const status = selectStatus(item);
    return {
      ...current,
      [status]: (current[status] ?? 0) + 1
    };
  }, {});

  return Object.entries(counts)
    .map(([status, count]) => `${status}: ${count}`)
    .join(", ");
}

function latestRun(history: FixationHistoryEntry[]): FixationHistoryEntry | null {
  return history[0] ?? null;
}

export function FixationWorkspaceScreen() {
  const { clientId } = useParams<{ clientId: string }>();
  const parsedClientId = Number(clientId);

  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [profile, setProfile] = useState<ClientProfileItem | null>(null);
  const [employmentRecords, setEmploymentRecords] = useState<EmploymentRecordItem[]>([]);
  const [grants, setGrants] = useState<GrantItem[]>([]);
  const [actualCapitalizations, setActualCapitalizations] = useState<ActualCapitalizationItem[]>([]);
  const [fixationHistory, setFixationHistory] = useState<FixationHistoryEntry[]>([]);
  const [clearinghouseSnapshots, setClearinghouseSnapshots] = useState<ClearinghouseSnapshotItem[]>([]);
  const [retirementPlanningDocuments, setRetirementPlanningDocuments] = useState<RetirementPlanningDocumentItem[]>([]);
  const [missingDataItems, setMissingDataItems] = useState<MissingDataItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNotFound, setIsNotFound] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadWorkspace() {
      if (!Number.isInteger(parsedClientId) || parsedClientId <= 0) {
        if (isActive) {
          setIsNotFound(true);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const [
          nextClient,
          profileResponse,
          nextEmploymentRecords,
          nextGrants,
          nextActualCapitalizations,
          nextFixationHistory,
          nextClearinghouseSnapshots,
          nextRetirementPlanningDocuments,
          nextMissingDataItems
        ] = await Promise.all([
          getClient(parsedClientId),
          getClientProfile(parsedClientId),
          getEmploymentRecords(parsedClientId),
          getGrants(parsedClientId),
          getActualCapitalizations(parsedClientId),
          getFixationHistory(parsedClientId),
          getClearinghouseSnapshots(parsedClientId),
          getRetirementPlanningDocuments(parsedClientId),
          getMissingDataItems(parsedClientId)
        ]);

        if (!isActive) {
          return;
        }

        setClient(nextClient);
        setProfile(profileResponse.profile);
        setEmploymentRecords(nextEmploymentRecords);
        setGrants(nextGrants);
        setActualCapitalizations(nextActualCapitalizations);
        setFixationHistory(nextFixationHistory);
        setClearinghouseSnapshots(nextClearinghouseSnapshots);
        setRetirementPlanningDocuments(nextRetirementPlanningDocuments);
        setMissingDataItems(nextMissingDataItems);
        setIsNotFound(false);
      } catch (error) {
        if (!isActive) {
          return;
        }

        if (error instanceof ApiTransportError && error.status === 404) {
          setIsNotFound(true);
          setClient(null);
        } else {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    void loadWorkspace();

    return () => {
      isActive = false;
    };
  }, [parsedClientId]);

  const latestFixationRun = useMemo(() => latestRun(fixationHistory), [fixationHistory]);

  if (isLoading) {
    return (
      <section>
        <h2>Fixation Activity Workspace</h2>
        <p>Loading fixation activity workspace...</p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>Fixation Activity Workspace</h2>
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
        <h2>Fixation Activity Workspace</h2>
        <p>Unable to load fixation activity workspace.</p>
        <pre>{errorMessage}</pre>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  if (client === null) {
    return (
      <section>
        <h2>Fixation Activity Workspace</h2>
        <p>Fixation activity workspace is unavailable.</p>
        <p>
          <Link to="/clients">Back to client list</Link>
        </p>
      </section>
    );
  }

  const clientState = { clientName: client.full_name };

  return (
    <section>
      <h2>Fixation Activity Workspace</h2>
      <p>Client ID: {client.client_id}</p>

      <section aria-labelledby="workspace-file-foundation-heading">
        <h3 id="workspace-file-foundation-heading">File Foundation</h3>
        <p>Client Name: {client.full_name}</p>
        <p>ID Number: {client.id_number}</p>
        <p>Retirement Planning File Status: {client.file_status}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>Open Retirement Planning File</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-professional-identification-heading">
        <h3 id="workspace-professional-identification-heading">Professional Identification</h3>
        <p>Birth Date: {profile?.birth_date ?? client.birth_date ?? "Not provided"}</p>
        <p>Contact Method: {profile?.contact_method ?? "Not provided"}</p>
        <p>Contact Details: {profile?.contact_details ?? "Not provided"}</p>
        <p>Professional Identification Status: {profile?.professional_identification_status ?? client.professional_identification_status}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>Open Client Profile</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-source-data-heading">
        <h3 id="workspace-source-data-heading">Fixation Activity Source Data</h3>
        <p>Employment Records: {employmentRecords.length}</p>
        <p>Grants: {grants.length}</p>
        <p>Actual Capitalizations: {actualCapitalizations.length}</p>
        <p>Saved Fixation Runs: {fixationHistory.length}</p>
        <p>Latest Fixation Run: {latestFixationRun ? `${latestFixationRun.status} / ${latestFixationRun.created_at ?? "Unknown"}` : "None"}</p>
        <p>
          <Link to={`/clients/${client.client_id}/employment-history`} state={clientState}>
            Open Employment History
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/grants`} state={clientState}>
            Open Grants
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/actual-capitalizations`} state={clientState}>
            Open Actual Capitalizations
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/fixation/input`} state={clientState}>
            Open Fixation Parameters
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/fixation/history`} state={clientState}>
            Open Fixation History
          </Link>
        </p>
      </section>

      <section aria-labelledby="workspace-collected-evidence-heading">
        <h3 id="workspace-collected-evidence-heading">Collected Evidence</h3>
        <p>Clearinghouse Snapshots: {clearinghouseSnapshots.length}</p>
        <p>Snapshot Collection Status: {countByStatus(clearinghouseSnapshots, (snapshot) => snapshot.collection_status)}</p>
        <p>Retirement Planning Documents: {retirementPlanningDocuments.length}</p>
        <p>Document Collection Status: {countByStatus(retirementPlanningDocuments, (document) => document.collection_status)}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>Open Collection Tools</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-verification-state-heading">
        <h3 id="workspace-verification-state-heading">Verification State</h3>
        <p>Snapshot Verification Status: {countByStatus(clearinghouseSnapshots, (snapshot) => snapshot.verification_status)}</p>
        <p>Document Verification Status: {countByStatus(retirementPlanningDocuments, (document) => document.verification_status)}</p>
        <ul>
          {clearinghouseSnapshots.map((snapshot) => (
            <li key={snapshot.clearinghouse_snapshot_id}>
              Snapshot {snapshot.source_file}: {snapshot.verification_status}
              {snapshot.verification_notes ? ` - ${snapshot.verification_notes}` : ""}
              {snapshot.verified_at ? ` - ${snapshot.verified_at}` : ""}
            </li>
          ))}
          {retirementPlanningDocuments.map((document) => (
            <li key={document.document_id}>
              Document {document.document_type}: {document.verification_status}
              {document.verification_notes ? ` - ${document.verification_notes}` : ""}
              {document.verified_at ? ` - ${document.verified_at}` : ""}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="workspace-missing-information-heading">
        <h3 id="workspace-missing-information-heading">Missing Information</h3>
        <p>Missing Data Items: {missingDataItems.filter((item) => item.missing_item_type === "data").length}</p>
        <p>Missing Document Items: {missingDataItems.filter((item) => item.missing_item_type === "document").length}</p>
        {missingDataItems.length === 0 ? (
          <p>No missing information registered.</p>
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
        <p>
          <Link to={`/clients/${client.client_id}`}>Open Missing Information Tools</Link>
        </p>
      </section>

      <p>
        <Link to="/clients">Back to client list</Link>
      </p>
    </section>
  );
}
