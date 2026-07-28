# PKG-007 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-007 — M02 Controlled Pension Intake and Opaque Source Preservation` |
| Status | `DEFINITION_ACCEPTED` |
| Accepted definition HEAD | `18fd30b4de8e2c68978e524962fc750f118675b4` |
| Base | `eb80f7986b39544af6f87a5a6b561f1a833543ee` |
| Module | `M02` |
| Definition | `specs/runtime/PKG_007_FINAL_PACKAGE_DEFINITION.md` |
| Implementation | `NOT_AUTHORIZED` |
| Migration execution | `NOT_AUTHORIZED` |
| M03 | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |

## Accepted Definition Chain

1. `940fc96fef1ebc04ed5be999d91edbc7c2eec9bd` —
   `docs: define M02 controlled pension intake`
2. `d73fe127c4dacc6ecce5053022b10098488921f7` —
   `docs: align PKG-007 definition with V1 intake behavior`
3. `18fd30b4de8e2c68978e524962fc750f118675b4` —
   `docs: close PKG-007 definition reaudit gaps`

## Accepted Product Boundary

The accepted definition covers:

- controlled manual pension intake;
- optional opaque source preservation;
- V1-derived XML and DAT support;
- additional opaque PDF, CSV, and XLSX preservation;
- multi-file batch intake;
- separate per-file records and results;
- declared manual source facts;
- preservation of original bytes;
- server-computed SHA-256;
- client-scoped immutable blobs;
- duplicate-candidate detection;
- explicit supersession;
- the M02 lifecycle;
- retained history;
- client isolation;
- route-generation asynchronous safety; and
- future handoff to M03 review.

M02 is not a parser, classification layer, ledger, or calculation module.
`accepted_for_review` is not authoritative acceptance. V1 import equivalence is
not claimed before M03-M04 and the remaining downstream chain are completed
and separately accepted.

## V1 Governing Rule

> V1 is authoritative for existing professional logic, business meaning, and material product behavior. V2 may change technical implementation, but not material meaning or behavior without an explicit approved decision.

The following accepted corrections are derived from V1 evidence:

- `.dat` support;
- support for UTF-8, UTF-8 BOM, Windows-1255, ISO-8859-8, and Latin-1;
- `declared_start_date`;
- `declared_product_type`;
- manual provider/account fallback; and
- multi-file selection.

## Accepted Technical Adaptations

The following are accepted as bounded technical adaptations and are not
claimed to exist in V1:

- backend-managed storage;
- immutable blob model;
- opaque relative storage keys;
- client-local SHA-256 deduplication;
- retained non-destructive history;
- explicit supersession;
- request-level and per-file atomic cleanup;
- attachment-only download;
- no public or static serving; and
- generation-token asynchronous isolation.

## File Contract

The accepted opaque extensions are:

- `.pdf`;
- `.xml`;
- `.dat`;
- `.csv`;
- `.xlsx`.

The limit is exactly:

`25 MiB per file`

XML, DAT, and CSV may use:

- UTF-8;
- UTF-8 BOM;
- Windows-1255;
- ISO-8859-8;
- Latin-1.

M02 preserves the exact received bytes. It performs no parsing, byte
normalization, transcoding, schema validation, or semantic validation.

## Manual Intake Contract

The accepted manual source facts include:

- declared provider when supplied;
- declared product/fund identity;
- declared account/reference when supplied;
- declared balance and components;
- declared statement/import date;
- `declared_start_date`;
- `declared_product_type`;
- notes and declared basis; and
- a server-generated `manual_technical_reference` when required.

The technical reference is not a real account, provider, professional source
fact, or declared account identifier. It is not passed downstream as a
declared account.

## Batch and Failure Contract

- The frontend supports multi-file selection.
- Every identifiable file has independent intake, source, lifecycle,
  validation, and result boundaries.
- Processing is atomic per file.
- Per-file failures do not roll back independently committed files.
- Request-level failures are distinguished from per-file failures.
- Independently committed files remain committed.
- Uncommitted files are cleaned without partial rows or orphaned bytes.
- There is no global rollback of committed files.
- Mixed outcomes return structured per-file results alongside a distinct
  request-level error when completed outcomes exist.
- Retry remains governed by checksum, duplicate-candidate, immutable-blob
  reuse, and no-overwrite rules.
- Stale request errors, completions, and `finally` effects cannot change a new
  client context.

No distributed transaction, queue, or background-processing system is part of
the accepted definition.

## Lifecycle

The M02 states are:

- `uploaded`;
- `metadata_review`;
- `accepted_for_review`;
- `rejected`;
- `superseded`.

The only allowed transitions are:

1. `uploaded -> metadata_review`;
2. `uploaded -> rejected`;
3. `metadata_review -> accepted_for_review`;
4. `metadata_review -> rejected`;
5. `accepted_for_review -> metadata_review`;
6. `accepted_for_review -> rejected`;
7. `accepted_for_review -> superseded`.

Every other transition is prohibited. `rejected` and `superseded` are terminal
and retained. `accepted_for_review` means ready for future M03 review only; it
does not make the source authoritative.

## Data Model Determination

`ADDITIVE_MIGRATION_REQUIRED`

The planned entities are:

- `m02_intake_records`;
- `m02_preserved_sources`;
- `m02_preserved_blobs`.

No migration has been created or executed. The schema has not been
implemented, and implementation has not been authorized.

## Audit History

Initial definition audit disposition:

`V1_SOURCE_UNAVAILABLE_FOR_PKG_007_ALIGNMENT`

After the definition and V1 evidence became available:

`RETURN_TO_CODEX_FOR_V1_ALIGNMENT_CORRECTION`

| Defect | Description | Final status |
|---|---|---|
| D-007-V1-001 | DAT support | `FIXED` |
| D-007-V1-002 | Encoding alignment | `FIXED` |
| D-007-V1-003 | Manual intake source facts | `FIXED` |
| D-007-V1-004 | Multi-file journey | `FIXED` |

All four defects were corrected. The first Point Reaudit returned two wording
gaps only: an explicit frontend `.dat` test and an explicit distinction
between batch-wide request failure and per-file failure. Both were corrected.

Final Point Reaudit:

`FINAL_POINT_REAUDIT_PASSED_ACCEPT_PKG_007_DEFINITION`

## Acceptance and Negative Criteria

| Item | Result |
|---|---|
| Acceptance Criteria | `22` |
| Negative Acceptance Criteria | `16` |
| Remaining defects | `None` |
| User decisions | `None` |

## Explicit Exclusions

- implementation;
- migration execution;
- XML or DAT parsing;
- normalized import;
- M03;
- classification;
- ledger;
- conversion;
- tax;
- fixation changes;
- scenarios;
- recommendations;
- reports;
- OCR;
- live clearinghouse retrieval;
- object-storage implementation;
- broad authorization;
- production deployment;
- production-readiness claim; and
- V1/V2 parity claim.

## Follow-Up Boundary

- PKG-007 definition is accepted.
- Implementation requires a separate Gate authorization.
- M03 remains `NOT_AUTHORIZED`.
- No next package is authorized.
