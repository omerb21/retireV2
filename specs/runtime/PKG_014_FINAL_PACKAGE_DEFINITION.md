# PKG-014 Final Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-014` |
| Title | `M09 Declared Retirement Cashflow Adjustments and Parallel Scenario Subjects Foundation` |
| Module | `M09` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Authoritative base | `f1cbddbf27d7712ce2409248240a0cb4cadebc8d` |
| Accepted PKG-013 implementation HEAD | `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea` |
| Current Alembic head | `c4e8a1f6d203` |
| Scenario family | `declared_retirement_cashflow_adjustments` |
| Scenario contract version | `v1` |
| Combined contract identifier | `declared_retirement_cashflow_adjustments/v1` |
| M09 role | `ORCHESTRATOR_AND_AGGREGATOR_ONLY` |

This document is a definition proposal for acceptance audit. It is not an
accepted definition, implementation authorization, migration authorization,
production-readiness decision, professional sufficiency decision, or V1/V2
parity claim.

## 2. Authoritative Sources and Predecessor Contracts

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.
- Accepted PKG-013 definition and implementation contracts.
- Accepted implementation boundary
  `50cdf8322d0a24215f5f9e1c488e5acb3736c1ea`.
- PKG-013 implementation acceptance evidence merged on master at
  `f1cbddbf27d7712ce2409248240a0cb4cadebc8d`.
- Existing M01-M08 accepted contracts only as immutable upstream authority
  boundaries; this package does not reinterpret them.

The accepted family `deterministic_monthly_cashflow/v1` remains historically
and semantically unchanged. This proposal defines a separate family and does
not retrofit, migrate, alias, or reinterpret existing runs.

## 3. Exact Product Outcome and Professional Meaning

PKG-014 proposes an immutable, client-scoped foundation for independently
current M09 scenario subjects. Each adjusted subject binds the same complete
server-resolved factual cashflow baseline to explicit planner-declared
additional monthly income or expense assumptions over explicit full-month
ranges.

The exact professional meaning is:

**an objective planner-declared retirement cashflow sensitivity/planning
alternative**

It is not a forecast, recommendation, preference, optimizer, automatically
inferred retirement plan, or automatic consequence of a retirement date.
Examples may include higher or lower retirement living-cost assumptions, an
explicit temporary retirement expense, or explicit additional retirement-
period income. Examples are explanatory only; no amount is a default.

## 4. Normative Single-Authority Architecture

**Every material business calculation has exactly one authoritative owning
module/engine.**

PKG-014 must not weaken this law. For the new family M09 may own only:

- typed scenario-subject orchestration;
- explicit planner-declared adjustment evidence;
- explicit full-month applicability and alignment;
- addition of admitted adjustment income to inflows;
- addition of admitted adjustment expenses to outflows;
- the existing M09 aggregation operations;
- immutable persistence and evidence mechanics;
- per-subject currentness; and
- subject-aware M10 technical eligibility evidence.

M09 must not own retirement-income cessation, pension-start, M05, M06, M07,
M08, tax, fixation, CBS, grant, indexation, investment-return, discounting,
NPV, withdrawal, commutation, allocation, conservation, minimum-pension,
optimization, ranking, or recommendation formulas. M06 remains the sole
pension-conversion formula owner.

## 5. Family and Version Boundary

- `scenario_family` is exactly `declared_retirement_cashflow_adjustments`.
- `scenario_contract_version` is exactly `v1`.
- The combined human-readable contract identifier is exactly
  `declared_retirement_cashflow_adjustments/v1`.
- Existing combined contract identifier:
  `deterministic_monthly_cashflow/v1`, unchanged.
- The separate family and contract-version fields are server-owned closed
  values. There is no second or ambiguous version field.
- No alias, free-form family, caller-selected implementation version, or
  implicit fallback is permitted.
- Unsupported families and versions fail closed.
- A future semantic change requires a separately accepted contract version.

## 6. Immutable Scenario Subject Contract

A `scenario_subject` is immutable and server-owned. Its conceptual fields are:

- `scenario_subject_id`;
- `client_id`;
- `scenario_family`;
- `scenario_contract_version`;
- scenario-assumption manifest identity;
- calculation-semantic fingerprint;
- evidence/integrity fingerprint;
- optional display label;
- actor/provenance evidence; and
- server-owned creation timestamp.

The display label is non-authoritative. Subject IDs, adjustment IDs, display
labels, actor identities, timestamps, run IDs, and sequence values must not
make otherwise equal subjects calculation-semantically different.

No subject is updated or deleted in place. Changed calculation semantics
require a new immutable subject or a separately accepted successor-evidence
contract.

## 7. Calculation-Semantic Identity

The subject calculation-semantic fingerprint depends only on calculation-
affecting scenario semantics. For adjusted subjects it includes a canonical
ordered adjustment multiset containing, for every occurrence:

- adjustment type;
- canonical amount;
- start month;
- end month; and
- multiplicity.

Its canonical semantic envelope also binds the exact
`scenario_family = declared_retirement_cashflow_adjustments` and
`scenario_contract_version = v1`; those calculation-affecting contract tokens
are distinct fields, not a combined value stored in `scenario_family`.

Canonical ordering is lexicographic by type, canonical amount text,
`start_month`, then `end_month`; equal tuples are retained repeatedly so their
multiplicity remains calculation-affecting. The semantic fingerprint excludes
subject ID, adjustment ID, display label, planner actor, timestamps, run ID,
and sequence.

The evidence/integrity fingerprint separately binds server-owned identities,
provenance, timestamps, the semantic fingerprint, and the immutable evidence
envelope. It must not be substituted for semantic equality.

## 8. Semantic Duplicate Rejection

Within the same `client_id + scenario_family + scenario_contract_version`,
creation fails closed when an existing subject has the same calculation-
semantic fingerprint. The stable reason code is:

`scenario_subject_semantically_duplicate`

A different label, actor, timestamp, or generated identity does not make a
semantic duplicate distinct. First-stage behavior is rejection; there is no
automatic reuse, merge, or supersession of the existing subject.

## 9. Subject Types and Server-Owned Baseline

### 9.1 Baseline Subject

Exactly one baseline subject exists per
`client_id + scenario_family + scenario_contract_version`, where the latter
two fields have the exact values frozen in Section 5. It has:

- server-generated identity;
- the canonical empty adjustment manifest;
- the same complete factual baseline contract used by adjusted subjects;
- server-generated no-adjustment evidence;
- database-enforced uniqueness expectation; and
- no caller-authored empty-evidence authority.

The stable marker is:

`server_resolved_no_scenario_adjustments`

The server owns baseline creation and resolution. Caller input such as
`adjustments=[]` cannot authoritatively declare a baseline or an empty domain.

### 9.2 Adjusted Subject

An adjusted subject contains at least one valid positive adjustment. An empty
adjusted subject is invalid. Its adjustment manifest is immutable after
creation.

## 10. Closed Adjustment Vocabulary

The adjustment type vocabulary is exactly:

- `declared_additional_monthly_income`;
- `declared_additional_monthly_expense`.

Direction is implied by the type. There is no arbitrary type, generic
direction, caller-defined component category, or negative-sign direction.

## 11. Adjustment Evidence Contract

Each adjustment includes conceptually:

- server-generated adjustment ID;
- scenario subject ID;
- exact closed adjustment type;
- canonical Decimal ILS monthly amount;
- explicit `start_month`;
- explicit `end_month`;
- planner-declared provenance;
- planner actor evidence;
- server-owned creation timestamp;
- canonical semantic representation; and
- participation in semantic and evidence fingerprints.

The stable provenance marker is:

`planner_declared_scenario_adjustment`

This marker is informational provenance by default. It is not authentication,
professional approval, recommendation, or automatic acceptance of an
otherwise invalid adjustment.

## 12. Amount Contract

- Decimal is the only monetary authority.
- Currency is fixed to ILS.
- Canonical scale is exactly two decimal places.
- Minimum is `0.01`.
- Maximum is `999999999999999999.99`.
- Zero and negative values are prohibited.
- Scientific notation is not canonical.
- More than two decimal places is rejected.
- There is no silent rounding, clipping, coercion, or float authority.
- Direction comes from the closed type, not the sign.

Component and aggregate persistence remains bounded by accepted
`Numeric(20,2)` semantics. Representability is validated before persistence,
and overflow produces typed fail-closed lifecycle evidence rather than an
uncaught database exception.

## 13. Range and Applicability Contract

Every adjustment requires strict canonical `YYYY-MM` `start_month` and
`end_month`, with `start_month <= end_month`. Endpoints are inclusive and
represent full calendar months only.

The adjustment range must be wholly contained within the explicit execution
horizon. An adjustment may cover only part of that horizon. Outside the
explicit range it is `contractually_not_applicable`; this is not missing data
converted to zero.

There is no proration, implicit extension, inferred continuation, day-level
calculation, or date-derived adjustment range.

## 14. Additive-Only Semantics

The adjustment contract is exactly `ADDITIVE_ONLY`. A valid adjustment adds a
scenario-specific hypothetical component to the complete factual baseline.
It may never:

- replace factual recurring income or expense;
- suppress or waive a factual component;
- edit a source record;
- edit M05 or M06 output;
- reduce the mandatory factual universe; or
- turn a missing factual dependency into a scenario assumption.

No replacement contract exists in v1.

## 15. Multiplicity and Double-Counting Boundary

Adjustments are explicitly additional hypothetical cashflows and are not
automatically deduplicated against factual records. Equal amount, text,
provider, or timing similarity creates no automatic suppression.

Within the adjustment manifest:

- duplicate adjustment identity fails closed;
- separately declared adjustments with equal semantic fields are each
  calculation-affecting through multiplicity;
- multiplicity is retained in the semantic fingerprint; and
- UI and evidence must expose multiplicity clearly.

This contract does not invent professional economic deduplication.

## 16. Factual Baseline Authority and Domain Separation

The factual component universe remains complete and server-owned. Caller and
UI cannot select an authoritative subset, remove a factual component, waive
completeness, declare the factual domain empty, forge `server_resolved_none`,
or forge factual eligibility, currentness, source identity, or fingerprint.

Two authority domains remain distinct:

1. **Factual resolved inventory** — complete, immutable, and server-owned.
2. **Scenario adjustment manifest** — subject-owned, immutable, and explicitly
   planner-declared.

Execution evidence binds both domains, but display or persistence must not make
them indistinguishable. Baseline empty-adjustment evidence has no effect on the
existing server-owned factual-domain completeness contract.

## 17. Scenario Execution Arithmetic

For the new family M09 calculation authority remains limited to:

- consume stored authoritative factual components;
- consume explicit admitted declared adjustments;
- align components over applicable full months;
- add adjustment income to inflows;
- add adjustment expense to outflows;
- sum inflows and outflows;
- compute `period_net = inflows - outflows`; and
- compute deterministic range sums.

There is no adjustment-specific business formula. An in-range adjustment
contributes its stored canonical amount; outside its range it is contractually
not applicable.

## 18. Parallel Per-Subject Currentness

For combined contract identifier
`declared_retirement_cashflow_adjustments/v1`, the currentness key is:

`client_id + scenario_subject_id + scenario_family + scenario_contract_version`

Here `scenario_family` is exactly `declared_retirement_cashflow_adjustments`
and `scenario_contract_version` is exactly `v1`.

The subject-aware contract version is:

`m09-subject-currentness-v1`

- There is one current leaf per subject.
- Multiple subjects may be current simultaneously.
- Rerun of subject A supersedes only the prior A leaf.
- Subject B does not stale A merely by existing or running.
- A factual upstream change may stale every affected subject.
- The assumption manifest is immutable.
- Currentness is evaluated read-time and fails closed on integrity conflict.

This package must not reinterpret `m09-currentness-v1` or alter the global
currentness behavior of `deterministic_monthly_cashflow/v1`.

## 19. Existing V1 Family Compatibility

`deterministic_monthly_cashflow/v1` is preserved exactly. There is no retrofit
into default subjects and no migration may rewrite historical run identities,
fingerprints, currentness, eligibility, predecessor semantics, or semantic
result meaning.

Legacy v1 runs remain readable under their accepted contract. They do not
automatically become parallel-comparison inputs and are not reclassified under
subject-aware currentness or eligibility v2.

## 20. Subject-Aware M09-to-M10 Eligibility

The new family uses exactly:

`m09-to-m10-eligibility-v2`

It must not reinterpret `m09-to-m10-eligibility-v1`. Eligibility v2 is a
**per-run** derived fail-closed evidence contract, never a caller-authored
boolean. It preserves all
existing integrity, dependency, currentness, warning, and successful-complete
conditions and additionally proves:

- same-client subject ownership;
- valid subject identity;
- exact `scenario_family = declared_retirement_cashflow_adjustments` and
  `scenario_contract_version = v1`;
- valid assumption integrity fingerprint;
- valid calculation-semantic fingerprint;
- current leaf within that subject;
- valid closed adjustment vocabulary;
- positive canonical Decimal amounts within bounds;
- valid ranges wholly contained in the run horizon;
- complete factual baseline;
- no caller reduction of the factual universe;
- no unsupported adjustment;
- no semantically duplicate subject;
- result, dependency, inventory, and upstream-snapshot integrity;
- no blockers; and
- required mandatory-warning disposition.

Every eligible run exposes and persists its canonical
`factual_baseline_material_fingerprint`. Per-run eligibility proves the
individual factual baseline is valid; it does not and cannot prove equality to
an unknown future peer. Pair-level equality belongs exclusively to future M10
admission.

Eligibility means only that a separately authorized M10 may consume the
persisted M09 subject result. It is not professional authority, ranking,
recommendation, production readiness, or permission to execute M10.

## 21. M10 Boundary

PKG-014 does not implement M10. It creates upstream capability so a future,
separately authorized M10 may compare two independently current and eligible
subject runs.

Intended first-stage future admission remains:

- same client;
- two distinct scenario subjects;
- exact same `scenario_family`, equal to
  `declared_retirement_cashflow_adjustments`;
- exact same `scenario_contract_version`, equal to `v1`;
- same exact run horizon;
- current within each subject;
- eligible under `m09-to-m10-eligibility-v2`;
- valid subject, result, inventory, dependency, and upstream fingerprints;
- semantically distinct adjustment manifests;
- exact same persisted `factual_baseline_material_fingerprint`;
- exact same `component_domain_contract_version`;
- exact same M09 engine and result-schema versions; and
- exact same calculation-affecting factual upstream contract/engine versions
  bound by the factual-baseline material identity.

The preferred first pair is baseline subject versus one adjusted subject, but
only when both carry the exact same factual-baseline material fingerprint. A
factual source change between executions makes the old pair non-comparable;
upstream rerun or reassessment is required. M10 must not normalize, reconcile,
or rebuild factual differences.

Individual factual integrity and cross-subject factual equality are separate
requirements. Two individually current and eligible runs with different
factual baseline material are not comparable. `eligible_for_m10=true` or its
equivalent per-run evidence never substitutes for pair-level equality. A
mismatch fails closed with the stable blocking reason:

`comparison_factual_baseline_material_mismatch`

Future M10 remains `COMPARATOR_ONLY`: persisted side-by-side values, exact
`A - B`, equality, and numeric greater/lower only. No percentage, ranking,
score, recommendation, annualization, or NPV is authorized.

## 22. Fingerprint Contract

The following identities are distinct and independently verifiable:

- subject calculation-semantic fingerprint;
- subject evidence/integrity fingerprint;
- adjustment manifest fingerprint;
- factual inventory fingerprint;
- factual baseline material fingerprint;
- upstream snapshot fingerprint;
- run semantic result fingerprint; and
- result integrity fingerprint.

Canonical object keys and collection ordering must be explicit and stable.
Adjustments are ordered by their semantic tuple while retaining repeated equal
tuples. Factual components retain accepted server-owned canonical ordering.

Repeated execution with the same subject, factual baseline, horizon, and
supported versions must produce the same semantic result fingerprint. Run ID,
timestamp, sequence, actor, and other evidence-only fields are excluded from
semantic equality but may be bound by integrity fingerprints.

The stable persisted field is
`factual_baseline_material_fingerprint`. It is a deterministic canonical
fingerprint over the calculation-affecting factual baseline material used by a
run, excluding all scenario adjustments. Directly or through canonical
constituent fingerprints it binds at least:

- factual resolved-inventory identity and content;
- factual component identities and exact amounts;
- factual applicability/month evidence relevant to the run;
- factual source identities and versions;
- factual eligibility and currentness evidence required by contract;
- `component_domain_contract_version`;
- relevant calculation-affecting factual upstream contract/engine versions;
  and
- factual inventory fingerprint or its canonical material.

It excludes scenario-subject ID, adjustment manifest, adjustment IDs,
adjustment values, subject label, run ID, timestamp, actor when merely
metadata, and other non-calculation display metadata. Every new-family run
snapshot and result evidence persists this exact fingerprint. Future M10 may
validate equality of the two persisted values but must not recompute or rebuild
the factual baseline from raw components.

## 23. Persistence and Migration Expectations

Implementation will likely require additive persistence, but this definition
does not authorize schema creation or migration execution. The future design
must conceptually preserve:

- immutable scenario subjects;
- immutable adjustment manifests;
- immutable normalized adjustment records if used;
- an append-only run chain per subject;
- historical run and dependency evidence;
- baseline uniqueness;
- semantic-subject uniqueness;
- explicit client ownership; and
- database-level immutability consistent with PKG-013.

No existing PKG-013 row or accepted migration is rewritten or destructively
reused.

## 24. Required Database Invariants

Future implementation must enforce at database level, where raw-SQL bypass
would otherwise violate evidence integrity:

- client-bound subject identity;
- one baseline per
  `client_id + scenario_family + scenario_contract_version`;
- semantic subject uniqueness per
  `client_id + scenario_family + scenario_contract_version`;
- immutable historical subject, adjustment, manifest, run, and result evidence;
- append-only semantics;
- predecessor and sequence uniqueness within each subject;
- consistent same-client foreign-key relationships; and
- rejection of UPDATE/DELETE wherever evidence must remain immutable.

Final table, constraint, index, trigger, and DDL choices remain implementation
design and are not authorized here.

## 25. Run Lifecycle and Warning Semantics

The accepted PKG-013 closed run statuses and separation among status,
currentness, and M10 eligibility remain unchanged. No partial authoritative
scenario is permitted.

Accepted warning categories remain blocking, mandatory review, and
informational. `planner_declared_scenario_adjustment` is informational
provenance by default. There is no generic warning-acceptance bypass.

## 26. Client Isolation and Caller-Forgery Boundary

- Subject lookup is scoped by `client_id + scenario_subject_id`.
- Foreign and nonexistent resources produce equivalent public behavior.
- Cross-client subject, adjustment, run, or result use fails closed.
- Direct service invocation enforces ownership.
- Body-level client override is prohibited.
- Caller cannot author trusted server-owned IDs, baseline evidence,
  currentness, factual inventory, eligibility, fingerprints, timestamps, run
  identity, source evidence, or result.

Future calculation-affecting request schemas use `extra=forbid` or an
equivalent fail-closed contract.

## 27. API Authority Boundary

Future requests may carry only explicitly allowed planner inputs, such as an
optional display label, closed adjustment values and ranges, and explicit run
horizon. The server owns client binding, generated identities, baseline
resolution, factual inventory, currentness, eligibility, fingerprints,
server-owned actor/timestamp semantics, run identity, and result.

API admission binds `scenario_family` to
`declared_retirement_cashflow_adjustments` and
`scenario_contract_version` to `v1`; the combined identifier is display and
contract-reference terminology, not a caller-authored family value.

The browser cannot create a baseline by sending an empty list and cannot
provide an authoritative factual subset.

## 28. Frontend Product Boundary

A future bounded UI may:

- request or view the unique baseline subject;
- create and view adjusted subjects;
- enter explicit adjustment type, amount, and range;
- display factual baseline separately from scenario adjustments;
- display multiplicity explicitly;
- display subject/run currentness; and
- display M10 eligibility evidence.

It may not uncheck factual components, replace factual records, enter arbitrary
component types, manipulate fingerprints, declare baseline none, rank,
recommend, optimize, or calculate tax or NPV.

## 29. Frontend Async Isolation

All future UI paths require route-, client-, subject-, and request-aware stale-
response protection. A captured client ID alone is insufficient. Each
independent channel requires monotonic context generation, per-request epoch,
and unique active loading ownership.

Deterministic controlled-promise tests must cover:

- subject list and baseline resolution;
- subject creation;
- subject detail;
- inventory and validation;
- run execution;
- history; and
- result/currentness/M10-eligibility composite loading.

For every materially independent channel, A→B and A→B→A races cover stale
success, rejection, structured error, and finally/loading cleanup. Old-A and
new-A ownership must remain distinguishable.

## 30. Fail-Closed Contract

At minimum the future implementation blocks:

- missing or foreign subject;
- unsupported family or version;
- invalid subject or manifest fingerprint;
- semantic duplicate subject;
- invalid adjustment type;
- zero, negative, noncanonical, or out-of-range amount;
- invalid month or reversed range;
- adjustment range outside the execution horizon;
- caller-authored baseline-none evidence;
- incomplete factual inventory;
- caller reduction of factual universe;
- duplicate adjustment identity;
- result or aggregate numeric overflow;
- stale dependencies;
- invalid result, dependency, inventory, or snapshot fingerprint;
- unsupported currentness or eligibility contract version; and
- undisposed mandatory warnings.

No partial authoritative scenario or `run anyway` path exists.

Future pair admission additionally blocks unequal persisted
`factual_baseline_material_fingerprint` values as
`comparison_factual_baseline_material_mismatch`. This is a blocking relational
comparison condition, not a warning and not a per-run eligibility claim.

## 31. Stop Conditions

Stop future implementation and return the named blocker if any condition is
required:

- `PKG_014_SINGLE_AUTHORITY_VIOLATION` — M09 would duplicate an upstream or
  professional formula.
- `PKG_014_V1_SEMANTIC_REWRITE_REQUIRED` — accepted
  `deterministic_monthly_cashflow/v1` history or meaning would change.
- `PKG_014_SUBJECT_CURRENTNESS_LEAKAGE` — one subject would stale a sibling
  merely because the sibling exists or runs.
- `PKG_014_FACTUAL_UNIVERSE_REDUCTION_REQUIRED` — caller or scenario logic
  would omit, waive, or reduce mandatory factual components.
- `PKG_014_REPLACEMENT_OR_SUPPRESSION_REQUIRED` — a requirement needs
  replacement, suppression, or mutation rather than additive-only evidence.
- `PKG_014_NEW_CALCULATION_FORMULA_REQUIRED` — implementation requires a new
  business calculation beyond admitted addition, subtraction, and alignment.
- `PKG_014_RETIREMENT_TIMING_FORMULA_REQUIRED` — retirement, pension-start, or
  employment-cessation timing would be inferred or calculated.
- `PKG_014_TAX_NPV_OPTIMIZATION_REQUIRED` — tax, NPV, return, allocation,
  optimization, ranking, or recommendation is required.
- `PKG_014_NUMERIC_PRECISION_CONFLICT` — exact Decimal and `Numeric(20,2)`
  constraints cannot represent the accepted contract without a new decision.
- `PKG_014_DB_IMMUTABILITY_BLOCKED` — critical append-only invariants cannot be
  enforced against raw SQL for supported databases.
- `PKG_014_CLIENT_ISOLATION_BLOCKED` — same-client ownership or foreign-ID
  non-leakage cannot be guaranteed.
- `PKG_014_CALLER_FORGED_AUTHORITY_REQUIRED` — implementation would trust a
  caller-authored server field, fingerprint, currentness, eligibility, or
  baseline declaration.
- `PKG_014_M10_IMPLEMENTATION_REQUIRED` — delivery would require comparison or
  other M10 behavior.
- `PKG_014_PREDECESSOR_REGRESSION_BLOCKED` — an accepted predecessor contract
  would need to be weakened or rewritten.

## 32. Acceptance Criteria

- **AC-014-001:** Definition work begins from exact base `f1cbddbf27d7712ce2409248240a0cb4cadebc8d` on `pkg-014-review`, with no unrelated tracked change.
- **AC-014-002:** Package identity and M09 `ORCHESTRATOR_AND_AGGREGATOR_ONLY` role are exact; `scenario_family == declared_retirement_cashflow_adjustments`, `scenario_contract_version == v1`, and the combined identifier is `declared_retirement_cashflow_adjustments/v1`, with no ambiguous second version field.
- **AC-014-003:** The definition states the normative single-authority law and proves M09 owns no duplicated upstream or professional formula.
- **AC-014-004:** `deterministic_monthly_cashflow/v1` remains byte-, history-, currentness-, eligibility-, and semantic-contract unchanged.
- **AC-014-005:** The product is represented only as an objective planner-declared retirement cashflow sensitivity/planning alternative.
- **AC-014-006:** An immutable client-owned scenario subject binds exact `scenario_family`, exact `scenario_contract_version`, manifest identity, semantic fingerprint, integrity fingerprint, provenance, and creation evidence.
- **AC-014-007:** Calculation-semantic identity includes only calculation-affecting adjustment semantics and explicitly excludes IDs, labels, actor, timestamps, run ID, and sequence.
- **AC-014-008:** Canonical ordering and multiplicity produce deterministic subject semantic fingerprints.
- **AC-014-009:** Same `client_id + scenario_family + scenario_contract_version` semantic duplicate creation fails closed as `scenario_subject_semantically_duplicate` regardless of label or evidence-only differences.
- **AC-014-010:** Exactly one server-owned baseline exists per `client_id + scenario_family + scenario_contract_version` with canonical empty manifest and `server_resolved_no_scenario_adjustments` evidence.
- **AC-014-011:** Caller-authored empty adjustments cannot create or forge the baseline subject.
- **AC-014-012:** Every adjusted subject contains at least one valid positive adjustment and remains immutable.
- **AC-014-013:** The closed vocabulary is exactly additional monthly income and additional monthly expense, with direction implied by type.
- **AC-014-014:** Each adjustment binds server identity, subject, type, canonical amount, inclusive range, planner provenance, timestamp, and fingerprint evidence.
- **AC-014-015:** Amount validation enforces canonical Decimal ILS with exactly two places and inclusive range `0.01` through `999999999999999999.99` without rounding or float authority.
- **AC-014-016:** Adjustment months are strict `YYYY-MM`, ordered, inclusive, full-month, and wholly contained in the execution horizon.
- **AC-014-017:** Months outside an adjustment range are `contractually_not_applicable`, with no missing-to-zero interpretation, proration, or extension.
- **AC-014-018:** Adjustment semantics are `ADDITIVE_ONLY` and cannot replace, suppress, waive, or mutate factual evidence or upstream output.
- **AC-014-019:** Equal separately declared adjustments remain separately calculation-affecting through explicit multiplicity, while duplicate identity fails closed.
- **AC-014-020:** Factual inventory remains complete and server-owned, separate from the immutable planner-declared adjustment manifest, and contributes to a canonical `factual_baseline_material_fingerprint` excluding scenario adjustments.
- **AC-014-021:** Every run snapshot/result binds factual inventory and adjustment manifest as distinct authority domains and persists/exposes the canonical `factual_baseline_material_fingerprint` without making their provenance indistinguishable.
- **AC-014-022:** M09 arithmetic is limited to full-month alignment, admitted additions, inflow/outflow sums, period net, and deterministic range totals.
- **AC-014-023:** Currentness key is `client_id + scenario_subject_id + scenario_family + scenario_contract_version` under `m09-subject-currentness-v1`, with exact family/version tokens and one current leaf per subject.
- **AC-014-024:** Multiple subject leaves may be current simultaneously; rerun A supersedes only A while factual dependency change can stale every affected subject.
- **AC-014-025:** Legacy `m09-currentness-v1` is not reinterpreted and existing runs remain readable under their accepted contract.
- **AC-014-026:** `m09-to-m10-eligibility-v2` is per-run derived fail-closed evidence proving individual subject, manifest, factual, dependency, result, currentness, and warning integrity and exposing the persisted factual-baseline material fingerprint; it does not claim peer equality.
- **AC-014-027:** Eligibility v2 does not reinterpret v1 and conveys no professional authority, recommendation, or M10 execution authorization.
- **AC-014-028:** Future M10 admission requires two distinct same-client subjects with exact equal `scenario_family`, `scenario_contract_version`, horizon, persisted `factual_baseline_material_fingerprint`, component-domain version, M09 engine/result-schema versions, and calculation-affecting factual upstream versions; both runs are current, individually eligible, and adjustment-semantically distinct.
- **AC-014-029:** PKG-014 implements no M10 behavior; intended future M10 remains comparator-only and baseline-versus-one-adjusted is preferred only when exact factual-baseline material equality holds.
- **AC-014-030:** Distinct semantic, evidence, adjustment-manifest, factual-inventory, factual-baseline-material, snapshot, result-semantic, and result-integrity fingerprints are defined with deterministic canonical ordering and exclusions.
- **AC-014-031:** Repeated execution from identical semantic inputs produces the same semantic result fingerprint independent of run IDs and timestamps.
- **AC-014-032:** Persistence expectations are additive, immutable, append-only, client-owned, and preserve baseline and semantic-subject uniqueness.
- **AC-014-033:** Critical baseline, client, uniqueness, predecessor, sequence, and UPDATE/DELETE invariants are required at database level for supported databases.
- **AC-014-034:** Client isolation applies to subjects, adjustments, runs, history, currentness, and eligibility, including direct-service and foreign-ID non-leakage paths.
- **AC-014-035:** Calculation-affecting APIs reject extra fields and never trust caller-authored server identity, baseline, factual inventory, currentness, eligibility, fingerprint, actor/timestamp authority, or result.
- **AC-014-036:** Frontend exposes bounded subject and adjustment workflows while preserving factual/adjustment separation and no authoritative factual-selection control.
- **AC-014-037:** Controlled-promise tests prove route/client/subject/request isolation for all seven materially independent async paths under A→B and A→B→A races.
- **AC-014-038:** Blocking, mandatory-review, and informational warning categories remain distinct; planner-declared provenance is informational by default and creates no bypass.
- **AC-014-039:** Every fail-closed and stop condition produces typed evidence without partial authoritative output; future pair-level factual-baseline mismatch blocks as `comparison_factual_baseline_material_mismatch` and cannot be replaced by individual eligibility.
- **AC-014-040:** Verification proves only the definition and necessary narrow plan alignment changed; no code, tests, migration, acceptance record, master merge, M10, or next-package work occurred.

## 33. Negative Acceptance Criteria

- **NAC-014-001:** Any semantic, historical, fingerprint, currentness, eligibility, or persistence rewrite of `deterministic_monthly_cashflow/v1`.
- **NAC-014-002:** Caller-created baseline, caller-authored `adjustments=[]` authority, or forged no-adjustment evidence.
- **NAC-014-003:** More than one baseline for the same `client_id + scenario_family + scenario_contract_version`.
- **NAC-014-004:** Label-, actor-, timestamp-, ID-, run-, or sequence-only distinction between semantically duplicate subjects.
- **NAC-014-005:** Empty adjusted subject.
- **NAC-014-006:** Arbitrary adjustment type, free-form direction, caller category, or sign-derived direction.
- **NAC-014-007:** Zero or negative adjustment amount.
- **NAC-014-008:** Float authority, scientific-notation canonicalization, more than two decimal places, silent rounding, clipping, or coercion.
- **NAC-014-009:** Amount outside `0.01` through `999999999999999999.99` or aggregate outside accepted `Numeric(20,2)` bounds.
- **NAC-014-010:** Invalid/reversed month range, range outside run horizon, implicit extension, inferred continuation, day-level logic, or proration.
- **NAC-014-011:** Replacement, suppression, waiver, mutation, or correction of a factual component through a scenario adjustment.
- **NAC-014-012:** Caller selection or reduction of the authoritative factual subset or caller declaration of factual emptiness/completeness.
- **NAC-014-013:** Scenario assumption used to repair or replace a missing factual dependency.
- **NAC-014-014:** Automatic economic deduplication of explicit additional adjustments against factual records.
- **NAC-014-015:** Loss of multiplicity for separately declared semantically equal adjustments or acceptance of duplicate adjustment identity.
- **NAC-014-016:** Factual inventory and planner-declared adjustment evidence made indistinguishable.
- **NAC-014-017:** One subject becoming stale only because another subject exists or executes.
- **NAC-014-018:** In-place mutation or deletion of subject, manifest, adjustment, run, result, or historical evidence.
- **NAC-014-019:** Retrofit of legacy v1 runs into default subjects, subject currentness, eligibility v2, or comparison inputs.
- **NAC-014-020:** Reinterpretation of `m09-currentness-v1` or `m09-to-m10-eligibility-v1`.
- **NAC-014-021:** Caller-forged subject ownership, baseline, inventory, currentness, eligibility, fingerprints, server actor/timestamp, run identity, or result.
- **NAC-014-022:** Foreign-ID existence leakage or cross-client subject/run/result use.
- **NAC-014-023:** Partial authoritative scenario, caller omission authority, waiver, or `run anyway`.
- **NAC-014-024:** M10 comparison implementation, automatic pair selection, or comparison persistence in PKG-014.
- **NAC-014-025:** Percentage, annualization, ranking, score, recommendation, optimization, preference, or forecast claim.
- **NAC-014-026:** Tax, fixation, CBS, indexation, grant, investment return, discounting, NPV, allocation, withdrawal, commutation, conservation, or minimum-pension formula.
- **NAC-014-027:** Retirement-date consequence, employment-income cessation, pension-start, or pension/capital allocation formula.
- **NAC-014-028:** V1 coefficient `200`, minimum pension `5500`, rate `0.03`, age 90, implicit horizon, or hidden balanced threshold.
- **NAC-014-029:** M08E, report generation, M11-M14 implementation, or production-readiness claim.
- **NAC-014-030:** Migration creation/execution, schema change, production code, implementation test, or acceptance record during definition drafting.
- **NAC-014-031:** Generic warning acceptance or planner-declared provenance used to bypass blocking or mandatory-review conditions.
- **NAC-014-032:** Authorization of PKG-014 implementation, M10 implementation, or any next package by this definition proposal.
- **NAC-014-033:** Future M10 admission of two otherwise eligible subject runs whose persisted `factual_baseline_material_fingerprint` values differ, or M10 normalization/reconstruction used to conceal that mismatch.

## 34. Verification Matrix

| Area | Required definition/implementation evidence |
|---|---|
| Base and scope | Exact branch/base; docs-only diff; protected paths untouched |
| Family isolation | Existing v1 regression and no reinterpretation; new family closed |
| Subject semantics | Exact family/version tokens; canonical semantic multiset; duplicate rejection; baseline uniqueness |
| Adjustment validation | Closed types, Decimal boundaries, canonical months, containment |
| Factual authority | Complete server inventory; no caller subset or suppression |
| Currentness | Independent A/B leaves; A rerun affects A only; upstream staleness propagation |
| Eligibility v2 | Per-run subject-aware fail-closed evidence, persisted factual-baseline material fingerprint, and v1 non-reinterpretation |
| Future pair admission | Exact shared factual-baseline material and calculation-affecting version equality; mismatch blocks |
| Determinism | Stable semantic and result fingerprints; evidence fields excluded from equality |
| Persistence | Additive migration plan; database-enforced uniqueness and immutability |
| Client isolation | API and direct-service foreign/nonexistent equivalence |
| Frontend isolation | Controlled A→B/A→B→A races for seven independent channels |
| Authority audit | No duplicated formula, M10, tax, NPV, timing, ranking, or recommendation logic |

## 35. Explicit Deferred and Excluded Scope

Deferred and excluded from PKG-014 are:

- retirement-date consequences;
- pension commencement and employment-income cessation;
- pension/capital allocation, withdrawal, commutation, max pension, max capital,
  or balanced strategies;
- tax/net, fixation, grants, CBS/indexation, NPV, investment returns;
- optimization, ranking, recommendation, preference, report, or client output;
- M08E;
- M10 implementation;
- M11-M14;
- production retention, release, security-role, and operational readiness;
- V1 constants including coefficient `200`, minimum pension `5500`, rate
  `0.03`, age 90, implicit horizons, and hidden balanced thresholds; and
- V1/V2 parity.

## 36. Expected Implementation Shape

If separately authorized after definition acceptance, expected implementation
may include additive subject/adjustment persistence, subject-aware M09 service
and API contracts, bounded UI, database invariants, and focused/full regression
evidence. This section is non-authorizing and does not freeze final table,
route, class, or component names.

## 37. Authorization Boundary

- PKG-014 definition acceptance: `NOT_YET_DECIDED`.
- PKG-014 implementation: `NOT_AUTHORIZED`.
- Migration creation or execution: `NOT_AUTHORIZED`.
- M10 implementation: `NOT_AUTHORIZED`.
- M11-M14 implementation: `NOT_AUTHORIZED`.
- Next package: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Production readiness: `NOT_CLAIMED`.

The only permitted next gate is independent definition acceptance audit.

PKG_014_DEFINITION_PROPOSED_FOR_ACCEPTANCE
