# RETIRE V2 — SC-06 proposed boundary (design only)

Status: **DESIGN ONLY — NOT IMPLEMENTATION AUTHORIZATION**  
Predecessor: SC-05 accepted at `389a4e77f0321a44e9211a13bbc96338188d7410` after independent Work PASS.  
Scope: **professional authority admission for a scenario pension-coefficient candidate**, without lookup, financial outputs or scenario calculation.

## 1. Why SC-06 follows SC-05

SC-05 delivered DB-owned pension-election drafts, a source/input inventory, an inert gate bridge and append-only documentary professional reviews. SC-05 deliberately disabled the dictionary-based coefficient lookup and did not confer execution authority. **A documentary review is not authorization.**

SC-06 must not silently reinterpret a stored `reviewed_for_candidate` decision as permission to execute.

## 2. Bounded outcome

Propose a single **read-only, database-derived authority assessment** that either reports a narrowly scoped, verified professional admission record or returns explicit blockers. The assessment must never invoke `coefficient()`, create monetary results, update canonical portfolio facts or provide a calculation adapter.

Review/approval of an executable decision and legal/financial authorization are **separate professional policy decisions**. Until their precise meaning is authorized by the owner, the only permitted output is **NOT_AUTHORIZED**.

## 3. Input and trust contract

- Request/caller may supply only routing identity: `client_id`, `scenario_id`, `decision_id` and a read-only context or session factory owned by the server; no hashes, source flags, actor strings or derived facts.
- One PostgreSQL-owned `REPEATABLE READ READ ONLY` snapshot, at the same ownership boundary approved in SC-03/SC-04. Never concatenate outputs from separate snapshots.
- Derive current scenario version, pension decision identity and source fingerprint, current election and its complete fingerprint, product version and explicit profile facts directly from canonical DB state.
- Read professional documentary records from the same snapshot; validate exact record integrity, provenance, version and actor linkage. Stale, missing, conflicting or `rejected` evidence must block.
- A matching documentary record must **not** by itself grant permission. A distinct approved admission contract and authenticated professional action would be required in a later authorized increment.

## 4. Fail-closed result

Proposed envelope `SCENARIO_COEFFICIENT_AUTHORITY_ASSESSMENT_V1`:
- `state: BLOCKED | UNRESOLVED`
- `blockers: list[str]` (stable reason codes)
- `authority_state: NOT_EVALUATED`
- `execution_allowed: false`
- `coefficient_candidate: null`
- `financial_result: null`
- `planning_snapshot: null`
- minimal scenario/decision/fingerprint identifiers **only when DB verified**.

This is not a new coefficient lookup service; `scenario_annuity_coefficient_assessment_service` remains blocked as accepted in SC-05.

## 5. Mandatory negative tests for a future authorized implementation

1. Forged or stale fingerprints/dict flags cannot be accepted or passed to `coefficient()`.
2. Foreign-client scenario, missing source/election, current version mismatch, replaced election, altered product/profile/source: block.
3. Missing, rejected, tampered or stale documentary review: block.
4. Matched documentary review: still `execution_allowed=false` and no coefficient lookup.
5. Consistent single PostgreSQL read-only snapshot; refuse unsupported database or pre-used transaction.
6. No state mutation, no new public API or application-role privilege elevation.
7. SC-03/SC-04 snapshot and source identity contracts unchanged; SC-05 accepted head is the regression baseline.

## 6. Scope exclusions

No pension-factor lookup or fallback, financial calculation, cashflow, 161d/tax eligibility, NPV, report generation, frontend workflow activation, scenario calculation adapter, master merge, production migration/deployment or new ACL privileges.

## 7. Acceptance and authorization gates

- Before implementation: owner/product authority must explicitly decide whether the next increment is a **read-only status/authority assessment** or a future **professional admission workflow**, and what evidence counts as a valid professional admission.
- Implement one bounded vertical slice only after that choice; no speculative permission state.
- Targeted tests on disposable local PostgreSQL, **one** consolidated independent Work Medium READ ONLY acceptance at the package boundary.
- No CI/merge/deploy without explicit separate approval.
