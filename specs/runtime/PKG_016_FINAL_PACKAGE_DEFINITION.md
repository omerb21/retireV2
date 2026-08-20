# PKG-016 Final Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-016` |
| Title | `M10 Stateless Comparator Frontend Presentation and Invocation Foundation` |
| Module | `M10` |
| Classification | `FRONTEND_PRESENTATION_AND_INVOCATION_ONLY` |
| Business authority | `NO_NEW_M10_BUSINESS_AUTHORITY` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Authoritative base | `91e0d3f01c4c01c1e5d81f06bc678dfa9f79635d` |
| Accepted PKG-015 v2 definition HEAD | `73d2ce72c39d90c64457b9bf49d32176483fcc4e` |
| Accepted PKG-015 v2 implementation HEAD | `4cb10f2bc36c041a7681b60edfbcba712037f0c6` |
| PKG-015 v2 implementation acceptance evidence | `fd63b38abb9d51bffa71eb494ec62e6f1d728d9a` |
| Current Alembic head | `e6b4c8d2f507` |

This document proposes a bounded browser presentation and invocation slice for
the already accepted PKG-015 v2 comparator. It is not an accepted definition,
implementation authorization, backend-change authorization, migration
authorization, production-readiness decision, broader-M10 decision, or
next-package authorization.

## 2. Authoritative Sources and Consumed Contracts

The authoritative repository documents are:

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`;
- `specs/runtime/PKG_015_V2_FINAL_PACKAGE_DEFINITION.md`; and
- `specs/runtime/PKG_015_v2_implementation_acceptance_record.md`.

PKG-016 consumes exactly these accepted contract identifiers, without alias,
fallback, reinterpretation, or version negotiation:

1. `declared_retirement_cashflow_adjustments/v1`
2. `m09-subject-currentness-v1`
3. `m09-to-m10-eligibility-v2`
4. `m10-scenario-comparison-v2`
5. `m10-pair-admission-v2`
6. `m10-comparison-result-v2`
7. `m10-comparison-fingerprint-v2`

The accepted PKG-015 blocker vocabulary and precedence remain closed server
authority. Where this document summarizes that contract, the accepted PKG-015
v2 definition controls.

## 3. Exact Product Outcome

PKG-016 makes the accepted stateless comparator usable in the browser for one
route client. It presents the one server-evidenced eligible baseline run and
server-evidenced eligible adjusted-run candidates, lets the user construct one
transient baseline-reference/adjusted-compared request, invokes the accepted
comparator, and renders its exact success or structured blocker response.

It creates no calculation, compatibility rule, professional interpretation,
persisted comparison, planner selection, or downstream authority.

## 4. Repository Evidence and Existing Surfaces

The following existing surfaces were inspected and are sufficient for the
bounded definition:

| Concern | Existing surface |
|---|---|
| Route client | `useParams` in `frontend/src/pages/M09CashflowScreen.tsx`; route pattern in `frontend/src/routes/AppRoutes.tsx` |
| Client generation | `useClientContextGeneration(clientId, location.key)` in `frontend/src/hooks/useClientContextGeneration.ts` |
| API transport | `buildApiUrl` in `frontend/src/api/apiBase.ts`; `ApiTransportError` and JSON transport pattern in `frontend/src/api/clientsApi.ts` and `frontend/src/api/m09CashflowApi.ts` |
| Subject discovery | `listM09Subjects(clientId)` -> `GET /api/clients/{client_id}/m09/subjects` |
| Run discovery | `listM09SubjectRuns(clientId, subjectId)` -> `GET /api/clients/{client_id}/m09/subjects/{subject_id}/runs` |
| Explicit evidence reads | Existing `getM09SubjectCurrentness` and `getM09SubjectEligibility` GET clients; summaries already expose `is_current` and `eligible_for_m10` |
| Identity/display metadata | `M09ScenarioSubject` exposes server-owned `scenario_subject_id`, `subject_type`, `display_label`, family/version, and `created_at`; `M09SubjectRunSummary` exposes `run_id`, sequence, horizon, status, server evidence booleans, and `created_at` |
| Comparator | Existing backend `POST /api/clients/{client_id}/m10/compare` in `backend/app/api/m10_comparison_routes.py`, with exact request/response models in `backend/app/schemas/m10_comparison.py` |
| Established isolation | Generation, channel-epoch, and loading-owner patterns in `M09CashflowScreen.tsx` and `M09ScenarioSubjects.tsx` |

The subject service currently returns subjects ordered by `created_at` and run
summaries by descending `run_sequence`. PKG-016 needs no new discovery,
admission, validation, or comparison backend route. The mutating
`resolveM09BaselineSubject` and subject/run creation APIs are not PKG-016
discovery surfaces and must not be invoked by this read-only screen.

## 5. Authority Model

Every material business calculation has exactly one authoritative owning
module or engine. For this package:

- PKG-014/M09 owns subject identity, subject role, run currentness, and M10
  eligibility evidence;
- PKG-015/M10 owns atomic pair admission, comparison arithmetic, relations,
  response schema, blocker selection and precedence, and fingerprinting; and
- the browser owns only read-only presentation, transient request construction,
  request invocation, display formatting, and generation-safe UI state.

The browser must not reconstruct currentness, eligibility, baseline ownership,
scenario semantic identity, factual-baseline compatibility, horizon
compatibility, family/version compatibility, delta, or relation.

## 6. Exact IN Scope

Only the following is in scope for a future separately authorized
implementation:

- one bounded client-scoped comparison screen and its route/navigation entry;
- read-only use of the existing M09 subject and subject-run list surfaces;
- presentation of one server-evidenced eligible baseline reference;
- presentation of server-evidenced eligible/current adjusted candidates;
- transient selection of exactly one baseline reference and one adjusted run;
- exact invocation of `POST /api/clients/{client_id}/m10/compare`;
- exact success presentation from `m10-comparison-result-v2`;
- one-to-one presentation of accepted structured comparator blockers;
- separate discovery, transport, business-blocker, success, and stale-discard
  UI states;
- client-generation, request-epoch, and loading-owner isolation; and
- focused frontend tests, frontend regressions, type-check, and production
  build evidence for that implementation.

This is a comparison screen, not a generic M10 dashboard.

## 7. Exact OUT Scope

The following are explicitly excluded:

- new metrics, percentages, percentage changes, materiality thresholds, or
  significance labels;
- better/worse, preference, recommendation, ranking, optimization, suitability,
  forecast, probability, NPV, or professional-decision semantics;
- assumption-delta exposure or browser-side assumption comparison;
- adjusted-versus-adjusted, baseline-versus-baseline, more-than-two-run,
  multi-scenario, cross-family, cross-version, or partial-horizon comparison;
- missing-value placeholders, synthesis, zero-fill, fallbacks, defaults,
  interpolation, normalization, or compatibility inference;
- comparison persistence, history, saved comparison, review, approval,
  preferred-scenario selection, supersession, revocation, or archival;
- M10 downstream eligibility, M11/M12 eligibility or authority, M11-M14 work,
  or report generation;
- browser monetary, delta, relation, currentness, eligibility, baseline, or
  compatibility calculations;
- backend business, API-semantic, schema, eligibility, or blocker expansion;
- database models or migrations; and
- production readiness or any next package after PKG-016.

## 8. Read-Only Discovery Contract

Discovery is one client-generation-owned workflow:

1. Call `listM09Subjects(clientId)` for the route client.
2. Admit only subjects whose server response reports exact family/version
   `declared_retirement_cashflow_adjustments/v1` and exact server-owned
   `subject_type` of `baseline` or `adjusted`. Any unexpected subject within the
   intended candidate set fails closed; it is not coerced or reclassified.
3. Call `listM09SubjectRuns(clientId, scenarioSubjectId)` for each admitted
   subject.
4. A run is UI-eligible only when its server-returned summary says both
   `is_current === true` and `eligible_for_m10 === true`. The browser performs no
   reason reconstruction from status, horizon, fingerprints, manifests, dates,
   or raw business facts.
5. Exactly one such run may represent a subject. More than one is malformed or
   unexpected server evidence and makes discovery fail closed; the browser has
   no tie-break.

The explicit currentness and eligibility GET endpoints remain authoritative
available surfaces, but PKG-016 does not need to duplicate summary evidence by
default. If future implementation evidence shows the summary booleans are not
sufficient or cannot be consumed without reconstructing authority, it must stop
with `PKG_016_DISCOVERY_AUTHORITY_INSUFFICIENT`.

Discovery establishes individually eligible/current candidates only. It does
not establish pair admission. The browser must not compare fingerprints,
horizons, versions, or manifests to pre-admit a pair. The single comparator
POST is the atomic authority for pair compatibility and any accepted blocker.

## 9. Baseline Authority and Behavior

The browser obtains baseline ownership only from the subject-list response's
server-owned `subject_type`.

- Exactly one apparent baseline subject with exactly one server-evidenced
  eligible/current run: display that run as the fixed reference authority.
- No baseline subject, or a baseline with no eligible/current run: comparison
  is unavailable; adjusted selection and compare invocation are disabled.
- More than one apparent baseline subject, or more than one eligible/current
  run for the baseline subject: discovery fails closed; no tie-break and no
  compare invocation.

The screen never calls `POST .../subjects/baseline`, creates a baseline, selects
between baselines, or derives baseline status from display text or other facts.

## 10. Adjusted-Run Authority and Ordering

Only a subject reported by the server as `adjusted`, with exactly one run whose
summary reports both accepted evidence booleans as true, is selectable. An
adjusted subject with no such run is omitted from the selectable list and may be
represented only by the neutral aggregate state that no eligible adjusted run
exists. Unexpected multiple eligible/current runs for any subject fail the
whole discovery generation closed so no browser tie-break creates authority.

Selectable adjusted candidates use the deterministic neutral order:

1. ascending server-returned subject `created_at`; then
2. ascending exact `scenario_subject_id` as a tie-break.

This technical order conveys no quality, preference, ranking, recency benefit,
or recommendation. `display_label`, when present, is display metadata only;
subject ID and run ID remain visible or inspectable identifiers. No candidate
is automatically selected merely because it is first.

## 11. Transient Pair Selection

The baseline reference is fixed by server evidence. A user may transiently
choose exactly one adjusted candidate as `compared_run_id`. Compare is enabled
only while the current generation has one valid baseline run and one explicitly
chosen adjusted run.

This choice is only construction of one browser request. It does **not** mean a
planner-selected, recommended, approved, preferred, reviewed, saved,
M11-eligible, or M12-eligible scenario or comparison. It is not persisted in the
backend, browser storage, URL, or any business record. Route/client generation
change clears it immediately.

## 12. Exact Comparator Invocation

The only comparator call is:

`POST /api/clients/{client_id}/m10/compare`

The path `client_id` is the validated current route client. The JSON body has
exactly:

```json
{
  "reference_run_id": "<server-evidenced baseline run id>",
  "compared_run_id": "<explicitly selected adjusted run id>"
}
```

There is no body `client_id`, subject ID, family, version, currentness,
eligibility, fingerprint, horizon, label, preference, or additional field. Run
IDs from a previous generation are cleared and cannot be submitted.

## 13. Exact Success Presentation

The screen renders server-returned `m10-comparison-result-v2` without creating a
new result contract. It presents:

- the four exact contract/schema identifiers and `comparison_fingerprint`;
- `delta_direction`, `client_id`, scenario family/version, horizon,
  factual-baseline material fingerprint, component-domain version, and exposed
  `versions` evidence;
- the exact `reference_run` and `compared_run` evidence;
- each server-returned `monthly_comparisons` item in returned order, including
  `month` and, for `gross_inflow_total`, `gross_outflow_total`, and `period_net`,
  exact reference value, compared value, delta, and relation; and
- exact `range_totals` values, deltas, and relations for those same metrics.

The response is one point-in-time stateless result. The browser does not verify
or recreate the fingerprint and does not supplement, omit, reorder, aggregate,
or reinterpret result semantics.

## 14. Decimal and Display Boundary

All authoritative monetary members are server-returned canonical strings. UI
code must retain the original string as the semantic value and must perform no
`Number`, `parseFloat`, numeric coercion, subtraction, comparison, rounding, or
re-serialization over it.

The safe default is verbatim string display. A presentation helper may add a
fixed currency label or purely textual thousands separators only when it:

- validates and retains the exact original server string alongside the display;
- changes no sign, digits, two-decimal scale, or value;
- is string-based and round-trips exactly to the original canonical string; and
- is tested with positive, negative, zero, large, and boundary strings.

If those properties cannot be proved, display verbatim. Relations are rendered
only from the exact server enum: `equal`,
`compared_greater_than_reference`, or
`compared_lower_than_reference`. Friendly text may be one-to-one, but may not
introduce better/worse or other qualitative meaning.

## 15. Blocker Presentation Contract

Accepted business blockers are an exact structured response from the
comparator: HTTP 404 for `comparison_run_unavailable`, HTTP 409 for other
accepted comparator blockers, and HTTP 422 for request-schema validation as
defined by PKG-015/FastAPI. The UI must parse a recognized `{code, message}`
detail as a business blocker only where the accepted comparator contract says
so.

The accepted closed code set is:

- `comparison_run_unavailable`
- `comparison_same_subject`
- `comparison_pair_role_invalid`
- `comparison_scenario_contract_mismatch`
- `comparison_horizon_mismatch`
- `comparison_factual_baseline_material_mismatch`
- `comparison_component_domain_contract_mismatch`
- `comparison_engine_version_mismatch`
- `comparison_result_schema_version_mismatch`
- `comparison_factual_upstream_version_mismatch`
- `comparison_run_not_current`
- `comparison_run_not_eligible`
- `comparison_fingerprint_invalid`
- `comparison_semantically_identical_manifest`
- `comparison_month_alignment_mismatch`
- `comparison_numeric_domain_invalid`

Each code maps one-to-one to deterministic presentation text, remains visible
and testable, is never suppressed or combined, and receives no invented
severity. Server precedence is not reproduced or changed in the browser: the UI
renders the one code returned. Unknown/malformed error bodies are transport/API
failure, not a new business blocker. No blocker response renders a partial
comparison.

## 16. Closed UI State Taxonomy

The observable states are distinct:

1. `initial/loading`: current-generation discovery has no renderable prior data;
2. `eligible_pair_available`: one baseline and at least one adjusted candidate
   exist; compare remains disabled until explicit adjusted selection;
3. `no_eligible_adjusted_run`: baseline is available but candidate set is empty;
4. `discovery_unavailable`: missing/ambiguous baseline or malformed discovery
   evidence; no invocation;
5. `comparing`: current pair request is pending under its owner token;
6. `comparator_success`: exact current-generation response is shown;
7. `accepted_structured_blocker`: exact current-generation recognized blocker
   code/message is shown with no result;
8. `transport_or_api_failure`: discovery or compare transport, server, schema,
   or unrecognized error is shown separately; and
9. `stale_request_discarded`: no visible mutation; stale completion is ignored.

Discovery absence is not a recommendation or professional warning. Transport
failure is not a comparator blocker.

## 17. Client and Async Generation Isolation

Every client-bound async operation captures `{clientId, generation}` from
`useClientContextGeneration` and a channel/request epoch or owner token.
Discovery subrequests belong to one aggregate discovery epoch; compare belongs
to a separate compare epoch. Success, error, `finally`, loading, enablement, and
selection mutations require both current client generation and current owner.

On any `clientId` or `location.key` generation transition, the screen
immediately clears subject/run candidates, baseline, adjusted selection,
result, blocker, transport error, and actionable run IDs, and starts with new
loading ownership. Abort may be used for efficiency but is not correctness;
token checks remain mandatory.

An old A response cannot affect a new A visit after A -> B -> A. Stale success
cannot render, stale rejection cannot set error, and stale `finally` cannot
clear a new request's loading state or alter controls. Foreign/nonexistent
resource non-leakage remains backend-owned and unchanged.

## 18. Mandatory Race Evidence

Future implementation acceptance must include deterministic deferred-promise
tests, not timing sleeps, for both workflows:

### 18.1 Discovery A -> B -> A

Enter A; start discovery A-old; switch to B; switch back to A; start discovery
A-new; resolve or reject A-old; resolve A-new. At every intermediate point only
the current generation may mutate UI, and the final UI contains only A-new
baseline, candidates, loading, and error state.

### 18.2 Compare A -> B -> A

On A select a pair and start compare A-old; switch B; switch back A; discover
and select a new pair; start compare A-new; settle A-old success or failure;
settle A-new. Only A-new may render result or blocker and own loading/control
state.

### 18.3 Error and Finally Ownership

For discovery and compare independently, an old rejected request must not set
error, erase a new success, clear new loading, or enable/disable controls. Old
success must likewise not clear or overwrite a new error/blocker/result.

## 19. Q-019 Boundary

Q-019 remains partly unresolved for broader M10. Its new metrics,
threshold/materiality, assumption-delta semantics, partial/missing
presentation, and broader compatibility branches remain excluded. PKG-016 is
bounded to the exact result and admission subset already frozen by PKG-014 and
PKG-015, so those branches do not block this definition.

## 20. Q-020 Boundary

Q-020 remains partly unresolved for broader M10. Multi-scenario, review,
persisted selection, supersession, archive, M11 eligibility, and M12 eligibility
remain excluded. A transient two-run request is not any of those concepts, so
those branches do not block this definition.

## 21. No New Result Contract

PKG-016 produces no authoritative business contract. Its output is a browser
presentation of `m10-comparison-result-v2`. Test-only component labels, test IDs,
or TypeScript types are non-business implementation details and must not create
an M10 version, compatibility promise, persisted artifact, or public schema.
`m10-comparison-result-v3` is not created or authorized.

## 22. Backend Immutability

The expected implementation condition is `NO_BACKEND_BUSINESS_CHANGE` and the
preferred implementation is frontend-only. No backend route, request/response
field, schema, eligibility rule, blocker, precedence, calculation, or
persistence change is pre-authorized. If implementation discovers that any
backend semantic or schema change is required, it must stop with
`PKG_016_BACKEND_SEMANTIC_EXPANSION_REQUIRED` and return for a new governance
decision.

## 23. Expected and Authorized Implementation Paths

`EXPECTED_IMPLEMENTATION_PATHS` are evidence-based likely paths, not authority:

- new bounded API client such as `frontend/src/api/m10ComparisonApi.ts`;
- new bounded screen such as `frontend/src/pages/M10ComparisonScreen.tsx`;
- focused tests adjacent to or under the repository's existing frontend test
  conventions;
- `frontend/src/routes/AppRoutes.tsx` for the client-scoped route;
- `frontend/src/pages/ClientDetailScreen.tsx` for bounded navigation; and
- reuse, normally without semantic modification, of
  `frontend/src/api/m09CashflowApi.ts`,
  `frontend/src/api/apiBase.ts`, and
  `frontend/src/hooks/useClientContextGeneration.ts`.

Exact implementation filenames may be refined only by a separately accepted
implementation plan without expanding scope. `AUTHORIZED_IMPLEMENTATION_PATHS`
is empty at this definition stage. No code or test path is authorized now.

## 24. Expected Future Verification

A separately authorized implementation must provide:

- focused API-client contract tests for exact path, method, and two-field body;
- focused screen tests for discovery states, exact rendering, blocker mapping,
  selection clearing, and no automatic selection;
- deterministic A -> B and A -> B -> A stale success/error/finally/loading
  tests for discovery and comparison;
- regression coverage for existing frontend tests;
- frontend type-check and production build via the repository scripts;
- proof that no backend, migration, persistence, or accepted artifact changed;
  and
- proof that no browser arithmetic or authority reconstruction exists.

These are future acceptance expectations, not test authorization in this task.

## 25. Stop Conditions

Implementation must stop and return the named condition if any is required:

1. `PKG_016_BACKEND_SEMANTIC_EXPANSION_REQUIRED`
2. `PKG_016_NEW_METRIC_REQUIRED`
3. `PKG_016_MATERIALITY_OR_SIGNIFICANCE_REQUIRED`
4. `PKG_016_ASSUMPTION_DELTA_SEMANTICS_REQUIRED`
5. `PKG_016_MULTI_SCENARIO_REQUIRED`
6. `PKG_016_ADJUSTED_VS_ADJUSTED_REQUIRED`
7. `PKG_016_COMPARISON_PERSISTENCE_REQUIRED`
8. `PKG_016_REVIEW_OR_SELECTION_AUTHORITY_REQUIRED`
9. `PKG_016_M11_OR_M12_AUTHORITY_REQUIRED`
10. `PKG_016_BROWSER_CALCULATION_REQUIRED`
11. `PKG_016_MISSING_VALUE_SYNTHESIS_REQUIRED`
12. `PKG_016_UPSTREAM_ELIGIBILITY_RECONSTRUCTION_REQUIRED`
13. `PKG_016_NEW_PROFESSIONAL_DECISION_REQUIRED`
14. `PKG_016_SCOPE_EXPANSION_REQUIRED`
15. `PKG_016_DISCOVERY_AUTHORITY_INSUFFICIENT`
16. `PKG_016_BASELINE_AUTHORITY_AMBIGUOUS`
17. `PKG_016_PAIR_PREADMISSION_ROUTE_REQUIRED`
18. `PKG_016_BLOCKER_CONTRACT_DIVERGENCE_REQUIRED`
19. `PKG_016_CLIENT_GENERATION_ISOLATION_UNAVAILABLE`
20. `PKG_016_NONDETERMINISTIC_DISCOVERY_REQUIRED`

These conditions are fail-closed definition boundaries. They do not authorize
the named expansion.

## 26. Acceptance Criteria

- **AC-016-001:** Package identity and title are exact; classification is `FRONTEND_PRESENTATION_AND_INVOCATION_ONLY`, business authority is `NO_NEW_M10_BUSINESS_AUTHORITY`, definition is `PROPOSED_FOR_ACCEPTANCE`, and implementation is `NOT_AUTHORIZED`.
- **AC-016-002:** The authoritative base and three immutable PKG-015 definition, implementation, and acceptance-evidence references are exact.
- **AC-016-003:** All seven consumed contract identifiers are exact and no alias, fallback, negotiation, or new result contract exists.
- **AC-016-004:** Repository evidence names the actual route, generation hook, M09 read APIs, metadata, comparator route/schema, and isolation patterns; no convenience backend route is invented.
- **AC-016-005:** The product is one bounded client-scoped comparison screen and navigation entry, not a generic M10 dashboard.
- **AC-016-006:** Discovery uses only existing client-scoped GET subject/run surfaces and never calls baseline resolution or any M09 mutation.
- **AC-016-007:** Subject type, family, version, currentness, and eligibility are consumed only from server evidence and are never reconstructed from raw facts.
- **AC-016-008:** Exactly one server-reported baseline subject with exactly one current and M10-eligible run becomes the fixed reference.
- **AC-016-009:** Zero eligible baseline fails closed and disables invocation; multiple apparent baselines or eligible baseline runs fail closed with no browser tie-break.
- **AC-016-010:** Only server-reported adjusted subjects with exactly one server-evidenced current and eligible run are selectable.
- **AC-016-011:** More than one eligible/current run for any subject is malformed discovery evidence and fails the generation closed without a tie-break.
- **AC-016-012:** Candidate ordering is ascending server `created_at`, then exact subject ID, and carries no rank, quality, preference, or recommendation meaning.
- **AC-016-013:** Pair compatibility is decided only by the atomic comparator POST; the browser never compares horizon, fingerprint, manifest, family, or version material to pre-admit a pair.
- **AC-016-014:** The baseline is fixed and the user explicitly chooses exactly one adjusted run; the first candidate is not automatically selected.
- **AC-016-015:** Selection is transient request construction only and has no planner selection, review, approval, preference, persistence, or downstream meaning.
- **AC-016-016:** Invocation is exactly `POST /api/clients/{client_id}/m10/compare` for the current route client.
- **AC-016-017:** The strict request body has exactly `reference_run_id` and `compared_run_id` in their accepted roles and no additional field.
- **AC-016-018:** Compare cannot be invoked without one current-generation eligible baseline and one explicitly selected current-generation adjusted candidate.
- **AC-016-019:** Success renders the exact exposed contract, fingerprint, client, family/version, horizon, compatibility, versions, and run-evidence fields returned by the server.
- **AC-016-020:** Each returned monthly item is rendered in server order with exact reference, compared, delta, and relation members for all three accepted metrics.
- **AC-016-021:** Exact range-total reference, compared, delta, and relation members for the same three metrics are rendered without aggregation or omission.
- **AC-016-022:** The browser performs no monetary, delta, range, percentage, relation, fingerprint, eligibility, currentness, or compatibility calculation.
- **AC-016-023:** Monetary strings remain authoritative strings; no float conversion or client rounding occurs, and any optional separators are reversible string-only presentation with the exact source retained.
- **AC-016-024:** Relation presentation derives one-to-one only from the three server-returned relation enum values and creates no better/worse meaning.
- **AC-016-025:** Each accepted comparator blocker code remains visible/testable, maps one-to-one to deterministic text, is neither suppressed nor combined, and receives no invented severity.
- **AC-016-026:** The UI renders only the one server-selected blocker and never duplicates or changes PKG-015 blocker precedence or renders a partial result.
- **AC-016-027:** Accepted business blocker, discovery unavailability, transport/API failure, and stale discard remain four distinct outcome classes.
- **AC-016-028:** Initial/loading, eligible-pair, no-eligible-adjusted, discovery-unavailable, comparing, success, blocker, transport/API-failure, and silent stale-discard states have the observable behavior in Section 16.
- **AC-016-029:** Every discovery and compare operation captures current `clientId`, generation, and channel/request ownership before asynchronous work.
- **AC-016-030:** Client/route generation transition immediately clears all old client-bound candidates, selection, run IDs, result, blocker, error, and ownership state.
- **AC-016-031:** A -> B isolation proves no A value, ID, result, blocker, error, or loading completion can render or remain actionable in B.
- **AC-016-032:** Discovery A -> B -> A deterministic evidence proves A-old success is discarded and only A-new discovery state renders.
- **AC-016-033:** Discovery A -> B -> A deterministic evidence proves A-old rejection and `finally` cannot set error, clear A-new loading, or alter controls.
- **AC-016-034:** Compare A -> B -> A deterministic evidence proves A-old success is discarded and only A-new comparison state renders.
- **AC-016-035:** Compare A -> B -> A deterministic evidence proves A-old rejection and `finally` cannot set error, clear A-new loading, overwrite success, or alter controls.
- **AC-016-036:** Abort is never the sole stale-response correctness mechanism; generation and owner checks protect success, error, and `finally` mutations.
- **AC-016-037:** Deterministic deferred-promise tests cover discovery and compare stale success, stale failure, stale `finally`, loading, error, result, blocker, and control enablement.
- **AC-016-038:** Focused API/screen regressions, full frontend tests, type-check, and production build pass under existing repository scripts before implementation acceptance.
- **AC-016-039:** No metrics, percentages, thresholds, significance, assumption deltas, missing-value synthesis, ranking, recommendation, optimization, suitability, or professional decision is introduced.
- **AC-016-040:** No persistence, saved comparison, history, review, approval, supersession, revocation, archive, report, or preferred-scenario state is introduced.
- **AC-016-041:** No M10 downstream eligibility or M11/M12 authority is created; M11-M14 remain unauthorized.
- **AC-016-042:** No backend semantic/schema/eligibility/blocker change, database model, migration, or accepted-artifact change occurs.
- **AC-016-043:** Q-019 and Q-020 unresolved broader branches remain excluded while the already frozen two-run subset is consumed unchanged.
- **AC-016-044:** Broad M10 remains `BLOCKED_FOR_LOGIC_DETAIL`; M08E remains `EXCLUDED`; `02M` remains `FROZEN`; production readiness is not claimed.
- **AC-016-045:** PKG-016 implementation and every next package remain `NOT_AUTHORIZED`; the only next gate is independent definition acceptance audit.

## 27. Negative Acceptance Criteria

- **NAC-016-001:** Browser subtraction or any delta calculation.
- **NAC-016-002:** Browser numeric comparison or relation calculation.
- **NAC-016-003:** Percentage or percentage-change calculation or display.
- **NAC-016-004:** Materiality threshold, significance label, or better/worse interpretation.
- **NAC-016-005:** Assumption-delta exposure or browser-side assumption comparison.
- **NAC-016-006:** Adjusted-versus-adjusted or baseline-versus-baseline comparison.
- **NAC-016-007:** More than two runs, multi-scenario table, or generic M10 dashboard.
- **NAC-016-008:** Partial horizon, cross-family, cross-version, fallback, alias, or compatibility expansion.
- **NAC-016-009:** Missing-value placeholder, zero-fill, default, interpolation, normalization, or synthesis.
- **NAC-016-010:** Comparison persistence, database record, browser storage, or URL-persisted selection.
- **NAC-016-011:** Saved comparison, comparison history, review, approval, supersession, revocation, or archive.
- **NAC-016-012:** Preferred, selected, approved, or recommended scenario business meaning.
- **NAC-016-013:** Ranking, scoring, optimization, suitability, forecast, probability, NPV, or professional advice.
- **NAC-016-014:** M10 downstream eligibility, M11/M12 eligibility, or M11-M14 authority.
- **NAC-016-015:** Browser reconstruction of M09 currentness.
- **NAC-016-016:** Browser reconstruction of M10 eligibility.
- **NAC-016-017:** Browser inference or tie-break of baseline ownership.
- **NAC-016-018:** Browser pair pre-admission from horizon, fingerprint, manifest, family, or version data.
- **NAC-016-019:** Calling baseline resolution, subject creation, run execution, or another mutating M09 route from the comparison screen.
- **NAC-016-020:** Automatic selection of the first adjusted candidate or ordering that implies preference.
- **NAC-016-021:** Request field beyond exact reference and compared run IDs, or a run ID retained from a prior generation.
- **NAC-016-022:** Recalculation, verification, enrichment, or replacement of server response or comparison fingerprint material.
- **NAC-016-023:** JS number/float conversion, client rounding, scientific reformatting, or semantic change to monetary strings.
- **NAC-016-024:** Blocker suppression, combination, reordering, invented code, severity, warning, or professional interpretation.
- **NAC-016-025:** Converting discovery absence or transport/API failure into an accepted comparator blocker.
- **NAC-016-026:** Rendering stale success, blocker, discovery values, or run IDs.
- **NAC-016-027:** Allowing stale rejection or `finally` to change error, loading, result, selection, or control state.
- **NAC-016-028:** Cross-client data, error, result, blocker, selection, or actionable-ID leakage, including A-old into A-new after A -> B -> A.
- **NAC-016-029:** Backend route, semantic, schema, eligibility, blocker, precedence, or business-logic expansion.
- **NAC-016-030:** Database model, migration, comparison table, or persistence lifecycle.
- **NAC-016-031:** Broad-M10 authorization or resolution of an excluded Q-019/Q-020 branch.
- **NAC-016-032:** PKG-016 implementation, production-readiness, or next-package authorization by this definition.

## 28. Definition Verification Matrix

| Area | Definition-audit evidence |
|---|---|
| Base/scope | Exact base; one docs-only commit; only definition and narrow Build Plan change |
| Discovery | Existing GET surfaces; summary server evidence; no mutation or reconstructed authority |
| Roles/invocation | One baseline reference, one adjusted compared, exact route/body |
| Presentation | Exact response, Decimal-string boundary, no calculation or enrichment |
| Blockers | Accepted closed codes; one-to-one mapping; distinct transport/discovery/stale states |
| Isolation | Client generation plus request ownership; A -> B and A -> B -> A success/error/finally/loading evidence |
| Governance | PKG-015 preserved; broad M10 blocked; downstream and next package unauthorized |
| Repository | Accepted artifacts unchanged; no backend/frontend/test/migration change; Alembic unchanged |

## 29. Definition-Task File Boundary

This docs-only task may change exactly:

- `specs/runtime/PKG_016_FINAL_PACKAGE_DEFINITION.md`; and
- the narrow active-state rows in
  `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.

No frontend, backend, test, migration, acceptance-record, or accepted PKG-015
artifact is part of this definition commit.

## 30. Governance State

- PKG-015 v2: `CLOSED_ON_MASTER`.
- PKG-016 definition: `PROPOSED_FOR_ACCEPTANCE`.
- PKG-016 implementation: `NOT_AUTHORIZED`.
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`.
- Q-019/Q-020: partly unresolved for broader M10; bounded excluded branches do
  not block this proposal.
- M11-M14: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Production readiness: `NOT_CLAIMED`.
- Next package after PKG-016: `NOT_AUTHORIZED`.

Current branch/master wording remains semantic; creating or accepting a future
commit must not make an active self-referential status false.

## 31. Authorization Boundary

No implementation path is authorized. No code, test, migration, backend reuse
change, deployment, merge to master, or next-package work follows from this
proposal. The only permitted next gate is independent PKG-016 definition
acceptance audit.

PKG_016_DEFINITION_PROPOSED_FOR_ACCEPTANCE
