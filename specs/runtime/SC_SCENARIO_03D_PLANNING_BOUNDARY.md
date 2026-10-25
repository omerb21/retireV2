# SC-SCENARIO-03D — Unit D1: scenario planning boundary (design checkpoint)

Status: **D1 DESIGN COMPLETED; NO ADAPTER OR EXECUTION AUTHORIZED**.

This is an implementation-unit checkpoint under the existing SC-03D acceptance package, not a change to governance v1.1. SC-03 is independently accepted through commit `adc45f0422cff851c5a60d0066121c99029b2b6d`. Do not reopen it absent a demonstrated regression.

## Repository-grounded contracts

1. `scenario_snapshot_candidate_service.build_manifest_candidate_snapshot(factory, *, client_id, scenario_id, claimed_manifest=None)` is the authoritative public read boundary for scenario manifest + candidate. It owns a dedicated PostgreSQL `REPEATABLE READ`, read-only transaction. Candidate `planning_snapshot=None`, `execution_allowed=False`, `financial_result=None` are **invariants**, not TODO flags for bypass.
2. `scenario_calculation_admission_service.assess(db, client_id, scenario_id)` currently returns `assessment_state=blocked`; it has no permission, tax or professional approval authority. Its independent reads must not be recombined with a candidate from a different snapshot and presented as one admitted unit.
3. `planning_input_service.derive(db, client_id)` constructs a **current-client** canonical planning result using `_snapshot`, `PlanningInputDecision`, current income/expense/timing records, pension sources, and canonical authority fingerprints. It is **not** a scenario decision adapter; passing its output unchanged cannot yield a scenario-specific result.
4. `scenario_engine_compatibility_service` establishes only structural contracts for `pension_target_date_execution_service.execute_from_planning_result`, `capital_projection_execution_service.execute`, and `retirement_monthly_income_gap_service.assess`. Structural compatibility does not imply admission.

## D1 decision: do not adapt engines directly

The candidate's component-level `pension` and `capital_asset` actions cannot be mapped mechanically to:
- pension source-monthly basis and temporal authority;
- a complete capital registry and admitted projection basis;
- income-target and comparable-income authorities.

No multiplication, proportional pension derivation, capital-net-of-tax or monthly gap may be inferred from draft allocation amounts.

## D2 — next bounded implementation unit (not started)

Implement a **read-only scenario planning coverage inventory** behind the existing DB-owned snapshot boundary. Its only purpose is to enumerate, for each proposed decision, the required canonical producer/authority families and report `PRESENT_NOT_ADMITTED`, `MISSING`, or `UNRESOLVED` based on verifiable database-owned evidence; default to `UNRESOLVED` where authority semantics are not proven. Results must carry `client_id`, `scenario_id`, `scenario_version`, the authoritative manifest fingerprint, and a separate inventory fingerprint. No `planning_snapshot`, `execution_allowed=True`, financial result, or engine call.

**Before D2 code:** identify exact existing producer APIs and their transaction ownership; do not call a producer that independently starts a transaction inside the scenario snapshot. If no safe producer exists, report `MISSING_SCENARIO_SAFE_PRODUCER` rather than using the factual planning output as scenario authority.

**Scoped files:** a new `backend/app/services/scenario_planning_coverage_service.py`, a new `backend/tests/test_scenario_planning_coverage.py`, and the existing governance test allowlist only if its rules require it. No model, route, migration, frontend, engine or formula changes.

**Acceptance tests:** repeatable deterministic inventory fingerprint; mixed source actions remain distinct; absent authority fails closed; duplicate decisions and cross-client references cannot become present authority; changing manifest/scenario version changes identity; no financial calculations; no writes. Run focused tests locally. Reserve WORK review for SC-03D's actual acceptance gate.

## Handoff

- HEAD at D1 creation: record from the GitHub commit response.
- Completed: source-to-contract map and conservative D2 scope only.
- Tests: none required for a documentation-only checkpoint.
- Open: scenario-safe factual producer binding, professional/tax/permission admissions, all financial execution.
- Next unit: D2 producer discovery and coverage-inventory implementation, not engine execution.
