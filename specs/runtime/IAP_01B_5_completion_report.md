# V2-IAP-01B-5 Completion Report

## Package Identity

| Field | Value |
|---|---|
| Package ID | `V2-IAP-01B-5` |
| Scope | Planner-assumptions route contract review only |
| Repository | `omerb21/retireV2` |
| Branch | `master` |
| Starting commit | `bee5557ea322671e835461ff063609bec71c9a0e` |
| Commit created | No |

## Files Changed

| File | Change type | Purpose |
|---|---|---|
| `backend/tests/test_v21_package_b_api.py` | Modified | Replace stale absent-route assertion with explicit current planner-assumptions validation contract. |
| `specs/runtime/IAP_01B_5_exception_resolution_register.md` | Added | Records resolved route-contract exception and downstream governance exception. |
| `specs/runtime/IAP_01B_5_completion_report.md` | Added | Records commands, results, final status, and acceptance recommendation. |

No V1 files were touched. No backend app code, frontend files, governance tests, schema/table-boundary tests, alembic, migrations, models, services, UI, business logic, package files, dependencies, or unrelated untracked files were modified.

## Exact Current Failure

```text
tests/test_v21_package_b_api.py::test_planner_assumption_route_absent
assert 422 == 404
```

## Accepted Route Contract Evidence

`git log` and repository search show accepted later Package D route behavior:

```text
6295270 v21-package-d: add assumptions and advisory missing information maintenance
```

That commit includes `backend/tests/test_v21_package_d_api.py`, which asserts planner-assumption create/list/read/update, lifecycle filtering, validation behavior, ownership, and no delete/supersede routes. Current `backend/app/api/clients_routes.py` defines POST, GET list, GET one, and PUT routes for `/api/clients/{client_id}/planner-assumptions`.

## Exact Change Summary

Renamed:

```text
test_planner_assumption_route_absent
```

to:

```text
test_planner_assumption_route_present_rejects_incomplete_package_d_payload
```

The rewritten test posts the same incomplete payload and now asserts exactly:

```text
status_code == 422
```

and exact missing required fields:

```text
("body", "assumption_category")
("body", "assumption_value_text")
("body", "rationale")
("body", "owner")
```

No multiple-status allowance was added.

## Commands Run And Results

| Command | Result |
|---|---|
| `git status --short --untracked-files=all` | Succeeded. Initial status showed unrelated untracked local files only. |
| `git rev-parse HEAD` | Succeeded: `bee5557ea322671e835461ff063609bec71c9a0e`. |
| `Set-Location backend; python -m pytest -q tests/test_v21_package_b_api.py::test_planner_assumption_route_absent; Set-Location ..` | Failed as expected before change: `assert 422 == 404`. |
| `git log`, `rg`, and `Get-Content` evidence commands | Confirmed accepted Package D planner-assumptions route contract. |
| Direct response probe | Initial helper had a PowerShell/Python separator mistake. Corrected helper then hit the known direct `TestClient`/`httpx` issue because pytest `conftest.py` was not loaded. Pytest failure and Package D route tests provided the accepted route evidence. |
| `Set-Location backend; python -m pytest -q tests/test_v21_package_b_api.py::test_planner_assumption_route_present_rejects_incomplete_package_d_payload; python -m pytest -q tests/test_v21_package_b_api.py; python -m pytest -q; Set-Location ..` | Replacement targeted test passed: 1 passed in 3.88s. `test_v21_package_b_api.py` passed: 39 passed in 107.08s. Full backend suite ran: 1 failed, 227 passed in 329.65s. |
| `git status --short --untracked-files=all` | Succeeded. Pre-report final status recorded allowed test modification plus unrelated untracked local files. |

## Downstream Exceptions

| Test | Result |
|---|---|
| `tests/test_governance_baseline.py::test_repository_has_only_approved_tracked_changes_for_governance_gate` | Failed because `backend/tests/test_v21_package_b_api.py` is not yet approved in the governance allowlist. Governance tests were forbidden for this package. |

## Final Git Status

```text
 M backend/tests/test_v21_package_b_api.py
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
?? specs/runtime/IAP_01B_5_completion_report.md
?? specs/runtime/IAP_01B_5_exception_resolution_register.md
```

## Recommendation

```text
YES_WITH_EXPLICIT_DOWNSTREAM_EXCEPTION
```

V2-IAP-01B-5 may be accepted for the planner-assumptions route-contract scope. The stale absent-route test was replaced with one explicit accepted current route validation contract, and no commit was created.
