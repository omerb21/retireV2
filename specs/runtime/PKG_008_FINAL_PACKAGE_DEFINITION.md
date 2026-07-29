# PKG-008 — M03 Source Review and Downstream Evidence Eligibility Foundation

## 1. Identity and status

| Item | Value |
|---|---|
| Package | `PKG-008 — M03 Source Review and Downstream Evidence Eligibility Foundation` |
| Module | `M03` |
| Definition status | `DRAFT_PENDING_GATE_REVIEW` |
| Product outcome | Append-only, client-scoped source/manual review and narrow downstream evidence eligibility |
| Predecessor | `PKG-007 — M02 Controlled Pension Intake and Opaque Source Preservation` |
| Definition base | `fdf435c33ce039c6c2ef578db7d2dffae5a4412d` |
| Accepted PKG-007 implementation | `4f2ff42467283653d6e022706c749815bd8c9589` |
| Accepted PKG-007 closure | `fdf435c33ce039c6c2ef578db7d2dffae5a4412d` |
| Existing Alembic head | `b6d8e2f4a701` |
| Migration | `ADDITIVE_MIGRATION_REQUIRED_NOT_EXECUTED` |
| Implementation | `NOT_AUTHORIZED` |
| M04 | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |

This document is a definition draft only. It does not authorize code changes,
test changes, migration execution, M04, parsing, normalization,
classification, downstream execution, or production use.

## 2. Authoritative sources

The authoritative planning source is:

`specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`

This definition is also constrained by:

- `specs/runtime/PKG_007_FINAL_PACKAGE_DEFINITION.md`;
- `specs/runtime/PKG_007_definition_acceptance_record.md`;
- `specs/runtime/PKG_007_acceptance_record.md`;
- the accepted PKG-007 implementation at
  `4f2ff42467283653d6e022706c749815bd8c9589`; and
- the locked product and architecture decisions in the authorization that
  requested this definition draft.

If a later implementation request conflicts with these sources or changes a
locked product meaning, implementation must stop rather than improvise.

## 3. Predecessor contracts

PKG-008 consumes PKG-007 records without changing their meaning:

- M02 owns intake creation, opaque upload preservation, controlled manual
  intake, source/blob/checksum provenance, duplicate indications,
  superseding-candidate detection, lifecycle, storage, and download.
- M02 `accepted_for_review` means only that a target may be explicitly selected
  for M03 review.
- M02 `accepted_for_review` does not create an M03 review, imply acceptance, or
  create downstream authority.
- M02 `rejected` and `superseded` remain retained terminal states controlled
  only by M02.
- PKG-008 must not update M02 intake, source, blob, checksum, duplicate,
  supersession, storage, or lifecycle data.
- Existing M02 download remains the only permitted byte-download behavior.
- `D-007-010_DEFERRED_NON_BLOCKING` remains unchanged and is neither fixed nor
  expanded by PKG-008.

For this bounded package, the locked decisions narrow the broader M03 planning
language without changing M02:

- `preserved` is M02 evidence context, not a persisted M03 review-revision
  state;
- `superseded` is an M02 lifecycle state and derived M03 exclusion reason, not
  an independently authored M03 review decision; and
- the planning row's additive-correction concept is bounded here to
  append-only `annotation` records with no typed corrected value or overwrite.

The dependency boundary remains:

`M01 -> M02 -> M03 -> separately authorized downstream transformation`

M04 is not opened or authorized by this definition.

## 4. Exact product outcome

After a separately authorized implementation, a user working in a non-archived
client case can explicitly start an append-only review for an eligible M02
uploaded source or manual record, accept or reject it with a reason, reopen a
terminal decision through a new review revision, add append-only annotations,
inspect immutable review and annotation history, and see a fail-closed
eligibility explanation.

Only a valid current `accepted` review decision may produce narrow technical
eligibility for a separately authorized downstream transformation.

Eligibility means only:

> Source-level or manual-record evidence has passed review and may be consumed
> by a separately authorized downstream transformation.

Eligibility does not mean parsed, normalized, classified, professionally
authoritative, financially authoritative, tax-authoritative,
calculation-ready, M04 accepted, or M05 ready.

## 5. Target-kind contract

The closed target-kind vocabulary is exactly:

- `source_evidence_review`;
- `manual_record_review`.

One M02 intake identifies one M03 review target. A target kind is derived and
validated by the backend from the M02 creation path and references; it is not
trusted merely because the caller supplies it.

### 5.1 Uploaded target

`source_evidence_review` references:

- the existing M02 intake;
- its existing M02 preserved source;
- the existing preserved blob and server-computed checksum provenance.

M03 stores references only. It does not duplicate raw bytes, storage keys,
source rows, blob rows, checksums, filenames, or other M02 provenance.

### 5.2 Manual target

`manual_record_review` references the existing M02 intake only. It has no
preserved source, blob, checksum, or fabricated external-evidence reference.
The M02 manual technical reference remains an operational identifier and is
not external evidence.

An uploaded/manual mismatch, missing uploaded provenance, unexpected manual
source/blob reference, or foreign-client reference fails closed.

## 6. Lifecycle and transition contract

Persisted review revision states are exactly:

- `under_review`;
- `accepted`;
- `rejected`.

Allowed actions are exactly:

| Current controlling revision | Action | New immutable revision |
|---|---|---|
| none | `start review` | `under_review` root |
| `under_review` | `accept` with reason | `accepted` child |
| `under_review` | `reject` with reason | `rejected` child |
| `accepted` | `reopen` with reason | `under_review` child |
| `rejected` | `reopen` with reason | `under_review` child |

`start review` is explicit. Candidate listing, target viewing, M02 transition
to `accepted_for_review`, page loading, download, or eligibility lookup must
not create a review.

Same-state actions, skipped actions, accept/reject without an open controlling
revision, reopening an open revision, and starting a second chain for the same
target are rejected with stable conflict responses.

## 7. Immutable revision contract

Every state-changing action creates one new immutable review revision.
Previously persisted revisions are never updated or deleted.

The review chain is a single linear chain per target:

- the first `under_review` revision is the root;
- each later revision references its immediate predecessor;
- one predecessor cannot have more than one successor;
- revision order is a server-assigned monotonic sequence scoped to the target;
- the current controlling revision is the unique leaf, not a caller-selected
  row and not a timestamp-only latest-wins guess;
- revision identity, sequence, actor/reviewer, and timestamp are server-owned;
- accepting or rejecting creates a terminal child and does not mutate the
  prior `under_review` row;
- reopening creates a new `under_review` child and does not mutate the prior
  terminal row.

The service and persistence transaction must prevent concurrent actions from
creating divergent leaves or more than one current open `under_review`
revision. A stale expected-current revision must fail rather than append to an
obsolete chain position.

## 8. Reopen contract

Reopen is permitted only from the current controlling `accepted` or `rejected`
revision and only while the M01 case is not archived.

Reopen requires:

- a non-empty reason;
- a server-owned operational actor/reviewer;
- a server-owned timestamp; and
- an immutable predecessor reference to the prior terminal revision.

The new controlling revision is `under_review`. The prior terminal decision
remains unchanged and visible. Eligibility becomes false immediately because
the controlling revision is no longer `accepted`.

Reopen is not correction, deletion, reversal in place, automatic
re-acceptance, M02 lifecycle mutation, or proof of a human authenticated
identity.

## 9. Annotation contract

The package uses the term `annotation`, not a general correction framework.

An annotation is an immutable append-only row containing:

- topic;
- note;
- reason;
- server-owned actor;
- server-owned timestamp;
- review revision reference;
- M02 intake reference;
- M02 source reference for uploaded targets;
- optional `supersedes_annotation_id`.

An annotation contains no typed corrected value, professional value,
classification, calculation input, eligibility override, or replacement
content. Old value is not required because no value is overwritten.

An annotation may supersede another annotation only by adding a new row that
references an existing same-client, same-target annotation. The earlier row
remains immutable and visible.

Annotations may be added after `accepted`, `rejected`, or M02 `superseded`
states when the case is not archived. An annotation:

- does not reopen review;
- does not alter any review decision;
- does not restore or remove eligibility;
- does not alter M02 lifecycle or metadata; and
- does not mutate raw source or blob evidence.

## 10. Eligibility contract

Eligibility is backend-derived, fail-closed, and evaluated from current
persisted state. It is never trusted from caller input and is not stored as a
caller-mutable boolean.

Eligibility is true only when all of the following hold:

1. the target belongs to the requested client;
2. the M02 intake remains `accepted_for_review`;
3. the unique current controlling review revision is `accepted`;
4. no newer `under_review` or `rejected` revision controls the chain;
5. for an uploaded target, intake/source/blob/checksum provenance is complete,
   internally consistent, and same-client;
6. the target is not M02 `rejected` or `superseded`; and
7. no foreign-client reference, broken chain, concurrency conflict, or
   lifecycle mismatch exists.

An eligibility response includes:

- target kind;
- review chain/current revision ID;
- accepted revision ID when currently accepted;
- reviewer/operational actor;
- decision timestamp;
- decision reason;
- M02 intake reference;
- M02 source/blob/checksum references only for uploaded targets;
- M02 lifecycle context;
- `eligible` as a derived response value; and
- a stable exclusion reason when not eligible.

No eligibility response may claim professional approval, source reliability,
financial correctness, tax authority, parsing, normalization, classification,
calculation readiness, or downstream execution authorization.

## 11. Manual-intake contract

Manual M02 intake must pass the same explicit M03 review lifecycle before a
future M04 package may consume it.

For `manual_record_review`:

- the M02 intake is the target and provenance anchor;
- there is no preserved source, blob, checksum, filename, or external evidence;
- the M02 manual technical reference is not evidence and must not be presented
  as such;
- candidate, detail, history, annotation, and eligibility responses omit
  uploaded-only provenance fields or return them as explicitly absent;
- eligibility can describe only the reviewed manual record; and
- no source/blob/checksum row may be invented to satisfy a common schema.

## 12. M02 interaction boundary

M03 never changes M02 lifecycle. In particular:

- M03 rejection does not set M02 to `rejected`;
- M03 acceptance does not alter M02 `accepted_for_review`;
- M03 reopen does not alter M02;
- annotations do not alter M02;
- source supersession remains exclusively an M02 action; and
- M03 cannot create, replace, delete, or relink an M02 source or blob.

If M02 later becomes `rejected` or `superseded`, M03 eligibility becomes false
while every M03 review revision and annotation remains retained. M03 may
display `superseded` as a derived M02 exclusion reason, but it cannot author
`superseded` as a review state or decision.

Reopening an M01 case does not alter review history and does not automatically
restore eligibility. Eligibility is re-derived from the unchanged review chain
and current M02 context.

## 13. Archived-case behavior

An archived M01 case is read-only for M03.

Allowed:

- view review candidates/targets;
- view review history;
- view annotations;
- view eligibility and exclusion explanations; and
- use existing M02 download behavior where already permitted.

Forbidden:

- start review;
- accept;
- reject;
- reopen;
- add annotation; and
- mutate or delete any M03 record.

The backend enforces archived read-only behavior. Hiding a frontend action is
not sufficient.

## 14. Backend/API boundary

After separate implementation authorization, the bounded client-scoped backend
surface may provide:

- list M02 targets eligible to be selected for M03 review;
- get one review target with current M02 context;
- explicitly start review;
- accept an open review with reason;
- reject an open review with reason;
- reopen a terminal review with reason;
- list immutable review history;
- add an annotation;
- list immutable annotation history; and
- derive and return eligibility/exclusion details.

Mutation requests may accept only the action inputs needed by the contract,
such as reason, annotation topic/note, an optional same-chain predecessor
expectation, and optional `supersedes_annotation_id`.

The caller cannot author or override:

- trusted client ownership;
- target kind without backend validation;
- reviewer/actor;
- timestamp;
- revision ID or sequence;
- review state or accepted decision outside the named action;
- current/controlling revision;
- eligibility;
- M02 lifecycle;
- source/blob/checksum provenance; or
- archived-case mutability.

Foreign, missing, or mismatched IDs return stable safe responses without
revealing whether a record exists for another client. Mutations are
transactional and leave no partial revision or annotation on failure.

## 15. Frontend/UI boundary

After separate implementation authorization, one bounded client-scoped M03 UI
may:

- list uploaded and manual review candidates with distinct presentation;
- show M02 context and uploaded provenance without duplicating it;
- show that manual targets have no external source/blob/checksum evidence;
- require an explicit `start review` action;
- show the current controlling revision and immutable history;
- collect a reason for accept, reject, and reopen;
- collect annotation topic, note, reason, and optional superseded annotation;
- show derived eligibility or a stable exclusion explanation;
- present archived cases as read-only; and
- invoke existing permitted M02 download behavior for uploaded sources.

The UI does not parse, normalize, preview as interpreted business content,
classify, create ledger entries, execute downstream transformations, or claim
professional authority. It does not generate trusted actor, timestamp,
revision, decision, provenance, or eligibility values.

## 16. Client isolation

Every candidate, target, revision, annotation, eligibility lookup, and mutation
is scoped by the route client ID and validated against explicit persisted
client ownership.

Required isolation includes:

- same-client validation across M01 case, M02 intake, M02 source/blob, M03
  revision predecessor, and annotation supersession references;
- no cross-client joins, candidate indications, counts, checksums, IDs, or
  timing assertions exposed to the caller;
- no mutation through a foreign target/revision/annotation ID;
- no foreign-ID existence leakage through status, message, or response shape;
  and
- no caller-supplied client field replacing route ownership.

## 17. Async and stale-response protection

The frontend must preserve the accepted `clientId + monotonic route-context
generation` guard for:

- candidate load;
- review detail/history load;
- annotation-history load;
- start review;
- accept;
- reject;
- reopen;
- annotation save;
- eligibility refresh;
- success;
- error; and
- `finally` state.

On A→B and A→B→A transitions, client-owned data, selection, history,
annotations, eligibility, errors, pending/loading state, and mutation state are
reset or rebound immediately. A stale response may not update the active
context, including when the route returns to the same numeric client ID with a
new generation. A new request in the revisited context must still complete.

## 18. Migration and persistence boundary

Implementation requires one additive Alembic successor above
`b6d8e2f4a701`. Migration execution is not authorized by this definition.

Preferred conceptual entities:

1. M03 review revisions.
2. M03 annotations.

Required review-revision persistence properties:

- server-generated immutable identity;
- explicit client ownership;
- closed target-kind discriminator;
- required M02 intake reference;
- optional M02 preserved-source reference required only for uploaded targets;
- immutable predecessor reference;
- server-assigned target-scoped revision sequence;
- exact persisted state;
- reason where required;
- server-owned actor/reviewer and timestamp;
- uniqueness preventing a second chain for the target;
- linear-chain/concurrency enforcement preventing divergent successors;
- deterministic unique controlling leaf; and
- indexes supporting client/target/history lookup.

Required annotation persistence properties:

- server-generated immutable identity;
- explicit client ownership;
- review revision and M02 intake references;
- uploaded-only optional source reference;
- topic, note, and reason;
- server-owned actor and timestamp;
- optional same-target superseded-annotation reference; and
- indexes supporting client/target/history lookup.

The migration must:

- be additive and preserve all prior rows;
- create no M03 review or annotation backfill;
- infer no review decision, actor, evidence, or eligibility;
- create no second Alembic head;
- enforce same-row structural checks and uniqueness where representable;
- upgrade and downgrade safely without altering M02 rows; and
- prefer no M02 schema change.

An M02 schema change is prohibited unless a later implementation investigation
proves a narrowly additive foreign-key support change unavoidable and the
approval gate accepts it. Destructive reuse, professional backfill, and direct
mutation of predecessor data are prohibited.

## 19. Security and caller-forgery boundaries

The application does not currently establish broad authenticated human-user
identity. A planner invokes the UI action, while the backend assigns the
server-controlled operational reviewer/actor using the existing technical
provenance convention.

That actor:

- is deterministic and server-owned;
- represents the M03 review workflow;
- is not accepted from browser text;
- is not authentication or authorization;
- is not proof of the physical person who acted; and
- is not professional approval or authority.

The backend, not the caller, controls identity, ownership, actor, timestamp,
revision sequencing, lifecycle validation, accepted/rejected decision
creation, provenance resolution, and eligibility derivation. Request payloads
attempting to forge those values are ignored where harmless or rejected with a
stable validation error.

No broad auth/role system, professional approval hierarchy, source-reliability
ranking, or downstream authorization is introduced.

## 20. Stop conditions

Future implementation must stop and return to the approval gate with the
applicable code if:

| Stop code | Condition |
|---|---|
| `M03_LIFECYCLE_CONTRACT_VIOLATION` | The exact states or transitions cannot be implemented without mutation, hidden transition, or additional state. |
| `M03_REVIEW_REVISION_IMMUTABILITY_BLOCKED` | A prior review revision would need update/deletion or a deterministic linear immutable chain cannot be enforced. |
| `M03_MANUAL_TARGET_CONTRACT_BLOCKED` | Manual review cannot remain intake-only without fabricated source/blob/checksum evidence. |
| `M03_ANNOTATION_AUTHORITY_EXPANSION` | Annotation would require typed correction, professional value, eligibility effect, or source/M02 mutation. |
| `M03_DOWNSTREAM_ELIGIBILITY_EXPANSION` | Eligibility would acquire parsing, classification, authority, calculation readiness, or downstream execution meaning. |
| `M03_M02_CONTRACT_CONFLICT` | Implementation would change M02 lifecycle, supersession, bytes, source, blob, checksum, metadata, or download ownership. |
| `M03_CLIENT_ISOLATION_BLOCKED` | Same-client constraints or A→B/A→B→A isolation cannot be preserved. |
| `M03_FOREIGN_ID_LEAKAGE_BLOCKED` | A foreign target/reference cannot fail without revealing existence or provenance. |
| `M03_CALLER_FORGED_EVIDENCE_BLOCKED` | The backend cannot prevent caller control of actor, timestamp, revision, decision, ownership, provenance, or eligibility. |
| `M03_MIGRATION_INTEGRITY_BLOCKED` | The migration cannot be additive above `b6d8e2f4a701`, preserve prior rows, and retain one head. |
| `M04_SCOPE_REQUIRED` | Classification, M04 eligibility/authority, or M04 implementation is required. |
| `PARSER_SCOPE_REQUIRED` | Parsing, extraction, normalization, parser schema, field location, or quarantine is required. |
| `PRIOR_PACKAGE_REGRESSION_BLOCKED` | Accepted M01, M02, PKG-005, PKG-006, or PKG-007 behavior cannot be preserved. |

Stop-condition count: `13`.

## 21. Acceptance criteria

| ID | Acceptance criterion |
|---|---|
| AC-008-001 | A client-scoped candidate list includes only M02 intakes currently eligible to be selected for M03 review and distinguishes `source_evidence_review` from `manual_record_review` without creating a review. |
| AC-008-002 | M02 transition to `accepted_for_review`, candidate loading, target viewing, eligibility lookup, and download create no M03 revision; only an explicit `start review` action creates the first `under_review` revision. |
| AC-008-003 | An uploaded target references the existing same-client intake, preserved source, blob, and checksum provenance without duplicating any raw byte, source, blob, checksum, filename, or storage record. |
| AC-008-004 | A manual target references only its same-client M02 intake, exposes uploaded provenance as absent, and never presents the manual technical reference as source/blob/checksum or external evidence. |
| AC-008-005 | Start, accept, reject, and reopen each append exactly one immutable revision in a deterministic linear chain with server-generated identity, sequence, actor/reviewer, and timestamp. |
| AC-008-006 | Accepting or rejecting requires a non-empty reason, creates a new terminal child revision, and leaves the prior `under_review` revision byte-for-byte unchanged and visible in history. |
| AC-008-007 | Reopening requires a reason, creates a new controlling `under_review` revision referencing the prior terminal revision, and leaves the accepted/rejected revision unchanged. |
| AC-008-008 | Transactional concurrency and stale-current checks prove that one target has one chain, one controlling leaf, and never more than one current open `under_review` revision. |
| AC-008-009 | Eligibility is false before review, while the controlling revision is `under_review`, after reopen, and after the latest controlling decision is `rejected`. |
| AC-008-010 | Eligibility is true only for the requested client when M02 remains `accepted_for_review`, the controlling revision is `accepted`, and all target-kind-specific provenance and chain invariants are valid. |
| AC-008-011 | An eligibility response contains the locked review, decision, intake, lifecycle, exclusion, and target-appropriate provenance fields while making only the narrow separately-authorized-downstream-transformation claim. |
| AC-008-012 | If M02 becomes `rejected` or `superseded`, eligibility becomes false with a derived exclusion reason while all M03 revisions and annotations remain retained and unchanged. |
| AC-008-013 | Adding or superseding an annotation appends an immutable same-client row with the locked fields and never reopens review, changes a decision, restores eligibility, or changes M02. |
| AC-008-014 | Accepted, rejected, and M02-superseded targets may receive historical annotations only while the M01 case is not archived; prior annotations remain visible. |
| AC-008-015 | Archived M01 cases allow the locked read/download operations and backend-reject start, accept, reject, reopen, annotation, update, and delete attempts without changing history or eligibility. |
| AC-008-016 | Every API and persistence operation validates route-client ownership across case, intake, uploaded provenance, revision chain, and annotation references; foreign or mismatched IDs fail without existence leakage or partial writes. |
| AC-008-017 | Caller attempts to provide or override client ownership, actor/reviewer, timestamp, revision identity/sequence, current revision, decision state, eligibility, or source/blob/checksum provenance do not control persisted or derived evidence. |
| AC-008-018 | Frontend A→B and A→B→A tests prove immediate reset and generation-guarded candidate/detail/history/annotation/eligibility reads plus start/accept/reject/reopen/annotation success, error, and `finally` behavior; stale responses cannot affect the active context and new-context requests still work. |
| AC-008-019 | The UI provides explicit start, reasoned accept/reject/reopen, annotation, immutable history, target-kind distinction, archived read-only, and eligibility/exclusion presentation using real backend state without authority inflation. |
| AC-008-020 | Tests prove no M02 intake/source/blob/checksum/lifecycle/download mutation, no automatic M02 supersession, and no regression to accepted M01, PKG-005, PKG-006, or PKG-007 behavior. |
| AC-008-021 | The additive migration upgrades from `b6d8e2f4a701`, adds only the bounded M03 revision/annotation persistence and constraints, performs no inferred backfill or M02 rewrite, downgrades safely, and leaves one Alembic head. |
| AC-008-022 | Focused backend/frontend, migration, concurrency, isolation, forgery, archived, eligibility, predecessor-regression, full-suite, build/type-check, Python compile, Alembic single-head, and `git diff --check` verification all pass without parser, normalization, classification, ledger, calculation, or downstream execution behavior. |

Acceptance criteria count: `22`.

## 22. Negative acceptance criteria

| ID | Prohibited outcome |
|---|---|
| NAC-008-001 | Automatic review creation from M02 `accepted_for_review`, candidate/detail load, eligibility lookup, download, page load, or any action other than explicit `start review`. |
| NAC-008-002 | Direct state mutation, same-state transition, skipped transition, caller-authored state, or update/delete of an existing review revision. |
| NAC-008-003 | Updating an accepted or rejected revision during reopen, correction, annotation, M02 lifecycle change, or later review activity. |
| NAC-008-004 | More than one review chain, divergent successors, more than one controlling leaf, or more than one current open `under_review` revision for a target. |
| NAC-008-005 | A typed corrected value, old-value requirement, professional value, classification, calculation input, authority decision, or general correction framework inside an annotation. |
| NAC-008-006 | Treating a manual technical reference as external evidence or inventing a preserved source, blob, checksum, filename, or uploaded provenance for a manual target. |
| NAC-008-007 | Treating eligibility as parsed, normalized, classified, professionally/financially/tax authoritative, calculation-ready, M04 accepted, M05 ready, or authorization to execute downstream work. |
| NAC-008-008 | XML/DAT/CSV/XLSX/PDF parsing, extraction, normalization, schema interpretation, field-level raw location, item-level review, quarantine, malware workflow, or normalized output. |
| NAC-008-009 | M04 classification, M05 ledger creation, conversion, tax/fixation calculation, scenario work, or any downstream mutation or execution. |
| NAC-008-010 | M03-authored M02 rejection or supersession, automatic supersession, or mutation of M02 lifecycle, metadata, intake, source, blob, checksum, bytes, storage, duplicate, or download behavior. |
| NAC-008-011 | Raw-byte mutation, source replacement, physical deletion, destructive correction, duplicate evidence storage, or ordinary UI/API deletion. |
| NAC-008-012 | Caller-forged ownership, reviewer/actor, timestamp, revision identity/sequence, accepted/rejected evidence, current revision, eligibility, M02 context, or source/blob/checksum provenance. |
| NAC-008-013 | Foreign-client read/write, cross-client reference, checksum/provenance disclosure, target-count disclosure, or differing response that leaks foreign-ID existence. |
| NAC-008-014 | An annotation reopening review, altering a decision, restoring eligibility, changing M02 lifecycle, or mutating another annotation. |
| NAC-008-015 | Mutation of M03 records while the M01 case is archived, or automatic review/eligibility change merely because the case is reopened. |
| NAC-008-016 | Stale A→B or A→B→A read, mutation, success, error, loading, pending, selection, eligibility, or `finally` state altering the active client context. |
| NAC-008-017 | Broad authentication/roles, professional approval hierarchy, production retention/redaction workflow, parser, M04, M05, M09–M14, or 02M scope. |
| NAC-008-018 | Claiming M03 completion, production readiness, full M08 readiness/completion, another-package authorization, downstream authority, or V1/V2 parity. |

Negative acceptance criteria count: `18`.

## 23. Verification matrix

| Verification area | Required proof | Criteria |
|---|---|---|
| Candidate/start boundary | Candidate visibility, explicit start, no automatic rows | AC-008-001–002; NAC-008-001 |
| Target kinds and provenance | Uploaded joins existing provenance; manual has none | AC-008-003–004; NAC-008-006 |
| Immutable lifecycle | Linear append-only chain, reasons, terminal preservation, reopen | AC-008-005–008; NAC-008-002–004 |
| Eligibility | Fail-closed truth table, response shape, M02 rejection/supersession exclusion | AC-008-009–012; NAC-008-007 |
| Annotations | Append-only history and no decision/eligibility effect | AC-008-013–014; NAC-008-005, NAC-008-014 |
| Archived behavior | Read-only backend and UI, unchanged history after reopen | AC-008-015; NAC-008-015 |
| Client/API security | Same-client constraints, foreign-ID non-disclosure, forgery rejection | AC-008-016–017; NAC-008-012–013 |
| Frontend isolation | Deferred-promise A→B and A→B→A across every protected path | AC-008-018–019; NAC-008-016 |
| Predecessor preservation | M02 and prior packages unchanged | AC-008-020; NAC-008-010–011 |
| Migration | Upgrade/downgrade, constraints, concurrency, row preservation, one head | AC-008-021 |
| Scope negatives | No parser, normalized output, M04/M05/downstream behavior | AC-008-022; NAC-008-008–009, NAC-008-017–018 |
| Repository regression | Focused/full backend and frontend, build, compile, Alembic, diff check | AC-008-022 |

Browser E2E, CI, deployment, and production verification may be claimed only
if separately available and actually executed.

## 24. Explicit deferred and excluded scope

Deferred beyond this bounded foundation:

- parser and parser schema;
- extraction and normalized import;
- field-level raw location;
- item-level or field-level review;
- quarantine and malware workflow;
- M04 classification;
- M05 ledger;
- conversion;
- tax/fixation logic;
- professional approval hierarchy;
- broad authentication and roles;
- production retention, redaction, and exceptional deletion policy;
- object-storage or production-storage changes; and
- downstream execution.

Explicitly excluded:

- raw byte mutation, source replacement, or physical deletion;
- M02 lifecycle mutation or M02 supersession action;
- automatic review creation or automatic acceptance;
- caller-forged reviewer, timestamp, decision, provenance, or eligibility;
- technical-reference-as-evidence;
- typed correction or professional-value framework;
- parser, normalization, classification, ledger, conversion, or calculation;
- M04, M05, or M09–M14 authorization;
- 02M change;
- production-readiness or M03-complete claim; and
- V1/V2 parity claim.

No unresolved product decision blocks definition review. Exact table, column,
index, constraint, route, component, and technical-actor code names may follow
existing repository conventions during a separately authorized implementation,
provided they preserve every contract in this definition. Production
authentication, retention/redaction, and downstream transformation behavior
remain separately deferred decisions.

## 25. Authorization boundary

This definition draft authorizes no implementation activity.

- Definition: `DRAFT_PENDING_GATE_REVIEW`
- Implementation: `NOT_AUTHORIZED`
- Migration execution: `NOT_AUTHORIZED`
- Parser/normalization: `NOT_AUTHORIZED`
- M04: `NOT_AUTHORIZED`
- Downstream execution: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`

No acceptance record is created by this draft. A separate definition gate must
accept or return this contract before any implementation authorization may be
considered.

## 26. Final package gate

`PKG_008_DEFINITION_DRAFT_READY_FOR_GATE_REVIEW`

This gate means only that the draft is ready for product/architecture review.
It is not `READY_FOR_IMPLEMENTATION`, does not authorize migration execution,
and does not open M04 or another package.
