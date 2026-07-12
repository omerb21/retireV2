# V2 Contract: Internal Pension Analysis Workspace

Package: `V2-IAP-02L_MINIMAL_IMPLEMENTATION_CONTRACT_INTERNAL_PENSION_WORKSPACE`

## 1. Current State

- HEAD reviewed: `47e9b2091963b5ec1c173966d0f0b01602b94d67` (`47e9b20 docs: add internal pension analysis workspace build plan`).
- The 02K build plan is accepted in the repository baseline.
- 02L authorizes no implementation.
- 02L defines only the first implementation package for `V2 Internal Pension Analysis Workspace`.
- Existing backend routes, frontend API functions, section components, and focused tests are sufficient for a frontend-first composition package.

## 2. Workspace Contract

| Workspace section | Purpose | Existing data/UI source | Read/write behavior | Allowed user actions | Forbidden user actions | Required test assertions | Package dependency |
|---|---|---|---|---|---|---|---|
| Client context header | Keep the planner inside one named client file. | `GET /api/clients/{client_id}`; existing `ClientDetailScreen` client state | Read-only inside the workspace. | View client ID, full name, and file status. | Edit profile through the workspace; expose client-facing content. | Correct client context renders; no workspace profile controls render. | Existing client-detail route and load behavior. |
| Pension holdings list/summary | Review current pension holdings without calculation or projection. | `GET /api/clients/{client_id}/pension-holdings?lifecycle_status=current`; existing read-only Pension Holdings group in `RetirementPlanningConsolidatedReviewSection` and fact context in `PensionAnalysisRecordSection` | Read-only in the first workspace slice. Existing holdings maintenance remains outside this workspace contract. | View current holding identity, known amounts/dates, and source context already exposed by existing components. | Create/update holdings from the workspace; calculate, project, score, compare, or recommend. | Current holdings content, loading, empty, and error states remain visible through reused components; no calculation/projection controls. | Existing holdings endpoint, API client, and section components. |
| Pension holding analysis record | Record manual professional analysis separately for each current holding. | `GET`, `POST`, and `PUT /api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record`; `PensionAnalysisRecordSection` | Read current fact context; create or update only `analysis_record_text`. | View fact context; create one record per holding; update its text. | Change holding facts through the record; add automated conclusions, recommendations, statuses, calculations, or additional fields. | Existing create/update, current-holding, empty, error, and read-only fact-context assertions remain passing; workspace renders the section once. | Existing analysis-record routes, API client, component, and focused test. |
| Planner assumptions | Keep planner-entered assumptions visible and maintainable but separate from facts. | `GET`, `POST`, and `PUT /api/clients/{client_id}/planner-assumptions`; `PlannerAssumptionsSection` | Existing create/update and lifecycle-filter behavior only. | View, create, and update approved assumption fields; change the local lifecycle filter. | Use assumptions as calculation authority; calculate outcomes; add delete, recommendation, approval, readiness, or unapproved lifecycle controls. | Existing approved-field, partial-update, lifecycle, empty/error, and prohibited-control assertions remain passing; workspace renders the section once. | Existing planner-assumption routes, API client, component, and focused test. |
| Advisory missing information | Show and maintain internal advisory gaps without creating client tasks or automated readiness. | `GET`, `POST`, and `PUT /api/clients/{client_id}/missing-items`; `AdvisoryMissingInformationSection` | Existing create/update behavior for approved advisory fields only. | View items; create an open advisory item; update approved advisory status, planning domain, and neutral reason. | Create linkage fields, client-facing tasks, automatic priority/readiness, recommendations, or unsupported statuses. | Existing legacy-neutral display, create/update, error, and prohibited-behavior assertions remain passing; workspace renders the section once. | Existing missing-item routes, API client, component, and focused test. |
| Consolidated internal retirement planning review | Preserve one read-only cross-domain internal review after the focused pension sections. | Existing list APIs composed by `RetirementPlanningConsolidatedReviewSection`; no aggregate backend endpoint | Read-only. | View the existing seven groups and their independent loading, empty, and error states. | Edit records, derive summaries/counts/warnings, calculate, prioritize, recommend, or expose client output. | Existing seven-group API, ordering, current-lifecycle, empty, error, and no-raw-code assertions remain passing; workspace renders the review once after maintenance sections. | Existing API functions, consolidated component, and focused test. |
| Internal notes/status area | Prevent accidental invention of a new workflow. | No general workspace notes/status source is evidenced. `analysis_record_text` remains the only supported pension-analysis narrative field. | Deferred; not rendered in the first slice. | None beyond analysis-record text above. | Add general notes, workflow status, readiness, approval, recommendation, or lifecycle behavior. | Assert no general internal notes/status controls appear in the workspace. | Future package only if a later accepted contract names an existing or newly authorized source. |

The workspace is internal-planner-only. It must not include tax calculations, cashflow calculations, scenario modeling, portfolio projection, recommendations, advice generation, LLM/tool behavior, OCR, imports, clearinghouse integration, PDF/report generation, 161D output, client-facing output, admin/settings, mutable calculation tables, or external data integration.

## 3. Existing Implementation Surface

| Backend endpoint/source | Schema/service/source | Frontend page/component/source | Test evidence | Usable for first implementation |
|---|---|---|---|---|
| `GET /api/clients/{client_id}` | Existing `ClientResponse` route contract | `ClientDetailScreen.tsx` | `ClientDetailScreen.test.tsx` | Yes |
| `GET /api/clients/{client_id}/pension-holdings?lifecycle_status=current` | `PensionHoldingResponse`; direct client-scoped route | `clientsApi.ts`; `PensionAnalysisRecordSection.tsx`; `RetirementPlanningConsolidatedReviewSection.tsx` | `test_v21_package_b_api.py`; section tests | Yes |
| `GET/POST/PUT /api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record` | `PensionAnalysisRecord` contracts; direct client-scoped routes | `clientsApi.ts`; `PensionAnalysisRecordSection.tsx` | `test_v22_slice1_analysis_record_api.py`; `PensionAnalysisRecordSection.test.tsx` | Yes |
| `GET/POST/PUT /api/clients/{client_id}/planner-assumptions` | Existing planner-assumption request/response contracts; direct routes | `clientsApi.ts`; `PlannerAssumptionsSection.tsx` | `test_v21_package_d_api.py`; `PlannerAssumptionsSection.test.tsx` | Yes |
| `GET/POST/PUT /api/clients/{client_id}/missing-items` | Existing legacy-compatible missing-item/advisory contracts; direct routes | `clientsApi.ts`; `AdvisoryMissingInformationSection.tsx` | `test_v21_package_b_api.py`; `test_v21_package_d_api.py`; section test | Yes |
| Existing list APIs for seven consolidated groups | Existing independent route contracts; no workspace service required | `RetirementPlanningConsolidatedReviewSection.tsx` | `RetirementPlanningConsolidatedReviewSection.test.tsx` | Yes |
| No general internal workspace notes/status endpoint | No supported general notes/status schema or service | No supported component | No supporting test evidence | No; explicitly deferred |

No concrete backend technical blocker exists. Existing APIs provide every data source and mutation required by the first slice. No new API client function is required.

## 4. First Implementation Path Decision

`FRONTEND_FIRST`

The first slice is a semantic workspace composition inside the existing client-detail flow. It reuses accepted components and API clients; it does not change their backend contracts or business behavior.

## 5. Required Outcome

The next implementation package is ready under the narrow contract below.

## 6. Next Implementation Package

### Package

`V2-IAP-02M_IMPLEMENT_INTERNAL_PENSION_ANALYSIS_WORKSPACE_FIRST_SLICE`

### Package Type

`frontend-first`

### Exact Allowed Files

- `frontend/src/pages/InternalPensionAnalysisWorkspaceSection.tsx` (new)
- `frontend/src/pages/InternalPensionAnalysisWorkspaceSection.test.tsx` (new)
- `frontend/src/pages/ClientDetailScreen.tsx`
- `frontend/src/pages/ClientDetailScreen.test.tsx`

No other file is allowed. In particular, `frontend/src/api/clientsApi.ts`, existing section components and their tests, all backend files, migrations, package files, and dependencies are forbidden.

### Exact Implementation Contract

- Add `InternalPensionAnalysisWorkspaceSection` as a client-scoped internal composition component.
- Pass only existing client context needed for the header: client ID, full name, and file status.
- Compose the existing `PensionAnalysisRecordSection`, `PlannerAssumptionsSection`, `AdvisoryMissingInformationSection`, and `RetirementPlanningConsolidatedReviewSection` exactly once.
- Use the existing read-only Pension Holdings group and existing pension-holding fact context as the holdings review surface; do not create a new holdings request or duplicate holding state.
- Place the workspace in `ClientDetailScreen` within the existing client-detail flow.
- Remove the four directly composed child sections from the existing data-matrix list when the workspace replaces them, preventing duplicate requests and duplicate controls.
- Leave `RetirementPlanningFactsSection` and all non-workspace client-detail behavior unchanged.
- Do not add the deferred internal notes/status area.

### User-Facing Sections

1. Internal Pension Analysis Workspace heading.
2. Client Context header showing client ID, full name, and file status.
3. Pension Holdings review through existing read-only holdings/fact-context presentation.
4. Pension Analysis Records.
5. Planner Assumptions.
6. Advisory Missing Information.
7. Retirement Planning Consolidated Review.

### Allowed User Actions

- View client context and existing read-only review data.
- Create or update pension analysis record text through the reused section.
- View, create, update, and lifecycle-filter planner assumptions through the reused section.
- View, create, and update approved advisory missing-information fields through the reused section.

### Forbidden User Actions

- Edit pension holdings through this workspace.
- Add general internal notes or workflow status.
- Calculate, project, compare, score, prioritize, recommend, advise, approve, generate output, import data, or invoke external/LLM behavior.
- Access any client-facing workspace or output.

### Tests Required

- Add focused `InternalPensionAnalysisWorkspaceSection.test.tsx` assertions that:
  - render the workspace heading and exact client context;
  - render each reused section exactly once;
  - preserve the required section order;
  - do not render general internal notes/status controls;
  - do not render text or controls for calculations, projections, recommendations, reports, imports, OCR, clearinghouse, admin/settings, or client-facing output.
- Update `ClientDetailScreen.test.tsx` assertions that:
  - the workspace is composed once inside client detail;
  - client ID, full name, and file status are passed to it;
  - the four reused child sections are no longer directly composed by `ClientDetailScreen`;
  - `RetirementPlanningFactsSection` and the existing consolidated client-detail ordering outside the replaced composition remain intact.
- Run the two targeted test files first.
- Run existing focused tests for `PensionAnalysisRecordSection`, `PlannerAssumptionsSection`, `AdvisoryMissingInformationSection`, and `RetirementPlanningConsolidatedReviewSection` as regression evidence.
- Run the full frontend test suite and `npm run build` after targeted tests pass.

### Acceptance Gate

- Only the four exact allowed files change.
- The workspace renders once in the client-detail flow with exact client context.
- Existing child components are reused without modification and appear once in the contracted order.
- No backend/API/schema/service/migration or dependency change occurs.
- No duplicate workspace API requests are introduced through duplicate component composition.
- Targeted tests, four existing section regression tests, full frontend tests, and frontend build pass.
- A read-only review package is completed before commit.
- The implementation commit is followed by a checkpoint confirming HEAD, exact changed files, test evidence, and authority for the next build package.

### Stop Conditions

- Any implementation requires a file outside the four-file allowlist.
- Any existing component or API client must change to complete the slice.
- A missing or incompatible backend endpoint is discovered.
- A migration, schema, model, service, package, or dependency change is required.
- The workspace would duplicate child components or their requests.
- Any explicitly forbidden behavior or product direction is required.
- Any targeted test, required regression test, full frontend test, or build fails; record the exact failure and stop without broadening scope.

### Expected Commit Message

`feat: compose internal pension analysis workspace`

## 7. Blocker Package

Not applicable. No concrete backend blocker was found, so `V2-IAP-02M_BACKEND_BLOCKER_FOR_INTERNAL_PENSION_WORKSPACE` must not be opened from this contract.

## 8. 02L Acceptance Gate

- Exactly one file is created by 02L.
- The contract defines sections, existing data sources, read/write behavior, allowed and forbidden actions, tests, acceptance gate, and stop conditions.
- It selects one implementation path and one required outcome.
- It does not select another product direction.
- It does not authorize implementation inside 02L.
- It does not create another discovery, decision, governance, or evidence loop.

READY_FOR_IMPLEMENTATION_PACKAGE
