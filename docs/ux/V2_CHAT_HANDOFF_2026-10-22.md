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
