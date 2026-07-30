import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getClient, type ClientDetailItem } from "../api/clientsApi";
import {
  actOnM04, createM04Proposal, getM04Eligibility, getM04History,
  getM04MatchedRules, getM04Target, listM04Targets, overrideM04,
  previewM04Rules, startM04, undoM04, type M04Component,
  type M04ComponentInterpretation, type M04ComponentKind,
  type M04ProductFamily, type M04Revision, type M04RulePreview,
  type M04Target,
} from "../api/m04ClassificationApi";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";

const PRODUCT_FAMILIES: M04ProductFamily[] = [
  "insurance_policy", "savings_policy", "provident_fund",
  "investment_provident_fund", "education_fund", "pension_fund",
  "unknown_or_unresolved",
];
const COMPONENT_KINDS: M04ComponentKind[] = [
  "severance_component", "contribution_component", "unknown_component",
];
const INTERPRETATIONS: M04ComponentInterpretation[] = [
  "pension", "capital", "unresolved",
];
type ComponentDraft = {
  evidenceIdentity: string; originalLabel: string | null; originalCode: string | null;
  componentKind: M04ComponentKind; interpretation: M04ComponentInterpretation;
  currentEmployerRelated: "yes" | "no" | "unknown"; explanation: string;
};
const message = (error: unknown) =>
  error instanceof Error ? error.message : "M04 request failed";
const draftsFrom = (rows: M04Component[]): ComponentDraft[] => rows.map((row) => ({
  evidenceIdentity: row.evidence_identity,
  originalLabel: row.original_label,
  originalCode: row.original_code,
  componentKind: row.component_kind,
  interpretation: row.interpretation,
  currentEmployerRelated: row.current_employer_related,
  explanation: row.explanation || "Planner classification explanation",
}));

export function M04ClassificationScreen() {
  const { clientId: raw } = useParams();
  const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } =
    useClientContextGeneration(clientId, location.key);
  const [client, setClient] = useState<ClientDetailItem | null>(null);
  const [targets, setTargets] = useState<M04Target[]>([]);
  const [target, setTarget] = useState<M04Target | null>(null);
  const [history, setHistory] = useState<M04Revision[]>([]);
  const [preview, setPreview] = useState<M04RulePreview | null>(null);
  const [rules, setRules] = useState<Record<string, unknown>[]>([]);
  const [retainedId, setRetainedId] = useState("");
  const [reasonCode, setReasonCode] = useState("planner_decision");
  const [explanation, setExplanation] = useState("");
  const [family, setFamily] = useState<M04ProductFamily>("unknown_or_unresolved");
  const [components, setComponents] = useState<ComponentDraft[]>([]);
  const [historicalId, setHistoricalId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setClient(null); setTargets([]); setTarget(null); setHistory([]);
    setPreview(null); setRules([]); setRetainedId(""); setExplanation("");
    setFamily("unknown_or_unresolved"); setComponents([]); setHistoricalId("");
    setError(null); setLoading(false); setSubmitting(false);
  }, [clientId, location.key]);

  const bindRevision = useCallback((revision: M04Revision | null) => {
    if (!revision) return;
    setFamily(revision.product_family ?? "unknown_or_unresolved");
    setComponents(draftsFrom(revision.components));
  }, []);

  const loadTargets = useCallback(async () => {
    if (clientId === null) return;
    const token = captureClientContext(); setLoading(true); setError(null);
    try {
      const [nextClient, rows] = await Promise.all([
        getClient(clientId), listM04Targets(clientId),
      ]);
      if (!isCurrentClientContext(token)) return;
      setClient(nextClient); setTargets(rows);
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setLoading(false);
    }
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadTargets(); }, [loadTargets]);

  const loadTarget = useCallback(async (intakeId: string) => {
    if (clientId === null) return;
    const token = captureClientContext(); setLoading(true); setError(null); setPreview(null);
    try {
      const [next, revisions, eligibility, matched] = await Promise.all([
        getM04Target(clientId, intakeId), getM04History(clientId, intakeId),
        getM04Eligibility(clientId, intakeId), getM04MatchedRules(clientId, intakeId),
      ]);
      if (!isCurrentClientContext(token)) return;
      const combined = { ...next, eligibility };
      setTarget(combined); setHistory(revisions); setRules(matched);
      bindRevision(combined.current_revision);
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setLoading(false);
    }
  }, [bindRevision, captureClientContext, clientId, isCurrentClientContext]);

  const runPreview = async () => {
    if (clientId === null || !target) return;
    const token = captureClientContext(); setLoading(true); setError(null);
    try {
      const next = await previewM04Rules(clientId, target.intake_id);
      if (!isCurrentClientContext(token)) return;
      setPreview(next); setFamily(next.product_family);
      setComponents(draftsFrom(next.components));
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setLoading(false);
    }
  };

  const mutate = async (operation: () => Promise<unknown>) => {
    if (clientId === null || !target) return;
    const token = captureClientContext(); const intakeId = target.intake_id;
    setSubmitting(true); setError(null);
    try {
      await operation();
      if (!isCurrentClientContext(token)) return; // stale mutation launches zero refreshes
      const refreshToken = captureClientContext();
      const [next, revisions, eligibility, matched, rows] = await Promise.all([
        getM04Target(clientId, intakeId), getM04History(clientId, intakeId),
        getM04Eligibility(clientId, intakeId), getM04MatchedRules(clientId, intakeId),
        listM04Targets(clientId),
      ]);
      if (!isCurrentClientContext(refreshToken)) return;
      const combined = { ...next, eligibility };
      setTarget(combined); setHistory(revisions); setRules(matched); setTargets(rows);
      setPreview(null); setExplanation(""); bindRevision(combined.current_revision);
    } catch (cause) {
      if (isCurrentClientContext(token)) setError(message(cause));
    } finally {
      if (isCurrentClientContext(token)) setSubmitting(false);
    }
  };

  if (clientId === null) return <p>Invalid client ID.</p>;
  const current = target?.current_revision ?? null;
  const archived = target?.m01_lifecycle_status === "archived" ||
    client?.m01_case?.lifecycle_status === "archived";
  const revalidationRequired =
    target?.eligibility.exclusion_reason === "m04_revalidation_required";
  const revalidationStarted = history.some(
    (row) => row.action_type === "start_revalidation",
  );
  const reasonReady = Boolean(reasonCode.trim() && explanation.trim());
  const reasonPayload = current ? {
    expected_current_revision_id: current.revision_id,
    reason_code: reasonCode, explanation,
  } : null;
  const overrideReady = reasonReady && family !== "unknown_or_unresolved" &&
    components.length > 0 && components.every((row) =>
      row.componentKind !== "unknown_component" &&
      row.interpretation !== "unresolved" && row.explanation.trim());
  const updateComponent = (id: string, patch: Partial<ComponentDraft>) =>
    setComponents((rows) => rows.map((row) =>
      row.evidenceIdentity === id ? { ...row, ...patch } : row));

  return <section>
    <h2>M04 Evidence-Backed Classification</h2>
    <p>Classification is not parsing, ledger creation, reconciliation, tax, fixation, liquidity authority, calculation readiness, or M05 authorization.</p>
    {archived ? <p>Archived case: M04 is read-only.</p> : null}
    {loading ? <p>Loading M04 classification...</p> : null}
    {error ? <pre role="alert">{error}</pre> : null}
    <h3>Eligible and historical targets</h3>
    {targets.length ? <ul>{targets.map((row) => <li key={row.intake_id}>
      <button type="button" onClick={() => void loadTarget(row.intake_id)}>
        {row.target_kind === "manual_record_review" ? "Manual record" : "Uploaded source"} — {row.intake_id}
      </button>
    </li>)}</ul> : <p>No M03-eligible or historically classified targets.</p>}
    <label>Open historical target by M02 intake ID
      <input value={retainedId} onChange={(event) => setRetainedId(event.target.value)} />
    </label>
    <button type="button" disabled={!retainedId.trim()}
      onClick={() => void loadTarget(retainedId.trim())}>Open historical target</button>

    {target ? <section>
      <h3>Classification target</h3>
      <p>{target.target_kind === "manual_record_review"
        ? "Manual target — no external source/blob/checksum evidence."
        : `Uploaded target provenance: ${target.source_id ?? "unavailable"}`}</p>
      <p>Provider: {target.declared_provider_name ?? "unresolved"}; product: {target.product_name ?? "unresolved"}; type: {target.declared_product_type ?? "unresolved"}; code: {target.product_identifier ?? "unresolved"}.</p>
      <p>Original component facts: {target.declared_component_values.length
        ? JSON.stringify(target.declared_component_values) : "none"}</p>
      <p>M03: {target.m03_eligible ? "currently eligible" : `ineligible — ${target.m03_exclusion_reason}`}</p>
      <p>M05 gate: {target.eligibility.eligible_for_m05
        ? "technically eligible for a separately authorized M05 package"
        : `not eligible — ${target.eligibility.exclusion_reason}`}</p>

      <fieldset disabled={archived || submitting}>
        <legend>Lifecycle actions</legend>
        {!current ? <button type="button"
          onClick={() => void mutate(() => startM04(clientId, target.intake_id))}>
          Start classification
        </button> : null}
        {current?.state === "under_review" ? <>
          <button type="button" onClick={() => void runPreview()}>Preview exact rules</button>
          <button type="button" onClick={() => void mutate(() =>
            createM04Proposal(clientId, target.intake_id, current.revision_id))}>
            Create proposal
          </button>
        </> : null}
        <label>Reason code
          <input value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} />
        </label>
        <label>Explanation
          <textarea value={explanation} onChange={(event) => setExplanation(event.target.value)} />
        </label>
        {current?.state === "under_review" ? <button type="button" disabled={!reasonReady}
          onClick={() => reasonPayload && void mutate(() =>
            actOnM04(clientId, target.intake_id, "unresolved", reasonPayload))}>
          Mark unresolved
        </button> : null}
        {current?.state === "proposed" ? <>
          <button type="button" disabled={!reasonReady}
            onClick={() => reasonPayload && void mutate(() =>
              actOnM04(clientId, target.intake_id, "accept", reasonPayload))}>
            Accept proposal
          </button>
          <button type="button" disabled={!reasonReady}
            onClick={() => reasonPayload && void mutate(() =>
              actOnM04(clientId, target.intake_id, "reject", reasonPayload))}>
            Reject proposal
          </button>
        </> : null}
        {current && ["accepted", "unresolved", "rejected"].includes(current.state) &&
          !revalidationRequired ? <button type="button" disabled={!reasonReady}
            onClick={() => reasonPayload && void mutate(() =>
              actOnM04(clientId, target.intake_id, "reopen", reasonPayload))}>
            Reopen classification
          </button> : null}
        {current && revalidationRequired &&
          ["accepted", "unresolved", "rejected"].includes(current.state) ?
          <button type="button" disabled={!reasonReady}
          onClick={() => reasonPayload && void mutate(() =>
            actOnM04(clientId, target.intake_id, "start-revalidation", reasonPayload))}>
          Start revalidation
        </button> : null}

        {current && ["proposed", "accepted", "unresolved", "rejected"].includes(current.state) ? <section>
          <h4>Planner-authored override proposal</h4>
          <label>Product family
            <select value={family} onChange={(event) => setFamily(event.target.value as M04ProductFamily)}>
              {PRODUCT_FAMILIES.map((value) => <option key={value}>{value}</option>)}
            </select>
          </label>
          {components.map((row) => <fieldset key={row.evidenceIdentity}>
            <legend>{row.originalLabel ?? row.originalCode ?? row.evidenceIdentity}</legend>
            <label>Component kind
              <select value={row.componentKind} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { componentKind: event.target.value as M04ComponentKind })}>
                {COMPONENT_KINDS.map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
            <label>Interpretation
              <select value={row.interpretation} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { interpretation: event.target.value as M04ComponentInterpretation })}>
                {INTERPRETATIONS.map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
            <label>Component explanation
              <textarea value={row.explanation} onChange={(event) =>
                updateComponent(row.evidenceIdentity, { explanation: event.target.value })} />
            </label>
          </fieldset>)}
          <button type="button" disabled={!overrideReady || (revalidationRequired && !revalidationStarted)}
            onClick={() => reasonPayload && void mutate(() => overrideM04(
              clientId, target.intake_id, {
                ...reasonPayload, confirmed: true, product_family: family,
                pension_subtype: null, components: components.map((row) => ({
                  evidence_identity: row.evidenceIdentity,
                  component_kind: row.componentKind,
                  interpretation: row.interpretation,
                  current_employer_related: row.currentEmployerRelated,
                  explanation: row.explanation,
                })),
              }))}>
            Create override proposal
          </button>
        </section> : null}

        {current && ["proposed", "accepted", "unresolved", "rejected"].includes(current.state) ? <section>
          <h4>Undo as additive proposal</h4>
          <select aria-label="Historical revision for undo" value={historicalId}
            onChange={(event) => setHistoricalId(event.target.value)}>
            <option value="">Select prior revision</option>
            {history.filter((row) => row.revision_sequence < current.revision_sequence)
              .map((row) => <option key={row.revision_id} value={row.revision_id}>
                #{row.revision_sequence} {row.state}
              </option>)}
          </select>
          <button type="button" disabled={!reasonReady || !historicalId || revalidationRequired}
            onClick={() => reasonPayload && void mutate(() => undoM04(
              clientId, target.intake_id, {
                ...reasonPayload, confirmed: true, historical_revision_id: historicalId,
              }))}>
            Create undo proposal
          </button>
        </section> : null}
      </fieldset>

      {preview ? <section>
        <h4>Non-persisting exact-rule preview</h4>
        <p>Catalogue: {preview.catalogue_version}</p>
        <p>Family: {preview.product_family}</p>
        <p>Unresolved: {preview.unresolved_reasons.join(", ") || "none"}</p>
        <p>Conflicts: {preview.conflicts.join(", ") || "none"}</p>
      </section> : null}
      <h4>Current matched-rule evidence</h4>
      <ul>{rules.map((row, index) => <li key={String(row.rule_id ?? index)}>
        {String(row.rule_id ?? "unknown rule")} — {String(row.rationale ?? "no rationale")}
      </li>)}</ul>
      <h4>Immutable classification history</h4>
      <ol>{history.map((row) => <li key={row.revision_id}>
        #{row.revision_sequence} {row.action_type} → {row.state}; family {row.product_family ?? "none"}; interpretation {row.aggregate_interpretation ?? "none"}; catalogue {row.catalogue_version}
      </li>)}</ol>
    </section> : null}
    <p><Link to={`/clients/${clientId}`}>Back to M01 client case</Link></p>
  </section>;
}
