# PKG-013 Definition Acceptance Record

## Record Identity

| Field | Value |
|---|---|
| Package | `PKG-013` |
| Title | `M09 Deterministic Monthly Cashflow Orchestration Foundation` |
| Acceptance type | `Definition Acceptance` |
| Final decision | `ACCEPT_PKG_013_DEFINITION` |
| Historical base/master | `81bf748fa358c7e664a8f31d60bdb04cd94838de` |
| Accepted definition HEAD | `5293d8ccdee9d3700fc09fd276ba6ebb39449512` |
| Definition commits | `3` |
| Current Alembic head | `f9a1c3e5b702` |

The accepted definition HEAD is permanently
`5293d8ccdee9d3700fc09fd276ba6ebb39449512`. The commit containing this
acceptance record is documentation evidence only, is created directly above the
accepted definition HEAD, does not replace or redefine that historical
boundary, and is not counted as a definition commit.

## Exact Definition History

1. `d351929ef5401b2687666f21eb8b8352877626c0`
   `docs: define PKG-013 deterministic monthly cashflow foundation`
2. `dbc7388e179998a4d174d0c7ab0692af46ca9810`
   `docs: align build plan with PKG-013 M09 contract`
3. `5293d8ccdee9d3700fc09fd276ba6ebb39449512`
   `docs: close PKG-013 definition audit gaps`

## Acceptance and Audit History

The initial Definition Acceptance Audit decision was
`RETURN_PKG_013_DEFINITION_FOR_CORRECTION`. It identified two blocking
defects: `D-013-D001` and `D-013-D002`.

Correction commit `5293d8ccdee9d3700fc09fd276ba6ebb39449512`
was then re-audited with the following result:

- `D-013-D001 CLOSED`
- `D-013-D002 CLOSED`
- New defects: none
- Non-blocking findings: none
- Final decision: `ACCEPT_PKG_013_DEFINITION`

This record preserves the return-and-correction history; it does not represent
the initial draft as having been accepted immediately.

## Single-Authority Architecture

Every material business calculation has exactly one authoritative owner. M09
is accepted for planning only as `ORCHESTRATOR_AND_AGGREGATOR_ONLY`.

M09 owns only:

- monthly alignment of already authoritative components;
- inflow aggregation;
- outflow aggregation;
- `period_net`; and
- deterministic range totals.

M09 must not duplicate upstream formulas. Preventing V1-style duplicated
calculation authority is a core accepted PKG-013 boundary.

## Accepted First-Stage Family

The only accepted family/version is
`deterministic_monthly_cashflow/v1`. No other M09 scenario family is accepted
by this definition.

Deferred and unaccepted families include maximum pension, maximum capital,
balanced/NPV, net-tax cashflow, investment-return scenarios,
withdrawal/commutation, optimization, ranking, recommendation, comparison,
reports, Monte Carlo, and LLM-generated calculation assumptions.

## Server-Owned Completeness

Each run uses an immutable server-owned `resolved_component_inventory`, bound
to the client, family, contract version, and requested horizon. The server
determines the complete mandatory component universe and automatically includes
every mandatory eligible component.

The caller and UI cannot reduce, omit, waive, select authoritatively, or
redefine that universe. There is no authoritative partial-portfolio mode, no
`run anyway`, and no silent omission.

`server_resolved_none` is server-generated evidence only. Caller checkbox,
free text, omission, or assertion of none cannot establish completeness or
become calculation authority.

## Closed Component Contract

The first-stage component vocabulary is exactly:

- `recurring_income_record`
- `recurring_expense_record`
- `m06_monthly_pension_result`

M05 balances are not monthly cashflow. M06 capital-equivalent output, M07
facts, automatically inferred M08 facts, free-form amounts, and caller-authored
amounts are excluded from the component vocabulary.

## Dependency Boundaries

### M05

- An M09-specific eligibility gate is required.
- `eligible_for_m06` is not generic M09 authority.
- M09 cannot transform an M05 balance into monthly cashflow.

### M06

- Only an eligible current `balance_to_monthly_pension` result may feed a
  monthly-pension component.
- A canonical Decimal `ILS/month` handoff is required.
- Display output is not silently upgraded to authority.
- Absence of a valid handoff fails closed.
- M09 does not recompute the conversion.

### M07

M07 is omitted for `deterministic_monthly_cashflow/v1`; there is no inheritance
from `m08a_fixation/v1`.

### M08 and M08F

M08 is omitted for the current closed vocabulary. A future M08-dependent
component would require a persisted M08 result and exact per-use M08F
eligibility. Technical success alone is insufficient, and M09 duplicates no
M08 formula.

## Horizon Contract

The first-stage horizon requires explicit `start_month` and `end_month` in
canonical `YYYY-MM` form. Both endpoints are included; the horizon contains
full calendar months in deterministic ascending order. There is no default or
inferred horizon, partial-month prorating, or frequency conversion.

## Monetary Contract

Authoritative aggregation is Decimal-only. Binary float authority and silent
float conversion are prohibited. M09 does not reround upstream amounts and uses
exact addition and subtraction. For this v1 contract, monthly components are
canonical two-decimal ILS. Display formatting is separate from calculation
authority.

## Fail-Closed Contract

- missing is not zero;
- blocked is not zero;
- unsupported is not zero;
- unresolved is not zero;
- stale is not current;
- superseded is not current;
- ineligible is not accepted; and
- an invalid fingerprint is not accepted.

No partial authoritative result is permitted.

## Assumptions, Snapshots, and History

The assumption manifest is typed and immutable, uses `extra=forbid`, and
preserves versions and fingerprints. Free text and LLM text cannot affect the
calculation. Each run preserves an immutable upstream snapshot and append-only
scenario-run history. Later predecessor edits do not mutate historical runs.

## Currentness and M10 Boundary

Execution status is distinct from currentness. `success_complete` is neither
automatically current nor automatically M10-eligible. M10 eligibility is
derived and fail-closed. M10 may consume persisted M09 results only and must not
execute or recalculate M09.

This definition acceptance does not make M10 ready. M10-M14 remain
`BLOCKED_FOR_LOGIC_DETAIL`.

## Definition Acceptance Criteria

- AC: `40 PASS / 0 FAIL / 0 NOT_PROVEN`
- IDs: `AC-013-001` through `AC-013-040`
- NAC: `32 PASS / 0 FAIL / 0 NOT_PROVEN`
- IDs: `NAC-013-001` through `NAC-013-032`

These are definition-contract acceptance criteria, not implementation test
results.

## Business Build Plan State

The synchronized Business Build Plan establishes:

- bounded M09: `READY_FOR_BUILD_PLANNING`;
- accepted first-stage family: `deterministic_monthly_cashflow/v1`;
- Q-017: resolved for the first stage only;
- Q-018: resolved for the first stage only;
- M10-M14: `BLOCKED_FOR_LOGIC_DETAIL`;
- M08E: excluded;
- `02M`: frozen; and
- no module: `READY_FOR_IMPLEMENTATION`.

## Migration and Governance Boundary

- No migration was created.
- Alembic head remains `f9a1c3e5b702`.
- Definition acceptance does not authorize migration.
- Definition acceptance does not authorize implementation.
- Definition acceptance does not authorize a master merge by itself.
- M10 implementation is not authorized.
- The next package is not authorized.

PKG_013_DEFINITION_ACCEPTED
