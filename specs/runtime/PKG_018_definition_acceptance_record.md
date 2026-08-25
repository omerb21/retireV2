# PKG-018 Definition Acceptance Record

## Record Identity

- Package: `PKG-018 — M10 Server-Owned Baseline Reference Evidence Presentation Foundation`
- Acceptance type: `Definition Acceptance`
- Classification: `FRONTEND_PRESENTATION_ONLY`
- Business authority: `NO_NEW_M10_BUSINESS_AUTHORITY`
- Definition: `ACCEPTED`
- Immutable accepted definition HEAD:
  `12e121c8e5f5c51dae0490e2d338b463d140d1bc`
- Implementation: `NOT_AUTHORIZED`
- Audit decision: `ACCEPT_PKG_018_DEFINITION`
- Findings: `NO_FINDING`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`
- Definition sufficiency: `SUFFICIENT`
- Definition base / current master:
  `6c38e3974bf104140ed12b6bc429ba84ebad83a5`
- Expected Alembic head: `e6b4c8d2f507`

The immutable accepted definition boundary is exactly
`12e121c8e5f5c51dae0490e2d338b463d140d1bc`. The later documentation-only
commit containing this record is acceptance evidence only and does not replace,
extend, or redefine the accepted definition HEAD.

## Audit Decision and Sufficiency

- Decision: `ACCEPT_PKG_018_DEFINITION`
- Findings: `NO_FINDING`
- Definition sufficiency: `SUFFICIENT`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`

The accepted definition is self-contained for independent implementation
authorization review. This record authorizes no implementation, master merge,
or next package.

## Correction Defect Closure

- `D-018-DAR001`: `CLOSED` — exact field-level baseline binding recorded.
- `D-018-DAR002`: `CLOSED` — no-visible-baseline and outcome classes recorded.
- `D-018-DAR003`: `CLOSED` — implementation/API envelope recorded exactly.
- `D-018-DAR004`: `CLOSED` — deterministic future test obligations recorded.
- `D-018-DAR005`: `CLOSED` — Q-019/Q-020 exclusions restored exactly.

## Accepted Definition and Build Plan Integrity

| Accepted artifact | Blob SHA |
|---|---|
| `specs/runtime/PKG_018_FINAL_PACKAGE_DEFINITION.md` | `0675a9eebacd8a8e45adb5125e4fdd42f3603396` |
| `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md` | `63698328a1f508046bdb87c364312a1f8ac9775f` |

Neither artifact is modified by this acceptance-record commit.

## Accepted Objective and Authority

PKG-018 defines literal server-owned baseline-reference evidence presentation
only. It owns zero business calculation, zero state-transition authority, and
zero downstream authority.

The bounded planner-facing meaning is that the current reference is the
server-owned baseline with no planner-declared scenario adjustments. It is not
a claim about factual portfolio or cash-flow emptiness, a zero result, no
comparison difference, causality, quality, suitability, or recommendation.

## Exact Marker Contract

The sole authoritative marker is:

`server_resolved_no_scenario_adjustments`

The accepted dual-marker requirement is exact:

```text
subject.provenance ==
"server_resolved_no_scenario_adjustments"

AND

subject.adjustment_manifest.baseline_evidence ==
"server_resolved_no_scenario_adjustments"
```

Both server-owned values must corroborate. No alias, fallback, inference,
normalization, repair, or browser synthesis is accepted.

## Empty-Array Prohibition

```text
adjustments.length === 0
```

is not authoritative baseline evidence. An empty adjustment array alone cannot
create, corroborate, repair, or replace the exact marker contract.

## Accepted Presentation and Fail-Closed Semantics

For valid fully bound evidence, the accepted neutral presentation is:

```text
Server-owned baseline reference
No planner-declared scenario adjustments.
```

For invalid or malformed PKG-018 evidence when an existing visible baseline is
present, the exact optional outcome is:

```text
Server-owned baseline reference evidence unavailable.
```

This optional evidence failure:

- does not invalidate a comparator-valid pair;
- does not block comparison;
- does not remove the baseline;
- does not alter currentness or eligibility; and
- does not create or reuse a comparator blocker.

No partial marker claim, default, or inferred meaning is accepted.

If no current visible baseline exists, PKG-018 renders no panel or context. It
does not synthesize unavailable evidence for a baseline that does not exist.

The accepted outcome classes remain exactly distinct:

1. comparator business blocker;
2. optional PKG-018 baseline evidence unavailable or malformed;
3. transport/API discovery failure; and
4. stale discarded context.

There is no conversion between classes. Optional evidence failure is not a
comparator blocker, transport failure, stale discard, or eligibility failure.

## Binding and Client-Generation Authority

Accepted presentation binds to the exact current visible baseline and requires
all of these literal field-level constraints:

```text
subject.client_id == current route client
subject.subject_type == "baseline"
subject.scenario_family == "declared_retirement_cashflow_adjustments"
subject.scenario_contract_version == "v1"
subject.combined_contract_identifier ==
"declared_retirement_cashflow_adjustments/v1"
run.scenario_subject_id == subject.scenario_subject_id
run.is_current == true
run.eligible_for_m10 == true
```

The subject/run must belong to the current visible baseline and current
discovery generation. Identity must not be reconstructed from list order,
labels, amounts, empty arrays, dates, or fingerprint fragments.

`useClientContextGeneration` and existing discovery ownership remain
authoritative. A -> B and A -> B -> A must prevent old-client or old-generation
baseline evidence from populating the current context. PKG-018 owns no separate
baseline memory or async owner.

## Existing Source and Async Preservation

The accepted definition reuses only existing M09 subject discovery:

- `GET /api/clients/{client_id}/m09/subjects`;
- `listM09Subjects(clientId)`;
- the retained baseline candidate, subject, and run;
- `visibleBaseline` or its exact equivalent; and
- `useClientContextGeneration`.

There is no second fetch, subject-detail request, endpoint, response expansion,
API-client semantic expansion, async effect, request-owner channel, or duplicate
discovery.

## Exact Future Implementation and API Envelope

The accepted future implementation surfaces are exactly:

- `frontend/src/pages/M10ComparisonScreen.tsx`
- `frontend/src/pages/M10ComparisonScreen.test.tsx`

An optional tiny presentational helper and focused test are permitted only when
narrowly justified by the accepted definition. No other implementation surface
is accepted.

The exact preserved comparator endpoint is:

`POST /api/clients/{client_id}/m10/compare`

Its existing request and response contract remains unchanged. The immutable
expected diff boundaries are:

- `BACKEND_DIFF = NONE`
- `API_CLIENT_DIFF = NONE`
- `API_EXPANSION = NONE`
- `MIGRATION_DIFF = NONE`
- `PERSISTENCE_DIFF = NONE`

There is no second subject fetch, subject-detail request, new async effect, new
request owner, or API-client semantic expansion.

## Comparator and Predecessor Preservation

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017: `CLOSED_ON_MASTER`

PKG-015 remains sole owner of comparator pair admission, arithmetic, blockers,
fingerprints, deltas, and relations. PKG-016 remains owner of M10 invocation,
comparator presentation, transient adjusted selection, request ownership, and
loading/error/result/blocker lifecycle. PKG-017 remains owner of literal
selected-adjustment evidence presentation.

PKG-018 adds no selection/reset control, comparator-state mutation, blocker,
pair-admission change, baseline-eligibility change, result change, or
baseline-versus-adjusted evidence comparison.

## Architecture Invariant

Every material business calculation retains exactly one authoritative owner:

- M09 owns scenario subject, baseline, and adjustment evidence.
- PKG-015 owns M10 pair admission and arithmetic.
- PKG-016 owns M10 frontend invocation, comparator presentation, transient
  selection, and request ownership.
- PKG-017 owns selected adjusted scenario literal adjustment evidence.
- PKG-018 owns literal server-owned baseline-reference evidence presentation
  only.

PKG-018 owns zero calculation and zero state-transition authority.

## Explicit Exclusions

The accepted definition creates no:

- empty-array inference;
- factual portfolio or cash-flow emptiness claim;
- zero-result, no-difference, zero-impact, or no-effect claim;
- baseline-versus-adjusted manifest comparison;
- assumption delta or semantic diff;
- causal attribution;
- metric, percentage, materiality, score, or rank;
- recommendation, preference, suitability, or professional advice;
- selection, reset, confirmation, review, or approval action;
- comparator-state mutation or new blocker;
- request, fetch, endpoint, async owner, or response expansion;
- backend/API/schema expansion;
- migration, persistence, route state, browser storage, or history;
- M11/M12 handoff or broader M11-M14 authority;
- broader scenario-family support or compatibility fallback;
- actor-authentication claim or generic debug metadata surface;
- factual component or field-level source disclosure; or
- currentness/eligibility diagnostics product or reason-code taxonomy.

## Q-019 and Q-020 Exclusions

Q-019 explicitly excludes metrics, percentages, materiality/significance,
semantic assumption differences, causal attribution, broader scenario-family
support, factual component disclosure, and missing or partial value
substitution.

Q-020 explicitly excludes multi-scenario comparison,
adjusted-versus-adjusted comparison, review, preference, persisted selection,
comparison persistence/history, supersession, archive, and M11/M12 handoff.
These are authority boundaries, not optional wording.

## Deterministic Future Implementation Test Obligations

These are accepted future implementation obligations. This definition
acceptance record does not claim that they have already run.

### Valid evidence

- exact valid dual markers; and
- exact accepted presentation wording.

### Marker corruption

- missing, wrong, null, or wrong-primitive subject provenance;
- missing, wrong, null, or wrong-primitive manifest marker;
- provenance/manifest mismatch; and
- null, array, or non-object manifest.

### Empty-array rule

- `adjustments.length === 0` without valid dual markers does not create
  baseline meaning.

### Binding failures

- wrong client;
- wrong subject role;
- wrong family, version, or combined identifier;
- subject/run mismatch; and
- non-current or non-M10-eligible run when that malformed runtime case is
  reachable.

### Baseline availability and isolation

- no visible baseline renders no PKG-018 context;
- same-context replacement/removal is tested only if reachable through
  existing discovery;
- A -> B; and
- A -> B -> A.

### Optional outcome separation

- malformed optional evidence does not block an otherwise valid comparator
  pair;
- transport failure remains distinct; and
- stale discard remains distinct.

### Predecessor preservation

- PKG-017 selected adjustment evidence remains unchanged; and
- comparator request, result, and blocker behavior remain unchanged.

### No-new-request proof

- no second subject fetch;
- no new API-client call; and
- no new async owner.

### Scope proof

- `BACKEND_DIFF = NONE`
- `API_CLIENT_DIFF = NONE`
- `API_EXPANSION = NONE`
- `MIGRATION_DIFF = NONE`
- `PERSISTENCE_DIFF = NONE`

## Acceptance-Criteria Evidence

- Range: `AC-018-001` through `AC-018-042`
- Result: `42 PASS / 0 FAIL / 0 AMBIGUOUS`

All accepted criteria are contiguous and objectively auditable across package
identity, marker authority, corroboration, binding, client generation,
presentation, failure semantics, predecessor preservation, exclusions,
deterministic testing, and governance.

## Negative-Acceptance Evidence

- Range: `NAC-018-001` through `NAC-018-030`
- Result: `30 PASS / 0 FAIL / 0 AMBIGUOUS`

## Stop-Condition Evidence

All 19 accepted stop conditions are `NOT_FIRED`:

1. `PKG_018_SERVER_OWNED_BASELINE_MARKER_UNAVAILABLE`
2. `PKG_018_BASELINE_MARKER_INFERRED_FROM_EMPTY_ARRAY`
3. `PKG_018_BASELINE_PROVENANCE_MANIFEST_MISMATCH`
4. `PKG_018_BASELINE_SUBJECT_RUN_BINDING_UNAVAILABLE`
5. `PKG_018_CLIENT_ISOLATION_OR_GENERATION_OWNERSHIP_UNAVAILABLE`
6. `PKG_018_NEW_FETCH_OR_ASYNC_CHANNEL_REQUIRED`
7. `PKG_018_BACKEND_API_OR_SCHEMA_EXPANSION_REQUIRED`
8. `PKG_018_NEW_BUSINESS_CALCULATION_REQUIRED`
9. `PKG_018_ASSUMPTION_DELTA_OR_MANIFEST_COMPARISON_REQUIRED`
10. `PKG_018_CAUSAL_ATTRIBUTION_REQUIRED`
11. `PKG_018_FACTUAL_PORTFOLIO_EMPTINESS_INFERENCE_REQUIRED`
12. `PKG_018_COMPARATOR_SELECTION_OR_BLOCKER_MUTATION_REQUIRED`
13. `PKG_018_ADDITIONAL_METRIC_PERCENTAGE_OR_MATERIALITY_REQUIRED`
14. `PKG_018_PERSISTENCE_HISTORY_OR_REVIEW_REQUIRED`
15. `PKG_018_RANKING_RECOMMENDATION_OR_PREFERENCE_REQUIRED`
16. `PKG_018_M11_OR_M12_HANDOFF_REQUIRED`
17. `PKG_018_FAIL_CLOSED_PRESENTATION_UNAVAILABLE`
18. `PKG_018_PREDECESSOR_CONTRACT_CHANGE_REQUIRED`
19. `PKG_018_NEW_PROFESSIONAL_DECISION_REQUIRED`

Result: `19 NOT_FIRED`

## Historical Incomplete Record Candidate

Commit `1eca1b5da3027879dabbbe6d14f37c19757cccef` remains unchanged in linear
history with status:

`HISTORICAL_INCOMPLETE_DEFINITION_ACCEPTANCE_RECORD_CANDIDATE`

It is evidence of the failed record audit and is not the final accepted record
evidence. The append-only correction commit containing this revised record is
the current definition acceptance-record candidate pending WORK re-audit. The
immutable accepted definition boundary remains
`12e121c8e5f5c51dae0490e2d338b463d140d1bc`.

## Governance After Definition Acceptance Record

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017: `CLOSED_ON_MASTER`
- PKG-018 definition: `ACCEPTED`
- Immutable accepted definition HEAD:
  `12e121c8e5f5c51dae0490e2d338b463d140d1bc`
- Historical incomplete acceptance-record candidate:
  `1eca1b5da3027879dabbbe6d14f37c19757cccef`
- Record status: `CORRECTED_CANDIDATE_PENDING_WORK_REAUDIT`
- PKG-018 implementation: `NOT_AUTHORIZED`
- Master merge: `NOT_AUTHORIZED`
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11-M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- `02M`: `FROZEN`
- Next package beyond PKG-018: `NOT_AUTHORIZED`
- Production readiness: `NOT_CLAIMED`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`

PKG_018_DEFINITION_ACCEPTED
