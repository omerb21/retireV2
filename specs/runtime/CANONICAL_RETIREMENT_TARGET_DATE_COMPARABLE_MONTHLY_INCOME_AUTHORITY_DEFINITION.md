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

## Contract details requiring resolution before independent acceptance
1. Exact runtime path for validated, unrounded RTISA monthly equivalents, and proof of one-to-one binding to CRTISBA amount authority without re-executing upstream logic.
2. Exact request, success and blocked output schema; closed fields, status vocabularies and error precedence.
3. Canonical numerator/denominator or Decimal format, reduction, size limits and exact serialization.
4. Fingerprint contract strings and precise field-by-field JSON preimages for included contribution, total and blocked result.
5. Precise partial-total and completeness behavior when any source requires normalization or has unresolved basis.
6. Read-only transaction failure behavior and regression-sensitive negative oracle matrix.

These six items are acceptance blockers until specified from repository-authoritative evidence or a genuine professional choice. They are not implementation permissions.

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

DEFINITION_DRAFT_NOT_ACCEPTED
