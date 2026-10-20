# Retirement Monthly Income Gap Authority (RMIGA) — Definition Candidate

## 1. Identity and lifecycle

- Package: `RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY` (`RMIGA`).
- Title: `Retirement Monthly Income Gap Authority`.
- Classification: `CLASS A / COMPLEX CLASS A`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Definition base master: `e30976a82f98a96617be1f09cdba2e67b8a9f076`.
- Governance blob at that base: `95978276b77aa7e3a4af4b783fa097f62137da15`.
- Status: `DEFINITION_CANDIDATE_PENDING_INDEPENDENT_ACCEPTANCE`.
- Implementation: `NOT_AUTHORIZED`.
- Downstream: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This file is the sole proposed semantic authority for RMIGA. It defines an
internal planner-only calculation. It creates no endpoint, UI, migration,
persistence, deployment or downstream authorization.

## 2. Accepted upstream authority boundary

RMIGA consumes, but never changes, these accepted authorities:

1. **RIT** (`CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_V1`)
   owns the confirmed positive monthly target, `ILS` currency, income basis,
   price basis, optional real-price reference date, client, planning identity,
   retirement target date, target semantic fingerprint and target result
   fingerprint. At the definition base, its executable service blob is
   `1835b5883e55ad853ac81ac14cb279d82f639961`.
2. **CMIA** owns the complete comparable monthly-income result or the accepted
   no-total block. Its immutable accepted Definition HEAD is
   `dc17a4155a442d08aef7896ac08d74c7d1048adf`, Definition blob is
   `56bc4400f4b2c4ac04471d422d167979322d1212`, accepted implementation HEAD is
   `7ace33fdc8468d56e5b5aab490ef615031b72738`, and accepted implementation TREE
   is `af59f475dde233a056957abccaa63096f8e39f14`.
3. CMIA's accepted producer chain remains the sole owner of contribution
   admission, source identity, exact comparable monthly amounts and the
   complete comparable total. RMIGA does not directly consume RTISA, CRTISBA,
   RTICB, PTE or Planning Input and does not revalidate their professional
   decisions independently.

The only arithmetic authority introduced here is:

`monthly_gap = confirmed_RIT_monthly_target - complete_CMIA_comparable_monthly_income`.

A positive result is an arithmetic `SHORTFALL`; zero is `EQUAL`; a negative
result is an arithmetic `SURPLUS`. These labels describe the sign only. They
are not adequacy findings, recommendations, funding instructions or scenarios.

## 3. Purpose and exclusions

RMIGA returns a numeric result only when the same read snapshot contains:

- a structurally and cryptographically valid RIT result that is `CURRENT`,
  `READY`, confirmed and blocker-free;
- a structurally and cryptographically valid CMIA `COMPLETE` result;
- exact agreement on client, planning fingerprint, retirement date, currency,
  income basis, price basis, nullable price-reference date and RIT target
  semantic/result fingerprints; and
- a valid exact RIT amount and a valid canonical CMIA rational total.

A validated CMIA `BLOCK_NO_TOTAL` maps to an RMIGA `BLOCK_NO_GAP` without any
numeric target-minus-income result. Malformed, forged or mutually inconsistent
upstream evidence is an integrity error, not a professional block.

Excluded: taxation, gross/net conversion, nominal/real conversion, CPI or other
indexation, capital funding, withdrawals, pension adequacy, recommendations,
forecasting, scenarios, client-facing presentation, persistence, migrations,
API expansion and any change to an upstream professional rule.

## 4. Internal entrypoint and closed request

Proposed Python entrypoint:

`assess(db: Session, request: Mapping[str, Any]) -> dict`

The request has exactly these keys:

| Key | Exact contract |
|---|---|
| `client_id` | strict positive integer; `bool` is invalid |
| `expected_planning_calculation_input_fingerprint` | 64 lowercase ASCII hexadecimal characters |
| `expected_retirement_target_date` | canonical real ISO date `YYYY-MM-DD` |

Reject missing or extra keys, invalid types, invalid hash syntax and invalid
calendar dates before touching the Session. There is no actor, target amount,
comparable amount, basis, source list or fingerprint supplied by the caller.

## 5. One-snapshot producer composition

RMIGA owns one pristine read-only transaction and invokes one bounded internal
CMIA composition under that transaction. The bounded return has exactly:

- `cmia_result`: the exact result that public CMIA would return; and
- `target`: the exact accepted RIT result already used by that CMIA evaluation.

The bounded CMIA interface must reuse CMIA's actual accepted in-snapshot RTICB
evidence path. It must not perform a second RIT read, a second CMIA evaluation,
open another Session, or reconstruct a target from CMIA fields. Refactoring
CMIA to expose this bounded evidence must preserve public CMIA output bytes,
field inventory, fingerprints, exceptions and transaction behavior.

RMIGA verifies the public CMIA result using the accepted CMIA validator and
verifies the RIT result using the accepted RIT closed schema and fingerprint
contracts. A hash match alone never substitutes for complete schema and
semantic validation.

## 6. Transaction ownership and cleanup

1. A request-invalid call issues no SQL.
2. A Session with an existing transaction or nonempty `new`, `dirty` or
   `deleted` state is rejected without modifying caller state.
3. Supported databases are PostgreSQL and the established SQLite test adapter.
4. PostgreSQL uses `REPEATABLE READ READ ONLY`; no lock, write, flush, commit or
   retry is permitted. SQLite tests use the accepted CMIA snapshot convention.
5. Ownership begins only after actual SQLAlchemy connection acquisition, or
   when a failed acquisition demonstrably autobegan a transaction as reported
   by `db.in_transaction()`.
6. Retain the actual acquired Connection. On every success, block or exception,
   roll back the owned transaction exactly once.
7. If rollback succeeds, return the constructed result or re-raise the original
   exception unchanged.
8. If rollback fails, the rollback exception takes precedence. Attempt
   invalidation on the retained Connection when available, then permanently
   prevent Session reuse. Secondary invalidation/cleanup failures never replace
   the rollback exception.
9. A failure before ownership does not trigger rollback or invalidate a
   caller-owned Session. A partial acquisition that autobegins a transaction
   does require owned cleanup even if no Connection was returned.

## 7. Validation and failure precedence

Apply the first applicable stage in this exact order:

1. `request_validation` — closed request and canonical values.
2. `snapshot_admission` — pristine Session, supported dialect, snapshot setup.
3. `cmia_authority` — exact accepted CMIA success/block schema and fingerprint.
4. `target_authority` — exact accepted RIT schema, result fingerprint,
   confirmation and readiness.
5. `cross_authority_identity` — client, planning identity, retirement date and
   RIT target semantic/result fingerprints.
6. `basis_compatibility` — currency, income basis, price basis and nullable
   price-reference date.
7. `amount_authority` — canonical RIT target decimal and canonical CMIA total
   rational.
8. `arithmetic` — exact subtraction and sign classification.
9. `result_identity` — closed result schema, canonical serialization and hash.
10. transaction cleanup — rollback failure overrides every prior outcome.

A valid CMIA `BLOCK_NO_TOTAL` is handled at stage 3 and returns
`BLOCK_NO_GAP`; stages 4 through 9 are not evaluated from rejected or absent
numeric evidence. A valid CMIA `COMPLETE` combined with anything other than the
same valid current RIT authority is an integrity contradiction and raises; it
is never converted to zero or a professional block.

## 8. Exact amount representation and arithmetic

### 8.1 RIT target

Use the exact canonical positive decimal string at `target.monthly_amount`.
For `W.F`, let `C` be the integer formed by concatenating `W` and `F`, and let
`s=len(F)`; absent a decimal point, `s=0`. The exact target rational is
`C/10**s`, reduced by gcd. No binary float, quantization or display rounding is
permitted. The inherited RIT contract already limits the canonical target to
18 whole digits and six fractional digits.

### 8.2 CMIA total

Accept only CMIA's canonical rational object with exactly:
`numerator`, `denominator`, `currency`, `frequency`. Numerator is canonical
nonnegative ASCII integer text, denominator is canonical positive ASCII integer
text, denominator is positive, gcd is 1, zero is `0/1`, currency is `ILS`, and
frequency is `MONTHLY`.

### 8.3 Gap

For target `a/b` and comparable income `c/d`, compute
`(a*d - c*b)/(b*d)` and reduce by gcd. Denominator is always positive. The gap
numerator is canonical signed integer text matching `0|-?[1-9][0-9]*`; zero is
`0/1`. No intermediate rounding, decimal context, tolerance, saturation or
RMIGA-owned numeric bound is authorized.

`gap_state` is determined solely from the reduced numerator:

- `> 0`: `SHORTFALL`;
- `= 0`: `EQUAL`;
- `< 0`: `SURPLUS`.

Host resource failures remain technical exceptions. They never produce a
partial amount or professional interpretation.

## 9. Complete result schema

Schema version:
`RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_V1`.

Exact top-level keys:

`schema_version`, `result_state`, `client_id`,
`planning_calculation_input_fingerprint`, `retirement_target_date`,
`target_result_fingerprint`, `target_semantic_fingerprint`,
`cmia_result_fingerprint`, `target_income_basis`, `target_price_basis`,
`target_price_reference_date`, `target_monthly_amount`,
`comparable_monthly_income`, `monthly_gap`, `gap_state`,
`included_contributions`, `excluded_source_ids`, `source_count`,
`result_fingerprint`.

Binding rules:

- `result_state="COMPLETE"`.
- Identity and basis fields exactly equal the validated same-snapshot RIT and
  CMIA fields.
- `target_monthly_amount`, `comparable_monthly_income` and `monthly_gap` each
  contain exactly `numerator`, `denominator`, `currency`, `frequency`.
- `included_contributions`, `excluded_source_ids` and `source_count` are exact
  deep copies of the validated CMIA result, preserving order, all source
  identities and all contribution fingerprints. RMIGA neither filters nor
  reorders them.
- No timestamp, actor, rounded display amount, adequacy conclusion,
  recommendation or client-supplied arithmetic appears.

## 10. Blocked result schema

Schema version:
`RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_NO_GAP_V1`.

Exact keys:

`schema_version`, `result_state`, `client_id`,
`supplied_planning_calculation_input_fingerprint`,
`supplied_retirement_target_date`, `observed_cmia_result_fingerprint`,
`observed_cmia_failure_stage`, `observed_cmia_failure_detail_code`,
`observed_cmia_blocked_source_ids`, `failure_stage`,
`failure_detail_code`, `result_fingerprint`.

Rules:

- `result_state="BLOCK_NO_GAP"`.
- The only admitted source is a fully validated CMIA `BLOCK_NO_TOTAL`.
- `failure_stage="upstream_authority"` and
  `failure_detail_code="RMIGA_COMPARABLE_INCOME_BLOCKED"`.
- Observed CMIA fields reproduce the validated CMIA block exactly.
- `observed_cmia_blocked_source_ids` preserves the CMIA sorted list exactly.
- No target amount, comparable amount, gap, sign, subtotal, contribution or
  inferred zero is present.

## 11. Fingerprints and canonical serialization

Serialization for every RMIGA fingerprint is UTF-8 JSON with
`ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`,
`allow_nan=False`, followed by lowercase SHA-256. There is no Unicode
normalization and no mutation after hashing.

Namespaces and complete preimages:

- Complete result namespace:
  `RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_JSON_V1`;
  `{"contract":namespace,"result":<complete result without result_fingerprint>}`.
- Block result namespace:
  `RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_JSON_V1`;
  `{"contract":namespace,"result":<blocked result without result_fingerprint>}`.

All listed nullable keys are present with JSON null. No optional key may be
silently omitted. Independent encoders must reproduce exact bytes and digests.

## 12. Internal exceptions

RMIGA-owned failures are raised, never returned as complete/block results:

| Stage | Exact code |
|---|---|
| `request_validation` | `RMIGA_REQUEST_SCHEMA_INVALID` |
| `request_validation` | `RMIGA_CLIENT_ID_INVALID` |
| `request_validation` | `RMIGA_EXPECTED_PLANNING_FINGERPRINT_INVALID` |
| `request_validation` | `RMIGA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID` |
| `snapshot_admission` | `RMIGA_REQUIRES_FRESH_TRANSACTION` |
| `snapshot_admission` | `RMIGA_UNSUPPORTED_DATABASE` |
| `cmia_authority` | `RMIGA_CMIA_RESULT_INVALID` |
| `target_authority` | `RMIGA_TARGET_AUTHORITY_INVALID` |
| `cross_authority_identity` | `RMIGA_CROSS_AUTHORITY_IDENTITY_MISMATCH` |
| `basis_compatibility` | `RMIGA_BASIS_IDENTITY_MISMATCH` |
| `amount_authority` | `RMIGA_TARGET_AMOUNT_INVALID` |
| `amount_authority` | `RMIGA_COMPARABLE_AMOUNT_INVALID` |
| `arithmetic` | `RMIGA_ARITHMETIC_ERROR` |
| `result_identity` | `RMIGA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED` |

The proposed immutable internal exceptions carry exact `stage`, `code` and
validated `client_id|None`, contain no unverified monetary evidence in their
message, and preserve a technical cause through exception chaining where
applicable. Original producer, database, timeout and host-resource exceptions
propagate unchanged after successful cleanup. RMIGA never manufactures a CMIA
or RIT failure envelope.

## 13. Ordinary acceptance criteria

| ID | Required executable proof |
|---|---|
| `RMIGA-AC-001` | Exact package identity, Class A status, base and exclusions; implementation remains unauthorized. |
| `RMIGA-AC-002` | Closed request validation precedes every database interaction. |
| `RMIGA-AC-003` | One same-snapshot bounded CMIA composition supplies the exact CMIA result and the exact RIT target it used; no second reader or Session. |
| `RMIGA-AC-004` | A current confirmed RIT and CMIA complete result bind client, planning fingerprint, retirement date and target semantic/result fingerprints exactly. |
| `RMIGA-AC-005` | Currency, income basis, price basis and nullable reference date match exactly. |
| `RMIGA-AC-006` | Positive difference yields exact reduced rational and `SHORTFALL`. |
| `RMIGA-AC-007` | Equal amounts yield exactly `0/1` and `EQUAL`. |
| `RMIGA-AC-008` | Negative difference retains a negative numerator and yields `SURPLUS`. |
| `RMIGA-AC-009` | RIT targets with up to six fractional digits subtract exactly from mixed CMIA rational denominators without rounding. |
| `RMIGA-AC-010` | Empty/all-excluded CMIA complete zero remains valid and gap equals the exact positive RIT target. |
| `RMIGA-AC-011` | Source contribution order, source identities, excluded IDs, source count and contribution fingerprints are preserved byte-for-byte from CMIA. |
| `RMIGA-AC-012` | Every valid CMIA blocked variant yields the exact block schema and no numeric fields. |
| `RMIGA-AC-013` | Complete and blocked result schemas have exact key sets, explicit nulls and independently reproduced fingerprint goldens. |
| `RMIGA-AC-014` | PostgreSQL proves one repeatable-read/read-only snapshot, no writes/commit/retry, and visibility consistency under a concurrent upstream change. |
| `RMIGA-AC-015` | Success, block and technical-exception paths roll back; partial acquisition and rollback-failure precedence permanently prevent unsafe Session reuse. |
| `RMIGA-AC-016` | Accepted public RIT and CMIA outputs, fingerprints and failure behavior remain unchanged. |
| `RMIGA-AC-017` | No migration, endpoint, frontend surface or persistent RMIGA record is introduced. |
| `RMIGA-AC-018` | Focused affected regressions and governance inventory detect forbidden downstream, API, schema or authority expansion. |

Acceptance range: `RMIGA-AC-001` through `RMIGA-AC-018`; count: `18`.

## 14. Negative and mutation-sensitive acceptance

| ID | Prohibited outcome / required kill |
|---|---|
| `RMIGA-NAC-001` | Caller supplies or overrides target, comparable income, source identity, basis or actor. |
| `RMIGA-NAC-002` | A second RIT/CMIA read, nested public transaction, new Session, write, flush, commit or retry occurs. |
| `RMIGA-NAC-003` | A CMIA block, partial subtotal or absent total produces numeric gap. |
| `RMIGA-NAC-004` | Malformed or rehashed forged CMIA/RIT evidence is accepted. |
| `RMIGA-NAC-005` | Client, planning, date, target or CMIA fingerprint mismatch is accepted. |
| `RMIGA-NAC-006` | Currency, gross/net, nominal/real or reference-date mismatch is converted or ignored. |
| `RMIGA-NAC-007` | Binary float, tolerance, quantization, rounding or saturation affects subtraction. |
| `RMIGA-NAC-008` | A surplus is clamped to zero or relabeled as adequacy. |
| `RMIGA-NAC-009` | Source contributions are filtered, reordered, duplicated or reconstructed outside CMIA. |
| `RMIGA-NAC-010` | Result fingerprint omits sign, amount, basis, source binding or upstream identity. |
| `RMIGA-NAC-011` | A raised technical/integrity error is converted to professional block. |
| `RMIGA-NAC-012` | Rollback failure allows a result to escape or the failed Session to be reused. |
| `RMIGA-NAC-013` | An endpoint, UI, table, migration or deployment change is introduced. |
| `RMIGA-NAC-014` | Tax, normalization, funding, withdrawal, recommendation, forecast or scenario semantics are introduced. |
| `RMIGA-NAC-015` | Upstream RIT or CMIA behavior/fingerprint changes for RMIGA convenience. |
| `RMIGA-NAC-016` | Downstream or production readiness is inferred from Definition acceptance. |

Material mutation controls must use unchanged ordinary oracles and demonstrate
PASS -> actual production mutation reached -> FAIL -> restoration -> PASS for:

1. bounded same-snapshot producer composition;
2. target/CMIA fingerprint and planning/date identity bindings;
3. income/price/reference-date compatibility;
4. signed exact subtraction and sign classification;
5. source-binding preservation;
6. result fingerprint preimages;
7. forbidden commit/write/second reader; and
8. rollback-failure precedence and Session non-reuse.

Acceptance range: `RMIGA-NAC-001` through `RMIGA-NAC-016`; count: `16`.

## 15. PostgreSQL and concurrency evidence

A future authorized implementation must use real PostgreSQL for:

- `REPEATABLE READ READ ONLY` transaction establishment;
- proof that no RMIGA SQL writes or commit occur;
- concurrent RIT or CMIA-contributor mutation after the snapshot begins, proving
  the reader cannot mix old target with new comparable income or vice versa;
- technical DB failure rollback;
- partial connection acquisition ownership;
- rollback failure, retained-Connection invalidation and Session non-reuse.

SQLite may prove deterministic value and schema behavior only. It is not proof
of PostgreSQL isolation, connection, rollback or concurrency semantics.

## 16. Stop conditions

Stop before implementation or stop the affected implementation path if:

1. `RMIGA_SINGLE_SNAPSHOT_COMPOSITION_UNAVAILABLE` — the actual RIT result used
   by CMIA cannot be exposed without a second read or public CMIA drift.
2. `RMIGA_UPSTREAM_IDENTITY_AMBIGUOUS` — accepted RIT and CMIA identities cannot
   be matched exactly.
3. `RMIGA_BASIS_COMPATIBILITY_AMBIGUOUS` — currency, income basis, price basis or
   reference-date equality would require a new professional rule.
4. `RMIGA_AMOUNT_AUTHORITY_AMBIGUOUS` — exact target or comparable amount cannot
   be obtained from accepted owner evidence.
5. `RMIGA_ARITHMETIC_RULE_AMBIGUOUS` — exact signed subtraction would require
   rounding, tolerance or an owner decision not stated here.
6. `RMIGA_TRANSACTION_OWNERSHIP_CONTRADICTION` — one-snapshot ownership cannot
   preserve accepted upstream behavior and cleanup guarantees.
7. `RMIGA_UPSTREAM_SEMANTIC_CHANGE_REQUIRED` — implementation would change RIT,
   CMIA or their fingerprints rather than consume them.
8. `RMIGA_SECURITY_OR_SOURCE_ISOLATION_WEAKENED`.
9. `RMIGA_SCOPE_EXPANSION_REQUIRED` — implementation needs persistence, API/UI,
   tax, funding, adequacy, recommendation, scenario or deployment behavior.

Stop-condition range: item 1 through item 9; count: `9`.

## 17. Implementation surface and next gate

A future separately authorized implementation is expected to add one internal
RMIGA service and focused tests, plus the smallest bounded CMIA internal
evidence-returning adapter needed by Section 5. No model, schema migration, API
route or frontend file is authorized by this Definition.

Because RMIGA consumes two accepted authorities and a material transaction
boundary, Governance v1.1 requires a bounded pre-implementation contract
enumeration after independent Definition acceptance and Definition closure on
master. The enumeration must cover exact valid/invalid RIT and CMIA state
combinations, amount forms, failure envelopes, mutation controls and reusable
accepted harnesses. It is not a second Definition and grants no implementation
authority.

No unresolved professional decision is presently identified. Any later need to
interpret shortfall adequacy, fund it, normalize bases, convert tax treatment or
present it to a client is outside RMIGA and requires a separate owner decision
and package authorization.

RMIGA_DEFINITION_CANDIDATE_READY_FOR_INDEPENDENT_AUDIT
