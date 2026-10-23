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

## 13. Technical contract decisions safe to specify without financial owner approval

These are **proposed engineering constraints**, not permission to implement the engine or to select disputed pension/tax policy.

1. **Closed action vocabulary:** public scenario action values are `pension`, `capital_asset`, and a separate residual/retain status pending semantics. The only authorized adapter mapping for conversion actions is `pension -> pension`, `capital_asset -> capital` when consulting V2 `destinations()`. Unknown action values fail with a structured validation code; do not silently normalize aliases.
2. **Product-type safety:** scenario eligibility uses only the server-stored product row associated with the client and component. An explicit canonical product-type resolver must reject missing, ambiguous or unknown types as `needs_professional_resolution`, never rely on the ordinary `BASE_MATRIX` fallback. Crucially, recognizing a product type does **not** imply overriding severance prerequisites; that policy remains undecided.
3. **Unresolved professional rules default:** where eligibility, tax treatment or documentation is disputed, response state is `needs_professional_resolution`. No final financial output and no accepted conversion decision can follow from that state. This avoids implicitly deciding whether legacy V1 special-product precedence was lawful.
4. **Read-only preview and factual immutability:** preview gathers authoritative source and rules, reports full component inventory and reasons; it does not create decisions, pensions or assets, and cannot call factual `execute` or `reverse`.
5. **Explicit submit only:** a whole-product selection is a *preview scope*, not implicit permission to save all eligible components. Subsequent save may only refer to an exact, user-reviewed list of source component IDs and amounts. Submitted batch is atomic: if any submitted item is now invalid, none is accepted. Whether excluded rows must be individually acknowledged remains an owner decision.
6. **Deterministic monetary validation:** Decimal(20,2) source amounts; forbid binary floating point for backend money, reject malformed, negative, zero and over-allocated requests, including total assigned across the *same scenario*. Preserve component-level precision and prohibit double counting.
7. **Concurrency contract to be independently reviewed:** acquire locks in a consistent documented order (client → scenario aggregate → affected products by ID → components by ID); enforce optimistic `scenario_version`, product versions, source fingerprint and idempotency on save. Each request either commits *all enumerated decisions* or returns a structured rejection with **no partial decision writes**. Specific locking mechanism/transaction DB compatibility requires implementation review.
8. **Currentness:** a source/ruleset change invalidates evaluated outputs and labels affected scenarios `needs_revalidation`; preserve historical decisions, evidence and revisions rather than deleting or silently recalculating results.
9. **Scoped prerequisites:** each precondition must declare producer identity, subject (component/product/scenario), effective date, source version and missing-vs-inapplicable status. For an undecided V1 global severance blocker, mark impacted eligibility unresolved; do not apply an unreviewed blanket block to unrelated decisions.
10. **No early tax claims:** permission preview always uses `tax_status=not_evaluated` until the professional tax authority is accepted. V1 frontend's `localStorage` settings never become V2 authoritative rules.

### Residual approval board (professional decisions only)

| Decision | Safest provisional behavior until owner chooses |
| --- | --- |
| Product exception vs prohibited severance | Do not grant contested override; flag resolution required |
| Pre-2000 tax classification | Never publish approved taxable/exempt outcome; not evaluated |
| Mixed-plan eligible subset | Preview all and permit **no automatic submit**; explicit submitted list as engineering constraint |
| Acknowledging excluded rows | Display all exclusions; record neither implicit consent nor silent discard |
| Leave-unallocated semantics | Treat unassigned money as calculated availability **in preview only**; no persistent interpretation |
| Global unresolved-severance block scope | Do not infer cross-source eligibility; mark affected prerequisites unresolved |
| Ruleset editor/authority and historical effect | No mutable production rule governance inferred from static version string |
| Evidence for termination/settlement/grants/tax/161d | No successful eligibility classification without source-backed prerequisites where applicable |

This section closes ambiguities of **technical safety behavior**, not those professional choices. `CONTRACT_READINESS=BLOCKED` and `IMPLEMENTATION=NOT_AUTHORIZED` remain unchanged until reviewed.

## 14. V2 evidence-producer mapping — direct code inspection

- **Monetary source:** `backend/app/models/pension_product.py` holds the 11 canonical component balances, `product_id`, `product_type` and version. Source identity/version and a scenario-specific fingerprint still need a formal contract.
- **Reported versus calculated total:** `backend/app/services/pension_product_reconciliation.py::reconcile` already computes exact Decimal component sums and reported-total discrepancies; it never distributes a discrepancy. Future UX should reuse this, not invent totals.
- **Employment/termination:** `backend/app/models/employment_record.py` contains start/end dates, current status and exempt grant status, including `requires_reconciliation`. Presence of a historical employment record does not by itself prove eligibility for conversion.
- **Historical grants:** `backend/app/models/grant.py` supports a client-scoped grant with optional employment-period link and dated nominal/indexed amounts. A matching/approval rule for a particular pension component has not been established.
- **Personal dates:** `backend/app/models/client_profile.py` contains optional birth date and gender. These are not a complete accepted pension coefficient or retirement-date authority.
- **Tax approvals / 161d:** no authoritative producer was established in this targeted inspection. Tax output remains `not_evaluated` until evidence and professional rules are accepted.
- **Conversion permission:** `backend/app/services/canonical_conversion_matrix.py` has a static rule version, not a historical signed ruleset registry.

**Proposed evidence DTO:** source ID, source version or digest, effective date, scope (component/product/scenario), status (satisfied/missing/requires_reconciliation/not_applicable/unverified), and structured reason code. Do not equate an available row with an approved eligibility determination.

**SCV-010 remains OPEN:** mapping an employment period, grant or tax approval to a specific source component requires an accepted authority and scope. `CONTRACT_READINESS=BLOCKED`.

## 15. Owner-approved O-03: reviewed eligible subset of a whole plan (2026-10-23)

**APPROVED PRODUCT WORKFLOW:** For a whole pension plan, show **every classified component** and its eligibility status; allow a conversion for only the permitted subset after the planner has explicitly reviewed and confirmed it. Prohibited components are not converted. **Never silently discard excluded components** or imply the entire plan was converted.

**Required proposed contract semantics implementing O-03 (subject to technical independent re-review):**
1. Server preview enumerates all factual components, source balances and exact classifications; displays allowed / prohibited / unresolved independently, with Hebrew reasons. Product-type overrides remain unresolved by O-01 and cannot be treated as permitted merely by the UI.
2. Planner selects the desired eligible components and amounts, while the interface keeps all excluded components visible. Nothing is implicitly selected for a commit and no preview is a write.
3. Before submission, show a clear confirmation of selected components/amounts and excluded/rejected/unresolved components. O-04 remains OPEN regarding whether each exclusion needs its own acknowledgment or a single reviewed-group acknowledgment.
4. Submit **only explicit component IDs and exact amounts**, not a `whole_product=true` execution request. Server independently revalidates client ownership, source/version, action permissions, exact balances, source fingerprint and batch validity; any invalid submitted component rejects the *entire submitted batch* with zero partial writes.
5. Original factual source components, forbidden components and residual balances are never changed by scenario decisions. Report unconverted funds separately; no invented tax, monthly pension or NPV.
6. This is a scenario-domain UX/business decision only. The existing V2 factual `whole_product` code path, which reports `skipped` and performs actual mutations, is unchanged and **must not** be reused as a scenario implementation.

**O-03 is CLOSED / APPROVED. O-01, O-02, O-04, O-05, O-06, O-07, O-08 remain OPEN.** Independent Work review verdict `BLOCKED` and implementation prohibition remain until these and other critical contract gates are addressed.

## 16. Owner-approved O-04: one grouped acknowledgment of excluded components (2026-10-23)

**APPROVED:** One explicit confirmation is sufficient for the entire excluded-component group, **only after** presenting the complete list of excluded components and the individual reason for each exclusion. No need for one click per excluded row. This complements the owner-approved O-03 explicit eligible-subset selection.

**Proposed implementation safeguards, subject to independent contract review:**
- Before confirmation, display each excluded source product/component identity, its positive balance, the attempted destination, and the specific blocked/unresolved reason. Keep excluded and available amounts distinct.
- The grouped acknowledgment applies to a specific preview revision/fingerprint comprising the chosen action, selected amounts, and complete exclusion list/reasons. A changed source balance, eligibility result, selection, or ruleset invalidates that acknowledgment and requires redisplay and reconfirmation.
- Confirmation does not reclassify forbidden components as legally convertible, does not authorize an unknown product-type exception, and cannot waive missing professional evidence.
- On submission, revalidate the explicitly selected permitted component IDs and amounts atomically in the scenario service. Any newly disallowed item rejects the submitted batch, without factual mutations or implicit omission.
- Audit metadata should record only that the *displayed exclusion set* was acknowledged under the preview revision; it must not imply individualized tax or severance eligibility approval.

**O-03 and O-04 are now CLOSED / OWNER APPROVED.** O-01, O-02, O-05, O-06, O-07, O-08 remain OPEN. Independent Work contract verdict and implementation gate remain BLOCKED.

## 17. Owner-approved O-05: automatic unallocated residual (2026-10-23)

**APPROVED BUSINESS DECISION:** Funds not allocated to pension or capital remain an **automatically calculated unallocated residual**, not a separate conversion, retention, or `leave_unallocated` decision. This applies at the component level and to the sum of the plan, within an individual scenario.

**Proposed precision and presentation contract (pending independent technical re-review):**
- For each source component `c`, compute `residual_c = factual_original_balance_c - sum(accepted_scenario_allocation_amounts_c)`. The plan residual is the exact sum of component residuals. Sum across distinct component IDs only; no duplicated counting if a component has multiple allowed allocations.
- A draft selection is not yet an accepted allocation. Preview may present a separately labeled **projected remaining** amount based on the draft, but persisted/effective residual uses accepted scenario decisions only. Never silently merge draft and accepted totals.
- Require `0 <= accepted_allocations_c <= factual_original_balance_c` for every component. A negative result or stale source version must fail validation, not be clipped to zero.
- When the source/ruleset changes, mark the scenario `needs_revalidation` and distinguish historical accepted allocations from current availability; do not present stale residual as a newly validated balance.
- The residual remains in the original factual product classification and is not automatically pension income or capital asset. No fabricated tax result, monthly income, NPV or source mutation.
- Display at minimum **original classified component balance**, **accepted allocated principal**, and **automatically calculated remaining principal**. Where the reported plan total differs from classified sum, show the discrepancy separately via existing canonical `reconcile`, not by allocating it.

**O-03, O-04, O-05 CLOSED / OWNER APPROVED.** O-01, O-02, O-06, O-07, O-08 remain OPEN. Contract readiness remains `BLOCKED`; no authorized scenario-engine implementation.

## 18. Owner-approved O-06: scoped unsettled-severance blocker (2026-10-23)

**APPROVED:** An unsettled severance component, including unresolved employment settlement or rights-continuity prerequisites, is blocked from conversion, as are operations whose professional eligibility **actually depends** on resolving it. The existence of such a component does **not** automatically block conversions of unrelated employee/employer contribution components in the same product or scenario.

**Technical enforcement contract proposed for independent review:**
1. Determine blockers for each requested source component and action, with an evidence-backed `dependency_scope` identifying the affected component(s) and specific reason code; never copy V1's blanket global blocker into the V2 scenario engine.
2. Do not infer that a contribution component depends on unsettled severance merely because both belong to the same pension product or client. A broader blocker requires explicit, reviewable professional evidence and a rule establishing that dependency.
3. Preview must display blocked/unresolved severance items alongside independent eligible contribution items, including reasons and any dependency links. This integrates with approved O-03 whole-plan subset and O-04 grouped excluded-component acknowledgment.
4. Revalidate every submitted component and declared dependency under the same server transaction; if a selected item becomes blocked, reject the **submitted batch atomically**, without excluding it silently. Independently eligible items remain available for a new explicit request.
5. This decision does **not** resolve O-01 product-type exception precedence or O-08 the required evidence producers and severance-specific validity criteria. Until those are accepted, affected cases remain `needs_professional_resolution`; never invent eligibility.
6. Scenario cancellation or amendment must not write source balances or perform factual conversion reversal.

**O-03, O-04, O-05, O-06 are owner-approved and CLOSED.** O-01, O-02, O-07 and O-08 remain OPEN; `CONTRACT_READINESS=BLOCKED` and `IMPLEMENTATION=NOT_AUTHORIZED`.

## 19. O-01 owner clarification: product classification is not severance entitlement (2026-10-23)

**Professional source clarification received:** Education funds (`קרן השתלמות`) and investment provident funds (`קופת גמל להשקעה`) do not have genuine severance components. Their product-type override exists because actual source balances may appear in different technical contribution columns, including post-2000 contribution columns that ordinary pension products cannot convert to capital. Treating those technical columns as conclusive eligibility would incorrectly block capital conversion for these two product classes.

**Correction to earlier contract discussion:** The hypothetical conflict 'a genuine severance component in an education/investment fund is legally overridden' is not the business reason for the V1 exception, and must NOT be presented as such. A severance-coded source row under one of these product types is a **source classification anomaly**, not an approved severance conversion. It needs source reconciliation before any authoritative scenario eligibility decision. This does not change O-06's scoped protections for genuine severance in products where severance is applicable.

**Proposed test/contract obligations:**
1. Verify canonical product type from server-controlled source metadata; do not trust an arbitrary browser-supplied type, substring alone, or unknown-type base-matrix fallback.
2. For verified education-fund / investment-provident-fund products, permit the product-specific **capital eligibility check** for balances found in genuine contribution columns, including `תגמולי_עובד_אחרי_2000` and `תגמולי_מעביד_אחרי_2000`, subject to any separately accepted evidence prerequisites.
3. If a component has a genuine severance code under one of these products, return `needs_source_reconciliation`; do not silently relabel as contribution, and do not infer professional approval from the legacy override.
4. Continue separating destination permission from tax determination. Existing `capital_gains`/`exempt` labels in the factual matrix do not become approved scenario tax outputs.
5. Add explicit parity/negative cases for irregular technical contribution-column placements, unexpected severance-coded components, unknown product type and correctly typed normal pension products.

**Decision status:** O-01 business rationale is clarified by owner; exact server-side type resolver and inconsistent-input handling are proposed for acceptance. The overall contract and implementation remain `BLOCKED` pending remaining policy/evidence decisions and independent review.

## 20. O-02 source-level tax conflict isolation (2026-10-23; NOT an owner tax ruling)

A targeted comparison of V1 `frontend/src/config/conversionRules.ts` default rules, V1 backend `app/services/pension_portfolio/conversion_rules.py`, and V2 backend `backend/app/services/canonical_conversion_matrix.py` confirms the following **for ordinary product types**:

| Component | Destination permission | V1 frontend default pension tax | V1 backend pension tax | V2 backend pension tax |
| --- | --- | --- | --- | --- |
| `תגמולי_עובד_עד_2000` | allowed | `exempt` | `taxable` | `taxable` |
| `תגמולי_מעביד_עד_2000` | allowed | `exempt` | `taxable` | `taxable` |

The frontend code comment identifies these as capital-origin contributions, whereas its tax label differs from backend defaults. The frontend also supports `localStorage` rule loading, so those defaults do not constitute an immutable tax authority. **No source inspection adjudicates real Israeli tax entitlement, whether the converted principal is exempt, or whether a pension payment is exempt.**

**Binding scope of the future scenario permission contract:** A permission to allocate to `pension` can be displayed as a permission only. Tax classification must be returned as `not_evaluated` in scenario preview/decision responses until O-02 has a professional disposition and documented evidence. Preserve the original component identity and existing factual source details for future tax calculation. Do not silently copy `tax_for` into the scenario tax result. Do not change factual tax rules in V1 or V2 as a side effect of this contract.

**Required professional ruling for O-02:** specify separately (a) capital-origin nature of pre-2000 contributions, (b) whether and when converting them to a pension creates exempt versus taxable pension payments, (c) whether allocation permission and tax entitlement can diverge, (d) required evidence/effective-date authority, and (e) which existing V1 behavior is financially correct for actual users. Do not choose `exempt` merely because of a frontend comment, or `taxable` merely because two backends agree.

**O-02 remains OPEN.** The independent Work `BLOCKED` contract readiness and `NOT_AUTHORIZED` financial implementation gates remain unchanged.
