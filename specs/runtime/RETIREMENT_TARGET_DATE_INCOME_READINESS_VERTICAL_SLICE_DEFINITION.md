# RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE — Definition

## 1. Status and authority

- Classification: `CLASS A / COMPLEX CLASS A`.
- Definition base: `93058f3f4e6a54f7e5c02254a6fd444f651326d4`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- This document defines an application workflow over the already accepted planning-input,
  retirement monthly income target (RIT), retirement target-date income source admission
  (RTISA), and retirement target-date income comparison basis (RTICB) authorities.
- It creates no new professional calculation, fingerprint, persistence, or source authority.
- Owner clarification fixes the deployment model as one professional user and one shared client
  workspace. This Definition includes the narrow authentication boundary required for that model.
- Implementation remains `NOT_AUTHORIZED`; this document is Definition authority only.

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
| Dependencies/configuration | `backend/requirements.txt` contains no password-verification or session-signing dependency; `.gitignore` excludes `.env`; `.env.example` has no auth variables | Implementation must add pinned maintained libraries and variable names only, never production credential values |
| Deployment | No `Dockerfile`, Railway configuration, `Procfile`, or reverse-proxy contract is present; current CORS is hard-coded for local Vite | Railway startup, HTTPS-origin, proxy, and CORS configuration must be delivered and tested explicitly |

No backend API route currently exposes RIT assessment/confirmation, RTISA, or RTICB.
All currently registered client routes accept a path `client_id`; database filters prevent
cross-client row lookup but do not establish that the caller may access that client.

## 3. Single-user authentication authority

### 3.1 Owner decision and current verdict

The owner fixes this application as one professional user and one workspace containing every
client. There are no roles, registrations, user-management screens, or per-client ownership
grants. This closes the earlier ambiguity about the identity/permission model. The repository still
contains no authentication implementation, so authentication must be delivered as part of a later
authorized implementation of this Definition before internet deployment.

The existing RIT parameter `trusted_professional_actor` remains an enforcement boundary. Direct
service tests supplying a string, a path `client_id`, browser state, or caller-authored headers are
not authentication.

### 3.2 Narrow server-side mechanism

The implementation contract is a single credential plus stateless signed server session:

1. `AUTH_USERNAME`, `AUTH_PASSWORD_HASH`, `AUTH_ACTOR_ID`, `AUTH_SESSION_SECRET`, and
   `AUTH_ALLOWED_ORIGIN` are supplied only as Railway service/shared variables. They are absent
   from source, Git, frontend bundles, API responses, logs, and exception text.
2. `AUTH_PASSWORD_HASH` is an Argon2id verifier produced out of band. The application never stores
   or receives a production plaintext password except transiently in the TLS-protected login
   request, and never persists it. A pinned maintained Argon2 implementation is required.
3. `AUTH_SESSION_SECRET` is an independently generated high-entropy secret shared by every backend
   replica. A pinned maintained timed-signing implementation is required; handwritten token crypto
   is forbidden.
4. Successful login creates a signed, absolute-expiry session containing only a contract version,
   `AUTH_ACTOR_ID`, issued time, expiry time, and a non-secret session nonce. It contains no password
   or client data. Signature, exact shape, actor equality, and expiry are verified on every request.
5. The session is transported only in `__Host-retire_v2_session`, with `Secure`, `HttpOnly`,
   `Path=/`, no `Domain`, and `SameSite=Lax`. The default absolute lifetime is eight hours and is
   bounded by server configuration; there is no sliding extension on ordinary API calls.
6. Session state is not held in process memory, filesystem, or a replica-local cache. Shared
   configuration makes sessions survive process restart and work across replicas without sticky
   routing. Rotating `AUTH_SESSION_SECRET` invalidates all outstanding sessions.
7. Logout clears the cookie with matching attributes and an expired/max-age-zero value. It ends the
   browser's session; global revocation is performed by secret rotation. No claim of per-token
   server-side revocation is made.
8. Incorrect username and password produce the same generic response. Username comparison is
   constant-time where applicable, and password verification performs a real/dummy Argon2id check
   so account existence is not exposed by timing. Responses and logs never echo credentials.

### 3.3 Route protection and CSRF/origin boundary

- Authentication middleware protects every `/api` route, including all existing client APIs, not
  only the new vertical-slice router.
- The only unauthenticated application endpoints are `POST /api/auth/login`, a data-free health
  endpoint, and narrowly required CORS preflight. API documentation is disabled in production or
  protected by the same middleware.
- `GET /api/auth/session` returns only authenticated state and the non-secret canonical actor label
  needed by the UI. `POST /api/auth/logout` requires a valid session and clears it.
- Every unsafe authenticated request requires an exact allowed `Origin` and an anti-CSRF header
  bound to the verified signed session. The anti-CSRF value is returned after login/session check,
  kept in browser memory, and is never accepted as authentication by itself.
- CORS uses the exact HTTPS `AUTH_ALLOWED_ORIGIN`, `allow_credentials=true`, and no wildcard origin,
  method, or header expansion beyond the application contract. Frontend requests use
  `credentials: "include"`.
- Authentication establishes access to the single workspace; there is no per-client permission
  lookup. Path `client_id` remains mandatory and every producer retains existence, client-ID
  equality, row ownership, response identity, stale, and fingerprint checks. Authentication never
  repairs a nonexistent or incorrectly addressed record.
- `AUTH_ACTOR_ID` is read from verified server configuration and placed on the authenticated
  request context. The RIT confirmation route passes that exact value as
  `trusted_professional_actor`. JSON, query, path, cookie payload fields not covered by the server
  signature, arbitrary headers, local storage, and display names cannot override it.

### 3.4 Railway deployment contract

Repository evidence contains no Railway config, Dockerfile, reverse proxy, or production CORS
configuration. Railway deployment configuration is therefore an implementation/deployment
deliverable, not assumed existing evidence.

The deployment facts used here are Railway's official public-networking, variables, and
multi-replica guidance: `https://docs.railway.com/networking/public-networking`,
`https://docs.railway.com/variables`, and
`https://docs.railway.com/deployments/optimize-performance`.

- Railway public networking terminates HTTPS with managed certificates; production access is HTTPS
  only. Trusted proxy handling must be configured narrowly so arbitrary forwarded-protocol headers
  cannot make a direct insecure request appear secure.
- Railway variables hold the credential verifier, actor ID, signing secret, exact allowed origin,
  and database URL. No actual password or secret value is added to `.env.example`.
- Railway does not provide sticky sessions across replicas. The stateless signed session therefore
  has identical behavior after restart and on any replica when all replicas receive the same sealed
  variables.
- Frontend and backend must be deployed under the same browser site (preferably one HTTPS origin or
  controlled subdomains). If that cannot be achieved, deployment is blocked until cookie
  `SameSite`, CORS, CSRF, and origin behavior is independently proven for the actual domains.
- Startup fails closed when production auth variables are missing, empty, malformed, use a
  plaintext-looking password instead of an Argon2id verifier, contain an invalid actor, or specify
  a non-HTTPS production origin. Local/test configuration is explicit and cannot become a
  production fallback.

## 4. Exact package scope

Once implementation is separately authorized, this package may add only:

1. The single-user authentication configuration, credential verifier, timed session signer,
   authentication/CSRF middleware, and authenticated request context defined in section 3.
2. Login, session-status, and logout routes; narrowly required health behavior; exact production
   CORS/origin configuration; and startup validation of the authentication variables.
3. A backend route module for an authenticated planning-context read, RIT assessment, RIT
   confirmation, and RTICB execution.
4. Request/response adapter schemas that preserve the accepted service contracts and registration
   of the new router behind the global authentication boundary.
5. A frontend login/session/logout adapter, an authentication gate, a Hebrew RTL readiness screen,
   a route under the selected client, and a link from the existing Planning Input workflow.
6. Pinned maintained password-verification and timed-signing dependencies strictly needed by the
   contract, plus Railway deployment/configuration documentation without credential values.
7. Focused authentication, backend, API, frontend, integration, and required PostgreSQL tests.

No user/session database model, schema migration, role model, registration, user-management UI,
per-client permission table, professional service, accepted fingerprint, or calculation-logic
change is in scope. RTISA remains an internal RTICB producer and is not exposed as a second public
workflow.

## 5. API contract

All four routes are under:

`/api/clients/{client_id}/retirement-income-readiness`

Every route first authenticates the one configured professional and establishes the single
workspace request context. There is no per-client permission decision. After authentication, the
route validates the positive path `client_id`, confirms that the addressed client and every loaded
record belong to that ID, and rejects missing or mismatched identities before returning
professional state.

### 5.1 Read current planning context

`GET /context`

- Calls the existing planning-input reader with the route session and authenticated workspace path
  `client_id`.
- Returns only existing authority fields needed by this workflow: `client_id`,
  `planning_calculation_input_fingerprint`, `planning_input_ready`, the current
  `retirement_target_date` and `retirement_target_ready`, and the existing `blocking_facts`.
- It creates no new fingerprint or interpretation. The values must equal the existing Planning
  Input result byte-for-byte/value-for-value.
- The route owns this simple read boundary and rolls back its session in `finally`, matching the
  existing Planning Input read route. It opens no second session.
- The screen must not call the general Planning Input endpoint as a substitute for this exact
  context adapter. Both endpoints are protected by the global authentication boundary; a
  navigation link is convenience only and is never treated as authentication.

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

The route injects path `client_id`, obtains `trusted_professional_actor` only from the verified
server-side authenticated request context, and calls RIT `confirm` exactly once. An actor field is
forbidden. An extra field, path/body client identity conflict, or malformed value fails closed.
The route does not own or wrap the RIT write transaction. CAS, retry, stale-context, exact-money,
confirmation, timestamp, and fingerprint semantics remain those of RIT.

### 5.4 Execute comparison readiness

`POST /comparison`

The browser body contains exactly:

- `expected_planning_calculation_input_fingerprint`
- `expected_retirement_target_date`

The adapter preserves extra fields long enough to fail the accepted exact RTICB request schema,
overwrites any attempted caller `client_id` with the authenticated path identity, and invokes RTICB
`assess` exactly once with the complete accepted request. The result, including failure results,
ordered `reason_codes`, ordered blockers, source partitions, fingerprints, and readiness, is
returned without API reclassification. RTICB owns and closes its read snapshot. No result is
persisted.

Application validation failures retain accepted codes. Transport mapping may distinguish
authentication, malformed HTTP, not-found addressing, and unavailable infrastructure, but must not turn a
professional `NOT_READY`, `NORMALIZATION_REQUIRED`, `BASIS_UNRESOLVED`, or `EXCLUDED` result into
invented success, advice, or another professional state.

## 6. Frontend workflow and states

The new route is:

`/clients/:clientId/retirement-income-readiness`

Planning Input adds one explicit navigation link. The screen validates a positive integer route
client ID and keeps every request scoped to it. A response with another `client_id` is rejected.
Late responses from a previously selected client are discarded with `AbortController` plus an
active-generation guard.

Before any workspace screen is shown, the frontend calls the session-status endpoint with
credentials included. An unauthenticated response shows the Hebrew login screen and clears all
cached client/professional state. Login submits only username and password over HTTPS; neither is
stored in local storage, session storage, URL state, logs, or source. After authentication the
frontend retains the returned anti-CSRF value only in memory, supplies it on unsafe requests, and
never supplies a professional actor. Logout calls the protected logout endpoint, clears all
in-memory state regardless of response outcome, and returns to the login screen. A session-expired
response during any request performs the same local clearing and never renders retained client
data as current.

### 6.1 Load sequence

1. Load the authenticated context endpoint, whose facts are sourced from existing Planning Input.
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
| `AUTH_CHECKING` | Application startup or explicit post-login verification | Login or authenticated workspace |
| `LOGIN_REQUIRED` | No valid server session or session expired | Submit credentials only |
| `AUTHENTICATING` | One login request in flight | Authenticated workspace or generic login failure |
| `AUTHENTICATION_FAILED` | Incorrect credential or rejected session | Generic Hebrew error; retry login |
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

## 7. Database transaction and authentication-session ownership

- Authentication sessions are stateless signed cookies and are distinct from SQLAlchemy database
  sessions. No request handler, service, or frontend state creates server-side authentication
  session durability.
- Authentication and CSRF validation complete before a protected route invokes a professional
  service or discloses whether a `client_id` exists.
- All replicas verify the same token contract with the same Railway-provided signing secret and
  actor ID; no replica affinity is required.

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

- Missing, malformed, expired, wrongly signed, wrong-version, or wrong-actor sessions return the
  same unauthenticated response before protected route/service execution.
- Incorrect login credentials return one generic failure and create no cookie or authenticated
  context. Logout of a valid session expires the cookie; replay after expiry or secret rotation is
  rejected.
- Missing/mismatched Origin or anti-CSRF proof on an unsafe authenticated request fails before the
  mutation. CORS success, a cookie-shaped value, an arbitrary actor header, or a CSRF value alone
  never authenticates a request.
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

### 9.1 Authentication, actor binding, and client addressing

| Case | Expected oracle |
|---|---|
| No/invalid/expired authenticated session | Uniform unauthenticated response before service invocation and client disclosure |
| Caller supplies actor in body/query/header/local state | Rejected or ignored as untrusted; persisted actor equals configured `AUTH_ACTOR_ID` only |
| Caller supplies another client ID in body | Exact-schema/identity failure; path identity remains controlling and no mismatched record is returned |
| Authenticated caller addresses nonexistent client | Not-found/fail-closed response with no professional result or mutation |
| Authenticated caller addresses existing client | Service called once with exact path client and server-bound canonical actor |
| Late response after navigation A→B | A result is discarded and never rendered under B |

### 9.2 Target assessment and confirmation

Positive cases cover creation at expected version zero, exact retry of the immediately produced
revision, current assessment, both income bases, both price bases, and explicit permitted source
kinds. Negative/malformed/stale cases cover missing amount/bases/date, invalid precision, invalid
real reference date, extra/missing fields, stale planning fingerprint, stale retirement date,
wrong expected version, conflicting retry payload, exhausted version, missing confirmation,
tampered stored fingerprint, and wrong-client record observation. Oracles assert exact status/code,
persisted values, actor from the server-authenticated context, server timestamp, version,
fingerprints, rollback, and no partial write.

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

### 9.4 Authentication and Railway security acceptance

Focused tests must prove:

1. Correct configured username plus matching Argon2id password creates only the expected signed
   cookie attributes and an authenticated session; incorrect username, incorrect password, and
   malformed input return the same generic failure and create no session.
2. Passwords, password hashes, signing secrets, and actual production values are absent from Git,
   frontend output, response bodies, and logs. Tests use disposable non-production values.
3. Every registered `/api` route is denied without a verified session except the exact login,
   data-free health, and preflight allowlist; newly registered routes cannot silently bypass this
   inventory assertion.
4. Tampered, expired, wrong-version, wrong-actor, and wrong-secret cookies are rejected. Valid
   sessions work after application-process restart and across two verifier instances sharing the
   same configuration, without an in-memory session store or sticky routing.
5. Logout expires the cookie with matching scope attributes; the cleared/expired cookie cannot
   access a protected route. Signing-secret rotation invalidates a previously valid session.
6. Unsafe requests reject absent or incorrect Origin and anti-CSRF proof before mutation. A valid
   CSRF value without a valid signed session, or a valid session with forged actor input, fails
   closed.
7. The RIT confirmation service receives exactly configured `AUTH_ACTOR_ID` after login; changing
   JSON, query, header, frontend state, unsigned cookie content, username case, or display text
   cannot change `trusted_professional_actor`.
8. Authentication grants the single workspace, not a per-client grant. Existing positive client
   IDs work only when the addressed client exists; nonexistent clients, path/body conflicts,
   wrong-client stored rows, and response `client_id` mismatches remain rejected.
9. Production startup fails closed for each missing/malformed authentication variable, a
   plaintext-looking password value, non-HTTPS origin, weak/invalid signing secret, or invalid
   actor. Exact configured HTTPS origin and credentialed CORS behavior are accepted.
10. Frontend tests prove initial session check, generic login failure, successful login, included
    credentials, in-memory CSRF handling, logout state clearing, session-expiry clearing, and no
    actor/credential persistence or client-data display while unauthenticated.

### 9.5 Mutation controls

Material production-path mutations must be killed for:

1. accepting a protected API request without a verified signed session;
2. replacing configured actor with caller actor;
3. omitting session expiry/signature/version/actor verification;
4. omitting unsafe-method Origin or anti-CSRF enforcement;
5. storing authentication sessions in replica-local memory or filesystem;
6. invoking a professional service before authentication;
7. skipping client existence/path/row/response identity validation;
8. dropping expected version/fingerprint/date;
9. automatically retrying a target conflict;
10. wrapping RIT or RTICB in another transaction;
11. opening a hidden second database session;
12. persisting an RTICB result;
13. treating normalization/unresolved/excluded as directly comparable;
14. reordering or dropping server reasons/blockers;
15. accepting stale A response on client B;
16. retaining client/comparison state after logout, expiry, or identity changes.

Each mutation test requires reached-path evidence, failure of the ordinary production-path oracle,
restoration, and a passing ordinary oracle. Mock-only assertions disconnected from the route/screen
path do not count.

## 10. Explicit exclusions

This package excludes income aggregation, normalization, income gap, funding/coverage, resource
eligibility, withdrawals, scenarios, allocation, cashflow, tax optimization, new professional
fingerprints, derived RTICB persistence, immutable planning-run history, M11–M14, frozen 02M,
excluded M08E, and any production-readiness claim. It does not expose downstream execution or
change RIT, RTISA, RTICB, Planning Input, pension portfolio, or target-date professional semantics.

It also excludes multi-user tenancy, professional roles, registration, password-reset/email flows,
user administration, per-client ownership partitioning, an external identity provider, an
authentication-session database/cache, and an actual production username/password/secret. A more
complex identity platform requires a later evidence-backed owner decision and is not implied by
this single-user contract.

## 11. Feasibility, blockers, and authorization gate

The application composition, authentication boundary, API adapters, frontend flow, test oracles,
and transaction boundaries are technically feasible using existing accepted service contracts.

`RTDIR-VS-PREREQ-001 — TRUSTED_PROFESSIONAL_PRINCIPAL_AND_CLIENT_AUTHORIZATION_NOT_ESTABLISHED`
is closed at Definition level by the owner's single-user decision and sections 3 and 9. No
per-client ownership authorization is required. No remaining Owner Decision is required for this
Definition.

Implementation prerequisites remain technical and do not authorize implementation: select and pin
maintained Argon2id and timed-signing libraries; provision Railway variables out of band; establish
the actual Railway frontend/backend HTTPS domains; configure trusted proxy/origin/CORS behavior;
and independently verify the focused security matrix on the deployed topology. No actual
production password, hash, actor value, or signing secret is defined here.

Acceptance of this corrected Definition does not itself authorize authentication, the vertical
slice, any downstream package, or production deployment. Implementation is `NOT_AUTHORIZED`,
downstream is `NOT_AUTHORIZED`, and production readiness is `NOT_CLAIMED`.

Definition candidate status: `COMPLETE_PENDING_INDEPENDENT_DEFINITION_ACCEPTANCE`.
