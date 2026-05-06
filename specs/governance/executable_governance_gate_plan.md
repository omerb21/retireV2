# Executable Governance Gate Plan

This file does not implement executable checks.

## Gate A: Spec Persistence Gate

Purpose: Verify that every accepted authority decision required by a phase is persisted in repository specs before phase resume or closure.

Future check concept: Compare phase closure materials and drift register entries against persisted spec files.

Inputs: Phase authority files, governance drift register, phase closure checklist, commit references.

Pass condition: All required authority decisions are persisted or have Supervisor-recorded exceptions.

Fail condition: Any active authority decision exists only outside repository specs without exception.

Implemented now: no

## Gate B: Drift Register Gate

Purpose: Verify that known drift is either resolved or tracked with deterministic ownership and target phase.

Future check concept: Validate required drift register fields for every open drift item.

Inputs: specs/governance/drift_register.md, system integrity audits, phase closure package.

Pass condition: Every known drift item has id, classification, risk, owner phase, blocking status, mitigation, required decision, target phase, source evidence, and status.

Fail condition: Any known drift is missing, unclassified, ownerless, or has unclear blocking status.

Implemented now: no

## Gate C: Contract Compliance Gate

Purpose: Verify that runtime flows use approved contracts and do not bypass required contract fields or output shapes.

Future check concept: Inspect schema definitions, imports, runtime return types, payload builders, and tests for contract-aligned usage.

Inputs: backend/app/schemas, backend/app/engines, backend/app/services, backend/app/api, backend/tests, relevant specs.

Pass condition: Required contract objects are used where specified and all deviations are registered or excepted.

Fail condition: Required contract usage is bypassed, duplicated, contradicted, or untracked.

Implemented now: no

## Gate D: Architecture Boundary Gate

Purpose: Verify approved responsibility boundaries between API, service, engine, persistence, and tests.

Future check concept: Trace dependency directions and data ownership for active phase flows.

Inputs: API routes, service modules, engines, persistence models, tests, architecture specs, drift register.

Pass condition: Active phase boundaries are respected or boundary risks are registered with target decision phase.

Fail condition: Active phase implementation crosses forbidden boundaries without authority.

Implemented now: no

## Gate E: Phase Closure Gate

Purpose: Verify that a phase can close only after test, repository, spec, drift, architecture, contract, and Supervisor closure evidence is recorded.

Future check concept: Validate closure package fields against the phase closure checklist.

Inputs: specs/governance/phase_closure_checklist.md, test evidence, git status, commit references, drift register, Supervisor closure record.

Pass condition: Closure package addresses all required fields or records Supervisor exception.

Fail condition: Closure package omits required fields and has no Supervisor exception.

Implemented now: no
