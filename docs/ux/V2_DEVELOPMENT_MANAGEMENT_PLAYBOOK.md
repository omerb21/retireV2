# RETIRE V2 — Development Management Playbook
**Owner continuity notes — 2026-10-22**

> Read this document **before doing any new development**. This is the owner-discussed operating approach, not an independent authorization to change protected business logic, merge or deploy. The accepted V2 Governance Protocol v1.1 and explicit Owner/Product Decisions prevail if a rule conflicts.

## 1. Central correction learned in October 2026

The V2 development process spent substantial effort on canonical state, evidence, inputs, audit/provenance, tax/scenario definitions and authoritative contracts, while neglecting the real planner's **work rhythm**. A technically complete data model is not a usable professional product. The first React shell and the long ClientDetailScreen with extensive status/provenance fields failed the owner’s hands-on usability review. A list of all modules and technical statuses is not an acceptable professional workflow.

A first narrow UX table with many appended per-product editors also failed. The owner specifically objected to endless scrolling, duplicate product displays and unclear conversion affordances. Editing a financial classification is **not** a pension/capital conversion.

A later standalone interactive HTML prototype for **the whole synthetic client journey** was viewed by the owner and approved as the *UX direction* (appearance and flow, not financial correctness). The owner is open to improving upon V1, not demanding visual duplication.

**Rule:** Design the planner's complete professional journey before mapping accepted M01–M14 modules to screens. Organize UI around decisions and actions, not persistence entities, implementation packages, proof labels or arbitrary technical completeness states.

## 2. Approved UX north star

One client workspace with 5 visible practical phases:
1. **Client and case** — short, relevant case identity, easy entry to the real work. Put deep provenance/status details behind contextual disclosure, not on the default screen.
2. **Pension portfolio** — ONE ledger, one product per row, 11 canonical monetary classifications as columns, totals/reconciliation as needed, selection of cells, contextual action panel, compact expandable product details. Avoid a list of duplicate full product editors below the table.
3. **Supplementary professional facts** — employer/employment, historical grants, pensions already in payment, further income, capital assets and relevant client facts; accessible without drowning the user in controls.
4. **Named scenarios** — create, duplicate, modify, reverse decisions; select portions of monetary components and convert to pension or capital within an isolated scenario; incorporate employer/severance choices and timing.
5. **Results and comparisons** — compare accepted evaluated scenarios with clear basis, tax and temporal qualifications, then reporting/161ד where applicable and authorized. No fabricated pension/NPV/tax results.

This is not a demand that the end product be exactly five routes: it is the visible workflow. Backend modules may be numerous but must be largely invisible to the day-to-day planner.

**Acceptance:** Owner review must test a **complete end-to-end synthetic case**, including returning to previous decisions, changing sources, building alternative scenarios and comparing outputs. Review of disconnected pretty screens is inadequate. Synthetic UI can validate UX; it cannot prove business calculations.

## 3. Three different operations must NEVER be conflated

- **Source evidence**: original clearinghouse XML/snapshot and reported values; preserved for provenance. Imported data can be wrong, incomplete or contradictory.
- **Factual correction / monetary reclassification**: professional adjustment to an actual client's product balance/11 monetary columns. Version-checked saved canonical product facts; retain original evidence and audit reasons/history as accepted contracts require. Moving 10,000 between classification columns is NOT conversion.
- **Scenario conversion**: hypothetical allocation of some/all of a component to a pension or a capital asset, including applicable eligibility, coefficients, timing and tax rules. It creates a separate decision in an independent scenario, not a mutation of actual source balances. Scenario choices may be reversed/modified without restoring full system snapshots or deleting actual records.

Critical discovered implementation issue: V2's existing `POST /canonical-conversions` **changes persisted factual PensionProductComponent balances**. Do NOT call it as scenario execution, and do not execute-and-reverse it to simulate independence. Its preview is not sufficient proof of a new scenario engine.

V1 snapshot/restore existed because V1 scenario conversions mutated factual balances; do not perpetuate that design flaw in V2. Scenario evaluations become stale/need revalidation when authoritative facts change; preserve decisions, never silently recalculate or present stale outputs as current.

Financial amounts are exact decimal strings; do not calculate authoritative money with browser floating point. No invented 161ד eligibility/future exemptions/tax ceilings, pension factors or NPV values.

## 4. Design-by-workflow development rules

- Examine V1 code as **behavioral evidence** where useful (selection, decision sequencing, conversion rule mapping), not as a blueprint for copying V1 bugs or UI.
- Map existing authoritative V2 contracts to each action; identify which producer is not yet implemented. A route, stub, API name, test fixture or attractive prototype does not prove functioning business capability.
- State clearly at every increment what is: UX-only, frontend connected to live GET/PUT, backend verified, calculation validated, or production-ready. Never blur these labels.
- Build **one bounded, vertical slice** that a planner can use; check the entire user action including error states and reversal before adding more technical panels.
- Keep critical background audit/control/data lineage in the system, available contextually; hide implementation machinery from default UI without deleting it.
- Do not leave the owner to infer button meanings: “classification correction”, “conversion to pension”, “conversion to capital” must be distinct, explicit actions.
- Preserve the accepted financial and tax authority of V2. The UI consumes; it must not create alternative formulas, inferred permissions or its own calculation engine.

## 5. Governance, independent reviews and role division

- **Owner is the professional authority**, not a Git/CI engineer or the project's manual quality-control system. Ask the owner only for genuine product decisions or necessary external inputs, and never repeatedly ask for information or approvals already given.
- The assistant responsible for a defined task should **do the technical work itself** with connected GitHub/tools when available, rather than inventing inaccessible tools or shifting routine Git troubleshooting to the owner. Distinguish what the tool can verify from what requires owner's local Windows/Docker runtime.
- Earlier substantial authoritative-engine packages used a **multi-model workflow**: bounded implementation, separate technical scrutiny and independent acceptance/master closure audit; reuse that approach for financial-engine/model changes. A UI spike may be developed in an isolated branch more directly, but passing a handful of UI tests does not replace independent authorization for business-engine or production changes.
- Governance Protocol v1.1: respect accepted definition/implementation packages, source evidence, owner decisions, authority boundaries and explicit acceptances. **Do not reopen accepted packages or repair them speculatively**, do not broaden scope to solve one obstacle, and do not activate downstream modules without required acceptance.
- Master closure / controlled merge: compare the exact base/head/TREE, change list, approval evidence and target master drift; do not auto-resolve divergence or overwrite accepted work. Independent acceptance and approval to merge/deploy are separate gates. `production readiness = NOT_CLAIMED` until affirmatively demonstrated.
- Parallel development chats need explicit central coordination. They do **not** have magically different GitHub permissions; avoid inventing distinct tool access between chats. Do not assume a secondary chat can deploy where another cannot.
- No production write/merge/deploy in this UX branch absent explicit authorization. Source-change commits to a named isolated development branch are not the same as master merge or production deployment.

## 6. Time and CI-cost controls (hard lessons)

- The owner experienced excessive repeated CI executions, including a run that triggered ~13 CI executions in one development cycle. **Never run the full CI suite after each commit.**
- Check workflow configuration and recent runs before triggering CI. Prefer fast static inspection, local targeted tests and a single consolidated validation after code is stable.
- The owner has explicitly approved **one full CI run** in prior workflows when asked; do not treat old approval as perpetual permission for unlimited expensive runs. Honor budget constraints and the CI policy of the actual repo/branch.
- Do not create uncontrolled bot loops of fix–commit–CI–new blocker–fix. Identify dependencies, contracts, acceptance scope and likely failures **up front**; batch coherent fixes, then test once. Reuse valid prior evidence; revalidate only affected deltas.
- Protect the user from repeated technical back-and-forth. If a multi-step task can be completed with available tools, continue until a substantive blocker, delivering tangible progress. If local device action is required, provide exact minimal PowerShell commands and explain why.
- Work credits, CI runner minutes and deployment risk are real costs. Prefer direct GitHub tools and isolated local tests where sufficient; do not spend Cloud Work/CI credits merely to change and redeploy a static preview.

## 7. Environments and safety

- GitHub repository V2: `omerb21/retireV2`. V1: `omerb21/retire`; they are distinct. Railway hosts the V2 server, but has experienced outages. Do not let an outage trigger uncontrolled production work.
- Use *isolated* branches and synthetic client records. For local end-to-end tests prefer Docker Compose PostgreSQL with disposable storage and FastAPI in development mode. Never copy production database, secrets, session cookies, client identities or Railway DB credentials to a test machine.
- Authentication, 2FA, narrow DB roles, CSRF, session, client isolation, exact monetary values, append-only audit and source provenance are non-negotiable. Do not disable security safeguards simply to get a local run working.
- Before shipping a test harness, inspect database migrations' explicit runtime prerequisites, roles and permission grants. Local Docker success requires more than an HTTP `/health` response: verify migrations, seed, persisted update and isolation.
- If a test harness fails, distinguish **harness failure** from product defect. Capture the exact failing command and code path, repair minimal setup, rerun in isolation, not in production.

## 8. Development status labels

Use separate truthful statuses:
- UX direction owner-approved;
- frontend code drafted;
- frontend TypeScript/build/tests passed, with exact SHA and counts;
- local FastAPI/Postgres integration pending/passed;
- scenario persistence pending;
- scenario business engine pending;
- M09 new execution pending, M10 replacement comparison pending;
- independent professional acceptance pending;
- merge/production deployment **not authorized**.

Do not announce “finished”, “working real scenarios”, “fully tested” or “production-ready” on the strength of screenshots or mocked frontend tests.

## 9. Mandatory handoff across chats

At a chat boundary, update **two separate documents** in the active branch:
1. `docs/ux/V2_DEVELOPMENT_MANAGEMENT_PLAYBOOK.md` (this stable management/UX rulebook);
2. `docs/ux/V2_CHAT_HANDOFF_2026-10-22.md` (exact current branch, SHA, committed files, blocker, next step and test evidence).

Start a new chat by instructing it to read both files from GitHub **before any further code changes**, plus accepted repo governance as needed. Update the handoff after subsequent steps. Do not rely on conversation memory alone, copied assistant assurances or an old release notes artifact.

**If this playbook and authoritative accepted business governance conflict, STOP and surface that exact conflict; neither these notes nor prior assistant statements silently supersede higher authority.**
