# RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE — Consolidated Definition

## 1. Status, authority, and package boundary

- Package: `RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE` (`RTDIR-VS`).
- Classification: `CLASS A / COMPLEX CLASS A`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Definition base: `93058f3f4e6a54f7e5c02254a6fd444f651326d4`.
- This document is the consolidated correction of the Definition candidate whose parent is
  `7370a4f47433142f68e0af4850e74b36f9b2d201`, followed by the focused five-blocker correction
  whose parent is `41d36c4bc5d8eb5e71fb3fc12d3ae688fe578769`.
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
- `https://docs.railway.com/networking/public-networking/specs-and-limits`
- `https://docs.railway.com/variables`
- `https://docs.railway.com/deployments/optimize-performance`
- `https://docs.railway.com/deployments/healthchecks`
- `https://docs.railway.com/deployments/deployment-teardown`

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

The only supported production topology for this package is option A: one Railway service and one
FastAPI process serve both the compiled Vite frontend and `/api`. There is no second public gateway,
private-backend hop, Caddy service, or browser cross-origin request.

1. One canonical HTTPS origin, `AUTH_PUBLIC_ORIGIN`, reaches the Railway public HTTP edge and then
   the single FastAPI service. FastAPI serves compiled frontend files and all API routes itself.
2. Railway terminates public TLS. Security-relevant forwarded information is accepted only under
   the exact public-edge provenance contract in section 4.2; private-network ingress is forbidden.
3. Exactly one backend Railway replica and exactly one Uvicorn worker are permitted. Production
   startup requires `WEB_CONCURRENCY=1`; deployment acceptance independently verifies replica
   count `1`. Horizontal replicas, overlapping rolling instances, and multiple workers are not
   supported by this Definition.
4. The existing Railway PostgreSQL service is the shared durable authority for login-attempt
   limiting. Authentication sessions themselves remain stateless signed cookies.
5. Ordinary code deploys set `RAILWAY_DEPLOYMENT_OVERLAP_SECONDS=0`; the old deployment is drained
   and removed before the new deployment may serve authenticated traffic. A signing-key rotation is
   a deliberate stop, variable replacement, and start with observable downtime. Mixed-secret
   overlap is prohibited in both cases.

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
| `AUTH_INGRESS_MODE` | Exact value `railway_public_edge`; no private-network or direct-container production ingress |
| `WEB_CONCURRENCY` | Exact decimal string `1` |
| `RAILWAY_DEPLOYMENT_OVERLAP_SECONDS` | Exact decimal string `0` |

No default, local-development value, dynamically generated secret, or plaintext password may be
used as a production fallback. Startup parses and validates the complete set before serving a
request and exits non-zero on any missing, empty, duplicate, malformed, weak, inconsistent, or
forbidden value. Error output names the invalid variable but never prints its value.

Both 32-byte secrets must be generated out of band by a cryptographically secure random generator,
with 256 bits of source entropy. Deployment evidence records the generator/procedure and variable
presence without recording either value. Startup can prove encoding and decoded length, not source
entropy; absence of the provisioning evidence stops deployment under `SC-006`.

### 4.2 Railway public-edge provenance and client-IP derivation

Railway's public-networking specification identifies `X-Real-IP` as the client's remote IP and
`X-Forwarded-Proto` as `https`; it does not publish stable ingress proxy CIDRs. The application
therefore does not implement CIDR or XFF hop inference and never reads `Forwarded`,
`X-Forwarded-For`, `CF-Connecting-IP`, or the socket peer as the end-user identity.

The authority boundary is the deployment topology, not a caller-selectable header:

1. the FastAPI service has exactly one public Railway domain/custom domain attached;
2. no TCP proxy, private-network HTTP caller, sidecar, second service, or direct container port may
   reach the production listener;
3. Railway public HTTP ingress is the only network path to that listener; and
4. deployed black-box evidence must prove that Railway overwrites a caller-supplied `X-Real-IP`
   before the request reaches the application. Railway documents the header's meaning, but marks
   public-network specifications as changeable; this proof is repeated at every release.

Only after all four conditions hold may the application consume the single `X-Real-IP` value.
Missing, duplicate, comma-containing, whitespace-repaired, zone-qualified, non-IP, or overlong
values are `400 CLIENT_IP_INVALID`. The canonical attempt IP is
`ipaddress.ip_address(value).compressed`; IPv4-mapped IPv6 is converted to canonical IPv4.
Caller-supplied `X-Forwarded-For` is ignored even when present. If a forged `X-Real-IP` survives the
edge, if the edge behavior cannot be proven, or if any alternate ingress exists, `SC-003` stops
deployment rather than accepting a spoofable limiter key.

`X-Forwarded-Proto` must occur exactly once with exact value `https`. `X-Forwarded-Host` must occur
exactly once and, after standards-based parsing, equal the host and optional port in
`AUTH_PUBLIC_ORIGIN`. The received `Host` must equal the same authority, except for the narrowly
defined Railway healthcheck in section 4.3. `Origin`, when required, is exact string equality with
`AUTH_PUBLIC_ORIGIN`.

### 4.3 Health, startup, and Railway lifecycle

- `GET /healthz/live` is data-free and returns `200` with exactly `{"status":"ok"}` when the
  process event loop is serving.
- `GET /healthz/ready` is data-free and returns `200` with exactly `{"status":"ready"}` only after
  configuration validation and a minimal PostgreSQL/limiter-schema readiness check; otherwise it
  returns `503` with exactly `{"status":"unavailable"}`.
- Neither endpoint returns environment values, database details, version strings, client data, or
  authentication state.
- Existing `GET /health` remains a public, data-free legacy liveness alias returning exactly
  `{"status":"ok"}`; it is not the Railway deployment healthcheck and performs no database query.
- Railway deployment healthcheck path is exactly `/healthz/ready`. Railway calls it over plain HTTP
  on the injected `PORT`, with Host `healthcheck.railway.app`. That Host exception is accepted only
  for `GET /healthz/live`, `GET /healthz/ready`, and `GET /health`; it never applies to `/api`, SPA,
  static, docs, or unknown paths and never authorizes forwarded client-IP input.
- A Railway healthcheck is a deployment-start gate, not continuous monitoring. Continuous uptime
  requires a separately configured external HTTPS monitor of `/healthz/ready`; absence of such a
  monitor blocks a production-readiness claim, not implementation acceptance.
- Startup listens on Railway's injected `PORT`, validates configuration, applies no migration
  implicitly, verifies migration head/schema availability read-only, and serves readiness only
  after the limiter table is usable. A smoke test then proves login shell, login, session, one
  protected route, logout, cache headers, and forged-forwarding rejection.
- Exactly one replica and `WEB_CONCURRENCY=1` are read back before activation. Overlap is zero.
  Railway may restart or relocate a singleton; stateless sessions and PostgreSQL limiter state
  survive process replacement, but session-secret changes follow the explicit downtime rotation
  procedure in section 6.3.

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

Implementation requires exactly one additive Alembic revision, `b3c9d6f2a410`, with
`down_revision = "a2b8c5e1f309"`. It creates only table `rtdir_login_rate_limit_buckets` and index
`ix_rtdir_login_rate_limit_buckets_updated_at`; it neither references nor mutates professional
retirement-planning tables. The table contract is exact:

| Column | PostgreSQL type | Null | Constraint |
|---|---|---:|---|
| `bucket_key` | `CHAR(64)` | no | primary key; lowercase hexadecimal check `bucket_key ~ '^[0-9a-f]{64}$'` |
| `bucket_kind` | `VARCHAR(8)` | no | check in `('GLOBAL','USER','IP')` |
| `window_started_at` | `TIMESTAMPTZ` | no | database-time value |
| `failure_count` | `INTEGER` | no | check `0 <= failure_count AND failure_count <= 2147483647` |
| `locked_until` | `TIMESTAMPTZ` | yes | null below threshold; otherwise exact window end |
| `updated_at` | `TIMESTAMPTZ` | no | database-time value |

The primary key is the only uniqueness authority. The named checks are
`ck_rtdir_login_bucket_key_hex`, `ck_rtdir_login_bucket_kind`,
`ck_rtdir_login_failure_count`, and `ck_rtdir_login_lock_window` (the last requires
`locked_until IS NULL OR locked_until = window_started_at + INTERVAL '900 seconds'`). Downgrade
drops the index and table only. PostgreSQL migration tests prove upgrade, downgrade, parent/head,
names, types, nullability, checks, and isolation from professional tables.

No username, password, raw IP, actor, cookie, token, or client record is stored. Keys use
HMAC-SHA-256 with decoded `AUTH_RATE_LIMIT_SECRET_B64` over these exact UTF-8 preimages:

- global: `RTDIR_LOGIN_LIMIT_V1\0GLOBAL`;
- username: `RTDIR_LOGIN_LIMIT_V1\0USER\0` plus the exact submitted valid username; and
- IP: `RTDIR_LOGIN_LIMIT_V1\0IP\0` plus the canonical client IP.

All time is one transaction-local `SELECT transaction_timestamp()` value. Fixed windows begin at
the first counted failure and last exactly 900 seconds:

- username threshold: 5 failures per window;
- IP threshold: 20 failures per window; and
- global threshold: 200 failures per window.

HMAC input is the bytes shown above: ASCII namespace/type including literal NUL bytes, followed by
the exact UTF-8 username bytes or canonical ASCII IP bytes. `bucket_key` stores
`hmac.new(secret, preimage, sha256).hexdigest()` only; `bucket_kind` is independently checked when a
row is loaded. No raw identifier is stored.

Every required bucket operation uses this exact transaction primitive:

1. begin `READ COMMITTED`; obtain database time once;
2. for each required key in ascending `bucket_key` order execute `INSERT ... VALUES (..., 0, NULL,
   db_now) ON CONFLICT (bucket_key) DO NOTHING`;
3. select all required rows in the same order `FOR UPDATE`; a kind mismatch is store corruption;
4. if `db_now >= window_started_at + INTERVAL '900 seconds'`, reset that row to
   `window_started_at=db_now, failure_count=0, locked_until=NULL, updated_at=db_now`;
5. read or mutate the locked rows, then commit; any exception rolls back the whole operation.

The unique primary key serializes concurrent first insertions: one insert wins and every contender
then locks the same row. Sorted row locking prevents cross-bucket lock-order cycles. There is no
advisory or table/global lock. The exact login sequence is:

1. validate public-edge provenance, protocol, Host, and Origin; derive the canonical IP;
2. validate the 8 KiB framing and JSON/schema. A malformed request runs one mutation primitive for
   IP and GLOBAL only, incrementing both; no username key or Argon2 call exists;
3. a valid-shaped request derives USER, IP, and GLOBAL keys and runs a read/check primitive. If any
   locked row is at its threshold, commit the observed decision and return `429` without Argon2;
4. when below threshold, commit and release every database lock, then perform exactly one real or
   dummy Argon2 verification outside every database transaction;
5. begin a new mutation primitive for USER, IP, and GLOBAL and re-evaluate all windows/thresholds.
   If another request reached a threshold during Argon2, commit no reset/increment for this attempt
   and return `429`;
6. on failed verification, increment all three counts using
   `LEAST(failure_count + 1, 2147483647)`. The transition reaching a threshold sets
   `locked_until=window_started_at + INTERVAL '900 seconds'`; saturation never wraps. Commit, then
   return `429` if any threshold is reached, otherwise `401`;
7. on successful verification below every threshold, delete the USER and IP rows in the same
   locked transaction, leave GLOBAL unchanged, commit, and only then sign/issue a session.

The linearization point is the commit of the final locked decision/mutation transaction (or the
commit of the precheck that returns an already-limited result). Thus concurrent threshold crossing
has exactly one database commit order; later commits see the threshold and cannot issue a session.
Argon2 never runs while a row/table/advisory lock is held. This permits concurrent expensive
verification while retaining a linearizable outcome at the final commit.

`Retry-After` is the ceiling of the longest positive `(locked_until - db_now)` among applicable
rows, clamped to integer `1..900`. Malformed/schema-invalid attempts never create USER rows. There
is no manual/frontend reset or progressive delay.

Before each precheck, a separate bounded cleanup transaction deletes at most 64 rows selected by
`updated_at, bucket_key` with `FOR UPDATE SKIP LOCKED` where
`updated_at < transaction_timestamp() - INTERVAL '1800 seconds'`. A single-process lifespan task
runs the same cleanup every 900 seconds; startup and each scheduled run repeat 64-row transactions
until no eligible row remains. Thus a healthy running deployment retains no expired row beyond one
cleanup interval after the 1800-second eligibility delay, while each transaction remains bounded.
No current or immediately previous window is deleted. Cleanup failure rolls back, marks readiness
unavailable, and causes login to return `503 AUTH_RATE_LIMIT_UNAVAILABLE` before Argon2 until a
cleanup succeeds; already-authenticated professional requests remain available because the limiter
is not their authority. It never silently disables retention. Store timeout, unavailable database,
missing/malformed table, lock/deadlock exhaustion, transaction failure, or ambiguous database time
has the same fail-closed login result. PostgreSQL tests must interleave concurrent first insertion,
threshold crossing, success/failure reset order, saturation, cleanup/`SKIP LOCKED`, restart
persistence, scheduled cleanup failure/recovery, and injected store failure; each asserts committed
rows and returned status, not only mocked calls.

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

1. Railway public-edge provenance/protocol/Host validation;
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

### 7.4 Complete public/protected HTTP surface

Production constructs FastAPI with `docs_url=None`, `redoc_url=None`, and `openapi_url=None`.
Consequently `/docs`, `/redoc`, and `/openapi.json` are ordinary `404 ROUTE_NOT_FOUND` responses;
they are neither public documentation nor an authentication side channel. Development may enable
them only under non-production configuration bound to loopback; production startup fails if any is
registered.

The complete unauthenticated production allowlist is:

- `GET`/`HEAD /`, `GET`/`HEAD /login`, and `GET`/`HEAD` for each exact existing frontend route
  pattern: `/clients`, `/clients/new`, `/clients/{positive_id}`,
  `/clients/{positive_id}/employment-history`, `/clients/{positive_id}/pension-products`,
  `/clients/{positive_id}/legacy-conversion-history`,
  `/clients/{positive_id}/professional-sources`, `/clients/{positive_id}/planning-input`,
  `/clients/{positive_id}/grants`, `/clients/{positive_id}/actual-capitalizations`,
  `/clients/{positive_id}/fixation/workspace`, `/clients/{positive_id}/fixation/input`,
  `/clients/{positive_id}/fixation/result`, `/clients/{positive_id}/fixation/history`,
  `/clients/{positive_id}/fixation/runs/{positive_run_id}`, plus the existing non-client
  `/fixation/input`, `/fixation/result`, `/fixation/history`, and
  `/fixation/runs/{positive_run_id}`; these exact paths return the same data-free `index.html` shell;
- `GET`/`HEAD /assets/{build-manifest filename}` and exact root static files emitted by the compiled
  build manifest. Path traversal, source maps, dotfiles, arbitrary filesystem paths, and a filename
  absent from the manifest are never served;
- `POST /api/auth/login`;
- valid CORS `OPTIONS` under section 7.2; and
- `GET`/`HEAD /health`, `/healthz/live`, and `/healthz/ready` under section 4.3.

The public shell and static assets contain no client data, actor value, username, credential,
secret, CSRF, environment value, or serialized authenticated state. Public immutable hashed assets
use `Cache-Control: public, max-age=31536000, immutable`; `index.html`, login shell, and un-hashed
root assets use `Cache-Control: no-store`. A public shell may render only the authentication gate
until `GET /api/auth/session` succeeds.

Every other registered HTTP route is authenticated before route existence, path parsing, or data
disclosure. This includes every current router family in the repository: `/api/clients` and all
client case/profile/clearinghouse/document/historical-analysis/capital/income/expense/work-intention/
assumption/missing-item/employment/grant/capitalization descendants; professional-source and
canonical-pension-source routes; all retirement-planning-input and projection routes; all fixation
and M07 routes; official-parameter-set routes; pension-product/import routes; canonical-conversion
routes; legacy M06 archive reads; M09 reads; and the four new RTDIR context/target/comparison routes.
It also includes `GET /api/auth/session` and `POST /api/auth/logout`. The implementation test
enumerates `app.routes` and fails if any APIRoute is neither in this protected set nor the exact
public allowlist; protection is not inferred from an `/api` prefix.

At this Definition base, the exact protected route-pattern inventory (method is the method already
registered by the referenced router; no additional method is implied) is:

- `/api/clients`, `/api/clients/{client_id}`, `/case`, `/profile`;
- client descendants `/clearinghouse-snapshots[/{clearinghouse_snapshot_id}[/verification]]`,
  `/documents[/{document_id}[/verification]]`,
  `/pension-holdings/{pension_holding_id}/analysis-record`,
  `/capital-assets[/{capital_asset_id}]`, `/recurring-incomes[/{recurring_income_id}]`,
  `/recurring-expenses[/{recurring_expense_id}]`,
  `/retirement-timing-work-intentions[/{retirement_timing_work_intention_id}]`,
  `/planner-assumptions[/{planner_assumption_id}]`, `/missing-items[/{missing_data_item_id}]`,
  `/employment-records[/{employment_record_id}]`, `/grants[/{grant_id}]`, and
  `/actual-capitalizations[/{capitalization_id}]`;
- client descendants `/professional-source-snapshot`,
  `/canonical-pension-sources/manual[/{source_id}]`, and
  `/canonical-pension-sources/conversion/{destination_id}/temporal-authority`;
- client descendant `/retirement-planning-input` plus `/capital-projection`, `/base-date`,
  `/income-resolutions/{income_id}`, `/target-date`, `/projection-basis`,
  `/projection-basis/{capital_asset_id}`, and `/projection-basis/{capital_asset_id}/clear`;
- `/api/fixation/review/validate`, `/api/fixation/review/convert`, `/api/fixation/save`, and client
  descendants `/fixation/validate`, `/fixation/calculate`, `/fixation/latest`, `/fixation/history`,
  `/fixation/runs/{run_id}`, `/fixation/runs/{run_id}/internal-planner-judgment`,
  `/fixation/runs/{run_id}/dependency-manifest`,
  `/fixation/runs/{run_id}/dependency-comparison`, `/fixation/m07/revisions`, and
  `/fixation/m07/eligibility-date-revisions`;
- `/api/official-parameter-sets`, `/resolve`, and `/{parameter_set_id}`;
- client descendant `/pension-products`, `/imports`, `/save-selected`, and `/{product_id}`;
- client descendant `/canonical-conversions`, `/preview`, and `/{conversion_id}/reverse`;
- client descendants `/m06/subjects[/{subject_id}[/history]]` and
  `/m09/inventories/{inventory_id}`, `/m09/runs[/{run_id}]`,
  `/m09/subjects[/{subject_id}[/runs[/{run_id}]]]`;
- new `/api/auth/session`, `/api/auth/logout`; and
- new client descendants `/retirement-income-readiness/context`,
  `/retirement-income-readiness/target`, and `/retirement-income-readiness/comparison`.

Square brackets above are inventory notation only. The runtime oracle compares concrete
`(method, path_format)` pairs, including every GET/POST/PUT/DELETE registration, against a checked-in
expected set. Any newly registered route fails closed until this Definition or an accepted successor
classifies it.

Unknown `/api/*` requests authenticate first, then return `404 ROUTE_NOT_FOUND`. Unknown non-API
paths do not receive SPA fallback and return the same 404 envelope after the public-route matcher.
Methods not registered on a known path return `405 METHOD_NOT_ALLOWED`; they never fall through to
`index.html`. The healthcheck Host exception cannot reach any route outside the three health paths.

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

`field_paths` is a deterministically sorted unique list of RFC 6901 JSON Pointers and contains no
submitted values. Body fields use `/<escaped-field-name>`; path parameters use
`/path/<escaped-parameter-name>`; a missing body itself uses `/`; an extra field uses its actual
escaped field name. Multiple failures are sorted by UTF-8 byte order after pointer construction.
Authentication failures always use an empty list. Unknown internal exceptions
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
response. Precedence is exactly: public-edge/proto/forwarded-host/Host; public/preflight/protected
classification; CORS preflight; Origin where required; login Content-Type and byte limit; session;
CSRF; JSON framing; path/query/body schema; client/address identity; accepted service execution;
producer shape/response identity; known infrastructure mapping; unexpected failure. For an unknown
`/api` path, the protected classification deliberately authenticates before the final route-not-found
decision. No later failure may replace an earlier response:

Every transport failure uses exactly `TransportErrorV1`, the listed status/code/field paths, and
`Cache-Control: no-store, private` plus `Pragma: no-cache`. “Retry” below means a caller may retry
only after satisfying the stated condition; it is not an automatic frontend loop.

| Failure class | HTTP | Unique code or professional response | `field_paths` | Retry |
|---|---:|---|---|---|
| Login Content-Type not exactly JSON (parameters allowed only valid UTF-8 charset) | 415 | `LOGIN_CONTENT_TYPE_UNSUPPORTED` | `[]` | no; correct request |
| Login body exceeds 8192 bytes before JSON parse | 413 | `LOGIN_BODY_TOO_LARGE` | `[]` | no; reduce body |
| Malformed JSON/UTF-8/framing | 400 | `REQUEST_JSON_INVALID` | `[]` | no; correct request |
| Login missing/unknown/extra/wrong-type/invalid field | 422 | `LOGIN_REQUEST_INVALID` | sorted exact `/username`, `/password`, and/or actual extra-field pointer | no; correct request |
| Other request/path schema failure | 422 | `REQUEST_SCHEMA_INVALID` | sorted exact failing paths | no; correct request |
| Missing/duplicate/malformed edge IP, proto, forwarded host, or ordinary Host | 400 | `EDGE_REQUEST_INVALID` | `[]` | no; deployment/client correction |
| Wrong/missing login or unsafe-request Origin | 403 | `ORIGIN_FORBIDDEN` | `[]` | no; correct origin |
| Wrong username or password below every threshold | 401 | `AUTHENTICATION_FAILED` | `[]` | yes; new deliberate login |
| Bucket already/recently reaches threshold | 429 | `LOGIN_RATE_LIMITED` plus exact `Retry-After` | `[]` | only after Retry-After |
| Limiter cleanup/store/schema/time/transaction unavailable | 503 | `AUTH_RATE_LIMIT_UNAVAILABLE` | `[]` | yes; after service recovery |
| Protected request has no session cookie | 401 | `SESSION_MISSING` | `[]` | yes; login |
| Bad signature, malformed/extra/wrong-type payload, wrong actor, or future-dated session | 401 | `SESSION_INVALID` | `[]` | yes; login |
| Validly signed but expired session | 401 | `SESSION_EXPIRED` | `[]` | yes; login |
| Missing/malformed/mismatched CSRF on unsafe authenticated request | 403 | `CSRF_INVALID` | `[]` | yes; reload session then retry deliberately |
| Addressed client does not exist on a route that owns lookup | 404 | `CLIENT_NOT_FOUND` | `["/path/client_id"]` | no; select valid client |
| Stale planning-input/target identity | 409 | `PLANNING_IDENTITY_STALE` | `[]` | yes; reload context |
| RIT record-version CAS conflict | 409 | `RIT_VERSION_CONFLICT` | `["/expected_record_version"]` | yes; reload target |
| Accepted producer returns malformed/missing required output | 500 | `PRODUCER_RESPONSE_INVALID` | `[]` | no automatic retry |
| Non-null producer response client differs from path | 500 | `RESPONSE_CLIENT_MISMATCH` | `[]` | no automatic retry |
| Context database retry exhausted | 503 | `CONTEXT_DATABASE_RETRY_EXHAUSTED` | `[]` | yes; after backoff |
| RIT assessment database retry exhausted | 503 | `RIT_ASSESS_DATABASE_RETRY_EXHAUSTED` | `[]` | yes; after backoff |
| RIT confirmation database retry exhausted | 503 | `RIT_CONFIRM_DATABASE_RETRY_EXHAUSTED` | `[]` | yes; reload before retry |
| RTICB technical database retry exhausted before a professional envelope exists | 503 | `RTICB_DATABASE_RETRY_EXHAUSTED` | `[]` | yes; after backoff |
| RTICB professional `block_no_result` | 200 | exact accepted RTICB envelope | not applicable | professional workflow only |
| Known non-limiter backend infrastructure unavailable | 503 | `BACKEND_INFRASTRUCTURE_UNAVAILABLE` | `[]` | yes; after service recovery |
| Unexpected programming/serialization/framework failure | 500 | `INTERNAL_ERROR` | `[]` | no automatic retry |
| Authenticated unknown path | 404 | `ROUTE_NOT_FOUND` | `[]` | no |
| Unsupported method on known route | 405 | `METHOD_NOT_ALLOWED` | `[]` | no; correct method |

`400`, `401`, `403`, `404`, `405`, `409`, `413`, `415`, `422`, `429`, `500`, and `503` use
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
| `API-002` | Runtime `app.routes` inventory proving the complete HTTP surface is public or protected exactly as section 7.4; actor/client addressing and response-identity tests |
| `API-003` | Table-driven exact DTO/status/code/body/field-path/retry/cache tests for every row in section 9.4 and preservation of professional envelopes |
| `API-004` | Spies/mutations proving exact once-only service calls, argument construction, pristine session admission, and no route-owned transaction leakage |
| `PG-001` | Real PostgreSQL migration/schema, concurrent first-insert, threshold-crossing, recheck-after-Argon, reset order, saturation, cleanup/retention, restart persistence, and fail-closed store tests |
| `PG-002` | Real PostgreSQL RIT confirmation/CAS/retry/actor/no-partial-write regressions through the route |
| `PG-003` | Real PostgreSQL RTICB repeatable-read/read-only single-snapshot and no-prequery/no-second-session tests |
| `BROWSER-001` | Hebrew RTL login/session-expiry/logout-failure/cache and no-persistent-secret tests |
| `BROWSER-002` | Context/target/confirmation/refresh/client-switch and mixed RTICB blocker/source/reason presentation tests |
| `DEPLOY-001` | Railway staging black-box proof of one FastAPI origin/service, compiled SPA routing, HTTPS, overwritten `X-Real-IP`, forbidden alternate ingress, healthcheck Host/HTTP behavior, one replica/worker, zero overlap, rotation downtime, smoke test, cookie, CORS, and cache headers |
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
| Skip dummy Argon2 or distinguish unknown username timing/body/logging | `API-001`, `MUT-001` |
| Accept tampered, expired, future-dated, malformed, wrong-actor, or sliding session | `PURE-001`, `API-001`, `MUT-001` |
| Leave one pre-existing registered data route outside authentication | `API-002`, `MUT-001` |
| Make docs/OpenAPI public in production or authenticate/deny the login shell/assets | `API-002`, `DEPLOY-001`, `MUT-001` |
| Apply SPA fallback to unknown API/path or embed client/auth state in public shell | `API-002`, `BROWSER-001`, `MUT-001` |
| Let Railway health Host exception reach API/static/SPA or treat deploy check as monitoring | `DEPLOY-001`, `MUT-001` |
| Trust forged `X-Real-IP`, XFF, `Forwarded`, or private-network header provenance | `PURE-001`, `DEPLOY-001`, `MUT-001` |
| Hold limiter row/global lock during Argon or omit final locked threshold recheck | `PG-001`, `MUT-001` |
| Race concurrent initial insert/threshold commit or wrap saturated counter | `PG-001`, `MUT-001` |
| Delete current limiter row, make cleanup unbounded, or ignore cleanup failure | `PG-001`, `MUT-001` |
| Merge ambiguous 500/503 or retry-exhaustion mappings | `API-003`, `MUT-001` |
| Pre-query/duplicate-invoke RIT assess or allow confirm actor/client override | `API-004`, `PG-002`, `MUT-001` |
| Reclassify context result or accept response client mismatch | `API-003`, `API-004`, `MUT-001` |
| Permit overlapping old/new signing secrets or nonzero Railway deployment overlap | `API-001`, `DEPLOY-001`, `MUT-001` |

For every row above, `MUT-001` records the concrete mutated statement/branch, executes through the
ordinary HTTP/service/PostgreSQL/deployed path, proves the mutant line/branch was reached, observes
the named ordinary oracle fail, restores the source, and observes the unmodified control pass.
Mock-only reachability, a mutant-specific assertion, or an expected exception injected directly by
the test does not satisfy the mutation contract.

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
| `AC-037` | Migration `b3c9d6f2a410` has exact parent/schema/check/index/downgrade and remains isolated from professional authorities. | `PG-001`, `GOV-001` |
| `AC-038` | Limiter operations are linearizable at commit, including concurrent first insert and threshold crossing, without a database lock during Argon2. | `PG-001`, `MUT-001` |
| `AC-039` | Failure saturation, successful reset, Retry-After, cleanup retention, and every store/cleanup failure match section 5.3. | `PURE-002`, `PG-001`, `API-001` |
| `AC-040` | Every section 9.4 failure has its sole status/code/envelope/field-path/cache/retry behavior and professional `block_no_result` remains HTTP 200. | `API-003`, `BROWSER-002` |
| `AC-041` | One FastAPI Railway service serves compiled SPA and API at one HTTPS origin with no alternate/private ingress. | `DEPLOY-001`, `GOV-001` |
| `AC-042` | Client IP is derived only from Railway-edge-overwritten `X-Real-IP`; XFF/Forwarded/CF/direct/private inputs cannot forge it. | `PURE-001`, `DEPLOY-001` |
| `AC-043` | Railway readiness uses its exact Host/HTTP exception, remains deployment-only, and startup/smoke/replica/worker/zero-overlap conditions are proven. | `DEPLOY-001` |
| `AC-044` | Full runtime route inventory enforces the exact public data-free surface, production docs disablement, protected data routes, cache policy, and closed SPA fallback. | `API-002`, `BROWSER-001`, `DEPLOY-001` |
| `AC-045` | All newly enumerated security/transport/deployment mutants reach and fail ordinary acceptance oracles before restoration. | `MUT-001` |

Acceptance range: `AC-001` through `AC-045`; count: `45`.

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
| `NAC-023` | Limiter lock is held during Argon2, a concurrent commit can bypass threshold, or a counter wraps. | `PG-001`, `MUT-001` |
| `NAC-024` | Cleanup deletes an active/recent row, grows without bound by contract, fails open, or blocks the whole table. | `PG-001`, `MUT-001` |
| `NAC-025` | Any alternative status/code is selected for a section 9.4 failure or a professional envelope is reclassified. | `API-003`, `MUT-001` |
| `NAC-026` | Separate public frontend/backend origins, alternate ingress, caller-trusted IP header, or unverified Railway edge provenance. | `DEPLOY-001`, `GOV-001` |
| `NAC-027` | Production docs/OpenAPI, unknown SPA fallback, client-bearing public shell, or unauthenticated data route. | `API-002`, `BROWSER-001`, `MUT-001` |
| `NAC-028` | Healthcheck Host exception reaches non-health routes, overlap is nonzero, or healthcheck is represented as continuous monitoring. | `DEPLOY-001`, `MUT-001` |

Negative-acceptance range: `NAC-001` through `NAC-028`; count: `28`.

## 16. Deterministic implementation and deployment stop conditions

| ID | Stop condition | Detection oracle/evidence |
|---|---|---|
| `SC-001` | Repository/base/accepted upstream contract differs from the accepted implementation authorization. | `GOV-001` identity check |
| `SC-002` | One same-origin HTTPS frontend/API topology cannot be implemented without an unaccepted architecture change. | `DEPLOY-001` topology proof |
| `SC-003` | Railway public ingress does not demonstrably replace caller `X-Real-IP`, or an alternate/private path reaches the listener. | `DEPLOY-001` ingress proof |
| `SC-004` | Railway cannot enforce/read back exactly one backend replica and one worker or requires overlapping mixed-secret instances. | `DEPLOY-001` configuration readback |
| `SC-005` | PostgreSQL limiter migration/atomic locking/database time cannot satisfy section 5.3. | `PG-001` |
| `SC-006` | Required production secret/config input is absent/malformed or would require a committed/plaintext fallback. | `PURE-001`, startup/readiness proof |
| `SC-007` | Pinned Argon2/signing dependency or exact cryptographic parameters cannot be installed and verified on the deployment runtime. | `PURE-001`, `DEPLOY-001` |
| `SC-008` | Global middleware cannot classify and protect the complete registered HTTP inventory with only the exact public allowlist. | `API-002` route inventory |
| `SC-009` | Configured actor fails the exact RIT predicate or accepted RIT cannot receive it solely from authenticated server context. | `PURE-001`, `API-002`, `PG-002` |
| `SC-010` | Exact DTO/status mapping would require changing an accepted Planning Input/RIT/RTISA/RTICB professional contract. | `API-003`, contract diff |
| `SC-011` | Comparison cannot pass a pristine session to public RTICB assess without pre-query, second session, or transaction workaround. | `API-004`, `PG-003` |
| `SC-012` | A material security/transaction/UI mutation cannot reach and fail an ordinary production-path oracle. | `MUT-001` |
| `SC-013` | Deployment black-box evidence cannot prove HTTPS, Host/proxy, cookie, CORS, cache, limiter persistence, health, and rotation constraints. | `DEPLOY-001` |
| `SC-014` | Implementation discovers a new professional decision, calculation authority, multi-user need, or downstream dependency. | `GOV-001` and owner/governance review |
| `SC-015` | Railway public-edge testing does not prove caller `X-Real-IP` replacement, or an alternate/private path can reach the listener. | `DEPLOY-001` ingress proof |
| `SC-016` | FastAPI cannot serve the exact compiled SPA/static allowlist and protected API on one Railway service without widening the public surface. | `API-002`, `DEPLOY-001` |

Stop-condition range: `SC-001` through `SC-016`; count: `16`. Encountering any condition stops
implementation or deployment at that gate. It does not authorize a workaround, weaker guarantee,
new infrastructure, or scope expansion.

## 17. Independent blocker disposition

| Blocker | Definition disposition |
|---|---|
| `RTDIR-VS-GOV-001` | Closed by sections 13–16: contiguous unique `AC-001..045`, `NAC-001..028`, `SC-001..016`, exact counts, oracle mappings, and deterministic stop conditions. |
| `RTDIR-VS-SEC-001` | Closed by section 5.3 and `AC-037..039`: mandatory revision/parent, exact PostgreSQL schema, HMAC storage, bounded/saturating counters, sorted insert-and-lock primitive, no lock during Argon2, final linearization commit, concurrent insertion/crossing, cleanup/retention, reset, restart and fail-closed oracles. |
| `RTDIR-VS-SEC-002` | Closed by sections 4–6: exact input limits, Argon2id policy, token/signature/secret/nonce/lifetime/cookie/config/startup contract. |
| `RTDIR-VS-SEC-003` | Closed by section 6.3: single active key, stop/start rotation, no overlap/previous key, explicit copied-token behavior. |
| `RTDIR-VS-SEC-004` | Closed by section 7.1–7.2: exact CSRF header/token binding/order/constant-time checks and closed CORS/preflight/origin policy. |
| `RTDIR-VS-SEC-005` | Closed by sections 7.3 and 11.1: exact logout failure states, deletion versus revocation limits, retry/reload, and no-store/browser-cache contract. |
| `RTDIR-VS-ACTOR-001` | Closed by section 8: exact RIT `_valid_actor` predicate and server-only authenticated binding. |
| `RTDIR-VS-API-001` | Closed by section 9.2: exact two-field browser comparison DTO, forbidden caller client ID/extras, then path injection. |
| `RTDIR-VS-API-002` | Closed by section 10: no comparison pre-query/second session/rollback workaround and exact RTICB public snapshot ownership. |
| `RTDIR-VS-API-003` | Closed by section 9.4 and `AC-040`: every listed failure has one status, machine code/professional response, field-path rule, retry rule, no-store behavior, and executable ordinary oracle without reclassifying `block_no_result`. |
| `RTDIR-VS-UI-001` | Closed by section 11: deterministic multi-blocker/source/reason composition, neutral readiness, refresh/conflict/client isolation, Hebrew RTL, and logout/cache behavior. |
| `RTDIR-VS-DEPLOY-001` | Closed at Definition level by sections 3–4 and `AC-041..043`: one FastAPI service/origin, compiled SPA plus API, public-edge-only ingress, Railway `X-Real-IP` deployment proof, exact health Host/HTTP behavior, one replica/worker, zero overlap, rotation downtime and smoke gate. |
| `RTDIR-VS-TEST-001` | Closed by section 13 and `AC-045`: complete ordinary and reached-path mutation inventory covers all five focused surfaces and records mutant, production path, reach evidence, oracle failure, restoration and passing control. |
| `RTDIR-VS-SEC-006` | Closed by section 7.4 and `AC-044`: exact public data-free login/static/SPA/preflight/health surface, complete protected registered-route inventory, production docs disablement, closed fallback/unknown/method behavior, Host exception and cache policy. |

## 18. Final consistency and authorization gate

The original thirteen blockers plus focused `RTDIR-VS-SEC-006` are addressed by one internally
consistent architecture. The five focused blockers are `SEC-001`, `API-003`, `DEPLOY-001`,
`TEST-001`, and `SEC-006`; the nine previously closed blockers retain their accepted dispositions.
No professional ambiguity and no additional Owner/Product Decision remains.

Remaining prerequisites are deterministic implementation/deployment work, not unresolved
Definition choices:

1. independently accept this corrected Definition;
2. separately authorize implementation;
3. provision actual non-committed credentials/secrets and the canonical HTTPS origin;
4. prove the deployed Railway public edge overwrites caller `X-Real-IP` and that no alternate
   ingress reaches the FastAPI listener;
5. enforce/read back one replica and one worker;
6. apply and validate the PostgreSQL limiter migration;
7. execute all mapped ordinary and mutation suites; and
8. pass deployed-topology evidence before any production-readiness claim.

No implementation, Railway resource mutation, password generation, push, merge, downstream
authorization, or production-readiness claim is part of this Definition correction.

Implementation = `NOT_AUTHORIZED`.

Downstream = `NOT_AUTHORIZED`.

Production readiness = `NOT_CLAIMED`.
