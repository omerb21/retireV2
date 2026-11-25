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
import { heLabel } from "../i18n/he";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiTransportError) {
    return "לא ניתן לטעון את סביבת קיבוע הזכויות. אפשר לנסות שוב בעוד רגע.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "לא ניתן לטעון את סביבת קיבוע הזכויות.";
}

function countByStatus<T>(items: T[], selectStatus: (item: T) => string): string {
  if (items.length === 0) {
    return "אין";
  }

  const counts = items.reduce<Record<string, number>>((current, item) => {
    const status = selectStatus(item);
    return {
      ...current,
      [status]: (current[status] ?? 0) + 1
    };
  }, {});

  return Object.entries(counts)
    .map(([status, count]) => `${heLabel(status)}: ${count}`)
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
        <h2>סביבת קיבוע זכויות</h2>
        <p>טוען את סביבת קיבוע הזכויות...</p>
      </section>
    );
  }

  if (isNotFound) {
    return (
      <section>
        <h2>סביבת קיבוע זכויות</h2>
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
        <h2>סביבת קיבוע זכויות</h2>
        <p role="alert">{errorMessage}</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
        </p>
      </section>
    );
  }

  if (client === null) {
    return (
      <section>
        <h2>סביבת קיבוע זכויות</h2>
        <p>סביבת קיבוע הזכויות אינה זמינה.</p>
        <p>
          <Link to="/clients">חזרה לרשימת הלקוחות</Link>
        </p>
      </section>
    );
  }

  const clientState = { clientName: client.full_name };

  return (
    <section>
      <h2>סביבת קיבוע זכויות</h2>
      <p>מזהה לקוח: {client.client_id}</p>

      <section aria-labelledby="workspace-file-foundation-heading">
        <h3 id="workspace-file-foundation-heading">פרטי התיק</h3>
        <p>שם הלקוח: {client.full_name}</p>
        <p>מספר זהות: {client.id_number}</p>
        <p>מצב תיק תכנון הפרישה: {heLabel(client.file_status)}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>פתיחת תיק תכנון הפרישה</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-professional-identification-heading">
        <h3 id="workspace-professional-identification-heading">זיהוי מקצועי</h3>
        <p>תאריך לידה: {profile?.birth_date ?? client.birth_date ?? "לא נמסר"}</p>
        <p>אמצעי קשר: {heLabel(profile?.contact_method, "לא נמסר")}</p>
        <p>פרטי קשר: {profile?.contact_details ?? "לא נמסר"}</p>
        <p>מצב זיהוי מקצועי: {heLabel(profile?.professional_identification_status ?? client.professional_identification_status)}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>פתיחת פרופיל הלקוח</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-source-data-heading">
        <h3 id="workspace-source-data-heading">נתוני המקור לקיבוע זכויות</h3>
        <p>תקופות העסקה: {employmentRecords.length}</p>
        <p>מענקים: {grants.length}</p>
        <p>היוונים בפועל: {actualCapitalizations.length}</p>
        <p>חישובי קיבוע שנשמרו: {fixationHistory.length}</p>
        <p>חישוב קיבוע אחרון: {latestFixationRun ? `${heLabel(latestFixationRun.status)} / ${latestFixationRun.created_at ?? "לא ידוע"}` : "אין"}</p>
        <p>
          <Link to={`/clients/${client.client_id}/employment-history`} state={clientState}>
            פתיחת תקופות העסקה
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/grants`} state={clientState}>
            פתיחת מענקים
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/actual-capitalizations`} state={clientState}>
            פתיחת היוונים בפועל
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/fixation/input`} state={clientState}>
            פתיחת נתוני קיבוע זכויות
          </Link>
        </p>
        <p>
          <Link to={`/clients/${client.client_id}/fixation/history`} state={clientState}>
            פתיחת היסטוריית קיבוע זכויות
          </Link>
        </p>
      </section>

      <section aria-labelledby="workspace-collected-evidence-heading">
        <h3 id="workspace-collected-evidence-heading">אסמכתאות שנאספו</h3>
        <p>דוחות מסלקה: {clearinghouseSnapshots.length}</p>
        <p>מצב איסוף דוחות: {countByStatus(clearinghouseSnapshots, (snapshot) => snapshot.collection_status)}</p>
        <p>מסמכי תכנון פרישה: {retirementPlanningDocuments.length}</p>
        <p>מצב איסוף מסמכים: {countByStatus(retirementPlanningDocuments, (document) => document.collection_status)}</p>
        <p>
          <Link to={`/clients/${client.client_id}`}>פתיחת כלי איסוף המידע</Link>
        </p>
      </section>

      <section aria-labelledby="workspace-verification-state-heading">
        <h3 id="workspace-verification-state-heading">מצב אימות</h3>
        <p>מצב אימות דוחות: {countByStatus(clearinghouseSnapshots, (snapshot) => snapshot.verification_status)}</p>
        <p>מצב אימות מסמכים: {countByStatus(retirementPlanningDocuments, (document) => document.verification_status)}</p>
        <ul>
          {clearinghouseSnapshots.map((snapshot) => (
            <li key={snapshot.clearinghouse_snapshot_id}>
              דוח {snapshot.source_file}: {heLabel(snapshot.verification_status)}
              {snapshot.verification_notes ? ` - ${snapshot.verification_notes}` : ""}
              {snapshot.verified_at ? ` - ${snapshot.verified_at}` : ""}
            </li>
          ))}
          {retirementPlanningDocuments.map((document) => (
            <li key={document.document_id}>
              מסמך {heLabel(document.document_type)}: {heLabel(document.verification_status)}
              {document.verification_notes ? ` - ${document.verification_notes}` : ""}
              {document.verified_at ? ` - ${document.verified_at}` : ""}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="workspace-missing-information-heading">
        <h3 id="workspace-missing-information-heading">מידע חסר</h3>
        <p>נתונים חסרים: {missingDataItems.filter((item) => item.missing_item_type === "data").length}</p>
        <p>מסמכים חסרים: {missingDataItems.filter((item) => item.missing_item_type === "document").length}</p>
        {missingDataItems.length === 0 ? (
          <p>לא נרשם מידע חסר.</p>
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
        <p>
          <Link to={`/clients/${client.client_id}`}>פתיחת כלי המידע החסר</Link>
        </p>
      </section>

      <p>
        <Link to="/clients">חזרה לרשימת הלקוחות</Link>
      </p>
    </section>
  );
}
