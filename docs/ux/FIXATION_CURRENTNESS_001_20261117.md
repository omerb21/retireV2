# FIXATION-CURRENTNESS-001 | Saved fixation run professional currentness

## Owner decision 261 (2026-11-19): personal-workspace documentation boundary

RETIRE V2 is a single-planner professional tool, not a multi-approver SaaS.
The saved-run `internal-planner-judgment` statuses are **documentation only**.
Specifically, `internal_action_identified` records an identified possible action;
it is neither permission to execute that action nor a certificate that the
historical fixation result is current. The planner may document a run whose
freshness is `legacy`, `changed`, or `unknown`. A saved note does not modify
run freshness, authorize an operation, or make an old result a recalculation.
Client/run ownership and uniqueness of the note still apply.

This decision resolves the ambiguity about the judgment POST. It does **not**
declare the broader fixation currentness mechanism complete: current calculations
must still distinguish historical results from newly calculated results and
surface known source changes. Technical integrity, required calculation inputs,
client isolation, and lost-update protection remain in force. Do not introduce
self-approval workflow gates for this single professional user.

**Status: OPEN / NOT VERIFIED**  
**Assessment:** code-only review under directive 196, at accepted implementation SHA `c2c44bed48267fa56cf8d41f19686cee1bfc810d`.  
**Scope:** consumer-side and server-side professional currentness of an already persisted fixation run. This is separate from PKG-02 and its accepted CAS implementation. No code remediation or new tests authorized here.

## Precisely established capability

- `POST /api/clients/{client_id}/fixation/runs/{run_id}/dependency-comparison` in `backend/app/api/fixation_routes.py` retrieves the saved manifest and compares it against `payload.current_context` after admission.
- The API returns technical states such as `changed`, `unchanged`, and `unknown`, with per-dependency field identities. It does **not** independently rebuild the full current professional context from authoritative client database sources. Its contract explicitly does **not** certify professional approval or automatically change a saved run's status.
- Directive 195 proved a saved run with a valid manifest changes from `unchanged` to `changed` when a capitalization amount in supplied current context is updated from the synthetic database amount. The changed field was `capitalization:cap-1.amount`.
- There is a distinct `GET /api/clients/{client_id}/fixation/runs/{run_id}/dependency-manifest` endpoint to inspect historical manifest evidence. That inspection alone is not a currentness check.

## Code-based consumption map

| Surface | Reads or action | Currentness check found before action? | Risk boundary |
|---|---|---|---|
| `frontend/src/pages/RunHistoryScreen.tsx` | `getFixationHistory(clientId)`; marks latest *successful* run by history status; links to detail | **NO** `dependency-comparison` invocation found | `success` or `latest` is historical metadata, not source-currentness |
| `frontend/src/pages/RunDetailScreen.tsx` | `getFixationRunDetail(clientId,runId)` and history; presents result monetary/tax figures and run status | **NO** comparison invocation found | Historical figures can be viewed without an accompanying verified-as-current indication |
| `frontend/src/pages/CalculationResultScreen.tsx` | Reopens latest successful saved run with `getFixationHistory` plus `getFixationRunDetail`; displays `ResultPresentation`, including exemption/capitalization amounts | **NO** comparison invocation found for reopening | May be interpreted as usable current result although the displayed run is historical |
| `frontend/src/pages/FixationWorkspaceScreen.tsx` | Reads history, displays latest run status/date, links to history and input | **NO** comparison invocation found | Summary may suggest successful/current activity, but does not validate current facts |
| `backend/app/api/fixation_routes.py`: history, latest, saved run detail | Return persisted historical run status, result and snapshots | **NO** mandatory comparison before historical GET | Read APIs faithfully return historical evidence, not a current professional certification |
| `backend/app/api/fixation_routes.py`: `/internal-planner-judgment` | Creates planner judgment associated with a saved run | **NOT VERIFIED** as currentness gate; no automatic comparison visible in the route | Potential consequential professional action; requires end-to-end service review before claiming blocked/allowed |

**Important:** preserving viewable historical records is legitimate. The finding is about the absence of a proven, mandatory **current-context certification gate before professional reliance**, not a requirement to hide history or invalidate all old calculations.

## Current-context authority and professional use

- Caller passes `current_context`, `current_input_contract_version`, and `current_result_contract_version`. Backend parses/admit-checks the supplied context and compares it with the historical manifest.
- No proof was found that the comparison endpoint reconstructs all current capitalization, grant, source-evidence and accepted-decision facts exclusively from the authoritative database. Validation of supplied context is not the same as independent authoritative re-fetch.
- A frontend cannot conclude that a saved result remains current solely from `run.status == success`, latest-run selection, or equality of historical hashes.
- A stored result may continue to be shown for audit/history. Any proposed professional use, approval, report/export, or downstream recommendation based on its *current* correctness requires a separately defined and enforced gate.

## Proposed next-review questions (no implementation authority)

1. Which consumers permit professional actions beyond viewing history, including `internal-planner-judgment`, reporting, export, reuse, or final 161D-related work? Identify their exact contract and whether they accept a saved run ID.
2. Which authoritative DB data and professional admissions must be reconstructed on the server to determine currentness? A historical input snapshot or browser-submitted context is insufficient by itself.
3. What should `changed`, `unknown`, legacy-manifest-unavailable and incomplete authoritative source cases do to professional actions? Define fail-closed rules separately from historical display.
4. What response/currentness proof (including server timestamp and version/fingerprints) should accompany the result to avoid a time-of-check/time-of-use race?
5. How will currentness checks preserve immutable historical evidence, professional audit traces and legitimately superseded results?

## Classification

| Claim | Status |
|---|---|
| A valid saved manifest detects a changed capitalization in admitted comparison context | **PASS**, directive 195 synthetic PG16 |
| `dependency-comparison` independently fetches authoritative current facts | **NOT VERIFIED; code shows caller-supplied context** |
| All screens and downstream professional actions enforce freshness | **NOT VERIFIED** |
| A saved historical result may be read as a historical record | **NOT APPLICABLE** as an automatic professional-validity claim |
| Actual financial/tax calculation correctness following the change | **NOT TESTED**; outside this scope |

**Decision:** preserve as a separate open finding. No product code, schema, financial formula, UI behavior, merge or deploy changes were made by directive 196.
