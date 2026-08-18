# PKG-015 v2 Definition Acceptance Record

## Record Identity

| Field | Value |
|---|---|
| Package | `PKG-015 v2` |
| Title | `M10 Stateless Persisted-Result Comparator Foundation` |
| Acceptance type | `Definition Acceptance` |
| Definition status | `ACCEPTED` |
| Final decision | `ACCEPT_PKG_015_V2_DEFINITION` |
| Definition base | `8a0bd85a98d78f39d19eee937989b7ddd0192844` |
| Accepted v2 definition HEAD | `73d2ce72c39d90c64457b9bf49d32176483fcc4e` |
| Initial v2 definition commit | `8a24ee0f9252a8fdce44763da3c82870bd862d2a` |
| V2 correction commit | `73d2ce72c39d90c64457b9bf49d32176483fcc4e` |
| Historical v1 accepted definition | `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e` |
| Historical v1 acceptance record | `1c302e0d760ab7e66c94c6c1695fc71cda6b4e7d` |
| Current Alembic head | `e6b4c8d2f507` |

## Immutable Accepted Definition Boundary

The immutable accepted v2 definition HEAD is exactly:

`73d2ce72c39d90c64457b9bf49d32176483fcc4e`

The acceptance-record commit created directly above that boundary is
documentation evidence only. It does not replace, extend, or redefine the
accepted v2 definition HEAD and does not authorize implementation.

The accepted v2 definition history is:

1. `8a24ee0f9252a8fdce44763da3c82870bd862d2a` — initial v2 definition.
2. `73d2ce72c39d90c64457b9bf49d32176483fcc4e` — D-015-V2D001 correction.

## Acceptance Evidence

Initial v2 definition audit:

`RETURN_PKG_015_V2_DEFINITION_FOR_CORRECTION`

Finding:

- `D-015-V2D001`
- `BLOCKING_DEFINITION_DEFECT`

Focused re-audit after correction:

- `D-015-V2D001 CLOSED`
- New findings: `NO_FINDING`
- Final decision: `ACCEPT_PKG_015_V2_DEFINITION`

Acceptance results:

- AC: `48 PASS / 0 FAIL / 0 AMBIGUOUS`
- AC range: `AC-015-001` through `AC-015-048`
- NAC: `41 PASS / 0 FAIL / 0 AMBIGUOUS`
- NAC range: `NAC-015-001` through `NAC-015-041`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`

## Accepted v2 Architecture

The accepted v2 definition establishes:

- role `COMPARATOR_ONLY`;
- a predecessor-compatible M10 comparison contract;
- no M09 ordinal and no predecessor schema rewrite;
- no predecessor currentness or eligibility rewrite;
- predicates 19 and 20 as the owners of invalid per-run month membership
  through predecessor currentness;
- predicate 29 as a defensive pair-level canonical month-sequence invariant
  guard whose failure branch is not normally reachable through a valid accepted
  predecessor state and whose retained public blocker is
  `comparison_month_alignment_mismatch`;
- structural/helper evidence only for the predicate 29 failure branch;
- predicate 30 as numeric-domain validation;
- exactly 30 ordered predicates and 16 retained public blockers;
- stateless comparison of persisted M09 values only;
- no comparison persistence and no frontend; and
- no recommendation, ranking, optimization, or suitability semantics.

## Exact v2 Identifiers

| Identifier | Accepted value |
|---|---|
| `comparison_contract_version` | `m10-scenario-comparison-v2` |
| `pair_admission_contract` | `m10-pair-admission-v2` |
| `comparison_result_schema` | `m10-comparison-result-v2` |
| `comparison_fingerprint_schema` | `m10-comparison-fingerprint-v2` |

Historical v1 identifiers are not active v2 identifiers.

## Defect and Implementation State

### D-015-I001

- Status: `OPEN`
- `BLOCKED_BY_ACCEPTED_V1_CONTRACT_INCOMPATIBILITY`
- `RESOLUTION_REQUIRES_ACCEPTED_V2_CONTRACT_IMPLEMENTATION_CORRECTION_AND_INDEPENDENT_WORK_IMPLEMENTATION_REAUDIT`

D-015-I001 remains `OPEN` and may be closed only after all of the following are
true:

1. The accepted PKG-015 v2 definition is closed on master.
2. The implementation is corrected against that accepted v2 contract.
3. The corrected implementation passes an independent WORK implementation
   re-audit.

No subset of these conditions closes D-015-I001. Acceptance of the v2
definition alone, implementation correction alone, or implementation tests
alone do not close it. Only independent acceptance after correction may close
the defect.

### D-015-I002

Status: `OPEN`

### D-015-I003

Status: `OPEN`

The frozen v1 implementation candidate is:

`aca250f50409e569b30552ec312818ce50dcfc74`

Its status remains:

- `NOT_ACCEPTED`
- `PAUSED`

## Governance

- PKG-015 v2 definition: `ACCEPTED`.
- PKG-015 implementation: `NOT_ACCEPTED / PAUSED`.
- Implementation correction:
  `NOT_AUTHORIZED_YET_PENDING_V2_DEFINITION_CLOSURE_ON_MASTER`.
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`.
- M11-M14: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Next package: `NOT_AUTHORIZED`.
- No production-readiness claim is made.
- No V1/V2 parity claim is made.
- This record creates no implementation, migration, persistence, frontend,
  broad-M10, or next-package authorization.

PKG_015_V2_DEFINITION_ACCEPTED
