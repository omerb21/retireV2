# PKG-009 — M04 Evidence-Backed Asset and Component Classification Decisions

## 1. Identity and status

| Field | Value |
|---|---|
| Package | `PKG-009 — M04 Evidence-Backed Asset and Component Classification Decisions` |
| Module | `M04` |
| Definition status | `DRAFT_PENDING_GATE_REVIEW` |
| Implementation | `NOT_AUTHORIZED` |
| Migration execution | `NOT_AUTHORIZED` |
| M05 | `NOT_AUTHORIZED` |
| Acceptance record | `NOT_CREATED` |
| Authoritative base | `4233ea87e887dd895eb0497f46e05df9cf6e8ea0` |
| Predecessor implementation | PKG-008 at `3abfc010e6f8803c9f22f50925e0e6f8443fc4d1` |
| Predecessor migration | `e4a7c3d9b802` |

This document defines a bounded M04 package. It does not authorize source-code
changes, migration execution, M05 work, or implementation acceptance.

## 2. Authoritative sources

The authoritative sources for this package are:

1. `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`;
2. the accepted PKG-008 definition,
   `specs/runtime/PKG_008_FINAL_PACKAGE_DEFINITION.md`;
3. the accepted PKG-008 implementation record,
   `specs/runtime/PKG_008_acceptance_record.md`;
4. the accepted M01, M02, and M03 repository contracts on the authoritative
   base; and
5. the product and architecture decisions locked in this definition.

Where an implementation detail is not fixed here, a later implementation may
follow existing repository conventions only if it preserves every contract in
this document. It may not invent a professional, tax, pension, calculation, or
source-authority rule.

## 3. Predecessor contracts

PKG-009 consumes M03 as a read-only predecessor authority. It preserves:

- M01 case ownership, lifecycle, archive behavior, and client isolation;
- M02 intake identity, target kind, lifecycle, preserved-source provenance,
  opaque bytes, blob/checksum ownership, and supersession ownership;
- M03 immutable review history, annotations, accepted-review identity, and
  derived downstream-evidence eligibility;
- foreign-ID non-disclosure and same-client validation;
- append-only history and server-controlled provenance; and
- the accepted frontend `clientId + monotonic route-context generation`
  protection.

M04 never mutates M02 or M03. M02/M03 rejected or superseded state excludes
downstream eligibility without rewriting any M04 revision.

## 4. Exact product outcome

PKG-009 creates explainable, immutable, and versioned M04 classification
decisions for an M03-eligible manual or uploaded target.

The decision model separates:

- product family at asset level;
- component classification;
- component pension/capital interpretation;
- derived aggregate interpretation;
- lifecycle and explicit planner acceptance;
- exact matched-rule evidence; and
- source and M03 provenance.

Only a current, explicitly accepted, fully resolved classification may create
narrow, derived eligibility for a separately authorized M05 package.

PKG-009 does not create a parser, normalized source facts, a balance ledger,
reconciliation, conversion, tax treatment, fixation, exemption, formal 161D
logic, liquidity or withdrawal conclusions, scenarios, or recommendations.

## 5. Classification and taxonomy contract

Classification uses a bounded parent-asset plus component-decision model. One
flat enum may not combine product family, severance/contribution component
meaning, and pension/capital interpretation.

### 5.1 Asset-level decision

An asset-level decision contains:

- `product_family`;
- an optional pension-fund subtype/regime only when explicitly evidenced;
- a derived aggregate pension/capital interpretation;
- lifecycle;
- explanation;
- matched-rule evidence; and
- M03 provenance.

The bounded product-family vocabulary is exactly:

- `insurance_policy`;
- `savings_policy`;
- `provident_fund`;
- `investment_provident_fund`;
- `education_fund`;
- `pension_fund`; and
- `unknown_or_unresolved`.

Severance and contribution components are not product families.
`old_pension_fund` and `new_pension_fund` are not inferred or introduced as
top-level families. A neutral optional subtype remains unresolved unless exact
approved evidence supports it.

### 5.2 Component-level decision

Each component decision contains:

- a stable component evidence identity;
- the immutable original component label/code;
- `component_kind`;
- a separate pension/capital interpretation;
- matched-rule evidence; and
- an explanation.

The bounded first-stage component-kind vocabulary is:

- `severance_component`;
- `contribution_component`; and
- `unknown_component`.

`contribution_component` represents תגמולים. The term
`compensation_component` is prohibited. Finer V1 distinctions may be
preserved as original labels and rule evidence, but do not expand the
authoritative component enum without an explicit accepted mapping.

### 5.3 Interpretation axis

The separate interpretation vocabulary is:

- `pension`;
- `capital`;
- `mixed`; and
- `unresolved`.

Individual components are normally `pension`, `capital`, or `unresolved`.
Asset-level `mixed` is derived only when resolved component decisions have
materially different interpretations. Product family may be resolved while a
required component interpretation remains unresolved. Any required unresolved
interpretation blocks M05 eligibility. These values create no tax, exemption,
liquidity, withdrawal, or professional-authority conclusion.

## 6. Input and target contract

The stable M04 classification subject is keyed semantically by:

- `client_id`;
- `intake_id`; and
- `target_kind`.

A separate physical subject table is optional. Subject semantics are not.
Target kind is reused unchanged from M03.

### 6.1 Uploaded target

M03 does not parse uploaded bytes. An uploaded target without explicitly
persisted structured classification facts remains unresolved.

Filename, MIME type, checksum, blob identity, storage metadata, and
provider-like filename text are provenance or technical metadata, not
classification evidence. PKG-009 does not add a parser, normalized-import
model, or new professional source-fact intake channel.

### 6.2 Manual target

A manual target may consume only explicitly persisted M02 declared metadata.
Its technical reference is not account, product, or external evidence. It has
no fabricated source/blob/checksum meaning. Missing required facts remain
unresolved.

## 7. Exact-rule catalogue contract

The rule model is:

`static versioned exact-rule catalogue + manual unresolved workflow`

Rules are deterministic, exact, immutable within a catalogue version,
server-resolved, evidence-traceable, and incapable of automatic professional
acceptance.

Each rule preserves:

- catalogue version;
- rule ID;
- matcher type;
- exact matcher value;
- provider/source-format scope where required;
- output product family or component decision;
- output interpretation only where explicitly evidenced;
- rationale;
- V1 source citation or approved-decision reference; and
- conflict behavior.

The initial technical rule-catalogue version is exactly `m04-rules-v1`.
Implementation may not select another initial identifier. It is an immutable
technical identifier only, not a legal, tax, pension, or
professional-authority version.

Every preview reports the catalogue version used. Every persisted proposal and
revision references the exact catalogue version used to produce or assess it,
and historical revisions retain their original catalogue version. A future
catalogue version requires a separately controlled version change; it does not
rewrite historical rule identity. PKG-009 introduces neither rule effective
dates nor database-administered catalogue scope.

Provider-only fallback, partial-name fallback, fuzzy matching, scoring,
latest-wins behavior, and unapproved global precedence are prohibited.
Component rules classify only the component unless a separate exact
asset-level rule applies. Conflicting exact rules produce unresolved output.

## 8. Proposal and explicit acceptance contract

Exact-rule execution may produce only `proposed`; it may never produce
authoritative `accepted` automatically. Explicit planner action is required to
create an accepted successor.

A proposal preserves:

- the immutable input snapshot;
- catalogue version;
- exact matched rule IDs;
- explanations; and
- unresolved conflicts.

Preview is non-persisting. Persisting a proposal is an explicit lifecycle
operation and creates a new immutable revision.

## 9. Lifecycle and transition contract

Persisted lifecycle states are exactly:

- `under_review`;
- `proposed`;
- `accepted`;
- `unresolved`; and
- `rejected`.

Allowed transitions are:

- no chain → explicit start → new `under_review`;
- `under_review` → exact proposal → new child `proposed`;
- `under_review` → unresolved decision → new child `unresolved`;
- `proposed` → explicit accept → new child `accepted`;
- `proposed` → reject → new child `rejected`;
- `unresolved` → reopen → new child `under_review`;
- `accepted` → reopen → new child `under_review`;
- `rejected` → reopen → new child `under_review`;
- `proposed`, `accepted`, `unresolved`, or `rejected` → override → new child
  `proposed`;
- `proposed`, `accepted`, `unresolved`, or `rejected` → undo → new child
  `proposed`; and
- active case after a prior archived period, with a historical leaf of
  `accepted`, `unresolved`, or `rejected` → `start_revalidation` → new child
  `under_review`.

Override and undo are prohibited from no chain and from `under_review`.
`start_revalidation` is allowed only when current M03 eligibility is true and
the target remains same-client and same-target. An override, undo, or
revalidation never creates `accepted` directly. Each must follow the ordinary
proposal and explicit-acceptance lifecycle applicable to its resulting state.

No previous revision is updated or deleted. Source/M03 supersession is a
derived predecessor exclusion. Historical M04 supersession is derived from a
successor in the chain, not authored by rewriting the prior revision.

## 10. Immutable revision and input-snapshot contract

Every state-changing action appends one revision. Each persisted revision
preserves an immutable snapshot of only the facts present at decision time:

- target kind;
- client and intake identity;
- accepted M03 revision identity;
- M03 eligibility context;
- explicitly persisted provider name;
- explicitly persisted product name/type/code;
- explicitly persisted account/reference identifier;
- explicitly persisted component labels/codes/values;
- statement date when available; and
- original source/provenance links.

Raw bytes and checksum content are not duplicated unnecessarily. Missing
product facts are not inferred.

Stored M03 eligibility context is decision-time evidence only. It may include
the accepted M03 revision ID, an evaluated-at server timestamp, target/intake
identity, M03 lifecycle references, the eligibility or exclusion basis
evaluated at that moment, and provenance references. It is not persisted
current eligibility authority, is not a boolean trusted indefinitely, and
never permits current server-side M03 revalidation to be skipped. Every
authoritative M04 read or mutation and every M05 eligibility calculation
re-derives current M03 eligibility.

Revision history is linear, server-sequenced, same-client, same-target, and has
one deterministic current leaf. A predecessor has at most one child.

## 11. Reopen, override, undo, and revalidation contract

Reopen creates a new `under_review` successor and preserves every prior
revision. It creates no proposed classification.

Override is allowed only when the current source state is `proposed`,
`accepted`, `unresolved`, or `rejected`; it is prohibited from no chain and
from `under_review`. It creates exactly one planner-authored immutable
successor in state `proposed` and requires:

- previous classification revision;
- complete old and new asset axes;
- old and new component decisions;
- structured reason code;
- non-empty explanation;
- server actor and timestamp;
- server identity and sequence;
- original input snapshot;
- prior matched-rule evidence;
- an explicit indication that the proposal is planner-authored override
  evidence;
- same-client and same-target validation; and
- explicit confirmation.

An override may resolve an unresolved decision. It may not edit M02/M03,
create new source evidence, delete or conceal prior decisions, or create
`mixed` without supporting resolved component decisions.

An override from `accepted` makes that accepted revision historical and
non-current as soon as the proposed successor is appended. M05 eligibility is
therefore false while the override proposal is current. The proposal requires
explicit planner acceptance; only `proposed` → `accepted` may restore
eligibility. Rejecting it creates a new `rejected` successor and does not
restore the old authority. Returning to the prior classification requires
another additive successor.

Undo is an additive planner-authored reversal proposal. It is allowed only
when the current source state is `proposed`, `accepted`, `unresolved`, or
`rejected`; it is prohibited from no chain and from `under_review`. Undo
creates exactly one successor in state `proposed` that:

- identifies the historical revision whose classification values are proposed
  again;
- copies only those classification values into the new proposal;
- retains the current and selected historical revisions;
- records a structured reason and non-empty explanation;
- uses a fresh server-owned ID, sequence, actor, and timestamp;
- preserves complete audit history; and
- requires explicit confirmation.

Undo never moves the current pointer backward, deletes the current revision,
reactivates an old accepted revision, creates immediate `accepted`, or restores
M05 eligibility without explicit acceptance. Its proposal follows only
`proposed` → explicit accept → `accepted` or `proposed` → reject →
`rejected`.

`start_revalidation` is a fourth, distinct action. It is allowed only when:

- M01 is active after a prior archived period;
- a historical M04 chain exists;
- the current historical leaf is `accepted`, `unresolved`, or `rejected`;
- current M03 eligibility is true; and
- the target remains same-client and same-target.

It creates exactly one `under_review` child referencing the prior leaf,
captures a fresh immutable input snapshot, resolves the current accepted M03
revision, captures the current catalogue version, and retains prior
classification and rule evidence as historical context only. It does not copy
old acceptance authority and cannot make M05 eligibility true.

After `start_revalidation`, only the ordinary lifecycle applies:
`under_review` → exact-rule proposal → `proposed`, or `under_review` →
insufficient/conflicting evidence → `unresolved`; a proposal then proceeds
only to explicit planner `accepted` or `rejected`. There is no direct
revalidation-to-accepted, archive-reopen-to-accepted, or old-accepted-revision
eligibility restoration.

Reopen, override, undo, and `start_revalidation` are distinct in API, UI,
audit evidence, and tests.

## 12. Confidence and ancillary-metadata boundary

Confidence is omitted from the authoritative contract. Classification uses
`match_basis`, exact rule evidence, explanation, and unresolved/conflict
status. Any future display-only confidence requires a separate accepted
decision and must remain informational, server-derived, threshold-free, and
incapable of enabling M05.

`current_employer_related` may be included only as component-level or
evidence-linked metadata with values `yes`, `no`, or `unknown`. It requires
explicit persisted evidence, remains `unknown` otherwise, and never implies
employment termination, severance availability, liquidity, withdrawal, or tax
eligibility.

Generic `blocked_or_restricted` authority and tax-relevance/tax-treatment
metadata are deferred.

## 13. M03 reuse and M02 interaction boundary

Every authoritative M04 read or mutation:

1. reuses target kind and intake identity unchanged;
2. resolves the accepted M03 review revision server-side;
3. revalidates current M03 eligibility;
4. validates the requested client;
5. treats preserved-source identity only as provenance;
6. treats blob/checksum as carrying no classification meaning;
7. does not use M03 actor, reason, or annotations as classification rules; and
8. never mutates M02 or M03.

M02/M03 rejection or supersession makes M05 eligibility false while retaining
all M04 history.

## 14. Derived M05 eligibility contract

`eligible_for_m05` is derived at read time, server-controlled, fail-closed,
and never accepted from caller input or persisted as caller authority.

It is true only when all of the following hold:

1. the M01 case is active and not archived;
2. current M03 eligibility is true;
3. the target belongs to the requested client;
4. the M04 chain is valid and linear;
5. the current leaf is `accepted`;
6. product family is resolved;
7. every required component decision is resolved;
8. aggregate interpretation is resolved;
9. no material conflict exists;
10. no newer M04 revision exists;
11. source/intake is not rejected or superseded; and
12. snapshot, catalogue version, and matched-rule evidence are valid.

It is false for no decision, `under_review`, `proposed`, `unresolved`,
`rejected`, opaque uploaded facts, M03 ineligibility, rejected/superseded
source or intake, malformed chain, missing/incompatible rule evidence,
unresolved required component meaning, archived case, or foreign/inconsistent
provenance. The response supplies stable exclusion reasons.

When an override or undo proposal succeeds an accepted leaf, eligibility is
false until that current proposal is explicitly accepted. Rejection never
restores the prior accepted authority.

Eligibility means only that the accepted, resolved M04 classification may be
consumed by a separately authorized M05 package. It does not mean reconciled,
ledger-created, tax-ready, calculation-ready, liquid, withdrawable,
pension-start eligible, or fixation eligible.

After an archived case is reopened, eligibility is not restored automatically.
The stable exclusion reason is `m04_revalidation_required` while no
`start_revalidation` successor exists or while the revalidation chain is
`under_review`, `proposed`, `unresolved`, or `rejected`.

Post-reopen eligibility may become true only when a post-reopen revalidation
chain exists, its current leaf was explicitly accepted, its input snapshot was
refreshed, current M03 revision and eligibility remain valid, current
catalogue/rule evidence remains valid, and every ordinary M05 eligibility
condition holds. Eligibility remains derived rather than persisted authority.

## 15. Persistence and integrity model

The bounded persistence model consists of:

1. a classification revision; and
2. component decisions owned by that revision.

Classification revisions require:

- server-generated identity and target-scoped sequence;
- explicit client ownership and stable subject identity;
- predecessor with at most one child;
- deterministic current leaf;
- same-client and same-target relationships;
- immutable input snapshot and matched-rule evidence;
- lifecycle, product family, optional pension subtype, aggregate
  interpretation, explanation/reason, and catalogue version;
- the exact catalogue version used by every proposal/revision, retained on
  historical revisions without rewrite;
- the action kind needed to distinguish start, reopen, override, undo, and
  `start_revalidation`, including planner-authored proposal evidence;
- server actor and timestamp; and
- append-only storage.

Component decisions require revision ownership, stable evidence identity,
original label/code, component kind, component interpretation, matched-rule
evidence, explanation, and revision-local uniqueness.

Ordinary ORM update/delete paths are blocked. Corrupted, inconsistent, or
incomplete stored evidence makes M05 eligibility false.

Required protection layers are:

- database constraints for structural ownership, uniqueness, linear-history
  invariants representable in DDL, and component attachment;
- ORM insert/update/delete guards for immutable entities;
- service validation for lifecycle, current leaf, same-client/same-target
  references, server-owned evidence, catalogue compatibility, and concurrency;
  and
- fail-closed eligibility derivation that rejects malformed or forged stored
  evidence, including corruption introduced outside ordinary ORM paths.

## 16. Backend and API boundary

The minimum client-scoped API capability is:

- list M03-eligible or historically classified targets;
- get target detail and immutable classification history;
- preview exact-rule matches without persistence;
- explicitly start classification;
- explicitly `start_revalidation` after archive reopen;
- create a proposed revision;
- mark unresolved;
- accept the current proposal;
- reject;
- reopen without proposed values;
- create a planner-authored override proposal;
- create a planner-authored undo proposal;
- get matched-rule evidence; and
- get derived M05 eligibility.

The caller cannot supply trusted client ownership, M03 eligibility, accepted
M03 revision, source provenance, input-snapshot provenance, catalogue version,
rule match, actor, timestamp, identity, sequence, predecessor/current pointer,
accepted authority, or M05 eligibility.

Structured failures cover resource unavailable, foreign/missing ID, M03
ineligible, incomplete evidence, uploaded facts unavailable, exact mapping
conflict, no exact rule, stale revision, invalid transition, archived mutation,
cross-target reference, catalogue incompatibility, and concurrent leaf
conflict. Preview responses report the exact catalogue version. Revalidation,
reopen, override, and undo are distinct operations and return their resulting
revision identity, lifecycle state, predecessor, and server-owned evidence.

## 17. Frontend and planner workflow boundary

The bounded planner UI supports:

- candidate and historical-target lists;
- manual/uploaded distinction;
- original persisted labels and identifiers;
- M02/M03 provenance and M03 eligibility/exclusion;
- product-family proposal, component decisions, and aggregate interpretation;
- exact matched-rule explanations and unresolved/conflict warnings;
- explicit start, preview, accept, reject, reopen, override, undo, and
  `start_revalidation`, with each action presented distinctly;
- immutable history;
- M05 eligibility/exclusion explanation; and
- archived read-only presentation.

It does not include parser preview, a raw XML/normalized editor, ledger,
reconciliation, conversion, tax, fixation, or scenarios. Browser values never
become trusted rule evidence, acceptance authority, provenance, actor,
timestamp, identity, lifecycle pointer, or eligibility.

## 18. Client isolation and async protection

Every route validates same-client ownership across case, M02 intake, M03
review, M04 subject, revision, predecessor, component, and rule evidence.
Foreign and missing IDs have identical public responses and reveal no
existence, count, identifier, provenance, or timing distinction.

All frontend reads, mutations, and follow-up refreshes capture `clientId` and a
monotonic route-context generation. Deterministic tests cover A→B, A→B→A,
stale success, rejected promise, structured API error, stale `finally`, and
zero stale follow-up refresh. Stale responses cannot change active data,
selection, history, proposals, eligibility, errors, loading, pending, success,
or mutation state.

## 19. Archived-case behavior

Archived M01 cases permit candidate/history reads where applicable, target
detail, revision history, rule evidence, provenance, and M05 exclusion
explanation.

They prohibit start, proposal persistence, unresolved decision, accept,
reject, reopen, override, undo, `start_revalidation`, and any persisted rule
execution. Archiving creates no successor, changes no M04 revision, leaves any
accepted classification historical, and sets `eligible_for_m05=false` with an
archived/revalidation-required exclusion.

Reopening M01 creates no M04 revision, changes no history, does not reactivate
the prior accepted revision, and leaves eligibility false with
`m04_revalidation_required`. Only the explicit `start_revalidation` contract
in section 11 can begin post-reopen review, and it is available only after the
case is active again. Successful revalidation requires the refreshed
`under_review` → `proposed` → explicitly `accepted` sequence; no archive or
reopen event itself restores authority.

## 20. Migration boundary

Migration is `REQUIRED` for a later separately authorized implementation. It
must be additive above `e4a7c3d9b802`.

The migration must:

- create one new Alembic revision and leave one Alembic head;
- add only bounded PKG-009 objects and required structural indexes/uniqueness;
- support linear revision history and component ownership;
- preserve all prior rows;
- perform no M02/M03 mutation, classification backfill, or professional
  inference;
- pass a SQLite upgrade/downgrade/upgrade cycle;
- remain compatible with PostgreSQL DDL; and
- remove only PKG-009 objects on downgrade.

This definition does not assign the future Alembic revision ID and does not
authorize migration creation or execution.

## 21. Stop conditions

Future implementation must stop and return to the approval gate if:

| Stop code | Condition |
|---|---|
| `M04_EXACT_RULE_EVIDENCE_BLOCKED` | An exact rule lacks an approved V1 citation or accepted decision reference. |
| `M04_TAXONOMY_AXIS_VIOLATION` | Product family, component kind, and interpretation cannot remain separate axes. |
| `M04_COMPONENT_TO_ASSET_INFERENCE_BLOCKED` | Component evidence would be used to classify an asset without a separate exact asset rule. |
| `M04_HEURISTIC_RULE_SCOPE_REQUIRED` | Provider-only, partial, fuzzy, scored, latest-wins, or unapproved global precedence is required. |
| `M04_RULE_PROOF_INTEGRITY_BLOCKED` | Catalogue version, exact rule identity, rationale, or matched-rule evidence cannot be preserved immutably. |
| `PARSER_OR_NORMALIZED_FACTS_REQUIRED` | Parsing, extraction, normalization, or a new professional source-fact channel is required. |
| `M04_M02_M03_MUTATION_REQUIRED` | Implementation requires changing M02/M03 data, lifecycle, evidence, source, or authority. |
| `M05_LEDGER_OR_RECONCILIATION_REQUIRED` | A ledger, balance reconciliation, conversion, or downstream execution is required. |
| `TAX_OR_FIXATION_SCOPE_REQUIRED` | Tax, exemption, fixation, 161D, liquidity, or withdrawal meaning is required. |
| `M04_REVISION_INTEGRITY_BLOCKED` | Append-only linear history, deterministic leaf, component ownership, distinct reopen/override/undo/revalidation actions, explicit-acceptance sequencing, or fail-closed corruption handling cannot be enforced. |
| `M04_CALLER_FORGED_AUTHORITY_BLOCKED` | Caller control of acceptance, rule evidence, actor, timestamp, ownership, provenance, or eligibility cannot be prevented. |
| `M04_MIGRATION_INTEGRITY_BLOCKED` | An additive single-head migration above `e4a7c3d9b802` cannot preserve predecessor data and constraints. |
| `PRIOR_PACKAGE_REGRESSION_BLOCKED` | Accepted M01-M03 or PKG-001 through PKG-008 behavior cannot be preserved. |
| `M04_OPAQUE_UPLOAD_CLASSIFICATION_BLOCKED` | An opaque uploaded target would be classified without approved persisted structured evidence. |

Stop-condition count: `14`.

## 22. Acceptance criteria

| ID | Acceptance criterion |
|---|---|
| AC-009-001 | Every authoritative candidate/detail/preview/mutation/eligibility operation revalidates the current accepted M03 review revision and current M03 eligibility; an ineligible target cannot start or advance M04. |
| AC-009-002 | Uploaded targets retain same-client M02 source/blob/checksum only as provenance, while manual targets retain intake-only provenance and expose no fabricated external source/blob/checksum evidence. |
| AC-009-003 | Every revision and component decision preserves the original persisted product/component labels, codes, identifiers, and decision-time snapshot unchanged and auditable. |
| AC-009-004 | An uploaded target without approved persisted structured classification facts remains `unresolved`; filename, MIME, blob, checksum, storage metadata, and provider-like filename text cannot resolve it. |
| AC-009-005 | Asset product family and component kind are stored and presented as separate bounded decisions; component evidence cannot classify the parent asset without a separate exact asset rule. |
| AC-009-006 | Component pension/capital interpretation is a separate axis from product family and component kind, and any required `unresolved` interpretation blocks M05 eligibility. |
| AC-009-007 | Asset-level `mixed` is derived only from resolved component decisions with materially different `pension` and `capital` interpretations and cannot be directly asserted without that support. |
| AC-009-008 | Every preview reports and every persisted proposal/revision immutably retains the exact catalogue and matched-rule identity used; the initial catalogue identifier is exactly `m04-rules-v1`, cannot be substituted by implementation, and carries no legal, tax, pension, or professional-authority meaning. |
| AC-009-009 | Every matched rule exposes its exact matcher, scope, output, rationale, V1 citation or approved-decision reference, conflict behavior, and reader-facing explanation. |
| AC-009-010 | Deterministic tests prove no provider-only, partial-name, fuzzy, scored, latest-wins, threshold, or unapproved global-precedence fallback can produce a proposal. |
| AC-009-011 | Conflicting exact rules produce an explicit unresolved/conflict result with retained evidence and never silently select a classification. |
| AC-009-012 | Exact-rule execution may create only a `proposed` successor; it never creates `accepted`, and list/detail/preview/M03 eligibility never creates a revision automatically. |
| AC-009-013 | Only an explicit planner accept action against the current `proposed` leaf creates an `accepted` successor after server-side lifecycle, M03, client, catalogue, and stale-leaf validation. |
| AC-009-014 | Override and undo are accepted only from a current `proposed`, `accepted`, `unresolved`, or `rejected` leaf, never from no chain or `under_review`; each appends exactly one planner-authored `proposed` successor, leaves the accepted/prior revisions unchanged, makes eligibility false, and requires explicit `proposed` → `accepted` before authority may return. |
| AC-009-015 | Reopening `accepted`, `rejected`, or `unresolved` creates a new controlling `under_review` successor and never edits the terminal revision or restores M05 eligibility automatically. |
| AC-009-016 | Reopen appends `under_review` without proposed values; override appends changed values as `proposed`; undo appends historical values as a new `proposed`; and `start_revalidation` appends refreshed-snapshot `under_review`; each is distinct, append-only, server-provenanced, and cannot bypass the applicable proposal plus explicit-acceptance sequence. |
| AC-009-017 | IDs, ownership resolution, actor, timestamp, sequence, predecessor/current leaf, M03 evidence, input provenance, catalogue/rules, acceptance, and M05 eligibility are resolved and controlled server-side. |
| AC-009-018 | Database, ORM, and service tests enforce one linear same-client/same-target chain, one child per predecessor, revision-local component ownership/uniqueness, and no cross-client or cross-target reference. |
| AC-009-019 | Archiving changes no revision, makes eligibility false, and creates no successor; reopening creates no revision or authority; only eligible same-client `start_revalidation` from historical `accepted`, `unresolved`, or `rejected` appends one refreshed-snapshot `under_review` child and retains `m04_revalidation_required` until the revalidation sequence is explicitly accepted. |
| AC-009-020 | Every API and persistence lookup returns the same public response for foreign and missing IDs and exposes no foreign existence, count, identity, provenance, rule, component, or timing information. |
| AC-009-021 | `eligible_for_m05` is derived read-time and fail-closed; after archive/reopen it can become true only for a newly and explicitly accepted post-`start_revalidation` leaf with refreshed snapshot, current valid M03 revision/eligibility, valid current catalogue/rules, all ordinary conditions, and no wider readiness claim. |
| AC-009-022 | M02/M03 rejection, supersession, or other locked eligibility invalidation makes M05 eligibility false while leaving every M04 revision, component, snapshot, and rule-evidence row unchanged. |
| AC-009-023 | Frontend A→B and A→B→A tests cover every read, mutation, follow-up refresh, stale success, rejected promise, structured error, and `finally`, proving zero stale active-context updates. |
| AC-009-024 | The additive migration and full verification upgrade above `e4a7c3d9b802`, preserve all predecessor data, add only bounded M04 structures, leave one Alembic head, pass SQLite/PostgreSQL, focused/full/regression/build/compile/diff checks, and prove all parser, normalization, M02/M03 mutation, M05 execution, ledger/reconciliation, tax/fixation, and prior-regression exclusions. |

Acceptance criteria count: `24`.

## 23. Negative acceptance criteria

| ID | Prohibited outcome |
|---|---|
| NAC-009-001 | Parser implementation, byte parsing, extraction, parser preview, or parser schema. |
| NAC-009-002 | Normalized import, normalized source facts, or a new M04 source-fact intake/editor. |
| NAC-009-003 | Raw-source/blob/checksum mutation, replacement, deletion, correction, or use as inferred classification meaning. |
| NAC-009-004 | Mutation of M02/M03 lifecycle, review, annotation, intake, source, supersession, or accepted predecessor authority. |
| NAC-009-005 | Caller-forged ownership, provenance, snapshot, catalogue/rules, actor/timestamp, revision identity/sequence/current pointer, acceptance, or eligibility. |
| NAC-009-006 | Mutation, overwrite, correction-in-place, concealment, or reclassification-in-place of an accepted decision. |
| NAC-009-007 | Delete-in-place of any M04 subject, revision, component decision, snapshot, matched-rule evidence, override, or undo history. |
| NAC-009-008 | Silent classification of conflicting exact rules or unsupported inference from component evidence to the whole asset. |
| NAC-009-009 | Provider-only, partial-name, fuzzy, scored, threshold, or other heuristic fallback. |
| NAC-009-010 | Global latest-wins, timestamp precedence, or unapproved rule-order precedence resolving a classification conflict. |
| NAC-009-011 | Tax, exemption, fixation, formal 161D, liquidity, withdrawal, pension-start, severance-availability, or professional-authority conclusion. |
| NAC-009-012 | M05 ledger creation, balance reconciliation, or any claim that classification proves a reconciled balance. |
| NAC-009-013 | Conversion, calculation execution/readiness, scenarios, recommendations, or reports. |
| NAC-009-014 | Persisted/caller-controlled M05 eligibility, direct M05 execution/authority, or M05/next-package authorization outside its separate gate. |
| NAC-009-015 | M04 mutation while M01 is archived or automatic eligibility restoration after the case is reopened. |
| NAC-009-016 | Foreign-client access, cross-client/cross-target subject, predecessor, component or rule link, or any foreign-ID existence leakage. |
| NAC-009-017 | A stale A→B or A→B→A read, mutation, refresh, success, rejection, API error, loading/pending state, or `finally` changing the active client context. |
| NAC-009-018 | M04-complete, production-ready, V1/V2 parity, M09-M14, 02M, or other-package authorization claim. |

Negative acceptance criteria count: `18`.

## 24. Verification matrix

| Verification area | Required proof | Criteria |
|---|---|---|
| M03 and target provenance | Current M03 eligibility, manual/upload distinction, immutable labels, opaque-upload unresolved | AC-009-001–004; NAC-009-001–004 |
| Taxonomy | Separate bounded asset/component/interpretation axes and derived mixed | AC-009-005–007; NAC-009-008, NAC-009-011 |
| Exact rules | Version/rule identity, evidence/explanation, no fallback, unresolved conflict | AC-009-008–011; NAC-009-008–010 |
| Proposal and acceptance | Proposal-only automation and explicit acceptance | AC-009-012–013; NAC-009-005 |
| Immutable lifecycle | Immutable accepted revision, reopen successor, additive override/undo | AC-009-014–016; NAC-009-006–007 |
| Server authority and isolation | Server-owned evidence, same-client/target enforcement, non-leakage | AC-009-017–018, AC-009-020; NAC-009-005, NAC-009-016 |
| Archived behavior | Read-only archive and explicit post-reopen revalidation | AC-009-019; NAC-009-015 |
| M05 eligibility | Complete fail-closed truth table and predecessor invalidation without history mutation | AC-009-021–022; NAC-009-011–014 |
| Frontend async | A→B/A→B→A across reads, mutations, refresh, error, and finally | AC-009-023; NAC-009-017 |
| Migration, regression, scope | Additive single-head migration, full verification, and excluded capabilities absent | AC-009-024; NAC-009-001–004, NAC-009-011–014, NAC-009-018 |

Browser E2E, CI, deployment, and production verification may be claimed only
if separately available and actually executed.

## 25. Included, deferred, and excluded scope

Included:

- M03-target consumption;
- immutable classification snapshots;
- versioned exact-rule proposal;
- asset-level product family;
- component-level decisions;
- separate pension/capital interpretation;
- unresolved/conflict behavior;
- explicit planner acceptance;
- immutable revisions and additive overrides/undo;
- derived M05 eligibility;
- bounded backend API and frontend workflow;
- client isolation and async-context protection;
- additive migration; and
- focused and regression tests.

Deferred:

- parser and normalized source facts;
- automatic classification of opaque uploaded targets;
- planner-entered new source facts in M04;
- database-managed rule administration;
- old/new pension mapping without evidence;
- confidence scoring;
- generic restriction status;
- tax-relevance metadata;
- rule effective-date administration;
- bulk catalogue reclassification;
- multi-user approval; and
- production authentication/administration.

Explicitly excluded:

- parser implementation, normalized import, and raw-source mutation;
- M02/M03 lifecycle or evidence mutation;
- M05 ledger, reconciliation, conversion, and downstream execution;
- tax, exemption, fixation, formal 161D, liquidity, and withdrawal logic;
- scenarios, recommendations, and reports;
- M09-M14 or 02M work;
- V1/V2 parity;
- production readiness or M04-complete claims; and
- authorization of M05 or any next package.

No unresolved product decision blocks definition review. Exact table, column,
index, route, component, and server-actor code names may follow repository
conventions during a separately authorized implementation only if every
contract above remains unchanged.

## 26. Authorization boundary and final gate

This definition authorizes no implementation activity.

- Definition: `DRAFT_PENDING_GATE_REVIEW`
- Implementation: `NOT_AUTHORIZED`
- Migration creation/execution: `NOT_AUTHORIZED`
- Parser/normalization: `NOT_AUTHORIZED`
- M05: `NOT_AUTHORIZED`
- Next package: `NOT_AUTHORIZED`

No implementation acceptance record is created. A separate gate must accept or
return this definition before implementation authorization may be considered.

`PKG_009_DEFINITION_READY_FOR_ACCEPTANCE_AUDIT`

This final status means only that the definition is ready for acceptance audit.
It is not `READY_FOR_IMPLEMENTATION`, does not authorize migration execution,
and does not open M05 or another package.
