# Baseline Exception Register

Package: `V2-IAP-01A`

| Exception ID | Area | Command | Observed result | Current classification | Blocks next package? | Required follow-up |
|---|---|---|---|---|---|---|
| `IAP01A-BE-001` | Backend test collection | `Set-Location backend; python -m pytest --collect-only -q; Set-Location ..` | `226 tests collected`, then collection stopped at `tests/test_health.py` with `TypeError: Client.__init__() got an unexpected keyword argument 'app'`. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, `BLOCKING_PLATFORM_ISSUE` | Yes, unless V2-IAP-01B explicitly authorizes platform/test-environment fixes. | Decide and authorize dependency/test-client/runtime test-environment hardening in V2-IAP-01B. |
| `IAP01A-BE-002` | Backend test execution | `Set-Location backend; python -m pytest -q; Set-Location ..` | Execution stopped during collection at `tests/test_health.py` with `TypeError: Client.__init__() got an unexpected keyword argument 'app'`. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION`, `BLOCKING_PLATFORM_ISSUE` | Yes, unless V2-IAP-01B explicitly authorizes platform/test-environment fixes. | Resolve or explicitly carry backend test execution blocker in V2-IAP-01B. |
| `IAP01A-FE-001` | Frontend tests | `Set-Location frontend; npm test; Set-Location ..` | Failed: `2 failed | 78 passed (80)` tests. `PensionAnalysisRecordSection.test.tsx` cannot find `Existing Pension Provider`; `RetirementPlanningFactsSection.test.tsx` expected 5 lifecycle filters and got 6. | `BASELINE_EXCEPTION`, `TEST_EXCEPTION` | Yes for broad feature packages; acceptable only as explicit exception for targeted platform/runtime hardening. | Decide whether V2-IAP-01B carries these as known frontend exceptions or includes separately authorized frontend test/UI fix scope. |
| `IAP01A-GIT-001` | Repository working tree | `git status --short --untracked-files=all` | Unrelated untracked files exist in `CURRENT_PROJECT_STATE.md`, `_evidence/`, and `specs/bootstraps/`. | `BASELINE_EXCEPTION`, `NON_BLOCKING_DOCUMENTED_EXCEPTION` | No for this package; should be reviewed before commit/staging. | Keep untracked files separate from IAP-01A scope; stage only approved files if a later commit is authorized. |

## Positive Baseline Evidence

| Area | Command | Observed result | Evidence status |
|---|---|---|---|
| Backend route evidence | `Set-Location backend; python -c "from app.main import app; ..."; Set-Location ..` | Route listing succeeded and produced registered FastAPI routes. | Positive runtime baseline evidence; not an exception. |
| Frontend build | `Set-Location frontend; npm run build; Set-Location ..` | Passed: `tsc -b && vite build`, 53 modules transformed, built in 5.18s. | Positive build baseline evidence; not an exception. |

## Recommendation

`YES_WITH_EXPLICIT_EXCEPTIONS`: V2-IAP-01B may start only as a targeted platform/runtime hardening package that explicitly addresses or carries the actual backend pytest, frontend test, and unrelated-untracked-file baseline exceptions above. It should not start as broad business feature work.
