# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_AUTHORITY — Corrected Definition

## 1. Authority and boundaries

Package `CRTISBA`; governance `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`; base
`ba3029089444ad083e8149993e22c475200ae94c`. This complete corrected Definition supersedes its
prior text. CRTISBA is append-only source-bound professional basis evidence. It never changes
amounts, PTE, RTISA admission, RTICB, normalization, aggregation, funding, tax, allocation, or
scenarios. Implementation/downstream/deployment are `NOT_AUTHORIZED`; readiness is `NOT_CLAIMED`.

## 2. Binding Owner Decisions

- **OD-1:** each canonical pension needs explicit `GROSS|NET`; missing, clear, stale, or invalid is
  `UNKNOWN`. Never infer from tax treatment, product, label, payer, or other source facts.
- **OD-2:** every successful current PTE independently exposes
  `NOMINAL_AT_RETIREMENT_TARGET_DATE`, null reference date, provenance `OWNER_DECISION_OD2`. It
  remains visible when OD-1 is missing/cleared and applies only to that exact calculated amount.
- **OD-3:** recurring price basis is explicit `NOMINAL_AT_RETIREMENT_TARGET_DATE` with null date or
  `REAL_AT_REFERENCE_DATE` with an authoritative date. Never infer from source/timestamps. Recurring
  income basis is only `amount_basis`: gross/net/unknown -> GROSS/NET/UNKNOWN.

Identity, amount authority, income basis, price basis, provenance, admission, delegation, and
comparison readiness are separate contracts.

## 3. Accepted upstream identities

Consume without modification: Planning Input source/planning/target identities; pension monthly
basis and temporal semantic/source fingerprints; PTE execution/result identities; RTISA entries,
exact amounts, admission and result fingerprint; portfolio `source_entry_fingerprint`; authenticated
server `trusted_professional_actor`. Pension IDs are `manual:<id>|conversion:<id>`; recurring IDs
are `income:<id>`. Frequencies are `monthly|quarterly|annual|other`. Recurring version is its full
current Planning Input source fingerprint, never an invented number.

## 4. Exact amount authorities

Common binding is positive client, canonical ID/kind, current source fingerprint and current amount
fingerprint. Source must occur exactly once and be current/client-owned/kind-correct.

Pension fingerprint namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_PENSION_AMOUNT_AUTHORITY_JSON_V1`; exact
canonical preimage keys are: `contract`, `client_id`, `source_id`, positive `source_version`,
`source_fingerprint`, `base_amount_semantic_fingerprint`, `base_amount_source_fingerprint`,
`temporal_semantic_fingerprint`, `temporal_source_fingerprint`,
`planning_calculation_input_fingerprint`, ISO `retirement_target_date`,
`pension_source_execution_fingerprint`, `pension_source_result_fingerprint`,
`portfolio_source_entry_fingerprint`, and `amount`. `amount` is exactly
`{numerator,denominator,currency,frequency}` where numerator equals RTISA
`monthly_equivalent.numerator` and portfolio `source_unquantized_target_monthly_amount`, denominator
is `"1"`, currency `"ILS"`, frequency `"MONTHLY"`. Display-rounded values are forbidden.

Recurring namespace is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RECURRING_AMOUNT_AUTHORITY_JSON_V1`; exact
keys: `contract`, `client_id`, `source_id`, `source_fingerprint`, exact Decimal `amount`,
`amount_basis`, and `frequency` including `other`. For `other`, RTISA stays `UNRESOLVED`, monthly
equivalent stays null, and `RTISA_SOURCE_FREQUENCY_UNSUPPORTED` is preserved. A price decision may
be stored, but state remains `UPSTREAM_UNRESOLVED`, readiness false, blocker
`CRTISBA_RECURRING_FREQUENCY_UNSUPPORTED`; it never becomes comparison-ready.

Decimals are plain exact base-10 strings, no exponent/float/grouping; dates are `YYYY-MM-DD`; hashes
are lowercase 64 hex. Any changed listed identity/amount makes prior evidence stale.

## 5. Pension representations

No standalone decision is allowed. Exact current delegation with matching fingerprints and RTISA
reason `SAME_CANONICAL_PENSION` yields `NOT_APPLICABLE_DELEGATED`, complete for coverage but never
comparison-counted. Missing resolution yields `DELEGATION_UNRESOLVED` plus
`CRTISBA_PENSION_REPRESENTATION_DELEGATION_UNRESOLVED`; mismatch yields `DELEGATION_STALE` plus
`..._STALE`; malformed/ambiguous/wrong target yields `DELEGATION_INVALID` plus `..._INVALID`.
All three block readiness and never receive ordinary recurring treatment.

## 6. Persistence and transactions

One additive migration creates `retirement_target_date_income_source_basis_decisions` with immutable
ID, source identity, `decision_version BIGINT`, bound identities, decision/provenance, server actor,
database transaction time, and fingerprint. First command requires expected version 0, proves no
row, inserts 1. Later commands lock/select unique max, require exact CAS, insert expected+1. Maximum
is `9223372036854775807`; next append fails `CRTISBA_DECISION_VERSION_EXHAUSTED`. Unique
client/kind/source/version is mandatory. DB trigger rejects ordinary UPDATE/DELETE; application role
has SELECT/INSERT only. No current pointer; max version is authoritative.

No automatic retry exists for CAS, unique, serialization, deadlock, flush, commit, or uncertain
outcome. Service owns one transaction: flush, commit once, return after commit. Pre-commit failure
rolls back. Known commit failure maps `CRTISBA_COMMIT_FAILED`; uncertain outcome maps
`CRTISBA_COMMIT_OUTCOME_UNKNOWN` and requires explicit read; rollback failure maps
`CRTISBA_ROLLBACK_FAILED`, invalidates/closes session, and session is never reused.

Pension rows store OD-1 only; OD-2 is freshly derived from current PTE. Pension clear therefore
cannot erase OD-2. Recurring rows store OD-3. Clear appends UNKNOWN only for the stored decision.

Read owns one pristine PostgreSQL `REPEATABLE READ READ ONLY` snapshot across Planning/PTE/portfolio/
RTISA/decisions, no nested public reader/session, ending by rollback/release.

Write validates DTO, begins one transaction, may take an advisory lock only to serialize CRTISBA
decision writers, locks the actual source row `FOR UPDATE` (RecurringIncome or actual pension
manual/destination row), then latest decision, and re-derives every identity after locks. Upstream
writers need not take the advisory lock. If source update commits first, post-lock CAS rejects the
stale decision. If decision locks/commits first, source update blocks then commits; next read reports
the immutable decision stale. No upstream writer changes and no pre-lock cached authorization.

## 7. Exact DTOs and states

Route: `PUT /api/clients/{client_id}/retirement-income-readiness/source-bases/{source_id}`. Unknown
keys/coercion/boolean integers/noncanonical values are forbidden. Common positive keys are
`operation="CLASSIFY"`, `source_kind`, `expected_decision_version`,
`expected_source_fingerprint`, `expected_amount_authority_fingerprint`. Pension also requires
positive `expected_source_version`, `income_basis=GROSS|NET`, and forbids price keys. Recurring
requires `expected_source_version=null`, `price_basis`, and `price_reference_date` (null nominal,
non-null real), and forbids income/pension keys. Actor is never input.

`operation="CLEAR"` accepts only common keys plus kind-specific expected source version; all
classification keys are forbidden. Write response exact keys: `schema_version`, client/source/kind,
decision version/state, income basis/provenance, price basis/reference/provenance, source fingerprint,
amount fingerprint, decision fingerprint. Actor/time are excluded.

GET collection exact top-level keys: `schema_version`, `client_id`, planning fingerprint, target
date, RTISA result fingerprint, `source_basis_entries`, `partitions`, `blockers`, readiness state/
boolean, result fingerprint. Entry exact keys: source ID/kind/category/admission, source fingerprint/
version, amount fingerprint, decision version/fingerprint/state, income basis/provenance, price
basis/reference/provenance, blockers. Pension OD-2 remains nominal when income is UNKNOWN.
Partitions: current, missing, unknown, stale, invalid, upstream_unresolved,
not_applicable_delegated, delegation_unresolved/stale/invalid. History API is not authorized.

Professional blocked exact shape: schema version, `result_state="block_no_result"`, client/source,
operation, stage, detail code, sorted field paths, observed source/amount/version, failure fingerprint.
Observed values are null unless validated before failure; no partial result.

## 8. Fingerprints

SHA-256 canonical UTF-8 JSON: sorted keys, compact separators, `ensure_ascii=false`,
`allow_nan=false`, no Unicode normalization. Decision namespace
`..._DECISION_JSON_V1` preimage is exactly contract, client/source/kind, decision version, source
version/fingerprint, amount fingerprint, and stored decision/provenance fields; actor/time and
derived OD-2 are excluded. Result namespace `..._RESULT_JSON_V1` is `{contract,result}` excluding
result fingerprint. Failure namespace `..._FAILURE_JSON_V1` contains contract, client/source,
operation, stage/code/fields, and observed source/amount/version. Declared arrays are sorted.
Different decision versions may change fingerprints. Golden vectors freeze decimals, dates, nulls,
and all preimages.

## 9. Closed outcome/transport contract

All responses: `Cache-Control: no-store`, `Pragma: no-cache`. Professional GET blockers are HTTP 200
basis/block_no_result envelopes; transport failures never masquerade as professional decisions.

| Operation/stage | Public code(s) | HTTP/envelope | Retry/observed rule |
|---|---|---|---|
| any request/auth | `REQUEST_VALIDATION_ERROR`, `AUTHENTICATION_REQUIRED` | 422/401 RTDIR error | corrected request/login; null |
| client/ownership | `CRTISBA_CLIENT_NOT_FOUND`, `CRTISBA_CLIENT_OWNERSHIP_INVALID` | 404 RTDIR error | no; null |
| transaction precheck | `CRTISBA_REQUIRES_FRESH_TRANSACTION`, `CRTISBA_UNSUPPORTED_DATABASE` | 503 RTDIR error | new request; null |
| GET universe | `CRTISBA_SOURCE_UNIVERSE_INVALID`, `..._COVERAGE_MISMATCH`, `..._DUPLICATE_SOURCE_ID` | 200 block_no_result | source correction; validated only |
| PUT source | `CRTISBA_SOURCE_NOT_FOUND`, `..._KIND_MISMATCH`, `..._NOT_CURRENT` | 404/409 RTDIR error | refresh; validated only |
| PUT locked CAS | `CRTISBA_SOURCE_VERSION_STALE`, `..._FINGERPRINT_STALE`, `..._AMOUNT_AUTHORITY_STALE` | 409 RTDIR error | explicit refresh; observed validated identities |
| PUT delegated | `CRTISBA_DELEGATED_SOURCE_DECISION_FORBIDDEN` | 409 RTDIR error | no; validated |
| GET delegation | exact three Section 5 blockers | 200 basis result | source correction; validated |
| GET/PUT upstream | `CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE`, `..._INVALID`, `..._STALE` | 200 basis / 409 error | refresh; validated |
| GET frequency other | `CRTISBA_RECURRING_FREQUENCY_UNSUPPORTED` | 200 basis result | source correction; validated |
| GET decision | `CRTISBA_DECISION_MISSING`, `..._UNKNOWN`, `..._STALE`, `..._INVALID` | 200 basis result | explicit action; validated |
| PUT semantics | `CRTISBA_PENSION_INCOME_BASIS_REQUIRED`, `..._RECURRING_PRICE_BASIS_REQUIRED`, `..._REAL_REFERENCE_DATE_REQUIRED`, `..._NOMINAL_REFERENCE_DATE_NOT_NULL`, `..._INCOME_BASIS_CONTRADICTION` | 422 RTDIR error | corrected request; null |
| PUT decision CAS/ceiling | `CRTISBA_DECISION_VERSION_CONFLICT`, `CRTISBA_DECISION_VERSION_EXHAUSTED` | 409 RTDIR error | explicit refresh/no retry; version only |
| fingerprint | `CRTISBA_FINGERPRINT_FAILURE` | 500 RTDIR error | no retry; null |
| DB/serialization/deadlock | `CRTISBA_DATABASE_UNAVAILABLE` | 503 RTDIR error | new explicit request; null |
| flush/commit | `CRTISBA_FLUSH_FAILED`, `CRTISBA_COMMIT_FAILED`, `CRTISBA_COMMIT_OUTCOME_UNKNOWN` | 503 RTDIR error | no automatic retry; null |
| rollback | `CRTISBA_ROLLBACK_FAILED` | 503 RTDIR error | new session; null |
| unexpected | `INTERNAL_SERVER_ERROR` | 500 RTDIR error | no retry; null |

`field_paths` is the exact sorted rejected/causal path array, empty only when no request field caused
the outcome. Original producer code is preserved in diagnostics; the public code above is fixed.
Single-workspace actor is server-authenticated; client ID must still address an existing record.

## 10. Acceptance evidence

Ordinary production-path matrices must prove: OD-1 GROSS/NET and no inference; missing/clear OD-1
with visible OD-2; exact unquantized pension tuple and every upstream identity; all four recurring
frequencies and `other` non-readiness; nominal/real/date rules; valid and three invalid delegation
states; strict positive/clear/read/write/blocked DTOs; first insert/CAS/max/clear/ceiling/immutability;
all transport rows including cache/envelope/fields/retry/observed values; fingerprint golden vectors
and version determinism; coherent read and both race orderings; zero upstream side effects.

Material risk-scoped mutation groups require ordinary PASS -> reached production mutation -> same
oracle FAIL -> guaranteed restoration -> same oracle PASS for: OD-2 independence; pension identity/
amount tuple; frequency other; delegation mapping; DTO/envelope mapping; CAS/latest/ceiling/DB
immutability; post-row-lock races; no-retry and transaction failure mapping; fingerprint inclusions/
exclusions; professional/technical transport. Input-only mutations or source-text inspection alone
are insufficient.

Real isolated PostgreSQL must prove migration upgrade/downgrade and one head; exact constraints,
indexes, trigger and privileges; first insert/CAS/ceiling; concurrent version uniqueness; actual
source-row locks and both races; repeatable-read snapshot; flush/commit/rollback/session invalidation;
actor/timestamp persistence; and no upstream mutations. SQLite is evidence only for pure DTO,
mapping, fingerprint, ordering, and ordinary behavior.

## 11. Blocker closure and stop conditions

| Blocker | Binding sections | Status |
|---|---|---|
| DEF-001 | 2, 6, 7 | CLOSED |
| DEF-002 | 4 | CLOSED |
| DEF-003 | 3, 4 | CLOSED |
| DEF-004 | 5 | CLOSED |
| DEF-005 | 6 | CLOSED |
| DEF-006 | 6 | CLOSED |
| DEF-007 | 7, 8 | CLOSED |
| DEF-008 | 9 | CLOSED |
| DEF-009 | 10 | CLOSED |

Stop rather than invent authority if an accepted producer lacks a listed identity/exact amount, an
actual source row cannot be locked/revalidated, append-only enforcement is impossible, or accepted
upstream semantics would need change. No additional Owner Decision is presently required. DTOs,
fingerprints, no-retry policy, transactions, locks, states, transport and evidence above are the
single contract; no contradictory alternative remains.

`02M=FROZEN`; `M08E=EXCLUDED`; `M11-M14=NOT_AUTHORIZED`.

Definition status: `READY_FOR_INDEPENDENT_DEFINITION_ACCEPTANCE_AUDIT`.

Implementation = `NOT_AUTHORIZED`.
Downstream = `NOT_AUTHORIZED`.
Production readiness = `NOT_CLAIMED`.
