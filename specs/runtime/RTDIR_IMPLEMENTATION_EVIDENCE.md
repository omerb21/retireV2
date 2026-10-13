# RTDIR implementation traceability evidence

Package: `RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE`
Accepted definition: `07f9025d8e2aadf850491e69eedae3c99a4d27cc`

This is implementation evidence, not a new Definition, independent acceptance, downstream
authorization, Railway deployment proof, or production-readiness claim.

## Executable traceability matrix

| Definition obligations | Production owner | Ordinary oracle | Mutation-sensitive oracle | Environment |
|---|---|---|---|---|
| AC-001..003, 018..020, 037, 044; NAC-001..003, 015..016, 027; SC-001, 008..009 | `main`, security middleware, route inventory, migration | `test_rtdir_vertical_slice.py`, `test_rtdir_migration.py`, governance baseline | missing session, forged actor, unknown API, altered head/route inventory fail | SQLite/local + static Git |
| AC-004..017, 033, 038..039, 042..043; NAC-004..013, 023..024, 026, 028; SC-003..007, 013, 015 | config/session/transport/auth/limiter | RTDIR security tests and opt-in `test_rtdir_postgresql.py` | wrong Origin/edge/CSRF/cookie/hash parameters, threshold races, saturation and cleanup fail | local pure/API + isolated PostgreSQL 16; Railway black-box remains unavailable |
| AC-021..027, 040; NAC-017..019, 025; SC-010..011 | readiness adapters and accepted Planning Input/RIT/RTICB owners | RTDIR adapter tests plus existing Planning Input/RIT/RTISA/RTICB suites | client override, producer identity, duplicate call/session/prequery and mapping mutations fail | SQLite/local + isolated PostgreSQL where opted in |
| AC-028..031; NAC-014, 020..022 | authentication gate and Hebrew RTL readiness screen | AuthenticationGate/authenticated API tests and frontend full suite | persisted credential, missing abort generation, reordered evidence, hidden excluded source mutations fail | Vitest/jsdom + production build |
| AC-032, 041..043; NAC-026, 028; SC-002..004, 006..007, 013, 015..016 | Dockerfile, Railway config, compiled SPA serving, startup config | build, static config and local production-path API tests | extra replica/worker/overlap, alternate origin/route, widened health exception fail | local build; actual Railway staging explicitly outstanding |
| AC-034..036, 045; NAC-002, 022; SC-012, 014 | consolidated governance and mutation evidence | focused/integrated/full suites and `git diff --check` | ordinary production-path assertions must fail under each material mutation and pass after restoration | local + isolated PostgreSQL; no downstream behavior |

The authoritative contiguous obligation inventories remain in the accepted Definition and are
checked as exactly `AC-001..AC-045`, `NAC-001..NAC-028`, and `SC-001..SC-016`. The accepted
producer reconciliation remains exactly 97 observations: 18 Planning Input, 29 RIT, 30 reached
RTISA, and 20 RTICB; 73 route-reached and 24 preempted. Implementation adapters do not create,
rename, retry, or reclassify those producer outcomes. Preempted cases are proved through the
accepted producer/path invariants rather than fabricated database states.

## Deployment evidence boundary

The repository implements the single-service/single-origin contract, production configuration
validation, one worker, one replica declaration, zero overlap gate, exact internal readiness
exception, compiled SPA allowlist, protected API middleware, and durable PostgreSQL limiter.
Actual Railway evidence is intentionally not claimed here. Before production readiness, staging
must independently prove public HTTPS, edge replacement of caller `X-Real-IP`, absence of alternate
ingress, replica/worker readback, zero-overlap secret rotation, secret-provisioning procedure,
healthcheck Host behavior, smoke login/session/protected-route/logout, CORS/cache/cookie headers,
external continuous readiness monitoring, and limiter persistence across restart.

Downstream implementation is not authorized. Production readiness is not claimed.

## Consolidated implementation-audit correction

The append-only correction after candidate `a68befe` adds executable ordinary oracles for the
reported code findings: deployment-mode ambiguity fails closed; readiness queries the exact
`b3c9d6f2a410` head; production builds use same-origin `/api`; invalid/expired logout preserves
401 plus cookie deletion; uncertain browser logout hides client data and exposes retry and session
check actions; CSRF is canonical decoded 32-byte base64url with constant-time byte comparison;
accepted producer outputs are strictly shape, state, identity, and fingerprint checked; and
unexpected production exceptions use the no-store `INTERNAL_ERROR` envelope.

The PostgreSQL module reaches the real saturating UPDATE branch and adds migration-head, concurrent
placeholder/threshold, zero-anchor, restart-persistence, and cleanup evidence. Those tests remain
opt-in and are not claimed executed when an isolated PostgreSQL 16 environment is unavailable.
Railway black-box evidence remains a deployment-only gate.
