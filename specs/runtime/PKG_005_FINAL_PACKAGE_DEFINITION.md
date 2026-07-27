# PKG-005 — Fixation End-to-End Usable Slice

## 1. Definition status

| Item | Value |
|---|---|
| Package | `PKG-005 - Fixation End-to-End Usable Slice` |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Product outcome | A usable end-to-end fixation workflow in the existing application UI |
| Package structure | One coherent product package; no subpackages are authorized |
| Implementation | `NOT_STARTED` |
| Base definition HEAD | `3344c1dfab7eb8a0fe2743631934405b90f97e26` |
| Next package | `NOT_AUTHORIZED` |

This document defines a product milestone. It does not authorize implementation,
does not change an accepted professional rule, and does not claim production
readiness, full M08 completion, or V1/V2 parity.

## 2. Product outcome and package boundary

PKG-005 is accepted only when a user can complete one coherent workflow through
the real application UI and backend:

1. Open an existing client and enter the fixation workspace.
2. Enter a `יום זכאות` (`eligibility_date`) through the accepted B1 evidence
   boundary, or select an existing finalized B1 revision.
3. Preserve and display the exact B1 revision selected for the calculation.
4. Validate the request using the accepted PKG-004D M07 admission boundary.
5. Resolve a missing or ambiguous eligibility date through visible UI actions.
6. Supply the existing M08B, M08C, and M08D inputs required by the bounded
   calculation without weakening their accepted gates.
7. Calculate and see the normalized date, year, result, material breakdown,
   warnings, and failures.
8. Save the run, reopen it, and see its input snapshot, resolver provenance,
   result, and relevant warnings.

The package includes all frontend, backend orchestration, schema, API, test, and
fixture changes necessary for that outcome. Those technical layers are not
separate packages or separately acceptable milestones.

## 3. Current-state gap inspection

| Area | Current classification | Repository finding and PKG-005 gap |
|---|---|---|
| Client fixation page and navigation | Already usable | Client detail links to the fixation workspace, and the workspace links to input and history. Preserve this navigation. |
| Fixation review/input components | Exists but uses legacy contract | The current input screen exposes direct eligibility date/year fields and uses the legacy review conversion flow. It cannot produce an admitted PKG-004D request. |
| Frontend request types | Exists but uses legacy contract | The current payload types contain direct `eligibility_date` and `eligibility_year`, legacy scalar parameters, and incomplete M08 wrappers. They must represent the accepted admission request. |
| Validate/calculate/save API calls | Already usable at transport level | The routes exist, but the current frontend caller sends the wrong contract. Save recalculates and persists a request and can be reused once the request is admissible. |
| Client retrieval | Already usable | Existing client APIs and screens provide the required client context. |
| B1 revision retrieval | Backend exists but UI/API missing | B1 service functions can retrieve and list bounded client revisions, but no client-facing HTTP route or frontend integration exposes them. |
| B1 eligibility-date write | Backend exists but UI/API missing | The accepted B1 service lifecycle can create a draft, append evidence/assertion, and finalize it. There is no usable HTTP or UI workflow for the fixation user. |
| Missing resolver handling | Backend exists but UI incomplete | PKG-004D returns structured M07 resolution diagnostics; the UI does not present a targeted correction action. |
| Ambiguous resolver handling | Backend exists but UI missing | The resolver supports explicit candidate selection, but the UI does not show candidates, record a choice, or retry with it. |
| Conflict selection representation | Backend exists but UI missing | The request can carry a selection using the selected revision and normalized candidate value; frontend types and controls do not expose it. |
| M08B parameter input | Incomplete | The UI has several scalar fields, but it does not construct the complete accepted caller-supplied parameter-set wrapper and omits required accepted-use data. |
| Grants and capitalization input | Incomplete | Grant, actual-capitalization, collection-state, inclusion, conflict, support, accepted-for-use, and reservation concepts exist, but the UI request does not consistently construct the full admitted M08C/M08D shape. |
| Result view | Already usable for basic results; incomplete for this workflow | It displays calculation sections and audit rows, but needs typed admission failures and material M07 provenance rather than relying on generic records. |
| Saved-run history and retrieval | Already usable; provenance presentation incomplete | History and run-detail routes/screens exist. The run snapshot contains dependency and resolver evidence, but the UI does not present the selected revision and provenance clearly. |
| Actor provenance boundary | Bounded technical actor included; broad authentication remains outside this milestone | The repository has no general trusted session/user identity implementation. The narrow B1 eligibility-date write uses a deterministic, server-controlled technical workflow actor recorded through the existing B1 audit/provenance fields. It does not introduce authentication or identify the human who entered the date. Browser-supplied actor text remains prohibited. |

## 4. Coherent user workflow

### 4.1 Entry and revision choice

The existing client fixation workspace remains the entry point. The calculation
input screen loads a bounded list of the client's finalized B1 evidence
revisions. The user explicitly selects the revision used by the request.

The repository has no accepted deterministic “current finalized revision”
selector. Therefore PKG-005 must not use latest-wins, implicit source ranking, or
an inferred current revision. A revision newly created in the same workflow may
be selected automatically only by the exact revision ID returned by that
successful create-and-finalize operation. The selected revision ID remains
visible before calculation.

### 4.2 Eligibility-date entry through B1

When a suitable finalized revision is not available, the input screen provides a
clear `יום זכאות` date field. Submitting that field calls a narrow, client-scoped
B1 operation which:

1. creates a revision draft using the accepted B1 lifecycle and the supported
   eligibility-date evidence contract;
2. writes the exact `eligibility_date` as planner-assertion/fact evidence using
   existing B1 services;
3. finalizes the revision using existing accepted behavior;
4. records a fixed, deterministic, server-controlled technical workflow actor
   through the existing B1 audit/provenance fields;
5. returns the exact revision ID and lifecycle status; and
6. completes atomically, rolling back the attempted revision if any step fails.

This operation does not derive legal eligibility, use generic
`retirement_timing`, create a new approval lifecycle, or bypass B1. The technical
actor represents the PKG-005 server workflow, not an authenticated human. Its
semantic identity is `actor_type: system`, `actor_id/code: fixation-ui`, and
`actor_label: Fixation workflow`; exact field names may follow existing
repository conventions. The browser does not supply or override the
authoritative actor. This operational provenance is not authentication,
authorization, professional approval, authority, or proof of who physically
entered the date. Client ownership and isolation remain enforced through the
route client ID and existing B1 service boundaries.

### 4.3 Validation, resolution, and retry

The frontend constructs the PKG-004D request using
`m07_input_reference.b1_evidence_revision_id`. It sends no direct
`eligibility_date`, `eligibility_year`, or legacy `M07EntryContext`.

For an unambiguous revision, validation proceeds with the server-resolved value.
For `missing_inputs`, the UI identifies the missing eligibility date, explains
that calculation has not run, and offers the date-entry action. For
`ambiguous_inputs`, it displays the safe candidate dates and stable candidate
references returned by the backend. The user chooses a candidate and retries
with an explicit selection bound to the selected B1 revision. A safe
missing/foreign-revision response does not expose another client's identifiers,
evidence, or candidate values.

The legacy review-conversion route must not be used to initiate the new
calculation request. Any retained legacy helper remains non-authoritative and
cannot restore a direct date/year admission path.

### 4.4 Existing M08 inputs

After M07 admission, the same product screen supplies the existing non-M07
inputs. PKG-005 adapts the UI and request construction; it does not redesign
their accepted meanings.

- **M08B:** retain the current caller-supplied parameter approach for this
  milestone. The UI sends the complete accepted `parameter_set` wrapper,
  including the required four calculation values, parameter-set identity,
  tax/effective period, source/basis/status, actor/decision evidence, and
  accepted-for-use state required by the existing contract. The tax year is
  labelled as the parameter tax year and is not a caller-supplied eligibility
  year. The official-parameter resolver is a follow-up, not part of PKG-005.
- **M08C:** preserve grants, actual capitalizations, collection states, future
  grant reservation, explicit inclusion, conflicts, support, and
  accepted-for-use behavior. The UI must expose or preserve every field required
  by the admitted wrapper and must not silently manufacture acceptance.
- **M08D:** preserve asserted-versus-system evidence, CBS CPI code and request
  mapping, failure statuses, immutable evidence, client isolation, and the
  no-authoritative-fallback rule. The browser must never create CBS system
  evidence. It may request the existing CBS calculation mode or provide an
  accepted asserted mode through the existing boundary.

An M08B, M08C, or M08D blocker remains a blocker even after M07 resolves.

### 4.5 Result, save, and reopen

On success, the result screen presents at least:

- normalized eligibility date and eligibility year;
- the key result values exposed by the engine;
- grant and capitalization effects exposed by the engine;
- relevant warnings and audit information; and
- the exact client and selected B1 revision context.

The existing save route is reused with the same admitted request. After save,
the UI displays the saved-run identity/date and provides navigation to its
detail. Reopening a run presents the material input snapshot, selected B1
revision and explicit selection if any, dependency scope/version, resolver
outcome and fingerprint, relevant sources, calculation result, warnings, and
audit evidence. Raw JSON may remain available as supporting evidence, but it is
not the only product presentation.

## 5. Required backend changes

The implementation package is expected to make bounded additions to the existing
backend:

1. Expose client-scoped, bounded retrieval of finalized B1 revisions using the
   existing B1 service and isolation rules.
2. Expose a narrow atomic create-and-finalize eligibility-date revision
   operation which composes the accepted B1 service lifecycle without adding a
   new lifecycle or authority decision.
3. Return only the safe revision and candidate data necessary for selection.
4. Accept and validate the exact PKG-004D M07 reference/selection request already
   supported by the fixation admission boundary.
5. Preserve existing validate, calculate, save, history, run-detail, dependency
   manifest, resolver, engine, and snapshot behavior.
6. Bind every narrow B1 eligibility-date write to the fixed, deterministic,
   server-controlled technical workflow actor described in section 4.2, using
   the existing B1 audit/provenance fields. Ignore or reject frontend actor
   input; do not represent the technical actor as an authenticated human,
   authorization decision, professional approval, or authority.

The precise route names may follow the repository's existing client-scoped API
convention. Their semantics must remain the narrow operations above.

## 6. Required frontend changes

The implementation package is expected to:

1. replace the legacy fixation admission request types with typed
   `m07_input_reference` and optional explicit selection structures;
2. load and display the bounded finalized B1 revision list for the active
   client;
3. add the narrow eligibility-date create/finalize control and select the
   returned revision by exact ID;
4. show the selected revision identity and status before validation;
5. stop sending direct eligibility date/year and stop using legacy review
   conversion to initiate calculation;
6. render structured missing, ambiguous, safe missing/foreign, and existing M08
   failures with actionable, non-leaking messages;
7. display ambiguous candidate dates, capture an explicit choice, and retry;
8. construct the complete existing M08B, M08C, and M08D admitted input shapes;
9. preserve validation-before-calculation behavior and make both outcomes
   visible;
10. present normalized result and provenance fields; and
11. save and reopen the real backend run without mocks or frontend-only
    persistence.

Broad visual redesign and a new design system are not part of this package.

## 7. Reproducible acceptance demonstrations

### Scenario 1 — Successful run

A user opens an existing client, creates or selects a finalized B1 revision with
a valid eligibility date, supplies valid parameter and M08C/M08D inputs,
validates, calculates, sees the result, saves the run, and reopens it with the
same inputs, revision provenance, result, and warnings.

### Scenario 2 — Missing date

A selected revision has no usable eligibility date. The UI shows
`missing_inputs`; CBS and the engine do not run. The user adds the date through
the B1 operation, selects the exact returned revision, retries, and can proceed.

### Scenario 3 — Ambiguous date

A selected revision exposes two different eligible normalized dates. The UI
shows both safe candidates. The user explicitly selects one, retries
successfully, saves the run, and the reopened snapshot records the selection.

### Scenario 4 — Preserved M08 gate

M07 resolves a valid eligibility date but an existing M08B, M08C, or M08D
requirement fails. The UI shows that existing failure, and neither M07
resolution nor the UI bypasses or weakens the blocker.

## 8. Acceptance criteria

### Product-visible and executable behavior

- **AC-005-001:** From an existing client, the user can navigate through the
  existing UI to the fixation input workflow without entering a client ID
  manually.
- **AC-005-002:** The UI displays a bounded, client-isolated list of finalized B1
  revisions and requires a visible, exact revision selection before admission.
- **AC-005-003:** The user can enter a `יום זכאות` date through the fixation UI;
  the real backend creates and finalizes the B1 evidence revision and returns its
  exact identity.
- **AC-005-004:** A newly created revision is selected only by the exact returned
  ID, and its identity and finalized status are visible before validation.
- **AC-005-005:** The user can run validation separately and sees whether the
  request is ready for calculation.
- **AC-005-006:** For missing eligibility evidence, the UI displays the missing
  field, confirms that downstream calculation did not run, and provides a usable
  add-date-and-retry path.
- **AC-005-007:** For ambiguous eligibility evidence, the UI displays the safe
  candidate dates, lets the user select one, and retries with an explicit
  revision-bound selection.
- **AC-005-008:** A missing or foreign revision produces a safe actionable error
  without exposing another client's revision, evidence, or candidate data.
- **AC-005-009:** The UI supports the complete existing caller-supplied M08B
  parameter wrapper and distinguishes parameter tax year from the
  server-resolved eligibility year.
- **AC-005-010:** The UI preserves the existing M08C grant, capitalization,
  collection, reservation, inclusion, conflict, support, and accepted-for-use
  inputs required for an admitted request.
- **AC-005-011:** The UI preserves the existing M08D asserted/system distinction
  and CBS/no-fallback boundary and clearly presents an M08D failure.
- **AC-005-012:** A valid request calculates through the real backend and shows
  normalized eligibility date/year, key values, exposed grant/capitalization
  effects, warnings, and failures.
- **AC-005-013:** The user can save a successful run, see its run identity/date,
  and navigate to the saved-run detail.
- **AC-005-014:** Reopening a saved run visibly preserves its material inputs,
  selected B1 revision, explicit candidate selection if used, resolver
  provenance, dependency scope/version, result, audit evidence, and warnings.

### Contract, evidence, and regression behavior

- **AC-005-015:** Every fixation validate, calculate, and save request from the
  updated UI uses `m07_input_reference.b1_evidence_revision_id`, sends only valid
  optional conflict selections, and sends no direct eligibility date/year or
  legacy M07 context.
- **AC-005-016:** The narrow B1 eligibility-date operation composes the existing
  draft/write/finalize lifecycle atomically, retains client isolation, records
  the deterministic server-controlled technical workflow actor through existing
  B1 provenance fields, trusts no frontend-supplied actor, creates no
  authentication claim, and does not create a competing evidence lifecycle.
- **AC-005-017:** Missing and ambiguous M07 outcomes stop CBS and the fixation
  engine, while a resolved M07 outcome does not bypass any M08B/M08C/M08D gate.
- **AC-005-018:** The four required acceptance scenarios are covered by a small
  set of realistic frontend/backend workflow tests using the real contracts,
  including save/reopen and client isolation.
- **AC-005-019:** Existing PKG-004D regression tests, fixation engine golden
  tests, full backend tests, full frontend tests, frontend production build,
  compile checks, Alembic single-head verification, and `git diff --check` pass.
- **AC-005-020:** No formula, accepted domain rule, migration head, dependency
  manifest meaning, or existing saved-run immutability contract changes.

## 9. Negative acceptance criteria

- **NAC-005-001:** The UI or API must not restore, send, or accept legacy
  `M07EntryContext` as the new fixation admission path.
- **NAC-005-002:** A caller must not supply `eligibility_date` or
  `eligibility_year` directly to fixation admission.
- **NAC-005-003:** The eligibility-date UI must not write outside the accepted B1
  evidence lifecycle or treat browser state as persisted evidence.
- **NAC-005-004:** The system must not select a hidden “latest”, “best”, or
  “current” B1 revision or rank sources without an accepted deterministic
  mechanism.
- **NAC-005-005:** The UI or server must not resolve ambiguous dates without the
  user's explicit, revision-bound selection.
- **NAC-005-006:** Caller-supplied resolver outcomes, fingerprints, authority,
  reliability, qualification, or professional sufficiency must not replace
  server resolution.
- **NAC-005-007:** PKG-005 must not weaken, silently default, infer, or bypass an
  accepted M08B, M08C, or M08D requirement.
- **NAC-005-008:** The browser must not manufacture CBS system evidence or create
  an authoritative fallback after CBS failure.
- **NAC-005-009:** No fixation, grant, capitalization, indexation, exemption, or
  tax formula may change.
- **NAC-005-010:** Acceptance must not rely on UI-only mocks, fake persistence, or
  a workflow disconnected from the real validate/calculate/save/reopen backend.
- **NAC-005-011:** A successful result without save and reopen provenance is not
  sufficient for package acceptance.
- **NAC-005-012:** PKG-005 must not introduce a new B1 lifecycle, implicit current
  revision marker, broad evidence editor, table, or migration solely to avoid
  explicit revision selection.
- **NAC-005-013:** PKG-005 must not be divided into backend, frontend, schema, or
  other independently authorized or accepted subpackages.
- **NAC-005-014:** PKG-005 must not expand into formal 161D, full M08F, M09-M14,
  02M, V1/V2 parity, broad UI redesign, a new design system, or production
  deployment.
- **NAC-005-015:** Browser-supplied actor text must not be trusted or described as
  authenticated, and the permitted server technical actor must be operational
  provenance only. The package must not claim a real-user identity, treat that
  actor as authorization, authority, or professional approval, implement a
  broad authentication model, or claim production readiness.

## 10. Required verification

Implementation acceptance must include:

- focused frontend component and integration tests for revision entry/selection,
  missing, ambiguous, M08 blocker, success, save, and reopen behavior;
- backend API/service tests for any newly exposed B1 routes, atomicity, safe
  failures, and client isolation;
- validate/calculate/save and saved-run reopen tests;
- PKG-004D missing, ambiguous, selection, and admission regressions;
- fixation engine golden tests;
- full backend test suite;
- full frontend test suite;
- frontend production build;
- backend/frontend compile checks;
- Alembic single-head verification; and
- `git diff --check`.

Tests must use the real frontend request contract and real backend routes. A
small number of realistic workflow tests is preferred over redundant schema-only
tests.

## 11. Expected implementation change groups

The authorized implementation plan is expected to touch only the groups required
by the coherent workflow:

- backend B1 client-scoped route/orchestration and narrow request/response
  schemas;
- backend route registration and focused B1/fixation API tests;
- frontend B1/fixation API types and calls;
- fixation input/review, result, and run-detail presentation;
- focused frontend component/integration tests and fixtures; and
- only directly necessary supporting types or test helpers.

Exact files must be confirmed against the implementation authorization and the
then-current repository. Unrelated refactors are excluded.

## 12. Persistence and migration expectation

No database migration is expected. PKG-005 must reuse the accepted B1 revision,
evidence, fixation run, snapshot, dependency manifest, and audit persistence.
If implementation discovers that the usable workflow requires a new table,
column, lifecycle state, current-revision marker, or changed immutable snapshot
meaning, it must stop and return to GPT Chat for a scope and authority decision.

## 13. Explicit exclusions

- formula or professional-rule changes;
- automatic legal eligibility-date derivation;
- official parameter resolver integration;
- broad B1 evidence editing, qualification, approval, or source-ranking workflow;
- broad authentication/authorization design;
- formal Form 161D generation;
- full M08F;
- M09 scenario engine;
- M10 comparison;
- M11 recommendations;
- M12 client report;
- M13/M14 full production work;
- 02M;
- V1/V2 parity;
- broad UI redesign or a new design system; and
- production deployment.

## 14. Stop conditions

Implementation must stop and report rather than improvise if:

- the existing B1 schema cannot record the fixed server-controlled technical
  workflow actor without a migration or lifecycle change, or implementation
  would falsely represent that actor as an authenticated human user;
- safe bounded B1 selection cannot be implemented with explicit revision
  identity and the existing lifecycle;
- an accepted M07 or M08 professional rule, formula, authority boundary,
  no-fallback rule, or dependency meaning would need to change;
- a migration, new persistence lifecycle, implicit current-revision mechanism,
  or immutable snapshot meaning would need to be added;
- a necessary change expands into an explicit exclusion or a new package;
- client isolation or safe non-disclosure cannot be preserved; or
- implementation authorization differs materially from this definition.

## 15. Final gate

`PKG_005_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

Implementation is not authorized by this document. No subpackage is authorized,
and the next package remains `NOT_AUTHORIZED`.
