# RETIRE V2 — Stage 6 Phase 1 bounded implementation decision

Date: 2026-10-27
Branch: `feature/professional-workspace-ux-first-20261022`
Design acceptance: **PASS_DESIGN_ONLY** at HEAD `af804c6278511bc0c0424ee721508a21f9eeb5e6` (independent GPT Work verdict furnished by product owner).
Normative source: `docs/ux/STAGE6_BLOCKED_VERDICT_CONTRACT_REPAIR_2026-10-26.md`, N1.1–N1.6.

## Separate implementation decision

The product owner previously delegated routine technical development decisions to the development manager. This document records a **bounded proposed implementation sequence** following accepted design, rather than implicitly treating design PASS as permission to execute code or deploy.

**Scope of first implementation package: Stage6-P1A — permission authority only.**

- Extend the **existing** `scenario_permission_preview_service` with a database-snapshot-local, read-only `derive_pension_action_permission_admission` producing N1.6 closed admission evidence.
- Consume one externally-owned caller transaction established using PostgreSQL REPEATABLE READ READ ONLY. Never open a second snapshot via public `preview()`.
- Derive current `scenario/version/decision/source/component/amount/effective_date` from existing manifest and PostgreSQL records; check exact source digest, allocation bounds, current approved ruleset and mapping and one component/action rule with `allowed` status and `BASE_PERMISSION_ALLOWED`.
- Emit deterministic N1.6 SHA-256 using the **existing permission canonical_json** function. No permission-admission persistence, no invented professional/eligibility or tax approval, no financial result.
- Keep `scenario_calculation_admission_service.assess()`, SC-03 through SC-06A semantics, existing factual pension sources and current public Preview unchanged.
- Validate with targeted offline unit/contract tests: allowed component amid mixed product, blocked component, unknown product mapping, stale source, change in amount/version/ruleset, date before ruleset, overallocated source, forged fingerprint, no duplicate snapshot.
- Run targeted local tests only during the implementation; **do not run repository-wide CI or trigger CI per commit**. Do not merge or deploy in this package.

**Subsequent separately gated slices**, in dependency order:
1. Stage6-P1B — N1.3 authenticated single-planner admission storage: append-only revisions, CAS and version invalidation, migration and tests.
2. Stage6-P1C — canonical M1/M2/T1/T2/P1 producers and one-source scenario planning result; preserve existing factual planning hashes and calculator.
3. Stage6-P1D — narrowly accept `scenario_decision_balance_ratio` in PTE, bind N1.4 read-only BLOCKED/RESULT_READY output, negative and contract tests. No generic/insurer automatic lookup or capital/tax logic.
4. One consciously authorized **cost-controlled** CI run and independent functional/security acceptance after slice integration; separate decision for merge and any Railway deployment.

## Stop and fail closed

If existing ownership makes N1.6 implementation require a new generic permission engine, alteration of `assess()`, accounting conversions, or unconstrained ORM/autoflush writes, **stop that slice and report a concrete mismatch**. Do not reinterpret PASS_DESIGN_ONLY as authority to relax security. CPI indexation until withdrawal is deferred to a separately accepted product package. No Phase 1 auto-coefficient lookup, no fallback 200.

## Status

`STAGE_6_DESIGN=ACCEPTED`
`STAGE_6_IMPLEMENTATION=NOT_YET_STARTED`
`FINANCIAL_CALCULATION=NOT_AUTHORIZED`
`PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED`

This planning record contains no code changes, CI runs, merges or deployments.
