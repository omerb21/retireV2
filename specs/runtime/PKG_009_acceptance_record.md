# PKG-009 Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-009 — M04 Evidence-Backed Asset and Component Classification Decisions` |
| Module | `M04` |
| Status | `ACCEPTED_AND_CLOSED` |
| Authoritative base | `cd43f981faf95d36c4dc59592c2a1a65d027038b` |
| Accepted implementation HEAD | `ae73a7706214b137b7452b9f66c483ee5b57009c` |
| Review branch | `origin/pkg-009-review` |
| Accepted definition HEAD | `9ce733a2efaf804ff3dc4dcdbb8e5796d69c3d5b` |
| Definition | `specs/runtime/PKG_009_FINAL_PACKAGE_DEFINITION.md` |
| Definition acceptance record | `specs/runtime/PKG_009_definition_acceptance_record.md` |
| Accepted migration | `95222c79dce8` |
| Migration parent | `e4a7c3d9b802` |
| Catalogue | `m04-rules-v1` |
| Accepted implementation commits above base | `14` |

## Accepted Implementation Chain

1. `7972367859a29e8964321f1f4aa45bbd70a9f160` — `feat: add PKG-009 classification persistence`
2. `12599702bf5a3897542d23ca766d80764694f7e9` — `feat: implement PKG-009 classification workflow`
3. `02eb8816516656c7526216acb6602c9ebd7e88ee` — `feat: add PKG-009 planner classification UI`
4. `e326a5bbd15a13c14de05ea65c7e0f5dd30dd4e1` — `test: cover PKG-009 acceptance contracts`
5. `c3e730c00c10b655d5e35c8e4573af4f22e7f132` — `test: recognize PKG-009 additive schema`
6. `d2ade0fe9b36c9f8f72a98222e35df9f6e420edc` — `fix: preserve PKG-009 eligibility exclusions`
7. `e95c8c4db121d1d73740d9f6e0f7656a12e2fb92` — `fix: enforce PKG-009 ORM immutability`
8. `29cca9bb109f6ec72f2f351599872afba2195d0b` — `fix: validate PKG-009 aggregate integrity`
9. `c2e60a274852aee7be084c00d7e52e334fe497d5` — `fix: isolate PKG-009 frontend requests`
10. `509195f6cdf4f713c00f38b94c25cd8df5d0269c` — `test: complete PKG-009 race and evidence coverage`
11. `2a23ed3cb5d21658050e8015a35b4b76253991ee` — `fix: reject duplicate PKG-009 snapshot identities`
12. `a31cf88dec9f03783688629292f77e31991bc077` — `fix: invalidate PKG-009 async ownership`
13. `2e0a955a722059e84aac73fe10872e9b9edc4754` — `test: cover PKG-009 unmount and preview races`
14. `ae73a7706214b137b7452b9f66c483ee5b57009c` — `test: prove PKG-009 post-mutation previews`

## Accepted Product Outcome

PKG-009 implements explainable, immutable, versioned M04 classification
decisions for M03-eligible targets. The accepted implementation separates:

- asset product family;
- component kinds;
- component interpretation;
- derived aggregate interpretation;
- classification lifecycle;
- matched-rule evidence;
- explicit planner acceptance;
- M03 provenance; and
- derived M05 eligibility.

The accepted implementation does not implement M05, parsing, extraction,
normalization, new fact intake, ledger behavior, reconciliation, conversion,
tax, exemption, fixation, formal 161D, liquidity or withdrawal decisions,
scenarios, recommendations, or reports.

## Accepted Taxonomy

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

Interpretation values are `pension`, `capital`, `mixed`, and `unresolved`.
`contribution_component` represents תגמולים; `compensation_component` is
prohibited. Component interpretation cannot be `mixed`. Whole-asset `mixed`
is derived only from materially differing resolved components. No old/new
pension inference is implemented.

## Persistence and Immutability

- Three bounded M04 persistence structures preserve stable subject identity,
  append-only revisions, and revision-owned components.
- One-child predecessor enforcement and target-sequence uniqueness preserve a
  deterministic revision chain.
- Same-client and same-target integrity is enforced.
- ORM instance and bulk update/delete paths are protected.
- The archive-generation exception is narrow and applies only to its accepted
  controlled boundary.
- Direct corruption causes authoritative reads and eligibility to fail closed.
- No pointer rollback, history mutation, or destructive reuse is accepted.

## Catalogue

- The exact technical catalogue version is `m04-rules-v1`.
- Matching is exact and deterministic.
- There is no provider-only fallback, partial matching, fuzzy matching,
  scoring, latest-wins behavior, or unsupported precedence.
- Conflicts become unresolved.
- Automatic rules create proposals only; explicit planner acceptance is
  required.
- Persisted matched-rule evidence remains visible to readers.

## Lifecycle

Implemented actions are:

- `start`;
- `preview`;
- `proposal`;
- `unresolved`;
- `accept`;
- `reject`;
- `reopen`;
- `override`;
- `undo`; and
- `start_revalidation`.

Every state change appends a revision. There is no pointer rollback, history
mutation, or automatic acceptance. Override and undo create proposed
successors. A rejected override or undo does not restore old authority.
Post-archive revalidation requires a new proposal and explicit acceptance.

## Input and M03 Boundary

- Manual decisions consume only persisted M02 metadata.
- Uploaded opaque targets remain unresolved.
- Filename, MIME, checksum, path, and blob metadata are not classification
  evidence.
- Every authoritative operation rederives current M03 eligibility.
- M03 annotations and reasons do not become classification rules.
- Foreign and missing resources use non-leaking failure behavior.

## Derived M05 Eligibility

Derived M05 eligibility is read-time, server-controlled, fail-closed, and
never caller-authored. It is not M05 authorization. It requires current M03
eligibility and a current accepted, resolved M04 authority. Corrupted snapshot,
rule evidence, aggregate/component semantics, provenance, or revision chain
causes ineligibility.

Eligibility does not mean ledger-ready, reconciled, tax-ready,
calculation-ready, liquid, withdrawable, pension-start eligible, or
fixation-eligible.

## Frontend

- The bounded planner workflow exposes all nine state-changing lifecycle
  actions and the non-persisting preview.
- Full persisted technical evidence and the current/history distinction are
  rendered.
- Archived cases are read-only.
- Route generation and per-request ownership protect A→B, A→B→A, and
  same-generation X→Y transitions.
- Unmount invalidates active request ownership.
- Preview and mutation ownership are cross-invalidated.
- A stale mutation launches zero refresh calls.
- A new post-mutation preview succeeds for each of the nine lifecycle actions.

## Acceptance Evidence

The final audit status is:

`ACCEPT_PKG_009_IMPLEMENTATION`

| Audit area | Result |
|---|---|
| Safety | `PASS` |
| Final review HEAD | `ae73a7706214b137b7452b9f66c483ee5b57009c` |
| Commit chain | `14 commits above master` |
| Migration | `95222c79dce8` |
| Alembic | `single head` |
| Catalogue | `m04-rules-v1` |
| AC | `24 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `18 PASS / 0 FAIL / 0 NOT_PROVEN` |
| Blocking implementation defects | `None` |
| Material non-blocking follow-up | `None` |
| Product decisions required | `None` |
| Final status | `ACCEPT_PKG_009_IMPLEMENTATION` |

## Verified Test Evidence

| Verification | Result |
|---|---|
| Focused frontend | `151 passed` |
| Full frontend | `335 passed` |
| Focused backend | `59 passed` |
| Full backend, final independently observed result | `798 passed` |
| Production frontend build | `PASS` |
| Python compile | `PASS` |
| SQLite migration cycle | `PASS` |
| PostgreSQL offline DDL | `PASS` |
| Alembic | one head `95222c79dce8` |
| `git diff --check` | `PASS` |
| AC | `24 PASS / 0 FAIL / 0 NOT_PROVEN` |
| NAC | `18 PASS / 0 FAIL / 0 NOT_PROVEN` |

The FastAPI `on_event` deprecation, React Router future flags, and npm
`http-proxy` configuration message are recorded as non-blocking environment
warnings only. They are not implementation defects.

## Closed Defects

| Defect | Accepted resolution boundary | Final status |
|---|---|---|
| `D-009-I001` | ORM append-only mutation/delete bypass closed | `CLOSED` |
| `D-009-I002` | Aggregate/component semantic fail-open closed | `CLOSED` |
| `D-009-I003` | Frontend async request ownership and race evidence closed | `CLOSED` |
| `D-009-I004` | Persisted rule/decision evidence rendering closed | `CLOSED` |
| `D-009-I002R` | Duplicate snapshot identity fail-open closed | `CLOSED` |
| `D-009-I003R` | Unmount and preview/mutation ownership closed | `CLOSED` |
| `D-009-I003R-EVIDENCE-001` | Post-mutation preview evidence closed for all nine lifecycle actions | `CLOSED` |

## Authorization Boundary

- PKG-009 implementation is accepted and closed.
- M04 is complete only within the accepted PKG-009 scope.
- M05 remains `NOT_AUTHORIZED`.
- Migration execution for accepted PKG-009 is included in the accepted
  package.
- The next package remains `NOT_AUTHORIZED`.
- M09–M14 remain `BLOCKED_FOR_LOGIC_DETAIL`.
- `02M` remains `FROZEN`.
- No production-readiness claim is made.
- No V1/V2 parity claim is made.
