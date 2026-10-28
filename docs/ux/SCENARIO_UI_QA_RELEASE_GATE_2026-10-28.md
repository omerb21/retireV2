# RetireV2 — Scenario UI QA release gate (2026-10-28)

**State: CODE_PREPARED_NOT_RUNTIME_VERIFIED**. This document records the path to a *manually testable staging UI*, not public release or final retirement plan.

## Actual original application entrypoint

- Frontend route: `/clients/{clientId}/workspace` (`frontend/src/routes/AppRoutes.tsx`).
- Select **תכנון תרחישים**, choose an existing draft with at least one decision.
- In `ScenarioDraftPanel`, the staging preview appears only with `VITE_STAGE6_PREVIEW_ENABLED=1` **at frontend build time**.
- The preview now includes **בקרת הקצאות תרחיש** for both pension and capital-only drafts; capital-only drafts do not expose pension election edit form.
- Back-end allocation GET: `/api/clients/{clientId}/scenario-drafts/{scenarioId}/allocation-evidence`.
- Back-end route is mounted **only** when signed-session production-style auth is enabled, `STAGE6_PREVIEW_ENABLED=1` and `RAILWAY_ENVIRONMENT_NAME=staging`. It is never mounted on regular production, Render or development server. Do not bypass this guard to make a demo work.

## Workstation preflight

On a separate recovery worktree, check out `development/retirev2-product-completion-20261028` without altering the canonical recovery branch, and run `scripts/verify_scenario_ui_readiness.ps1` in an environment with backend and frontend dependencies already installed. This executes narrow Python pytest suites, Vitest API/component suites, then a staging-enabled `npm run build` (TypeScript and Vite). A successful script is **not proof** of browser or PostgreSQL E2E behavior.

## Required browser-and-PostgreSQL acceptance

Only on a dedicated isolated staging deployment with synthetic client/products, approved schema migration head, signed-session auth and separate PostgreSQL:
1. Open client workspace, create/save a draft with two decisions allocating part of the same source; reload the page. Verify persisted version, correct component identity, action partitions, allocated and unallocated amounts.
2. Enter an exact balance, then exceed balance by ₪0.01. Verify `BLOCKED`; no available remainder, no financial result. Roll back decision change through a *new* draft version, not by editing factual sources.
3. Inspect a capital-only draft. Allocation section is visible; no pension election form or computed monthly pension is shown.
4. Change factual source version/balance after draft was created; prior structural evidence becomes stale. Verify source blocker appears without silently copying the old value.
5. Archive or switch scenario/client during an in-flight evidence fetch. The response must not appear in the new context.
6. Test missing/corrupted signed session, cross-client URL, non-staging route, invalid scenario ID and database failure. Verify no data exposure; fail closed with no-store headers.
7. Verify the previously approved Stage 6 one-decision nominal-gross flow still operates independently; never interpret principal allocation as Stage 6 gross pension output.
8. Test a second tab editing the same scenario during a read; currentness and version must be checked by the backend from its own snapshot.
9. Test keyboard navigation and small viewport, accessibility of alerts/status, and document RTL direction.
10. Verify no M09 current execution or M10 comparison was enabled; no tax, net, NPV, income gap or final retirement report is represented.

## Release boundary

- All new backend/TypeScript/unit/security tests must pass.
- Frontend bundle must build **with the preview flag**, and frontend and backend flags must both be correctly set in isolated staging.
- The original application must complete signed-session browser testing against actual isolated PostgreSQL.
- Failures must be repaired and rerun before calling `SCENARIO_UI_MANUAL_QA_READY=YES`.
- This work does not grant authority for pension aggregation, tax, M09 active cashflow, M10 comparison, M11-M14 recommendation or production deployment.
- No merge, GitHub Actions, Render changes, V1 production changes, Railway provisioning or deployment is authorized by this QA document alone.
