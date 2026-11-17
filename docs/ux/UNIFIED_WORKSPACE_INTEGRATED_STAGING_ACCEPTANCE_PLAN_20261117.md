# RETIRE V2 | PKG-01/02/03 + CAS | Integrated Staging Acceptance Plan

**Directive:** 198 | **Status:** PLAN ONLY / NOT AUTHORIZED FOR MERGE, MIGRATION, TEST EXECUTION OR DEPLOYMENT  
**Date:** 2026-11-17  
**Reference implementation HEAD:** `81cc82fd4800b078353ff46663ab78fb2f53156a`  
**Reference branch:** `feat/pkg03-scenario-readiness-20261117`  
**PR #7:** Draft, unchanged.

## A. What is already accepted versus what is still missing

PKG-01 (unified workspace), PKG-02 (supplementary factual editors and atomic PostgreSQL CAS), and PKG-03 (read-only admission evidence) have independent isolated technical acceptances. None establishes that the combined revision works with Railway Staging's real auth, schema, deployment routing and retained records. Staging health checks alone do not prove application-level professional workflow.

- PKG-01 reference SHA: `c623577b76317009e2262c5b7fc23d1fe19c66b7` (prior accepted unified workspace baseline).
- PKG-02 editor reference SHA: `2c2eb2ce0269f46310bc6a731d0baad902530b64`; acceptance documented in `UNIFIED_WORKSPACE_PKG02_ACCEPTANCE_20261117.md`.
- PKG-02 CAS/test accepted SHA: `c2c44bed48267fa56cf8d41f19686cee1bfc810d`, followed by documentary base `e824bb2bdf629de64e15d48b5d65f79a23e06066` (branch `fix/pkg02-dependency-cas-20261116`).
- PKG-03 accepted SHA: `81cc82fd4800b078353ff46663ab78fb2f53156a`, branching *directly from* `e824bb2bdf629de64e15d48b5d65f79a23e06066`; `UNIFIED_WORKSPACE_PKG03_ACCEPTANCE_20261117.md`.

**Integration ordering:** `c623577b` (PKG-01) -> `2c2eb2ce` (PKG-02 editors) -> `c2c44bed` (CAS) -> `e824bb2b` (documentation base) -> `81cc82fd` (PKG-03). This is already an ancestry chain in the current proposed candidate. Do not independently merge all four historical branches, duplicate commits or cherry-pick their patches on top of one another.

**Candidate selection / no-loss check for a future authorized integration task:**
1. Record hashes of current candidate, target Staging code/branch, PR #7 head/base, and actual Staging deployment SHA. Verify repository and a clean integration branch before any changes.
2. Check `git merge-base --is-ancestor` for each accepted commit and the candidate; inspect `git log --ancestry-path`, diff/stat and file lists rather than relying on branch names. Confirm both UI editors and CAS migration are present in candidate.
3. Compare target Staging baseline to candidate with a three-way diff and detect divergent commits before defining a safe fast-forward/merge strategy. If divergence exists, stop for conflict review; never force push, reset or implicitly overwrite.
4. Only under a *new* supervisor directive create an integration candidate/ref pinned to an approved SHA. Merge/rebase/cherry-pick, if actually needed, must be specifically authorized and independently compared against the reference candidate and Stage 6/fixation gates.
5. After approved integration, check a single build SHA across frontend image, backend image, DB migration inventory and deployed environment. Do not silently mix backend from one SHA with frontend from another.

## B. Phase 0 - read-only staging preflight (separate future authorization)

**Inputs:** named Railway Staging service/environment, verified Staging URL, running git SHA/image digests, read-only DB schema introspection privilege, backup/restore ownership, approved acceptance tester, test scope and session. Never use Production credentials or data.

- Confirm environment identity and network routing: the browser, API, session middleware and DB must all target only Staging. Confirm internal-only access, TLS/cookies, tenant/actor scoping and no unexpected Stage 6 capability escalation.
- Inspect Staging migration/version state *read-only*: `alembic_version`, full migration dependency chain, presence/types/defaults/check constraints of `version` columns in `actual_capitalizations`, `capital_asset`, `recurring_income`, `recurring_expense`; relevant FKs, indexes, grants, row counts and non-null/positive-version characteristics. Compare against migration file `backend/alembic/versions/c194e2f0a816_pkg02_atomic_fact_versions.py`, revision `c194e2f0a816`, parent `b2d7e4c9f108`.
- Verify read-only whether Staging is at that parent, has additional migration descendants, preexisting version columns, partially applied schema changes or drift, and whether read/write application role has only required permissions. A mismatch, absent prerequisite, unexpected additional head, irreversible drift or inability to verify schema is **STOP / ESCALATE**.
- Capture pre-migration backup identifier, recovery point, encryption/access retention, restore drill evidence, migration duration/lock estimates, maintenance window and owners. Read-only checks do **not** execute `alembic upgrade`, ALTER, backfill, transactions containing writes or any data cleanup.
- Confirm specific idempotency/retry limitations, DDL locking impacts, rollback feasibility and application backward/forward compatibility. Do **not** assume Alembic `downgrade` is a safe production rollback; restore or separately authorized forward-fix may be necessary.

**Gate:** signed Staging schema compatibility report and deployment/migration runbook approved by supervisor; otherwise no migration or deploy.

## C. Phase 1 - authorized staging migration and deployment (future, not this directive)

These steps are a proposed order only, not authority to execute:

1. Set a change window, stop concurrent schema writers and take/verify a recoverable pre-change database snapshot. Assign change owner and abort criteria.
2. Ensure the approved candidate is reproducibly built and its deployment artifact SHA matches the vetted source. Confirm rollback-ready prior image and version compatibility matrix.
3. Execute **only** the supervisor-approved Staging CAS migration via migration-role credentials, with transaction/lock monitoring, bounded timeout and exact Alembic target. Preserve historical rows and monetary amounts; confirm positive versions, defaults and constraints after applying. Stop immediately on drift or partial failure. Never promote migration privileges to the normal app role.
4. Bring the approved frontend/backend candidate online using a controlled, reversible rollout; verify routing to the migrated *Staging* DB, active SHA, auth and CSRF. A green health check is necessary but **not sufficient**.
5. If schema-compatible rollout, mandatory post-deploy integrity checks and functional acceptance do not pass, freeze further changes, capture evidence, and use the pre-approved recovery route. Do not improvise a DB downgrade.

No new Stage 6 calculation/permission enablement is included in a Staging rollout. Do not change production in this phase.

## D. Phase 2 - authenticated integrated browser acceptance, synthetic clients only

Run with a real Staging backend, Staging PostgreSQL and a genuine authenticated internal planner session. The only test records used or modified must be **new synthetic Staging clients**, marked clearly and uniquely (two clients A/B), not real clients or Production copies. Verify identity and isolation by server reads and protected API calls, not by mocks. Preserve audit and evidence traces. Avoid irreversible professional actions, tax submissions, payouts and financial engine calls.

| Step | Workflow and assertions | Gate / evidence |
|---|---|---|
| 1. Case entry (PKG-01) | Create/open synthetic A and B; client header, ID, route, session, correct case; A-B-A navigation must never show stale client A data during B. Verify 401/403 behavior against real server as appropriate. | Screenshot, request IDs, HTTP traces, client IDs; no cross-client leakage |
| 2. Canonical pension portfolio (PKG-01) | Real saved synthetic pension product and component balances with legitimate source input; grid, product count, selection, search, correction, version conflict and reload. Verify unchanged untouched components and canonical source history. | Before/after server values, versioned write evidence, no conversion API from scenario planning |
| 3. Supplementary facts (PKG-02) | On synthetic clients create/read/edit/remove permissible capitalization; create/read/edit assets, incomes, expenses; verify frequency/amount basis and no cross-client reads. Ensure conversion-derived capital rows are not silently edited as ordinary facts. | Actual DB-backed persistence, no unrelated source monetary change |
| 4. CAS (PKG-02) | With two authenticated Staging sessions or controlled concurrent writes, verify `expected_version`, exactly one winning write, stale 409 `RECORD_VERSION_CONFLICT`, 404 on cross-client/unknown, retained unsaved editor content, nonnegative versions and preserved financial fields. Cover capitalization DELETE conflict if authorized for synthetic data. | Real PostgreSQL atomicity, not a GET-before-PUT mock; explicit DB verification |
| 5. Scenario planning (existing + PKG-01) | Create two server-saved drafts, select, rename, add planned allocations, change scenarios, navigate planning -> results -> planning; check versioned writes, saved identity, and no POST `canonical-conversions` from hypothetical decisions. Do not treat planned sums as paid pension/cash. | Saved draft version and client scope; evidence of no factual balance mutation |
| 6. Admission presentation (PKG-03) | For selected A/B scenarios verify true server `scenario_id/client_id/version`, `assessment_state=blocked`, `financial_result=null`, blockers including `SCENARIO_EMPTY` or other actual codes. A real source change should yield `SOURCE_STALE` when contract permits; refresh is GET-only. Test 404/409, denied session, failed network and stale responses with controlled requests, marking injections separately from true backend enforcement. | No positive readiness, no M09 archive or synthetic calculated value shown, traceability to current exact saved draft |
| 7. Results boundary and return | Results stage distinguishes draft allocations from financial output; Stage 6 capability remains denied unless independently allowed by its existing environment gate, never bypassed via PKG-03. Return to planning retains chosen scenario and unsaved fact editor navigation guard. | Screenshots, requested endpoints, before/after persisted records |
| 8. Retained legacy workflows | Smoke only directly affected old client/pension/scenario/supplement routes and report historical surfaces, with no writes outside test scope; validate no regression introduced by combining feature paths. | Focused route evidence, not a full historic test rerun |

**Use a scoped matrix, not fake PASS:** run unit/build checks changed by actual integration and focused Playwright on the real server. Previously accepted standalone suites are not repeated unless combination introduces relevant behavior changes. Record which browser tests are true Staging end-to-end, which inject network/response failures, and which remain only component-mock proof. Explicitly record skipped/unavailable checks.

**Mandatory artifacts:** code SHA and image digest, schema fingerprint/migration version before/after (when separately authorized), synthetic client IDs and cleanup plan, backend/DB/browser logs sanitized of sensitive data, timestamps and HTTP request identifiers, per-step screenshots, Playwright JUnit/results, changed rows/version evidence and test-run URL. The test operator must independently review failed/skipped tests and unexpected writes. Log a separate cleanup of only synthetic clients under an authorized cleanup procedure.

**Stop conditions:** wrong environment, failed auth boundary, client leakage, unknown migration state, schema drift, contradictory financial authority, lost fact data, changed original balances from scenario edit, CAS lost update, historical M09 treated as current, status falsely green after 404/409, unapproved deployment artifact or unverified rollback.

## E. Recovery and safety plan (to approve before any Staging change)

- **Before rollout:** record immutable prior app image(s), DB snapshot/point-in-time-recovery markers, schema version, restore access and verified restore procedure, service routing and feature flags. Restore rehearsal should use a *separate disposable or authorized isolated recovery environment*, not Production.
- **Failure before migration:** do not deploy; leave Staging unchanged and retain diagnosis.
- **Failure during migration:** stop migration, check transaction/DDL outcome and `alembic_version` with database owner; do not retry blindly. Decide between preapproved restore and forward repair only after evidence review.
- **Failure after migration:** revert app image only if backward compatibility with new schema has been explicitly demonstrated; otherwise use approved coordinated restore of matching app+DB or an authorized forward fix. Avoid discarding other Staging activity without an agreed recovery-point and data-loss assessment.
- **Verification after recovery:** schema/version, service image, synthetic row integrity, authentication, scenario read, and safe health check; incident record and new supervisor decision required to retry.

## F. Four explicit open release gates

| Gate | Current state | Required independent closure | Consequence while open |
|---|---|---|---|
| `FIXATION-CURRENTNESS-001` | OPEN, see `FIXATION_CURRENTNESS_001_20261117.md` | Inventory history/detail/reuse/report/judgment consumers and consequential actions; define authoritative *server-reconstructed* current-context and saved manifest comparison, fail-closed on changed/unknown/legacy; protect against TOCTOU; test historical viewing separately from professionally relied-upon saved result with real PG16 and browser. | Saved fixation result is historical evidence, not certified current for professional reliance |
| `STAGING-ACCEPTANCE` | NOT PERFORMED | Run all scoped integrated browser steps above against actual approved Staging build + authentic server, compare actual persistence, auth, source and selected scenario version; require supervisor review of artifacts, not health-only. | No integrated deployment acceptance or production promotion |
| `CAS-MIGRATION` | Tested only on disposable synthetic PG16; not applied to Staging | Read-only Staging schema/drift preflight; approved backup and restore plan; separately authorized migration; post-migration Alembic + four-table schema and data/version integrity checks and concurrent-write 409 on live Staging PG16. | Cannot assume Staging supports atomic editors |
| `FINANCIAL-CALCULATION-AUTHORITY` | NOT AUTHORIZED | Separate professional product decision on supported sources, annuity coefficients, tax/exemption assumptions, input/output contracts, environment permissions, currentness and Stage 6 admission; real calculation correctness, negative and permission tests and explicit acceptance. | No new monetary scenario comparison or implied approval from PKG-03 |

**Other UX/deployment check:** the stage 3 note `PKG02-CONCURRENCY-001` still describes preflight-only protection despite CAS implementation. Verify the displayed statement during Staging review, log it as a wording discrepancy, and request explicit code-change authorization before amending it. Do not represent the note as accurate CAS documentation.

## G. Recommended authorized execution order

1. Supervisor approves this plan and names Staging topology, test owner, approved SHA, rollback owner and a read-only inspection scope.
2. Perform **read-only** identity, migration-state, schema-drift and recovery preflight. Decision gate before any mutation.
3. Authorize one pinned integration candidate only if a divergence or missing commit is discovered; otherwise treat the accepted `81cc82fd` ancestry as the reference and validate its compatibility with the actual target.
4. Under a distinct change authorization, prepare backup, apply the controlled CAS migration to Staging, verify schema and then deploy the pinned compatible app revision (or use a separately approved migration/deploy sequence where compatibility dictates).
5. Execute focused five-stage live functional acceptance with two synthetic clients, capture JUnit/browser/API/DB evidence, inspect all failed/skipped checks and validate recovery readiness.
6. Supervisor independently decides Staging acceptance. Keep fixation currentness and financial authority separate, blocking any consequential Production or financial-use approval until closed.

**Directive 198 performed documentation only.** This plan is not approval to create an integration branch, merge, run tests, migrate, deploy, toggle Stage 6 or alter PR #7, Staging or Production.
