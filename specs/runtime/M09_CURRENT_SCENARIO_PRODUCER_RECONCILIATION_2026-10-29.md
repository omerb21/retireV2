# RetireV2 — M09 current scenario execution readiness: producer-level reconciliation

**Status: PROFESSIONAL_RULES_UNRESOLVED / CODE NOT AUTHORIZED**  
**Baseline:** verified UI HEAD `d1893c0e79fadbab1a1cfa7b351be3935d7c8ca2`.  
**Authority:** owner-approved seven fundamentals in `specs/runtime/PRODUCT_SCENARIO_FOUNDATION_OWNER_DECISION_2026-10-28.md`. This analysis does not activate historical M09 execution or sealed M10.

## Code-verified owners and compatibility boundary

| Existing owner | Verified entrypoint | Supported meaning | Not safe to infer |
|---|---|---|---|
| Draft | `backend/app/schemas/scenario_draft.py` / `scenario_draft_service.py` | Source product+component, exact amount, action pension/capital_asset, effective date, version history | Event automatically becomes cash flow |
| Canonical snapshot | `scenario_snapshot_candidate_service.py` | Same transaction, factual source fingerprint, balance, allocation constraints and changed-source invalidation | Structural consistency is financial approval |
| Allocation evidence | `scenario_allocation_snapshot_service.py` | Exact principal split, unallocated remainder, fail-closed per-source blockers | Principal is monthly income |
| Stage 6 P1D | `scenario_stage6_single_pension_estimate_service.py` | **One** pension decision, one admitted professional factor, nominal gross estimate at an approved target date | Multi-decision sum, lifetime duration, tax/net, ongoing CPI |
| Historical M09 | `backend/app/services/m09_cashflow_service.py` | Previously persisted deterministic monthly cashflow engine with recurring income/expense source categories; `m09_cashflow_routes.py` exposes archived reads | Historical run is current scenario, old route authorization permits new run |
| M10 | `backend/app/api/m10_comparison_routes.py` | No exposed current comparison route | New results comparison is authorized by old contracts |

## Current-source risks observed from code

1. Historical M09 recurring domain checks include current lifecycle, monthly frequency, income gross basis, verification, provenance, source date and month overlap. Those facts have their **own canonical authority**; scenario draft balances alone cannot replace them.
2. Historical M09 uses `gross_inflow_total`, `gross_outflow_total`, and `period_net`, where period_net is arithmetic gross-in minus out, **not after-tax pension net**. UI must not label it net disposable income after tax.
3. Stage 6 result does not establish the month-by-month policy after pension start, suspension, future factor changes, or death. Its result date is not an approved universal start/end schedule.
4. A capital_asset decision cannot be treated as monthly pension or counted as an inflow without a separate realization-date and tax contract.
5. No authority supports treating unallocated source remainder as a future payment.
6. Current-vs-historical result identity must be explicit. Archive routes already carry `X-Professional-Authority: archive-only`; no current producer may reuse that authority implicitly.

## Exact proposed engineering sequencing (execution only after separate approval)

**M09-P1: read-only producer input envelope.** Derive manifest, source inventory, decision identities, and statuses from the existing PostgreSQL read-only snapshot; no money outputs. All current structural blockers preserved. Evidence fingerprints bind exact snapshot.

**M09-P2: one-source periodized gross stream.** Under an approved temporal rule, call the accepted Stage 6 producer for admitted pension decisions, without modifying its formula or taking client-supplied factors. Required professional rule: when monthly gross starts, when it ends, whether it persists at constant nominal value, and how the source is distinguished from existing recurring pensions.

**M09-P3: multiple pensions and recurring items.** Only after approving summation, source collision policy, missing data policy, and applicability of existing recurring-income/expense facts. Explicitly no tax, CPI or discounting fallback.

**M09-P4: scenario immutability/currentness and persistence.** Retain accepted version and full input provenance; new results never overwrite historical M09 run or scenario facts. New current-run model and migrations require separate approval.

**M10-P1: comparability gate.** Same client, accepted versions, horizon, nominal/gross basis and complete source scope required. First allow evidence of compatibility, then an approved quantitative difference; no automatic recommendation.

**M11–M14:** planner review, client report, audit/export and production readiness remain out of scope pending distinct authorization.

## Professional decisions needed for executable M09

- **Periodization:** Is an accepted single pension decision's approved nominal gross amount effective from its elected `pension_start_date` on a whole-month basis, or from a prorated date? What is its supported end period?
- **Concurrent-income identity:** When is a current recurring-income pension the same economic source as a scenario pension? How are collisions proven and blocked?
- **Allocation overlap:** How do two pension decisions tied to the same factual component coexist? Structural sums may fit the balance while professional payout options conflict.
- **Capital conversion:** Should capital_asset decisions remain outside monthly cashflow initially, until their realization and taxation rules are explicit? (Conservative default: exclude, display separately.)
- **Expenses and non-pension income:** Does the current scenario inherit all verified recurring M09 facts by default, or explicitly selected subsets per scenario? Preserve verification and lifecycle status.
- **Outcome semantics:** Use distinct labels for monthly **gross inflows**, **expenses** and **gross difference**; reserve pension *net after tax* until approved tax/fixation producer.
- **Source fingerprint/currentness:** Which approved M06/Stage6 receipts are included, and what changes invalidate a month or range run?
- **Persistence:** One immutable run per scenario version/horizon or only an ephemeral estimate until user confirms an accepted scenario?

Until these are resolved, `SCENARIO_UI_MANUAL_QA_READY=YES` does not imply `M09_CURRENT_READY=YES`, `M10_READY=YES` or production readiness.

## Next bounded technical implementation

Existing Stage 6 + allocation evidence should be used as the only authenticated current scenario inputs. Do not wire historical M09 execution or M10 route. The next code task must specify accepted field set, professional periodization and error states, explicit source collision constraints, and tests for duplicate pensions, missing factor, no date, version CAS conflict, source stale, partial-month edge, and gross-vs-tax-net label.
