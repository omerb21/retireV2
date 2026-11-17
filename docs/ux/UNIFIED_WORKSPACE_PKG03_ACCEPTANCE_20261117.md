# RETIRE V2 | Unified Workspace PKG-03 | Isolated Technical Acceptance

**Directive:** 198 (documentation and planning only)  
**Supervisor decision:** PKG-03 technically accepted in an isolated environment on 2026-11-17.  
**Accepted implementation HEAD:** `81cc82fd4800b078353ff46663ab78fb2f53156a`  
**Implementation branch:** `feat/pkg03-scenario-readiness-20261117`  
**Implementation parent/base:** `e824bb2bdf629de64e15d48b5d65f79a23e06066`, on `fix/pkg02-dependency-cas-20261116`.  
**PR #7:** Draft, unchanged. **Staging / Production:** neither accepted nor modified.

## 1. Scope accepted

- Typed, client- and scenario-scoped GET of the existing `/api/clients/{client_id}/scenario-drafts/{scenario_id}/calculation-admission` endpoint, with strict response-shape and identity validation.
- Selected saved scenario name, server scenario ID, revision and draft status in both unified workspace stage 4 (planning) and stage 5 (results).
- Read-only rendering of server calculation-admission assessment and blocker codes/decision references, including `SOURCE_STALE` as a signal requiring reinspection.
- Explicit boundary between draft allocations, stored decisions, and a *financial calculation result*. No synthetic cashflow, tax, pension, 161D, M09 or M10 outputs.
- Per-selection fetch and read-only refresh with AbortController and epoch/identity checks for client, scenario, version and A-B-A transitions. Failed, unknown, mismatched or obsolete responses never confer approval.
- Existing Stage 6 capability check remains independent; no additional execution permissions, new financial engine, factual balance mutation, backend/model/migration change, or legacy-route removal.

**API evidence contract:** `SCENARIO_CALCULATION_ADMISSION_V1` returns `client_id`, `scenario_id`, `scenario_version`, `assessment_state="blocked"`, `financial_result=null`, and `blockers[{code,decision_id}]`. This is a read-only database snapshot assessment, not a profession-wide readiness certificate, cross-request freshness lease, positive authorization, or approved financial result. No server-owned time/fingerprint certification of comprehensive future currentness is claimed. Client guards require the exact identity and version of the selected saved scenario. A version mismatch is shown as unavailable.

## 2. Exact five-file implementation diff

Compared `e824bb2bdf629de64e15d48b5d65f79a23e06066` to accepted `81cc82fd4800b078353ff46663ab78fb2f53156a`; only these paths changed:

1. `frontend/src/api/scenarioDraftsApi.ts`: typed read-only evidence fetch; strict contract validation; `GET`, `no-store`, cancellation.
2. `frontend/src/components/ScenarioDraftPanel.tsx`: bounded readiness display in existing planning/results, scoped race/error handling and read-only refresh.
3. `frontend/src/components/ScenarioDraftPanel.workflow.test.tsx`: focused component tests of blocked/stale/errors, revisions and A-B-A isolation alongside existing workflow behavior.
4. `frontend/e2e/pkg03-readiness.spec.ts` (new): synthetic localhost Chromium acceptance against real backend and PostgreSQL 16.
5. `.github/workflows/retire-v2-pkg03-readiness.yml` (new): isolated CI orchestration, scope guard, unit/build/browser checks and retained evidence.

No change to `RetirementWorkspaceScreen.tsx` was required. No backend, Alembic, calculation, fixation, permission or persistence-code edits were made.

## 3. Evidence and acceptance result

**Final green run:** [GitHub Actions #44046568891](https://github.com/omerb21/retireV2/actions/runs/44046568891)  
**Exact run HEAD:** `81cc82fd4800b078353ff46663ab78fb2f53156a`  
**Evidence:** [retire-v2-pkg03-44046568891 artifact](https://github.com/omerb21/retireV2/actions/runs/44046568891/artifacts/14311542860) (JUnit, unit/build/browser logs, isolated backend logs and browser screenshots; artifact retention applies).

| Check | Observed result | Evidence boundary |
|---|---|---|
| Scoped workflow and disposable PG16 setup | PASS | No Staging resource or live production DB |
| `ScenarioDraftPanel.workflow.test.tsx` | **16 passed / 16** | jsdom/Vitest; mocked draft/admission/capability APIs and child components |
| TypeScript and Vite production build | **PASS** | Build correctness, not live deployment acceptance |
| `pkg03-readiness.spec.ts` | **1 passed / 1** | Chromium, localhost Vite + real backend + isolated PostgreSQL 16 |
| Browser verified saved scenario | PASS in one synthetic case | Create through actual API; render identity and revision in stage 4; show `blocked` and `SCENARIO_EMPTY` |
| Browser verified results stage | PASS in one synthetic case | Stage 5 shows blocked assessment and absence of an authorized financial result |
| Admission GET / no write | PASS in synthetic case | Observed `GET` methods, explicit read-only refresh, unchanged saved draft before/after |
| Server response and 404 | PASS in synthetic case | Real PG16 server contract, `financial_result=null`, 404 for missing scenario and cross-client mismatch |

**Do not overstate mock evidence:** the 16 Vitest tests cover conditional frontend behavior, including injected HTTP-409-style errors, stale-source evidence, revision mismatch, and client A-B-A races. They **do not** establish real backend 409 handling, server-side access control or real concurrent transaction behavior. The one Playwright test exercises a genuine backed-by-PG16 endpoint and checks selected paths; it is not a full real-server matrix of all 16 unit scenarios. Server-level CAS authorization and concurrency evidence belongs to the separately accepted PKG-02 synthetic tests.

The first PKG-03 CI attempt failed on an escaped-newline TypeScript syntax error and intermediate runs were cancelled while the branch was updated. The final accepted run above was green; do not aggregate prior runs as green.

## 4. Not verified end-to-end by PKG-03

- A real existing sourced scenario transitioning from current source to `SOURCE_STALE` after a factual write, followed by browser refresh, across all service boundaries.
- Network failure, 401/403, 409, response-shape corruption, in-flight A-B-A, stale version and every selection race against the real Staging backend: covered in part by component mocks, **not** fully by real PG16 browser tests.
- Real authenticated Staging tenancy, session expiry, browser cross-client navigation and unsaved-editor preservation across the full five-stage path.
- Stage 6 financial authorization, positive readiness, sanctioned producer output, M09 archive exclusion across every consumer, genuine financial comparison, or any pension/tax calculation.
- PKG-01, PKG-02 and PKG-03 integrated live-browser acceptance with Staging's actual database state, CAS schema migration and deployment topology.
- Independent server-authoritative currentness and mandatory professional gate for persisted fixation runs: `FIXATION-CURRENTNESS-001` remains OPEN.

## 5. Acceptance limits and release decision

**PKG-03 isolated technical acceptance: PASS / CLOSED by supervisor under directive 198.**  
**Staging integrated functional acceptance: NOT PERFORMED.**  
**Staging CAS migration: NOT PERFORMED.**  
**Production deployment or professional financial-use authorization: NOT GRANTED.**

Draft statuses and admission blocker evidence never imply a positive financial execution authority. Staging deployment, PR merge, any migration and professional reliance each require separate supervisor authorization and evidence. No product change or tests were run by directive 198.
