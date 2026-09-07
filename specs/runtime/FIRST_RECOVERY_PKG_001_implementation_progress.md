# FIRST_RECOVERY_PKG_001 implementation progress

Status: INCOMPLETE — NOT READY FOR INDEPENDENT AUDIT.

This is implementation evidence, not a definition or acceptance manifest.
Semantic authority remains the immutable definition at
`09cd67417614cbdc4e422321db9324f7f9883ac0`, blob
`adf2a7e1b06f2f8660f82b2c735e51515395d713`.

## Foundation stage

Implemented but deliberately not registered in production yet:

- Canonical product/component/source-link/audit model declarations.
- Exact monetary validation, reconciliation, serialized CRUD and optimistic versions.
- Recognized XML import mapping, transactional source preservation and replay checks.
- Canonical-only source reader and a closed conversion-availability response.
- Canonical API router tested in an isolated FastAPI application.
- Hebrew product screen/API client tested in an isolated route.
- Read-only cutover preflight planner and conflict tests.

Production router registrations and old workflow files have NOT been removed.
The new source reader has NOT been connected to M06.
No migration revision or schema cutover has been implemented.
Do not deploy this intermediate stage as the completed package.

The model registry now explicitly loads the existing PensionAnalysisRecord model
required by Client's relationship; isolated canonical tests exposed that the
previous registry depended on an unrelated API import to register it.

## Validation recorded during development

- Focused backend: 65 passed (canonical foundation and cutover preflight).
- Focused frontend: 7 passed.
- Full frontend: 931 passed, 32 files (before the subsequent source-diagnostics display addition).
- Frontend production build/type-check passed before that display addition.
- Full backend run in progress at this stage; an early governance failure is
  attributable to new files not yet tracked. No full-backend success is claimed.

These are intermediate results, not final package validation.

## Remaining work before acceptance submission

- Implement and test the actual migration, including frozen preflight, legacy
  export interpretation, evidence counts, safe rollback policy and upgrade from
  the existing schema on supported databases.
- Complete old-path deletion and all caller migrations in the same package.
- Connect canonical source availability to M06 without changing conversion semantics.
- Remove M01 progression UI/API and professional gates as required by definition.
- Register canonical API/UI only with complete cutover.
- Retire obsolete workflow tests while preserving useful integrity regressions.
- Complete archive-retention and repository-wide reachability inventory.
- Harden and validate remaining import/identity/metadata edge cases, source/audit
  immutability and downstream deletion protection against migrated records.
- Run final focused/full suites, build, migration and governance verification.
- Push review branch only once the complete package passes verification.

## Storage note for review

PostgreSQL monetary columns use NUMERIC(20,2). SQLite lacks a native fixed decimal
type and its NUMERIC affinity converts nonintegral values to binary floats.
The foundation therefore uses a two-decimal text encoding on SQLite, with Decimal
validation and arithmetic; a maximum-precision round-trip test covers this.
The eventual migration must preserve the same lossless representation.

Master and the immutable definition are unchanged. No merge or push has occurred.
M11–M14 and any next package remain NOT_AUTHORIZED; 02M remains FROZEN;
M08E remains EXCLUDED; production readiness remains NOT_CLAIMED.
