# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY

## 1. Definition status and governance

- Package ID: `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY` (`RTICB`).
- Package class: `CLASS A / COMPLEX CLASS A`.
- Artifact status: `DEFINITION_DRAFT`.
- Governing protocol: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Binding owner decision: `OWNER-DECISION-RTICB-001`.
- Implementation: `NOT_AUTHORIZED`.
- Downstream implementation: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This Definition does not constitute Definition acceptance or implementation
authorization. After Definition acceptance and before any implementation
authorization, the protocol-required `PRE-IMPLEMENTATION CONTRACT ENUMERATION`
must be completed and accepted.

## 2. Objective and authority boundary

RTICB is a comparability authority only. It determines, deterministically and
per admitted target-date income source, whether the source's already-authoritative
native basis permits direct comparison with the confirmed retirement monthly
income target.

RTICB creates authority over:

1. the exact input identity used for a comparison assessment;
2. complete coverage of the current RTISA source universe;
3. one deterministic comparison classification per RTISA source entry;
4. ordered reasons supporting every non-direct classification;
5. whether classification completed successfully; and
6. whether the complete admitted source set is ready for a future *direct*
   income-total/gap comparison without normalization.

RTICB does not create authority over normalized amounts, tax treatment,
inflation, totals, gaps, coverage, eligibility, withdrawals, allocation,
optimization, or scenarios. It does not change any upstream authority.

## 3. Binding owner decision

`OWNER-DECISION-RTICB-001` is applied as follows:

- Direct income-basis compatibility is exact equality: `GROSS` with `GROSS`,
  or `NET` with `NET`.
- Direct price-basis compatibility is exact equality:
  `NOMINAL_AT_RETIREMENT_TARGET_DATE` with the same basis, or
  `REAL_AT_REFERENCE_DATE` with the same basis.
- When both price bases are `REAL_AT_REFERENCE_DATE`, both authoritative
  reference dates must be present and exactly equal.
- `UNKNOWN`, missing, malformed, or unsupported basis evidence is not directly
  comparable.
- A mismatch is classified; it is never silently normalized.
- RTICB may say that normalization is required, but it never calculates or
  supplies a normalized value.

## 4. Upstream authorities consumed

RTICB consumes exactly two current result authorities:

1. `CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY`, including its
   `target_result_fingerprint`, `target_semantic_fingerprint`, current/confirmed
   authority state, and the authoritative target fields `income_basis`,
   `price_basis`, and `price_reference_date`.
2. `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_AUTHORITY`
   (`RTISA`), including its `admission_result_fingerprint`, readiness and
   universe evidence, complete ordered source entries, admission states,
   upstream identities, native income basis, and native price evidence.

Those authorities already bind, transitively, the canonical planning input,
retirement target date, pension execution/portfolio, pension monthly amount
basis, pension temporal/indexation basis, and target-date resource-state
contracts. RTICB validates the supplied upstream identities; it does not
reconstruct those authorities or independently discover income sources.

## 5. Required upstream admissibility

A ready comparison result requires all of the following:

- both results belong to the requested positive integer `client_id`;
- both bind the same valid `planning_calculation_input_fingerprint`;
- both bind the same valid ISO `retirement_target_date`;
- the target result fingerprint and semantic fingerprint are valid and
  recompute exactly;
- the target is `CURRENT`, confirmed, and `target_ready = true`;
- the target currency is `ILS`;
- the target basis tuple is structurally valid under its accepted authority;
- the RTISA result fingerprint is valid and recomputes exactly;
- RTISA reports `COMPLETE_EVIDENCED`, `READY`, and `admission_ready = true`;
- RTISA source entries and included/excluded/unresolved ID partitions are
  complete, unique, sorted, disjoint, and exactly cover the entries; and
- every preserved upstream source and pension-result identity is valid.

If one of these conditions fails, RTICB fails closed. It must not repair,
reinterpret, partially consume, or mix the two authorities.

## 6. Source universe and coverage

The RTICB source universe is exactly the complete `source_entries` sequence in
the current RTISA result. No source is added, removed, deduplicated, joined, or
rediscovered by RTICB.

For every RTISA entry, RTICB emits exactly one comparison entry with the same
`source_id`. Source entries are ordered by ascending Unicode code-point order of
`source_id`, matching the canonical RTISA ordering. Duplicate, missing,
unexpected, empty, non-string, or out-of-order source IDs invalidate the whole
result.

Only entries whose RTISA `admission_state` is `INCLUDED` are economically
admitted comparison candidates. `EXCLUDED` and `UNRESOLVED` entries remain in
the result as explicit coverage evidence and cannot contribute to a future
direct total. RTICB never bypasses or upgrades RTISA admission state.

## 7. Authoritative basis projection

Each comparison entry preserves, without inference:

- target `income_basis`, `price_basis`, and `price_reference_date`;
- source `native_income_basis`;
- source `native_price_evidence.price_basis`;
- source `native_price_evidence.price_reference_date`;
- RTISA `admission_state` and `reason_codes`;
- RTISA upstream source identity; and
- the relevant target and RTISA fingerprints.

Tax characterization, source category, description, origin, pension type,
employment intent, or other professional knowledge must never be used to fill
or infer a missing basis field. They may remain provenance only.

## 8. Per-source classification taxonomy

The smallest binding state taxonomy is:

| State | Meaning |
|---|---|
| `DIRECTLY_COMPARABLE` | The source is admitted and every required basis dimension exactly matches the target. |
| `NORMALIZATION_REQUIRED` | The source is admitted, its relevant basis evidence is authoritative and known, but one or more dimensions differ from the target. |
| `BASIS_UNRESOLVED` | The source is admitted but required native basis evidence is unknown, missing, malformed, or unsupported. |
| `NOT_ADMITTED` | RTISA did not admit the source (`EXCLUDED` or `UNRESOLVED`); RTICB performs no basis comparison for it. |

Reason codes are a sorted unique list. Their closed vocabulary is:

- `RTICB_SOURCE_NOT_ADMITTED`
- `RTICB_SOURCE_ADMISSION_UNRESOLVED`
- `RTICB_INCOME_BASIS_UNKNOWN`
- `RTICB_INCOME_BASIS_MISMATCH`
- `RTICB_PRICE_BASIS_UNKNOWN`
- `RTICB_PRICE_BASIS_MISMATCH`
- `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`
- `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`

The state/reason mapping is exact:

- `DIRECTLY_COMPARABLE` has no reasons.
- `NORMALIZATION_REQUIRED` has one or more mismatch reasons and no unknown or
  not-admitted reason.
- `BASIS_UNRESOLVED` has one or more unknown/missing reasons. If both unresolved
  and mismatch conditions exist, `BASIS_UNRESOLVED` controls while every
  independently determinable mismatch reason is still preserved.
- `NOT_ADMITTED` has `RTICB_SOURCE_NOT_ADMITTED`; an upstream `UNRESOLVED` entry
  additionally has `RTICB_SOURCE_ADMISSION_UNRESOLVED`. No basis mismatch or
  unknown reason is emitted for a source that RTISA did not admit.

## 9. Classification algorithm

For each RTISA entry, in canonical source order:

1. If `admission_state != INCLUDED`, emit `NOT_ADMITTED` according to Section 8
   and stop classification for that entry.
2. Validate source native income basis. Values other than `GROSS` or `NET`
   produce `RTICB_INCOME_BASIS_UNKNOWN`. Otherwise, inequality with the target
   produces `RTICB_INCOME_BASIS_MISMATCH`.
3. Validate source native price basis. Values other than
   `NOMINAL_AT_RETIREMENT_TARGET_DATE` or `REAL_AT_REFERENCE_DATE` produce
   `RTICB_PRICE_BASIS_UNKNOWN`.
4. If the source price basis is known and differs from the target price basis,
   emit `RTICB_PRICE_BASIS_MISMATCH`. Reference dates are then not compared,
   because the price-basis mismatch already establishes the required
   normalization dimension.
5. If both price bases are `REAL_AT_REFERENCE_DATE`, require both reference
   dates to be valid ISO dates. A missing/malformed source date produces
   `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`; otherwise, inequality produces
   `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`.
6. If both price bases are `NOMINAL_AT_RETIREMENT_TARGET_DATE`, both reference
   dates must be null under their upstream contracts. A non-null value is an
   invalid upstream authority, not a normalization case.
7. Resolve the state from the reason set using Section 8.

Comparison never reads or changes amount fields. An admitted source with zero
amount is still classified because comparability is a basis property, not an
amount-materiality shortcut.

## 10. Downstream readiness model

RTICB separates two booleans and their states:

### 10.1 Classification completion

`classification_state = COMPLETE` and `classification_complete = true` only
when both upstream authorities are valid/current, the RTISA universe is
complete, and every RTISA source has exactly one valid RTICB entry.

A complete result may contain `NORMALIZATION_REQUIRED`, `BASIS_UNRESOLVED`, or
`NOT_ADMITTED` entries. Completion means the comparison question was answered;
it does not mean a direct total is safe.

### 10.2 Direct-comparison readiness

`direct_comparison_state = READY` and `direct_comparison_ready = true` only
when classification is complete and every RTISA `INCLUDED` source is
`DIRECTLY_COMPARABLE`.

An empty admitted source set is direct-comparison ready only when RTISA itself
is complete and ready. This readiness says that a future complete direct total
would omit no admitted source; it does not calculate or authorize that total.

Otherwise the state is `NOT_READY`, and aggregate blockers are the sorted unique
union of:

- `RTICB_NORMALIZATION_REQUIRED` when any admitted source has that state;
- `RTICB_BASIS_UNRESOLVED` when any admitted source has that state; and
- `RTICB_SOURCE_UNIVERSE_NOT_ADMITTED` when RTISA contains an `UNRESOLVED`
  source (normally prevented by ready RTISA, retained as fail-closed validation).

Future total/gap logic must not omit an admitted source with
`NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED`. It must stop until a separately
authorized authority resolves the basis or performs the required normalization.

## 11. Result contract

A successful result contains exactly:

- `schema_version`
- `client_id`
- `planning_calculation_input_fingerprint`
- `retirement_target_date`
- `target_result_fingerprint`
- `target_semantic_fingerprint`
- `rtisa_admission_result_fingerprint`
- `comparison_input_fingerprint`
- `target_basis`
- `source_comparisons`
- `directly_comparable_source_ids`
- `normalization_required_source_ids`
- `basis_unresolved_source_ids`
- `not_admitted_source_ids`
- `classification_state`
- `classification_complete`
- `direct_comparison_state`
- `direct_comparison_ready`
- `blockers`
- `comparison_result_fingerprint`

`target_basis` contains exactly `income_basis`, `price_basis`, and
`price_reference_date`. Each source comparison contains exactly:

- `source_id`
- `rtisa_admission_state`
- `source_upstream_identity`
- `source_income_basis`
- `source_price_basis`
- `source_price_reference_date`
- `comparison_state`
- `reason_codes`
- `source_comparison_fingerprint`

No normalized or calculated amount is present.

## 12. Determinism and fingerprints

All fingerprints are lowercase SHA-256 over UTF-8 canonical JSON with sorted
object keys, compact separators, `ensure_ascii = false`, and non-finite values
rejected. Arrays remain in their contractually defined canonical order.

Namespaces are versioned and distinct:

- `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V1`
- `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V1`
- `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V1`

`comparison_input_fingerprint` binds the client, planning identity, retirement
target date, target result/semantic fingerprints, and RTISA admission result
fingerprint.

Each `source_comparison_fingerprint` binds the input fingerprint plus the full
source comparison entry excluding that fingerprint. This keeps distinct source
identities distinct even when their basis classifications are identical.

`comparison_result_fingerprint` binds the result contract namespace and the
entire successful result excluding that fingerprint. Any source addition,
removal, reordering, upstream identity change, basis change, state change,
reason change, or readiness change therefore changes the result identity.

Actor metadata and wall-clock time are not RTICB inputs and must not appear in
its fingerprints.

## 13. Failure and fail-closed contract

Expected authority unavailability is represented by a deterministic
`block_no_result` envelope rather than a partial successful result. Its fields
are exactly:

- `schema_version`
- `client_id`
- supplied and observed planning fingerprints
- supplied and observed retirement target dates
- observed target result fingerprint, if valid
- observed RTISA result fingerprint, if valid
- `result_state = block_no_result`
- `failure_stage`
- `failure_detail_code`
- `result_fingerprint`

Failure stages are ordered:

1. `request_validation`
2. `snapshot_admission`
3. `target_authority`
4. `rtisa_authority`
5. `cross_authority_identity`
6. `source_universe`
7. `classification`
8. `result_identity`

Within a stage, detail codes are lexicographically ordered. Only the earliest
applicable failure is authoritative. Schema mismatch, malformed canonical data,
fingerprint mismatch/construction failure, stale identity, incomplete RTISA,
coverage mismatch, unsupported database, or unexpected authority exception
must not produce a ready or partial comparison result.

Infrastructure/database exceptions are technical failures and remain
exceptions after rollback; they are not converted into professional
classifications.

## 14. Transaction and execution boundary

One public RTICB operation receives one caller-supplied SQLAlchemy `Session` and
owns one transaction/snapshot for the complete target-plus-RTISA assessment.

- PostgreSQL uses one repeatable-read, read-only transaction.
- SQLite uses the repository's accepted equivalent test boundary.
- The operation requires a fresh session transaction state.
- All upstream reads used to produce the two consumed results occur within that
  same snapshot and supplied session.
- Public upstream endpoints/readers that open, commit, retry, or own another
  transaction must not be nested.
- No second session, intermediate commit, write, flush, autoflush, hidden retry,
  or cross-snapshot result reuse is permitted.
- Exactly one final transaction completion occurs after the full result is
  assembled and fingerprinted.
- Any failure rolls back the complete operation; a failed rollback invalidates
  the connection according to established repository discipline.

Implementation may expose/reuse non-public, non-owning upstream derivation
boundaries solely to preserve this snapshot discipline. Such extraction must
not change accepted upstream semantics.

## 15. Persistence, API, and UI posture

RTICB is a pure derived authority. No persistence requirement has been found.
The expected implementation introduces no table, column, migration, stored
decision, audit row, write command, or mutation endpoint.

No API or frontend surface is required for this package. A future consumer may
be authorized separately, but this Definition does not authorize exposure or
workflow changes.

## 16. Explicit exclusions

RTICB must not own or perform:

- tax calculation or tax characterization inference;
- gross-to-net, net-to-gross, gross-up, or net-down conversion;
- CPI calculation, price indexation, price normalization, reference-date
  conversion, or future inflation projection;
- income totals, income gaps, funding coverage, or resource eligibility;
- withdrawals, capital conversion, annuitization, allocation, optimization, or
  scenario execution;
- source discovery, admission, deduplication, identity resolution, or
  applicability decisions;
- changes to target, pension, RTISA, planning-input, resource-state, M09/M10,
  M11-M14, `02M`, or `M08E` semantics.

## 17. Expected implementation surface

Subject to later authorization, the expected minimum surface is:

- one backend pure-derived comparison service;
- focused unit/contract tests;
- focused PostgreSQL snapshot/boundary tests;
- governance inventory/traceability updates if required by current tests; and
- at most narrow non-public extraction in the two upstream services when needed
  to preserve the single-snapshot boundary without semantic change.

Expected absent surfaces: models, migrations, persistence schemas, write APIs,
frontend code, navigation, totals/gap engines, and normalization engines.

## 18. Acceptance criteria

- `AC-01`: package identity, class, governance version, and owner decision are explicit.
- `AC-02`: only the current target authority and current RTISA result are direct inputs.
- `AC-03`: target and RTISA client identity must match the request.
- `AC-04`: target and RTISA planning fingerprints must match exactly.
- `AC-05`: target and RTISA retirement target dates must match exactly.
- `AC-06`: target result and semantic fingerprints are independently validated.
- `AC-07`: RTISA result fingerprint is independently validated.
- `AC-08`: stale, unavailable, malformed, or non-ready target authority fails closed.
- `AC-09`: partial, unavailable, malformed, or non-ready RTISA fails closed.
- `AC-10`: source universe equals RTISA source entries exactly.
- `AC-11`: every RTISA entry has exactly one ordered comparison entry.
- `AC-12`: only RTISA `INCLUDED` entries undergo basis comparison.
- `AC-13`: excluded/unresolved RTISA entries remain explicit coverage evidence.
- `AC-14`: `GROSS/GROSS` and `NET/NET` income bases match directly.
- `AC-15`: known unequal income bases require normalization.
- `AC-16`: unknown/missing/unsupported income basis is unresolved.
- `AC-17`: equal nominal-at-target price bases match directly.
- `AC-18`: known unequal price bases require normalization.
- `AC-19`: unknown/missing/unsupported price basis is unresolved.
- `AC-20`: equal real price bases require equal valid reference dates.
- `AC-21`: missing/malformed real source reference date is unresolved.
- `AC-22`: unequal real reference dates require normalization.
- `AC-23`: nominal authorities require null reference dates and malformed upstream data fails closed.
- `AC-24`: classification reasons use only the closed vocabulary and canonical ordering.
- `AC-25`: unresolved evidence takes state precedence over known mismatches without hiding either reason.
- `AC-26`: zero-amount admitted sources are still classified.
- `AC-27`: classification completion is independent from direct-comparison readiness.
- `AC-28`: normalization-required sources permit a complete classification result but block direct comparison.
- `AC-29`: unresolved-basis sources permit a complete classification result but block direct comparison.
- `AC-30`: an empty admitted universe is ready only when RTISA is complete and ready.
- `AC-31`: no admitted source may be silently omitted from future total/gap readiness.
- `AC-32`: source ordering and every ID partition are deterministic.
- `AC-33`: input, entry, failure, and result fingerprints use distinct versioned namespaces.
- `AC-34`: source identity remains bound independently of equal basis semantics.
- `AC-35`: actor metadata and timestamps do not affect comparison fingerprints.
- `AC-36`: one supplied session and one snapshot cover all authoritative reads.
- `AC-37`: no second session, nested public reader, intermediate commit, write, flush, or hidden retry occurs.
- `AC-38`: expected unavailability yields the deterministic fail-closed envelope.
- `AC-39`: unexpected technical/database failures rollback and remain technical.
- `AC-40`: no persistence, migration, API, frontend, total/gap, or normalization behavior is introduced.

Acceptance range: `AC-01` through `AC-40` (40 criteria).

## 19. Negative acceptance criteria

- `NAC-01`: inferring gross/net from source category, tax labels, or pension type.
- `NAC-02`: inferring nominal/real basis from source origin or general knowledge.
- `NAC-03`: inventing a real-price reference date.
- `NAC-04`: treating `UNKNOWN` as a match.
- `NAC-05`: treating unequal known bases as directly comparable.
- `NAC-06`: performing gross/net conversion or tax calculation.
- `NAC-07`: performing CPI/indexation/reference-date conversion.
- `NAC-08`: emitting a normalized source amount.
- `NAC-09`: calculating income totals, gaps, coverage, or eligibility.
- `NAC-10`: independently discovering or rebuilding the source universe.
- `NAC-11`: bypassing RTISA admission state.
- `NAC-12`: dropping an admitted non-comparable source from readiness assessment.
- `NAC-13`: upgrading an excluded or unresolved source to admitted.
- `NAC-14`: accepting partial or non-ready RTISA as complete.
- `NAC-15`: accepting a stale or unconfirmed target authority.
- `NAC-16`: accepting mismatched client/planning/target identities.
- `NAC-17`: accepting malformed or non-recomputing upstream fingerprints.
- `NAC-18`: non-deterministic source, reason, blocker, or failure ordering.
- `NAC-19`: collapsing distinct source identities solely because their bases match.
- `NAC-20`: using actor/time metadata in semantic comparison identity.
- `NAC-21`: opening a second session or cross-snapshot authority read.
- `NAC-22`: nested public reader, intermediate commit, write/autoflush, or hidden retry.
- `NAC-23`: introducing persistence, schema, migration, API, or frontend scope.
- `NAC-24`: changing accepted upstream semantics to simplify RTICB.
- `NAC-25`: authorizing normalization, total/gap execution, or any downstream package.

Negative-acceptance range: `NAC-01` through `NAC-25` (25 criteria).

## 20. Stop conditions

- `SC-01`: an accepted upstream contract cannot expose its result within one RTICB snapshot without semantic change.
- `SC-02`: an admitted source requires a basis interpretation not already authoritative upstream.
- `SC-03`: target and source basis vocabularies conflict beyond exact mapping stated here.
- `SC-04`: an additional Owner/Product Decision is needed to classify a valid input combination.
- `SC-05`: complete coverage would require independent source discovery or bypassing RTISA.
- `SC-06`: correctness would require persistence, normalization, totals, gaps, tax, CPI, or scenario semantics.
- `SC-07`: implementation would require reopening a closed authority rather than narrow non-semantic extraction.
- `SC-08`: deterministic identity or single-snapshot behavior cannot be proven with the accepted repository contracts.

Stop-condition range: `SC-01` through `SC-08` (8 conditions). Encountering any
condition stops Definition/implementation progression and requires explicit
owner/governance resolution; no implementation workaround is implied.

## 21. Pre-implementation contract enumeration requirement

After Definition acceptance, the mandatory enumeration must cover at least:

- all upstream ready/unavailable/stale/malformed producer routes;
- every admitted income-basis and price-basis combination;
- nominal and real reference-date equality, mismatch, missing, and malformed cases;
- admitted, excluded, and unresolved RTISA states;
- empty, singleton, and multi-source universes;
- valid combinations and malformed near-misses;
- deterministic failure envelopes and precedence;
- fingerprint mutation controls for every bound input and non-input;
- source coverage/order mutations;
- single-session/snapshot transaction mutations; and
- reusable harnesses for later implementation acceptance.

The enumeration is not performed or accepted by this Definition draft.

## 22. Current decisions and unresolved matters

`OWNER-DECISION-RTICB-001` fully resolves the professional ownership boundary
needed for this draft. No additional Owner/Product Decision is unresolved.

Implementation remains `NOT_AUTHORIZED`. Downstream authorization remains
`NOT_AUTHORIZED`. Production readiness remains `NOT_CLAIMED`.
