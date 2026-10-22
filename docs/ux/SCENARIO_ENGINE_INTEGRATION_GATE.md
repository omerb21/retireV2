# Scenario integration gate — backend evidence and next contract
Date: 2026-10-22
Applies to: owner-approved professional full-workflow UX; NOT a calculation implementation or approval.

## Findings verified against master

- GET /api/clients/{id}/m06/subjects and /history are historical/archival reads. The M06 router offers no prospective simulation mutation endpoint.
- /api/clients/{id}/m09 routes expose archived inventories/runs/subjects. The router is explicitly archive-only and cannot execute new prospective cashflows.
- /api/clients/{id}/m10 currently exposes no replacement comparison endpoint; legacy stateless comparison is sealed.
- POST /api/clients/{id}/canonical-conversions/preview can preview a conversion for current saved balances. POST /canonical-conversions **executes a database mutation of factual component balances**, with a separate reversal history. Neither operation is a scenario producer.
- The accepted product save API takes expected_version and a full component map. It belongs to factual corrections, not scenario decisions.

## Required new scenario-owned contract (proposal; not implemented)

A named scenario is an independent entity under one client, with:
- scenario_id and immutable client_id;
- explicit base_factual_revision and/or accepted source fingerprint;
- retirement date and employment decisions;
- selected portions of product/component balances identified by canonical product_id and component_code;
- destination pension or capital, timing/effective date and supporting professional decision parameters;
- status: draft, needs_revalidation, validated, archived;
- created/updated/audited identifiers and optimistic version.

Each proposed allocation is a **decision**, not a new PensionProductComponent and not an irreversible asset transformation. It cannot exceed the available amount from the scenario's verified base and must obey all applicable rules and tax/employer approvals; a UI alone cannot assign eligibility.

A scenario preview/evaluation adapter must be read-only with respect to the base portfolio. It must consume authoritative, accepted facts and a scenario snapshot, then return per-decision eligibility, warnings and calculated outputs only from approved services. A committed scenario operation must never call current executeConversion and then reverse it to fake isolation.

When underlying factual data changes, retain the scenario and its decisions while marking its calculation as needing revalidation. No old result may be shown as current without a visible invalidation or a fresh accepted evaluation.

A comparison producer must take two explicit scenario evaluation identities and input fingerprints, never combine archived runs and freshly edited draft balances without an explicit compatibility check.

## Delivery increments

A. Frontend: client-scoped workbench and factual editing. **Implemented in isolated branch; tests authored, run not yet proven.**
B. Backend: independently persisted scenario draft + allocations and revisions; no payroll/pension/tax outputs claimed. Requires business authorization on model and authority semantics.
C. Backend: evidence-based eligibility/previews for selected pension/capital allocations, including employer severance decisions and professional constraints. Never reuse factual execute as hypothetical conversion.
D. Engine: current (non-archive) M09 scenario cashflows/financial outputs + revalidation guard.
E. Comparison: current (non-sealed) M10 comparison and report semantics.
F. UX: connect workflow tabs to B-E incrementally with tests and one synthetic professional journey; integrate V1 comparison oracles only where professionally accepted.

## Mandatory negative tests

- A scenario choice never changes current PensionProduct components.
- Reject a plan for a different client or a stale factual base.
- Replacing or correcting the source marks affected scenario calculations stale but preserves choices.
- Reversing/altering a scenario allocation restores scenario availability and does not create/delete actual capital assets or pensions in the client record.
- No 161ד entitlement, tax exemption, or future pension factor is inferred without the required official inputs/authority.
- Draft, preview and compare views never display an archive result as if it were a new current scenario calculation.

All backend build decisions remain subject to governance/professional review; do not merge the current UI branch as a completed planning system.