# SC-SCENARIO-02 — Scenario-specific calculation admission boundary

Status: **DESIGN ONLY / NOT IMPLEMENTED**. This is a conservative integration contract, not financial admission or an approval to alter current calculation engines.

## Verified repository entry points (2026-10-25)

- `backend/app/services/scenario_draft_service.py`: `read` and `list_drafts` return scenario version, decision IDs, source identities, amounts, action, effective date, validation states and `financial_validation: not_evaluated`. `_source_digest` provides a staleness anchor, explicitly not financial authorization.
- `backend/app/services/scenario_permission_preview_service.py`: independent, read-only permission calculation for **a product, action and effective date**, returning component-specific status and a source fingerprint. A product-level mixed result must never authorize every component.
- `backend/app/services/capital_projection_execution_service.py`: `execute(client_id, plan, authority)` consumes an admitted planning snapshot and matching capital-projection basis; `read(db,client_id)` derives these from current factual data. It is not an entry point for raw draft decisions.
- `backend/app/services/pension_target_date_portfolio_service.py`: `execute_from_planning_result(planning, client_id, expected_planning_calculation_input_fingerprint)` requires matching snapshot identity, a ready retirement target and complete pension-source coverage. `read` obtains the factual planning snapshot.
- `backend/app/services/retirement_monthly_income_gap_service.py`: `assess(db,request)` requires precisely `client_id`, `expected_planning_calculation_input_fingerprint`, and `expected_retirement_target_date`; owns a fresh read-only snapshot and validates downstream CMIA and target identities. It must not be used to label current-client results as scenario-specific.

## Required boundary before financial scenario computation

1. **Snapshot:** One isolated and consistent transaction captures the client, scenario identity + version, decisions, canonical pension sources, target-date authority, and current planning fingerprint. Never mutate canonical client rows or execute existing conversion write endpoints.
2. **Admission:** Validate all decision references to their client, product, component code and immutable identity; compare recorded draft source digest to the canonical digest in the *same snapshot*. Reject missing, outdated, archived or ambiguous records. Accept no client-supplied scenario authority.
3. **Allocation:** Aggregate decimal amounts by exact source component; reject negative, invalid precision, or aggregate allocation above canonical balance. Check action/date against permission rules per decision and component. **Permission 'allowed' is necessary but not sufficient**: professional eligibility and tax remain independent blockers.
4. **Derived scenario input:** Construct a typed, complete and independently fingerprinted scenario-specific planning snapshot. Reuse existing engine contracts only if their accepted input semantics can be satisfied without bypassing source coverage, identity, time basis or authority checks. Otherwise block with a specific reason rather than fabricating output or modifying formulas.
5. **Execution:** Read-only computation with explicit result provenance: client_id, scenario_id, scenario_version, decision_set fingerprint, canonical source snapshot fingerprint, planning basis fingerprint, ruleset digest, target date, engine contract version, and result fingerprint. No results carried across stale versions.
6. **Output:** Separate `SCENARIO_READY`, `SCENARIO_BLOCKED` and `NOT_EVALUATED`. Do not label sums of planned allocations as pension, capital-net-of-tax or monthly gap. Never claim execution authority.

## Fail-closed cases to test

- Source, balance, classification or product version changes between admission and execution.
- Cross-client product, mismatched component identity, archived draft, stale version or a replaced decision preserving the same decision_id.
- Two decisions overallocate the same component, including cross-action allocation; exact decimal handling.
- Missing/blocked/unknown/reconciliation-required permission; permission preview for wrong action/date.
- Incomplete pension-source coverage, missing projection basis, missing retirement target, CMIA block and target-basis mismatch.
- Any change to the planning fingerprint after a scenario result; transaction rollback and no persisted factual changes.
- Concurrent scenario mutation; ensure no result is attributed to a different scenario version.

## Explicit non-goals of this design phase

- No authoritative per-scenario monthly pension, capital projection, tax or income gap is implemented.
- No Alembic migration, write pathway, backfilling, frontend financial forecast or production deployment.
- Existing 01A/01B/01C and the permission ruleset remain unchanged.

## Next implementation gate

Build a narrow backend read-only **scenario admission assessment** first, returning structured blockers and snapshot identities, with PostgreSQL isolation and negative tests. Only after this passes should any existing calculation engine be adapted behind a compatible adapter. Avoid claiming scenario-specific results until the adapted input is independently verified.
