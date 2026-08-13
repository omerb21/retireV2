# PKG-014 Implementation Acceptance Record

## Record Identity

- Package: `PKG-014`
- Title: `M09 Declared Retirement Cashflow Adjustments and Parallel Scenario Subjects Foundation`
- Acceptance type: `Implementation Acceptance`
- Decision: `ACCEPT_PKG_014_IMPLEMENTATION`
- Definition base / implementation base: `c9af24365a533e509fd327ce5056dae719b656bf`
- Accepted definition HEAD: `39fbc553e6bca7f10b9c1d237d3be1366be11477`
- Definition acceptance evidence on master: `c9af24365a533e509fd327ce5056dae719b656bf`
- Accepted implementation HEAD: `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d`
- Alembic head: `e6b4c8d2f507`
- M10 implementation: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`

The accepted implementation boundary is permanently
`0fd7fb82c3cea99dde4be098d6cb82b08c25c76d`. The documentation-only commit
containing this record does not replace, extend, or redefine that accepted
implementation HEAD.

## Exact Implementation History

The accepted implementation consists of exactly these eleven linear commits
above `c9af24365a533e509fd327ce5056dae719b656bf`, in order:

1. `5fb4cd84bb2d173099e85e444225e325d83ef5c1` — `feat: add PKG-014 scenario subject persistence`
2. `bdfc6c7df6ac4db1befc99c0a5f9fab553142697` — `feat: execute PKG-014 parallel cashflow subjects`
3. `60f3cdbdaf938a66d378630c7b28b724e19ca7f0` — `feat: add PKG-014 scenario subject workflow`
4. `49ebfaa868ecafe97213dec74d4f2baa82268df6` — `test: record PKG-014 implementation evidence`
5. `e7d761429b84d632ed4f204edee5073107b9a27d` — `fix: close PKG-014 fail-closed evidence gaps`
6. `34a425a95fe3cf8237901d6a1da42be0a99ea137` — `fix: verify PKG-014 semantic result integrity`
7. `b93b72d881087cd40bb1130c5055bd35934208a4` — `fix: seal PKG-014 manifests and fail closed on tampering`
8. `3da39e195c5cc4a2caf8660518e7b7515871f6dd` — `fix: isolate PKG-014 subject workflows and evidence`
9. `84068dfb5a13fca0a2c99f88ec238d4288a3da39` — `test: correct PKG-014 implementation evidence`
10. `b53279c8c4e3956d04d5a96941e9e52029ceee2c` — `test: prove PKG-014 subject async isolation`
11. `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d` — `test: complete PKG-014 A-B-A async evidence`

The history contains no merge commit. This acceptance-record commit is
documentation evidence only and is not an implementation commit.

## Audit History

### Initial Implementation Audit

- Decision: `RETURN_PKG_014_IMPLEMENTATION_FOR_CORRECTION`
- Findings: `D-014-I001`, `D-014-I002`, `D-014-I003`, `D-014-I004`
- AC: `29 PASS / 7 FAIL / 4 NOT_PROVEN`
- NAC: `31 PASS / 1 FAIL / 1 NOT_PROVEN`

### First Correction Re-audit

- `D-014-I001 CLOSED`
- `D-014-I003 CLOSED`
- `D-014-I004 CLOSED`
- `D-014-I002 OPEN`
- AC: `39 PASS / 0 FAIL / 1 NOT_PROVEN`
- NAC: `33 PASS / 0 FAIL / 0 NOT_PROVEN`
- Remaining criterion: `AC-014-037 NOT_PROVEN`

### First Async Evidence Re-audit

`D-014-I002` remained open because direct A→B→A evidence was incomplete for
plain rejection, structured API error, and stale `finally`/loading ownership.

### Final Async Evidence Re-audit

- `D-014-I002 CLOSED`
- AC: `40 PASS / 0 FAIL / 0 NOT_PROVEN`
- NAC: `33 PASS / 0 FAIL / 0 NOT_PROVEN`
- Findings: `NO_FINDING`
- Decision: `ACCEPT_PKG_014_IMPLEMENTATION`

This record preserves the failed and partial audit history; final acceptance
does not erase those earlier results.

## Accepted Implementation Contract Summary

Without redefining the accepted package definition, the accepted
implementation provides:

- server-owned immutable scenario subjects;
- exact `scenario_family = declared_retirement_cashflow_adjustments`;
- exact `scenario_contract_version = v1`;
- a uniquely server-owned baseline subject;
- a canonical empty baseline adjustment manifest with
  `server_resolved_no_scenario_adjustments`;
- a closed two-type adjustment vocabulary;
- `ADDITIVE_ONLY` semantics;
- canonical positive Decimal ILS amounts;
- explicit contained full-month ranges;
- preservation of adjustment multiplicity;
- a separately server-owned factual inventory;
- `factual_baseline_material_fingerprint`;
- `m09-subject-currentness-v1`;
- `m09-to-m10-eligibility-v2`;
- immutable subject, run, and result evidence;
- database-enforced manifest sealing and append-only protection;
- fail-closed manifest parity and result integrity;
- client isolation;
- a bounded frontend scenario workflow;
- subject/client generation-aware asynchronous isolation; and
- no M10 comparator implementation.

## Defect Closures

### D-014-I001

`D-014-I001 CLOSED`

The accepted correction includes an additive manifest-seal migration,
database rejection of post-seal adjustment INSERT, immutable child-set
semantics, manifest-to-row parity validation, and fail-closed currentness,
eligibility, and read behavior under tampering. Live PostgreSQL execution was
not performed and is not claimed.

### D-014-I002

`D-014-I002 CLOSED`

Final controlled-promise evidence covers exactly these seven real asynchronous
channels:

1. `subject-list`
2. `baseline-resolution`
3. `subject-creation`
4. `subject-detail`
5. `subject-execution`
6. `run-history`
7. `run-result`

The evidence directly covers A→B, A→B→A, stale success, ordinary rejection,
structured `ApiTransportError`, and stale `finally`/loading ownership.
Production ownership mechanisms remained unchanged throughout the final two
evidence-only commits.

### D-014-I003

`D-014-I003 CLOSED`

The accepted UI presents `Factual baseline — read-only` separately from
`Declared scenario adjustments`. Each persisted adjustment occurrence exposes
the accepted type, amount, and range evidence, and multiplicity remains
visible. No factual edit, suppression, or replacement authority exists.

### D-014-I004

`D-014-I004 CLOSED`

Accepted evidence includes semantic-order permutation proof, factual-baseline
fingerprint dimension sensitivity and invariance, upstream factual-change
staleness, complete client-isolation evidence, tamper/result-integrity
evidence, and the corrected implementation evidence matrix.

## Migration Evidence

- Entering Alembic head: `c4e8a1f6d203`
- PKG-014 initial migration: `d5f9b2a7c406`
- PKG-014 manifest-seal correction: `e6b4c8d2f507`
- Final Alembic head: `e6b4c8d2f507`
- Alembic heads: exactly one
- Correction migration: additive
- `d5f9b2a7c406`: remained immutable after initial implementation review
- SQLite upgrade/downgrade/re-upgrade: verified
- PostgreSQL offline upgrade/downgrade DDL: verified
- Live PostgreSQL execution: `NOT_PERFORMED`

## Independently Accepted Test Evidence

Backend evidence from the focused correction audit:

- Focused PKG-014 backend: `22 passed`
- Full backend in the WORK Linux audit environment: `1094 passed, 0 skipped`
- Broad PKG-011/PKG-013 predecessor regression slice: `94 passed`
- PKG-014 warnings: none
- Python compile: `PASS`

The final asynchronous evidence-only corrections did not modify backend code
or migrations, so backend tests were not rerun in the final evidence-only
re-audit.

Frontend final accepted evidence:

- `M09ScenarioSubjects` component: `48 passed`
- Focused `M09ScenarioSubjects` plus legacy `M09CashflowScreen`: `62 passed`
- Full frontend: `888 passed`
- Production build/type-check: `PASS`
- `git diff --check`: `PASS`

Environment-specific WORK counts above are preserved and are not replaced by
counts from another execution environment.

## AC/NAC Result

- `AC-014-001` through `AC-014-040`: `40 PASS / 0 FAIL / 0 NOT_PROVEN`
- `NAC-014-001` through `NAC-014-033`: `33 PASS / 0 FAIL / 0 NOT_PROVEN`
- `AC-014-037 PASS` after final controlled-promise A→B→A evidence completion

## Stop Conditions

The final audit cleared all fourteen accepted stop conditions:

1. `PKG_014_SINGLE_AUTHORITY_VIOLATION`
2. `PKG_014_V1_SEMANTIC_REWRITE_REQUIRED`
3. `PKG_014_SUBJECT_CURRENTNESS_LEAKAGE`
4. `PKG_014_FACTUAL_UNIVERSE_REDUCTION_REQUIRED`
5. `PKG_014_REPLACEMENT_OR_SUPPRESSION_REQUIRED`
6. `PKG_014_NEW_CALCULATION_FORMULA_REQUIRED`
7. `PKG_014_RETIREMENT_TIMING_FORMULA_REQUIRED`
8. `PKG_014_TAX_NPV_OPTIMIZATION_REQUIRED`
9. `PKG_014_NUMERIC_PRECISION_CONFLICT`
10. `PKG_014_DB_IMMUTABILITY_BLOCKED`
11. `PKG_014_CLIENT_ISOLATION_BLOCKED`
12. `PKG_014_CALLER_FORGED_AUTHORITY_REQUIRED`
13. `PKG_014_M10_IMPLEMENTATION_REQUIRED`
14. `PKG_014_PREDECESSOR_REGRESSION_BLOCKED`

Their clearance does not authorize work beyond PKG-014.

## PKG-013 Preservation

`deterministic_monthly_cashflow/v1` remains behaviorally preserved. There is
no retrofit of legacy runs and no rewrite of:

- `m09-currentness-v1`;
- `m09-to-m10-eligibility-v1`;
- legacy result meaning; or
- the legacy predecessor chain.

## M10 Boundary

- M10 implementation: `NOT_AUTHORIZED`
- PKG-014 provides only the accepted parallel M09 outputs and evidence
  foundation.
- No M10 comparator model, service, route, or UI is part of PKG-014.

## Governance

- Accepted implementation HEAD is immutable:
  `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d`.
- This acceptance-record commit is documentation-only evidence above it.
- This record does not itself become the accepted implementation HEAD.
- Master merge remains `NOT_AUTHORIZED` until a separate acceptance-record
  audit authorizes it.
- Next package remains `NOT_AUTHORIZED`.
- No production-readiness or V1/V2 parity claim is made.
- M08E remains excluded.
- `02M` remains frozen.

PKG_014_IMPLEMENTATION_ACCEPTED
