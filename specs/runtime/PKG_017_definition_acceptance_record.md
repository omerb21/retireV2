# PKG-017 Definition Acceptance Record

## 1. Record Identity

| Field | Value |
|---|---|
| Package | `PKG-017` |
| Title | `M10 Selected Scenario Adjustment Evidence Presentation Foundation` |
| Acceptance type | `Definition Acceptance` |
| Final decision | `ACCEPT_PKG_017_DEFINITION` |
| Professional decision | `NO_OMER_PROFESSIONAL_DECISION_REQUIRED` |
| Findings | `NO_FINDING` |
| Classification | `FRONTEND_PRESENTATION_ONLY` |
| Business authority | `NO_NEW_M10_BUSINESS_AUTHORITY` |
| Definition status | `ACCEPTED` |
| Implementation | `NOT_AUTHORIZED` |
| Base master | `16a404f4263771a2ec47d59c930f10cb4d85ad60` |
| Accepted definition HEAD | `c1039ba8e1bc1a214a3f21a135c99186411ff2ec` |
| Definition acceptance-record evidence HEAD | the documentation-only commit containing this record |
| Alembic head | `e6b4c8d2f507` |

## 2. Immutable Accepted Definition Boundary

The immutable accepted PKG-017 definition HEAD is exactly:

`c1039ba8e1bc1a214a3f21a135c99186411ff2ec`

Its exact parent is base master
`16a404f4263771a2ec47d59c930f10cb4d85ad60`. The accepted definition consists
of exactly one commit above that base:

`c1039ba8e1bc1a214a3f21a135c99186411ff2ec` —
`docs: define PKG-017 selected scenario adjustment evidence`

The definition history contains zero merge commits. The documentation-only
commit containing this acceptance record is later evidence only. It does not
replace, extend, amend, recreate, or redefine the immutable accepted definition
HEAD and is not part of the accepted definition candidate.

## 3. Accepted Audit Decision

Independent WORK audit recorded exactly:

- Decision: `ACCEPT_PKG_017_DEFINITION`.
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`.
- Findings: `NO_FINDING`.

The definition is accepted. Implementation remains `NOT_AUTHORIZED`.

## 4. Accepted Definition Integrity Anchors

The immutable blobs at accepted definition HEAD
`c1039ba8e1bc1a214a3f21a135c99186411ff2ec` are:

| Accepted artifact | Blob SHA |
|---|---|
| `specs/runtime/PKG_017_FINAL_PACKAGE_DEFINITION.md` | `f6e5da9d4c54b902da6dec7e11f6502f92b1dd32` |
| `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md` | `26bef42aead24ed32e8ce9b136dd43242bbeefaa` |

No other file belongs to the accepted definition candidate. Future integrity
checks must resolve these anchors at the accepted definition HEAD, not at the
acceptance-record evidence HEAD.

## 5. Accepted Objective and Authority Boundary

The accepted objective is literal presentation of persisted adjustment
occurrences belonging to the currently selected eligible adjusted scenario
inside the existing M10 comparison context.

The package creates no recalculation, reinterpretation, aggregation, assumption
comparison, causal attribution, ranking, recommendation, persistence, or
downstream selection authority. It owns no business calculation and grants no
implementation authority.

## 6. Existing Authoritative Source and Reuse

The sole source is the existing client-scoped endpoint:

`GET /api/clients/{client_id}/m09/subjects`

Future implementation must reuse:

- `frontend/src/api/m09CashflowApi.ts`;
- `listM09Subjects(clientId)`;
- the complete retained `M09ScenarioSubject`;
- `M09ScenarioSubject.adjustments`;
- `Candidate.subject` in the accepted PKG-016 screen; and
- `useClientContextGeneration` and existing discovery ownership.

No new API, endpoint, response field, subject-detail request, second subject
fetch, or new request-owner channel is accepted by this definition.

## 7. Scenario-Family Boundary

The only accepted scenario family/version is:

`declared_retirement_cashflow_adjustments/v1`

There is no alias, fallback, negotiation, reinterpretation, or broader family
support.

## 8. Authoritative Adjustment Schema

Every adjustment occurrence in the existing API response has these required,
non-null fields:

1. `adjustment_id`
2. `ordinal`
3. `adjustment_type`
4. `amount`
5. `start_month`
6. `end_month`
7. `provenance`
8. `semantic_fingerprint`
9. `actor`
10. `created_at`

`semantic_fingerprint`, `actor`, and `created_at` are optional for primary
planner-facing display only. They are not optional in the API contract or in
bounded fail-closed validation of required response evidence.

## 9. Accepted Adjustment Types and Provenance

The only accepted adjustment types are:

- `declared_additional_monthly_income`; and
- `declared_additional_monthly_expense`.

There are no aliases and no sign-derived type inference.

The exact server-owned adjustment provenance is:

`planner_declared_scenario_adjustment`

The exact server-owned baseline no-adjustment marker is:

`server_resolved_no_scenario_adjustments`

The browser may display these values but may not derive, synthesize, normalize,
or reinterpret them.

## 10. Selected-Scenario Binding and Transient Semantics

Evidence binds only to:

- the current selected eligible adjusted candidate;
- its exact authoritative `scenario_subject_id`;
- the current route client; and
- the current monotonic generation and discovery ownership.

Identity must not be reconstructed from labels, values, dates, list position,
or fingerprint fragments.

Selection remains transient UI/request state only. It creates no preferred,
reviewed, approved, saved, selected-for-planning, M11-ready, M12-ready,
recommended, or downstream-authorized scenario meaning.

## 11. Literal Planner-Facing Evidence

Primary allowed presentation for every occurrence is:

- `adjustment_type`;
- exact `amount` string;
- exact `start_month`;
- exact `end_month`;
- exact `provenance`; and
- sufficient occurrence identity/order evidence through `adjustment_id` and/or
  `ordinal`.

`semantic_fingerprint`, `actor`, and `created_at` may appear only as secondary
optional presentation metadata. Fingerprints are not the product purpose and
must never be computed or verified in the browser.

The UI must be useful and planner-facing, not a raw JSON dump or developer
debug panel. Wording remains neutral and creates no qualitative interpretation.

## 12. Multiplicity and Ordering

Every server-returned occurrence remains distinct. Duplicate-looking rows stay
separate even when type, amount, and dates are equal. The browser must not
deduplicate, merge, group, collapse, synthesize, suppress, or total occurrences.

Server array order and persisted `ordinal` are authoritative evidence. The
browser preserves them exactly and performs no sorting or reconciliation. An
inconsistency fails the entire selected-subject presentation closed. There is
no business ordering by amount, type, sign, duration, importance, materiality,
or perceived impact.

## 13. Monetary Boundary

The exact accepted amount domain is:

`0.01` through `999999999999999999.99`

Each amount is canonical two-decimal string evidence. The browser performs no
`Number`, `parseFloat`, `parseInt`, arithmetic, total, subtotal, aggregation,
rounding, percentage, normalization that changes authority, or impact
calculation. The original server string remains authoritative, including
trailing zeros and values beyond safe JS integer precision.

## 14. Date and Range Boundary

`start_month` and `end_month` are required non-null server strings in exact
`YYYY-MM` form. The accepted contract is not nullable or open-ended.

The browser does not calculate duration, overlap, active-month count,
applicability, proration, effective impact, or any derived range meaning.

## 15. Empty Adjusted Subject and Baseline Evidence

An accepted adjusted scenario subject must contain at least one adjustment. An
empty adjusted runtime array is malformed evidence and fails presentation
closed. It must not be described as the same as baseline, no material
difference, or zero impact.

Optional baseline context may use only exact server evidence
`server_resolved_no_scenario_adjustments`. An empty array alone does not
establish baseline business meaning. The browser must not compare baseline and
adjusted manifests.

## 16. Assumption-Delta and Causal-Attribution Exclusions

The accepted definition prohibits:

- manifest comparison;
- semantic assumption diff;
- larger/smaller assumption claims;
- baseline-versus-adjusted assumption comparison;
- adjusted-versus-adjusted assumption comparison;
- per-adjustment difference; and
- attribution language or logic such as “caused,” “impact,” “contribution,”
  “explains the delta,” or “effect on cash flow.”

There is no per-adjustment effect or causal semantics in PKG-017.

## 17. Comparator and Predecessor Preservation

PKG-015 remains the sole comparator business-calculation, pair-admission,
arithmetic, relation, blocker-precedence, response-schema, and comparison-
fingerprint owner.

PKG-016 remains the accepted comparator frontend presentation and invocation
owner. PKG-017 does not change:

- the comparator endpoint;
- request body;
- pair admission;
- response schema;
- blocker vocabulary or precedence;
- delta arithmetic;
- numeric relations;
- comparison fingerprints; or
- accepted PKG-016 discovery, invocation, rendering, error, generation, or
  request-ownership behavior.

PKG-015 and PKG-016 remain `CLOSED_ON_MASTER` and are not reopened.

## 18. Client, Generation, and Selection Isolation

All adjustment evidence is route-client scoped and requires current `clientId`,
current monotonic generation, and existing discovery ownership. No prior-client
evidence, foreign-client existence leakage, or global M10 state is accepted.

- A→B removes A evidence immediately and stale A evidence cannot render in B.
- A→B→A prevents A-old evidence from appearing in the A-new generation.
- S1→S2 leaves only S2 evidence, with no mixed S1/S2 rows.
- Clearing selection removes all selected-scenario evidence.
- Invalidating or removing the candidate from current eligible candidates makes
  its evidence disappear fail closed.

PKG-017 introduces no asynchronous request. It reuses subject objects already
obtained by accepted PKG-016 discovery. No second fetch and no new request-owner
channel are needed or accepted.

## 19. Fail-Closed Evidence and Outcome Separation

Malformed, missing, null, unsupported, contradictory, or empty-adjusted
evidence causes the entire authoritative adjustment list to be withheld. The UI
may present a neutral evidence-unavailable state but must not create partial
rows, default values, fabricated evidence, or silently skip a malformed
occurrence.

The following outcome classes remain distinct:

1. comparator business blocker;
2. selected-scenario adjustment evidence unavailable or malformed;
3. transport/API failure; and
4. stale discarded state.

No new M10 blocker is created, and no existing comparator blocker is reused or
reinterpreted as an adjustment-presentation failure.

## 20. Runtime-Validation Boundary

The existing generic M09 frontend API client does not provide complete runtime
response validation. The accepted definition therefore requires bounded local
fail-closed validation of the adjustment evidence needed for presentation.

This future validation may live within the presentation surface. It does not
require or authorize backend expansion, an API schema change, a new API request,
generic API-client semantic expansion, or new business authority. This record
does not imply that the future implementation already exists.

## 21. Expected Future Implementation Surfaces

Expected future scope is limited to:

- `frontend/src/pages/M10ComparisonScreen.tsx`; and
- `frontend/src/pages/M10ComparisonScreen.test.tsx`.

A small dedicated presentational component and focused test may be added only
when narrowly justified. Expected future evidence is:

- `BACKEND_DIFF = NONE`;
- `API_EXPANSION = NONE`;
- `MIGRATION_DIFF = NONE`; and
- `PERSISTENCE_DIFF = NONE`.

Implementation remains `NOT_AUTHORIZED`.

## 22. Architecture Invariant

Every material business calculation has exactly one authoritative owner:

- M09 owns scenario-subject and adjustment evidence;
- PKG-015 owns comparator admission and arithmetic;
- PKG-016 owns accepted frontend comparator presentation and invocation; and
- PKG-017 owns literal presentation only and zero business calculations.

## 23. Q-019 and Q-020 Preservation

Excluded Q-019 branches remain:

- new metrics;
- percentages;
- materiality/significance;
- semantic assumption differences;
- causal attribution;
- broader family compatibility; and
- partial-value substitution.

Excluded Q-020 branches remain:

- multi-scenario and adjusted-versus-adjusted comparison;
- review and preference;
- persisted selection;
- comparison persistence/history;
- supersession/archive; and
- M11 or M12 handoff.

The accepted definition resolves or authorizes none of these branches.

## 24. Acceptance-Criteria Evidence

- Exact range: `AC-017-001` through `AC-017-040`.
- Count: `40`.
- Result: `40 PASS / 0 FAIL / 0 AMBIGUOUS`.
- Gaps: `NONE`.
- Duplicates: `NONE`.

## 25. Negative-Acceptance-Criteria Evidence

- Exact range: `NAC-017-001` through `NAC-017-028`.
- Count: `28`.
- Result: `28 PASS / 0 FAIL / 0 AMBIGUOUS`.
- Gaps: `NONE`.
- Duplicates: `NONE`.

## 26. Accepted Stop-Condition Evidence

All 17 exact conditions are `NOT_FIRED`:

1. `PKG_017_NEW_BUSINESS_CALCULATION_REQUIRED` — `NOT_FIRED`
2. `PKG_017_ASSUMPTION_DELTA_SEMANTICS_REQUIRED` — `NOT_FIRED`
3. `PKG_017_CAUSAL_ATTRIBUTION_REQUIRED` — `NOT_FIRED`
4. `PKG_017_ADJUSTMENT_TOTAL_CALCULATION_REQUIRED` — `NOT_FIRED`
5. `PKG_017_NEW_COMPARISON_METRIC_REQUIRED` — `NOT_FIRED`
6. `PKG_017_PERCENTAGE_OR_MATERIALITY_REQUIRED` — `NOT_FIRED`
7. `PKG_017_BACKEND_API_EXPANSION_REQUIRED` — `NOT_FIRED`
8. `PKG_017_PERSISTENCE_OR_HISTORY_REQUIRED` — `NOT_FIRED`
9. `PKG_017_SELECTION_OR_RECOMMENDATION_AUTHORITY_REQUIRED` — `NOT_FIRED`
10. `PKG_017_M11_OR_M12_HANDOFF_REQUIRED` — `NOT_FIRED`
11. `PKG_017_CLIENT_ISOLATION_EVIDENCE_UNAVAILABLE` — `NOT_FIRED`
12. `PKG_017_ADJUSTMENT_PROVENANCE_UNAVAILABLE` — `NOT_FIRED`
13. `PKG_017_BASELINE_EVIDENCE_UNAVAILABLE` — `NOT_FIRED`
14. `PKG_017_MULTIPLICITY_PRESERVATION_UNAVAILABLE` — `NOT_FIRED`
15. `PKG_017_NEW_PROFESSIONAL_DECISION_REQUIRED` — `NOT_FIRED`
16. `PKG_017_SELECTED_SUBJECT_BINDING_UNAVAILABLE` — `NOT_FIRED`
17. `PKG_017_MALFORMED_EVIDENCE_FAIL_CLOSED_UNAVAILABLE` — `NOT_FIRED`

These conditions remain fail-closed boundaries and grant no authority to
perform the named expansion.

## 27. Accepted Future Test Strategy

Future deterministic implementation evidence is expected to cover:

- both accepted adjustment types;
- exact Decimal strings, trailing zeros, and values beyond JS safe integer;
- separate duplicate-looking occurrences;
- server array order and persisted ordinal;
- literal dates and provenance;
- S1→S2 and selection clearing;
- A→B and A→B→A generation isolation;
- malformed evidence fail-closed behavior;
- empty-adjusted evidence rejection;
- outcome-class separation and no new blocker;
- preservation of comparator regressions;
- the full frontend suite; and
- production build/type-check without config weakening.

This is accepted definition-level future evidence only. No test or
implementation work is authorized by this record.

## 28. Accepted Definition Scope Preservation

The accepted definition candidate changed only:

- `specs/runtime/PKG_017_FINAL_PACKAGE_DEFINITION.md`; and
- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.

This acceptance-record evidence commit changes only:

`specs/runtime/PKG_017_definition_acceptance_record.md`

It does not change the accepted definition, accepted Build Plan blob, any
PKG-015 or PKG-016 artifact, frontend, backend, tests, migration, persistence,
API behavior, or master.

## 29. Broad Governance State

- PKG-015: `CLOSED_ON_MASTER`.
- PKG-016: `CLOSED_ON_MASTER`.
- PKG-017 definition: `ACCEPTED_PENDING_DEFINITION_RECORD_AUDIT`.
- Accepted definition HEAD:
  `c1039ba8e1bc1a214a3f21a135c99186411ff2ec`.
- Definition acceptance-record evidence HEAD: the documentation-only commit
  containing this record; evidence only, not the accepted definition HEAD.
- PKG-017 implementation: `NOT_AUTHORIZED`.
- Master merge: `NOT_AUTHORIZED`.
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`.
- M11-M14: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Next package beyond PKG-017: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This record authorizes no implementation, frontend/backend code, tests,
migration, persistence, API expansion, broad M10 work, M11-M14 work, master
merge, production claim, or next package.

PKG_017_DEFINITION_ACCEPTED
