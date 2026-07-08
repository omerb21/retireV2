# Platform Runtime Baseline

Package: `V2-IAP-01A`

This document records the current V2 platform/runtime baseline as evidence only. It does not authorize or implement fixes. It does not mark any business capability as implemented.

## Repository Baseline

| Field | Value |
|---|---|
| Repository | `omerb21/retireV2` |
| Inspected commit | `aa12410308f7919a2660ed223a1d7f7baaa0395e` |
| Commit label | `aa12410 docs: add V2 package acceptance gates` |
| Evidence date | 2026-07-08 |
| Package scope | Documentation/evidence only |

Initial `git status --short --untracked-files=all` showed unrelated untracked local files in `CURRENT_PROJECT_STATE.md`, `_evidence/`, and `specs/bootstraps/`. No staged files were present before this package.

## Backend Import And Startup Behavior

The backend application imports successfully from the `backend` directory with:

```powershell
python -c "from app.main import app; [print(','.join(sorted(getattr(route, 'methods', []) or [])) + ' ' + getattr(route, 'path', '') + ' ' + getattr(route, 'name', type(route).__name__)) for route in app.routes]"
```

Observed result: command succeeded and listed registered FastAPI routes.

This is runtime registration evidence for the imported FastAPI app object. It is not proof that every route behavior is correct, that the database is reachable, or that every test passes.

## Backend Route Listing Behavior

Route listing is available by importing `app.main:app` from the `backend` directory and iterating `app.routes`.

Observed registered routes:

```text
GET,HEAD /openapi.json openapi
GET,HEAD /docs swagger_ui_html
GET,HEAD /docs/oauth2-redirect swagger_ui_redirect
GET,HEAD /redoc redoc_html
GET /api/clients list_clients
POST /api/clients create_client
GET /api/clients/{client_id} get_client
PUT /api/clients/{client_id}/profile put_client_profile
GET /api/clients/{client_id}/profile get_client_profile
POST /api/clients/{client_id}/clearinghouse-snapshots create_clearinghouse_snapshot
GET /api/clients/{client_id}/clearinghouse-snapshots list_clearinghouse_snapshots
GET /api/clients/{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id} get_clearinghouse_snapshot
PUT /api/clients/{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id}/verification update_clearinghouse_snapshot_verification
POST /api/clients/{client_id}/documents create_retirement_planning_document
GET /api/clients/{client_id}/documents list_retirement_planning_documents
GET /api/clients/{client_id}/documents/{document_id} get_retirement_planning_document
PUT /api/clients/{client_id}/documents/{document_id}/verification update_retirement_planning_document_verification
POST /api/clients/{client_id}/pension-holdings create_pension_holding
GET /api/clients/{client_id}/pension-holdings list_pension_holdings
GET /api/clients/{client_id}/pension-holdings/{pension_holding_id} get_pension_holding
PUT /api/clients/{client_id}/pension-holdings/{pension_holding_id} update_pension_holding
POST /api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record create_pension_analysis_record
GET /api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record get_pension_analysis_record
PUT /api/clients/{client_id}/pension-holdings/{pension_holding_id}/analysis-record update_pension_analysis_record
POST /api/clients/{client_id}/capital-assets create_capital_asset
GET /api/clients/{client_id}/capital-assets list_capital_assets
GET /api/clients/{client_id}/capital-assets/{capital_asset_id} get_capital_asset
PUT /api/clients/{client_id}/capital-assets/{capital_asset_id} update_capital_asset
POST /api/clients/{client_id}/recurring-incomes create_recurring_income
GET /api/clients/{client_id}/recurring-incomes list_recurring_incomes
GET /api/clients/{client_id}/recurring-incomes/{recurring_income_id} get_recurring_income
PUT /api/clients/{client_id}/recurring-incomes/{recurring_income_id} update_recurring_income
POST /api/clients/{client_id}/recurring-expenses create_recurring_expense
GET /api/clients/{client_id}/recurring-expenses list_recurring_expenses
GET /api/clients/{client_id}/recurring-expenses/{recurring_expense_id} get_recurring_expense
PUT /api/clients/{client_id}/recurring-expenses/{recurring_expense_id} update_recurring_expense
POST /api/clients/{client_id}/retirement-timing-work-intentions create_retirement_timing_work_intention
GET /api/clients/{client_id}/retirement-timing-work-intentions list_retirement_timing_work_intentions
GET /api/clients/{client_id}/retirement-timing-work-intentions/{retirement_timing_work_intention_id} get_retirement_timing_work_intention
PUT /api/clients/{client_id}/retirement-timing-work-intentions/{retirement_timing_work_intention_id} update_retirement_timing_work_intention
POST /api/clients/{client_id}/planner-assumptions create_planner_assumption
GET /api/clients/{client_id}/planner-assumptions list_planner_assumptions
GET /api/clients/{client_id}/planner-assumptions/{planner_assumption_id} get_planner_assumption
PUT /api/clients/{client_id}/planner-assumptions/{planner_assumption_id} update_planner_assumption
POST /api/clients/{client_id}/missing-items create_missing_data_item
GET /api/clients/{client_id}/missing-items list_missing_data_items
PUT /api/clients/{client_id}/missing-items/{missing_data_item_id} update_missing_data_item
POST /api/clients/{client_id}/employment-records create_employment_record
GET /api/clients/{client_id}/employment-records list_employment_records
PUT /api/clients/{client_id}/employment-records/{employment_record_id} update_employment_record
DELETE /api/clients/{client_id}/employment-records/{employment_record_id} delete_employment_record
POST /api/clients/{client_id}/grants create_grant
GET /api/clients/{client_id}/grants list_grants
PUT /api/clients/{client_id}/grants/{grant_id} update_grant
DELETE /api/clients/{client_id}/grants/{grant_id} delete_grant
POST /api/clients/{client_id}/actual-capitalizations create_actual_capitalization
GET /api/clients/{client_id}/actual-capitalizations list_actual_capitalizations
PUT /api/clients/{client_id}/actual-capitalizations/{capitalization_id} update_actual_capitalization
DELETE /api/clients/{client_id}/actual-capitalizations/{capitalization_id} delete_actual_capitalization
POST /api/fixation/review/validate validate_fixation_review
POST /api/fixation/review/convert convert_fixation_review
POST /api/fixation/validate validate_fixation
POST /api/fixation/calculate calculate_fixation_endpoint
POST /api/fixation/save save_fixation
POST /api/fixation/runs/{run_id}/internal-planner-judgment create_fixation_run_internal_planner_judgment
GET /api/clients/{client_id}/fixation/latest latest_fixation_result
GET /api/clients/{client_id}/fixation/history fixation_history
GET /api/fixation/runs/{run_id} fixation_run_detail
GET /health health
```

## Backend Test Collection Behavior

Command:

```powershell
Set-Location backend
python -m pytest --collect-only -q
Set-Location ..
```

Observed result: collection found `226 tests collected`, then stopped with one collection error:

```text
ERROR tests/test_health.py - TypeError: Client.__init__() got an unexpected keyword argument 'app'
```

Classification: `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, and `BLOCKING_PLATFORM_ISSUE` for full backend test confirmation.

## Backend Test Execution Behavior

Command:

```powershell
Set-Location backend
python -m pytest -q
Set-Location ..
```

Observed result: execution stopped during collection with the same `tests/test_health.py` `TestClient`/httpx error:

```text
ERROR tests/test_health.py - TypeError: Client.__init__() got an unexpected keyword argument 'app'
```

Classification: `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, and `BLOCKING_PLATFORM_ISSUE`.

## Frontend Build Behavior

Command:

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Observed result: passed.

Summary:

```text
tsc -b && vite build
53 modules transformed
dist/index.html 0.33 kB
dist/assets/index-pB1BIqAr.js 296.49 kB
built in 5.18s
```

## Frontend Test Behavior

Command:

```powershell
Set-Location frontend
npm test
Set-Location ..
```

Observed result: failed with two existing frontend test failures:

```text
Test Files  2 failed | 16 passed (18)
Tests  2 failed | 78 passed (80)
```

Failures:

```text
src/pages/PensionAnalysisRecordSection.test.tsx > PensionAnalysisRecordSection > loads current pension holdings and creates one separate analysis record with read-only fact context
TestingLibraryElementError: Unable to find an element with the text: Existing Pension Provider.

src/pages/RetirementPlanningFactsSection.test.tsx > RetirementPlanningFactsSection > proves client-detail integration and allowed Package C UI boundary
AssertionError: expected ... to have a length of 5 but got 6
```

Classification: `BASELINE_EXCEPTION` and `TEST_EXCEPTION`. These failures block claiming full frontend test confirmation, but they do not block starting a targeted platform/runtime hardening package if that next package explicitly carries them as exceptions or includes approved fix scope.

## Database And Config Discovery Notes

Observed repository-local config files:

- `backend/.env`
- `backend/.env.example`
- `backend/alembic.ini`
- `backend/requirements.txt`
- `frontend/package.json`
- `frontend/vite.config.ts`

No database migrations, schema changes, dependency changes, or app configuration changes were made in this package.

The backend route listing command imports the app object successfully without requiring a database mutation. Full backend tests do not reach execution because collection stops at the `TestClient`/httpx compatibility exception.

## Positive Baseline Evidence

| Evidence | Result | Notes |
|---|---|---|
| Backend route listing | Passed | The backend app imports from `backend` and registered FastAPI routes were listed. This is positive runtime baseline evidence, not an exception. |
| Frontend build | Passed | `npm run build` completed successfully. This is positive build baseline evidence, not an exception. |

## Known Exceptions And Blocking Assessment

| Exception | Classification | Blocks V2-IAP-01B? | Reason |
|---|---|---|---|
| Backend `python -m pytest --collect-only -q` stops at `tests/test_health.py` `TestClient`/httpx error after collecting 226 tests. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, `BLOCKING_PLATFORM_ISSUE` | Yes, unless IAP-01B explicitly authorizes platform/test-environment fixes. | Backend tests cannot be fully collected or confirmed. |
| Backend `python -m pytest -q` stops at the same collection error. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, `BLOCKING_PLATFORM_ISSUE` | Yes, unless IAP-01B explicitly authorizes platform/test-environment fixes. | Backend test execution is blocked before running tests. |
| Frontend `npm test` has 2 failing tests out of 80. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION` | Yes for broad feature work; acceptable only as explicit exception for targeted hardening. | Frontend tests are not fully confirmed. |

Recommendation: `YES_WITH_EXPLICIT_EXCEPTIONS` for starting V2-IAP-01B only if it is limited to authorized platform/runtime hardening and explicitly addresses or carries the backend pytest collection/execution blocker, frontend test failures, and unrelated untracked local files. Broad feature work should not start on this baseline.
