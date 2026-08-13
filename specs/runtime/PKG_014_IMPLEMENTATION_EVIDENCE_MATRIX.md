# PKG-014 Implementation Evidence Matrix

Package: `PKG-014 ג€” M09 Declared Retirement Cashflow Adjustments and Parallel Scenario Subjects Foundation`

Definition boundary: `39fbc553e6bca7f10b9c1d237d3be1366be11477`  
Implementation base: `c9af24365a533e509fd327ce5056dae719b656bf`  
Scenario contract: `declared_retirement_cashflow_adjustments/v1`

This is implementation evidence only. It does not amend the accepted definition, authorize M10, assert professional authority, or claim production readiness.

## Acceptance Criteria

| Status | Criterion | Implementation evidence | Test evidence |
|---|---|---|---|
| PASS | AC-014-001 | Dedicated implementation branch from the exact accepted master base. | Git verification. |
| PASS | AC-014-002 | Closed family/version constants and request literals. | `test_adjusted_validation_and_semantic_duplicate_rejection`. |
| PASS | AC-014-003 | New service delegates factual resolution and upstream formulas to accepted owners. | PKG-013 regression suite. |
| PASS | AC-014-004 | Legacy routes, models, tables, currentness, and eligibility remain unchanged. | `test_existing_family_remains_separate`; PKG-013 suite. |
| PASS | AC-014-005 | UI labels the outcome only as a planner-declared sensitivity alternative. | `M09ScenarioSubjects.test.tsx`. |
| PASS | AC-014-006 | `m09_scenario_subjects` binds client, contract, manifests, fingerprints, provenance, actor, and timestamp. | focused API and migration tests. |
| PASS | AC-014-007 | Semantic subject payload excludes identities, label, actor, and timestamps. | semantic duplicate test. |
| PASS | AC-014-008 | Canonically sorted adjustment multiset retains repeated entries and is order-independent. | `test_semantic_identity_is_order_independent`; multiplicity execution test. |
| PASS | AC-014-009 | Database uniqueness and service conflict enforce `scenario_subject_semantically_duplicate`. | duplicate rejection test. |
| PASS | AC-014-010 | Partial unique database index plus idempotent service resolution enforce one server baseline. | baseline idempotency and migration tests. |
| PASS | AC-014-011 | Baseline endpoint accepts no caller evidence; adjusted requests reject empty lists and extras. | validation test. |
| PASS | AC-014-012 | Adjusted requests require at least one adjustment; subject membership is sealed atomically and all evidence tables are append-only. | validation/append-only tests; `test_pkg014_seal_rejects_raw_adjustment_injection`. |
| PASS | AC-014-013 | Pydantic, database checks, and service direction mapping use exactly two adjustment types. | validation and migration tests. |
| PASS | AC-014-014 | Adjustment rows bind generated identity, subject/client, canonical fields, provenance, actor, timestamp, and semantic fingerprint. | focused API test. |
| PASS | AC-014-015 | String-only canonical Decimal validation enforces `0.01..999999999999999999.99`. | invalid amount parameter test. |
| PASS | AC-014-016 | Strict ordered inclusive months and execution containment are enforced before persistence. | out-of-horizon non-persistence test. |
| PASS | AC-014-017 | Components exist only for months inside each adjustment range. | partial-range arithmetic test. |
| PASS | AC-014-018 | Scenario components are added alongside untouched factual inventory. | additive arithmetic and PKG-013 regression tests. |
| PASS | AC-014-019 | Separate equal rows remain separate occurrences; duplicate row identity and ordinal are constrained. | multiplicity test and migration constraints. |
| PASS | AC-014-020 | Factual material fingerprint binds the factual material constituent, horizon, component-domain contract, engine and result schema while excluding subject/adjustment/evidence metadata. | `test_factual_material_fingerprint_binds_dimensions_and_excludes_scenario_metadata`; parallel baseline/adjusted test; accepted PKG-013 constituent tests. |
| PASS | AC-014-021 | Run stores factual inventory and adjustment manifest in distinct fields and snapshot domains. | run response assertions. |
| PASS | AC-014-022 | Arithmetic is limited to monthly inflow/outflow addition, net, and range totals. | exact arithmetic test. |
| PASS | AC-014-023 | Runs are chained and selected by client plus subject under `m09-subject-currentness-v1`. | parallel currentness test. |
| PASS | AC-014-024 | Rerunning A stales only A; B remains current; an upstream factual change independently stales the affected old run. | `test_parallel_currentness_and_replay_semantics`; `test_upstream_factual_change_stales_run_and_eligibility`. |
| PASS | AC-014-025 | Legacy `m09-currentness-v1` behavior remains on legacy routes. | full PKG-013 suite. |
| PASS | AC-014-026 | Eligibility v2 derives fail-closed from sealed manifest parity, subject, inventory, snapshot, results, dependencies, and currentness and exposes factual material identity. | manifest-child, monthly-result, range-total, manifest-JSON and upstream-change tamper tests. |
| PASS | AC-014-027 | Eligibility response and UI state technical scope only and preserve v1 separately. | API schema and UI text tests. |
| PASS | AC-014-028 | Per-run evidence exposes the exact fields needed by a future separately authorized pair admission. | run response tests; no pair endpoint exists. |
| PASS | AC-014-029 | No M10 pair selection, comparison, persistence, or route was added. | route/file diff audit. |
| PASS | AC-014-030 | Separate subject, manifest, inventory, factual-material, snapshot, semantic-result, and integrity fingerprints persist and are read-time verified. | `test_result_tampering_is_non_authoritative`; `test_manifest_json_tampering_is_detected`; focused run tests. |
| PASS | AC-014-031 | Semantic result evidence canonicalizes adjustment occurrences without run or adjustment IDs. | replay semantic-fingerprint test. |
| PASS | AC-014-032 | Five additive client-owned append-only tables, including the immutable subject seal, preserve historical evidence. | correction migration upgrade/downgrade and raw-SQL trigger tests. |
| PASS | AC-014-033 | Database constraints/triggers cover baseline, semantic uniqueness, client FKs, predecessor, sequence, and mutation. | `test_pkg014_migration.py`. |
| PASS | AC-014-034 | Every public and direct-service lookup includes client and subject scope; foreign resources are equivalent to nonexistent resources. | `test_client_isolation_matrix_matches_nonexistent_resources`. |
| PASS | AC-014-035 | Extra fields and caller-owned identities/evidence are absent or forbidden in calculation requests. | request validation test. |
| PASS | AC-014-036 | UI renders factual baseline read-only and separately renders every declared occurrence, including baseline no-adjustment evidence and visible multiplicity. | `renders factual evidence separately from each declared occurrence without edit authority`; baseline UI test. |
| PASS | AC-014-037 | Client generation plus monotonic subject generation, subject identity, channel epoch and loading ownership protect the seven actual channels: `subject-list`, `baseline-resolution`, `subject-creation`, `subject-detail` (initial detail and history), `subject-execution`, independently refreshed `run-history`, and composite `run-result` (result/currentness/eligibility). | Exact controlled-promise evidence is mapped in **AC-014-037 Async Isolation Evidence** below. Only `M09ScenarioSubjects.test.tsx` is counted as subject-workflow proof. |
| PASS | AC-014-038 | Planner provenance is emitted only as informational warning; dependency blockers remain blockers. | focused response assertions and PKG-013 tests. |
| PASS | AC-014-039 | Validation fails before persistence; dependency/calculation failures persist no partial result; sealed-manifest and result tampering cannot be returned as authoritative success. | out-of-horizon non-persistence, manifest-drift and result-tamper tests. |
| PASS | AC-014-040 | Scope verification covers only implementation, tests, additive migration, UI, and this evidence matrix. | final Git diff audit. |

## AC-014-037 Async Isolation Evidence

All tests below are in `frontend/src/pages/M09ScenarioSubjects.test.tsx`. Each stale settlement is released explicitly through a controlled promise. The assertions cover only state owned by the affected channel: subject list or selection, baseline/detail, run history, current run/result/currentness/eligibility, error visibility, and the current loading owner. Equal subject ID after A→B→A is not sufficient ownership because the route/client token and monotonic subject generation must also match.

| Actual channel | A→B evidence | A→B→A evidence | Settlement and ownership evidence |
|---|---|---|---|
| `subject-list` | `ignores stale candidate success after client switch`; `suppresses stale subject-list plain rejection and preserves the newer client loading owner`; structured-rejection parameter of the same test | `keeps an old subject-list A result out of a new A client generation` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale list/error cannot replace B or new-A subjects or clear the newer spinner. |
| `baseline-resolution` | `suppresses stale baseline success after A-to-B and preserves the newer client loading owner`; `suppresses stale baseline-resolution plain rejection and preserves the newer client loading owner`; structured-rejection parameter of the same test | `keeps an old baseline success out of a new A client generation` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale baseline cannot become selected or clear the newer client loading owner. |
| `subject-creation` | `keeps stale create response from selecting a subject after client change`; `suppresses stale subject-creation plain rejection and preserves the newer client loading owner`; structured-rejection parameter of the same test | `keeps an old create success from appending or selecting into a new A client generation` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale create cannot select/append a subject, surface an error, or clear current loading. |
| `subject-detail` (detail plus initial history) | `invalidates subject A detail success and finally immediately on A-to-B`; `suppresses stale subject-detail plain rejection and preserves the newer subject loading owner`; structured-rejection parameter of the same test | `distinguishes old A rejection from new A after A-to-B-to-A`; `keeps an old subject-detail success out of a new A subject generation` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale detail/history cannot replace current selection/history or current loading/error state. |
| `subject-execution` | `does not let stale subject execution write result or clear new-subject loading`; `suppresses stale subject-execution plain rejection and preserves the newer subject loading owner`; structured-rejection parameter of the same test | `keeps an old execution success from overwriting a new A result after A-to-B-to-A` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale execution cannot write run/result/currentness/eligibility, trigger authoritative history for the current context, or clear newer loading. |
| `run-history` (independent post-execution refresh) | `keeps independently refreshed stale run history out of the next subject and preserves its loading`; `suppresses independently refreshed stale run-history plain rejection and preserves newer loading`; structured-rejection parameter of the same test | `keeps independently refreshed old A history out of a new A subject generation` | Fulfilled, plain rejected, structured rejected, and stale `finally`; stale history cannot enter B/new-A history, surface an error, or clear newer loading. |
| `run-result` (composite result/currentness/eligibility) | `keeps a stale run-result success out of the next subject and preserves its loading`; `suppresses stale run-result plain rejection and preserves the newer subject loading owner`; structured-rejection parameter of the same test | `guards stale run composite rejection across subject A-to-B-to-A`; `keeps an old run-result composite out of a new A subject generation` | Composite fulfilled, plain rejected, structured rejected, and stale `finally`; stale result/currentness/eligibility cannot become current merely because the selected subject ID returns to A, and cannot alter error/loading ownership. |

`M09ScenarioSubjects` owns no independent inventory/validation request channel. Inventory is part of the returned run evidence. The legacy `M09CashflowScreen.test.tsx` suite remains separate regression evidence and is not counted as proof of callback or state ownership inside the PKG-014 subject workflow.

## Negative Acceptance Criteria

| Status | Criterion | Exclusion evidence |
|---|---|
| PASS | NAC-014-001 | No accepted legacy model/service/migration semantics were edited. |
| PASS | NAC-014-002 | Baseline has a dedicated server endpoint; empty adjusted subjects are rejected. |
| PASS | NAC-014-003 | Database partial unique baseline index. |
| PASS | NAC-014-004 | Semantic identity excludes label, actor, time, and generated IDs. |
| PASS | NAC-014-005 | Nonempty request validator. |
| PASS | NAC-014-006 | Literal type vocabulary and database check. |
| PASS | NAC-014-007 | Positive amount validator and database check. |
| PASS | NAC-014-008 | Canonical string regex rejects float/scientific/rounded input. |
| PASS | NAC-014-009 | Numeric bounds enforced before storage and at database level. |
| PASS | NAC-014-010 | Strict month schema, ordered ranges, and horizon containment. |
| PASS | NAC-014-011 | No factual mutation path exists. |
| PASS | NAC-014-012 | Factual inventory is rebuilt only by the accepted server resolver. |
| PASS | NAC-014-013 | Incomplete factual inventory produces dependency failure, not repair. |
| PASS | NAC-014-014 | No factual/adjustment economic deduplication code exists. |
| PASS | NAC-014-015 | Equal adjustment occurrences remain distinct; database identities are unique. |
| PASS | NAC-014-016 | Separate persisted factual and adjustment envelopes. |
| PASS | NAC-014-017 | Currentness query is subject-scoped. |
| PASS | NAC-014-018 | ORM listeners and database triggers reject UPDATE/DELETE, while the correction trigger rejects adjustment INSERT after subject sealing. |
| PASS | NAC-014-019 | No backfill or retrofit of legacy runs. |
| PASS | NAC-014-020 | Separate v1 and v2 route/response contracts. |
| PASS | NAC-014-021 | Request schemas expose none of the server-owned evidence fields. |
| PASS | NAC-014-022 | Composite same-client foreign keys plus public-route and direct-service foreign-vs-nonexistent equivalence matrix. |
| PASS | NAC-014-023 | No waive, partial, or run-anyway input exists. |
| PASS | NAC-014-024 | No M10 comparison endpoint, model, service, or UI. |
| PASS | NAC-014-025 | UI and service provide no percentage, ranking, score, recommendation, or forecast. |
| PASS | NAC-014-026 | No tax, fixation, indexation, investment, NPV, allocation, withdrawal, or conservation formula. |
| PASS | NAC-014-027 | No retirement-date, cessation, pension-start, or allocation formula. |
| PASS | NAC-014-028 | No V1 constants or implicit horizon were introduced. |
| PASS | NAC-014-029 | No M08E, reports, M11-M14, or production-readiness work. |
| PASS | NAC-014-030 | Both PKG-014 migrations are additive and linear; the correction migration adds only manifest-seal enforcement above `d5f9b2a7c406`. |
| PASS | NAC-014-031 | Informational provenance cannot clear blockers or mandatory warnings. |
| PASS | NAC-014-032 | No M10 or next-package authorization is claimed. |
| PASS | NAC-014-033 | No pair admission exists; per-run eligibility cannot assert cross-run factual equality. |

## Verification Commands

- Backend focused: `pytest -q tests/test_pkg014_m09_scenario_subjects.py tests/test_pkg014_migration.py`
- PKG-013 regression: `pytest -q tests/test_pkg013_m09_cashflow.py tests/test_pkg013_migration.py`
- Full backend: `pytest -q`
- Frontend focused: `npm test -- --run src/pages/M09ScenarioSubjects.test.tsx src/pages/M09CashflowScreen.test.tsx`
- Full frontend: `npm test -- --run`
- Frontend build: `npm run build`
- Python compile: `python -m compileall -q app tests alembic`
- Whitespace: `git diff --check`

Final acceptance remains subject to independent Acceptance Audit.

