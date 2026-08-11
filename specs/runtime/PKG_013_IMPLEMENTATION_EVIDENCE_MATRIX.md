# PKG-013 Implementation Evidence Matrix

Package: `PKG-013 — M09 Deterministic Monthly Cashflow Orchestration Foundation`

This is implementation-review evidence, not an acceptance record, production-readiness claim, M10 implementation, or authorization for another package. Test names refer to `backend/tests/test_pkg013_m09_cashflow.py` (`behavior`), `backend/tests/test_pkg013_architecture.py` (`architecture`), `backend/tests/test_pkg013_migration.py` (`migration`), and `frontend/src/pages/M09CashflowScreen.test.tsx` (`UI`).

## Acceptance criteria

| Criterion | Implementation evidence | Test evidence | Result |
|---|---|---|---|
| AC-013-001 | Isolated `pkg-013-implementation` branch was created from authorized base `f8ed3b2b...`; accepted definition and planning records are untouched. | Pre-implementation Git SHA/status checks and final changed-file audit. | PASS |
| AC-013-002 | Service constants and request validation admit only `deterministic_monthly_cashflow/v1`. | `test_exact_family_horizon_and_extra_fields_fail_closed`. | PASS |
| AC-013-003 | M09 consumes authoritative source amounts and contains no upstream calculation formula. | `test_m09_has_no_upstream_formula_or_forbidden_scope_import`; `test_m09_consumes_the_m06_authoritative_handoff_without_formula_copy`. | PASS |
| AC-013-004 | `_monthly_rows` owns only Decimal inflow/outflow sums, net subtraction, and range sums. | `test_m09_business_arithmetic_is_only_addition_and_subtraction`; `test_exact_decimal_aggregation_and_immutable_evidence`. | PASS |
| AC-013-005 | `M09ResolvedComponentInventory` persists server-resolved client/family/horizon/domain/timestamp/fingerprint evidence; request has no subset fields. | `test_server_inventory_and_none_are_server_owned`; `test_m09_request_and_ui_have_no_caller_portfolio_authority`. | PASS |
| AC-013-006 | Canonical component evidence includes ID/type/direction/month/amount/source/version/fingerprint/owner/provenance. | `test_exact_decimal_aggregation_and_immutable_evidence`; `test_m06_handoff_is_consumed_without_conversion`. | PASS |
| AC-013-007 | `_monthly_rows` rejects a repeated canonical component identity before persistence. | Behavioral duplicate-economic-meaning test plus architecture/service guard review; duplicate-ID branch is deterministic. | PASS |
| AC-013-008 | Recurring-income assessment enforces current, monthly, gross, same-client, full-month, canonical ILS evidence. | Parameterized `test_ineligible_current_recurring_record_blocks_partial_success`; exact aggregation test. | PASS |
| AC-013-009 | Recurring-expense assessment enforces current, monthly, same-client, full-month, canonical ILS evidence. | Parameterized ineligible test; exact aggregation test. | PASS |
| AC-013-010 | Empty eligible domains receive server-generated none evidence bound to assessment, actor, snapshot and fingerprint. | `test_server_inventory_and_none_are_server_owned`. | PASS |
| AC-013-011 | Required canonical ordered inclusive months are schema-validated and expanded ascending. | `test_exact_family_horizon_and_extra_fields_fail_closed`; exact aggregation month-order assertion. | PASS |
| AC-013-012 | Non-monthly and partial-month sources block; no conversion/proration operation exists. | Parameterized ineligible test; arithmetic architecture test. | PASS |
| AC-013-013 | Central `M09_MONEY_PRECISION=20`/`M09_MONEY_SCALE=2` derives exact bounds and validates every component, monthly total, net and range total before `Numeric(20,2)` persistence. | `test_numeric_20_2_exact_boundaries_are_explicit`; `test_exact_maximum_component_persists_for_one_month`; `test_period_net_accepts_exact_negative_boundary_and_rejects_below_it`; overflow API tests. | PASS |
| AC-013-014 | Source components are not rerounded; totals use exact Decimal sums/subtraction. | Exact aggregation and zero tests; arithmetic architecture test. | PASS |
| AC-013-015 | Typed domain blockers persist dependency failure; aggregate overflow persists `calculation_failed`; neither produces partial rows or relies on DB overflow. | `test_failed_inventory_is_persisted_without_partial_rows`; `test_oversized_component_is_typed_dependency_failure`; monthly/range overflow API tests; M06 mismatch test. | PASS |
| AC-013-016 | Request/UI expose no subset, omit, waive, or run-anyway control. | Extra-field rejection; architecture request test; UI `offers no component omission...`. | PASS |
| AC-013-017 | M05 `eligible_for_m06` is not an M09 input contract. | Architecture forbidden-scope test; M06 snapshot is retained only behind M06 provenance. | PASS |
| AC-013-018 | M05 balances are never emitted as component types or converted in M09. | Closed-component vocabulary test; arithmetic/forbidden-scope architecture tests. | PASS |
| AC-013-019 | M06 revalidation verifies manifest fingerprint, predecessor bindings and exact column/fingerprinted-handoff equality; M09 independently rejects a mismatch. | `test_m06_handoff_column_and_fingerprinted_manifest_integrity_contract`; `test_m09_rejects_mismatched_m06_handoff_without_success`; M06 regression suite. | PASS |
| AC-013-020 | M09 reads canonical `ILS/month` from the verified fingerprinted JSON handoff, confirms equality with the indexed column, and records `formula_owner=M06`; no conversion is copied. | Valid/tampered column, tampered JSON, mismatch and bad-fingerprint cases in `test_m06_handoff_column_and_fingerprinted_manifest_integrity_contract`; M09 mismatch/API and architecture tests. | PASS |
| AC-013-021 | Capital-equivalent mode and absent/invalid handoff never become a monthly zero/component. | `test_missing_or_invalid_m06_handoff_fails_closed`; M06 boundary service branch and structural test. | PASS |
| AC-013-022 | M09 has no M07/fixation manifest or dependency. | Forbidden-scope architecture test and changed-file audit. | PASS |
| AC-013-023 | M09 v1 has no M08 component/API/dependency. | Forbidden-scope architecture test and closed-component test. | PASS |
| AC-013-024 | Typed request/manifest use fixed keys and `extra=forbid`, binding persisted inventory ID/fingerprint. | Extra-field rejection; architecture request test; immutable evidence test. | PASS |
| AC-013-025 | No request free text/arbitrary assumptions can reach execution. | Extra-field rejection and request architecture test. | PASS |
| AC-013-026 | Run persists immutable assumption manifest and upstream snapshot with consumed component/source evidence and fingerprints. | Exact aggregation/immutable evidence and source-edit history tests. | PASS |
| AC-013-027 | Read-time reassessment detects source changes without rewriting historical rows. | `test_source_edit_preserves_history_and_invalidates_currentness`. | PASS |
| AC-013-028 | ORM guards plus database triggers independently reject UPDATE/DELETE on all three evidence tables while allowing insert, read and successor insert. | `test_append_only_records_reject_orm_and_bulk_mutation`; `test_pkg013_database_triggers_block_raw_update_delete_but_allow_append`; corrective downgrade and PostgreSQL offline-DDL tests. | PASS |
| AC-013-029 | Persisted status, derived currentness, and derived M10 eligibility are distinct fields/contracts. | Replay currentness and M10 reason-code tests. | PASS |
| AC-013-030 | Run response exposes ordered rows, evidence, totals, manifests, fingerprints, status and derived assessments only. | Exact aggregation test; API response-model runtime coverage. | PASS |
| AC-013-031 | Canonical JSON/deterministic ordering excludes run identity/timestamp from semantic fingerprint. | `test_replay_semantic_fingerprint_excludes_run_metadata`. | PASS |
| AC-013-032 | Read-time currentness checks leaf, supported contract, integrity, material reassessment and eligibility. | Replay and source-edit currentness tests; integrity code exercised by every run response. | PASS |
| AC-013-033 | M10 eligibility is false for failed/stale/blocking/integrity-invalid runs and includes reason codes. | Failed-run and stale/superseded M10 tests; current success assertion. | PASS |
| AC-013-034 | Only a derived M10 eligibility endpoint exists; no M10 execution/recalculation code was added. | Route/static changed-file audit and full regression suite. | PASS |
| AC-013-035 | Warning categories are checked by stable classification; mandatory warnings fail eligibility and informational warnings remain explanatory. | Eligibility implementation path plus schema/runtime response coverage; no generic acceptance input exists. | PASS |
| AC-013-036 | Every inventory/run/history/currentness/eligibility lookup scopes by client and hides foreign existence. | Both client-isolation tests including direct-service enforcement. | PASS |
| AC-013-037 | Schemas and server models own actor, IDs, timestamps, inventory, status, fingerprints, results and assessments. | Extra-field rejection, server-none test, architecture request test, API runtime suite. | PASS |
| AC-013-038 | UI keeps independent generation/epoch ownership for inventory, execute, history and saved-result/currentness/M10 composite loads. | Fourteen controlled-promise UI tests separately exercise A→B/A→B→A stale success, rejection, structured error, finally, pending owner, old-A/new-A and successful new owner. | PASS |
| AC-013-039 | Original additive migration `a7c9e1f3b805` remains published; corrective trigger migration `c4e8a1f6d203` is one head above it and has deterministic downgrade. | Migration suite covers upgrade/downgrade/re-upgrade, evidence-loss refusal, raw-SQL triggers, corrective downgrade, and SQLite/PostgreSQL offline DDL. | PASS |
| AC-013-040 | Focused, predecessor and full suites plus build, compile/import, Alembic and diff checks execute at the corrected proposed HEAD. | Exact runtime counts and command results are recorded in the correction report; focused backend and UI suites include all four defect regressions. | PASS |

## Negative acceptance criteria

| Criterion | Implementation evidence | Test evidence | Result |
|---|---|---|---|
| NAC-013-001 | No upstream M05/M06/M07/M08/tax/fixation/indexation formula is present in M09. | Forbidden-scope and M06-owner architecture tests. | PASS |
| NAC-013-002 | Monetary authority uses Decimal/Numeric and canonical strings; no float conversion path. | Closed-component/no-float and arithmetic tests. | PASS |
| NAC-013-003 | Both months are required and no date-derived/default horizon exists. | Family/horizon rejection test; architecture source scan. | PASS |
| NAC-013-004 | Exact request schema forbids family aliases, component universe/subsets and required-domain input. | Extra-field rejection and request architecture tests. | PASS |
| NAC-013-005 | Request has no notes/title/rationale/arbitrary JSON/LLM field. | Extra-field rejection and request architecture tests. | PASS |
| NAC-013-006 | Missing, oversized, fingerprint-invalid or column/manifest-mismatched M06 authority is typed and fail-closed; no conflict is treated as zero. | M06 manifest adversarial cases, M09 mismatch failure, oversized-component failure, server-none and missing-handoff tests. | PASS |
| NAC-013-007 | No partial-success override exists in API or UI. | Failed-inventory persistence and no-omission UI tests. | PASS |
| NAC-013-008 | M09 never consumes M05 downstream-eligibility as its authority. | Forbidden-scope architecture test. | PASS |
| NAC-013-009 | No balance conversion/allocation/amortization exists in M09. | Arithmetic architecture and closed-component tests. | PASS |
| NAC-013-010 | M06 formula/coefficient/ratio rounding remains solely M06-owned. | M06 handoff behavior and owner architecture tests. | PASS |
| NAC-013-011 | No inherited fixation/tax manifest exists. | Forbidden-scope architecture test. | PASS |
| NAC-013-012 | No M08 dependency is introduced. | Forbidden-scope architecture test and changed-file audit. | PASS |
| NAC-013-013 | No M08 technical-success/latest gate exists. | Forbidden-scope architecture test. | PASS |
| NAC-013-014 | Success, currentness and M10 eligibility are independently derived. | Source-edit and stale-success M10 tests. | PASS |
| NAC-013-015 | Historical M09 evidence rejects ORM, SQLAlchemy bulk and raw-SQL UPDATE/DELETE; DB triggers provide enforcement independently of application interception. | ORM/bulk append-only test; raw connection trigger test for every table; successor-insert/read and downgrade tests. | PASS |
| NAC-013-016 | Composite client scoping prevents cross-client association and public existence leakage. | Full client-resource and direct-service isolation tests. | PASS |
| NAC-013-017 | Caller cannot send authoritative inventory/result/actor/status/fingerprint/currentness/eligibility fields. | Request extra-field rejection and server-ownership architecture test. | PASS |
| NAC-013-018 | No proration/frequency conversion/interpolation/inflation/return/discount arithmetic exists. | Ineligible source tests and arithmetic architecture test. | PASS |
| NAC-013-019 | No pension coefficient/default/fallback exists. | Forbidden-authority literal and arithmetic architecture tests. | PASS |
| NAC-013-020 | No minimum-pension rule exists. | Forbidden-authority architecture test. | PASS |
| NAC-013-021 | No discount rate, NPV, or discounting exists. | Forbidden-authority architecture test. | PASS |
| NAC-013-022 | No maximum-age or age-derived horizon exists. | Forbidden-authority architecture test and explicit horizon tests. | PASS |
| NAC-013-023 | No hidden six/12-month projection exists. | Required explicit horizon test and source/architecture audit. | PASS |
| NAC-013-024 | No scenario-side fixation/grant/CBS/exemption/tax calculation exists. | Forbidden-scope architecture test. | PASS |
| NAC-013-025 | Execution writes only new M09 evidence and the minimal M06 result handoff; no source state is mutated. | Source-edit/history and append-only tests; changed-file/service audit. | PASS |
| NAC-013-026 | No comparison/ranking/optimization/recommendation/report output exists. | Response schema and changed-file audit. | PASS |
| NAC-013-027 | No net-tax/insurance/withdrawal/commutation component or formula exists. | Closed-component and forbidden-scope architecture tests. | PASS |
| NAC-013-028 | Only exact v1 family exists; no generic/alternate/Monte Carlo family. | Unsupported-family rejection test. | PASS |
| NAC-013-029 | No professional defaults, advice, or LLM inputs/calculations exist. | Request architecture and forbidden-scope tests. | PASS |
| NAC-013-030 | No M10-M14, formal 161D/M08E, or 02M implementation/change is included. | Changed-file audit against base. | PASS |
| NAC-013-031 | UI/API wording makes no production, professional-sufficiency, or parity claim. | UI render test and response/static review. | PASS |
| NAC-013-032 | Implementation is proposed on a review branch only; no acceptance record or master merge is created. | Final Git branch/remote verification. | PASS |
