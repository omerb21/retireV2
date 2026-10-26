# RETIRE V2 — Canonical Operation / Duplicate Mechanism Audit

**Status:** source inventory completed; **full semantic de-duplication is not yet certified.**  
**Owner requirement:** single-person retirement-planning workspace and future agent/MCP: every real business operation must have one explicit authoritative producer/action. No parallel mock/legacy/proposed execution paths marketed as equivalent.

**Repository branch:** `feature/professional-workspace-ux-first-20261022`. Source inventory based on all 15 `backend/app/api/*_routes.py`, frontend `src/api` clients, `RetirementWorkspaceScreen.tsx`, `ScenarioDraftPanel.tsx` and the accepted governance notes.

## Confirmed duplicate mechanism — P1 for UX clarity

`RetirementWorkspaceScreen.tsx` renders both:
- **Canonical saved scenario drafting:** `ScenarioDraftPanel` with `scenarioDraftsApi` routes `GET/POST /api/clients/{client_id}/scenario-drafts`, `PUT /{scenario_id}`, `POST /duplicate`, `POST /archive`. Data saved in PostgreSQL, versioned, not financially authoritative.
- **Legacy browser-only demo:** `mockAlternatives`, `mockActiveId`, `mockSource`, `mockAmount`, `startMockScenarioFromSelection`, `previewWholePlan` and a second draft-comparison rendering in Results. Not persisted and disappears on refresh.

**Decision:** server-saved scenario drafts are the ONLY future user-visible scenario editing action. Eliminate the browser-only mock alternative as a separate workflow and route selected portfolio component into the canonical saved editor. Results must compare saved draft summaries only and explicitly show financial outcomes as not yet calculated.

## API/producer map — assessed, not all interchangeable

| User action | Canonical producer or status | Noncanonical path / risk |
| --- | --- | --- |
| Correct factual pension-product amounts | `PUT /api/clients/{client_id}/pension-products/{product_id}` | `POST /pension-products/save-selected` is an atomic **multi-product batch** operation that calls the same `_update_locked` producer as single-product PUT after a version preflight. These are two granularities of one canonical write rule, **not two competing business engines** |
| Create/edit/archive hypothetical scenario | `/api/clients/{client_id}/scenario-drafts` family | Browser-only mock editor **confirmed duplicate UX** |
| Authoritative factual canonical conversion | `POST /api/clients/{client_id}/canonical-conversions` | Must never be a scenario-simulation producer |
| Permission-only scenario conversion preview | `POST /api/clients/{client_id}/scenario-conversions/permission-preview` | Distinct from executing canonical conversion and distinct from editing draft |
| View historical conversion | `GET /api/clients/{client_id}/m06/*` | Archive-only read, not a second conversion writer |
| View archived cashflow/comparison | `GET /api/clients/{client_id}/m09/*`, sealed `m10` | Archive-only or sealed; no live scenario financial calculation |
| Planning base date and retirement target | `/retirement-planning-input/target-date` vs `/retirement-income-readiness/target` | **Confirmed separate concepts:** `retirement-planning-input/target-date` writes the planned retirement **date** via `retirement_target_service.set_target` and `PlanningInputDecision`; `retirement-income-readiness/target` writes the desired **monthly income amount**, basis and price reference via `retirement_monthly_income_target_service.confirm`. Distinct input facts, not duplicate producers |
| Fixation validation vs calculation vs saving | `/fixation/validate`, `/fixation/calculate`, `/fixation/save` | Different lifecycle operations, no proven duplicate |
| Retirement readiness context | `GET /retirement-income-readiness/context` | Separate read model of planning input, not necessarily second writer |
| Professional review/readiness | Internal SC-05/06 services | No public review execution API; financial admission/lookup prohibited |

## Prevention mechanisms

- `backend/tests/test_api_route_ownership_contract.py` introduced to reject exact or equivalent-param method+path duplicates at FastAPI registration. This is an **HTTP collision test only**; it does not prove semantic uniqueness of distinct endpoints.
- For future MCP, define a canonical action catalogue with one action per business intent and explicit separation of `read`, `factual write`, `draft write`, `preview`, `historical read`, and `financial execute`. Never expose prototype or archive operations as an alternative way to perform an active action.
- Remaining review tasks: pension single-product PUT and multi-product `save-selected` **verified as shared `_update_locked` producer**; retirement date vs monthly-income target **confirmed distinct facts/producers**; all frontend write call sites and remaining non-scenario domains still require operation ownership review. Do not certify absence of every semantic duplicate until these are resolved.

## Next bounded implementation

1. Remove the mock editor and mock comparison from the main planning workflow; retain only the real saved drafts.
2. Preserve source selection from the one portfolio ledger into the saved draft editor, with client/source identity checks.
3. Replace the Results mock comparison with saved draft summaries; do not activate calculations.
4. Focused TS/Vite + backend route contract tests; one realistic synthetic-client walkthrough. One independent Work gate for the substantive UX consolidation, not per commit.

**No canonical fact mutation by scenario actions.** No approval chains, migrations, CI, merge or deploy authorization.

## Audit follow-up (26 October)

Reviewed both target service implementations. The retirement target date and desired monthly retirement income are **different professional facts**, not duplicate implementations of the same action. Preserve both APIs. The saved-scenario editor and mock local editor were consolidated in frontend; the owner-reported test run on the accepted UX delta was 25/25 PASS, while API registration collision tests reported 2/2 PASS. These tests **do not certify complete semantic API uniqueness** across every domain. New focused canonical-ID handoff oracle was added and awaits a local run.

**Remaining audit limitation:** this is an inventory of HTTP route registrations and selected core producer implementations, not yet an exhaustive call-graph of all backend and frontend functions. Do not claim system-wide duplicate-free status or MCP readiness based on it.

## PostgreSQL acceptance extension — pending local execution

The existing isolated PostgreSQL 16 test `backend/tests/test_scenario_draft_postgresql.py::test_postgresql_draft_migration_and_cas` now additionally exercises persisted duplicate, clone-only edit, two-scenario read comparison, original archive, and distinct-client separation. This reuses the existing disposable `postgres_url` fixture and migration path, without creating an API, schema, mock store, or a second scenario system. **No PASS claim until the owner runs it.**
