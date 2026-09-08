# FIRST_RECOVERY_PKG_001 implementation evidence

This document supersedes the earlier incomplete progress checkpoints. It is
implementation evidence, NOT an acceptance record and NOT a changed definition.

Code and migration verification completed; independent WORK audit not performed.
The final handoff records the committed review HEAD/tree and push verification.

## Immutable authority and linear history

- Implementation branch: `codex/first-recovery-pkg-001-implementation`.
- Definition/start: `09cd67417614cbdc4e422321db9324f7f9883ac0`.
- Definition blob: `adf2a7e1b06f2f8660f82b2c735e51515395d713`.
- Definition parent and unchanged master: `7b5f3739caa67a8422c5fff67ab7386b2f300741`.
- Preserved intermediate implementation commit:
  `65f07c8636cf9808734ce70e3aa092c81348c9ac`
  (Add canonical pension source foundation and isolated parity tests).
- Cutover is an append-only implementation commit after that intermediate commit.
  No reset, rebase, squash, amend, force push or merge is part of this work.
- The immutable definition file is not included in the implementation diff.
- PensionHolding disposition follows the explicit subsequent user authorization:
  `RETAIN_BACKEND_ONLY_ARCHIVE_FOR_HISTORICAL_FK_INTEGRITY`.

## Canonical authority and parity coverage

The registered current path is exclusively:
pension-products screen -> canonical API -> canonical service -> canonical tables.
PARITY-0002 through PARITY-0010 are implemented. PARITY-0011/0012/0014/0015
are source-contract dependencies only; no conversion behavior was implemented.

Created tables / models:

| Table | Model | Role |
| --- | --- | --- |
| pension_products | PensionProduct | One current product, professional metadata, three separate reported totals, optimistic version |
| pension_product_components | PensionProductComponent | Exactly 11 fixed Hebrew component identities; unique product/code |
| pension_product_source_links | PensionProductSourceLink | Immutable raw import/history/checksum/diagnostics and optional archived-source FK |
| pension_product_audit_events | PensionProductAuditEvent | Immutable create/import/update/delete/migration evidence |

All 11 component rows exist, including zero amounts. Generic contribution_component
and generic rewards totals are never component identities. Reported product,
rewards and severance totals remain separate from the 11/6/5 component sums.
Discrepancies are differences only, not balances, review gates or allocations.

PostgreSQL stores NUMERIC(20,2). SQLite uses lossless two-decimal text because
SQLite NUMERIC affinity would otherwise convert nonintegral values into binary
floating point. Decimal validation rejects floats, excess precision and overflow;
the maximum-precision round-trip is tested.

Manual creation initializes all 11 components to zero. Explicit saves cover
metadata/components/totals atomically. Per-client serialization uses PostgreSQL
advisory locking plus row locking, or the SQLite transactional write boundary;
optimistic versions reject stale writes. Selected saves preflight the complete
batch. Direct delete preserves source/audit evidence and fails closed on
downstream FK restrictions.

Import uses only the exact accepted employee/employer, period and severance
mappings. Unknown values remain diagnostics; layer totals are not product totals.
Raw bytes and checksum are preserved. Deterministic provider/account or explicit
source identity drives checksum/account replay idempotency; a newer statement
updates atomically without discarding source history. No heuristic distribution,
review ceremony or generic component was introduced.

The Hebrew RTL screen supports import, manual create, metadata, all 11 balances,
separate reported totals/sums/discrepancies, explicit save and confirmed delete.
Existing Hebrew date helpers provide DD/MM/YYYY and Israeli history timestamps.
No conversion controls exist on this screen.

## Migration and cutover

Revision `d3e9a6b2c410`, direct parent `c2d8f5a1b309`; exactly one head.

The migration is self-contained: no imports of mutable application services.
It performs online preflight before canonical DDL, locks legacy authority during
cutover, rejects ambiguous active M02 identity or competing M05 leaves/amounts,
maps only exact recognized identities, and reports deterministic counts.
It creates one product and eleven components per unambiguous source identity;
unknown evidence remains a provenance snapshot. Reported summary fields are
never decomposed or distributed. Opaque uploads remain preserved, not guessed
into products.

Existing M02 raw blobs/source records, M03/M04/M05 history and FKs are not deleted.
PensionHolding is NOT automatically converted into canonical balances or component
rows. Existing analysis-record FKs are NOT rewritten. Immutable archive triggers
block legacy professional INSERT/UPDATE/DELETE after cutover. Canonical source
and audit history have UPDATE/DELETE guards.

Actual temporary SQLite upgrades from the previous head with data passed,
including archive/FK preservation and ambiguity rollback before schema/version
movement. An unsafe downgrade is explicitly prohibited; operational rollback
requires a verified pre-cutover backup, not reactivation of old authority.
PostgreSQL schema DDL compilation passed (four tables, four NUMERIC(20,2) columns,
component uniqueness, no float/text monetary substitution).
A live PostgreSQL server was not available in this environment; no actual
PostgreSQL upgrade is claimed. The user's local database was not used or changed.

## REPLACED_MEANS_REMOVED and caller inventory

V2-REM-0001 through V2-REM-0009 and source-side V2-REM-0018/V2-REM-0020
are covered. PPR-001/002/010/011 have no surviving current parallel authority.
PPR-003 is closed at the source boundary only: conversion is unavailable.

| Caller / former authority | Final disposition |
| --- | --- |
| main.py router registration | Canonical router registered; M02/M03/M04/M05 routers removed |
| AppRoutes / client navigation | Direct pension-products route; four old professional routes removed |
| M01 client/profile work | Professional transition endpoint, allowed-target response field, edit/progression gate and UI controls removed |
| Existing M09 record safety | Administrative archived-client write protection isolated in client_record_safety; not a professional progression gate |
| M02 upload/intake | Professional API/UI/services/schemas removed; only backend raw storage/download primitives and historical persistence retained |
| M03 review/annotation | Action API/service/schema/UI/client and obsolete workflow tests deleted |
| M04 classification/proposal/revalidation | Action API/service/catalogue/schema/UI/client and obsolete workflow tests deleted |
| M05 ledger authority | Action API/service/schema/UI/client and obsolete workflow tests deleted |
| Current client consolidated review | Reads canonical products; no holding balance or old ledger reader |
| Retirement facts screen / clientsApi | Holding CRUD, balance form and analysis mutation callers removed; unrelated fact groups retained |
| PensionAnalysisRecordSection | Production UI and obsolete tests deleted; no new/recomputed historical-source analysis |
| Historical analysis GET | Returns already-persisted text scoped by client/historical FK; does not query holding balances |
| M07 evidence current-source whitelist | PensionHolding removed; existing serialized evidence remains historical |
| M06 source actions | All six source-dependent entry points call canonical availability and fail closed |
| M06 UI/API client | Historical read-only subjects/details/history; mutation controls and mutation/candidate client calls removed |
| M09 downstream source eligibility | Current use closes through M06 canonical availability; existing M06 snapshot vocabulary retained, no formula changes |
| Model registry / server bootstrap | All archive FK targets and immutable listeners registered before first query |
| Other reports, exports, background/config/bootstrap callers | Repository-wide search found no additional current legacy balance reader or activatable workflow |

M06 reports `CANONICAL_CONVERSION_CONTRACT_NOT_IMPLEMENTED`, never a fallback.
The historical calculation primitives and manifest fingerprint rules are retained,
not repurposed as a new canonical conversion engine. Historical M06 evidence
remains readable but is not eligible as current upstream authority.

The startup regression was a late import of archive models/SQL guards while an
Engine query listener was being iterated. Eager load_all_models() registration
before the first request removes that listener mutation. The migrated archive
test exercises actual application startup and requests without late manual
model registration.

## Retained archive-only persistence and symbols

| Models / tables | Justification and limits |
| --- | --- |
| PensionHolding / pension_holding | Historical FK target only; no current CRUD, professional balance reader, navigation, fallback or automatic migration |
| PensionAnalysisRecord / pension_analysis_record | Persisted historical text/FK preserved; GET-only API; new/update operations absent and DB writes blocked |
| M02IntakeRecord / m02_intake_records | Frozen original record/provenance and FK target; no professional writer/reader/gate |
| M02PreservedBlob, M02PreservedSource / m02_preserved_blobs, m02_preserved_sources | Backend-only original bytes/checksum/storage and source traceability; not current balances |
| M03ReviewRevision, M03Annotation / m03_review_revisions, m03_annotations | Frozen historical review/annotation evidence and FK integrity |
| M04ClassificationSubject, M04ClassificationRevision, M04ComponentDecision / m04_classification_subjects, m04_classification_revisions, m04_component_decisions | Frozen classification history and downstream FK targets |
| M05LedgerSubject, M05CandidateLink, M05LedgerRevision, M05LedgerValue, M05AdjustmentEvidence / corresponding five m05 tables | Frozen ledger/adjustment history and M06 FK targets; no selectable current balance |

Every retained production file with a legacy symbol is classified below.
Class/column/constraint names inside these files inherit only that retained role;
they do not authorize the original professional workflow.

| Production path | Classification of surviving references |
| --- | --- |
| backend/app/db/base.py | Archive model/FK/guard registration before first query |
| backend/app/api/clients_routes.py | GET-only historical analysis identifier/text; no PensionHolding query |
| backend/app/models/client.py | Historical ORM relationship; no current caller traverses it for balances |
| backend/app/models/retirement_facts.py | Archive PensionHolding mapping, frozen by migration triggers |
| backend/app/models/pension_analysis_record.py | Preserved historical FK/relationship; no mutation endpoint |
| backend/app/models/pension_analysis_record_contracts.py | Historical response identifier; frozen contract retained |
| backend/app/models/pension_product.py | Optional archived raw-source FK, not professional balance authority |
| backend/app/models/m02_intake.py | Frozen intake and raw-source preservation metadata/guards |
| backend/app/models/m03_review.py | Frozen historical review and annotation maps/guards |
| backend/app/models/m04_classification.py | Frozen historical classification maps/guards |
| backend/app/models/m05_ledger.py | Frozen ledger maps/guards; SQL lexical immutability primitives reused by M06 |
| backend/app/models/m06_conversion.py | Historical predecessor FKs and shared immutable SQL lexical guards |
| backend/app/schemas/m06_conversion.py | Historical response fields; old request envelopes only reach fail-closed actions |
| backend/app/services/m06_conversion_service.py | Historical fingerprint/snapshot identifiers and removed-source documentation |
| backend/app/services/m09_cashflow_service.py | Serialized historical M06 predecessor snapshot key; current eligibility fails closed |
| backend/app/services/m02_storage.py | Backend-only raw-source storage/integrity helpers |
| backend/app/services/pension_source_download.py | Backend-only historical raw-source streaming helper, no professional route |
| frontend/src/api/m06ConversionApi.ts | Read-only historical M06 response identifier |

### Reproducible repository-wide search

Command (case insensitive, no word-boundary exclusion):

```text
rg -n -i 'PensionHolding|pension_holding|pension-holdings|M02|M03|M04|M05|contribution_component' --glob '!package-lock.json' --glob '!FIRST_RECOVERY_PKG_001_implementation_progress.md'
```

The evidence document is excluded to avoid self-counting. Normal repository ignore
rules exclude generated/dependency/cache content. Result: 88 files, 2,158 matching
lines. No match exists outside the categories below.

| Category | Files | Matching lines |
| --- | ---: | ---: |
| Classified archive/runtime technical boundaries | 18 | 433 |
| Immutable migration history / new cutover | 11 | 277 |
| Tests and historical test matrix | 22 | 419 |
| Definitions and historical governance documentation | 37 | 1,029 |

The five executable reachability tests check exact retained production file
inventory, AST imports, registered routes, deleted files, absence of old UI
identifiers/callers, canonical-only source selection, no holding balance query
and no analysis mutator. SQL-capture tests exercise canonical API and all six M06
source actions and reject reads from legacy professional tables.
No background/export/bootstrap/script match outside these inventories was found.

Every non-production file match is listed below, including its matching-line
count. Historical definitions/acceptance records are documentary authority/history,
not permission to reactivate removed runtime paths.

| Path | Matching lines | Classification |
| --- | ---: | --- |
| backend/alembic/versions/95222c79dce8_pkg009_m04_classification.py | 58 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/a1c7e4d9f208_m03_m02_authority_digest.py | 4 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/a4c9e2f7b106_pkg010_m05_ledger.py | 63 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/b6d8e2f4a701_pkg007_m02_intake.py | 53 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/c2d8f5a1b309_m03_m02_evidence_snapshot.py | 4 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/d1f4a8c2e9b0_v21_package_a_retirement_facts_foundation.py | 7 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/d3e9a6b2c410_canonical_pension_source.py | 8 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/d7e3a6b9c204_pkg011_m06_conversion.py | 17 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/e4a7c3d9b802_pkg008_m03_review.py | 28 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/e8f4b7c2d305_pkg011_predecessor_ownership.py | 32 | Immutable historical migration / canonical cutover |
| backend/alembic/versions/f4c8b1a9d2e3_add_pension_analysis_records.py | 3 | Immutable historical migration / canonical cutover |
| backend/tests/PKG009_REQUIREMENTS_TEST_MATRIX.md | 6 | Historical/negative/parity test or test documentation |
| backend/tests/test_governance_baseline.py | 105 | Historical/negative/parity test or test documentation |
| backend/tests/test_migration_safety.py | 32 | Historical/negative/parity test or test documentation |
| backend/tests/test_phase6_schema.py | 14 | Historical/negative/parity test or test documentation |
| backend/tests/test_phase7_persistence.py | 14 | Historical/negative/parity test or test documentation |
| backend/tests/test_phase9_api.py | 14 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg007_m02_intake.py | 82 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg009_migration.py | 16 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg010_migration.py | 13 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg011_m06_conversion.py | 7 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg011_migration.py | 59 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg013_architecture.py | 1 | Historical/negative/parity test or test documentation |
| backend/tests/test_pkg013_m09_cashflow.py | 2 | Historical/negative/parity test or test documentation |
| backend/tests/test_recovery_cutover_preflight.py | 1 | Historical/negative/parity test or test documentation |
| backend/tests/test_recovery_holding_archive.py | 10 | Historical/negative/parity test or test documentation |
| backend/tests/test_recovery_migration.py | 3 | Historical/negative/parity test or test documentation |
| backend/tests/test_recovery_pension_products.py | 4 | Historical/negative/parity test or test documentation |
| backend/tests/test_recovery_reachability.py | 22 | Historical/negative/parity test or test documentation |
| backend/tests/test_v21_package_a_persistence.py | 10 | Historical/negative/parity test or test documentation |
| backend/tests/test_v21_package_b_api.py | 1 | Historical/negative/parity test or test documentation |
| frontend/src/pages/M06ConversionScreen.test.tsx | 1 | Historical/negative/parity test or test documentation |
| frontend/src/pages/RetirementPlanningConsolidatedReviewSection.test.tsx | 2 | Historical/negative/parity test or test documentation |
| specs/runtime/FIRST_RECOVERY_PKG_001_CANONICAL_PENSION_PRODUCT_AND_COMPONENT_SOURCE.md | 45 | Definition / historical governance documentation |
| specs/runtime/IAP_01B_4_completion_report.md | 2 | Definition / historical governance documentation |
| specs/runtime/IAP_01B_4_exception_resolution_register.md | 2 | Definition / historical governance documentation |
| specs/runtime/PKG_004B1_FINAL_PACKAGE_DEFINITION.md | 1 | Definition / historical governance documentation |
| specs/runtime/PKG_006_FINAL_PACKAGE_DEFINITION.md | 7 | Definition / historical governance documentation |
| specs/runtime/PKG_006_acceptance_record.md | 2 | Definition / historical governance documentation |
| specs/runtime/PKG_007_FINAL_PACKAGE_DEFINITION.md | 82 | Definition / historical governance documentation |
| specs/runtime/PKG_007_acceptance_record.md | 6 | Definition / historical governance documentation |
| specs/runtime/PKG_007_definition_acceptance_record.md | 16 | Definition / historical governance documentation |
| specs/runtime/PKG_008_FINAL_PACKAGE_DEFINITION.md | 119 | Definition / historical governance documentation |
| specs/runtime/PKG_008_acceptance_record.md | 26 | Definition / historical governance documentation |
| specs/runtime/PKG_008_definition_acceptance_record.md | 21 | Definition / historical governance documentation |
| specs/runtime/PKG_009_FINAL_PACKAGE_DEFINITION.md | 122 | Definition / historical governance documentation |
| specs/runtime/PKG_009_acceptance_record.md | 23 | Definition / historical governance documentation |
| specs/runtime/PKG_009_definition_acceptance_record.md | 26 | Definition / historical governance documentation |
| specs/runtime/PKG_010_FINAL_PACKAGE_DEFINITION.md | 130 | Definition / historical governance documentation |
| specs/runtime/PKG_010_definition_acceptance_record.md | 20 | Definition / historical governance documentation |
| specs/runtime/PKG_010_implementation_acceptance_record.md | 5 | Definition / historical governance documentation |
| specs/runtime/PKG_011_FINAL_PACKAGE_DEFINITION.md | 86 | Definition / historical governance documentation |
| specs/runtime/PKG_011_definition_acceptance_record.md | 3 | Definition / historical governance documentation |
| specs/runtime/PKG_011_implementation_acceptance_record.md | 5 | Definition / historical governance documentation |
| specs/runtime/PKG_013_FINAL_PACKAGE_DEFINITION.md | 15 | Definition / historical governance documentation |
| specs/runtime/PKG_013_IMPLEMENTATION_EVIDENCE_MATRIX.md | 4 | Definition / historical governance documentation |
| specs/runtime/PKG_013_definition_acceptance_record.md | 3 | Definition / historical governance documentation |
| specs/runtime/PKG_013_implementation_acceptance_record.md | 3 | Definition / historical governance documentation |
| specs/runtime/PKG_014_FINAL_PACKAGE_DEFINITION.md | 2 | Definition / historical governance documentation |
| specs/runtime/PKG_014_definition_acceptance_record.md | 1 | Definition / historical governance documentation |
| specs/runtime/PKG_017_implementation_acceptance_record.md | 1 | Definition / historical governance documentation |
| specs/runtime/V1_TO_V2_MECHANICAL_PARITY_LEDGER.md | 35 | Definition / historical governance documentation |
| specs/runtime/V2_CONTRACT_INTERNAL_PENSION_ANALYSIS_WORKSPACE.md | 4 | Definition / historical governance documentation |
| specs/runtime/V2_FULL_GAP_REGISTER_FROM_PARITY_LEDGER.md | 48 | Definition / historical governance documentation |
| specs/runtime/V2_FULL_PLAN_COVERAGE_PROOF.md | 33 | Definition / historical governance documentation |
| specs/runtime/V2_MASTER_BUILD_SEQUENCE_FULL_SYSTEM.md | 30 | Definition / historical governance documentation |
| specs/runtime/V2_REQUIRED_CAPABILITY_UNIVERSE.md | 33 | Definition / historical governance documentation |
| specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md | 28 | Definition / historical governance documentation |
| specs/runtime/V2_UNIVERSE_COVERAGE_PROOF.md | 33 | Definition / historical governance documentation |
| specs/runtime/platform_runtime_baseline.md | 7 | Definition / historical governance documentation |

## Test disposition and final verification

Obsolete M03/M04/M05 professional workflow suites and old analysis mutation tests
were deleted together with their production paths. M02 tests now cover retained
raw integrity and historical migration rather than removed acceptance lifecycle.
M01 tests no longer require progression. M06 tests retain pure arithmetic and
fingerprint semantics and now prove canonical-only fail-closed source behavior.
Frontend tests assert direct canonical work and historical-only M06/analysis
disposition rather than preserving old selectors/actions.

Earlier backend failures were classified and resolved without restoring old
production behavior:

- Obsolete expectations: old workflow/holding mutation cases removed; historical
  downgrade tests pinned to their original pre-cutover revision rather than
  bypassing the new downgrade prohibition.
- Archive compatibility: pre-cutover holding persistence fixtures explicitly use
  the historical schema; migrated archive/read-only/FK behavior has new tests.
- Genuine regression: archive model/listener registration moved before first query.
- Governance inventory: exact authorized paths/removals and canonical table lists
  updated; unknown paths, protected paths and later modules are still rejected.
- Architecture inventory: M09/M06 tests assert closed canonical availability,
  retaining the unchanged downstream formula/historical snapshot boundary.

| Verification | Result |
| --- | --- |
| Recovery backend focused: products, preflight, migration, holding archive, reachability | 82 passed |
| Additional M01 + canonical + holding regression | 82 passed |
| Archive / retained retirement facts regression | 35 passed |
| Migration + governance focused | 18 passed (4 migration, 14 governance) |
| Frontend focused: canonical product, M06 history, consolidated review | 16 passed (7 + 6 + 3) |
| Full frontend | 330 passed, 26 files |
| Frontend production build | PASS: tsc -b and Vite |
| Additional frontend type-check | PASS: npx tsc --noEmit |
| Full backend | 883 passed, 2 skipped, 7 warnings; 1307.52 seconds; exit 0 |
| Alembic heads | d3e9a6b2c410 (one head) |
| git diff --check | PASS under repository line-ending settings |
| Immutable definition comparison and blob | Unchanged, exact accepted blob |
| master and fetched origin/master | Unchanged, 7b5f3739caa67a8422c5fff67ab7386b2f300741 |
| Protected paths | CURRENT_PROJECT_STATE.md, _evidence/, specs/bootstraps/ absent before/after checks; untouched |
| Final worktree/index, review branch push | Verified after packaging in the final handoff; no self-referential commit hash in this document |

The two backend skips are existing raw-storage symlink tests on this Windows
environment, where symbolic links are unavailable. Seven Pydantic serializer
warnings come from existing invalid-input dependency-manifest test cases.
React Router future-flag warnings are not failures. No production-readiness claim
or independent acceptance is made. PostgreSQL validation limitation is explicit
above; temporary SQLite migration tests never target the user's local database.

## Exact change inventory relative to immutable definition

95 paths: 63 backend, 31 frontend, 1 implementation-evidence document.
19 additions, 43 modifications, 33 deletions. The temporary foundation preflight
service was created at 65f07c8 and removed after freezing its logic in the migration;
it therefore has no net path change relative to the definition.

The status-prefixed inventory below also identifies all deleted frontend/backend
production paths and obsolete test files. A = added, M = rewritten, D = deleted.
Deletion is recorded in linear Git history and is recoverable from that history;
no archive database table or protected user path was deleted.

```text
A	backend/alembic/versions/d3e9a6b2c410_canonical_pension_source.py
M	backend/app/api/clients_routes.py
D	backend/app/api/m02_intake_routes.py
D	backend/app/api/m03_review_routes.py
D	backend/app/api/m04_classification_routes.py
D	backend/app/api/m05_ledger_routes.py
A	backend/app/api/pension_product_routes.py
M	backend/app/db/base.py
M	backend/app/main.py
M	backend/app/models/m02_intake.py
M	backend/app/models/m03_review.py
M	backend/app/models/m04_classification.py
M	backend/app/models/m05_ledger.py
M	backend/app/models/pension_analysis_record.py
A	backend/app/models/pension_product.py
M	backend/app/models/retirement_facts.py
M	backend/app/schemas/m01_case.py
D	backend/app/schemas/m02_intake.py
D	backend/app/schemas/m03_review.py
D	backend/app/schemas/m04_classification.py
D	backend/app/schemas/m05_ledger.py
A	backend/app/schemas/pension_product.py
A	backend/app/services/canonical_pension_source_reader.py
A	backend/app/services/client_record_safety.py
M	backend/app/services/m01_case_service.py
D	backend/app/services/m02_evidence_digest.py
D	backend/app/services/m02_intake_service.py
D	backend/app/services/m03_review_service.py
D	backend/app/services/m04_classification_service.py
D	backend/app/services/m04_rule_catalogue.py
D	backend/app/services/m05_ledger_service.py
M	backend/app/services/m06_conversion_service.py
M	backend/app/services/m07_evidence_service.py
M	backend/app/services/m09_cashflow_service.py
M	backend/app/services/m09_scenario_subject_service.py
A	backend/app/services/pension_product_import_service.py
A	backend/app/services/pension_product_reconciliation.py
A	backend/app/services/pension_product_service.py
A	backend/app/services/pension_source_download.py
M	backend/tests/test_governance_baseline.py
M	backend/tests/test_migration_safety.py
M	backend/tests/test_phase6_schema.py
M	backend/tests/test_phase7_persistence.py
M	backend/tests/test_phase9_api.py
M	backend/tests/test_pkg004b1_m07_evidence.py
M	backend/tests/test_pkg006_m01_case.py
M	backend/tests/test_pkg007_m02_intake.py
D	backend/tests/test_pkg008_m03_review.py
D	backend/tests/test_pkg009_m04_classification.py
D	backend/tests/test_pkg010_m05_ledger.py
M	backend/tests/test_pkg011_m06_conversion.py
M	backend/tests/test_pkg011_migration.py
M	backend/tests/test_pkg013_architecture.py
M	backend/tests/test_pkg013_migration.py
M	backend/tests/test_pkg014_migration.py
A	backend/tests/test_recovery_cutover_preflight.py
A	backend/tests/test_recovery_holding_archive.py
A	backend/tests/test_recovery_migration.py
A	backend/tests/test_recovery_pension_products.py
A	backend/tests/test_recovery_reachability.py
M	backend/tests/test_v21_package_a_persistence.py
M	backend/tests/test_v21_package_b_api.py
D	backend/tests/test_v22_slice1_analysis_record_api.py
M	frontend/src/api/clientsApi.ts
D	frontend/src/api/m02IntakeApi.ts
D	frontend/src/api/m03ReviewApi.ts
D	frontend/src/api/m04ClassificationApi.test.ts
D	frontend/src/api/m04ClassificationApi.ts
D	frontend/src/api/m05LedgerApi.ts
M	frontend/src/api/m06ConversionApi.ts
A	frontend/src/api/pensionProductsApi.ts
M	frontend/src/i18n/he.ts
M	frontend/src/pages/ClientDetailM01.test.tsx
M	frontend/src/pages/ClientDetailScreen.test.tsx
M	frontend/src/pages/ClientDetailScreen.tsx
D	frontend/src/pages/M02PensionIntakeScreen.test.tsx
D	frontend/src/pages/M02PensionIntakeScreen.tsx
D	frontend/src/pages/M03SourceReviewScreen.test.tsx
D	frontend/src/pages/M03SourceReviewScreen.tsx
D	frontend/src/pages/M04ClassificationScreen.test.tsx
D	frontend/src/pages/M04ClassificationScreen.tsx
D	frontend/src/pages/M05LedgerScreen.test.tsx
D	frontend/src/pages/M05LedgerScreen.tsx
M	frontend/src/pages/M06ConversionScreen.test.tsx
M	frontend/src/pages/M06ConversionScreen.tsx
D	frontend/src/pages/PensionAnalysisRecordSection.test.tsx
D	frontend/src/pages/PensionAnalysisRecordSection.tsx
A	frontend/src/pages/PensionProductsScreen.test.tsx
A	frontend/src/pages/PensionProductsScreen.tsx
M	frontend/src/pages/RetirementPlanningConsolidatedReviewSection.test.tsx
M	frontend/src/pages/RetirementPlanningConsolidatedReviewSection.tsx
M	frontend/src/pages/RetirementPlanningFactsSection.test.tsx
M	frontend/src/pages/RetirementPlanningFactsSection.tsx
M	frontend/src/routes/AppRoutes.tsx
A	specs/runtime/FIRST_RECOVERY_PKG_001_implementation_progress.md
```

## Governance

FIRST_STAGE_INTEGRATED_SYSTEM_AND_UI_VALIDATION remains the active checkpoint.
M11-M14 remain NOT_AUTHORIZED. No next implementation package is authorized.
02M remains FROZEN. M08E remains EXCLUDED.
Production readiness remains NOT_CLAIMED. Only WORK may independently accept this
package. The implementation branch is for review only; no merge is authorized.
