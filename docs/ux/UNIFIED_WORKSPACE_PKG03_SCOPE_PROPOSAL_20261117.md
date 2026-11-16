# RETIRE V2 | Unified Workspace PKG-03 | Proposed scope for supervisor approval

**Status:** PROPOSAL ONLY / NOT AUTHORIZED FOR IMPLEMENTATION  
**Directive:** 196  
**Reviewed accepted HEAD:** `c2c44bed48267fa56cf8d41f19686cee1bfc810d`  
**Audience:** one authenticated internal retirement planner; not clients.

## Derivation from existing product plan

- `docs/ux/PROFESSIONAL_WORKSPACE_INTEGRATION.md` defines the five-stage professional journey: client, portfolio, supplementary facts, **scenario decisions**, **comparison**. Its named future slices are scenario domain contracts, backend integration, report generation and professional review.
- In current `frontend/src/pages/RetirementWorkspaceScreen.tsx`, stage 3 contains the accepted PKG-02 factual editors; stages 4 and 5 already mount `ScenarioDraftPanel` for saved alternatives and a results view.
- `frontend/src/components/ScenarioDraftPanel.tsx` already supports server-persisted scenario drafts, versioned decisions, scenario selection, a conditional Stage 6 internal results panel and a saved-scenario comparison panel gated on explicit capability detection.
- `GET /api/clients/{id}/scenario-drafts/{scenario_id}/calculation-admission` exists and is deliberately **evidence only**: `backend/app/services/scenario_calculation_admission_service.py` returns `assessment_state=blocked` and `financial_result=null`; it does not authorize execution.
- `backend/app/api/m09_cashflow_routes.py` is Archive Only, not a current calculation producer. `backend/app/api/scenario_stage6_internal_routes.py` explicitly says staging-only, not mounted by default or in Production.
- `docs/ux/SCENARIO_PERSONAL_WORKFLOW_RECOVERY_2026-10-26.md` records Stage 6 integration as blocked until separate professional permission, source, coefficient, input/output contract and supervisor acceptance. `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md` forbids invoking canonical factual conversions as scenario mutations.

**Next capability not yet fully integrated:** An unambiguous *professional readiness/currentness summary for each saved scenario* in the unified Results stage, tied to real server-side admission evidence and correctly separating draft allocations, blocked calculations, archived runs and explicitly authorized results. This is the next bounded preparatory slice **before** any scenario financial-comparison implementation.

## Proposed PKG-03: Unified Scenario Readiness and Result Authority Boundary

### Scope authorized for review, not yet for coding

1. Reuse existing saved `scenario_id`, client ID, version and server-owned status. No parallel browser-only scenario identity and no new money engine.
2. Present existing read-only calculation-admission evidence for the selected scenario in Stage 4 and Stage 5: reason codes, stale/missing source references, revalidation required, and whether a financial result is **unavailable**. Do not translate an evidence-only state into approval or return value.
3. Clearly distinguish **saved draft decisions and allocation totals** from **actual financial outputs**. In production, no gross pension, tax, 161D, cashflow, NPV, or M09/M10 result may appear unless its separate existing environment-specific currentness and authority contract permits it.
4. Preserve the existing Stage 6 capability gate and avoid bypassing restricted endpoints, lifecycle review, financial authorization or tenant scoping. UI must not invoke POST `canonical-conversions` for a hypothetical decision.
5. Use one client-specific read-only fetch with cancellation/race protection and no draft writes. On 404, 409, missing authentication or unexpected admission response, display an explicit blocked/unknown state; never present a stale cached PASS.
6. Keep legacy routes functional. Preserve draft content, versioned save conflict behavior and ability to return from comparison to planning.

### Explicitly out of scope

- New computation engine, M09/M10 replacement, pension coefficient lookup, tax/fee formula, exemption/fixation logic, 161D, PDF or client-facing report.
- Database migrations, schema changes, canonical conversion mutations, scenario calculation execution, authorization escalation, modifying historical runs.
- `FIXATION-CURRENTNESS-001` remediation; it is a separate product decision.
- Any declaration that an existing evidence-only `assessment_state` is a professionally usable financial result.

### Current implementation versus gap

| Component | Current verified code status | PKG-03 proposed delta |
|---|---|---|
| Unified workspace stage 4 | Real saved scenario draft editing and selection already mounted | Small, explicit admission/currentness read-only indication only |
| Unified workspace stage 5 | Saved draft result panel; Stage 6 view is feature-gated | Make the difference between draft evidence, blocked financial execution and approved result unmistakable |
| Scenario draft API | Existing client-scoped, versioned draft reads/writes | Reuse only; no new writer |
| Calculation-admission API | Existing PostgreSQL read-only assessment, financial result null | Read and display evidence; do not elevate authority |
| Stage 6 internal producer | Staging-only conditional capability | No production enablement and no bypass |
| M09 cashflow | Archive Only | No integration as a current result |
| PKG-01 / PKG-02 | Accepted isolated workspace and fact editors | Preserve them; do not retest unchanged suites |

## Prerequisites and permission gates

- Supervisor must expressly approve a narrow *read-only readiness presentation* package before code changes, with exact allowed code files and test scope.
- Any subsequent genuine scenario calculation or financial comparison requires a **different** explicit Product Decision and professionally approved source/coefficients/permissions/input-output/currentness contracts. PKG-03 by itself does not authorize those capabilities.
- Access must remain scoped to authenticated internal planner and selected `client_id`/`scenario_id`, preserving fail-closed cross-client behavior.
- Original source balances, evidence, retirement decisions and tax figures must not be modified by read-only display.

## Proposed files only (subject to supervisor confirmation)

| Area | Proposed path | Change |
|---|---|---|
| UI | `frontend/src/components/ScenarioDraftPanel.tsx` | Render precise admission/currentness evidence in planning and results views |
| UI integration | `frontend/src/pages/RetirementWorkspaceScreen.tsx` | Only if needed to pass selected scenario identity and client-scoped refresh signals |
| API client | `frontend/src/api/scenarioDraftsApi.ts` | Add a typed read-only GET helper for existing `calculation-admission` route |
| Tests | `frontend/src/components/ScenarioDraftPanel.workflow.test.tsx` | Focused route behavior, loading, 409, stale, client A-B-A and no financial output |
| Tests | `frontend/e2e/pkg03-readiness.spec.ts` (NEW) | Synthetic current client, saved draft, stale/blocked admission display; no live financial engine |
| Acceptance doc | `docs/ux/UNIFIED_WORKSPACE_PKG03_ACCEPTANCE.md` (NEW, post implementation only) | Exact scope, evidence and outstanding non-goals |

Paths are candidates; verify their existence and contracts again at implementation HEAD. **No backend, model, migration, engine or permission change is proposed by this first slice.**

## Acceptance conditions for a future approved execution directive

1. A selected saved scenario displays its exact client-scoped ID/status/version and server admission assessment; states `blocked`, `needs_revalidation`, `unavailable`, and `unknown` never display as professionally approved.
2. A factual input change that changes current admission identity updates the visible status on refetch; historical responses cannot overwrite later client/scenario selection.
3. Draft decisions and original canonical balances remain unchanged; no backend write on read-only readiness checks.
4. A failure or unrecognized API shape fails closed, preserves unsaved scenario edit and does not show fabricated pension/tax/comparison figures.
5. The comparison view cannot use historical M09 archive runs or hidden internal Stage 6 endpoints as current production financial authority.
6. Targeted frontend tests plus narrow synthetic browser verification pass; demonstrate no regressions to PKG-01/02 contracts without restarting full accepted suites.
7. Enumerate exact files, SHA and CI run; obtain independent supervisor acceptance before deployment.

## Stop conditions

Stop before implementation if the existing admission API cannot provide bounded truthful readiness evidence without altering calculation models or authority, if required change extends beyond proposed files, if sensitive sources would be exposed, or if a financial result is implicitly promised. Bring the exact blocker to the supervisor rather than expanding PKG-03.

**Decision requested:** approve/revise/reject this *read-only scenario readiness* PKG-03 scope. No implementation authorization is implied by this proposal. A full financially calculated comparison remains a later, separately gated milestone.
