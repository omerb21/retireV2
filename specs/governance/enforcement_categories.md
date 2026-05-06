# Governance Enforcement Categories

## BLOCKING_GOVERNANCE_DRIFT

Definition: A governance or authority traceability gap that prevents an approved phase from safely resuming or closing.

When it applies: Use when required authority is missing, conflicting, or not persisted, and the missing authority affects an active gate.

Blocking behavior: Blocks the affected phase until the drift is resolved or Supervisor grants an explicit exception.

Allowed action: Persist missing authority, record the resolution, or obtain Supervisor exception.

Forbidden action: Continue the affected phase while the drift remains unresolved and unexcepted.

## TRACKED_DEFERRED_DRIFT

Definition: A confirmed drift that does not block the current phase after it is recorded with owner phase and target decision point.

When it applies: Use when the issue is real but belongs to a later approved phase or decision gate.

Blocking behavior: Does not block the current phase after registration; blocks the target phase if still unresolved at that phase gate.

Allowed action: Track with owner, required decision, target phase, source evidence, and status.

Forbidden action: Treat as resolved without a recorded decision or correction.

## ACCEPTED_TEMPORARY_POLICY

Definition: A Supervisor-approved temporary policy with explicit scope, limitations, and replacement condition.

When it applies: Use only when Supervisor accepts a temporary rule needed to proceed within a bounded phase scope.

Blocking behavior: Does not block within its approved scope; blocks use outside that scope.

Allowed action: Apply exactly within the documented scope and preserve its limitations.

Forbidden action: Generalize the temporary policy into default behavior or use it as implicit authority elsewhere.

## DECISION_REQUIRED

Definition: A known issue that requires Supervisor or architecture decision before implementation may proceed.

When it applies: Use when multiple valid paths may exist and choosing one would create policy, contract, API, persistence, or architecture authority.

Blocking behavior: Blocks implementation in the affected area until the decision is recorded.

Allowed action: Inspect, document evidence, and request decision.

Forbidden action: Implement one option without recorded authority.

## CLEANUP_DEBT

Definition: Non-blocking dead code, duplicate helper logic, naming debt, or local cleanup that does not affect approved behavior.

When it applies: Use when the issue is real but does not alter current contracts, formulas, persistence guarantees, or phase closure.

Blocking behavior: Does not block current phase unless it becomes behavior-affecting.

Allowed action: Track for later cleanup phase or targeted hardening.

Forbidden action: Mix cleanup with controlled phase implementation unless cleanup is explicitly authorized.

## CONTRACT_ENFORCEMENT_REQUIRED

Definition: A contract usage gap where implementation must be aligned to an approved schema or interface before the affected flow is valid.

When it applies: Use when runtime code bypasses, contradicts, or omits required contract fields or output shapes.

Blocking behavior: Blocks the affected flow or phase gate until corrected or explicitly deferred.

Allowed action: Execute targeted contract enforcement within approved files and scope.

Forbidden action: Relax the contract, introduce hidden defaults, or create wrapper behavior without authority.

## ARCHITECTURE_BOUNDARY_RISK

Definition: A boundary issue where API, service, engine, persistence, or test layers may be coupled in a way that conflicts with approved ownership.

When it applies: Use when routes, services, engines, persistence, or tests bypass the intended layer boundary or duplicate responsibilities.

Blocking behavior: Blocks only if it affects the active phase gate; otherwise it must be tracked with target phase and decision.

Allowed action: Record exact boundary evidence and assign owner phase.

Forbidden action: Refactor the boundary without explicit phase approval.
