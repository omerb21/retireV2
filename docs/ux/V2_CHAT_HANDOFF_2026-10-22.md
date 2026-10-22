# RETIRE V2 — Chat Handoff and Exact Technical State — 2026-10-22

**Purpose:** Allow a new ChatGPT conversation to continue development without restarting discovery, losing professional UX decisions, repeating CI, or confusing tested vs untested milestones.

**MANDATORY FIRST READ:** [Development Management Playbook](./V2_DEVELOPMENT_MANAGEMENT_PLAYBOOK.md). Also read [Professional Workspace Integration](./PROFESSIONAL_WORKSPACE_INTEGRATION.md) and [Scenario Engine Integration Gate](./SCENARIO_ENGINE_INTEGRATION_GATE.md). Governing protocol: RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1; documentation here is a handoff, not additional authorization.

## A. Active repository and branch (verified October 22)

- Main V2 repo: `omerb21/retireV2`. Historic V1 comparison repo: `omerb21/retire` (separate).
- Active development branch: `feature/professional-workspace-ux-first-20261022`.
- Branch base `master`: `6f3d523e9c81b55da045ac3c85e747104821d5da` (last checked). No master merge/deploy.
- Last code-implementation HEAD before documentation: `6dff74258e37d450cdb880e32b89988d74aa04e1`. The current branch HEAD will have advanced after this handoff doc is committed: **always read actual GitHub branch HEAD before editing**.
- Previous experimental branch `prototype/v2-professional-workspace-shell` is superseded: polished visually but failed professional user acceptance (excessive client detail, duplicate product editors, confusing conversions). Do not merge it.
- Current branch was deliberately forked from master, not from failed prototype.
- Owner-approved standalone full-workflow UX prototype: `V2_Full_Retirement_Workflow_Prototype.html`, generated as a chat artifact. Owner: looks “excellent”; correct appearance and logic; cannot certify real professional usability without real persisted scenarios. Keep this distinction.
- Five workflow phases: (1) client/case (2) canonical pension ledger (3) supplementary facts (4) independent scenarios with pension/capital decisions (5) comparison and reports.
- A handoff package and UX prototype are also supplied as conversation downloadable artifacts; if unavailable in a new chat, use the playbook and new React implementation as the durable description and ask user for the HTML only if visual comparison is truly necessary.

## B. Exact last user feedback and product direction

The user is a professional retirement planner with about 20 years' experience and is **not a developer**. They are NOT asking to visually clone V1. They welcome a superior workflow. Initial V2 technical screens were rejected because they exposed large amounts of tracking/provenance/status data irrelevant during a planning session, with endless scrolling and repeated details below ledger. At V1, select balances within a table and choose an action. Proper conversion means allocating a selected balance to a **pension** or a **capital asset**; it is not moving money to a different classification column. V1 scenario conversion altered actual holdings and required snapshot/restore; that behavior must NOT recur.

The full interactive synthetic journey UX was approved as a design direction, not as financial correctness or a fully working product. Owner asked us to proceed to real V2 implementation, retaining strict controls on calculations and data authority.

## C. Implemented in current branch (not in master)

- `frontend/src/pages/RetirementWorkspaceScreen.tsx` + CSS: real authenticated client route `/clients/:clientId/workspace`; reads `getClient` and `listPensionProducts` from the current V2 API; explicit data/client-bound guards; compact navigation and ONE ledger.
- Client list link in `ClientListScreen.tsx` opens the new workspace; existing ClientDetail and PensionProducts routes stay intact.
- `App.tsx` routes the workspace without redundant old global nav.
- Portfolio row-per-product, actual component columns, search, hide-empty-columns, discrepancy filter, cell selection; no writes from selections/filters.
- Factual correction of several components in ONE product via ONE `savePensionProduct` PUT with `expected_version`. Errors keep draft. Stage navigation does not drop unsaved draft. No fake conversion of classification correction into pension/capital decision.
- `RetirementWorkspaceScreen.test.tsx` has 7 authored tests: client isolation, GET ledger, atomic factual save, stale/conflict error, invalid amounts, blocked navigation with unsaved correction, no scenario writes.
- Supplementary data tab currently links to existing V2 screens; it is not integrated into one uninterrupted workspace yet.
- Scenario and results steps are deliberately nonfunctional honest placeholders. Do NOT replace placeholder with calls to current mutating `executeConversion`.
- Docs: `docs/ux/PROFESSIONAL_WORKSPACE_INTEGRATION.md` and `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md`.
- No new calculation engine, production data changes, master merge, Railway deploy, or GitHub Actions CI runs on the feature branch.

## D. Tests that DID pass, and what has NOT been tested

On user's Windows computer, isolated checkout:
`C:\Users\omer\Downloads\retireV2-workspace-test-20261022-120616`
User ran PowerShell validation on commit `c3e5e3bdfaf336faf078a78575034af9801b2dc4`:
- `npm ci`: installed 179 packages;
- `npm run build`: `tsc -b && vite build` passed;
- 4 selected test files passed, **34 tests passed (34/34)**:
  - `src/App.test.tsx` — 1
  - `src/components/ProfessionalWorkflowOverview.test.tsx` — 11
  - `src/pages/PensionProductsScreen.test.tsx` — 15
  - `src/pages/RetirementWorkspaceScreen.test.tsx` — 7.
- React Router v7 future-flag warnings were not test failures.
- Those 34 tests verified frontend component behavior and mocked service calls, NOT actual PostgreSQL persistence or business-calculation acceptance.
- The development branch gained **Docker/dev scripts and fixes after `c3e5e3b`**. These later changes are **UNTESTED** on Windows; no claims of full integration success.

## E. Active blocker at the exact handoff

Goal: run *real V2 FastAPI + real PostgreSQL + current React frontend* entirely locally with synthetic records. Files added to branch:
- `dev/Dockerfile.workspace`
- `dev/compose.workspace.yml`
- `dev/Start-Workspace-Local.ps1`.

User ran `git pull --ff-only`, receiving `57f8d014de4e5768fdf9bf64a25abbe957955598`, then ran:
```powershell
cd "C:\Users\omer\Downloads\retireV2-workspace-test-20261022-120616"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\dev\Start-Workspace-Local.ps1"
```
Outcome:
- Docker Desktop, Docker build, `postgres:16` initialization and container health: OK.
- Alembic migrated a long chain through the final `CRTISBA` migration, then failed with:
```
RuntimeError: CRTISBA_APPLICATION_DB_ROLE is required for PostgreSQL
```
- Script correctly did Docker Compose `down --volumes --remove-orphans`, so failed temporary DB/containers were removed.
- Cause: synthetic Compose initially used one DB owner account and did not supply the mandatory restricted app role required by `backend/alembic/versions/c4e8a2f6b731_crtisba_source_basis.py`. Migration *deliberately* requires a named PostgreSQL role and grants SELECT/INSERT (not UPDATE/DELETE) to the protected append-only decisions table.

**Fix already committed to feature branch, BUT NOT TESTED YET**:
1. `dev/init_workspace_role.sql`: create `rtdir_synthetic_app` login (not migration owner).
2. `dev/compose.workspace.yml`: run init SQL in fresh disposable PostgreSQL, supply `MIGRATION_DATABASE_URL`, `APPLICATION_DATABASE_URL`, and `CRTISBA_APPLICATION_DB_ROLE=rtdir_synthetic_app`.
3. `dev/start_workspace_backend.sh`: run Alembic using migration owner, explicit permission grants, then start FastAPI with restricted runtime-role connection.
4. `dev/grant_workspace_permissions.py`: grant runtime app access to ordinary migrated tables/sequences, verify it is not superuser and is separate from migration owner; specifically verify CRTISBA has SELECT/INSERT only, UPDATE/DELETE denied.
5. `dev/Dockerfile.workspace`: bundle the new entrypoint and grant script.
6. `dev/Start-Workspace-Local.ps1`: faster exact error detection if backend process dies during migration.
- Last code-implementation SHA `6dff74258e37d450cdb880e32b89988d74aa04e1`.
- This is **local test infrastructure only**; no changes to original backend Alembic migration, production Dockerfile, Railway deployment or V2 financial logic.

**Next immediate action:**
1. Read the actual latest branch HEAD and review these test harness changes for correctness/security. Do not copy production secrets or weaken immutable-table permissions.
2. If review shows no obvious defect, request the owner to rerun in SAME existing local checkout:
```powershell
cd "C:\Users\omer\Downloads\retireV2-workspace-test-20261022-120616"
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File ".\dev\Start-Workspace-Local.ps1"
```
3. Observe exact output. Resolve any new local migration/seed issues **only in isolated dev files**, unless a verified product defect requires its own separately governed task. Avoid repeated blind long waits. A passing `/health` alone is not enough; ensure seeded clients/products and reload/update persistence, and cross-client isolation.
4. App URL should be `http://127.0.0.1:5173/clients/1/workspace` (client id generated; launcher prints actual URL). Use local user test only. `Ctrl+C` should trigger cleanup. The frontend uses development API base `http://127.0.0.1:18080/api`.
5. After integration acceptance, start a distinct, governed scenario-model package: persistence of scenario decisions separate from actual products, eligibility, reversible allocation, current M09 execution, replacement M10 comparison — not unapproved technical shortcuts.

Possible subsequent blocking requirements must be grounded in observed logs. Do not predict success or invent further blockers.

## F. Verified backend limitations and protected decisions

- `backend/app/api/m06_conversion_routes.py`: historical conversion archive; read-only.
- `backend/app/api/m09_cashflow_routes.py`: archive-only scenario/cashflow history, no current planning execution.
- `backend/app/api/m10_comparison_routes.py`: sealed comparison route, no replacement exposed.
- `backend/app/api/canonical_conversion_routes.py`: preview, execute, reverse of actual source conversions. Backend execution updates saved component balances.
- `backend/app/api/pension_product_routes.py`: factual GET/PUT/import; `expected_version` guarded and transactionally audited.
- Current `frontend/src/api/pensionProductsApi.ts` exposes exact component string balances; 11 required codes in backend.
- Do not report hypothetical pension, capital income, indexed amounts, grants' tax or 161ד calculations as live until authoritative evaluated adapters exist. Report `NOT_AUTHORIZED`/not available when appropriate; do not add fake figures as placeholders in real V2.

## G. Management rules (READ PLAYBOOK FOR FULL DETAILS)

1. User is professional product owner, **not** a Git operator/CI engineer. Assistant operates tools, does real bounded work, asks only essential product decisions.
2. Owner criticized multiple cycles of ~13 repeated GitHub CI actions and expensive Work credits. Prefer GitHub connector and local targeted tests; consolidate fixes, authorize full CI before use, never per-commit CI.
3. Avoid governance loops: check dependencies/contracts/allowed scope BEFORE running. Reuse accepted evidence, revalidate deltas; don't rediscover/reopen closed milestones.
4. Distinguish authoring, independent audit/acceptance, master merge and Railway production deploy. They are separate gates; no automatic master changes.
5. Product UX is evaluated via complete work journey, not appearance alone. Keep controls/provenance but expose only contextually.
6. Never let a technical phase map override user's actual business flow; V1 is behavioral evidence, not a buggy model to clone.
7. Respect Governance v1.1, owner-authorized packages, production readiness `NOT_CLAIMED` and downstream `NOT_AUTHORIZED`.
8. Do not invent special permissions for different conversations, background work, status or test completions.
9. No real client data in samples; local/preview synthetic only.

## H. Opening a new conversation

Copy/paste:

> Continue RETIRE V2 from the 2026-10-22 handoff in `omerb21/retireV2`, branch `feature/professional-workspace-ux-first-20261022`. **Before editing code, use the connected GitHub tool** to read `docs/ux/V2_DEVELOPMENT_MANAGEMENT_PLAYBOOK.md` and `docs/ux/V2_CHAT_HANDOFF_2026-10-22.md` from that branch. Also read `docs/ux/PROFESSIONAL_WORKSPACE_INTEGRATION.md` and `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md` and verify actual branch HEAD. Treat the first two files as binding continuity guidance subject to Governance v1.1. Our latest local Docker end-to-end attempt failed solely at CRTISBA role migration prerequisite; an isolated dev-stack fix was committed after the failed run but remains untested. Resume with static review then one local rerun of `dev/Start-Workspace-Local.ps1`. Do not merge, deploy, rerun expensive CI, or connect current factual canonical conversion execution to hypothetical scenarios. Update the handoff documents before the next chat transition. Do not require me to repeat decisions already recorded.

**Handoff status:** Prepared; current docs alone do not certify local Docker run, business calculations, scenario engine or production readiness.

## I. Follow-up local trial, October 22 at 13:51 Israel time

- Owner fast-forwarded the local Windows checkout from `57f8d014` to `e8c306ecfe0f1109fd0f95d89aba26e2d0b215e3` and invoked `dev/Start-Workspace-Local.ps1`.
- Docker image and synthetic PostgreSQL started successfully, but the backend container exited before Alembic with `/opt/workspace/start_workspace_backend.sh: 3: set: Illegal option -`.
- Root cause indicated by this error and Windows checkout: shell script CRLF line endings reaching `/bin/sh` in the image. This is a local harness failure, **not** evidence that the earlier CRTISBA-role correction failed; migrations did not execute on this attempt.
- Minimal local-harness correction committed as `d372b2c6c5ab3b712902af3d1962e28952e6e781`: `dev/Dockerfile.workspace` now strips carriage returns from the copied shell entrypoint during the image build. No backend migration, financial logic, production Dockerfile, master, or deployment change.
- **Not yet retested**: owner must `git pull --ff-only` and rerun `dev/Start-Workspace-Local.ps1` in the same isolated checkout. Inspect output before any further changes. Upon success verify seed, persisted edits, reload, and cross-client isolation. No scenario engine or comparison acceptance is claimed.
- As of this handoff amendment, the last known implementation commit was `d372b2c6c5ab3b712902af3d1962e28952e6e781`; the documentation commit will advance branch HEAD, so fetch actual HEAD again before editing.

## J. Second local run, October 22 at 13:53 Israel time

- After CRLF normalization (`bbb441d`), Windows owner reran the launcher. Full Alembic chain reached `c4e8a2f6b731`; the app-role grants were verified, Uvicorn started, `GET /health` returned HTTP 200, first client POST returned 200 and first pension-product POST returned 201.
- Local seed's first pension-product PUT returned HTTP 422: all 11 component keys were mangled non-UTF-8 Hebrew text. The diagnostic reflects a **Windows PowerShell 5.1 JSON response decoding error**; the server did not receive the canonical Hebrew component codes. The script's POST response was parsed with `Invoke-RestMethod` and reused property names in its PUT.
- Targeted local-only fix commit: `67948ae222cc3f8f3a018f32c0a06712160eea1f` changes `dev/Start-Workspace-Local.ps1` to read HTTP response bytes via `Invoke-WebRequest -UseBasicParsing`, decode UTF-8 explicitly, and parse JSON using `ConvertFrom-Json`. No application, migration, financial, security or production changes.
- Owner explicitly time-boxed this experiment: **one further rerun**, then abandon this local Docker harness if another blocker occurs and return to core V2 development. Do not iterate an open-ended series of environment patches. The new fix is NOT YET TESTED; no end-to-end/persistence acceptance claim.
- Next: fetch current feature HEAD, fast-forward isolated checkout and run the same launcher once. If successful, exercise a synthetic factual save and reload and client isolation. If unsuccessful, stop Docker work and document blocker. No master merge, production deploy or expensive CI permitted.

## K. Local launcher success reported by owner (2026-10-22)

- Owner reports the final corrected local launcher **works** after commit `67948ae`. Treat this as owner-reported local stack/startup success; detailed logs for this successful run, factual save/reload, and cross-client isolation are not yet provided.
- The environment repair loop is closed for now; do not reopen Docker troubleshooting speculatively.
- Immediate remaining bounded acceptance check: in synthetic workspace, edit an existing client A product component via explicit factual correction, save, refresh and confirm persisted exact amount; navigate to synthetic client B and confirm no A products appear; verify scenario/results are non-mutating placeholders. Do not use real client data.
- Upon that check, advance bounded UX integration of supplementary facts through existing accepted APIs. A genuinely independent scenario decision persistence/engine requires a distinct governed package and must not call canonical factual conversion execution.
- No master merge, production deployment, expensive CI or scenario-financial acceptance authorized. Always re-read live branch HEAD before edits.
