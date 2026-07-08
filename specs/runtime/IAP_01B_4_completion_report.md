# V2-IAP-01B-4 Completion Report

## Package Identity

| Field | Value |
|---|---|
| Package ID | `V2-IAP-01B-4` |
| Scope | Backend table-boundary tests review and explicit accepted-additive-table alignment only |
| Repository | `omerb21/retireV2` |
| Branch | `master` |
| Starting commit | `25d46439f65544ab28b9c8ea778eb647cd76255e` |
| Commit created | No |

## Files Changed

| File | Change type | Purpose |
|---|---|---|
| `backend/tests/test_phase6_schema.py` | Modified | Add explicit accepted additive table allowlist and keep exact table-boundary assertion. |
| `backend/tests/test_phase7_persistence.py` | Modified | Add explicit accepted additive table allowlist and keep exact table-boundary assertion. |
| `backend/tests/test_phase9_api.py` | Modified | Add explicit accepted additive table allowlist and keep exact table-boundary assertion. |
| `specs/runtime/IAP_01B_4_exception_resolution_register.md` | Added | Records resolved table-boundary exceptions and downstream exceptions. |
| `specs/runtime/IAP_01B_4_completion_report.md` | Added | Records commands, results, final status, and acceptance recommendation. |

No V1 files were touched. No backend app code, frontend files, governance tests, route-contract tests, schema models, persistence logic, API implementation, alembic migrations, services, UI, business logic, package files, dependencies, or unrelated untracked files were modified.

## Exact Extra Tables Found

```text
capital_asset
internal_planner_judgments
pension_analysis_record
pension_holding
planner_assumption
recurring_expense
recurring_income
retirement_timing_work_intention
```

## Accepted Additive Evidence

| Table group | Evidence |
|---|---|
| V21 Package A fact tables: `capital_asset`, `pension_holding`, `planner_assumption`, `recurring_expense`, `recurring_income`, `retirement_timing_work_intention` | Accepted commit `a7cb006 v21-package-a: add retirement facts foundation`; migration `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; test authority `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `internal_planner_judgments` | Accepted commit `df956c3 slice2-p7: persist internal planner judgment`; migration `c9d4e7f1a2b5_slice_2_package_7_internal_planner_judgment.py`; exercised by `test_phase10_api_behavior.py`. |
| `pension_analysis_record` | Accepted commit `ab1b933 phase2: add pension holding analysis record foundation`; migration `f4c8b1a9d2e3_add_pension_analysis_records.py`; exercised by `test_v22_slice1_analysis_record_api.py`. |

## Exact Change Summary

Each modified test file now defines the same explicit `ACCEPTED_ADDITIVE_TABLES` set and asserts the exact expected table set:

```text
APPROVED_TABLES | ACCEPTED_ADDITIVE_TABLES | {"alembic_version"}
```

The tests do not use broad subset-only assertions and will still fail if any unexpected table appears.

## Commands Run And Results

| Command | Result |
|---|---|
| `git status --short --untracked-files=all` | Succeeded. Initial status showed unrelated untracked local files only. |
| `git rev-parse HEAD` | Succeeded: `25d46439f65544ab28b9c8ea778eb647cd76255e`. |
| `Set-Location backend; python -m pytest -q tests/test_phase6_schema.py::test_phase6_migration_applies_and_exact_table_set_exists tests/test_phase7_persistence.py::test_database_contains_only_approved_phase1_tables_plus_alembic_version tests/test_phase9_api.py::test_phase9_api_end_to_end; Set-Location ..` before changes | Failed: 3 failed. Failure output showed accepted additive extra tables and was later expanded by exact table extraction. |
| Verbose targeted pytest and temp SQLite table extraction | Confirmed exact extra tables listed above. One initial PowerShell heredoc helper failed before running; rerun with a PowerShell-safe one-liner succeeded. |
| `rg` and `git log` evidence commands | Confirmed accepted migration and test provenance for all extra tables. |
| `Set-Location backend; python -m pytest -q tests/test_phase6_schema.py::test_phase6_migration_applies_and_exact_table_set_exists tests/test_phase7_persistence.py::test_database_contains_only_approved_phase1_tables_plus_alembic_version tests/test_phase9_api.py::test_phase9_api_end_to_end; python -m pytest -q tests/test_phase6_schema.py tests/test_phase7_persistence.py tests/test_phase9_api.py; python -m pytest -q; Set-Location ..` after changes | Targeted run passed: 3 passed in 9.48s. Phase6/phase7/phase9 file suite passed: 13 passed in 28.57s. Full backend suite ran: 2 failed, 226 passed in 231.62s. |
| `git status --short --untracked-files=all` | Succeeded. Pre-report final status recorded allowed test modifications plus unrelated untracked local files. |

## Downstream Exceptions

| Test | Result |
|---|---|
| `tests/test_governance_baseline.py::test_repository_has_only_approved_tracked_changes_for_governance_gate` | Failed because `backend/tests/test_phase6_schema.py` and `backend/tests/test_phase7_persistence.py` are not yet approved in the governance allowlist. Governance tests were forbidden for this package. |
| `tests/test_v21_package_b_api.py::test_planner_assumption_route_absent` | Failed because current response status is `422` and the test expects `404`. Route-contract tests were forbidden for this package. |

## Final Git Status

```text
 M backend/tests/test_phase6_schema.py
 M backend/tests/test_phase7_persistence.py
 M backend/tests/test_phase9_api.py
?? CURRENT_PROJECT_STATE.md
?? _evidence/branches.txt
?? _evidence/git-log.txt
?? _evidence/git-status.txt
?? _evidence/head-file-tree.txt
?? _evidence/head.txt
?? _evidence/repository-history.bundle
?? _evidence/staged.patch
?? _evidence/tags.txt
?? _evidence/working-tree.patch
?? specs/bootstraps/ARCHITECT_BOOTSTRAP_V2_1.md
?? specs/bootstraps/BOOTSTRAP_CODEX_V2_1.md
?? specs/bootstraps/BOOTSTRAP_INSTRUCTOR_V2_1.md
?? specs/bootstraps/BOOTSTRAP_SUPERVISOR_V2_1.md
?? specs/runtime/IAP_01B_4_completion_report.md
?? specs/runtime/IAP_01B_4_exception_resolution_register.md
```

## Recommendation

```text
YES_WITH_EXPLICIT_DOWNSTREAM_EXCEPTIONS
```

V2-IAP-01B-4 may be accepted for the table-boundary scope. The known table-boundary failures are resolved with exact accepted-additive table assertions, no broad wildcard or subset-only assertion was introduced, and no commit was created.
