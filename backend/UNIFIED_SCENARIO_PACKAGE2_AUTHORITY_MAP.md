# RETIRE V2 - Package 2 engine integration authority map (2026-11-07)

Baseline: `2c4c570e05311edf467e374ac4d5bd4e96e88f2b`.
No engine math is rewritten, no tax/NET approximation is authorized. The
approved Package 1 envelope `UNIFIED_RETIREMENT_SCENARIO_RESULT_V1` remains
unchanged. The new internal consumer contract is
`UNIFIED_RETIREMENT_SCENARIO_ENGINE_BINDINGS_V1`.

## Contract decision before implementation

| Producer | Current source of truth | Scenario identity, dates, seals and currentness | Status in this package |
|---|---|---|---|
| Stage 6 P1C/P1D | Canonical decision/selected pension election, DB-held factor admission, five PTE fingerprints | Must bind `client_id`, `scenario_id`, `scenario_version`, original per-decision source hashes, target & statement date; admission is decision/version-specific | CONNECTED using the existing `_aggregate_extension` in the same read-only snapshot; valid output remains explicitly **NONBINDING_ESTIMATE**, never guaranteed insurer pension |
| Capital Projection | Canonical client-level `planning_input_service`, `capital_projection_basis_service` and `capital_projection_execution_service` | Planning-input fingerprint, admission fingerprint, date and asset basis; no existing scenario allocation authority | BLOCKED: `CAPITAL_PROJECTION_IS_CLIENT_SCOPED_NOT_SCENARIO_ADMITTED` |
| M06 | Historical M06 conversion revisions/evidence | Historical event identities, not a current hypothetical scenario | NOT INVOKED: historical reads do not grant new execution authority |
| Employment grants & severance | Canonical employment/grants, M05 evidence, fixation grant inputs | Requires employer-event choice, continuation/sequence and approved tax-year interpretation per scenario | BLOCKED: `SEVERANCE_SCENARIO_ADMISSION_NOT_DEFINED` |
| Fixation/M07 | Canonical pension/grant/capitalization evidence, eligibility dates, official parameters and calculated fixation inputs | Explicit eligible age/event, tax-year parameter set and actual vs projected decision distinction; prior fixation run cannot authorize a new scenario | BLOCKED: `FIXATION_ELIGIBILITY_AND_SCENARIO_TAX_ADMISSION_REQUIRED` |
| Stage 6 Monthly Cashflow | Canonical Stage 6 decision estimates and admitted current recurring income facts | Scenario/version/manifest; start/end months; unique source ID; per-month income/price basis; full result fingerprint | CONNECTED optionally through existing `_cashflow_extension` in the same PostgreSQL snapshot; only COMPLETE gross months can be exposed, as **NONBINDING_GROSS** |
| M09 | Historical persisted monthly cashflow runs | Archived scenario subjects and versions only | NOT INVOKED: current gross horizon uses Stage 6 |
| Income target | Existing RIT confirmed input, not a calculated outcome | Client-level target and planning fingerprint; requires independent revalidation | PRESERVED as `base.income_target`, authority not promoted |
| Net/tax | No authorized per-scenario complete tax and net producer | Would require validated taxable income, statutory treatment, tax year, deductions and authority | BLOCKED: `NET_TAX_EXECUTION_NOT_AUTHORIZED` |

## Unified engine-binding envelope

`build_unified_scenario_engine_bindings(factory, client_id, scenario_id,
start_month=None, end_month=None)`:

- Reuses the original `build_manifest_candidate_snapshot` transaction owner,
  which runs in PostgreSQL `REPEATABLE READ READ ONLY`, and package-1
  `_assemble` for the **same** manifest/candidate.
- Exposes `base` as the unchanged package-1 contract, plus an explicit
  `identity`, `domain_results`, `net_income`, and sealed
  `result_fingerprint`.
- Uses the native Stage 6 aggregate producer/validator to bind pension
  decision identities. The producer itself checks duplicate canonical
  product/component sources, date comparability and per-decision permission.
- Uses the native Stage 6 gross cashflow producer and public validator for
  requested horizons. The producer itself separates recurring income vs
  pension, checks duplicate source IDs, and does not include blocked months
  as positive calculated total.
- Never calculates new financial figures or joins gross income to capital.
  For gross cashflow it does NOT add the pension aggregate to the existing
  Stage 6 monthly totals (which already include pension contributions).
- Does not carry tax, capital, severance, fixation or historical result
  objects into a current hypothetical scenario without a professional
  admission contract.
- All result states remain `BLOCKED`, `NOT_REQUESTED`,
  `NONBINDING_ESTIMATE` or `NONBINDING_GROSS`. The wrapper never labels
  any financial output professionally approved or guaranteed.
- The whole-envelope SHA fingerprint changes on scenario/base/engine result,
  horizon, blocker, or professional evidence change. The package-1 base
  staleness checker remains available unchanged.
- No HTTP routes or grants are introduced. A future authenticated API must
  explicitly reuse the existing client isolation and CSRF boundary.

## Mandatory acceptance and remaining professional decisions

- Local PG16 tests: `test_scenario_unified_engine_binding_postgresql.py`
  execute the real snapshot/database owners with synthetic clients and
  no factor admission, and verify fail-closed, isolation and invalidation.
- A positive pension estimate with a genuine, decision-scoped professional
  admission and complete compared PTE fingerprints has **not** been proven
  end-to-end for this unified wrapper.
- Positive capital, severance and taxation depend on professional approval
  of the scenario applicability contracts. Do not copy client-level
  calculated capital or historical fixation runs as if scenario-valid.
- Full net cashflow depends on an approved taxable base and applicable
  legal/financial inputs. This package does not invent them.
- Full professional synthetic scenario with pension + capital + tax + net
  is therefore not an achieved acceptance gate.
