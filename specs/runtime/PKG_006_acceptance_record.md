# PKG-006 Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-006 — M01 Client Case Foundation` |
| Status | `ACCEPTED` |
| Accepted implementation HEAD | `9ae1d2d42e9d02b5dc97b6be26dbe2410aa9b11a` |
| Base | `6b076a1f4ef731fb388aff22f707e714d5d53241` |
| Definition | `specs/runtime/PKG_006_FINAL_PACKAGE_DEFINITION.md` |
| Migration | `f3a7c9d2e610` |
| Migration parent | `a9c4e7f2b615` |
| Module | `M01` |

## Accepted Implementation Chain

1. `9793ebf0913614ce0aaa0b0720172262f33e8bf2` —
   `feat: add M01 client case backend`
2. `edd722076e26e5cce9796162ff7ed2a040375598` —
   `feat: implement M01 client case workspace`
3. `c16c3596e47aedaaf9b36694c30b9f089d21af5f` —
   `fix: preserve M01 fact invariants across client updates`
4. `9ae1d2d42e9d02b5dc97b6be26dbe2410aa9b11a` —
   `fix: isolate M01 workspace state across client contexts`

## Accepted Product Outcome

The system now allows a user to:

1. open an existing client case;
2. view client identity, lifecycle, and completeness;
3. edit authoritative minimum facts;
4. view missing and conflicting diagnostics;
5. enter employment status from the closed vocabulary;
6. enter exactly one planned retirement age or date;
7. move between allowed lifecycle states;
8. receive structured blocking for a prohibited transition;
9. use an archived case in read-only mode;
10. explicitly reopen an archived case to `delivered`;
11. navigate to employment history and fixation;
12. move A-to-B and A-to-B-to-A without client-state leakage;
13. continue using PKG-005 without regression.

M01 completeness and lifecycle are case-management facts only. They are not
professional, legal, tax, retirement, or calculation determinations.

## Persistence and Migration

PKG-006 adds only these three Client fields:

- `employment_status`;
- `planned_retirement_date`;
- `planned_retirement_age`.

All three fields are nullable. There is no backfill, inference, deletion, or
rewrite of historical data. The single Alembic head is `f3a7c9d2e610`.
Existing clients remain incomplete until facts are entered explicitly.

## Employment Status

The closed vocabulary is exactly:

- `salaried_employee`;
- `self_employed`;
- `salaried_and_self_employed`;
- `not_currently_working`;
- `unknown`.

`NULL` and `unknown` do not satisfy completeness. Free text is rejected. No
value is inferred from employment history, employer records, or M07. The field
has no side effect on employer records, retirement, eligibility, tax, or
fixation.

## Planned Retirement

The accepted fields are:

- `planned_retirement_date`;
- `planned_retirement_age`.

Exactly one is required for completeness. Supplying both is a conflict. Age is
technically constrained to `18–120`. A planned retirement date must be later
than the birth date. There is no conversion, precedence, latest-wins behavior,
or inference. Neither field is used as an M07 or M08 eligibility input.

## Completeness

The backend is the sole authority for M01 completeness.

The completeness field set is:

- `display_name`;
- `id_number`;
- `birth_date`;
- `gender`;
- `employment_status`;
- `planned_retirement`.

There is no persisted `is_complete` field, and the frontend does not determine
completeness. Missing and conflicting field IDs are returned by the backend.
Invalid persisted facts fail closed. Forward lifecycle targets are blocked
when the case is incomplete or conflicting. Contact, household, pension, tax,
and fixation data are outside M01 completeness.

## Lifecycle

The lifecycle states are:

- `draft`;
- `intake`;
- `analysis`;
- `review`;
- `delivered`;
- `archived`.

The only allowed transitions are:

1. `draft -> intake`;
2. `intake -> draft`;
3. `intake -> analysis`;
4. `analysis -> intake`;
5. `analysis -> review`;
6. `review -> analysis`;
7. `review -> delivered`;
8. `delivered -> review`;
9. `delivered -> archived`;
10. `archived -> delivered`.

Stored `NULL` and legacy `active` are read as effective `draft`, without
read-time backfill. Unknown noncanonical status fails closed. Same-state and
skipped transitions are prohibited. Forward movement requires completeness.
An already advanced incomplete case is not automatically moved backward.
Archived cases are read-only, and the only reopen transition is
`archived -> delivered`. Calculations do not change lifecycle.

## Client Isolation and Async Safety

The accepted frontend boundary includes:

- authoritative route client ID;
- monotonic route-context generation;
- full reset of all client-owned state;
- render ownership tied to the current client context;
- current-context checks for success, rejection, and `finally`;
- A-to-B protection;
- A-to-B-to-A protection;
- rejection of stale reads, mutations, errors, loading state, and saving state;
- successful operation of a new A request after an old A request settles.

## Acceptance Defects and Corrections

The initial audit result was:

`RETURN_TO_CODEX_FOR_CORRECTION`

| Defect | Description | Final status |
|---|---|---|
| D-006-001 | Birth-date and planned-retirement invariant | `FIXED` |
| D-006-002 | Incomplete client-context state reset | `FIXED` |
| D-006-003 | Archived UI not fully read-only | `FIXED` |

The final focused audit result was:

`FOCUSED_REAUDIT_PASSED_ACCEPT_PKG_006`

## Test Evidence

### Backend

| Verification | Result |
|---|---|
| PKG-006 focused | `35 passed` |
| Focused profile/API/isolation and PKG-005 | `49 passed` |
| Full backend | `598 passed` |
| Python compile | `76 Python files` |
| Alembic | one head `f3a7c9d2e610` |

### Frontend

| Verification | Result |
|---|---|
| M01/client-detail focused | `16 passed` |
| PKG-005 focused | `28 passed` |
| Full frontend | `92 passed` |
| Production build/type-check | `PASS` |
| Build | `54 modules built` |

### Repository

| Verification | Result |
|---|---|
| `git diff --check` | `PASS` |

No browser E2E execution is claimed.

## Accepted Limitations

- Single application user.
- Single case owner.
- No household model.
- No team or broad authorization.
- No M02 workflow.
- No Israeli-ID checksum validation.
- No formal 161D.
- No M09–M14.
- No production deployment.
- No production-readiness claim.
- No V1/V2 parity claim.

## Follow-Up Boundary

- PKG-006 establishes the usable M01 client-case foundation.
- PKG-006 acceptance does not authorize M02.
- PKG-006 acceptance does not authorize another package.
- The next package remains `NOT_AUTHORIZED`.
