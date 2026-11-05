# RETIRE V2 Stage 6 - Neon and Render staging acceptance

Verification date: 2026-11-05

## Runtime and isolation
- Staging Render web service: `srv-dbm5nerbc2fs738d4kqg`, Frankfurt, Free.
- Public staging URL: https://retirev2-stage6-review-20261105.onrender.com
- Auto deploy disabled. Current validated deployed staging app commit: `6225fece670954cdfb2ffba6e91e20f6e8ac43b3` (deploy `dep-dbm7mt88v5cc73dqp990`).
- Source branch: `feature/neon-stage6-db-reconnect-20261105`.
- Neon: `broad-moon-42906584`, DB `retire_v2_stage6_validation`, PostgreSQL 16.15.
- DB connection uses the restricted application role `retire_v2_stage6_app`.
- Stage 6 capability bound to the approved Render service ID, hostname and Neon host.
- Production Render service `srv-dbgr0ik9v7es73b6hs7g` remains separate and unchanged.
- No real customer data migrated or accessed.

## Passed gates
- Alembic `PREFLIGHT PASS`, `MIGRATION PASS`; verified head `d6f1a9c3b704`, 77 public tables, 129 FKs.
- Immutable factor-admission trigger exists. Application role: SELECT/INSERT permitted; UPDATE/DELETE denied on that ledger.
- Windows Python 3.11 bootstrap: 15 tests passed.
- Stage 6 unit/API: 201 tests passed; one non-blocking library deprecation warning.
- Disposable localhost PostgreSQL 16 Docker integration: 9 tests passed; container removed.
- Render staging Docker deployment: status `live`, with frontend TypeScript/Vite build validated.
- Full frontend Vitest gate (run in staging Docker build, no GitHub Actions): **390/390 passed across 47 test files**. The scenario UI refactor and selected-alternative tab transitions are covered.
- Authenticated live HTTP smoke: `STAGE6_LIVE_SMOKE_PASS` with 13 individually reported PASS outcomes (readiness, negative auth, login, session, A/B clients and capability, missing client, logout/session invalidation).
- Authenticated synthetic product/scenario workflow: `STAGE6_SYNTHETIC_WORKFLOW_PASS`. Product creation, two A alternatives, one B alternative, professional-admission fail-closed responses, and cross-client scenario isolation all passed.

## Independent persisted-data verification
Read-only SQL against staging Neon after workflow:
- Client A (ID 1, `STAGE6_SYNTH_A_20261105`): one product, two draft scenarios, two draft pension decisions.
- Client B (ID 2, `STAGE6_SYNTH_B_20261105`): one product, one draft scenario, one draft pension decision.
- Each canonical synthetic product: 11 components, total balance ILS 200,000.00, version 2.
- A1: one ILS 100,000.00 draft pension allocation, version 2.
- A2: one ILS 140,000.00 draft pension allocation, version 2.
- B1: one ILS 90,000.00 draft pension allocation, version 2.
- All three draft decisions have source fingerprints and `validation_state=unverified`.
- Zero professional factor admissions and zero pension election records.
- Latest read-only Neon verification: 0 planning-input decisions/retirement targets. Therefore a persistent-Staging `RESULT_READY` gross calculation cannot be responsibly demonstrated using current fixtures: no pension election, no planning target and no factor evidence have been set.
- Alembic revision remains `d6f1a9c3b704`.

## Acceptance limitation and next gate
- Fail-closed gross estimations have been verified with missing professional evidence; **a positive READY gross pension value has NOT been verified live**.
- The user reviewed the scenario workflow screenshots and confirmed the simplified UI looks good. The redesigned interface separates planning and results, hides secondary professional diagnostics behind expandable sections, and preserves the selected alternative between tabs while respecting client scope.
- A later manual positive-amount check with controlled documentary evidence remains out of scope of this UX acceptance.
- Further positive financial-estimate acceptance requires explicit synthetic professional evidence with controlled admission; tax, net, actual retirement advice, and production release are out of scope.
- No merge into development/main, no production deployment, no manual GitHub Actions run.
- Keep this PR as draft pending **live positive-amount review and subsequent release decision**.
- The real PostgreSQL 16 Stage 6 P1D integration test does exercise a synthetic `RESULT_READY` gross calculation, aggregate and comparison successfully. It is not a substitute for a positive result on the persistent Staging Neon service.

## Frontend acceptance details
- Full suite was executed as `npm test -- --reporter=dot` in a Docker build stage, followed by a successful TypeScript/Vite build.
- One async UI test and a browser-like `<details>` disclosure assertion were repaired; all 390 final tests passed.
- Production Render remains on branch `codex/render-v2-runtime-recovery-01`, with auto-deploy off.

## Full portfolio conversion workbench - 2026-11-05
- User requested the same **full balance table** as the pension portfolio rather than selecting sources from a collapsed table or a single drop-down.
- The planning tab now uses `ScenarioConversionMatrix` and a shared `PORTFOLIO_COMPONENT_COLUMNS` declaration for the exact same 11 balance columns and their order.
- Supports a **single component** (including partial amount), **whole program**, or **whole column across all programs**.
- A grouped selection creates a draft decision per component and persists the group in **one atomic, versioned** `replaceScenarioDraft` request. Existing decisions and identities are preserved.
- Each selected component in a grouped plan has its own editable amount and effective date; an optional shared date acts only as a default.
- Strict integer-cent monetary arithmetic; refuses invalid, stale, mismapped or overallocated balances. A failed group selection cannot silently become a partial "whole program" or "whole column" plan.
- Operations are strictly **scenario draft planning**, not actual conversions or source-balance mutations. The existing professional authorization and gross-estimate gates remain unchanged.
- Redundant process-step narration was removed; readiness and technical comparison details are grouped under a single optional advanced diagnostics section.
- Staging Render Docker build: **390/390 frontend Vitest tests passed across 47 files**, followed by successful TypeScript/Vite build and LIVE deploy at `6225fece670954cdfb2ffba6e91e20f6e8ac43b3`.
- Independent Neon check after deploy: 2 synthetic clients, 3 draft scenarios, zero factor admissions; Alembic head unchanged.
- **Manual visual acceptance of the new conversion grid remains pending**; prior user approval applied to the earlier simplified planning view, not to this newly revised grid.

## Runbook
`backend/scripts/stage6_live_smoke.py`: authenticated read-only HTTP checks.
`backend/scripts/stage6_live_workflow.py`: guarded idempotent synthetic source/draft setup and negative-financial + cross-client checks.
`backend/scripts/run_stage6_unit_acceptance_win.ps1`: offline unit/API suite.
`backend/scripts/run_stage6_pg_integration_win.ps1`: disposable local PostgreSQL integration suite.
