# RETIRE V2 Stage 6 - Neon and Render staging acceptance

Verification date: 2026-11-05

## Runtime and isolation
- Staging Render web service: `srv-dbm5nerbc2fs738d4kqg`, Frankfurt, Free.
- Public staging URL: https://retirev2-stage6-review-20261105.onrender.com
- Auto deploy disabled. Currently deployed staging app commit: `bc637bf6335d148cafc2ac4c764a9679a9f8a2d4`.
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
- Render staging Docker deployment: status `live`.
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
- Alembic revision remains `d6f1a9c3b704`.

## Acceptance limitation and next gate
- Fail-closed gross estimations have been verified with missing professional evidence; **a positive READY gross pension value has NOT been verified live**.
- The user has seen and confirmed the authenticated A/B client list, but **manual scenario screen acceptance is pending**: open A workspace, choose `תכנון תרחישים`, review A1/A2, check Stage 6 panel and blockers, switch to B and verify B-only context.
- Further positive financial-estimate acceptance requires explicit synthetic professional evidence with controlled admission; tax, net, actual retirement advice, and production release are out of scope.
- No merge into development/main, no production deployment, no manual GitHub Actions run.
- Keep this PR as draft pending UI review and subsequent release decision.

## Runbook
`backend/scripts/stage6_live_smoke.py`: authenticated read-only HTTP checks.
`backend/scripts/stage6_live_workflow.py`: guarded idempotent synthetic source/draft setup and negative-financial + cross-client checks.
`backend/scripts/run_stage6_unit_acceptance_win.ps1`: offline unit/API suite.
`backend/scripts/run_stage6_pg_integration_win.ps1`: disposable local PostgreSQL integration suite.
