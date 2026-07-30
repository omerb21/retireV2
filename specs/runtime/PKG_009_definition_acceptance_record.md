# PKG-009 Definition Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-009 — M04 Evidence-Backed Asset and Component Classification Decisions` |
| Module | `M04` |
| Definition status | `ACCEPTED` |
| Authoritative base | `4233ea87e887dd895eb0497f46e05df9cf6e8ea0` |
| Definition draft commit | `f3ddd843bf77608cc1b13312fabe04c6bb495f4d` |
| Accepted definition HEAD | `9ce733a2efaf804ff3dc4dcdbb8e5796d69c3d5b` |
| Definition branch | `origin/pkg-009-definition` |
| Definition | `specs/runtime/PKG_009_FINAL_PACKAGE_DEFINITION.md` |
| Predecessor | Accepted PKG-008 — M03 Source Review and Downstream Evidence Eligibility Foundation |
| Predecessor migration | `e4a7c3d9b802` |
| Implementation | `NOT_AUTHORIZED` |
| Migration creation/execution | `NOT_AUTHORIZED` |
| M05 | `NOT_AUTHORIZED` |
| Next package | `NOT_AUTHORIZED` |

## Accepted Product Outcome

PKG-009 defines explainable, immutable, and versioned M04 classification
decisions for M03-eligible manual or uploaded targets.

The accepted decision model separates:

- asset-level product family;
- component decisions;
- component pension/capital interpretation;
- derived aggregate interpretation;
- explicit planner acceptance;
- exact matched-rule evidence;
- source and M03 provenance; and
- derived M05 eligibility.

The accepted definition does not define parser implementation, normalized
source facts, a ledger, reconciliation, conversion, tax, exemption, fixation,
formal 161D, liquidity or withdrawal authority, scenarios, recommendations,
or reports.

## Accepted Taxonomy Contract

Product families are exactly:

- `insurance_policy`;
- `savings_policy`;
- `provident_fund`;
- `investment_provident_fund`;
- `education_fund`;
- `pension_fund`; and
- `unknown_or_unresolved`.

Component kinds are exactly:

- `severance_component`;
- `contribution_component`; and
- `unknown_component`.

The interpretation axis is exactly:

- `pension`;
- `capital`;
- `mixed`; and
- `unresolved`.

`contribution_component` represents תגמולים.
`compensation_component` is prohibited. No old/new pension subtype is
classified automatically. `mixed` is derived only from resolved component
decisions with materially different interpretations.

## Accepted Rule Contract

- The rule strategy is a static, versioned exact-rule catalogue.
- The initial technical catalogue version is exactly `m04-rules-v1`.
- Matching is exact and deterministic.
- Provider-only fallback, partial-name fallback, fuzzy matching, scoring,
  latest-wins behavior, and unsupported global precedence are prohibited.
- Automatic rule execution may produce only `proposed`.
- Explicit planner acceptance is required to create new accepted authority.
- Persisted revisions retain the exact catalogue and matched-rule identity
  used.

## Accepted Lifecycle

Persisted states are exactly:

- `under_review`;
- `proposed`;
- `accepted`;
- `unresolved`; and
- `rejected`.

The accepted action distinctions are:

- reopen → `under_review`;
- override → planner-authored `proposed`;
- undo → planner-authored `proposed`; and
- `start_revalidation` → fresh-snapshot `under_review`.

Every state-changing action appends a revision. No prior revision is updated
or deleted, the current pointer is never rolled back, and no previous accepted
revision is reactivated. New authority always requires explicit acceptance.
Rejecting an override or undo does not restore earlier authority.

## Archive and Revalidation

Archive and M01 reopen do not mutate M04 history. Eligibility remains false
after reopen, and `start_revalidation` is required.

`start_revalidation` is allowed only from a historical leaf in:

- `accepted`;
- `unresolved`; or
- `rejected`.

It creates a fresh `under_review` successor and refreshes the immutable input
snapshot, current accepted M03 revision, and current catalogue context. The
ordinary proposal and explicit-acceptance sequence then applies. The exclusion
reason remains `m04_revalidation_required` until a newly accepted
post-revalidation leaf exists.

## M03 Snapshot Context

Stored M03 context is decision-time evidence only and is not current
eligibility authority. Every authoritative read, mutation, and M05 eligibility
calculation must rederive current M03 eligibility server-side.

## Derived M05 Eligibility

M05 eligibility is read-time, server-controlled, fail-closed, and never
caller-authored. It is not M05 authorization.

It requires a current accepted and resolved M04 leaf, current M03 eligibility,
and a valid same-client chain and provenance. It becomes false when a successor
is `proposed`, `unresolved`, or `rejected`, when M01 is archived, when M03
becomes invalid, or when stored evidence is corrupted.

Eligibility does not mean:

- ledger ready;
- reconciled;
- tax ready;
- calculation ready;
- liquid;
- withdrawable;
- pension-start eligible; or
- fixation eligible.

## Migration Boundary

- A future implementation migration is `REQUIRED`.
- Its expected parent is `e4a7c3d9b802`.
- No migration was created or executed during definition work.
- No backfill or professional inference is authorized.
- Migration creation and execution remain `NOT_AUTHORIZED`.

## Acceptance Evidence

Final definition audit status:

`ACCEPT_PKG_009_DEFINITION_WITH_NON_BLOCKING_WORDING_NOTES`

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Scope | `PASS` |
| Product-decision fidelity | `PASS` |
| D-009-001 | `FIXED` |
| D-009-002 | `FIXED` |
| D-009-003 | `FIXED` |
| AC | `24 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `18 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Blocking definition defects | `None` |
| Material ambiguities | `None` |
| Product decisions required | `None` |
| Final status | `ACCEPT_PKG_009_DEFINITION_WITH_NON_BLOCKING_WORDING_NOTES` |

## Non-Blocking Follow-Up

The future requirements-to-tests matrix must explicitly map all ordinary
lifecycle actions, including start, proposal creation, unresolved decision,
accept, and reject, in addition to reopen, override, undo, and
`start_revalidation`.

This is a non-blocking wording follow-up. It is not implementation debt, is not
a definition defect, does not block implementation planning, does not modify
the accepted definition contract, and does not authorize implementation.

## Scope Boundaries

- The PKG-009 definition is accepted.
- Implementation remains `NOT_AUTHORIZED`.
- Migration creation and execution remain `NOT_AUTHORIZED`.
- M05 remains `NOT_AUTHORIZED`.
- The next package remains `NOT_AUTHORIZED`.
- M09–M14 remain `BLOCKED_FOR_LOGIC_DETAIL`.
- `02M` remains `FROZEN`.
- No M04 implementation-complete claim is made.
- No production-readiness claim is made.
- No V1/V2 parity claim is made.

## Closure Boundary

Definition acceptance and closure do not authorize implementation. A separate
implementation gate is required. No implementation acceptance record,
implementation branch, migration, M05 work, or next package is authorized by
this record.
