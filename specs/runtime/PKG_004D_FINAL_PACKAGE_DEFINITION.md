# PKG-004D — M08A Resolver Admission Integration

## 1. Definition Status

| Field | Value |
|---|---|
| Package | `PKG-004D — M08A Resolver Admission Integration` |
| Package type | Narrow PKG-004B2 consumer integration for the existing bounded M08A fixation admission path |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Implementation | `NOT_STARTED` |
| Accepted dependencies | PKG-004B1 evidence foundation; PKG-004B2 `CALCULATION_INPUT_RESOLVER_FRAMEWORK`; PKG-004C exact `eligibility_date` contract; existing bounded M08A engine; existing M08B, M08C, and M08D admission foundations |
| Formula changes | `NONE` |
| Migration expected | `NO` |
| Next package authorization | `NOT_AUTHORIZED` |

This document defines a future implementation package. It does not authorize
implementation, register a runtime manifest, change fixation admission, or
start another package.

## 2. Purpose

PKG-004D integrates the accepted PKG-004B2 resolver into the existing bounded
M08A fixation admission path for exactly one M07 calculation input:

`eligibility_date`

For new calculations, the server resolves that value from a finalized,
client-scoped PKG-004B1 evidence revision under a server-owned production
manifest. A `resolved` result supplies the normalized date, from which the
server derives:

`eligibility_year = eligibility_date.year`

The package replaces the obsolete caller-supplied M07 qualification gate with
a calculation-input resolution gate. It does not determine the professional
or legal eligibility date and does not change the existing M08A formula.

## 3. Accepted Dependencies Consumed Without Redefinition

PKG-004D consumes the following accepted contracts:

- PKG-004B1 owns finalized evidence revisions, fact evidence, planner
  assertions, source references, provenance, and client isolation.
- PKG-004B2 owns manifest-based resolution, normalization, coalescing,
  ambiguity, explicit selection, result fingerprinting, and the three resolver
  outcomes.
- PKG-004C owns the exact B1 field identity and strict evidence value contract
  for `eligibility_date`.
- M08A owns the existing bounded fixation formula and `FixationInput`.
- M08B owns annual parameter applicability and its current fail-closed gates.
- M08C owns grant, capitalization, reservation, conflict, support, and
  accepted-for-use admission.
- M08D owns CBS system evidence, asserted-value distinction, typed failure,
  and no-fallback behavior.

PKG-004D must not broaden, reinterpret, or replace those contracts.

## 4. Server-Owned Production Manifest

Implementation will register one concrete production manifest in the accepted
PKG-004B2 manifest registry:

| Property | Contract |
|---|---|
| Calculation scope | `m08a_fixation` |
| Manifest version | `1` |
| Required field count | exactly one |
| Required field | `eligibility_date` |
| Technical type | `date` |
| Normalization | `iso_date`, preserving the strict PKG-004C `YYYY-MM-DD` evidence contract |
| Null permitted | no |
| Conditional fields | none |

The calculation scope and manifest version are server constants. They are not
accepted from the caller.

The manifest must not include:

- `employment_status`;
- `retirement_timing`;
- evidence collection states;
- grant or capitalization arrays;
- annual parameters;
- pension commencement;
- tax year as separate M07 evidence;
- qualification, warning-review, approval, or authority fields.

Unknown scope or manifest version fails closed through the existing PKG-004B2
manifest boundary.

## 5. New Request Boundary

The new fixation-admission request contains the existing non-M07 calculation
inputs plus one narrow resolver reference:

```text
m07_input_reference:
    b1_evidence_revision_id
    selections?
```

The exact schema name may follow repository conventions. The resolver
reference contains:

- one required `b1_evidence_revision_id`;
- optional explicit PKG-004B2 conflict selections.

Selections must be scoped to that revision and may select only an available
`eligibility_date` candidate under the server-owned M08A manifest.

The caller must not supply:

- calculation scope;
- manifest version;
- M07 state;
- `qualified` or `warning_reviewed`;
- reviewer or review reason;
- qualification trace;
- resolver outcome;
- normalized resolver values;
- `eligibility_date`;
- `eligibility_year`;
- resolver fingerprint;
- source references.

Pydantic request models must forbid extra fields. Direct caller values must be
rejected rather than ignored.

The existing calculate, validate, and save operations should be adapted through
their shared admission boundary. No new public calculation API is required.
Existing review-helper endpoints must not allow a direct date or legacy M07
context to bypass the new admission boundary for a new calculation.

## 6. Compatibility Strategy for `M07EntryContext`

PKG-004D chooses compatibility strategy 1:

> Remove `M07EntryContext` from the new request contract while retaining
> legacy read compatibility for stored historical snapshots and manifests.

For new calculations:

- `M07EntryContext` is not required or accepted as authority;
- no `qualified` state is fabricated from a resolved B2 result;
- no qualification warning, review, reviewer, timestamp, or trace is created;
- resolver evidence replaces qualification state in new dependency evidence.

For historical records:

- the legacy schema remains available to parse or serialize prior stored
  snapshots where required;
- prior snapshots and dependency manifests remain readable;
- historical content is not rewritten, backfilled, or reclassified;
- legacy qualification content remains historical data only and does not
  govern admission of a new calculation.

## 7. Resolver Invocation

After request structure and route/client identity are validated, the server
constructs the PKG-004B2 request:

```text
resolve_calculation_inputs(
    client_id = route client,
    calculation_scope = "m08a_fixation",
    manifest_version = "1",
    b1_evidence_revision_id = request reference,
    selections = request selections
)
```

The route client ID is authoritative. The resolver must load only the exact
finalized B1 revision owned by that client.

## 8. Resolver Outcome Behavior

### 8.1 `resolved`

Admission may continue only when:

- a calculation-ready payload exists;
- it contains exactly `eligibility_date`;
- the normalized value is a valid ISO calendar date;
- the payload scope, version, client, and B1 revision match the
  server-constructed request.

The server derives `eligibility_year` from the normalized date. It then
continues through the existing M08B, M08C, and M08D gates and constructs the
unchanged `FixationInput`.

### 8.2 `missing_inputs`

Admission stops before:

- parameter applicability resolution dependent on eligibility date or year;
- any CBS request;
- construction or admission of `FixationInput`;
- engine invocation;
- creation of a saved successful result.

The response contains structured field diagnostics for `eligibility_date`.
No date or year is inferred.

### 8.3 `ambiguous_inputs`

Admission stops and returns:

- field code `eligibility_date`;
- the available normalized dates;
- candidate identities;
- source references needed for explicit selection.

No source is ranked and no date is selected automatically. A later request may
provide one valid explicit selection through the resolver reference.

### 8.4 Explicit Selection

A selection is valid only when it:

- refers to `eligibility_date`;
- belongs to the same B1 revision;
- identifies a currently available normalized candidate;
- satisfies the accepted PKG-004B2 selection contract.

A stale, foreign-revision, unavailable, or otherwise invalid selection cannot
produce `resolved`.

## 9. Eligibility-Year Derivation

After and only after a `resolved` result:

```text
eligibility_date = resolved_payload["eligibility_date"]
eligibility_year = eligibility_date.year
```

`eligibility_year` is server-derived and is not B1 evidence. The caller cannot
supply it. The derived year must continue to match the existing M08B parameter
set under the current parameter applicability rules.

## 10. M08B Boundary

The existing caller-supplied M08B parameter wrapper remains temporarily
unchanged in PKG-004D.

PKG-004D preserves:

- applicable tax-year matching against the derived eligibility year;
- effective-period checks against the resolved eligibility date;
- required parameter values;
- existing accepted-for-use and fail-closed behavior.

This package does not replace that wrapper with the official parameter
resolver and does not redesign annual parameter authority. If correct M07
integration proves to require an M08B redesign or a different parameter
resolution path, implementation must stop for separate scope direction.

## 11. M08C Boundary

PKG-004D preserves the existing behavior for:

- grant and severance collection state;
- grant items;
- actual capitalization collection state and items;
- future grant reservation;
- conflict decisions;
- accepted-for-use gates;
- support status.

No M08C gate is removed or inferred from M07 resolution.

## 12. M08D Boundary

PKG-004D preserves:

- the CBS trust boundary;
- server-controlled CBS request and response evidence;
- the distinction between system-calculated and asserted indexed values;
- typed failures;
- the no-fallback rule.

An unresolved M07 input must stop admission before any CBS call.

## 13. Engine Boundary

PKG-004D does not change:

- `FixationInput`;
- fixation formulas;
- the 15-year boundary;
- the 32-year window;
- grant impact;
- capitalization impact;
- monthly exempt pension calculation;
- existing golden calculation outcomes.

The admission adapter supplies the resolved date and derived year to the
existing `FixationInput`. The engine remains unaware of B1, B2, manifests,
resolver outcomes, selections, and source references.

## 14. Snapshot and Dependency Evidence

### 14.1 New Input Snapshots

New saved runs must preserve in the existing JSON snapshot boundary:

- the B1 evidence revision ID;
- calculation scope `m08a_fixation`;
- manifest version `1`;
- resolver outcome `resolved`;
- resolver fingerprint;
- normalized `eligibility_date`;
- derived `eligibility_year`;
- source references;
- any explicit conflict selection used;
- the existing non-M07 admitted input context.

The snapshot must not store professional approval or authority state.
If the existing save operation persists a failed resolution attempt, its
snapshot must preserve the unresolved outcome and diagnostics without
inventing resolved values or a calculation-ready result.

### 14.2 New Dependency Manifests

New runs require a new dependency-manifest schema version whose M07 dependency
content is resolver evidence rather than qualification state. The exact
version identifier may follow repository conventions.

For the M07 resolver dependency, the stable comparison content must include:

- B1 evidence revision ID;
- calculation scope;
- manifest version;
- resolver fingerprint;
- normalized eligibility date;
- derived eligibility year;
- source references;
- explicit selection evidence, when used.

New-to-new comparisons use that resolver dependency. They must not compare M07
qualification state.

### 14.3 Historical Compatibility

The existing JSON columns can represent the new snapshot and manifest content;
no migration is expected.

- Legacy manifest schema versions remain readable.
- Legacy snapshots remain readable through the legacy schema.
- Historical records are not rewritten.
- A comparison across incompatible manifest schema versions returns
  technically `unknown` with the existing safe schema-incompatibility
  behavior; it must not claim unchanged or changed by silently equating legacy
  qualification state with resolver evidence.

No persistent B2 resolution table or resolution-history lifecycle is added.

## 15. API Boundary

The existing fixation routes remain the public calculation boundary.
Implementation may narrow their request model and shared admission service only
as needed to:

- accept the resolver reference;
- reject caller-supplied M07 values and authority state;
- invoke PKG-004B2 server-side;
- return structured missing or ambiguous diagnostics;
- preserve resolver evidence for saved runs.

The currently untyped request dictionaries should be tightened with the new
admission schema. Route redesign, a new public calculation API, and UI work are
outside scope.

## 16. Deterministic Validation Order

The new-calculation path must execute in this order:

1. Parse the narrow request structure and reject forbidden extra fields.
2. Validate the route client and request ownership boundary.
3. Construct the server-owned M08A scope and manifest version.
4. Resolve the finalized B1 revision through PKG-004B2.
5. Stop on unavailable revision, `missing_inputs`, `ambiguous_inputs`, or
   invalid selection.
6. Validate the resolved payload and derive `eligibility_year`.
7. Apply the unchanged M08B parameter applicability gates.
8. Apply the unchanged M08C admission gates.
9. Perform M08D/CBS work only where required by admitted grant inputs.
10. Construct the existing `FixationInput`.
11. Invoke the unchanged fixation engine.
12. Persist the snapshot, versioned dependency evidence, and result.

No CBS call or engine invocation may occur before successful M07 resolution.

## 17. Structured Failure Compatibility

The admission boundary must expose structured technical failures for:

| Condition | Required behavior |
|---|---|
| B1 revision missing or unavailable | fail closed without calculation payload |
| Foreign-client B1 revision | same safe external behavior as a missing revision |
| Unknown M08A manifest | fail closed as unsupported server manifest configuration |
| Missing `eligibility_date` | `missing_inputs` diagnostic naming the field |
| Invalid or non-normalizable `eligibility_date` | `missing_inputs` diagnostic naming the field |
| Ambiguous `eligibility_date` | `ambiguous_inputs` with available candidates and source references |
| Stale or invalid selection | selection failure or unresolved ambiguity; never automatic selection |

Missing and foreign B1 references must not disclose existence differences.
These failures are technical calculation-input failures, not professional
review, qualification, warning-review, or authority states.

## 18. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-D-001 | The server registers exactly one production manifest under scope `m08a_fixation` and version `1`. |
| AC-D-002 | The manifest contains exactly one required, non-nullable `date` field: `eligibility_date`, normalized under the accepted ISO-date contract. |
| AC-D-003 | Scope and manifest version are server-controlled and cannot be supplied or overridden by the caller. |
| AC-D-004 | The new request accepts a finalized B1 revision reference and optional PKG-004B2 selections, but rejects caller-supplied date, year, outcome, fingerprint, source references, and M07 qualification context. |
| AC-D-005 | A `resolved` result supplies the normalized `eligibility_date`, and the server derives `eligibility_year = eligibility_date.year`. |
| AC-D-006 | Missing or invalid eligibility-date evidence produces structured `missing_inputs` behavior and no calculation-ready admission. |
| AC-D-007 | Multiple different normalized dates produce structured `ambiguous_inputs` behavior with candidates and source references and no automatic selection. |
| AC-D-008 | A valid explicit selection for the same revision and available candidate resolves ambiguity; stale, invalid, or foreign-revision selection does not. |
| AC-D-009 | Missing and foreign-client B1 revisions fail with safe equivalent external behavior, and all resolution remains client-isolated. |
| AC-D-010 | No parameter-dependent work, CBS call, `FixationInput` construction, engine call, or saved successful result occurs before M07 resolution succeeds. |
| AC-D-011 | Existing M08B parameter applicability, effective-period, accepted-for-use, and fail-closed behavior remains unchanged and uses the derived year and resolved date. |
| AC-D-012 | Existing M08C collection, support, conflict, reservation, and accepted-for-use gates remain unchanged. |
| AC-D-013 | Existing M08D CBS trust, evidence, typed-failure, asserted-value distinction, and no-fallback behavior remains unchanged. |
| AC-D-014 | The existing `FixationInput`, engine formulas, boundaries, and golden outcomes remain unchanged. |
| AC-D-015 | New snapshots and dependency manifests preserve B1 revision, resolver scope/version/outcome/fingerprint, normalized date, derived year, source references, and explicit selection evidence without professional authority state. |
| AC-D-016 | Historical snapshots and manifests remain readable without rewrite or backfill; incompatible dependency schema versions compare as technically `unknown`; no migration or persistent resolution lifecycle is added. |
| AC-D-017 | `M07EntryContext` is absent from new-calculation admission, no `qualified` state is fabricated, and legacy qualification content is retained only for historical reads. |

## 19. Negative Acceptance Criteria

| ID | Prohibited behavior |
|---|---|
| NAC-D-001 | Treating caller-supplied `M07EntryContext`, qualification, warning review, reviewer, or trace as authority for a new calculation. |
| NAC-D-002 | Fabricating `state="qualified"` or any approval state from a PKG-004B2 `resolved` result. |
| NAC-D-003 | Accepting `eligibility_date` directly from the caller outside the resolver result. |
| NAC-D-004 | Accepting caller-supplied `eligibility_year`, resolver outcome, fingerprint, normalized values, or source references. |
| NAC-D-005 | Ranking or selecting evidence by latest-wins, timestamp, source type, reliability, actor, verification label, or claimed authority. |
| NAC-D-006 | Falling back from `eligibility_date` to `retirement_timing` or another adjacent field. |
| NAC-D-007 | Automatically determining the professional or legal eligibility date. |
| NAC-D-008 | Removing or weakening M08C accepted-for-use, collection, support, conflict, capitalization, or reservation gates. |
| NAC-D-009 | Redesigning M08B, replacing its current wrapper, or changing annual-parameter authority in this package. |
| NAC-D-010 | Weakening the M08D CBS trust boundary, typed failures, evidence distinction, or no-fallback rule. |
| NAC-D-011 | Changing `FixationInput`, formulas, calculation boundaries, or golden engine outcomes. |
| NAC-D-012 | Rewriting, backfilling, reclassifying, or destructively migrating historical snapshots or dependency manifests. |
| NAC-D-013 | Adding a persistent B2 resolution table, current selector, resolution history, or new resolution lifecycle. |
| NAC-D-014 | Expanding into UI, frontend, scenarios, M08E, full M08F, M09-M14, formal 161D, or 02M. |
| NAC-D-015 | Claiming M08 completion, production readiness, V1/V2 parity, or authorization of another package. |

## 20. Required Future Implementation Tests

Future implementation must test at least:

1. a valid B1 `eligibility_date` resolves and reaches the unchanged engine;
2. `eligibility_year` is derived correctly;
3. caller-supplied `eligibility_date` is rejected;
4. caller-supplied `eligibility_year` is rejected;
5. a missing date stops before parameter-dependent, CBS, and engine calls;
6. an invalid date stops before those calls;
7. ambiguous dates stop and expose candidates and source references;
8. a valid explicit selection resolves ambiguity;
9. a stale or invalid selection cannot resolve;
10. missing and foreign B1 revisions have safe equivalent failure;
11. client isolation is preserved;
12. the M08A production manifest contains exactly `eligibility_date`;
13. unknown scope or manifest version fails closed;
14. no `retirement_timing` fallback exists;
15. no M07 qualification context is required or fabricated;
16. a legacy stored run remains readable;
17. a new snapshot stores revision, resolver fingerprint, normalized date,
    derived year, source references, and selection evidence;
18. dependency comparison uses resolver evidence rather than M07 qualification
    state;
19. M08B failures remain unchanged;
20. M08C accepted-for-use and support gates remain unchanged;
21. CBS behavior remains unchanged;
22. engine golden results remain unchanged;
23. no migration or persistent resolution table is added;
24. no UI or frontend file changes.

## 21. Expected Implementation Shape

Expected implementation may touch only the narrow technical seams required
for:

- M08A production manifest registration;
- fixation-admission request schemas;
- the shared fixation-admission service;
- server-side PKG-004B2 invocation;
- fixation snapshot and versioned dependency construction;
- dependency comparison compatibility;
- focused and boundary regression tests.

A migration is not expected. A persistent B2 resolution model is prohibited.
Implementation must remain a narrow adaptation of the existing fixation
routes and services.

## 22. Explicit Exclusions

PKG-004D excludes:

- fixation formula changes;
- automatic eligibility-date calculation;
- source reliability, authority, or professional sufficiency decisions;
- M08B redesign or official-parameter resolver integration;
- M08C redesign;
- removal of M08C accepted-for-use gates;
- M08D redesign;
- UI or frontend;
- new scenario behavior;
- M08E;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- historical backfill;
- production readiness;
- V1/V2 parity.

## 23. Stop Conditions

Implementation must stop and return for product or architecture direction if:

- correct integration requires a formula or `FixationInput` change;
- M08B must be redesigned or its resolver replaced in the same package;
- M08C accepted-for-use or support boundaries must be removed;
- the CBS trust boundary, typed failures, or no-fallback rule must change;
- historical snapshots cannot remain readable without destructive migration;
- resolver evidence cannot be preserved in existing JSON persistence without a
  new persistent resolution lifecycle;
- UI or scenario work is required;
- more than `eligibility_date` becomes required for the bounded M08A manifest;
- the eligibility date must be derived legally or professionally rather than
  supplied as evidence;
- M08E, full M08F, M09-M14, formal 161D, or 02M must be opened.

## 24. Final Gate

`PKG_004D_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

This gate confirms only that the final package definition exists. It does not
authorize implementation, manifest registration, fixation-admission changes,
or work on another package.
