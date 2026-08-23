# PKG-017 Final Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-017` |
| Title | `M10 Selected Scenario Adjustment Evidence Presentation Foundation` |
| Module | `M10` |
| Classification | `FRONTEND_PRESENTATION_ONLY` |
| Business authority | `NO_NEW_M10_BUSINESS_AUTHORITY` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Authoritative base | `16a404f4263771a2ec47d59c930f10cb4d85ad60` |
| Accepted PKG-016 implementation HEAD | `cc8fe1c169747e7da96e4f05ed78b996865018a1` |
| Current M10 authority | `COMPARATOR_ONLY` |
| Current Alembic head | `e6b4c8d2f507` |

This document proposes a narrow contextual presentation slice over already
accepted M09 evidence held by the accepted PKG-016 screen. It is not an
accepted definition, implementation authorization, backend/API authorization,
migration or persistence authorization, broader-M10 decision, professional
decision, production-readiness decision, or next-package authorization.

## 2. Authoritative Sources and Predecessor Boundaries

The controlling repository sources are:

- `specs/runtime/PKG_014_FINAL_PACKAGE_DEFINITION.md` and its accepted M09
  implementation;
- `specs/runtime/PKG_015_V2_FINAL_PACKAGE_DEFINITION.md` and its accepted
  stateless comparator implementation;
- `specs/runtime/PKG_016_FINAL_PACKAGE_DEFINITION.md` and its accepted frontend
  implementation;
- `specs/runtime/PKG_016_implementation_acceptance_record.md`; and
- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.

PKG-015 and PKG-016 are `CLOSED_ON_MASTER`. PKG-017 does not reopen, replace,
reinterpret, or extend either package. PKG-015 remains the sole comparator
owner, PKG-016 remains the accepted comparator presentation and invocation
owner, and current M10 business authority remains `COMPARATOR_ONLY`.

## 3. Exact Product Objective

PKG-017 presents the exact persisted adjustment evidence associated with the
currently selected eligible adjusted scenario inside the existing M10
comparison context.

The presentation lets a planner see which declared adjustment assumptions
belong to that one transiently selected adjusted scenario without leaving the
comparison screen. It is contextual presentation only. It does not calculate,
reinterpret, aggregate, compare, rank, recommend, approve, or persist anything.

Displaying a scenario's adjustment evidence does not elevate transient UI
selection into business selection authority.

## 4. Authority Model

Every material business calculation has exactly one authoritative owning
module or engine. PKG-017 owns zero business calculations.

- PKG-014/M09 owns subject identity, subject type, adjustment occurrence
  identity, manifest evidence, adjustment values, occurrence order,
  provenance, fingerprints, actor evidence, and timestamps.
- PKG-015/M10 owns pair admission, comparator arithmetic, deltas, relations,
  blocker precedence, response schema, and comparison fingerprinting.
- PKG-016 owns the accepted browser discovery, transient pair construction,
  comparator invocation/presentation, and generation/request isolation.
- PKG-017 may only render existing M09 adjustment facts for the current
  PKG-016 selection.

The browser is not a second calculation, provenance, fingerprint, selection,
or comparison authority.

## 5. Exact IN Scope

The bounded future implementation may add only:

- a meaningful planner-facing adjustment-evidence section within the existing
  client-scoped M10 comparison screen;
- binding of that section to the one currently selected eligible adjusted
  subject already held by PKG-016 discovery state;
- literal presentation of each accepted server-returned occurrence;
- a neutral evidence-unavailable state for malformed selected-subject evidence;
- immediate clearing on selection or client-generation change; and
- focused deterministic presentation and isolation tests.

The section is not a raw JSON dump or developer-debug panel. Fingerprints and
low-level metadata may support evidence identity but are not its primary
planner-facing purpose.

## 6. Exact OUT of Scope

PKG-017 excludes:

- any new business calculation or metric;
- totals, subtotals, aggregation, percentages, materiality, or impact;
- manifest comparison, assumption-delta semantics, or causal attribution;
- rank, score, preference, recommendation, approval, review, or suitability;
- saved selection, comparison persistence, history, supersession, or archive;
- adjusted-versus-adjusted or multi-scenario comparison;
- broader scenario-family support or compatibility logic;
- a new endpoint, response field, schema, backend service, or query;
- a database model, migration, or persistence lifecycle;
- a new M10 blocker, changed blocker precedence, or comparator change;
- M11/M12 handoff or any M11-M14 authority; and
- implementation, production readiness, or a next package during definition
  drafting.

## 7. Existing Authoritative Source and API Reuse

The only source is the existing client-scoped M09 subject response:

`GET /api/clients/{client_id}/m09/subjects`

The future frontend must reuse:

- `frontend/src/api/m09CashflowApi.ts`;
- `listM09Subjects(clientId)`;
- `M09ScenarioSubject.adjustments`;
- the exact `M09ScenarioSubject` already retained in each PKG-016 candidate;
  and
- `useClientContextGeneration` and existing PKG-016 discovery ownership.

No second subject fetch may be introduced solely for PKG-017 because the
accepted screen already holds the required server evidence. No new endpoint,
field, or API-client semantic surface is required.

## 8. Repository Evidence and Closed Source Contract

Repository inspection establishes:

- `listM09Subjects(clientId)` returns client-scoped `M09ScenarioSubject`
  objects;
- each response exposes `scenario_subject_id`, `client_id`, family/version,
  `subject_type`, manifest evidence, subject provenance, fingerprints, and
  `adjustments`;
- each adjustment exposes `adjustment_id`, `ordinal`, `adjustment_type`,
  `amount`, `start_month`, `end_month`, `provenance`,
  `semantic_fingerprint`, `actor`, and `created_at`;
- adjusted-subject creation rejects an empty adjustment list;
- accepted adjusted subjects therefore contain at least one valid positive
  adjustment occurrence;
- baseline creation is server-owned, contains zero adjustment rows, and carries
  exact provenance `server_resolved_no_scenario_adjustments`; and
- the service returns adjustment rows in ascending persisted `ordinal` order.

An adjusted subject with an empty runtime `adjustments` array is not an
accepted empty state. It is malformed or contradictory evidence and must fail
the presentation closed.

## 9. Family, Type, and Provenance Boundary

The only supported scenario contract is:

`declared_retirement_cashflow_adjustments/v1`

The only accepted adjustment types are:

- `declared_additional_monthly_income`; and
- `declared_additional_monthly_expense`.

The accepted adjustment provenance is exactly:

`planner_declared_scenario_adjustment`

The accepted baseline no-adjustment provenance is exactly:

`server_resolved_no_scenario_adjustments`

These values are displayable server evidence only. The browser must not derive,
alias, normalize, or infer any of them.

## 10. Selected-Scenario Binding

Adjustment evidence binds only to the exact selected candidate object whose
accepted `scenario_subject_id` and eligible/current run establish the current
PKG-016 transient selection. Identity must never be reconstructed from label,
amount, dates, fingerprint fragments, run order, or list position.

Selection remains request/UI state only. It does not mean preferred, reviewed,
approved, saved, selected-for-planning, recommended, or downstream-authorized.
If there is no current selected adjusted candidate, no selected-scenario
adjustment evidence is presented.

## 11. Required Planner-Facing Evidence

For every selected-scenario adjustment occurrence the primary presentation must
show at least:

- exact adjustment type, with a neutral one-to-one label;
- exact authoritative amount string;
- exact `start_month`;
- exact `end_month`;
- exact provenance; and
- enough exact occurrence identity/order evidence to preserve multiplicity,
  using `adjustment_id` and/or `ordinal` without inventing a user-facing
  aggregate identity.

The selected `scenario_subject_id` must remain visible or inspectable so the
evidence is tied to its authoritative subject.

`adjustment_manifest_fingerprint`, per-adjustment `semantic_fingerprint`,
`actor`, and `created_at` are optional secondary provenance metadata. They may
be displayed when useful for evidence identity, but they are not required as
the primary planner-facing content. Fingerprints are never computed or verified
in the browser.

## 12. Multiplicity and Ordering

Every server-returned adjustment is a distinct occurrence. Duplicate-looking
occurrences remain separate when their type, amount, and dates are equal. The
browser must not deduplicate, merge, group, collapse, total, or infer semantic
equivalence.

The presentation preserves the server-owned occurrence array order and exact
`ordinal`. It must not sort by amount, type, sign, duration, identity,
fingerprint, perceived importance, or any business criterion. Order conveys no
preference, rank, impact, or materiality.

Malformed, duplicate, missing, non-integer, or contradictory occurrence
identity/order evidence makes the selected subject's adjustment presentation
unavailable as a whole. The browser must not silently skip a row or repair
ordering, because doing so would change authoritative multiplicity.

## 13. Monetary Boundary

Adjustment `amount` remains the exact server-returned positive canonical Decimal
string in the accepted M09 domain `0.01` through
`999999999999999999.99`, with exactly two decimal places and no leading plus,
scientific notation, separators, whitespace, leading-zero variation, rounding,
or coercion.

The browser must not use `Number`, `parseFloat`, `parseInt`, arithmetic, totals,
subtotals, aggregation, rounding, percentages, normalization that changes the
value, or impact calculation. A display helper may only add reversible
string-based presentation while retaining the exact source string; verbatim is
the safe default.

## 14. Date and Range Boundary

`start_month` and `end_month` are presented as exact server evidence in the
accepted `YYYY-MM` representation. The browser must not calculate duration,
number of months, overlap, active-month count, effective monthly impact,
applicability, proration, or open-ended meaning. It must not attribute a
comparison result to a date range.

## 15. No Assumption-Delta or Causal Semantics

PKG-017 displays one selected adjusted subject's existing adjustment evidence.
It must not:

- compare baseline and adjusted manifests;
- compare two adjusted manifests;
- compute or describe assumption differences;
- declare one assumption set larger or smaller;
- create a semantic diff;
- correlate an adjustment with a comparator delta; or
- attribute any result, relation, or cashflow value to an occurrence.

Wording such as “caused,” “explains the delta,” “impact,” “contribution,” or
“effect on cash flow” is prohibited. No per-adjustment effect calculation or
causal evidence exists in the accepted source.

## 16. UI Neutrality and Useful Presentation

Permitted neutral labels include “Declared additional monthly income,”
“Declared additional monthly expense,” “Amount,” “Start month,” “End month,”
and “Provenance.”

The UI must avoid benefit, cost, improvement, worse, better, recommended,
important, material, optimal, favorable, unfavorable, or similar qualitative
language. The section should be readable by a planner and clearly contextual,
without elevating optional fingerprints, actor, or timestamp metadata above the
business-readable adjustment facts.

## 17. Comparator and PKG-016 Preservation

PKG-017 must not change:

- `POST /api/clients/{client_id}/m10/compare`;
- the comparator request body;
- pair admission;
- the comparison result schema;
- the closed blocker vocabulary or precedence;
- delta arithmetic or numeric relations;
- the comparison fingerprint; or
- PKG-016 discovery, baseline identification, candidate eligibility,
  transient selection, invocation, success rendering, blocker rendering,
  transport/API failure handling, generation isolation, or request ownership.

The new section is additive presentation. Existing PKG-016 regression tests
remain authoritative and must not be replaced or weakened.

## 18. Client, Generation, and Selection Isolation

All visible adjustment evidence must belong to the active route `clientId`, the
current monotonic client generation, and current discovery ownership. No prior
client or foreign-client subject identity may remain visible or actionable, and
no global M10 adjustment state may be introduced.

- On A→B, selected A adjustment evidence disappears immediately and cannot
  render in B.
- On A→B→A, A-old evidence cannot reappear in the new A generation, even though
  the client ID text is equal.
- On S1→S2, S1 rows disappear and only S2 evidence renders; no mixed rows are
  permitted.
- When selection is cleared, no previous selected-scenario evidence remains.
- If the selected subject no longer exists among the current generation's
  eligible candidates, selection and adjustment evidence disappear fail
  closed.

No new asynchronous operation is expected. Existing discovery generation and
ownership guards must protect presentation derived from the retained subject
objects. A delayed stale completion must never repopulate old evidence.

## 19. Fail-Closed Evidence and Outcome Classes

Before presenting a selected adjusted subject as authoritative adjustment
evidence, the frontend must deterministically establish the complete bounded
display shape: current subject identity/client/family/version/type, non-empty
adjustment array, exact allowed adjustment types, canonical amounts and months,
exact provenance, occurrence identities, ordinals, and required primitive
types.

If required material is malformed, null, missing, contradictory, unsupported,
or unavailable, the complete selected-subject adjustment list is withheld. The
UI may show a neutral “selected scenario adjustment evidence unavailable”
state. It must not fabricate a partial list, skip malformed occurrences,
default a field, or infer evidence from `adjustment_manifest`.

The UI must preserve four distinct outcome classes:

1. accepted comparator business blocker;
2. selected-scenario adjustment evidence unavailable or malformed;
3. transport/API or discovery failure; and
4. silently discarded stale state.

Adjustment-evidence failure is not pair-admission failure and must not create,
reuse, or masquerade as an M10 blocker code.

## 20. Baseline Evidence Boundary

Baseline adjustment context is optional. If shown, it may use only the exact
server-owned subject provenance
`server_resolved_no_scenario_adjustments` together with the accepted baseline
subject evidence. The browser must not infer “zero adjustments” merely from an
empty array, create a “no difference from baseline” statement, or compare the
baseline manifest with the adjusted manifest.

If authoritative baseline marker evidence is unavailable, omit the baseline
context or fail that optional context closed; do not synthesize it. Selected
adjusted evidence remains bound to its own accepted non-empty contract.

## 21. Expected Future Implementation Surfaces

Expected changes are limited to:

- `frontend/src/pages/M10ComparisonScreen.tsx`; and
- `frontend/src/pages/M10ComparisonScreen.test.tsx`.

A small dedicated presentational component and its focused test may be added
only if it improves clarity without creating an authority or API layer.

Expected API-client diff is `NONE`. A narrow type/import reuse change is allowed
only if technically unavoidable and semantically inert. Expected backend,
model, migration, database-query, persistence, comparator, routing, Build Plan,
definition, and acceptance-record diffs during implementation are `NONE`.

## 22. Definition-Level Verification Strategy

Future deterministic focused tests must prove:

- selected adjusted-subject occurrences render from retained M09 evidence;
- both exact adjustment types render with neutral one-to-one labels;
- canonical positive, trailing-zero, and beyond-safe-JS-integer amount strings
  remain exact strings;
- duplicate-looking occurrences render separately with distinct identity/order;
- server array order and exact ordinal are preserved;
- start/end month and provenance render literally;
- S1→S2 leaves only S2 evidence;
- clearing selection removes all selected-scenario evidence;
- A→B immediately removes A evidence;
- A→B→A rejects A-old evidence under the new generation;
- malformed type, amount, month, provenance, identity, ordinal, array, or
  selected-subject contract fails the whole evidence section closed;
- an empty adjusted-subject adjustment array fails closed;
- evidence unavailability creates no M10 blocker and remains distinct from
  comparator and transport states; and
- existing PKG-016 request, response validation, blockers, monetary rendering,
  and race tests remain green.

Future implementation must pass the existing frontend production build and
type-check without configuration weakening. No backend behavior change is
expected; repository diff proof is primary, and the PKG-015 comparator
regression must remain green if run.

## 23. Q-019 and Q-020 Exclusions

Unresolved Q-019 branches remain excluded: additional metrics, percentages,
materiality/significance, semantic assumption differences, causal attribution,
broader family compatibility, and partial-value substitution policy. Literal
planner-declared adjustment evidence does not resolve them.

Unresolved Q-020 branches remain excluded: simultaneous multi-scenario
comparison, adjusted-versus-adjusted comparison, review, preference, persisted
selection, comparison persistence, supersession, archive/history, M11 handoff,
and M12 handoff.

Broad M10 remains `BLOCKED_FOR_LOGIC_DETAIL`. M11-M14 remain
`NOT_AUTHORIZED`. M08E remains `EXCLUDED`, and `02M` remains `FROZEN`.

## 24. Stop Conditions

Future implementation must stop and report the exact applicable condition if
any becomes necessary. A stop condition does not authorize the named expansion.

1. `PKG_017_NEW_BUSINESS_CALCULATION_REQUIRED`
2. `PKG_017_ASSUMPTION_DELTA_SEMANTICS_REQUIRED`
3. `PKG_017_CAUSAL_ATTRIBUTION_REQUIRED`
4. `PKG_017_ADJUSTMENT_TOTAL_CALCULATION_REQUIRED`
5. `PKG_017_NEW_COMPARISON_METRIC_REQUIRED`
6. `PKG_017_PERCENTAGE_OR_MATERIALITY_REQUIRED`
7. `PKG_017_BACKEND_API_EXPANSION_REQUIRED`
8. `PKG_017_PERSISTENCE_OR_HISTORY_REQUIRED`
9. `PKG_017_SELECTION_OR_RECOMMENDATION_AUTHORITY_REQUIRED`
10. `PKG_017_M11_OR_M12_HANDOFF_REQUIRED`
11. `PKG_017_CLIENT_ISOLATION_EVIDENCE_UNAVAILABLE`
12. `PKG_017_ADJUSTMENT_PROVENANCE_UNAVAILABLE`
13. `PKG_017_BASELINE_EVIDENCE_UNAVAILABLE`
14. `PKG_017_MULTIPLICITY_PRESERVATION_UNAVAILABLE`
15. `PKG_017_NEW_PROFESSIONAL_DECISION_REQUIRED`
16. `PKG_017_SELECTED_SUBJECT_BINDING_UNAVAILABLE`
17. `PKG_017_MALFORMED_EVIDENCE_FAIL_CLOSED_UNAVAILABLE`

## 25. Acceptance Criteria

- **AC-017-001:** Package identity and title are exact; classification is `FRONTEND_PRESENTATION_ONLY`, business authority is `NO_NEW_M10_BUSINESS_AUTHORITY`, definition is `PROPOSED_FOR_ACCEPTANCE`, and implementation is `NOT_AUTHORIZED`.
- **AC-017-002:** The authoritative base is exact, PKG-015 and PKG-016 remain `CLOSED_ON_MASTER`, and accepted PKG-016 implementation HEAD is preserved.
- **AC-017-003:** The exact objective is contextual presentation of persisted adjustment evidence for the currently selected eligible adjusted scenario, with zero new business calculation or authority.
- **AC-017-004:** Future scope is frontend presentation only and is expected to touch only the existing M10 screen and its tests unless a small authority-free presentational component is justified.
- **AC-017-005:** Existing `listM09Subjects(clientId)`, retained `M09ScenarioSubject.adjustments`, and `useClientContextGeneration` are reused with no second subject fetch.
- **AC-017-006:** Only `declared_retirement_cashflow_adjustments/v1` is supported, with no alias, fallback, or broader-family compatibility.
- **AC-017-007:** Evidence binds by exact authoritative `scenario_subject_id` to the current PKG-016 selected eligible adjusted candidate, never by label, values, position, or fingerprint fragments.
- **AC-017-008:** Selection remains transient request/UI state and creates no preference, review, approval, recommendation, saved selection, planning selection, or downstream authority.
- **AC-017-009:** The accepted adjusted-subject contract is non-empty; a runtime adjusted subject with zero adjustment occurrences fails presentation closed.
- **AC-017-010:** Only `declared_additional_monthly_income` and `declared_additional_monthly_expense` are recognized and rendered one-to-one.
- **AC-017-011:** Every occurrence presents exact type, amount, start month, end month, provenance, and enough exact identity/order evidence to preserve multiplicity.
- **AC-017-012:** Amount remains the exact canonical positive Decimal string in the accepted M09 domain, including trailing zeros and values beyond safe JS integer precision.
- **AC-017-013:** Start and end months are literal server evidence; no duration, overlap, applicability, proration, or active-month calculation exists.
- **AC-017-014:** Adjustment provenance is exactly `planner_declared_scenario_adjustment` and is never browser-derived.
- **AC-017-015:** Selected evidence remains tied to exact adjustment and subject occurrence identities without an invented aggregate identity.
- **AC-017-016:** Separately returned duplicate-looking adjustments remain separately visible occurrences without deduplication, grouping, merging, totaling, or equivalence inference.
- **AC-017-017:** Server array order and exact ordinal are preserved without business sorting or preference meaning.
- **AC-017-018:** Fingerprints, actor, and `created_at` are optional secondary provenance metadata; fingerprints are never browser-computed or verified.
- **AC-017-019:** Presentation is meaningful and planner-facing rather than raw JSON or a developer metadata dump, and wording remains neutral.
- **AC-017-020:** No Number conversion, arithmetic, total, subtotal, aggregation, rounding, percentage, impact, or materiality calculation occurs.
- **AC-017-021:** No assumption-manifest comparison, semantic diff, larger/smaller assumption claim, or assumption-delta semantics exists.
- **AC-017-022:** No adjustment is described as causing, explaining, contributing to, or affecting a comparator result or cashflow value.
- **AC-017-023:** PKG-015 remains sole comparator owner and its endpoint, request, admission, result, blocker, arithmetic, relation, and fingerprint contracts are unchanged.
- **AC-017-024:** All accepted PKG-016 discovery, selection, invocation, presentation, error, and isolation behavior is additive-preserved without replacement or weakening.
- **AC-017-025:** All adjustment evidence is current-client, current-generation, and current-discovery-owned, with no foreign or prior-client evidence or global M10 state.
- **AC-017-026:** A→B immediately removes A selected-scenario evidence and prevents it from rendering or remaining actionable in B.
- **AC-017-027:** A→B→A deterministic evidence proves A-old adjustment evidence cannot reappear in the new A generation.
- **AC-017-028:** S1→S2 immediately removes S1 evidence and renders only S2 occurrences without mixed rows or stale repopulation.
- **AC-017-029:** Clearing selection or losing the selected subject from current eligible candidates removes all previous selected-scenario adjustment evidence.
- **AC-017-030:** Malformed, missing, null, contradictory, unsupported, empty-adjusted, or wrong-primitive evidence withholds the whole adjustment list without fabrication or silently skipped occurrences.
- **AC-017-031:** Adjustment evidence unavailable, comparator blocker, transport/API failure, and stale discard remain four distinct observable outcome classes.
- **AC-017-032:** Adjustment presentation creates no new M10 blocker code, reuses no blocker as an evidence-display error, and changes no blocker precedence.
- **AC-017-033:** Optional baseline context uses only exact `server_resolved_no_scenario_adjustments` server evidence and never infers baseline emptiness or difference semantics from an array.
- **AC-017-034:** No new endpoint, response field, schema, backend service, database query, API semantic surface, or second subject fetch is introduced.
- **AC-017-035:** No model, migration, persistence, history, review lifecycle, or saved state is introduced.
- **AC-017-036:** Future deterministic tests cover literal evidence, both types, amount boundaries, multiplicity, ordering, selection changes, clearing, client races, malformed evidence, and outcome separation.
- **AC-017-037:** Existing PKG-016 comparator request, response validation, blocker, monetary rendering, race tests, full frontend tests, type-check, and production build remain passing without config weakening.
- **AC-017-038:** PKG-015 and PKG-016 accepted artifacts and behavior remain unchanged; implementation backend/API/migration/persistence diffs are `NONE`.
- **AC-017-039:** Q-019 and Q-020 exclusions, broad-M10 blocked status, M11-M14 unauthorized status, M08E exclusion, and `02M` freeze remain explicit.
- **AC-017-040:** Definition drafting changes only this definition and narrow proposal-stage Build Plan state, authorizes no implementation or next package, and makes no production-readiness claim.

## 26. Negative Acceptance Criteria

- **NAC-017-001:** Per-adjustment, selected-scenario, monthly, range, or manifest total or subtotal.
- **NAC-017-002:** Arithmetic, summation, subtraction, multiplication, division, aggregation, or numeric comparison over adjustment evidence.
- **NAC-017-003:** `Number`, float/integer parsing, rounding, coercion, scientific reformatting, or semantic alteration of amount strings.
- **NAC-017-004:** Percentage, materiality, significance, threshold, or impact calculation or label.
- **NAC-017-005:** Causal attribution, contribution, explanation-of-delta, or effect-on-cashflow language or logic.
- **NAC-017-006:** Baseline-versus-adjusted or adjusted-versus-adjusted manifest diff, semantic diff, or assumption-delta comparison.
- **NAC-017-007:** Deduplication or suppression of separately returned duplicate-looking adjustment occurrences.
- **NAC-017-008:** Merging, grouping, collapsing, or synthesizing adjustment occurrences or an aggregate occurrence identity.
- **NAC-017-009:** Business sorting by amount, type, sign, duration, importance, impact, fingerprint, or preference.
- **NAC-017-010:** Browser-generated or inferred adjustment provenance, baseline marker, subject identity, adjustment identity, or ordinal.
- **NAC-017-011:** Browser-generated, recalculated, repaired, or verified adjustment or manifest fingerprint.
- **NAC-017-012:** Inferring authoritative baseline no-adjustment meaning solely from an empty adjustment array.
- **NAC-017-013:** Partial rendering, defaulting, row skipping, zero-fill, or fabrication after malformed required evidence.
- **NAC-017-014:** New M10 business blocker vocabulary or use of an existing comparator blocker for presentation failure.
- **NAC-017-015:** Suppression, combination, reordering, severity invention, or frontend precedence for comparator blockers.
- **NAC-017-016:** New backend endpoint, validation route, or subject-detail fetch created for PKG-017.
- **NAC-017-017:** New response field, API schema expansion, compatibility alias, fallback, or broader scenario family.
- **NAC-017-018:** A second `listM09Subjects` call or another fetch solely to obtain already-retained selected-subject evidence.
- **NAC-017-019:** New backend service, database query, model, table, migration, or persistence.
- **NAC-017-020:** Preferred, reviewed, approved, saved, recommended, selected-for-planning, or downstream-authorized scenario meaning.
- **NAC-017-021:** Ranking, scoring, optimization, suitability, favorable/unfavorable, better/worse, or professional advice.
- **NAC-017-022:** Saved selection, browser storage, URL persistence, comparison persistence, history, supersession, archive, or review lifecycle.
- **NAC-017-023:** Simultaneous multi-scenario, adjusted-versus-adjusted, baseline-versus-baseline, or generic dashboard expansion.
- **NAC-017-024:** M11/M12 handoff, eligibility, readiness, or any M11-M14 authority.
- **NAC-017-025:** Resolution or authorization of an excluded Q-019 or Q-020 branch.
- **NAC-017-026:** Change to comparator endpoint/body, pair admission, response schema, delta, relation, fingerprint, blocker contract, or PKG-016 ownership.
- **NAC-017-027:** Cross-client, prior-generation, A-old, S1-old, or no-longer-selected adjustment evidence remaining visible or actionable.
- **NAC-017-028:** Frontend/backend implementation, test implementation, migration, persistence, acceptance record, master merge, next package, or production-readiness claim during definition drafting.

## 27. Definition-Task File Boundary

This definition task may change exactly:

- `specs/runtime/PKG_017_FINAL_PACKAGE_DEFINITION.md`; and
- narrow proposal-stage PKG-017 state in
  `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.

No code, test, migration, persistence, API, acceptance record, PKG-015 artifact,
or PKG-016 artifact may change. Implementation remains `NOT_AUTHORIZED`.

## 28. Governance State After Draft

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017 definition: `DRAFTED_PENDING_WORK_DEFINITION_AUDIT`
- PKG-017 implementation: `NOT_AUTHORIZED`
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11-M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`
- Next package beyond PKG-017: `NOT_AUTHORIZED`
- Production readiness: `NOT_CLAIMED`

The only next gate is independent WORK definition audit. Acceptance,
implementation, master merge, downstream work, and production readiness require
separate explicit authorization.

PKG_017_DEFINITION_PROPOSED_FOR_ACCEPTANCE
