# V2 Actual Build Plan: Internal Pension Analysis Workspace

Package: `V2-IAP-02K_ACTUAL_BUILD_PLAN_INTERNAL_PENSION_ANALYSIS_WORKSPACE`

Status: `BUILD_PLAN_COMPLETE`

Implementation authorization in 02K: `NO`

## 1. Current State

- Repository HEAD reviewed: `a7d314d6b83750debf1e131eac756d3f7a3fa1b7` (`a7d314d docs: record admin settings evidence investigation`).
- 02D planning exists in the full capability coverage matrix, development plan, and package sequence register.
- 02F execution roadmap exists.
- 02G structured product discovery options exist.
- 02H previously selected `OPT-I Administration/settings evidence investigation`.
- 02J completed that bounded path with final classification `EVIDENCE_ABSENT` and required next state `STOP_ADMIN_SETTINGS_PATH`.
- The admin/settings path is stopped and is not part of this milestone.
- V2.1 Milestone 1 Packages A through E are closed and provide an existing internal facts, assumptions, missing-information, and consolidated-review foundation.
- This build plan selects a build-oriented milestone based on those existing V2.1 foundations. It does not derive implementation authority from V1 and does not reopen product discovery or product decision.

## 2. Build Milestone Definition

### Milestone Name

`V2 Internal Pension Analysis Workspace`

### Audience

Internal planner only.

### Purpose

Create a usable internal workspace for reviewing pension holdings, planner assumptions, advisory missing information, and pension analysis records in client context, with an improved consolidated internal review surface.

The milestone assembles and makes usable existing bounded V2.1 capabilities. It does not authorize calculation, projection, advice, recommendation, external integration, or client-facing output.

## 3. Explicit Exclusions

The following are outside the milestone and every package in this plan:

- Tax calculations.
- Retirement cashflow calculations.
- Scenario modeling.
- Portfolio projection.
- Recommendations or advice generation.
- LLM or tool behavior.
- OCR.
- Imports.
- Clearinghouse integration.
- PDF or report generation.
- 161D output.
- Client-facing output.
- Admin/settings.
- Mutable calculation tables.
- Any external data integration.

## 4. Existing Foundations To Use

| Foundation | Repository evidence | Build-plan use boundary |
|---|---|---|
| Pension holdings | `CURRENT_PROJECT_STATE.md` V2.1 Packages A-C; `V1_TO_V2_FULL_CAPABILITY_COVERAGE_MATRIX.md` V1-CAP-022 | Existing client-scoped fact persistence, API, maintenance UI, and tests may be composed into the internal workspace. No portfolio projection is authorized. |
| Pension analysis record | `V1_TO_V2_FULL_CAPABILITY_COVERAGE_MATRIX.md`; `V2_FULL_DEVELOPMENT_PLAN_FROM_V1_GAPS.md`; existing V2.1 planning evidence cited by those artifacts | Existing record capability may be displayed and used within its accepted contract. Any missing write/status behavior must be named by the contract before a narrow implementation package may add it. |
| Planner assumptions | `CURRENT_PROJECT_STATE.md` V2.1 Package D; coverage matrix V1-CAP-026 | Existing client-scoped assumptions may be displayed and used as planner-entered context. They must not become calculation authority. |
| Advisory missing information | `CURRENT_PROJECT_STATE.md` V2.1 Package D; coverage matrix V1-CAP-028 | Existing advisory missing-information items may be displayed and maintained within their accepted API/UI boundary. They must not become client-facing tasks or automated readiness decisions. |
| Consolidated internal retirement planning review | `CURRENT_PROJECT_STATE.md` V2.1 Package E; coverage matrix V1-CAP-029 | Existing seven-group, read-only internal review is the primary composition baseline. Improvement must preserve separation between facts, assumptions, and missing information. |
| Client context | `CURRENT_PROJECT_STATE.md`; coverage matrix V1-CAP-001 and V1-CAP-019 | Workspace remains client-scoped and internal. No global or client-facing workspace is authorized. |
| Backend and frontend test structure | `CURRENT_PROJECT_STATE.md` package closures; acceptance standard; test evidence cited by the coverage matrix | Later packages must use focused backend/frontend tests, then full validation and build evidence. Existing tests are evidence only and do not authorize broader behavior. |

## 5. Actual Package Sequence

### V2-BUILD-01-CONTRACT

**Package name:** Internal Pension Analysis Workspace Contract

**Purpose:** Define the exact workspace contract before code.

**Expected files/areas:**

- Allowed file only: `specs/runtime/V2_CONTRACT_INTERNAL_PENSION_ANALYSIS_WORKSPACE.md`.
- The contract must define workspace sections, data displayed, user actions, read/write boundaries, backend contracts, frontend contracts, behavior explicitly not calculated, behavior explicitly not recommended, and stop conditions.

**Forbidden files/areas:**

- All source code, tests, backend, frontend, migrations, models, schemas, services, UI, package files, dependencies, and existing planning documents.

**Dependencies:**

- Accepted 02K build plan.
- Existing V2.1 Packages A-E repository contracts and evidence.

**Tests required:**

- None. This is a contract-only package and must not run implementation tests as acceptance evidence.

**Acceptance gate:**

- Contract names every workspace section and exact data source.
- Read and write actions are explicit for each section.
- Backend and frontend gaps are classified as required or unnecessary.
- No calculation, recommendation, client-facing, admin/settings, or external-integration behavior is introduced.
- Review package is completed before commit, followed by a post-commit checkpoint confirming the accepted contract HEAD.

**Stop conditions:**

- A required source artifact is missing.
- Exact workspace sections, actions, or data sources cannot be named.
- A proposed behavior requires any explicit milestone exclusion.
- A database or migration requirement is discovered; record it for a separate schema package and do not authorize implementation through this contract.

**Expected commit message:** `docs: define internal pension analysis workspace contract`

### V2-BUILD-02-BACKEND-SCHEMA-API-GAP

**Package name:** Backend Schema/API Gap Implementation

**Purpose:** Implement only the minimum backend gaps required by the accepted workspace contract.

**Expected files/areas:**

- Only when the accepted contract identifies a concrete gap: `backend/app/models/*`, `backend/app/schemas/*`, `backend/app/api/*`, `backend/app/services/*`, and focused `backend/tests/*`.
- The execution package must replace these area patterns with an exact file allowlist before implementation.

**Forbidden files/areas:**

- Frontend.
- Migrations unless a separate schema package is first created and accepted.
- Calculation engines, tax/cashflow/scenario/projection logic, recommendations, imports, OCR, reports, LLM behavior, client-facing output, admin/settings, external integrations, and unrelated files.

**Dependencies:**

- Accepted V2-BUILD-01 contract.
- Exact backend gaps and exact allowed files named by that contract.

**Tests required:**

- Targeted backend schema, service, and API tests for every changed contract.
- Exact client ownership, response shape, validation, and read/write boundary assertions.
- Relevant backend regression tests identified by the accepted contract.

**Acceptance gate:**

- Every changed source/test file maps to a contracted capability.
- All targeted tests pass or an explicit exception blocks acceptance.
- No endpoint or persistence behavior exists outside the contract.
- Review package is completed before commit, followed by a post-commit checkpoint with HEAD and git status evidence.

**Stop conditions:**

- The contract does not require a backend gap; skip this package with explicit evidence.
- Exact files cannot be named before implementation.
- A migration or new database structure is required; stop and split a separate schema package.
- Any excluded domain or behavior becomes necessary.

**Expected commit message:** `feat: implement pension workspace backend contract gaps`

### V2-BUILD-03-BACKEND-WORKSPACE-SERVICE

**Package name:** Internal Workspace Service Assembly

**Purpose:** Provide a backend read model or service assembly for the internal workspace if the accepted contract proves one is needed.

**Expected files/areas:**

- `backend/app/services/*`, `backend/app/api/*`, and focused `backend/tests/*` only.
- The execution package must name exact files before implementation.

**Forbidden files/areas:**

- Models, schemas, and migrations unless separately authorized by an accepted preceding package.
- Frontend.
- New calculation engines, tax/cashflow/scenario/projection logic, recommendations, external integrations, reports, LLM behavior, client-facing output, and admin/settings.

**Dependencies:**

- Accepted V2-BUILD-01 contract.
- Accepted V2-BUILD-02 when backend contract gaps exist.
- Explicit evidence that existing list APIs alone cannot satisfy the workspace contract.

**Tests required:**

- Focused service and API tests proving exact client-scoped workspace composition.
- Tests preserving separation of holdings, analysis records, assumptions, and missing-information data.
- Tests proving no derived calculation or recommendation fields are returned.

**Acceptance gate:**

- Workspace data composition matches one explicit read contract.
- Existing authoritative records remain the sources of truth.
- Targeted and relevant backend regression tests pass.
- Review package is completed before commit, followed by a post-commit checkpoint.

**Stop conditions:**

- Existing APIs satisfy the contract; skip this package with explicit evidence.
- Service assembly would duplicate or alter source-of-truth records.
- Exact files cannot be named.
- Any excluded domain, external source, or new persistence requirement appears.

**Expected commit message:** `feat: assemble internal pension workspace data`

### V2-BUILD-04-FRONTEND-WORKSPACE-UI

**Package name:** Frontend Internal Pension Analysis Workspace

**Purpose:** Create or improve the internal planner UI workspace showing pension holdings, pension analysis records, planner assumptions, advisory missing information, and consolidated internal review.

**Expected files/areas:**

- Contract-required files under `frontend/src/pages/*`, `frontend/src/components/*`, `frontend/src/api/*`, and focused frontend test files.
- The execution package must name exact files before implementation.

**Forbidden files/areas:**

- Backend and migrations except already accepted backend dependencies.
- Client-facing output, PDF/report/export, recommendations, LLM behavior, projection UI, tax/cashflow/scenario UI, admin/settings, imports/OCR, clearinghouse, and unrelated UI redesign.

**Dependencies:**

- Accepted V2-BUILD-01 contract.
- Accepted or explicitly skipped backend packages with evidence.
- Stable backend/API contracts required by the workspace.

**Tests required:**

- Targeted frontend tests for every rendered section.
- Tests for all contracted user actions and read/write boundaries.
- Tests for loading, empty, and error states required by the contract.
- Tests preserving internal-only presentation and separation of facts, assumptions, and missing information.

**Acceptance gate:**

- Every contracted section is rendered from its accepted data source.
- Every contracted interaction is precise and does not imply calculation, recommendation, or client output.
- Targeted frontend tests and relevant regression tests pass.
- Review package is completed before commit, followed by a post-commit checkpoint.

**Stop conditions:**

- Exact page, component, API, and test files cannot be named.
- Backend behavior not accepted by a preceding package is required.
- UI requires any explicit exclusion or creates a new product direction.

**Expected commit message:** `feat: add internal pension analysis workspace`

### V2-BUILD-05-INTERNAL-REVIEW-SUMMARY

**Package name:** Internal Review Summary

**Purpose:** Add an internal-only summary section only if the accepted contract requires it and it was not completed by the workspace UI package.

**Expected files/areas:**

- Exact backend and/or frontend source and test files defined by the accepted contract and prior package evidence.
- The execution package must provide an exact file allowlist.

**Forbidden files/areas:**

- Recommendations, advice wording, client report language, PDF/export, calculations, projections, scoring, readiness decisions, LLM behavior, external integrations, and admin/settings.

**Dependencies:**

- Accepted V2-BUILD-01 contract.
- Accepted V2-BUILD-04 workspace UI.
- Explicit evidence that a separate internal summary remains required.

**Tests required:**

- Targeted backend and/or frontend tests for the exact summary contract.
- Tests proving the summary is internal, descriptive, source-backed, and contains no recommendations or calculated conclusions.

**Acceptance gate:**

- Summary content is traceable to accepted underlying records.
- No advisory conclusion, recommendation, score, calculation, or client-facing wording is introduced.
- Targeted tests pass.
- Review package is completed before commit, followed by a post-commit checkpoint.

**Stop conditions:**

- The contract does not require a separate summary; skip this package with explicit evidence.
- Summary semantics require recommendation, readiness, calculation, or new source-of-truth behavior.
- Exact files cannot be named.

**Expected commit message:** `feat: add internal pension review summary`

### V2-BUILD-06-VALIDATION-CLOSURE

**Package name:** Validation and Closure

**Purpose:** Run required backend, frontend, build, and governance validation and close the milestone without fixing newly discovered failures inside the closure package.

**Expected files/areas:**

- `specs/runtime/V2_INTERNAL_PENSION_ANALYSIS_WORKSPACE_COMPLETION_REPORT.md`
- `specs/runtime/V2_INTERNAL_PENSION_ANALYSIS_WORKSPACE_EXCEPTION_REGISTER.md`

**Forbidden files/areas:**

- All source code, tests, backend, frontend, migrations, models, schemas, services, UI, package files, dependencies, prior package evidence, and unrelated files.

**Dependencies:**

- All required implementation packages accepted and committed.
- Any conditionally unnecessary package explicitly skipped with evidence.

**Tests required:**

- Backend targeted tests introduced or changed by the milestone packages.
- `python -m pytest -q` from `backend/`, where appropriate to the accepted validation contract.
- Frontend targeted tests introduced or changed by the milestone packages.
- `npm test` from `frontend/`.
- `npm run build` from `frontend/`.
- Backend governance validation.
- Final `git status --short --untracked-files=all`.
- Final `git log --oneline` evidence.

**Acceptance gate:**

- Required targeted and full validations pass.
- Any failure, skip, or not-run check is recorded as an explicit exception and is not positive evidence.
- Source, runtime, UI, entity, service, and test evidence are accounted for under the package acceptance standard.
- Completion report answers `Decision: may the next package start?` with an allowed decision.
- Review package is completed before commit, followed by a final post-commit checkpoint.

**Stop conditions:**

- Any validation fails; record the exact failure and stop without fixing it.
- An unmapped implementation artifact or unexpected git-status item exists.
- An explicit milestone exclusion was introduced.
- Required acceptance evidence is absent.

**Expected commit message:** `docs: close internal pension analysis workspace milestone`

## 6. Package Ordering Rules

1. No implementation may begin before V2-BUILD-01-CONTRACT is accepted and committed.
2. Each implementation package must be narrow and must name exact allowed files before edits begin.
3. If the accepted contract proves that a backend gap is unnecessary, V2-BUILD-02 and/or V2-BUILD-03 may be skipped and the plan may proceed to frontend work only with explicit evidence.
4. If a new database structure or migration is needed, stop and split it into a separate schema package before implementation. The schema package must define exact models, migrations, tests, downgrade behavior, and table-boundary evidence.
5. If any package requires calculations, projections, recommendations, imports, OCR, reports, LLM behavior, client-facing output, admin/settings, mutable calculation tables, clearinghouse, or another external integration, stop.
6. If exact files cannot be named, stop before implementation.
7. No package may broaden the selected milestone or substitute a different product direction.
8. A skipped package requires explicit contract and repository evidence; silence is not a skip decision.

## 7. Acceptance Model

Every package must use the following acceptance controls:

| Control | Requirement |
|---|---|
| Allowed files | The execution package must list exact files. Area patterns in this build plan are planning boundaries only and are not edit authorization. |
| Forbidden files | All files outside the exact allowlist are forbidden, together with every milestone exclusion. |
| Tests required | The package must name targeted tests before implementation and run the relevant regression scope after implementation. Documentation-only packages run no implementation tests. |
| Review before commit | A read-only review package must show git status, scoped diff, full contents of package evidence documents, and requested test evidence. No commit occurs during review. |
| Checkpoint after commit | Verify HEAD, commit subject, final git status, accepted files, and authority for the next package. A committed predecessor does not automatically authorize broader scope. |
| Evidence accounting | Apply `specs/acceptance/package_acceptance_standard.md`; documentation alone is not positive implementation evidence. Failed, skipped, flaky, or not-run tests are exceptions. |
| Stop behavior | Stop at the first contract, scope, file-boundary, schema, excluded-domain, or validation blocker. Record the exact blocker without expanding scope. |

## 8. Next Immediate Step

Next immediate package:

`V2-IAP-02L_CONTRACT_INTERNAL_PENSION_ANALYSIS_WORKSPACE`

Allowed file:

`specs/runtime/V2_CONTRACT_INTERNAL_PENSION_ANALYSIS_WORKSPACE.md`

02L must not implement. It must define the exact workspace contract and convert the planning-area boundaries above into concrete implementation requirements and exact stop conditions.

Implementation is not authorized by 02K. Acceptance and commit of 02K authorize only opening the contract package under its one-file boundary.

## 9. Anti-Loop Controls

- This is the build plan.
- No more broad V1/V2 mapping.
- No more product discovery before this milestone.
- No more admin/settings path.
- No more lowest-risk evidence-only path.
- If the next package does not move toward implementation, reject it.
- If a package returns NO-GO without naming a concrete implementation blocker, reject it.
- If a package tries to choose another product direction, reject it.
- Evidence and governance work is permitted only when it directly defines, verifies, or closes one package in this build sequence.
