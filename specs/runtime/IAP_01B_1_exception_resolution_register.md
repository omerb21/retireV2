# V2-IAP-01B-1 Exception Resolution Register

Package: `V2-IAP-01B-1`

Scope: backend pytest collection compatibility only.

| Exception ID | Exception | Classification | Resolution status | Files changed | Evidence |
|---|---|---|---|---|---|
| `IAP01B1-BE-001` | Backend pytest collection stopped at `tests/test_health.py` with `TypeError: Client.__init__() got an unexpected keyword argument 'app'`. | `DEPENDENCY_COMPATIBILITY`, `TEST_HARNESS_INCOMPATIBILITY` | Resolved. Backend pytest collection now completes. | `backend/conftest.py` | Before change, `python -m pytest --collect-only -q` collected 226 tests and stopped with 1 collection error. After change, `python -m pytest --collect-only -q` collected 228 tests. |

## Downstream Exceptions Discovered

These exceptions were discovered only after the collection blocker was removed. They were not fixed because V2-IAP-01B-1 is limited to backend pytest collection compatibility.

| Exception ID | Downstream exception | Classification | Status | Evidence |
|---|---|---|---|---|
| `IAP01B1-DOWNSTREAM-001` | `tests/test_governance_baseline.py::test_repository_has_no_untracked_files_for_governance_gate` fails because `backend/conftest.py` is untracked. | `GOVERNANCE_BASELINE_EXPECTATION` | Carried for a later package or owner decision. | `python -m pytest -q`: assertion reports `untracked files detected: ['?? backend/conftest.py']`. |
| `IAP01B1-DOWNSTREAM-002` | `tests/test_phase6_schema.py::test_phase6_migration_applies_and_exact_table_set_exists` fails on exact table-set assertion after later accepted additive tables. | `STALE_TEST_EXPECTATION` | Carried for a later package. | `python -m pytest -q`: extra tables include later planning fact tables. |
| `IAP01B1-DOWNSTREAM-003` | `tests/test_phase7_persistence.py::test_database_contains_only_approved_phase1_tables_plus_alembic_version` fails on exact table-set assertion after later accepted additive tables. | `STALE_TEST_EXPECTATION` | Carried for a later package. | `python -m pytest -q`: extra tables include later planning fact tables. |
| `IAP01B1-DOWNSTREAM-004` | `tests/test_phase9_api.py::test_phase9_api_end_to_end` fails on exact table-set assertion after later accepted additive tables. | `STALE_TEST_EXPECTATION` | Carried for a later package. | `python -m pytest -q`: extra tables include later planning fact tables. |
| `IAP01B1-DOWNSTREAM-005` | `tests/test_v21_package_b_api.py::test_planner_assumption_route_absent` expects `404`; current route returns `422`. | `STALE_TEST_EXPECTATION` | Carried for a later package. | `python -m pytest -q`: `assert 422 == 404`. |

## Recommendation

```text
YES_WITH_EXPLICIT_DOWNSTREAM_EXCEPTIONS
```

V2-IAP-01B-1 may be accepted as a collection-compatibility package because the required collection blocker is resolved and no existing tests or application runtime code were modified.
