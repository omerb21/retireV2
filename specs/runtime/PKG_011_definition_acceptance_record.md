# PKG-011 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-011` |
| Title | `M06 First-Stage Explicit Pension/Capital Conversion Foundation` |
| Acceptance type | `Definition Acceptance` |
| Final decision | `ACCEPT_PKG_011_DEFINITION` |
| Authoritative master | `596b353dbaabae82d0c278dff02d04083f90b94a` |
| Accepted definition HEAD | `618e53184c1ae3286962e075d82ef1756e2e8ed9` |
| Review branch | `pkg-011-review` |
| Merge base | `596b353dbaabae82d0c278dff02d04083f90b94a` |
| Definition commits above master | `3` |

The accepted definition HEAD is the final formatting-corrected HEAD, `618e53184c1ae3286962e075d82ef1756e2e8ed9`.

## Definition References

- Definition: `specs/runtime/PKG_011_FINAL_PACKAGE_DEFINITION.md`
- Business plan: `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`
- Definition final token: `PKG_011_DEFINITION_PROPOSED_FOR_ACCEPTANCE`

## Acceptance Audit History

### Initial Definition Acceptance Audit

Status: `ACCEPT_PKG_011_DEFINITION_WITH_NON_BLOCKING_FINDINGS`

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Commit isolation | `PASS` |
| Definition fidelity | `PASS` |
| D01-D07 | `PASS` |
| Predecessor contract | `PASS` |
| Modes and subject identity | `PASS` |
| Coefficient evidence | `PASS` |
| Numeric contract | `PASS` |
| Date and applicability | `PASS` |
| Lifecycle | `PASS` |
| Warnings | `PASS` |
| Blocking reasons | `PASS` |
| Warning review and correction | `PASS` |
| Manifest | `PASS` |
| Revalidation and downstream eligibility | `PASS` |
| API and frontend | `PASS` |
| Persistence and concurrency | `PASS` |
| AC | `42 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `38 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Plan synchronization | `PASS` |
| Governance | `PASS` |
| Blocking definition defects | `None` |
| Scope violations | `None` |

Initial non-blocking findings:

1. Several Markdown tables contained malformed header rows.
2. Unrelated pre-existing tracked modifications existed in another shared checkout; they were excluded from evidence and left untouched. This was not a repository defect.

### Formatting Correction

| Field | Value |
|---|---|
| Commit | `618e53184c1ae3286962e075d82ef1756e2e8ed9` |
| Message | `docs: fix PKG-011 definition table headers` |
| Scope | Presentation-only Markdown header correction |

### Focused Re-Audit

Final status: `ACCEPT_PKG_011_FORMAT_CORRECTION`

| Re-audit area | Result |
|---|---|
| Safety | `PASS` |
| Commit isolation | `PASS` |
| Table-header corrections | Exactly `9` |
| Semantic freeze | `PASS` |
| AC | `42`, unchanged |
| NAC | `38`, unchanged |
| Token and code freeze | `PASS` |
| Markdown quality | `PASS` |
| Governance | `PASS` |
| Blocking defects | `None` |
| Material non-blocking findings | `None` |
| Scope violations | `None` |

The original Markdown formatting finding is closed.

## Locked Professional Decisions

### D01

The first-stage allowlist is only:

- `pension_fund`;
- `insurance_policy`; and
- the current M05 `contribution_component`.

### D02

Coefficient authority is only:

- documentary; or
- planner-declared.

There is no inference, lookup, default, V1 `200.0`, or caller-authored authority.

### D03

Documented applicability is inclusive. Undocumented applicability requires an explicit planner declaration and warning review. A date contradiction blocks.

### D04

- The authoritative path is Decimal-only.
- Coefficient input is a canonical decimal string.
- Exact coefficient precision is retained.
- The exact raw-result representation is retained.
- Division is preserved as an exact ratio.
- Display is quantized to `0.01` using `ROUND_HALF_UP`.

### D05

Explicit zero is valid.

### D06

There is no first-stage conservation or residual contract. Its exact status is:

`NOT_IMPLEMENTED_NO_AUTHORITATIVE_FIRST_STAGE_CONTRACT`

### D07

Monthly-to-capital authority is only the same-chain M02 `declared_monthly_pension_amount`. M01 monthly pension is excluded.

## Accepted Package Boundary

The accepted definition establishes:

- same-client M01-M05 predecessor authority;
- read-only predecessor consumption;
- exactly two modes: `balance_to_monthly_pension` and `monthly_pension_to_capital_equivalent`;
- an immutable semantic conversion subject;
- explicit coefficient provenance;
- Decimal-only calculation;
- separation of exact raw authority from the displayed result;
- lifecycle states `draft`, `resolved`, `warning_reviewed`, `blocked`, and `superseded`;
- append-only successors;
- exact-set warning-review semantics;
- coefficient/provenance correction only;
- a calculation/provenance manifest;
- read-time predecessor revalidation;
- technical downstream eligibility only;
- API anti-leakage;
- frontend client, generation, subject, and revision ownership;
- an additive migration expected only under later authorization; and
- deterministic concurrency behavior.

## AC and NAC Outcome

### AC

- Result: `42 PASS / 0 FAIL / 0 NOT_PROVEN`
- Range: `AC-011-001` through `AC-011-042`

### NAC

- Result: `38 PASS / 0 FAIL / 0 NOT_PROVEN`
- Range: `NAC-011-001` through `NAC-011-038`

| Integrity check | Result |
|---|---|
| Missing IDs | `None` |
| Duplicates | `None` |
| Altered criteria | `None` |

## Defects, Findings, and Violations

| Item | Result |
|---|---|
| Blocking definition defects | `None` |
| Remaining definition evidence gaps | `None` |
| Material non-blocking findings after focused correction | `None` |
| Scope violations | `None` |

## Explicit Exclusions

Definition acceptance does not authorize:

- implementation;
- migration creation;
- migration execution;
- production deployment or readiness;
- automatic coefficient lookup or catalogue;
- M07 implementation;
- M08 implementation;
- M09-M14;
- tax;
- fixation;
- 161D;
- exemption;
- withdrawal or liquidity;
- pension commencement;
- scenarios;
- recommendations;
- reports;
- historical-capitalization generation;
- V1/V2 parity; or
- changes to `02M`.

## Governance

- PKG-011 definition is accepted.
- This record does not authorize implementation.
- This record does not authorize migration creation or execution.
- This record does not merge the definition to master.
- Master merge requires separate authorization.
- M07 and M08 remain unchanged.
- M09-M14 remain blocked.
- `02M` remains frozen.
- The next package remains unauthorized.
- The review branch must remain unchanged until the Definition Acceptance Record Audit completes.

PKG_011_DEFINITION_ACCEPTED
