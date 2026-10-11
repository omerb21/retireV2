# RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE — Definition

## 1. Status and authority

- Classification: `CLASS A / COMPLEX CLASS A`.
- Definition base: `93058f3f4e6a54f7e5c02254a6fd444f651326d4`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- This document defines an application workflow over the already accepted planning-input,
  retirement monthly income target (RIT), retirement target-date income source admission
  (RTISA), and retirement target-date income comparison basis (RTICB) authorities.
- It creates no new professional calculation, fingerprint, persistence, or source authority.
- Implementation is blocked until the prerequisite in section 3 is separately defined,
  accepted, implemented, and available to the routes in this package.

## 2. Repository evidence and current boundary

The evidence sweep established the following current producer and consumer path.

| Surface | Current evidence | Ownership consequence |
|---|---|---|
| Planning input | `GET /api/clients/{client_id}/retirement-planning-input` calls `planning_input_service.read`, derives projection basis, and rolls its route session back | Existing read endpoint supplies `client_id`, current planning identity and retirement date facts; it is not an authenticated client boundary |
| Retirement date | `PUT .../target-date` calls `retirement_target_service.set_target` | Existing date decision is separate from monthly-income target confirmation |
| RIT assessment | `retirement_monthly_income_target_service.assess(db, client_id)` | Public service owns a fresh transaction, client lock, sticky stale transition, retries, and commit/rollback |
| RIT confirmation | `retirement_monthly_income_target_service.confirm(db, complete_command, trusted_professional_actor)` | Public service owns its fresh write transaction, row/client locking, CAS, retries, commit/rollback, server time, and persisted actor |
| RTISA | `retirement_target_date_income_source_admission_service.read` and `read_in_snapshot` | Public reader owns its snapshot; `read_in_snapshot` is only for a caller that already owns that snapshot |
| RTICB | `retirement_target_date_income_comparison_basis_service.assess(db, request)` | Public service owns one fresh repeatable-read/read-only snapshot, composes RIT `assess_in_snapshot` and RTISA `read_in_snapshot`, and rolls back its snapshot |
| Frontend | `/clients/:clientId/planning-input` uses `planningInputApi.ts`; no RIT, RTISA, or RTICB adapter/screen/route exists | The new workflow must be linked from Planning Input and must display server results without deriving classifications |
| Authentication | `main.py` registers CORS and routers only; no authentication middleware, security dependency, request principal, user session, or permission resolver exists | A path `client_id`, database existence check, request field, browser state, or header string is not authorization |

No backend API route currently exposes RIT assessment/confirmation, RTISA, or RTICB.
All currently registered client routes accept a path `client_id`; database filters prevent
cross-client row lookup but do not establish that the caller may access that client.

## 3. Blocking trusted-professional prerequisite

### 3.1 Verdict

The current repository is category **D — no established actor authority**.

- There is no authenticated server-side principal (category A).
- There is no configured, server-controlled identity contract that represents the responsible
  professional for this workflow (category B).
- Existing browser/request actor strings are category C and are not trusted.
- Fixed technical workflow actors elsewhere in the repository identify a technical workflow,
  not the human professional required by RIT confirmation, and cannot be substituted silently.

The name `trusted_professional_actor` on the RIT service parameter is an enforcement boundary,
not evidence that a trusted source exists. Direct service tests supplying a string do not create
request authentication.

### 3.2 Smallest prerequisite contract

A separately accepted prerequisite must provide a FastAPI request dependency with this semantic
contract, without this package choosing cookie, token, proxy, directory, or identity-provider
technology:

1. Resolve a request-scoped authenticated principal from server-verified evidence.
2. Return an immutable canonical `professional_actor_id`, 1–128 characters, suitable for the
   existing RIT actor validation and stable audit attribution.
3. Authorize that principal for the exact path `client_id` before any client data or service is
   accessed.
4. Fail closed with an authentication failure when no verified principal exists and an
   authorization failure when the principal lacks access.
5. Never accept, override, or fall back to actor or permission data from JSON, query parameters,
   path parameters, arbitrary headers, local storage, frontend state, or display names.
6. Make actor provenance and client authorization independently testable through dependency
   override, while production wiring cannot be overridden by caller input.

The owner must authorize the identity/permission source and its operational trust model. Until
that happens, the routes defined below must not be registered in production. Returning a fixed
professional actor, accepting a browser actor, or exposing an unauthenticated route is forbidden.

## 4. Exact package scope

After the prerequisite is satisfied, this package may add only:

1. A backend route module for an authorized planning-context read, RIT assessment, RIT
   confirmation, and RTICB execution.
2. Request/response adapter schemas that preserve the accepted service contracts.
3. Registration of that router after the trusted-principal dependency is available.
4. A frontend API adapter and a Hebrew RTL readiness screen.
5. A route under the selected client and a link from the existing Planning Input workflow.
6. Focused backend, API, frontend, integration, and required PostgreSQL tests.

No model, schema, migration, professional service, accepted fingerprint, or calculation logic is
in scope. RTISA remains an internal RTICB producer and is not exposed as a second public workflow.

## 5. API contract

All four routes are under:

`/api/clients/{client_id}/retirement-income-readiness`

Every route first resolves the trusted principal and authorizes it for `client_id`. Authorization
must happen before client existence or professional state is disclosed.

### 5.1 Read current planning context

`GET /context`

- Calls the existing planning-input reader with the route session and authorized `client_id`.
- Returns only existing authority fields needed by this workflow: `client_id`,
  `planning_calculation_input_fingerprint`, `planning_input_ready`, the current
  `retirement_target_date` and `retirement_target_ready`, and the existing `blocking_facts`.
- It creates no new fingerprint or interpretation. The values must equal the existing Planning
  Input result byte-for-byte/value-for-value.
- The route owns this simple read boundary and rolls back its session in `finally`, matching the
  existing Planning Input read route. It opens no second session.
- The screen must not call the currently unauthenticated Planning Input endpoint as a substitute
  for this authorized context route. A navigation link from that page is convenience only and is
  never treated as authorization.

### 5.2 Assess target

`GET /target`

- Calls `retirement_monthly_income_target_service.assess(db, client_id)` exactly once.
- Returns the accepted RIT result unchanged.
- The route does not begin, commit, roll back, retry, lock, or wrap the service transaction.
- RIT's sticky stale transition remains owned by RIT.

### 5.3 Confirm target

`PUT /target`

The browser body contains exactly the accepted RIT command fields except `client_id`:

- `expected_record_version`
- `expected_planning_calculation_input_fingerprint`
- `expected_retirement_target_date`
- `monthly_amount`
- `income_basis`
- `price_basis`
- `price_reference_date`
- `source_kind`

The route injects path `client_id`, obtains `trusted_professional_actor` only from the prerequisite,
and calls RIT `confirm` exactly once. An actor field is forbidden. An extra field, path/body client
identity conflict, or malformed value fails closed. The route does not own or wrap the RIT write
transaction. CAS, retry, stale-context, exact-money, confirmation, timestamp, and fingerprint
semantics remain those of RIT.

### 5.4 Execute comparison readiness

`POST /comparison`

The browser body contains exactly:

- `expected_planning_calculation_input_fingerprint`
- `expected_retirement_target_date`

The adapter preserves extra fields long enough to fail the accepted exact RTICB request schema,
overwrites any attempted caller `client_id` with the authorized path identity, and invokes RTICB
`assess` exactly once with the complete accepted request. The result, including failure results,
ordered `reason_codes`, ordered blockers, source partitions, fingerprints, and readiness, is
returned without API reclassification. RTICB owns and closes its read snapshot. No result is
persisted.

Application validation failures retain accepted codes. Transport mapping may distinguish
authentication/authorization, malformed HTTP, and unavailable infrastructure, but must not turn a
professional `NOT_READY`, `NORMALIZATION_REQUIRED`, `BASIS_UNRESOLVED`, or `EXCLUDED` result into
invented success, advice, or another professional state.

## 6. Frontend workflow and states

The new route is:

`/clients/:clientId/retirement-income-readiness`

Planning Input adds one explicit navigation link. The screen validates a positive integer route
client ID and keeps every request scoped to it. A response with another `client_id` is rejected.
Late responses from a previously selected client are discarded with `AbortController` plus an
active-generation guard.

### 6.1 Load sequence

1. Load the authorized context endpoint, whose facts are sourced from existing Planning Input.
2. Load RIT target assessment.
3. Display target state and editable fields from the accepted authority.
4. Execute RTICB only after the target is current and the screen has the exact current planning
   fingerprint and retirement target date.
5. Present RTICB output verbatim through display labels only.

No request is automatically retried after a write/CAS/stale conflict. An explicit refresh may
repeat reads. After a successful confirmation, the screen discards all prior results and reloads
Planning Input, target assessment, and then RTICB with the newly observed identities.

### 6.2 Explicit states

| UI state | Entry condition | Permitted transition |
|---|---|---|
| `LOADING_CONTEXT` | Initial load or explicit refresh | Context unavailable/not ready, target state, or technical failure |
| `CONTEXT_NOT_READY` | Planning identity or retirement date is absent/not ready | Navigate to Planning Input or explicit refresh |
| `TARGET_MISSING` | RIT authority is `MISSING` | Edit and explicitly confirm |
| `TARGET_INVALID` | RIT authority is invalid/unavailable | Display exact blockers; explicit refresh only |
| `TARGET_STALE` | Planning fingerprint/date changed or reconfirmation required | Edit/reconfirm using newly loaded expectations |
| `TARGET_CURRENT` | Confirmed current RIT target | Explicit comparison execution |
| `EDITING_TARGET` | Local unsaved fields | Cancel locally or submit confirmation |
| `CONFIRMING_TARGET` | One write in flight | Success reload, CAS/stale conflict, or technical failure |
| `CONFIRMATION_CONFLICT` | Version/context conflict | No automatic retry; explicit refresh required |
| `COMPARISON_LOADING` | One explicit/current comparison request | One server result or technical failure |
| `DIRECTLY_COMPARABLE` | RTICB ready and no blockers | Display source classifications and exact reasons |
| `NORMALIZATION_REQUIRED` | Exact RTICB blocker/state | Display only; no normalization or advice |
| `BASIS_UNRESOLVED` | Exact RTICB blocker/state | Display only; no inferred basis |
| `UPSTREAM_NOT_READY` | Target/RTISA/identity failure result | Display exact stage/code and refresh/navigation options |
| `TECHNICAL_FAILURE` | Network/server/infrastructure failure | Explicit retry/refresh only |

`EXCLUDED` entries remain visible with their server-provided admission state and exact ordered
reasons. The UI does not omit them, include them in a total, or reinterpret them.

## 7. Transaction and session ownership

- One FastAPI `get_db` session is supplied per request.
- The context route owns only its direct planning-input read and closes it with rollback.
- The target assessment route delegates transaction ownership entirely to RIT `assess`.
- The target confirmation route delegates transaction ownership entirely to RIT `confirm`.
- The comparison route delegates snapshot ownership entirely to RTICB `assess`; RTICB alone calls
  RIT/RTISA snapshot helpers.
- Routes must not call the public RIT, RTISA, or RTICB owners inside another transaction.
- Routes must not instantiate `SessionLocal`, call `get_db` manually, create an engine, or hide a
  second session.
- The frontend orchestrates separate HTTP requests; there is no cross-request transaction.
- Target confirmation is the only new workflow write. Comparison is read-only and leaves no
  persisted result or history.

PostgreSQL is required only to prove RIT lock/CAS/retry behavior, RTICB repeatable-read snapshot
behavior, cross-session concurrency, and absence of partial writes. API mapping and frontend state
tests may use existing non-PostgreSQL fixtures where they do not claim database concurrency.

## 8. Failure and refresh contract

- Stale planning fingerprint or retirement date fails closed using accepted RIT/RTICB semantics.
- A target version conflict is never overwritten or automatically replayed.
- Missing confirmation remains missing; the browser cannot synthesize actor, timestamp, state, or
  version.
- RTISA unavailable/not-ready is displayed through the RTICB failure result and cannot be bypassed.
- Unknown or malformed service result shape is a technical failure, not a professional result.
- Network failure preserves existing screen data as visibly stale/non-authoritative and offers an
  explicit retry.
- Any input/target mutation invalidates the displayed comparison until a fresh server execution
  succeeds with matching identities.
- The UI may translate known codes to Hebrew labels, but must retain the exact code and deterministic
  ordering and must use a neutral fallback for an unknown code.

## 9. Acceptance matrices

### 9.1 Actor and client isolation

| Case | Expected oracle |
|---|---|
| No authenticated principal | Fail before service invocation and before client disclosure |
| Principal lacks requested client permission | Fail before service invocation; another client's data is absent |
| Caller supplies actor in body/query/header | Rejected or ignored as untrusted; persisted actor equals dependency principal only |
| Caller supplies another client ID in body | Path-authorized client controls; exact-schema failure, never cross-client access |
| Authorized principal/client | Service called once with exact authorized client and canonical actor |
| Late response after navigation A→B | A result is discarded and never rendered under B |

### 9.2 Target assessment and confirmation

Positive cases cover creation at expected version zero, exact retry of the immediately produced
revision, current assessment, both income bases, both price bases, and explicit permitted source
kinds. Negative/malformed/stale cases cover missing amount/bases/date, invalid precision, invalid
real reference date, extra/missing fields, stale planning fingerprint, stale retirement date,
wrong expected version, conflicting retry payload, exhausted version, missing confirmation,
tampered stored fingerprint, and wrong-client record observation. Oracles assert exact status/code,
persisted values, actor from principal, server timestamp, version, fingerprints, rollback, and no
partial write.

### 9.3 RTICB presentation

The API/frontend matrix covers:

- ready/directly comparable;
- normalization required;
- basis unresolved;
- every accepted `EXCLUDED` entry presentation;
- target missing/stale/invalid/unavailable;
- RTISA unavailable/not ready;
- planning fingerprint mismatch;
- retirement-date mismatch;
- malformed request and malformed upstream result;
- source coverage/schema/fingerprint failures;
- exact source order, partitions, `comparison_state`, ordered `reason_codes`, blockers, and
  readiness.

Independent frontend oracles compare rendered rows/codes to fixed fixtures, never to frontend
classification helpers. Independent API oracles spy on exact service arguments, transaction calls,
and returned payload identity. Browser integration covers navigation from Planning Input, explicit
confirmation, refresh, conflict, client switch, and comparison display.

### 9.4 Mutation controls

Material production-path mutations must be killed for:

1. replacing dependency actor with caller actor;
2. skipping client authorization;
3. invoking a service before authorization;
4. dropping expected version/fingerprint/date;
5. automatically retrying a target conflict;
6. wrapping RIT or RTICB in another transaction;
7. opening a hidden second session;
8. persisting an RTICB result;
9. treating normalization/unresolved/excluded as directly comparable;
10. reordering or dropping server reasons/blockers;
11. accepting stale A response on client B;
12. retaining a comparison after input or target identity changes.

Each mutation test requires reached-path evidence, failure of the ordinary production-path oracle,
restoration, and a passing ordinary oracle. Mock-only assertions disconnected from the route/screen
path do not count.

## 10. Explicit exclusions

This package excludes income aggregation, normalization, income gap, funding/coverage, resource
eligibility, withdrawals, scenarios, allocation, cashflow, tax optimization, new professional
fingerprints, derived RTICB persistence, immutable planning-run history, M11–M14, frozen 02M,
excluded M08E, and any production-readiness claim. It does not expose downstream execution or
change RIT, RTISA, RTICB, Planning Input, pension portfolio, or target-date professional semantics.

## 11. Feasibility, blockers, and authorization gate

The application composition, API adapters, frontend flow, test oracles, and transaction boundaries
are technically feasible using existing accepted service contracts. One independent blocker
remains:

`RTDIR-VS-PREREQ-001 — TRUSTED_PROFESSIONAL_PRINCIPAL_AND_CLIENT_AUTHORIZATION_NOT_ESTABLISHED`

This is a security/identity prerequisite, not a professional calculation ambiguity. The owner must
authorize the prerequisite trust source and permission model. No implementation of this vertical
slice, including route registration, is authorized until that prerequisite is independently
accepted and implemented. No downstream package or production readiness follows from acceptance
of this Definition.

Definition candidate status: `COMPLETE_WITH_EXPLICIT_BLOCKED_PREREQUISITE`.

