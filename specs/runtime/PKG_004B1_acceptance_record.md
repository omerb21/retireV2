# PKG-004B1 Acceptance Record

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-004B1 - M07 Source Profile and Assessment Evidence Foundation` |
| Status | `ACCEPTED` |
| Base | `725676f21306f13ce668c8b014cbd157bd9d960c` |
| Accepted implementation HEAD | `b9e3860eab8948249a27396f06703aca99df1743` |
| Accepted Alembic head | `a9c4e7f2b615` |

The accepted migration chain is:

1. `b4e7c1d8f203`
2. `e6f1a9c3b702`
3. `a9c4e7f2b615`

## Accepted Technical Scope

PKG-004B1 provides:

- client-scoped M07 evidence revisions;
- fact evidence with provenance and verification;
- planner assertions stored separately;
- missing, unresolved, conflict, and warning findings;
- deterministic technical assessment;
- a server-owned required-evidence manifest;
- a canonical readable payload;
- deterministic SHA-256 fingerprints;
- the `draft`, `finalized`, `superseded`, and `abandoned` lifecycle;
- immutable finalized evidence;
- successor revisions and atomic supersession;
- client-isolated reference validation;
- server-controlled evidence actors;
- exactly one evidence basis per fact;
- deterministic non-null fact identity;
- migration preflight and duplicate rejection;
- PostgreSQL offline migration SQL support;
- parameter-set references without parameter duplication.

## Authority Boundary

The explicit authority classification is:

`EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`

PKG-004B1 does not create:

- `qualified`;
- `warning_reviewed`;
- professional qualification;
- warning acceptance;
- `accepted_for_use`;
- current M07 authority;
- a current-authority selector;
- an eligibility conclusion;
- a professional stale lifecycle.

## Acceptance Evidence

The acceptance review proceeded through these checkpoints:

1. The initial implementation audit at `8e5117e` returned the package for correction.
2. The focused correction audit at `be340b4` identified three remaining issues.
3. The final focused recheck at `3b2c80b` identified migration defects F-401 through F-403.
4. The migration-only micro-recheck at `b9e3860e` verified:
   - F-401 `FIXED`;
   - F-402 `FIXED`;
   - F-403 `FIXED`;
   - no new defects.

Final migration-only micro-recheck evidence:

| Verification | Result |
|---|---|
| Migration-focused tests | `17 passed` |
| Focused PKG-004B1 tests | `47 passed` |
| Migration safety | `9 passed` |
| PostgreSQL offline upgrade | `PASS` |
| PostgreSQL offline downgrade | `PASS` |
| SQLite upgrade/downgrade | `PASS` |
| Alembic | single head `PASS` |
| Git diff check | `PASS` |

Prior full regression evidence from the accepted implementation sequence:

| Verification | Result |
|---|---|
| Full backend | `477 passed` |
| PKG-001/002/003/004A regressions | `181 passed` |
| API regressions | `70 passed` |
| Frontend | `80 passed` |
| Frontend production build | `PASS` |
| Python compile | `PASS` |

The final micro-recheck was migration-only and did not rerun unrelated suites,
because its correction changed only the replacement migration and
migration-focused tests. The prior full regression results remain the
acceptance evidence for those unrelated suites.

## Accepted Package Limitations

The following are accepted package boundaries, not acceptance defects:

- no production administrative authentication;
- service actors are administrative context, not proven professional identities;
- raw SQL or database-administrator bypass remains an operational limitation;
- no HTTP API;
- no UI;
- no authoritative retirement-date resolver;
- no authoritative pension-commencement resolver;
- no qualification;
- no warning review;
- no `accepted_for_use`;
- no current selector;
- no fixation integration;
- no historical backfill;
- mutable upstream source records do not mutate finalized canonical evidence.

## Exclusions Preserved

PKG-004B1 makes no change to:

- `M07EntryContext`;
- fixation admission;
- the fixation engine;
- CBS;
- M08E;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- PKG-004B2.

## Follow-up Boundary

- PKG-004B2 remains outside scope.
- Professional decisions regarding qualification, warning review,
  `accepted_for_use`, and current authority remain unresolved.
- No next package is authorized by this acceptance record.
