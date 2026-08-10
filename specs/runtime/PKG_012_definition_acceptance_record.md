# PKG-012 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-012` |
| Title | `M08C/M08D Exempt Grant Offset and Historical Indexation Foundation` |
| Acceptance type | `Definition Acceptance` |
| Final decision | `ACCEPT_PKG_012_DEFINITION` |
| Authoritative historical master/base | `49caa28275c453f3b7cb45d9b2c86a3cc144bf94` |
| Accepted definition HEAD | `e11571f639e49ed38975da5a000f90c8c60fd45a` |
| Definition commit | `d4884ef9c35ebe966e766c4c6c8f84ebd3cdca20` |
| Plan-sync commit | `e11571f639e49ed38975da5a000f90c8c60fd45a` |
| Review branch | `pkg-012-review` |
| Definition commits above master | `2` |
| Alembic head at definition acceptance | `e8f4b7c2d305` |

The accepted definition boundary remains
`e11571f639e49ed38975da5a000f90c8c60fd45a`. The acceptance-record commit is
not part of that historical boundary.

## Definition References

- Definition: `specs/runtime/PKG_012_FINAL_PACKAGE_DEFINITION.md`
- Business plan: `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`
- Definition final token: `PKG_012_DEFINITION_PROPOSED_FOR_ACCEPTANCE`

## Accepted Definition Boundary

### Exact business record

Each authoritative exempt-grant record contains exactly six business facts:

1. `employer_name`
2. `employer_withholding_file_number`
3. `employment_start_date`
4. `employment_end_date`
5. `grant_receipt_date`
6. `exempt_grant_amount`

The server-owned technical `grant_id` is record identity, not a seventh business
fact.

### Direct professional-user authority

Professional-user-entered structured records are authoritative for this bounded
path. Zero grant records means `no exempt grants`. No secondary approval,
evidence-sufficiency, source-ranking, reliability, or candidate-resolution
workflow applies.

### Excluded historical models

- There is no separate prior-withdrawal record, status, formula, or workflow.
- There is no prior-fixation status, discovery, resolver, or ambiguity workflow.
- Document presence remains supporting material and is not an automatically
  interpreted calculation fact.

### Exact 15-year rule

The accepted V1-derived year/month/day difference excludes a grant only when:

`years_difference > 15`

Exactly 15 years is included.

### Exact 32-year rule

- The window begins exactly `11,688` days before eligibility.
- The ratio is `overlap_days / full_employment_days`.
- No inclusive endpoint day is added.
- Employment after eligibility is excluded from the numerator.
- Full employment duration remains the denominator.
- The ratio is not prematurely rounded.

### CBS authority

PKG-012 consumes accepted PKG-002 CBS series `120010`. Request and response
evidence are server-owned. Required indexation fails closed without nominal,
manual, cached, estimated, asserted, hard-coded, or other authoritative fallback.

### Monetary sequence

For each relevant nonzero grant:

1. round the full CBS indexed amount to `0.01`;
2. multiply by the unrounded ratio;
3. round the proportional amount to two decimals;
4. multiply by `1.35`;
5. round the per-grant offset to two decimals; and
6. sum the already-rounded per-grant offsets.

The exact `1.35` multiplier applies only after proportionality, is consumed
through accepted parameter context, and has no hidden fallback.

### Separation

Actual capitalizations remain separate records, snapshots, and calculation
effects. M06 is not a dependency and its results cannot become grants, actual
capitalizations, or historical prior-use facts.

## Accepted Module Ownership

### M08C

M08C owns:

- direct client-scoped grant CRUD;
- the exact six-field record;
- zero-record semantics;
- separate future-grant reservation;
- separate actual-capitalization records; and
- client isolation.

### M08D

M08D owns:

- the exact 15-year relevance rule;
- exact 32-year proportionality;
- PKG-002 CBS indexation;
- monetary rounding checkpoints;
- `1.35` placement;
- per-grant offset;
- aggregate grant offset; and
- formula evidence and version.

### M08A

M08A retains:

- initial exempt capital;
- final subtraction;
- future-grant impact;
- actual-capitalization impact;
- zero floor;
- remaining exempt capital; and
- final fixation result.

M08A receives the bounded M08D grant-offset handoff. M08D creates no competing
remaining-exempt-capital result.

### M08B

M08B remains the accepted parameter authority. PKG-012 creates no M08B authority
expansion.

## Definition Acceptance Evidence

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Ref/commit verification | `PASS` |
| Definition identity | `PASS` |
| Professional contract | `PASS` |
| Six-field contract | `PASS` |
| 15-year audit | `PASS` |
| 32-year audit | `PASS` |
| CBS/indexation | `PASS` |
| Rounding / `1.35` | `PASS` |
| Multi-grant | `PASS` |
| Actual-capitalization/M06 separation | `PASS` |
| Module ownership | `PASS` |
| Persistence/migration contract | `PASS` |
| Frontend contract | `PASS` |
| Saved-run/currentness | `PASS` |
| Client isolation | `PASS` |
| Golden cases | `PASS` |
| AC catalogue | `PASS` |
| NAC catalogue | `PASS` |
| Plan synchronization | `PASS` |
| Definition-vs-plan contradiction scan | `PASS` |
| Scope | `PASS` |

| Finding | Count |
|---|---|
| Blocking definition defects | `0` |
| Non-blocking definition findings | `0` |
| Scope violations | `0` |
| Professional decisions required | `0` |

## AC and NAC Outcome

### AC

- Count: `39`
- Range: `AC-012-001` through `AC-012-039`
- Missing IDs: `None`
- Duplicate IDs: `None`

### NAC

- Count: `30`
- Range: `NAC-012-001` through `NAC-012-030`
- Missing IDs: `None`
- Duplicate IDs: `None`

## Accepted Definition Expectations

| Area | Accepted expectation |
|---|---|
| Migration | `ADDITIVE_MIGRATION_REQUIRED` |
| Frontend | `NARROW_FRONTEND_CHANGE_REQUIRED` |

These are definition requirements only. Migration creation, migration execution,
and frontend implementation remain unauthorized.

## Accepted Golden Checkpoint

```text
indexed amount = 100000
ratio = 0.5
proportional amount = 50000.00
offset = 67500.00
```

No additional numeric golden result is established by this acceptance record.

## Accepted Exclusions

Definition acceptance does not authorize or include:

- prior withdrawals;
- prior fixation;
- an M07 prior-use resolver;
- document truth-resolution;
- source ranking;
- a client-declaration or evidence workflow;
- actual-capitalization redesign;
- M06 dependency;
- M08E or formal 161D output;
- M09-M14;
- scenarios, recommendations, or reports;
- a production-readiness claim;
- a V1/V2 full-parity claim; or
- any change to `02M`.

## Governance

- PKG-012 definition is accepted.
- The accepted definition HEAD remains
  `e11571f639e49ed38975da5a000f90c8c60fd45a`.
- PKG-012 implementation is `NOT_AUTHORIZED`.
- Migration creation is `NOT_AUTHORIZED`.
- Migration execution is `NOT_AUTHORIZED`.
- Production code is not authorized.
- Implementation tests are not authorized.
- This record does not authorize a master merge.
- The next package remains unauthorized.
- M08E remains excluded.
- M09-M14 remain blocked.
- `02M` remains frozen.

PKG_012_DEFINITION_ACCEPTED
