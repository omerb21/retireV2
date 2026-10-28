# Work execution brief — RetireV2 UI readiness

**Mode:** ChatGPT Work — Medium
**Repository:** `omerb21/retireV2`
**Branch:** `development/retirev2-product-completion-20261028`
**Target:** `SCENARIO_UI_MANUAL_QA_READY=YES`, or an evidence-backed external blocker.
**Do not** move or alter `recovery/stage6-canonical-integration-20261028`, V1, Render or any production environment.

## Execution, not reporting

Continue working on the existing development branch. Do not stop after reviewing this brief or writing a plan. Use a fresh, isolated PostgreSQL database with synthetic clients only. Preserve Stage 6 accepted evidence rather than rerunning it without reason.

1. Run `scripts/verify_scenario_ui_readiness.ps1` or its exact individual commands in an accessible runtime; install dependencies from locked manifests if needed. Fix *every* test failure and TypeScript/build error in the branch. Record executed commands and actual outputs.
2. Launch the **original** backend and built frontend together using production-style authenticated middleware, dedicated local/staging-only configuration, `STAGE6_PREVIEW_ENABLED=1`, `RAILWAY_ENVIRONMENT_NAME=staging` and build-time `VITE_STAGE6_PREVIEW_ENABLED=1`. Isolate service credentials and database; do not alter production or create billable cloud resources.
3. Create synthetic clients, source components and versioned scenario drafts via existing accepted APIs/data initialization. Verify signed session, scenario persistence and the staged allocation-evidence UI at `/clients/{clientId}/workspace` > `תכנון תרחישים`.
4. Execute and repair the browser + PostgreSQL acceptance cases in `docs/ux/SCENARIO_UI_QA_RELEASE_GATE_2026-10-28.md`. The browser test must confirm amounts, blocked states, capital-only workflow, stale response invalidation, route visibility and security.
5. If local browser automation is unavailable, run an authenticated endpoint integration test against actual isolated PostgreSQL and report browser verification separately as **NOT_VERIFIED**. Do not call UI manually ready until it is actually viewable and tested.
6. Continue implementation and test repair without incremental status stops. Commit on the development branch only. Do not start GitHub Actions, create a parallel demo app, merge or deploy to production.

The approved professional scope is **nonfinancial allocation evidence** only. All M09 current cashflow, tax/net, M10 comparison and M11-M14 final product remain independently gated. Nothing in this brief authorizes invented financial formulas.

At completion provide exactly the working UI URL or reproducible local launch, test report with actual results, and current commit SHA. Do not claim readiness on code presence alone.
