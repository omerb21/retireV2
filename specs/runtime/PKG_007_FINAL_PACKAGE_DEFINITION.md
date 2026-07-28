# PKG-007 — M02 Controlled Pension Intake and Opaque Source Preservation

## 1. Definition status

| Item | Value |
|---|---|
| Package | `PKG-007 — M02 Controlled Pension Intake and Opaque Source Preservation` |
| Module | `M02` |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Product outcome | Controlled manual pension intake and optional opaque source preservation |
| Storage model | `MANAGED_LOCAL_STORAGE_FIRST_STAGE` |
| Migration | `ADDITIVE_MIGRATION_REQUIRED` |
| Implementation | `NOT_AUTHORIZED` |
| M03 | `NOT_AUTHORIZED` |
| Definition base HEAD | `eb80f7986b39544af6f87a5a6b561f1a833543ee` |
| Existing Alembic head | `f3a7c9d2e610` |
| Next package | `NOT_AUTHORIZED` |

This document defines one coherent M02 product package. It does not authorize
implementation or migration execution, does not open M03, does not parse or
classify uploaded content, and does not claim production readiness, malware
safety, or V1/V2 parity.

## 2. Authority and Build Sequence

The authoritative source is
`specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.

Its locked Build Sequence places M02 immediately after the accepted M01
foundation:

> **Source intake and preservation: M02-M03.** Define approved intake formats,
> preserve raw evidence, and require review before normalized information
> becomes authoritative.

The dependency order is:

`M01 -> M02/M03 -> M04 -> M05 -> M06/M07 -> M08 -> ...`

PKG-007 covers M02 only. M03 remains a separate package and is not authorized
by this definition.

## 3. Locked product outcome

After a separately authorized implementation, a user working inside an active
client case can:

1. open a client-scoped pension intake screen;
2. create a controlled manual intake record preserving the declared start date
   and declared product-type text when supplied;
3. select and upload one or more opaque source files in one operation, with a
   separate intake, source, validation result, and lifecycle for every file;
4. see preserved source metadata and preservation status;
5. see the original filename without using it as a storage path;
6. see the server-computed SHA-256 checksum and byte size;
7. see duplicate-candidate and superseding-candidate indications;
8. correct permitted metadata without replacing source bytes;
9. move the intake through backend-authorized lifecycle transitions;
10. see retained rejected and superseded history;
11. download preserved bytes through a client-scoped attachment route;
12. return to the M01 case;
13. move A-to-B and A-to-B-to-A without state leakage; and
14. continue using accepted PKG-005 and PKG-006 workflows without regression.

Manual values remain declared or collected M02 facts. Preserving a file does
not make its contents correct, parsed, classified, authoritative, or eligible
for ledger or calculation use.

## 4. Current-state mapping

| Repository area | Classification | Evidence and PKG-007 treatment |
|---|---|---|
| M01 Client and case context | Reusable as-is | `Client` supplies authoritative client ownership and PKG-006 supplies stable client navigation, lifecycle display, and client-context generation. M02 records must reference an existing client and must not change M01 completeness or lifecycle. |
| `PensionHolding` | Conflicting; not reusable as M02 persistence | It already requires a constrained `product_type` and carries source, verification, and lifecycle concepts used by later retirement-fact workflows. Reusing it would make M02 perform classification or downstream fact creation. Existing records remain untouched. |
| `ClearinghouseSnapshot` | Metadata shell only; not sufficient | It stores import date, source type, filename text, collection metadata, and verification metadata. It has no preserved bytes, storage key, checksum, duplicate relation, M02 lifecycle, or immutable blob reference. It must not be repurposed destructively. |
| `RetirementPlanningDocument` | Metadata shell only; not sufficient | It stores filename text and collection metadata but no upload, byte preservation, checksum, storage reference, M02 lifecycle, or duplicate/superseding relation. It remains unchanged. |
| Existing collection APIs | Reusable as regression evidence only | Current routes accept JSON metadata and never receive file bytes. Their client-scoped lookup patterns are useful, but they are not M02 upload routes. |
| Existing pension-fact UI | Conflicting with M02 authority | `RetirementPlanningFactsSection` edits `PensionHolding` records with later-stage vocabularies. It cannot serve as the M02 intake screen or silently create downstream holdings. |
| Client-detail navigation | Reusable with bounded change | The accepted M01 client screen is the correct entry point for one client-scoped M02 route. Existing employment and fixation links remain unchanged. |
| Client-context generation hook | Reusable as-is | The accepted `clientId + monotonic route-context generation` pattern must guard every M02 read, upload, save, download preparation, and lifecycle mutation. |
| SHA-256 usage | Reusable pattern, new byte helper required | Existing services use `hashlib.sha256` for canonical evidence fingerprints. M02 requires a separate streaming byte-checksum helper; a browser-provided checksum is never authoritative. |
| Upload/file validation | Missing and required | No `UploadFile`, multipart route, extension allowlist, MIME validator, signature validator, size limiter, partial-upload cleanup, or file-download implementation exists. |
| Storage infrastructure | Missing and required | Deployment configuration currently defines database connectivity only. There is no managed upload directory, object-store client, storage adapter, public/static serving contract, or reference-retention helper. |
| Authentication | Accepted first-stage limitation | The application remains single-user and has no broad trusted human-session identity. M02 uses server-controlled operational provenance only and makes no authentication or professional-approval claim. |
| Database and migrations | Reusable chain; additive successor required | SQLAlchemy and Alembic are established. Current single head is `f3a7c9d2e610`. Dedicated M02 tables are required because existing business tables cannot represent the locked intake/blob/source boundaries safely. |
| Frontend upload support | Missing and required | No multipart API helper, intake route, progress/status screen, history presentation, duplicate/superseding display, or download action exists. |
| Tests | Reusable with substantial focused additions | Existing client isolation, A-to-B/A-to-B-to-A, M01, PKG-005, PKG-006, migration, API, and frontend test patterns are reusable. File/storage/lifecycle/rollback coverage is missing. |
| Object storage | Deferred | The first stage uses managed local storage behind an adapter boundary. No object-storage implementation is authorized. |
| Parsing, OCR, and live retrieval | Excluded | No existing runtime behavior is authorized for M02. XML, DAT, CSV, and XLSX remain opaque; OCR and live clearinghouse retrieval are excluded. |

## 5. Locked Q-003 and Q-004 decisions

### 5.1 Allowed opaque files

The only allowed extensions are:

- `.pdf`;
- `.xml`;
- `.dat`;
- `.csv`;
- `.xlsx`.

The maximum accepted size of each submitted file is exactly:

`25 MiB = 26,214,400 bytes`

Every other extension is rejected. Explicitly prohibited formats include:

- `.xls`;
- `.xlsm` and every other macro-enabled Office format;
- ZIP, RAR, and 7z archives;
- images;
- HTML;
- scripts;
- executables.

XML, DAT, CSV, and XLSX are preserved as opaque artifacts and are not parsed
for business content in M02. DAT support is V1-derived and does not establish
a new V2 format interpretation.

### 5.2 Q-004 exclusions

| Capability | M02 status |
|---|---|
| OCR | `EXCLUDED` |
| Live clearinghouse retrieval | `EXCLUDED` |
| XML parsing | `DEFERRED_TO_M03` |
| Normalized import | `DEFERRED_TO_M03` |

No external integration is included.

## 6. Additive persistence model

### 6.1 Migration determination

`ADDITIVE_MIGRATION_REQUIRED`

The future implementation requires one additive Alembic successor to
`f3a7c9d2e610`. No existing table is to be renamed, repurposed, backfilled, or
destructively changed.

### 6.2 `m02_intake_records`

One record represents one manual intake and its optional source-preservation
workflow.

| Field | Contract |
|---|---|
| `intake_id` | Stable server-generated primary key |
| `client_id` | Required foreign key to `clients.client_id` |
| `declared_provider_name` | Nullable trimmed value declared by the user; may remain missing or explicitly unknown and creates no provider authority |
| `product_name` | Nullable declared product/fund name |
| `product_identifier` | Nullable declared product/fund code or identifier |
| `declared_account_reference` | Nullable account/reference identifier declared by the user |
| `manual_technical_reference` | Required server-generated stable technical identity for a manual-only record; nullable for upload-created records; never a professional account number |
| `declared_total_balance_amount` | Nullable exact decimal; no classification or calculation meaning |
| `declared_monthly_pension_amount` | Nullable exact decimal; no conversion meaning |
| `declared_component_values` | Nullable JSON list of declared label/exact-decimal-string pairs; labels remain opaque and unclassified |
| `declared_statement_date` | Nullable statement/import date |
| `declared_start_date` | Nullable source date declared by the user; not eligibility, retirement, or pension-start authority and causes no M02 calculation |
| `declared_product_type` | Nullable opaque product-type text declared by the user; not M04 classification, taxonomy authority, or a pension/capital decision |
| `source_type` | Required trimmed declared source type |
| `declared_basis` | Nullable text describing the declared basis |
| `notes` | Nullable intake notes |
| `lifecycle_status` | Required M02 lifecycle value |
| `preservation_status` | `not_applicable`, `pending`, `preserved`, or `failed` |
| `preservation_failure_code` | Nullable stable failure code; no raw exception or path |
| `duplicate_candidate` | Required boolean, default false |
| `duplicate_of_intake_id` | Nullable same-client self-reference |
| `superseding_candidate` | Required boolean, default false |
| `superseding_intake_id` | Nullable same-client self-reference to the older candidate |
| `created_by_actor` | Required server-controlled operational actor |
| `updated_by_actor` | Required server-controlled operational actor |
| `created_at` | Required server timestamp |
| `updated_at` | Required server timestamp |

The component list is declared evidence only. It may preserve labels and exact
decimal strings but may not map them to M04 categories or M05 ledger
components.

Creation may preserve incomplete metadata in `metadata_review` or `uploaded`.
Saving a manual intake is never blocked merely because a real provider or
declared account reference is missing. The backend may return those omissions
as diagnostics. It must not invent a provider or present
`manual_technical_reference` as a real account.

Transition to `accepted_for_review` requires a nonempty source type and no
unresolved preservation failure when an upload was requested. For an
upload-created intake, the existing provider, product, and declared-account
metadata gate remains required. For a manual-only intake, at least one
nonempty product name, product identifier, or `declared_product_type` is
required, while missing `declared_provider_name` or
`declared_account_reference` remains a diagnostic and does not block the M02
transition. A future downstream package may require those real identifiers,
but M02 does not create or satisfy that downstream authority.

Balance, component, monthly-pension, declared statement date,
`declared_start_date`, and `declared_product_type` remain declared source facts.
Their presence creates no tax, pension, capital, availability, eligibility,
classification, retirement-date, pension-start, or calculation inference.

### 6.3 `m02_preserved_blobs`

One blob row represents one immutable physical object within one client
boundary.

| Field | Contract |
|---|---|
| `blob_id` | Stable server-generated primary key |
| `client_id` | Required client owner |
| `storage_key` | Required opaque relative key, globally unique |
| `sha256_checksum` | Required lowercase 64-character server-computed hex digest |
| `byte_size` | Required, greater than zero and at most `26,214,400` |
| `validated_media_type` | Required accepted media-type family |
| `created_at` | Required server timestamp |

Required constraints and indexes:

- unique `(client_id, sha256_checksum)`;
- unique `storage_key`;
- check on checksum length and normalized hexadecimal form;
- check on byte-size range;
- composite uniqueness supporting same-client foreign keys;
- immutable blob identity, checksum, size, media type, and storage key;
- delete restriction while any source references the blob.

Physical deduplication is client-local only. A checksum match in another
client does not share a blob, alter the response, or reveal existence.

### 6.4 `m02_preserved_sources`

One source row links an intake record to one preserved blob and its safe
metadata.

| Field | Contract |
|---|---|
| `source_id` | Stable server-generated primary key |
| `client_id` | Required client owner |
| `intake_id` | Required unique same-client reference to `m02_intake_records` |
| `blob_id` | Required same-client reference to `m02_preserved_blobs` |
| `original_filename` | Required metadata only; never a storage path |
| `normalized_extension` | Required one of `.pdf`, `.xml`, `.dat`, `.csv`, `.xlsx` |
| `declared_mime_type` | Declared MIME value accepted by the validator; may be empty only for DAT under the bounded technical text rule in section 9.4 |
| `validated_media_type` | Required server-determined accepted type |
| `detected_text_encoding` | Nullable technical metadata for XML, DAT, or CSV when deterministically identified; never parser or schema validity |
| `uploaded_at` | Required server timestamp |

Required constraints and indexes:

- one preserved source per intake record;
- same-client composite foreign keys for intake and blob references;
- index by `(client_id, uploaded_at)`;
- index by `(client_id, intake_id)`;
- no cascade that can delete a referenced blob;
- no ordinary mutation of blob linkage or source byte identity.

### 6.5 Provenance actor

Until broad authentication is separately introduced, actor fields use a
deterministic server-controlled technical workflow actor following the
existing repository convention:

`system:m02-intake:M02 intake workflow`

It is operational provenance only. It is not authentication, authorization,
professional review, proof of the human operator, or source authority. The
browser cannot supply or override it.

## 7. Controlled manual-intake contract

A manual-only intake:

1. is created through a client-scoped JSON operation;
2. receives its client ID from the route;
3. starts in `metadata_review`;
4. stores only declared values, including `declared_start_date` and
   `declared_product_type` when supplied;
5. has `preservation_status=not_applicable`;
6. may be corrected while editable;
7. derives missing-metadata diagnostics on the backend;
8. receives a deterministic server-generated `manual_technical_reference`
   that is explicitly technical, is not displayed as a real account, and is
   never emitted downstream as a declared account identifier;
9. may be saved with missing or explicitly unknown
   `declared_provider_name` and with no `declared_account_reference`;
10. may move to `accepted_for_review` only after the path-specific M02
    metadata gate in section 6.2 is satisfied;
11. does not create a `PensionHolding`, classification, ledger row, calculation
   input, or M07/M08 evidence record; and
12. remains visible throughout its non-destructive history.

Manual metadata writes are atomic. Validation failure leaves the previous
record unchanged. Numeric values are preserved as exact declared decimals;
M02 performs no conversion, aggregation, reconciliation, or sign
interpretation.

## 8. Opaque-upload contract

An upload operation:

1. is client-scoped and multipart;
2. accepts one or more files selected in one request;
3. ignores browser paths and never trusts a browser-selected storage key;
4. streams bytes into backend-managed temporary storage;
5. enforces the byte limit during streaming;
6. computes SHA-256 over the exact received bytes;
7. validates extension, declared MIME family, and deterministic signature or
   container characteristics;
8. creates or reuses one same-client immutable blob for each file;
9. creates a separate intake and source record for every file, including every
   duplicate candidate;
10. never stores duplicate physical bytes for a same-client checksum match;
11. starts a successfully preserved upload in `uploaded`;
12. returns a structured per-file result with backend-authored metadata,
    diagnostics, indicators, lifecycle, and allowed transitions;
13. never combines file bytes, merges file metadata into one intake, or assigns
    a batch-wide lifecycle in place of each file's lifecycle; and
14. never parses or extracts business content.

A file rejected by request, extension, size, MIME, signature, container, or
text validation creates no source or blob for that file. If technically valid
bytes cannot be preserved after validation has completed, that file's source
and blob are rolled back and one client-scoped intake failure record is
retained in `metadata_review` with `preservation_status=failed` and a stable
safe failure code. That record contains no storage key, checksum claim, file
contents, temporary path, or raw storage exception and cannot move to
`accepted_for_review` unless a new successful intake is created. Failure of
one file does not roll back other files that completed successfully.

## 9. File validation contract

### 9.1 Common validation

All uploads require:

- an allowed lowercase-normalized extension;
- a compatible declared MIME family;
- size greater than zero and no more than `26,214,400` bytes;
- deterministic type-specific validation;
- a safe original filename representation;
- no executable interpretation;
- no reliance on `application/octet-stream` as a general bypass; the narrow
  V1-derived DAT handling in section 9.4 is the only exception and still
  requires bounded non-binary text validation.

Any extension/MIME/signature mismatch is rejected with a stable structured
error. Validation does not establish that the document is truthful, safe,
authoritative, or semantically well formed.

### 9.2 PDF

- extension: `.pdf`;
- declared MIME: `application/pdf`;
- required signature: PDF header `%PDF-`;
- stored and downloaded only as an attachment;
- no rendering, text extraction, OCR, or structural business validation.

### 9.3 XLSX

- extension: `.xlsx`;
- declared MIME:
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`;
- must be a valid OOXML ZIP container;
- central-directory inspection must reject unsafe paths, encrypted members,
  macro/VBA content, and macro-enabled workbook types;
- `[Content_Types].xml` and the workbook container identity must be present;
- declared total uncompressed member size must not exceed the same 25 MiB
  first-stage bound;
- no member is extracted to a public or persistent path;
- no workbook cells or business content are read.

### 9.4 XML, DAT, and CSV

Accepted declared MIME families are:

- XML: `application/xml` or `text/xml`;
- DAT: `text/plain`, or an empty/`application/octet-stream` declaration only
  when the bounded text checks below succeed; this is not a general
  `application/octet-stream` bypass;
- CSV: `text/csv`.

All three must:

- contain non-binary text;
- decode without normalization as UTF-8, UTF-8 with BOM, Windows-1255,
  ISO-8859-8, or Latin-1;
- contain no NUL bytes;
- preserve the exact received bytes without rewriting, transcoding, or
  normalizing the encoding;
- retain the deterministically detected encoding as source metadata when it
  can be identified; and
- remain opaque after technical validation.

Encoding detection proves only that the bounded text check succeeded. It is
not evidence of parser validity, XML schema validity, professional
correctness, or source authority. M02 performs no XML or DAT structural or
semantic parsing, XML schema validation, CSV delimiter or column parsing,
extraction, or normalized import. CSV uses the same technical encoding set
only for opaque preservation; this is not asserted as a V1 professional CSV
contract and authorizes no future CSV parsing.

## 10. Managed local-storage contract

The first-stage storage mode is:

`MANAGED_LOCAL_STORAGE_FIRST_STAGE`

Required behavior:

- the backend receives its storage root from required server configuration
  `M02_STORAGE_ROOT`;
- the root is outside repository, public, frontend, and static-serving roots;
- startup fails closed when the root is missing, unresolved, not writable, or
  unsafe;
- only opaque generated relative storage keys are persisted;
- absolute paths are never persisted or returned;
- the browser cannot select directories, keys, or filenames used for storage;
- original filenames remain metadata only;
- storage keys do not include client-controlled path segments;
- existing objects are never overwritten by filename;
- final creation uses collision-safe exclusive or atomic placement;
- a narrow storage adapter separates domain logic from managed-local-storage
  operations;
- future object storage may implement the adapter under separate
  authorization, but is not implemented by PKG-007.

The storage root configuration must not default silently to the repository,
current working directory, home directory, or a public web root.

## 11. Checksum, duplicate, and blob-reference contract

The checksum algorithm is exactly:

`SHA-256`

It is computed by the backend over the received bytes while streaming or
before final storage commit. A caller-provided checksum is ignored or rejected
and is never authoritative.

A duplicate candidate is exactly:

`same client + same SHA-256 checksum`

On a same-client match:

- a new intake and source record are created;
- `duplicate_candidate=true`;
- `duplicate_of_intake_id` identifies the existing matching intake;
- the source references the existing immutable same-client blob;
- duplicate physical bytes are removed from temporary storage;
- the existing intake, source, and blob are not changed;
- no silent merge or overwrite occurs.

Checksums are never searched or disclosed across client boundaries in a way
that changes an external response. Same bytes uploaded for another client
produce an independent client-owned blob and reveal no cross-client match.

## 12. Superseding-candidate contract

A superseding candidate is exactly:

`same client + same declared source_type + newer declared statement/import date`

Detection is automatic, but lifecycle supersession is explicit:

- `superseding_candidate=true` identifies a possible older intake;
- `superseding_intake_id` links to that candidate;
- the older intake is not automatically changed;
- only an allowed explicit transition can mark an
  `accepted_for_review` intake as `superseded`;
- missing date prevents date comparison only;
- equal date is not newer;
- a different source type is not a match;
- all older metadata and bytes remain retained;
- no candidate is declared more correct, authoritative, or professionally
  sufficient.

## 13. Intake lifecycle

### 13.1 Initial states

| Creation path | Initial lifecycle |
|---|---|
| Successful opaque upload | `uploaded` |
| Manual-only intake | `metadata_review` |

### 13.2 Allowed transitions

| Current state | Target state | Preconditions and effect |
|---|---|---|
| `uploaded` | `metadata_review` | Required upload-path metadata is present; bytes remain unchanged |
| `uploaded` | `rejected` | Stable rejection reason required |
| `metadata_review` | `accepted_for_review` | Path-specific required metadata in section 6.2 is complete and preservation is not failed |
| `metadata_review` | `rejected` | Stable rejection reason required |
| `accepted_for_review` | `metadata_review` | Reopens permitted metadata correction; bytes remain immutable |
| `accepted_for_review` | `rejected` | Stable rejection reason required |
| `accepted_for_review` | `superseded` | Explicit action and a valid same-client superseding candidate required |

Every other transition, including same-state and skipped transitions, is
blocked by the backend with a stable structured conflict.

### 13.3 Lifecycle rules

- `rejected` and `superseded` are terminal and read-only.
- Corrections to terminal records require a new intake record.
- Metadata is editable only in `uploaded` or `metadata_review`, and after an
  explicit `accepted_for_review -> metadata_review` transition.
- Blob bytes, checksum, size, storage key, and original source identity are
  never editable.
- Only `accepted_for_review` may be handed to a future M03 review package.
- `accepted_for_review` means ready to enter review; it is not source
  authority or downstream acceptance.
- Lifecycle authority is backend-authored. The frontend displays only returned
  allowed targets.
- M01 lifecycle is separate and unchanged.

Rejection uses stable reason codes plus optional non-authoritative notes.
Browser-authored free text is never used as a lifecycle code or authority.

## 14. Storage/database atomicity and failure cleanup

The future implementation must follow this bounded sequence:

1. stream into a generated temporary file inside the managed storage boundary;
2. enforce size and compute SHA-256 while streaming;
3. validate extension, MIME, signature/container, and filename metadata;
4. resolve the same-client blob inside a database transaction;
5. when new bytes are required, atomically place them under a generated final
   key without overwrite;
6. insert blob, source, and intake state in one database transaction;
7. commit only after required storage operations succeed;
8. on storage failure, roll back source/blob rows and record only the bounded
   failed-intake outcome described in section 8;
9. on database failure, remove only a newly created unreferenced final object;
10. always remove the request's temporary file in success, rejection, error,
    cancellation, and `finally`.

A request must never report success when the database points to missing bytes.
A crash may leave an unreferenced opaque object but must not leave a committed
source pointing to absent content. A bounded reconciliation/cleanup operation
may remove objects proven unreferenced; it must never delete by filename or
without checking database references.

For a multi-file request, this sequence and its transaction/compensation
boundary apply independently to each file. Successful files remain committed
when another file fails. A failed file leaves no partial source/blob state, and
the response contains one stable result per submitted file. Same-checksum
files in the same batch still create separate intake/source records and may
share the same client-local immutable blob. Response order is not authority
and need not match selection order.

Raw exceptions, file content, absolute paths, and full storage keys must not
appear in client responses or logs.

### 14.1 Per-file processing failure

A per-file processing failure occurs after the batch request has been accepted
and the backend has begun handling identifiable files, but one file fails type,
size, encoding/binary, storage, checksum, database-persistence, or metadata
validation. The result remains per-file:

- other files may succeed;
- the failed file leaves no partial intake/source/blob rows or orphaned bytes;
- every file that reached its independent committed state remains committed;
- there is no batch-wide rollback of committed files; and
- the response returns one structured result for each identifiable file.

### 14.2 Batch-wide request failure

A batch-wide request failure occurs when the backend cannot begin or complete
the request framework as a batch, including malformed multipart, unavailable
request body, client/context validation failure, invalid or foreign client,
transport interruption before a complete file is received, failure before
files can be identified or processing can begin, or another unrecoverable
request-level failure.

In that case:

- no per-file success is reported for a file that did not reach its independent
  committed state;
- every file already independently committed remains committed;
- every identified but uncommitted file is cleaned up without partial
  intake/source/blob rows or orphaned bytes;
- there is no global rollback of committed files;
- when completed or committed per-file outcomes exist, the API returns those
  structured results alongside a distinct request-level error;
- when no file processing began, the API returns request-level failure only;
- retry remains subject to the existing checksum, duplicate-candidate,
  immutable-blob reuse, and no-overwrite contract; it never creates a silent
  merge, duplicate, or overwrite.

No distributed transaction, queue, or background-processing system is
introduced by this distinction.

## 15. Privacy, access, and download

Preserved sources have:

- no public URL;
- no static serving;
- no inline preview;
- no exposed storage path;
- no frontend direct-file access;
- no cross-client checksum disclosure.

Download is available only through a backend client-scoped route containing
both route client ID and source ID. The backend:

- resolves the source under both identifiers;
- fails foreign and missing IDs safely without existence leakage;
- confirms the referenced blob belongs to the same client;
- returns attachment disposition only;
- uses a sanitized original filename for display;
- sets `X-Content-Type-Options: nosniff`;
- does not log content or full paths.

The package remains bounded to the existing single-user application. Public
network and production deployment remain unauthorized. The technical workflow
actor is not authentication or proof of a human identity.

## 16. Retention and deletion

- There is no ordinary UI delete action.
- There is no ordinary API physical-delete route.
- Rejected and superseded records remain retained and visible.
- Corrections and newer uploads are additive.
- Bytes remain retained while any source references their blob.
- Foreign keys and service checks prevent referenced blob deletion.
- No legal retention period is asserted.
- Default first-stage operational retention continues until a future
  exceptional administrative process exists.

Exceptional deletion or redaction is outside PKG-007 and belongs to future
M14/privacy/operations decisions. A future process must leave a metadata
tombstone sufficient to explain missing or redacted bytes, but PKG-007 creates
no UI, route, policy duration, or administrative authority for that process.

## 17. Antivirus and malware boundary

Antivirus scanning is:

`NOT_REQUIRED_FIRST_STAGE`

This is permitted only because PKG-007:

- never executes uploaded content;
- never renders it inline;
- never performs server-side document or business-content processing;
- rejects macro-enabled formats;
- stores bytes outside public/static roots; and
- downloads only as an attachment.

No malware-safety claim is permitted. Production deployment requires a
separate M14 malware-control decision.

If implementation would execute, render, or actively process preserved files,
it must stop with:

`M02_MALWARE_CONTROL_REQUIRED`

## 18. API contract

The bounded backend surface may include:

- create manual intake under `/api/clients/{client_id}/...`;
- create one or more upload intakes through one multipart request under the
  same client scope, returning one structured result per file;
- list client intake history;
- get one client intake;
- update permitted metadata;
- transition lifecycle;
- download one preserved source as an attachment.

The multipart upload API accepts only `.pdf`, `.xml`, `.dat`, `.csv`, and
`.xlsx`, applies the 25 MiB limit and validation independently to every file,
and preserves XML/DAT/CSV bytes in the locked encoding set without semantic
parsing. A batch response is not one lifecycle result: it contains one
correlatable result for each submitted file.

The API distinguishes a request-level batch error from per-file validation,
storage, checksum, persistence, and metadata errors. A request-level error is
returned beside per-file results only when completed or committed per-file
outcomes exist; otherwise it is returned alone. It never relabels an
uncommitted file as successful or rolls back an independently committed file.

Every response is backend-authored and includes:

- client and intake IDs;
- declared metadata;
- preservation status and safe failure code;
- source metadata when preserved;
- detected text encoding when available;
- checksum and byte size;
- duplicate and superseding indicators and safe same-client links;
- lifecycle and allowed targets;
- missing/conflicting metadata diagnostics;
- server timestamps and operational provenance.

Required error families include stable codes for:

- client/intake/source not found without foreign existence leakage;
- unsupported extension;
- file too large;
- empty file;
- MIME mismatch;
- signature/container mismatch;
- unsafe filename metadata;
- unsupported binary text or unsupported text encoding;
- invalid OOXML container;
- preservation failure;
- metadata incomplete;
- invalid lifecycle transition;
- terminal record read-only;
- invalid superseding target;
- storage unavailable.

No route accepts client ownership, storage root, storage key, absolute path,
checksum authority, lifecycle authority, or technical actor from the browser.

## 19. Frontend product contract

The M02 screen must:

- be entered from the active M01 client case;
- show the active client identity;
- provide controlled manual fields, including declared start date and declared
  product-type text, while labeling any server technical reference as
  non-account operational identity;
- allow multi-file selection with the exact accepted types and per-file 25 MiB
  limit shown before submission;
- configure the file chooser for `.pdf`, `.xml`, `.dat`, `.csv`, and `.xlsx`
  without presenting any of them as parsed in M02;
- display upload/preservation progress or pending state;
- display a separate validation, preservation, lifecycle, duplicate, and
  superseding result for every submitted file;
- display batch request errors separately from per-file validation, storage,
  checksum, persistence, and metadata errors;
- retain and continue showing completed successes when a batch-level error
  occurs;
- display stable validation and preservation failures;
- display source metadata, checksum, byte size, and timestamps;
- display duplicate and superseding candidate indications without authority
  claims;
- display lifecycle and only backend-returned actions;
- display retained rejected and superseded history;
- permit metadata correction only when backend state allows it;
- offer attachment download without exposing a storage path;
- provide no ordinary delete action;
- provide no parsing, preview, classification, ledger, or calculation action;
- return to the M01 client case.

The file input value, local path, filename, MIME, and browser checksum are never
treated as storage or authority.

## 20. Client isolation and asynchronous safety

Every intake record, source, blob, metadata operation, duplicate lookup,
superseding lookup, lifecycle mutation, download, UI state, and navigation
operation is client-scoped.

Frontend state must use the accepted:

`clientId + monotonic route-context generation`

contract. Every protected operation captures both values and may update state
from success, rejected response, caught error, and `finally` only while both
remain current.

Route activation must immediately reset all prior-client:

- intake rows and history;
- selected intake and source;
- manual form fields;
- file selection and upload draft;
- checksum and source metadata;
- duplicate/superseding indicators;
- lifecycle and allowed targets;
- diagnostics;
- progress, loading, saving, transition, and download flags;
- success and error messages.

Required deterministic behavior covers:

- foreign intake and source IDs;
- checksum matches between clients without leakage;
- A-to-B;
- A-to-B-to-A;
- stale upload success;
- stale upload error;
- stale upload `finally`;
- batch upload during A-to-B;
- one stale file completion inside a batch;
- mixed success and failure in one batch;
- stale batch-wide request error after A-to-B;
- stale batch `finally`;
- stale batch-wide `finally` after A-to-B-to-A;
- same checksum within one batch;
- duplicate against an earlier source;
- client switch during a batch;
- per-file responses arriving in an order different from file selection;
- stale lifecycle mutation;
- stale manual-intake save;
- failed B loading never falling back to A data;
- new A work succeeding after an old A request settles.

## 21. M02/M03 authority boundary

M02 may determine only:

- source bytes preserved or not preserved;
- preservation metadata present or missing;
- duplicate candidate;
- superseding candidate;
- M02 intake state;
- eligibility to enter a future M03 review.

M02 must not determine:

- that file contents are correct;
- that a source is authoritative;
- that fields inside the file are accepted;
- parser or schema validity;
- item-level acceptance;
- downstream facts;
- classification;
- ledger eligibility;
- tax, pension, capital, fixation, or calculation meaning.

`accepted_for_review` means only that the intake is ready for a future M03
source-level review. It does not mean accepted as authoritative.

## 22. Required backend work after separate authorization

The future backend package would require bounded work in:

- additive SQLAlchemy models and relationships for intake, source, and blob;
- one additive Alembic successor and migration tests;
- request/response schemas, including declared manual start/product facts,
  technical-reference boundaries, per-file batch results, and stable
  validation errors;
- M02 intake/lifecycle service;
- managed-local-storage adapter and server configuration;
- streaming checksum and byte-limit handling;
- extension, MIME, PDF, bounded text-encoding, and OOXML container validators;
- V1-aligned XML/DAT/CSV technical encoding detection without byte
  normalization or semantic parsing;
- same-client duplicate/blob reuse;
- superseding-candidate detection;
- atomic persistence and compensation cleanup;
- client-scoped list/get/update/transition/download routes;
- deterministic technical actor provenance;
- foreign-ID non-leakage and immutable/reference-retention enforcement.

This does not authorize a broad client-route refactor, object storage, broad
authentication, parsing, M03, or downstream mutation.

## 23. Required frontend work after separate authorization

The future frontend package would require bounded work in:

- M02 API types and multipart transport;
- one client-scoped M02 intake/history screen;
- route registration and an M01 navigation link;
- manual-intake and multi-file opaque-upload forms;
- visible accepted-type and size guidance;
- preservation, metadata, duplicate, superseding, and lifecycle presentation;
- attachment download action;
- retained terminal-history presentation;
- route-context reset and generation guards;
- deterministic component/integration tests;
- M01, PKG-005, and PKG-006 regression coverage.

No M03, parser, classification, ledger, or report UI is included.

## 24. Acceptance criteria

| ID | Acceptance criterion |
|---|---|
| AC-007-001 | A user can create a client-scoped manual-only intake storing `declared_start_date` and `declared_product_type` when supplied; missing/explicitly-unknown provider and missing declared account do not block save, and the server technical reference is not displayed or emitted as a real account. The intake starts in `metadata_review` and creates no source/blob or downstream fact. |
| AC-007-002 | A user can submit one or more allowed opaque files in one multipart operation; each identifiable file receives a separate intake, source, validation result, lifecycle, and structured response, with no combined blob or merged record and no content parsing. A batch-wide request failure is reported separately from per-file outcomes. |
| AC-007-003 | `.pdf`, `.xml`, `.dat`, `.csv`, and `.xlsx` up to exactly 25 MiB per file are accepted only when extension, MIME, and required signature/container/text validation agree; DAT support is V1-derived opaque preservation only. |
| AC-007-004 | XML, DAT, and CSV encoded as UTF-8, UTF-8 BOM, Windows-1255, ISO-8859-8, or Latin-1 pass bounded non-binary text validation without byte normalization; detected encoding is retained when identifiable, while empty, oversized, prohibited-extension, MIME-mismatched, invalid-signature/container, unsupported-binary, NUL-bearing, or unsupported-encoding files fail with stable errors and no successful source. |
| AC-007-005 | The backend sanitizes original filename metadata, generates an opaque relative storage key, persists no absolute path, and never overwrites by filename. |
| AC-007-006 | SHA-256 is computed over received bytes by the backend; a browser-supplied checksum cannot control the persisted digest. |
| AC-007-007 | A same-client checksum match creates a separate duplicate-candidate intake/source linked to the existing immutable blob without storing duplicate physical bytes or changing history. |
| AC-007-008 | The same checksum under a different client neither reuses the foreign blob nor exposes that a match exists. |
| AC-007-009 | A newer same-client, same-source-type declared date is shown as a superseding candidate; missing/equal dates and different source types do not create that candidate. |
| AC-007-010 | Superseding detection does not automatically transition or delete the older intake; supersession occurs only through the explicit allowed transition. |
| AC-007-011 | The backend enforces exactly the seven locked lifecycle transitions and returns stable conflicts for same-state, skipped, terminal, or otherwise invalid transitions. |
| AC-007-012 | Required metadata blocks lifecycle transitions according to the creation path and diagnostics are backend-authored; a manual-only intake may be saved and may satisfy the M02 gate without a real provider or declared account, while those omissions remain visible diagnostics and may block a future downstream package that requires them. |
| AC-007-013 | `accepted_for_review -> metadata_review` permits metadata correction without replacing bytes; rejected and superseded records remain terminal and read-only. |
| AC-007-014 | Intake history, including duplicate, rejected, and superseded records, remains visible and no ordinary delete action or route exists. |
| AC-007-015 | Upload, database, and storage failure paths are atomic per file: no success references missing bytes, failed or uncommitted file state is cleaned without partial rows or orphaned bytes, and independently committed files remain committed after per-file or request-level batch failure. A request-level error is returned alone before processing begins or beside completed per-file outcomes when they exist. |
| AC-007-016 | Download requires matching route client ID and source ID, returns attachment disposition with `nosniff`, and exposes no public URL, absolute path, or foreign existence. |
| AC-007-017 | Foreign intake/source IDs, lifecycle requests, downloads, duplicate lookups, and superseding lookups fail safely without cross-client data or checksum leakage. |
| AC-007-018 | A-to-B and A-to-B-to-A tests prove immediate reset plus rejection of stale upload/manual-save/lifecycle success, error, and `finally` effects; batch tests cover stale single-file completion, stale batch-wide request error, stale batch-wide `finally`, mixed committed/per-file-failed/request-level-failed results, same-batch checksum reuse, retry under the duplicate contract, client switching, and out-of-order responses while new-context requests still work. |
| AC-007-019 | The UI visibly presents declared manual fields, clearly non-account technical reference, multi-file selection, per-file preservation/validation results, safe errors, metadata, checksum, duplicate/superseding indications, lifecycle actions, history, and navigation using real backend state. |
| AC-007-020 | XML, DAT, CSV, and XLSX remain opaque; tests prove that encoding detection is not parser validity and that no XML/DAT schema or business parsing, CSV interpretation, workbook extraction, OCR, preview, classification, ledger mutation, or calculation occurs. |
| AC-007-021 | M02 writes do not change M01 completeness/lifecycle, PKG-005 fixation behavior, PKG-006 client-case behavior, M07/M08 evidence, or engine inputs. |
| AC-007-022 | The additive migration upgrades from `f3a7c9d2e610`, creates only the approved M02 tables/constraints/indexes, preserves all prior rows, downgrades safely, and leaves one Alembic head. |

Acceptance criteria count: `22`.

## 25. Negative acceptance criteria

| ID | Prohibited outcome |
|---|---|
| NAC-007-001 | XML or DAT parsing, schema adapters, normalized import, CSV column interpretation, workbook business extraction, or parser warnings. |
| NAC-007-002 | OCR, image intake, inline preview, or live clearinghouse retrieval. |
| NAC-007-003 | M03 source authority review, M04 classification, M05 ledger creation, or any downstream fact mutation. |
| NAC-007-004 | Tax, fixation, pension conversion, eligibility, scenario, recommendation, or report calculation. |
| NAC-007-005 | Treating preservation, technical validation, `accepted_for_review`, duplicate detection, or superseding detection as source truth or professional acceptance. |
| NAC-007-006 | Accepting an extension outside the allowlist, a file over 25 MiB, a MIME/signature mismatch, macro-enabled content, an unsafe OOXML container, unsupported binary text, NUL-bearing XML/DAT/CSV, or a text encoding outside the locked set; rejecting XML/DAT merely because it is not UTF-8 is also prohibited. |
| NAC-007-007 | Using original filename, browser path, client directory, absolute path, or browser-selected storage key for physical storage. |
| NAC-007-008 | Public/static serving, inline rendering, exposed storage paths, filename-based overwrite, or executable interpretation. |
| NAC-007-009 | Trusting a browser checksum, technical actor, manual technical reference, lifecycle status, allowed-target list, duplicate result, superseding result, or client ownership, or presenting the server technical reference as a real account or declared downstream account identifier. |
| NAC-007-010 | Cross-client blob reuse, checksum-match disclosure, foreign-ID existence leakage, or client-unscoped download. |
| NAC-007-011 | Blocking history by silently merging duplicates, overwriting an existing source, or deleting the older record or blob. |
| NAC-007-012 | Automatically marking an older intake superseded merely because a newer candidate exists. |
| NAC-007-013 | Ordinary UI/API deletion, destructive correction, physical replacement, or deletion of a referenced blob. |
| NAC-007-014 | Allowing stale A-to-B or A-to-B-to-A upload, batch, per-file completion, save, lifecycle, error, loading, progress, or `finally` effects to alter the current client. |
| NAC-007-015 | Introducing broad authentication, object storage, antivirus/DLP, a production admin process, M03 implementation, or a broad frontend/backend refactor. |
| NAC-007-016 | Claiming malware safety, production deployment/readiness, M02/M03 completion, another-package authorization, or V1/V2 parity. |

Negative acceptance criteria count: `16`.

## 26. Required future tests

### 26.1 Backend focused tests

- manual-only create, list, get, metadata update, and lifecycle behavior,
  including declared start/product fields, missing/unknown provider, missing
  declared account, and a server technical reference that is never a real
  account or downstream declared identifier;
- required-metadata diagnostics;
- single- and multi-file multipart upload with per-file preservation metadata,
  lifecycle, validation, and structured result;
- exact 25 MiB boundary, empty file, and over-limit streaming rejection;
- extension and declared MIME allowlists;
- PDF signature validation;
- XLSX OOXML identity, path, encryption, macro, and declared-size safety;
- XML/DAT/CSV UTF-8, UTF-8 BOM, Windows-1255, ISO-8859-8, Latin-1, unsupported
  binary, and NUL handling without byte normalization or semantic parsing;
- per-file atomicity for mixed success/failure, same checksum within a batch,
  duplicate against an earlier source, and response order differing from
  selection order;
- malformed multipart before processing and foreign-client failure before
  processing, each returning request-level failure only;
- request interruption before commit and request-level failure after one file
  committed;
- mixed committed, per-file-failed, and request-level-failed outcomes;
- cleanup of all uncommitted files and retention of independently committed
  files after request-level failure;
- retry after batch failure under the existing duplicate/no-overwrite contract;
- filename sanitization, generated key, path traversal, and overwrite
  prevention;
- server SHA-256 using known byte fixtures;
- browser-checksum rejection or non-use;
- same-client duplicate record plus physical blob reuse;
- same checksum for different clients without response or timing assertion that
  exposes a match;
- superseding candidate with newer, equal, missing, and different-source-type
  dates;
- all seven allowed transitions and representative invalid transitions;
- terminal read-only behavior and new-record correction path;
- rejected/superseded retention and absent delete routes;
- storage/database rollback, failed atomic placement, commit failure,
  temporary cleanup, and unreferenced-object cleanup;
- reference-protected blob deletion;
- client-scoped download, attachment headers, `nosniff`, sanitized filename,
  foreign IDs, and missing IDs;
- no `PensionHolding`, snapshot, document, M07/M08, or calculation side effect;
- deterministic operational actor and no browser actor;
- additive migration upgrade/downgrade, constraints, indexes, existing-data
  preservation, and single head.

### 26.2 Frontend focused tests

- M02 route and M01 navigation;
- manual-intake form and real API payload, including declared start/product
  fields and non-account technical-reference presentation;
- multi-file upload with allowed-type/per-file-size guidance;
- an explicit `.dat` file-chooser test proving `.dat` appears in the
  `accept`/allowlist, is selectable, is not rejected merely by extension,
  appears in the selected-file list, is submitted in a multi-file batch,
  receives a separate per-file result, remains opaque without parsing or
  semantic validation, and cannot update the new client when its completion is
  stale after A-to-B or A-to-B-to-A;
- progress, pending, success, validation failure, preservation failure, and
  cleanup presentation;
- metadata and missing-field diagnostics;
- checksum, byte size, filename, and timestamps;
- duplicate and superseding candidate presentation without authority claims;
- lifecycle actions only from backend-returned targets;
- metadata correction and terminal read-only behavior;
- retained rejected/superseded history;
- absent delete and preview actions;
- attachment download initiation without storage-path exposure;
- A-to-B immediate reset;
- A-to-B-to-A generation uniqueness;
- stale upload success, error, and `finally`;
- batch upload across A-to-B, stale single-file completion, mixed
  success/failure, stale batch `finally`, same-batch checksum, prior-source
  duplicate, client switch during batch, and out-of-order results;
- separate presentation of batch request error and per-file errors without
  deleting or hiding retained committed successes;
- malformed pre-processing batch failure, request interruption before commit,
  request-level failure after one committed file, mixed
  committed/per-file-failed/request-level-failed outcomes, retry after failure,
  stale batch-wide error after A-to-B, and stale batch-wide `finally` after
  A-to-B-to-A;
- stale lifecycle mutation and manual-save mutation;
- failed B load never showing A data;
- new A requests operating after old A settles.

### 26.3 Full verification

- relevant M01 regressions;
- PKG-005 regressions;
- PKG-006 regressions;
- full backend suite;
- full frontend suite;
- frontend production build/type-check;
- Python compile;
- Alembic single head;
- `git diff --check`.

Browser E2E must not be claimed unless actually available and executed.

## 27. Expected implementation file groups

Exact filenames must be confirmed by a later implementation authorization.
Expected bounded groups are:

- backend M02 models and model registration;
- one Alembic migration and migration tests;
- M02 request/response schemas;
- managed-local-storage/checksum/type-validation service;
- M02 intake/lifecycle/duplicate/superseding service;
- client-scoped M02 API routes and download response;
- backend focused and regression tests;
- frontend M02 API types and multipart helper;
- one M02 intake/history screen;
- M01 navigation and app route registration;
- frontend M02 deterministic tests;
- configuration example for the backend-managed storage root;
- dependency declaration only if multipart/container handling requires it.

No unrelated code, tests, acceptance records, or package definitions belong in
the implementation change set.

## 28. Explicit exclusions

- M03 source-review implementation;
- XML or DAT parsing, DAT business-structure determination, or normalized
  import;
- OCR;
- live clearinghouse integration;
- item-level parser warnings or malformed-content interpretation;
- quarantine;
- M04 classification;
- M05 ledger;
- pension/capital conversion;
- tax or fixation changes;
- scenarios;
- recommendations;
- reports;
- household modeling;
- team ownership or broad authorization;
- object storage;
- antivirus, malware sandbox, or enterprise DLP;
- exceptional admin deletion/redaction;
- production retention duration;
- public-network or production deployment;
- M09-M14 implementation;
- 02M;
- V1/V2 parity claim.

## 29. Deferred production matters

The following do not block a bounded first-stage implementation but remain
unresolved for production:

- object-storage adapter implementation and operational durability;
- backup, restore, replication, and disaster recovery for preserved bytes;
- capacity monitoring and storage quotas;
- legal retention duration;
- exceptional administrative redaction/deletion authority and tombstone
  workflow;
- production authentication and role authorization;
- malware scanning, sandboxing, DLP, and incident response;
- public-network deployment controls;
- M03 parser formats, schemas, warnings, review, and authority;
- M14 privacy and operations policy.

## 30. Stop conditions for future implementation

Stop and return to the approval gate if:

- an allowed type, 25 MiB limit, locked text-encoding set, MIME/signature rule,
  or lifecycle transition must change;
- managed local storage cannot be configured outside public/static/repository
  roots;
- only unsafe absolute paths or browser-controlled paths are available;
- implementation requires destructive reuse of an existing table;
- client-local immutable blob references cannot be enforced;
- a referenced blob could be deleted or overwritten;
- database/storage compensation cannot prevent committed missing-byte
  references;
- upload or download cannot be client-scoped without existence leakage;
- broad authentication becomes necessary;
- antivirus/malware control becomes mandatory;
- preserved files would be executed, rendered inline, or actively processed,
  requiring `M02_MALWARE_CONTROL_REQUIRED`;
- M03 parsing, review authority, M04 classification, M05 ledger, or calculation
  behavior becomes necessary to make the package work;
- existing PKG-005 or PKG-006 behavior cannot be preserved;
- a new product, professional, privacy, or retention decision is required;
- implementation authorization differs materially from this definition.

## 31. Final package gate

PKG-007 is one coherent M02 package definition. It is ready only for a separate
implementation-authorization decision.

- Definition: `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`
- Implementation: `NOT_AUTHORIZED`
- Migration execution: `NOT_AUTHORIZED`
- M03: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`
