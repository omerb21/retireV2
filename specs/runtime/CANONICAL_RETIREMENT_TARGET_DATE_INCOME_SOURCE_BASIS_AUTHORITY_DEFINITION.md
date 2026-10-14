# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_AUTHORITY — Definition

## 1. Status, purpose, and authority

- Package: `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_AUTHORITY` (`CRTISBA`).
- Classification: `COMPLEX CLASS A — DEFINITION ONLY`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Authoritative repository base: `ba3029089444ad083e8149993e22c475200ae94c`.
- Rejected dependent Definition `787813ab1adc7ef4669191b30250b907d6de3cae` is not a base or authority for this Definition.
- This package defines a source-by-source, append-only, version-bound professional basis authority.
- It classifies basis evidence only. It never changes a source amount, source admission, comparison
  result, pension execution, target, or professional calculation.
- Implementation, downstream work, deployment, and production readiness remain respectively
  `NOT_AUTHORIZED`, `NOT_AUTHORIZED`, `NOT_AUTHORIZED`, and `NOT_CLAIMED`.

CRTISBA closes the missing professional basis-evidence boundary required before a future RTICB
consumer binding can classify otherwise valid sources. It does not itself modify RTISA or RTICB.

## 2. Binding Owner Decisions

The following decisions are adopted exactly and are normative.

### OD-1 — pension income basis

Every canonical pension income source requires an explicit professional `GROSS` or `NET`
classification. `tax_treatment`, pension product type, source labels, payer identity, and all other
existing fields are forbidden inference inputs. No decision means `UNKNOWN`. A stale, malformed,
or contradictory decision also produces `UNKNOWN`; it never falls back to an inferred value.

### OD-2 — pension target-date price basis

The accepted successful pension target-date calculated amount has the professional price meaning
`NOMINAL_AT_RETIREMENT_TARGET_DATE`. That classification is bound to the exact accepted target-date
amount result and the current pension source identity. It has no separate professional input field.
It applies only to that calculated target-date result. It does not reclassify the pension's
historical/base amount, source statement amount, converted balance, or any other upstream amount.
The accepted projection calculation remains unchanged.

### OD-3 — recurring-income price basis

Every current recurring-income source requires an explicit professional price-basis decision:

- `NOMINAL_AT_RETIREMENT_TARGET_DATE`: the professional explicitly asserts that the unchanged
  accepted recurring amount is already expressed in target-date nominal ILS. Reference date must
  be null. This is a classification, not an inflation calculation.
- `REAL_AT_REFERENCE_DATE`: the professional explicitly asserts that the unchanged accepted amount
  is real ILS at one authoritative canonical reference date. The date is mandatory.
- no valid decision: `UNKNOWN`.

`source_date`, creation/update timestamps, start/end dates, and descriptive text never supply or
infer the price basis or reference date. Existing explicit recurring `amount_basis` alone governs
income basis: `gross -> GROSS`, `net -> NET`, and `unknown -> UNKNOWN`. CRTISBA does not duplicate or
override that field.

## 3. Accepted upstream contracts inspected

| Surface | Accepted evidence at the base | Binding use |
|---|---|---|
| Planning source snapshot | `professional_source_snapshot_service._snapshot`; source contract `canonical-professional-source-snapshot-v1` | Current canonical pension sources, source version, amount authority, monthly-basis authority, temporal authority, and source provenance. |
| Planning Input | `planning_input_service.derive`; `canonical-retirement-planning-input-v1` | Canonical `source_id`, complete serialized source `source_fingerprint`, planning-calculation fingerprint, target date, current recurring records, and pension-alias resolution. |
| Pension monthly basis | accepted `pension_monthly_basis` result embedded in each pension source | `base_amount_semantic_fingerprint` and `base_amount_source_fingerprint` bind the accepted base amount authority; no re-derivation. |
| Pension execution | `pension_target_date_execution_service`; accepted source execution/result fingerprints | Exact current target-date amount authority bound by OD-2. |
| RTISA | `retirement_target_date_income_source_admission_service`; `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_RESULT_V1` | Complete source universe, admission state, current source fingerprints, and accepted amount representations. Admission remains read-only evidence. |
| RTICB | `retirement_target_date_income_comparison_basis_service`; `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V1` | Future consumer target only. Existing comparison semantics/results remain immutable. |
| RTDIR security | authenticated one-workspace server-side actor contract | Browser input cannot provide or forge decision actor or client ownership. |

### 3.1 Exact identities available today

- Canonical pension `source_id` is exactly `manual:<manual_pension_source_id>` or
  `conversion:<pension_destination_id>`.
- A canonical pension has a positive persisted `version`, a complete Planning Input
  `source_fingerprint`, monthly-basis semantic/source fingerprints, temporal semantic/source
  fingerprints, and—when target-date execution succeeds—source execution and result fingerprints.
- A recurring source ID is exactly `income:<positive recurring_income.id>`.
- `RecurringIncome` has no accepted numeric source-version column. Its complete canonical current
  version token is therefore the Planning Input SHA-256 of the serialized full current row. This
  Definition does not invent a numeric recurring source version.
- The recurring amount authority is the exact tuple `{amount, amount_basis, frequency}` from the
  current row. CRTISBA gives that tuple a new namespaced fingerprint solely to bind a basis decision;
  it does not create another amount.

## 4. Separation of professional concepts

The implementation must preserve these non-interchangeable concepts:

| Concept | Owner | Meaning |
|---|---|---|
| source identity | Planning/RTISA | Canonical ID and current client-owned source record. |
| source version | Upstream source | Pension positive version; recurring complete current-row fingerprint. |
| amount authority | Pension execution or recurring row | Existing amount/result and its identity; never changed by CRTISBA. |
| professional basis classification | CRTISBA plus OD-2 | Income and price meaning attached to the bound amount authority. |
| decision provenance | CRTISBA | Who explicitly decided, when, under which contract/version and expected identities. |
| price reference date | CRTISBA recurring decision only | Required date for `REAL_AT_REFERENCE_DATE`; never inferred from `source_date`. |
| admission | RTISA | Whether the source belongs in the target-date admitted universe. |
| comparability | RTICB/future binding | Whether admitted amount basis matches RIT basis. Explicit basis does not itself authorize normalization. |

No field in one row may silently substitute for another concept.

## 5. Canonical source and amount identity

### 5.1 Shared source identity

Every decision is bound to:

- positive `client_id`;
- canonical `source_id`;
- `source_kind` exactly `PENSION` or `RECURRING_INCOME`;
- current source fingerprint, a lowercase SHA-256;
- one current amount-authority fingerprint, a lowercase SHA-256;
- current planning-calculation fingerprint and retirement target date where required below.

Source IDs are globally interpreted only with `client_id` and `source_kind`. The source must exist,
belong to that client, be current, occur exactly once in the accepted source universe, and have the
kind implied by its canonical prefix and upstream entry. Wrong-client, duplicate, absent, archived,
superseded, delegated alias, or mismatched-kind rows cannot receive or reuse a decision.

### 5.2 Pension binding

A pension decision binds all of:

1. positive upstream pension `version`;
2. complete current Planning Input `source_fingerprint`;
3. monthly-basis semantic fingerprint;
4. monthly-basis source fingerprint;
5. successful pension `source_execution_fingerprint`;
6. successful pension `source_result_fingerprint`;
7. planning-calculation input fingerprint used by that execution;
8. canonical retirement target date used by that execution.

The pension amount-authority fingerprint is SHA-256 canonical JSON under namespace
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_PENSION_AMOUNT_AUTHORITY_JSON_V1` over exactly
those eight identities plus `client_id` and `source_id`. It does not contain basis decision,
`tax_treatment`, actor, or decision time.

A changed source version, source fingerprint, monthly-basis identity, execution identity, planning
fingerprint, or target date makes the prior decision stale. OD-2 price classification is likewise
stale because it is bound to the old calculated amount.

### 5.3 Recurring binding

The recurring source-version token is the complete accepted current-row `source_fingerprint`. The
recurring amount-authority fingerprint is SHA-256 canonical JSON under namespace
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RECURRING_AMOUNT_AUTHORITY_JSON_V1` over:

```json
{
  "contract": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RECURRING_AMOUNT_AUTHORITY_JSON_V1",
  "client_id": 1,
  "source_id": "income:1",
  "source_fingerprint": "<sha256>",
  "amount": "<accepted exact serialized amount>",
  "amount_basis": "gross|net|unknown",
  "frequency": "monthly|quarterly|annual"
}
```

The complete source fingerprint intentionally makes any source-record replacement/change stale,
while the separate amount fingerprint proves which amount authority was classified. `source_date`
may participate transitively in the full source fingerprint but has no basis meaning and is absent
from the amount-authority preimage except through that opaque identity.

## 6. Persistence and append-only versioning

Implementation requires exactly one additive migration above the then-current Alembic head. It
creates one append-only table, provisionally
`retirement_target_date_income_source_basis_decisions`; the implementation inventory must freeze
the final revision and constraint names before coding.

Each row contains at least:

| Field | Contract |
|---|---|
| `decision_id` | immutable unique ID |
| `client_id`, `source_id`, `source_kind` | canonical owned source identity |
| `decision_version` | positive `BIGINT`, monotonically increasing per client/kind/source |
| `source_version_at_decision` | positive pension version; null for recurring |
| `source_fingerprint_at_decision` | exact current SHA-256 |
| `amount_authority_fingerprint_at_decision` | exact amount-authority SHA-256 |
| `pension_execution_fingerprint_at_decision` | exact SHA-256 for pension; null for recurring |
| `pension_result_fingerprint_at_decision` | exact SHA-256 for pension; null for recurring |
| `planning_calculation_input_fingerprint_at_decision` | exact SHA-256 for pension; null for recurring |
| `retirement_target_date_at_decision` | exact pension execution date; null for recurring |
| `income_basis` | `GROSS`, `NET`, or `UNKNOWN` under Section 7 |
| `income_basis_provenance` | `EXPLICIT_PROFESSIONAL`, `UPSTREAM_RECURRING_AMOUNT_BASIS`, or `MISSING` |
| `price_basis` | `NOMINAL_AT_RETIREMENT_TARGET_DATE`, `REAL_AT_REFERENCE_DATE`, or `UNKNOWN` |
| `price_reference_date` | canonical date only for real recurring decision; otherwise null |
| `price_basis_provenance` | `OWNER_DECISION_OD2`, `EXPLICIT_PROFESSIONAL`, or `MISSING` |
| `actor` | accepted server-side trusted professional actor |
| `decided_at` | database transaction timestamp |
| `decision_fingerprint` | exact CRTISBA decision fingerprint |

Unique `(client_id, source_kind, source_id, decision_version)` and unique `decision_id` constraints
are mandatory. Rows are never updated or deleted by ordinary application behavior. The effective
decision is the unique highest version for that identity. Clearing/replacing a professional choice
appends an `UNKNOWN` decision rather than deleting history. Historical rows remain readable only as
history and never silently become current again.

The table enforces kind-specific nullability and provenance consistency. Pension rows require the
pension binding fields, `price_basis=NOMINAL_AT_RETIREMENT_TARGET_DATE`, null reference date, and
`price_basis_provenance=OWNER_DECISION_OD2`. Recurring rows require null pension-only fields,
income basis/provenance copied from current `amount_basis`, and explicit/missing price provenance.

No current-pointer update is required. PostgreSQL write serialization uses the project's stable
per-client transaction advisory lock plus the client row `FOR UPDATE`; the current source row and
latest decision row are then locked/validated. The write re-derives current identities only after
locks, checks strict expected identities and expected decision version, and appends version + 1.
Concurrent writes cannot both claim the same next version. No stale request can create a current
decision after a source or amount identity change.

## 7. Professional classification rules

### 7.1 Pension

- Write input requires explicit `income_basis` exactly `GROSS` or `NET`.
- `UNKNOWN` is a read state and explicit clearing command, not a valid positive classification.
- Server derives price basis exactly `NOMINAL_AT_RETIREMENT_TARGET_DATE`, reference date null, and
  provenance `OWNER_DECISION_OD2` only after successful current target-date execution identity is
  validated.
- Income provenance is `EXPLICIT_PROFESSIONAL`.
- `tax_treatment` is preserved as upstream evidence but cannot affect the chosen income basis.

### 7.2 Recurring income

- Server maps current upstream `amount_basis`: `gross -> GROSS`, `net -> NET`, `unknown -> UNKNOWN`.
- Client cannot submit or override recurring income basis.
- Positive price decision is exactly one of:
  - `NOMINAL_AT_RETIREMENT_TARGET_DATE` with reference date null;
  - `REAL_AT_REFERENCE_DATE` with one real canonical reference date.
- `UNKNOWN` with null reference date is the missing/cleared state.
- Nominal means the professional explicitly classifies the unchanged amount as target-date nominal;
  it is not derived from `source_date` and does not execute a conversion.
- Real reference date is explicit professional evidence and is unrelated to `source_date` unless
  the professional independently chooses the same calendar date.

### 7.3 Delegated pension representations

An RTISA recurring `PENSION_REPRESENTATION` delegated to a canonical pension does not receive an
independent basis decision. Its read state is `NOT_APPLICABLE_DELEGATED`, bound to the accepted
resolution and canonical pension source ID. It remains excluded under RTISA. Allowing a separate
decision would create duplicate authority and is forbidden.

## 8. Strict commands and read result

### 8.1 Write command

The future protected route is:

`PUT /api/clients/{client_id}/retirement-income-readiness/source-bases/{source_id}`

The strict body has common expected identity fields and one discriminated payload:

```json
{
  "source_kind": "PENSION",
  "expected_decision_version": 0,
  "expected_source_version": 1,
  "expected_source_fingerprint": "<sha256>",
  "expected_amount_authority_fingerprint": "<sha256>",
  "expected_pension_execution_fingerprint": "<sha256>",
  "expected_pension_result_fingerprint": "<sha256>",
  "expected_planning_calculation_input_fingerprint": "<sha256>",
  "expected_retirement_target_date": "YYYY-MM-DD",
  "income_basis": "GROSS"
}
```

or:

```json
{
  "source_kind": "RECURRING_INCOME",
  "expected_decision_version": 0,
  "expected_source_version": null,
  "expected_source_fingerprint": "<sha256>",
  "expected_amount_authority_fingerprint": "<sha256>",
  "price_basis": "REAL_AT_REFERENCE_DATE",
  "price_reference_date": "YYYY-MM-DD"
}
```

Extra/missing/wrong-kind keys, coercion, boolean integers, noncanonical ID/date/hash, and conflicting
fields are rejected before service entry. A dedicated explicit clear command uses the same expected
identities and appends the kind-valid `UNKNOWN` state; omission/null in a positive command is not an
implicit clear.

The actor is injected only from the authenticated server session. It is absent from the DTO.

### 8.2 Read operation and result

The future protected read is:

`GET /api/clients/{client_id}/retirement-income-readiness/source-bases`

It derives the complete current RTISA source universe in one coherent snapshot and returns:

- schema/version, client, planning fingerprint, retirement target date;
- RTISA admission result fingerprint;
- sorted `source_basis_entries` one-for-one with RTISA source entries;
- sorted IDs partitioned into `current`, `missing`, `stale`, `unknown`,
  `not_applicable_delegated`, and `invalid`;
- `basis_readiness_state` (`READY` or `NOT_READY`) and `basis_ready`;
- sorted blockers;
- result fingerprint.

Each entry contains exact source/kind/category/admission identity; source version token and source
fingerprint; amount-authority fingerprint; decision version/fingerprint or null; income basis and
provenance; price basis/reference/provenance; `decision_state`; and source-specific blockers.

`READY` means every non-delegated current canonical pension and every non-delegated current
recurring-income source has a `CURRENT` decision/effective classification, with neither basis
`UNKNOWN`, and all bindings match. RTISA admission state is reported but never changed. An excluded
future/ended recurring source still requires its explicit price classification under OD-3. A
delegated pension representation is complete as `NOT_APPLICABLE_DELEGATED`.

## 9. Missing, UNKNOWN, stale, contradictory, and invalid behavior

- `MISSING`: no decision row exists; effective basis fields are `UNKNOWN`/null.
- `UNKNOWN`: latest append-only decision explicitly records missing/cleared evidence or recurring
  upstream `amount_basis=unknown`.
- `STALE`: latest decision is structurally valid but any bound source/version/amount/execution/
  planning/date identity differs from current accepted authority.
- `INVALID`: malformed row, fingerprint mismatch, duplicate latest version, impossible kind/provenance
  combination, wrong client, or broken source relationship.
- `CURRENT`: all required bindings and decision fingerprint recompute exactly.
- `NOT_APPLICABLE_DELEGATED`: valid recurring pension representation delegated to one current
  canonical pension; no independent decision is allowed.

Missing/unknown/stale/invalid never falls back to labels, tax treatment, source date, historical
decision, previous source version, or RTISA/RTICB classification. Source replacement under the same
ID changes its fingerprint/version and stales the old decision. A new source ID never inherits an
old decision. Historical decisions remain immutable evidence.

## 10. Fingerprint contracts

All fingerprints are SHA-256 of canonical UTF-8 JSON with sorted keys, `ensure_ascii=false`, compact
separators, and `allow_nan=false`. No Unicode normalization, timestamps outside the defined
preimage, browser actor, request ID, or iteration order is added.

### 10.1 Decision fingerprint

Namespace:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_DECISION_JSON_V1`.

Preimage contains exactly the professional semantics and bound authority identity:

- contract namespace;
- client/source ID and kind;
- decision version;
- source version token and source fingerprint;
- amount-authority fingerprint;
- pension execution/result, planning, and target-date identities when pension;
- income basis and provenance;
- price basis, reference date, and provenance.

Actor and `decided_at` are persisted audit provenance but are fingerprint-invariant. This prevents
identical professional decisions by different trusted actors/times from acquiring different
semantic identity while retaining full audit evidence.

### 10.2 Result fingerprint

Namespace:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1`.
Preimage is exactly `{contract, result}` where `result` is the full read DTO excluding
`result_fingerprint`. Entries and all partitions are canonical sorted arrays.

### 10.3 Failure fingerprint

Namespace:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_FAILURE_JSON_V1`.
Professional block/failure preimage contains exact supplied valid identities, exact observed
validated identities or null, failure stage/detail, and no partial basis result. Internal JSON/hash
construction errors are technical exceptions, never semantic fingerprint failures.

## 11. Transaction ownership and concurrency

### 11.1 Read

Read requires a pristine session and owns one `REPEATABLE READ READ ONLY` PostgreSQL transaction
(SQLite transaction only for application tests). Planning, pension execution evidence, RTISA
universe, and latest decisions are read in the same snapshot. It opens no nested public reader or
second session. It ends by rollback/release; technical failure rolls back and propagates.

### 11.2 Write

Write owns one transaction. It validates DTO before acquisition, then obtains the same stable
PostgreSQL per-client advisory transaction lock used for serialized client mutations and locks the
client row `FOR UPDATE`. Only afterward it re-reads the current source, amount authority, accepted
target context, and latest decision. It applies expected-version and expected-fingerprint CAS,
inserts one decision row, and commits once.

Any mismatch rolls back with no insert. Unique/version conflict, serialization/deadlock retry, if
the repository's accepted database retry policy is reused, must re-enter the complete lock and
identity validation and may never replay a stale pre-lock result. No partial insert, update of old
decision, or fail-open classification is allowed.

## 12. Failure precedence and exact code families

Evaluation is deterministic and stops at the first stage:

1. `request_validation`
2. `snapshot_admission`
3. `client_authority`
4. `source_universe`
5. `source_identity`
6. `amount_authority`
7. `decision_authority`
8. `result_identity`

Required codes include:

| Stage | Exact codes |
|---|---|
| request | `CRTISBA_CLIENT_ID_INVALID`, `CRTISBA_SOURCE_ID_INVALID`, `CRTISBA_REQUEST_INVALID` |
| snapshot | `CRTISBA_REQUIRES_FRESH_TRANSACTION`, `CRTISBA_UNSUPPORTED_DATABASE` |
| client | `CRTISBA_CLIENT_NOT_FOUND`, `CRTISBA_CLIENT_OWNERSHIP_INVALID` |
| universe | `CRTISBA_SOURCE_UNIVERSE_INVALID`, `CRTISBA_SOURCE_COVERAGE_MISMATCH`, `CRTISBA_DUPLICATE_SOURCE_ID` |
| source | `CRTISBA_SOURCE_NOT_FOUND`, `CRTISBA_SOURCE_KIND_MISMATCH`, `CRTISBA_SOURCE_NOT_CURRENT`, `CRTISBA_SOURCE_VERSION_STALE`, `CRTISBA_SOURCE_FINGERPRINT_STALE`, `CRTISBA_DELEGATED_SOURCE_DECISION_FORBIDDEN` |
| amount | `CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE`, `CRTISBA_AMOUNT_AUTHORITY_INVALID`, `CRTISBA_AMOUNT_AUTHORITY_STALE`, `CRTISBA_PENSION_EXECUTION_NOT_READY`, `CRTISBA_PENSION_EXECUTION_IDENTITY_STALE` |
| decision | `CRTISBA_DECISION_MISSING`, `CRTISBA_DECISION_UNKNOWN`, `CRTISBA_DECISION_STALE`, `CRTISBA_DECISION_INVALID`, `CRTISBA_DECISION_VERSION_CONFLICT`, `CRTISBA_PENSION_INCOME_BASIS_REQUIRED`, `CRTISBA_RECURRING_PRICE_BASIS_REQUIRED`, `CRTISBA_REAL_REFERENCE_DATE_REQUIRED`, `CRTISBA_NOMINAL_REFERENCE_DATE_NOT_NULL`, `CRTISBA_INCOME_BASIS_CONTRADICTION` |
| identity | `CRTISBA_DECISION_FINGERPRINT_INVALID`, `CRTISBA_RESULT_FINGERPRINT_INVALID` |

Read returns a deterministic professional result with entry blockers for ordinary missing/unknown/
stale classification. Malformed producer/table relationships or unavailable database/producer
machinery fail closed. SQLAlchemy/driver/database, rollback, serialization/hash, assertion, and
programming failures remain technical and map through accepted RTDIR `500/503` transport; they are
not converted to professional decisions.

## 13. Ordinary executable acceptance inventory

Implementation acceptance must prove:

1. explicit pension `GROSS` and `NET` each persist and read current;
2. pension income basis never follows `tax_treatment` or product/source labels;
3. pension missing/clear is `UNKNOWN`;
4. pension price basis is exactly OD-2 nominal at target date with null reference;
5. OD-2 binds the exact current source version, monthly-basis identities, execution/result,
   planning fingerprint, and target date;
6. changing any pension binding makes the old decision stale;
7. historical/base pension amounts are not reclassified or changed;
8. recurring `gross/net/unknown` maps only to `GROSS/NET/UNKNOWN` income basis;
9. client cannot override recurring income basis;
10. explicit recurring nominal has null reference and the exact target-date meaning;
11. explicit recurring real requires and preserves the authoritative reference date;
12. `source_date` changes never infer price basis/reference date;
13. missing recurring price decision is `UNKNOWN`;
14. contradictory nominal/date and real/no-date commands fail;
15. wrong-source, wrong-client, wrong-kind, replaced-source, superseded-source, and stale expected
    identities fail before insert;
16. recurring full source fingerprint and amount-authority fingerprint are independently bound;
17. delegated pension representation rejects an independent decision;
18. all current RTISA source IDs occur exactly once in output and admission remains unchanged;
19. excluded future/ended recurring sources remain excluded but require basis evidence;
20. append-only versions increase monotonically; old rows never change;
21. explicit clear appends `UNKNOWN` and preserves history;
22. identical professional semantics produce identical decision fingerprint regardless of actor/time;
23. source/amount/basis changes alter the appropriate fingerprint;
24. read ordering, partitions, blockers, and result fingerprint are deterministic;
25. malformed/duplicate persisted decisions fail closed;
26. public route authentication, path ownership, strict DTOs, no-store headers, and actor injection
    match accepted RTDIR security;
27. basis writes do not change source amount, RTISA admission, existing RTICB results, or pension
    projection outputs;
28. one snapshot/read and one locked atomic write transaction are observed with correct rollback.

## 14. Mutation-sensitive acceptance inventory

Use ordinary production-path oracles; each passes before mutation, fails under a controlled
production-branch mutation, and passes after guaranteed restoration. Shared branch coverage is
sufficient where it proves multiple sources.

- infer pension income basis from `tax_treatment`;
- infer recurring price basis/reference from `source_date`;
- accept pension decision without explicit GROSS/NET;
- classify pension target-date amount as real or omit OD-2 binding;
- drop one pension version/monthly-basis/execution/planning/date identity check;
- accept real recurring basis without reference date;
- accept nominal recurring basis with a reference date;
- permit browser-supplied recurring income basis or actor;
- reuse a decision for a different source/client/kind;
- ignore a changed source fingerprint or amount-authority fingerprint;
- let an old decision become current after source replacement;
- update/delete a historical row instead of append;
- bypass expected decision version or post-lock revalidation;
- allow two concurrent writers to create the same next version/current ambiguity;
- change RTISA admission, source amount, pension execution, or RTICB comparison as a side effect;
- omit or duplicate a source in the read universe;
- make decision/result fingerprint actor/time or iteration-order sensitive;
- open a second snapshot or use a pre-lock cached source;
- fail open on technical database/fingerprint failure.

## 15. PostgreSQL-only evidence obligations

Real isolated PostgreSQL evidence is required for:

- migration upgrade/downgrade, exact constraints/indexes/FKs, one Alembic head, and preservation of
  existing data;
- per-client advisory lock plus client/source/latest-decision row locking order;
- concurrent same-source writes and exact version uniqueness;
- source mutation racing a decision write, proving post-lock stale rejection;
- append-only immutability and absence of a second current interpretation;
- one repeatable-read read snapshot under concurrent source/decision commits;
- rollback after conflict/injected failure and no partial row;
- real server transaction timestamp and trusted actor persistence;
- no mutation of source, amount, RTISA, RTICB, or pension-execution tables.

SQLite may prove pure DTO, mapping, fingerprint, ordering, and ordinary service behavior. It is not
evidence for concurrency, locking, constraints, or snapshot semantics.

## 16. Future RTICB consumer-binding requirements

This Definition unblocks `CRTCMIA-DEF-001` by providing authoritative, source-bound income and
price basis evidence for every relevant RTISA source. A separately accepted append-only RTICB
consumer-binding must, at minimum:

1. consume CRTISBA and RTISA in the same RTICB-owned snapshot;
2. match client, planning fingerprint, retirement target date, complete source IDs, admission
   fingerprint, source fingerprint, amount-authority fingerprint, and current decision fingerprint;
3. substitute effective CRTISBA basis evidence only into the future comparison input—not rewrite
   historical RTISA entries or accepted RTICB results;
4. preserve RTISA admission and source amounts verbatim;
5. keep missing/unknown/stale/invalid CRTISBA evidence as `BASIS_UNRESOLVED`/not ready;
6. treat explicit mismatched basis as `NORMALIZATION_REQUIRED`, never execute normalization;
7. retain `NOT_ADMITTED` for excluded/delegated entries;
8. create a new versioned comparison identity so historical RTICB fingerprints remain valid;
9. prove one-to-one complete source coverage and no fallback to legacy UNKNOWN inference;
10. preserve one-snapshot transaction ownership and technical/professional error separation.

That future binding enables genuine production-path evidence for `CRTCMIA-DEF-006`: directly
comparable sources can be produced from explicit current basis evidence rather than fabricated
RTISA states or mocked RTICB outputs. It does not by itself authorize CRTCMIA implementation,
aggregation, normalization, or a total.

## 17. Explicit exclusions

Not authorized: gross/net conversion; tax/withholding calculation; price normalization;
CPI/indexation conversion; replacement/change of pension calculations; change to recurring amounts;
aggregation or comparable monthly income total; Gap/Surplus; funding/resource eligibility;
capital-to-income conversion; withdrawals/allocation; scenarios/recommendations; broad frontend
refactoring; Railway deployment; M11–M14. `02M` remains `FROZEN`; `M08E` remains `EXCLUDED`.

## 18. Stop conditions

Implementation must stop for a Definition/Owner decision if:

- an accepted current pension source lacks a stable version, source fingerprint, monthly-basis
  identity, or successful target-date execution identity needed by OD-2;
- a recurring source cannot expose its accepted exact amount/basis/frequency and full fingerprint;
- canonical source replacement cannot be distinguished from the prior source version;
- one source could have two effective highest decision versions;
- exact append-only persistence requires changing an accepted source table;
- a basis classification would require inference from tax treatment, source date, product type, or
  other forbidden evidence;
- an accepted upstream contract must be semantically rewritten;
- transaction ownership cannot guarantee post-lock validation and one-snapshot reads;
- a future consumer would need to alter historical RTISA/RTICB results;
- implementation would execute conversion/normalization or aggregation.

## 19. Pre-implementation enumeration

Before coding, freeze:

1. exact migration revision/parent, table, columns, constraints, indexes, and FK names;
2. complete pension/manual/conversion and recurring source-field inventory;
3. exact amount-authority preimages for each source kind;
4. exact DTO key sets, clear command, route paths, and transport mappings;
5. decision/result/failure fingerprint preimages and golden vectors;
6. current/stale/unknown/invalid/delegated state matrix;
7. all failure codes and precedence;
8. client advisory-lock key and complete lock order;
9. read/write transaction call graphs and rollback matrix;
10. ordinary, mutation, migration, and PostgreSQL concurrency tests;
11. protected-route/security inventory;
12. explicit proof that no accepted source/RTISA/RTICB/pension execution semantics change.

## 20. Consolidated self-review and unresolved ambiguity

Self-review confirms that this Definition:

- adopts OD-1, OD-2, and OD-3 without inference;
- uses only fields and identities present in accepted producers;
- handles the absence of a recurring numeric version through its accepted full-row fingerprint,
  without inventing a version field;
- binds pension OD-2 to the current target-date calculated amount rather than historical amounts;
- keeps classification, amount, provenance, identity, reference date, admission, and comparability
  separate;
- uses append-only history and deterministic current-version selection;
- preserves RTISA, RTICB, RIT, pension execution, and recurring amount semantics;
- defines a minimal future binding while withholding its implementation;
- authorizes no normalization, aggregation, downstream package, or deployment.

Additional professional Owner decisions required: **none**.

Implementation-level names listed as provisional must be frozen during authorized pre-implementation
enumeration without changing professional semantics.

Definition status: `READY_FOR_INDEPENDENT_DEFINITION_ACCEPTANCE_AUDIT`.

Implementation = `NOT_AUTHORIZED`.

Downstream = `NOT_AUTHORIZED`.

Production readiness = `NOT_CLAIMED`.
