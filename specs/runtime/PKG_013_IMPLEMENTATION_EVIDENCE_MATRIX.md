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
| AC-013-013 | Monetary columns are `Numeric(...,2)` and service accepts/persists Decimal-derived canonical strings only. | `test_component_contract_is_closed_and_has_no_float_authority`; exact aggregation test. | PASS |
| AC-013-014 | Source components are not rerounded; totals use exact Decimal sums/subtraction. | Exact aggregation and zero tests; arithmetic architecture test. | PASS |
| AC-013-015 | Typed domain blockers make inventory incomplete and persist a dependency-failed run without result rows. | Parameterized ineligible test; `test_failed_inventory_is_persisted_without_partial_rows`; M06 missing-handoff test. | PASS |
| AC-013-016 | Request/UI expose no subset, omit, waive, or run-anyway control. | Extra-field rejection; architecture request test; UI `offers no component omission...`. | PASS |
| AC-013-017 | M05 `eligible_for_m06` is not an M09 input contract. | Architecture forbidden-scope test; M06 snapshot is retained only behind M06 provenance. | PASS |
| AC-013-018 | M05 balances are never emitted as component types or converted in M09. | Closed-component vocabulary test; arithmetic/forbidden-scope architecture tests. | PASS |
| AC-013-019 | M06 candidates require current resolved supported leaf, downstream eligibility, manifest and fingerprint. | M06 handoff success, overlap, and missing-handoff behavior tests. | PASS |
| AC-013-020 | Minimal M06-owned `authoritative_monthly_amount` handoff supplies canonical `ILS/month`; M09 records `formula_owner=M06`. | M06 handoff behavior and architecture tests; 44-test M06 regression suite. | PASS |
| AC-013-021 | Capital-equivalent mode and absent/invalid handoff never become a monthly zero/component. | `test_missing_or_invalid_m06_handoff_fails_closed`; M06 boundary service branch and structural test. | PASS |
| AC-013-022 | M09 has no M07/fixation manifest or dependency. | Forbidden-scope architecture test and changed-file audit. | PASS |
| AC-013-023 | M09 v1 has no M08 component/API/dependency. | Forbidden-scope architecture test and closed-component test. | PASS |
| AC-013-024 | Typed request/manifest use fixed keys and `extra=forbid`, binding persisted inventory ID/fingerprint. | Extra-field rejection; architecture request test; immutable evidence test. | PASS |
| AC-013-025 | No request free text/arbitrary assumptions can reach execution. | Extra-field rejection and request architecture test. | PASS |
| AC-013-026 | Run persists immutable assumption manifest and upstream snapshot with consumed component/source evidence and fingerprints. | Exact aggregation/immutable evidence and source-edit history tests. | PASS |
| AC-013-027 | Read-time reassessment detects source changes without rewriting historical rows. | `test_source_edit_preserves_history_and_invalidates_currentness`. | PASS |
| AC-013-028 | Three additive append-only entities, predecessor chain and server-authorized inserts preserve history. | `test_append_only_records_reject_orm_and_bulk_mutation`; replay/successor test; migration tests. | PASS |
| AC-013-029 | Persisted status, derived currentness, and derived M10 eligibility are distinct fields/contracts. | Replay currentness and M10 reason-code tests. | PASS |
| AC-013-030 | Run response exposes ordered rows, evidence, totals, manifests, fingerprints, status and derived assessments only. | Exact aggregation test; API response-model runtime coverage. | PASS |
| AC-013-031 | Canonical JSON/deterministic ordering excludes run identity/timestamp from semantic fingerprint. | `test_replay_semantic_fingerprint_excludes_run_metadata`. | PASS |
| AC-013-032 | Read-time currentness checks leaf, supported contract, integrity, material reassessment and eligibility. | Replay and source-edit currentness tests; integrity code exercised by every run response. | PASS |
| AC-013-033 | M10 eligibility is false for failed/stale/blocking/integrity-invalid runs and includes reason codes. | Failed-run and stale/superseded M10 tests; current success assertion. | PASS |
| AC-013-034 | Only a derived M10 eligibility endpoint exists; no M10 execution/recalculation code was added. | Route/static changed-file audit and full regression suite. | PASS |
| AC-013-035 | Warning categories are checked by stable classification; mandatory warnings fail eligibility and informational warnings remain explanatory. | Eligibility implementation path plus schema/runtime response coverage; no generic acceptance input exists. | PASS |
| AC-013-036 | Every inventory/run/history/currentness/eligibility lookup scopes by client and hides foreign existence. | Both client-isolation tests including direct-service enforcement. | PASS |
| AC-013-037 | Schemas and server models own actor, IDs, timestamps, inventory, status, fingerprints, results and assessments. | Extra-field rejection, server-none test, architecture request test, API runtime suite. | PASS |
| AC-013-038 | UI provides horizon, server inventory, blockers, execution, results, history/currentness/eligibility without selection authority; request ownership uses route generation plus channel epoch. | Five controlled-promise UI tests cover stale success/rejection/error/finally, A→B→A, old/new A, history/result and pending owner. | PASS |
| AC-013-039 | Migration `a7c9e1f3b805` is additive above `f9a1c3e5b702`, one-head, reversible without evidence and refuses evidence loss. | Four migration tests, including SQLite/PostgreSQL offline DDL. | PASS |
| AC-013-040 | Focused/full suites, build, compile, Alembic and diff checks are recorded in the implementation report. | Runtime commands reported at proposed implementation HEAD. | PASS |

## Negative acceptance criteria

| Criterion | Implementation evidence | Test evidence | Result |
|---|---|---|---|
| NAC-013-001 | No upstream M05/M06/M07/M08/tax/fixation/indexation formula is present in M09. | Forbidden-scope and M06-owner architecture tests. | PASS |
| NAC-013-002 | Monetary authority uses Decimal/Numeric and canonical strings; no float conversion path. | Closed-component/no-float and arithmetic tests. | PASS |
| NAC-013-003 | Both months are required and no date-derived/default horizon exists. | Family/horizon rejection test; architecture source scan. | PASS |
| NAC-013-004 | Exact request schema forbids family aliases, component universe/subsets and required-domain input. | Extra-field rejection and request architecture tests. | PASS |
| NAC-013-005 | Request has no notes/title/rationale/arbitrary JSON/LLM field. | Extra-field rejection and request architecture tests. | PASS |
| NAC-013-006 | Ineligible/missing/invalid authority blocks or is excluded with typed evidence; none is server-generated only. | Ineligible parameterization, server-none, M06 missing-handoff tests. | PASS |
| NAC-013-007 | No partial-success override exists in API or UI. | Failed-inventory persistence and no-omission UI tests. | PASS |
| NAC-013-008 | M09 never consumes M05 downstream-eligibility as its authority. | Forbidden-scope architecture test. | PASS |
| NAC-013-009 | No balance conversion/allocation/amortization exists in M09. | Arithmetic architecture and closed-component tests. | PASS |
| NAC-013-010 | M06 formula/coefficient/ratio rounding remains solely M06-owned. | M06 handoff behavior and owner architecture tests. | PASS |
| NAC-013-011 | No inherited fixation/tax manifest exists. | Forbidden-scope architecture test. | PASS |
| NAC-013-012 | No M08 dependency is introduced. | Forbidden-scope architecture test and changed-file audit. | PASS |
| NAC-013-013 | No M08 technical-success/latest gate exists. | Forbidden-scope architecture test. | PASS |
| NAC-013-014 | Success, currentness and M10 eligibility are independently derived. | Source-edit and stale-success M10 tests. | PASS |
| NAC-013-015 | ORM and bulk update/delete of M09 evidence are blocked. | Append-only mutation test; downgrade evidence-loss test. | PASS |
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
