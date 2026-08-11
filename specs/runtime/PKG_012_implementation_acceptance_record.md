# PKG-012 Implementation Acceptance Record

## Package

| Field | Value |
|---|---|
| Package | `PKG-012` |
| Title | `M08C/M08D Exempt Grant Offset and Historical Indexation Foundation` |
| Acceptance type | `Implementation Acceptance` |
| Final decision | `ACCEPT_PKG_012_IMPLEMENTATION` |

## Authoritative Refs

| Field | Value |
|---|---|
| Historical master/base | `79a328f3153db53249457fd157d83728ac576745` |
| Accepted historical definition HEAD | `e11571f639e49ed38975da5a000f90c8c60fd45a` |
| Definition acceptance/master commit | `79a328f3153db53249457fd157d83728ac576745` |
| Accepted implementation HEAD | `9381982143a8ad39879fa103567f672c5ac7a713` |
| Implementation branch | `pkg-012-implementation` |
| Implementation commits above master | `8` |
| Alembic head | `f9a1c3e5b702` |

The immutable accepted implementation boundary is
`9381982143a8ad39879fa103567f672c5ac7a713`. The commit containing this
acceptance record is documentation evidence only and does not become, replace,
or redefine the accepted implementation HEAD.

## Accepted Definition Refs

The accepted definition remains in:

- `specs/runtime/PKG_012_FINAL_PACKAGE_DEFINITION.md`
- `specs/runtime/PKG_012_definition_acceptance_record.md`

Implementation acceptance is subordinate to and bounded by the accepted
PKG-012 definition. This record does not modify that definition.

## Accepted Implementation Commit History

The accepted implementation sequence is:

1. `bf27a2e952146135e647922e529fe1e2ae45e3f6`
2. `ebebdc89a2d9323fb6375fcd1170a176e8178f93`
3. `cd787b4ca8316101892f2664458a5d1b6b319a73`
4. `56668bdb28571d12287876f9b6d3777f0bf4f3fd`
5. `f56864f2e842ab92c738ef46e71171e5fd87e58d`
6. `08701db1a64fbd10668b8ae1deaa8875b62b42be`
7. `11ba36705f03010d057645205c09b0f066a90968`
8. `9381982143a8ad39879fa103567f672c5ac7a713`

This sequence is linear and contains no merge commits.

## Accepted Implementation Boundary

### M08C Grant Contract

- The business contract contains exactly `employer_name`,
  `employer_withholding_file_number`, `employment_start_date`,
  `employment_end_date`, `grant_receipt_date`, and `exempt_grant_amount`.
- `grant_id` is a server-owned technical identity.
- Zero persisted rows means no exempt grants.
- The six facts use direct professional-user authority within the accepted
  package boundary.
- Caller-indexed authority and a source-ranking or evidence-sufficiency
  authority layer are not included.
- CRUD is client-scoped.

### Fifteen-Year Rule

```text
years_difference =
    eligibility_year - grant_year
    + (eligibility_month - grant_month) / 12
    + (eligibility_day - grant_day) / 365.25
```

Exclusion occurs only when:

```text
years_difference > 15
```

Exactly 15 years is included.

### Thirty-Two-Year Rule

- The window is exactly `11,688` days.
- The denominator is the full employment duration.
- The numerator is bounded overlap with the window.
- Endpoints are not counted inclusively.
- Post-eligibility time is excluded from the numerator.
- The ratio is not pre-rounded.

### CBS Authority

- The accepted PKG-002 authority and series `120010` are used.
- CBS request and evidence are server-owned, and raw evidence is retained.
- Caller-forged CBS authority is rejected.
- Required CBS failure fails closed without an authoritative fallback.
- A canonical zero may bypass the live CBS call without fabricating CBS
  request or response evidence.

### Decimal and Rounding Contract

- Canonical arithmetic uses `Decimal`, `ROUND_HALF_UP`, and quantum `0.01`.
- The indexed amount is rounded first.
- The rounded indexed amount is multiplied by the unrounded Decimal ratio.
- The proportional amount is rounded, multiplied by the admitted `1.35`, and
  the per-grant offset is rounded.
- The aggregate sums the independently rounded per-grant offsets.

Accepted numeric reproduction:

```text
raw CBS = 2.675
indexed = 2.68
ratio = 0.5
proportional = 1.34
offset = 1.81
```

Accepted golden reproduction:

```text
indexed = 100000.00
ratio = 0.5
proportional = 50000.00
offset = 67500.00
```

### Multiplier Authority

- The admitted accepted parameter context is authoritative.
- The accepted multiplier is exactly `1.35`.
- The engine consumes the admitted value.
- Missing or incompatible parameter context fails closed.
- There is no calculation-driving hard-coded fallback.

### Multiple Grants

- Grants remain independent by `grant_id`.
- There is no automatic deduplication or merge.
- Per-grant rounding occurs before aggregate summation.

### Actual Capitalizations and M06

- Actual capitalizations remain separate and grant rules do not apply to them.
- M06 remains excluded from PKG-012.

### M08A Ownership

M08A retains ownership of initial exempt capital, future-grant effects, actual
capitalization effects, final subtraction, the zero floor, remaining exempt
capital, and the final fixation result. M08D provides only the bounded aggregate
grant offset and per-grant breakdown.

### Saved Runs and Currentness

- Persisted client-scoped grants are the sole authoritative grant source for a
  saved run.
- A saved run freezes canonical Decimal evidence and retains parameter-set and
  multiplier provenance.
- Later grant edit or deletion does not mutate historical saved-run evidence.
- Run-detail reload reproduces the frozen state.
- No caller-authored legacy grant envelope can create an authoritative saved
  run.

### Client Isolation

- Persisted grants are scoped to their owning client.
- Foreign grant injection is rejected, and foreign CRUD identities remain
  non-leaking.
- CBS evidence remains server-owned and client-bound.

### Frontend

- The UI provides CRUD for the exact six business fields and provides no
  indexed-amount input.
- Per-grant and aggregate results are displayed.
- Client ID plus monotonic generation owns asynchronous state.
- Stale A-to-B and A-to-B-to-A success, structured error, rejection, and
  `finally` paths are guarded.
- Pending-new-owner evidence is accepted for load, create, update, delete, and
  calculate/result behavior.

## Migration

| Field | Value |
|---|---|
| Revision | `f9a1c3e5b702` |
| Parent | `e8f4b7c2d305` |
| Alembic heads | `1` |
| Migration type | `Additive` |

Legacy rows are preserved. No withholding-file number is inferred during
backfill, legacy indexed values are not rewritten, and nullable indexed
persistence permits system-derived authority.

## Acceptance Audit History

The first implementation audit returned
`RETURN_PKG_012_IMPLEMENTATION_FOR_CORRECTION` with:

- `D-012-I001`
- `D-012-I002`
- `D-012-I003`

Subsequent re-audits kept the package blocked until the defects and evidence
requirements were closed. The final accepted re-audit found:

- `D-012-I001 CLOSED`
- `D-012-I002 CLOSED`
- `D-012-I003 CLOSED`
- no new blocking or material defect; and
- no remaining evidence gap.

The correction history remains part of the acceptance evidence.

## Final AC/NAC Acceptance

| Check | Result |
|---|---|
| AC | `39 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `30 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Previously passing criteria regressed | `None` |
| Blocking implementation defects | `None` |
| Remaining evidence gaps | `None` |

## Accepted Test Evidence

The following records the final independent WORK evidence.

| Evidence | Result |
|---|---|
| Focused backend | `102 passed` |
| Zero/saved-run/multiplier focused | `4 passed` |
| Focused frontend | `58 passed` |
| Full backend | `1028 passed, 0 skipped, 9 warnings` |
| Full frontend | `826 passed` |
| Frontend production build | `PASS` |
| Python compileall | `PASS` |
| Alembic head | `f9a1c3e5b702` |
| `git diff --check` | `PASS` |
| Final tracked status | `clean` |

The nine warnings comprise two FastAPI `on_event` deprecations and seven
existing PKG-003 legacy float-evidence fixture warnings. There is no PKG-012
zero Decimal serialization warning.

## Frozen Definition Integrity

The following files remained byte-identical throughout implementation:

- `specs/runtime/PKG_012_FINAL_PACKAGE_DEFINITION.md`
- `specs/runtime/PKG_012_definition_acceptance_record.md`
- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`

## Governance Status

- PKG-012 implementation is accepted.
- The accepted implementation HEAD is
  `9381982143a8ad39879fa103567f672c5ac7a713`.
- This acceptance record does not redefine or replace that accepted
  implementation HEAD.
- Master merge remains `NOT_AUTHORIZED`; this record does not merge code.
- The next package remains `NOT_AUTHORIZED`.
- M08E remains excluded.
- M09-M14 remain blocked.
- `02M` remains frozen.
- No other package implementation is authorized by this record.

PKG_012_IMPLEMENTATION_ACCEPTED
