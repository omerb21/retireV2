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

## L. Synthetic UX acceptance feedback and client navigation correction (2026-10-22)

- Owner verified factual correction saving works on the local synthetic stack (reported as passed), and scenario stage displays the non-operational notice (screenshot observed). These are owner-reported checks, not an independent SQL write/read audit or professional engine acceptance.
- Owner observed navigation problem: selecting the other client returned to the legacy M01 ClientDetail instead of the professional workspace. Screenshots showed client B on `/clients/2` (legacy), and client A scenario placeholder on `/clients/1/workspace`.
- Minimal UX navigation edits in feature branch: commit `1daba2ee2b4c9d947083331e7333832322e72a07` changes primary name link in `ClientListScreen.tsx` to `/clients/:clientId/workspace`; commit `25e5d115836623d7e9d884b4d0a729d62c7fd638` adds a direct return link from the existing `ClientDetailScreen.tsx` to the same client's professional workspace. Legacy details remain accessible via an explicitly labeled secondary link.
- Navigation edits not yet exercised after fast-forward of local checkout. No expensive CI run and no production deploy. Existing portfolio client guard remains unchanged. Next: single focused manual A to B to A browser navigation check after `git pull --ff-only` and browser reload; no need to rebuild Docker. Proceed thereafter to accepted supplementary facts workspace slice; scenario domain model needs independent governed contract before implementation.

## M. Client-switching accepted; read-only supplements slice started (2026-10-22)

- Owner confirmed client switching is fixed after navigation changes.
- Follow-up code commit `4a8d9ccf79585b8fdde53d97d7b71a06cbf5fe9a` adds **read-only** client-scoped counts in the new `supplement` step from accepted GET APIs: employment records, historical grants, actual capitalizations, capital assets, recurring incomes, and recurring expenses. No scenario write or financial calculation is introduced.
- Read response groups are rejected on client-ID mismatch, with cancellation on route/step change and visible loading/error states. Original links to accepted detail/edit screens remain.
- **Code is drafted and committed but NOT YET compiled, tested or manually accepted.** Must run a narrow TS/build check and focused navigation/supplement tests prior to claiming acceptance. No full CI authorized. Avoid presenting counts as calculated income, tax, or planning results.
- Master remains unchanged, no deployment or production readiness claimed. Read latest HEAD before next changes.

## N. Focused supplementary-data tests drafted (2026-10-22)

- Live feature branch read after prior update: `4fc91bdc142bc861d263b29ce7d271c816109a24`, master remained `6f3d523e9c81b55da045ac3c85e747104821d5da`.
- Follow-up test-only commits `1a9ad8045b44afde563c33c6353cb6deda07cd64` and `8dcbf233a623c1623295d3ffabb0324fde3f173e` add API mocks and two focused tests to `frontend/src/pages/RetirementWorkspaceScreen.test.tsx`: read-only employment summary/count, and failure closed on a cross-client supplementary response. Existing seven workspace tests remain.
- **Tests authored but NOT executed** in the connector environment; latest TypeScript build and local FastAPI/React integration of the supplementary summary remain UNVERIFIED. Do not report passing tests on the basis of code inspection.
- New code is limited to the development branch's React UX and test file; no backend calculation, scenario write, production deployment, master merge or full GitHub CI run.
- Minimal next validation in owner's existing isolated Windows checkout, without restarting Docker unless the owner explicitly wants live UI: `git pull --ff-only`, then from frontend `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`. Inspect actual result before any acceptance or further edits. Do not repeat broad tests absent invalidating changes.
- Next governed UX vertical slice after verification: in-workspace supplementary facts display/edit boundaries using accepted APIs, with client isolation; preserve source provenance, factual/scenario separation and scenario engine NOT_AUTHORIZED status.

## O. Focused frontend verification PASSED (2026-10-22 14:47 Israel time)

Owner ran in isolated Windows checkout fast-forwarded to `b80d5aace8f755b639ffcbe8735b3560def0a2f4`:
- `npm.cmd run build`: `tsc -b && vite build` PASSED, 76 Vite modules transformed.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: 1 file PASSED, 9/9 tests PASSED, duration 2.15 seconds.
- Included two new supplementary tests: read-only scoped GET summaries and rejection of cross-client response data.
- React Router v7 future-flag warnings were non-fatal warnings, not failures.
- Verification is **owner-executed targeted frontend build and mocked-API unit/component tests**, not independent backend SQL integration or domain-calculation acceptance.
- Local prior synthetic factual save and client navigation were reported working by owner. Supplementary read-only cards have not yet received a direct browser review.
- No new code, master merge, deployment or expensive CI authorized. Continue next bounded UX slice only within accepted API boundaries. Scenario engine still NOT_AUTHORIZED.

## P. In-workspace supplementary details drafted (2026-10-22)

- Development branch was at `80f5c691b889226f095d36824e24e697e08faf34` when this slice began. Existing 9/9 focused frontend tests and build had passed at previous HEAD (owner executed).
- New implementation commit `d676fc0fcd6520ec878f1c4e95991478ee37d11d`: in stage 3, display read-only lists containing actual accepted API fields (employment dates/employer, grant date/exempt grant, past capitalization/date, capital-asset known value and verification state, recurring income amount/basis/frequency, recurring expense amount/frequency), replacing bare category counts. No calculation or source write, client-bound mismatch guard retained, edit links to existing accepted screens retained.
- Focused test alignment commit `db79799aeb748fd8bfc75b65c63b2004f7fac65c`: checks real employer row display and heading count, keeps cross-client mismatch test.
- **These new changes have NOT YET been built or tested.** Prior passing tests on older SHA do not automatically cover this delta. Next minimal validation: one targeted `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` from the existing checkout after `git pull --ff-only`. No Docker rerun required for TypeScript/unit tests.
- Keep this as UI read-only. No direct edit forms, scenario persistence, business logic, tax/NPV or production merge authorization. Do not mistake display of reported income and expense amounts for accepted calculated outputs.

## Q. Read-only supplementary detail slice verified (2026-10-22 15:28 Israel)

Owner fast-forwarded isolated Windows checkout to `766fe3848acbd2ad51856de69c4f411f0206e9c9` and ran:
- `npm.cmd run build`: PASS, `tsc -b && vite build`; Vite 76 modules, build complete in 930 ms.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 1 test file, 9/9 tests, 2.36 sec total.
- React Router future-flag warnings are non-fatal.
- Verified are frontend compile/build and targeted mocked API component tests, **not** browser acceptance of supplementary detail content, full backend integration or retirement-financial computation.
- Next bounded slice: integrate edit affordances and existing authoritative edit routes from supplementary sections without rewriting existing domain contracts; preserve actual-source and scenario separation, client-scoped state and independent gate on scenario engine. Avoid needless repeated CI.

## R. Contextual supplementary-edit navigation slice (2026-10-22)

- Parent branch HEAD before edits: `98a18ea41ea916b7efbf0d7646041b65d39e3eae`; accepted read-only supplementary detail build and 9 component tests had passed at prior HEAD.
- Feature-only commit `770cf6fcc4b933a22f5143d603e6ef191d3fc046` introduces a contextual edit link under each supplementary category: employment records -> existing employment-history screen; historical grants -> existing grants screen; actual capitalizations -> existing actual-capitalizations screen; capital assets and recurring incomes/expenses -> existing planning-input screen. Removes redundant generic links. This reuses authoritative existing editors and avoids implementing duplicate domain writes.
- Return navigation to the new professional workspace added in existing screens: employment history `d2dc79162c885097fb90155c4af33fe90a3b20b4`, grants `1302b3d6f55b7b88f9b1db9e5691af50715e538a`, actual capitalizations `48dc1591be375607d5ede04a87245ab2d10b6420`, planning input `41085e496d6bc14fbc8d34526171cdea0ea1ad23`.
- **Not yet compiled, unit-tested or browser-reviewed** after these code edits. Minimum next check: local `git pull --ff-only`, `npm.cmd run build`, and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`. Avoid full CI.
- No new edit mutations, scenario writes, financial calculations, changes to backend, master merge or production deployment. Genuine inline edit UX remains a future slice requiring reuse of accepted API contracts and route guard review.

## S. Contextual edit navigation build verified (2026-10-22 15:41 Israel time)

Owner fast-forwarded Windows isolated checkout to `30a64c9ccb774285b40ec5c542c3aac4a67c4866`, then:
- `npm.cmd run build`: PASS; `tsc -b && vite build`, 76 modules, 917 ms.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 9/9 tests, 2.22 seconds.
- React Router v7 future-flag warnings only; no errors.
- The 9 component tests do not specifically exercise new contextual link destinations or return navigation; browser navigation acceptance remains outstanding. Do not claim full end-to-end acceptance.
- Contextual links reuse legacy authoritative editors; no duplicate write path introduced.
- Next prioritization: targeted links/return-navigation tests then in-workspace factual edit UX with existing contracts, no scenario mutation. No master merge, deployment or broad CI authorized.

## T. Supplementary edit-link coverage (2026-10-22)

- Before change feature HEAD was `fe778449cce10c42fbed5665ed89ca4227688500`, previously owner-verified build and 9 tests at `30a64c9`.
- Test-only change `b6c663313d5a2620787ae3388160b51a9414cba7` adds one targeted component test verifying all six category contextual edit anchors resolve to their client-scoped authoritative editor routes, without invoking pension write APIs.
- This test is **not yet executed**. No direct edit forms were added: source-owned legacy screens remain the sole write interfaces. Next action: targeted build/test validation, plus browser validation of return navigation when convenient. Avoid broad CI.
- No scenario logic or backend change, no merge, no deploy. Continue with owner-approved workflow UX and existing domain authority boundaries.

## U. Supplementary edit destinations test PASSED (2026-10-22 15:44 Israel)

- Owner fast-forwarded isolated checkout to `5a0cfc5c6d9bb4a7dc33db770e3217bd5704ae9d`.
- `npm.cmd run build`: PASS, `tsc -b && vite build`, 76 modules, 927 ms.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 10/10 focused tests, 2.33 seconds.
- New test confirms correct client-scoped links to authoritative editors for all six supplementary sections; existing tests cover factual PUT guards, scenario non-mutation, and client mismatch guards.
- React Router future-flag warnings only. This is mocked API component testing, not full browser or DB integration.
- Next authorized development goal: minimize legacy navigation by moving a bounded factual editing interaction into the professional workspace, reusing an accepted API and preserving validation, source and lifecycle semantics. Avoid new scenario contracts or financial calculations.
- No master merge, production deploy or full CI.

## V. First bounded in-workspace edit: existing employment record (2026-10-22)

- Owner's previous local build and 10/10 focused tests verified `5a0cfc5`, followed by documentation update `66dc7dc3ab15fef52cdacfce3b6ae6b6b57b5821`.
- Feature commit `8343d73516eaabbe3ac8ad802de40d7abb112fea` adds a limited inline **existing employment record correction** form in supplementary stage, using existing `updateEmploymentRecord(clientId, employmentRecordId, payload)` API, followed by authoritative `getEmploymentRecords` reload. No parallel server write interface, no scenario logic.
- Only existing records are editable here; create/delete continue in existing employment-history screen. The UI checks response client and record identity and prevents showing a different client's supplementary data.
- Focused test commit `5b488c05feaa6a3bfb01277d22dc2d239b43c5c8` adds a mocked correction test checking PUT client/id/payload and no pension product write.
- **Neither build nor test of this delta has been run.** Before accepting, run narrow `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` after git pull. Also browser verify factual persistence and client switch when convenient. Any error must be fixed before extending forms.
- No master merge, production deploy, broad CI or authorized scenario engine.

## W. Inline employment edit targeted verification PASSED (2026-10-22 15:50 Israel time)

Owner fast-forwarded local checkout to `32de20ee6a1fd38b6423dd74ba7438c7f5f34b5e` and executed:
- `npm.cmd run build`: PASS, `tsc -b && vite build` (76 modules; 921 ms Vite).
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 11/11 tests in one file (2.32 s).
- New test covers in-workspace employment-record edit through existing accepted PUT, followed by data refetch. Prior tests cover client isolation and pension/scenario non-mutation.
- React Router future-flag warnings only, nonfatal.
- This is frontend mocked API validation, not an end-to-end actual DB write or an independent proof of all employment record validation semantics.
- Next: review lifecycle/client-route stale async response and date/field validation of the employment form before expanding inline edits. Avoid restarting costly infrastructure and do not repeat already-passed broad checks unnecessarily.
- No master merge, deployment, full CI, calculation modification or scenario engine activation.

## X. Employment editor safeguards added (2026-10-22)

- Starting feature branch HEAD `04b18978f0daf2773cf3347ea63fad31864d4f4c`. Owner had reported passing build and 11/11 focused tests for previous employment editor slice.
- `f0ab731e01a27f9b73c53a46872310cc20956e24`: inline employment editor now checks required employer/date format and chronology before PUT; assigns an incrementing generation token to saves and invalidates that token on client change. Late save results/errors after a client switch are ignored. Refreshed record client ownership is checked; a mismatch is shown as an error rather than replacing display.
- `9b33604eb2aefdebd5e2524360ec1fc684a22dcf`: two new targeted tests for invalid end date blocking PUT and stale employment save after navigating to another client.
- **Build and tests for these changes have not been run.** Request one local targeted build and the workspace test file; do not infer acceptance from prior 11 passing tests.
- No server/data model change, scenario implementation, master merge, production deploy or full CI.

## Y. Employment editor safeguards verified (2026-10-22 16:14 Israel)

Owner fast-forwarded Windows local checkout to `b00797cf2afdf77dd6083fda2adb609d2438319c` and executed:
- `npm.cmd run build`: PASS; TypeScript and Vite, 76 modules, 833 ms build.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 13/13 tests, one test file, 2.28 s.
- Specifically, chronology guard and stale save across client navigation tests passed. React Router future-flag warnings are non-fatal.
- These are frontend mocked-API tests, not direct PostgreSQL employment-save integration.
- Next: bounded extension of inline edits only if an accepted endpoint and validation constraints are read and retained; no unapproved hypothetical scenario execution. Prefer concise meaningful UX improvements over endless infrastructure reruns.
- No merge to master, deployment or GitHub CI.

## Z. Inline factual grant correction added, PENDING targeted verification (2026-10-22)

- Started from feature branch HEAD `b3dbfd333e8417ee338f2376f157493be631f7d2`, after owner-verified 13/13 tests at prior implementation HEAD.
- `22add1ba2e4e055951149de1247295aa516e0245` adds an existing-grant correction form in stage 3 using existing authoritative `updateGrant(clientId, grantId, GrantPayload)`, then refetches `getGrants`. Preserves all six fields of the legacy grant payload. Client/record identity checks and async generation protection reject stale cross-client updates; create/delete remain in legacy grants screen.
- `273bc3bbd16ee6bd5c5e0f88924622ed6bee0d12` adds two tests: successful owner-scoped grant correction with existing endpoint and rejection of negative grant input before any write.
- `a62a0831118c3eaebef9362a4885b2c7fd8ae74e` fixes escaping of form validation regexes in the new code. No backend/financial calculation or scenario changes.
- **Not yet compiled or tested**. Owner should run a single incremental local `git pull --ff-only` followed by `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`. Expect 15 tests. If failure occurs, inspect result and make one narrow correction before further development.
- Backend integration and professional correctness of grants are not claimed by these frontend mock tests. No master merge, deployment or full CI.

## AA. Inline grant correction focused verification PASSED (2026-10-22 16:19 Israel)

- Owner fast-forwarded local Windows checkout to `57f0b467255b83e93fa48bb3e17a96463e2f9221`.
- `npm.cmd run build`: PASS, `tsc -b && vite build`, 76 modules, 875 ms Vite.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 15/15 tests (one test file), 2.56 seconds total.
- This includes authorized existing-grant PUT and negative amount rejection, employment editing, client separation, and scenario non-mutation. React Router future-flag warnings only.
- Verification uses mocked API component tests, not a live PostgreSQL grant save or professional tax decision confirmation. Do not treat recorded exempt grant values as calculated or tax-authorized amounts.
- Next recommended gate: targeted live synthetic UI/API save-and-reload of a historical grant and employment record before further proliferation of in-workspace editors; use no real client data.
- No full CI, master merge, or production deployment.

## AB. Synthetic live API factual persistence check prepared (2026-10-22)

- Feature branch had passed previous 15/15 frontend mocked-API component tests, documented at `5c318c61bbe5aa9c28bd5d7f3856602c948cfcaf`.
- New local-only PowerShell test script `dev/Test-Workspace-Factual-Saves.ps1`, commit `e00dc28e3539029ea0858c836829e7da3719e363`.
- Designed for the owner-managed ephemeral Docker/FastAPI stack at 127.0.0.1:18080. Requires two synthetic named clients already seeded by `dev/Start-Workspace-Local.ps1`; refuses to act if either is missing.
- Uses existing employment and grants POST, PUT and independent GET APIs. Asserts record owner and identity, updated employment employer and updated grant amount persistence, plus no newly-created A record IDs appearing in B's GET lists.
- ASCII-only Windows PowerShell 5.1 compatible and explicitly decodes JSON replies as UTF-8. Does not touch production, Railway, or true pension balances, and does not claim professional validation of grant tax treatment.
- **Script not executed yet**: local DB persistence and client isolation results remain PENDING. Owner should keep existing local dev launcher alive, fast-forward feature branch in a second PowerShell window, run `powershell -NoProfile -ExecutionPolicy Bypass -File ".\\dev\\Test-Workspace-Factual-Saves.ps1"` from repository root; capture output. If local stack is no longer running, avoid assuming success; restart only by explicit choice.
- Backend smoke is a narrower API integration test, not a browser UI end-to-end test. No full CI, master merge, deploy or scenario engine change.

## AC. Local factual persistence smoke bootstrap correction (2026-10-22)

- User ran `dev/Test-Workspace-Factual-Saves.ps1` after successful `git pull --ff-only`. The script failed at `[int]$a[0].client_id`: PowerShell 5.1 reported `System.Object[]` instead of integer client ID.
- Failure was in test-harness client selection before any employment/grant create/update actions. No server persistence outcome can yet be claimed.
- Commit `75e7230d19b1a47fcae3b1e949d0dd23d4772667` normalizes the GET clients response when Windows PowerShell nests the JSON result and requires exactly one named synthetic A and B client with scalar IDs.
- **Fix not yet verified**. One retry with existing running local stack: from repository root `git pull --ff-only`, then `powershell -NoProfile -ExecutionPolicy Bypass -File ".\\dev\\Test-Workspace-Factual-Saves.ps1"`. If blocked again, inspect rather than repeat indefinite environment debugging. No full CI, master merge or deployment.

## AD. Local synthetic PostgreSQL factual saves verified (2026-10-22)

- Owner ran `git pull --ff-only` to `841517cea499e8c61fb6a16528e84426a318811e` and then `powershell -NoProfile -ExecutionPolicy Bypass -File ".\\dev\\Test-Workspace-Factual-Saves.ps1"` while the isolated local FastAPI/PostgreSQL stack was available.
- Actual console result:
  - `PASS: employment POST / PUT / independent GET.`
  - `PASS: grant POST / PUT / independent GET.`
  - `PASS: client B lists exclude A employment and grant IDs.`
  - `LOCAL SYNTHETIC API SMOKE PASSED. A=1 B=2. Temporary database only.`
- This validates backend persistence of synthetic employment and historical grant edits and cross-client list exclusion through existing APIs against disposable PostgreSQL. It does not prove end-to-end React form interaction, professional tax/eligibility correctness, full database access-control guarantees or hypothetical scenario engine.
- Local infrastructure validation loop is closed; avoid additional Docker iterations without new evidence. Continue development within accepted professional workspace UX/API scope. No master merge, production deployment or full CI.

## AE. Supplementary-edit workflow continuity refinement (2026-10-22)

- Previous owner-reported local synthetic PostgreSQL integration succeeded (employment/grant POST, PUT and independent GET; A/B isolation), and documented HEAD was `d694ce0bc5d018b26d70cf2e10032b471fdf6c89`.
- Feature commit `31dc882c7161f39846ac0efd4095aabf8f5607cc` makes stage navigation refuse to discard an unsaved employment or grant editor, or an in-flight factual save. Opening one supplementary editor closes the other, so only one of these factual edits is shown at a time. Supplementary copy now correctly describes in-workspace editing and which operations still use existing screens.
- Test-only commit `3b274724865214c496dab54d15dcce0bc7b4093e` adds focused coverage of unsaved employment draft preservation on stage navigation.
- **New changes NOT YET built or tested**. Minimal validation: pull feature branch; run `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` (expected 16 tests). Do not use broad CI.
- No new backend writes, financial contracts, scenario engine, master merge or production deploy.

## AF. Shared unsaved-edit warning render correction (2026-10-22 16:46 Israel)

- Owner ran frontend build from correct folder at feature HEAD `285b3cde575e300e4cd1afb4792c5b54e5c79e83`: TypeScript/Vite build passed (76 modules).
- Focused Vitest run: **15 of 16 tests passed, 1 failed**, specifically `keeps an unsaved supplementary employment edit when switching workflow stages`. DOM showed stage remained "נתונים משלימים" and unsaved field remained intact, but `role="alert"` was absent.
- Root cause from source inspection: global `error` state was rendered only inside portfolio step, even though `switchStep` sets it when an employment or grant edit is active.
- Commit `d1b00a2583520e20c5384c3312ed3136932d14c2` moves the existing `error` alert out of portfolio-only content into the shared workspace body so stage-navigation validation is visible on every step. No business logic, data persistence, API or scenario engine change.
- **Fix is not yet executed/tested**. Next bounded check: owner runs `git pull --ff-only` from frontend, `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`; expect 16/16. Do not run broad CI.
- No master merge/deploy; no claim of complete end-to-end browser acceptance.

## AG. Workspace navigation warning verification PASSED (2026-10-22 16:49 Israel)

- Owner fast-forwarded local Windows checkout to `e2558b0d108f5ddc43435414eb0cc1d79d3e202c`.
- `npm.cmd run build`: PASS, `tsc -b && vite build`, 76 modules, 827ms Vite build.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 16 of 16 tests, 2.57 seconds.
- Previously failing unsaved supplementary edit warning test now PASSED after moving alert to shared workspace content. React Router v7 future-flag notices are non-fatal.
- This closes the focused frontend regression. Earlier owner-run local synthetic API smoke verified employment/grant POST/PUT/GET and client B isolation, but not a browser-driven end-to-end UI save.
- Next: advance professional workflow UX in bounded accepted slices, minimize unnecessary manual repeat builds. Keep source facts, factual correction and hypothetical scenario strictly separate.
- No master merge, production deployment or full CI.

## AH. Prevent lost supplementary drafts when opening other records (2026-10-22)

- Prior owner-verified feature build passed and 16/16 focused workspace tests passed; recorded docs HEAD was `d63ae1189afcbf2dc82afc4b3de37daed9019969`.
- `dd638d1616565b602d86c868bda9f418325d1cfc`: opening another employment/grant record via the supplementary list is refused while any supplementary editor is open or an API save is in flight. The previous behavior silently discarded an active factual edit. Displays the shared workflow alert and keeps the original draft. Cancel buttons also clear the shared alert.
- `21346b2b48561a13c67ff1f0a33c514d2fec7083`: adds focused test that edited employment draft survives attempted selection of another employment record.
- **Pending validation:** pull feature branch from frontend; `npm.cmd run build`; `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`; expect 17 tests. Do not launch full CI.
- No new financial write contract, master merge, production deployment or scenario engine changes.

## AI. Supplementary record switching guard verification PASSED (2026-10-22 17:02 Israel)

- Owner pulled to `ed2a7f1f3d17e9f7d6d6a7745bef158eb0d1a4a6`.
- `npm.cmd run build`: PASS (`tsc -b && vite build`; 76 modules; Vite 939 ms).
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS 17/17; one test file, 2.78 sec.
- Newly added `preserves an unsaved employment edit when another supplementary record is opened` passes. React Router v7 future-flag warnings are non-blocking.
- Frontend mocked tests and earlier local synthetic API smoke passed; browser E2E not yet claimed. Avoid repeating this validation unnecessarily.
- Proceed to higher-impact workflow UX after this. No full CI, master merge or production deployment.

## AJ. Supplementary category focus UX (2026-10-22)

- Started at owner-verified `a058c4e533ed95770a32fe191825061fa1a332b5`: 17/17 focused workspace tests passed and frontend build passed at 17:02.
- `f3ca9dace6877180bfdeffeee0022b8fc4292dfc`: added an on-page category navigation for six supplementary factual data categories, with live record counts and a default 'all data' view; selecting a category narrows the visible list without changing any authoritative records or invoking writes. When employment/grant editing or saving is in progress, moving to another category is blocked to preserve the draft.
- `62bdec2644176cb45038d297ab1fd6cd17cb7065`: focused UI test for category filtering, returning to all data, and absence of employment/grant writes.
- **Build and new test NOT YET RUN**. Request one local frontend `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` after pull, expected 18 focused tests.
- No scenario execution, financial calculation change, backend contract change, full CI, master merge or deploy.

## AK. Supplementary category focus verification PASSED (2026-10-22 17:06 Israel)

- Owner pulled feature branch to `14b94c6d0ff515e0dbe2bc8658600f5913194c82`.
- `npm.cmd run build`: PASS (`tsc -b && vite build`, 76 transformed modules; Vite 870ms).
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 18/18 tests in one test file; 2.66s.
- The category filtering no-mutation test passed. React Router v7 future-flag warnings are informational.
- Focused validation of category navigation is complete. Recommended next work: holistic visual/interaction design and layout of professional workspace rather than more isolated navigation guards.
- No full CI, master merge or production deploy.

## AL. Professional workbench visual hierarchy pass (2026-10-22)

- Started from owner-verified 18/18 frontend focused tests and build; baseline was `cb47e0201a34d1813c7f944a9be778033c96364e`.
- Commit `019c85e0ef42a148c92f50bd2a760e4157ffafc1` changes only `frontend/src/pages/RetirementWorkspaceScreen.css`: adds a clearer client header border, easier-to-target stage buttons, centered max-width workspace, focusable category filter presentation, section cards for supplementary facts, distinct factual editor forms, and narrow-screen horizontal category/stage scrolling plus single-column data cards.
- Does not change APIs, React logic, source facts, scenario engine or financial calculations.
- **Pending local visual/build verification**: run `git pull --ff-only` and `npm.cmd run build` from frontend and inspect local synthetic workspace on desktop and narrow viewport. Previously passing 18 UI tests do not verify visual polish; there are no new logic tests.
- No full CI, master merge or production deployment.

## AM. CSS workbench build verified (2026-10-22)

- Owner ran `git pull --ff-only` through `eb710022318b25eda087365f4a45489f3e5f5a34` and `npm.cmd run build` from frontend.
- PASS: `tsc -b && vite build`; 76 modules transformed; CSS emitted at 9.39 kB; 952 ms Vite build; no compilation errors.
- This validates compilation only, NOT browser visual design. Visual acceptance for desktop and mobile layouts remains pending; avoid claiming it passed.
- Prior 18/18 UI logic tests remained previously verified, not rerun for CSS-only change. No CI, master merge, deployment or scenario engine change.

## AN. Category filter guard consistency (2026-10-22)

- Previous visual CSS-only change at `eb710022318b25eda087365f4a45489f3e5f5a34` passed the owner's TypeScript/Vite build; 18 focused UI tests were previously passed before CSS changes, but visual browser acceptance is still pending. The last documentation HEAD was `8f8ca4f672dfec253ea2252cc8a86bbc59f8380e`.
- Frontend package has Vitest/jsdom but no checked-in Playwright/Storybook/screenshot harness, so no visual acceptance claimed from tooling.
- Source review found that the 'כל הנתונים' category filter button bypassed the unsaved edit guard used by the other six filter buttons.
- Commit `ddf92b3ebde9ffc3998e9e43623fa05c5487d554` centralizes category selection and checks active employment/grant editor and pending save for both 'all' and individual filters. Re-selecting active category is a no-op.
- Commit `49f2850d4ab976a94d78a04350a062dd2f411fad` adds a regression test: returning to 'all data' with unsaved employment edit stays in selected category, shows warning, preserves changed field and sends no write.
- **Pending targeted local compilation and 19 focused tests**. No backend/financial changes, CI, master merge or deployment.

## AO. Category guard validation PASSED (2026-10-22 18:43 Israel)

- Owner fast-forwarded to `276551ce06b1c7ea5b3725ba8e4493f3ded7d5ba` and executed `npm.cmd run build` from frontend: PASS, `tsc -b && vite build`, 76 transformed modules, 843ms Vite.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS 19/19, 2.92s, including guard on returning to 'all supplementary data' with an unsaved employment edit. React Router future-flag warnings are informational.
- This closes the focused category-navigation logic correction. CSS/visual acceptance is still not done, so next effort should prioritize a real browser viewport review rather than another speculative styling pass.
- No master merge, production deploy, scenario implementation or full CI.

## AP. Browser screenshot review: pension ledger sticky column overlap (2026-10-22)

- User confirmed original local server at 127.0.0.1:5173 had remained running; attempted second Docker launcher failed because 127.0.0.1:18080 was already bound. No backend fault; do not restart or stop existing stack without reason.
- User supplied first actual desktop Chrome screenshot at /clients/1/workspace, showing pension ledger with four synthetic products. Visual defect: sticky product/provider columns collide with displayed reported total amounts; text visually overdraws.
- Source inspection confirmed inconsistent first sticky column max-width 200px vs second sticky offset 180px, with no fixed provider width and no dedicated reported total minimum width.
- Commit `7fb5f94a6579797174c2ff04fa0c16a140144c17` changes CSS only: consistent 220px first sticky width and second right offset, fixed 185px provider width and explicit wrapping, dedicated 145px reported total column with LTR isolated numeric values; mobile widths 150px/145px with matching offsets.
- **Unverified visually and not yet locally built.** Owner can fast-forward current frontend checkout (without stopping running local dev server) and refresh existing browser, then provide another screenshot; CSS hot reload should apply. Test is visual rather than repeating 19 logic tests.
- A screenshot of supplementary data stage is still needed for UX review. No CI, master merge or deployment.

## AQ. Supplementary cards real-browser visual refinement (2026-10-22)

- Owner provided a live Chrome screenshot of Step 3 ("נתונים משלימים") in the synthetic workspace. Actual factual reads show 1 employment, 1 historical grant, and four empty categories. Data matches prior local synthetic API state.
- The screenshot shows six cards compressed into a single row, excessively narrow and tall, with broken English record names and unbalanced empty whitespace. Header/category filter is usable.
- Commit `3bb34f06f8154218de02ecdcc055e75c174b8dda` is CSS-only: supplementary card grid gets a 310px minimum width with responsive wrapping (generally 3–4 cards across rather than six), content top alignment and less forced equal card height, more legible item labels, and consistent native-look action button styling. Uses `:has(> section)` to scope the grid override without modifying the client identity DL. Single-column for smaller screens.
- **Not yet visually verified or built locally**. Existing local dev server is already running and should be reused; pull branch from a second PowerShell terminal and hard-refresh Step 3. Do not restart the Docker stack.
- No new API, financial decisions, calculation/scenario change, CI, master merge or deployment.

## AR. Supplementary card layout screenshot review (2026-10-22)

- Owner pulled `1b17cf91742f882d55569980745be8571c073b35` and provided refreshed live Chrome screenshot of Step 3.
- Visual review: layout no longer compresses six categories into one row; four cards wrap on first row and two on second at this viewport. Labels and action buttons legible without apparent overlap. Layout correction visually accepted for this desktop viewport.
- Follow-up UX opportunities, not yet implemented: reduce visual footprint of four empty categories and make categories with records more prominent. No claim of mobile layout verification or overall UX acceptance.
- No code changes from this review, CI, merge, or deployment.

## AS. Populated vs empty supplementary facts distinction (2026-10-22)

- Last confirmed desktop screenshot after the 310px minimum-width card fix showed legible four/two cards and was visually accepted; handoff HEAD before this slice `656a0654995254126085ec31667570a84b83d947`.
- `ac01aad3edccba0bf086134020995d8caff1203e`: supplementary sections now carry only presentation-oriented `has-records` or `is-empty` CSS classes derived directly from client-scoped GET response lengths.
- `d779938f00a6674d6638d56b052ab3a00880eec4`: CSS highlights groups with data using top border while reducing padding and forced height for empty groups; no change in whether empty cards/links appear, no hidden data.
- `55e568ba6e8e1661720f89826117fb3e227ff205`: focused test verifies classes on populated and empty categories and that no factual write endpoint was invoked.
- **NOT YET VERIFIED:** owner should run `git pull --ff-only`, `npm.cmd run build`, and targeted `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` from frontend; expect 20/20. Review refreshed Step 3 screenshot if available. Do not infer visual acceptance from test.
- No backend write contract, financial calculations, scenario execution, full CI, master merge, or production deployment.

## AT. Populated/empty card focused verification PASSED (2026-10-22 19:12 Israel)

- Owner reran from the correct `frontend` directory after an initial wrong-directory run. Correct `npm.cmd run build` PASS (`tsc -b && vite build`, 76 modules; 984ms Vite).
- Correct `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: PASS, 20/20 focused tests, 2.83s total. Includes populated/empty category display markers and no factual writes.
- Wrong-directory failures were environment invocation errors (`ENOENT` package.json and `document is not defined` with a different Vitest version), not code regressions. Future commands must include explicit frontend `cd`.
- Continue substantive professional workflow work; no need to repeat this focused validation now. Visual verification of latest populated/empty card color/spacing remains separate.
- No master merge, production deployment or full CI.

## AU. In-workspace employment creation (2026-10-22)

- Began from owner-verified 20/20 focused frontend tests and local PostgreSQL synthetic employment/grant POST/PUT/GET smoke; baseline docs HEAD `3e724276ca4973375ca6d92ece2144acd2634bab`.
- `33fbd95e6826cd459d4f451814ebe056c94c27e9`: Employment category in Step 3 now includes "הוסף רשומת תעסוקה". Reuses approved employment fields and the existing `createEmploymentRecord` POST endpoint; update path remains existing PUT. New record starts with blank employer/date and current-employment flag, and both create/update refetch GET after successful mutation. Single-editor and cross-client generation safeguards remain. Delete stays on existing full screen. No backend/schema changes.
- `20026be94eb53b37198bcab27de93005be543315`: targeted mock-API test asserts new record POST payload, GET refetch and no update PUT.
- **NOT YET BUILT OR TESTED**. The owner should fast-forward feature branch and run single frontend build plus `RetirementWorkspaceScreen.test.tsx` suite; expected 21 tests. A separate browser create/save may be valuable after build.
- No scenario execution, financial calculations, CI, master merge or production deployment.

## AV. Inline employment creation verified (2026-10-22 19:15 Israel)

- Owner pulled to `7966ede4fbc4e1ebbcb6d9e93f1fadbc1f3a637d`, compiled frontend successfully (`tsc -b && vite build`, 76 modules, 963 ms), and ran focused workspace Vitest suite: **21/21 PASS** (3.41 seconds).
- New test verifies a synthetic employment record is created through the established POST and refreshed through the GET. This is a mocked frontend test. Earlier synthetic local PostgreSQL POST/PUT/GET smoke passed, but this new inline create form has not been browser E2E validated.
- React Router future flag warnings are non-fatal. No master merge, production deploy or full CI.
- Next: consider matching in-workspace grant creation via existing accepted POST and strict payload validation, avoiding new tax conclusions.

## AW. Inline historical grant creation (2026-10-22)

- Prior owner-verified `npm.cmd run build` and 21/21 focused tests passed; preceding handoff HEAD `2bf30f7c699221ac20e638ad880bb1f2c0375d7d`.
- Commit `156d80245b3f4d8e5ce0bc3b4322c67e115671b0`: supplementary grant section now exposes "הוסף מענק היסטורי", using the exact six fields of accepted GrantPayload and existing `createGrant` API (POST); existing inline update remains PUT. After successful POST it validates client ownership and refetches grants for authoritative display. Same generation guard and single active supplementary edit; no deletes added.
- Commit `8ff0a0c2d789c378e5091f431ceba11f1e5c4ce9`: added focused mock-API test for creating a grant with accepted payload, GET refetch and no update PUT. Inputs represent **reported exempt grant amount**, not a computed or approved tax exemption.
- **PENDING:** owner runs a single frontend build and focused `RetirementWorkspaceScreen.test.tsx` suite (expect 22 tests). Scripts should always start by changing directory to `C:\\Users\\omer\\Downloads\\retireV2-workspace-test-20261022-120616\\frontend` before npm commands.
- No financial/business formula, backend/schema, scenario execution, CI, master merge or production deployment.

## AX. Inline historical grant creation verified (2026-10-22 19:52 Israel)

- Owner pulled feature branch to `49b07f2910729c7f5702215d031690b495726ed7` and ran `npm.cmd run build` from frontend: `tsc -b && vite build` PASS, 76 modules transformed, Vite 845 ms.
- `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx`: **22/22 PASS**, including new historical grant POST/refetch test and existing employment create, versioned component correction, scoping and unsaved-edit guards.
- Router future-flag notices are nonfatal. These tests use mocked API and do not establish that browser form creation has been validated against live local PostgreSQL.
- Next meaningful acceptance gate: local browser save/read-back of new employment and grant with disposable synthetic client and dedicated isolated DB. No master merge, production deploy or full CI.

## AY. Owner browser E2E acceptance and professional employment workflow correction (2026-10-22)

- Owner verified manually in still-running isolated local browser /clients/1/workspace: newly created historical employment and historical grant persisted and remained visible after Ctrl+F5. Screenshot showed employment count 2 and grant count 2; **acceptance of those create/read-back paths recorded** (not full application approval).
- Owner identified two product-model corrections: (1) historic severance settlement should be entered under the employer, with grant, pension-continuity (רצף קצבה), severance-continuity (רצף פיצויים) and evidence organized per employment/retirement event. Grants overview should be a consolidated report/navigation, not detached primary entry. (2) current employer needs its own rich workflow distinct from historic employers. Current employer's severance handling is a scenario decision, NOT a historic factual exemption or automatic conversion.
- Code/API observation: EmploymentRecordItem currently only employer_name, work_start_date, work_end_date, is_current, notes. GrantItem currently employer_name (nullable), withholding file, employment period, receipt date, exempt_grant_amount; **there is no employment_record_id link or retirement_event_id in either frontend contract**. Never infer a link from name/date alone or silently migrate it.
- Proposed *subject to domain authority and data/API review*: Historic employer → one or more employment periods / retirement-termination events → evidence-backed settlement allocations (paid exempt/taxable grants, רצף קצבה, רצף פיצויים, etc) with linkage to source products/payers and approvals; separate current-employer actual payroll/compensation facts and prospective scenario-owned future retirement/severance choices. Employer can have multiple events; settlement is not a single mandatory choice. Any existing detached grant must be shown as **unlinked pending reconciliation** until explicitly matched and confirmed, never automatically attached. A grants summary can expose an action to open the owner event instead of becoming a second independent write authority.
- Regulator references reviewed: ITA new 161 employer instructions; ITA 161ד 2026 guide and 161ג for sequences (source docs via gov.il). Distinguish the 161 historic-event record from 161ד eligibility calculation; do not assert a historic grant affects exemption without rules/evidence.
- **STOP further ad hoc grant/current-employer fields in existing cards.** Next implementation slice is evidence-based schema/backend audit, a decision record of required entities and migrations, and revised professional screen flow, then ask for targeted domain approval before new writes. Leave existing accepted UI/API backwards compatible; no speculative linking by name.
- Branch restriction stays: no main/master merge, production deployment, broad CI or unapproved financial calculations.

## AZ. Approved period-of-employment identity + backend FK discovery (2026-10-22)

- Owner explicitly corrected the architectural premise: each employer record represents one continuous employment period; after leaving and returning to the same company it is a new record, even when legal employer matches. One ended employment period has one settlement containing multiple components, not multiple termination events.
- Audited `backend/app/models/employment_record.py`, `backend/app/models/grant.py`, `backend/app/api/clients_routes.py` and `frontend/src/api/clientsApi.ts`. Correction to earlier assumption: ORM Grant **already has nullable `employment_record_id` FK** and employment relationship, but current public request/response schemas and create/update routes omit it, so user-facing data remains detached. Do not claim schema lacks any linking infrastructure.
- New controlled design/compatibility decision document `docs/ux/EMPLOYMENT_PERIOD_SETTLEMENT_MODEL_2026-10-22.md` at commit `62b7bea44cbb0bb67b51b0bed1b14551c0a7fdc6`. Explicitly prohibits automatic linking by employer name, silent data migrations, historical tax interpretation from grant amount, or duplicating a severance event for repeat employment.
- No production backend, migration, API or frontend mutation performed in this architectural slice. Next work: audit existing FK migration/use and contract-based linking with client isolation; current employer screen and historical settlement components remain separately scoped.

## BA. Explicit, guarded grant-to-employment-period backend contract (2026-10-22)

- Implemented backend-only endpoint `POST /api/clients/{client_id}/grants/{grant_id}/employment-link` with explicit `employment_record_id`. No automatic matching by employer name. Validates same-client record ownership, ended period, exact start/end dates, and refuses reassignment to another period (409). Supports repeat employment by the same legal employer as two independent records.
- Grant GET / POST / PUT public response now includes nullable `employment_record_id`; existing GrantRequest remains unchanged for backwards-compatible create/update. Existing unlinked grants stay unlinked until explicit user operation.
- Deletion of an employment record containing linked grants now returns 409 instead of attempting to orphan/delete linked historical facts.
- Commits: `537dac15926969824c37d04a31bb8dfcf63534d2`, `c3947e7e117d62584718b643bc7cc13d03243317`, `ca91a8ddd4c958ff8511bc8db3137155c586110f`. New isolated backend API tests cover link, reload, repeat employment, cross-client rejection, current period rejection, date mismatch, refusal to move and deletion guard.
- **NOT YET EXECUTED/VALIDATED**: backend tests require local Python+DB testing; do not claim acceptance or production readiness. Client-side link reconciliation control intentionally not yet exposed, pending browser flow review and accepted backend test results.
- Existing independent grant POST remains operational for legacy/back-compat; not yet the target employer-centred workflow. No backend migration, scenario calculation, full CI, master merge, or production deploy.

## BB. Linked grant integrity hardening, pending backend test execution

- Post-link consistency audit identified a gap: existing PUT grant and PUT employment period endpoints could diverge historical dates after an explicit link.
- Commit `61f2f6f0c9d646711d0bfcbc426f1fc89a644b5e` now returns HTTP 409 if a linked grant's employment start/end dates are changed to conflict with its period, or if a period with linked grants is changed to current or its start/end boundaries are edited. Non-identity employer-name/notes edits remain permitted. Historical grants already linked through the ORM FK are thus protected through both endpoints.
- Commit `7f52a49eec4e2adb3cca693411d72484098cf58a` added regression assertions for both invalid edit paths.
- **Backend tests have NOT RUN in this chat**. Next acceptance: check out feature branch locally and run isolated backend `pytest tests/test_employment_grant_link_api.py -q` inside compatible backend environment, preferably from a local one-off Docker Compose run without disrupting existing browser/server. Existing 22 frontend tests were already owner-verified before the API changes; these changes did not modify frontend.
- No automated matching or historical grant migration, UI-link control, scenario mutation, full CI, master merge or production deploy.

## BC. Offline backend verification command for grant-period link (2026-10-22)

- Confirmed `dev/compose.workspace.yml` maps live backend 127.0.0.1:18080, so launching another stack would collide with still-running user's browser environment.
- `dev/Dockerfile.workspace` installs pinned Python dependencies, copies backend source and test suite, including Alembic migrations. Added `dev/Test-Employment-Grant-Link.ps1` in commit `ed29bef6484a2b000ad89bcbd7e762ac46ce252e`: Docker builds standalone image and invokes `python -m pytest tests/test_employment_grant_link_api.py -q` in `--network none` container, no ports, no stack restart. Tests use disposable SQLite fixture.
- **Still unexecuted:** owner should pull then run `powershell -NoProfile -ExecutionPolicy Bypass -File ".\\dev\\Test-Employment-Grant-Link.ps1"` from repo root. Do not announce backend approval until actual output received. No CI or deployment.

## BD. Backend grant/period link tests PASSED (owner local Docker, 2026-10-22)

- Owner pulled feature HEAD `18b135dd454e08aeff7a152b28c5fc9d5ea02b30` and executed `dev/Test-Employment-Grant-Link.ps1` successfully. Docker standalone image built, pytest in `--network none` resulted **2 passed, 1 nonfatal Starlette/anyio DeprecationWarning, 7.10 s**.
- Regression test covers explicit historical period linking, repeated legal employer/independent periods, conflicting edits, current period and cross-client failures, and linked-period deletion guard. The running local dev stack was left untouched.
- Backend contract passes isolated tests; no UI integration or end-to-end linked-grant acceptance yet. Next implement explicit link UI in historic employment category and read-only linked/unlinked grants display, with user-confirmed matching; preserve existing grants and avoid hidden data changes.
- No CI, master merge or production deployment.

## BE. Explicit historical grant linking UI pending test validation (2026-10-22)

- Backend 2/2 link/API tests passed in independent, offline Docker image (owner-provided output). Follow-on feature branch implements UI through `79c22232fc000b901af840d0551daad4361eae7a` clientsApi typing and link POST wrapper, `2156486183437db513f8b6e112876e7283d44ebe` workspace historical employment row controls. Existing unlinked grant with matching dates is shown *as a candidate only*, never automatically linked; user must press the explicit link action and approve a browser confirmation. Current periods cannot link, and existing link ownership is visible. After successful save validate returned client/grant/period IDs and reload grants. Error/failed response never claims success.
- `a45e018d00afa1400e5f57840e7cdb2060ab707e` adds an interactive mocked frontend integration test using explicit window.confirm and API GET reload.
- IMPORTANT: Browser user's original FastAPI container is still running its **old built image**. Pulling GitHub into checkout does not update that backend; POST link endpoint will be missing (404) until local synthetic backend is rebuilt/restarted in a planned fashion. Do not advise launching another stack on bound port or claim live link E2E.
- Frontend new suite expected 23 total tests, **not yet run**. Existing grants section still has legacy create/edit controls; should be moved to employer-centered entry only after a transactional create-and-link API is designed, rather than chaining two writes and leaving orphan grants on partial failure.
- No master merge, production deploy or full CI.

## BF. Frontend suite verified and transactional historical grant creation API (2026-10-23)

- Owner pulled feature head `ada9f81`, built frontend with `tsc -b && vite build` successfully, and ran focused workspace suite **23/23 PASS**. Router future-flag warnings not failures.
- Implemented API `POST /api/clients/{client_id}/employment-records/{employment_record_id}/grants` at `f1b93c48ef3602505d3ef065b5399164d263196e`: one database transaction creates a historic grant with its explicit employment period FK. Checks same-client period, ended employment, exact period dates. Legacy grant creation remains unchanged.
- Added backend test at `16183267ab6183930e075a3305ae9374939c0d52`: atomic creation/readback and rejects active/cross-client/mismatched periods without orphan rows.
- **Not yet executed**: new backend test. Prior standalone `dev/Test-Employment-Grant-Link.ps1` runner can be reused to execute the now 3 focused backend tests. No browser UI for atomically creating linked grant yet; next integrate its frontend entry under historical employment after test approval, then deprecate independent grant input from supplement summary.
- Original local browser backend is still old Docker image; no port collisions or backend restarts should be triggered implicitly.
- No broader CI, master merge, production deployment, financial/tax calculations, or scenario mutations.

## BG. Atomic employer-centred historical grant creation frontend pending validation (2026-10-23)

- Owner pulled `8778cc5` and ran standalone Docker backend tests **3/3 PASS**, 1 nonfatal Starlette DeprecationWarning. Existing dev server unaffected.
- Frontend commits: `6bc6dfb406b4d13a3179903c629af72d28437dfe` (typed API atomic POST), `083887cfd75a4902de0277e93471d80cdd82591c` (create a linked grant only from an ended employment period row, prefill employer + period dates; grants summary no longer has independent create action; link to legacy overview and editing remain temporarily), `6f6e11b6f8668a825934df0c38bc91ecb0a75d88` (replace old detached creation test with linked creation/refetch).
- Existing standalone grant update remains for backwards-compatible editing. There is no new retirement/exemption calculation and no current-employer grant-create action.
- **PENDING:** owner needs a single frontend `npm.cmd run build` and focused Vitest suite (23 tests expected) from frontend after git pull. Docker backend on 18080 remains the older running container and will not expose the atomic API until a controlled refresh. Do NOT claim browser end-to-end acceptance of this new feature.
- No CI, master merge or deployment.

## BH. User acceptance revealed flawed employment settlement UX and duplicate exempt-grant invariant (2026-10-23)

- User screenshot confirms linked exempt grants of 123456 and 2500 NIS under same historical employment period; this violates user's explicit **one exempt severance grant per employment period** business rule. Both records are synthetic. Do **not** infer which value is correct or delete/merge automatically.
- User correctly identified that adding a historic employer via the workspace still has no settlement fields; asking to create a grant afterwards is the wrong business workflow. **Current UI is incomplete and not professionally accepted.** Previously declared link/Create E2E as accepted would be misleading.
- Hotfix backend API commit `b75833909c8ebd6d3baa19f07184ed50a8da017c` returns 409 on second linked exempt grant in atomic create and explicit link routes. Test commit `6f388167b3bff40a5d737ee0243ebfca3623ba12` adds duplicate create/link assertions. UI commit `b8e9b61ea7d13f734cb523844d1b29cdfcc9fb13` disables create/link where an exempt grant already exists and warns if multiple currently linked.
- **Not a complete solution:** HTTP pre-check can race in parallel requests; DB uniqueness constraint should follow data reconciliation and migration design. Existing synthetic duplicate remains intact for visual detection. Do not apply uniqueness migration before reconciling. The consolidated historical employer form must capture employment plus factual 161/settlement fields in one workflow/transaction, including explicit no-grant/not-yet-known distinctions and statuses; model other settlements separately from the one exempt grant field. Avoid treating 161 tax classifications as computed or approved from a single entry. An employment can exist without a positive exempt grant; require appropriate choice instead of forcing an amount. Current employer remains different.
- **Next actions:** verify existing test suite with owner; design and implement atomic employer+settlement creation after data model and professional fields approved; retire separate grant-creation UI rather than instruct user to create a grant manually; do not consider UI accepted. No CI, master merge or deploy.

## BI. Employer-first historical exempt severance intake (2026-10-23) — pending new focused tests

- Owner reported a UX/domain regression after live browser attempt: two linked exempt grants under one period, and no exempt-grant input in historical employment creation. This is **not accepted** as a correct professional workflow.
- Implemented initial create-only **atomic historical employment + optional exempt grant** API `POST /clients/{client_id}/historical-employment-settlements` (`26abe8aba2769d6ffcee1b086c3ed54445c6ad51`) requiring ended employment and explicit UI choice `recorded / none / not_reviewed`. For recorded status the same DB transaction creates the period and precisely one linked grant. Missing status required; missing amount is never converted to zero. Test (`7edc11c12874819f395f63524c9547fd179cdea6`) asserts no orphan on validation error and multiple periods of same legal employer remain distinct.
- Frontend API (`89b56c630033dcc1a9538cc27e6d69a97dbd0679`) and integrated historical employment create form (`dc43c358665c2b4bc0ac86967b2ee89955172289`) now ask status/withholding file/receipt date/amount *within the employer intake*; added focused test (`4bee560a29db4e7ae129d30b273f7eb5d369b03a`). Existing current-employment creation stays on old POST. This **does not yet replace editing existing historical employers**, nor capture taxable grants, pension/severance continuity, verification and source documents.
- Important limitation: `none` and `not_reviewed` are currently *request-time decisions only*, not persistently distinguishable in the existing employment table (both create no grant row). Before professional release, add explicit persisted settlement status and source provenance with approved migration. Avoid claiming durable not-reviewed distinction; read-side currently sees both simply as no linked grant.
- Duplicate-control backend checks are application-side pre-checks, not race-proof uniqueness constraints. Migration and existing duplicate reconciliation remain unresolved. Do not delete synthetic duplicates silently.
- New backend test count expected 4, frontend workspace suite expected 24. **Both not executed yet.** Running browser backend still old image until deliberate refresh.
- No CI, master merge or production deploy.

## BJ. Focused test regressions diagnosed and patched (2026-10-23)

- Owner ran tests against HEAD `30992c8`; frontend build PASS, backend pytest **3 pass / 1 fail**, frontend Vitest **23 pass / 1 fail**. Both failures are within the new employment settlement development slice.
- Backend failure: test asserted `get_grants()[0]` was the linked original grant after creating a second unlinked grant. API orders by randomized grant_id, not insertion. The test relied on an invalid ordering guarantee, not evidence that the stored FK was lost. Fixed assertions to find the original `gid` explicitly (commit `85b80ed8eabd3a9052977d198c526f0bb91245b1`).
- Frontend failure: the newly added preflight validation used literal regex `/^\\d{4}-\\d{2}-\\d{2}$/` rather than `/^\d{4}-\d{2}-\d{2}$/`; it rejected every normal grant receipt date and prevented the API call, exactly matching the displayed form error. Fixed one regex (commit `b250268c7fdc39072967884a7b4f6cb30d0e6932`).
- **Retest required:** same isolated Docker script (4 expected) and focused Frontend Vitest suite (24 expected). Do not claim success until user output. No master merge, deployment or global CI.

## BK. Owner verified focused regression fixes (2026-10-23)

- Owner pulled `a133c24` and reran `dev/Test-Employment-Grant-Link.ps1`: **4 passed**, one nonblocking Starlette DeprecationWarning, 22.50s.
- Owner reran frontend `npm.cmd run build`: `tsc -b && vite build` **PASS**, 76 modules. Focused `RetirementWorkspaceScreen.test.tsx`: **24/24 passed**; two React Router future-flag warnings only.
- Both previous failures from BJ resolved. This is code-level acceptance only, NOT PostgreSQL browser end-to-end acceptance for employer-first historical settlement form. Running Docker server may still have an older image. Existing two linked synthetic exempt grant amounts remain unresolved; do not mutate or delete them automatically.
- Business incompleteness: persist reviewed/none/not-reviewed status, full severance settlement evidence/components, uniqueness enforcement and reconcile legacy duplicates before schema constraint, current-employer separate facts. Keep isolated feature branch; no full CI, merge or deployment.

## BL. Persisted historical-settlement status design gate (2026-10-23)

- Owner supplied confirmed `dev/Test-Employment-Grant-Link.ps1` **4/4 PASS**, and workspace Vitest **24/24 PASS** and frontend build PASS. These are targeted code validations, not full browser E2E for employer-first flow.
- Audited ORM `EmploymentRecord`, Alembic environment, request contract. Existing employer-first create endpoint accepts `not_reviewed / none / recorded`, but the first two are currently indistinguishable after reload because no persisted settlement status exists. Do not present those choices as durable until migration.
- Added document `docs/ux/HISTORICAL_EMPLOYMENT_SETTLEMENT_PERSISTENCE_GATE_2026-10-23.md` at `946ceb3eb8317326e55a91a06d317670e0dca3a6`, covering one-to-one settlement, source/status, backfill that preserves existing duplicates and unlinked data, read/update contracts, and conditional DB uniqueness guard after reconciliation.
- Do not invent an Alembic `down_revision`; actual migration heads still need exhaustive verification before a schema change. Thus this slice intentionally changes documentation only, not DB or API. Next task: precise heads/permissions audit then additive migration and positive/negative tests; no production deployment.

## BM. Safe migration-head discovery tool (2026-10-23)

- Created `dev/Inspect-Settlement-Migration-Heads.ps1` (head `8e77b26ee5c8f486a74a69a204b668381d6dc2d4`). It builds the local existing backend workspace test image, then executes `alembic heads --verbose` and `alembic history -r base:heads` in an offline, disposable container. No database connection, migration application, running-stack restart, network access, port binding, CI, or deployment.
- Motivation: 46 Alembic revision files and uncertain graph heads. Do not guess `down_revision` for a one-to-one historical employment settlement status table. Existing user-confirmed synthetic duplicated linked grants would make an unconditional unique FK constraint unsafe.
- Next: derive authoritative migration heads from audit output, implement additive status persistence and safe backfill with duplicate reconciliation status; test against fresh ephemeral SQLite and synthetic PostgreSQL without deleting live test records.

## BN. Persisted exempt grant state migration, pending isolated test (2026-10-23)

- Owner ran read-only Alembic audit: exactly one head, `c4e8a2f6b731`, parent `b3c9d6f2a410`. Full graph from base confirmed.
- New revision `d2c4e6a8b031` (parent `c4e8a2f6b731`) adds constrained non-null `employment_records.exempt_grant_status`; SQLite-compatible batch operation. On upgrade historic periods: 0 linked grants -> `not_reviewed` (NEVER infer none); 1 -> `recorded`; >1 -> `requires_reconciliation`, preserving duplicate rows and amounts. No unique index or grant deletion.
- ORM/API create and read now persist and expose statuses; employer-first API `none` remains distinguishable after reload, with read-only workspace display. Explicit linkage and grant creation set `recorded`; explicit grant deletion recalculates status and never infers `none`.
- Added isolated backend test to verify persisted status readback across all 3 user choices. New expected focused backend count **5**, existing frontend workspace count **24**, pending verification.
- **Outstanding design**: finished-period edits and verification/source evidence, source-of-truth for duplicates, final DB uniqueness constraint after reconciliation, full taxable and continuity components, independent current employer workflow. Do not assume professional acceptance, do not restart synthetic DB stack, and do not deploy or run full CI.

## BO. Legacy duplicate migration regression (2026-10-23), pending execution

- Added `backend/tests/test_historical_settlement_migration.py` to apply migration `d2c4e6a8b031` via Alembic Operations on a deliberately crafted **disposable SQLite** pre-migration employment/grants schema: 2 linked grants on a single period, 1 grant on another, no grant on a third, plus active current employment.
- Asserts duplicates remain untouched with `requires_reconciliation`, single linked grant -> `recorded`, missing/current -> `not_reviewed`, and explicit `none` persists. The test is migration-specific, not the existing five API tests.
- Added `dev/Test-Historical-Settlement-Migration.ps1` to rebuild the isolated test image and run only this migration test with `--network none`, without changing the active PostgreSQL service, stack, local data or full CI.
- **Important**: this is SQLite coverage, NOT a PostgreSQL-specific migration acceptance. A fresh isolated PostgreSQL test is still required before applying to the active local PostgreSQL DB. No migration has been applied to the running service. Do not claim test passed before user runs it.

## BP. Isolated PostgreSQL migration regression script (2026-10-23)

- Owner confirmed 1/1 SQLite migration probe PASS with synthetic duplicate grants preserved and active PostgreSQL untouched.
- New `backend/tests/postgres_historical_settlement_migration_probe.py` creates a representative pre-migration schema **inside a dedicated disposable PostgreSQL database**, inserts two grants on one historical period, one on another, no grant on third, and current employer; applies migration `d2c4e6a8b031` through Alembic Operations and verifies statuses, exact unchanged grant rows, `none` persistence, invalid-status constraint, and downgrade removing new column.
- New `dev/Test-Historical-Settlement-Postgres.ps1` builds existing test image, creates its own random isolated Docker network and ephemeral PostgreSQL:16 container with tmpfs and **no published ports**, runs probe through a throwaway backend container, and removes only those uniquely named temporary test resources in `finally`. It never uses the active compose project, ports, DB credentials, or Railway. **Pending owner execution**; do not claim PostgreSQL PASS yet.
- This tests the migration against a deliberately minimal legacy schema, **not full-schema Alembic upgrade from actual production/synthetic data**. Follow with full-stack isolated migration acceptance before applying the migration to live local test DB. No CI, master merge or production deployment.

## BQ. PostgreSQL isolated migration probe PASSED (2026-10-23)
- User pulled `0410e28` and ran `dev/Test-Historical-Settlement-Postgres.ps1` successfully: `PASS: isolated PostgreSQL upgrade/backfill/constraint/downgrade; grant rows preserved` and `PASS: independent PostgreSQL historical-settlement migration. Workspace database untouched.`
- Verified behavior: the migration preserves both historic duplicate links while flagging reconciliation, preserves one linked grant, does not infer `none` from no grant, supports explicit `none` and check constraint, and downgrades. These results use a **reduced representative PostgreSQL schema**, not full application Alembic history.
- Remaining gate before applying to running temporary PostgreSQL: test full real Alembic chain against a completely separate fresh PostgreSQL database, seed duplicates at parent `c4e8a2f6b731`, migrate to `d2c4e6a8b031` and inspect records. Never stop/recreate running workspace DB (tmpfs). No full CI, master merge, or deployment.

## BR. Full-chain isolated PostgreSQL migration acceptance probe (2026-10-23) — pending execution

- Owner confirmed the representative PostgreSQL migration probe PASS on `0410e28`. Handoff recorded at `a55d9bb`.
- Added `backend/tests/postgres_full_history_settlement_probe.py` and `dev/Test-Historical-Settlement-Full-Postgres.ps1`. Isolated PostgreSQL:16 test container (random name, no host port, tmpfs, own network). In the disposable database only, execute **actual full Alembic history** to verified parent `c4e8a2f6b731`, create a synthetic client and employment periods, seed two unequal exempt grant amounts on one period, one on another, none on third, plus current employer, execute new migration `d2c4e6a8b031`; assert stored statuses and exact preserved grant amounts. The PowerShell wrapper does not reference the active Compose project, and deletes only its own named throwaway resources.
- New full-chain test has NOT run; failures, if any, must be diagnosed from results. In particular some older full history migrations may require prerequisites the minimal isolated probe did not exercise. Do not assume success.
- No full CI or master/deploy. Do not restart active workspace PostgreSQL.

## BS. Full-chain PostgreSQL probe blocked by missing CRTISBA app role; isolated wrapper repaired (2026-10-23)
- User ran `dev/Test-Historical-Settlement-Full-Postgres.ps1`: entire earlier Alembic chain reached revision `c4e8a2f6b731` but failed there with `RuntimeError: CRTISBA_APPLICATION_DB_ROLE is required for PostgreSQL`. The new historical settlement migration was NOT reached. This is test harness misconfiguration, not evidence that the new migration fails.
- Confirmed `c4e8a2f6b731_crtisba_source_basis.py` requires a pre-existing PostgreSQL application role and environment variable in order to issue explicit restricted grants. The isolated probe now creates `settlement_probe_app NOLOGIN` in its own throwaway PostgreSQL container and supplies `CRTISBA_APPLICATION_DB_ROLE=settlement_probe_app` to the test process (commit `60737f8fbbcc80e97a2203f8bb8b8894f871fe0a`). No application/production migration changes, no active DB or running Compose access.
- Full-chain retest **pending owner execution**. Preserve current tmpfs active Postgres; do not run full CI.

## BT. Full-chain PostgreSQL migration PASS; guarded local synthetic update prepared (2026-10-23)
- User executed `dev/Test-Historical-Settlement-Full-Postgres.ps1` on `b0acac8`: **PASS**. Complete Alembic history through parent `c4e8a2f6b731`, seeded synthetic duplicate grants, upgraded to `d2c4e6a8b031`, and verified statuses and exact grant amounts. This was a fresh isolated PostgreSQL, not the active workspace DB.
- Added `dev/Apply-Historical-Settlement-Local.ps1` on branch: guarded local-only migration and backend-only recreate. It checks the expected running synthetic DB container and DB name/user, creates a timestamped **binary pg_dump custom-format backup** copied from the container, validates archive readability, recreates **backend only** with `--no-deps`, checks backend health and Alembic revision `d2c4e6a8b031`, and lists historical status counts. It does NOT run compose down or recreate the tmpfs PostgreSQL container. Backup directory `dev-local-backups` in user's root is locally generated: don't commit this directory.
- **New script has NOT been tested on owner's machine yet.** Owner should review/run only when ready; stop on any guard failure, never reset DB. Existing synthetic duplicate grants must remain intact.
- Current UX remains incomplete for taxable grants, 161 evidence, continuity and existing-employer settlement edit. Do not mislabel this stage as professionally accepted. No master merge, production deployment or full CI.

## BU. User-verified active local synthetic PostgreSQL upgrade (2026-10-23)
- After guarded `dev/Apply-Historical-Settlement-Local.ps1` took a valid custom-format backup (`dev-local-backups/retirement_v2_synthetic-20261023-123438.dump`) and recreated **backend only**, the script itself stopped during `alembic current` because Windows PowerShell interpreted Alembic INFO on stderr as an error. This script issue was patched in commit `bca0cf5426b10252e7a5c8bf847d23a0f0ed5cc1`.
- User verified separately (no additional migration): Docker backend health `healthy`; GET `http://127.0.0.1:18080/health` -> `ok`; current DB `alembic_version` -> `d2c4e6a8b031`; aggregate historical `exempt_grant_status` -> `requires_reconciliation|1`. The active synthetic DB remained running and now contains migrated status.
- Do not rerun guarded migration script, stop active tmpfs DB, or reset synthetic test records. Technical DB upgrade accepted. Next: existing-historical-employer settlement edit and duplicate reconciliation UX and tests, without automatic deletion of either synthetic grant.

## BV. Edit historical exempt-grant status in existing employer workflow (2026-10-23) — focused tests pending

- Owner confirmed active local synthetic DB: Backend healthy, GET /health ok, Alembic `d2c4e6a8b031`, one historical period status `requires_reconciliation`. The pre-migration custom dump is stored locally. No further DB migration required.
- Implemented optional `exempt_grant_status` on the existing employment PUT, in its same database transaction as employment metadata. The server permits explicit `none` / `not_reviewed` ONLY if the historical period has **zero linked grants**; refuses false `recorded` or `requires_reconciliation` without grants (409). For one linked grant it accepts only `recorded`; multiple linked grants only `requires_reconciliation`. Current employment cannot receive settlement status (422). Omitted status preserves backward compatibility with existing caller.
- In professional workspace, historical employer edit shows settlement section, allows status selection when zero linked grants, and visibly locks status if grant is linked or needs reconciliation; sends status with employer PUT atomically. No grant is deleted/relinked automatically.
- Added focused Backend test `test_historical_status_edit_guarded_by_actual_grant_links`, expected backend tests now **6**. Changes not yet tested on owner's machine. Frontend compile + focused 24 tests need rerun due JSX/form change. Guard must not be called 'professional closure' pending receipt/evidence fields and full termination model.
- No CI, master merge or production deploy. Do not restart local tmpfs DB. Code branch only.

## BW. User browser confirmation and dual editor entrypoint cleanup (2026-10-23)
- User browser screenshots confirm local backend `healthy`, /health `ok`, existing historical period `Synthetic Employer After` shows `נדרשת בדיקת כפילות`, both linked grants 2500.00 and 123456.00 remain visible, and status editing locked in inline workspace employer form. Existing legacy `פתיחת עריכה: רשומות תעסוקה` link was sending user to an older unrelated editor, confusing the workflow.
- Removed duplicate legacy employment navigation link from the supplementary panel and labelled inline employer correction as canonical workflow. Grant panel retains clearly marked link `פעולות מענקים נוספות בממשק הוותיק` because not every grant action is yet replaced. Other category links unchanged.
- Updated frontend focused test that formerly asserted the legacy employment link, to expect no old employment link and an explicit legacy grant fallback. Changed only frontend and test; no local DB or backend changes, no CI/master/production.
- Pending owner run: `npm.cmd run build` and `npm.cmd exec vitest -- run src/pages/RetirementWorkspaceScreen.test.tsx` in frontend folder. Existing Vite dev server should hot-reload after `git pull`.

## BX. Legacy employment navigation cleanup frontend verification PASS (2026-10-23)
- User pulled commit `76c029d`; `npm.cmd run build` passed (TypeScript + Vite, 76 modules), and focused workspace Vitest suite passed **24/24** including updated test `uses workspace employment editing and labels legacy grant fallback explicitly`.
- React Router v7 future-flag warnings only, not test failures. Backend earlier **6/6** and active local backend `healthy` / /health `ok` from prior owner verification. No further migrations are required.
- Next UX stage: historical-employment termination components and evidence are **not yet modeled**. Do not invent professional contracts or treat taxable grants, continuity elections, 161 forms as fully supported. Preserve two linked synthetic exempt grants, keep status `requires_reconciliation`, maintain distinction current employer vs historical factual settlement.
- No master merge, production deployment or full CI.

## BY. Credit-efficient three-role methodology and next UX-only slice (2026-10-23)
- Owner requests preserving low credit cost of direct in-chat development **while retaining three-role methodology**: direct bounded coding, Codex for complex implementation / independent implementation handoff, Work for substantive independent review at gates. Do not spend review credits after every small commit. Governance playbook section 10 now records scope, explicit independent review and acceptance boundaries.
- Added scenario and comparison **UX-MOCK/read-only process descriptions**, no new calculation, scenario persistence, APIs or database writes. Five professional steps include named alternative, source, scenario-only decision, review/reversal, and separately validated evaluation; results phase specifies planned comparison, stale-result disclosure and professional decision context. Clearly labelled wireframe text rather than functioning scenario features.
- Changes are branch-only; local frontend build/focused Vitest **not yet run for this newest text change**. No CI, master merge, production deployment, database or backend changes.
- Follow-up: one focused frontend build/test if/when owner pulls; then owner UX review of practical complete scenario journey before any authoritative implementation. Independently reviewed business contracts remain separate.

## BZ. UX mock scenario/comparison visual workflow (2026-10-23)
- On the isolated branch, replaced scenario-only descriptive list with a **non-executable conceptual workspace table** for baseline + two hypothetical alternatives, and four-step professional decision lifecycle. These are *labels and plan only*, no actual persisted scenarios or scenario API calls.
- Replaced comparison placeholder paragraph with scrollable comparison **structure**: retirement date, allocations, monthly pensions, capital draw, taxes/exemptions, evidence and freshness, all cells explicitly `לא חושב`. No invented estimates.
- Expanded the existing focused scenario navigation test to check two `טרם נוצרה` states, no fictitious computed result (21 cells), and no factual product write calls. Latest UI changes and test assertions remain **pending user's local TypeScript/Vitest execution**.
- Guardrails: `UX-MOCK`, in-chat bounded update; Codex and Work reserved for material implementation/review gates to conserve credits. No schema change, DB migration, backend change, master merge or production deploy.

## CA. Owner-confirmed UX mock build/test pass (2026-10-23)
- Owner pulled `c05d56e` to local Windows workspace. `npm.cmd run build` succeeded (TypeScript and Vite 76 transformed modules); focused `RetirementWorkspaceScreen.test.tsx` passed **24/24**, including scenario/results read-only/no factual writes assertion. React Router future-flag warnings nonblocking.
- This validates presentation and existing focused interactions only, not scenario implementation or professional calculations. Work/Codex independent review not invoked; reserve for substantive domain/implementation gate. No backend/database changes, CI, merge or deployment.

## CB. Interactive scenario UX-only exploration (2026-10-23)
- Owner requested continuing cost-conscious UX prototyping with independent Codex/Work checkpoints reserved for substantial implementation/acceptance.
- Added an **in-memory, client-scoped, temporary scenario decision walkthrough** in the React workspace: create a named test alternative, select a displayed pension product as conceptual source, select an intended pension/capital/unchanged action, add/cancel mock decision, duplicate/delete mock alternative. All labels stress these are conceptual choices, **NOT amount allocations, eligibility determinations, approved tax calculations or persisted scenarios**.
- Drafts are React state only and reset on client route change or refresh; no backend calls, factual balance changes or scenario engine added. Comparisons remain entirely `לא חושב`.
- Added a focused Vitest interaction test; **latest changes have not yet been run on local Windows**. Expected focused count 25 if pass. No full CI, code review by Work, master merge or deployment. Do not present this as accepted domain behavior.

## CC. Interactive mock test PASS, correct scenario selection granularity (2026-10-23)
- Owner pulled `e805769`; local `npm.cmd run build` succeeded and focused Frontend Vitest passed **25/25**. Only React Router future warnings.
- Design correction in isolated UX branch: the mock previously chose an entire pension product as a conceptual source, contrary to the professional 11-column ledger selection model. Changed the temporary scenario dropdown to offer only **positive, reported monetary components** identified by `product_id|classification_code`; its display includes product, component name and existing amount. This is presentation of reported facts only, not an eligible or executable allocation. Decision summaries now show the specific source component. Updated the single focused scenario test with the component value.
- No amount splitting/eligibility/financial calculations or backend writes have been introduced. The mock can still record more than one conceptual action on a component because it does not allocate actual amounts; this is not scenario-engine authority.
- Latest component-granularity change is **pending local build/Vitest**. No CI, Work/Codex spend, schema change, master merge or deploy. Owner UX review needed before treating workflow direction as accepted.

## CD. Component-level scenario mock test failure diagnosed and fixed (2026-10-23)
- Owner pulled `9406b42`: TypeScript/Vite build **PASS**, focused tests **24/25**. The single failing scenario mock interaction test found no `בטל החלטת הדמיה` button because the new component source selector presented **zero** valid options and add button remained disabled.
- Cause is the **incorrectly double-escaped JavaScript regex literal** added in component dropdown filtering, matching backslashes rather than digit/decimal notation. This is a UI prototype filter bug, NOT evidence of a backend, tax, or PostgreSQL error.
- Fixed dropdown match with escape-free `/^[0-9]+(?:[.][0-9]+)?$/` plus zero exclusion `!/^0+(?:[.]0+)?$/`; amended focused test to assert visible positive component option *before* selecting or adding a decision.
- The fix and test update are **not yet run on owner's local Windows**. Expected 25/25 if successful. Only in-memory mock UI changed; no financial math, backend, DB, CI, master merge or production deploy.

## CE. Owner verified component-level scenario mock fix (2026-10-23)
- Owner pulled `b7f85c2`, TypeScript/Vite build succeeded (76 modules), focused `RetirementWorkspaceScreen.test.tsx` **25/25 PASS**. The positive-component selector regex bug is closed. React Router future-flag warnings nonblocking.
- Component-granularity choices and mock create/copy/cancel interactions are **UX-only**, in React memory; no persisted scenario, calculation, or protected business logic approval.
- Preserve budget methodology (direct small UX changes; Codex implementation gate and Work independent review for substantive domain changes), no repeated CI. Next substantive UX consideration: owner hands-on professional journey review, no authority to implement scenario engine from this test.

## CF. GitHub edit-tool interruption and bounded recovery (2026-10-23)
- User requested continued budget-conscious UX work and asked about recurring GitHub problems. The prior large single edit was rejected by an OpenAI tool safety check **before any GitHub write**; it was not GitHub's rejection. Confirmed branch unchanged immediately after refusal. Reattempted as small, separately auditable commits, all accepted by GitHub.
- Extended transient mock scenario decisions to include a user-entered partial monetary amount in **integer cents using BigInt**. Checks require positive, max 2 decimals and aggregate decisions from same monetary source <= currently reported component amount *within the same mock alternative*. Decisions in other alternatives are independent. The mock renders the amount and a rejection notice for invalid/excess allocations; cloning and cancellation keep the temporary state behavior.
- Updated focused test to enter 40 of 100 and reject an additional 70 on the same component. No database, APIs, professional eligibility or tax authority changed; amounts are mock only. **Changes are pending owner's local frontend build/Vitest execution**, not accepted yet.
- No CI, Codex, Work spend, master merge or deploy. If failed, fix narrowly rather than rerun full checks.

## CG. Owner-confirmed partial-allocation mock tests (2026-10-23)
- Owner pulled `0e4fd31`. TypeScript/Vite build PASS; focused workspace Vitest **25/25 PASS**, including mock partial amount input, aggregate no-overallocation guard, duplication/cancellation and no financial writes. Only React Router future-flag warnings.
- Partial allocation is a client-side mock, not persisted scenario or validated retirement calculation. No more testing of this unchanged slice required. Next gate is professional full-journey UX review and independent scrutiny before implementation of authoritative scenario workflow. No CI/master merge/production deployment.

## CH. UX journey review and dynamic mock comparison (2026-10-23)
- Recorded formal in-chat UX gap review in `docs/ux/SCENARIO_WORKFLOW_UX_REVIEW_2026-10-23.md`, with separate independent Work review still **PENDING**.
- Updated `RetirementWorkspaceScreen.tsx` comparison mock: dynamic columns correspond to **actual temporary alternatives created** in Step 4, with in-memory decision counts and source-component/amount/action summaries. Retains `לא חושב` for every modeled financial metric; no calculation/persistence. Thus supports scenario → comparison → back-to-scenario journey for UX testing.
- Adapted focused Vitest expected uncalculated baseline count and asserted duplicated alternatives/decision amounts appear after step navigation. **LATEST CHANGES NOT YET RUN**: owner should execute local frontend TypeScript/Vite build and the existing focused 25-test suite once.
- No Backend or database modifications, no full CI, no Work/Codex credits used, no master merge or production deploy.

## CI. Owner-verified dynamic comparison and portfolio-to-scenario UX handoff (2026-10-23)
- Owner pulled `38f12a2` and verified TypeScript/Vite build PASS and **25/25** focused workspace Vitest tests PASS (only nonblocking React Router warnings). Dynamic ephemeral comparison is validated.
- Added an isolated **UX-MOCK one-way handoff** button in the factual ledger's selected-components panel: selecting exactly one component with a positive numeric factual balance and no unsaved edit transfers its product+classification identifier into the transient scenario source selection, then switches to Step 4. This creates no mock decision automatically, does not change the factual ledger and makes no financial API call; multiple/zero selections cannot trigger it.
- Added one focused test exercising selection → handoff → create preview alternative → selected source preserved without financial write. Latest UI/test changes **not yet locally verified**; expected **26/26** focused tests if pass.
- Strictly no Backend, schema, domain calculation, full CI, production release, or Work/Codex invocation. Professional UX acceptance and independent architectural review remain pending.

## CJ. Owner-confirmed portfolio-to-scenario UX handoff (2026-10-23)
- Owner pulled `bc6cf38`; TypeScript/Vite build PASS and focused workspace Vitest **26/26 PASS**, including single-component handoff to transient scenario and no financial API mutation. React Router v7 future warnings only.
- Working UX mock journey: factual ledger → exact component selection → scenario preview → partial mock decisions → ephemeral alternatives → dynamic comparison. This is not approved scenario-engine functionality. Next step is a hands-on professional UX walkthrough and independent Work review at the substantive implementation gate, rather than further speculative backend code. No CI/merge/deploy.

## CK. Formal in-chat professional UX readiness gate (2026-10-23)
- Updated `docs/ux/SCENARIO_WORKFLOW_UX_REVIEW_2026-10-23.md` following owner-verified **26/26** focused tests, marking dynamic comparison and factual source-component handoff as UX-MOCK complete.
- Documented pending business-domain gates: `unchanged` mock action allocation semantics, source provenance/version and stale detection, historical grant reconciliation/eligibility prerequisites, alternative editing/naming, and baseline-comparison contract. None are authoritatively designed or implemented merely because the UI passed tests.
- **No new executable code** in this step; no need to rerun local build or tests. Next checkpoint is owner reviewing the actual synthetic client flow, then one bounded independent Work review prior to Codex-authoritative scenario persistence or engine. No CI, DB, merge or deployment.

## CL. Ready-to-run professional UX acceptance on synthetic case (2026-10-23)
- Created `docs/ux/SCENARIO_OWNER_UX_ACCEPTANCE_SCRIPT_2026-10-23.md`: concrete nine-step walkthrough in the locally running V2 synthetic client from ledger source through two partial mock decisions, over-allocation rejection, copy/revise, dynamic comparison, and mock reset. Includes observable criteria and owner sign-off categories.
- Called out UI limitations rather than inventing implemented features: no direct in-place decision edit, no remaining-unallocated display, no professional timing/eligibility/tax calculation, no persisted scenario/source freshness contract. Independent Work review and owner's hands-on UX acceptance both **PENDING**.
- No executable code changed and no additional local build/Vitest is needed. No CI, Railway, DB migration, master merge, deployment or Codex/Work credit consumption. Next meaningful input: owner's professional observations from the scenario UX walkthrough, not a technical shell log.

## CM. Owner professional feedback accepted with changes, immediate UX refinements (2026-10-23)
- Owner reviewed all nine synthetic-case UX acceptance steps. Existing wide ledger accepted; must later show imported reported total **and** computed sum; editing via cancel/recreate acceptable now, scenario storage undecided.
- Critical new professional scope: support **entire pension plans as well as individual source components**. Do not assume mass plan conversion is legally/financially identical across its classified monetary components. Pending owner/professional domain contract for how whole-plan selection decomposes and eligibility/tax provenance remains intact.
- Implemented in-chat mock refinements: for selected classification, display original source balance, amount assigned in active alternative, remaining unallocated, using exact integer cents; high-contrast over-allocation error; dynamic comparison adds nominal **principal designated** pension/capital rows (explicitly *not* monthly pension or approved withdrawals), and leaves whole-portfolio remaining **uncomputed**. Future results must include actual capital, monthly pension, unused funds, eventually NPV only when authoritative engines validate them.
- Added focused Vitest assertions for remaining source balance and altered uncomputed rows. **Most recent commits NOT YET verified locally**; owner should run the usual Vite/TypeScript build and focused workspace test ONCE. No backend/DB, CI, merge or deploy; Work/Codex review not invoked.
- Formal review updated: `docs/ux/SCENARIO_WORKFLOW_UX_REVIEW_2026-10-23.md`. Professional UX direction is **approved with changes / extended hands-on needed**, NOT a final domain architecture authorization.

## CN. Owner-confirmed balance-context mock refinements (2026-10-23)
- Owner pulled `e6ab63e`; frontend TypeScript/Vite build PASS and focused workspace Vitest **26/26 PASS**. The original/current/remaining selected-component context, prominent validation warning and nominal mock allocations summary compile and meet existing focused UI tests.
- Main open professional UX priority: selecting a **whole pension plan as well as individual components** without hiding component-level tax classification or implying plan-wide financial eligibility. Do not implement direct canonical conversions or persisted scenario engine from this prototype.
- No need to rerun unchanged focused tests. Work independent review and final financial-domain acceptance still pending. No CI, production deployment or merge.

## CO. Whole-plan scenario source preview, preserving classifications (2026-10-23)
- Owner accepted 26/26 tests for mock balance/availability and nominal comparison UX on branch `e6ab63e`, before this change. User explicitly needs **both whole-plan and individual-component** scenario entry.
- Added a **non-executable whole-plan preview** dropdown to the factual ledger selection toolbar. Choosing a plan enters Step 4, shows its positive classified monetary components separately with actual source amounts, and allows focusing an individual component for a mock allocation; no automatic bulk allocation or tax-class aggregation. The existing single-component handoff remains.
- Added focused Vitest coverage verifying two distinct classification sources survive choosing whole plan, and focusing a component does not write financial data. **Latest code/test are not locally verified**; expected **27/27** focused cases once owner builds/tests. There is no eligible 'convert entire plan' operation yet: business design must decide decomposition, eligibility, and overrides before actual engine.
- No Backend/database/CI/merge/production changes, and no Codex/Work credit spend. Independent business acceptance pending.

## CP. Owner verified whole-plan classified preview (2026-10-23)
- Owner pulled `201fa04`; TypeScript/Vite build PASS and focused `RetirementWorkspaceScreen.test.tsx` **27/27 PASS**. The whole-plan source preview displays components separately and makes no financial API writes; warnings are React Router future flags only.
- UX mock supports plan selection for review, but **not** a single bulk financial conversion. Owner requirement for plan-wide actions with preserved classification is open for explicit professional rules and reviewed design. No additional code or full CI needed for this validated slice. No Backend/DB/master merge/production deploy.

## CQ. Critical V1-derived conversion legality gate (2026-10-23)
- Owner requires V2 to enforce V1-style permission rules separately for EACH pension portfolio classification: not every monetary column can be converted into capital. V1 displays rejection errors. Whole-plan choices must preserve all component rules.
- Inspected V1 `app/services/pension_portfolio/conversion_rules.py`, `frontend/src/config/conversionRules.ts`, conversion settings UI and conversion hook on `omerb21/retire` main. Documented 11 classification permissions, special product-type overrides, unsettled severance prerequisites and browser/server mismatches at `docs/ux/V1_TO_V2_CONVERSION_RULES_GATE_2026-10-23.md`.
- In isolated branch, added an explicitly **UX-MOCK, NON-AUTHORITATIVE** eligibility guard mirroring V1 server permission matrix, and wired it to mock decision creation. Disallowed conversions show visible error and do not enter local scenario; unknown classes fail closed. Added focused unit tests and UI interaction test.
- **These changes are PENDING LOCAL TEST**. Existing earlier owner evidence: TypeScript/Vite build and 27/27 focused workspace tests passed at `201fa04`; new expectation: **28 focused workspace cases plus new rule unit test file**. Run targeted frontend build + both focused tests once. No CI/master merge/deploy.
- **Authoritative V2 server-side validation and professional rule acceptance are NOT completed.** Next substantive step is Codex bounded server-contract implementation with independent Work review, not presenting the prototype as legally compliant. Never use existing canonical factual-conversion endpoint for scenario decisions.

## CR. Owner verified V1-derived UX mock conversion safeguards (2026-10-23)
- Owner pulled `a6ebe86`, TypeScript/Vite production build PASS (77 transformed modules), and two focused Vitest files PASS: workspace **28/28**, mock rule unit tests **5/5**, total **33/33**. Only nonblocking React Router v7 future-flag warnings.
- Confirmed **mock UI-only** disallow rules for classified capital/pension actions in tests. Backend authoritative V2 scenario validation, V1 frontend/server reconciliation, product-specific exceptions and professional authorization remain OPEN. No financial execution, migration, CI, merge or deploy.
- Next serious implementation should occur only against a reviewed scenario-domain rule contract, with Codex implementation / independent Work gate as appropriate. Avoid claiming the 33 UI tests demonstrate production legal eligibility.

## CS. Authoritative scenario conversion enforcement draft gate (2026-10-23)
- Owner confirmed 33/33 focused frontend tests for V1-derived mock conversion legality guard. This is strictly non-authoritative UX-only.
- Created `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`: review-ready contract separating permission, scenario eligibility, and tax/financial outcomes; versioned component-level inputs; strict server-side revalidation; no factual canonical-conversion mutation; fail-closed whole-plan batch behavior as a **proposal** rather than accepted product rule.
- Identified unresolved owner/domain decisions: V1 frontend/server rule authority mismatch; global unsettled severance blocker scope; partial-batch handling; leave-unallocated semantics; prerequisites and stale results.
- No executable code changed, so no local build/test needed for this document-only step. No independent Work review, Codex authoritative implementation, CI, database modification, merge or production release.

## CT. Existing V2 permission matrix integration discovery (2026-10-23)
- Read-only verified real V2 `canonical_conversion_matrix.py`: existing centrally versioned backend `destinations`/tax rules for 11 classified sources, product-type overrides, and `canonical_component_conversion_service._preflight`.
- **Critical difference:** factual `whole_product` conversion skips prohibited components and proceeds with eligible ones; explicit selections instead fail on forbidden destination. Scenario bulk semantics must be owner-approved, not inferred from this factual service.
- Source conversions mutate real component facts; never call factual route from scenarios. Current M06 archived evidence / M09 scenario adjustments are not yet a connected pension-product scenario engine.
- Updated `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md` with actual code references and adjusted implementation direction: reuse existing permissions as starting point via read-only scenario adapter, preserving separate tax/eligibility gates. No executable code, CI, DB, merge, production change. Independent Work not yet run.

## CU. Independent Work review package ready, not executed (2026-10-23)
- Updated `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md` with explicit distinction between **unreviewed mixed batch (fail-closed)** and an **explicitly reviewed eligible subset (enumerated, revalidated, atomic on submitted components)**. Both are proposals, not owner-accepted product rules. No automatic silent skipping.
- Created `docs/ux/WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md` with independent evidence-based audit tasks covering 11×2 permissions, V1–V2 tax mismatches, factual whole-plan `skipped`, M09 identity, severance, batch races and planned Codex slices.
- **Work has NOT been invoked and no independent verdict exists.** No code changed in this step, no CI/build/tests needed, no DB, backend, merge or deploy. Latest executable validation remains 33/33 owner-confirmed at `a6ebe86`.

## CV. V1–V2 rule parity source audit, Work gate still open (2026-10-23)
- No tool is exposed here to launch an independent ChatGPT Work audit. Do NOT claim independent review has run; owner must switch to Work mode and supply `docs/ux/WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md`.
- Direct source inspection produced `docs/ux/CONVERSION_MATRIX_PARITY_FINDINGS_2026-10-23.md`: all 11 canonical V1 backend vs V2 backend permission pairs match for ordinary product types; pre-2000 contributions' pension tax mapping differs from V1 frontend defaults while both backend mappings match. V2 factual whole-product path can skip disallowed components. Product-type overrides, full financial eligibility, and effective rule governance remain open.
- No executable code changed or CI run. Latest owner-confirmed 33/33 focused tests remain valid on preceding frontend revisions; this documentation does not assert an independent or runtime backend validation.

## CW. Additional backend permission contract test coverage (2026-10-23)
- No direct Work execution connector is available in this chat; independent review remains pending, and the prepared Work read-only brief remains the handoff.
- Inspected `backend/tests/test_canonical_conversion_matrix.py`: despite its filename, existing coverage there primarily exercises annuity coefficient lookups rather than the 11 money-class destination matrix.
- Created `backend/tests/test_component_conversion_permission_contract.py` with 11 parametrized V1-backend reference permissions, product-type overrides for all canonical codes, unknown-code rejection, matrix version and explicit pre-2000 backend tax discrepancy preservation. **Code not yet run by owner**; this is contract regression evidence, not independent legal validation or server-side scenario enforcement.
- No financial implementation changed, no CI, DB, deployment or merge. The newest backend test file may be checked in the existing isolated backend environment without stopping/recreating PostgreSQL tmpfs.

## CX. Backend conversion-permission test static readiness (2026-10-23)
- Read-only examined `backend/tests/test_component_conversion_permission_contract.py` against the current V2 `COMPONENT_CODES`, `canonical_conversion_matrix.destinations`, and `PensionProductError`. Found no evident mismatch in import names or eleven canonical classifications. This is **STATIC REVIEW ONLY**, not a successful pytest run.
- The standalone file defines **15 expected pytest cases**: 11 parameterized base-code permission checks and four other test functions (product overrides, unknown code, matrix version, pre-2000 backend tax handling). It has no database dependency and need not touch/restart the PostgreSQL tmpfs.
- To verify in the owner's existing checkout after fast-forward: from `backend`, run `python -m pytest -q tests/test_component_conversion_permission_contract.py` using the existing project Python environment. Do not invoke full CI, migrations, tests requiring DB reset or production changes.
- Work independent audit and authoritative pension-product scenario engine are still PENDING; frontend **33/33** was verified at `a6ebe86`.

## CY. Owner confirmed focused V2 backend permission tests (2026-10-23)
- Owner pulled `2c902a0` and executed `python -m pytest -q tests/test_component_conversion_permission_contract.py` from local backend: **15 passed in 1.74s**.
- Previous local frontend verification: **33/33 passed** across two files. Together **48 focused tests** are confirmed, on their respective code slices; NOT full-suite CI or professional tax/scenario-engine acceptance.
- Next pending stage: independent READ-ONLY Work review using `docs/ux/WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md` and parity findings. No authoritative scenario server enforcement yet, no financial calculation changes, merge, CI or deployment.

## CY. Independent Work audit received — CONTRACT BLOCKED (2026-10-23)
- Owner supplied complete external Work audit of the scenario conversion contract. Read-only Work checked V2 HEAD `d2b32d5...`, V1 HEAD `611557d...`, and reported NO Work code changes or test execution. The owner-provided audit reports prior Frontend 33/33 and Backend 15/15 separately from Work execution; do not attribute runs to Work.
- Work verdict: `CONTRACT_READINESS=BLOCKED`, `SCENARIO_ENGINE_IMPLEMENTED=NO`, `SERVER_SIDE_SCENARIO_ENFORCEMENT=NOT_IMPLEMENTED`, `IMPLEMENTATION=NOT_AUTHORIZED`. Ten findings SCV-001 through SCV-010, notably silent factual whole-plan pruning, unknown product type fallback, product-type exceptions overriding severance, pre-2000 tax conflict, capital action vocabulary mismatch, lack of historical ruleset authority, M09 mismatch, missing transaction semantics and prerequisite producers.
- Updated `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md` with all blocker dispositions, proposed P0–P5 phases and eight still-open professional owner decisions. **No scenario backend implementation is authorized; no Codex coding delegation.**
- No executable code changed; no CI/backend DB/merge/deploy. The new HEAD is documentation only; no new local tests needed.

## CZ. Post-Work technical safety contract closure, professional choices remain open (2026-10-23)
- Added §13 to `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`: explicit action mapping, closed source product resolver, fail-closed unresolved eligibility, read-only preview, exact component-list atomic submit, exact money, proposed lock/CAS/idempotency, source/ruleset stale handling, scoped professional evidence, and no early tax claims.
- These are **proposed conservative technical requirements only**. Eight professional owner decisions are recorded as an approval board; none silently approved. External independent Work audit verdict remains **BLOCKED** and authoritative financial scenario implementation **NOT AUTHORIZED**.
- No executable code, CI, DB, merge or production changes. No local test run required for this documentation-only change.

## DA. Verified existing factual evidence producers for contract (2026-10-23)
- Read-only inspected V2 pension component/product models, Decimal reconciliation service, employment records, grants and client profile. Appended source mapping to section 14 of `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`.
- V2 already computes component sums and discrepancies; reuse authoritative `reconcile` rather than duplicate. Employment/grant rows exist, but no automatic per-component entitlement linkage is confirmed; professional prerequisite mapping, 161d/tax producer and ruleset governance remain open.
- Audit status remains BLOCKED; no authoritative scenario code, CI, deployment or DB changes. Document-only update; no test run required.

## DB. Single professional decision board and review segmentation (2026-10-23)
- Created `docs/ux/SCENARIO_CONVERSION_OWNER_DECISION_REGISTER_2026-10-23.md`: O-01…O-08 with explicit nonapproved conservative proposals, G0…G4 review/implementation gates and one focused owner choice O-03 about consciously selecting an eligible subset for a mixed whole plan. Do not treat proposals as accepted law/policy.
- The contract stays BLOCKED; Work found missing authoritative scenario enforcement. Next owner answer can resolve O-03 only, without prejudging tax, severance exception precedence, evidence, or rule governance.
- No executable changes, tests, CI, migrations, merge or deploy.

## DC. Professional owner APPROVED O-03 whole-plan explicit eligible subset (2026-10-23)
- Owner explicitly approved: show all classified components of a full plan, permit converting only allowed components following explicit review and confirmation; prohibited components stay unconverted and must never be silently skipped.
- Updated `docs/ux/SCENARIO_CONVERSION_OWNER_DECISION_REGISTER_2026-10-23.md` to mark O-03 CLOSED/APPROVED and updated `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md` section 15 with preview→review→explicit enumerated subset→server revalidation→atomic submitted-batch semantics.
- O-01, O-02 and O-04…O-08 remain OPEN, particularly O-04 acknowledgment granularity. Work audit is still BLOCKED; no Codex financial implementation authorized. No executable code/CI/DB/merge/deploy change; no tests needed for docs-only edits.

## DD. Owner APPROVED O-04 grouped exclusion confirmation (2026-10-23)
- Owner chose a **single explicit acknowledgment for all excluded plan components**, after seeing the complete per-component list and each exclusion reason; no individual confirmation required. O-03 eligible-subset selection remains approved.
- Updated owner decision register and scenario contract §16. Proposed engineering safeguards: acknowledgment bound to exact reviewed preview/reason set, invalidation on changed source/selection/ruleset, server-side atomic revalidation; do not imply financial eligibility.
- O-03/O-04 CLOSED; O-01/O-02/O-05…O-08 remain OPEN; Work BLOCKED contract verdict and financial implementation prohibition unchanged. Documents only; no additional tests needed.

## DE. Owner APPROVED O-05 automatic residual (2026-10-23)
- Owner approved: money not allocated to pension/capital is an **automatically calculated remaining balance**, not a separate conversion/retain decision.
- Updated decision register and scenario contract §17. Define per-component original minus accepted allocations with exact Decimal, separate projected draft remaining, reject over-allocation and negative residual, mark stale if source changes, and display reconciliation discrepancy separately.
- O-03/O-04/O-05 are owner-approved. O-01/O-02/O-06/O-07/O-08 still open; Work contract BLOCKED and authoritative implementation prohibited. Documentation only; no code or CI changes.

## DF. Owner APPROVED O-06 scoped severance blocker (2026-10-23)
- Owner decision: block conversions of unresolved severance components and actions genuinely dependent on them, without automatically blocking unrelated contribution components.
- Updated decision register and scenario contract §18; component/action-scoped dependency evidence, no implicit product-level/global veto, integration with O-03/O-04 review and atomic submit, no fictitious authorization for unknown O-01/O-08 cases.
- O-03/O-04/O-05/O-06 now APPROVED; O-01/O-02/O-07/O-08 OPEN. Work BLOCKED implementation gate remains. Docs only; no code changes, tests, CI, DB, merge or deploy.

## DG. Owner correction of O-01 product-type rationale (2026-10-23)
- Owner clarified that education funds/investment provident funds cannot have genuine severance; their type-level exception ensures capital conversion remains possible when balances land in arbitrary technical contribution columns, notably post-2000 columns otherwise pension-only.
- Corrected owner decision register and appended contract §19. Treat unexpected severance-coded rows under these products as source-classification anomalies requiring reconciliation, rather than legal severance eligibility through override. Closed product identity determination, anomaly handling and tax authority still require validation. O-01 rationale clarified, not blanket scenario implementation authorization.
- No financial code change, CI, DB, merge or deploy. Contract remains BLOCKED.

## DH. O-02 tax discrepancy isolated, NOT professionally resolved (2026-10-23)
- Direct V1 frontend/V1 backend/V2 backend source comparison confirms both pre-2000 employee and employer contributions may be converted to pension in the base matrix; V1 frontend default `exempt` conflicts with both backends' `taxable` pension labels. Added contract §20 source comparison and prohibition on deriving a tax ruling from code agreement or comments.
- Scenario permission display may state allowed pension allocation subject to other prerequisites, but scenario tax response must be `not_evaluated` until O-02 evidence/authority resolved. No factual tax code changed.
- Owner clarification O-01 product-type exception remains recorded, O-03…O-06 approved. Contract remains BLOCKED pending tax, evidence and governance gates. No executable code, CI, DB, merge or deployment changes.

## DI. Owner APPROVED O-02 tax classification; O-07 governance proposal (2026-10-23)
- Professional owner expressly confirmed that pension payments from `תגמולי_עובד_עד_2000` and `תגמולי_מעביד_עד_2000` are tax **exempt**, as in V1 frontend; V1/V2 backend taxable labels are inconsistent with approved business rule. O-02 CLOSED for these two classifications and pension destination only.
- Updated owner decision register and scenario contract §21. Current V2 server tax labels are **not** corrected in executable code; separate scoped domain fix and tests need explicit implementation authorization. Scenario current tax API stays `not_evaluated` until approved evidence/ruleset implementation.
- Added O-07 proposed immutable ruleset registry (signed owner approval, effective intervals, fingerprints, historical replay, stale re-evaluation). O-07 not yet owner-approved. Overall Work contract verdict BLOCKED, engine implementation not authorized. No CI, DB, factual code or deployment changes.

## DJ. Owner APPROVED O-07 conversion ruleset governance (2026-10-23)
- Owner approved approval authority restricted to system owner or explicitly delegated professional. Preserve historical versions, effective dates and change audit; historical scenario results must not be silently overwritten.
- Updated decision register and contract §22 with approval/delegation audit, immutable ruleset versions, revision/currentness semantics. This is accepted governance policy, not implementation authorization. O-08 evidence policy and O-01 anomaly verification remain open. Work contract BLOCKED.
- Docs-only. No changes to financial services, CI, DB, deployment or production.

## DK. Owner APPROVED O-08 evidence-dependent blocking (2026-10-23)
- Owner approved: a missing essential professional datum blocks only the component/action that depends on it, not an unrelated conversion or the entire scenario. Missing datum, reason and evidence source must be shown and documented.
- Updated owner decision register and enforcement contract §23 with dependency scope, provenance, status distinction, per-action errors, revalidation/staleness and atomicity; detailed source-to-rule mapping remains a review prerequisite.
- O-02 through O-08 approved; O-01 owner rationale clarified, canonical product-type/anomaly verification pending. Independent Work contract remains BLOCKED, no financial implementation authorized. Docs only, no CI/DB/merge/deploy.

## DL. Second-pass independent Work audit handoff ready (2026-10-23)
- Added a second-pass addendum to `docs/ux/WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md`, asking Work to evaluate each SCV-001…SCV-010 against approved O-02…O-08, clarified O-01, contract contradictions, read-only preview versus authoritative save readiness, and proof that factual balances stay unchanged.
- Cleaned stale chronological statements in owner decision register; current status O-02…O-08 owner approved, O-01 anomaly/type resolver technical verification pending. First Work verdict BLOCKED remains until a **new independently executed** audit reports otherwise.
- Work was **not invoked from this chat**; no code/CI/DB/merge/deploy activity. All changes documentation-only.

## DM. Second independent Work audit BLOCKED; unified normative draft (2026-10-23)
- Owner delivered Work re-review at HEAD `979c32b4caed8d16b377d186fc8410e9c97f6a51`: POLICY_READINESS=PASS; existing chronological CONTRACT_CONSISTENCY=BLOCKED; permission-only read-only preview BLOCKED but narrowly resolvable; professional preview and authoritative save BLOCKED. No Work code changes/tests.
- Created `docs/ux/V2_SCENARIO_CONVERSION_NORMATIVE_CONTRACT_V1_2026-10-23.md`: proposed single normative contract containing O-01–O-08, permission-only strict preview shape, closed action and proposed product class, 11 visible rows including zero, source fingerprint canonical JSON/sha256, group-review digest, client ownership/read-only guards, tax/eligibility not evaluated, factual ledger isolation and re-review checklist.
- Prepended NON-NORMATIVE archival warning to former chronological `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`; old contradictory sections explicitly superseded for review, not silently deleted. Important: exact alias mapping from real source and full server DTO/error shape still require independent review and acceptance before implementation.
- No executable code changes/CI/DB/migrations/deployment/merge. Implementation remains NOT_AUTHORIZED, no passing second re-review verdict for newly unified contract.


## DN. Product-type intake audit correction (2026-10-23)
- Continued source examination found a critical omission in prior handoff updates: `pension_product_import_service._prepare_batch` maps numeric XML `SUG-MUTZAR` to Hebrew `PRODUCT_TYPE_LABELS` **before persistence**. The earlier statement that imported numeric codes were saved directly in `PensionProduct.product_type` was WRONG; superseded explicitly, not evidence for implementation.
- Actual persisted known imported types are five Hebrew labels (codes 1–5). Unrecognized nonempty types use `סוג מוצר לא ממופה`, missing types use `סוג מוצר לא נמסר`; source XML and diagnostics retain earlier evidence. Manual `product_type` remains free text; no approved closed alias inventory for special fund types.
- Corrected the normative contract §H in commit `7a7094bf089a555bee99e53c170282f71e11a132`. Earlier §H/H1 assertions added in `7c02605` and `39b409b` are invalid and superseded; do not use them as proof.
- No CI, tests, local state, financial code, merge, database migration or deployment. Contract and permission preview remain NOT_AUTHORIZED, authoritative save BLOCKED. Next: source-backed manual frontend type inventory and independent review preparation.


## DO. UI product type and unknown XML type evidence (2026-10-23)
- Read `frontend/src/pages/RetirementWorkspaceScreen.tsx` and `frontend/src/api/pensionProductsApi.ts` on active branch: existing workspace component-balance correction echoes persisted `product_type` into PUT; API type is `string`; **no closed product-type selector was established in inspected UI**. This is not proof that no manual form exists elsewhere.
- Checked `pension_product_import_service._prepare_batch` and `ProductMetadata`: unknown XML type receives nonempty literal `סוג מוצר לא ממופה`, missing receives `סוג מוצר לא נמסר`; these are accepted as strings during schema validation. Unknown source types are therefore not safely handled by substring/base matrix fallback in prospective scenario preview.
- Added evidence to normative contract §I in commit `e445914ce53038c22f129c727243d99d946b5362`. Do not treat the five Hebrew imported labels as complete legal type equivalences; education/investment provident manual aliases and savings insurance semantics are still open.
- No CI/tests/code/database changes, merge or deploy. Preview implementation and scenario save not authorized. Further work: locate complete manual-entry UI and obtain authoritative classification mapping, then independently re-review normative contract.


## DP. Manual product input located in actual routed screen (2026-10-23)
- Inspected `frontend/src/routes/AppRoutes.tsx` and `frontend/src/pages/PensionProductsScreen.tsx`: the route `/clients/:clientId/pension-products` exposes metadata form with unbounded (nonempty) free-text `product_type` input; the default is `קופת גמל`. `productTypeLabel` is a display-only 1–5 code formatter, not an authoritative type resolver.
- Added normative contract §J with exact finding. No complete manually entered type vocabulary can be proven from code. For prospective Preview an unknown/ambiguous type must fail closed; future controlled selector is a separate UX/migration task.
- No financial code, CI, tests, database, PR, merge or deployment. Preview and authoritative save remain not authorized; external independent review required.


## DQ. Independent review package prepared after complete source-chain checks (2026-10-23)
- Rechecked `canonical_conversion_matrix`, `pension_product_import_service`, `pension_product_reconciliation` and normative contract. Verified imported known codes map to Hebrew labels before persistence, manual default is free text, unknown types use explicit fallback labels, and tax/permission are currently conflated in matrix values.
- Updated `docs/ux/WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md` with third-pass bounded questions, exact source list, SCV-001...010 disposition expectation, and separate preview/save verdicts. Commit `158eef5f5ad087a66d7f7385b1d7245aa129b125`.
- Independent Work has NOT been invoked or passed. No CI/tests, financial implementation, DB changes, merge, or deployment. Contract remains design-only and preview/save implementation unauthorized. Next decision gate is independent read-only review of normative §§A–J, especially O-01 closed resolver, manual free text, anomalous severance, tax mismatch and signed ruleset absence.


## DR. Preview read-only locking hazard identified (2026-10-23)
- Static source inspection: `canonical_pension_source_reader.current_products` and `pension_product_routes.detail` call `lock_client`, which in SQLite executes an UPDATE writer reservation, and in PostgreSQL takes an advisory transaction lock and `SELECT FOR UPDATE`. These helpers must not be assumed safe for an explicitly zero-write permission preview.
- Client ID filtering in `get_product` is not independently proof of principal-to-client authorization. Independent review must trace middleware and authorization dependency and require a new truly read-only, consistent, tenant-authorized snapshot access pattern.
- Added this requirement to `WORK_INDEPENDENT_REVIEW_BRIEF_SCENARIO_CONVERSION_2026-10-23.md`, commit `6441802e39355ac47f9539be0e44e41bd142bf64`. No independent Work invocation, tests, CI, DB operations, code changes, merge or deploy; implementation still blocked.


## DS. Authentication and strictly nonwriting Preview reader source findings (2026-10-23)
- Inspected `main.py`, `security/middleware.py`, `security/config.py`, `db/session.py`, `pension_product_routes.py`, `canonical_pension_source_reader.py` and `pension_product_service.py`. Production middleware enforces session validation and CSRF/origin on unsafe operations; development/test bypass its production branch. No proven per-client principal permissions model in inspected sources; single configured actor is present.
- Existing factual read helpers use `lock_client` with SQLite UPDATE or PostgreSQL FOR UPDATE/advisory lock. A zero-write Permission Preview needs a dedicated snapshot read and independently accepted security scope, not unchecked helper reuse or a speculative multi-tenant RBAC rewrite.
- Updated normative contract §K (commit `87e06abd3df5e0141cb6ad8d58104c8ecae13d60`). This is static source assessment, not independent Work approval. No executable modifications, tests, CI, database, merge or deployment. Permission-only preview and scenario save remain unauthorized.


## DT. Production actor session boundary verified (2026-10-23)
- Read `security/transport.py::validate_session`, `security/session.py`, `security/config.py` and `api/auth_routes.py`. Production verified Session sets `trusted_professional_actor` from `actor_id`, bound to configured single `AUTH_ACTOR_ID`. No evidenced per-planner client ACL. Suitable review proposal: accept authenticated operator scope only for current single-operator model, not imaginary multi-tenant RBAC.
- Added normative contract §L at commit `cbd62bb995b5c0e0adbd52b7ca7120c2f3951b30` with bounded session access assumptions and security tests. Zero-write snapshot, source type resolution and independent review still outstanding.
- No CI, tests, code, DB, merge or deployment. No Work audit executed; authoritative scenario-save remains BLOCKED.
