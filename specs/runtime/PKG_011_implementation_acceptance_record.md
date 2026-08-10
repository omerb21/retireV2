# PKG-011 Implementation Acceptance Record

## Package

| Field | Value |
|---|---|
| Package | `PKG-011` |
| Title | `M06 First-Stage Explicit Pension/Capital Conversion Foundation` |
| Acceptance type | `Implementation Acceptance` |
| Final decision | `ACCEPT_PKG_011_IMPLEMENTATION` |

## Authoritative Refs

| Field | Value |
|---|---|
| Master | `1e56337f2dfa2afba919a17218727eb9825fef62` |
| Accepted implementation HEAD | `9fffc9987859cf42c1b1f63ef155f07408910bc7` |
| Implementation branch | `pkg-011-implementation` |
| Merge base | `1e56337f2dfa2afba919a17218727eb9825fef62` |
| Commits above master | `8` |
| Alembic head | `e8f4b7c2d305` |

The immutable accepted implementation boundary is
`9fffc9987859cf42c1b1f63ef155f07408910bc7`.

## Accepted Definition Refs

The accepted definition remains in:

- `specs/runtime/PKG_011_FINAL_PACKAGE_DEFINITION.md`
- `specs/runtime/PKG_011_definition_acceptance_record.md`

Implementation acceptance is subordinate to and bounded by the accepted PKG-011
definition. This record references but does not copy or modify that definition.

## Acceptance History

### Initial Implementation Audit

| Field | Value |
|---|---|
| Initial implementation HEAD | `fd9091d13ed6db6c967a8726bda022c53f702e87` |
| Final status | `RETURN_PKG_011_IMPLEMENTATION_FOR_CORRECTION` |
| AC | `35 PASS / 6 FAIL / 1 NOT_PROVEN` |
| NAC | `37 PASS / 1 FAIL / 0 NOT_PROVEN` |

### Closed Defects and Evidence Gap

- `D-011-I001 - CLOSED`: persisted same-client M04/M05 integrity previously used
  incomplete single-column foreign keys. Migration `e8f4b7c2d305` adds composite
  `(revision_id, client_id)` predecessor uniqueness and M06 composite ownership
  foreign keys, with direct SQLite persistence and PostgreSQL DDL proof. Affected:
  `AC-011-034`, `AC-011-038`, and `NAC-011-027`.
- `D-011-I002 - CLOSED`: manifest fingerprints previously depended on ordering of
  semantically unordered collections. Canonicalization now covers exactly
  `warnings`, `informational_warnings`, `blocking_reasons`,
  `predecessors.m05_warning_snapshot`, and
  `predecessors.m05_warning_dispositions`. Affected: `AC-011-030`.
- `D-011-I003 - CLOSED`: frontend mutation-success ownership, loading ownership,
  and deterministic race evidence were incomplete. Correction provides owned
  request IDs, generation/domain ownership, bounded successor-transition
  ownership, stale success/error/rejection/finally protection, and deterministic
  A-to-B and A-to-B-to-A evidence. Affected: `AC-011-035`.
- `D-011-I004 - CLOSED`: `conversion_not_current` had no production path.
  Revision-specific technical eligibility assessment now preserves historical
  immutability and foreign/missing anti-leakage. Affected: `AC-011-033`.
- `D-011-I005 - CLOSED`: deterministic concurrency evidence now proves warning
  review versus correction, correction versus supersede, and warning-disposition
  failure rollback, with one winner, one child, and no residue. Affected:
  `AC-011-036`.
- `AC-011-040 evidence gap - CLOSED`: the former `NOT_PROVEN` result is now
  `PASS`. The re-audit proves the persisted evidence envelope for documentary
  resolved, planner warning draft, warning-reviewed, explicit zero, blocked,
  coefficient-corrected, superseded, and predecessor-invalidated cases.

## Final Acceptance Outcome

| Check | Result |
|---|---|
| AC (`AC-011-001` through `AC-011-042`) | `42 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC (`NAC-011-001` through `NAC-011-038`) | `38 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Blocking implementation defects | `None` |
| Remaining evidence gaps | `None` |
| Scope violations | `None` |
| Material non-blocking findings | `None` |

## Accepted Implementation Boundary

The accepted PKG-011 implementation provides:

- client-scoped M06 conversion subjects and same-client M01-M05 predecessor authority;
- an exact product/component allowlist and two exact conversion modes;
- documentary and planner-declared coefficient authority with canonical Decimal-only input;
- exact raw Decimal/ratio calculation with separate `ROUND_HALF_UP` display values;
- explicit-zero preservation and date/applicability gating;
- an immutable append-only lifecycle, exact warning review, and coefficient correction by immutable successor;
- a typed and versioned calculation/provenance manifest with order-independent fingerprints for unordered evidence collections;
- read-time predecessor revalidation and technical downstream eligibility, including `conversion_not_current`;
- client-scoped anti-leakage and intent-only API boundaries;
- generation/request-owned frontend behavior and deterministic concurrency/rollback; and
- additive persistence through Alembic head `e8f4b7c2d305`.

This acceptance does not authorize or claim:

- M07 or M08 implementation;
- M09-M14;
- tax, exemption, fixation, or 161D behavior;
- withdrawal, liquidity, pension commencement, historical capitalization creation,
  or conservation/residual logic;
- a coefficient catalogue or automatic lookup;
- the V1 `200.0` fallback;
- scenarios, comparisons, recommendations, or reports;
- production readiness or V1/V2 parity; or
- any change to `02M`.

## Test Evidence

The following is the independently audited final re-audit evidence.

### Backend

| Evidence | Result |
|---|---|
| Focused PKG-011 | `50 passed` |
| M02-M05 focused regression | `350 passed` |
| Full backend | `1005 passed` |

The focused re-audit environment reported no skipped or todo tests other than
existing warning output.

### Frontend

| Evidence | Result |
|---|---|
| Focused M06 | `14 passed` |
| Full frontend | `780 passed` |
| Production build/type-check | `PASS` |

### Repository and Migration

| Evidence | Result |
|---|---|
| Alembic head | `e8f4b7c2d305` |
| Master-to-head upgrade | `PASS` |
| Correction downgrade/re-upgrade | `PASS` |
| SQLite composite FK inspection | `PASS` |
| PostgreSQL offline upgrade/downgrade | `PASS` |
| Python compile | `PASS` |
| `git diff --check` | `PASS` |
| Audit checkout | `clean` |

## Governance Status

- PKG-011 implementation is accepted.
- The accepted implementation HEAD is immutable historical authority:
  `9fffc9987859cf42c1b1f63ef155f07408910bc7`.
- This acceptance record does not merge the implementation.
- Master merge remains unauthorized.
- A separate acceptance-record audit is required.
- A separate master merge authorization is required after that audit.
- M07 and M08 remain unchanged and unauthorized.
- M09-M14 remain blocked.
- `02M` remains frozen.
- The next package remains unauthorized.
- `pkg-011-implementation` must not change before acceptance-record audit completes.

PKG_011_IMPLEMENTATION_ACCEPTED
