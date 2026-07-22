# PKG-003 Acceptance Record

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-003 - M08F Dependency Manifest and Technical Change Detection Foundation` |
| Status | `ACCEPTED_WITH_FOLLOW_UP` |
| Base | `9801bac` |
| Accepted implementation HEAD | `4b89d49` |
| Migration head | `d7a3c9e5f102` |

## Accepted Commit Chain

1. `d142b7d feat: add fixation dependency manifest`
2. `69dac25 feat: expose client-scoped dependency assessment`
3. `70f8da3 test: prove PKG-003 dependency boundaries`
4. `5677412 fix: require admitted dependency comparison context`
5. `9048495 fix: include complete fixation dependencies`
6. `fb1ac3b fix: enforce trusted dependency comparison context`
7. `e4af047 fix: align dependency manifest identifiers`
8. `68345a0 test: prove PKG-003 acceptance corrections`
9. `19eabee fix: make dependency trust server-controlled`
10. `7a02e76 test: prove final PKG-003 trust boundaries`
11. `0a93830 fix: remove forgeable CBS comparison provenance`
12. `4b89d49 test: prove CBS comparison is fail-closed`

## Accepted Technical Scope

PKG-003 establishes a typed and versioned dependency manifest with immutable one-to-one persistence for new fixation runs. It uses hybrid explicit identity and canonical SHA-256 JSON fingerprinting, binds every manifest to its client and run, and provides the technical comparison results `unchanged`, `changed`, and `unknown` against an explicit current comparison context.

The accepted foundation includes mandatory-dependency preflight, fail-closed duplicate dependency identities, client isolation, side-effect-free comparison, and legacy-run behavior of `unknown` without fabricated backfill. The migration is additive. The package does not change `is_latest`, latest-success behavior, or history ordering.

## Contract Identities

| Contract | Identity |
|---|---|
| Manifest schema | `pkg003.fixation-dependency-manifest.v1` |
| Content schema | `pkg003.dependency-content.v1` |
| Fingerprint algorithm | `sha256-canonical-json-v1` |
| Comparison algorithm | `pkg003.dependency-comparison.v1` |
| CBS adapter | `pkg002.cbs-indexation-adapter.v1` |

## CBS Boundary

Saved CBS evidence produced through PKG-002 admission may be persisted in the immutable historical manifest. PKG-003 comparison never treats current CBS evidence as authoritative: a current CBS comparison returns `unknown` with reason `current_cbs_evidence_unavailable` and does not call CBS or use a fallback. Reusing a saved historical CBS manifest as current context does not retain trust. No token, wrapper, flag, provenance factory, or trusted-current comparator exists.

## Closed Defects

- `D-301 CLOSED`
- `D-301R CLOSED`
- `D-302 CLOSED`
- `D-302R CLOSED`
- `D-303 CLOSED`
- `D-304 CLOSED`
- `D-305 CLOSED`
- `D-306 CLOSED`
- `D-307 CLOSED`

## Verification Evidence

| Verification | Result |
|---|---|
| Focused PKG-003 | `63 passed` |
| Full backend | `346 passed` |
| Migration | `7 passed` |
| PKG-001/002/003 regression | `116 passed` |
| API/client-isolation final selected audit group | `80 passed` |
| Frontend | `80 passed` |
| Frontend production build | `passed` |
| Python compile | `passed` |
| Alembic | single head `d7a3c9e5f102` |
| Git diff check | `passed` |
| Skipped tests | `none` |
| Live CBS requests during comparison audit | `none` |

## Accepted Follow-up Limitations

| Limitation | Classification |
|---|---|
| Explicit current context | accepted limitation |
| Current CBS comparison always returns `unknown` | accepted limitation |
| No parameter catalog | follow-up package |
| No M07 repository | follow-up package |
| No automatic current resolver | follow-up package |
| No professional stale mapping | follow-up package |
| No prior-fixation runtime fact | follow-up package |
| No rerun, replay, or correction | follow-up package |
| No UI | accepted limitation for PKG-003 |
| No independent application build identity | follow-up package |
| No adapter runtime build identity | follow-up package |

These limitations do not authorize another implementation package.

## Explicit Exclusions

- professional acceptance;
- downstream eligibility;
- persisted stale state;
- requires-review lifecycle;
- supersession;
- correction chain;
- rerun or replay;
- prior-fixation fact;
- parameter catalog;
- M07 repository;
- automatic resolver;
- UI;
- full M08F lifecycle;
- M08E;
- M09-M14;
- formal 161D;
- 02M;
- V1/V2 parity;
- production-readiness claim.

## Closure Boundary

PKG-003 acceptance does not mean full M08F completion, professional eligibility implementation, M08 completion, production readiness, formal 161D readiness, or V1/V2 parity. The next package is not authorized by this record.
