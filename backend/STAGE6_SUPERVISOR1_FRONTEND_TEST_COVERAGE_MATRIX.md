# RETIRE V2 - הוראת מפקח 1 - ביקורת הסרת בדיקות Frontend

Baseline examined: `6225fece670954cdfb2ffba6e91e20f6e8ac43b3` (16 tests in `ScenarioDraftPanel.workflow.test.tsx`).
Current working branch after UI cleanup: 11 tests in that file before this supervisor instruction.
The eight deleted cases below were not replaced one-for-one at the time of deletion.
A lower number of tests is not proof of less safety, and a higher number is not proof of more safety.

| Original deleted test (exact title) | Requirement and original behavior | Why removed | Existing safety coverage and/or replacement | Remaining gap |
| --- | --- | --- | --- | --- |
| `discards a late allowed preview after switching to another saved scenario` | Cancel previously allowed source-permission preview after an async switch between scenario IDs | Source-permission preview button/panel was removed from everyday UI | `ScenarioDraftPanel.workflow.test.tsx`: client-bound Stage 6 capability invalidation; `ScenarioStage6Panel.test.tsx`: late estimate and aggregate rejection after version/client change; backend `test_scenario_permission_preview.py` | The obsolete preview UI action no longer exists; must retain the independent scenario/client async guards. |
| `does not offer a permission check for a source-stale decision` | Stale source must not acquire a valid permission by UI action | Permission check button removed | `test_scenario_draft.py`: canonical source fingerprint, read staleness and now unrelated conversion preserving staleness; `test_scenario_calculation_admission.py`: SOURCE_STALE block; `scenarioConversionPlan.test.ts`: stale batch rejected | No UI preview required, but direct API/mutation must always block or label stale source. |
| `renders blocked permission even when the product-level preview is mixed` | A partial or mixed permission response must not be presented as universally allowed | Product-level preview panel removed | `test_scenario_permission_preview.py`: exact product matrix, corrupt/missing component fail-closed; `test_scenario_calculation_admission.py`: always blocked without admission; Stage 6 service closed envelopes | No direct UI preview remains; recheck future positive-result feature separately. |
| `expires a displayed allowed preview when the canonical source snapshot changes` | Canonical evidence change invalidates previous allowed status | No displayed permission preview after cleanup | `test_scenario_draft.py`: source balance/version fingerprint invalidation and new no-silent-reanchor regression; `ScenarioStage6Panel.test.tsx`: stale async result invalidation | Actual DB change during an in-flight staging browser request still requires manual E2E acceptance. |
| `rejects a late allowed result when product classification changes without version bump` | Classification affects source fingerprint, even without version update | Preview-result widget removed | `test_scenario_draft.py::test_source_fingerprint_detects_balance_and_classification_change`; `test_scenario_permission_preview.py`: unsupported types blocked; Stage 6 strict source-identity checks | No comparable transient UI preview to retain. |
| `shows a read-only side-by-side summary for distinct saved scenarios` | Avoid combining allocations between separate alternatives | Read-only comparison table in planning tab removed to reduce clutter | `ScenarioMonthlyComparisonPanel.test.tsx`: server-sourced two-scenario comparison with client/version fingerprint checks; backend Stage 6 monthly comparison tests | Full live positive comparison still blocked pending genuine professional evidence. |
| `opens the selected scenario from comparison without altering saved data` | Switching scenario selection must not mutate drafts or leak the previous selection | Comparison list action removed; direct alternative buttons became primary navigation | `ScenarioDraftPanel.workflow.test.tsx`: selected alternative tab transfer and client-scoped fallback; `RetirementWorkspaceScreen.test.tsx`: client transition guards | Retain cross-alternative state and reload tests as scenarios evolve. |
| `never presents a negative amount as an available remainder` | Negative remaining balance must not be rendered as available | Old comparison/remainder table removed | `scenarioConversionPlan.test.ts`: overallocations, exact cents and batch refusal; `ScenarioDraftPanel.workflow.test.tsx`: no negative available amount; server rejects excess allocations | Recheck historical stored invalid drafts via server read and admission gates. |

## Coverage retained outside the former UI

- `backend/tests/test_stage6_internal_api.py`: session/CSRF/origin and disabled-production protections for estimate, comparison and factor writes.
- `backend/tests/test_stage6_p1d_postgresql.py`: positive calculation under controlled synthetic professional evidence and pre-PTE invalidations, as well as strict scenario-version isolation.
- `backend/tests/test_scenario_draft_postgresql.py`: PostgreSQL CAS conflict, transactions, independent clones, client isolation and browser-like reload.
- `frontend/src/components/ScenarioStage6Panel.test.tsx`: rejecting forged READY envelopes, wrong client, wrong decision, expired estimate/aggregate, and cross-client async race.
- `frontend/src/components/ScenarioConversionMatrix.test.tsx` and `scenarioConversionPlan.test.ts`: per-component/program/column selection, amount/date override, stale canonical source, and exact currency.
- New `test_scenario_draft.py` regressions from supervisor instruction: preserving only unchanged elections, invalidating material edits, stale-source reanchoring prevention, atomic overalloc / foreign source and CAS conflicts.

## Release cautions

- Baseline comparison is by **test title and asserted security behavior**, not by count.
- Replaced tests require execution; adding them to the branch does **not** establish PASS.
- Frontend-level availability gating cannot grant authorization: all API admission still requires backend and database checks.
- No staging or production deployment authorized by supervisor instruction 1.
