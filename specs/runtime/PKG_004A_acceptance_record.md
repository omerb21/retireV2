# PKG-004A Acceptance Record

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-004A - Annual Tax Parameter-Set Authority Foundation` |
| Status | `ACCEPTED_WITH_FOLLOW_UP` |
| Base | `2c87e00` |
| Accepted implementation HEAD | `f7a03a0` |
| Migration head | `a8e4f2c6d901` |

## Professional Decision

Official annual tax and fixation parameters are global. They are not client-owned and are not accepted separately by each client. Client-specific results arise from client facts and calculation inputs, while official parameter authority is selected by exact tax year and effective period.

## Accepted Commit Chain

1. `ff2bf5d feat: add official annual parameter sets`
2. `8c935e0 feat: resolve effective official parameters`
3. `22ba03c feat: expose parameter authority boundaries`
4. `a02a227 test: prove PKG-004A parameter authority`
5. `053cbc5 test: register PKG-004A additive table`
6. `121445f fix: enforce official parameter evidence boundaries`
7. `bc01e09 test: prove PKG-004A acceptance corrections`
8. `b05629c fix: preserve superseded parameter evidence immutability`
9. `e0f541c fix: align parameter pagination contract`
10. `1243d79 test: prove final PKG-004A corrections`
11. `b409ebb fix: make parameter supersession an atomic service operation`
12. `f7a03a0 test: prove supersession cannot be forged`

## Accepted Technical Scope

PKG-004A establishes global official parameter-set persistence with a stable ID, tax year, effective period, revision/version, Decimal/Numeric storage, source and evidence metadata, a canonical readable payload, and a deterministic fingerprint.

The accepted parameter values are:

- monthly cap;
- exemption percentage;
- capital multiplier;
- grant impact multiplier.

The accepted lifecycle is `draft`, `verified`, `active`, `rejected`, and `superseded`. Active and superseded evidence is immutable; evidence states have deletion protection; and correction is performed through a new revision. Official supersession is a narrow atomic service-only operation.

Resolution requires exact tax-year and effective-date applicability and produces `resolved`, `unavailable`, or `ambiguous`. There is no fallback or latest-wins behavior. The public API uses read-safe DTOs and bounded pagination with `items`, `total`, `offset`, and `limit`. Admission evidence is repository-resolved, and caller-supplied values cannot forge official authority.

## Authority Boundary

- There is no `client_id`, client acceptance, `accepted_by`, or client-specific parameter override.
- Caller values do not become official authority, and equality of values does not grant authority.
- Repository lookup is required.
- No token, wrapper, flag, marker, or provenance capability exists.
- Direct ORM update cannot supersede an active record.
- Official supersession uses a narrow atomic database update.
- Only `status`, `superseded_by`, and `superseded_at` change during supersession.
- Stale or repeated supersession fails closed.

## Selection Semantics

- Exact tax-year match is required.
- The requested effective date must be included in the effective period.
- Only `active` records are candidates.
- Zero candidates returns `unavailable`.
- One candidate returns `resolved`.
- Multiple candidates returns `ambiguous`.
- There is no previous-year fallback, newest-revision fallback, source ranking, or caller override.

## Closed Defects

- `D-401 CLOSED`
- `D-401R CLOSED`
- `D-401R-01 CLOSED`
- `D-402 CLOSED`
- `D-403 CLOSED`
- `D-404 CLOSED`
- `D-405 CLOSED`
- `D-405R CLOSED`

## Accepted Follow-up Risk

`D-406` is `ACCEPTED_FOLLOW_UP`. Overlap detection remains service-level, and a concurrent activation race is not prevented by a database-native exclusion. Inconsistent overlapping active rows still resolve fail-closed as `ambiguous`; no ranking or fallback is permitted.

## Verification Evidence

| Verification | Result |
|---|---|
| Focused PKG-004A | `65 passed` |
| Full backend | `413 passed` |
| Migration | `9 passed` |
| PKG-001/002/003 regressions | `116 passed` |
| Relevant API | `82 passed` |
| Frontend | `80 passed` |
| Frontend production build | `passed` |
| Python compile | `passed` |
| Alembic | single head `a8e4f2c6d901` |
| Git diff check | `passed` |
| Skipped tests | `none` |

No migration was added after `a8e4f2c6d901`, and no parameter content seed or backfill was introduced.

## Known Limitations

| Limitation | Classification |
|---|---|
| No write HTTP API | accepted within PKG-004A |
| No production administrator authentication | follow-up package |
| No parameter content seed | accepted within PKG-004A |
| No automatic fixation integration | accepted within PKG-004A |
| No correction UI | follow-up package |
| Service-level lifecycle administration | accepted within PKG-004A |
| No database-native overlap exclusion | follow-up package |
| No application build identity | follow-up package |
| No M07/current resolver | follow-up package |
| Raw SQL/database-administrator bypass | accepted operational limitation |

These limitations do not authorize another implementation package.

## Explicit Exclusions

- parameter content seed;
- production administrator authentication;
- write API;
- UI;
- automatic fixation integration;
- M07 repository;
- eligibility resolution;
- future reserve;
- grant/capitalization authority;
- current dependency resolver;
- CBS;
- stale/professional lifecycle;
- correction UI or workflow;
- M08E;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- engine changes;
- V1/V2 parity;
- production-readiness claim.

## Closure Boundary

PKG-004A acceptance does not mean official parameter content has been populated, the fixation engine automatically selects parameters, full current dependency resolution exists, M08F is complete, M08 is complete, production readiness has been reached, formal 161D readiness has been reached, or V1/V2 parity has been established. The next package is not authorized by this record.
