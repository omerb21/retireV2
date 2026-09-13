# PKG-003 implementation verification evidence

Candidate implementation evidence only; not a WORK acceptance manifest and not a new semantic definition.

## Authority and boundary

- Package: FIRST_RECOVERY_PKG_003_CANONICAL_PENSION_AND_FINANCIAL_SOURCE_SNAPSHOT.
- Branch: codex/first-recovery-pkg-003-canonical-source-snapshot.
- Base / unchanged master: `486d47b18ce82af0d68b6c535adf0c458047f78c`.
- Base tree: `69e6f4426d5485b4b1430c87f378d2fb3e98cae5`.
- Accepted WORK definition supplied as `Pasted%20markdown%2820260913-111456%29.md`; SHA256 `5F990C8BF5FD916B0C52A66553E7DD6E575470E1DDEDE632D35535DB4F9D21BD`.
- Its final normalized token is `ACCEPT_FIRST_RECOVERY_PKG_003_CANONICAL_PENSION_AND_FINANCIAL_SOURCE_SNAPSHOT_DEFINITION`.
- Separate user implementation authorization and continuation instructions apply. No push or merge authorized.
- No new owner decisions, semantic deviations, or resolution/escalation of unrelated drift items.

## Implementation evidence pointers

- Manual source model/schema/service and public manual routes: stable server identity, exact entered money or balance/factor facts, expected-version writes under existing per-client lock, supersede without hard delete. Nullable source facts are not guessed.
- Snapshot service: one derived response, independent of old workflow readers. Product components, pension sources and capital sources stay separate. Monetary strings and ratios are not rounded into a second authority. Reported controls have a separate explicit control-only designation.
- GET starts a fresh read transaction. PostgreSQL uses REPEATABLE READ READ ONLY; SQLite uses explicit BEGIN (including a WAL concurrent-writer test). No client write lock, autoflush, version/timestamp touch, or persisted snapshot.
- Tests pause a reader after its first SELECT, commit each of product/conversion/manual-pension/manual-capital writes, then resume the reader. It returns the complete old snapshot; a subsequent read returns the new fingerprint. PostgreSQL and SQLite cases pass.
- Corrupted ownership/ratio/link data fails explicitly. Synthetic display-only discrepancies are injected at the read boundary without disabling PKG-002 history guards.
- UI uses one server snapshot for professional sources, Hebrew names and accessible labels, RTL, DD/MM/YYYY, exact amount strings, provenance, missing facts, manual editing/superseding, and keyed/aborted client reloads.
- M09 public routes retain only persisted archive GETs, explicitly labelled archive-only. M10 comparison has no registered execution route. Old execution UI files, routes and navigation are removed.
- The unchanged historical engines remain covered by 120 tests using `backend/tests/legacy_m09_m10_test_app.py`, a private test-only FastAPI harness. It copies adapters from the accepted base solely for schema/engine/persistence regression. It is not imported by production. Independent tests use the real `app.main` to prove execution is unreachable and archive GET never calls currentness/calculation services.
- No changes to M09/M10 engine files, PKG-002 conversion/reversal rules, existing monetary contracts, or historical migration files.

## Migration evidence

- Exactly one new revision: `a6b2d9e5f743`, down_revision `f5a1c8d4e632`.
- Only new table: `canonical_manual_pension_sources`, with client FK/index, input mode, source identity/facts, ExactMoney monthly_amount/balance, exact decimal text factor/rate, date/tax/indexation facts, current/superseded state, version and timestamps.
- DB constraints: input/lifecycle domains, positive version/factor, nonnegative money, mutually exclusive authority fields, client FK.
- PostgreSQL money uses the project NUMERIC(20,2); SQLite uses the project lossless money text representation. Factor/rate use bounded exact decimal strings, not floats or rounded results.
- Real PostgreSQL upgrade preserves existing RecurringIncome values and does not copy rows. Empty-table downgrade/re-upgrade works; populated-table downgrade fails before destroying history. SQLite additive upgrade/downgrade also passes.
- Final single Alembic head: `a6b2d9e5f743`.
- Isolated portable PostgreSQL 16.15 only, ephemeral loopback clusters created and stopped by the test fixture. No normal user database or system installation was used.

## Verification results

- Focused snapshot/manual/SQLite/concurrency + real-app reachability + governance: **53 passed** (37 source tests, 2 real-app reachability tests, 14 governance).
- Historical M09/M10 regression harness: **120 passed**.
- PostgreSQL PKG-003 final integration: **6 passed**, including real API GET and manual API transaction/lifecycle/version behavior.
- Combined PostgreSQL/migration regression run: **11 passed** (PKG-003 plus PKG-002 precision/reversal and PKG-001 cutover/batch migrations; one SQLite migration test included). PKG-003 API additions were subsequently reverified in the six-test final run.
- Existing PKG-002 PostgreSQL conversion concurrency regression: **1 passed** separately. All eleven PostgreSQL cases skipped by the non-opt-in full run were executed successfully in the isolated PostgreSQL runs.
- Full frontend: **175 passed**, 28 files.
- Final focused frontend: **21 passed** (snapshot UI, consolidated view, client navigation and route sealing).
- TypeScript `npx tsc --noEmit`: PASS.
- Production `npm run build`: PASS (66 modules).
- Full backend final result: **1082 passed, 13 skipped, 7 warnings** in 791.15 seconds.
- Alembic heads: `a6b2d9e5f743 (head)`.
- Whitespace check: PASS.

Reproduction commands (backend working directory unless specified):

```text
python -m pytest -q tests/test_professional_source_snapshot.py tests/test_professional_source_reachability.py tests/test_governance_baseline.py --tb=short
python -m pytest -q tests/test_pkg013_m09_cashflow.py tests/test_pkg014_m09_scenario_subjects.py tests/test_pkg015_m10_comparison.py --tb=short
RECOVERY_POSTGRES_TEST=1 RECOVERY_POSTGRES_BIN=<isolated trusted PostgreSQL 16 bin directory>
python -m pytest -q tests/test_professional_source_postgresql.py --tb=short
python -m pytest -q tests/test_professional_source_postgresql.py tests/test_canonical_conversion_migration.py tests/test_recovery_migration_postgresql.py tests/test_recovery_batch_migration.py --tb=short
python -m pytest -q tests/test_canonical_conversion_concurrency.py --tb=short
python -m pytest -q --tb=short -rs
python -m alembic heads
frontend: npm test -- --reporter=dot
frontend: npx tsc --noEmit
frontend: npm run build
git diff --check
```

Intermediate failures were verification-scope mismatches (removed public execution UI, old table/head inventories) or new fixture defects (required general-income fields, SQLite FK rejection exception type). No professional behavior was weakened. The initial full run against obsolete expectations was stopped; the next completed run had 1081 passes and one already-fixed FK exception expectation. The final full run passed all 1082 enabled tests.

Warnings: existing React Router v7 future notices and expected no-route messages for removed paths; seven Pydantic Decimal/float serializer warnings in existing malformed-caller-CBS-evidence tests.
Full-suite skips: eleven PostgreSQL opt-in cases (run separately with isolated PostgreSQL) and two existing symbolic-link tests in test_pkg007_m02_intake.py, unavailable on this host.

## Exact scope inventory

Status A/M/D denotes added/modified/deleted relative to the accepted base.
This evidence document itself is required audit documentation (A).

| Status | File | Classification |
|---|---|---|
| M | `backend/app/api/clients_routes.py` | Required production: canonical snapshot, manual source or narrow integration |
| M | `backend/app/api/m09_cashflow_routes.py` | Required legacy execution sealing / persisted archive read |
| M | `backend/app/api/m10_comparison_routes.py` | Required legacy execution sealing / persisted archive read |
| M | `backend/app/db/base.py` | Required production: canonical snapshot, manual source or narrow integration |
| M | `backend/app/main.py` | Required production: canonical snapshot, manual source or narrow integration |
| M | `backend/tests/test_governance_baseline.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_phase6_schema.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_phase7_persistence.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_phase9_api.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_pkg011_migration.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_pkg013_m09_cashflow.py` | Required archive regression adaptation (test-only) |
| M | `backend/tests/test_pkg013_migration.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_pkg014_m09_scenario_subjects.py` | Required archive regression adaptation (test-only) |
| M | `backend/tests/test_pkg014_migration.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_pkg015_m10_comparison.py` | Required archive regression adaptation (test-only) |
| M | `backend/tests/test_recovery_batch_migration.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_recovery_migration.py` | Required backend test / explicit governance or schema inventory |
| M | `backend/tests/test_recovery_migration_postgresql.py` | Required backend test / explicit governance or schema inventory |
| D | `frontend/src/api/m09CashflowApi.ts` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/api/m10ComparisonApi.test.ts` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/api/m10ComparisonApi.ts` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| M | `frontend/src/pages/ClientDetailScreen.test.tsx` | Required frontend test |
| M | `frontend/src/pages/ClientDetailScreen.tsx` | Required production: canonical snapshot, manual source or narrow integration |
| D | `frontend/src/pages/M09CashflowScreen.test.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/pages/M09CashflowScreen.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/pages/M09ScenarioSubjects.test.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/pages/M09ScenarioSubjects.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/pages/M10ComparisonScreen.test.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| D | `frontend/src/pages/M10ComparisonScreen.tsx` | REPLACED_MEANS_REMOVED: obsolete execution UI/API or its availability tests |
| M | `frontend/src/pages/RetirementPlanningConsolidatedReviewSection.test.tsx` | Required frontend test |
| M | `frontend/src/pages/RetirementPlanningConsolidatedReviewSection.tsx` | Required production: canonical snapshot, manual source or narrow integration |
| M | `frontend/src/routes/AppRoutes.test.tsx` | Required frontend test |
| M | `frontend/src/routes/AppRoutes.tsx` | Required production: canonical snapshot, manual source or narrow integration |
| A | `backend/alembic/versions/a6b2d9e5f743_canonical_manual_pension_sources.py` | Required additive migration |
| A | `backend/app/api/professional_source_routes.py` | Required production: canonical snapshot, manual source or narrow integration |
| A | `backend/app/models/canonical_manual_pension_source.py` | Required schema/model |
| A | `backend/app/schemas/canonical_manual_pension_source.py` | Required schema/model |
| A | `backend/app/services/canonical_manual_pension_service.py` | Required production: canonical snapshot, manual source or narrow integration |
| A | `backend/app/services/professional_source_snapshot_service.py` | Required production: canonical snapshot, manual source or narrow integration |
| A | `backend/tests/legacy_m09_m10_test_app.py` | Required archive regression adaptation (test-only) |
| A | `backend/tests/test_professional_source_postgresql.py` | Required backend test / explicit governance or schema inventory |
| A | `backend/tests/test_professional_source_reachability.py` | Required backend test / explicit governance or schema inventory |
| A | `backend/tests/test_professional_source_snapshot.py` | Required backend test / explicit governance or schema inventory |
| A | `frontend/src/api/professionalSourceApi.ts` | Required production: canonical snapshot, manual source or narrow integration |
| A | `frontend/src/components/ProfessionalSourceSnapshot.test.tsx` | Required frontend test |
| A | `frontend/src/components/ProfessionalSourceSnapshot.tsx` | Required production: canonical snapshot, manual source or narrow integration |
| A | `frontend/src/pages/ProfessionalSourceSnapshotScreen.tsx` | Required production: canonical snapshot, manual source or narrow integration |
| A | `specs/runtime/FIRST_RECOVERY_PKG_003_implementation_evidence.md` | Required implementation verification report; no semantic authority |

## Protected paths and governance

CURRENT_PROJECT_STATE.md is the pre-existing protected untracked file, SHA256
`B82F26B1C90E41F8E05DBC99C266A8DF71B6E0D0C17A6A230E852D77A54BAFDD`.
_evidence/, specs/bootstraps/, start_retire_v2_fixed.bat remain absent.
None is staged, modified, deleted, or overwritten.

02M FROZEN; M08E EXCLUDED; M11-M14 NOT_AUTHORIZED; next/downstream package NOT_AUTHORIZED;
production readiness NOT_CLAIMED; FIRST_STAGE_INTEGRATED_SYSTEM_AND_UI_VALIDATION ACTIVE.
M02-M05 remain removed; PensionHolding and M06 remain archive-only.
No WORK implementation acceptance, master integration, or production-readiness claim is made here.
