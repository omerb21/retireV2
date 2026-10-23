# RETIRE V2 — Owner's synthetic-case UX acceptance script

**Status:** READY FOR OWNER WALKTHROUGH — NOT YET PROFESSIONALLY ACCEPTED  
**Branch:** `feature/professional-workspace-ux-first-20261022`  
**Scope:** five-phase planning workspace, in-browser ephemeral scenarios only. This document does not authorize financial logic or production merge.

## Preconditions

- Use the *existing isolated local V2 synthetic client*, not a real client, and do not reset/recreate its PostgreSQL tmpfs container.
- Use the current locally running frontend, with the latest branch changes visible. No build or CI run required solely for this non-code document.
- The owner has confirmed `26/26` focused workspace tests and TypeScript/Vite build on commit `bc6cf38`. Automation confirms controls behave in tested cases, not professional appropriateness.
- Do not use the canonical conversion endpoint for scenario choices: it modifies authoritative facts.

## One realistic consultation — observable walkthrough

| Step | Action in UI | What should be visible | Owner decision to record |
| --- | --- | --- | --- |
| 1 | Open the synthetic client's workspace, Step 2 **תיק פנסיוני** | One ledger with monetary classifications and no duplicate product editors | Is identifying a source component practical without horizontal/vertical hunting? |
| 2 | Click one *positive* monetary component (not the entire product). Choose **העבר רכיב להדמיית תרחיש (ללא שמירה)** | Navigate to Step 4 **תכנון תרחישים** with the chosen product/classification preselected; factual balance unchanged | Is this transfer intuitive, and is its separation from **תיקון יתרות נבחרות** unmistakable? |
| 3 | Select **צור חלופת הדמיה**. Enter a positive partial amount smaller than the selected source balance and choose **ייעוד לקצבה**. Add the mock decision | One local decision listing source, mock amount and action; no calculation | Are action names and the selected component meaningful in ordinary planning language? |
| 4 | Allocate another part of the *same component* to **ייעוד להון**, keeping the total at or below its displayed balance | Both local decisions appear; no source-balance modification | Are the remaining, unallocated funds clear to the planner? **Currently not displayed** |
| 5 | Try another amount that exceeds the remaining source balance | A local validation warning blocks adding the decision | Is this enough as a UX prototype? Note that eligibility, timing and tax are **not** validated |
| 6 | Choose **שכפל חלופת הדמיה** then **בטל החלטת הדמיה** in the copied alternative | The copied alternative changes independently; the original remains intact | Does copy-and-cancel suffice, or do you need **edit an existing decision**? **Editing in place is not implemented** |
| 7 | Open Step 5 **תוצאות והשוואה** | Columns named after actually created temporary alternatives, with their decision summaries. All financial metric rows say **לא חושב** | Which comparison facts and explanatory details must precede calculated results? |
| 8 | Return to Step 4, change/delete another mock decision, then return to Step 5 | Comparison summary reflects the current local alternatives | Are controls easy enough to use repeatedly in a consultation? |
| 9 | Switch to another client or refresh the page | Ephemeral mock decisions disappear; nothing was saved to server | Is it sufficiently clear to the planner that this is **not a saved scenario**? |

**Important:** The user interface does not yet expose a professional final/approved scenario or complete retirement results. A snapshot of Step 5 is not an approved comparison report.

## Professional decisions blocking authoritative design

| Gate | Question | Proposed handling, pending owner approval |
| --- | --- | --- |
| Allocation status | Does **השארה ללא שינוי** mean an explicit allocation of that sum or simply undecided remaining funds? | Do not copy mock semantics into persistence; model residual as a separately defined state |
| Action date | When does the action become effective, and should retirement/withdrawal dates vary by component? | Add timing semantics to scenario definition before real calculations |
| Eligibility | Which monetary classifications may be converted or withdrawn, and under which conditions? | Separate authoritative validation rules from interactive mock constraints |
| Historical facts | What happens when grants, termination payments or tax evidence require reconciliation? | Exclude or mark affected computations as blocked, rather than assume |
| Source freshness | What if the official component balance changes after scenario creation? | Source snapshot/version + invalidation of stale computed output |
| Comparing alternatives | What counts as comparable outcomes (pension, capital, tax, liquidity, assumptions, dates)? | Work review at a single contract gate, once professional workflow is accepted |

## Owner feedback format

Record **one of** `APPROVE UX DIRECTION`, `APPROVE WITH CHANGES`, or `REWORK`, and note any friction with the exact UI step above. An approval here is **only** of navigation and planning UX direction; it does not approve tax law, pension eligibility, persistent scenario architecture, or deployment.

## Model-work separation and release safety

In-chat direct development is appropriate for low-risk mock UI and test refinements. Codex handles bounded substantial implementation **after** approved domain definitions; Work independently examines the coherent architecture/contract package. No Work/Codex independent review has been performed. No extra CI runs or production changes are authorized by this protocol.
