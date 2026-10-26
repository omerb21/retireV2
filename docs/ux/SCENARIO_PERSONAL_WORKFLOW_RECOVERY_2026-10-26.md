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

## Stage 6 — bounded independent acceptance instruction (ready for Work READ ONLY)

**Scope / question:** At the latest feature-branch HEAD, determine whether *any* existing, accepted canonical financial producer can consume a **saved hypothetical scenario** without inventing professional permission, source authority, pension factors, tax treatment or financial amounts. Return a precise `AUTHORIZED_NOW / BLOCKED_PENDING_DECISIONS / UNSUPPORTED_BY_EXISTING_CONTRACT` finding per producer, with file/line evidence and the smallest required next decision. **Do not implement an adapter.**

**Review sources:** this document; `docs/ux/API_CANONICAL_OPERATION_AUDIT_2026-10-26.md`; `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md`; `docs/ux/SCENARIO_CONVERSION_OWNER_DECISION_REGISTER_2026-10-23.md`; `docs/ux/SC-06_PROFESSIONAL_ADMISSION_BOUNDARY_PROPOSAL_2026-10-26.md`; actual implementation of `scenario_draft_service`, `scenario_input_manifest_service`, `scenario_snapshot_candidate_service`, `scenario_engine_compatibility_service`, `scenario_calculation_admission_service`, `pension_target_date_execution_service`, `capital_projection_execution_service`, `retirement_monthly_income_gap_service`, `scenario_coefficient_readiness_service`, and `scenario_annuity_coefficient_assessment_service`. Respect completed SC-03 through SC-06A and the cancellation of SC-06B.

**Required reviewer output (concise):**
1. Map exact saved-draft decision fields → inert DB-owned manifest → candidate → each existing engine's *actual* callable input, provenance and admission obligations; identify where there is no authorized mapping, without filling gaps.
2. Separate arithmetic/formula reuse from permission to invoke it, from authoritative source revision, from pension coefficient entitlement, from tax/161d; confirm non-mutating hypothetical behavior and explicit residual of unallocated funds.
3. Reconcile previously approved owner decisions O-02 through O-08 with current guardrails; clearly flag unresolved O-01 and any genuine new owner choice. Do not assume that approved product UX rules authorize tax outputs.
4. Recommend **one smallest viable calculation capability** (or `NONE` if blocked), name its **existing canonical producer**, negative tests and required professional approval; never propose M09/M10 resurrection or a parallel engine.
5. Classify each outstanding blocker as `SOURCE_EVIDENCE`, `PROFESSIONAL_DECISION`, `CALCULATION_CONTRACT`, or `TECHNICAL_WIRING`; include evidence and acceptance owner.
6. State explicitly whether a new implementation can be authorized now. Default to **NOT AUTHORIZED** until independently accepted with an explicit scope.

**Reviewer constraints:** independent Work, READ ONLY; do not change code, database, migrations, financial rules, privileges, branch, CI or deploy. No new governance package; this is the handoff under the existing acceptance route. The central development conversation may not treat its own mapping as independent approval.

## Independent Stage 6 verdict received — BLOCKED (owner-provided Work review)

**Reviewed branch HEAD:** `9e42741aa217be3774827550a090d778d15c53e3`; tree `cadcd8d77c3c97f7a38e3d74a72c1942bc79f9e7`. The reviewer performed READ ONLY inspection; no tests/CI. **Verdict: BLOCKED.** No canonical producer currently has authority to calculate from a persisted hypothetical scenario. Review evidence is owner-supplied, not an implementation approval.

**Permitted today:** base permission preview and source/readiness/manifest/candidate evidence ONLY; unallocated residual may be shown as draft arithmetic, not financial forecast. **Not permitted:** scenario coefficient lookup, financial result, calculation adapter, tax/161d, capital forecast, gap/surplus, M09/M10 execution or deployment.

### Proposed narrow next contract — SINGLE_PENSION_DECISION_TARGET_MONTHLY_ESTIMATE (DESIGN ONLY)

**Goal:** Evaluate ONE `pension` decision from an existing saved draft, with a verified canonical source, using the existing `pension_target_date_execution_service.execute_from_planning_result`. Never infer the monthly amount from capital alone or turn a draft allocation into a factual conversion.

**Conditions required BEFORE authorization:**
1. Same DB-owned PostgreSQL `REPEATABLE READ READ ONLY` snapshot for scenario, decision, product/component, current permission and ruleset, pension election/review/authority, and target date. No caller-asserted provenance or authority.
2. Bind an exact current base permission to `scenario_id`, decision/version, product/component/version/fingerprint, chosen action, allocated amount, effective date, and approved ruleset fingerprint; reject any mismatch, expiry, unknown type, insufficient balance or over-allocation. No blanket approval from a documentary review.
3. Explicit owner-authorized coefficient source and selection conditions. **Never** use `annuity_coefficient_service` fallback `200`, heuristic match or silent manual-review bypass; missing exact permitted coefficient must block (unless separately approved professional input contract is independently accepted).
4. Verified adapter supplying the incumbent executor's exact input authority: monthly amount basis; canonical source identity; temporal authority/retirement target; all required fingerprints and provenance. Neither inert manifest nor syntactically compatible payload is execution admission.
5. Define output semantics as a provisional *single-decision gross monthly estimate* ONLY if professionally authorized; no tax, net pension, 161d, NPV, capital output, aggregated scenario total, gap/surplus or eligibility representation. Otherwise output no number.
6. Persist no portfolio changes. Any persisted result identity, if independently authorized, must be tied to client/scenario/decision/version/manifest and input-authority fingerprints, be invalidated by source/decision/ruleset changes and never appear current after staleness.

**Open owner decisions — DO NOT ASSUME:**
- **P1:** Which precise coefficient evidence is authoritative: exact, current, versioned provider/plan-specific match only? What qualifies as proof of current applicability?
- **P2:** What is the allowed outcome when there is no such coefficient, or the record says `manual_review_required`? Safe proposed default: **BLOCKED, no number**, until separately admitted professional input.
- **P3:** Which approved professional event/review grants permission to use an elected coefficient for a specific draft decision? Documentary SC-06A alone does NOT.
- **P4:** Is the result explicitly a **gross, nominal, scenario-only estimated monthly pension** tied to one retirement date and without any tax/eligibility claim? What exact date/basis is authorized?
- **P5:** What authoritative input maps the decision's capital amount to the executor's required `monthly_amount_basis` and its fingerprints? This cannot be reverse-engineered from an unauthorised fallback coefficient.

**Existing owner decisions:** O-02–O-08 remain binding but are NOT tax/calculation authority. O-01 product-type discrepancy remains unresolved; any first slice must restrict itself to already technically accepted types and fail closed on any unknown/ambiguous product type.

**Independent reviewer must next:** validate owner answers and produce a bounded, versioned input/admission/output/negative-test contract with citations, using current canonical producers only. Minimum checks: cross-client, stale/coherent rehash, preview/ruleset binding, amount/permission, missing factor and review, no engine call on failed gate, Decimal exactness, no DML, source integrity, deterministic invalidation, no M09/M10/fixation/tax calls. No new governance machinery, no CI, no implementation until PASS plus explicit owner authorization.

**Status:** `STAGE_6_IMPLEMENTATION=NOT_AUTHORIZED`; `COEFFICIENT_LOOKUP=NOT_AUTHORIZED`; `FINANCIAL_CALCULATION=NOT_AUTHORIZED`; `SCENARIO_CALCULATION_ADAPTER=NOT_AUTHORIZED`; `PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED`.
