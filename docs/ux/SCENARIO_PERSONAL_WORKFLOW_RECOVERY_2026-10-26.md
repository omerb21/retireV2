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
