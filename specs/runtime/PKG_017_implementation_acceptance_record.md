# PKG-017 Implementation Acceptance Record

## Record Identity

- Package: `PKG-017`
- Title: `M10 Selected Scenario Adjustment Evidence Presentation Foundation`
- Acceptance type: `Implementation Acceptance`
- Audit decision: `ACCEPT_PKG_017_IMPLEMENTATION`
- Findings: `NO_NEW_FINDING`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`
- Classification: `FRONTEND_PRESENTATION_ONLY`
- Business authority: `NO_NEW_M10_BUSINESS_AUTHORITY`
- Definition status: `CLOSED_ON_MASTER`
- Implementation status: `ACCEPTED`
- Implementation base / current master: `15dc9a10663e95d7fe364c95fece2adaf1ecc470`
- Accepted definition HEAD: `c1039ba8e1bc1a214a3f21a135c99186411ff2ec`
- Accepted implementation HEAD: `5280a1063e16af99df99eb836f724aeea0031ff3`
- Historical rejected implementation candidate: `9cfaa654927e9b8616559951e05a266e5a5c5dac`
- Implementation acceptance-record evidence HEAD: the documentation-only commit containing this record
- Alembic head: `e6b4c8d2f507`

The immutable accepted implementation boundary is exactly
`5280a1063e16af99df99eb836f724aeea0031ff3`. The later documentation-only
commit containing this record is evidence only and does not replace, extend,
or redefine that implementation boundary.

## Audit Decision, Findings, and Defects

- Decision: `ACCEPT_PKG_017_IMPLEMENTATION`
- Findings: `NO_NEW_FINDING`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`
- `D-017-I001`: `CLOSED`
- `D-017-I002`: `CLOSED`

## Exact Accepted Implementation History

The accepted history is the following four-commit linear chain above base
`15dc9a10663e95d7fe364c95fece2adaf1ecc470`:

1. `4086af59042f888933093d611f0f5dc86997012e` — `feat: add PKG-017 selected scenario adjustment evidence`
2. `9cfaa654927e9b8616559951e05a266e5a5c5dac` — `test: prove PKG-017 evidence presentation boundaries`
3. `e622d4004d1434c4f63e9fdf2f515bce0ee2f339` — `fix: remove PKG-017 comparator state mutation`
4. `5280a1063e16af99df99eb836f724aeea0031ff3` — `test: prove PKG-017 presentation-only correction`

The candidate through commit 2 was rejected. Commits 3 and 4 close the two
identified defects. The complete accepted history contains zero merge commits
and no rewrite. The acceptance-record commit is not an implementation commit.

## Historical Rejected Candidate

`9cfaa654927e9b8616559951e05a266e5a5c5dac` is exactly:

`HISTORICAL_REJECTED_IMPLEMENTATION_CANDIDATE`

It is not an accepted implementation, a superseded accepted implementation, a
prior accepted boundary, or the current implementation boundary. Its defects
`D-017-I001` and `D-017-I002` are both `CLOSED` in the accepted implementation.

## Accepted Implementation Scope and Integrity Anchors

The accepted candidate changes exactly:

- `frontend/src/pages/M10ComparisonScreen.tsx`
- `frontend/src/pages/M10ComparisonScreen.test.tsx`

No other implementation file belongs to the accepted candidate. Before this
acceptance-record commit:

- `BACKEND_DIFF = NONE`
- `API_CLIENT_DIFF = NONE`
- `API_EXPANSION = NONE`
- `MIGRATION_DIFF = NONE`
- `PERSISTENCE_DIFF = NONE`
- `DOCS_DIFF = NONE`

The immutable accepted blobs at implementation HEAD are:

| Accepted path | Blob SHA |
|---|---|
| `frontend/src/pages/M10ComparisonScreen.tsx` | `12c1673ef5d515088519e3c8613c87d37253753d` |
| `frontend/src/pages/M10ComparisonScreen.test.tsx` | `f6dabeef6bf065372ba55909a453540cf40160fd` |

## Core Accepted Behavior

The currently selected eligible adjusted scenario displays literal persisted
adjustment evidence from the already-loaded M09 scenario subject. Primary
displayed evidence includes `adjustment_type`, `amount`, `start_month`,
`end_month`, `provenance`, `adjustment_id`, `ordinal`, and
`scenario_subject_id`. No derived business result is created.

## Selected-Subject Binding

Evidence binds to the current selected adjusted run, exact `Candidate.subject`,
authoritative `scenario_subject_id`, matching run `scenario_subject_id`, current
route client, current generation, accepted family/version, adjusted subject
type, run currentness, and M10 eligibility. Identity is never reconstructed
from display label, value, date, list position, or fingerprint fragment.

## Existing Source Reuse and Async Boundary

The implementation reuses:

- `GET /api/clients/{client_id}/m09/subjects`
- `listM09Subjects(clientId)`
- `M09ScenarioSubject.adjustments`
- `Candidate.subject`
- `useClientContextGeneration`

There is no second subject fetch, additional endpoint, subject-detail request,
async effect, new request owner, or comparator request transition. PKG-017 is
validation and rendering over already-loaded evidence only.

## Bounded Runtime Validation

Local fail-closed validation covers, as applicable:

- scenario-subject and client identity;
- accepted scenario family/version and adjusted subject type;
- required manifest evidence and fingerprints;
- actor, `actor_is_authentication`, and `created_at`;
- a non-empty adjusted occurrence list;
- run currentness and M10 eligibility;
- occurrence identity and unique adjustment IDs;
- contiguous ordinal/order integrity;
- accepted adjustment type;
- canonical amount and months;
- exact provenance; and
- required occurrence evidence.

No generic API validation framework or business-admissibility authority was
created.

## Adjustment-Type, Monetary, Month, and Provenance Boundaries

The only accepted adjustment types are:

- `declared_additional_monthly_income`
- `declared_additional_monthly_expense`

There is no alias or sign inference. Amount is exact canonical string evidence
from `0.01` through `999999999999999999.99`. Values beyond JavaScript safe
integer precision remain literal strings. Adjustment monetary evidence uses no
`Number`, `parseFloat`, `parseInt`, `BigInt` arithmetic, `Math` processing,
totals, subtotals, rounding, percentages, value-changing normalization, or
impact calculation.

`start_month` and `end_month` remain literal canonical `YYYY-MM` evidence.
Structural validation includes `end_month >= start_month`; there is no duration,
month-count, overlap, applicability, proration, or derived effective-range
calculation.

Accepted adjustment provenance is exactly
`planner_declared_scenario_adjustment`, without browser synthesis or inferred
replacement. Baseline handling remains unchanged.

## Multiplicity and Ordering

Every server-returned occurrence remains separate. Duplicate-looking
occurrences remain distinct. There is no deduplication, grouping, merging,
collapse, synthetic occurrence, aggregation, or total. Unique adjustment IDs
remain an integrity requirement.

Server array order and the contiguous persisted ordinal sequence are
authoritative. There is no browser sorting, resequencing, repair, or
reconciliation. An ordering inconsistency fails closed.

## Fail-Closed Behavior and Outcome Separation

If any required selected-scenario occurrence or evidence is malformed,
incomplete, unsupported, mismatched, or contradictory, the complete adjustment
list is withheld. There are no partial authoritative rows, defaults,
reconstruction, silently skipped malformed rows, or new M10 blocker.

These outcome classes remain distinct:

1. comparator business blocker;
2. selected-scenario adjustment evidence unavailable or malformed;
3. transport/API failure; and
4. stale discarded state.

No new blocker vocabulary was introduced.

## Presentation-Only Correction and Defect Closure

The rejected candidate initially introduced `Clear selected scenario` and a
PKG-017-owned comparator-state transition. Commit
`e622d4004d1434c4f63e9fdf2f515bce0ee2f339` removed that behavior.

The accepted implementation contains no `Clear selected scenario` button, no
`clearSelected`, no `onClear`, no PKG-017-specific selection reset, no
PKG-017-specific `compareEpoch` mutation, and no PKG-017-specific
loading/result/blocker/error mutation. This is the closure basis for both
`D-017-I001 CLOSED` and `D-017-I002 CLOSED`.

## Comparator and Selection Preservation

PKG-015 remains sole comparator admission/arithmetic owner. PKG-016 remains
owner of comparator frontend invocation/presentation, transient selection
behavior, and comparator request ownership. PKG-017 adds only literal
adjustment-evidence presentation.

There is no change to `POST /api/clients/{client_id}/m10/compare`, its request
body, pair admission, success-response contract, blocker vocabulary or
precedence, result semantics, delta arithmetic, numeric relations, or
comparison fingerprints.

S1 -> S2 uses existing PKG-016 selection behavior only. PKG-017 derives
evidence from the current visible selected candidate, adds no selection
mutation, and exposes no clear-selection capability.

## Client-Generation Isolation

Deterministic A -> B and A -> B -> A protections establish that old-client and
old-generation adjustment evidence cannot populate the current context.
`useClientContextGeneration` and existing discovery/request ownership remain
authoritative.

## No-Calculation, Assumption-Delta, and Causal-Attribution Boundaries

PKG-017 performs zero business calculation. Regex validation, equality,
ordinal consistency, and canonical `YYYY-MM` lexical ordering are structural
checks and do not create business-calculation authority. There is no monetary
arithmetic, total, percentage, materiality, duration, assumption delta, or
causal attribution.

Manifest comparison, baseline-versus-adjusted assumption comparison,
adjusted-versus-adjusted comparison, semantic assumption diff, larger/smaller
assumption claims, and per-adjustment business differences remain prohibited.
There is no authority to state that an adjustment caused an outcome, had an
impact or contribution, explained a result or delta, or affected cash flow.

## Q-019 and Q-020 Exclusions

Q-019 remains excluded for new metrics, percentages, materiality/significance,
semantic assumption differences, causal attribution, broader family
compatibility, and partial-value substitution.

Q-020 remains excluded for multi-scenario comparison,
adjusted-versus-adjusted comparison, review, preference, persisted selection,
comparison persistence/history, supersession, archive, and M11/M12 handoff.

## Acceptance-Criteria Evidence

- Range: `AC-017-001` through `AC-017-040`
- Result: `40 PASS / 0 FAIL / 0 AMBIGUOUS`
- `AC-017-004`: `PASS`
- `AC-017-024`: `PASS`
- `AC-017-036`: `PASS`
- `AC-017-038`: `PASS`

## Negative-Acceptance Evidence

- Range: `NAC-017-001` through `NAC-017-028`
- Result: `28 PASS / 0 FAIL / 0 AMBIGUOUS`
- `NAC-017-026`: `PASS`

## Stop-Condition Evidence

All 17 accepted stop conditions are `NOT_FIRED`:

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

## Accepted Test and Build Evidence

| Evidence | Accepted result |
|---|---|
| Focused M10 screen | `67 passed` |
| Focused comparator screen/API | `92 passed` |
| Full frontend | `29 files; 980 passed; 0 failures` |
| Production build/type-check | `PASS` |
| PKG-015 comparator regression | `69 passed; 2 unchanged FastAPI on_event deprecation warnings` |

An initial full frontend run observed one unrelated M05 timeout. That exact
test passed independently, and a complete unchanged rerun passed all 980 tests.
The initial timeout is not a PKG-017 failure.

## Predecessor and Architecture Preservation

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017 definition: `CLOSED_ON_MASTER`

No predecessor accepted artifact or authority changed. The invariant remains:
every material business calculation has exactly one authoritative owner.

- M09 owns scenario subjects and adjustment evidence.
- PKG-015 owns comparator admission and arithmetic.
- PKG-016 owns comparator frontend invocation, presentation, transient
  selection, and request ownership.
- PKG-017 owns literal adjustment-evidence presentation only.

## Definition and Document Integrity

The immutable evidence blobs remain:

| Artifact | Blob SHA |
|---|---|
| PKG-017 definition | `f6e5da9d4c54b902da6dec7e11f6502f92b1dd32` |
| Definition acceptance record | `2920ff16dd0eff7ef7f25ae8751b61cc5b526dd8` |
| Business Build Plan | `26bef42aead24ed32e8ce9b136dd43242bbeefaa` |

This record changes none of those artifacts and changes no implementation file.

## Governance After Record

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017 definition: `CLOSED_ON_MASTER`
- PKG-017 implementation: `ACCEPTED_PENDING_IMPLEMENTATION_RECORD_AUDIT`
- Immutable accepted implementation HEAD: `5280a1063e16af99df99eb836f724aeea0031ff3`
- Historical rejected candidate: `9cfaa654927e9b8616559951e05a266e5a5c5dac`
- Implementation acceptance-record evidence: the documentation-only commit containing this record
- Master merge: `NOT_AUTHORIZED`
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11-M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`
- Next package: `NOT_AUTHORIZED`
- Production readiness: `NOT_CLAIMED`

PKG_017_IMPLEMENTATION_ACCEPTED
