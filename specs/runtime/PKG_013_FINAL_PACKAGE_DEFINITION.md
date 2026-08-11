# PKG-013 Final Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-013` |
| Title | `M09 Deterministic Monthly Cashflow Orchestration Foundation` |
| Module | `M09` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Authoritative base | `81bf748fa358c7e664a8f31d60bdb04cd94838de` |
| Base tree | `fdc37766348161b84e858545522dff9770c167c8` |
| Current Alembic head | `f9a1c3e5b702` |

This document proposes one bounded M09 definition. It is not an accepted
definition, implementation authorization, migration authorization, production
readiness decision, or parity claim.

## 2. Authoritative Sources and Predecessor Contracts

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.
- Accepted M01-M06 definitions and implementation records on the authoritative
  base.
- Accepted bounded M07 resolver contracts, only where a consuming family
  explicitly requires them.
- Accepted M08 and M08F contracts, only where a consuming component explicitly
  requires them.
- PKG-012 closure on master at
  `81bf748fa358c7e664a8f31d60bdb04cd94838de`.

Earlier broad M09 blocker language is historical planning provenance. It is
superseded only for the exact first-stage family and contracts in this document.

## 3. Exact Product Outcome

PKG-013 defines an append-only, client-scoped, replayable foundation that
produces one immutable deterministic monthly cashflow scenario from explicitly
eligible authoritative monthly components.

The only scenario family is:

`deterministic_monthly_cashflow`

The result contains gross inflow, gross outflow, and their difference for every
full calendar month in an explicit inclusive horizon. It performs no tax,
optimization, projection economics, recommendation, or duplicated upstream
calculation. M09 is `ORCHESTRATOR_AND_AGGREGATOR_ONLY`; it is not a general
retirement scenario engine.

## 4. Normative Single-Authority Architecture

**Every material business calculation has exactly one authoritative owner.**

M09 must not copy, translate, approximate, or independently implement a formula
owned by another module. It may consume immutable authoritative upstream
outputs. If a value requires any additional business formula before monthly
aggregation, that formula must be supplied by an accepted upstream contract or
a separately authorized engine.

This is a normative acceptance rule. Tests must detect materially equivalent
formula implementations in M09 services, routes, models, schemas, UI helpers,
and background work. The V1 failure mode in which materially identical
calculations existed in multiple functions or services is explicitly forbidden.

## 5. Scenario Family and Version Contract

- Supported family: exactly `deterministic_monthly_cashflow`.
- Initial proposed family contract version:
  `deterministic_monthly_cashflow/v1`.
- Family identity and supported version are stable and server-owned.
- No alias, generic family, free-form mode, caller-defined family, or
  caller-overridden family/version is accepted.
- Adding a component type, formula, assumption, or dependency that changes
  meaning requires a new accepted family contract version.

## 6. Horizon Contract

Authoritative execution requires explicit `start_month` and `end_month` in
canonical `YYYY-MM` form.

- Both values are required and must identify valid calendar months.
- `end_month >= start_month`.
- Both endpoints are included.
- Periods are full calendar months in deterministic ascending order.
- There is no default or hidden horizon.
- There is no implicit 12-month, six-month, or age-90 period.
- M09 does not derive the horizon from `today`, M01 retirement date or age,
  employment end, pension start, or descriptive client facts.

## 7. Partial-Month and Frequency Boundary

M09 owns no generic partial-month or frequency-conversion formula. It must not
invent day-count, first-month, last-month, annual-to-monthly,
quarterly-to-monthly, daily normalization, interpolation, or allocation logic.

Only an upstream amount already authoritative for one full calendar month may
become a first-stage component. Recurring records whose frequency is not
`monthly`, or whose applicability would require partial-month treatment, block
their mandatory use rather than being converted or prorated.

## 8. Closed First-Stage Component Contract

The closed `component_type` vocabulary is exactly:

| Component type | Direction | Authority boundary |
|---|---|---|
| `recurring_income_record` | `inflow` | Eligible current V2 recurring-income record with `frequency=monthly` and `amount_basis=gross` |
| `recurring_expense_record` | `outflow` | Eligible current V2 recurring-expense record with `frequency=monthly` |
| `m06_monthly_pension_result` | `inflow` | Eligible current M06 `balance_to_monthly_pension` result only when an accepted upstream contract exposes a canonical Decimal `ILS/month` handoff |

No M05 balance, M06 capital-equivalent result, M07 fact, M08 result, free-text
label, or arbitrary amount is a monthly component by implication.

Each component contains at least:

- stable server-resolved `component_id`;
- `direction` exactly `inflow` or `outflow`;
- closed `component_type`;
- canonical Decimal `amount` and currency/unit evidence;
- applicable canonical `month`;
- authoritative source identity and source module/owner;
- source record/result and revision identity;
- source contract/version;
- source fingerprint/digest where the owner provides one; and
- captured currentness and eligibility evidence.

`component_id` must be a deterministic identity derived from the authoritative
source identity, component contract, and month. Duplicate `component_id` within
one run/month fails closed. Business descriptions never determine identity or
type.

## 9. Recurring Income and Expense Authority

CRUD existence, notes, `source_status`, or `verification_state` alone never
authorizes a component. Implementation requires a typed M09-specific
eligibility/currentness assessment for each recurring record.

An eligible recurring record requires:

- same client;
- a canonical nonnegative two-decimal ILS amount;
- exact record kind and direction;
- `frequency=monthly`;
- for income, `amount_basis=gross`;
- valid start/end dates and a deterministic full-month applicability result;
- lifecycle `current`, not superseded;
- not rejected, blocked, malformed, or unresolved;
- deterministic record identity;
- explicit M09 currentness/eligibility state;
- no unresolved authority ambiguity; and
- a source snapshot/digest sufficient to detect later material edits.

An applicable month is included only when the record contract establishes that
the whole month is applicable without prorating. A boundary date inside a month
requires an accepted upstream rule; otherwise the affected component is
ineligible for authoritative execution.

The family request must explicitly declare its required recurring component
set or an explicit authoritative `confirmed_none` state for each required
recurring domain. Missing mandatory recurring data is not zero. Ambiguous
duplicate economic meaning, including possible duplication between recurring
pension income and an M06 pension result, blocks execution until resolved by an
accepted authority contract; M09 does not choose or deduplicate professionally.

## 10. M05 Boundary

`eligible_for_m06` is not reusable as M09 authority. M09 requires the distinct
gate `eligible_for_m09_deterministic_monthly_cashflow` or an equivalently named
typed contract.

The gate requires same-client ownership, a unique current subject/candidate and
leaf, state `reconciled` or `warning_reviewed`, current predecessor authority,
complete monetary mapping/provenance, compatible ILS evidence, all mandatory
warnings disposed, no candidate tie, no corruption, no blocked/superseded
state, and fingerprint consistency.

M05 values are balances and reconciliation evidence, not monthly cashflow.
PKG-013 permits no direct M05 value as a monthly component. M05 may appear only
as captured dependency/snapshot evidence supporting an M06 component. M09 must
not divide, amortize, allocate, withdraw, or otherwise convert an M05 balance.

## 11. M06 Boundary

M09 may consider only a unique current M06 leaf that is `resolved` or
`warning_reviewed`, has `eligible_for_downstream=true`, current predecessors,
valid coefficient evidence and fingerprints, same-client ownership, and a
supported contract/version.

Only `balance_to_monthly_pension` can be a candidate source for
`m06_monthly_pension_result`. `monthly_pension_to_capital_equivalent` is not
monthly cashflow. M09 freezes the conversion subject/revision, formula/mode,
authoritative input, coefficient/provenance, exact raw output, display output,
eligibility evidence, and version/fingerprints.

Current M06 division authority may preserve an exact ratio while its display is
two-decimal. M09 must not convert that ratio into a Decimal or promote a display
value to authoritative monthly cashflow unless an accepted upstream M06
handoff explicitly defines the canonical Decimal `ILS/month` value. Until then,
that candidate fails closed. Missing, blocked, unsupported, or ineligible M06
is never zero and is never recomputed by M09.

## 12. M07 Boundary

M07 is not a mandatory dependency for
`deterministic_monthly_cashflow/v1`. The family does not inherit
`m08a_fixation/v1`, does not define a generic M09 tax manifest, and adds no tax
facts. When no accepted component requires M07, the dependency manifest omits
M07 entirely.

A later net-tax family would require separate M07 scope, manifest, and an
authoritative tax-calculation owner.

## 13. M08 and M08F Boundary

M08 is conditional, not universal. The closed first-stage component vocabulary
currently contains no direct M08-derived monthly component, so M08 is omitted
from a normal `deterministic_monthly_cashflow/v1` dependency manifest.

If a future accepted component version makes M08 material, it must require the
exact persisted M08 run/result and per-use M08F eligibility. Technical success,
latest existence, stale output, failed CBS/calculation, unsupported result, or
special-handling result is insufficient. There is no manual substitute or
fallback, and M09 never recomputes M08. Incomplete runtime M08F support blocks
that future component rather than expanding this package.

## 14. Calculation Ownership and Decimal Contract

M09 owns only:

```text
gross_inflow_total =
    sum(authorized monthly inflow components)

gross_outflow_total =
    sum(authorized monthly outflow components)

period_net =
    gross_inflow_total - gross_outflow_total
```

It also owns deterministic range totals produced by summing the stored monthly
rows. It owns no other business formula.

All authoritative monetary aggregation uses Decimal. Binary float input or
authority is rejected; there is no silent float conversion. Each component
enters already canonicalized by its owner, and M09 does not reround it.

For `deterministic_monthly_cashflow/v1`, every admitted component must be
canonical two-decimal ILS for a full month. Monthly and range totals therefore
use exact Decimal addition/subtraction and are persisted as canonical
two-decimal Decimal strings. This is an aggregation representation boundary,
not a new economic rounding formula. Display formatting is separate and cannot
change raw authority.

## 15. Explicit Non-Ownership

M09 does not own M05 balances/reconciliation, M06 conversion, coefficients,
M07 resolution, M08 fixation/exemption, grant offsets, CBS indexation, pension
exemption, tax, national insurance/health tax, inflation/indexation, returns,
discounting, NPV, withdrawal/commutation, severance taxation, minimum-pension
rules, projection growth, ranking, optimization, or recommendation.

## 16. Fail-Closed Completeness

For every dependency or component declared mandatory:

- missing is not zero;
- blocked is not zero;
- unsupported is not zero;
- unresolved is not zero;
- stale is not current;
- superseded is not current;
- ineligible is not accepted; and
- an invalid fingerprint is not accepted.

A missing mandatory dependency blocks authoritative success. No partial
authoritative scenario is emitted, and no component is silently omitted to
obtain success.

## 17. Typed Assumption Manifest

Every execution freezes an immutable typed manifest with `extra=forbid` and at
least:

- `manifest_schema_version`;
- `scenario_contract_version`;
- `scenario_family`;
- `client_id` and server-owned `scenario_run_id`;
- `start_month` and `end_month`;
- typed family-specific assumptions, limited in v1 to explicit required-domain
  declarations and selected authoritative component identities;
- immutable upstream snapshot reference;
- engine/version identities;
- fingerprint algorithm version; and
- manifest fingerprint.

All calculation-affecting fields are explicit and typed. PlannerAssumption
free text, planner/pension-analysis notes, title, rationale, work-intention
narrative, arbitrary JSON, caller unknown fields, and LLM text cannot affect
calculation. Non-calculating display metadata is segregated and excluded from
the semantic fingerprint.

## 18. Immutable Upstream Snapshot

Execution freezes applicable client identity, family/version, horizon,
component IDs and exact values, source identities/versions, M05 evidence used
through M06, M06 result and eligibility evidence, M07 only if a future accepted
component requires it, M08/M08F only if required, recurring authority and
currentness, engine/contract versions, fingerprints/digests, and warning
dispositions.

Later upstream edits never mutate a historical run. They may make its read-time
currentness false.

## 19. Persistence and Lifecycle

Implementation is expected to require additive persistence above
`f9a1c3e5b702`, but no migration is authorized by this definition.

The persistence design must distinguish immutable scenario identity/subject if
needed, immutable run, immutable assumption manifest, immutable upstream
snapshot, immutable result, blocker/failure evidence, successor/supersession,
deterministic current leaf, and read-time currentness.

Historical input/result evidence is append-only and never updated or deleted.
Scenario execution cannot mutate M05, M06, M08, or source records.

## 20. Closed Run Status Contract

Persisted execution status is exactly:

- `success_complete`;
- `validation_failed`;
- `dependency_failed`;
- `calculation_failed`; and
- `unsupported`.

Execution status is separate from currentness and M10 eligibility.
`success_complete` means only that this bounded execution completed; it does
not mean current, authoritative for professional use, or M10-eligible.

## 21. Result Contract

A persisted result contains at least run/client/family/version identities,
manifest and snapshot identities/fingerprints, server calculation timestamp,
result schema and engine versions, ordered monthly rows, per-month component
evidence, monthly gross totals and `period_net`, deterministic range totals,
warnings, blockers/reason codes, status, result fingerprint, currentness
evidence, M10 eligibility assessment, and predecessor/supersession identity.

It contains no comparison score, preferred scenario, rank, recommendation,
NPV, tax result, or optimization result.

## 22. Determinism and Fingerprints

- Months are ordered ascending.
- Component directions/types use stable contract order.
- Within type, source identity/order is stable.
- Duplicate component identities are rejected.
- Canonical serialization produces stable fingerprints.
- Repeated execution with identical authoritative inputs and assumptions
  produces identical authoritative values and semantic result fingerprint.
- Server run ID, timestamp, and other intentionally non-deterministic metadata
  are retained but excluded from the semantic result fingerprint.

## 23. Read-Time Currentness

`latest` alone is insufficient. A run is current only when it is the
non-superseded current scenario leaf, captured dependencies remain current,
captured fingerprints match, required upstream eligibility remains valid,
family/contract versions remain supported, and result integrity is valid.

Historical and stale runs remain readable. A stale run is historical evidence,
not current scenario authority.

## 24. Derived M10 Eligibility

M10 eligibility is a fail-closed derived assessment containing at least:

- `eligible_for_m10`;
- `assessed_scenario_run_id`;
- `current_scenario_run_id`;
- stable `reason_codes` and `informational_warnings`;
- server `assessment_timestamp`; and
- `eligibility_contract_version`.

Eligibility is true only for a persisted complete success that is current and
non-superseded, uses supported versions, has valid manifest/snapshot/result
fingerprints, had all mandatory dependencies eligible at execution, still has
all required dependencies eligible/current, has no blocker or partial output,
has completed mandatory warning disposition, and has valid result integrity.

Execution success alone is insufficient. M10 may consume persisted M09 results
only and may not execute or recalculate M09. This definition does not authorize
M10 implementation.

## 25. Warning Semantics

Warnings are typed as exactly one of:

- `blocking_condition`;
- `mandatory_review_warning`; or
- `informational_warning`.

A warning can coexist with M10 eligibility only when the family contract marks
it informational or its exact mandatory review is completed. There is no
generic "warning accepted" bypass.

## 26. Client Isolation and Caller-Forgery Boundary

- Every route/service query uses `client_id + resource_id` ownership.
- Missing and foreign identities have the same public failure behavior.
- No global existence lookup leaks foreign resources.
- Cross-client upstream identities are rejected before execution/persistence.
- Direct services enforce the same ownership as routes.
- Snapshots cannot reference another client's records.
- Caller input cannot author trusted ownership, component amount/identity,
  upstream eligibility/currentness, actor, timestamp, fingerprint, result,
  run identity, or M10 eligibility.

## 27. Frontend Boundary and Async Isolation

The bounded first-stage implementation is expected to include a client-scoped
UI for explicit horizon/component selection, execution, history, result detail,
currentness, blockers/warnings, and M10 eligibility explanation. It includes no
comparison, recommendation, projection chart, or client report.

All asynchronous work requires client ID plus monotonic route-context
generation and per-request ownership. Deterministic tests cover A-to-B and
A-to-B-to-A, stale success, structured error, rejection, stale `finally`, and a
pending-new-owner request. Stale work cannot alter assumptions, selection,
validation, loading/submission, error, result, saved-run link, history, or M10
eligibility.

## 28. Stop Conditions

Stop implementation planning or implementation if any of these applies:

- `M09_SINGLE_AUTHORITY_CONTRACT_VIOLATION`
- `M09_COMPONENT_VOCABULARY_EXPANSION_REQUIRED`
- `M09_RECURRING_AUTHORITY_UNRESOLVED`
- `M09_M05_MONTHLY_VALUE_FORMULA_REQUIRED`
- `M09_M06_CANONICAL_MONTHLY_HANDOFF_BLOCKED`
- `M09_M07_SCOPE_REQUIRED`
- `M09_M08F_INTERFACE_BLOCKED`
- `M09_PARTIAL_MONTH_FORMULA_REQUIRED`
- `M09_MONETARY_PRECISION_CONFLICT`
- `M09_FAIL_CLOSED_COMPLETENESS_BLOCKED`
- `M09_IMMUTABILITY_OR_CURRENTNESS_BLOCKED`
- `M09_CLIENT_ISOLATION_BLOCKED`
- `M09_CALLER_FORGED_AUTHORITY_BLOCKED`
- `M10_IMPLEMENTATION_REQUIRED`
- `PRIOR_PACKAGE_REGRESSION_BLOCKED`

## 29. Acceptance Criteria

- **AC-013-001:** Branch/base verification proves exact base `81bf748fa358c7e664a8f31d60bdb04cd94838de` and no unrelated change.
- **AC-013-002:** Family is exactly `deterministic_monthly_cashflow` with server-owned supported contract version.
- **AC-013-003:** Every material business formula has one authoritative owner and M09 contains no duplicate upstream formula.
- **AC-013-004:** M09 owns only monthly inflow sum, outflow sum, net subtraction, and deterministic range sums.
- **AC-013-005:** Component type/direction vocabulary is closed and rejects unknown or caller-defined values.
- **AC-013-006:** Every component carries deterministic identity, exact Decimal amount, month, owner, source, version, and currentness/eligibility evidence.
- **AC-013-007:** Duplicate component identity within a run/month fails closed.
- **AC-013-008:** Eligible recurring income requires same client, monthly frequency, gross amount basis, full-month applicability, currentness, and explicit M09 eligibility.
- **AC-013-009:** Eligible recurring expense requires same client, monthly frequency, full-month applicability, currentness, and explicit M09 eligibility.
- **AC-013-010:** Missing required recurring-domain evidence is distinguished from authoritative `confirmed_none` and never becomes zero by omission.
- **AC-013-011:** Explicit canonical `start_month` and `end_month` are required, ordered, inclusive, and generate full months ascending.
- **AC-013-012:** No partial-month or non-monthly frequency conversion occurs in M09.
- **AC-013-013:** Monetary authority is Decimal-only; every v1 component and persisted total is canonical two-decimal ILS without binary float conversion.
- **AC-013-014:** Components are not rerounded; monthly/range totals use exact Decimal addition and subtraction.
- **AC-013-015:** Every mandatory missing, blocked, unsupported, unresolved, stale, superseded, ineligible, or fingerprint-invalid dependency blocks complete authoritative success.
- **AC-013-016:** No partial authoritative scenario is persisted as a successful complete result.
- **AC-013-017:** M05 uses an M09-specific gate and `eligible_for_m06` is not treated as generic M09 authority.
- **AC-013-018:** M05 balances are snapshot/dependency evidence only and never manufactured into monthly cashflow.
- **AC-013-019:** M06 consumption requires one current eligible same-client supported leaf with complete provenance/fingerprints.
- **AC-013-020:** Only an accepted canonical Decimal `ILS/month` handoff for `balance_to_monthly_pension` can create an M06 monthly component; exact-ratio conversion is never rounded by M09.
- **AC-013-021:** M06 capital-equivalent, missing, blocked, unsupported, or ineligible output cannot become a monthly component or zero.
- **AC-013-022:** M07 is omitted for v1 and no `m08a_fixation/v1` or generic tax manifest is inherited.
- **AC-013-023:** M08 is omitted when not material; any future required use is explicit and requires persisted result plus exact per-use M08F eligibility.
- **AC-013-024:** Typed assumption manifest uses `extra=forbid`, explicit calculation inputs, versions, and stable fingerprint.
- **AC-013-025:** Free text, notes, title, rationale, arbitrary JSON, unknown fields, and LLM content cannot affect calculation.
- **AC-013-026:** Immutable upstream snapshot freezes all consumed values, authority, versions, eligibility/currentness, warnings, and fingerprints.
- **AC-013-027:** Later source changes do not mutate historical runs and can make read-time currentness false.
- **AC-013-028:** Persistence is additive and append-only with immutable input/result/failure evidence and deterministic successor/current leaf.
- **AC-013-029:** Closed run statuses remain separate from currentness and M10 eligibility.
- **AC-013-030:** Result contains ordered rows, component evidence, totals, manifests, fingerprints, status, currentness, and M10 assessment without excluded outputs.
- **AC-013-031:** Canonical ordering and serialization yield identical semantic values/fingerprint for identical authority, excluding run ID/timestamp.
- **AC-013-032:** Read-time currentness validates current leaf, dependency eligibility/currentness, fingerprints, supported versions, and result integrity.
- **AC-013-033:** M10 eligibility is derived fail-closed and complete success alone is insufficient.
- **AC-013-034:** M10 consumes persisted M09 results only and never executes/recalculates M09.
- **AC-013-035:** Blocking, mandatory-review, and informational warnings have distinct stable semantics with no generic bypass.
- **AC-013-036:** Routes and direct services enforce same-client ownership and foreign/missing non-leakage before persistence.
- **AC-013-037:** Caller cannot forge ownership, component authority, actor, timestamp, fingerprint, result, currentness, or eligibility.
- **AC-013-038:** Frontend deterministic tests prove A-to-B/A-to-B-to-A success/error/rejection/finally and pending-new-owner isolation for every included async operation.
- **AC-013-039:** Migration is additive above `f9a1c3e5b702`, preserves existing records, has one head, and introduces no professional backfill.
- **AC-013-040:** Focused/backend/frontend/migration tests, build, compile, deterministic replay, client isolation, formula-owner scan, and `git diff --check` supply acceptance evidence.

## 30. Negative Acceptance Criteria

- **NAC-013-001:** Duplicated M05, M06, M07, M08, tax, fixation, indexation, coefficient, or other upstream formula in M09.
- **NAC-013-002:** Binary float as monetary authority or silent float-to-Decimal conversion.
- **NAC-013-003:** Hidden/default horizon, including today, retirement date, employment end, pension start, six months, 12 months, or age 90.
- **NAC-013-004:** Caller-defined family, alias, free-form mode, or caller-overridden family/version.
- **NAC-013-005:** Free text, notes, rationale, title, arbitrary JSON, unknown field, or LLM output affecting calculation.
- **NAC-013-006:** Missing, blocked, unsupported, unresolved, stale, superseded, ineligible, or corrupt authority treated as zero/current/accepted.
- **NAC-013-007:** Silent omission producing a partial authoritative successful scenario.
- **NAC-013-008:** Reuse of `eligible_for_m06` as generic M09 authority.
- **NAC-013-009:** M05 balance converted, allocated, amortized, or otherwise manufactured into monthly cashflow by M09.
- **NAC-013-010:** M06 formula, coefficient logic, rounding, or exact-ratio conversion duplicated in M09.
- **NAC-013-011:** Inheritance of `m08a_fixation/v1` or creation of generic M09 tax facts/manifest.
- **NAC-013-012:** Unconditional or artificial M08 dependency.
- **NAC-013-013:** M08 technical success/latest existence treated as per-use M08F eligibility.
- **NAC-013-014:** `success_complete` treated as current, professionally authoritative, or automatically M10-eligible.
- **NAC-013-015:** Update-in-place or deletion of historical run, manifest, snapshot, result, warning, or failure evidence.
- **NAC-013-016:** Cross-client association, snapshot reference, lookup, or foreign-ID existence leakage.
- **NAC-013-017:** Caller-forged amount, component/source identity, actor, timestamp, status, fingerprint, currentness, result, or eligibility.
- **NAC-013-018:** Partial-month, annual, quarterly, daily, interpolation, inflation, return, or discounting formula in M09.
- **NAC-013-019:** `PENSION_COEFFICIENT = 200` or any implicit coefficient/default/fallback.
- **NAC-013-020:** `MINIMUM_PENSION = 5500` or any minimum-pension rule.
- **NAC-013-021:** `DEFAULT_DISCOUNT_RATE = 0.03`, NPV, or discounting.
- **NAC-013-022:** `MAX_AGE_FOR_NPV = 90` or age-derived horizon.
- **NAC-013-023:** Hidden six-month projection or implicit 12+ month horizon.
- **NAC-013-024:** Scenario-side fixation, grant-offset, CBS, pension-exemption, or tax calculation.
- **NAC-013-025:** Mutation/restore of client portfolio, fixation, M05, M06, M08, or source state.
- **NAC-013-026:** Comparison score, ranking, preferred scenario, optimization, recommendation, or report scope.
- **NAC-013-027:** Net-tax cashflow, national-insurance/health-tax, prospective withdrawal, or commutation.
- **NAC-013-028:** Maximum-pension, maximum-capital, balanced, generic, Monte Carlo, or caller-defined scenario family.
- **NAC-013-029:** Automatic professional defaults, investment advice, LLM assumptions, or LLM calculations.
- **NAC-013-030:** M10-M14 implementation, formal 161D/M08E, or change to frozen `02M`.
- **NAC-013-031:** Production-readiness, professional-sufficiency, or V1/V2 parity claim.
- **NAC-013-032:** Definition proposal treated as acceptance or implementation/migration authorization.

## 31. Verification Matrix

| Area | Required evidence |
|---|---|
| Authority ownership | Production/static call graph and tests prove no duplicated upstream formula |
| Family/horizon | Schema/API tests reject aliases, unknown versions, malformed/reversed/missing months, and hidden defaults |
| Components | Closed vocabulary, deterministic identity, duplicate rejection, recurring/M06 eligibility and ambiguity tests |
| Arithmetic | Decimal-only tests, no float acceptance, exact monthly/range sums, canonical serialization and replay fingerprints |
| Dependencies | M05 gate, M06 canonical handoff, M07 omission, conditional M08/M08F, and all fail-closed states |
| Persistence | Additive migration, one Alembic head, immutable history, concurrency, rollback, and no upstream mutation |
| Currentness/M10 | Corruption/staleness/supersession/version tests and success-not-eligibility evidence |
| Isolation | API and direct-service same-client/non-leakage tests |
| Frontend | A-to-B/A-to-B-to-A matrices including pending-new-owner ownership |
| Regression | Accepted M01-M08 suites, compile, build, and `git diff --check` |

## 32. Explicit Deferred and Excluded Scope

Excluded are maximum-pension, maximum-capital, balanced and generic strategies;
NPV; net-tax cashflow; all tax; minimum pension and V1 `5500`; V1 coefficient
`200`; V1 `3%`; age-90 and hidden projection horizons; returns; inflation;
discounting; withdrawal; commutation; automatic portfolio mutation;
optimization; ranking; recommendation; M10 comparison implementation; M11;
M12; system-wide M13 expansion; M14/production readiness; formal 161D/M08E;
Monte Carlo; investment advice; LLM assumptions/calculations; automatic
professional defaults; and V1/V2 parity.

Deferred scenario families remain unresolved future scope and are not made
ready by this definition.

## 33. Expected Implementation Shape

If separately authorized, implementation will likely require additive scenario
persistence, typed schemas and canonical fingerprints, backend models/services/
routes, M09-specific eligibility/currentness services, bounded frontend
execution/history/detail UI, and mandatory focused/full tests. This expected
shape authorizes none of those changes now.

## 34. Authorization Boundary

- Definition: proposed only.
- Definition acceptance: not yet granted.
- Implementation and migration creation/execution: `NOT_AUTHORIZED`.
- No module is `READY_FOR_IMPLEMENTATION`.
- M10-M14 remain `BLOCKED_FOR_LOGIC_DETAIL`.
- M08E remains excluded.
- `02M` remains frozen.
- The next package remains `NOT_AUTHORIZED`.

PKG_013_DEFINITION_PROPOSED_FOR_ACCEPTANCE
