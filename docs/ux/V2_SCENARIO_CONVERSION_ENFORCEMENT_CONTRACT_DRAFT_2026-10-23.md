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

## 10. Existing V2 backend source-code reconciliation (read-only, 2026-10-23)

**Actual files examined on the UX branch:**
- `backend/app/models/pension_product.py`: 11 canonical component codes and exact source product versions.
- `backend/app/services/canonical_conversion_matrix.py`: `MATRIX_VERSION = canonical-component-conversion-matrix-v1`, `destinations(code, product_type)` and `tax_for` already provide **authoritative permissions for factual conversions**.
- `backend/app/services/canonical_component_conversion_service.py`: `_preflight` locks source rows and checks expected product version; explicit selections invoke `tax_for`, whereas `whole_product=True` **silently accumulates disallowed components in `skipped` and proceeds with selected allowed components**. This must not be naively copied into scenario batch semantics.
- `backend/app/api/canonical_conversion_routes.py`: `/preview` and factual `execute` live together; execute changes canonical ledger facts.
- `backend/app/services/m06_conversion_service.py`: historical evidence reads only, not a new scenario pension producer.
- `backend/app/services/m09_scenario_subject_service.py`: immutable scenario subject adjustment manifests and baseline artifacts exist, but their adjustments are **not** the pension-component allocation scenario contract proposed here.
- `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md`: already documents why present M06/M09/M10 archive/stateless outputs are not a complete prospective scenario engine.

**Explicit correction to earlier assumption:** V2 already has a central server-side component permission matrix for factual conversions; the missing capability is authoritative **scenario-scoped** validation/decisions and a reviewed compatibility contract, not inventing any permissions service from zero.

**Rule parity and potential conflicts:** V2 canonical matrix appears to cover the same 11 permissions as V1's backend for ordinary products, with education/investment product-type overrides. Its tax values and some V1 frontend settings differ and require row-by-row explicit verification; permission parity does NOT imply tax parity. In particular, never load the V1 browser `localStorage` settings as V2 financial authority.

**Revised implementation direction:**
1. Reuse `destinations` as the *starting permission reference* subject to rule/version review, in a **new read-only scenario adapter**; do not call factual conversion `preview` if it needs conversion-specific inputs or implies its execution lifecycle.
2. Verify effective source snapshot and scenario lifecycle *independently* of `M09ScenarioSubject` and M06 archival state, or obtain explicit integration contract approval before extending them.
3. The current factual `whole_product` skip behavior is a **separate behavior** from the proposed scenario **atomic fail-closed** batch. The owner must explicitly choose whether to block whole batch or allow informed selection/exclusion; preserve skipped components in both UX and backend results.
4. Add exact comparison tests between V1 backend and V2 `destinations` for every code and recognized product class; negative tests must verify no write and no accidental eligible-subset commit on forbidden scenario batches.
5. Do not refactor the factual conversion route as part of this UX/domain contract. Any change to it requires its own impact analysis and accepted governance gate.

**Gate:** preliminary in-chat code review only; neither independent Work acceptance nor authoritative scenario engine implementation has occurred.

## 11. Explicitly reviewed partial-plan selection — proposed UX only

The previous sections use **atomic fail-closed** as the default for a submitted unreviewed batch. This does **not** prohibit an explicitly reviewed eligible-only request:

1. Planner requests whole-plan `pension` or `capital_asset` preview.
2. Server resolves every positive **canonical source component**, its available amount, classification and individual `allowed/blocked/needs_resolution` status.
3. UI displays *all* components, including blocked ones; no component is silently removed. It displays a clear **eligible subset** and the aggregate eligible nominal principal, while keeping blocked amounts separate from unused balances.
4. Planner may consciously select the permitted subset, alter amounts or cancel. The submitted request explicitly lists the chosen component identities and amounts, source/ruleset versions, and acknowledged excluded components. It is **not** `whole_product=true` implicit conversion.
5. Server revalidates precisely this reviewed request against source and ruleset at submit. If anything changed or one submitted component is forbidden, **reject the complete submitted request atomically** with structured reasons; never silently apply the remaining subset.
6. Blocked/unselected capital is never classified as converted; financial reporting distinguishes total original, converted nominal principal, blocked, selected-but-unallocated and independently assessed residual. Duplicate counting is prohibited.

**Product decision still pending:** whether the planner must always manually acknowledge individual excluded components or can acknowledge a reviewed group. Do not interpret the assistant's recommendation of 'convert only eligible components' as owner approval.

**Bounded future UX-MOCK:** a read-only list of per-component permission results for a selected whole plan, with explicit counts and disabled action preview; no server mutation and no persistent decision. To avoid conflicting sources of truth, the authoritative V2 service must later supply these results rather than the frontend's V1 snapshot.

## 12. Independent Work audit disposition — BLOCKED (2026-10-23)

**External independent review received from owner; read-only, no repo changes/tests by Work.** Review evidence cites V2 HEAD `d2b32d5abe97e478f7a97ef19a99c8a4e5de5738` and V1 HEAD `611557d7d413fa06519b0a381e259177852a8244`. Verify commit drift before relying on line-level findings. Work verdict: `CONTRACT_READINESS=BLOCKED`, `SCENARIO_ENGINE_IMPLEMENTED=NO`, `SERVER_SIDE_SCENARIO_ENFORCEMENT=NOT_IMPLEMENTED`, `IMPLEMENTATION=NOT_AUTHORIZED`.

### Required changes from SCV-001…SCV-010

| Finding | Contract disposition |
| --- | --- |
| SCV-001 | Define separate scenario-owned API, no factual execute or execute-and-reverse. |
| SCV-002 | Never copy factual whole-product silent skip; return all permitted, blocked and unresolved components and require explicit reviewed selection. |
| SCV-003 | Closed canonical product-type resolver; missing, ambiguous, unknown must fail closed. |
| SCV-004 | Product-type exception precedence over blocked severance requires professional decision; do not enable in authoritative scenario until approved. |
| SCV-005 | Permission and tax decoupled; `tax_status=not_evaluated` until professional authority accepted, including pre-2000 conflicting tax labels. |
| SCV-006 | Public action `capital_asset` maps *only* to V2 internal `capital`; one versioned mapping, no permissive alias. |
| SCV-007 | Define persistent ruleset authority and historical version/effective date/signer/predecessor, not only static `MATRIX_VERSION`. |
| SCV-008 | M09 monthly cashflow adjustments are **not** pension product allocation aggregate. Use separate scenario decision aggregate, subject to architecture review. |
| SCV-009 | Contract must define component_id, lock ordering, idempotency, CAS, scenario total allocation, snapshot fingerprint, rollback and conflict precedence before authoritative save. |
| SCV-010 | Attach each professional prerequisite to named authoritative evidence producer, scope, version and reason code. Unrelated source allocations must not inherit an unreviewed V1 global blocker. |

### Proposed strict phased engineering boundary (NOT APPROVED TO IMPLEMENT)

**P0 / owner+contract:** finalize permission/eligibility/tax boundary, exception precedence, explicit reviewed eligible-subset semantics, residual, historical rules and evidence scope.

**P1 / read-only server preview:** read sources using client/product scope, classify from persisted canonical type, enumerate each component with structured allow/block/unresolved decisions; return `tax_status=not_evaluated`. No persistence and no dependency on factual execute.

**P2 / scenario aggregate:** separate versioned scenario/revision and append-only decisions under client, component_id, exact source version/fingerprint, deterministic money, total-availability constraint, idempotency and lifecycle. Never update factual components.

**P3 / explicit batch save:** client authorization, deterministic lock order, optimistic version, same ruleset and factual snapshot, revalidation and atomic rollback. No implicit pruning.

**P4 / frontend integration:** replace local mock permission guard with authoritative read-only preview; show original, permitted, blocked, unresolved and residual separately.

**P5 / negative and parity tests:** 11×2, exception precedence, cross-client, unknown product, change races, double allocations, stale ruleset, rejection rollback and full source snapshots. No financial outputs until accepted engines.

### OPEN owner decisions; must not be silently inferred

1. Can education/investment product-type overrides bypass blocked severance classifications or do blocked severance prerequisites always prevail?
2. What is the professional tax authority for pre-2000 employee/employer contributions' pension conversion?
3. Confirm explicit reviewed eligible subset vs whole-batch rejection for mixed plans.
4. Per-component exclusion acknowledgement or grouped review?
5. Is leave-unallocated only residual or also an explicit retain instruction?
6. What scope should unsettled severance/rights-continuity blockers have?
7. Who approves rule versions and retroactive applicability?
8. Which evidence source and currency/validity must govern termination, settlement, historical grants, tax approvals and 161d?

**Review outcome is binding as a release/milestone gate:** Do not hand off financial implementation to Codex as approved; correct and seek review of this contract first. Owner-reviewed 33/33 frontend and 15/15 backend results support only their narrow test surfaces, not the missing scenario engine.
