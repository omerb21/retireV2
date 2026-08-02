# PKG-010 — M05 Manual Pension Balance Ledger and Exact Reconciliation Foundation

## 1. Identity and status

| Field | Value |
|---|---|
| Package | `PKG-010 — M05 Manual Pension Balance Ledger and Exact Reconciliation Foundation` |
| Module | `M05` |
| Definition status | `DEFINITION_PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Migration creation/execution | `NOT_AUTHORIZED` |
| M06 | `NOT_AUTHORIZED` |
| Acceptance record | `NOT_CREATED` |
| Authoritative base | `1d336485f4dd7c187894dd8670f40dba73a36df9` |
| Predecessor implementation | PKG-009 at `ae73a7706214b137b7452b9f66c483ee5b57009c` |
| Predecessor migration | `95222c79dce8` |

This document defines a bounded M05 package. It does not authorize source-code
changes, migration creation or execution, M06 work, or implementation
acceptance.

## 2. Authoritative sources

The authoritative sources for this package are:

1. `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`;
2. `specs/runtime/PKG_009_FINAL_PACKAGE_DEFINITION.md`;
3. `specs/runtime/PKG_009_definition_acceptance_record.md`;
4. `specs/runtime/PKG_009_acceptance_record.md`;
5. the accepted M01-M04 repository contracts at the authoritative base; and
6. the product and architecture decisions locked in this definition.

Implementation details not fixed here may follow repository conventions only
when every contract below remains unchanged. They may not introduce a
professional, tax, pension, conversion, liquidity, or source-authority rule.

## 3. Predecessor contracts

PKG-010 consumes M01-M04 as read-only predecessor authorities. It preserves:

- M01 client ownership, active/archive lifecycle, and client isolation;
- M02 manual-intake identity, lifecycle, persisted declared metadata, and
  supersession ownership;
- M03 immutable review history, current accepted-review identity, decision
  timestamp, and derived downstream eligibility;
- M04 immutable classification history, current accepted/resolved authority,
  component evidence identities, and read-time M05 eligibility;
- same-client validation and foreign-ID non-disclosure;
- append-only history and server-controlled provenance; and
- the accepted frontend client-generation and request-ownership boundary.

M05 never mutates M01, M02, M03, or M04. Upstream invalidation changes derived
authority and eligibility without rewriting ledger history.

## 4. Exact product outcome

PKG-010 creates a bounded, immutable, client-scoped ledger and exact
reconciliation foundation for M02 manual pension records only. It separates
immutable source values, derived reconciliation values, and explicitly
adjusted effective ledger values.

The package may establish narrow, derived technical eligibility for a
separately authorized M06 package. It does not implement M06, conversion,
coefficients, tax, exemption, fixation, formal 161D, liquidity, withdrawal,
pension commencement, scenarios, recommendations, or reports.

## 5. Authoritative candidate and target contract

An authoritative candidate must satisfy all of the following at evaluation
time:

1. the M01 client is active;
2. the M02 intake is manual and accepted;
3. M03 has a current accepted authority;
4. M04 has a current accepted and resolved classification;
5. M04 read-time eligibility for M05 is true;
6. provider is present;
7. declared account reference is present;
8. statement date is present;
9. total balance is present;
10. every monetary value declares `currency = ILS`;
11. monetary values are exact finite Decimal values; and
12. required provenance is complete and internally consistent.

Uploaded opaque sources are not authoritative sources of M05 monetary values.
No filename, MIME type, checksum, path, blob metadata, XML, DAT, CSV, XLSX, or
other opaque content may be interpreted by this package.

## 6. Monetary component and interpretation vocabulary

The monetary component vocabulary is exactly:

- `contribution_component`;
- `severance_component`; and
- `unknown_component`.

`contribution_component` represents תגמולים. The term
`compensation_component` is prohibited.

`capital` and `pension` remain M04 classification interpretations or derived
grouping views. They are not additional monetary components. A grouping view
may not be added to the same reconciliation sum as its underlying component.

## 7. Monetary-value states and Decimal boundary

Every source monetary field has exactly one explicit state:

- `recorded_value` — a present, finite, non-zero Decimal value;
- `recorded_zero` — an explicitly recorded finite Decimal zero;
- `missing` — no source value was recorded;
- `excluded` — a source value exists but is explicitly outside the bounded
  reconciliation input; or
- `malformed` — the supplied representation is not an accepted monetary value.

`missing`, `malformed`, and `excluded` never become zero silently. Monetary
values use exact finite Decimal semantics. The boundary rejects Boolean,
list/object, NaN, positive or negative infinity, unapproved formatted-string
coercion, and implied currency.

Source, derived, and adjusted/effective values remain separately identified
and reader-visible. A derived or adjusted value never replaces the immutable
source value.

## 8. Currency contract

PKG-010 is ILS-only. Every monetary value carries explicit
`currency = ILS`. A missing, different, ambiguous, or inferred currency fails
the applicable candidate/reconciliation/eligibility check closed with
`currency_or_unit_invalid`. Multi-currency reconciliation and conversion are
outside this package.

## 9. Ledger subject and candidate identity

A server-generated ledger subject belongs to one client and one exact logical
account identity. Logical account identity requires exact:

- provider identity; and
- declared account reference.

There is no fuzzy matching, normalization-based inference, provider/account
guessing, or use of `manual_technical_reference` as account identity. Multiple
statements may link to one subject only through an explicit, server-validated
candidate linkage that proves exact account identity and same-client scope.

Each immutable server-resolved candidate identity contains:

- client ID;
- M02 intake ID;
- target kind;
- current accepted M03 revision ID; and
- current accepted M04 revision ID.

The caller cannot author trusted predecessor identities. Duplicate candidate
tuples are prohibited.

## 10. Authoritative-current precedence

Within one proven ledger subject, authoritative-current precedence is:

1. latest statement date; then
2. latest current accepted M03 `decided_at`.

Equal statement date and equal accepted M03 timestamp produce
`authoritative_candidate_tie`. A tie is not resolved by insertion order or any
other timestamp.

The following are never precedence inputs:

- M02 created or updated time;
- M04 acceptance time;
- latest-created or latest-updated order;
- M02 superseding-candidate logic; or
- fuzzy provider/account matching.

A newer ineligible candidate does not replace an older eligible candidate.
The authoritative result exposes `newer_ineligible_candidate_exists` as a
warning unless upstream supersession explicitly invalidates the older source.
That warning is not an exclusion by itself.

## 11. Normative persistence and integrity model

The implementation must provide bounded structures semantically equivalent to:

1. a ledger subject;
2. an immutable ledger revision;
3. revision-owned ledger values/components;
4. immutable candidate links; and
5. additive adjustment evidence.

Exact table and column names remain implementation-level, but these structures
and invariants are normative:

- stable server-generated identities;
- explicit client ownership;
- client-scoped composite integrity;
- one exact subject/account identity;
- unique revision sequence per subject;
- at most one child per predecessor;
- unique immutable candidate identity;
- unique value/evidence identity per revision;
- same-client, same-subject, and same-account constraints;
- deterministic current leaf;
- append-only revisions, candidate links, values, and adjustments;
- fail-closed corruption detection;
- no mutation of M02-M04; and
- no inferred or professional backfill.

## 12. Ledger states and immutable current leaf

Persisted ledger revision states are exactly:

- `draft`;
- `reconciled`;
- `warning_reviewed`;
- `blocked`; and
- `superseded`.

The current revision is the unique valid leaf of one immutable linear chain.
No prior revision, value row, candidate link, adjustment, warning evidence, or
provenance snapshot may be updated or deleted. Every accepted state-changing
action creates exactly one successor revision.

## 13. Lifecycle and transition contract

### 13.1 Start

No existing ledger chain → new `draft`. The server resolves and captures the
candidate identity, immutable source values, current M03/M04 authority, account
identity, statement date, currency, component expectations, evaluation date,
and provenance snapshot.

### 13.2 Reconcile

Current `draft` → new `reconciled`. This is allowed only when:

- all upstream authority remains current;
- required values exist and are valid;
- there is no unresolved authoritative-candidate tie;
- the expected component set is complete;
- no required warning remains unreviewed; and
- `abs(discrepancy) <= 0.50 ILS`.

### 13.3 Review warning

Warning-bearing current `draft` → new `warning_reviewed`. The action requires
exact warning IDs, reason code, explanation, explicit confirmation, and a
server-owned actor and timestamp. The successor retains the exact warning and
value snapshot. Reviewing a warning does not change source facts or infer its
professional meaning.

### 13.4 Mark blocked

Current non-`superseded` revision → new `blocked`. The action requires a stable
reason code, explanation, current-revision intent, and retained evidence.

### 13.5 Adjust

Current non-`superseded` revision → successor `draft`. Only effective monetary
values may change. Adjustment evidence contains field/component identity,
previous effective value, new effective value, currency, reason, explanation,
explicit confirmation, server actor/timestamp, predecessor, and source
provenance.

### 13.6 Supersede

Current revision → new `superseded`. Supersession is additive and performs no
deletion.

### 13.7 Revalidate

An upstream-invalidated current revision → successor `draft` using current
server-resolved M03/M04 authority and a new evidence snapshot. It does not edit
or restore prior authority.

### 13.8 Optional additive undo

If an undo action is exposed, it creates a successor `draft` based on a valid
same-subject historical revision. It requires current-revision intent, the
historical revision ID, reason, explanation, and explicit confirmation. It is
never pointer rollback and never mutates history. This definition does not
require an undo endpoint for package acceptance.

## 14. Exact reconciliation contract

The normative formula is:

`discrepancy = total_balance - sum(explicitly included reconcilable source components exactly once)`

All operations use exact Decimal arithmetic. The authoritative component sum
may include only `contribution_component` and `severance_component`.

The sum excludes monthly pension, capital grouping, pension grouping,
`unknown_component`, primary tagmul, duplicated aliases, missing or malformed
values, inferred periods, and adjusted source provenance counted a second
time. Every evidence identity participates at most once.

Each decision snapshot persists:

- signed discrepancy;
- absolute discrepancy;
- included component evidence identities;
- excluded component evidence identities and reasons; and
- reconciliation algorithm version.

The tolerance boundary is exact:

- `abs(discrepancy) <= 0.50 ILS` satisfies reconciliation tolerance; and
- `abs(discrepancy) > 0.50 ILS` creates a warning requiring structured review.

Neither total nor components are corrected silently.

## 15. Expected component completeness

The accepted M04 snapshot determines the expected monetary component evidence
identities. The ledger distinguishes:

- no component expected;
- component expected and recorded zero;
- component expected and value present;
- component expected but missing;
- malformed; and
- excluded.

If no reconcilable components are expected, total-only reconciliation may use
a component sum of exact zero only with persisted evidence
`no_reconcilable_components_expected`. If a required component is expected but
missing or malformed, the revision cannot become `reconciled`.

## 16. Negative-value warning contract

Signed source and effective values are preserved exactly. Any negative total
or component creates `negative_value_review_required`. Such a draft cannot
become `reconciled`. It may become `warning_reviewed` only through the
structured warning-review action.

The package does not infer debt, reversal, correction, invalidity, tax meaning,
or withdrawal meaning from a negative sign.

## 17. Stale-warning contract

The server owns `evaluation_date`. A statement is stale only when it is older
than 12 full calendar months at that date. Exactly 12 calendar months is not
stale. The evaluation date and result are persisted in the decision snapshot;
historical revisions are not reinterpreted using the current clock.

`stale_warning` alone does not block authority, does not require
`warning_reviewed`, and does not block M06 technical eligibility.

## 18. Adjustment boundary

Source values remain immutable and visible. Adjustments affect effective
ledger values only and force a new `draft` requiring reconciliation again.

An adjustment may not change provider, account, product, statement date,
currency, M02/M03/M04 identities, source values, classification, actor,
timestamp, sequence, provenance, or a prior reconciliation result. An
adjustment cannot create an authoritative total when the source total is
`missing`, `malformed`, or `excluded`.

## 19. Derived M06 technical eligibility

M06 technical eligibility is derived read-time, server-controlled, and
fail-closed. It is true only when:

1. M01 is active;
2. the current ledger chain is structurally and semantically valid;
3. exactly one authoritative candidate exists;
4. M02 is current, manual, and accepted;
5. M03 is current, accepted, and eligible;
6. M04 is current, accepted, resolved, and eligible for M05;
7. current ledger state is `reconciled` or `warning_reviewed`;
8. provider, account, statement date, and source total exist;
9. every monetary value is finite Decimal in explicit ILS;
10. provenance is complete;
11. expected component completeness is satisfied;
12. no authoritative-candidate tie or supersession exists;
13. no corruption exists; and
14. no mandatory warning remains unresolved.

Stable exclusion reasons include:

- `archived_case`;
- `no_authoritative_candidate`;
- `authoritative_candidate_tie`;
- `upstream_source_ineligible`;
- `m03_ineligible`;
- `m04_ineligible`;
- `upstream_revalidation_required`;
- `ledger_draft`;
- `ledger_blocked`;
- `ledger_superseded`;
- `required_value_missing`;
- `component_set_incomplete`;
- `reconciliation_unresolved`;
- `warning_not_reviewed`;
- `negative_value_review_required`;
- `provenance_invalid`;
- `ledger_chain_inconsistent`; and
- `currency_or_unit_invalid`.

`newer_ineligible_candidate_exists` is a warning, not an exclusion by itself.

Eligibility does not establish conversion validity, coefficient availability,
tax treatment, exemption, fixation, liquidity, withdrawal availability,
pension commencement, or report readiness. It does not authorize M06.

## 20. Archived-case behavior

For an archived M01 case, ledger detail, immutable history, provenance,
warnings, and eligibility explanation remain readable. Start, reconcile,
warning review, block, adjust, supersede, revalidate, and optional undo are
rejected. M06 eligibility is false with `archived_case`.

Reopening M01 changes no ledger history and restores no authority
automatically. Explicit revalidation against current M03/M04 authority is
required before any new authoritative ledger state may be created.

## 21. Backend and API boundary

The bounded client-scoped API may provide:

- list eligible candidates and retained subjects;
- get current ledger;
- get immutable ledger history;
- get complete provenance;
- start;
- reconcile;
- review warning;
- mark blocked;
- adjust;
- supersede;
- revalidate;
- optional additive undo; and
- get technical M06 eligibility.

Mutation schemas are strict and accept intent fields only. The server owns
client ownership, candidate identity, upstream revision identities, source
values, actor, timestamp, sequence, current leaf, provenance, reconciliation,
stale evaluation/result, and eligibility. Caller-supplied trusted forms of
those fields are rejected or ignored only where the strict schema explicitly
provides no such field.

All reads and mutations are client-scoped. Missing and foreign resources use
the same non-leaking public response and reveal no foreign identity, count,
provenance, monetary value, lifecycle, or timing information.

## 22. Frontend and async-ownership contract

The planner-facing workflow displays separately:

- source value;
- derived value;
- adjusted/effective value;
- component evidence identity;
- included/excluded reconciliation status;
- signed and absolute discrepancy;
- warnings and their review evidence;
- authoritative-candidate precedence and tie state;
- stale warning and evaluation date;
- immutable history;
- adjustment evidence; and
- M06 technical eligibility and reasons.

Every async ownership unit binds client ID, monotonic route generation,
per-request epoch, subject/candidate identity, and current revision identity.
Deterministic acceptance evidence must cover A→B, A→B→A, same-client subject
X→Y, unmount, success, rejected promise, structured error, and `finally` for
reads and state-changing actions. A stale mutation launches zero refreshes. A
current mutation completes its authoritative detail/history/provenance/
eligibility/list refresh without being cleared by stale `finally` handling.

## 23. Migration boundary

A separately authorized implementation may create one additive Alembic
revision above `95222c79dce8`. It must:

- add only the bounded PKG-010 structures and integrity constraints;
- preserve all predecessor rows and migration history;
- perform no M01-M04 mutation or backfill;
- perform no monetary, account, component, or professional inference;
- leave one Alembic head;
- pass SQLite upgrade/downgrade/re-upgrade verification;
- remain compatible with PostgreSQL DDL; and
- remove only PKG-010 objects on downgrade.

This definition does not assign a migration revision ID and does not authorize
migration creation or execution.

## 24. Stop conditions

Future implementation must stop and return to the approval gate if:

| Stop code | Condition |
|---|---|
| `M05_MANUAL_CANDIDATE_CONTRACT_BLOCKED` | An authoritative candidate cannot remain limited to accepted manual M02 intake with current M03/M04 authority. |
| `M05_EXACT_ACCOUNT_IDENTITY_BLOCKED` | Subject linkage would require fuzzy, inferred, or technical-reference account identity. |
| `M05_MONETARY_STATE_COLLAPSE_REQUIRED` | Missing, excluded, malformed, recorded zero, and recorded value cannot remain distinct. |
| `M05_DECIMAL_OR_CURRENCY_INTEGRITY_BLOCKED` | Exact finite Decimal and explicit ILS enforcement cannot be guaranteed. |
| `M05_COMPONENT_DOUBLE_COUNT_REQUIRED` | Reconciliation would count a component/evidence identity or grouping more than once. |
| `M05_RECONCILIATION_CONTRACT_VIOLATION` | The exact formula, component boundary, completeness rules, or 0.50 ILS tolerance cannot be preserved. |
| `M05_CANDIDATE_PRECEDENCE_BLOCKED` | Exact statement-date/M03-decision precedence and deterministic tie behavior cannot be enforced. |
| `M05_WARNING_CONTRACT_BLOCKED` | Negative, discrepancy, stale, or newer-ineligible warnings would gain unsupported meaning or lose required evidence. |
| `M05_REVISION_IMMUTABILITY_BLOCKED` | Append-only chain, one-child predecessor, immutable values, or additive adjustment cannot be enforced. |
| `M05_UPSTREAM_MUTATION_REQUIRED` | Implementation requires mutation of M01-M04 data, lifecycle, evidence, classification, or authority. |
| `M05_CALLER_FORGED_AUTHORITY_BLOCKED` | Caller control of source facts, predecessor authority, provenance, reconciliation, actor, timestamp, or eligibility cannot be prevented. |
| `M05_CLIENT_ISOLATION_BLOCKED` | Same-client subject, candidate, revision, value, and provenance integrity cannot be enforced. |
| `M05_FOREIGN_ID_LEAKAGE_BLOCKED` | Foreign and missing identifiers cannot use indistinguishable public behavior. |
| `M05_MIGRATION_INTEGRITY_BLOCKED` | An additive single-head migration above `95222c79dce8` cannot preserve predecessor data. |
| `PARSER_OR_NORMALIZATION_SCOPE_REQUIRED` | Parsing, extraction, normalization, `_find_balance`, or other uploaded-source interpretation is required. |
| `M06_SCOPE_REQUIRED` | Conversion, coefficients, or any M06 execution/authority is required. |
| `PRIOR_PACKAGE_REGRESSION_BLOCKED` | Accepted M01-M04 or PKG-001 through PKG-009 behavior cannot be preserved. |

Stop-condition count: `17`.

## 25. Acceptance criteria

| ID | Acceptance criterion |
|---|---|
| AC-010-001 | Candidate listing and ledger creation admit only same-client M02 manual records; uploaded opaque sources cannot supply authoritative monetary values. |
| AC-010-002 | Every authoritative candidate operation revalidates active M01, accepted/current M02, current accepted M03 authority, current accepted/resolved M04 authority, and M04 read-time M05 eligibility. |
| AC-010-003 | Provider, declared account reference, statement date, source total, explicit ILS, finite Decimal values, and complete provenance are required before a candidate can become authoritative. |
| AC-010-004 | Uploaded filenames, MIME, checksums, paths, blobs, XML, DAT, CSV, XLSX, and other opaque content never create M05 monetary authority. |
| AC-010-005 | The server creates one client-scoped ledger subject only for an exact provider identity plus declared account reference; `manual_technical_reference` is never account identity. |
| AC-010-006 | Candidate identity is server-resolved from client, M02 intake, target kind, current accepted M03 revision, and current accepted M04 revision, and duplicate tuples are rejected. |
| AC-010-007 | Multiple statements link to one subject only through explicit, server-validated, same-client exact-account linkage; fuzzy or inferred linkage is impossible. |
| AC-010-008 | Monetary components use only `contribution_component`, `severance_component`, and `unknown_component`; `compensation_component` is rejected and capital/pension grouping is not a component. |
| AC-010-009 | Every monetary field distinguishes `recorded_value`, `recorded_zero`, `missing`, `excluded`, and `malformed`, and readers retain that distinction. |
| AC-010-010 | Boolean, list/object, NaN, infinity, unapproved formatted strings, and implied currency fail validation and never become Decimal zero or authority. |
| AC-010-011 | Every monetary value is an exact finite Decimal with explicit `currency = ILS`; non-ILS or ambiguous units fail closed. |
| AC-010-012 | Source, derived, and adjusted/effective values are persisted and displayed separately; source values remain immutable and visible. |
| AC-010-013 | Persistence provides the five normative semantic structures, stable server IDs, same-client/account constraints, unique sequences/candidates/values, one-child predecessors, and a deterministic leaf. |
| AC-010-014 | Start, reconcile, warning review, block, adjust, supersede, and revalidate each append exactly one valid successor and never update/delete prior history. |
| AC-010-015 | Start from no chain creates one `draft` with a server-resolved candidate and complete decision-time source/upstream/provenance snapshot. |
| AC-010-016 | Reconcile uses exact Decimal `total_balance - sum(included reconcilable source components exactly once)` and succeeds only with current authority, complete values/components, no tie, no mandatory unreviewed warning, and tolerance satisfied. |
| AC-010-017 | Deterministic tests prove discrepancy boundaries `0`, `0.01`, `0.49`, and `0.50` ILS satisfy tolerance while `0.51` ILS creates a review-required warning. |
| AC-010-018 | Only contribution and severance evidence identities enter the authoritative sum, each at most once; unknown/grouping/alias/monthly/inferred/duplicated values are excluded with evidence. |
| AC-010-019 | When M04 proves no reconcilable component is expected, total-only reconciliation uses exact zero component sum and persists `no_reconcilable_components_expected`. |
| AC-010-020 | An expected required component that is missing or malformed prevents `reconciled` and yields stable completeness/value evidence. |
| AC-010-021 | Negative source or effective total/component values remain signed, create `negative_value_review_required`, cannot become `reconciled`, and gain no inferred business meaning. |
| AC-010-022 | Warning review appends `warning_reviewed` only from a warning-bearing draft and immutably retains exact warning IDs, reason, explanation, confirmation, server actor/time, and warning/value snapshot. |
| AC-010-023 | Adjust appends a new `draft`, changes effective monetary values only, retains previous/new/source/provenance evidence, cannot create a missing source total, and forces reconciliation again. |
| AC-010-024 | Within one subject, authoritative precedence uses latest statement date then latest accepted M03 `decided_at`; equal values produce `authoritative_candidate_tie`. |
| AC-010-025 | A newer ineligible candidate leaves an older eligible candidate authoritative and exposes `newer_ineligible_candidate_exists` unless upstream supersession invalidates the older source. |
| AC-010-026 | Server-controlled staleness uses more than 12 full calendar months; exactly 12 months is not stale, and evaluation date/result are snapshot-persisted without historical reinterpretation. |
| AC-010-027 | Archive permits reads only and makes M06 eligibility false; reopen changes no history/authority and requires explicit revalidation against current M03/M04. |
| AC-010-028 | Structural or semantic corruption of chain, candidate, values, reconciliation, warnings, or provenance makes authoritative reads and M06 eligibility fail closed without history mutation. |
| AC-010-029 | M06 eligibility is derived read-time from the complete locked truth table, uses stable exclusions/warnings, and makes no M06, conversion, tax, liquidity, or readiness claim. |
| AC-010-030 | Strict client-scoped APIs expose bounded reads/actions, accept intent fields only, resolve authority server-side, and return indistinguishable public behavior for foreign and missing IDs. |
| AC-010-031 | Frontend tests cover A→B, A→B→A, same-client X→Y, unmount, success, rejection, structured error, `finally`, zero stale-mutation refresh, and current post-mutation refresh for every async ownership unit. |
| AC-010-032 | An additive migration above `95222c79dce8` creates only bounded M05 structures, performs no backfill, preserves predecessor data, leaves one head, and passes SQLite/PostgreSQL verification. |
| AC-010-033 | Full regression and integrity tests prove M01-M04 tables, source values, lifecycle, review, classification, authority, and history are never mutated by M05 actions or migration. |

Acceptance criteria count: `33`.

## 26. Negative acceptance criteria

| ID | Prohibited outcome |
|---|---|
| NAC-010-001 | Use or persistence of `compensation_component`. |
| NAC-010-002 | Counting capital/pension grouping views or aliases in addition to their underlying monetary components. |
| NAC-010-003 | Caller-authored trusted source facts, candidate/predecessor identity, provenance, authority, actor, timestamp, reconciliation, stale result, or eligibility. |
| NAC-010-004 | Stored or caller-controlled M04 authority/eligibility boolean replacing current M04 read-time revalidation. |
| NAC-010-005 | M02 superseding-candidate logic used as ledger account precedence. |
| NAC-010-006 | Fuzzy, normalized, partial, guessed, or inferred provider/account matching. |
| NAC-010-007 | Latest-created, latest-updated, M02 timestamp, or M04 acceptance timestamp selecting the authoritative candidate. |
| NAC-010-008 | Silent coercion of missing, malformed, or excluded monetary values to zero. |
| NAC-010-009 | Acceptance of NaN, infinity, non-finite Decimal, or unapproved formatted monetary coercion. |
| NAC-010-010 | Boolean, list, or object accepted as monetary input. |
| NAC-010-011 | Dropping a negative sign or inferring debt, reversal, correction, or invalidity from it. |
| NAC-010-012 | Component sum, derived value, or adjustment creating/replacing a missing authoritative source total. |
| NAC-010-013 | `_find_balance`, primary tagmul, tag priority, weighted fallback, period inference, or snapshot latest/meaningful selection. |
| NAC-010-014 | Mutation, replacement, deletion, parsing, extraction, or normalization of raw or opaque source evidence. |
| NAC-010-015 | In-place update/delete, pointer rollback, or concealment of ledger subject, revision, value, candidate, warning, adjustment, or provenance history. |
| NAC-010-016 | Adjustment of provider, account, product, statement date, currency, upstream IDs, source value, classification, actor, timestamp, sequence, or prior reconciliation result. |
| NAC-010-017 | Staleness alone treated as invalidity, mandatory warning review, or M06 ineligibility. |
| NAC-010-018 | Restriction or warning metadata treated as tax, liquidity, withdrawal, conversion, or professional authority. |
| NAC-010-019 | Any M05 mutation while M01 is archived or automatic authority restoration after reopen. |
| NAC-010-020 | Foreign-client access, cross-client/cross-subject linkage, or foreign-ID existence/count/value/provenance leakage. |
| NAC-010-021 | A stale frontend response, rejection, API error, loading state, mutation refresh, or `finally` changing the active client/subject/revision context. |
| NAC-010-022 | M06 conversion, coefficient, downstream execution, tax, exemption, fixation, 161D, liquidity, withdrawal, scenario, recommendation, or report implementation. |
| NAC-010-023 | Multi-currency reconciliation, implied currency, or currency conversion. |
| NAC-010-024 | Production-readiness, V1/V2 parity, M05-complete beyond this package, M06 authorization, M09-M14 authorization, 02M change, or next-package authorization claim. |

Negative acceptance criteria count: `24`.

## 27. Verification matrix

| Verification area | Required proof | Criteria |
|---|---|---|
| Manual candidate and authority | Manual-only candidates, all predecessor gates, opaque upload exclusion | AC-010-001-004; NAC-010-003-005, NAC-010-014 |
| Identity and precedence | Exact subject/linkage, immutable candidate tuple, deterministic dates/tie/newer-ineligible warning | AC-010-005-007, AC-010-024-025; NAC-010-005-007 |
| Vocabulary and values | Bounded components, five value states, Decimal/ILS, source-derived-effective separation | AC-010-008-012; NAC-010-001-002, NAC-010-008-010, NAC-010-023 |
| Persistence and lifecycle | Normative structures, immutable chain, all required transitions | AC-010-013-015, AC-010-022-023; NAC-010-003, NAC-010-015-016 |
| Reconciliation | Exact formula, boundary matrix, uniqueness, zero-expected and missing-required behavior | AC-010-016-020; NAC-010-002, NAC-010-012-013 |
| Warnings | Negative-value and calendar-stale behavior with immutable evidence | AC-010-021-022, AC-010-026; NAC-010-011, NAC-010-017-018 |
| Archive and integrity | Read-only archive/reopen, corruption fail-closed | AC-010-027-028; NAC-010-015, NAC-010-019 |
| M06 boundary | Complete technical eligibility truth table and non-authority meaning | AC-010-029; NAC-010-018, NAC-010-022, NAC-010-024 |
| API and isolation | Strict intent schemas, server authority, same-client persistence, non-leakage | AC-010-030; NAC-010-003-004, NAC-010-020 |
| Frontend async | Route/request/subject/revision ownership and full stale-settlement matrix | AC-010-031; NAC-010-021 |
| Migration and regression | Additive single-head migration and no M01-M04 mutation | AC-010-032-033; NAC-010-014-015, NAC-010-022-024 |

Browser E2E, CI, deployment, and production verification may be claimed only
if separately available and actually executed.

## 28. Included, deferred, and explicitly excluded scope

Included:

- manual M02 candidate discovery and exact account linkage;
- immutable ledger subjects, revisions, values, candidates, and adjustments;
- source/derived/effective value separation;
- exact ILS Decimal reconciliation;
- component completeness and evidence-identity uniqueness;
- candidate precedence and tie handling;
- discrepancy, negative-value, stale, and newer-ineligible warnings;
- immutable lifecycle and provenance;
- derived M06 technical eligibility;
- bounded client-scoped API and planner workflow;
- async ownership and client isolation; and
- an additive migration only after separate implementation authorization.

Deferred:

- optional additive undo if not selected for the separately authorized
  implementation;
- authentication/role expansion;
- production retention/redaction policy;
- broader account-identity master data;
- additional currencies and conversion; and
- M06 and later modules.

Explicitly excluded:

- all uploaded-source parsing;
- XML/DAT/CSV/XLSX extraction;
- normalization;
- `_find_balance`;
- tag priority or weighted fallback;
- component-period inference;
- primary tagmul formulas;
- snapshot latest/meaningful selection;
- generic restriction metadata;
- blocked-balance downstream workflow;
- current-employer termination decisions;
- multi-currency;
- M06 conversion and coefficients;
- tax, exemption, fixation, formal 161D, liquidity, withdrawal, scenarios,
  recommendations, and reports;
- M09-M14 and `02M`;
- production-readiness and V1/V2 parity claims; and
- authorization of M06 or any next package.

## 29. Authorization boundary and final gate

This definition authorizes no implementation activity.

- Definition: `DEFINITION_PROPOSED_FOR_ACCEPTANCE`
- Implementation: `NOT_AUTHORIZED`
- Migration creation/execution: `NOT_AUTHORIZED`
- M06: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`

No acceptance record is created. A separate gate must accept or return this
definition before implementation authorization may be considered.

`PKG_010_DEFINITION_READY_FOR_ACCEPTANCE_AUDIT`

This final status means only that the definition is ready for acceptance
audit. It is not `READY_FOR_IMPLEMENTATION`, does not authorize migration
creation/execution, and does not open M06 or another package.
