# RETIRE V2 — SC-SCENARIO-01: Scenario draft persistence gate

**Status:** ENGINEERING DESIGN / NOT IMPLEMENTATION AUTHORIZATION / NOT PROFESSIONAL ELIGIBILITY.
**Baseline:** accepted Permission Preview at `b3b24542a8b80b53f38f96c85419c34f0073ac5c`.
**Purpose:** create durable, independent, client-scoped scenario drafts that never mutate factual pension products.

## Verified integration gap

- `frontend/src/pages/RetirementWorkspaceScreen.tsx` stores `mockAlternatives` and `ScenarioMockDecision` in component state. There is no durable scenario source of truth.
- `POST /api/clients/{client_id}/scenario-conversions/permission-preview` reads one actual imported pension product in a zero-write snapshot and returns basic component/action permissions. It does **not** validate or authorize a saved allocation, tax or professional eligibility.
- `canonical_component_conversion_service.execute()` **mutates** factual product balances and creates factual destinations, and MUST NOT be called for a scenario.
- M09/M10 archive/legacy outputs are not producers of new prospective scenarios.

## Proposed bounded increment: SC-SCENARIO-01A

Implement ONLY independent named draft storage and editing; detailed financial allocation admission remains a separate acceptance gate. Drafts are not accepted conversions.

**Scenario aggregate (proposal):** `scenario_id`, immutable `client_id`, user-visible `name`, `status=draft|needs_revalidation|archived`, integer optimistic `version`, `created_by`, `updated_by`, `created_at`, `updated_at`. One scenario belongs to exactly one client; copying between clients is disallowed. Audit revisions append, never overwrite accepted revision evidence.

**Draft decision (proposal):** `decision_id`, `scenario_id`, `source_product_id`, `source_component_id`, `component_code`, exact two-decimal `amount`, `action=pension|capital_asset`, `effective_date`, `product_version_at_review`, `source_fingerprint_at_review`, `ruleset_digest_at_review`, `permission_preview_id_at_review`, `validation_state=unverified|needs_revalidation`. A missing optional review token must be represented as absent, not fabricated. Persisting a draft with `validation_state=unverified` **never** claims permission, eligibility, or available balance.

**Availability is derived, never authored:** for each scenario, sum its current draft allocations by canonical (product_id, component_id), compare against freshly captured factual component balance, and display potential excess as unresolved; do not persist residual as a decision. Never quietly create or remove allocations for zero rows or blocked components. Duplicate allocations of the same source may be aggregated for display, but not silently collapsed across effective dates or actions.

**Mutation safety contract:** all draft create/edit/remove operations require current scenario `version` (optimistic CAS), are client-scoped, and never invoke factual conversion, `savePensionProduct`, or write to `pension_products`, `pension_product_components`, factual `capital_asset` or pensions. Failed CAS returns a conflict rather than overwriting another revision. No historical decisions are erased by archiving.

**Staleness:** a stored review fingerprint is evidence of what was seen, NOT proof of current balance. A future validation/admission action must fetch a fresh permission preview and compare original fingerprint, product version, chosen effective date and exact ruleset. Changed/missing source marks dependent decisions `needs_revalidation`; preserve user intent. Product data changes may be detected lazily upon opening a scenario, without introducing cross-table hooks into factual mutation APIs for the first draft-storage increment.

**Professional safeguards:** no scenario is displayed as `validated` and no allocations are labeled professionally eligible based on permission preview alone. Group acknowledgment, source/evidence dependency validation, exact availability enforcement, and accepted allocation submission remain later gated work. No tax treatment, annuity, NPV, 161d, or financial scenario result.

## Proposed delivery sequence

1. **01A — Draft persistence only:** client-scoped scenario and draft decision CRUD; independent revisions; CAS; no financial authority. Display states honestly as draft/unverified.
2. **01B — Preview-backed review:** read current Permission Preview, show all 11 real components with reason/status, explicit per-row selection, exact review digest and grouped exclusion acknowledgement. No save as accepted decision until eligibility dependencies and atomically enforced availability are authorized.
3. **01C — Admission and authoritative decisions:** separate owner-reviewed schema and transaction for accepted allocations, source staleness CAS, professional evidence dependencies, idempotency and full audit.
4. **01D — Current calculations and comparison:** new scenario producer and calculation/evaluation contracts; never impersonate archive M09/M10 outputs.

## First increment acceptance evidence

- Client A -> B -> A isolation including loaded scenario and draft decisions; cross-client requests return indistinguishable not-found.
- Create, rename, copy within the same client, edit, archive, reload and reconstruct drafts from backend; no reliance on browser memory.
- Concurrent edit must fail CAS without losing existing revision.
- Editing decisions and deleting last decision leave no stale editor UI state.
- Exact Decimal amounts; no float financial storage; no fabricated residual.
- Factual `PensionProduct` rows, balances, canonical conversion tables and factual pensions/capital assets unchanged before/after draft operations.
- Real source changes must surface `needs_revalidation` on subsequent draft review without deleting decisions.
- Basic permission is NEVER presented as professional eligibility.
- No new CI, migration or production deployment until specific implementation authority is granted.

## Gate

**01A implementation is NOT authorized by this design document.** Before implementing migrations and scenario tables, independently review the bounded scenario lifecycle, required client scope/CAS/revision semantics and interaction with real portfolio data. Owner professional decisions O-01–O-08 and accepted SC-PERM remain closed. The design is deliberately narrower than an authoritative scenario save.
