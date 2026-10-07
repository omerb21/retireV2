# Retirement Planning V2 Governance Protocol

## 1. Protocol Identity and Authority

- Protocol identity: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL`
- Version: `v1.1`
- Status: `PROPOSED_FOR_ACCEPTANCE`
- Classification: `PROCESS_GOVERNANCE_ONLY`
- Business authority: `NONE`
- Product authority: `NONE`
- Calculation authority: `NONE`
- Draft base master: `fafaaa8df7a80feb8e5194195e0166e3103dabbd`
- Expected Alembic head: `a2b8c5e1f309`

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


## 23. Risk-Based Compact Governance

This protocol uses three execution classes. Classification controls process
depth; it never weakens an accepted semantic or professional requirement.

### Class A - semantic or material contract work

The normal lifecycle is:

`TRIAGE/DEFINITION -> INDEPENDENT DEFINITION ACCEPTANCE -> PRE-IMPLEMENTATION CONTRACT ENUMERATION (when complex) -> IMPLEMENTATION AUTHORIZATION -> IMPLEMENTATION + SELF-VALIDATION -> INDEPENDENT IMPLEMENTATION ACCEPTANCE -> MERGE + CLOSURE`

Class A applies when a change can affect business semantics, product semantics,
calculation rules, authority boundaries, schemas, persistence, material
transaction behavior, or any other accepted contract surface.

### Class B - technical determinism correction

Class B may be used only for a local technical blocker that does not require a
new owner decision and does not change business semantics, numerical semantics,
scope, schema, persistence authority, or package authorization.

A Class B correction must:

- preserve the accepted package definition;
- derive correction behavior from an already authoritative executable contract;
- keep corrections append-only;
- use independently recomputed vectors or controls where determinism is relevant;
- close the named blocker explicitly; and
- pass direct regressions for the touched risk surface.

Escalate to Class A immediately if the correction requires a new semantic rule,
new scope, new schema, new authority, or unresolved interpretation.

### Class C - mechanical execution

Class C is limited to mechanical work whose semantic result is already accepted,
such as exact fast-forward integration, normal push, immutable bundle creation,
manifest or mapping-only correction, or closure bookkeeping that does not alter
tracked accepted behavior.

Class C requires precondition verification, exact mechanical execution, and
postcondition verification. It cannot create semantic authority.

## 24. Pre-Implementation Contract Enumeration for Complex Class A Work

A complex Class A package must not proceed directly from accepted Definition to
implementation when it consumes multiple existing authorities, producer routes,
failure envelopes, transaction boundaries, or deterministic evidence surfaces.

Before implementation authorization, WORK must produce a concise
implementation-oriented contract enumeration sufficient to expose edge cases
before code is written. It is an evidence and route inventory, not a second
semantic definition.

Where applicable it must identify:

1. the authoritative producer or upstream route inventory;
2. general invariants derived from executable producer behavior;
3. valid route combinations and boundary states;
4. malformed near-miss states that must be rejected;
5. failure taxonomy and technical/domain separation;
6. fixture authority rules, including where synthetic fixtures are forbidden;
7. mutation controls that a correct guard or boundary test must detect;
8. test-oracle expectations for each material invariant; and
9. reusable existing harnesses or accepted evidence that must not be rebuilt.

The enumeration must generalize the contract. It must not merely list the last
observed failing example.

If enumeration reveals a semantic ambiguity not resolved by the accepted
Definition or authority hierarchy, implementation remains unauthorized until
that ambiguity is resolved at the proper Class A gate.

## 25. Evidence Reuse and Delta Revalidation

Evidence reuse is the default.

Previously accepted evidence remains valid unless a later diff can reasonably
invalidate the behavior, artifact identity, environment assumption, or
authority on which that evidence depends.

Every correction or acceptance pass must begin with an invalidation analysis:

- what changed;
- which prior findings or evidence can be affected by that change;
- which accepted evidence is therefore reusable; and
- which narrow validations must be rerun.

Closed blockers are not reopened merely because another blocker remains open.
They are reopened only when the new delta touches their governing code, test
oracle, fixture authority, dependency, or other material assumption.

A mapping-only, manifest-only, or other documentary delta does not require
PostgreSQL, full-backend, or other broad suite repetition when immutable diff
inspection proves that runtime behavior is unchanged.

A PostgreSQL rerun is required when the delta can change database-specific,
transaction, isolation, concurrency, SQL, persistence, or DBAPI behavior.

A broad affected-regression or full-backend suite should be run when a candidate
is genuinely ready for that level of validation. Afterward it is not repeated
for every narrow correction. It is repeated only if invalidation analysis shows
that the correction can affect evidence established by that broad run.

Reused evidence must retain provenance. Candidate-reported execution may be
reused as candidate-reported evidence where valid; it must not silently be
relabeled as an independently executed WORK result.

## 26. Root-Cause Correction and Generalization Rule

A repeated implementation rejection must not automatically produce another
patch-by-example instruction.

Before authorizing a correction, GPT Chat or WORK must perform a narrow
root-cause triage that states:

1. the exact broken behavior;
2. the authoritative code or contract that governs it;
3. the general invariant or route rule being violated;
4. the family of valid and invalid cases implied by that invariant;
5. the minimal controls that expose the defect; and
6. the smallest implementation and test surface that may change.

Codex correction prompts must target the generalized rule, not only the latest
counterexample.

If a proposed correction merely changes one constant, ordering assumption, ID
position, fixture, or expected exception to satisfy the last failing example
without proving the general contract, the correction is incomplete.

## 27. Mutation Sensitivity for Boundary and Guard Tests

Where acceptance depends on a guard, isolation rule, transaction boundary,
forbidden call, fail-closed validator, or similar negative invariant, a test is
not sufficient merely because it can trigger its own locally injected expected
exception.

The acceptance oracle must, where practical, prove regression sensitivity by
introducing the forbidden behavior into the actual authoritative execution path
and demonstrating that the normal oracle fails for that reason.

Examples include:

- intermediate commit;
- second Session creation;
- nested public reader or transaction boundary;
- unintended write or autoflush;
- forbidden downstream authority call; and
- malformed but correctly re-fingerprinted outer metadata.

Mutation controls must confirm that the mutated path actually executed. A local
`pytest.raises` branch that can pass before the mutated path is reached is not
proof of regression sensitivity.

Mutation testing is risk-scoped. It is required for material boundary claims,
not as a blanket requirement for every ordinary value assertion.

## 28. Reusable Acceptance Harnesses and Evidence Assets

A harness, fixture factory, route matrix, mutation oracle, or deterministic
vector validator that has been independently shown to represent the owning
contract should be treated as a reusable project asset.

Future packages should reuse or extend such assets rather than recreate
equivalent bespoke controls.

When a reusable harness is changed, the audit must distinguish:

- changes to the harness itself;
- changes to the system under test; and
- evidence that remains valid because neither relevant surface changed.

Private WORK audit harnesses remain audit artifacts unless separately authorized
for tracked inclusion. Reuse does not by itself authorize tracking private audit
artifacts.

## 29. Validation Economy Without Quality Reduction

Validation depth follows risk and invalidation, not habit.

During implementation, prefer:

- focused package tests;
- directly affected regressions; and
- narrow database tests when the touched surface requires them.

During correction, prefer:

- blocker reproductions;
- generalized valid/invalid route controls; and
- regressions for protected invariants touched by the diff.

Use broad affected-regression and full-backend runs at meaningful candidate
boundaries, not automatically after every small append-only correction.

This rule may reduce duplicate execution only when prior evidence remains
applicable. It may never be used to skip evidence that the current diff can
invalidate.

## 30. Agent Role and Effort Discipline

GPT Chat owns product, architecture, lifecycle authorization, and governance
gating. It does not silently implement production behavior or auto-merge an
unaccepted candidate.

WORK owns independent read-only audit, route enumeration, evidence analysis,
triage, and acceptance. WORK must distinguish independent execution from reused
or candidate-reported evidence.

Codex owns authorized implementation, tests, Git commits, bundles, and
mechanical integration.

Operational effort should match task risk:

- use higher reasoning effort for complex Class A definition work, contract
  enumeration, material implementation correction, and final independent
  acceptance;
- use lighter effort for mechanical commits, bundles, exact mappings,
  documentary corrections, and Class C closure;
- do not spend high-cost implementation effort on broad revalidation that
  invalidation analysis proves unnecessary.

Specific model names are operational defaults, not semantic governance. GPT Chat
may update the current model choice without changing this protocol, provided the
risk/effort distinction above is preserved.

## 31. New-Session Bootstrap Rule

A new GPT Chat session handling Retirement Planning V2 must reconstruct project
state from authoritative artifacts rather than relying on conversational memory
alone.

At minimum it should establish:

1. current `master` / `origin/master` identity;
2. this governance protocol and its accepted version;
3. the current package or next-gap authorization status;
4. the latest relevant accepted definition and implementation boundaries;
5. Alembic head where relevant; and
6. protected local state supplied by the user when that state is not present in
   the tracked repository.

`CURRENT_PROJECT_STATE.md` and protected local bootstrap material may remain
untracked by design. If a new session cannot access those local artifacts, it
must not invent their contents. It may use current tracked master plus explicit
user-provided state and request the protected artifact only when it is necessary
to resolve a material ambiguity.

Conversation memory may accelerate orientation but is not an immutable project
authority.

## 32. v1.1 Additional Governance Acceptance Criteria

| ID | Criterion |
|---|---|
| `GOV-AC-018` | Complex Class A work performs pre-implementation contract enumeration when producer routes, failure states, transaction boundaries, or comparable cross-authority complexity make example-by-example correction risk material. |
| `GOV-AC-019` | Evidence reuse is the default and every correction identifies which prior evidence is invalidated by the actual diff. |
| `GOV-AC-020` | Closed blockers are revalidated only when the new delta can materially affect them. |
| `GOV-AC-021` | Repeated correction work is driven by root cause and a generalized contract invariant, not only by the latest failing example. |
| `GOV-AC-022` | Material guard and boundary claims use mutation-sensitive or equivalent adversarial evidence that proves the normal oracle detects real execution-path violations. |
| `GOV-AC-023` | Broad PostgreSQL, affected-regression, and full-backend evidence is rerun according to diff-based invalidation rather than automatically after every narrow correction. |
| `GOV-AC-024` | Reusable accepted harnesses and evidence assets are reused or extended where applicable instead of rebuilt without need. |
| `GOV-AC-025` | New sessions reconstruct state from authoritative repository artifacts and required protected local state rather than treating conversational memory as project authority. |

Governance AC range: `GOV-AC-001` through `GOV-AC-025`; count: `25`.

## 33. v1.1 Additional Governance Negative Acceptance Criteria

| ID | Prohibited outcome |
|---|---|
| `GOV-NAC-012` | Default broad-suite reruns when exact diff analysis proves the prior evidence cannot be invalidated. |
| `GOV-NAC-013` | Reopening a closed blocker without a material delta to its governing behavior, oracle, fixture authority, dependency, or assumption. |
| `GOV-NAC-014` | Authorizing repeated patch-by-example corrections without first deriving the governing general invariant or route rule. |
| `GOV-NAC-015` | Treating a self-injected expected exception as sufficient proof of a material boundary guard when an actual execution-path mutation can bypass the oracle. |
| `GOV-NAC-016` | Relabeling candidate-reported or reused test execution as newly independently executed WORK evidence. |
| `GOV-NAC-017` | Rebuilding an accepted reusable harness or vector system without a concrete invalidation or package-specific need. |
| `GOV-NAC-018` | Relying on conversational memory as the sole authority for current project state in a new session. |

Governance NAC range: `GOV-NAC-001` through `GOV-NAC-018`; count: `18`.

## 34. v1.1 Additional Adoption Stop Conditions

Adoption must also stop on any of these conditions:

8. `GOVERNANCE_PROTOCOL_DISCARDS_VALID_EVIDENCE_WITHOUT_INVALIDATION`
9. `GOVERNANCE_PROTOCOL_ALLOWS_PATCH_BY_EXAMPLE_WITHOUT_ROOT_CAUSE`
10. `GOVERNANCE_PROTOCOL_ALLOWS_COMPLEX_CLASS_A_IMPLEMENTATION_WITHOUT_REQUIRED_CONTRACT_ENUMERATION`
11. `GOVERNANCE_PROTOCOL_WEAKENS_MUTATION_SENSITIVITY_FOR_MATERIAL_BOUNDARIES`

Stop-condition range: item `1` through item `11`; count: `11`.

GOVERNANCE_PROTOCOL_V1_1_PROPOSED_FOR_ACCEPTANCE
