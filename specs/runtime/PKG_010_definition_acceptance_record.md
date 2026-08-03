# PKG-010 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-010 — M05 Manual Pension Balance Ledger and Exact Reconciliation Foundation` |
| Module | `M05` |
| Definition status | `ACCEPTED_AND_CLOSED` |
| Authoritative base | `1d336485f4dd7c187894dd8670f40dba73a36df9` |
| Accepted definition HEAD | `31ea6332e1ad7d2b2fa8b7969fb395a40fb1d778` |
| Definition | `specs/runtime/PKG_010_FINAL_PACKAGE_DEFINITION.md` |
| Accepted predecessor | `PKG-009` |
| Predecessor implementation | `ae73a7706214b137b7452b9f66c483ee5b57009c` |
| Predecessor migration | `95222c79dce8` |
| Definition commits | `3` |

The accepted definition commit chain above the authoritative base is:

1. `9133754ebfc4b8a8e86b4bdf81916bad2f36c180`
2. `32bee73185a8fa202772dba325826811ddba5d46`
3. `31ea6332e1ad7d2b2fa8b7969fb395a40fb1d778`

## Accepted Scope

PKG-010 defines:

- a manual-only M05 ledger foundation;
- client-scoped immutable ledger subjects and revisions;
- M02 manual records only;
- current M03 and M04 authority revalidation;
- explicit server-owned ILS confirmation;
- exact provider/account identity;
- one-to-one component mapping;
- canonical persisted M02 Decimal predecessor values;
- strict observable component-string validation;
- strict M05-authored monetary mutation validation;
- source, derived, and effective value separation;
- exact effective-value reconciliation;
- an exact `0.50 ILS` tolerance;
- negative-value warnings;
- structured warning disposition;
- deterministic stale-date semantics;
- additive adjustments;
- an immutable lifecycle; and
- read-time technical M06 eligibility only.

## Accepted Component Vocabulary

The accepted component vocabulary is exactly:

- `total_balance`;
- `contribution_component`;
- `severance_component`; and
- `unknown_component`.

`contribution_component` represents תגמולים. `compensation_component` is
prohibited. Capital, pension, mixed, and unresolved remain M04 interpretation
or grouping dimensions only; no capital/pension grouping may be counted as an
additional monetary fact. `unknown_component` is not reconcilable authority.

## Accepted Reconciliation

The accepted formula is:

`discrepancy = effective_total_balance - sum(effective_reconcilable_component_value for each included evidence identity exactly once)`

- Only mapped contribution and severance values participate.
- Exactly one effective value participates per evidence identity.
- The source value remains immutable.
- Total-only reconciliation is prohibited.
- A non-empty current resolved component set is required.
- Arithmetic uses exact Decimal values.
- `abs(discrepancy) <= 0.50 ILS` satisfies tolerance.
- A discrepancy above tolerance requires structured review.
- Silent correction and double counting are prohibited.

## Accepted Predecessor-Value Boundary

- Persisted M02 `Numeric(20,2)` values are consumed as canonical Decimal
  predecessor facts.
- M05 does not reconstruct unavailable original representation.
- M05 does not claim to identify whether original input was `0.50`, `0.500`,
  exponent notation, a JSON number, or a binary float.
- M05 does not reparse or round canonical predecessor values.
- Strict representation checks apply to observable M02 component strings and
  M05-authored monetary values.
- Binary-float mutation input remains prohibited.
- Canonical zero is `0.00`.
- Maximum magnitude is `999999999999999999.99`.

## Accepted Lifecycle

Persisted states are exactly:

- `draft`;
- `reconciled`;
- `warning_reviewed`;
- `blocked`; and
- `superseded`.

Accepted actions are:

- start;
- reconcile;
- review warning;
- mark blocked;
- adjust;
- supersede; and
- revalidate.

`superseded` is terminal. Reconcile and review-warning originate only from
`draft`. Every mutation requires current-leaf intent, concurrent same-leaf
actions allow exactly one winner, and every state change creates one immutable
successor. Optional undo is outside required package acceptance.

## Warning Catalogue

Mandatory warnings are exactly:

- `reconciliation_difference_review_required`; and
- `negative_value_review_required`.

Informational warnings are exactly:

- `stale_warning`; and
- `newer_ineligible_candidate_exists`.

Warning disposition requires the exact current mandatory-warning set. Invalid,
missing, extra, unknown, informational, or stale disposition input is rejected
with `warning_disposition_invalid`.

## Stale Semantics

- `evaluation_date` is a server-owned date-only value.
- A statement is stale only when older than 12 full calendar months.
- Calendar subtraction clamps the day to the last valid day.
- Equality to the threshold is not stale.
- A future statement date is rejected as `statement_date_invalid`.
- Staleness alone does not block technical eligibility.

## Acceptance Evidence

Final definition audit status:

`ACCEPT_PKG_010_DEFINITION`

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Final definition HEAD | `31ea6332e1ad7d2b2fa8b7969fb395a40fb1d778` |
| Definition commits above master | `3` |
| AC | `33 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `24 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Stop conditions | `24 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Blocking definition defects | `None` |
| Material non-blocking wording notes | `None` |
| Product decisions required | `None` |
| Final status | `ACCEPT_PKG_010_DEFINITION` |

## Closed Defects

| Defect | Closure | Status |
|---|---|---|
| `D-010-001` | Exact M01 derived mutation predicate and M02 `accepted_for_review` vocabulary established. | `CLOSED` |
| `D-010-002` | Explicit source-snapshot-specific server-controlled ILS confirmation established. | `CLOSED` |
| `D-010-003` | Exact persisted provider/account byte identity and manual target kind established. | `CLOSED` |
| `D-010-004` | Canonical persisted M02 values separated from representation-sensitive M02 strings and M05-authored inputs. | `CLOSED` |
| `D-010-005` | Total-only reconciliation removed and a non-empty complete component mapping required. | `CLOSED` |
| `D-010-006` | Deterministic indexed one-to-one M02-M04-M05 component mapping established. | `CLOSED` |
| `D-010-007` | Reconciliation restricted to exactly one current effective value per identity. | `CLOSED` |
| `D-010-008` | Complete exact lifecycle matrix and concurrency rules established. | `CLOSED` |
| `D-010-009` | Stable mandatory/informational warning catalogue and exact-set disposition established. | `CLOSED` |
| `D-010-010` | Date-only calendar-month stale threshold and examples established. | `CLOSED` |
| `D-010-011` | Enforcement, concurrency, offline migration, frontend, stop, and AC/NAC evidence expanded. | `CLOSED` |
| `D-010-012` | Authoritative M05 vocabulary and effective-value reconciliation aligned with M04 and PKG-010. | `CLOSED` |

## Authorization Boundary

- The PKG-010 definition is `ACCEPTED_AND_CLOSED`.
- Implementation remains `NOT_AUTHORIZED`.
- Migration creation and execution remain `NOT_AUTHORIZED`.
- M06 remains `NOT_AUTHORIZED`.
- The next package remains `NOT_AUTHORIZED`.
- No production-readiness claim is made.
- No V1/V2 parity claim is made.
- M09–M14 remain `BLOCKED_FOR_LOGIC_DETAIL`.
- `02M` remains `FROZEN`.

Definition acceptance and closure do not authorize implementation. A separate
implementation gate is required.
