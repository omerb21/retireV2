# Canonical Retirement Target-Date Comparable Monthly Income Authority (CMIA) — Definition Candidate

## 1. Identity and lifecycle
- Package: `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_AUTHORITY` (`CMIA`).
- Classification: `CLASS A / COMPLEX CLASS A`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Base master: `0f9db6656c9dbbb2aea6f4dc49c367a5dde3245f`.
- Status: `DEFINITION_CANDIDATE_PENDING_INDEPENDENT_ACCEPTANCE`.
- Implementation: `NOT_AUTHORIZED`; downstream: `NOT_AUTHORIZED`; production readiness: `NOT_CLAIMED`.

This consolidated text supersedes all earlier draft paragraphs on this branch. It does not change upstream accepted authority or implement a runtime service.

## 2. Purpose, exact meaning and exclusions
CMIA calculates **one complete comparable monthly-income total at the confirmed retirement target date**, denominated in ILS/month, summing each accepted RTICB V2 `DIRECTLY_COMPARABLE` entry once, using the exact RTISA source amount authority under the **same database read snapshot**. Sources marked `NOT_ADMITTED` contribute nothing. If *any* entry is `BASIS_UNRESOLVED` or `NORMALIZATION_REQUIRED`, CMIA returns no total and a professional `BLOCK_NO_TOTAL` result; never expose a partial comparable subtotal as the complete total.

An empty accepted source universe or an entirely `NOT_ADMITTED` universe may yield exact zero when RTICB is `COMPLETE` and direct-ready. Zero does not establish sufficiency relative to RIT. CMIA performs no GROSS/NET or nominal/real conversion, CPI, tax, benefit calculations, gap/surplus, funding, withdrawal, projection, scenario, client output or recommendation. It changes neither input facts nor authority over existing amounts.

## 3. Sole upstream owners and exact binding
- **RIT**: confirmed target, client, planning and target-date identity; currency, income basis, price basis and reference date; target semantic/result fingerprints.
- **RTISA**: admission, complete source universe, authoritative unrounded pension monthly equivalent and canonical recurring monthly-equivalent numerator/denominator, RTISA admission result fingerprint. Recurring `monthly_equivalent` numerator is the validated native 2-decimal amount and denominator is `"1"`, `"3"` or `"12"` for monthly/quarterly/annual. Pension numerator is the unquantized target-date amount, denominator `"1"`; rounded `native_amount` is forbidden as input.
- **CRTISBA**: canonical source/version/source-fingerprint/amount-authority binding; collection fingerprint and its RTISA admission fingerprint; the exact pension/recurring amount-authority preimages. Its public collection does **not** carry full numeric RTISA amounts.
- **RTICB V2**: full source-comparison universe, comparison states, source entry fingerprints, classification completeness, direct readiness, target and CRTISBA identities, comparison result/input fingerprints.

Do not invert a hash to infer a numeric amount; do not re-run a source under a different owner or snapshot. Source sets from the accepted RTICB result, CRTISBA collection and RTISA result must correspond exactly by sorted canonical ID, admission state and source fingerprint. **RTISA entries do not expose a `source_version` or `source_kind` field.** Those authoritative fields must be checked on RTICB/CRTISBA against the CRTISBA producer context and upstream Planning Input (pension version or recurring source-fingerprint version), rather than demanded from the RTISA public envelope. RTISA source kind is determined from its accepted canonical source identity and source-authority contract, not an invented RTISA field.

## 4. Execution and internal producer composition
Proposed Python entrypoint: `assess(db: Session, request: Mapping[str, Any]) -> dict`. Exact request keys: `client_id` (strict positive integer excluding bool), `expected_planning_calculation_input_fingerprint` (64 lowercase hex SHA-256), `expected_retirement_target_date` (canonical ISO calendar date). Reject invalid requests before touching the session.

The CMIA entrypoint owns a **single pristine read-only transaction**: no pre-existing transaction, dirty/new/deleted ORM state, new Session, autoflush, write, commit, retry, independently timed upstream reader or nested public reader. PostgreSQL uses REPEATABLE READ READ ONLY; SQLite testing follows the established RTICB snapshot semantics. Roll back the owned read transaction on result and exception, retaining the original exception class for technical failures.

The implementation must provide a **bounded internal evidence-carrying producer composition** under that same transaction, with logical return members `comparison`, `target`, `crtisba_collection`, `rtisa`, `amount_contexts`. These are *internal evidence*, not a new public RTICB or CRTISBA schema. Reuse/refactor existing pure producer functions so the result of current public `RTICB.assess` remains byte-for-byte and fingerprint-identical. `CRTISBA._derive_snapshot` currently holds validated `rtisa` and `contexts`, while `derive_in_snapshot` discards them for its public collection; expose the evidence through a properly bounded internal interface, **not** by independently calling RTICB.assess then RTISA.read or by permanently binding CMIA to a private implementation function.

Prove:
1. `comparison.crtisba_result_fingerprint == crtisba_collection.result_fingerprint`.
2. `crtisba_collection.rtisa_admission_result_fingerprint == rtisa.admission_result_fingerprint`.
3. RIT/client/planning/target-date identities match all outputs and request.
4. Every RTICB comparison source maps one-to-one to exactly one RTISA source and CRTISBA source-basis entry with identical admission and source fingerprint; source version is independently bound through the validated CRTISBA/Planning producer context, not a nonexistent RTISA field.
5. For each contributing source, the accepted CRTISBA amount-authority canonical preimage reconstructed from the producer's evidence equals the CRTISBA/RTICB published `amount_authority_fingerprint`. Do not treat matching arbitrary hashes or synthetic fixtures as authoritative proof.
6. Current accepted upstream result schemas, integrity rules, source ownership, failure modes and fingerprint constructions are unchanged.

If a bounded integration cannot preserve these invariants, stop before implementation and correct the Definition.

## 5. Contributor selection, completeness and evaluation order
The only accepted `COMPLETE` path is RTICB `classification_state=COMPLETE`, `classification_complete=true`, `direct_comparison_state=READY`, `direct_comparison_ready=true`, combined with fully validated producer identities and amounts.

All entries `DIRECTLY_COMPARABLE` must have RTISA admission `INCLUDED` and validated exact monthly equivalents, and must contribute **once** by canonical source ID. All `NOT_ADMITTED` entries, including delegated pension aliases, are noncontributing and listed separately. `NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED` makes the complete total `BLOCK_NO_TOTAL` even when some other sources are comparable; neither a partial subtotal nor a fabricated zero is returned.

Validate a successfully classified RTICB output, its source universe, target and fingerprints **before** concluding comparability readiness. For valid `NOT_READY`, do not require a missing monthly amount from an unresolved/noncontributing source and do not misreport a missing amount as corruption. For `READY`, validate all contributing amounts and bindings before summing. A validated **upstream RTICB failure** produces a separate CMIA `BLOCK_NO_TOTAL` envelope preserving the upstream failure identity. An invalid RTICB failure, inconsistent producer schema or amount-fingerprint mismatch does not become a professional block; it is a fail-closed integrity error. Unexpected database and producer exceptions remain technical exceptions.

## 6. Exact arithmetic
Use rational integer arithmetic, **never binary float or intermediate rounding**. Parse only upstream-owner validated finite nonnegative decimal numerator text with the source-owner's formatting/precision rules and its exact valid positive denominator string; convert each decimal coefficient and scale into a reduced integer numerator/positive denominator. Add by exact cross multiplication and gcd reduction in sorted canonical source-ID order. Serialize rational results as `{"numerator":"N","denominator":"D","currency":"ILS","frequency":"MONTHLY"}` with ASCII canonical integers, no leading zeros, positive denominator, gcd(N,D)=1, zero as `0/1`.

Portfolio PTE currently bounds source decimal coefficient to at most 100 digits and scale at most 100, while RTISA recurring `_money` accepts up to 12 whole digits and two fractional digits. Existing PTE pension aggregate's 97-integer-digit bound is **not** an all-source CMIA total limit. Reject malformed or resource-exhausting operands fail-closed, but do not impose an invented smaller valid-value range or silently round/cap. The implementation must prove a bounded resource strategy over the accepted finite source universe. If valid accepted inputs cannot be calculated under a justified bound, stop for a technical contract correction rather than misstate a result.

## 7. Success result: exact closed field inventory
Schema `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_V1`. Exact top-level fields:

`schema_version`, `result_state`, `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date`, `target_result_fingerprint`, `target_semantic_fingerprint`, `comparison_input_fingerprint`, `comparison_result_fingerprint`, `crtisba_result_fingerprint`, `rtisa_admission_result_fingerprint`, `target_income_basis`, `target_price_basis`, `target_price_reference_date`, `included_contributions`, `excluded_source_ids`, `total_monthly_equivalent`, `source_count`, `result_fingerprint`.

`result_state="COMPLETE"`. `source_count` is an integer equal to length of `included_contributions`. `excluded_source_ids` is a sorted unique list of exactly `NOT_ADMITTED` source IDs. Contributions are sorted strictly by source ID, with exact fields:

`source_id`, `source_kind`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`, `source_comparison_fingerprint`, `monthly_equivalent`, `contribution_fingerprint`.

Each `monthly_equivalent` and `total_monthly_equivalent` contains exactly `numerator`, `denominator`, `currency`, `frequency`, in canonical rational form above. No timestamps, display-rounded fields, inferred price adjustments or client-supplied amounts.

## 8. Blocked result: exact closed field inventory
Schema `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_NO_TOTAL_V1`. Exact fields:

`schema_version`, `result_state`, `client_id`, `supplied_planning_calculation_input_fingerprint`, `supplied_retirement_target_date`, `observed_comparison_result_fingerprint`, `observed_crtisba_result_fingerprint`, `observed_rtisa_admission_result_fingerprint`, `observed_upstream_failure_stage`, `observed_upstream_failure_detail_code`, `observed_upstream_failure_fingerprint`, `failure_stage`, `failure_detail_code`, `blocked_source_ids`, `result_fingerprint`.

`result_state="BLOCK_NO_TOTAL"`. Exactly two admitted cases:
- Valid RTICB classification `NOT_READY`: `failure_stage="comparability"`, `failure_detail_code="CMIA_DIRECT_COMPARISON_NOT_READY"`, blocked IDs are sorted unique IDs with `NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED`; three upstream failure fields are null.
- Valid RTICB blocked result: `failure_stage="upstream_authority"`, `failure_detail_code="CMIA_UPSTREAM_COMPARISON_BLOCKED"`, `blocked_source_ids=[]`; observed upstream failure stage/code/fingerprint reproduce accepted RTICB failure exactly.

A valid blocked result never contains a total or a subtotal. When an upstream result does not possess a given observed success fingerprint, the corresponding observed fingerprint field is null. All observed hash values are either canonical 64 lowercase hex or null, never a fabricated placeholder.

## 9. Canonical fingerprints
Canonical serialization: UTF-8 JSON with `ensure_ascii=False`, `sort_keys=True`, `separators=(",",":")`, `allow_nan=False`, lowercase SHA-256. Closed namespaces/preimages:
- Contribution: `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_CONTRIBUTION_JSON_V1`; `{"contract": namespace, "contribution": contribution without contribution_fingerprint}`.
- Success: `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_JSON_V1`; `{"contract": namespace, "result": success without result_fingerprint}`.
- Block: `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_JSON_V1`; `{"contract": namespace, "result": block without result_fingerprint}`.

No omitted optional keys other than fingerprints being calculated, no mutation after hashing, no undocumented Unicode normalization. Verify with independently reconstructed golden vectors before implementing.

## 10. Failure precedence and ownership
Stop at first applicable failure:
1. `request_validation`: invalid closed request (before DB).
2. `snapshot_admission`: session state/dialect.
3. `target_authority`: RIT accepted envelope, fingerprint, readiness.
4. `crtisba_authority`: accepted producer result or validated upstream block.
5. `cross_authority_identity`: client/planning/target identity.
6. `source_universe`: mismatch, unsorted, missing, duplicate or extra source identities.
7. `classification`: RTICB entry and result validity, direct-readiness coherence.
8. `comparability`: validated upstream block or RTICB NOT_READY; return admitted `BLOCK_NO_TOTAL` and no amount.
9. `amount_authority`: for ready candidates only, validate monthly amount, source/fingerprint and CRTISBA amount preimage.
10. `aggregation`: rational arithmetic and justified bounds.
11. `result_identity`: canonical serialization and digest.

CMIA-owned integrity/technical error names (not upstream professional blockers):
- `request_validation`: `CMIA_REQUEST_SCHEMA_INVALID`, `CMIA_CLIENT_ID_INVALID`, `CMIA_EXPECTED_PLANNING_FINGERPRINT_INVALID`, `CMIA_EXPECTED_RETIREMENT_TARGET_DATE_INVALID`.
- `snapshot_admission`: `CMIA_REQUIRES_FRESH_TRANSACTION`, `CMIA_UNSUPPORTED_DATABASE`.
- `target_authority`: `CMIA_TARGET_AUTHORITY_INVALID`.
- `crtisba_authority`: `CMIA_CRTISBA_AUTHORITY_INVALID`.
- `cross_authority_identity`: `CMIA_CROSS_AUTHORITY_IDENTITY_MISMATCH`.
- `source_universe`: `CMIA_SOURCE_UNIVERSE_MISMATCH`.
- `classification`: `CMIA_COMPARISON_RESULT_INVALID`.
- `amount_authority`: `CMIA_RTISA_AMOUNT_INVALID`, `CMIA_AMOUNT_AUTHORITY_FINGERPRINT_MISMATCH`.
- `aggregation`: `CMIA_AGGREGATION_NUMERIC_ERROR`.
- `result_identity`: `CMIA_RESULT_FINGERPRINT_CONSTRUCTION_FAILED`.

These CMIA integrity errors return **no total**, are distinct from `BLOCK_NO_TOTAL` and must preserve the original cause where technically applicable. Do not emit a fake RTICB failure; no new public endpoint or UI authorized. Within a stage, validate schema before fingerprints, identity before numeric aggregation; explicitly reject a malformed upstream block instead of accepting its claimed status.

## 11. Test and evidence contract
A future authorized implementation shall reuse the accepted RIT/RTISA/CRTISBA/RTICB transaction, source and fingerprint harnesses. Independent ordinary and mutation-sensitive cases must cover:
1. empty/all-excluded `COMPLETE` with zero sum and no contributions;
2. one pension (unrounded PTE amount), one monthly recurring, quarterly/annual recurring and mixed exact rational sums;
3. delegated pension alias excluded and no double counting;
4. sorted source order, source count and complete/excluded identity partitions;
5. RTICB `NOT_READY` with missing amount on unresolved source: valid block, not corrupt;
6. RTICB upstream valid block: preserved stage/code/hash; corrupt blocked hash: integrity failure;
7. one missing/duplicate/extra source or tampered source version/fingerprint or admission state;
8. inconsistent CRTISBA/RTISA result fingerprint or source amount authority fingerprint;
9. substitution of rounded pension amount for RTISA unquantized amount is detected;
10. zero/negative/malformed denominator and noncanonical decimal payload are rejected;
11. mutated contributor count, sorted order, amount or membership invalidates independently reconstructed canonical digest;
12. read-only single-snapshot DB proof, no commit/write/nested public reader and rollback on technical exception;
13. exact allowed response keys and explicit nulls, reproducible preimage bytes and SHA-256 golden vectors;
14. no change in accepted public RTICB and CRTISBA result bytes/fingerprints.

## 12. Negative acceptance criteria
- NAC-01: never include any source not `DIRECTLY_COMPARABLE`.
- NAC-02: never count a source twice, including pension delegation.
- NAC-03: never infer monetary values from RTICB classifications or hashes.
- NAC-04: never derive recurring frequency or pension amount independently of RTISA.
- NAC-05: never use displayed/quantized source amounts.
- NAC-06: never return numeric partial subtotal in a blocked result.
- NAC-07: never allow mismatched client/planning/date/source authority identity.
- NAC-08: never invent an amount or treat malformed source evidence as zero.
- NAC-09: never accept a forged fingerprint or unsorted/duplicate source set.
- NAC-10: never open a separate snapshot, write, flush, commit or retry.
- NAC-11: never relabel technical exception as a professional block.
- NAC-12: never add public API/UI, persistence or downstream authorization in this Definition.
- NAC-13: never infer conversion/tax/normalization/scenario/gap semantics.
- NAC-14: never weaken accepted producer contracts for a convenient aggregate.

## 13. Stop conditions
- SC-01: the proposed internal bundle cannot preserve current producer output semantics and single-snapshot transaction boundaries.
- SC-02: source-level amount authority cannot be reconstructed from accepted producer evidence.
- SC-03: the resource strategy would reject valid upstream amounts without accepted justification.
- SC-04: failure/identity precedence contradicts an accepted upstream error contract.
- SC-05: any new professional interpretation or unauthorized amount normalization is required.
- SC-06: independently reconstructable exact result and block fingerprint preimages cannot be demonstrated.
- SC-07: security or source/client isolation would be weakened.
- SC-08: ordinary and adversarial tests cannot detect an invalid sum or forged producer evidence.

## 14. Pre-implementation complex Class A enumeration and next gate
After **independent Definition Acceptance**, complete a bounded pre-implementation enumeration for all actual RTISA source amount shapes, CRTISBA current and excluded states, RTICB comparison states, direct-readiness transitions, malformed near-misses, one-snapshot composition and fingerprint vectors. The enumeration is **not** a second Definition and grants no implementation authority. Freeze the accepted Definition HEAD and complete governance's Definition manifest and master-closure gates before separately authorizing implementation; respect the protocol's exact gate order. No broad V1/V2 remapping, product discovery, tax/GAP package or production deployment.

DEFINITION_CANDIDATE_READY_FOR_INDEPENDENT_AUDIT
