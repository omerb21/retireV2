# M01 Internal Professional Case Workflow Hub — Definition Candidate

## 1. Identity and lifecycle

- Package: `M01_INTERNAL_PROFESSIONAL_CASE_WORKFLOW_HUB`.
- `CLASSIFICATION = CLASS_A`.
- `COMPLEX_CLASS_A = NO`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Definition base master: `12f0cba011c53f1ca750305f49e87fd922d43909`.
- Definition base TREE: `9288c14b95a2fb5fd801c1e28ad129e66142306c`.
- Status: `DEFINITION_CORRECTION_PENDING_FOCUSED_REAUDIT`.
- Implementation: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

The package adds a read-only professional workflow overview at the top of the
existing `ClientDetailScreen`. It projects already accepted persisted facts and
current readiness into navigation assistance. It creates no persisted workflow
state, professional authority, calculation, blocker, completion event, or
authorization.

## 2. Mandatory continuity

The planning handoff on
`origin/planning/workflow-review-and-pending-definition-register` at
`f4a2e96e2e7712e61f620224c61add3843acd500` was inspected. Its pending package
is preserved exactly:

- package: `RMIGA_INTERNAL_WORKSPACE_CONSUMER_BINDING`;
- branch: `codex/rmiga-internal-workspace-consumer-binding-definition`;
- HEAD: `dc4ea5de393dfb69d5bb3c5758c7dfcdebb42b64`;
- TREE: `e5461f5cf272feb9611667b1e5426083f64c5836`;
- Definition blob: `594c0434821d581bf1423e5b071ca1db36d2ee72`;
- status: `DEFINITION_ACCEPTANCE_PENDING_INDEPENDENT_AUDIT`.

This package does not merge, accept, implement, supersede, copy, discard, or
otherwise change that candidate. In particular, RMIGA is not available in the
current UI and this overview must say so.

## 3. Inspected executable contracts

The Definition is grounded in these base-master contracts:

1. `GET /api/clients/{client_id}` returns `m01_case` with exact
   `completeness.status` values `complete | incomplete`, plus
   `missing_field_ids` and `conflicting_field_ids`.
2. `ClientDetailScreen` already loads the addressed client, profile,
   clearinghouse snapshots, retirement-planning documents and missing-data
   items, and rejects stale client-context results.
3. Collection and verification status values are general strings. They are not
   an accepted universal downstream-blocking vocabulary. An advisory missing
   item with `advisory_status = open` is a workflow fact, not by itself a new
   calculation blocker.
4. `GET /api/clients/{client_id}/retirement-income-readiness/context` returns
   exact schema `RTDIR_PLANNING_CONTEXT_V1`, `client_id`,
   `planning_calculation_input_fingerprint`, `planning_input_ready`,
   `retirement_target_date`, `retirement_target_ready`, and ordered
   `blocking_facts`.
5. The context route validates producer identity and returns only accepted
   authenticated, client-bound state. The existing frontend `readContext()`
   supports an `AbortSignal` and rejects a mismatched non-null response client.
6. The readiness screen can perform an ephemeral RTICB comparison, but no
   accepted persisted comparison-completion fact is exposed to
   `ClientDetailScreen`.
7. The existing `useClientContextGeneration` contract binds a captured
   `{clientId, generation}` to the active route key and client.
8. All five required destinations already exist in `AppRoutes`; no route
   registration change is required.

The overview may summarize missing information, evidence counts and readiness
facts. It must never infer that an arbitrary missing item blocks downstream
use, reinterpret a producer blocker, or infer completion from navigation.

## 4. Component and data contract

`ClientDetailScreen` renders exactly one
`ProfessionalWorkflowOverview` immediately after the client identity heading
and before editable case/profile content, only after the addressed client is
successfully loaded and still owns the active client context.

The component receives only current-client facts already held by the screen:

- `clientId`;
- `m01Case`;
- `clearinghouseSnapshots`;
- `retirementPlanningDocuments`;
- `missingDataItems`; and
- whether the collection read completed successfully or failed.

`ClientDetailScreen` also owns an integer `readinessContextRevision`, initially
zero for each mounted client workspace. The component receives that revision
with the active client identity. Every accepted readiness response is stored
with the exact `{clientId, routeKey, readinessContextRevision, generation}`
token under which it was requested and may render only while all four values
remain current.

The component performs one read-only `readContext(clientId, signal)` request
per mounted client context. It uses one `AbortController` and the existing
client-context generation policy. It verifies the returned `client_id` again
before accepting the response. It stores no result outside React component
state.

After every successful, still-current M01 case save or profile save, the screen
must treat the returned mutation as potentially affecting Planning Input or
RIT facts. It performs this exact sequence:

1. increment `readinessContextRevision` once;
2. make the prior accepted readiness token immediately ineligible to render,
   which clears Phase 3, Phase 4 and readiness-derived next-action state to
   `NOT_EVALUATED` in the same render;
3. abort the prior readiness `AbortController`; and
4. issue exactly one fresh `GET .../retirement-income-readiness/context` for
   the new revision.

There is no debounce, retry, reuse of the prior response, or same-client
exception. A response captured under an older revision is stale even when its
`clientId` and route key equal the current values. Failed saves do not advance
the revision because no accepted persisted fact changed.

On client ID or route-key change, error, abort, or unmount, all derived phases,
readiness data and suggested-action state for the old context are cleared
before any new response can render. A late A response cannot render during B,
and an old A response cannot render after A-to-B-to-A.

The overview performs no POST, PUT, PATCH, DELETE, navigation-side write,
producer invocation, recalculation, retry loop, persistence, browser-storage
write, or URL-state serialization.

## 5. Closed presentation vocabulary

Every phase has exactly one of:

- `COMPLETE`;
- `INCOMPLETE`;
- `BLOCKED`;
- `READY_TO_CONTINUE`;
- `NOT_EVALUATED`; or
- `NOT_AUTHORIZED`.

These values are UI projections only. They are not written to the server and
must not be described as persisted workflow state. Each rendered phase shows:

- fixed phase number and Hebrew phase title;
- projected state and a neutral Hebrew explanation;
- the exact grounded facts used for that projection; and
- one accessible link to its contracted fixed or condition-dependent primary
  destination.

Unknown or unavailable facts fail closed to `NOT_EVALUATED`; they are not
coerced to `COMPLETE`, `READY_TO_CONTINUE`, or `BLOCKED`.

## 6. Exact five-phase projection

### Phase 1 — Case foundation

- Hebrew title: `תשתית תיק הלקוח`.
- Route: `/clients/{client_id}`.
- `BLOCKED` when `conflicting_field_ids` is non-empty.
- `COMPLETE` only when `completeness.status === "complete"` and both field-ID
  arrays are empty.
- `INCOMPLETE` for an accepted incomplete case, missing fields, absent case
  envelope, or any non-conflicting state that is not exactly complete.
- Display missing and conflicting IDs exactly in producer order. Do not invent
  an additional required M01 field.

Conflicts take precedence over missing fields and completion. The Phase 1
phase link and any suggested Phase 1 next action target the existing editable
heading `m01-case-foundation-heading`, not the top of the client route.

### Phase 2 — Evidence and source preparation

- Hebrew title: `הכנת ראיות ומקורות`.
- Navigation is condition-dependent as frozen below.
- `NOT_EVALUATED` when the collection read failed or has not completed.
- `INCOMPLETE` when either the clearinghouse-snapshot collection or the
  retirement-planning-document collection is empty.
- `READY_TO_CONTINUE` only when both evidence collections contain at least one
  item and the collection read succeeded.

The phase displays exact counts for snapshots, documents and missing-data
items, plus counts grouped by the stored collection/verification/advisory
strings. `READY_TO_CONTINUE` means only that both kinds of evidence-collection
activity exist and professional source review is an appropriate continuation.
It does not mean verified, complete, calculation-ready or blocker-free. No arbitrary
`missing_status`, `verification_status`, or `advisory_status` is promoted to a
new `BLOCKED` or `COMPLETE` authority. Generic missing-data rows, alone or in
any count/status, never satisfy either evidence-collection condition and never
make professional-source preparation ready.

The Phase 2 primary action is exact and resolves or inspects the condition that
selected it:

1. while collection data is unavailable, target
   `/clients/{client_id}#clearinghouse-snapshots-heading` with the neutral
   purpose of inspecting/retrying the existing collection area;
2. when no clearinghouse snapshot exists, target that same snapshot heading;
3. otherwise, when no retirement-planning document exists, target
   `/clients/{client_id}#retirement-documents-heading`;
4. only when both collections have an item, target
   `/clients/{client_id}/professional-sources` for source preparation.

An existing missing-data row may be summarized and its existing editable
`/clients/{client_id}#missing-data-heading` anchor may be offered as a
secondary inspection link, but it cannot replace the primary action above or
imply professional-source readiness.

### Phase 3 — Planning input

- Hebrew title: `קלט תכנון`.
- Route: `/clients/{client_id}/planning-input`.
- `NOT_EVALUATED` while context is loading, after abort, or after context error.
- `COMPLETE` only when the accepted context says
  `planning_input_ready === true`.
- `BLOCKED` when `planning_input_ready === false` and `blocking_facts` is
  non-empty.
- `INCOMPLETE` when `planning_input_ready === false` and `blocking_facts` is
  empty.

The phase preserves each blocking fact's `source_id` and `code` in producer
order. It does not translate a warning or general missing item into a blocker.

### Phase 4 — Retirement-income readiness

- Hebrew title: `מוכנות הכנסה במועד היעד`.
- Route: `/clients/{client_id}/retirement-income-readiness`.
- `NOT_EVALUATED` while context is loading, after abort, or after context error.
- `BLOCKED` when either accepted context boolean
  `planning_input_ready` or `retirement_target_ready` is false.
- `READY_TO_CONTINUE` only when both booleans are true.

This overview never uses `COMPLETE` for Phase 4 because the comparison result
is an explicit, ephemeral action and is not persisted as workflow completion.
The phase displays the accepted retirement date or `לא נקבע`, and makes no
claim that comparison has occurred.

Within Phase 4, the separate line `פער הכנסה חודשי: NOT_AUTHORIZED` is always
shown for this package. It explains neutrally that RMIGA has no accepted UI
consumer yet. It must not link to, simulate, calculate, or preview RMIGA.

### Phase 5 — Other professional activity, including fixation

- Hebrew title: `פעילות מקצועית נוספת, לרבות קיבוע זכויות`.
- Route: `/clients/{client_id}/fixation/workspace`.
- State: `NOT_EVALUATED`.

The allowed inputs expose no accepted aggregate readiness or completion
authority for this heterogeneous phase. The route remains available, but the
overview does not infer fixation eligibility, completion, delivery, or
professional recommendation from case or planning readiness.

## 7. Exactly one suggested next action

The overview renders one and only one `הפעולה הבאה המוצעת` link. It uses this
deterministic priority:

1. If Phase 1 is `BLOCKED` or `INCOMPLETE`, use the Phase 1 in-page focus
   action defined in Section 8.
2. Otherwise, if Phase 2 is `INCOMPLETE` or `NOT_EVALUATED`, use the exact
   condition-dependent primary action in Phase 2.
3. Otherwise, if Phase 3 is `BLOCKED`, `INCOMPLETE`, or `NOT_EVALUATED`, link
   to Phase 3.
4. Otherwise link to Phase 4, whether it is `BLOCKED`,
   `READY_TO_CONTINUE`, or `NOT_EVALUATED`, because comparison remains an
   explicit non-persisted professional action.

Phase 5 is navigable but is never automatically recommended by this package;
the accepted inputs cannot prove when it is the next appropriate activity.
The suggested action is navigation guidance, not professional advice or an
authorization gate.

## 8. Navigation and lifecycle behavior

The exact canonical destinations are:

1. Phase 1: `/clients/{client_id}#m01-case-foundation-heading`;
2. Phase 2: the exact snapshot, document or professional-source destination
   selected by Section 6;
3. `/clients/{client_id}/planning-input`;
4. `/clients/{client_id}/retirement-income-readiness`;
5. `/clients/{client_id}/fixation/workspace`.

All links use the validated active numeric client ID, never a response-provided
or stale ID. Rendering and ordinary link navigation issue no writes. Existing
route authentication and client isolation remain unchanged.

The existing `m01-case-foundation-heading` becomes programmatically focusable
with `tabIndex={-1}`. Activating the Phase 1 phase link or suggested action:

1. updates only the fragment to `#m01-case-foundation-heading` as one browser
   history entry;
2. does not remount ClientDetailScreen, refetch the client, or reset editable
   state;
3. focuses the heading and scrolls it into view; and
4. works by keyboard activation.

Browser Back removes/restores the fragment without a client reload and returns
focus to the workflow action that initiated the in-page navigation. The
snapshot, document and missing-data anchors use the same no-reload accessible
focus/scroll contract with their existing heading IDs.

The overview root is a Hebrew RTL `<nav>` with an accessible name. The five
phases are an ordered list. State text is visible text, not color-only status.
Every destination is keyboard-accessible, and loading/error explanations use
appropriate live/alert semantics without exposing another client's details.

## 9. Synthetic client journey

The mandatory journey uses existing behavior only:

1. Client A loads with M01 `incomplete`, missing `employment_status`, one
   snapshot and no retirement-planning document. Phase 1 is `INCOMPLETE`; the
   sole next action focuses and scrolls to `m01-case-foundation-heading`
   without a client reload; keyboard activation and Browser Back are proven.
2. The professional completes the existing M01 form. The accepted PUT response
   returns `completeness.status = complete` with empty missing/conflict arrays.
   The screen increments `readinessContextRevision`, immediately removes the
   prior readiness projection, aborts its request and starts exactly one fresh
   context GET. A same-client late response for the old revision is rejected.
3. Until the fresh response settles, readiness-derived phases are
   `NOT_EVALUATED`; the sole next action is the Phase 2 document anchor because
   the document collection is empty. Adding a document through the existing
   form makes both evidence collections non-empty; generic missing-data rows
   do not affect that transition.
4. The next current context response then determines the accurate subsequent
   action: Phase 3 when planning input is not ready, or Phase 4 when planning
   and target are ready. Neither the pre-save context nor a cross-client
   response may decide it.
5. The journey asserts that no workflow status was persisted, no comparison
   was called, no RMIGA result was shown, RMIGA remains `NOT_AUTHORIZED`, and
   Client B data never appeared.

This demonstrates a useful next-action change after an existing professional
action while preserving all authority boundaries.

## 10. Exact implementation allowlist

Future implementation is limited to:

1. `frontend/src/pages/ClientDetailScreen.tsx` — mount the overview and pass
   current-client facts already loaded by the screen.
2. `frontend/src/pages/ClientDetailScreen.test.tsx` — regression and integrated
   journey/lifecycle oracles.
3. `frontend/src/components/ProfessionalWorkflowOverview.tsx` — pure projection,
   one existing context read, navigation and stale-response protection.
4. `frontend/src/components/ProfessionalWorkflowOverview.test.tsx` — phase,
   priority, accessibility, isolation and negative oracles.

This allowlist is sufficient on the inspected base: `readContext`, all five
routes, client-context generation, authentication and client data already
exist. Importing those existing contracts requires no change to their files.
If future drift makes one unavailable, implementation must stop and request
the smallest exact allowlist amendment rather than silently modifying another
path.

No backend, API, route registration, model, schema, persistence, migration,
calculation, middleware, existing producer, shared hook, or unrelated UI file
may change.

## 11. Ordinary acceptance inventory

| ID | Required executable proof |
|---|---|
| `M01-WFH-AC-001` | The overview renders at the top of the successfully loaded current ClientDetailScreen and nowhere on loading/not-found/error state; package governance is exactly CLASS_A and not Complex Class A. |
| `M01-WFH-AC-002` | Exactly five phases render in fixed order with exact Hebrew titles and the canonical/dynamic destinations in Sections 6 and 8. |
| `M01-WFH-AC-003` | Complete M01 yields Phase 1 COMPLETE only for exact complete status and empty missing/conflict arrays. |
| `M01-WFH-AC-004` | Missing M01 facts yield INCOMPLETE with exact field IDs; conflicts yield BLOCKED; Phase 1 action updates the fragment, focuses/scrolls to the existing editable heading, supports keyboard/Back, and causes no client reload. |
| `M01-WFH-AC-005` | Phase 2 is INCOMPLETE when either evidence collection is empty and READY_TO_CONTINUE only when both have activity; generic missing-data rows never satisfy that rule. |
| `M01-WFH-AC-006` | Every Phase 2 condition selects the exact actionable snapshot/document/professional-source destination; collection failure is NOT_EVALUATED with no stale counts and an inspect/retry anchor. |
| `M01-WFH-AC-007` | Ready context yields Phase 3 COMPLETE; false readiness with blockers yields BLOCKED and preserves exact blocker order and identity. |
| `M01-WFH-AC-008` | False planning readiness without blockers yields INCOMPLETE; loading/error/abort yields NOT_EVALUATED. |
| `M01-WFH-AC-009` | Phase 4 is READY_TO_CONTINUE only when planning and target readiness are both true. |
| `M01-WFH-AC-010` | Phase 4 is BLOCKED when either readiness boolean is false and is never permanently COMPLETE. |
| `M01-WFH-AC-011` | RMIGA is visibly NOT_AUTHORIZED, has no numeric/UI result and creates no endpoint request. |
| `M01-WFH-AC-012` | Phase 5 is navigable and NOT_EVALUATED without inferred fixation readiness or completion. |
| `M01-WFH-AC-013` | Exactly one next action follows Section 7, including Phase 1 focus and all materially distinct Phase 2 route policies, in table-driven combinations. |
| `M01-WFH-AC-014` | All navigation uses only the validated active client ID; in-page anchors and the three routed phases resolve to existing destinations. |
| `M01-WFH-AC-015` | One context request is issued per mounted client/revision with an AbortSignal; each successful current M01/profile save increments the revision and causes exactly one fresh request with no retry or write. |
| `M01-WFH-AC-016` | Client change or successful relevant save immediately makes old readiness state ineligible, clears Phases 3/4 and readiness-derived action, and aborts the prior request before fresh state renders. |
| `M01-WFH-AC-017` | Generation, client and revision controls reject late success/failure under same-client post-save, A-to-B and A-to-B-to-A sequences. |
| `M01-WFH-AC-018` | Invalid/mismatched context client is rejected and cannot influence status or navigation. |
| `M01-WFH-AC-019` | The synthetic journey proves Phase 1 focus, Phase 2 document action, post-save invalidation/fresh context and an accurate next-action change without a workflow write or stale same/cross-client state. |
| `M01-WFH-AC-020` | Rendering and navigation produce no POST/PUT/PATCH/DELETE, comparison, RMIGA, storage or URL-state side effect. |
| `M01-WFH-AC-021` | Existing ClientDetailScreen M01/profile/collection/forms/links and stale-context tests remain green. |
| `M01-WFH-AC-022` | RTL, ordered navigation, visible state text, accessible name, keyboard focus/scroll, Browser Back and loading/error announcements are verified. |
| `M01-WFH-AC-023` | Governance inventory proves CLASS_A, COMPLEX_CLASS_A = NO, exactly four allowed implementation paths, independent audit and separate implementation authorization. |

Acceptance range: `M01-WFH-AC-001` through `M01-WFH-AC-023`; count: `23`.

## 12. Negative acceptance inventory

| ID | Prohibited outcome / required negative proof |
|---|---|
| `M01-WFH-NAC-001` | A sixth phase, missing/reordered phase or destination inconsistent with Sections 6 and 8 is rendered. |
| `M01-WFH-NAC-002` | COMPLETE is inferred from visiting a route, having any collection row, or running an ephemeral comparison. |
| `M01-WFH-NAC-003` | Arbitrary missing/advisory/collection/verification strings become downstream authority, or generic missing-data rows alone make Phase 2 ready for professional sources. |
| `M01-WFH-NAC-004` | A warning or general missing item is promoted to an authoritative planning blocker. |
| `M01-WFH-NAC-005` | Phase 4 is permanently COMPLETE or claims that RTICB comparison was persisted. |
| `M01-WFH-NAC-006` | RMIGA appears available, linked, calculated, previewed, accepted or implementation-authorized. |
| `M01-WFH-NAC-007` | Phase 5 implies fixation eligibility, completion, recommendation or authorization. |
| `M01-WFH-NAC-008` | More/fewer than one next action renders, priority skips an unmet phase, or Phase 1/2 action cannot inspect or resolve its selecting condition. |
| `M01-WFH-NAC-009` | A stale, aborted, mismatched-client, old-generation or old-revision context changes Phase 3, Phase 4 or the next action. |
| `M01-WFH-NAC-010` | A-to-B-to-A or same-client save permits a pre-transition response to populate the current workspace. |
| `M01-WFH-NAC-011` | Client A names, IDs, counts, blockers, errors or actions remain visible while Client B loads or after B failure. |
| `M01-WFH-NAC-012` | Rendering/status/navigation causes a write, retry, comparison, RMIGA call or persistence mutation; a successful save causes zero or multiple fresh context GETs. |
| `M01-WFH-NAC-013` | An unavailable context is coerced to ready, complete or blocked instead of NOT_EVALUATED. |
| `M01-WFH-NAC-014` | Status is conveyed by color alone, links are not keyboard-accessible, or RTL/accessibility structure regresses. |
| `M01-WFH-NAC-015` | In-page navigation reloads the client, loses editable state, breaks keyboard/Back focus, or existing screen/authentication/isolation behavior regresses. |
| `M01-WFH-NAC-016` | Any path outside the allowlist or accepted authority changes, or package governance is represented as Complex Class A or as weaker than Class A. |
| `M01-WFH-NAC-017` | Definition acceptance is treated as implementation, RMIGA acceptance, downstream authorization or production readiness. |

Negative range: `M01-WFH-NAC-001` through `M01-WFH-NAC-017`; count: `17`.

Material mutation evidence at a future authorized implementation must use an
unchanged ordinary oracle and prove PASS -> actual projection/guard mutation
reached -> FAIL -> restoration -> PASS for: M01 completeness/conflict
precedence; evidence non-authority; planning/target readiness mapping; Phase 4
non-completion; RMIGA NOT_AUTHORIZED; next-action priority; context-client
binding; post-save revision invalidation; same-client late-response rejection;
Phase 1 focus/no-reload; Phase 2 destination selection; and generation/abort
A-to-B-to-A isolation.

## 13. Stop conditions

Stop Definition acceptance or the affected future implementation path if:

1. `M01_WFH_BASE_OR_AUTHORITY_DRIFT` — master, M01, context or route contract
   differs materially from the inspected identity.
2. `M01_WFH_RMIGA_PENDING_DEFINITION_DISTURBED` — the pending RMIGA candidate
   would be merged, superseded, discarded or represented as accepted.
3. `M01_WFH_STATUS_REQUIRES_NEW_AUTHORITY` — a phase status requires a new
   professional, calculation or persisted workflow decision.
4. `M01_WFH_MISSING_INFORMATION_BLOCKING_AMBIGUOUS` — implementation would need
   to assume that an informational missing item blocks downstream use.
5. `M01_WFH_COMPARISON_COMPLETION_PERSISTENCE_REQUIRED` — implementation would
   require treating ephemeral RTICB output as permanent completion.
6. `M01_WFH_RMIGA_UI_REQUIRED` — useful delivery would require implementing or
   exposing pending RMIGA UI integration.
7. `M01_WFH_STALE_CONTEXT_ISOLATION_UNAVAILABLE` — AbortController and
   generation/client/revision binding cannot prevent same-client post-save or
   A-to-B-to-A leakage.
8. `M01_WFH_ROUTE_OR_DATA_CONTRACT_MISSING` — a required fixed/dynamic route,
   in-page focus target, browser-history behavior or accepted read contract is
   unavailable.
9. `M01_WFH_ALLOWLIST_INSUFFICIENT` — implementation requires a path outside
   the four-path allowlist; request the smallest exact amendment.
10. `M01_WFH_EXISTING_SCREEN_REGRESSION_REQUIRED` — integration requires
    weakening existing client, form, authentication or isolation behavior.
11. `M01_WFH_SCOPE_EXPANSION_REQUIRED` — implementation requires a new API,
    backend service, persistence, migration, calculation, route or deployment.
12. `M01_WFH_UNRESOLVED_PROFESSIONAL_DECISION` — the UI would have to interpret
    readiness as advice, eligibility, adequacy, funding or authorization.

Stop-condition range: item 1 through item 12; count: `12`.

## 14. Decisions and next gate

No unresolved technical or professional blocker remains in this Definition.
The explicit choice not to derive a universal Phase 2 completion/blocking state
from free-form collection and missing-information strings, together with the
exact evidence-action routing policy and post-save context revision, resolves
the material ambiguities without weakening accepted downstream readiness.

Independent WORK must perform a deep Definition audit against this exact file.
Acceptance would freeze semantics only; implementation still requires a
separate authorization after Definition closure. The pending RMIGA Definition
remains separate and pending.

DEFINITION_ACCEPTANCE = PENDING_FOCUSED_REAUDIT

IMPLEMENTATION = NOT_AUTHORIZED

DOWNSTREAM = NOT_AUTHORIZED

PENDING_RMIGA_DEFINITION = PRESERVED

PRODUCTION_READINESS = NOT_CLAIMED

M01_INTERNAL_PROFESSIONAL_CASE_WORKFLOW_HUB_DEFINITION_CANDIDATE_READY_FOR_INDEPENDENT_AUDIT
