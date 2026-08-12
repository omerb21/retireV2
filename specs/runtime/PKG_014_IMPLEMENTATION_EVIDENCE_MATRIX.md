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
| PASS | AC-014-008 | Canonically sorted adjustment multiset retains repeated entries. | multiplicity execution test. |
| PASS | AC-014-009 | Database uniqueness and service conflict enforce `scenario_subject_semantically_duplicate`. | duplicate rejection test. |
| PASS | AC-014-010 | Partial unique database index plus idempotent service resolution enforce one server baseline. | baseline idempotency and migration tests. |
| PASS | AC-014-011 | Baseline endpoint accepts no caller evidence; adjusted requests reject empty lists and extras. | validation test. |
| PASS | AC-014-012 | Adjusted requests require at least one adjustment; all subject tables are append-only. | validation and append-only tests. |
| PASS | AC-014-013 | Pydantic, database checks, and service direction mapping use exactly two adjustment types. | validation and migration tests. |
| PASS | AC-014-014 | Adjustment rows bind generated identity, subject/client, canonical fields, provenance, actor, timestamp, and semantic fingerprint. | focused API test. |
| PASS | AC-014-015 | String-only canonical Decimal validation enforces `0.01..999999999999999999.99`. | invalid amount parameter test. |
| PASS | AC-014-016 | Strict ordered inclusive months and execution containment are enforced before persistence. | out-of-horizon non-persistence test. |
| PASS | AC-014-017 | Components exist only for months inside each adjustment range. | partial-range arithmetic test. |
| PASS | AC-014-018 | Scenario components are added alongside untouched factual inventory. | additive arithmetic and PKG-013 regression tests. |
| PASS | AC-014-019 | Separate equal rows remain separate occurrences; duplicate row identity and ordinal are constrained. | multiplicity test and migration constraints. |
| PASS | AC-014-020 | Factual material fingerprint derives only from accepted factual inventory material and versions. | parallel currentness test. |
| PASS | AC-014-021 | Run stores factual inventory and adjustment manifest in distinct fields and snapshot domains. | run response assertions. |
| PASS | AC-014-022 | Arithmetic is limited to monthly inflow/outflow addition, net, and range totals. | exact arithmetic test. |
| PASS | AC-014-023 | Runs are chained and selected by client plus subject under `m09-subject-currentness-v1`. | parallel currentness test. |
| PASS | AC-014-024 | Rerunning A stales only A; B remains current. | parallel currentness test. |
| PASS | AC-014-025 | Legacy `m09-currentness-v1` behavior remains on legacy routes. | full PKG-013 suite. |
| PASS | AC-014-026 | Eligibility v2 derives fail-closed from subject, snapshot, results, dependencies, and currentness and exposes factual material identity. | focused execution/currentness tests. |
| PASS | AC-014-027 | Eligibility response and UI state technical scope only and preserve v1 separately. | API schema and UI text tests. |
| PASS | AC-014-028 | Per-run evidence exposes the exact fields needed by a future separately authorized pair admission. | run response tests; no pair endpoint exists. |
| PASS | AC-014-029 | No M10 pair selection, comparison, persistence, or route was added. | route/file diff audit. |
| PASS | AC-014-030 | Separate subject, manifest, inventory, factual-material, snapshot, semantic-result, and integrity fingerprints persist. | focused run test. |
| PASS | AC-014-031 | Semantic result evidence canonicalizes adjustment occurrences without run or adjustment IDs. | replay semantic-fingerprint test. |
| PASS | AC-014-032 | Four additive client-owned append-only tables preserve historical evidence. | migration and ORM tests. |
| PASS | AC-014-033 | Database constraints/triggers cover baseline, semantic uniqueness, client FKs, predecessor, sequence, and mutation. | `test_pkg014_migration.py`. |
| PASS | AC-014-034 | Every lookup includes client and subject scope; foreign resources return the same 404 contract. | client isolation test. |
| PASS | AC-014-035 | Extra fields and caller-owned identities/evidence are absent or forbidden in calculation requests. | request validation test. |
| PASS | AC-014-036 | UI supports baseline, adjusted subjects, multiplicity, histories and technical evidence without factual selection controls. | frontend focused tests and build. |
| PASS | AC-014-037 | Generation/epoch/loading ownership protects subject list, baseline, creation, detail/history, execution, result/currentness/eligibility; accepted legacy inventory isolation remains covered. | controlled-promise frontend suites. |
| PASS | AC-014-038 | Planner provenance is emitted only as informational warning; dependency blockers remain blockers. | focused response assertions and PKG-013 tests. |
| PASS | AC-014-039 | Validation fails before persistence; dependency/calculation failures persist no partial monthly result. | focused failure tests. |
| PASS | AC-014-040 | Scope verification covers only implementation, tests, additive migration, UI, and this evidence matrix. | final Git diff audit. |

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
| PASS | NAC-014-018 | ORM listeners and database triggers reject UPDATE/DELETE. |
| PASS | NAC-014-019 | No backfill or retrofit of legacy runs. |
| PASS | NAC-014-020 | Separate v1 and v2 route/response contracts. |
| PASS | NAC-014-021 | Request schemas expose none of the server-owned evidence fields. |
| PASS | NAC-014-022 | Composite same-client foreign keys and scoped 404 lookups. |
| PASS | NAC-014-023 | No waive, partial, or run-anyway input exists. |
| PASS | NAC-014-024 | No M10 comparison endpoint, model, service, or UI. |
| PASS | NAC-014-025 | UI and service provide no percentage, ranking, score, recommendation, or forecast. |
| PASS | NAC-014-026 | No tax, fixation, indexation, investment, NPV, allocation, withdrawal, or conservation formula. |
| PASS | NAC-014-027 | No retirement-date, cessation, pension-start, or allocation formula. |
| PASS | NAC-014-028 | No V1 constants or implicit horizon were introduced. |
| PASS | NAC-014-029 | No M08E, reports, M11-M14, or production-readiness work. |
| PASS | NAC-014-030 | Implementation migration is solely the explicitly authorized additive PKG-014 migration. |
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

