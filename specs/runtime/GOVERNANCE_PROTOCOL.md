# Retirement Planning V2 Governance Protocol

## 1. Protocol Identity and Authority

- Protocol identity: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL`
- Version: `v1`
- Status: `PROPOSED_FOR_ACCEPTANCE`
- Classification: `PROCESS_GOVERNANCE_ONLY`
- Business authority: `NONE`
- Product authority: `NONE`
- Calculation authority: `NONE`
- Draft base master: `c7370f4d3a53d5c4da40ff6d534c403b6de38979`
- Expected Alembic head: `e6b4c8d2f507`

This protocol governs process and lifecycle evidence only. It creates no
business semantics, product behavior, calculation rule, implementation, API,
migration, persistence, test obligation beyond an accepted package definition,
package authorization, broad-module authorization, or production-readiness
claim.

## 2. Core Design Principle

Package semantics live in the accepted package definition.

Acceptance evidence must reference the accepted artifact; it must not reproduce
the package semantics.

Audits must verify the artifact appropriate to the current gate and must not
automatically re-audit already accepted semantic content.

This semantic single-source-of-truth rule reduces duplicated authority, token
drift, and audits of documentation that merely documents other documentation.

## 3. Mandatory Controls

The following controls are mandatory and may not be simplified away:

1. Verify the exact base and `master` before every lifecycle transition.
2. Require an independent WORK audit at every audit gate defined here.
3. Freeze an immutable accepted definition HEAD after semantic acceptance.
4. Freeze an immutable accepted implementation HEAD after implementation
   acceptance.
5. Identify accepted artifacts by exact commit SHA and, where applicable, exact
   blob or tree identity.
6. Never amend, rebase, squash, rewrite, or otherwise replace an accepted
   boundary.
7. Preserve append-only correction history.
8. Never force-push a lifecycle branch or `master`.
9. Integrate accepted lifecycle chains into `master` by pure fast-forward only.
10. Require a final WORK master-closure audit.
11. Require explicit implementation authorization after definition closure.
12. Never infer or grant authorization for the next package.
13. Never infer or grant broad-module authorization from a package transition.
14. Preserve protected-path discipline: protected local evidence or bootstrap
    paths remain outside tracked scope unless a separate explicit authorization
    names them.
15. Verify that the worktree and index are clean at transition boundaries,
    except for explicitly recognized untracked protected paths.
16. Preserve the architecture single-owner invariant in Section 17.
17. Verify the exact scope diff and changed-path allowlist at every relevant
    transition.
18. Verify migrations and the single Alembic head when migration state is
    relevant; a docs-only lifecycle must also prove that it did not change that
    state.
19. Preserve every professional-decision gate and its explicit decision token.
20. Enforce the stop conditions owned by the accepted artifact and the current
    lifecycle gate.
21. Make no production-readiness claim without a separate explicit gate.

## 4. Audit Depth and Evidence Rule

`Focused` means auditing the changed or risk-relevant layer with evidence. It
does not mean assuming correctness without evidence.

- A semantic definition audit remains deep and evaluates the full proposed
  package contract.
- An implementation audit remains deep and evaluates behavior, implementation
  surfaces, tests, boundaries, and relevant operational evidence.
- A manifest audit is mechanical because a conforming manifest intentionally
  contains no package semantics.
- A master-closure audit is integrity- and drift-focused because semantic or
  implementation acceptance already occurred against immutable artifacts.

Evidence of artifact drift reopens the affected evidence question and requires
the depth appropriate to the drift. Audit labels never excuse a missing proof.

## 5. Definition Lifecycle

The normal future definition lifecycle is:

A. Codex drafts the package definition.
B. Independent WORK performs a deep semantic definition audit.
C. If needed, Codex makes a narrow append-only correction and WORK performs a
   focused re-audit of the affected findings and risk surface.
D. The accepted definition HEAD is frozen as an immutable boundary.
E. Codex creates one short definition acceptance manifest.
F. WORK performs a mechanical audit of that manifest.
G. The definition chain and manifest are integrated into `master` by pure
   fast-forward.
H. WORK performs the final definition master-closure audit.
I. Only after definition closure may implementation be separately authorized.

No additional closure-record or closure-bookkeeping commit is part of this
normal lifecycle.

## 6. Accepted Definition as Sole Semantic Authority

The accepted definition is the sole package-level semantic source of truth for:

- objective and classification;
- business authority;
- source contracts and field semantics;
- binding and fail-closed behavior;
- acceptance criteria and negative acceptance criteria;
- stop conditions;
- expected implementation surfaces and deterministic test strategy;
- exclusions; and
- architecture ownership.

An acceptance manifest must not transcribe those items in prose. It may identify
them only by the accepted definition SHA, definition blob, AC range and count,
NAC range and count, and stop-condition count.

## 7. Short Definition Acceptance Manifest

The canonical future name is:

`specs/runtime/<PACKAGE_ID>_definition_acceptance_manifest.md`

The manifest is intentionally short and contains only machine- or
audit-friendly facts:

- package ID and exact title;
- classification and business authority;
- immutable accepted definition HEAD and definition blob;
- audit decision token and finding token;
- professional-decision token and definition sufficiency;
- AC range, count, and result;
- NAC range, count, and result;
- stop-condition count and result;
- implementation authorization status;
- master status; and
- final manifest token.

It must not duplicate endpoint definitions, field-level contracts,
presentation wording, binding details, Q-019/Q-020 lists, test matrices,
business exclusions, calculation semantics, or any other substantive package
contract. Those remain in the immutable accepted definition.

## 8. Definition Manifest Audit

The independent WORK definition-manifest audit is mechanical. It verifies only:

- the exact accepted definition SHA and blob;
- package identity;
- audit decision, finding, and professional-decision tokens;
- AC and NAC ranges, counts, and results;
- stop-condition count and result;
- that implementation remains unauthorized;
- manifest-only scope and the exact final token; and
- absence of contradictory governance status.

It does not re-audit package semantics already accepted by the semantic
definition audit. If semantic content was copied into the manifest, the normal
correction is to remove the unnecessary duplication, not expand the manifest
or its audit.

## 9. Implementation Lifecycle

The normal future implementation lifecycle is:

A. GPT Chat grants explicit implementation authorization.
B. Codex implements the authorized scope and its tests.
C. Independent WORK performs a deep implementation audit.
D. If required, Codex makes a narrow append-only correction and WORK performs a
   focused re-audit of the affected findings and risk surface.
E. The accepted implementation HEAD is frozen as an immutable boundary.
F. Codex creates one short implementation acceptance manifest.
G. WORK performs a mechanical implementation-manifest audit.
H. The implementation chain and manifest are integrated into `master` by pure
   fast-forward.
I. WORK performs the final implementation master-closure audit.

This lifecycle creates no extra closure-record commit and grants no automatic
authorization to another package or a broader module.

## 10. Short Implementation Acceptance Manifest

The canonical future name is:

`specs/runtime/<PACKAGE_ID>_implementation_acceptance_manifest.md`

The manifest contains only:

- package ID and exact title;
- accepted definition HEAD;
- immutable accepted implementation HEAD;
- accepted implementation tree or blob identifiers where relevant;
- WORK implementation decision and finding token;
- professional-decision token;
- test-suite summary and counts;
- migration and Alembic status;
- accepted changed-path summary;
- implementation status and master status; and
- final manifest token.

It must not reproduce the full implementation behavior contract already owned
by the accepted definition.

The independent WORK implementation-manifest audit mechanically verifies those
identities, tokens, counts, statuses, changed-path summary, non-semantic scope,
and final token. It does not repeat the deep implementation audit.

## 11. Final Master-Closure Audit Model

Definition and implementation final master-closure audits remain mandatory.
They are drift and integrity audits, not full semantic re-acceptance audits.
They verify, as applicable:

- exact refs, ancestry, merge base, and commit chain;
- no merge, rewrite, squash, or replacement;
- preservation of the immutable accepted boundary;
- accepted artifact, blob, and tree identity;
- net changed paths and diff quality;
- manifest identity and predecessor preservation;
- absence of architecture-authority drift;
- governance and authorization status; and
- migration state and the single Alembic head.

The audit does not mechanically rerun every AC or NAC semantic proof unless
there is evidence of artifact drift.

## 12. Append-Only Correction Policy

If a proposed definition has a defect, add a correction commit above the
candidate and obtain a focused WORK re-audit. The corrected definition HEAD,
once accepted, becomes the immutable accepted definition boundary.

If an implementation candidate has a defect, add a correction commit above the
candidate and obtain a focused WORK re-audit. The corrected implementation
HEAD, once accepted, becomes the immutable accepted implementation boundary.

If an acceptance manifest has a defect, add an append-only manifest correction.
Do not change the accepted definition or implementation boundary. WORK performs
only the focused mechanical re-audit required by the manifest change.

Failed, superseded, or incomplete candidates remain visible in history and
must be unambiguously distinguished from the accepted boundary. No accepted
commit is amended, rebased, squashed, deleted, or retagged by implication.

## 13. Token Taxonomy and Ownership

- `NO_FINDING` means the current full acceptance audit found no finding.
- `NO_NEW_FINDING` means a focused re-audit of previously identified findings
  introduced no additional finding.
- `<DEFECT_ID> CLOSED` means an existing named finding was closed.

These tokens are not interchangeable. `NO_NEW_FINDING` does not mean that the
earlier full audit had `NO_FINDING`, and `<DEFECT_ID> CLOSED` records closure of
an existing finding rather than absence of findings. A later re-audit never
retroactively replaces the token owned by an earlier audit stage.

Every prompt and report must identify the lifecycle stage that owns each audit,
finding, closure, professional-decision, and final token.

## 14. Prompt Discipline

Future GPT Chat prompts reference this protocol and add only package-specific
facts. A normal prompt should be approximately:

1. role;
2. lifecycle gate;
3. protocol identity and version;
4. exact refs;
5. package-specific scope;
6. package-specific stop conditions or exceptions;
7. required action;
8. required report; and
9. final token.

Global governance is referenced from
`specs/runtime/GOVERNANCE_PROTOCOL.md`; it is not restated in hundreds of prompt
lines. Exact package facts and exceptional controls remain explicit.

## 15. Conflict Rule

If an accepted package definition conflicts with this generic protocol about
business or package semantics, the accepted package definition wins for that
package's semantics.

If a conflict concerns lifecycle safety or governance, stop and request a GPT
Chat governance resolution. Neither source may be silently reinterpreted.

## 16. Historical Compatibility and Effective Date

This protocol is prospective. PKG-015 through PKG-018 definition retain their
existing accepted files, commits, tokens, and governing evidence. There is no
retroactive renaming, manifest conversion, history rewrite, cleanup commit, or
token replacement. Historical evidence remains valid under the protocol that
governed it.

This protocol becomes active only after:

1. a Codex draft;
2. a WORK governance audit;
3. any required append-only correction and focused re-audit;
4. freezing the immutable accepted protocol HEAD;
5. pure fast-forward integration to `master`; and
6. a final WORK governance master-closure audit.

The WORK acceptance report, immutable protocol HEAD, and master closure are
sufficient. No verbose governance acceptance record or governance acceptance
manifest is created unless WORK identifies a concrete need.

## 17. Architecture Invariant

Every material business calculation has exactly one authoritative owner.

This process refactor cannot transfer domain authority between modules or
packages and cannot create new business, product, or calculation authority.

## 18. Avoiding Documentation and Closure Loops

The normal lifecycle prohibits self-referential patterns in which:

- an acceptance record reproduces the full definition;
- an audit re-audits copied semantics rather than the accepted artifact;
- a correction changes copied prose while the authoritative artifact was
  already correct;
- a closure commit merely records closure;
- another audit audits that closure-only commit; or
- another bookkeeping commit records that audit.

Final closure is established by the accepted immutable artifact, accepted audit
result, exact ancestry, `master` state, and final WORK master-closure audit. No
additional commit is required merely to state `CLOSED_ON_MASTER`, unless a
genuine authoritative planning artifact must change for a non-self-referential
reason.

## 19. PKG-018 Transition and Preserved Governance State

- PKG-015: `CLOSED_ON_MASTER`
- PKG-016: `CLOSED_ON_MASTER`
- PKG-017: `CLOSED_ON_MASTER`
- PKG-018 definition: `CLOSED_ON_MASTER`
- PKG-018 immutable accepted definition HEAD:
  `12e121c8e5f5c51dae0490e2d338b463d140d1bc`
- PKG-018 implementation: `NOT_AUTHORIZED`
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11-M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`
- Next product package: `NOT_AUTHORIZED`
- Production readiness: `NOT_CLAIMED`

PKG-018's completed definition lifecycle is not reopened, converted, or
normalized. If this protocol becomes `CLOSED_ON_MASTER` before PKG-018
implementation authorization, the PKG-018 implementation lifecycle must use
Governance Protocol v1.

## 20. Governance Acceptance Criteria

| ID | Criterion |
|---|---|
| `GOV-AC-001` | The accepted package definition is the sole package-semantic source of truth. |
| `GOV-AC-002` | Independent WORK audits remain mandatory at every defined audit gate. |
| `GOV-AC-003` | Accepted definition and implementation HEADs are exact, immutable boundaries identified with artifact blobs or trees where applicable. |
| `GOV-AC-004` | Accepted chains reach `master` only by pure fast-forward, without force push or history rewrite. |
| `GOV-AC-005` | Corrections are append-only and preserve distinguishable historical candidates. |
| `GOV-AC-006` | Implementation requires separate explicit authorization after definition closure and never authorizes a next package automatically. |
| `GOV-AC-007` | Definition and implementation manifests are short, machine-friendly, and non-semantic. |
| `GOV-AC-008` | Manifest audits are mechanical and verify exact identities, tokens, counts, scope, and status. |
| `GOV-AC-009` | Semantic definition and implementation audits remain deep; focused re-audits require evidence for changed and risk-relevant layers. |
| `GOV-AC-010` | Final WORK master-closure audits remain mandatory and verify integrity and drift. |
| `GOV-AC-011` | Audit stages own distinct `NO_FINDING`, `NO_NEW_FINDING`, and `<DEFECT_ID> CLOSED` meanings without retroactive replacement. |
| `GOV-AC-012` | Historical package records remain valid and are not renamed, converted, normalized, or rewritten. |
| `GOV-AC-013` | PKG-018 definition remains closed unchanged, while a later authorized PKG-018 implementation uses v1 if v1 closes first. |
| `GOV-AC-014` | Closure follows immutable artifacts, audit evidence, ancestry, master state, and final audit without closure-only bookkeeping loops. |
| `GOV-AC-015` | Every material business calculation retains exactly one authoritative owner. |
| `GOV-AC-016` | No package transition authorizes broad M10, M11-M14, M08E, 02M changes, or the next product package. |
| `GOV-AC-017` | Production readiness remains unclaimed until a separate explicit gate. |

Governance AC range: `GOV-AC-001` through `GOV-AC-017`; count: `17`.

## 21. Governance Negative Acceptance Criteria

| ID | Prohibited outcome |
|---|---|
| `GOV-NAC-001` | Removing, bypassing, or making optional an independent WORK audit. |
| `GOV-NAC-002` | Mutating, replacing, or ambiguously identifying an accepted HEAD or artifact. |
| `GOV-NAC-003` | Force push, amend, rebase, squash, rewrite, merge integration, or non-fast-forward integration of an accepted chain. |
| `GOV-NAC-004` | Automatic implementation authorization after definition work. |
| `GOV-NAC-005` | Automatic next-package or broad-module authorization. |
| `GOV-NAC-006` | Copying substantive package semantics into an acceptance manifest. |
| `GOV-NAC-007` | Default full semantic re-audit of a non-semantic manifest or already accepted immutable semantics without drift evidence. |
| `GOV-NAC-008` | Retrospective renaming, conversion, token replacement, cleanup, or rewrite of historical evidence. |
| `GOV-NAC-009` | Closure-only records, audits, and bookkeeping commits that create a self-referential documentation loop. |
| `GOV-NAC-010` | Weakening, inferring, or bypassing a professional-decision gate. |
| `GOV-NAC-011` | Inferring or claiming production readiness from protocol, package, or closure status. |

Governance NAC range: `GOV-NAC-001` through `GOV-NAC-011`; count: `11`.

## 22. Governance Protocol Adoption Stop Conditions

Adoption must stop on any of these exact conditions:

1. `GOVERNANCE_PROTOCOL_WEAKENS_INDEPENDENT_AUDIT`
2. `GOVERNANCE_PROTOCOL_WEAKENS_IMMUTABLE_BOUNDARIES`
3. `GOVERNANCE_PROTOCOL_ALLOWS_NON_FF_MASTER_INTEGRATION`
4. `GOVERNANCE_PROTOCOL_WEAKENS_PROFESSIONAL_DECISION_GATE`
5. `GOVERNANCE_PROTOCOL_REQUIRES_HISTORICAL_REWRITE`
6. `GOVERNANCE_PROTOCOL_CREATES_NEW_BUSINESS_AUTHORITY`
7. `GOVERNANCE_PROTOCOL_CONFLICT_UNRESOLVED`

Stop-condition range: item `1` through item `7`; count: `7`.

GOVERNANCE_PROTOCOL_V1_PROPOSED_FOR_ACCEPTANCE
