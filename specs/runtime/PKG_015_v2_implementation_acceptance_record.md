# PKG-015 v2 Implementation Acceptance Record

## Record Identity

- Package: `PKG-015 v2`
- Title: `M10 Stateless Persisted-Result Comparator Foundation`
- Acceptance type: `Implementation Acceptance`
- Implementation status: `ACCEPTED`
- Final decision: `ACCEPT_PKG_015_V2_IMPLEMENTATION`
- Accepted implementation HEAD: `4cb10f2bc36c041a7681b60edfbcba712037f0c6`
- Implementation base: `9d722a14e4b4134b6afbda6c207660cda56746c8`
- Accepted definition HEAD: `73d2ce72c39d90c64457b9bf49d32176483fcc4e`
- Definition acceptance-record evidence HEAD: `715379d6157a3bd29c0cd74e66337421e378f252`
- Historical v1 implementation HEAD: `aca250f50409e569b30552ec312818ce50dcfc74`
- Alembic head: `e6b4c8d2f507`

The immutable accepted implementation boundary is exactly
`4cb10f2bc36c041a7681b60edfbcba712037f0c6`. The documentation-only commit
containing this record is evidence only. It does not replace, extend, or
redefine the accepted implementation HEAD.

## Exact Implementation History

The accepted PKG-015 v2 implementation consists of exactly these two linear
commits above `9d722a14e4b4134b6afbda6c207660cda56746c8`, in order:

1. `4368b6f50dc6902ccc8167eb4ae7f1614d8903c1` — `feat: port PKG-015 comparator to accepted v2 contract`
2. `4cb10f2bc36c041a7681b60edfbcba712037f0c6` — `test: prove PKG-015 v2 correction boundaries`

The history contains no merge commit. This acceptance-record commit is not an
implementation commit.

## Accepted Implementation Scope

The accepted implementation candidate changed exactly these five
implementation and test paths:

- `backend/app/api/m10_comparison_routes.py`
- `backend/app/main.py`
- `backend/app/schemas/m10_comparison.py`
- `backend/app/services/m10_comparison_service.py`
- `backend/tests/test_pkg015_m10_comparison.py`

No documentation other than this acceptance record, models, migration,
persistence, frontend, or unrelated backend path was part of the accepted
implementation candidate.

## WORK Implementation Acceptance Evidence

- Final decision: `ACCEPT_PKG_015_V2_IMPLEMENTATION`
- New findings: `NO_FINDING`
- `D-015-I001`: `CLOSED`
- `D-015-I002`: `CLOSED`
- `D-015-I003`: `CLOSED`
- AC: `48 PASS / 0 FAIL / 0 AMBIGUOUS`
- NAC: `41 PASS / 0 FAIL / 0 AMBIGUOUS`
- All 17 stop conditions: `CLEARED`
- Professional/product decision: No additional Omer professional decision was required.

## Architecture Acceptance

The accepted implementation preserves:

- `COMPARATOR_ONLY`;
- exactly two persisted M09 runs;
- a baseline reference and one adjusted compared run;
- stateless, read-only behavior;
- no M10 persistence;
- no history or currentness lifecycle for M10;
- no database writes;
- no upstream recalculation;
- no tax calculation;
- no pension calculation;
- no conversion calculation;
- no cashflow recalculation;
- no NPV;
- no recommendation;
- no ranking;
- no optimization;
- no suitability; and
- no frontend.

## Exact v2 Identifiers

The accepted identifiers are exactly:

- `m10-scenario-comparison-v2`
- `m10-pair-admission-v2`
- `m10-comparison-result-v2`
- `m10-comparison-fingerprint-v2`

There is no active v1 M10 identifier and no v3 identifier.

## Predicate Acceptance

Thirty predicates are accepted in exact order. In particular:

- predicates 7–18 are integrity;
- predicate 19 is reference currentness;
- predicate 20 is compared currentness;
- predicates 21–22 are eligibility;
- predicate 27 is factual upstream versions;
- predicate 28 is semantic manifest identity;
- predicate 29 is the defensive canonical month-sequence invariant guard; and
- predicate 30 is numeric domain.

Predicate 29 remains defensive and is not normally reachable through a valid
persisted accepted predecessor pair.

## D-015-I001 Acceptance Evidence

`D-015-I001` is closed because the accepted v2 semantics are implemented:

- missing or incomplete membership is owned by predecessor currentness;
- a reference membership defect maps to predicate 19 and
  `comparison_run_not_current`;
- a compared membership defect maps to predicate 20 and
  `comparison_run_not_current`;
- present-row corruption remains `comparison_fingerprint_invalid`;
- predicate 29 remains a defensive canonical sequence guard;
- the predicate 29 fail branch is proven structurally and at helper level,
  rather than by manufacturing a fake valid predecessor state;
- there is no ordinal;
- physical insertion order has no authority; and
- there is no predecessor currentness or eligibility rewrite.

## D-015-I002 Acceptance Evidence

`D-015-I002` is closed because:

- raw `Decimal` is validated before formatting;
- there is no silent rounding;
- there is no implicit quantization;
- invalid values including `Decimal("1.001")`, `Decimal("1E+2")`, and
  `Decimal("-0.001")` fail closed;
- valid exact values serialize only after validation; and
- accepted negative-zero handling is preserved.

Numeric semantics are not broadened beyond the accepted definition.

## D-015-I003 Acceptance Evidence

`D-015-I003` is closed because:

- every included M06 component is validated;
- component shape is validated;
- provenance is validated;
- exact handoff is validated;
- malformed components are not skipped;
- there is no fallback;
- there is no inferred authority;
- there is no sorting;
- there is no deduplication;
- stored order is preserved; and
- malformed, wrong, or missing upstream version material fails closed.

## Independent Test Evidence

The exact independent WORK evidence is:

| Evidence | Result |
|---|---|
| Focused PKG-015 | `69 passed, 2 warnings` |
| Predecessor regression slice | `66 passed, 2 warnings` |
| Full backend | `1163 passed, 0 skipped, 9 warnings` |
| Compile sanity | `PASS` |
| Alembic | `single head e6b4c8d2f507` |
| `git diff --check` | `PASS` |

The full-suite count differs from Codex's earlier `1161 passed, 2 skipped`
only because two conditional symlink tests executed and passed in WORK's
environment rather than being skipped. The warnings are not new defects.

## Response and Fingerprint Acceptance

- The successful response schema is closed.
- There is no optional semantic enrichment.
- Fingerprint material equals the complete successful response minus only
  `comparison_fingerprint`.
- The v2 identifiers are bound into fingerprint material.
- Canonical JSON and deterministic SHA-256 behavior are accepted.
- No v1 fingerprint authority is accepted as v2.

## Client and Resource Isolation

- Foreign and nonexistent run identifiers collapse to
  `comparison_run_unavailable`.
- Both reference and compared positions are covered.
- Reference lookup precedence is preserved.
- There is no caller-forged predecessor authority.

## Predecessor Authority

- Accepted `subject_currentness` authority is consumed.
- Accepted `subject_eligibility` authority is consumed.
- The exact contracts are `m09-subject-currentness-v1` and
  `m09-to-m10-eligibility-v2`.
- M10 does not reconstruct those authorities.
- No predecessor semantic rewrite occurred.

## Historical Boundaries

The following boundaries remain distinct:

- Accepted v2 definition HEAD:
  `73d2ce72c39d90c64457b9bf49d32176483fcc4e`
- Definition acceptance-record evidence HEAD:
  `715379d6157a3bd29c0cd74e66337421e378f252`
- Accepted v2 implementation HEAD:
  `4cb10f2bc36c041a7681b60edfbcba712037f0c6`
- Historical v1 implementation HEAD:
  `aca250f50409e569b30552ec312818ce50dcfc74`

None of these boundaries is conflated with another.

## Governance After Implementation Acceptance

- PKG-015 v2 implementation: `ACCEPTED`
- Accepted implementation HEAD:
  `4cb10f2bc36c041a7681b60edfbcba712037f0c6`
- Implementation acceptance record: `THIS DOCUMENT IS EVIDENCE ONLY`
- Master remains `9d722a14e4b4134b6afbda6c207660cda56746c8`.
- The implementation is not yet merged to master.
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11–M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`
- Next package: `NOT_AUTHORIZED`
- No production-readiness claim is made.
- No broad M10 completion claim is made.

PKG_015_V2_IMPLEMENTATION_ACCEPTED
