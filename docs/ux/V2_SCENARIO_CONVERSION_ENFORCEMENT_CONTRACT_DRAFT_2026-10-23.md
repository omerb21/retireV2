# V2 scenario conversion validation — review-ready contract DRAFT

**Status:** DRAFT / DOMAIN-CHANGE / INDEPENDENT-REVIEW PENDING. Not an authorization to implement or deploy financial logic.
**Basis:** owner requirement, V1 backend `app/services/pension_portfolio/conversion_rules.py`, V1 UI overrides/settings, V2 governance and UX gate. See `V1_TO_V2_CONVERSION_RULES_GATE_2026-10-23.md`.

## 1. Objective and boundaries

Each V2 scenario decision must be validated on the **underlying classified component**, never just the product's displayed total. A whole-plan action is a **bulk instruction decomposed into individual proposed component decisions**; product identity and source classification cannot be lost. Nothing in the scenario modifies the factual `PensionProductComponent` ledger. The current factual `POST /canonical-conversions` route must not be used for scenario evaluation, including execute-and-undo.

Three independent decisions must be modeled distinctly:
- **Permission to consider an action**, based on versioned rules, classification, product type, factual prerequisites and effective date.
- **Whether the action can be executed in a specific scenario**, based on client, available balance, other decisions, history and version.
- **Its financial/tax outcome**, deferred until a distinct accepted calculation contract, never inferred from permission alone.

## 2. Input contract (proposed, not implemented)

```text
client_id
scenario_id
scenario_version
source_product_id
source_product_version
source_classification_code (canonical 11-column code)
amount: exact decimal currency string
action: pension | capital_asset | leave_unallocated
effective_date
ruleset_version
factual_source_snapshot / immutable source reference
```

`leave_unallocated` is provisionally a **residual state**, not an independent withdrawal or conversion. Whether explicit 'keep invested / preserve original disposition' constitutes a separate decision is pending owner authority. Invalid or missing fields, unknown codes/types, zero/negative allocations, stale sources, client isolation failure and missing prerequisites must fail closed.

## 3. Evaluation output (proposed)

```text
status: allowed | blocked | needs_professional_resolution | stale
source_ref, action, requested_amount
rule_id, ruleset_version, reason_code, human_readable_hebrew_error
eligibility_preconditions / unresolved_source_facts
source_version / effective_date
tax_status: not_evaluated (until authorized engine)
```

Use structured reason codes, not only UI text; rules are deterministic and versioned for reproducibility. No eligibility is inferred from UI static checkboxes/localStorage.

## 4. Reused behavioral reference, not automatically accepted financial authority

V1 server permission summary across canonical codes:
- **Neither pension nor capital:** current-employer severance, unsettled severance, prior-employer rights-continuity severance.
- **Pension only:** prior-employer pension-continuity severance, post-2000 employee/employer contributions, non-paying post-2008 employee/employer contributions.
- **Pension and capital:** settled severance, pre-2000 employee/employer contributions.
- **Product-specific overrides:** investment provident fund and education fund logic (and aggregate contributions) are handled before the default field matrix in V1.
- V1 additionally has a **global unresolved severance/rights-continuity blocker** in `usePensionConversion` before preparing conversions; determine precisely which V2 scenarios it applies to. Do not silently make all unrelated planning impossible.
- V1 UI default permissions/tax metadata and backend tax treatment differ in some entries; professionally reconcile before using tax labels.

The mock `mockConversionEligibility.ts` is a *non-authoritative illustrative snapshot* and must not be imported by real finance services.

## 5. Whole-plan batch action and UX error contract

1. Expand the chosen plan into its constituent exact source components and retrieve rule decision for **each** requested action.
2. Present a review table: component, original amount, requested action/amount, permission state, reason and available amount; show forbidden rows prominently.
3. **Default batch commit is atomic fail-closed:** if any selected component is blocked/uncertain, do not save an automatically pruned subset. The owner may define an explicit review-and-exclude flow; pending product approval.
4. Allow manual overrides only by changing the proposed allocation/action to another supported rule; no user override of a legally prohibited action without an independently authorized exception contract.
5. Never split a single component's amount across decisions beyond available classified balance. Recheck server-side at commit with scenario version/source version.
6. Scenario modifications/cancellations cannot modify facts, other scenarios or the historical source records.

## 6. Server enforcement proposal

- Provide a **read-only authoritative validation/preview service** that handles single-component and whole-plan requests with the same rule engine used for committing a scenario decision.
- On scenario save/evaluation, re-run authoritative validation in one safe transaction, with optimistic versions and client authorization. Do not trust earlier preview or browser-only validation.
- Capture rejection with detailed rule IDs and Hebrew reasons; no silent drop of prohibited amounts. Keep a per-action audit trail without mutating factual product balances.
- Rule changes must be controlled and versioned; evaluate existing scenarios against their accepted ruleset and mark stale/incompatible outputs when necessary. Never retroactively relabel older results silently.

## 7. Minimum independent acceptance matrix

- All 11 classifications × pension/capital with allowed and disallowed examples; unknown classification fails closed.
- Product-type overrides and exact source-type matching, including education/investment products and ambiguous/unknown products.
- Whole plan with mixed eligible/ineligible components returns **zero saved decisions** on unresolved batch; independently test selected exclusions.
- Amount in exact cents: partials, boundaries, double allocation, negative and malformed inputs.
- Historical grant duplicates/reconciliation, missing employment termination evidence, unresolved severance, action date and rule-version change.
- Cross-client attempt, bypassed UI, concurrent scenario versions and source-balance update race.
- No source mutations, no `canonical-conversions` calls, no cross-scenario decision leaks.
- No tax, monthly pension, projected capital or NPV outputs absent accepted calculators.

## 8. Review and decisions required

1. Which **versioned rule authority** should V2 adopt when V1 front-end settings and server differ, and who can change rules?
2. Is the default **atomic-block-all** behavior for a mixed-rule whole-plan conversion acceptable, with an explicit optional exclude-and-retry workflow?
3. How should the V1 global unresolved-severance blocker map to V2's scoped decisions?
4. Is `leave_unallocated` residual-only, or does owner need a separate explicit 'retain original disposition' instruction?
5. What are accepted requirements for dates, minimum pension constraints, historical tax evidence, and grant reconciliation when evaluating conversion legality?
6. When a policy or source fact changes, which scenario decisions remain editable, which calculations are stale, and what evidence must be preserved?

## 9. Three-role execution gate

- **Direct chat:** requirements evidence, UX mock, contract draft, targeted tests and documentation.
- **Codex:** bounded authoritative scenario validation implementation **only after** rules and ownership are approved, including backend fail-closed integration.
- **Work:** independent check of V1 reference correctness, conflicts with accepted V2 authority, plan-batch semantics, race/security tests and proof that factual values remain unchanged before acceptance.
- **Owner:** professional decisions above. No merge, production release, migration or new financial calculation follows from this draft.

**Current gate:** contract drafted, not professionally accepted; no V2 authoritative validation service implemented.
