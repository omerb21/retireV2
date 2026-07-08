# V2-IAP-01B-4 Exception Resolution Register

Package: `V2-IAP-01B-4`

Scope: backend table-boundary tests review and explicit accepted-additive-table alignment only.

## Resolved Exceptions

| Exception ID | Exception | Classification | Resolution status | Files changed | Evidence |
|---|---|---|---|---|---|
| `IAP01B4-BE-001` | `tests/test_phase6_schema.py::test_phase6_migration_applies_and_exact_table_set_exists` failed because the exact table-boundary assertion did not include later accepted additive tables. | `STALE_TEST_EXPECTATION`, `ACCEPTED_ADDITIVE_SCHEMA_STATE` | Resolved with explicit accepted additive table allowlist and exact-set assertion. | `backend/tests/test_phase6_schema.py` | Targeted run passed: 3 passed in 9.48s. |
| `IAP01B4-BE-002` | `tests/test_phase7_persistence.py::test_database_contains_only_approved_phase1_tables_plus_alembic_version` failed for the same accepted additive tables. | `STALE_TEST_EXPECTATION`, `ACCEPTED_ADDITIVE_SCHEMA_STATE` | Resolved with explicit accepted additive table allowlist and exact-set assertion. | `backend/tests/test_phase7_persistence.py` | Targeted run passed: 3 passed in 9.48s. |
| `IAP01B4-BE-003` | `tests/test_phase9_api.py::test_phase9_api_end_to_end` failed for the same accepted additive tables. | `STALE_TEST_EXPECTATION`, `ACCEPTED_ADDITIVE_SCHEMA_STATE` | Resolved with explicit accepted additive table allowlist and exact-set assertion. | `backend/tests/test_phase9_api.py` | Targeted run passed: 3 passed in 9.48s; phase6/phase7/phase9 file suite passed: 13 passed in 28.57s. |

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

| Table | Accepted package / commit evidence | Migration / test evidence |
|---|---|---|
| `capital_asset` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `pension_holding` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `planner_assumption` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`; later API behavior accepted in `6295270 v21-package-d`. |
| `recurring_expense` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `recurring_income` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `retirement_timing_work_intention` | `a7cb006 v21-package-a: add retirement facts foundation` | `d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py`; `test_v21_package_a_persistence.py` `APPROVED_FACT_TABLES`. |
| `internal_planner_judgments` | `df956c3 slice2-p7: persist internal planner judgment` | `c9d4e7f1a2b5_slice_2_package_7_internal_planner_judgment.py`; `test_phase10_api_behavior.py`. |
| `pension_analysis_record` | `ab1b933 phase2: add pension holding analysis record foundation` | `f4c8b1a9d2e3_add_pension_analysis_records.py`; `test_v22_slice1_analysis_record_api.py`. |

## Downstream Exceptions

| Exception ID | Downstream exception | Classification | Status | Evidence |
|---|---|---|---|---|
| `IAP01B4-DOWNSTREAM-001` | Full backend suite governance gate reports `backend/tests/test_phase6_schema.py` and `backend/tests/test_phase7_persistence.py` as unapproved tracked changes. | `GOVERNANCE_ALLOWLIST_FOLLOWUP` | Carried. Governance tests were forbidden for this package. | `python -m pytest -q`: `test_repository_has_only_approved_tracked_changes_for_governance_gate` failed. |
| `IAP01B4-DOWNSTREAM-002` | `tests/test_v21_package_b_api.py::test_planner_assumption_route_absent` expects `404`; current route returns `422`. | `STALE_ROUTE_CONTRACT_EXPECTATION` | Carried. Route-contract tests were forbidden for this package. | `python -m pytest -q`: `assert 422 == 404`. |

## Recommendation

```text
YES_WITH_EXPLICIT_DOWNSTREAM_EXCEPTIONS
```

V2-IAP-01B-4 may be accepted for the table-boundary scope because the three target failures are resolved with exact accepted-additive table assertions.
