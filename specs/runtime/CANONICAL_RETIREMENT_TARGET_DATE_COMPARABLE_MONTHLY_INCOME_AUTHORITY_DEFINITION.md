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

DEFINITION_DRAFT_NOT_ACCEPTED
