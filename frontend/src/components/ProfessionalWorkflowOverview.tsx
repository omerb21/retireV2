import {
  type MouseEvent,
  type ReactNode,
  type RefObject,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link } from "react-router-dom";

import type {
  ClearinghouseSnapshotItem,
  M01CaseItem,
  MissingDataItem,
  RetirementPlanningDocumentItem,
} from "../api/clientsApi";
import {
  readContext,
  type ReadinessContext,
} from "../api/retirementIncomeReadinessApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import { formatIsoDate } from "../utils/dateFormat";

export type WorkflowStatus =
  | "COMPLETE"
  | "INCOMPLETE"
  | "BLOCKED"
  | "READY_TO_CONTINUE"
  | "NOT_EVALUATED"
  | "NOT_AUTHORIZED";

type CollectionLoadState = "loading" | "ready" | "error";

export interface ProfessionalWorkflowOverviewProps {
  clientId: number;
  routeKey: string;
  m01Case: M01CaseItem | null;
  clearinghouseSnapshots: ClearinghouseSnapshotItem[];
  retirementPlanningDocuments: RetirementPlanningDocumentItem[];
  missingDataItems: MissingDataItem[];
  collectionLoadState: CollectionLoadState;
  readinessContextRevision: number;
}

type AcceptedContext = {
  clientId: number;
  routeKey: string;
  revision: number;
  value: ReadinessContext;
};

type ContextLoad =
  | { state: "loading" }
  | { state: "error" }
  | { state: "ready"; accepted: AcceptedContext };

type ActionTarget =
  | { kind: "route"; to: string }
  | { kind: "anchor"; id: string };

export const workflowLifecyclePolicy = {
  nextReadinessContextRevision(current: number): number {
    return current + 1;
  },
};

export const workflowProjectionPolicy = {
  phase1(m01Case: M01CaseItem | null): WorkflowStatus {
    return m01Case?.completeness.conflicting_field_ids.length
      ? "BLOCKED"
      : m01Case?.completeness.status === "complete"
        && m01Case.completeness.missing_field_ids.length === 0
        && m01Case.completeness.conflicting_field_ids.length === 0
          ? "COMPLETE"
          : "INCOMPLETE";
  },
  phase2(
    collectionLoadState: CollectionLoadState,
    clearinghouseSnapshotCount: number,
    retirementPlanningDocumentCount: number,
  ): WorkflowStatus {
    return collectionLoadState !== "ready"
      ? "NOT_EVALUATED"
      : clearinghouseSnapshotCount === 0 || retirementPlanningDocumentCount === 0
        ? "INCOMPLETE"
        : "READY_TO_CONTINUE";
  },
  phase2Target(
    clientId: number,
    collectionLoadState: CollectionLoadState,
    clearinghouseSnapshotCount: number,
    retirementPlanningDocumentCount: number,
  ): ActionTarget {
    return collectionLoadState !== "ready" || clearinghouseSnapshotCount === 0
      ? { kind: "anchor", id: "clearinghouse-snapshots-heading" }
      : retirementPlanningDocumentCount === 0
        ? { kind: "anchor", id: "retirement-documents-heading" }
        : { kind: "route", to: `/clients/${clientId}/professional-sources` };
  },
  phase3(context: ReadinessContext | null): WorkflowStatus {
    return context === null
      ? "NOT_EVALUATED"
      : context.planning_input_ready
        ? "COMPLETE"
        : context.blocking_facts.length > 0
          ? "BLOCKED"
          : "INCOMPLETE";
  },
  phase4(context: ReadinessContext | null): WorkflowStatus {
    return context === null
      ? "NOT_EVALUATED"
      : context.planning_input_ready && context.retirement_target_ready
        ? "READY_TO_CONTINUE"
        : "BLOCKED";
  },
  rmigaStatus(): WorkflowStatus {
    return "NOT_AUTHORIZED";
  },
  nextTarget(
    clientId: number,
    phase1: WorkflowStatus,
    phase2: WorkflowStatus,
    phase2Target: ActionTarget,
    phase3: WorkflowStatus,
  ): ActionTarget {
    return phase1 !== "COMPLETE"
      ? { kind: "anchor", id: "m01-case-foundation-heading" }
      : phase2 === "INCOMPLETE" || phase2 === "NOT_EVALUATED"
        ? phase2Target
        : phase3 !== "COMPLETE"
          ? { kind: "route", to: `/clients/${clientId}/planning-input` }
          : { kind: "route", to: `/clients/${clientId}/retirement-income-readiness` };
  },
};

export const workflowRequestPolicy = {
  acceptsRequest(input: {
    active: boolean;
    aborted: boolean;
    responseClientId?: number;
    expectedClientId: number;
    capturedRevision: number;
    latestRevision: number;
    capturedGeneration: number;
    latestGeneration: number;
    currentClientContext: boolean;
  }): boolean {
    return input.active
      && !input.aborted
      && (input.responseClientId === undefined || input.responseClientId === input.expectedClientId)
      && input.capturedRevision === input.latestRevision
      && input.capturedGeneration === input.latestGeneration
      && input.currentClientContext;
  },
  acceptsRenderedContext(
    accepted: AcceptedContext,
    clientId: number,
    routeKey: string,
    revision: number,
  ): boolean {
    return accepted.clientId === clientId
      && accepted.routeKey === routeKey
      && accepted.revision === revision;
  },
};

export const workflowNavigationPolicy = {
  focusAndScroll(target: HTMLElement | null): void {
    target?.focus({ preventScroll: true });
    target?.scrollIntoView?.({ block: "start" });
  },
};

const STATUS_LABELS: Record<WorkflowStatus, string> = {
  COMPLETE: "הושלם",
  INCOMPLETE: "טרם הושלם",
  BLOCKED: "חסום",
  READY_TO_CONTINUE: "אפשר להמשיך",
  NOT_EVALUATED: "טרם הוערך",
  NOT_AUTHORIZED: "לא מורשה",
};

function counts(values: Array<string | null | undefined>): Array<[string, number]> {
  const grouped = new Map<string, number>();
  for (const value of values) {
    const key = value ?? "לא תועד";
    grouped.set(key, (grouped.get(key) ?? 0) + 1);
  }
  return [...grouped.entries()].sort(([left], [right]) => left.localeCompare(right));
}

function AnchorLink({
  clientId,
  targetId,
  children,
  triggerRef,
}: {
  clientId: number;
  targetId: string;
  children: ReactNode;
  triggerRef?: RefObject<HTMLAnchorElement>;
}) {
  function activate(event: MouseEvent<HTMLAnchorElement>) {
    if (
      event.button !== 0
      || event.altKey
      || event.ctrlKey
      || event.metaKey
      || event.shiftKey
    ) {
      return;
    }
    event.preventDefault();
    const href = `/clients/${clientId}#${targetId}`;
    window.history.pushState(window.history.state, "", href);
    workflowNavigationPolicy.focusAndScroll(document.getElementById(targetId));
  }

  return (
    <a
      ref={triggerRef}
      href={`/clients/${clientId}#${targetId}`}
      onClick={activate}
    >
      {children}
    </a>
  );
}

function ActionLink({
  clientId,
  target,
  children,
  triggerRef,
}: {
  clientId: number;
  target: ActionTarget;
  children: ReactNode;
  triggerRef?: RefObject<HTMLAnchorElement>;
}) {
  return target.kind === "anchor" ? (
    <AnchorLink clientId={clientId} targetId={target.id} triggerRef={triggerRef}>
      {children}
    </AnchorLink>
  ) : (
    <Link ref={triggerRef} to={target.to}>{children}</Link>
  );
}

function Status({ value }: { value: WorkflowStatus }) {
  return <strong><bdi>{value}</bdi> — {STATUS_LABELS[value]}</strong>;
}

export function ProfessionalWorkflowOverview({
  clientId,
  routeKey,
  m01Case,
  clearinghouseSnapshots,
  retirementPlanningDocuments,
  missingDataItems,
  collectionLoadState,
  readinessContextRevision,
}: ProfessionalWorkflowOverviewProps) {
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(clientId, routeKey);
  const requestGeneration = useRef(0);
  const latestRevision = useRef(readinessContextRevision);
  latestRevision.current = readinessContextRevision;
  const nextActionRef = useRef<HTMLAnchorElement>(null);
  const lastInPageOrigin = useRef<HTMLAnchorElement | null>(null);
  const [contextLoad, setContextLoad] = useState<ContextLoad>({ state: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    const capturedClient = captureClientContext();
    const capturedRevision = readinessContextRevision;
    const capturedGeneration = ++requestGeneration.current;
    let active = true;
    setContextLoad({ state: "loading" });

    void readContext(clientId, controller.signal).then((value) => {
      if (!workflowRequestPolicy.acceptsRequest({
        active,
        aborted: controller.signal.aborted,
        responseClientId: value.client_id,
        expectedClientId: clientId,
        capturedRevision,
        latestRevision: latestRevision.current,
        capturedGeneration,
        latestGeneration: requestGeneration.current,
        currentClientContext: isCurrentClientContext(capturedClient),
      })) {
        return;
      }
      setContextLoad({
        state: "ready",
        accepted: {
          clientId,
          routeKey,
          revision: capturedRevision,
          value,
        },
      });
    }).catch((reason: unknown) => {
      if (!workflowRequestPolicy.acceptsRequest({
        active,
        aborted: controller.signal.aborted,
        expectedClientId: clientId,
        capturedRevision,
        latestRevision: latestRevision.current,
        capturedGeneration,
        latestGeneration: requestGeneration.current,
        currentClientContext: isCurrentClientContext(capturedClient),
      })) {
        return;
      }
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setContextLoad({ state: "error" });
      }
    });

    return () => {
      active = false;
      controller.abort();
    };
  }, [
    captureClientContext,
    clientId,
    isCurrentClientContext,
    readinessContextRevision,
    routeKey,
  ]);

  useEffect(() => {
    function restoreFocusOnBack() {
      if (window.location.hash === "" && lastInPageOrigin.current !== null) {
        lastInPageOrigin.current.focus();
        lastInPageOrigin.current = null;
      }
    }
    window.addEventListener("popstate", restoreFocusOnBack);
    return () => window.removeEventListener("popstate", restoreFocusOnBack);
  }, []);

  const acceptedContext = contextLoad.state === "ready"
    && workflowRequestPolicy.acceptsRenderedContext(
      contextLoad.accepted,
      clientId,
      routeKey,
      readinessContextRevision,
    )
      ? contextLoad.accepted.value
      : null;

  const phase1 = workflowProjectionPolicy.phase1(m01Case);
  const phase2 = workflowProjectionPolicy.phase2(
    collectionLoadState,
    clearinghouseSnapshots.length,
    retirementPlanningDocuments.length,
  );
  const phase2Target = workflowProjectionPolicy.phase2Target(
    clientId,
    collectionLoadState,
    clearinghouseSnapshots.length,
    retirementPlanningDocuments.length,
  );
  const phase3 = workflowProjectionPolicy.phase3(acceptedContext);
  const phase4 = workflowProjectionPolicy.phase4(acceptedContext);
  const nextTarget = workflowProjectionPolicy.nextTarget(
    clientId,
    phase1,
    phase2,
    phase2Target,
    phase3,
  );

  const snapshotCollectionGroups = useMemo(
    () => counts(clearinghouseSnapshots.map((item) => item.collection_status)),
    [clearinghouseSnapshots],
  );
  const snapshotVerificationGroups = useMemo(
    () => counts(clearinghouseSnapshots.map((item) => item.verification_status)),
    [clearinghouseSnapshots],
  );
  const documentCollectionGroups = useMemo(
    () => counts(retirementPlanningDocuments.map((item) => item.collection_status)),
    [retirementPlanningDocuments],
  );
  const documentVerificationGroups = useMemo(
    () => counts(retirementPlanningDocuments.map((item) => item.verification_status)),
    [retirementPlanningDocuments],
  );
  const missingGroups = useMemo(
    () => counts(missingDataItems.map((item) => item.advisory_status)),
    [missingDataItems],
  );

  function rememberInPageOrigin(event: MouseEvent<HTMLDivElement>) {
    const anchor = (event.target as HTMLElement).closest("a");
    if (anchor?.hash) {
      lastInPageOrigin.current = anchor;
    }
  }

  return (
    <nav dir="rtl" aria-label="מפת תהליך העבודה המקצועי" onClick={rememberInPageOrigin}>
      <h3>מפת תהליך העבודה המקצועי</h3>
      <ol>
        <li>
          <h4>1. תשתית תיק הלקוח</h4>
          <p><Status value={phase1} /></p>
          {m01Case?.completeness.missing_field_ids.map((field) => (
            <p key={`missing:${field}`}>חסר: <bdi>{field}</bdi></p>
          ))}
          {m01Case?.completeness.conflicting_field_ids.map((field) => (
            <p key={`conflict:${field}`}>סתירה: <bdi>{field}</bdi></p>
          ))}
          <AnchorLink clientId={clientId} targetId="m01-case-foundation-heading">
            מעבר לעריכת תשתית התיק
          </AnchorLink>
        </li>
        <li>
          <h4>2. הכנת ראיות ומקורות</h4>
          <p><Status value={phase2} /></p>
          <p>תמונות מסלקה: {clearinghouseSnapshots.length}</p>
          <p>מסמכים: {retirementPlanningDocuments.length}</p>
          <p>פריטי מידע חסר: {missingDataItems.length}</p>
          {snapshotCollectionGroups.map(([name, count]) => <p key={`snapshot-collection:${name}`}>מצב איסוף מסלקה <bdi>{name}</bdi>: {count}</p>)}
          {snapshotVerificationGroups.map(([name, count]) => <p key={`snapshot-verification:${name}`}>מצב אימות מסלקה <bdi>{name}</bdi>: {count}</p>)}
          {documentCollectionGroups.map(([name, count]) => <p key={`document-collection:${name}`}>מצב איסוף מסמכים <bdi>{name}</bdi>: {count}</p>)}
          {documentVerificationGroups.map(([name, count]) => <p key={`document-verification:${name}`}>מצב אימות מסמכים <bdi>{name}</bdi>: {count}</p>)}
          {missingGroups.map(([name, count]) => <p key={`missing-advisory:${name}`}>מצב מידע חסר <bdi>{name}</bdi>: {count}</p>)}
          {collectionLoadState === "error" ? <p role="alert">נתוני האיסוף אינם זמינים לבדיקה.</p> : null}
          <ActionLink clientId={clientId} target={phase2Target}>
            {phase2Target.kind === "route" ? "המשך להכנת מקורות מקצועיים" : "טיפול בפעילות איסוף הראיות"}
          </ActionLink>
          {missingDataItems.length > 0 ? (
            <> · <AnchorLink clientId={clientId} targetId="missing-data-heading">בדיקת מידע חסר</AnchorLink></>
          ) : null}
        </li>
        <li>
          <h4>3. קלט תכנון</h4>
          <p><Status value={phase3} /></p>
          {acceptedContext?.blocking_facts.map((fact, index) => (
            <p key={`${fact.source_id ?? "none"}:${fact.code}:${index}`}>
              <bdi>{fact.code}</bdi>{fact.source_id ? <> · <bdi>{fact.source_id}</bdi></> : null}
            </p>
          ))}
          <Link to={`/clients/${clientId}/planning-input`}>מעבר לקלט התכנון</Link>
        </li>
        <li>
          <h4>4. מוכנות הכנסה במועד היעד</h4>
          <p><Status value={phase4} /></p>
          <p>תאריך יעד: {formatIsoDate(acceptedContext?.retirement_target_date ?? null) || "לא נקבע"}</p>
          <p>פער הכנסה חודשי: <Status value={workflowProjectionPolicy.rmigaStatus()} /></p>
          <Link to={`/clients/${clientId}/retirement-income-readiness`}>מעבר למוכנות הכנסה</Link>
        </li>
        <li>
          <h4>5. פעילות מקצועית נוספת, לרבות קיבוע זכויות</h4>
          <p><Status value="NOT_EVALUATED" /></p>
          <Link to={`/clients/${clientId}/fixation/workspace`}>מעבר לפעילות מקצועית נוספת</Link>
        </li>
      </ol>
      {contextLoad.state === "loading" ? <p aria-live="polite">טוען מצב מוכנות עדכני…</p> : null}
      {contextLoad.state === "error" ? <p role="alert">מצב המוכנות אינו זמין כעת.</p> : null}
      <section aria-labelledby="professional-workflow-next-action-heading">
        <h4 id="professional-workflow-next-action-heading">הפעולה הבאה המוצעת</h4>
        <ActionLink clientId={clientId} target={nextTarget} triggerRef={nextActionRef}>
          מעבר לפעולה הבאה
        </ActionLink>
      </section>
    </nav>
  );
}
