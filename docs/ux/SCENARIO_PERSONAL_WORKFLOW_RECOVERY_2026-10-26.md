# RETIRE V2 — return to the single-planner workflow

**Decision:** owner rejected the SC-06B review lifecycle/supersession mechanism. **SC-06B is cancelled.** Do not reopen accepted SC-03–SC-06A backend security or introduce SaaS workflow machinery.  
**Status:** scoped factual discovery / next UX slice contract; NOT financial implementation or deploy authorization.  
**Baseline:** feature/professional-workspace-ux-first-20261022, SC-06A PASS at `1b1d6cf7e6b8363c37c995cab0b8d1f97c9aec1c`.

## Current implementation — inspected, not assumed

1. `frontend/src/pages/RetirementWorkspaceScreen.tsx` renders `ScenarioDraftPanel` in the `scenario` phase. This already performs real server-backed creation, selection, editing, duplication and archiving of **non-authoritative** scenario drafts through `/api/clients/{client_id}/scenario-drafts`.
2. The same phase **also renders a distinct browser-only mock scenario workflow** (including `mockAlternatives`, `mockActiveId`, `mockAmount`, and `mockSource`). Those alternatives are not persisted, and the Results phase also contains mock comparison summaries.
3. `frontend/src/components/ScenarioDraftPanel.tsx` has a saved-draft comparison showing totals of selected draft allocations. It explicitly warns that these amounts are **not** pensions, liquid capital, tax or eligibility.
4. The actual `POST /canonical-conversions` mutates canonical balances and must never be used for hypothetical scenario operations.
5. SC-05/SC-06A establish evidence and documentary-readiness boundaries only; they do **not** authorize a coefficient lookup, scenario cashflow or financial result.

## Immediate next vertical slice — UX, not engine

**Goal:** present one clear planning path for one professional, using the **saved scenario drafts**, not two simultaneous scenario systems.

### Bounded work

- In the scenario stage, make `ScenarioDraftPanel` the single visible editor. Retire the separate mock editor only after confirming selected component transfer and editing workflows still work with saved drafts.
- Preserve the user's actual workflow: select a source balance in the single portfolio ledger; create or open a saved alternative; allocate a partial amount to pension/capital; edit or delete a decision; duplicate an alternative; return and compare draft allocations. No approval chain or lifecycle workflow.
- Show factual current component balances independently from hypothetical decisions. Never mutate the portfolio through scenario controls.
- Results stage must clearly distinguish **draft allocation comparison** from **financial calculation not yet available**, using saved alternatives as its only source; do not show browser-only alternatives as real plans.
- Errors and stale source/version conflicts must be transparent and recoverable; retain unsaved input when an API call fails.

### Acceptance tests before owner UX review

1. A named scenario and its decisions survive refresh (server persisted), remain client-scoped and are version-checked.
2. Create, edit, delete a decision; duplicate a scenario and edit the duplicate without modifying original.
3. Component selection from ledger is actionable in the saved scenario editor, or explicitly disabled rather than silently leading to the discarded mock.
4. Partial allocations and residuals are computed only as **non-authoritative display math** from exact decimal strings, with no invented pension/tax values.
5. Draft comparison never mixes temporary mock and saved server identities and remains honest about missing financial results.
6. A hypothetical decision never calls canonical-conversions POST or changes real component balances.
7. Client switch/refresh never displays another client's decisions; stale response guards and errors verified.
8. Focused TypeScript/Vite tests first, then one owner walkthrough with synthetic client. No per-commit CI.

## Explicit out of scope

- SC-06B supersession, auditor roles or multi-approver flows.
- New PostgreSQL migrations or ACLs.
- Approval/admission transitions, coefficient lookup, pensions, NPV, M09/M10 financial engines or 161d.
- Master merge, production deploy or full CI.

**Next implementation rule:** modify the UX in a cohesive bounded patch with focused tests, rather than another long chain of provenance/backend packages. Do not claim this diagnostic note is a passed frontend change.

## Stage 5 closure and Stage 6 existing-engine handoff — 2026-10-26

**Stage 5 evidence:** 9/9 `ScenarioDraftPanel.workflow.test.tsx` UI component tests passed, including source handoff, create, allocation, edit, duplicate, removal on clone, comparison and remount with server API mocks. 2/2 `test_scenario_draft_postgresql.py` tests passed with isolated PostgreSQL 16; the second exercised actual FastAPI HTTP routes, separate client isolation, optimistic concurrency, save/edit/duplicate/delete-decision, and a new HTTP client loading the persisted state. This is **not** a live browser E2E run; do not claim otherwise. No financial result was evaluated.

**Stage 6 scope (planning only; no execution authority):** reuse existing canonical producers, not M09/M10 historical engines and not a new financial calculation engine.

| Existing producer | Current input/authority | What the saved scenario does NOT yet supply |
| --- | --- | --- |
| `pension_target_date_execution_service.execute_from_planning_result` | Verified planning-result/source and monthly-basis plus temporal fingerprints | Verified scenario-specific planning result, source and authority bindings |
| `capital_projection_execution_service.execute` | Verified capital plan and source projection basis | Authorized per-scenario capital plan, full source coverage and source-basis authority |
| `retirement_monthly_income_gap_service.assess` | Fresh session and verified target-date/planning fingerprints | Admitted scenario-target and comparison context |
| `fixation_service.calculate_fixation_payload` → `fixation_engine` | Independent client-specific tax/fixation admission | No automatic authority to perform fixation calculations from a scenario decision |
| `scenario_engine_compatibility_service.assess_engine_compatibility` | Read-only signature and inert manifest compatibility | Explicitly returns `execution_allowed=False`, `SCENARIO_ADAPTER_MISSING`, `NO_SCENARIO_ENGINE_ADMISSION_CONTRACT`; it does NOT run financial engines |
| `scenario_calculation_admission_service.assess` | Read-only actual draft and canonical product sources | Returns `assessment_state=blocked`, `financial_result=None` and permission/professional/tax blockers |
| `scenario_snapshot_candidate_service` and scenario coefficient review services | Evidence-only database-owned snapshot/review artifacts | Explicitly inert, no coefficient/cashflow/scenario execution permission |

**Decision / independent acceptance input:** before any Stage 6 implementation, the independent professional acceptance route must specify exactly which existing producer can execute on which verified scenario inputs; whether allocations to pension vs capital are professionally admissible, the coefficient lookup authority, date/price/tax context, source balances and over-allocation handling, dependency/fingerprint freshness, the permitted output semantics, and fail-closed behavior. It must determine how the current inert manifest becomes a verified adapter input **without changing canonical source facts**. No existing acceptance package is reopened and no SC-06B supersession workflow is reinstated.

**Boundary:** Stage 6 financial execution, scenario adapter, coefficient lookup and deployment remain `NOT_AUTHORIZED`. The central development conversation may maintain UX and write read-only scoped tests, but cannot self-approve financial logic or substantive architecture. Do not treat structural compatibility as permission to calculate.
