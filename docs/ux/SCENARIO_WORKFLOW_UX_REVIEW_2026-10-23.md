# RETIRE V2 — Scenario workflow UX review (2026-10-23)

**Scope:** isolated UX branch `feature/professional-workspace-ux-first-20261022`; independent Work/Codex review **not performed**. This is an in-chat design review, not professional approval.

## Current evidence
- 25 focused workspace frontend tests and TypeScript/Vite build passed locally, owner-confirmed at commit `0e4fd31`.
- Scenario mock creates, duplicates, deletes alternatives, chooses product classification components and uses exact integer-cent controls for partial mock allocations; all state exists only in React memory.
- Scenario engine/persistence is not wired. Results render three fixed hypothetical columns with every computed cell marked `לא חושב`.
- Existing canonical conversion mutates authoritative source values and MUST NOT be called as a scenario decision.

## Journey gaps ranked

| Priority | Gap | UX consequence | Bounded next action |
| --- | --- | --- | --- |
| P0 | Results view is not connected to transient alternatives | Cannot complete create → compare → revise round trip, even as mock | Render dynamic alternative titles and **mock decision summaries only** in results; no calculated numbers |
| P0 | No source-line selection handoff from ledger to scenario | Planner must locate same classification again in another dropdown | Prototype a one-way, read-only selection handoff gated on no unsaved factual corrections |
| P1 | Decision amounts are only demo aggregate constraints | No professional eligibility/tax/temporal validation | Label specifically 'demo allocation guard'; defer authority to accepted scenario contracts |
| P1 | No stale/source-version lifecycle | Results could falsely appear current if authoritative facts change | Design explicit snapshot/fingerprint and stale state before real scenario execution |
| P1 | Supplemental sources/termination choices absent | Whole client journey not yet represented | Map data/decision contracts separately before controls |
| P2 | Fixed comparison grid | Cannot compare actual number of mock alternatives | Dynamic columns driven by ephemeral alternatives, with only decisions and 'not calculated' placeholders |

## Acceptance journey for UX-MOCK
1. Open an actual synthetic client and inspect factual portfolio, without modifying balances.
2. Start scenario preview, select an exact classification, record two partial illustrative allocations no greater than that component's reported value.
3. Duplicate the alternative, change a decision in the duplicate and confirm the original remains unchanged.
4. Move to comparison screen and see **the exact transient alternative names and their decision summaries**, never invented pension/capital/tax/NPV results.
5. Return to scenario screen and edit/delete a decision; verify the comparison preview reflects the change.
6. Switch clients / refresh and confirm the mock clears; verify no financial API write.
7. Independently review the resulting UX journey with the professional owner before changing domain contracts.

## Three-role / credit gates
- **In-chat:** simple UI mock, labels and focused tests only; never claim external independent review.
- **Codex:** only after UX direction acceptance; implement bounded scenario persistence and complex contract changes against approved definitions.
- **Work:** one coherent independent architectural and professional workflow review at transition to authoritative scenario capability; not after every UX commit.

## Safety / scope
No tax calculations, future tax parameters, simulated eligibility, client data publication, authoritative source mutations or production release. No automatic merger or CI expansion. In-chat review status: **completed with open UX items**. Independent Work review: **PENDING**.

## Follow-up review: connected prototype after 26/26 focused tests (2026-10-23)

**Verified evidence:** owner confirmed branch `bc6cf38` TypeScript/Vite build and 26/26 focused frontend tests pass; the review below inspects the actual code on the UX branch. These results are *automated UI acceptance evidence*, not an independent business sign-off.

### Closed prototype gaps
- **P0: dynamic comparison:** resolved in UX-MOCK. Alternative names, decision counts, exact component and mock amounts appear in Step 5; computed pension, capital, tax and NPV results are all explicitly unavailable.
- **P0: ledger handoff:** resolved in UX-MOCK. A single positive source component can be passed from Step 2 to Step 4, without persisting a scenario or using the canonical conversion endpoint.

### Remaining business-workflow blockers for authoritative implementation

1. **Professional meaning of an allocation:** the `unchanged` mock action currently consumes the selected amount in the same way as `pension` and `capital`; the real scenario contract needs clear semantics for a retained/undecided balance, mixed allocation, partial withdrawals and pension conversion. Do not copy mock decision types directly into backend schemas.
2. **Identity and traceability:** each decision currently references `product_id|classification_code` with an amount only. Real persisted scenarios need explicit client ownership, factual source version/snapshot, source provenance and effective decision date, plus eligibility status where appropriate.
3. **Data freshness:** Step 5 does not track whether a factual component changed after an ephemeral decision was created. Before genuine calculated results, implement a source version/fingerprint and a fail-closed stale result state. The current `לא חושב` labels prevent a misleading calculated outcome for now.
4. **Professional prerequisites:** historical employment settlements, severance grant reconciliation, tax approvals and retirement timing require explicit rule gates before relevant scenario paths are executable. A duplicate historical exempt grant marked `requires_reconciliation` must not silently be used for accepted tax computation.
5. **Scenario review ergonomics:** the prototype supports add/cancel/clone/delete; it has no in-place edit of an allocation, explanatory action labels, alternative naming, or client-level decision summaries. The owner should review this on a synthetic case before Codex implements persistent workflows.
6. **Interpretation of comparison:** baseline `מצב בסיס` is not an evaluated counterfactual; it is a placeholder. Do not display baseline financial deltas, rankings or optimization labels until both calculations and a comparison contract exist.

### Acceptance gate for the professional owner (not yet completed)

Walk a **single synthetic case** through facts → choice → partial allocation → clone → revise → compare. Check whether the choice of 11 components, the distinction between leave-as-is vs convert, and the decision sequence match a real retirement-planning consultation. Note where explanations, timing or other source documents are needed. The owner is *not required* to run technical shell commands for this review.

### Cost-conscious model split
- In-chat prototype and regression work: limited to view-only/local-state UX and targeted tests.
- Codex: once professional journey is approved, scope domain/persistence tasks by contract with no real-financial behavior inferred from prototype state.
- Work: independent multi-discipline audit at one substantive gate before acceptance/merge. **Not performed** as part of this review.

**Gate decision:** `UX-MOCK = technically verified; professional user acceptance PENDING; scenario domain contract PENDING; independent audit PENDING`. No production merge or financial engine development authorized by this review.

## Owner's professional acceptance findings and response (2026-10-23)

**Scope of owner feedback:** UX direction reviewed on local synthetic case, not acceptance of scenario financial implementation. Result: **APPROVE WITH CHANGES** (scenario flow requires further real-world use).

### Accepted for UX direction
- Existing horizontal scroll for numerous canonical monetary classification columns is acceptable.
- Fact correction vs scenario action distinction is clear.
- Partial allocation, over-allocation guard, cloning, cancellation and return-to-correct are usable as a provisional mock.
- Direct in-place editing of a decision is not necessary now; cancellation and re-creation suffice.
- Scenario persistence is **UNDECIDED**, and ephemeral state is acceptable in the current prototype.

### Owner change requests
1. **Ledger totals:** keep both imported/reported total and **computed sum of classified balances**, visually distinct. Deferred, not essential to this mock iteration. Must clarify inconsistency/reconciliation behavior; do not replace the reported figure.
2. **Choice granularity:** planning must permit **whole pension plans and individual monetary components**. Current component-only handoff is insufficient. **OPEN design requirement**; a whole plan may span different tax classes, so 'one action on whole plan' must be designed without collapsing provenance/tax distinctions.
3. **Scenario context:** show original source component balance, sum allocated within current mock alternative and amount still available. Implemented UX only; no server calculations.
4. **Warning salience:** emphasize over-allocation notice. Implemented accessible alert with stronger visual treatment.
5. **Comparison:** compare how much capital and how much pension each scenario yields and how much portfolio remains unutilized; eventually add NPV. In mock display **nominal principal allocated to pension/capital** separately labelled, NOT calculated monthly pension/withdrawal; full unused portfolio remains uncomputed pending approved scope/engine.
6. **Workflow readiness:** owner needs extended hands-on usage before locking scenario UX; do not mark professional journey fully accepted.

### Contract decisions intentionally deferred
- Semantics and eligibility of a whole-plan choice (by plan vs decomposition into 11 classification components), whether mass actions are bulk suggestions or binding, and override granularity.
- Defined portfolio 'computed total' vs reported total, reconciliation and whether empty classifications count.
- Meaning of 'remaining' — non-allocated within the selected component, all selected sources, or whole factual portfolio, including unclassified amounts and historical tax reconciliation; prevent double counting.
- Mapping nominal capital sources to actually **withdrawable capital** and nominal pension-designated sources to **monthly pension income**; no conversion without authorized assumptions, indexation/retirement date/actuarial factors/tax rules.
- NPV model and presentation only when authorized V2 financial engines and underlying assumptions are valid.
- Whether mock/real alternatives need retention and for how long. No automatic persistence.

### Readiness statement
**UX mock technically testable, user-approved with changes, domain contract and independent Work gate PENDING.** Do not call the mock scenario comparison a financially computed retirement comparison.
