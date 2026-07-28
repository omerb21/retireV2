# PKG-006 — M01 Client Case Foundation

## 1. Definition status

| Item | Value |
|---|---|
| Package | `PKG-006 - M01 Client Case Foundation` |
| Module | `M01` |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Product outcome | Client case foundation, derived minimum completeness, lifecycle, client isolation, and stable navigation |
| Migration | `ADDITIVE_MIGRATION_REQUIRED` |
| Implementation | `NOT_AUTHORIZED` |
| Base definition HEAD | `3ba3c45fd31b51e88157b174928dca2405cc756d` |
| Next package | `NOT_AUTHORIZED` |

This document defines one M01 product package. It does not authorize
implementation or migration execution, does not open M02 or another module,
does not change an accepted professional rule or calculation, and does not
claim production readiness or V1/V2 parity.

## 2. Authority and package boundary

The authoritative source is
`specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`. In its locked
`## 5. Build Sequence`, the first step is:

> **Case foundation: M01.** Stabilize client scope, authoritative facts,
> completeness, ownership, and navigation. Every later record must be
> client-bound.

PKG-006 implements that M01 step only. The first-stage ownership model remains
one application user and one case owner. Teams, role hierarchies, household
ownership, and broad authentication or authorization are outside this package.

The package does not implement an M02 intake workflow. It defines the M01 gate
that permits a complete case to enter the existing `intake` lifecycle state and
provides navigation only to screens that already exist.

## 3. Current-state mapping

| Area | Classification | Repository finding and PKG-006 treatment |
|---|---|---|
| Client identity model | Reusable with bounded change | `Client` already stores `display_name`, unique `id_number`, and `birth_date`. These remain the authoritative M01 identity facts. |
| Client profile | Reusable with bounded change | `ClientProfile` already stores `gender` and optional contact data. Gender participates in M01 completeness; contact data does not. The duplicate profile `birth_date` must not become a competing authority: the existing client API behavior that synchronizes the authoritative client birth date is preserved. |
| Client lifecycle field | Reusable with bounded change | `Client.status` exists as nullable `String(50)`, is not used by production behavior, and is not exposed by the current client API. It becomes the M01 lifecycle field under the compatibility rules in section 7. |
| Client creation API | Reusable with bounded change | Creation currently accepts name, identifier, and optional birth date, and writes `status=None`. It may continue creating an incomplete draft; the response and duplicate-identifier behavior need the M01 contract. |
| Client detail/profile API | Reusable with bounded change | Existing client-scoped get/profile operations provide identity and profile facts. They need bounded M01 edit, overview, completeness, and lifecycle response behavior. |
| Client service/repository | Missing and required | Client routes currently perform direct session work and have no dedicated M01 case service. A bounded backend case-domain operation is required for normalization, completeness, lifecycle validation, and atomic mutation; a broad repository refactor is not required. |
| Current file/completeness status | Conflicting with locked M01 | `file_status="file_created"` is hard-coded, and `professional_identification_status` uses contact information while omitting several locked M01 facts. Neither is M01 completeness authority. Compatibility fields may remain, but they must not control M01 status or intake eligibility. |
| Employment history | Reusable as-is but excluded from authority | `EmploymentRecord` stores employer dates and `is_current`. It remains available and client-scoped, but it must not infer or overwrite M01 `employment_status`. |
| M01 employment status | Missing and required | No explicit client-level field exists. M07 generic evidence and employment-history records have different contracts and cannot be reused as the M01 authority. |
| Retirement timing facts | Reusable as-is but excluded from authority | Existing timing records contain work-end, pension-start, anticipated-work-end, and other labelled dates. They retain their existing meanings and do not satisfy M01 completeness automatically. |
| M07/M08 eligibility evidence | Reusable as-is but excluded from authority | `eligibility_date` and its evidence lifecycle remain separate calculation inputs. They must not populate or imply the M01 planned-retirement fields. |
| M01 planned retirement | Missing and required | No explicit client-level planned-retirement age/date pair exists. Two nullable, mutually exclusive client fields are required. |
| Completeness calculation | Missing and required | No backend-derived M01 completeness result or stable missing/conflicting-field diagnostics exist. |
| Client list/create screens | Reusable with bounded change | Existing list and create navigation can be retained. A newly created partial client remains a draft and proceeds to the case screen for completion. |
| Client detail/workspace screen | Reusable with bounded change | The existing client detail screen is the central case entry and already links to fixation and employment history. It needs a clear case header, minimum-facts editor, completeness diagnostics, lifecycle controls, and stable module navigation. |
| Routes and navigation | Reusable with bounded change | Existing client-scoped detail, employment-history, fixation workspace/input/history, and run routes are retained. Missing module screens are shown as unavailable rather than implemented in PKG-006. |
| Client isolation | Reusable with required strengthening | Existing APIs and fixation routes commonly scope records by `client_id`. M01 overview, facts, completeness, lifecycle, frontend state, and every link must apply the same boundary, including foreign nested IDs and stale responses. |
| PKG-005 workflow | Reusable as-is and regression-protected | The accepted fixation entry, calculation, save, history, and reopen workflow remains reachable with its accepted client isolation and stale-response protections. No fixation request or calculation contract changes. |
| Existing migrations | Reusable chain; additive head required later | Current Alembic has one head, `a9c4e7f2b615`. Future implementation requires one additive successor for the three fields in section 5; no migration is executed by this definition. |
| Existing tests | Reusable with bounded additions | Client API, profile, client-isolation, detail-screen, navigation, async fixation, and PKG-005 regression tests provide a base. Focused M01 service/API/UI/migration coverage is missing. |

## 4. Product outcome

After a separately authorized implementation, a user can:

1. open an existing client case;
2. see a clear case title, authoritative minimum facts, lifecycle state, and
   completeness state;
3. edit the M01 minimum facts through the real backend;
4. see exactly which minimum facts are missing or conflicting;
5. advance or return the case through an allowed lifecycle transition;
6. receive a structured, visible rejection for an invalid transition;
7. navigate in the active client context to existing employment-history,
   fixation, calculation, and history screens;
8. return to the same client case without losing context;
9. move between client A, client B, and client A again without stale or retained
   data crossing client boundaries; and
10. continue using the accepted PKG-005 fixation workflow without regression.

Completeness and lifecycle are navigation and case-management facts only. They
do not calculate retirement, eligibility, tax, fixation, benefits, grants,
pension commencement, or employment termination, and they do not constitute
professional approval.

## 5. Persistence and additive migration contract

Future implementation requires `ADDITIVE_MIGRATION_REQUIRED`. The authorized
definition boundary permits adding only these nullable columns to `clients`:

| Field | Persistence type | Initial value for existing clients |
|---|---|---|
| `employment_status` | bounded string vocabulary | `NULL` |
| `planned_retirement_date` | date | `NULL` |
| `planned_retirement_age` | integer | `NULL` |

The migration must be a single successor to the then-current Alembic head and
must preserve a single-head chain. It may add database checks that express only
the locked vocabulary, age range, and mutual-exclusion contract, provided the
checks accept the existing `NULL` state.

No existing client receives an inferred backfill. In particular:

- employment status is not copied from employer records, employment history, or
  M07 evidence;
- planned retirement is not copied or derived from work-end, pension-start,
  eligibility, retirement-timing, M07, or M08 data;
- no historical row is deleted, rewritten, or reinterpreted as professional
  evidence; and
- existing clients remain incomplete until the missing M01 facts are entered
  explicitly.

`Client.status` is reused rather than adding a competing lifecycle column. Its
bounded compatibility behavior is specified in section 7. If implementation
finds data or behavior that makes that reuse unsafe without a destructive
migration or a material meaning change, it must stop with
`CLIENT_STATUS_MIGRATION_DECISION_REQUIRED`.

## 6. Authoritative minimum-fact contracts

### 6.1 Name

- Authority: `Client.display_name`.
- Normalize by trimming surrounding whitespace.
- An empty or whitespace-only value is invalid and missing for completeness.
- Editing the M01 case may update the name; it must not create another name
  authority.

### 6.2 Israeli ID or client identifier

- Authority: `Client.id_number`.
- Treat the value as an opaque string and preserve leading zeros.
- Normalize by trimming surrounding whitespace; do not convert to a number.
- Empty or whitespace-only input is invalid and missing.
- The existing uniqueness boundary remains authoritative.
- A duplicate normalized identifier must produce a stable client-facing
  conflict response, with no partial write and no disclosure of the other
  client's case data.
- PKG-006 does not introduce an Israeli-ID legal-validity or checksum rule
  because the field also permits a client identifier.

### 6.3 Birth date

- Authority: `Client.birth_date`.
- Accept a valid ISO calendar date through the API.
- `NULL` is missing.
- A future date is invalid.
- `ClientProfile.birth_date` must not become an independently selectable or
  latest-wins value; existing API synchronization behavior is preserved.

### 6.4 Gender

- Authority: `ClientProfile.gender`.
- Preserve the repository's existing accepted values and presentation rather
  than inventing a new gender taxonomy in PKG-006.
- Normalize surrounding whitespace.
- `NULL`, empty, or whitespace-only values are missing.
- Gender is used only for M01 completeness in this package and causes no
  calculation side effect.

### 6.5 Employment status

Authority is the new explicit client-level `Client.employment_status`.

The complete vocabulary is:

- `salaried_employee`;
- `self_employed`;
- `salaried_and_self_employed`;
- `not_currently_working`; and
- `unknown`.

Only these exact canonical values or `NULL` are accepted. Free text is rejected.
`NULL` and `unknown` are incomplete. The other four values satisfy only the M01
employment-status completeness fact.

The value is never inferred from `EmploymentRecord`, employment history, income,
or M07 evidence. It does not determine retirement, eligibility, work
termination, pension receipt, grants, fixation, or tax meaning, and editing it
does not modify any employer record.

### 6.6 Planned retirement authority

M01 has two explicit, nullable, mutually exclusive client-level fields:

- `Client.planned_retirement_date`; and
- `Client.planned_retirement_age`.

Exactly one must be present for completeness. The API must reject a mutation
that supplies both; it must not silently choose one, clear one, or apply
latest-wins. Clearing the currently stored choice and setting the alternative
may be performed in one atomic request.

`planned_retirement_age` must be an integer from `18` through `120`, inclusive.
This is a bounded technical human-range validation, not a legal eligibility
age, professional default, or recommendation.

`planned_retirement_date` must be a valid ISO calendar date and must be later
than the recorded birth date. It may be in the past or future; PKG-006 does not
infer whether retirement occurred.

The user explicitly enters or confirms the selected M01 planning fact. The
backend never derives age from date, date from age, or either value from:

- employment end date;
- pension start date;
- eligibility date;
- retirement-timing facts;
- M07/M08 evidence; or
- a legal or professional default.

M01 planned-retirement fields have no side effect on M07, M08, fixation, or
another calculation.

## 7. Lifecycle contract

The canonical persisted states in `Client.status` are:

- `draft`;
- `intake`;
- `analysis`;
- `review`;
- `delivered`; and
- `archived`.

### 7.1 Compatibility for existing data

Current production behavior does not use `Client.status`, current client
creation writes `NULL`, and historical fixtures may contain the placeholder
`active`. To preserve rows without a backfill:

- stored `NULL` is read as effective `draft`;
- stored legacy `active` is read as effective `draft`;
- neither compatibility value is rewritten merely by reading or editing facts;
- the first explicit lifecycle transition from effective `draft` to `intake`
  persists canonical `intake`;
- a later explicit backward transition to draft persists canonical `draft`; and
- any other non-canonical stored value fails closed as
  `unsupported_client_status`; it is not silently mapped or overwritten.

This compatibility rule is operational case-state normalization only. It does
not reinterpret historical `active` as professional approval or evidence.

### 7.2 Transition table

| Current state | Allowed target | Direction | Additional gate |
|---|---|---|---|
| `draft` | `intake` | Forward | Case must be complete and conflict-free |
| `intake` | `analysis` | Forward | Case must be complete and conflict-free |
| `intake` | `draft` | Backward | None |
| `analysis` | `review` | Forward | Case must be complete and conflict-free |
| `analysis` | `intake` | Backward | None |
| `review` | `delivered` | Forward | Case must be complete and conflict-free |
| `review` | `analysis` | Backward | None |
| `delivered` | `archived` | Forward | Case must be complete and conflict-free |
| `delivered` | `review` | Backward | None |
| `archived` | `delivered` | Explicit reopen | None |

Every transition not listed is blocked. State skipping and same-state
transition requests are invalid. A calculation or data edit never changes the
lifecycle automatically.

If a case in `intake`, `analysis`, `review`, or `delivered` later becomes
incomplete, its status is not changed automatically. It may remain in its
current state or move through an allowed backward transition, but it cannot
make a forward transition while incomplete or conflicting.

An archived case is read-only for normal M01 fact and lifecycle work. Its only
permitted lifecycle mutation is the explicit `archived -> delivered` reopen.
PKG-006 does not change the persistence or professional meaning of existing
M07/M08 records belonging to an archived client.

### 7.3 Transition operation and rejection

The backend receives a client-scoped target state, loads the current client,
derives completeness in the same transaction, validates the exact transition,
and persists only a successful transition. It returns the resulting state,
completeness, allowed targets, and update timestamp.

A rejected transition leaves all facts and status unchanged and returns a
structured reason, including as applicable:

- `invalid_lifecycle_transition`;
- `case_incomplete`;
- `case_has_conflicting_fields`;
- `archived_case_read_only`;
- `unsupported_client_status`; or
- `client_not_found`.

For incomplete/conflicting rejection, the response includes the same safe field
identifiers defined by the completeness contract. It does not expose another
client's existence or data.

## 8. Derived completeness contract

The backend is the sole completeness authority. Completeness is derived on
read and after relevant mutation; no persisted `is_complete` flag is added and
no frontend-authored completeness value is trusted.

The stable field identifiers are:

- `display_name`;
- `id_number`;
- `birth_date`;
- `gender`;
- `employment_status`; and
- `planned_retirement`.

The result shape contains at least:

- `status`: `complete` or `incomplete`;
- `missing_field_ids`: stable identifiers in the order above;
- `conflicting_field_ids`: stable concrete field identifiers;
- `allowed_lifecycle_targets`: targets permitted from the effective current
  state after applying completeness and archived behavior; and
- when a requested transition is rejected, a structured rejection reason.

Derivation rules:

1. normalized non-empty `display_name` is present;
2. normalized non-empty `id_number` is present;
3. valid non-null `birth_date` is present;
4. normalized non-empty `gender` is present;
5. `employment_status` is one of the four completeness-satisfying values and
   is neither `NULL` nor `unknown`; and
6. exactly one planned-retirement field is valid and present.

If both planned-retirement fields are absent, `planned_retirement` appears in
`missing_field_ids`. If both are present,
`planned_retirement_age` and `planned_retirement_date` appear in
`conflicting_field_ids`, completeness is `incomplete`, and no hidden precedence
is applied.

Address, telephone, email, contact method, spouse, dependants, household facts,
tax facts, fixation facts, pension facts, employment history, grants, and
actual capitalizations do not participate in M01 minimum completeness.

## 9. Required backend changes

A separately authorized implementation is expected to make only bounded M01
changes:

1. add the three nullable `Client` columns and their schema/domain validation;
2. reuse `Client.status` under the lifecycle and compatibility contract;
3. add a small M01 case-domain operation for normalization, derived
   completeness, allowed transitions, and atomic transition validation;
4. expose the M01 facts, effective lifecycle state, completeness diagnostics,
   and allowed targets through client-scoped response schemas;
5. expose an atomic M01 minimum-facts update that can safely switch between
   planned age and date and rejects conflicting input;
6. expose an explicit target-state lifecycle transition operation;
7. return stable validation and duplicate-identifier errors rather than
   leaking database exceptions;
8. keep all queries and mutations scoped to the route client ID and validate
   any nested record/run ID against that same client;
9. retain existing client/profile fact behavior and PKG-005 endpoints without
   changing calculations, M07/M08 evidence, or saved runs; and
10. produce the one bounded additive Alembic successor only after separate
    implementation authorization.

Route and schema names may follow the existing repository convention. The
semantics in this definition are fixed. A broad service/repository rewrite is
not required or authorized.

## 10. Required frontend behavior

A separately authorized implementation is expected to:

1. retain the existing client list/create/detail route structure;
2. make the client detail screen the clear M01 case overview;
3. display the client name, identifier, effective lifecycle status,
   completeness status, missing facts, and conflicts;
4. provide typed controls for all minimum facts, including the exact employment
   vocabulary and a mutually exclusive planned-age/planned-date choice;
5. send facts to the backend and render backend validation without computing an
   independent authoritative completeness result;
6. display only backend-returned lifecycle targets and send an explicit target
   transition request;
7. show structured transition rejections and missing/conflicting fields;
8. render archived cases as read-only with an explicit reopen action;
9. preserve existing client-scoped links to employment history and the PKG-005
   fixation workspace/input/history/run screens;
10. show unavailable future-module destinations as unavailable without
    implementing M02 or another module; and
11. retain a clear return link to the active client case from existing
    client-scoped screens where that navigation already exists or is directly
    touched by this package.

The package does not authorize a broad visual redesign, design system, or
unrelated screen refactor.

## 11. Client isolation and stale-response protection

Every M01 API, query, mutation, completeness result, lifecycle state, frontend
state object, and navigation link is bound to one route client ID.

The implementation must:

- reject a foreign client ID or a nested record/run belonging to another client
  without returning the foreign record's facts;
- clear client-specific case state immediately when the route client changes;
- increment a monotonic route-context generation whenever the route client
  context changes and capture both `clientId` and that generation for every
  asynchronous read or mutation;
- abort in-flight reads where practical and, regardless of abort support,
  discard every success, rejection, and `finally` effect unless both its
  captured `clientId` and generation match the current case;
- apply the same generation check to reads, saves, validation failures, and
  lifecycle mutation responses;
- prevent a stale `finally` from clearing or modifying the current context's
  loading or mutation-in-progress state;
- prevent a stale success or rejection from overwriting current facts, mutation
  results, errors, completeness, lifecycle targets, validation messages,
  navigation, or client-workspace state;
- avoid retaining missing fields, conflicts, form drafts, transition choices,
  errors, or loading state from the previous client; and
- construct all module links from the active route client, not from stale route
  state or a previously loaded record.

Tests must use deferred or otherwise deterministically controlled promises;
timing-only tests are insufficient. They must exercise both A→B and A→B→A with
deliberately reordered outcomes and prove at least:

1. a stale successful read cannot overwrite the current client's data;
2. a stale rejected read cannot display its old error;
3. a stale read `finally` cannot clear or modify the current loading state;
4. a stale successful mutation cannot change current mutation status, overwrite
   a newer mutation result, or restore stale completeness, lifecycle targets,
   validation messages, navigation, or workspace state;
5. a stale rejected mutation cannot display its error or change current
   mutation status;
6. a stale mutation `finally` cannot clear or modify the current mutation state;
   and
7. a new request in the revisited A context still succeeds normally after the
   first A context's stale outcomes settle.

Each acceptance check must validate both the captured `clientId` and the
monotonic route-context generation. A `clientId`-only guard is explicitly
insufficient for A→B→A. This strengthens the deterministic test contract for
the accepted generation-token design; it does not introduce another
concurrency architecture.

## 12. Navigation and PKG-005 preservation

The M01 case screen provides stable, client-scoped navigation to existing
destinations, including employment history and the fixation workflow. Existing
calculation and saved-history/run destinations remain reachable through the
accepted PKG-005 flow.

PKG-006 must not:

- alter direct eligibility admission or M07 resolution;
- change an M08 parameter, grant, indexation, calculation, or save contract;
- modify the accepted server technical actor;
- alter saved-run snapshots or immutability;
- use M01 planned retirement as a fixation eligibility input; or
- require M01 completeness merely to preserve already accepted PKG-005
  behavior unless a later product decision explicitly authorizes that gate.

## 13. Acceptance criteria

### Product-visible and executable behavior

- **AC-006-001:** A user can open an existing client and see a single clear case
  header containing the correct client identity, effective lifecycle state,
  and backend-derived completeness state.
- **AC-006-002:** The case screen displays every locked minimum fact and
  identifies each missing field using the stable backend identifiers.
- **AC-006-003:** The user can edit and persist name, identifier, birth date,
  gender, employment status, and exactly one planned-retirement value through
  the real client-scoped backend.
- **AC-006-004:** The employment control accepts only the five canonical values;
  `NULL` and `unknown` remain visibly incomplete and no employment history is
  changed.
- **AC-006-005:** The user can choose either planned retirement age or planned
  retirement date, switch atomically between them, and cannot persist both.
- **AC-006-006:** A complete draft can transition to `intake`; an incomplete or
  conflicting draft sees an actionable rejection naming the blocking fields.
- **AC-006-007:** Every listed forward, backward, archive, and reopen transition
  is available only from its defined source state, and a successful change is
  persisted and visible after reload.
- **AC-006-008:** An invalid, skipped, or same-state transition is rejected
  visibly and leaves the case unchanged.
- **AC-006-009:** A progressed case that later becomes incomplete retains its
  current status, cannot move forward, and may move backward according to the
  transition table.
- **AC-006-010:** An archived case is read-only for normal M01 work and can only
  be reopened through the explicit `archived -> delivered` action.
- **AC-006-011:** The user can navigate from the case to existing
  client-scoped employment-history and fixation destinations and return without
  losing or changing client context.
- **AC-006-012:** Switching A→B and A→B→A with reordered asynchronous responses
  never shows or applies facts, completeness, lifecycle, errors, or mutations
  from the wrong visit.

### Contract, migration, isolation, and regression behavior

- **AC-006-013:** The backend derives completeness from the authoritative facts,
  returns stable missing/conflicting identifiers and allowed lifecycle targets,
  and ignores or rejects frontend-authored completeness.
- **AC-006-014:** The additive migration adds only the three authorized nullable
  fields, preserves all rows without inferred backfill, upgrades and downgrades
  safely, and retains one Alembic head.
- **AC-006-015:** `Client.status` uses the six canonical states; legacy `NULL`
  and `active` are compatibility-read as draft without a read-time backfill,
  and any other stored value fails closed.
- **AC-006-016:** Duplicate identifiers, foreign client/record IDs, and missing
  clients produce stable safe responses with no partial write or cross-client
  disclosure.
- **AC-006-017:** M01 planned retirement and employment status cause no
  calculation, eligibility, employment-record, M07, M08, or saved-run side
  effect.
- **AC-006-018:** Focused M01 tests, PKG-005 fixation regressions, full backend
  and frontend suites, frontend production build/type-check, Python compile,
  Alembic single-head verification, and `git diff --check` all pass.

## 14. Negative acceptance criteria

- **NAC-006-001:** The frontend must not author, persist, or override
  `is_complete`, missing fields, conflicts, or lifecycle availability.
- **NAC-006-002:** Employment status must not be inferred from employment
  records, income, employment history, or M07 evidence, and free text must not
  satisfy completeness.
- **NAC-006-003:** Planned retirement must not be inferred from work end, pension
  start, eligibility date, retirement timing, M07/M08 evidence, age/date
  conversion, or a legal/professional default.
- **NAC-006-004:** When both planned-retirement fields exist, neither may win
  silently and the conflict must not be hidden or auto-corrected.
- **NAC-006-005:** Household, spouse, dependant, contact, tax, fixation, pension,
  grant, capitalization, or employment-history facts must not become mandatory
  for M01 completeness.
- **NAC-006-006:** Lifecycle must not skip states, auto-advance after edits or
  calculations, auto-regress after incompleteness, or create approval,
  recommendation, or professional sign-off meaning.
- **NAC-006-007:** Archived cases must not be edited through normal M01 mutation
  paths, and reopening must not bypass the explicit transition.
- **NAC-006-008:** No API, query, frontend state, or navigation link may disclose
  or retain another client's facts, record IDs, diagnostics, or results,
  including during A→B→A.
- **NAC-006-009:** Existing client data must not be deleted, overwritten, or
  backfilled from M07/M08, employment history, or inferred values.
- **NAC-006-010:** PKG-006 must not change an M07/M08 formula, authority,
  eligibility, parameter, indexation, calculation, evidence, snapshot, or
  PKG-005 workflow contract.
- **NAC-006-011:** PKG-006 must not implement M02 upload/intake, XML parsing,
  household modeling, team ownership, role hierarchy, broad authentication,
  scenarios, recommendations, reports, or another module.
- **NAC-006-012:** Acceptance must not depend on a broad application redesign,
  frontend-only persistence, mocks disconnected from the real API, production
  deployment, or a V1/V2 parity claim.

## 15. Required future implementation verification

Implementation acceptance must include:

- backend completeness unit tests for normalization, missing fields,
  `unknown`, mutually exclusive planning facts, and deterministic field order;
- client API tests for read/update, validation, duplicate identifiers, and
  stable diagnostics;
- lifecycle tests for every allowed transition and all invalid/skipped
  transition classes;
- tests for progressed-but-incomplete and archived read-only behavior;
- migration upgrade/downgrade tests, row preservation, nullable legacy clients,
  and Alembic single-head verification;
- client-isolation and safe foreign-ID non-disclosure tests;
- frontend case-workspace rendering, editing, validation, completeness,
  lifecycle, archived, and navigation tests;
- deferred-promise A→B and A→B→A tests covering stale successful and rejected
  reads, stale read `finally`, stale successful and rejected mutations, stale
  mutation `finally`, and a successful new request in the revisited A context;
- assertions in every stale-path test that both captured `clientId` and
  monotonic route-context generation gate all data, error, loading, mutation,
  completeness, lifecycle-target, validation-message, navigation, and
  client-workspace state updates; a `clientId`-only guard and timing-only tests
  are insufficient;
- PKG-005 fixation entry, calculate, save, history, reopen, isolation, and
  stale-response regression tests;
- full backend test suite;
- full frontend test suite;
- frontend production build and type-check;
- Python compile checks; and
- `git diff --check`.

Tests must use the real backend/frontend contracts. Client A and client B
fixtures must contain distinguishable facts so leakage cannot pass unnoticed.

## 16. Expected implementation change groups

Only the following directly necessary groups are expected after separate
authorization:

- one additive Alembic migration and migration tests;
- `Client` model and bounded client request/response schemas;
- M01 case-domain/completeness/lifecycle service logic;
- existing client-scoped routes and focused client API tests;
- frontend client API types/calls;
- client create/detail/workspace presentation and focused tests;
- route/navigation and async client-transition tests; and
- directly affected PKG-005 regression fixtures/tests.

Exact files must be confirmed at implementation authorization. Unrelated
backend services, frontend screens, formulas, accepted package records, and
broad refactors are excluded.

## 17. Explicit exclusions

- M02 upload or intake implementation;
- XML parsing or source ingestion;
- M03 source review or asset classification;
- ledger or conversion work;
- tax, fixation, pension, eligibility, grant, or indexation calculations;
- M07/M08 evidence, authority, formula, manifest, or lifecycle changes;
- official Form 161D;
- scenarios, comparisons, recommendations, or client reports;
- household modeling;
- team ownership or role hierarchy;
- broad authentication or authorization;
- M09-M14;
- 02M;
- production deployment;
- broad UI redesign or a new design system; and
- V1/V2 parity.

## 18. Stop conditions

Implementation must stop and return to GPT Chat rather than improvise if:

- `Client.status` cannot safely implement the defined lifecycle without a
  destructive migration, historical rewrite, or material meaning change;
- persistence beyond the three authorized nullable fields is required;
- migration would not be additive, would infer/backfill client facts, or would
  create more than one Alembic head;
- an employment-status value or planned-retirement rule outside this definition
  is required;
- implementation would infer a professional, legal, tax, eligibility,
  employment-termination, or pension meaning;
- client isolation or A→B→A response safety cannot be preserved;
- PKG-005 cannot be preserved without changing an accepted M07/M08 contract;
- household, authorization, M02, or another excluded module becomes necessary;
- existing client data would need deletion or reinterpretation; or
- implementation authorization differs materially from this definition.

## 19. Final gate

`PKG_006_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

Implementation and migration execution remain `NOT_AUTHORIZED`. No subpackage
or next package is authorized.
