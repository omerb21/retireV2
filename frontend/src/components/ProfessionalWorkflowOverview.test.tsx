import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  ClearinghouseSnapshotItem,
  M01CaseItem,
  MissingDataItem,
  RetirementPlanningDocumentItem,
} from "../api/clientsApi";
import type { ReadinessContext } from "../api/retirementIncomeReadinessApi";
import {
  ProfessionalWorkflowOverview,
  type ProfessionalWorkflowOverviewProps,
  workflowNavigationPolicy,
  workflowProjectionPolicy,
  workflowRequestPolicy,
} from "./ProfessionalWorkflowOverview";

const { readContextMock } = vi.hoisted(() => ({
  readContextMock: vi.fn(),
}));

vi.mock("../api/retirementIncomeReadinessApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/retirementIncomeReadinessApi")>(),
  readContext: readContextMock,
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

function m01Case(overrides: Partial<M01CaseItem> = {}): M01CaseItem {
  return {
    client_id: 7,
    display_name: "דנה לוי",
    id_number: "123456789",
    birth_date: "1980-01-01",
    gender: "female",
    employment_status: "salaried_employee",
    planned_retirement_date: null,
    planned_retirement_age: 67,
    lifecycle_status: "draft",
    completeness: {
      status: "complete",
      missing_field_ids: [],
      conflicting_field_ids: [],
    },
    updated_at: "2026-10-21T00:00:00Z",
    ...overrides,
  };
}

const snapshot: ClearinghouseSnapshotItem = {
  clearinghouse_snapshot_id: "snapshot:1",
  client_id: 7,
  import_date: "2026-10-01",
  source_type: "clearinghouse",
  source_file: "snapshot.xml",
  collection_status: "collected",
  collection_notes: null,
  verification_status: "verified",
  verification_notes: null,
  verified_at: "2026-10-02T00:00:00Z",
  created_at: "2026-10-01T00:00:00Z",
};

const documentItem: RetirementPlanningDocumentItem = {
  document_id: "document:1",
  client_id: 7,
  document_type: "pension_report",
  source_type: "uploaded",
  source_file: "report.pdf",
  collection_date: "2026-10-01",
  collection_status: "collected",
  collection_notes: null,
  verification_status: "verified",
  verification_notes: null,
  verified_at: "2026-10-02T00:00:00Z",
  created_at: "2026-10-01T00:00:00Z",
};

const missingItem: MissingDataItem = {
  missing_data_item_id: "missing:1",
  client_id: 7,
  missing_item_type: "data",
  missing_item_label: "מסמך משני",
  missing_status: "open",
  notes: null,
  planning_domain: null,
  related_record_type: null,
  related_record_id: null,
  advisory_status: "advisory",
  neutral_reason: null,
  created_at: "2026-10-01T00:00:00Z",
};

function context(overrides: Partial<ReadinessContext> = {}): ReadinessContext {
  return {
    schema_version: "RTDIR_PLANNING_CONTEXT_V1",
    client_id: 7,
    planning_calculation_input_fingerprint: "planning:7",
    planning_input_ready: true,
    retirement_target_date: "2047-01-01",
    retirement_target_ready: true,
    blocking_facts: [],
    ...overrides,
  };
}

function props(overrides: Partial<ProfessionalWorkflowOverviewProps> = {}): ProfessionalWorkflowOverviewProps {
  return {
    clientId: 7,
    routeKey: "route-a",
    m01Case: m01Case(),
    clearinghouseSnapshots: [snapshot],
    retirementPlanningDocuments: [documentItem],
    missingDataItems: [missingItem],
    collectionLoadState: "ready",
    readinessContextRevision: 0,
    ...overrides,
  };
}

function renderOverview(nextProps: ProfessionalWorkflowOverviewProps) {
  return render(
    <MemoryRouter>
      <ProfessionalWorkflowOverview {...nextProps} />
      <h3 id="m01-case-foundation-heading" tabIndex={-1}>תשתית תיק הלקוח</h3>
      <h3 id="clearinghouse-snapshots-heading" tabIndex={-1}>תמונות מצב מהמסלקה</h3>
      <h3 id="retirement-documents-heading" tabIndex={-1}>מסמכי תכנון פרישה</h3>
      <h3 id="missing-data-heading" tabIndex={-1}>מעקב אחר מידע חסר</h3>
    </MemoryRouter>,
  );
}

function phase(name: RegExp): HTMLElement {
  return screen.getByRole("heading", { name }).closest("li") as HTMLElement;
}

afterEach(() => {
  readContextMock.mockReset();
  window.history.replaceState(null, "", "/");
});

describe("ProfessionalWorkflowOverview", () => {
  it("projects the five read-only phases and the deterministic next action without inventing authority", async () => {
    readContextMock.mockResolvedValue(context());
    renderOverview(props());

    expect(await screen.findByRole("navigation", { name: "מפת תהליך העבודה המקצועי" })).toHaveAttribute("dir", "rtl");
    expect(within(phase(/^1\./)).getByText(/COMPLETE/)).toBeInTheDocument();
    expect(within(phase(/^2\./)).getByText(/READY_TO_CONTINUE/)).toBeInTheDocument();
    expect(within(phase(/^3\./)).getByText(/COMPLETE/)).toBeInTheDocument();
    expect(within(phase(/^4\./)).getByText(/READY_TO_CONTINUE/)).toBeInTheDocument();
    expect(within(phase(/^4\./)).getByText(/NOT_AUTHORIZED/)).toBeInTheDocument();
    expect(within(phase(/^5\./)).getByText(/NOT_EVALUATED/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "מעבר לפעולה הבאה" })).toHaveAttribute(
      "href",
      "/clients/7/retirement-income-readiness",
    );
    expect(readContextMock).toHaveBeenCalledTimes(1);
  });

  it("routes each Phase 2 condition to the existing location that can address it", async () => {
    readContextMock.mockResolvedValue(context());
    const rendered = renderOverview(props({ clearinghouseSnapshots: [], retirementPlanningDocuments: [] }));
    expect(await screen.findByRole("link", { name: "מעבר לפעולה הבאה" })).toHaveAttribute(
      "href",
      "/clients/7#clearinghouse-snapshots-heading",
    );

    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props({ retirementPlanningDocuments: [] })} />
        <h3 id="retirement-documents-heading" tabIndex={-1}>מסמכי תכנון פרישה</h3>
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "מעבר לפעולה הבאה" })).toHaveAttribute(
      "href",
      "/clients/7#retirement-documents-heading",
    );

    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props()} />
      </MemoryRouter>,
    );
    expect(within(phase(/^2\./)).getByRole("link", { name: "המשך להכנת מקורות מקצועיים" })).toHaveAttribute(
      "href",
      "/clients/7/professional-sources",
    );
  });

  it("focuses same-page Phase 1 and restores focus to the action on browser back", async () => {
    readContextMock.mockResolvedValue(context());
    renderOverview(props({
      m01Case: m01Case({
        completeness: {
          status: "incomplete",
          missing_field_ids: ["birth_date"],
          conflicting_field_ids: [],
        },
      }),
    }));
    await screen.findByRole("navigation", { name: "מפת תהליך העבודה המקצועי" });
    const action = screen.getByRole("link", { name: "מעבר לפעולה הבאה" });
    fireEvent.click(action);
    expect(window.location.hash).toBe("#m01-case-foundation-heading");
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "תשתית תיק הלקוח" }));

    window.history.replaceState(null, "", "/clients/7");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(document.activeElement).toBe(action);
  });

  it("kills and restores the ordinary focus oracle when the production focus mapping is removed", async () => {
    readContextMock.mockResolvedValue(context());
    renderOverview(props({
      m01Case: m01Case({
        completeness: {
          status: "incomplete",
          missing_field_ids: ["employment_status"],
          conflicting_field_ids: [],
        },
      }),
    }));
    await screen.findByRole("navigation", { name: "מפת תהליך העבודה המקצועי" });
    const action = screen.getByRole("link", { name: "מעבר לפעולה הבאה" });
    const target = screen.getByRole("heading", { name: "תשתית תיק הלקוח" });
    const ordinary = () => {
      action.focus();
      fireEvent.click(action);
      expect(document.activeElement).toBe(target);
    };

    ordinary();
    const mutation = vi.spyOn(workflowNavigationPolicy, "focusAndScroll").mockImplementation(() => undefined);
    let killed = false;
    try {
      ordinary();
    } catch {
      killed = true;
    } finally {
      mutation.mockRestore();
    }
    expect(killed).toBe(true);
    ordinary();
  });

  it("kills and restores each material workflow projection mapping with one unchanged ordinary oracle", async () => {
    const ordinary = async () => {
      readContextMock.mockResolvedValue(context({
        planning_input_ready: false,
        retirement_target_ready: false,
        blocking_facts: [{ source_id: "income:1", code: "PLANNING_BLOCKER" }],
      }));
      const view = renderOverview(props({
        m01Case: m01Case({
          completeness: {
            status: "incomplete",
            missing_field_ids: ["birth_date"],
            conflicting_field_ids: ["id_number"],
          },
        }),
        retirementPlanningDocuments: [],
        missingDataItems: [missingItem],
      }));
      try {
        expect(await within(phase(/^1\./)).findByText(/BLOCKED/)).toBeInTheDocument();
        expect(within(phase(/^2\./)).getByText(/INCOMPLETE/)).toBeInTheDocument();
        expect(within(phase(/^2\./)).getByRole("link", { name: "טיפול בפעילות איסוף הראיות" })).toHaveAttribute(
          "href",
          "/clients/7#retirement-documents-heading",
        );
        expect(await screen.findByText("PLANNING_BLOCKER")).toBeInTheDocument();
        expect(within(phase(/^3\./)).getByText(/BLOCKED/)).toBeInTheDocument();
        expect(within(phase(/^4\./)).getAllByText(/BLOCKED/)).toHaveLength(1);
        expect(within(phase(/^4\./)).getByText(/NOT_AUTHORIZED/)).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "מעבר לפעולה הבאה" })).toHaveAttribute(
          "href",
          "/clients/7#m01-case-foundation-heading",
        );
      } finally {
        view.unmount();
      }
    };

    await ordinary();
    const mutations = [
      () => vi.spyOn(workflowProjectionPolicy, "phase1").mockReturnValue("COMPLETE"),
      () => vi.spyOn(workflowProjectionPolicy, "phase2").mockReturnValue("READY_TO_CONTINUE"),
      () => vi.spyOn(workflowProjectionPolicy, "phase2Target").mockReturnValue({ kind: "route", to: "/wrong" }),
      () => vi.spyOn(workflowProjectionPolicy, "phase3").mockReturnValue("COMPLETE"),
      () => vi.spyOn(workflowProjectionPolicy, "phase4").mockReturnValue("COMPLETE"),
      () => vi.spyOn(workflowProjectionPolicy, "rmigaStatus").mockReturnValue("READY_TO_CONTINUE"),
      () => vi.spyOn(workflowProjectionPolicy, "nextTarget").mockReturnValue({ kind: "route", to: "/wrong" }),
    ];
    for (const mutate of mutations) {
      const mutation = mutate();
      let killed = false;
      try {
        await ordinary();
      } catch {
        killed = true;
      } finally {
        mutation.mockRestore();
      }
      expect(killed).toBe(true);
      await ordinary();
    }
  });

  it("invalidates same-client readiness immediately and ignores an obsolete revision response", async () => {
    const oldContext = deferred<ReadinessContext>();
    const freshContext = deferred<ReadinessContext>();
    readContextMock
      .mockImplementationOnce(() => oldContext.promise)
      .mockImplementationOnce(() => freshContext.promise);
    const rendered = renderOverview(props());
    await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(1));

    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props({ readinessContextRevision: 1 })} />
      </MemoryRouter>,
    );
    expect(within(phase(/^3\./)).getByText(/NOT_EVALUATED/)).toBeInTheDocument();
    await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(2));

    await act(async () => oldContext.resolve(context({
      planning_input_ready: false,
      retirement_target_ready: false,
      blocking_facts: [{ source_id: null, code: "STALE_SAME_CLIENT" }],
    })));
    expect(screen.queryByText("STALE_SAME_CLIENT")).not.toBeInTheDocument();

    await act(async () => freshContext.resolve(context({
      planning_input_ready: false,
      retirement_target_ready: false,
      blocking_facts: [{ source_id: null, code: "FRESH_BLOCKER" }],
    })));
    expect(await screen.findByText("FRESH_BLOCKER")).toBeInTheDocument();
  });

  it("kills and restores the same-client revision oracle when the production response guards are bypassed", async () => {
    const ordinary = async () => {
      const oldContext = deferred<ReadinessContext>();
      const freshContext = deferred<ReadinessContext>();
      let oldSignal: AbortSignal | undefined;
      readContextMock
        .mockImplementationOnce((_clientId: number, signal?: AbortSignal) => {
          oldSignal = signal;
          return oldContext.promise;
        })
        .mockImplementationOnce(() => freshContext.promise);
      const view = renderOverview(props());
      try {
        await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(1));
        view.rerender(<MemoryRouter><ProfessionalWorkflowOverview {...props({ readinessContextRevision: 1 })} /></MemoryRouter>);
        await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(2));
        expect(oldSignal?.aborted).toBe(true);
        await act(async () => oldContext.resolve(context({
          planning_input_ready: false,
          retirement_target_ready: false,
          blocking_facts: [{ source_id: null, code: "OBSOLETE_REVISION" }],
        })));
        expect(screen.queryByText("OBSOLETE_REVISION")).not.toBeInTheDocument();
        await act(async () => freshContext.resolve(context()));
      } finally {
        view.unmount();
      }
    };

    readContextMock.mockClear();
    await ordinary();
    readContextMock.mockClear();
    const requestMutation = vi.spyOn(workflowRequestPolicy, "acceptsRequest").mockReturnValue(true);
    const renderMutation = vi.spyOn(workflowRequestPolicy, "acceptsRenderedContext").mockReturnValue(true);
    let killed = false;
    try {
      await ordinary();
    } catch {
      killed = true;
    } finally {
      requestMutation.mockRestore();
      renderMutation.mockRestore();
    }
    expect(killed).toBe(true);
    readContextMock.mockClear();
    await ordinary();
  });

  it("rejects late A responses across an A-to-B-to-A route generation sequence", async () => {
    const oldA = deferred<ReadinessContext>();
    const b = deferred<ReadinessContext>();
    const newA = deferred<ReadinessContext>();
    readContextMock
      .mockImplementationOnce(() => oldA.promise)
      .mockImplementationOnce(() => b.promise)
      .mockImplementationOnce(() => newA.promise);
    const rendered = renderOverview(props());
    await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(1));
    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props({ clientId: 8, routeKey: "route-b", m01Case: m01Case({ client_id: 8 }) })} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(2));
    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props({ routeKey: "route-a-return" })} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(3));

    await act(async () => oldA.resolve(context({ blocking_facts: [{ source_id: null, code: "OLD_A" }] })));
    await act(async () => b.resolve(context({ client_id: 8, blocking_facts: [{ source_id: null, code: "CLIENT_B" }] })));
    expect(screen.queryByText(/OLD_A|CLIENT_B/)).not.toBeInTheDocument();
    await act(async () => newA.resolve(context({
      planning_input_ready: false,
      retirement_target_ready: false,
      blocking_facts: [{ source_id: null, code: "CURRENT_A" }],
    })));
    expect(await screen.findByText("CURRENT_A")).toBeInTheDocument();
  });

  it("kills and restores the A-to-B-to-A oracle when the production request guards are bypassed", async () => {
    const ordinary = async () => {
      const oldA = deferred<ReadinessContext>();
      const b = deferred<ReadinessContext>();
      const currentA = deferred<ReadinessContext>();
      readContextMock
        .mockImplementationOnce(() => oldA.promise)
        .mockImplementationOnce(() => b.promise)
        .mockImplementationOnce(() => currentA.promise);
      const view = renderOverview(props());
      try {
        await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(1));
        view.rerender(<MemoryRouter><ProfessionalWorkflowOverview {...props({ clientId: 8, routeKey: "route-b", m01Case: m01Case({ client_id: 8 }) })} /></MemoryRouter>);
        await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(2));
        view.rerender(<MemoryRouter><ProfessionalWorkflowOverview {...props({ routeKey: "route-a-return" })} /></MemoryRouter>);
        await waitFor(() => expect(readContextMock).toHaveBeenCalledTimes(3));
        await act(async () => oldA.resolve(context({
          planning_input_ready: false,
          retirement_target_ready: false,
          blocking_facts: [{ source_id: null, code: "OBSOLETE_A" }],
        })));
        expect(screen.queryByText("OBSOLETE_A")).not.toBeInTheDocument();
        await act(async () => currentA.resolve(context()));
      } finally {
        view.unmount();
      }
    };

    readContextMock.mockClear();
    await ordinary();
    readContextMock.mockClear();
    const requestMutation = vi.spyOn(workflowRequestPolicy, "acceptsRequest").mockReturnValue(true);
    const renderMutation = vi.spyOn(workflowRequestPolicy, "acceptsRenderedContext").mockReturnValue(true);
    let killed = false;
    try {
      await ordinary();
    } catch {
      killed = true;
    } finally {
      requestMutation.mockRestore();
      renderMutation.mockRestore();
    }
    expect(killed).toBe(true);
    readContextMock.mockClear();
    await ordinary();
  });

  it("fails unavailable context closed and preserves blocker order from an accepted response", async () => {
    readContextMock.mockRejectedValueOnce(new Error("unavailable"));
    const rendered = renderOverview(props());
    expect(await screen.findByRole("alert", { name: "" })).toHaveTextContent("מצב המוכנות אינו זמין כעת");
    expect(within(phase(/^3\./)).getByText(/NOT_EVALUATED/)).toBeInTheDocument();

    readContextMock.mockResolvedValueOnce(context({
      planning_input_ready: false,
      retirement_target_ready: false,
      blocking_facts: [
        { source_id: "income:2", code: "SECOND" },
        { source_id: "income:1", code: "FIRST" },
      ],
    }));
    rendered.rerender(
      <MemoryRouter>
        <ProfessionalWorkflowOverview {...props({ readinessContextRevision: 1 })} />
      </MemoryRouter>,
    );
    expect(await screen.findByText("SECOND")).toBeInTheDocument();
    const blockers = within(phase(/^3\./)).getAllByText(/SECOND|FIRST/);
    expect(blockers.map((item) => item.textContent)).toEqual(expect.arrayContaining(["SECOND", "FIRST"]));
    expect(blockers[0]).toHaveTextContent("SECOND");
    expect(blockers[1]).toHaveTextContent("FIRST");
  });
});
