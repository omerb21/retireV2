# RETIRE V2 — Stage 6 contract package completion and independent review gate

**Branch**: `feature/professional-workspace-ux-first-20261022`
**Status**: CENTRAL CONVERSATION CONTRACT PACKAGE COMPLETE; INDEPENDENT ACCEPTANCE NOT RUN; STAGE 6 EXECUTION BLOCKED.
**This document does not claim PASS or authorize implementation, lookup, a new API, CI, merge or deployment.**

## Package entrypoint

Review `docs/ux/STAGE6_INDEPENDENT_ACCEPTANCE_PACKET_2026-10-26.md` and `docs/ux/STAGE6_SINGLE_PENSION_DECISION_MONTHLY_ESTIMATE_CONTRACT_2026-10-26.md`, together with `docs/ux/LEGACY_MANAGER_COEFFICIENT_COVERAGE_MATRIX_2026-10-26.md` and the original handoff `docs/ux/SCENARIO_PERSONAL_WORKFLOW_RECOVERY_2026-10-26.md`.

## Central-code audit (read-only)

| Existing code | Verified role | Stage 6 constraint |
|---|---|---|
| `scenario_draft_service` | actual PostgreSQL scenario and decision owner; source fingerprints and CAS | Decisions are hypothetical; not a factual pension |
| `scenario_input_manifest_service` | derives inert scenario manifest | No authority to execute |
| `scenario_snapshot_candidate_service` | derives manifest/candidate in a read-only PostgreSQL snapshot, sums component allocations | `planning_snapshot=None`, `execution_allowed=False` |
| `scenario_coefficient_readiness_service` | SC-06A documentary readiness, exact read-only snapshot | even matching review is `MATCHED_NOT_AUTHORIZED`; execution remains false |
| `scenario_annuity_coefficient_assessment_service` | explicit fail-closed coefficient assessment | `COEFFICIENT_LOOKUP_NOT_AUTHORIZED` |
| `scenario_calculation_admission_service` | source/balance checks on actual draft | always records permission/professional/tax blockers; not an execution producer |
| `annuity_coefficient_service` | existing catalog owner; version/hash validation | defaults sex/age/year, pension chooses max id, no-match/error yields synthetic 200: unsafe for authority |
| `pension_monthly_basis_service` | canonical exact ratio and semantic/source fingerprint for *factual* manual pension sources or persisted conversions | an allocation is neither; no authority by copying structure |
| `planning_input_service` | collects actual pension sources into planning result | no scenario-derived unique pension source |
| `pension_target_date_execution_service` | existing canonical target-monthly executor | must have admitted planning result plus valid basis/temporal and five identity fingerprints |
| `scenario_engine_compatibility_service` | checks structural callable compatibility only | input shape != professional admission |

## Review-stage findings / blocker classes

1. **CALCULATION_CONTRACT**: no accepted producer presently maps a hypothetical decision's capital amount plus admitted coefficient to a scenario-owned `exact_ratio` monthly basis and source fingerprints. Direct manual pension source reuse would falsify provenance.
2. **PROFESSIONAL_DECISION**: source-specific/manual-factor selection is owner-approved in principle; the exact authenticated, decision/version-bound admission event and special option disclosure must be independently accepted. SC-06A review is documentation, not permission.
3. **SOURCE_EVIDENCE**: original policy program, rider, deposit tranche, option, age/sex, spouse details, historical factor convention must match. Historic pre-2001 original annuity annexes remain incomplete. Unknowns block the dependent decision rather than the entire scenario.
4. **TECHNICAL_WIRING**: derive a single consistent PostgreSQL snapshot and compatible five bound fingerprints without a new parallel producer, no mutation, and invalidate stale outcomes.
5. **SOURCE_EVIDENCE / LOOKUP**: current service's fallback 200 and heuristic defaults must not be used. Provider-specific verified source preferred; V1 generic is an explicitly accepted secondary planning approximation; a decision-specific manual factor is mandatory in the eventual UI.
6. **CALCULATION_CONTRACT / TEMPORAL**: a current amount divided by a coefficient is not necessarily a future-date monthly pension. Specify coefficient basis date, retirement date, any projected accumulation and temporal authority; prevent double projection.

## Acceptance criteria supplied to Work

- A **single narrowly scoped** `SINGLE_PENSION_DECISION_TARGET_MONTHLY_ESTIMATE` contract, no tax, NPV, liquidation, 161d, income gap or aggregated portfolio.
- Input mapping from real saved draft and its source evidence; professional scope and explicit source semantics; exact `Decimal`, catalog version and row, optional manual override.
- Negative tests for foreign/stale scenario, missing/wrong plan, affected source/tranche, over-allocation, fallback 200, historical inverse factor units, incorrect spouse guarantee, missing or forged semantic/source/temporal fingerprints; no engine invocation when admission is blocked.
- No new approval machinery (SC-06B canceled), no revival of M09/M10, no factual conversions, no migration, CI, merge, deploy.
- Verdict must be `PASS_DESIGN_ONLY` or `BLOCKED` with actual branch HEAD and line-based file evidence. **Neither grants automatic implementation.**

## Completion statement

Central drafting and code-based reconciliation of this bounded Stage 6 contract package are complete. **Independent Work acceptance remains outstanding because no Work execution tool is available in this chat.** No independent PASS, code implementation or financial outputs were performed. The next permitted activity is one independent Work Medium READ ONLY review against the latest branch HEAD; if BLOCKED, resolve only that exact gate. If PASS_DESIGN_ONLY, obtain explicit owner approval of an implementation slice before changing code. Never restart closed SC-03/SC-06A packages.
