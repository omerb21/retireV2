# PKG-014 Definition Acceptance Record

## Record Identity

| Field | Value |
|---|---|
| Package | `PKG-014` |
| Title | `M09 Declared Retirement Cashflow Adjustments and Parallel Scenario Subjects Foundation` |
| Acceptance type | `Definition Acceptance` |
| Decision | `ACCEPT_PKG_014_DEFINITION` |
| Definition base/master | `f1cbddbf27d7712ce2409248240a0cb4cadebc8d` |
| Accepted definition HEAD | `39fbc553e6bca7f10b9c1d237d3be1366be11477` |
| Current Alembic head | `c4e8a1f6d203` |
| Implementation | `NOT_AUTHORIZED` |
| M10 implementation | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |

## Historical Definition Boundary

The immutable accepted definition boundary is:

`39fbc553e6bca7f10b9c1d237d3be1366be11477`

The acceptance-record commit created directly above that boundary is
documentation evidence only. It does not replace, extend, or redefine the
accepted definition boundary and is not an implementation authorization.

## Exact Definition History

The accepted definition consists of exactly these two commits, in order:

1. `975fa38b6d7f65fdcb511f7e20ed29e452008b84` — `docs: define PKG-014 parallel cashflow scenarios`
2. `39fbc553e6bca7f10b9c1d237d3be1366be11477` — `docs: clarify PKG-014 contract identity and comparability`

The acceptance-record commit itself is not part of the accepted definition
boundary.

## Audit History

Initial WORK decision:

`RETURN_PKG_014_DEFINITION_FOR_CORRECTION`

Initial defects:

- `D-014-D001` — family/version token ambiguity.
- `D-014-D002` — missing shared factual-baseline pair invariant.

Final re-audit:

- `D-014-D001 CLOSED`
- `D-014-D002 CLOSED`
- `NO_FINDING`
- `ACCEPT_PKG_014_DEFINITION`

This record preserves the initial return-for-correction history; it does not
represent the original draft as having passed its first audit.

## Accepted Identity and Architecture

- `scenario_family = declared_retirement_cashflow_adjustments`
- `scenario_contract_version = v1`
- Combined identifier: `declared_retirement_cashflow_adjustments/v1`
- M09 role: `ORCHESTRATOR_AND_AGGREGATOR_ONLY`

Every material business calculation continues to have exactly one
authoritative owning module or engine. M09 owns only bounded scenario-subject
orchestration, full-month applicability, admitted adjustment addition,
accepted M09 aggregation, immutable evidence, per-subject currentness, and
subject-aware eligibility evidence. It gains no duplicated upstream,
professional, tax, timing, NPV, ranking, recommendation, or optimization
formula authority.

## Accepted Scenario-Subject Contract

- Scenario subjects are immutable, server-owned, and client-scoped.
- Exactly one server-owned baseline exists per
  `client_id + scenario_family + scenario_contract_version`.
- The baseline has a canonical empty adjustment manifest and marker
  `server_resolved_no_scenario_adjustments`.
- Caller-authored empty adjustments cannot create or forge the baseline.
- Subject calculation-semantic identity excludes evidence-only IDs, labels,
  actors, timestamps, run IDs, and sequence fields.
- Semantic duplicate creation fails closed as
  `scenario_subject_semantically_duplicate`.
- Separately declared semantically equal adjustments remain
  calculation-affecting through preserved multiplicity.
- Subject and historical evidence is immutable and append-only by contract.

## Accepted Adjustment Contract

The closed adjustment vocabulary is exactly:

- `declared_additional_monthly_income`
- `declared_additional_monthly_expense`

The adjustment boundary is exactly `ADDITIVE_ONLY`. Each adjustment is an
explicit planner-declared hypothetical addition, not a replacement,
suppression, waiver, correction, or mutation of a factual component.

Amounts are canonical Decimal ILS values with exactly two decimal places:

- Minimum: `0.01`
- Maximum: `999999999999999999.99`
- Zero: invalid
- Negative: invalid
- Float authority, scientific-notation canonicalization, silent rounding,
  clipping, and coercion: prohibited

Ranges use explicit strict `YYYY-MM` full months with inclusive endpoints,
must be wholly contained in the run horizon, and allow no proration, implicit
extension, inferred continuation, or day-level calculation.

## Factual Authority Separation

The complete factual inventory remains immutable and server-owned. It is
separate from the subject-owned, immutable, planner-declared adjustment
manifest. Caller and UI cannot select, reduce, waive, suppress, replace, or
forge the authoritative factual universe or its completeness/currentness
evidence.

An adjustment cannot repair a missing factual dependency. Execution evidence
binds both authority domains while preserving their distinct meaning and
provenance.

## Parallel Currentness

The new-family currentness key is:

`client_id + scenario_subject_id + scenario_family + scenario_contract_version`

The contract is `m09-subject-currentness-v1`:

- one current leaf per subject;
- multiple subjects may be current simultaneously;
- rerunning A supersedes only A;
- B does not stale A merely by existing or running; and
- a factual upstream change may stale every affected subject.

Accepted `m09-currentness-v1` behavior is not reinterpreted.

## Per-Run Eligibility and Future Pair Admission

`m09-to-m10-eligibility-v2` is a per-run, derived, fail-closed contract. It
proves individual admissibility and exposes the persisted:

`factual_baseline_material_fingerprint`

That fingerprint canonically binds calculation-affecting factual baseline
material and excludes scenario adjustments and evidence-only metadata.
Individual factual integrity does not prove equality to a future peer.

Future pair-level M10 admission requires exact equality of factual baseline
material, component-domain version, M09 engine/result-schema versions, and
relevant calculation-affecting factual upstream versions, in addition to same
client, exact family/version, exact horizon, individual currentness and
eligibility, and semantically distinct adjustment manifests.

Two otherwise eligible runs with different
`factual_baseline_material_fingerprint` values are not comparable and fail
closed with:

`comparison_factual_baseline_material_mismatch`

Future M10 may compare the persisted fingerprints and outputs. It may not
reconstruct, normalize, or reconcile different factual baselines.

## Existing Family and M10 Boundary

`deterministic_monthly_cashflow/v1` remains historically and semantically
unchanged. Legacy runs remain readable under their accepted contract and are
not retrofitted into default subjects, subject-aware currentness, eligibility
v2, or automatic comparison inputs.

PKG-014 does not implement M10. A future M10 remains `COMPARATOR_ONLY`, bounded
to persisted side-by-side values, exact `A - B`, equality, and numeric
greater/lower. No percentage, ranking, recommendation, score, annualization,
NPV, or automatic pair selection is accepted.

The preferred first future pair is baseline subject versus one adjusted
subject only when both use the exact same factual baseline material.

## Explicit Authority and Scope Exclusions

The accepted definition creates no authority for:

- retirement or pension timing formulas;
- factual income cessation;
- M05, M06, M07, or M08 formula duplication;
- tax, fixation, CBS, indexation, grants, NPV, or investment returns;
- allocation, withdrawal, commutation, optimization, ranking, recommendation,
  preference, forecast, or report behavior;
- M10 implementation;
- M11-M14 implementation;
- M08E;
- V1 constants or V1/V2 parity; or
- production readiness.

M08E remains excluded and `02M` remains frozen.

## AC/NAC Fidelity

- AC result: `40 PASS / 0 FAIL / 0 NOT_PROVEN`
- AC range: `AC-014-001` through `AC-014-040`
- NAC result: `33 PASS / 0 FAIL / 0 NOT_PROVEN`
- NAC range: `NAC-014-001` through `NAC-014-033`

The corrected NAC count is 33; the obsolete pre-correction count of 32 is not
accepted.

## Stop-Condition Fidelity

Fourteen stop conditions were accepted. They preserve the bounded definition
against single-authority violation, legacy semantic rewrite, cross-subject
currentness leakage, factual-universe reduction, replacement/suppression,
unapproved calculations or timing rules, tax/NPV/optimization expansion,
numeric conflict, database immutability failure, client-isolation failure,
caller-forged authority, M10 implementation, and predecessor regression.

These stop conditions add no implementation authority.

## Business Build Plan Alignment

The Business Build Plan was narrowly aligned to:

- record PKG-013 as accepted and closed;
- distinguish exact family, version, and combined identifier terminology;
- record PKG-014 as definition-stage only;
- keep PKG-014 implementation unauthorized;
- keep M10 blocked pending accepted parallel outputs sharing exact factual
  baseline material state;
- keep M10-M14 implementation unauthorized;
- keep M08E excluded;
- keep `02M` frozen; and
- keep the next implementation package unauthorized.

## Governance

- Accepted definition HEAD remains
  `39fbc553e6bca7f10b9c1d237d3be1366be11477`.
- Implementation remains `NOT_AUTHORIZED`.
- Migration creation and execution remain `NOT_AUTHORIZED`.
- M10 implementation remains `NOT_AUTHORIZED`.
- The next package remains `NOT_AUTHORIZED`.
- No master merge is performed by this acceptance record.
- No production-readiness claim is made.

PKG_014_DEFINITION_ACCEPTED
