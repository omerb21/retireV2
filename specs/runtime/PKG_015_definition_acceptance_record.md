# PKG-015 Definition Acceptance Record

## 1. Record Identity

| Field | Value |
|---|---|
| Package | `PKG-015` |
| Title | `M10 Stateless Persisted-Result Comparator Foundation` |
| Acceptance type | `Definition Acceptance` |
| Decision | `ACCEPT_PKG_015_DEFINITION` |
| Definition base | `6783eb50bb90291f38ddce68a429fe6085f3a1ff` |
| Initial definition draft | `424aa92cb2b990bc8e272f7bbe7b8dac0878f153` |
| Immutable accepted definition HEAD | `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e` |
| Accepted-definition tree | `d3ac166b0d25e7d047f206d4ca1b20f1268eb12b` |
| Alembic head at definition acceptance | `e6b4c8d2f507` |
| PKG-015 implementation | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |
| Broad M10 | `BLOCKED_FOR_LOGIC_DETAIL` |
| M11-M14 | `NOT_AUTHORIZED` |
| M08E | `EXCLUDED` |
| `02M` | `FROZEN` |

This record is acceptance evidence only. It does not redefine the immutable
accepted definition boundary. The definition acceptance-record HEAD is the
docs-only commit that adds this file and is not a definition commit.

## 2. Immutable Definition Boundary

The boundaries are permanently distinct:

- Definition base:
  `6783eb50bb90291f38ddce68a429fe6085f3a1ff`.
- Initial definition draft:
  `424aa92cb2b990bc8e272f7bbe7b8dac0878f153`.
- Accepted definition HEAD:
  `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e`.
- Definition acceptance-record HEAD: the child docs-only commit that creates
  this record.

The accepted definition HEAD remains
`fcadcaf33cc877014ea84dc13eb9d83205ae9b4e` after this record is committed.

## 3. Exact Definition History

The accepted definition history above the base contains exactly these two
definition commits, in Git order:

1. `424aa92cb2b990bc8e272f7bbe7b8dac0878f153` —
   `docs: define PKG-015 M10 stateless comparator`
2. `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e` —
   `docs: close PKG-015 comparator contract gaps`

The acceptance-record commit is evidence only and is not counted as a
definition commit.

## 4. Audit History

### 4.1 Initial Definition Audit

- Decision: `RETURN_PKG_015_DEFINITION_FOR_CORRECTION`.
- `D-015-D001` — `BLOCKING`.
- `D-015-D002` — `BLOCKING`.
- `D-015-D003` — `BLOCKING`.
- Other initial findings: `NONE`.

### 4.2 D-015-D001 Closure

Initial issue: public blocker precedence and mapping were not fully
deterministic.

The accepted correction freezes:

- one authoritative predicate-to-public-code mapping;
- exactly 30 ordered predicates;
- reference availability before compared availability;
- terminal, non-leaking `comparison_run_unavailable` behavior;
- reference integrity before compared integrity;
- integrity before currentness;
- currentness before eligibility;
- deterministic shared factual/version checks;
- semantic-manifest comparison after integrity/version checks;
- month alignment before numeric-domain validation;
- numeric-domain validation as the final blocker predicate;
- the same invalid persisted pair returning the same first public blocker; and
- a closed vocabulary of exactly 16 public blocker codes.

Final state: `D-015-D001 CLOSED`.

### 4.3 D-015-D002 Closure

Initial issue: the success response and fingerprint contracts were open-ended
and insufficiently canonical.

The accepted correction freezes:

- exact closed `m10-comparison-result-v1` top-level and nested schemas;
- no extra, optional, or null semantic fields;
- exact repository identity types: opaque string `run_id`, opaque string
  `scenario_subject_id`, and integer `client_id`;
- an exact closed `versions` object;
- an exact factual-upstream projection from persisted PKG-014 evidence;
- exact closed reference-run and compared-run evidence schemas;
- exact monthly-comparison and `range_totals` schemas;
- canonical two-decimal monetary strings and the full exact delta domain;
- `comparison_fingerprint_material` as exactly the successful response with
  only `comparison_fingerprint` omitted;
- exact UTF-8 canonical JSON serialization, lexical object-key ordering,
  contract-defined array order, compact separators, and standard escaping;
- no semantic null, floating monetary number, NaN, or Infinity;
- lowercase hexadecimal SHA-256;
- no implementation-specific fingerprint enrichment; and
- a newly accepted schema/contract version for any semantic schema change.

Final state: `D-015-D002 CLOSED`.

### 4.4 D-015-D003 Closure

Initial issue: the Business Build Plan contained stale active/current statements
inconsistent with the closed PKG-013 and PKG-014 state.

The accepted correction establishes one coherent controlling checkpoint:

- PKG-013: `CLOSED_ON_MASTER`;
- PKG-014: `CLOSED_ON_MASTER`;
- the narrow parallel-output prerequisite: resolved by PKG-014;
- PKG-015: definition acceptance/correction workflow only;
- broad M10: `BLOCKED_FOR_LOGIC_DETAIL`;
- PKG-015 implementation: `NOT_AUTHORIZED`;
- M11-M14: `NOT_AUTHORIZED`;
- M08E: `EXCLUDED`;
- `02M`: `FROZEN`; and
- retained obsolete checkpoints: explicitly `HISTORICAL / SUPERSEDED`.

Final state: `D-015-D003 CLOSED`.

## 5. Final Re-Audit Evidence

| Item | Result |
|---|---|
| D-015-D001 | `CLOSED` |
| D-015-D002 | `CLOSED` |
| D-015-D003 | `CLOSED` |
| New defects | `NONE` |
| Blocking findings | `NONE` |
| Non-blocking findings | `NONE` |
| Professional decision requirement | `NO_OMER_PROFESSIONAL_DECISION_REQUIRED` |
| Final decision | `ACCEPT_PKG_015_DEFINITION` |

## 6. Accepted Contract Summary

This summary records, but does not redefine, the accepted definition:

- Role: `COMPARATOR_ONLY`.
- Inputs: accepted persisted M09 results only.
- Supported scenario family: `declared_retirement_cashflow_adjustments`.
- Supported scenario version: `v1`.
- Reference: server-owned baseline subject run.
- Compared: adjusted subject run.
- Exactly two runs; adjusted-versus-adjusted is unsupported.
- Stateless comparator with no comparison persistence or frontend.
- Endpoint: `POST /api/clients/{client_id}/m10/compare`.
- Request body keys only: `reference_run_id`, `compared_run_id`.
- Caller-forged authority is prohibited and client non-leakage is mandatory.
- Pair admission uses the exact 30-step blocker precedence and exactly 16
  public blockers.
- `delta_direction = compared_minus_reference`.
- Arithmetic is exact Decimal subtraction with numeric relations only.
- No reconstruction; only persisted monthly and `range_totals` values are
  compared.
- Month alignment is exact and preserves persisted order.
- The result schema is exact and closed.
- The response fingerprint is deterministic and server-owned.
- Recommendation, ranking, optimization, and suitability semantics are absent.

## 7. Accepted Comparator Version Identifiers

The exact accepted identifiers are:

- `m10-scenario-comparison-v1`
- `m10-pair-admission-v1`
- `m10-comparison-result-v1`
- `m10-comparison-fingerprint-v1`

They are server-owned and cannot be supplied, changed, negotiated, or aliased by
the caller.

## 8. Accepted Criteria Sets

### Acceptance Criteria

- Count: `48`.
- Range: `AC-015-001` through `AC-015-048`.
- Contiguous: `YES`.
- Missing: `NONE`.
- Duplicates: `NONE`.

### Negative Acceptance Criteria

- Count: `41`.
- Range: `NAC-015-001` through `NAC-015-041`.
- Contiguous: `YES`.
- Missing: `NONE`.
- Duplicates: `NONE`.

## 9. Stop Conditions

The definition contains `17` accepted stop conditions. They include the two
correction-added gates:

- `PKG_015_NONDETERMINISTIC_BLOCKER_MAPPING_REQUIRED`
- `PKG_015_FINGERPRINT_OR_RESPONSE_SCHEMA_NOT_EXACT`

All 17 are definition-time implementation gates. Their existence does not
authorize implementation.

## 10. Upstream Preservation

PKG-013 semantics and PKG-014 semantics remain preserved. PKG-015 consumes
accepted persisted M09/PKG-014 evidence only and does not become co-owner of:

- M09 calculation;
- scenario-subject semantics;
- baseline semantics;
- adjustment semantics;
- factual-baseline-fingerprint semantics;
- currentness;
- eligibility; or
- upstream result arithmetic.

## 11. Explicit Scope Exclusions

The accepted definition excludes:

- implementation;
- migrations;
- persistence and history;
- comparison currentness;
- frontend/UI;
- adjusted-versus-adjusted comparison;
- more than two scenarios;
- other scenario families;
- a generic compatibility registry;
- materiality and significance;
- recommendation, ranking, optimization, and suitability;
- professional interpretation;
- M11-M14;
- M08E; and
- changes to `02M`.

## 12. Build Plan and Governance State

The accepted definition keeps broad M10 `BLOCKED_FOR_LOGIC_DETAIL`. Only the
narrow accepted PKG-015 definition contract may advance through governance.
Definition acceptance does not mean that M10 implementation is authorized or
that M10 is broadly complete.

**PKG-015 IMPLEMENTATION: `NOT_AUTHORIZED`.**

- Definition acceptance record creation: `AUTHORIZED`.
- Master merge: `NOT_AUTHORIZED` pending independent acceptance-record audit.
- Next package: `NOT_AUTHORIZED`.
- No production-readiness or V1/V2 parity claim is made.

PKG_015_DEFINITION_ACCEPTED
