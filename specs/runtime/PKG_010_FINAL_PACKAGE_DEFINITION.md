# PKG-010 — M05 Manual Pension Balance Ledger and Exact Reconciliation Foundation

## 1. Identity and status

| Field | Value |
|---|---|
| Package | `PKG-010 — M05 Manual Pension Balance Ledger and Exact Reconciliation Foundation` |
| Module | `M05` |
| Definition status | `CORRECTED_PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Migration creation/execution | `NOT_AUTHORIZED` |
| M06 | `NOT_AUTHORIZED` |
| Definition acceptance record | `NOT_CREATED` |
| Authoritative base | `1d336485f4dd7c187894dd8670f40dba73a36df9` |
| Predecessor implementation | PKG-009 at `ae73a7706214b137b7452b9f66c483ee5b57009c` |
| Predecessor migration | `95222c79dce8` |

This corrected definition authorizes no implementation, migration, M06 work,
or acceptance record.

## 2. Authoritative sources and predecessor boundary

The authoritative sources are:

1. `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`;
2. `specs/runtime/PKG_009_FINAL_PACKAGE_DEFINITION.md`;
3. `specs/runtime/PKG_009_definition_acceptance_record.md`;
4. `specs/runtime/PKG_009_acceptance_record.md`;
5. accepted M01-M04 repository contracts at the authoritative base; and
6. the decisions locked in this corrected definition.

M05 consumes M01-M04 as read-only predecessor authority. It never changes an
M01-M04 lifecycle, source fact, review, annotation, classification, revision,
provenance item, or authority decision.

## 3. Exact predecessor lifecycle vocabulary

### 3.1 M01 mutation eligibility

`M01 mutation-eligible` is a derived predicate, not a persisted status. It is
true exactly for these accepted non-archived persisted lifecycle states:

- `draft`;
- `intake`;
- `analysis`;
- `review`; and
- `delivered`.

The implementation may name the predicate `m01_case_not_archived` or
`m01_mutation_eligible`. It may not introduce a new M01 status.

`archived` remains historically readable and is mutation-ineligible. M06
technical eligibility is false for `archived`. PKG-010 imposes no narrower
professional M01 state requirement unless a later accepted package says so.

### 3.2 M02 acceptance

The exact required M02 lifecycle predicate is:

`lifecycle_status = accepted_for_review`

Generic `accepted` is not an M02 lifecycle term in this package. Every
candidate, lifecycle, revalidation, and M06-eligibility operation rechecks
`accepted_for_review` against the current same-client M02 manual intake.

### 3.3 M03 and M04 authority

M03 must expose its current accepted revision and current downstream
eligibility. M04 must expose its current accepted, resolved revision and
read-time eligibility for M05. Stored or caller-authored booleans never replace
those current authoritative reads.

## 4. Exact product outcome and target kind

PKG-010 creates a bounded, immutable, client-scoped manual pension balance
ledger and exact reconciliation foundation.

The only authoritative first-package target kind is exactly:

`target_kind = manual_record_review`

No other target kind is authoritative. Uploaded opaque sources cannot supply
M05 monetary values. The package separates immutable source values, derived
reconciliation values, and adjusted/effective values while preserving all
predecessor evidence.

M06, parsing, extraction, normalization, conversion, coefficients, tax,
exemption, fixation, formal 161D, liquidity, withdrawal, pension commencement,
scenarios, recommendations, and reports remain outside this package.

## 5. Candidate authority contract

A manual candidate may exist as a historical or `draft` ledger candidate, but
it becomes authoritative only when all of the following are current and valid:

1. M01 is mutation-eligible;
2. M02 `lifecycle_status = accepted_for_review`;
3. target kind is `manual_record_review`;
4. M03 has current accepted authority and downstream eligibility;
5. M04 has current accepted/resolved authority and read-time M05 eligibility;
6. `declared_provider_name` is non-null and non-empty;
7. `declared_account_reference` is non-null and non-empty;
8. source `statement_date` is present and valid;
9. source `total_balance` is present and valid;
10. at least one current resolved M04 component exists;
11. every required M04 component maps one-to-one to an M02 monetary component;
12. a valid M05 ILS currency confirmation covers the exact source snapshot;
13. all authoritative monetary values satisfy the scale-2 Decimal contract;
14. there is exactly one authoritative candidate after precedence; and
15. provenance is complete and internally consistent.

The server resolves candidate authority at every authoritative operation.

## 6. M05 currency-confirmation authority

M02 monetary fields do not carry currency. PKG-010 never infers ILS from
locale, provider, product, filename, package scope, target kind, or any other
metadata.

Before a candidate can become `reconciled` or `warning_reviewed`, the planner
must submit the bounded intent:

`confirm currency ILS for this current candidate`

This intent may accompany `start` and must accompany `reconcile` or
`review_warning` whenever the current draft lacks a still-valid confirmation.
It is not an additional lifecycle state or transition. The server persists the
confirmation in the immutable successor decision snapshot with:

- accepted value exactly `currency = ILS`;
- server-resolved candidate identity;
- exact current M02 intake reference;
- exact monetary source-snapshot reference/digest;
- explicit confirmation evidence;
- server-owned actor; and
- server-owned timestamp.

The caller supplies only confirmation intent. The server owns candidate,
source snapshot, actor, timestamp, accepted currency value, and confirmation
evidence. M02 is never mutated.

Confirmation applies only to the exact candidate/revision source snapshot.
Any change in monetary source facts invalidates it and requires renewed
confirmation. No other currency is accepted.

Without valid confirmation, a ledger may exist and remain readable as
`draft`, but it cannot become `reconciled` or `warning_reviewed`; M06 technical
eligibility is false with `currency_or_unit_invalid`.

## 7. Exact provider and account identity

Logical account identity uses exactly these persisted M02 fields:

- provider: `declared_provider_name`;
- account: `declared_account_reference`.

Each must be non-null and non-empty. Equality compares the exact persisted
Unicode string byte-for-byte after standard database UTF-8 serialization.
There is no trimming, case folding, Unicode normalization, punctuation
removal, whitespace collapsing, transliteration, provider alias mapping,
provider-code mapping, or fuzzy comparison.

Two values that differ byte-for-byte are different identities. Source strings
are not mutated or normalized. Any future normalization or code mapping
requires a separate accepted package decision. `manual_technical_reference`
is never provider or account identity.

Multiple statements link to one server-generated ledger subject only through
explicit server validation of exact same-client provider/account identity.

## 8. Candidate identity and precedence

The immutable server-resolved candidate tuple contains:

- client ID;
- M02 intake ID;
- target kind `manual_record_review`;
- current accepted M03 revision ID; and
- current accepted M04 revision ID.

The tuple is unique. The caller cannot author any trusted tuple element.

Within one proven subject, authoritative-current precedence is exactly:

1. latest source `statement_date`;
2. then latest current accepted M03 `decided_at`.

Equal date and equal timestamp produce `authoritative_candidate_tie`.
M02 created/updated time, M04 acceptance time, latest-created/latest-updated,
M02 superseding-candidate logic, and fuzzy account matching are prohibited.

A newer ineligible candidate does not replace an older eligible candidate.
The result exposes informational `newer_ineligible_candidate_exists`, unless
upstream supersession explicitly invalidates the older source.

## 9. Component vocabulary and deterministic mapping

The component vocabulary is exactly:

- `contribution_component`;
- `severance_component`;
- `unknown_component`.

`contribution_component` represents תגמולים. `compensation_component` is
prohibited. `capital` and `pension` are classification interpretations or
derived grouping views, not monetary components, and are never double-counted.

### 9.1 M02 component identity

An M02 declared monetary component is identified by:

- immutable `component_index`; and
- exact persisted `component_label`.

Its source monetary value is the exact value stored for that list item.
Duplicate labels at different indices remain distinct. Mapping by label alone
is prohibited.

### 9.2 M04 evidence identity

The accepted M04 evidence identity includes the predecessor component index
and exact decision-time label/code snapshot. A mapping is valid only with:

- same client;
- same M02 intake;
- same target;
- same component index;
- exact component label match;
- exact component code match where a code exists;
- current accepted M04 revision; and
- unique identity on both sides.

### 9.3 Ledger value identity

The server creates one immutable ledger value identity per mapped M04 evidence
identity. Each M04 component maps to exactly one M02 monetary component value,
and each M02 monetary component maps to at most one M04 component.

The mapping fails closed for duplicate M02 indices, duplicate M04 identities,
collapsed duplicate labels, index/label/code mismatch, missing M02 value,
unmapped M02 value, unmapped M04 component, cross-intake/client/target
reference, stale M04 revision, or `unknown_component` used as reconcilable.
Stable outcomes are `component_mapping_invalid` or
`component_set_incomplete`, as applicable.

An authoritative candidate requires a non-empty current resolved M04
component set. Empty components are `m04_ineligible` or
`component_set_incomplete`; total-only reconciliation is prohibited.

## 10. Monetary states, precision, and canonical zero

Every monetary field has exactly one state:

- `recorded_value`;
- `recorded_zero`;
- `missing`;
- `excluded`; or
- `malformed`.

Missing, excluded, and malformed never become zero silently.

All authoritative M05 monetary values use Decimal scale exactly `2`, with
persistence-compatible `Numeric(20,2)`. Accepted adjusted-value intent must be
an exact decimal representation with no more than two fractional digits and
must be canonically representable at scale 2 without rounding.

Reject rather than round:

- more than two fractional digits;
- exponent form not exactly representable at scale 2;
- binary float;
- NaN or infinity;
- Boolean;
- list/object;
- formatted currency or comma-formatted string; and
- whitespace-padded string unless strict schema parsing rejects it earlier.

All sums and discrepancy arithmetic use Decimal scale 2, with no intermediate
binary float, implicit rounding, or hidden post-comparison quantization. The
tolerance comparison uses the exact stored Decimal discrepancy.

Canonical zero normalizes `-0.00`, `0`, `0.0`, and `0.00` to `0.00`.
Canonical zero is not negative and creates no negative warning.

Required examples:

| Input | Outcome |
|---|---|
| `0.50` | accepted as `0.50` |
| `0.500` | rejected for excessive scale |
| `0.499` | rejected, never rounded |
| `-0.00` | canonical `0.00`, no negative warning |
| `-0.01` | accepted exact signed value plus mandatory negative warning |

## 11. Source, derived, and effective values

Every ledger value exposes immutable source value/state, derived values, and
one current effective value separately.

- Effective value initially equals the valid source value.
- An adjustment successor may replace only the effective value.
- Only the current effective value participates in reconciliation.
- Source and adjusted values are never both counted.
- Every predecessor effective value remains in immutable history.
- The server resolves the previous effective value; the caller cannot supply
  or forge it.
- Each successor snapshot contains exactly one current effective value per
  monetary identity.

An adjustment to total changes only `effective_total_balance`. An adjustment
to a component changes only that component's effective value. Multiple
adjustments apply sequentially through immutable successors.

One adjustment action changes exactly one monetary identity. Batch adjustment
is deferred.

## 12. Normative persistence and append-only model

Implementation must provide structures semantically equivalent to:

1. ledger subject;
2. immutable ledger revision;
3. revision-owned ledger values/components;
4. immutable candidate links; and
5. additive adjustment evidence.

Required invariants include stable server IDs, explicit client ownership,
same-client/subject/account composite integrity, unique revision sequence,
one child per predecessor, unique candidate tuple, unique value identity per
revision, deterministic current leaf, and immutable evidence snapshots.

No subject identity, revision, value, candidate link, adjustment, provenance,
warning snapshot, predecessor, or sequence may be updated or deleted after
insert. No M01-M04 row is backfilled or mutated.

## 13. Exact lifecycle matrix

Persisted states are exactly `draft`, `reconciled`, `warning_reviewed`,
`blocked`, and `superseded`.

| Current state | Action | Successor | Allowed |
|---|---|---|---|
| none | `start` | `draft` | yes |
| `draft` | `reconcile` | `reconciled` | yes, gates satisfied |
| `draft` | `review_warning` | `warning_reviewed` | yes, mandatory warning set fully disposed |
| `draft` | `mark_blocked` | `blocked` | yes |
| `draft` | `adjust` | `draft` successor | yes |
| `draft` | `supersede` | `superseded` | yes |
| `draft` | `revalidate` | `draft` successor | only when upstream invalidated |
| `reconciled` | `adjust` | `draft` successor | yes |
| `reconciled` | `mark_blocked` | `blocked` | yes |
| `reconciled` | `supersede` | `superseded` | yes |
| `reconciled` | `revalidate` | `draft` successor | only when upstream invalidated |
| `warning_reviewed` | `adjust` | `draft` successor | yes |
| `warning_reviewed` | `mark_blocked` | `blocked` | yes |
| `warning_reviewed` | `supersede` | `superseded` | yes |
| `warning_reviewed` | `revalidate` | `draft` successor | only when upstream invalidated |
| `blocked` | `adjust` | `draft` successor | yes |
| `blocked` | `revalidate` | `draft` successor | only when upstream invalidated |
| `blocked` | `supersede` | `superseded` | yes |
| `blocked` | `mark_blocked` | — | no |
| `superseded` | any mutation | — | no |

Additional normative rules:

- `superseded` is terminal and has no successor;
- `reconcile` and `review_warning` are allowed only from `draft`;
- repeated `mark_blocked` on `blocked` is rejected;
- `start` is rejected once any subject chain exists;
- every action carries current-leaf revision intent;
- two concurrent actions from one leaf permit exactly one winner;
- the loser receives a stable conflict and creates no row;
- one child per predecessor is enforced; and
- no action may create an empty or partial successor.

Optional undo is excluded from required acceptance and has no implementation
obligation in PKG-010.

## 14. Reconciliation formula and completeness

The normative formula is:

`discrepancy = effective_total_balance - sum(effective_reconcilable_component_value for each included evidence identity exactly once)`

Only current effective values participate. The authoritative sum includes
only mapped `contribution_component` and `severance_component` identities,
each once. It excludes monthly pension, capital/pension grouping, aliases,
`unknown_component`, primary tagmul, missing/malformed/excluded values,
inferred periods, and any duplicate source/adjusted representation.

The snapshot persists effective total, effective components, signed and
absolute discrepancy, included/excluded evidence identities and reasons, and
algorithm version.

Tolerance is exact:

- `abs(discrepancy) <= 0.50 ILS` satisfies tolerance;
- `abs(discrepancy) > 0.50 ILS` creates mandatory
  `reconciliation_difference_review_required`.

Boundary evidence must include `0.00`, `0.01`, `0.49`, `0.50`, and `0.51`.
No total or component is corrected silently.

Every required resolved M04 component maps to exactly one monetary value. An
empty set, missing value, malformed value, invalid mapping, or extra unmapped
M02 monetary component prevents `reconciled`. Component sum `0.00` is valid
only when at least one mapped component is explicitly `recorded_zero`.

## 15. Stable warning catalogue and exact-set disposition

The server computes all warning IDs.

Mandatory-review warnings are exactly:

- `reconciliation_difference_review_required`;
- `negative_value_review_required`.

Informational warnings are exactly:

- `stale_warning`;
- `newer_ineligible_candidate_exists`.

Any negative total/component effective or source value is retained exactly and
creates `negative_value_review_required`. Canonical `0.00` is not negative. A
negative-warning draft cannot become `reconciled`, but may become
`warning_reviewed` through exact-set disposition. No debt, reversal,
correction, invalidity, tax, or withdrawal meaning is inferred.

`review_warning` submits only:

- current revision intent;
- exact set of mandatory warning IDs currently present;
- reason code;
- explanation; and
- explicit confirmation.

The submitted mandatory set must equal the current server-computed mandatory
set exactly. Missing, extra, unknown, informational-as-mandatory, stale-set,
or caller-authored snapshot input fails with `warning_disposition_invalid`.
When both mandatory warnings exist, both must be disposed together; reviewing
one cannot clear the other.

The successor persists all warning IDs, mandatory/informational class, exact
disposition set, reason, explanation, actor, timestamp, effective/source value
snapshot, and discrepancy snapshot. M06 eligibility requires complete
disposition of every mandatory warning.

## 16. Deterministic calendar-month stale rule

Inputs are source `statement_date` and server-owned `evaluation_date`, both
date-only. No timezone conversion or timestamp arithmetic is used after dates
are resolved.

The server computes a threshold by shifting `evaluation_date` back 12 calendar
months and clamping its day to the last valid day of the target month.

`statement_date < threshold` means stale. Equality or a later statement date
is not stale.

| Statement date | Evaluation date | Outcome |
|---|---|---|
| `2025-01-31` | `2026-01-31` | not stale |
| `2025-01-30` | `2026-01-31` | stale |
| `2024-02-29` | `2025-02-28` | not stale |
| `2024-02-28` | `2025-02-28` | not stale |
| `2024-02-27` | `2025-02-28` | stale |
| `2025-03-31` | `2026-03-30` | not stale |
| `2025-03-29` | `2026-03-30` | stale |

A statement date after evaluation date is invalid with
`statement_date_invalid`. Missing evaluation date fails closed. The caller
cannot provide evaluation date. Historical snapshots retain evaluation date
and stale result and are never reinterpreted using the current clock.

`stale_warning` alone is informational: it does not require warning review,
invalidate authority, or block M06 technical eligibility.

## 17. Adjustment boundary

`adjust` changes exactly one current monetary identity and appends a complete
`draft` successor. Input intent contains target identity, new exact scale-2
effective value, reason, explanation, and explicit confirmation.

The server resolves previous effective value, source value/provenance,
currency, predecessor, actor, and timestamp. The caller cannot author the old
value. Total adjustment changes only `effective_total_balance`; component
adjustment changes only that component's effective value.

Adjustment cannot change provider, account, product, statement date,
currency, M02/M03/M04 IDs, source values, classification, actor, timestamp,
sequence, or prior reconciliation evidence. It cannot create authority when
source total is missing/malformed/excluded. Every adjustment forces fresh
reconciliation; source and adjusted values are never both counted. Batch
adjustment is deferred.

## 18. Archive and revalidation

Archived M01 cases remain readable but mutation-ineligible. M06 eligibility is
false with `archived_case`. Reopen changes no history and restores no authority.

`revalidate` is allowed only when upstream authority is invalidated and creates
a complete `draft` successor using current M02 `accepted_for_review`, current
M03/M04 authority, mapping, source facts, and a new server-owned evaluation
date. Currency confirmation must be renewed when the monetary source snapshot
changed.

## 19. Derived M06 technical eligibility

M06 eligibility is read-time, server-controlled, and fail-closed. It is true
only when:

1. M01 is mutation-eligible;
2. one valid ledger chain and authoritative candidate exist;
3. M02 is current `accepted_for_review` and target is
   `manual_record_review`;
4. M03 is current, accepted, and eligible;
5. M04 is current, accepted, resolved, and eligible for M05;
6. current state is `reconciled` or `warning_reviewed`;
7. exact provider/account, statement date, total, and provenance are present;
8. valid source-snapshot-specific ILS confirmation exists;
9. all monetary values are valid scale-2 Decimal;
10. component mapping is complete, unique, and non-empty;
11. no candidate tie, supersession, or corruption exists; and
12. every mandatory warning is fully disposed.

Stable exclusions include `archived_case`, `no_authoritative_candidate`,
`authoritative_candidate_tie`, `upstream_source_ineligible`, `m03_ineligible`,
`m04_ineligible`, `upstream_revalidation_required`, `ledger_draft`,
`ledger_blocked`, `ledger_superseded`, `required_value_missing`,
`component_mapping_invalid`, `component_set_incomplete`,
`reconciliation_unresolved`, `warning_not_reviewed`,
`negative_value_review_required`, `warning_disposition_invalid`,
`statement_date_invalid`, `provenance_invalid`,
`ledger_chain_inconsistent`, and `currency_or_unit_invalid`.

`newer_ineligible_candidate_exists` remains informational. Eligibility does
not authorize M06 or establish conversion, coefficient, tax, exemption,
fixation, liquidity, withdrawal, pension commencement, or report readiness.

## 20. Backend and strict API boundary

The bounded client-scoped API may list candidates/subjects; get current ledger,
history, provenance, warnings, and M06 eligibility; and perform `start`,
`reconcile`, `review_warning`, `mark_blocked`, `adjust`, `supersede`, and
`revalidate`.

Strict mutation schemas accept intent fields only. Currency confirmation is a
bounded intent within applicable start/reconcile/review flows, not an
additional lifecycle transition. The server owns client/subject/candidate,
upstream IDs, source facts, mapping, previous/effective values, actor,
timestamp, sequence, leaf, provenance, warning set, reconciliation,
evaluation date/stale result, and eligibility.

Missing and foreign identifiers return indistinguishable public behavior and
reveal no foreign identity, existence, count, lifecycle, value, warning,
provenance, or timing information.

## 21. Frontend and async ownership

The planner UI displays source, derived, and effective values separately;
component mapping/identity; included/excluded status; signed/absolute
discrepancy; mandatory/informational warnings; exact disposition; currency
confirmation; precedence/tie; evaluation/stale result; immutable history;
adjustment evidence; and M06 eligibility/exclusions.

Every candidate-list, subject-detail, history, provenance, eligibility,
mutation, and post-mutation-refresh unit binds client ID, monotonic route
generation, per-request epoch, subject/candidate identity, and current revision
identity.

Deterministic matrices cover A→B, A→B→A, same-client X→Y, unmount, success,
rejection, structured API error, and `finally`. A stale mutation launches zero
refresh calls. Only a current mutation may launch and apply its current
detail/history/provenance/eligibility/list refresh.

## 22. Append-only enforcement evidence

Future acceptance must prove blocking of:

- instance revision update/delete;
- instance value update/delete;
- candidate-link update/delete;
- adjustment update/delete;
- subject identity update/delete;
- ORM bulk update/delete;
- Core `Session.execute(update/delete)`;
- alias DML where supported;
- cascade and parent deletion;
- relationship collection mutation;
- predecessor and sequence rewrite;
- provenance rewrite; and
- warning-snapshot rewrite.

Legitimate inserts through the bounded service remain allowed. Unrelated-model
DML remains unaffected. Corruption attempts leave history unchanged and make
authoritative reads/eligibility fail closed.

## 23. Concurrency evidence

Deterministic tests must cover concurrent start, concurrent successors from one
leaf, sequence uniqueness, one-child predecessor, duplicate candidate,
duplicate value identity, simultaneous reconcile/review/adjust/supersede,
current-leaf resolution, and retry after conflict.

Exactly one valid successor may win. Every loser receives a stable conflict,
creates no partial revision/value/evidence row, and may retry against the new
current leaf.

## 24. Migration boundary and evidence

A separately authorized implementation may create one additive migration with
parent exactly `95222c79dce8`. It must provide:

- one Alembic head;
- no backfill or M02-M04 mutation;
- explicit `Numeric(20,2)` precision and scale;
- composite foreign keys and unique constraints supporting locked integrity;
- SQLite upgrade/downgrade/re-upgrade;
- PostgreSQL offline upgrade and downgrade SQL;
- no Python query-result dependency in offline mode;
- retry-safe migration tests; and
- downgrade that removes only PKG-010 structures.

This definition assigns no revision ID and authorizes no migration creation or
execution.

## 25. Stop conditions

| Stop code | Condition |
|---|---|
| `M05_LIFECYCLE_AMBIGUITY_BLOCKED` | The exact transition matrix, current-leaf intent, or terminal superseded behavior cannot be preserved. |
| `M05_PREDECESSOR_LIFECYCLE_BLOCKED` | Exact M01 mutation-eligible states or M02 `accepted_for_review` cannot be enforced. |
| `M05_PROVIDER_ACCOUNT_IDENTITY_AMBIGUITY` | Exact byte-for-byte provider/account identity cannot be used without normalization/inference. |
| `M05_COMPONENT_MAPPING_AMBIGUITY` | Index plus exact label/code one-to-one M02-M04-M05 mapping cannot be proven. |
| `M05_DECIMAL_SCALE_ROUNDING_AMBIGUITY` | Scale-2 Decimal, canonical zero, reject-not-round, or `Numeric(20,2)` cannot be enforced. |
| `M05_CURRENCY_CONFIRMATION_BLOCKED` | Explicit source-snapshot-specific server-controlled ILS confirmation cannot be retained immutably. |
| `M05_WARNING_CATALOGUE_AMBIGUITY` | Stable mandatory/informational IDs or exact-set disposition cannot be enforced. |
| `M05_ADJUSTMENT_EFFECTIVE_VALUE_AMBIGUITY` | One effective value per identity or single-identity additive adjustment cannot be proven. |
| `M05_RECONCILIATION_CONTRACT_VIOLATION` | Effective-value formula, uniqueness, completeness, or exact tolerance cannot be preserved. |
| `M05_CANDIDATE_PRECEDENCE_BLOCKED` | Statement-date/M03-decision precedence and deterministic tie cannot be enforced. |
| `M05_APPEND_ONLY_ENFORCEMENT_NOT_PROVABLE` | Required instance/bulk/Core/cascade/relationship immutability evidence cannot be produced. |
| `M05_CONCURRENCY_INVARIANTS_NOT_PROVABLE` | Exactly-one winner, sequence, predecessor, candidate, or value uniqueness cannot be proven. |
| `M05_FRONTEND_OWNERSHIP_NOT_PROVABLE` | Required async ownership and stale-settlement matrices cannot be produced. |
| `M05_AC_NAC_EVIDENCE_GAP` | Any AC or NAC lacks deterministic executable evidence. |
| `M05_PREDECESSOR_TOTAL_ONLY_REQUIRED` | Implementation would require treating an empty M04 component set as authoritative. |
| `M05_MONETARY_STATE_COLLAPSE_REQUIRED` | Recorded value/zero, missing, excluded, and malformed cannot remain distinct. |
| `M05_CALLER_FORGED_AUTHORITY_BLOCKED` | Caller control of source, predecessor, mapping, warnings, actor/time, reconciliation, or eligibility cannot be prevented. |
| `M05_CLIENT_ISOLATION_BLOCKED` | Same-client subject/candidate/revision/value/provenance integrity cannot be enforced. |
| `M05_FOREIGN_ID_LEAKAGE_BLOCKED` | Foreign and missing IDs cannot use indistinguishable public behavior. |
| `M05_MIGRATION_INTEGRITY_BLOCKED` | Additive offline-safe migration above `95222c79dce8` cannot preserve predecessor data. |
| `M05_GENERIC_SCOPE_EXPANSION_REQUIRED` | Generic restrictions, account normalization, batch adjustment, or another unapproved framework is required. |
| `PARSER_OR_NORMALIZATION_SCOPE_REQUIRED` | Parsing, extraction, normalization, `_find_balance`, or uploaded-source interpretation is required. |
| `M06_SCOPE_REQUIRED` | Conversion, coefficient, downstream M06 authority, or execution is required. |
| `PRIOR_PACKAGE_REGRESSION_BLOCKED` | Accepted M01-M04 or PKG-001 through PKG-009 behavior cannot be preserved. |

Stop-condition count: `24`.

## 26. Acceptance criteria

| ID | Acceptance criterion |
|---|---|
| AC-010-001 | `m01_mutation_eligible` is true exactly for `draft`, `intake`, `analysis`, `review`, and `delivered`; `archived` is readable, mutation-ineligible, and M06-ineligible without creating a new persisted status. |
| AC-010-002 | Every candidate/action/eligibility operation requires current same-client M02 `lifecycle_status = accepted_for_review` and exact `target_kind = manual_record_review`; no generic M02 `accepted` or other target kind is authoritative. |
| AC-010-003 | Current accepted/eligible M03 and current accepted/resolved M04 with read-time M05 eligibility are server-revalidated for every authoritative operation and cannot be replaced by caller/stored booleans. |
| AC-010-004 | Planner ILS confirmation is explicit intent; server persists exact candidate/intake/source-snapshot, `currency = ILS`, confirmation, actor, and timestamp; changed source facts require renewal and missing confirmation blocks terminal authority/M06. |
| AC-010-005 | Subject identity uses non-null/non-empty exact persisted `declared_provider_name` plus `declared_account_reference`, compared byte-for-byte after UTF-8 serialization with no transformation or `manual_technical_reference`. |
| AC-010-006 | Candidate identity is the unique server-resolved client/M02/target-kind/current-M03/current-M04 tuple, and uploaded opaque targets cannot supply monetary authority. |
| AC-010-007 | Components use only contribution, severance, and unknown vocabulary; `compensation_component` and capital/pension monetary grouping are rejected. |
| AC-010-008 | M02 component index plus exact label and M04 evidence index/label/code map one-to-one to one ledger value identity under same client/intake/target/current M04 revision; duplicate labels at distinct indices stay distinct. |
| AC-010-009 | Duplicate/mismatched/unmapped/cross-scope/stale/unknown reconcilable components fail with `component_mapping_invalid` or `component_set_incomplete` and never partially map. |
| AC-010-010 | Every monetary field retains `recorded_value`, `recorded_zero`, `missing`, `excluded`, or `malformed`; no non-value state becomes zero. |
| AC-010-011 | Authoritative money uses exact scale-2 Decimal and `Numeric(20,2)`; excessive scale, unrepresentable exponent, binary float, NaN/infinity, Boolean, object/list, formatted/comma/whitespace string are rejected without rounding. |
| AC-010-012 | `-0.00`, `0`, `0.0`, and `0.00` become canonical non-negative `0.00`; `0.500` and `0.499` reject while `-0.01` retains sign and creates the negative warning. |
| AC-010-013 | Source, derived, and exactly one current effective value per identity remain distinct; source and adjusted values are never counted together. |
| AC-010-014 | The five normative persistence structures enforce stable IDs, same-client/account integrity, unique sequence/candidate/value, one child per predecessor, deterministic leaf, and immutable snapshots. |
| AC-010-015 | The complete lifecycle matrix is enforced exactly, including terminal `superseded`, draft-only reconcile/review, rejected repeated block/start, current-leaf intent, and no empty/partial successor. |
| AC-010-016 | `start` creates one complete draft and concurrent start permits exactly one winner; every state-changing action appends one complete successor and preserves predecessors. |
| AC-010-017 | Reconciliation uses exact scale-2 `effective_total_balance - sum(one current effective reconcilable value per included identity)` and persists signed/absolute discrepancy, identities, reasons, and algorithm version. |
| AC-010-018 | Exact boundary tests prove `0.00`, `0.01`, `0.49`, and `0.50` satisfy tolerance and `0.51` creates `reconciliation_difference_review_required`, without rounding or silent correction. |
| AC-010-019 | Authority requires a non-empty resolved M04 component set and complete one-to-one monetary mapping; component sum zero is valid only with at least one explicit mapped `recorded_zero`; total-only reconciliation is impossible. |
| AC-010-020 | Negative values remain signed, canonical zero is not negative, and any negative total/component creates mandatory `negative_value_review_required` without inferred business meaning. |
| AC-010-021 | Warning IDs are exactly the two mandatory and two informational catalogue values, all computed server-side and persisted with their classification. |
| AC-010-022 | `review_warning` requires the exact current mandatory-warning set plus reason/explanation/confirmation; missing/extra/unknown/informational/stale sets fail `warning_disposition_invalid`, and all simultaneous mandatory warnings are disposed together. |
| AC-010-023 | One `adjust` action changes exactly one effective monetary identity, server-resolves old value, appends a draft, retains source/prior values/provenance, and forces fresh reconciliation; batch adjustment is absent. |
| AC-010-024 | Authoritative precedence uses latest statement date then latest accepted M03 `decided_at`; exact ties yield `authoritative_candidate_tie`, while a newer ineligible candidate only emits its informational warning unless upstream supersession invalidates the old source. |
| AC-010-025 | Staleness uses date-only 12-calendar-month subtraction with day clamp, exact threshold comparison, all seven locked examples, server evaluation date, future-date rejection, and immutable historical result. |
| AC-010-026 | Archive allows reads only and yields `archived_case`; reopen restores nothing, and revalidate creates a complete draft only after upstream invalidation using current predecessor authority. |
| AC-010-027 | M06 eligibility is derived read-time from the complete locked truth table, stable exclusions/warnings, valid ILS confirmation, non-empty mapping, and disposed mandatory warnings, without downstream authority claims. |
| AC-010-028 | Strict client-scoped APIs accept intent only, resolve all authority/evidence server-side, and provide identical public behavior for foreign and missing identifiers. |
| AC-010-029 | Instance, bulk ORM, Core DML, alias where supported, cascade/parent delete, relationship mutation, predecessor/sequence/provenance/warning rewrites are blocked for all M05 structures while legitimate service inserts and unrelated-model DML remain valid. |
| AC-010-030 | Deterministic concurrency tests prove exactly one winner for start and same-leaf successor races, sequence/child/candidate/value uniqueness, simultaneous actions, current-leaf resolution, clean losers, and retry after conflict. |
| AC-010-031 | Frontend matrices cover candidate/detail/history/provenance/eligibility/every mutation/refresh across A→B, A→B→A, X→Y, unmount, success, rejection, structured error, `finally`, zero stale refresh, and current-revision ownership. |
| AC-010-032 | The additive migration parent is exactly `95222c79dce8`, uses explicit Numeric/composite FK/unique constraints, no backfill or predecessor mutation, one head, SQLite cycle, PostgreSQL offline upgrade/downgrade without query-result dependency, retry-safe tests, and bounded downgrade. |
| AC-010-033 | Full AC/NAC and prior-package regression evidence proves fail-closed corruption, no M01-M04 mutation, and absence of parsing, normalization, M06 execution, tax/fixation/liquidity, production-readiness, or parity expansion. |

Acceptance criteria count: `33`.

## 27. Negative acceptance criteria

| ID | Prohibited outcome |
|---|---|
| NAC-010-001 | Use or persistence of `compensation_component`. |
| NAC-010-002 | Double-counting capital/pension grouping, aliases, source plus adjusted value, or any evidence identity. |
| NAC-010-003 | Caller-authored trusted source, candidate/predecessor identity, mapping, provenance, actor/time, warnings, reconciliation, stale result, currency fact, or eligibility. |
| NAC-010-004 | Stored/caller M04 authority boolean replacing current accepted/resolved M04 and read-time eligibility revalidation. |
| NAC-010-005 | M02 superseding-candidate logic used as account precedence. |
| NAC-010-006 | Trimming, case folding, Unicode normalization, punctuation/whitespace change, transliteration, alias/provider-code mapping, fuzzy matching, or other provider/account normalization. |
| NAC-010-007 | Latest-created/updated, M02 timestamps, M04 acceptance time, or insertion order selecting authoritative candidate. |
| NAC-010-008 | Silent zero coercion or silent ILS inference from locale/provider/product/filename/package/target scope. |
| NAC-010-009 | Implicit rounding, excessive scale, unrepresentable exponent, binary float, NaN/infinity, formatted/comma/whitespace monetary string. |
| NAC-010-010 | Boolean, list, or object accepted as monetary input. |
| NAC-010-011 | Negative-value discard or canonical `0.00` treated as negative. |
| NAC-010-012 | Empty M04 component set, total-only reconciliation, or component/effective sum creating a missing source total. |
| NAC-010-013 | `_find_balance`, primary tagmul, tag priority, weighted fallback, period inference, or snapshot latest/meaningful selection. |
| NAC-010-014 | Raw/opaque source parsing, extraction, normalization, mutation, replacement, or deletion. |
| NAC-010-015 | Any in-place instance update/delete, bulk ORM DML, Core DML, cascade/parent delete, relationship mutation, pointer rollback, concealment, or rewrite of subject/revision/value/candidate/adjustment/provenance/warning history. |
| NAC-010-016 | Adjustment of source/identity/date/currency/upstream/classification/provenance fields, caller old value, batch adjustment, or simultaneous counting of source and effective values. |
| NAC-010-017 | Staleness alone treated as invalidity, mandatory review, or M06 exclusion. |
| NAC-010-018 | Restriction/warning/classification treated as tax, liquidity, withdrawal, conversion, or professional authority. |
| NAC-010-019 | Mutation while M01 is archived or automatic authority restoration after reopen. |
| NAC-010-020 | Foreign-client access, cross-client/subject/intake linkage, or foreign existence/count/value/provenance/timing leakage. |
| NAC-010-021 | Stale frontend success/rejection/error/loading/refresh/`finally` changing the currently selected client, subject, candidate, revision, or form state. |
| NAC-010-022 | M06 conversion/coefficient/execution, tax, exemption, fixation, 161D, liquidity, withdrawal, scenarios, recommendations, or reports. |
| NAC-010-023 | Multi-currency, implied currency, currency conversion, or any accepted value other than explicitly confirmed ILS. |
| NAC-010-024 | Production-readiness, V1/V2 parity, M05-complete beyond PKG-010, M06/M09-M14 authorization, 02M change, or next-package authorization claim. |

Negative acceptance criteria count: `24`.

## 28. Verification matrix

| Area | Required evidence | Criteria |
|---|---|---|
| Predecessor lifecycle | Exact M01 predicate, M02 `accepted_for_review`, current M03/M04 | AC-010-001-003; NAC-010-004, NAC-010-019 |
| Currency and account identity | Explicit ILS snapshot confirmation and exact byte identity | AC-010-004-006; NAC-010-006, NAC-010-008, NAC-010-023 |
| Mapping and money | One-to-one indexed mapping, states, scale-2 Decimal, canonical zero | AC-010-007-012; NAC-010-001-002, NAC-010-009-012 |
| Effective values and persistence | Separate values, normative structures, immutable leaf chain | AC-010-013-016; NAC-010-003, NAC-010-015-016 |
| Reconciliation | Effective formula, tolerance, non-empty complete components | AC-010-017-019; NAC-010-002, NAC-010-012-013 |
| Warning and adjustment | Stable exact warning set and single-identity adjustment | AC-010-020-023; NAC-010-011, NAC-010-016-018 |
| Precedence and stale date | Exact dates/tie/newer-ineligible and seven calendar examples | AC-010-024-025; NAC-010-005, NAC-010-007, NAC-010-017 |
| Archive and M06 | Explicit revalidation and complete fail-closed technical gate | AC-010-026-027; NAC-010-018-019, NAC-010-022-024 |
| API and immutability | Intent-only/non-leaking APIs and all DML/cascade enforcement paths | AC-010-028-029; NAC-010-003, NAC-010-014-015, NAC-010-020 |
| Concurrency and frontend | Exactly-one successor and complete async ownership matrices | AC-010-030-031; NAC-010-021 |
| Migration and regression | Offline-safe additive migration and all AC/NAC/prior regression | AC-010-032-033; NAC-010-014, NAC-010-022-024 |

No AC/NAC may be claimed without deterministic executable evidence. Browser
E2E, CI, deployment, and production verification may be claimed only if
actually available and executed.

## 29. Included, deferred, and excluded scope

Included:

- manual `manual_record_review` candidates only;
- exact M01/M02/M03/M04 predecessor revalidation;
- exact provider/account identity;
- source-snapshot-specific ILS confirmation;
- scale-2 Decimal/Numeric monetary values and canonical zero;
- strict indexed M02-M04-M05 component mapping;
- immutable source/derived/effective values;
- exact effective-value reconciliation;
- stable mandatory/informational warnings;
- calendar-month stale evidence;
- immutable lifecycle, adjustment, concurrency, and provenance;
- fail-closed M06 technical eligibility;
- bounded APIs/frontend ownership; and
- separately authorized additive migration evidence.

Deferred or excluded:

- optional undo and batch adjustment;
- provider/account normalization or master-code mapping;
- all uploaded-source parsing and XML/DAT/CSV/XLSX extraction;
- normalization, `_find_balance`, tag priority, weighted fallback,
  period inference, primary tagmul, and snapshot meaningful/latest selection;
- generic restriction metadata and blocked-balance downstream workflow;
- current-employer termination decisions;
- multi-currency and conversion;
- M06, coefficients, tax, exemption, fixation, formal 161D, liquidity,
  withdrawal, scenarios, recommendations, and reports;
- M09-M14 and `02M`;
- production-readiness and V1/V2 parity; and
- authorization of M06 or any next package.

## 30. Definition correction disposition

| Defect | Corrected contract | Status |
|---|---|---|
| `D-010-001` | Exact M01 derived mutation predicate and M02 `accepted_for_review` vocabulary | `CLOSED_IN_DEFINITION` |
| `D-010-002` | Explicit source-snapshot-specific server-controlled ILS confirmation | `CLOSED_IN_DEFINITION` |
| `D-010-003` | Exact persisted provider/account byte identity and manual target kind | `CLOSED_IN_DEFINITION` |
| `D-010-004` | Scale-2 Decimal/Numeric, reject-not-round, canonical zero | `CLOSED_IN_DEFINITION` |
| `D-010-005` | Total-only reconciliation removed; non-empty complete component mapping required | `CLOSED_IN_DEFINITION` |
| `D-010-006` | Deterministic indexed one-to-one M02-M04-M05 component mapping | `CLOSED_IN_DEFINITION` |
| `D-010-007` | Reconciliation uses exactly one current effective value per identity | `CLOSED_IN_DEFINITION` |
| `D-010-008` | Complete exact lifecycle matrix and concurrency rules | `CLOSED_IN_DEFINITION` |
| `D-010-009` | Stable mandatory/informational warning catalogue and exact-set disposition | `CLOSED_IN_DEFINITION` |
| `D-010-010` | Date-only calendar-month stale threshold and examples | `CLOSED_IN_DEFINITION` |
| `D-010-011` | Expanded enforcement, concurrency, offline migration, frontend, stop, and AC/NAC evidence | `CLOSED_IN_DEFINITION` |

## 31. Authorization boundary and final gate

- Definition: `CORRECTED_PROPOSED_FOR_ACCEPTANCE`
- Definition correction: `COMPLETED`
- Implementation: `NOT_AUTHORIZED`
- Migration creation/execution: `NOT_AUTHORIZED`
- M06: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`

No definition acceptance record is created. A separate audit gate must accept
or return this corrected definition before implementation authorization may be
considered.

`PKG_010_CORRECTED_DEFINITION_READY_FOR_REAUDIT`

This status is not `READY_FOR_IMPLEMENTATION`, authorizes no migration, and
does not open M06 or another package.
