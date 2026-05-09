# Governance Operating Rules (Binding)

This file is binding governance operating policy.
It applies system-wide.
It applies to all future phases.
It applies to future changes affecting previously closed phases.
It applies to implementation proposals, documentation-only governance tasks, bug fixes, refactors, and persistence/API/service/engine/schema work.
It institutionalizes already accepted governance rules.
It does not create new runtime authority.
It does not reinterpret prior Supervisor decisions.
It does not escalate deferred drift.
It does not authorize implementation.
Repository governance authority is authoritative only within explicitly persisted scope.
If repository authority is insufficient, work must stop and request a decision.
Supervisor approval remains supreme for executable authorization.
No governance artifact may independently authorize implementation.
Governance institutionalization strengthens consistency, not implementation permissiveness.
Binding governance operating rules are repository authority infrastructure, not runtime implementation semantics.

## 1. Repository SSOT Rule
- Persisted specs and governance artifacts are authoritative.
- Conversation memory cannot override repository authority.
- Missing authority means stop and request decision.
- Repository governance authority is authoritative only within explicitly persisted scope.

## 2. Closed Phase Protection Rule
- Closed phases remain protected.
- Work touching closed Phase 4 / Phase 5A / Phase 5B / Phase 5C authority must state explicit approval basis.
- No silent reopening of closed phases.

## 3. Contract Authority Rule
- Every task must state whether contracts are touched.
- Approved contracts must not be bypassed with local dicts/models unless already accepted or separately approved.
- New local shapes must be classified as accepted boundary, drift, or blocker.

## 4. Runtime Authority Anchor Rule
- Accepted runtime authority is implementation anchor.
- Future architecture targets are not current runtime requirements.
- Runtime semantic changes require explicit approval.
- Accepted runtime authority has supremacy over cleanliness-driven theoretical redesign.

## 5. Runtime Semantics vs Internal Mechanics Rule
- Every implementation proposal must classify runtime semantics change: yes/no.
- Every implementation proposal must classify internal mechanics change: yes/no.
- Internal cleanliness alone cannot justify redesign.

## 6. Drift Register Rule
- Every task must state which drift items are referenced, touched, resolved, deferred, or escalated.
- No drift item may be silently resolved.
- DRIFT-005 escalation requires observable runtime instability evidence.
- DRIFT-002 through DRIFT-007 remain tracked unless explicitly changed by approved scope.

## 7. No Redesign By Cleanliness Rule
- Architecture cleanliness concern alone cannot justify implementation.
- Redesign requires evidence that accepted runtime authority is insufficient.
- Theoretical architectural preference cannot silently supersede accepted operational authority.

## 8. No Implementation By Phase Name Rule
- Being in Phase 6 does not justify persistence implementation.
- Every implementation proposal must prove need, scope, authority, and expected behavior.

## 9. Test Selection Governance Rule
- Test scope must be justified.
- Filter-review-before-execution is required when pattern-based test selection is used.
- Broad regression expansion requires explicit justification.

## 10. Verification Failure Classification Rule
- Test failure does not automatically justify redesign.
- Failures must be classified as authority failure, verification-scope mismatch, stale test assumption, governance mismatch, deferred concern interaction, or actual implementation blocker.

## 11. Commit Discipline Rule
- No commit without controlled commit instruction.
- Working-tree state and index state must be distinguished before staging.
- Every commit must be limited to approved files.

## 12. Governance Durability Rule
- Governance artifacts must preserve runtime authority continuity lineage.
- Governance durability tasks must classify whether they strengthen authority persistence or authority semantics.
- No executable authority originates from alignment artifacts unless explicitly approved.
- Governance institutionalization strengthens consistency, not implementation permissiveness.

## 13. Phase Closure Rule
Every closure must specify:
- what was done
- what was not done
- what authority was preserved
- what drift carries forward
- whether implementation is authorized

Also:
- Closure does not imply next-phase execution authorization.

## 14. Future Implementation Proposal Rule
Every executable scope proposal must include:
- exact files potentially touched
- exact behavior targeted
- runtime semantics change: yes/no
- internal mechanics change: yes/no
- drift referenced/touched/resolved/deferred
- source authority
- accepted runtime authority preserved
- tests required
- stop conditions
- commit boundaries
- statement that execution requires separate Supervisor approval

## 15. Binding Rules vs Phase-Specific Temporary Constraints
- Binding governance rules are distinct from phase-specific temporary constraints.
- Binding rules apply system-wide unless superseded by persisted Supervisor authority.
- Phase-specific temporary constraints apply only to their approved scope and cannot override binding governance rules without explicit Supervisor approval.

## 16. Supervisor Approval Supremacy
- Supervisor approval remains supreme for executable authorization.
- No governance artifact may independently authorize implementation.
- Readiness to propose execution is not authorization to execute.
