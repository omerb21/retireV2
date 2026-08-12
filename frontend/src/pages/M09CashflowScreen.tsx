import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useClientContextGeneration } from "../hooks/useClientContextGeneration";
import {
  M09_FAMILY, M09_VERSION, assessM09Inventory, executeM09Run, getM09Currentness,
  getM09Eligibility, getM09Run, listM09Runs, type M09ContractRequest, type M09Inventory,
  type M09Run, type M09RunSummary,
} from "../api/m09CashflowApi";
import { M09ScenarioSubjects } from "./M09ScenarioSubjects";

const errorMessage = (error: unknown) => error instanceof Error ? error.message : "M09 request failed";
const codes = (values: string[]) => values.length ? values.join(", ") : "none";

export function M09CashflowScreen() {
  const { clientId: raw } = useParams(); const location = useLocation();
  const clientId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const { captureClientContext, isCurrentClientContext } = useClientContextGeneration(clientId, location.key);
  const [startMonth, setStartMonth] = useState(""); const [endMonth, setEndMonth] = useState("");
  const [inventory, setInventory] = useState<M09Inventory | null>(null); const [run, setRun] = useState<M09Run | null>(null);
  const [history, setHistory] = useState<M09RunSummary[]>([]); const [error, setError] = useState<string | null>(null);
  const [busyCount, setBusyCount] = useState(0); const mounted = useRef(false); const epochs = useRef<Record<string, number>>({});
  const requestSequence = useRef(0); const activeLoading = useRef(new Set<number>());

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; activeLoading.current.clear(); }; }, []);
  useEffect(() => {
    epochs.current = {}; activeLoading.current.clear(); setBusyCount(0); setStartMonth(""); setEndMonth("");
    setInventory(null); setRun(null); setHistory([]); setError(null);
  }, [clientId, location.key]);

  const begin = () => { const id = ++requestSequence.current; activeLoading.current.add(id); setBusyCount(activeLoading.current.size); return id; };
  const finish = (id: number) => { if (activeLoading.current.delete(id) && mounted.current) setBusyCount(activeLoading.current.size); };
  const owner = (channel: string) => {
    const token = captureClientContext(); const epoch = (epochs.current[channel] ?? 0) + 1; epochs.current[channel] = epoch;
    return () => mounted.current && epochs.current[channel] === epoch && isCurrentClientContext(token);
  };
  const payload = (): M09ContractRequest => ({ scenario_family: M09_FAMILY, scenario_contract_version: M09_VERSION, start_month: startMonth, end_month: endMonth });

  const loadHistory = useCallback(async () => {
    if (clientId === null) return; const owns = owner("history"); const loading = begin();
    try { const next = await listM09Runs(clientId); if (owns()) setHistory(next); }
    catch (cause) { if (owns()) setError(errorMessage(cause)); } finally { finish(loading); }
  // owner/begin/finish deliberately use refs and stable generation callbacks.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureClientContext, clientId, isCurrentClientContext]);
  useEffect(() => { void loadHistory(); }, [loadHistory]);

  const assess = async () => {
    if (clientId === null) return; const owns = owner("inventory"); const loading = begin(); setError(null);
    try { const next = await assessM09Inventory(clientId, payload()); if (owns()) { setInventory(next); setRun(null); } }
    catch (cause) { if (owns()) setError(errorMessage(cause)); } finally { finish(loading); }
  };
  const execute = async () => {
    if (clientId === null) return; const owns = owner("execute"); const loading = begin(); setError(null);
    try { const next = await executeM09Run(clientId, payload()); if (owns()) { setRun(next); setInventory(next.inventory); await loadHistory(); } }
    catch (cause) { if (owns()) setError(errorMessage(cause)); } finally { finish(loading); }
  };
  const loadRun = async (runId: string) => {
    if (clientId === null) return; const owns = owner("result"); const loading = begin(); setError(null);
    try {
      const [next, currentness, eligibility] = await Promise.all([getM09Run(clientId, runId), getM09Currentness(clientId, runId), getM09Eligibility(clientId, runId)]);
      if (owns()) { setRun({ ...next, currentness, m10_eligibility: eligibility }); setInventory(next.inventory); }
    } catch (cause) { if (owns()) setError(errorMessage(cause)); } finally { finish(loading); }
  };

  if (clientId === null) return <p role="alert">Invalid client ID.</p>;
  const horizonValid = /^\d{4}-(0[1-9]|1[0-2])$/.test(startMonth) && /^\d{4}-(0[1-9]|1[0-2])$/.test(endMonth) && endMonth >= startMonth;
  return <main><h2>M09 Deterministic monthly cashflow</h2>
    <p>Orchestration and exact aggregation only. This is not professional, tax, calculation-readiness, recommendation, or M10 authority.</p>
    <p><Link to={`/clients/${clientId}`}>Back to client</Link></p>
    {error ? <p role="alert">{error}</p> : null}{busyCount ? <p>Loading M09 evidence…</p> : null}
    <section><h3>Explicit full-month horizon</h3>
      <label>Start month <input aria-label="Start month" type="month" value={startMonth} onChange={(event) => setStartMonth(event.target.value)} /></label>
      <label>End month <input aria-label="End month" type="month" value={endMonth} onChange={(event) => setEndMonth(event.target.value)} /></label>
      <button type="button" disabled={!horizonValid || busyCount > 0} onClick={() => void assess()}>Assess server inventory</button>
      <button type="button" disabled={!horizonValid || busyCount > 0} onClick={() => void execute()}>Execute complete inventory</button>
      <p>Family: {M09_FAMILY}/{M09_VERSION}. The server owns all component inclusion, exclusion and none evidence.</p>
    </section>
    {inventory ? <section><h3>Server-resolved component inventory</h3><p>Complete: {String(inventory.complete)}; blockers: {codes(inventory.blocker_codes)}.</p>
      <ul>{inventory.domains.map((domain, index) => <li key={`${String(domain.domain ?? "domain")}-${index}`}><strong>{String(domain.domain ?? "domain")}</strong><pre>{JSON.stringify(domain, null, 2)}</pre></li>)}</ul>
      <p>Fingerprint: {inventory.inventory_fingerprint}</p></section> : null}
    {run ? <section><h3>Saved run result</h3><p>Run {run.run_sequence}: {run.status}; blockers: {codes(run.blocker_codes)}.</p>
      <p>Current: {String(run.currentness.is_current)} ({codes(run.currentness.reason_codes)}). M10 technical eligibility only: {String(run.m10_eligibility.eligible_for_m10)} ({codes(run.m10_eligibility.reason_codes)}).</p>
      {run.monthly_results.length ? <table><thead><tr><th>Month</th><th>Inflows (ILS)</th><th>Outflows (ILS)</th><th>Net (ILS)</th></tr></thead><tbody>{run.monthly_results.map((row) => <tr key={row.monthly_result_id}><td>{row.month}</td><td>{row.gross_inflow_total}</td><td>{row.gross_outflow_total}</td><td>{row.period_net}</td></tr>)}</tbody></table> : <p>No authoritative monthly result rows.</p>}
      {run.range_totals ? <p>Range totals: inflows {run.range_totals.gross_inflow_total}; outflows {run.range_totals.gross_outflow_total}; net {run.range_totals.period_net}.</p> : null}
      <details><summary>Immutable assumption and upstream evidence</summary><pre>{JSON.stringify({ assumption_manifest: run.assumption_manifest, upstream_snapshot: run.upstream_snapshot }, null, 2)}</pre></details>
    </section> : null}
    <section><h3>Saved immutable runs</h3>{history.length ? <ol>{history.map((item) => <li key={item.run_id}><button type="button" onClick={() => void loadRun(item.run_id)}>Load run {item.run_sequence}</button> — {item.status}; {item.start_month}–{item.end_month}; current {String(item.is_current)}</li>)}</ol> : <p>No saved M09 runs.</p>}</section>
    <M09ScenarioSubjects clientId={clientId} />
  </main>;
}
