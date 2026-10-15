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

## 5. Persistence and named constraints

One additive migration creates `retirement_target_date_income_source_basis_decisions`. It has an
immutable surrogate `decision_id`, client/source identity, `decision_version BIGINT`, bound
planning/source/amount identities, decision/provenance fields, server actor, database transaction
timestamp, and decision fingerprint.

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
  `reject_crtisba_decision_mutation()`, rejecting every ordinary UPDATE and DELETE.

First write requires expected decision version 0, proves no row exists, and inserts version 1.
Later writes lock/select the unique maximum version, require exact CAS, and insert expected+1.
Maximum version is `9223372036854775807`; the next append fails
`CRTISBA_DECISION_VERSION_EXHAUSTED`. There is no current-pointer column. Application access is
SELECT/INSERT only. Pension rows store OD-1 only; OD-2 is derived from current PTE. Recurring rows
store OD-3. Clear appends `UNKNOWN` only for the stored decision.

## 6. Transaction ownership and concurrency

### 6.1 Admission and read

Before any authoritative query, a public CRTISBA owner requires a pristine Session: no active
transaction and no pending `new`, `dirty`, or `deleted` state. Read owns one PostgreSQL
`REPEATABLE READ READ ONLY` transaction and uses non-owning internal derivation functions for
Planning, PTE, portfolio and RTISA. No public transaction owner, second Session, nested begin,
commit, rollback, or retry may be invoked by a nested producer.

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
contributor, a change visible in the snapshot rejects the expected planning fingerprint; a change
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

`CRTISBA_PENSION_CLASSIFY_COMMAND_V1` exact keys/types:

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

`CRTISBA_RECURRING_CLASSIFY_COMMAND_V1` replaces the last two pension-specific lines with:

```text
source_kind: literal "RECURRING_INCOME"
expected_source_version: sha256 string exactly equal to expected_source_fingerprint
price_basis: "NOMINAL_AT_RETIREMENT_TARGET_DATE" | "REAL_AT_REFERENCE_DATE"
price_reference_date: null for NOMINAL; canonical ISO date for REAL
```

It otherwise has the same common expected fields. Pension price fields and recurring income-basis
fields are forbidden.

### 8.2 Clear commands

`CRTISBA_PENSION_CLEAR_COMMAND_V1` and `CRTISBA_RECURRING_CLEAR_COMMAND_V1` contain exactly:
`schema_version`, `operation="CLEAR"`, `source_kind`, `expected_decision_version`,
`expected_planning_calculation_input_fingerprint`, `expected_source_version`,
`expected_source_fingerprint`, and `expected_amount_authority_fingerprint`. Version types follow the
positive variant. All classification/reference keys are forbidden.

### 8.3 Write result

`CRTISBA_WRITE_RESULT_V1` exact keys are: `schema_version`, positive `client_id`, canonical
`source_id`, `source_kind`, positive `decision_version`, `decision_state` (`CURRENT|UNKNOWN`),
planning fingerprint, source version (positive integer pension; SHA string recurring), source
fingerprint, amount fingerprint, decision fingerprint, `income_basis`,
`income_basis_provenance`, `price_basis`, nullable ISO `price_reference_date`, and
`price_basis_provenance`. It contains no actor or timestamp.

### 8.4 Collection and entry

`CRTISBA_COLLECTION_RESULT_V1` exact keys are `schema_version`, `client_id`,
`planning_calculation_input_fingerprint`, nullable ISO `retirement_target_date`,
`rtisa_admission_result_fingerprint`, `source_basis_entries`, `partitions`, `blockers`,
`basis_readiness_state`, `basis_ready`, and `result_fingerprint`.

Each `CRTISBA_SOURCE_BASIS_ENTRY_V1` object has exactly `schema_version`, `source_id`,
`source_kind`, `source_category`, `admission_state`, sorted `rtisa_reason_codes`, `source_version`,
`source_fingerprint`, nullable `amount_authority_fingerprint`, nullable `decision_version`, nullable
`decision_fingerprint`, `decision_state`, nullable `income_basis`, nullable
`income_basis_provenance`, nullable `price_basis`, nullable `price_reference_date`, nullable
`price_basis_provenance`, and sorted `blockers`.

Partitions have exactly sorted unique arrays: `current`, `missing`, `unknown`, `stale`, `invalid`,
`upstream_unresolved`, `not_applicable_delegated`, `not_applicable_not_admitted`,
`delegation_unresolved`, and `delegation_stale`.

Delegated and ordinary excluded entries have null decision/amount/basis fields where inapplicable.
Valid pension OD-2 remains nominal when OD-1 is missing. History persistence has no public API.

### 8.5 Professional blocked result

`CRTISBA_BLOCK_NO_RESULT_V1` exact keys are `schema_version`, `result_state="block_no_result"`,
`client_id`, nullable `source_id`, `operation` (`READ|CLASSIFY|CLEAR`), `failure_stage`,
`failure_detail_code`, sorted `field_paths`, nullable
`observed_planning_calculation_input_fingerprint`, nullable `observed_source_version` (integer
pension or SHA recurring), nullable `observed_source_fingerprint`, nullable
`observed_amount_authority_fingerprint`, nullable `observed_decision_version`, and
`failure_fingerprint`. Observed values remain null until validated by the failing stage. A blocked
result contains no partial collection.

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
| PUT | planning fingerprint mismatch | `CRTISBA_PLANNING_IDENTITY_STALE` | 409 | `/expected_planning_calculation_input_fingerprint` | explicit refresh |
| PUT | source version mismatch | `CRTISBA_SOURCE_VERSION_STALE` | 409 | `/expected_source_version` | explicit refresh |
| PUT | source fingerprint mismatch | `CRTISBA_SOURCE_FINGERPRINT_STALE` | 409 | `/expected_source_fingerprint` | explicit refresh |
| PUT | amount fingerprint mismatch | `CRTISBA_AMOUNT_AUTHORITY_STALE` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | amount unavailable | `CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | amount invalid | `CRTISBA_AMOUNT_AUTHORITY_INVALID` | 409 | `/expected_amount_authority_fingerprint` | explicit refresh |
| PUT | decision CAS mismatch or `uq_crtisba_source_decision_version` | `CRTISBA_DECISION_VERSION_CONFLICT` | 409 | `/expected_decision_version` | explicit refresh |
| PUT | BIGINT ceiling | `CRTISBA_DECISION_VERSION_EXHAUSTED` | 409 | `/expected_decision_version` | no |
| PUT | `fk_crtisba_decision_client` | `CLIENT_NOT_FOUND` | 404 | `/path/client_id` | no |
| PUT | `pk_crtisba_decisions` | `CRTISBA_PERSISTENCE_IDENTITY_CONFLICT` | 500 | empty | no |
| PUT | any named `ck_crtisba_*` constraint | `CRTISBA_PERSISTENCE_CONTRACT_VIOLATION` | 500 | empty | no |
| PUT | `trg_crtisba_decision_immutable` | `CRTISBA_PERSISTENCE_IMMUTABILITY_VIOLATION` | 500 | empty | no |
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

Risk-scoped mutations require unchanged ordinary PASS, reached production mutation, same oracle
FAIL, guaranteed restoration, and same oracle PASS. Required groups are RTISA state mapping;
excluded-source mapping; pristine admission; isolation-before-query; each polymorphic lock target;
post-lock/global planning revalidation; nested transaction ownership; DTO discriminators;
serialization/preimage fields; named constraints/immutability; SQLSTATE/commit-dispatch classifier;
no-retry; transport mapping; forbidden pension inference; forbidden recurring inference.

Real isolated PostgreSQL must prove migration upgrade/downgrade and one head; all named objects;
trigger enforcement; first insert/CAS/ceiling; concurrent version uniqueness; all three row locks;
addressed-source and unrelated-Planning race orderings; `40001`/`40P01`; connection loss before and
after commit dispatch; known versus uncertain outcome; rollback failure/invalidation; explicit GET
reconciliation; snapshot consistency; and no upstream mutation. SQLite is limited to pure DTO,
mapping, fingerprint, ordering, and ordinary behavior.

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
