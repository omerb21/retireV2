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
