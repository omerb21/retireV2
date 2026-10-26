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

## Write-surface freeze and agent exposure policy (2026-10-26)

A new test `backend/tests/test_api_business_operation_inventory.py` enumerates all current POST/PUT/PATCH/DELETE routes from the **registered FastAPI application** and compares them with an explicit reviewed baseline. This catches newly added, removed or renamed write-shaped routes, including differently named paths not detected by the route-collision test. **It does not prove semantic uniqueness by itself, and has not yet been executed locally.**

**Potential overlap needing an explicit future agent decision:** `POST /api/clients/{client_id}/grants` creates a grant without an employment period link, whereas `POST /api/clients/{client_id}/employment-records/{employment_record_id}/grants` creates a grant attached atomically to a verified **ended** employment period. These are not equivalent contracts. The professional workspace should prefer the latter when a period is selected; a future MCP catalog must not advertise both as interchangeable 'create grant' operations. No existing API deletion or behavior change is authorized by this audit.

**MCP guardrail:** do not automatically expose every mutating OpenAPI route as an agent tool. Explicitly select one action per professional business intent; tag historical, preview, archive, direct-entry and context-linked variants according to what they actually do. A route inventory is a change-detection control, not a replacement for business contract ownership.

## Semantic producer follow-up — grants and historical employment (2026-10-26)

Inspected actual handlers in `backend/app/api/clients_routes.py` (rather than comparing paths alone):

| Professional intent | Existing route | Distinction / MCP rule |
| --- | --- | --- |
| Record an ended employment period and its exempt grant in one operation | `POST /api/clients/{client_id}/historical-employment-settlements` | Atomic creation of an EmploymentRecord and optional linked Grant. **Preferred when the period does not yet exist.** |
| Record exempt grant for an **existing** ended period | `POST /api/clients/{client_id}/employment-records/{employment_record_id}/grants` | Validates period status, dates and existing linked grant. **Preferred when an ended period is already selected.** |
| Record a grant when no verified period can yet be linked | `POST /api/clients/{client_id}/grants` | Creates an **unlinked** Grant. Does not set a period's exempt-grant status. **Fallback only; never present as equivalent to linked creation.** |
| Attach an existing unlinked grant to verified ended employment | `POST /api/clients/{client_id}/grants/{grant_id}/employment-link` | Explicit identity and date checks, prevents different-period relink or duplicate linked grant. **Reconciliation operation, not grant creation.** |

**Finding:** These four routes can produce related grant data, but they are different transactional intents. Their coexistence is not by itself proof of the V1 failure pattern. The underlying grant-row construction is repeated across handlers: a **maintenance/consistency risk**, not yet evidence of two contradictory active calculation engines. Do not create an extra business API or delete a supported fallback merely to make the endpoint count smaller.

**Agent catalog rule:** expose `record_historical_employment_with_grant` or `record_grant_for_existing_period` according to the state of the historical employment, not both as generic `create_grant`. Treat unlinked entry as a deliberately separate incomplete-data action; link is reconciliation. Future tests should assert equivalent field mapping where appropriate and preserve different constraints.

**Other reviewed boundaries:** `scenario-drafts` is the sole hypothetical scenario persistence service; `canonical-conversions` is the factual balance-changing service; `m06` and `m09` do not register mutation routes. `PUT /retirement-planning-input/target-date` and `PUT /retirement-income-readiness/target` address date vs monthly income amount respectively; single-item and batch `pension-products` updates share `_update_locked`.

**What has NOT been proven:** semantic uniqueness of fixation entrypoints, all capital/income supplemental writers, archived vs replacement financial producers, and any future agent binding. Structural route-inventory 3/3 PASS protects change visibility, **not** a certificate that all V2 business operations are duplicate-free.

## Confirmed semantic duplication resolved — fixation calculation (2026-10-26)

`POST /api/clients/{client_id}/fixation/validate` and `POST /api/clients/{client_id}/fixation/calculate` originally called **the same** `calculate_fixation_payload(... use_persisted_grants=True)` with the same request and result contracts. This was a real duplicate **discoverable operation**, not an independent calculation engine. Resolution: `calculate` is the canonical OpenAPI/agent operation; `validate` remains callable strictly as a compatibility alias with `include_in_schema=False`; frontend `validateFixation` delegates to `calculateFixation`, so normal frontend use issues only the canonical request. Added a registration/OpenAPI regression test. **Do not remove the compatibility route without a separate consumer impact audit.** No calculation, tax logic, schema or persisted results changed. Focused tests/build pending local verification.

## Health operations removed from agent discovery (2026-10-26)

Three monitoring routes (`GET/HEAD /health`, `/healthz/live`, `/healthz/ready`) previously generated duplicate GET/HEAD OpenAPI operation IDs. They remain registered and callable for operational monitoring but are now excluded from OpenAPI with `include_in_schema=False`. Added tests requiring their presence in router registration, absence from OpenAPI, and uniqueness of every discoverable OpenAPI operationId. This is a schema/catalog hygiene fix, not a change in readiness status or financial business processing. **Tests pending local run.**

### Calculation / report ownership status

- `POST /api/clients/{client_id}/fixation/calculate`: canonical client-context fixation calculation producer; legacy `/fixation/validate` invokes same calculator but is hidden from OpenAPI.
- `POST /fixation/review/validate`: validation of **review input contract**, not the fixation calculation engine.
- `POST /fixation/review/convert`: conversion of structured review into fixation engine input, not an executed financial calculation.
- `POST /fixation/save`: persists a new fixation run (which includes a calculation), materially different from a non-persisted calculation.
- `POST /api/clients/{client_id}/retirement-income-readiness/comparison`: compares target-income evidence; separate from the sealed `m10` general scenario comparison.
- `m09` routes are archive reads only; `m10` router has no live operation.
- Financial scenario engine/cashflow adapter and coefficient lookup remain **NOT AUTHORIZED**; no route has been re-enabled by this audit.

This is a grounded endpoint-level classification, **not** a complete proof of identical numerical output across fixation preview and saved-run paths; preserve both distinct professional intents while retaining one underlying approved calculation engine.
