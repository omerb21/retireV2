# RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE — Consolidated Definition

## 1. Status, authority, and package boundary

- Package: `RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE` (`RTDIR-VS`).
- Classification: `CLASS A / COMPLEX CLASS A`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Definition base: `93058f3f4e6a54f7e5c02254a6fd444f651326d4`.
- This document is the consolidated correction of the Definition candidate whose parent is
  `7370a4f47433142f68e0af4850e74b36f9b2d201`.
- Owner model: one professional user, one shared workspace, and all clients accessible to that
  authenticated professional.
- This Definition consumes the accepted Planning Input, retirement monthly income target (`RIT`),
  retirement target-date income source admission (`RTISA`), and retirement target-date income
  comparison basis (`RTICB`) authorities without changing their professional semantics.
- It defines the minimum authentication and deployment boundary required to expose those
  authorities over the internet on Railway.
- It does not authorize implementation, deployment, a downstream package, or production readiness.

Current gate:

- Definition candidate: `COMPLETE_PENDING_INDEPENDENT_DEFINITION_REACCEPTANCE`.
- Implementation: `NOT_AUTHORIZED`.
- Downstream: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

## 2. Repository evidence and governing invariants

| Surface | Repository evidence | Definition consequence |
|---|---|---|
| Planning Input | `GET /api/clients/{client_id}/retirement-planning-input` calls `planning_input_service.read`; `retirement_target_service.extend_read` supplies `planning_calculation_input_fingerprint` and retirement-target state | `/context` is an adapter over this accepted result, not a new authority |
| RIT assessment | `retirement_monthly_income_target_service.assess(db, client_id)` owns a fresh transaction, client lock, sticky stale transition, bounded database retry, and commit/rollback | The route calls it exactly once with a pristine request session and never wraps it |
| RIT confirmation | `retirement_monthly_income_target_service.confirm(db, complete_command, trusted_professional_actor)` owns validation, locking, CAS, exact retry, server time, actor persistence, and commit/rollback | The route injects the authenticated actor and path client ID only; it does not own the write transaction |
| RTISA | `read_in_snapshot` is a non-owning helper reserved for an already-owned snapshot | The vertical slice never exposes RTISA as a second public workflow |
| RTICB | `retirement_target_date_income_comparison_basis_service.assess(db, request)` requires a fresh session, opens one repeatable-read/read-only snapshot, composes RIT and RTISA snapshot helpers, returns success or `block_no_result`, and rolls back | `/comparison` must pass a pristine session directly to `assess` with no pre-query and return the professional envelope unchanged |
| Authentication | `backend/app/main.py` currently registers CORS and routers but no authentication middleware, authenticated request context, login, session, logout, or rate limiter | Existing path IDs, headers, browser fields, and service-test actor strings are not authentication |
| Dependencies | `backend/requirements.txt` contains no Argon2 or timed-signing package | Exact maintained dependencies are defined below and must be added only after implementation authorization |
| Deployment | No Railway configuration, production reverse-proxy contract, Dockerfile, or single-origin serving contract exists; current CORS is local-development oriented | Railway topology is a future implementation/deployment deliverable, not an already-provisioned fact |

The deployment facts referenced by this Definition are Railway's official public-networking,
variables, and replica guidance:

- `https://docs.railway.com/networking/public-networking`
- `https://docs.railway.com/variables`
- `https://docs.railway.com/deployments/optimize-performance`

The following invariants govern every later section:

1. Authentication establishes access to the one workspace; it does not establish per-client
   professional ownership.
2. Positive path client-ID validation, client existence where the called authority permits it,
   stored-row ownership, route/request identity, response identity, stale identity, and accepted
   fingerprint checks remain mandatory.
3. The professional actor is server-controlled and cannot be supplied or altered by the browser.
4. A professional failure envelope remains a successful semantic HTTP response when the accepted
   authority defines it that way.
5. No totals, gap, funding, eligibility, normalization execution, tax, scenario, or advice is
   introduced.

## 3. Binding single-user architecture

### 3.1 Primary supported topology

The only supported production topology for this package is:

1. One canonical HTTPS origin, `AUTH_PUBLIC_ORIGIN`, serves the compiled frontend and routes
   `/api/*` to the FastAPI application. The browser never needs a cross-site production cookie.
2. Railway terminates public TLS. The application accepts forwarded protocol/client information
   only from an explicitly configured trusted Railway proxy boundary described in section 4.
3. Exactly one backend Railway replica and exactly one Uvicorn worker are permitted. Production
   startup requires `WEB_CONCURRENCY=1`; deployment acceptance independently verifies replica
   count `1`. Horizontal replicas, overlapping rolling instances, and multiple workers are not
   supported by this Definition.
4. The existing Railway PostgreSQL service is the shared durable authority for login-attempt
   limiting. Authentication sessions themselves remain stateless signed cookies.
5. A deploy or signing-key rotation uses stop-then-start replacement, accepting a brief service
   interruption. Mixed-secret overlap is prohibited.

This constraint is intentional: it avoids a distributed session/revocation system and does not
make an unsupported multi-replica security claim. A future multi-replica topology requires a
separate Definition change and acceptance.

### 3.2 Explicitly absent architecture

There is no multi-user model, role system, tenant partition, per-client ownership assignment,
registration, invitation, password-reset/email workflow, user-management UI, external identity
provider, browser actor field, or process-local authentication session store.

## 4. Railway transport, proxy, and production configuration

### 4.1 Required production variables

Production startup requires all of the following, supplied through Railway variables and never
through committed values:

| Variable | Exact contract |
|---|---|
| `APP_ENV` | Exact value `production` |
| `DATABASE_URL` | Existing supported PostgreSQL URL; SQLite is forbidden in production |
| `AUTH_PUBLIC_ORIGIN` | One canonical ASCII origin `https://host` or `https://host:port`; no userinfo, path other than empty, query, fragment, wildcard, trailing slash, or comma-separated list |
| `AUTH_USERNAME` | UTF-8 string satisfying section 5.1; no normalization or case folding |
| `AUTH_PASSWORD_HASH` | Valid Argon2id PHC verifier with the exact parameters in section 5.2 |
| `AUTH_DUMMY_PASSWORD_HASH` | A different valid Argon2id PHC verifier with the same parameters, used for unknown usernames |
| `AUTH_ACTOR_ID` | Exact accepted RIT actor predicate in section 8 |
| `AUTH_SESSION_SECRET_B64` | Unpadded base64url, exactly 43 characters decoding to exactly 32 random bytes |
| `AUTH_RATE_LIMIT_SECRET_B64` | Independent unpadded base64url, exactly 43 characters decoding to exactly 32 random bytes |
| `AUTH_TRUSTED_PROXY_CIDRS` | Non-empty comma-separated canonical IPv4/IPv6 CIDRs; no `0.0.0.0/0` or `::/0` |
| `WEB_CONCURRENCY` | Exact decimal string `1` |

No default, local-development value, dynamically generated secret, or plaintext password may be
used as a production fallback. Startup parses and validates the complete set before serving a
request and exits non-zero on any missing, empty, duplicate, malformed, weak, inconsistent, or
forbidden value. Error output names the invalid variable but never prints its value.

Both 32-byte secrets must be generated out of band by a cryptographically secure random generator,
with 256 bits of source entropy. Deployment evidence records the generator/procedure and variable
presence without recording either value. Startup can prove encoding and decoded length, not source
entropy; absence of the provisioning evidence stops deployment under `SC-006`.

### 4.2 Trusted proxy and client-IP derivation

The immediate socket peer is authoritative unless it belongs to `AUTH_TRUSTED_PROXY_CIDRS`.

- If the peer is untrusted, all `Forwarded`, `X-Forwarded-*`, `X-Real-IP`, and equivalent headers
  are ignored for identity/security decisions; production requests that require HTTPS and arrive
  directly are rejected.
- If the peer is trusted, only `X-Forwarded-For` and `X-Forwarded-Proto` are accepted. Any duplicate,
  empty, malformed, overlong, or ambiguous header is rejected before authentication.
- The XFF list is parsed as IP literals only. Traversing right-to-left, trusted proxy addresses are
  removed; the first remaining address is the client. Absence of exactly one resulting client
  boundary is `PROXY_CHAIN_INVALID`.
- The canonical attempt IP is Python `ipaddress.ip_address(value).compressed`; IPv4-mapped IPv6 is
  converted to canonical IPv4. Zone identifiers are forbidden.
- `X-Forwarded-Proto` must be the single exact value `https`. Caller-supplied host/proto/IP headers
  cannot override the socket/trusted-proxy boundary.
- `Host` must equal the host and optional port of `AUTH_PUBLIC_ORIGIN` after standards-based
  canonical parsing. Origin equality is then exact string equality against `AUTH_PUBLIC_ORIGIN`.

Deployment acceptance must first record the actual Railway proxy chain/CIDRs and prove the rule
against the deployed service. If Railway cannot supply a stable, testable trust boundary, `SC-003`
stops deployment; the implementation must not trust all proxies.

### 4.3 Health and startup

- `GET /healthz/live` is data-free and returns `200` with exactly `{"status":"ok"}` when the
  process event loop is serving.
- `GET /healthz/ready` is data-free and returns `200` with exactly `{"status":"ready"}` only after
  configuration validation and a minimal PostgreSQL/limiter-schema readiness check; otherwise it
  returns `503` with exactly `{"status":"unavailable"}`.
- Neither endpoint returns environment values, database details, version strings, client data, or
  authentication state.
- Railway must route traffic only when readiness succeeds. These two GET endpoints and exact CORS
  preflight are the only unauthenticated non-login requests.

## 5. Login credential and brute-force authority

### 5.1 Login request contract

`POST /api/auth/login` accepts JSON with exactly:

```json
{"username":"string","password":"string"}
```

- Content type must be `application/json` with a body no larger than 8 KiB.
- `username` is a JSON string of 1–128 Unicode code points, at most 512 UTF-8 bytes, unchanged by
  trimming SP/TAB/CR/LF, and containing no Unicode `Cc` character.
- `password` is a JSON string of 1–1024 Unicode code points and at most 4096 UTF-8 bytes. NUL and
  other Unicode `Cc` characters are forbidden; other spaces are significant and are not trimmed.
- Unicode normalization, case folding, whitespace repair, form decoding, and alternate field names
  are forbidden. Username comparison is constant-time comparison of the exact UTF-8 bytes.
- Malformed JSON is `400 REQUEST_JSON_INVALID`. Missing, extra, wrong-type, empty, control-bearing,
  or overlong fields are `422 LOGIN_REQUEST_INVALID` and never reach password hashing.
- Exact `Origin: <AUTH_PUBLIC_ORIGIN>` is required before body parsing or credential work.

### 5.2 Password verification

Implementation uses exactly `argon2-cffi==23.1.0`, Argon2 version 19, type Argon2id, time cost `3`,
memory cost `65536` KiB, parallelism `4`, hash length `32`, and salt length at least `16` bytes.
Startup parses both configured PHC strings and rejects a different type/version/cost, malformed
encoding, salt shorter than 16 bytes, or hash length other than 32 bytes.

For the configured username, `AUTH_PASSWORD_HASH` is verified. For every other valid-shaped
username, `AUTH_DUMMY_PASSWORD_HASH` is verified using the supplied password. Username mismatch and
password mismatch produce the same status, response body, cache headers, logging class, and
limiter mutation. Credentials and verifiers are never logged or returned. The Definition does not
invent or set a production username, password, verifier, or secret.

### 5.3 Durable login-attempt limiter

One additive migration may create an authentication-infrastructure table containing only:

- `bucket_key`: HMAC-SHA-256 digest/hex primary key;
- `window_started_at`: PostgreSQL timestamptz;
- `failure_count`: bounded non-negative integer;
- `locked_until`: nullable PostgreSQL timestamptz; and
- `updated_at`: PostgreSQL timestamptz.

No username, password, raw IP, actor, cookie, token, or client record is stored. Keys use
HMAC-SHA-256 with decoded `AUTH_RATE_LIMIT_SECRET_B64` over these exact UTF-8 preimages:

- global: `RTDIR_LOGIN_LIMIT_V1\0GLOBAL`;
- username: `RTDIR_LOGIN_LIMIT_V1\0USER\0` plus the exact submitted valid username; and
- IP: `RTDIR_LOGIN_LIMIT_V1\0IP\0` plus the canonical client IP.

The PostgreSQL transaction uses database time and atomic row locking/upsert. Fixed windows begin at
the first counted failure and last exactly 900 seconds:

- username threshold: 5 failures per window;
- IP threshold: 20 failures per window; and
- global threshold: 200 failures per window.

Processing order is exact:

1. validate trusted transport and Origin;
2. derive the trusted client IP and atomically read the IP/global windows;
3. enforce body-size and JSON framing; on malformed input atomically count IP/global failure and
   return `400` unless that increment reaches a threshold, in which case return `429`;
4. enforce the exact request schema; on schema failure atomically count IP/global failure and
   return `422` unless that increment reaches a threshold, in which case return `429`;
5. derive the username key and atomically read its current window together with refreshed IP/global
   windows;
6. if any applicable valid window is already at threshold, return `429 LOGIN_RATE_LIMITED` without password
   verification and with integer `Retry-After` equal to the ceiling of the longest remaining lock;
7. otherwise execute real/dummy Argon2id verification;
8. on failure, atomically increment username, IP, and global buckets; the failure that reaches a
   threshold returns `429`, earlier failures return `401 AUTHENTICATION_FAILED`;
9. on success, atomically clear the matching username and IP buckets, retain the global failures
   until their window expires, and issue the session only after that transaction commits.

Malformed/schema-invalid login attempts do not reach hashing or a username bucket. Expired windows
reset to count zero on the next atomic operation. Reaching a threshold sets `locked_until` to
exactly `window_started_at + 900 seconds`. There is no manual/frontend
reset and no progressive delay. Store timeout, unavailable database, missing table, transaction
failure, or ambiguous time fails closed as `503 AUTH_RATE_LIMIT_UNAVAILABLE`; no password hash is
evaluated and no session is issued. Because the limiter is PostgreSQL-backed, restart does not
reset it. The deployment remains constrained to one replica/worker for the other reasons in
section 3; no cross-replica claim is made.

## 6. Signed session and secret-rotation contract

### 6.1 Token construction

Implementation uses exactly `itsdangerous==2.2.0`, `URLSafeTimedSerializer`, salt
`RTDIR_SESSION_COOKIE_V1`, HMAC key derivation, and SHA-256 digest. A deterministic canonical JSON
serializer uses UTF-8, sorted keys, compact separators, no NaN, and no implicit type coercion.

The signed payload contains exactly:

| Field | Type and rule |
|---|---|
| `contract` | Exact string `RTDIR_SESSION_V1` |
| `actor_id` | Exact validated `AUTH_ACTOR_ID` |
| `iat` | Integer UTC epoch seconds from server time |
| `exp` | Integer exactly `iat + 28800` |
| `nonce` | Unpadded base64url, 43 characters decoding to 32 CSPRNG bytes |
| `csrf` | Independent unpadded base64url, 43 characters decoding to 32 CSPRNG bytes |

No extra or missing field is accepted. Verification requires a valid HMAC-SHA-256 signature,
serializer age at most 28,800 seconds, exact payload types/shape, `exp == iat + 28800`, current time
strictly before `exp`, `iat` not more than 60 seconds in the future, actor equality with current
`AUTH_ACTOR_ID`, and canonical base64url nonce/CSRF values. A valid token never slides or renews on
API/session-status access. New authentication requires a fresh login after expiry.

### 6.2 Cookie contract

The only authentication cookie is `__Host-retire_v2_session` with:

- `Secure`;
- `HttpOnly`;
- `SameSite=Lax`;
- `Path=/`;
- no `Domain` attribute;
- `Max-Age=28800`; and
- `Expires` representing exactly the signed `exp` instant.

The cookie is issued only on a successful committed login. It is never accessible to frontend
JavaScript, duplicated under another name, accepted from a query/header/body field, or used over
non-HTTPS production transport.

### 6.3 Rotation and copied-token behavior

There is exactly one active signing secret and no previous-key acceptance. Rotation is a scheduled
stop-then-start deployment: stop the sole instance, change `AUTH_SESSION_SECRET_B64`, then start and
pass readiness. Every token signed by the old key is rejected once the new instance serves. Mixed
old/new secrets, overlapping instances, a previous-key grace window, and rolling rotation are
forbidden.

Changing only the rate-limit HMAC secret is forbidden while unexpired limiter rows exist; the safe
procedure is to retain it or explicitly expire/delete all limiter rows during an authorized
maintenance operation before replacement.

A copied signed cookie remains usable until its absolute expiry or session-secret rotation even
after browser logout. Stateless logout is not per-token revocation and no immediate global logout
claim is made. TLS, Secure/HttpOnly cookie handling, short absolute lifetime, and controlled key
rotation are the defined controls.

## 7. CSRF, CORS, middleware, logout, and cache contract

### 7.1 CSRF construction and validation

- The anti-CSRF header is exactly `X-RTDIR-CSRF`.
- The value is the exact signed session `csrf` field. It is returned in the successful login and
  session-status DTOs and held in frontend memory only.
- Unsafe methods are `POST`, `PUT`, `PATCH`, and `DELETE`. Every unsafe authenticated request
  requires exact Origin, valid session, and the header.
- Validation order is transport/proxy and Host, Origin, session signature/expiry/actor, CSRF shape,
  constant-time comparison of decoded 32-byte CSRF values, then body DTO and route/service.
- A CSRF token from another session, a token without a valid cookie, malformed encoding, and
  missing/extra values are rejected `403 CSRF_INVALID` before mutation.
- CSRF rotates only with a new login/session. `GET /api/auth/session` returns the same value and
  does not renew the session.

Login has no prior CSRF token but requires exact Origin. Logout follows section 7.3.

### 7.2 Production CORS and preflight

Primary production traffic is same-origin. The CORS policy nevertheless permits exactly
`AUTH_PUBLIC_ORIGIN`, credentials `true`, methods `GET, POST, PUT, DELETE, OPTIONS`, request headers
`Content-Type, X-RTDIR-CSRF`, no exposed headers, and preflight max age 600 seconds. Origin,
methods, and headers are explicit; no wildcard is permitted.

An OPTIONS request is answered without authentication only when Origin exactly matches, the
requested method is in the allowlist, and every requested header is in the allowlist. Otherwise it
is `403 ORIGIN_FORBIDDEN`. A missing Origin on an unsafe request is forbidden. If Origin is present
on a safe browser request it must also match exactly.

Semantic middleware order is mandatory:

1. trusted proxy/protocol/Host validation;
2. request-ID and response-cache wrapper;
3. exact CORS preflight handling;
4. route allowlist and signed-session authentication;
5. Origin and CSRF validation;
6. JSON/DTO validation; and
7. route and accepted service execution.

Framework registration order must be tested to prove this runtime order rather than inferred from
source order.

### 7.3 Logout and cache behavior

`POST /api/auth/logout` behavior is exact:

- Origin is checked first.
- A valid session plus valid CSRF returns `204` with no body and expires the cookie using the same
  name, Secure, HttpOnly, SameSite, Path and absent Domain attributes, with `Max-Age=0` and a past
  Expires value.
- A missing, malformed, expired, or wrongly signed session returns `401 AUTHENTICATION_REQUIRED`
  and also emits the same deletion cookie. It does not claim server revocation.
- A valid session with missing/invalid CSRF returns `403 CSRF_INVALID` and does not delete the
  cookie.
- A network/technical `5xx` response does not prove browser cookie deletion.

The frontend immediately hides client data on a logout attempt but reports success only after
`204`. On `401` it treats the server session as absent and shows login. On `403`, network failure,
or `5xx`, it shows a neutral “logout not confirmed” state with explicit retry and reload/session
check; it never claims the copied token was revoked.

Every login, session, logout, authenticated API, and authentication-error response includes
`Cache-Control: no-store, private` and `Pragma: no-cache`. Browser service workers, local storage,
session storage, IndexedDB, and persistent client caches must not retain credentials, CSRF values,
authenticated DTOs, or client results.

## 8. Trusted professional actor and client addressing

`AUTH_ACTOR_ID` is accepted only when it satisfies the existing RIT `_valid_actor` predicate
exactly:

1. value is a Python `str`;
2. length is 1–128 Unicode code points;
3. value equals `value.strip(" \t\r\n")`; and
4. no character has Unicode category `Cc`.

It is loaded from validated server configuration and attached to the request context only after
successful session verification. RIT confirmation receives that exact value. JSON, query, path,
headers (including actor-like headers), username, display label, cookie fields outside the signed
payload, and frontend state cannot substitute it.

Authentication permits the sole professional to address every client in the workspace. There is
no per-client authorization lookup. This does not weaken addressing controls:

- every client path parameter is a strict positive integer;
- request DTOs forbid body `client_id` unless the accepted service contract requires the route to
  inject it after validation;
- routes that own a legitimate client lookup retain not-found behavior;
- stored records must retain their existing `client_id` ownership checks;
- returned non-null `client_id` must equal the path or the accepted authority must return its own
  mismatch/failure envelope; and
- frontend generations and AbortController prevent a response for client A from rendering under B.

## 9. Exact HTTP, DTO, and error contract

### 9.1 Common transport DTOs

All DTOs use strict types and `extra="forbid"`.

`TransportErrorV1` contains exactly:

```json
{
  "schema_version": "RTDIR_TRANSPORT_ERROR_V1",
  "code": "STABLE_MACHINE_CODE",
  "message": "neutral Hebrew message",
  "field_paths": [],
  "request_id": "opaque server request id"
}
```

`field_paths` is a deterministically sorted unique list of JSON/path field paths and contains no
submitted values. Authentication failures always use an empty list. Unknown internal exceptions
return generic `INTERNAL_ERROR`; sensitive exception text is logged only under the request ID and
never returned.

`AuthenticatedSessionV1` contains exactly:

```json
{
  "schema_version": "RTDIR_AUTHENTICATED_SESSION_V1",
  "authenticated": true,
  "actor_id": "server-configured actor",
  "expires_at": "UTC RFC3339 second precision with Z",
  "csrf_token": "43-character base64url"
}
```

Login and `GET /api/auth/session` return this same DTO. Logout returns no body.

`PlanningContextV1` contains exactly:

```json
{
  "schema_version": "RTDIR_PLANNING_CONTEXT_V1",
  "client_id": 1,
  "planning_calculation_input_fingerprint": "64 lowercase hex",
  "planning_input_ready": true,
  "retirement_target_date": "YYYY-MM-DD or null",
  "retirement_target_ready": true,
  "blocking_facts": [{"source_id":"string or null","code":"string"}]
}
```

The adapter copies these values from one Planning Input read without reclassification. Every
`blocking_facts` item contains exactly nullable `source_id` and `code`; order equals the accepted
producer order. Missing/malformed required producer fields are technical failure, not repaired.

### 9.2 Endpoint request and response schemas

| Endpoint | Request | Successful response |
|---|---|---|
| `POST /api/auth/login` | Exact `username`, `password` from section 5.1 | `200 AuthenticatedSessionV1` plus cookie |
| `GET /api/auth/session` | No body/query | `200 AuthenticatedSessionV1`; no renewal |
| `POST /api/auth/logout` | No body/query; Origin/session/CSRF required as defined | `204`, no body, deletion cookie |
| `GET /api/clients/{client_id}/retirement-income-readiness/context` | Positive path ID; no body/query | `200 PlanningContextV1` |
| `GET /api/clients/{client_id}/retirement-income-readiness/target` | Positive path ID; no body/query | `200` exact accepted `RetirementMonthlyIncomeTargetResult`, including not-ready states |
| `PUT /api/clients/{client_id}/retirement-income-readiness/target` | Exact target-confirmation body below | `200` exact accepted current RIT result |
| `POST /api/clients/{client_id}/retirement-income-readiness/comparison` | Exact comparison body below | `200` exact RTICB success or `block_no_result` envelope |

Target-confirmation browser body contains exactly these eight fields and never `client_id` or actor:

- `expected_record_version`: strict integer in accepted RIT range;
- `expected_planning_calculation_input_fingerprint`: 64 lowercase hex;
- `expected_retirement_target_date`: valid canonical `YYYY-MM-DD`;
- `monthly_amount`: strict string passed to accepted RIT validation;
- `income_basis`: `GROSS` or `NET`;
- `price_basis`: `NOMINAL_AT_RETIREMENT_TARGET_DATE` or `REAL_AT_REFERENCE_DATE`;
- `price_reference_date`: canonical date or null under accepted RIT rules; and
- `source_kind`: one of the three accepted RIT source-kind literals.

After strict DTO validation, the route injects path `client_id` and the authenticated actor and
calls `RIT.confirm` exactly once.

Comparison browser body contains exactly:

```json
{
  "expected_planning_calculation_input_fingerprint":"64 lowercase hex",
  "expected_retirement_target_date":"YYYY-MM-DD"
}
```

Any `client_id` or other extra field is `422 REQUEST_SCHEMA_INVALID` before construction. The route
then injects the positive path client ID and constructs exactly the accepted three-field RTICB
request. It never silently overwrites a caller field.

### 9.3 Exact accepted professional response shapes

The target assessment and confirmation response is the accepted strict RIT result with exactly
these top-level fields:

- `schema_version`;
- nullable `client_id`;
- nullable `planning_calculation_input_fingerprint`;
- nullable `retirement_target_date`;
- nullable `target`;
- nullable `authority`;
- `authority_state`;
- `target_readiness_state`;
- `target_ready`;
- ordered `blockers`;
- nullable `target_semantic_fingerprint`; and
- `target_result_fingerprint`.

A non-null RIT `target` contains exactly `client_id`,
`planning_calculation_input_fingerprint`, `retirement_target_date`, `monthly_amount`, `currency`,
`income_basis`, `price_basis`, and nullable `price_reference_date`. A non-null RIT `authority`
contains exactly `record_version`, `source_kind`, `confirmation_state`, `confirmation_actor`,
`confirmed_at`, and `lifecycle_state`. The accepted RIT enums, strict values, ordering, and
fingerprints are not widened or reconstructed by the API.

An RTICB successful result contains exactly:

- `schema_version`, `client_id`, `planning_calculation_input_fingerprint`, and
  `retirement_target_date`;
- `target_result_fingerprint`, `target_semantic_fingerprint`,
  `rtisa_admission_result_fingerprint`, and `comparison_input_fingerprint`;
- `target_basis` with exactly `income_basis`, `price_basis`, and nullable
  `price_reference_date`;
- ordered `source_comparisons`;
- ordered `directly_comparable_source_ids`, `normalization_required_source_ids`,
  `basis_unresolved_source_ids`, and `not_admitted_source_ids`;
- `classification_state`, `classification_complete`, `direct_comparison_state`,
  `direct_comparison_ready`, ordered `blockers`; and
- `comparison_result_fingerprint`.

Each `source_comparisons` entry contains exactly `source_id`, `rtisa_admission_state`,
`source_upstream_identity`, `source_income_basis`, `source_price_basis`, nullable
`source_price_reference_date`, `comparison_state`, ordered `reason_codes`, and
`source_comparison_fingerprint`.

An RTICB `block_no_result` response contains exactly:

- `schema_version` and nullable `client_id`;
- nullable `supplied_planning_calculation_input_fingerprint`;
- nullable `observed_target_planning_calculation_input_fingerprint`;
- nullable `observed_rtisa_planning_calculation_input_fingerprint`;
- nullable `supplied_retirement_target_date`;
- nullable `observed_target_retirement_target_date`;
- nullable `observed_rtisa_retirement_target_date`;
- nullable `observed_target_result_fingerprint`;
- nullable `observed_rtisa_admission_result_fingerprint`;
- exact `result_state: "block_no_result"`;
- `failure_stage`, `failure_detail_code`; and
- `result_fingerprint`.

All four response shapes above remain strict: no API-only field is inserted, no field is dropped,
and no value, null, list order, enum, blocker, reason, or fingerprint is repaired.

### 9.4 Exact status mapping and precedence

Authentication/transport checks precede route semantics. The first failing layer determines the
response:

| Condition | HTTP | Code/response |
|---|---:|---|
| Malformed JSON syntax/encoding/body framing | 400 | `REQUEST_JSON_INVALID` |
| Invalid proxy chain/forwarded protocol/Host | 400 | `PROXY_CHAIN_INVALID` or `REQUEST_HOST_INVALID` |
| Missing/invalid/expired session on protected endpoint | 401 | `AUTHENTICATION_REQUIRED` |
| Wrong username or password below threshold | 401 | `AUTHENTICATION_FAILED` |
| Missing/wrong Origin or invalid CSRF | 403 | `ORIGIN_FORBIDDEN` or `CSRF_INVALID` |
| Route not found | 404 | `ROUTE_NOT_FOUND` |
| Context route client absent | 404 | existing `CLIENT_NOT_FOUND` mapped into `TransportErrorV1` |
| Login bucket reaches/is at threshold | 429 | `LOGIN_RATE_LIMITED` plus exact `Retry-After` |
| Missing/extra/wrong-type/out-of-range request/path field | 422 | `REQUEST_SCHEMA_INVALID` or `LOGIN_REQUEST_INVALID` |
| RIT confirmation stale context, CAS/version conflict, exhausted version, or accepted domain validation failure | 409 | exact existing RIT error code in `TransportErrorV1` |
| Context producer accepted conflict/integrity error | 409 | exact existing producer code |
| RIT assessment `RIT_CLIENT_ID_INVALID`, exhausted version, or dirty/non-fresh `RIT_RECORD_UNAVAILABLE` | 409 | exact existing RIT code; ordinary MISSING/STALE/INVALID/UNAVAILABLE result remains `200` |
| RIT assessment/confirmation unsupported-dialect `RIT_RECORD_UNAVAILABLE` | 503 | exact existing RIT code |
| RTICB `block_no_result`, including unavailable authority or identity mismatch | 200 | exact RTICB failure envelope, never 404/409/503 by reclassification |
| Known database/rate-limit store unavailability or unsupported production database | 503 | `AUTH_RATE_LIMIT_UNAVAILABLE`, `SERVICE_UNAVAILABLE`, or exact accepted 503 code |
| Unexpected programming/serialization/framework failure | 500 | generic `INTERNAL_ERROR` |

`400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, and `503` use
`TransportErrorV1`, except the exact data-free health response. For an `/api` path, authentication
precedes route-not-found disclosure, so an unauthenticated unknown API path is `401`; authenticated
unknown paths are `404`. An accepted professional result is never converted to a transport error.
A returned client identity is never rewritten to match the path.

## 10. Database transaction and RTICB snapshot ownership

Authentication cookie verification and CSRF validation perform no database work. A FastAPI
`get_db` session is created for a protected professional route but remains pristine until its
owner below uses it.

| Route | Exact ownership |
|---|---|
| `/context` | Route calls Planning Input once and rolls back in `finally`; no second session |
| `GET /target` | Route passes pristine session to public `RIT.assess` exactly once; RIT alone begins, locks, retries, commits/rolls back |
| `PUT /target` | Route passes pristine session to public `RIT.confirm` exactly once; RIT alone begins, locks, CAS-checks, retries, commits/rolls back |
| `POST /comparison` | Route performs no client-existence query, scalar/get/execute/flush/begin/commit/rollback, and no other service call before passing the pristine session and exact request to public `RTICB.assess` exactly once; RTICB alone owns and rolls back its snapshot |

The comparison route never opens a second session, invokes `SessionLocal`, calls `get_db` manually,
queries then rolls back to fake freshness, or performs a client-existence precheck. A nonexistent
or wrongly addressed client is represented by RTICB's accepted professional failure envelope when
RTICB produces one. The route still validates positive client-ID syntax and rejects a non-null
success/failure identity that violates the accepted RTICB schema; it does not mutate the envelope.

PostgreSQL tests must prove fresh-session admission, repeatable-read/read-only ownership, one
snapshot, no hidden write/autoflush, RIT locking/CAS/retry behavior, atomic rate-limit windows, and
rollback/no-partial-write behavior.

## 11. Deterministic Hebrew RTL frontend workflow

### 11.1 Authentication flow

Before rendering any workspace/client screen, the frontend calls `/api/auth/session` with
`credentials: "include"`. It stores the CSRF value and authenticated DTO only in memory. Login
accepts username/password in a Hebrew RTL screen, submits them once, and clears password state
after the response. No credential, actor, CSRF token, or authenticated/client DTO is persisted in
browser storage or URL state.

Session expiry/401 clears all in-memory client/result state and shows login. Logout follows section
7.3 and cannot report success on network/403/5xx failure. A reload always begins with a fresh
session-status request.

### 11.2 Readiness workflow

The authenticated route is
`/clients/:clientId/retirement-income-readiness`. It validates a positive integer client ID and uses
one active-generation counter plus `AbortController` so late responses for A never render under B.

Load and mutation sequence:

1. call exact `/context`;
2. call exact `GET /target`;
3. display target authority and editable confirmation fields;
4. after successful confirmation, discard all prior context/target/comparison state and call exact
   `/context` again, then `GET /target`;
5. execute `/comparison` only by explicit user action with the current context fingerprint/date;
6. after CAS/stale conflict, do not retry automatically; require explicit refresh.

### 11.3 Result composition

The UI displays the RTICB envelope without deriving professional state:

- `block_no_result` displays exact `failure_stage` and `failure_detail_code` and no source result;
- a successful result displays the server's `direct_comparison_state`,
  `direct_comparison_ready`, and every blocker in server order;
- all source comparisons remain visible in server order, including `EXCLUDED`/`NOT_ADMITTED`;
- every `reason_codes` list remains in exact server order;
- mixed `NORMALIZATION_REQUIRED` and `BASIS_UNRESOLVED` evidence displays both groups and both
  blockers without precedence invented by the UI;
- directly comparable entries never imply that the portfolio has usable income when the result is
  not ready, and even a ready comparison is labelled only as basis-comparison readiness;
- target `MISSING`, `INVALID`, `STALE`, `UNAVAILABLE`, and `CURRENT` states and exact RIT blockers
  remain distinct;
- technical codes may be secondary, but Hebrew labels are presentation-only and unknown codes use
  a neutral fallback while preserving the exact code.

No screen computes totals, gap, funding, eligibility, normalized values, tax, scenarios, or advice.
All screens and authentication/error/loading/logout states are Hebrew RTL.

## 12. Implementation surface and exclusions

Subject only to later implementation authorization, the minimum permitted surface is:

- global authentication/origin/CSRF/cache middleware and validated configuration;
- maintained pinned Argon2id and timed-signing dependencies from this Definition;
- login/session/logout and data-free health routes;
- one additive PostgreSQL/Alembic limiter-table migration and limiter service;
- the four vertical-slice routes and strict adapter DTOs;
- frontend authentication gate/login/logout behavior and one Hebrew RTL readiness page;
- single-origin Railway build/start/proxy documentation/configuration; and
- pure, API, browser, PostgreSQL, governance, mutation, and deployed-topology tests.

Explicitly excluded are changes to accepted Planning Input/RIT/RTISA/RTICB professional semantics,
professional fingerprints, client ownership, user/role models, server-side session persistence,
normalization execution, aggregation, income totals, gap, funding/coverage, eligibility,
withdrawals, allocation, cashflow, tax optimization, scenarios, M09/M10 professional execution,
M11–M14, frozen `02M`, excluded `M08E`, and any production-readiness claim.

## 13. Executable oracle catalog and mutation method

| Oracle | Required executable evidence |
|---|---|
| `PURE-001` | Strict config, origin, actor, login DTO, canonical IP/proxy parser, Argon2 PHC parser, session payload, expiry, cookie, and CSRF pure tests |
| `PURE-002` | Deterministic rate-limit key/window/threshold/reset/Retry-After tests with fixed database time |
| `API-001` | Login/session/logout ordinary, negative, cache, cookie, Origin, CSRF, expiry, copied-token, and rotation route tests |
| `API-002` | Registered-route inventory proving every `/api` route is protected except the exact allowlist; actor/client addressing and response-identity tests |
| `API-003` | Exact DTO/status/body tests for context, target assessment/confirmation, comparison, malformed JSON, schema errors, domain conflicts, and technical failures |
| `API-004` | Spies/mutations proving exact once-only service calls, argument construction, pristine session admission, and no route-owned transaction leakage |
| `PG-001` | Real PostgreSQL concurrent limiter threshold/upsert/lock/restart persistence and fail-closed store tests |
| `PG-002` | Real PostgreSQL RIT confirmation/CAS/retry/actor/no-partial-write regressions through the route |
| `PG-003` | Real PostgreSQL RTICB repeatable-read/read-only single-snapshot and no-prequery/no-second-session tests |
| `BROWSER-001` | Hebrew RTL login/session-expiry/logout-failure/cache and no-persistent-secret tests |
| `BROWSER-002` | Context/target/confirmation/refresh/client-switch and mixed RTICB blocker/source/reason presentation tests |
| `DEPLOY-001` | Railway staging black-box proof of one origin, HTTPS, Host/proxy boundary, one replica/worker, shared variables, restart persistence, rotation downtime, health, cookie, CORS, and cache headers |
| `GOV-001` | Scope, dependency pin, migration count/head, protected-path, secret scanning, route inventory, and no-downstream governance tests |
| `MUT-001` | Mutation harness recording mutant, reached-path evidence, failing ordinary oracle, restoration, and passing control |

Every material mutation must execute the ordinary production path. A mock-only assertion or a
self-injected expected exception is insufficient. Required mutation inventory:

| Mutation | Required failing oracle(s) |
|---|---|
| Skip/increase rate-limit threshold; omit global/IP/user bucket | `PURE-002`, `PG-001`, `API-001` |
| Fail open when limiter/database fails | `PG-001`, `API-001` |
| Replace durable limiter with process memory or enable multiple workers/replicas | `PG-001`, `DEPLOY-001`, `GOV-001` |
| Trust caller forwarding/protocol headers | `PURE-001`, `DEPLOY-001` |
| Allow login without exact Origin | `API-001`, `DEPLOY-001` |
| Accept cross-session/missing CSRF or compare non-constantly | `PURE-001`, `API-001` |
| Enable wildcard credentialed CORS or extra method/header | `API-001`, `DEPLOY-001` |
| Remove Secure/HttpOnly/SameSite/Path, add Domain, or mismatch cookie expiry | `PURE-001`, `API-001`, `DEPLOY-001` |
| Cache sensitive/authenticated response | `API-001`, `API-003`, `BROWSER-001` |
| Treat failed logout as success or copied token as revoked | `API-001`, `BROWSER-001` |
| Accept old/mixed signing secret or overlapping deployment | `API-001`, `DEPLOY-001` |
| Let malformed/overlong login reach Argon2 | `PURE-001`, `API-001` |
| Accept caller actor or invalid configured actor | `PURE-001`, `API-002`, `PG-002` |
| Accept and overwrite comparison `client_id`/extra field | `API-003`, `API-004` |
| Pre-query comparison client, open second session, or wrap RTICB transaction | `API-004`, `PG-003` |
| Convert RTICB `block_no_result` to transport error | `API-003`, `BROWSER-002` |
| Recompute/reorder/drop UI blockers/reasons or infer portfolio readiness | `BROWSER-002` |
| Render late client-A result under B | `BROWSER-002` |

## 14. Acceptance criteria

| ID | Criterion | Executable oracle(s) |
|---|---|---|
| `AC-001` | Package identity, governance, base, owner model, and non-authorization gates are exact. | `GOV-001` |
| `AC-002` | One professional authenticates into one workspace with no roles, registration, tenancy, or per-client grants. | `API-002`, `GOV-001` |
| `AC-003` | Every `/api` route is authenticated except exact login, health, and valid preflight allowlist. | `API-002` |
| `AC-004` | Login body/content type/size/string limits and exact-field validation are enforced before hashing. | `PURE-001`, `API-001` |
| `AC-005` | Exact username comparison and real/dummy pinned Argon2id verification produce indistinguishable credential failures. | `PURE-001`, `API-001` |
| `AC-006` | Username/IP/global limiter keys, 900-second windows, thresholds, reset, and Retry-After match section 5.3. | `PURE-002`, `PG-001`, `API-001` |
| `AC-007` | Limiter state is PostgreSQL-durable across restart and any limiter/store ambiguity fails closed. | `PG-001`, `DEPLOY-001` |
| `AC-008` | Trusted client IP/protocol/Host derive only through the configured proxy boundary; spoofed headers fail. | `PURE-001`, `DEPLOY-001` |
| `AC-009` | Production configuration is complete, exact, secret-free in Git/output, and fail-closed at startup. | `PURE-001`, `GOV-001`, `DEPLOY-001` |
| `AC-010` | Signed token algorithm, canonical format, exact fields, 256-bit secret, nonce/CSRF entropy, and validation are exact. | `PURE-001`, `API-001` |
| `AC-011` | Session lifetime is exactly 28,800 seconds, non-sliding, and cookie Max-Age/Expires agree with signed expiry. | `PURE-001`, `API-001` |
| `AC-012` | Cookie name and Secure/HttpOnly/SameSite/Path/no-Domain attributes are exact. | `PURE-001`, `API-001`, `DEPLOY-001` |
| `AC-013` | Single-key stop/start rotation rejects old tokens; copied tokens otherwise remain valid until expiry. | `API-001`, `DEPLOY-001` |
| `AC-014` | Valid logout deletes the cookie; invalid-session and failed logout behavior match section 7.3 without false revocation claims. | `API-001`, `BROWSER-001` |
| `AC-015` | Sensitive/authenticated responses are no-store/no-cache and browser persistence is absent. | `API-001`, `API-003`, `BROWSER-001` |
| `AC-016` | Exact Origin and session-bound, constant-time CSRF validation precede every unsafe mutation. | `PURE-001`, `API-001` |
| `AC-017` | CORS/preflight uses one exact origin and closed method/header sets with credentials and no wildcard. | `API-001`, `DEPLOY-001` |
| `AC-018` | Runtime middleware ordering matches section 7.2. | `API-001`, `API-002` |
| `AC-019` | `AUTH_ACTOR_ID` matches RIT `_valid_actor` exactly and only the authenticated server context reaches RIT. | `PURE-001`, `API-002`, `PG-002` |
| `AC-020` | No per-client grant exists, while positive ID, existence where permitted, row ownership, request/path, and response identity remain fail-closed. | `API-002`, `API-003` |
| `AC-021` | `/context` has the exact DTO and value-for-value accepted producer fields, using one route-owned read transaction. | `API-003`, `API-004` |
| `AC-022` | Target assessment invokes public RIT assess once with a pristine session and returns its semantic result unchanged. | `API-003`, `API-004`, `PG-002` |
| `AC-023` | Target confirmation validates exactly eight browser fields, injects path client and server actor, and preserves RIT CAS/retry semantics. | `API-003`, `API-004`, `PG-002` |
| `AC-024` | Comparison rejects caller client/extra fields before constructing exactly the accepted three-field RTICB request. | `API-003`, `API-004` |
| `AC-025` | Comparison performs no DB precheck and gives a pristine single session to public RTICB assess exactly once. | `API-004`, `PG-003` |
| `AC-026` | RTICB success and `block_no_result` envelopes remain HTTP 200 and byte/value unchanged. | `API-003`, `PG-003` |
| `AC-027` | All endpoint DTOs, status mappings, precedence, and generic technical errors match section 9. | `API-001`, `API-003` |
| `AC-028` | UI authentication/session/logout/expiry states are Hebrew RTL and never persist secrets or client state. | `BROWSER-001` |
| `AC-029` | After confirmation UI discards prior state and reloads exact `/context` then target before optional comparison. | `BROWSER-002` |
| `AC-030` | UI preserves all ordered blockers, reasons, excluded entries, mixed normalization/unresolved evidence, and neutral readiness semantics. | `BROWSER-002` |
| `AC-031` | Abort/generation isolation prevents cross-client late-response rendering and conflicts require explicit refresh. | `BROWSER-002` |
| `AC-032` | Railway topology is one HTTPS origin, one replica, one worker, PostgreSQL, and validated proxy/health behavior. | `DEPLOY-001` |
| `AC-033` | Secret/config rotation and restart behavior are proven without mixed instances or in-memory session durability claims. | `API-001`, `PG-001`, `DEPLOY-001` |
| `AC-034` | Pure, API, browser, PostgreSQL, governance, mutation, and deployed-topology suites cover their assigned boundaries. | `GOV-001`, `MUT-001` |
| `AC-035` | Every material mutation records reached-path evidence, fails its ordinary oracle, and passes after restoration. | `MUT-001` |
| `AC-036` | Implementation changes no accepted professional authority and introduces no excluded calculation/downstream behavior. | `GOV-001`, `API-003`, `BROWSER-002` |

Acceptance range: `AC-001` through `AC-036`; count: `36`.

## 15. Negative acceptance criteria

| ID | Prohibited outcome | Executable oracle(s) |
|---|---|---|
| `NAC-001` | Any unauthenticated protected API access or browser-only authentication gate. | `API-002` |
| `NAC-002` | Multi-user, roles, registration, tenancy, per-client ownership, or external IdP scope. | `GOV-001` |
| `NAC-003` | Plaintext/default/generated production credential or secret in source, Git, logs, frontend, or response. | `PURE-001`, `GOV-001` |
| `NAC-004` | Wrong username skips dummy Argon2 verification or reveals account existence. | `API-001` |
| `NAC-005` | Frontend/process-only limiter, restart reset, threshold bypass, or limiter fail-open. | `PG-001`, `DEPLOY-001` |
| `NAC-006` | Trusting caller-controlled forwarded IP/protocol/host or all proxy addresses. | `PURE-001`, `DEPLOY-001` |
| `NAC-007` | Malformed/overlong login reaching password hashing. | `PURE-001`, `API-001` |
| `NAC-008` | Sliding session, malformed payload repair, weak secret, or alternate token algorithm/format. | `PURE-001`, `API-001` |
| `NAC-009` | Missing cookie security attribute, any Domain attribute, or expiry mismatch. | `API-001`, `DEPLOY-001` |
| `NAC-010` | Previous/mixed signing keys, overlapping rotation, or unsupported replica/worker count. | `API-001`, `DEPLOY-001` |
| `NAC-011` | Claiming logout revokes a copied stateless token or reporting failed logout as success. | `API-001`, `BROWSER-001` |
| `NAC-012` | Wildcard credentialed CORS, non-exact Origin, extra method/header, or unaudited preflight. | `API-001`, `DEPLOY-001` |
| `NAC-013` | CSRF accepted without the bound valid session, across sessions, or by non-constant comparison. | `PURE-001`, `API-001` |
| `NAC-014` | Sensitive/authenticated response cached or persisted by frontend/browser storage. | `API-003`, `BROWSER-001` |
| `NAC-015` | Browser/request field substitutes or alters `trusted_professional_actor`. | `API-002`, `PG-002` |
| `NAC-016` | Per-client grant added, or client/path/row/response identity validation removed. | `API-002`, `API-003` |
| `NAC-017` | Comparison accepts/overwrites caller `client_id` or any extra field. | `API-003`, `API-004` |
| `NAC-018` | Comparison pre-queries client, opens a second session, resets a transaction, or wraps/nests RTICB ownership. | `API-004`, `PG-003` |
| `NAC-019` | Professional `block_no_result`/not-ready state converted to transport error or success invented from it. | `API-003`, `BROWSER-002` |
| `NAC-020` | UI reorders/drops/reclassifies reasons, blockers, excluded entries, or mixed evidence. | `BROWSER-002` |
| `NAC-021` | Directly comparable entries are presented as portfolio income/funding readiness. | `BROWSER-002` |
| `NAC-022` | Totals, gap, funding, eligibility, normalization, tax, scenario, downstream, or production-readiness behavior is introduced. | `GOV-001`, `BROWSER-002` |

Negative-acceptance range: `NAC-001` through `NAC-022`; count: `22`.

## 16. Deterministic implementation and deployment stop conditions

| ID | Stop condition | Detection oracle/evidence |
|---|---|---|
| `SC-001` | Repository/base/accepted upstream contract differs from the accepted implementation authorization. | `GOV-001` identity check |
| `SC-002` | One same-origin HTTPS frontend/API topology cannot be implemented without an unaccepted architecture change. | `DEPLOY-001` topology proof |
| `SC-003` | Actual Railway proxy CIDRs/chain cannot be identified and tested without trusting arbitrary forwarding headers. | `DEPLOY-001` proxy proof |
| `SC-004` | Railway cannot enforce/read back exactly one backend replica and one worker or requires overlapping mixed-secret instances. | `DEPLOY-001` configuration readback |
| `SC-005` | PostgreSQL limiter migration/atomic locking/database time cannot satisfy section 5.3. | `PG-001` |
| `SC-006` | Required production secret/config input is absent/malformed or would require a committed/plaintext fallback. | `PURE-001`, startup/readiness proof |
| `SC-007` | Pinned Argon2/signing dependency or exact cryptographic parameters cannot be installed and verified on the deployment runtime. | `PURE-001`, `DEPLOY-001` |
| `SC-008` | Global middleware cannot protect the complete registered `/api` inventory with only the exact allowlist. | `API-002` route inventory |
| `SC-009` | Configured actor fails the exact RIT predicate or accepted RIT cannot receive it solely from authenticated server context. | `PURE-001`, `API-002`, `PG-002` |
| `SC-010` | Exact DTO/status mapping would require changing an accepted Planning Input/RIT/RTISA/RTICB professional contract. | `API-003`, contract diff |
| `SC-011` | Comparison cannot pass a pristine session to public RTICB assess without pre-query, second session, or transaction workaround. | `API-004`, `PG-003` |
| `SC-012` | A material security/transaction/UI mutation cannot reach and fail an ordinary production-path oracle. | `MUT-001` |
| `SC-013` | Deployment black-box evidence cannot prove HTTPS, Host/proxy, cookie, CORS, cache, limiter persistence, health, and rotation constraints. | `DEPLOY-001` |
| `SC-014` | Implementation discovers a new professional decision, calculation authority, multi-user need, or downstream dependency. | `GOV-001` and owner/governance review |

Stop-condition range: `SC-001` through `SC-014`; count: `14`. Encountering any condition stops
implementation or deployment at that gate. It does not authorize a workaround, weaker guarantee,
new infrastructure, or scope expansion.

## 17. Independent blocker disposition

| Blocker | Definition disposition |
|---|---|
| `RTDIR-VS-GOV-001` | Closed by sections 13–16: contiguous unique `AC-001..036`, `NAC-001..022`, `SC-001..014`, exact counts, oracle mappings, and deterministic stop conditions. |
| `RTDIR-VS-SEC-001` | Closed by section 5.3: exact durable PostgreSQL limiter thresholds/windows/keys/order/reset/failure/restart contract and mutation oracles. |
| `RTDIR-VS-SEC-002` | Closed by sections 4–6: exact input limits, Argon2id policy, token/signature/secret/nonce/lifetime/cookie/config/startup contract. |
| `RTDIR-VS-SEC-003` | Closed by section 6.3: single active key, stop/start rotation, no overlap/previous key, explicit copied-token behavior. |
| `RTDIR-VS-SEC-004` | Closed by section 7.1–7.2: exact CSRF header/token binding/order/constant-time checks and closed CORS/preflight/origin policy. |
| `RTDIR-VS-SEC-005` | Closed by sections 7.3 and 11.1: exact logout failure states, deletion versus revocation limits, retry/reload, and no-store/browser-cache contract. |
| `RTDIR-VS-ACTOR-001` | Closed by section 8: exact RIT `_valid_actor` predicate and server-only authenticated binding. |
| `RTDIR-VS-API-001` | Closed by section 9.2: exact two-field browser comparison DTO, forbidden caller client ID/extras, then path injection. |
| `RTDIR-VS-API-002` | Closed by section 10: no comparison pre-query/second session/rollback workaround and exact RTICB public snapshot ownership. |
| `RTDIR-VS-API-003` | Closed by section 9: exact DTOs, response identity, complete status mapping, precedence, professional-envelope preservation, and technical errors. |
| `RTDIR-VS-UI-001` | Closed by section 11: deterministic multi-blocker/source/reason composition, neutral readiness, refresh/conflict/client isolation, Hebrew RTL, and logout/cache behavior. |
| `RTDIR-VS-DEPLOY-001` | Closed at Definition level by sections 3–4: one-origin, one-replica/worker Railway topology, TLS/proxy/cookie/secrets/health/startup contracts and explicit deployment proof gate. |
| `RTDIR-VS-TEST-001` | Closed by section 13 and mapped criteria: complete ordinary/mutation inventory separated across pure/API/browser/PostgreSQL/deployed-topology evidence. |

## 18. Final consistency and authorization gate

The thirteen reported Definition blockers are addressed by one internally consistent architecture.
No professional ambiguity and no additional Owner/Product Decision remains.

Remaining prerequisites are deterministic implementation/deployment work, not unresolved
Definition choices:

1. independently accept this corrected Definition;
2. separately authorize implementation;
3. provision actual non-committed credentials/secrets and the canonical HTTPS origin;
4. record and verify the actual Railway trusted-proxy boundary;
5. enforce/read back one replica and one worker;
6. apply and validate the PostgreSQL limiter migration;
7. execute all mapped ordinary and mutation suites; and
8. pass deployed-topology evidence before any production-readiness claim.

No implementation, Railway resource mutation, password generation, push, merge, downstream
authorization, or production-readiness claim is part of this Definition correction.

Implementation = `NOT_AUTHORIZED`.

Downstream = `NOT_AUTHORIZED`.

Production readiness = `NOT_CLAIMED`.
