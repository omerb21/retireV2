# Canonical Retirement Target-Date Comparable Monthly Income Authority

- Package: CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_AUTHORITY
- Classification: CLASS A / COMPLEX CLASS A
- Governance: RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1
- Baseline master: 0f9db6656c9dbbb2aea6f4dc49c367a5dde3245f
- Status: DEFINITION_DRAFT_ONLY
- Implementation: NOT_AUTHORIZED
- Downstream: NOT_AUTHORIZED
- Production readiness: NOT_CLAIMED

## Objective
Specify one authoritative, deterministic, read-only monthly income total built solely from source amounts whose RTICB V2 classification is DIRECTLY_COMPARABLE. This draft is not implementation authorization.

## Upstream authority
Consume accepted RIT, RTISA, CRTISBA, and RTICB outputs in one consistent read snapshot. RIT owns target and comparison basis. RTISA owns source admission and precise monthly equivalent amounts. CRTISBA owns amount authority and source-basis identities. RTICB owns the classification, source universe, blockers and comparison fingerprints.

## Proposed invariants
- Every valid admitted DIRECTLY_COMPARABLE source contributes exactly once, by canonical source ID.
- NOT_ADMITTED, NORMALIZATION_REQUIRED and BASIS_UNRESOLVED never contribute.
- A missing or invalid authoritative amount cannot silently become zero.
- Identity, source version, admission, RTICB entry and result fingerprint, and CRTISBA amount authority must validate before contribution.
- Never perform tax, currency, GROSS/NET or price-basis conversion, funding, gap/surplus, scenarios or recommendations.
- Never use UI-rounded amounts for arithmetic.
- Compute exact rational or Decimal sum using one specified canonical arithmetic format.
- A legitimately empty or fully excluded collection produces zero comparable subtotal, not a professional conclusion that target income is met.
- Any partial comparable subtotal must be explicitly distinguished from a complete all-sources income total.
- Preserve complete source-universe coverage, determinism, immutable fingerprints, and read-only transaction ownership.

## Original contract gaps and their resolution status
1. RTISA numeric payload and CRTISBA binding are now identified in executable code; the new one-snapshot evidence-carrying internal API still requires detailed contract acceptance.
2. Request and COMPLETE/BLOCK_NO_TOTAL output schemas are proposed below; corruption/error stage precedence remains acceptance-critical.
3. Exact rational reduction/serialization is proposed below; approved source-derived numeric resource limits still require proof.
4. Fingerprint namespaces and preimages are proposed below, subject to golden-vector independent validation.
5. Proposed complete-only output and non-ready block are defined below; no partial amount is public.
6. Transaction invariant and negative acceptance controls are proposed below; implementation-route mutation evidence remains future work.

The verified producer findings and proposed V1 execution contract below resolve the direction of these items but do not supersede acceptance of the exact internal producer composition API, error precedence, or source-bound precision limits. No implementation permission follows from this draft.

## Candidate acceptance criteria
AC-01: exact allowed source set and no double-counting.
AC-02: one validated authoritative amount per included source.
AC-03: exact arithmetic and deterministic amount representation.
AC-04: legitimate zero-source behavior without misleading completeness.
AC-05: sorted canonical contribution and noncontribution identities.
AC-06: independently reconstructable result and error fingerprints.
AC-07: strict classification and amount fingerprint validation.
AC-08: single-snapshot, read-only, no new DB session, commit or write.
AC-09: distinct domain blocked versus technical exception boundaries.
AC-10: mutation-sensitive tests detect tampering, duplicate counts and substitution of rounded amounts.

## Stop conditions
SC-01: accepted upstream contracts cannot supply or prove exact amount binding.
SC-02: required arithmetic, fingerprint or failure contracts remain ambiguous.
SC-03: a partial subtotal could be presented as complete expected income.
SC-04: any new source interpretation, normalization or professional rule is required.
SC-05: producer snapshot or fingerprint invariants cannot be preserved.

## Next action
Read-only targeted contract resolution from accepted upstream service code and definitions; expand this same file to a complete executable Definition candidate, then request ONE consolidated independent Definition Acceptance. Do not implement or merge this unaccepted draft.


## Verified producer-path findings (repository master)

These are inspected executable facts, not assumed new authority:

1. `retirement_target_date_income_comparison_basis_service.assess` currently starts a fresh PostgreSQL REPEATABLE READ READ ONLY / SQLite snapshot, calls RIT `assess_in_snapshot`, then CRTISBA `derive_in_snapshot`, validates producer envelopes, and returns only the classification. The comparison result exposes `source_comparisons`, `comparison_input_fingerprint`, `comparison_result_fingerprint`, `crtisba_result_fingerprint`, `target_result_fingerprint` and `target_semantic_fingerprint`, **not monthly amount values**.
2. `retirement_target_date_income_source_basis_service.derive_in_snapshot` obtains an RTISA output by its internal `_derive_snapshot` flow and calls RTISA `read_in_snapshot`, then constructs `CRTISBA_COLLECTION_RESULT_V1`. The CRTISBA public collection carries `rtisa_admission_result_fingerprint` and entries with `amount_authority_fingerprint`, but does **not** expose the complete RTISA amount payload.
3. RTISA `_pension_entry` provides `monthly_equivalent = {numerator: unquantized_target_monthly_amount, denominator: "1"}`; `native_amount` carries a different final/display pension amount. The unquantized amount must be the only aggregation input.
4. RTISA `_recurring_entry` provides `monthly_equivalent = {numerator: canonical native amount, denominator: "1" | "3" | "12"}` as determined by its own frequency table. This is a rational monthly amount, and the downstream authority must not replace it with display-rounded decimal arithmetic.
5. The existing RTICB result uses `direct_comparison_ready` only when every comparison entry is `DIRECTLY_COMPARABLE` or `NOT_ADMITTED`. A `NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED` source means direct total readiness is false. Exactly this predicate is a defensible gate for an **all-sources comparable total**, not a license to report a partial sum as complete.

### Exact interface gap to solve before acceptance

A downstream aggregate cannot safely take only public RTICB + CRTISBA responses and calculate a verified amount: neither exposes the numeric RTISA monthly equivalent; an amount-authority fingerprint is non-invertible. The eventual implementation must define a **single-snapshot internal producer composition** which returns both the validated RTICB classification and the exact RTISA entry payload bound to the same CRTISBA fingerprint, without invoking separate public readers/sessions or changing source owner authority. The contract must name that internal composition interface and prove no producer is recomputed in a different snapshot. Invoking `RTICB.assess` and then `RTISA.read` separately is forbidden.

### Safe proposed completion semantics

A canonical **complete total** is available only when RTICB reports `classification_complete = true` and `direct_comparison_ready = true`, all accepted RTISA identities/amount bindings validate, and every `DIRECTLY_COMPARABLE` source contributes once. When any source is normalization-required or unresolved, return a blocked/not-ready outcome for the authoritative complete total. A diagnostic subtotal may be considered separately but cannot be surfaced or fingerprinted as the complete total without a distinct approved contract. No new professional choice is required for the fail-closed complete-total policy.

### Deterministic arithmetic proposal for independent review

Parse RTISA numerator and denominator from their **existing exact string representation** using decimal/integer arithmetic. For each admitted directly comparable source, treat `numerator / denominator` as an exact rational, sum over source IDs in canonical sorted order with integer numerator/positive denominator arithmetic, then reduce by integer gcd and require a positive denominator. Do not quantize recurring thirds or convert through binary float. Canonical serialization proposal: numerator and denominator are ASCII signed/unsigned base-10 integer strings without leading zeros, with zero encoded as `{"numerator":"0","denominator":"1"}`. This is a new total-output proposal, not a claim that upstream currently exports reduced integer numerator strings. If an upstream decimal cannot be parsed exactly within approved limits, stop rather than round.

### Acceptance-critical unresolved engineering proof

The precise allowed internal composition entrypoint, full closed result/failure schemas and canonical JSON preimages are still to be locked. An independent reviewer must not accept this draft as a final executable contract until those are complete. The immutable upstream acceptance identities must be preserved.


## Exact proposed CMIA V1 execution contract

This section is a normative candidate for independent acceptance. It does not alter accepted upstream contracts.

### Request and execution entrypoint

`assess(db: Session, request: Mapping[str, Any]) -> dict` accepts precisely:
`client_id` (strict positive integer, not bool),
`expected_planning_calculation_input_fingerprint` (64 lowercase hex SHA-256),
`expected_retirement_target_date` (canonical YYYY-MM-DD calendar date).
Reject extraneous/missing fields before any DB operation. New public route/UI are outside this Definition package.

The service owns one fresh, pristine, read-only snapshot: PostgreSQL REPEATABLE READ READ ONLY, or project-supported SQLite BEGIN; prohibit preexisting transaction, pending state, fresh Session creation, writes, flush, commit or retry. It rolls back its owned snapshot on both successful read and failure.

A new **internal evidence-carrying composition**, used only inside the owner snapshot, must produce:
- the validated RTICB V2 result (exact unchanged public result schema),
- the CRTISBA collection identity whose fingerprint appears in that result,
- the same RTISA result/entries that CRTISBA consumed to generate that collection,
- the authoritative source/provenance context required to independently prove CRTISBA's amount-authority fingerprint.

The composition must execute producer logic once per owner-specific operation, share the one snapshot, and preserve current public `assess` and `derive_in_snapshot` result semantics. Specifically, it is forbidden to call `RTICB.assess(db,...)` and then `RTISA.read(db,...)`: those are independent public readers with independent transaction ownership. It is also forbidden to infer an RTISA amount from the CRTISBA amount hash. Existing `CRTISBA._derive_snapshot` currently includes `rtisa` in its internal snapshot object, while existing `CRTISBA.derive_in_snapshot` discards it from the public collection: this is the concrete integration seam to expose through a new bounded internal API, not a reason to change CRTISBA public response fields.

### CMIA output vocabulary and completeness

- `COMPLETE`: the RTICB validated classification is `COMPLETE`, `classification_complete=true`, `direct_comparison_state=READY`, `direct_comparison_ready=true`; the exact source universe and RTISA/CRTISBA amount identities have been reconciled and all directly comparable sources have validated exact amounts. Only this state returns `total_monthly_equivalent`.
- `BLOCK_NO_TOTAL`: upstream results are otherwise valid but the RTICB direct comparison result is `NOT_READY` due to `NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED`. Do not expose a numeric subtotal as a canonical total. Record the unchanged upstream blockers and source states in the failure identity.
- A structurally/fingerprint/identity-invalid upstream output, a missing amount for a supposedly directly comparable source, or a failed amount-authority reconciliation is a deterministic fail-closed error, **not** a valid zero/partial total.
- A raised producer/DB/serialization exception is a technical exception with rollback; it must not be converted to `BLOCK_NO_TOTAL`.

An empty RTICB source universe, or one containing exclusively valid `NOT_ADMITTED` entries, satisfies `COMPLETE` only if upstream genuinely reports complete/direct-ready classification. The exact total is zero and the contributor list is empty.

### Exact CMIA success wire shape

Schema: `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_V1`.

Closed top-level keys:
`schema_version`, `result_state`, `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date`, `target_result_fingerprint`, `target_semantic_fingerprint`, `comparison_input_fingerprint`, `comparison_result_fingerprint`, `crtisba_result_fingerprint`, `rtisa_admission_result_fingerprint`, `target_income_basis`, `target_price_basis`, `target_price_reference_date`, `included_contributions`, `excluded_source_ids`, `total_monthly_equivalent`, `source_count`, `result_fingerprint`.

`result_state` is exactly `COMPLETE`; currency is ILS and time unit MONTHLY, represented in the nested total object and not inferred from UI labels. `included_contributions` is a list sorted strictly by source_id, with closed entry keys:
`source_id`, `source_kind`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`, `source_comparison_fingerprint`, `monthly_equivalent`, `contribution_fingerprint`.

Each entry `monthly_equivalent` is the exact canonical reduced rational `{ "numerator": "<signed base-10 integer>", "denominator": "<positive base-10 integer>", "currency": "ILS", "frequency": "MONTHLY" }`. No floats. `source_count` is the strict integer length of `included_contributions`. `excluded_source_ids` is sorted unique and exactly comprises RTICB `NOT_ADMITTED` IDs, including delegated aliases; excluded sources never get amount entries.

`total_monthly_equivalent` has exactly the same 4-key rational object, adding all included contributions; for the empty contributor set it is `{"numerator":"0","denominator":"1","currency":"ILS","frequency":"MONTHLY"}`.

### Exact rational arithmetic and canonicalization

For an upstream RTISA numerator string parse the exact finite decimal `n`, and for denominator parse exact positive decimal/integer `d`. Convert `n/d` to an integer fraction without rounding using the decimal coefficient and power-of-ten exponent, multiply rational numerator/denominator, reduce with gcd, make denominator positive, canonicalize negative zero to zero. Nonnegative RTISA values remain nonnegative; the CMIA total does not invent negative source income. The accepted source owner's finite amount limits and validity rules apply. Downstream implementation must also enforce a documented bounded integer/rational size limit derived from validated upstream values, preventing unbounded CPU/memory; any newly introduced narrower limit than upstream requires explicit Definition correction and independent evidence before acceptance.

For each source_id in strict sorted canonical order, add numerator and denominator by exact cross multiplication, reduce after each step, never round. Equivalent rational sources yield identical canonical contribution value and aggregate regardless of source iteration order.

### Fingerprints

Use exact canonical JSON serialization: `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False).encode("utf-8")`, then lowercase SHA-256.

- Contribution namespace `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_CONTRIBUTION_JSON_V1`; preimage `{"contract": <namespace>, "contribution": <the closed contribution object excluding contribution_fingerprint>}`.
- Result namespace `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_RESULT_JSON_V1`; preimage `{"contract": <namespace>, "result": <the closed top-level result excluding result_fingerprint>}`.
- Block namespace `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_JSON_V1`; preimage `{"contract": <namespace>, "result": <the closed block envelope excluding result_fingerprint>}`.

Exactly one fingerprint level for each; forbid timestamps, floats, arbitrary metadata, implicit stringification, display rounding or mutation after fingerprint construction.

### Blocked-result shape

Schema `CANONICAL_RETIREMENT_TARGET_DATE_COMPARABLE_MONTHLY_INCOME_BLOCK_NO_TOTAL_V1`.

Closed top-level keys:
`schema_version`, `result_state`, `client_id`, `supplied_planning_calculation_input_fingerprint`, `supplied_retirement_target_date`, `observed_comparison_result_fingerprint`, `observed_crtisba_result_fingerprint`, `observed_rtisa_admission_result_fingerprint`, `failure_stage`, `failure_detail_code`, `blocked_source_ids`, `result_fingerprint`.

`result_state=BLOCK_NO_TOTAL`; `failure_stage=comparability`; `failure_detail_code=CMIA_DIRECT_COMPARISON_NOT_READY`; `blocked_source_ids` equals sorted unique RTICB source IDs in `NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED`. No total or partial sum field. The three `observed_*` hashes are the accepted SHA-256 identities of the same validated snapshot.

Malformed requests and upstream corruption shall NOT reuse this professional block code. Their precise internal exception and stage/code taxonomy remains an independent acceptance blocker if not specified; technical failures must not be serialized as professional blocks.

### Non-negotiable negative criteria

NAC-01 no sum based only on classification without validated RTISA amount.
NAC-02 no second transaction for amount acquisition.
NAC-03 no double-count of delegated pension aliases.
NAC-04 no rounded native/display pension amount as contribution.
NAC-05 no normalization, tax or conversion.
NAC-06 no COMPLETE on any normalization-required or unresolved comparison state.
NAC-07 no numerical partial total in BLOCK_NO_TOTAL.
NAC-08 no silent zero substitute for invalid amount.
NAC-09 no mutation or unverified reuse of producer fingerprints.
NAC-10 no persistence, public route/UI or downstream authority.
NAC-11 no misleading source coverage; exclude only NOT_ADMITTED.
NAC-12 no technical-exception disguise as business/comparability block.

### Pre-implementation enumeration after Definition acceptance

Enumerate the exact RTISA/CRTISBA/RTICB producer-cross-product including empty, all excluded, pension, recurring monthly/quarterly/annual, mixed and delegated cases. Cover ready, normalization-required and unresolved source states; invalid amount source identity, fingerprint, denominator and precision; malformed near-miss evidence; own-transaction and cross-snapshot mutation controls; golden fingerprint preimages and delta reuse. Do not treat this enumeration as second semantic Definition.


## Final integration constraints and error ordering for candidate review

### Integration seam — required implementation API shape

A new, internal-only `derive_comparison_with_amount_evidence_in_snapshot(db, request)` shall own the shared snapshot evidence assembly. It returns an immutable-by-value bundle with exactly `comparison`, `target`, `crtisba_collection`, `rtisa`, and `amount_contexts`. It may use refactored internal existing producer functions but **must** preserve existing public result bytes and hashes. The current `CRTISBA._derive_snapshot` provides validated `planning`, `portfolio`, `rtisa` and `contexts` under one transaction. Consumers may not use the underscore-prefixed helper as a permanent external/public contract: promote a bounded internal producer entrypoint with contract tests. The `amount_contexts` binding is used for verification only, not as replacement amount authority. A successful bundle proves:
- `comparison.crtisba_result_fingerprint == crtisba_collection.result_fingerprint`;
- `crtisba_collection.rtisa_admission_result_fingerprint == rtisa.admission_result_fingerprint`;
- all RTICB source IDs equal RTISA source IDs, each exactly once, with the same admission, source version and source fingerprint;
- each included source's `amount_authority_fingerprint` equals its validated CRTISBA `amount_contexts[source_id].amount`, and the context is recomputed using the accepted CRTISBA exact preimage and source owner's exact amount;
- exact RIT and planning/date identities agree throughout.

The bundle must not be serializable as a new client-facing authority and shall not add mutable cache or persisted result. If preserving producer behavior requires more than a narrow internal refactor, stop for a scope-authority correction before coding.

### Deterministic CMIA stage precedence

Perform sequentially and stop at the first failure:
1. `request_validation`: strict request shape/type/hash/date before DB touch.
2. `snapshot_admission`: pristine session and supported dialect.
3. `target_authority`: accepted RIT schema, fingerprint, identity, readiness.
4. `crtisba_authority`: accepted CRTISBA blocked/schema/fingerprint states; original four upstream block identities preserved.
5. `cross_authority_identity`: client, planning fingerprint and target date.
6. `source_universe`: duplicate/missing/extra/unsorted IDs and RTICB/RTISA/CRTISBA identity correspondence.
7. `classification`: RTICB source states, entry/result fingerprints, direct-readiness consistency.
8. `amount_authority`: admitted source numeric payload shape, source amount fingerprint/preimage, unrounded pension amount and source-version binding.
9. `comparability`: legitimate `NOT_READY` classification yields `BLOCK_NO_TOTAL` without sum.
10. `aggregation`: canonical exact rational addition and bounds.
11. `result_identity`: canonical serialization/fingerprint.

For stages 1–8 and 10–11, contract-invalid and technical failures are never labeled valid professional `BLOCK_NO_TOTAL`. Fail closed with a stage-specific implementation exception instead. **Open acceptance issue:** exact stable exception code vocabulary for each invalid-contract stage must be independently defined before implementation. Preserve the original accepted RTICB failure envelope unchanged; CMIA cannot rewrite upstream failures.

### Size/precision protection

The RTISA recurring `_money` parser presently permits at most 12 significant integer digits and two fractional digits and returns a canonical 2-decimal string. Pension exact source amounts follow PTE's separate validated numeric contract and can have more decimals due to target-date accumulation. A global “two decimals only” restriction on CMIA inputs would therefore be incorrect. The eventual bounds must be derived from the current accepted PTE precision/range and maximum admitted sources; imposing tighter limits must be separately justified without rejecting valid producer values.

Rational parsing never accepts arbitrary unbounded input: accept only already-validated upstream numeric strings and enforce an engineering limit sufficient for their current authoritative maximum. Reject malformed decimal/exponent/scientific notation where not produced by accepted RTISA canonical serialization. Guard against huge intermediate integer multiplication before performing it. Preserve exactness for recurring denominators 1/3/12 and pension denominator 1.

### Contract acceptance status

All above are **proposed** package-local constraints, not an accepted source of authority. The unresolved exact technical exception-code set, proven upper arithmetic bounds and tested single-assembly integration API are blockers for declaring this draft `DEFINITION_ACCEPTED`. Their resolution is technical contract work, not a new owner choice. No subsequent feature and no implementation is authorized by drafting this text.

DEFINITION_DRAFT_NOT_ACCEPTED
