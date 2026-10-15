# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_AUTHORITY — Final Corrected Definition

## 1. Authority, status, and boundaries

- Package: `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_AUTHORITY` (`CRTISBA`).
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Authoritative base: `ba3029089444ad083e8149993e22c475200ae94c`.
- This complete Definition supersedes earlier CRTISBA Definition text.
- CRTISBA is append-only, source-bound professional basis evidence. It does not change amounts,
  pension execution, RTISA admission, RTICB results, normalization, aggregation, funding, tax,
  allocation, or scenarios.
- Implementation, downstream work, and deployment are `NOT_AUTHORIZED`; production readiness is
  `NOT_CLAIMED`.

## 2. Preserved binding Owner Decisions

### OD-1 — pension income basis

Each current canonical pension needs an explicit `GROSS` or `NET` professional decision. Missing,
cleared, stale, or invalid evidence is `UNKNOWN`. No inference from tax treatment, product type,
labels, payer, or any other source fact is permitted.

### OD-2 — pension target-date price authority

Every successful current PTE independently exposes `NOMINAL_AT_RETIREMENT_TARGET_DATE`, null
reference date, and provenance `OWNER_DECISION_OD2`. It remains visible when OD-1 is missing or
cleared. It applies only to the exact calculated target-date amount and never to a historical/base
amount.

### OD-3 — recurring price basis

A recurring source may receive explicit `NOMINAL_AT_RETIREMENT_TARGET_DATE` with null reference
date, or `REAL_AT_REFERENCE_DATE` with one authoritative date. Missing/cleared evidence is
`UNKNOWN`. Price meaning is never inferred from source date, timestamps, start/end dates, or text.
Recurring income basis is only current `amount_basis`: gross/net/unknown maps to
`GROSS`/`NET`/`UNKNOWN`.

Identity, amount authority, income basis, price basis, provenance, admission, delegation, and
comparison readiness are separate contracts.

## 3. Accepted upstream identities and exact amount authority

CRTISBA consumes without modifying Planning Input source/planning/target identities; pension
monthly-basis and temporal semantic/source fingerprints; PTE execution/result identities; RTISA
entries, exact amounts, admission and result fingerprint; portfolio `source_entry_fingerprint`; and
the server-authenticated `trusted_professional_actor`.

Pension IDs are `manual:<id>` or `conversion:<id>`; recurring IDs are `income:<id>`. Recurring
frequencies are exactly `monthly`, `quarterly`, `annual`, and `other`. Recurring source version is
the complete current Planning Input source fingerprint, not an invented integer.

The pension amount-authority fingerprint namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_PENSION_AMOUNT_AUTHORITY_JSON_V1`. Its exact
preimage keys are `contract`, `client_id`, `source_id`, `source_version`, `source_fingerprint`,
`base_amount_semantic_fingerprint`, `base_amount_source_fingerprint`,
`temporal_semantic_fingerprint`, `temporal_source_fingerprint`,
`planning_calculation_input_fingerprint`, `retirement_target_date`,
`pension_source_execution_fingerprint`, `pension_source_result_fingerprint`,
`portfolio_source_entry_fingerprint`, and `amount`. `amount` is the object:

```json
{"numerator":"<RTISA monthly_equivalent.numerator>","denominator":"1","currency":"ILS","frequency":"MONTHLY"}
```

The numerator must also equal portfolio `source_unquantized_target_monthly_amount`; rounded display
amounts are forbidden.

The recurring namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RECURRING_AMOUNT_AUTHORITY_JSON_V1`; exact
preimage keys are `contract`, `client_id`, `source_id`, `source_fingerprint`, exact `amount`,
`amount_basis`, and `frequency`.

For `frequency=other`, RTISA remains unresolved with null monthly equivalent and
`RTISA_SOURCE_FREQUENCY_UNSUPPORTED`. A price decision may be stored, but CRTISBA state remains
`UPSTREAM_UNRESOLVED`, readiness false, and comparison readiness false. No monthly amount is
invented.

## 4. RTISA delegation and excluded sources

CRTISBA consumes RTISA output and never reinterprets raw `PensionIncomeResolution` rows.

Both underlying decisions `SAME_CANONICAL_PENSION` and `PENSION_NOT_YET_CANONICAL` may validly
produce the same accepted RTISA output:

| Exact RTISA evidence | CRTISBA state | Blocker | Standalone write |
|---|---|---|---|
| `EXCLUDED`, `DELEGATED_TO_CANONICAL`, `RTISA_SAME_CANONICAL_PENSION` | `NOT_APPLICABLE_DELEGATED` | none | forbidden |
| `UNRESOLVED`, `RTISA_SOURCE_IDENTITY_UNRESOLVED` | `DELEGATION_UNRESOLVED` | `RTISA_SOURCE_IDENTITY_UNRESOLVED` | forbidden |
| `UNRESOLVED`, `RTISA_SOURCE_IDENTITY_STALE` | `DELEGATION_STALE` | `RTISA_SOURCE_IDENTITY_STALE` | forbidden |

No other delegation state or invented RTISA code exists. Valid delegation is universe-complete,
non-counted, non-blocking, and has no independent decision.

An ordinary, non-delegated RTISA source excluded as future or ended is
`NOT_APPLICABLE_NOT_ADMITTED`. It is universe-complete, non-counted, non-blocking, and ineligible
for a standalone CRTISBA decision. It remains distinct from `NOT_APPLICABLE_DELEGATED`.

## 5. Exact persistence and named constraints

One additive migration creates `retirement_target_date_income_source_basis_decisions` with exactly
these columns; no additional current-pointer or compatibility authority column is permitted:

| Column | PostgreSQL type | Null/default |
|---|---|---|
| `decision_id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | primary key, non-null |
| `client_id` | `INTEGER` | non-null, no default |
| `source_id` | `VARCHAR(128)` | non-null, no default |
| `source_kind` | `VARCHAR(32)` | non-null, no default |
| `decision_version` | `BIGINT` | non-null, no default |
| `planning_calculation_input_fingerprint` | `VARCHAR(64)` | non-null, no default |
| `pension_source_version` | `INTEGER` | pension non-null; recurring null |
| `recurring_source_version_fingerprint` | `VARCHAR(64)` | recurring non-null; pension null |
| `source_fingerprint` | `VARCHAR(64)` | non-null, no default |
| `amount_authority_fingerprint` | `VARCHAR(64)` | non-null, no default |
| `pension_source_execution_fingerprint` | `VARCHAR(64)` | pension non-null; recurring null |
| `pension_source_result_fingerprint` | `VARCHAR(64)` | pension non-null; recurring null |
| `portfolio_source_entry_fingerprint` | `VARCHAR(64)` | pension non-null; recurring null |
| `retirement_target_date` | `DATE` | pension non-null; recurring null |
| `income_basis` | `VARCHAR(16)` | non-null |
| `income_basis_provenance` | `VARCHAR(40)` | non-null |
| `price_basis` | `VARCHAR(64)` | non-null |
| `price_reference_date` | `DATE` | real recurring only; otherwise null |
| `price_basis_provenance` | `VARCHAR(40)` | non-null |
| `decision_actor` | `VARCHAR(128)` | non-null; authenticated server actor |
| `decided_at` | `TIMESTAMP WITH TIME ZONE` | non-null; `transaction_timestamp()` |
| `decision_fingerprint` | `VARCHAR(64)` | non-null, no default |

`decision_id` is generated only by PostgreSQL identity. `decision_actor` is copied only from
`request.state.trusted_professional_actor`; the body cannot supply it. `decided_at` is database
transaction time, never application clock or client input.

The exact database object inventory is:

- primary key `pk_crtisba_decisions`;
- FK `fk_crtisba_decision_client` to `clients.client_id` with `ON DELETE RESTRICT`;
- unique `uq_crtisba_source_decision_version` on
  `(client_id, source_kind, source_id, decision_version)`;
- index `ix_crtisba_source_latest_version` on the same identity and descending version;
- checks `ck_crtisba_decision_version_positive`, `ck_crtisba_source_kind`,
  `ck_crtisba_source_identity_shape`, `ck_crtisba_income_basis`,
  `ck_crtisba_income_basis_provenance`, `ck_crtisba_price_basis`,
  `ck_crtisba_price_basis_provenance`, `ck_crtisba_kind_payload`,
  `ck_crtisba_reference_date`, and `ck_crtisba_hash_shapes`;
- trigger `trg_crtisba_decision_immutable`, backed by
  `reject_crtisba_decision_mutation()`, rejecting every ordinary UPDATE and DELETE. The trigger
  raises SQLSTATE `P7501` and diagnostic `CONSTRAINT_NAME=trg_crtisba_decision_immutable` with
  `RAISE EXCEPTION USING ERRCODE='P7501', CONSTRAINT='trg_crtisba_decision_immutable', MESSAGE='CRTISBA_DECISION_IMMUTABLE'`;
  message text is not diagnostic authority.

First write requires expected decision version 0, proves no row exists, and inserts version 1.
Later writes lock/select the unique maximum version, require exact CAS, and insert expected+1.
Maximum version is `9223372036854775807`; the next append fails
`CRTISBA_DECISION_VERSION_EXHAUSTED`. There is no current-pointer column. Application access is
SELECT/INSERT only. Pension rows store OD-1 only; OD-2 is derived from current PTE. Recurring rows
store OD-3. Clear appends `UNKNOWN` only for the stored decision.

The application database role receives only table `SELECT` and `INSERT`, plus `USAGE, SELECT` on
the identity sequence generated for `decision_id`. It receives no `UPDATE`, `DELETE`, `TRUNCATE`,
`TRIGGER`, ownership, or function-alter privilege. Migration ownership remains separate. Trigger
enforcement remains mandatory defense even when grants are correct.

## 6. Transaction ownership and concurrency

### 6.1 Admission and read

Before any authoritative query, a public CRTISBA owner requires a pristine Session: no active
transaction and no pending `new`, `dirty`, or `deleted` state. Read owns one PostgreSQL
`REPEATABLE READ READ ONLY` transaction and uses non-owning internal derivation functions for
Planning, PTE, portfolio and RTISA. No public transaction owner, second Session, nested begin,
commit, rollback, or retry may be invoked by a nested producer. A GET never commits.

The exact read-cleanup matrix is:

| Point reached | Outcome | Required termination |
|---|---|---|
| pristine admission rejects before transaction acquisition | failure | no rollback, invalidate, or close by CRTISBA |
| transaction acquisition or isolation setup started, then fails | failure | rollback if transaction exists; release Session after successful rollback |
| transaction acquired and derivation succeeds | success | rollback exactly once to terminate READ ONLY snapshot, then release Session |
| transaction acquired and derivation fails | failure | rollback exactly once, then release Session |
| any required read rollback fails | failure | preserve `CRTISBA_ROLLBACK_FAILED`, invalidate captured connection, close Session |

“Release” means returning the successfully rolled-back Session to the request dependency's normal
close path. A failed/invalidate/closed Session is never reused. No rollback occurs before a
transaction has actually been acquired.

### 6.2 Write

After strict DTO validation and before any authoritative query, write establishes PostgreSQL
`SERIALIZABLE`. It then:

1. reads the current client/global Planning identity;
2. locks the addressed source row `FOR UPDATE` in exactly one table:
   `recurring_income`, `canonical_manual_pension_sources`, or
   `canonical_pension_destinations`;
3. locks the latest CRTISBA decision row when present;
4. re-derives all authoritative Planning/source/amount/PTE/portfolio/RTISA identities in the same
   Session and transaction through non-owning internal functions;
5. applies planning, source, amount, and decision CAS;
6. inserts, flushes, and commits once.

No safety claim depends on upstream writers taking a CRTISBA advisory lock.

Addressed-source mutation visible before lock/revalidation rejects the stale write. If the decision
serializes first, a later source update makes it stale on the next read. For an unrelated Planning
contributor, a change visible in the snapshot rejects
`expected_planning_calculation_input_fingerprint`; a change
serialized later makes the accepted decision stale on the next read. An overlapping transaction may
instead produce PostgreSQL serialization abort. There is no automatic retry. The successful
PostgreSQL serial order, not wall-clock response order, is the linearization authority.

## 7. Closed database-failure contract

Implementation tracks phases `BEFORE_TRANSACTION`, `IN_TRANSACTION`, `FLUSHING`,
`FLUSHED`, `COMMIT_DISPATCHED`, `COMMITTED`, `ROLLING_BACK`, and `CLOSED`. The
`COMMIT_DISPATCHED` transition occurs immediately before calling `Session.commit()`.

SQLSTATE is extracted from `exc.orig.pgcode`, then `exc.orig.sqlstate`. The exhaustive
known-abort set is `40001`, `40P01`, `23503`, `23505`, `23514`, and `25P02`. A cancellation,
disconnect, missing SQLSTATE, or any other post-dispatch exception is not presumed to prove abort.

Trigger immutability is recognized only when both `pgcode == "P7501"` and
`exc.orig.diag.constraint_name == "trg_crtisba_decision_immutable"`. Ordinary check violations are
recognized by SQLSTATE `23514` plus membership in the closed set
`{ck_crtisba_decision_version_positive, ck_crtisba_source_kind,
ck_crtisba_source_identity_shape, ck_crtisba_income_basis,
ck_crtisba_income_basis_provenance, ck_crtisba_price_basis,
ck_crtisba_price_basis_provenance, ck_crtisba_kind_payload,
ck_crtisba_reference_date, ck_crtisba_hash_shapes}`. Neither classifier inspects exception text.

- A failure before commit dispatch is known not committed.
- A commit exception with intact connection and a known-abort SQLSTATE is known not committed.
- A named CRTISBA constraint maps as specified in Section 10 and is known not committed.
- Normal return from commit is committed.
- After commit dispatch, `connection_invalidated=true`, SQLSTATE class `08`, absent SQLSTATE, or any
  evidence not proving a known abort is `CRTISBA_COMMIT_OUTCOME_UNKNOWN`.
- Known-not-committed failures attempt rollback. Rollback failure takes precedence as
  `CRTISBA_ROLLBACK_FAILED`, then the connection is invalidated and Session closed.
- Uncertain outcome remains uncertain even if best-effort rollback succeeds. Connection is
  invalidated and Session closed. It must be reconciled by an explicit authenticated GET using the
  same expected identities; it is never replayed.
- No failed, invalidated, or closed Session is reused. No database failure is automatically retried.

## 8. Exact commands and response schemas

All models are strict: extra keys and coercion are forbidden; boolean is not integer. Path
`client_id` and `source_id` are not body keys. Hashes are lowercase 64 hex.

### 8.1 Positive commands

The decision route is exactly
`PUT /api/clients/{client_id}/retirement-income-readiness/source-bases/{source_id}`.
`CRTISBA_PENSION_CLASSIFY_COMMAND_V1` has exactly:

```text
schema_version: literal "CRTISBA_PENSION_CLASSIFY_COMMAND_V1"
operation: literal "CLASSIFY"
source_kind: literal "PENSION"
expected_decision_version: integer 0..9223372036854775807
expected_planning_calculation_input_fingerprint: sha256
expected_source_version: integer >= 1
expected_source_fingerprint: sha256
expected_amount_authority_fingerprint: sha256
income_basis: "GROSS" | "NET"
```

`CRTISBA_RECURRING_CLASSIFY_COMMAND_V1` has exactly:

```text
schema_version: literal "CRTISBA_RECURRING_CLASSIFY_COMMAND_V1"
operation: literal "CLASSIFY"
source_kind: literal "RECURRING_INCOME"
expected_decision_version: integer 0..9223372036854775807
expected_planning_calculation_input_fingerprint: sha256
expected_source_version: sha256 string exactly equal to expected_source_fingerprint
expected_source_fingerprint: sha256
expected_amount_authority_fingerprint: sha256
price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE"
price_reference_date: null for NOMINAL; canonical ISO date for REAL
```

Pension price fields and recurring income-basis fields are forbidden.

### 8.2 Clear commands

`CRTISBA_PENSION_CLEAR_COMMAND_V1` has exactly:

```text
schema_version: literal "CRTISBA_PENSION_CLEAR_COMMAND_V1"
operation: literal "CLEAR"
source_kind: literal "PENSION"
expected_decision_version: integer 0..9223372036854775807
expected_planning_calculation_input_fingerprint: sha256
expected_source_version: integer >= 1
expected_source_fingerprint: sha256
expected_amount_authority_fingerprint: sha256
```

`CRTISBA_RECURRING_CLEAR_COMMAND_V1` has exactly:

```text
schema_version: literal "CRTISBA_RECURRING_CLEAR_COMMAND_V1"
operation: literal "CLEAR"
source_kind: literal "RECURRING_INCOME"
expected_decision_version: integer 0..9223372036854775807
expected_planning_calculation_input_fingerprint: sha256
expected_source_version: sha256 string exactly equal to expected_source_fingerprint
expected_source_fingerprint: sha256
expected_amount_authority_fingerprint: sha256
```

All classification/reference keys are forbidden in either clear command.

### 8.3 Write result

`CRTISBA_WRITE_RESULT_V1` has exactly:

```text
schema_version: literal "CRTISBA_WRITE_RESULT_V1"
client_id: positive integer
source_id: canonical non-empty string
source_kind: "PENSION" | "RECURRING_INCOME"
decision_version: integer 1..9223372036854775807
decision_state: "CURRENT" | "UNKNOWN"
planning_calculation_input_fingerprint: sha256
source_version: positive integer for PENSION; sha256 string for RECURRING_INCOME
source_fingerprint: sha256
amount_authority_fingerprint: sha256
decision_fingerprint: sha256
income_basis: "GROSS" | "NET" | "UNKNOWN"
income_basis_provenance: "EXPLICIT_PROFESSIONAL" | "UPSTREAM_RECURRING_AMOUNT_BASIS" | "MISSING"
price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE" | "UNKNOWN"
price_reference_date: canonical ISO date | null
price_basis_provenance: "OWNER_DECISION_OD2" | "EXPLICIT_PROFESSIONAL" | "MISSING"
```

It contains no actor or timestamp.

### 8.4 Collection and entry

The collection route is exactly
`GET /api/clients/{client_id}/retirement-income-readiness/source-bases`.
`CRTISBA_COLLECTION_RESULT_V1` has exactly:

```text
schema_version: literal "CRTISBA_COLLECTION_RESULT_V1"
client_id: positive integer
planning_calculation_input_fingerprint: sha256
retirement_target_date: canonical ISO date | null
rtisa_admission_result_fingerprint: sha256
source_basis_entries: ordered array of CRTISBA_SOURCE_BASIS_ENTRY_V1 objects
partitions: exact partition object defined below
blockers: sorted unique array of non-empty strings
basis_readiness_state: "READY" | "NOT_READY"
basis_ready: boolean exactly equivalent to basis_readiness_state == "READY"
result_fingerprint: sha256
```

Each `CRTISBA_SOURCE_BASIS_ENTRY_V1` object has exactly:

```text
schema_version: literal "CRTISBA_SOURCE_BASIS_ENTRY_V1"
source_id: canonical non-empty string
source_kind: "PENSION" | "RECURRING_INCOME"
source_category: accepted RTISA source_category string
admission_state: "INCLUDED" | "EXCLUDED" | "UNRESOLVED"
rtisa_reason_codes: sorted unique array of accepted RTISA strings
source_version: positive integer | sha256 string | null
source_fingerprint: sha256
amount_authority_fingerprint: sha256 | null
decision_version: integer 1..9223372036854775807 | null
decision_fingerprint: sha256 | null
decision_state: "CURRENT" | "MISSING" | "UNKNOWN" | "STALE" | "INVALID" |
                "UPSTREAM_UNRESOLVED" | "NOT_APPLICABLE_DELEGATED" |
                "DELEGATION_UNRESOLVED" | "DELEGATION_STALE" |
                "NOT_APPLICABLE_NOT_ADMITTED"
income_basis: "GROSS" | "NET" | "UNKNOWN" | null
income_basis_provenance: "EXPLICIT_PROFESSIONAL" | "UPSTREAM_RECURRING_AMOUNT_BASIS" |
                         "MISSING" | null
price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE" | "UNKNOWN" | null
price_reference_date: canonical ISO date | null
price_basis_provenance: "OWNER_DECISION_OD2" | "EXPLICIT_PROFESSIONAL" | "MISSING" | null
blockers: sorted unique array of non-empty strings
```

Partitions have exactly sorted unique arrays: `current`, `missing`, `unknown`, `stale`, `invalid`,
`upstream_unresolved`, `not_applicable_delegated`, `not_applicable_not_admitted`,
`delegation_unresolved`, and `delegation_stale`.

State-specific values are binding:

| State | Decision identity | Effective basis values | Blockers |
|---|---|---|---|
| `CURRENT` | non-null version/fingerprint | current pension OD-1+OD-2 or recurring income+OD-3 | empty |
| `MISSING` | both null | pension income UNKNOWN/MISSING with current OD-2; recurring current income with price UNKNOWN/MISSING | `CRTISBA_DECISION_MISSING` |
| `UNKNOWN` | both non-null | pension income UNKNOWN/MISSING with current OD-2; recurring current income with price UNKNOWN/MISSING | `CRTISBA_DECISION_UNKNOWN` |
| `STALE` | both non-null | same safe effective values as MISSING; stale stored choice is not exposed as current | `CRTISBA_DECISION_STALE` |
| `INVALID` | nullable only if row identity cannot be trusted | same safe effective values as MISSING | `CRTISBA_DECISION_INVALID` |
| `UPSTREAM_UNRESOLVED` | nullable; may be non-null for stored frequency-other price decision | recurring income/price may be shown only as current evidence, never comparison-ready | exact accepted RTISA reasons |
| `NOT_APPLICABLE_DELEGATED` | both null | all basis/provenance/reference fields null | empty |
| `DELEGATION_UNRESOLVED` | both null | all basis/provenance/reference fields null | `RTISA_SOURCE_IDENTITY_UNRESOLVED` |
| `DELEGATION_STALE` | both null | all basis/provenance/reference fields null | `RTISA_SOURCE_IDENTITY_STALE` |
| `NOT_APPLICABLE_NOT_ADMITTED` | both null | all basis/provenance/reference fields null | empty |

Delegated/not-admitted entries have null amount-authority fingerprint because CRTISBA does not
authorize an amount decision for them. History persistence has no public API.

### 8.5 Professional blocked result

`CRTISBA_BLOCK_NO_RESULT_V1` has exactly:

```text
schema_version: literal "CRTISBA_BLOCK_NO_RESULT_V1"
result_state: literal "block_no_result"
client_id: positive integer
source_id: canonical string | null
operation: "READ" | "CLASSIFY" | "CLEAR"
failure_stage: closed enum below
failure_detail_code: closed stage-specific enum below
field_paths: sorted unique array of JSON-pointer strings
observed_planning_calculation_input_fingerprint: sha256 | null
observed_source_version: positive integer | sha256 string | null
observed_source_fingerprint: sha256 | null
observed_amount_authority_fingerprint: sha256 | null
observed_decision_version: integer 0..9223372036854775807 | null
failure_fingerprint: sha256
```

The only professional stage/code combinations are:

| `failure_stage` | Permitted `failure_detail_code` |
|---|---|
| `planning_context` | `CRTISBA_PLANNING_CONTEXT_UNAVAILABLE` |
| `retirement_target` | `CRTISBA_RETIREMENT_TARGET_NOT_READY` |
| `pension_portfolio` | `CRTISBA_PENSION_PORTFOLIO_NOT_READY` |
| `source_universe` | `CRTISBA_SOURCE_UNIVERSE_UNAVAILABLE` |

Observed values remain null until validated by the failing stage. A blocked result contains no
partial collection. Malformed producer objects, client mismatch, and database failures are
transport errors, not professional blocked results.

## 9. Canonical serialization and fingerprints

Canonical JSON is UTF-8, sorted keys, compact separators, `ensure_ascii=false`, `allow_nan=false`,
and no Unicode normalization. Decimal is a plain exact base-10 string without exponent, grouping,
plus sign, or float conversion. It is exactly Python `format(value, "f")`, preserving the accepted
Decimal coefficient and scale (for example `3000.00` remains `3000.00`). Date is strict
`YYYY-MM-DD`. Fingerprinted result values are JSON objects,
never JSON strings containing objects.

Decision namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_DECISION_JSON_V1`. Exact preimage keys are
`contract`, `client_id`, `source_id`, `source_kind`, `decision_version`,
`planning_calculation_input_fingerprint`, `source_version`, `source_fingerprint`,
`amount_authority_fingerprint`, `income_basis`, `income_basis_provenance`, `price_basis`,
`price_reference_date`, and `price_basis_provenance`. Actor/time and derived OD-2 are excluded.

Result namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1`; preimage is exactly
`{"contract":<namespace>,"result":<complete collection object without result_fingerprint>}`.

Failure namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_FAILURE_JSON_V1`; exact preimage keys are
`contract`, `client_id`, `source_id`, `operation`, `failure_stage`, `failure_detail_code`,
`field_paths`, `observed_planning_calculation_input_fingerprint`, `observed_source_version`,
`observed_source_fingerprint`, `observed_amount_authority_fingerprint`, and
`observed_decision_version`. Different decision versions may change fingerprints. Golden vectors
freeze every preimage and serialization rule.

## 10. Closed RTDIR transport contract

Every transport error is exact `RTDIR_TRANSPORT_ERROR_V1` with keys `schema_version`, `code`,
Hebrew catalogue `message`, sorted `field_paths`, and `request_id`; headers are exactly
`Cache-Control: no-store, private` and `Pragma: no-cache`. Authentication, Origin, CSRF, edge,
unknown-route and method failures remain owned by existing RTDIR middleware.

Message selection is fixed: `CLIENT_NOT_FOUND` uses the existing named Hebrew catalogue message
`הלקוח לא נמצא`; every new `CRTISBA_*` code, `REQUEST_SCHEMA_INVALID`,
`PRODUCER_RESPONSE_INVALID`, `RESPONSE_CLIENT_MISMATCH`, and `INTERNAL_ERROR` uses the accepted
generic fallback `לא ניתן להשלים את הבקשה` unless that exact code already has a named immutable
RTDIR catalogue entry. There is no route-local or discretionary message selection.

Precedence is middleware security, request schema, pristine-session/database admission, client,
source existence/currentness/kind, planning CAS, source/amount CAS, delegation/admission,
decision CAS/ceiling, insert/flush/commit. First failure wins.

| Operation | Original condition/code | Public code | HTTP | Exact field_paths | Retry |
|---|---|---|---:|---|---|
| GET/PUT | Pydantic/path validation | `REQUEST_SCHEMA_INVALID` | 422 | exact RTDIR pointers | corrected request only |
| GET/PUT | client absent | `CLIENT_NOT_FOUND` | 404 | `/path/client_id` | no |
| PUT | source absent | `CRTISBA_SOURCE_NOT_FOUND` | 404 | `/path/source_id` | refresh only |
| PUT | source not current | `CRTISBA_SOURCE_NOT_CURRENT` | 409 | `/path/source_id` | refresh only |
| PUT | kind mismatch | `CRTISBA_SOURCE_KIND_MISMATCH` | 409 | `/source_kind` | corrected request |
| PUT | delegated or ordinary excluded source | `CRTISBA_SOURCE_DECISION_FORBIDDEN` | 409 | `/path/source_id` | no |
| GET/PUT | non-pristine Session | `CRTISBA_REQUIRES_FRESH_TRANSACTION` | 503 | empty | new request |
| GET/PUT | non-PostgreSQL production DB | `CRTISBA_UNSUPPORTED_DATABASE` | 503 | empty | no |
| PUT | `expected_planning_calculation_input_fingerprint` mismatch | `CRTISBA_PLANNING_IDENTITY_STALE` | 409 | `/expected_planning_calculation_input_fingerprint` | explicit refresh |
| PUT | source version mismatch | `CRTISBA_SOURCE_VERSION_STALE` | 409 | `/expected_source_version` | explicit refresh |
| PUT | source fingerprint mismatch | `CRTISBA_SOURCE_FINGERPRINT_STALE` | 409 | `/expected_source_fingerprint` | explicit refresh |
| PUT | amount fingerprint mismatch | `CRTISBA_AMOUNT_AUTHORITY_STALE` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | amount unavailable | `CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | amount invalid | `CRTISBA_AMOUNT_AUTHORITY_INVALID` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | decision CAS mismatch or `uq_crtisba_source_decision_version` | `CRTISBA_DECISION_VERSION_CONFLICT` | 409 | `/expected_decision_version` | explicit refresh |
| PUT | BIGINT ceiling | `CRTISBA_DECISION_VERSION_EXHAUSTED` | 409 | `/expected_decision_version` | no |
| PUT | `fk_crtisba_decision_client` | `CLIENT_NOT_FOUND` | 404 | `/path/client_id` | no |
| PUT | `pk_crtisba_decisions` | `CRTISBA_PERSISTENCE_IDENTITY_CONFLICT` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_decision_version_positive` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_source_kind` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_source_identity_shape` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_income_basis` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_income_basis_provenance` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_price_basis` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_price_basis_provenance` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_kind_payload` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_reference_date` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `23514`, `ck_crtisba_hash_shapes` | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `P7501` plus `diag.constraint_name=trg_crtisba_decision_immutable` | `CRTISBA_PERSISTENCE_IMMUTABILITY_VIOLATION` | 500 | empty | no |
| PUT | SQLSTATE `40001` or `40P01` | `CRTISBA_SERIALIZATION_FAILURE` | 503 | empty | no automatic retry |
| GET/PUT | connection/database before commit dispatch | `CRTISBA_DATABASE_FAILURE` | 503 | empty | new request only |
| PUT | flush failure | `CRTISBA_FLUSH_FAILED` | 503 | empty | no automatic retry |
| PUT | proved known-abort commit failure | `CRTISBA_COMMIT_FAILED` | 503 | empty | no automatic retry |
| PUT | unproved outcome after commit dispatch | `CRTISBA_COMMIT_OUTCOME_UNKNOWN` | 503 | empty | GET reconciliation only |
| GET/PUT | rollback failure | `CRTISBA_ROLLBACK_FAILED` | 503 | empty | new Session/request |
| GET/PUT | malformed producer object | `PRODUCER_RESPONSE_INVALID` | 500 | empty | no |
| GET/PUT | producer client mismatch | `RESPONSE_CLIENT_MISMATCH` | 500 | empty | no |
| GET/PUT | fingerprint or unexpected program failure | `INTERNAL_ERROR` | 500 | empty | no |

Professional non-readiness—missing/unknown/stale decisions, unresolved frequency, RTISA unresolved
identity and stale delegation—returns HTTP 200 in `CRTISBA_COLLECTION_RESULT_V1`, never an RTDIR
transport error.

## 11. Executable acceptance contract

Ordinary production-path tests must prove: both valid delegation decision kinds produce the exact
RTISA valid code/state; the two exact unresolved/stale codes; ordinary future/ended excluded state;
pristine Session rejection; SERIALIZABLE is established before the first authoritative statement;
each of the three exact source-table locks; latest-decision lock; non-owning nested derivation;
addressed and unrelated Planning races; observed source version in failures; every schema literal,
key/type/null rule; recurring SHA version; Decimal/date/golden fingerprints; every named constraint
mapping; `CRTISBA_SOURCE_NOT_CURRENT`; all known/uncertain commit classes; connection loss before
and after dispatch; explicit uncertain-outcome reconciliation; and forbidden OD-1/OD-3 inference.

The ordinary matrix additionally proves the exact GET and PUT route registrations; successful GET
rollback/release with zero commit calls; GET derivation failure rollback; GET rollback failure with
connection invalidation, Session closure and non-reuse; no rollback before acquisition; every
state-specific entry value/null rule; all four closed professional stage/code pairs; database actor
and transaction timestamp provenance; SELECT/INSERT-only application-role grants including identity
sequence access; and every Section 10 message, pointer, envelope and cache mapping.

Risk-scoped mutations require unchanged ordinary PASS, reached production mutation, same oracle
FAIL, guaranteed restoration, and same oracle PASS. Required groups are RTISA state mapping;
excluded-source mapping; pristine admission; isolation-before-query; each polymorphic lock target;
post-lock/global planning revalidation; nested transaction ownership; DTO discriminators;
serialization/preimage fields; named constraints/immutability; SQLSTATE/commit-dispatch classifier;
no-retry; transport mapping; forbidden pension inference; forbidden recurring inference.

The trigger mutation group must prove structured extraction of SQLSTATE `P7501` and
`diag.constraint_name`, and that changing either diagnostic makes the unchanged public oracle fail.
A separate check-constraint oracle must raise `23514` with the exact check name and prove it cannot
be misclassified as immutability. The read-termination group mutates success rollback into commit,
removes failure rollback, and suppresses invalidation after rollback failure; each unchanged oracle
must fail and pass after restoration.

Real isolated PostgreSQL must prove migration upgrade/downgrade and one head; all named objects;
trigger enforcement; first insert/CAS/ceiling; concurrent version uniqueness; all three row locks;
addressed-source and unrelated-Planning race orderings; `40001`/`40P01`; connection loss before and
after commit dispatch; known versus uncertain outcome; rollback failure/invalidation; explicit GET
reconciliation; snapshot consistency; and no upstream mutation. SQLite is limited to pure DTO,
mapping, fingerprint, ordering, and ordinary behavior.

PostgreSQL role evidence queries `information_schema.role_table_grants` and sequence privileges,
then attempts SELECT, INSERT, UPDATE, DELETE and TRUNCATE under the application role. Only SELECT,
INSERT and identity-sequence use may succeed. It also proves `decision_actor` is the trusted server
actor and `decided_at` is the PostgreSQL transaction timestamp, not supplied values.

## 12. Consolidated consistency and blocker closure

| Blocker | Corrected binding | Ordinary | Mutation | PostgreSQL | Status |
|---|---|---|---|---|---|
| DEF-001 | Sections 2–3 preserved | required | required | identity | CLOSED |
| DEF-002 | Section 3 preserved | required | required | CAS | CLOSED |
| DEF-003 | Sections 2–3 preserved | required | required | not required for mapping | CLOSED |
| DEF-004 | Section 4 exact RTISA codes | complete | mapping group | persisted resolution | CLOSED |
| DEF-005 | Section 6 serializable contract | complete | lock/isolation groups | required | CLOSED |
| DEF-006 | Section 7 closed classifier | complete | phase/classifier groups | required | CLOSED |
| DEF-007 | Sections 8–9 exact contracts | complete | DTO/fingerprint groups | stored vectors | CLOSED |
| DEF-008 | Section 10 exact RTDIR table | complete | transport groups | DB rows | CLOSED |
| DEF-009 | Section 11 executable matrices | complete | complete | complete | CLOSED |

No clause authorizes reinterpretation of raw delegation rows, inference forbidden by OD-1/OD-3,
nested transaction ownership, automatic retry, or upstream writer changes. Stop rather than invent
authority if an accepted producer lacks a required identity, actual source row cannot be locked, or
accepted upstream semantics would need change. No additional Owner Decision is required.

`02M=FROZEN`; `M08E=EXCLUDED`; `M11-M14=NOT_AUTHORIZED`.

Definition status: `READY_FOR_INDEPENDENT_DEFINITION_ACCEPTANCE_AUDIT`.

Implementation = `NOT_AUTHORIZED`.
Downstream = `NOT_AUTHORIZED`.
Production readiness = `NOT_CLAIMED`.
