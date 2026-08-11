# PKG-013 Implementation Acceptance Record

## Record Identity

- Package: `PKG-013`
- Title: `M09 Deterministic Monthly Cashflow Orchestration Foundation`
- Acceptance type: `Implementation Acceptance`
- Final decision: `ACCEPT_PKG_013_IMPLEMENTATION`
- Implementation base/master: `f8ed3b2b4a16aa98a7f2746fa782dafe965e99fc`
- Accepted definition HEAD: `5293d8ccdee9d3700fc09fd276ba6ebb39449512`
- Accepted implementation HEAD: `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea`
- Current Alembic head: `c4e8a1f6d203`

The accepted implementation boundary is permanently
`50cdf8322d0a24215f5f9e1c488e5acb3736c1ea`. The documentation-only
acceptance-record commit above that HEAD does not replace, extend, or redefine
the accepted implementation boundary.

## Exact Implementation History

The accepted implementation consists of these seven commits, in order:

1. `8c80acc2aaca1036d4aeb3f3b7a91272c36e9baa` — `feat: add PKG-013 persistence foundation`
2. `ccb763f0b7c2d005a04a7d2309164753c47307e7` — `feat: implement deterministic M09 cashflow orchestration`
3. `7b3d8017368e54b7c724235db072dc0c2ae530f5` — `feat: add bounded M09 cashflow workspace`
4. `b0e292a114bc168089ea136f835e4dee6638d13a` — `test: record PKG-013 implementation evidence`
5. `ea0f043ccfee68025bd127877d34e0c5f527b8b0` — `fix: bind and bound PKG-013 monetary evidence`
6. `84846caf5ddfbb63640e1ac549c64340a9961115` — `fix: enforce PKG-013 append-only persistence`
7. `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea` — `test: prove PKG-013 correction evidence`

The acceptance-record commit is documentation evidence only and is not an
implementation commit.

## Audit and Defect History

The initial implementation candidate was
`b0e292a114bc168089ea136f835e4dee6638d13a`. Its initial implementation
acceptance audit decision was `RETURN_PKG_013_IMPLEMENTATION_FOR_CORRECTION`,
with these blocking findings:

- `D-013-I001`
- `D-013-I002`
- `D-013-I003`
- `D-013-I004`

The correction chain was:

- `ea0f043ccfee68025bd127877d34e0c5f527b8b0`
- `84846caf5ddfbb63640e1ac549c64340a9961115`
- `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea`

Final correction re-audit result:

- `D-013-I001 CLOSED`
- `D-013-I002 CLOSED`
- `D-013-I003 CLOSED`
- `D-013-I004 CLOSED`
- New findings: none
- Final decision: `ACCEPT_PKG_013_IMPLEMENTATION`

## Single-Authority Acceptance

Every material business calculation has exactly one authoritative owner.

M09 is accepted as `ORCHESTRATOR_AND_AGGREGATOR_ONLY`. M09 owns only:

- monthly alignment of already authoritative components;
- inflow aggregation;
- outflow aggregation;
- `period_net`;
- deterministic range totals; and
- orchestration, persistence, integrity, and currentness mechanics.

M09 contains no duplicate M05, M06, M07, M08, tax, CBS, fixation, NPV, or
other formula authority. M06 remains the sole pension-conversion formula
owner.

## Accepted Family

The exact implemented and accepted scenario family is:

`deterministic_monthly_cashflow/v1`

No other M09 scenario family was implemented or accepted.

## M06 Handoff Integrity

- M06 computes the authoritative monthly pension.
- M06 produces the canonical downstream handoff.
- The handoff amount is included in fingerprinted manifest evidence.
- The separate persisted/indexed handoff amount must exactly match the
  verified manifest evidence.
- M09 consumes the fingerprint-bound manifest value.
- A mismatch or fingerprint tampering fails closed.
- M09 does not recalculate `balance / coefficient`.
- The accepted typed blocker is
  `m06_authoritative_handoff_integrity_invalid`.

## Server-Owned Component Inventory

The accepted implementation includes:

- an immutable server-owned resolved inventory;
- the complete mandatory component universe;
- automatic inclusion of mandatory eligible components;
- server-only `server_resolved_none`;
- no caller or UI ability to reduce, omit, or waive the inventory;
- blocking of duplicate economic meaning;
- no partial authoritative portfolio; and
- no `run anyway` path.

## Recurring Eligibility

M09-specific recurring authority validation includes:

- same-client ownership;
- current lifecycle;
- monthly frequency;
- gross basis for income;
- source authority and review;
- canonical Decimal value;
- full-month applicability; and
- source dates, currentness, and fingerprint.

No proration or frequency conversion is implemented.

## Dependency Boundaries

### M05

- Balances are not cashflow components.
- `eligible_for_m06` is not generic M09 authority.
- M05 appears only behind M06 provenance.

### M06

- Only a current, eligible, canonical monthly handoff is admitted.
- Capital-equivalent output is excluded.
- No conversion formula is duplicated in M09.

### M07

- M07 is omitted.
- There is no `m08a_fixation/v1` inheritance.

### M08

- M08 is omitted for the current vocabulary.
- There is no fixation or M08 calculation path.

## Decimal and Numeric-Domain Contract

- Monetary authority is Decimal-only.
- Float authority and silent float conversion are prohibited.
- Authoritative upstream components are not rerounded.
- Addition and subtraction are exact.

The accepted persisted monetary domain is `Numeric(20,2)`, with these limits:

- Maximum: `999999999999999999.99`
- Minimum: `-999999999999999999.99`

Representability is validated before persistence for:

- component amounts;
- monthly inflow, outflow, and net values; and
- range totals.

Accepted typed reason codes are:

- `component_amount_outside_numeric_20_2`
- `aggregate_outside_numeric_20_2`

Numeric overflow fails through the typed lifecycle rather than an uncaught
database exception.

## Persistence and Append-Only Acceptance

The accepted migration chain is:

- Initial PKG-013 schema: `a7c9e1f3b805`
- Append-only correction: `c4e8a1f6d203`
- Current single Alembic head: `c4e8a1f6d203`

All three immutable M09 evidence tables are protected at database level
against UPDATE and DELETE. Accepted behavior is:

- INSERT allowed;
- SELECT allowed;
- UPDATE denied;
- DELETE denied; and
- successor inserts allowed.

The SQLite test path and PostgreSQL DDL enforce equivalent append-only
semantics.

## Run Lifecycle

Accepted persisted run statuses are exactly:

- `success_complete`
- `validation_failed`
- `dependency_failed`
- `calculation_failed`
- `unsupported`

Run status remains separate from currentness and M10 technical eligibility.
Numeric aggregate overflow uses controlled `calculation_failed` and does not
persist partial authoritative monthly rows.

## Currentness and M10 Boundary

- Currentness is evaluated at read time.
- Historical stale runs remain readable.
- Stale, superseded, or integrity-invalid runs are not current.
- M10 technical eligibility is derived fail-closed evidence only.
- No M10 comparison or recalculation implementation exists.
- M10 may consume persisted M09 results only.
- M10-M14 remain blocked.

## Client Isolation

Client isolation is accepted for inventory, runs, history, currentness, and
eligibility. Foreign or nonexistent resources do not leak identity. Direct
service invocation also enforces ownership.

## Frontend Acceptance

The frontend implements only the bounded PKG-013 workspace. It exposes no
authoritative component-selection, omission, waiver, none-declaration, or
partial-run controls.

Client async isolation uses:

- captured client ID;
- monotonic route/context generation;
- per-channel/request epoch; and
- unique active loading ownership.

Controlled-promise evidence covers inventory, execution, history, and the
saved-result/currentness/M10-eligibility composite path. A→B and A→B→A stale
success, error, and finally behavior is protected, including old-A/new-A
distinction.

## AC/NAC Implementation Result

- AC result: `40 PASS / 0 FAIL / 0 NOT_PROVEN`
- AC range: `AC-013-001` through `AC-013-040`
- NAC result: `32 PASS / 0 FAIL / 0 NOT_PROVEN`
- NAC range: `NAC-013-001` through `NAC-013-032`

These are implementation acceptance results.

## Independent Test Evidence

The final independent WORK re-audit recorded:

- Focused backend: `94 passed, 0 failed, 0 skipped`
- Focused frontend: `14 passed, 0 failed, 0 skipped`
- Targeted predecessor regression: `200 passed, 0 failed, 0 skipped`
- Full backend: `1072 passed, 0 skipped, 9 warnings`
- Full frontend: `840 passed across 26 files, 0 skipped`
- Frontend production build: `PASS`
- Python compile: `PASS`
- Alembic head: `c4e8a1f6d203`
- SQLite upgrade/downgrade/re-upgrade: `PASS`
- PostgreSQL offline upgrade/downgrade SQL: `PASS`
- `git diff --check`: `PASS`

The remaining backend warnings were:

- 2 FastAPI `on_event` deprecation warnings; and
- 7 existing PKG-003 legacy Pydantic fixture warnings.

They were not classified as PKG-013 acceptance blockers. This acceptance does
not make a production-readiness claim.

## Frozen Governance Artifacts

Implementation acceptance did not modify:

- `PKG_013_FINAL_PACKAGE_DEFINITION.md`
- `PKG_013_definition_acceptance_record.md`
- `V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`
- accepted PKG-012 artifacts.

Accepted definition HEAD remains
`5293d8ccdee9d3700fc09fd276ba6ebb39449512`. Accepted implementation HEAD
remains `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea`.

## Governance

- Implementation acceptance does not itself merge to master.
- No master merge has occurred.
- No M10 implementation was added.
- M11-M14 were not opened.
- No next package was opened or authorized.
- M08E remains excluded.
- `02M` remains frozen.
- No production-readiness claim is made.

PKG_013_IMPLEMENTATION_ACCEPTED
