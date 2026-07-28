# PKG-005 Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-005 — Fixation End-to-End Usable Slice` |
| Status | `ACCEPTED` |
| Accepted implementation HEAD | `1d8190bab4da1619c03b013f4f7b88bd53e18507` |
| Base | `35619682fbdb5f08eeea213aee017a5c251a8ff0` |
| Alembic head | `a9c4e7f2b615` |
| Definition | `specs/runtime/PKG_005_FINAL_PACKAGE_DEFINITION.md` |

## Accepted Product Outcome

The authenticated application workflow now allows a user to:

1. open an existing client;
2. enter the fixation workspace;
3. list finalized client-scoped B1 revisions;
4. explicitly select an exact revision;
5. enter an eligibility date through the accepted B1 lifecycle;
6. create and finalize a new B1 revision atomically;
7. resolve missing eligibility-date evidence;
8. resolve ambiguous dates through explicit candidate selection;
9. supply the existing M08B, M08C, and M08D input wrappers;
10. validate through the real backend;
11. calculate through the existing engine;
12. view normalized date and year, calculation outputs, effects, warnings, and
    audit information;
13. save a fixation run;
14. display the persisted save timestamp;
15. reopen the run;
16. view structured snapshot and resolver provenance.

PKG-005 is the first accepted end-to-end usable fixation product slice.

## B1 Workflow

- Finalized revision listing is client-scoped.
- Only exact revision IDs are selected.
- No latest-wins behavior, current marker, or hidden ranking exists.
- Eligibility-date creation uses the existing draft, assertion, fact-evidence,
  and finalization lifecycle.
- The creation and finalization operation is atomic.
- Rollback leaves no partial revision or evidence.
- No new evidence lifecycle or migration exists.
- No fallback to `retirement_timing` exists.
- No legal date derivation exists.

## Technical Actor

The accepted technical provenance actor is:

| Field | Value |
|---|---|
| Type | `system` |
| Code | `fixation-ui` |
| Label | `Fixation workflow` |
| Persisted representation | `system:fixation-ui:Fixation workflow` |

The actor is server-controlled and cannot be supplied or overridden by the
browser. It is operational provenance only. It is not authentication,
authorization, professional approval, or proof of the human who entered the
date.

## M07 Request Boundary

Every new validate, calculate, and save request uses:

`m07_input_reference.b1_evidence_revision_id`

Optional conflict selections are revision-bound.

The caller does not directly supply:

- `eligibility_date`;
- `eligibility_year`;
- `M07EntryContext`;
- qualification or review state;
- resolver outcome;
- fingerprint;
- normalized values;
- source references;
- manifest scope or version.

## Missing and Ambiguity Behavior

- `missing_inputs` is presented as an actionable missing-date workflow.
- Unresolved M07 stops before CBS and engine calls.
- The user can create a new eligibility-date revision and retry.
- `ambiguous_inputs` displays safe candidate dates.
- No candidate is selected automatically.
- Explicit selection is bound to the selected revision.
- Stale or foreign selections do not resolve.
- Selection evidence is preserved in the saved snapshot.

## M08 Boundary Preservation

### M08B

- The caller-supplied parameter-set wrapper remains.
- The UI supplies the complete accepted wrapper.
- Parameter tax year remains distinct from eligibility year.
- Effective dates, all four values, source and basis, status,
  accepted-for-use, and decision evidence are preserved.
- Official parameter-resolver integration did not occur.
- Fail-closed behavior remains.

### M08C

The accepted workflow preserves:

- collection states;
- grants;
- capitalizations;
- inclusion;
- conflicts;
- accepted values;
- provenance;
- support;
- accepted-for-use;
- future grant reservation.

### M08D

The accepted workflow preserves:

- explicit indexation mode;
- the asserted/system distinction;
- server-controlled CBS evidence;
- typed failures;
- no fallback;
- no CBS call before M07 resolution.

## Result, Save, and Reopen

The UI visibly presents:

- normalized eligibility date;
- eligibility year;
- selected B1 revision;
- explicit selection when used;
- resolver scope, version, outcome, and fingerprint;
- source references;
- parameter-set identity and tax year;
- effective dates;
- all four calculation values;
- source and basis;
- status;
- accepted-for-use;
- decision actor and timestamp;
- grant and capitalization effects;
- warnings;
- audit evidence;
- run ID;
- persisted save date and time.

Reopened data is loaded from persisted backend state and remains visible after
direct URL load or refresh. Raw JSON remains supporting evidence only and is
not the sole product presentation.

## Frontend Client-Context Isolation

PKG-005 establishes:

- state reset on route-client transition;
- client-bound selected revision, candidates, validation, result, and save
  state;
- no display of stale client-A data under client B;
- a monotonic route-context generation token that distinguishes an old
  client-A visit from a new client-A visit;
- capture of client ID and generation by every protected asynchronous
  operation;
- state updates from success, error, and `finally` branches only while both
  client ID and generation remain current;
- rejection of stale A-to-B-to-A responses;
- continued operation of new requests in the revisited client context.

Protected paths include:

- grants loading;
- capitalization loading;
- revision loading;
- eligibility-date revision creation;
- validation;
- ambiguity retry;
- calculation;
- result, history, and run-detail loading;
- save;
- loading, error, and submission state.

## Four Acceptance Scenarios

### Scenario 1 — Successful Workflow

`PASS`

- Create or select a revision.
- Validate.
- Calculate.
- Display the result.
- Save.
- Display the persisted timestamp.
- Reopen.
- Display structured provenance and inputs.

### Scenario 2 — Missing Date

`PASS`

- Missing input is shown.
- No CBS or engine invocation occurs.
- The date is added through B1.
- The exact returned revision is selected.
- Retry succeeds.

### Scenario 3 — Ambiguous Date

`PASS`

- Safe candidates are shown.
- An explicit selection is made.
- Retry succeeds.
- Selection is saved and visible after reopen.

### Scenario 4 — Preserved M08 Blocker

`PASS`

- M07 resolves.
- The existing M08 blocker remains effective.
- The correct failure is shown.
- No gate bypass occurs.

## Explicitly Absent

PKG-005 does not introduce:

- a migration;
- a database model or table;
- a new B1 lifecycle;
- a current-revision marker;
- a broad evidence editor;
- a broad authentication system;
- a formula or engine change;
- a dependency-manifest semantic change;
- official parameter-resolver integration;
- M08 gate weakening;
- browser-generated CBS system evidence;
- hidden source ranking;
- frontend-only fake persistence;
- formal 161D;
- full M08F;
- M09-M14;
- 02M;
- production deployment;
- a V1/V2 parity claim.

## Acceptance Evidence

The initial product audit result was:

`RETURN_TO_CODEX_FOR_CORRECTION`

The audit identified:

- D-005-001 — frontend client-transition isolation;
- D-005-002 — saved date missing;
- D-005-003 — incomplete structured parameter presentation.

Correction status:

| Defect or correction | Status |
|---|---|
| D-005-002 | `FIXED` |
| D-005-003 | `FIXED` |
| D-005-001 initial correction | `PARTIALLY_FIXED` |
| Final A-to-B-to-A correction | `FIXED` |

The final audit result was:

`POINT_REAUDIT_PASSED_ACCEPT_PKG_005`

| Audit area | Result |
|---|---|
| Repository safety | `PASS` |
| Generation uniqueness | `PASS` |
| Validation A-to-B-to-A | `PASS` |
| Save A-to-B-to-A | `PASS` |
| Load A-to-B-to-A | `PASS` |
| Stale error and `finally` protection | `PASS` |
| New A requests still work | `PASS` |
| Prior corrections preserved | `PASS` |
| Scope preservation | `PASS` |
| Remaining defects | `none` |

## Test Evidence

### Backend

| Verification | Result |
|---|---|
| Focused PKG-005 backend | `8 passed` |
| Full backend | `563 passed` |
| PKG-004D regressions | `PASS` |
| M08, CBS, and engine regressions | `PASS` |
| Python compile | `PASS` |
| Alembic | one head `a9c4e7f2b615` |

### Frontend

| Verification | Result |
|---|---|
| Initial focused | `12 passed` |
| First correction focused | `20 passed` |
| Final focused | `23 passed` |
| Initial full frontend | `76 passed` |
| First correction full frontend | `79 passed` |
| Final full frontend | `82 passed` |
| Production build and type-check | `PASS` |
| Final build | `54 modules built` |

### Technical

| Verification | Result |
|---|---|
| `git diff --check` | `PASS` |

Browser E2E infrastructure was unavailable. Acceptance relied on the strongest
available frontend component and integration harness combined with real
FastAPI route, service, persistence, and full-suite tests. No manual browser
demonstration is claimed.

## Accepted Limitations

- No browser E2E framework exists yet.
- The official M08B parameter resolver remains separate.
- No full client report exists.
- No formal Form 161D exists.
- No automatic legal eligibility-date derivation exists.
- No broad authentication identity exists.
- No production deployment occurred.
- No production-readiness claim is made.
- No full M08 completion claim is made.
- No V1/V2 parity claim is made.

## Follow-Up Boundary

- PKG-005 acceptance confirms that the bounded fixation workflow is usable
  through the current UI and backend.
- Broader retirement-planning workflows remain separate.
- Future work must be planned by product milestone rather than micro-package
  by default.
- PKG-005 acceptance does not authorize another package.
- The next package remains `NOT_AUTHORIZED`.
