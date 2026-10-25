# SC-SCENARIO-04 / P1 — Pension scenario adapter: source contract checkpoint

Status: **DESIGN/CONTRACT INVENTORY ONLY**. No scenario calculation or admission authorization.

Baseline: SC-03D coverage inventory accepted at `3c4c038394cd343048d907510a04e2b3d7ae7775`. Do not reopen SC-03 or SC-03D on this checkpoint.

## Two distinct existing pension interfaces

**Single pension source:** `pension_target_date_execution_service.execute_from_planning_result(planning_result, source_id, *, supplied_planning_calculation_input_fingerprint, supplied_monthly_basis_semantic_fingerprint, supplied_monthly_basis_source_fingerprint, supplied_temporal_semantic_fingerprint, supplied_temporal_source_fingerprint)`.

- Selects one unique `pension_inputs[].source_id`. Missing/duplicate source is a valid *blocked* input, not a structural exception.
- Uses source `monthly_amount_basis` (representation, authority kind, semantic/source fingerprints), `temporal_authority` (kind, origin, rate, semantic/source fingerprints), and planning `retirement_target` plus the planning fingerprint.
- A draft `amount` in a pension-product component is **not** an admitted monthly pension amount, pension factor, source temporal identity or ready retirement target.

**Complete pension portfolio:** `pension_target_date_portfolio_service.execute_from_planning_result(planning, client_id, expected_planning_calculation_input_fingerprint)`.

- Requires one admitted planning fingerprint, ready retirement target and a **complete** pension source universe with unique IDs.
- Dispatches source computations and assembles a complete-coverage result. A per-component scenario subset is not this source universe.

`planning_input_service.derive(db, client_id)` creates the *current-client factual* planning result from canonical source/decision/authority registries. This result must not be relabeled or hashed as a scenario-specific planning result without a defined, verified scenario transformation.

## Unresolved semantic bridge — do not infer

| Scenario information | Required authoritative bridge | Status |
|---|---|---|
| `action=pension`, component amount, effective date | Component-to-canonical pension source identity and decision semantics | MISSING |
| Pension amount allocated in draft | Authorized monthly amount representation and origin | MISSING |
| Proposed timing | Verified scenario monthly-basis and temporal authorities | MISSING |
| Changed source universe | Complete, mutually exclusive pension source coverage | MISSING |
| Retirement target | Independent scenario-target decision and accepted fingerprint | MISSING |
| Calculable result | Professional, permission and tax admission | NOT_EVALUATED |

A mechanically prorated current-client pension, current-source result under a scenario label, or inferred conversion ratio is prohibited.

## Next bounded implementation unit — P2 (not started)

Produce a **read-only component-to-pension-source reconciliation report**, not a financial adapter. It may use the existing DB-owned scenario snapshot owner and canonical source evidence, but must explicitly prove that both sets of identities were produced from the *same* snapshot before reporting a matching source. If the canonical pension registry cannot be read safely inside that transaction, report `SCENARIO_PENSION_SOURCE_BRIDGE_UNAVAILABLE` and no matches.

Output should be deterministic, tied to `client_id`, `scenario_id`, `scenario_version` and `manifest_fingerprint`; distinguish `MATCHED_NOT_ADMITTED`, `AMBIGUOUS`, `MISSING`, `UNRESOLVED`. Never upgrade an inference to `MATCHED`. Preserve `execution_allowed=False`, `financial_result=None`, `planning_snapshot=None`.

First establish the exact existing canonical source registry API/identity and transaction ownership. Keep implementation confined to a new service, focused tests, and governance allowlist if required. Do not alter calculation engines, formulas, migration or frontend. No Codex/Work run before a bounded, code-backed requirement exists; Work review remains at the acceptance gate.

## Handoff

- Completed: contract inventory and scope for first source reconciliation.
- Tests: not needed for documentation-only checkpoint.
- Open: canonical source identity binding; scenario-safe monthly/temporal authority; retirement target and professional/tax/permission admission; portfolio completeness.
- Next: P2 producer/identity discovery before code.
