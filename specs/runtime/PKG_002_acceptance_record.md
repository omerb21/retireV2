# PKG-002 Acceptance Record

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-002 - M08D CBS/Lamas Indexation Foundation` |
| Status | `ACCEPTED` |
| Base | `82f88d0` |
| Accepted implementation HEAD | `09bcd8a` |
| Migration head | `c2f8a4d1e706` |

## Accepted Commit Chain

1. `2b915a9 feat: add typed CBS indexation adapter`
2. `5084c5b feat: integrate CBS indexation admission evidence`
3. `9496364 feat: persist CBS calculation failure statuses`
4. `8dd76f3 test: prove PKG-002 CBS boundaries`
5. `b0257d9 fix: reject caller-forged CBS evidence`
6. `640c34d fix: normalize non-finite CBS responses`
7. `09bcd8a test: prove PKG-002 acceptance corrections`

## Accepted Scope

PKG-002 establishes the bounded M08D CBS/Lamas indexation foundation for admissible grant calculations. The system adapter uses CPI series `120010` and endpoint `https://api.cbs.gov.il/index/data/calculator/120010`. It maps the accepted positive grant amount to `value`, `grant_date` with recorded `work_end_date` fallback to `date`, and `eligibility_date` to `toDate`, using `yyyy-mm-dd`, `format=json`, `download=false`, and `lang=en`.

There is no authoritative fallback when required CBS calculation fails. A planner- or user-asserted indexed amount remains explicitly distinct from a system-calculated CBS result and is preserved only as asserted provenance. Successful CBS evidence, including request, response, CPI, endpoint, raw `answer.to_value`, rounded application amount, and calculation timestamp, is system-controlled. Caller-forged system evidence is rejected before grant inclusion branching and cannot persist as official-looking immutable evidence.

Typed failures persist as `calculation_failed` or `unsupported_calculation`, with safe failure evidence and without a successful result or success audit rows. Saved evidence is immutable and run retrieval remains client-isolated. Non-finite CBS values are malformed responses and do not trigger semantic retries. No live CBS request was performed as acceptance evidence.

The Acceptance Audit closed:

- `D-201 CLOSED`: caller-forged CBS evidence on an excluded grant;
- `D-202 CLOSED`: non-finite CBS result escaping typed failure;
- `D-203 CLOSED`: missing focused blocked-M07 no-call evidence.

## Verification Evidence

| Verification | Result |
|---|---|
| Focused PKG-002 | `34 passed` |
| Full backend | `282 passed` |
| Migration | `6 passed` |
| API/client-isolation targeted | `3 passed` |
| M08A/PKG-001 regressions | `4 passed` |
| Python compile | `passed` |
| Git diff check | `passed` |
| Alembic | single head `c2f8a4d1e706` |

## Explicit Exclusions

- UI;
- cache or standalone catalog;
- correction or supersession workflow;
- historical prior-use behavior;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- V1/V2 parity.

## Closure Boundary

PKG-002 acceptance is not production readiness, full M08D completion, full M08 completion, or a V1/V2 parity claim. The next package is not authorized by this record.
