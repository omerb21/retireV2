# RETIRE V2 Stage 6 - Neon + Render isolated staging acceptance

Date: 2026-11-05

## Isolated environments

- Render review service: `srv-dbm5nerbc2fs738d4kqg`
- URL: https://retirev2-stage6-review-20261105.onrender.com
- Plan: Free, Frankfurt, auto-deploy disabled
- Branch deployed: `feature/neon-stage6-db-reconnect-20261105`
- Deployed app SHA: `bc637bf6335d148cafc2ac4c764a9679a9f8a2d4`
- Neon project: `broad-moon-42906584`
- Database: `retire_v2_stage6_validation`, PostgreSQL 16.15
- Database application role: `retire_v2_stage6_app` (limited privileges)
- Exact preview binding: Render service ID, external hostname and direct Neon host
- Active production service `srv-dbgr0ik9v7es73b6hs7g` was NOT changed.

## Verified acceptance

- Neon migration: `PREFLIGHT PASS`, `MIGRATION PASS`.
- Alembic head: `d6f1a9c3b704`; 77 public tables and 129 foreign keys.
- Stage 6 factor-admission append-only trigger verified.
- App role SELECT/INSERT yes, UPDATE/DELETE no for admissions.
- New bootstrap checks: 15 passed under pinned Python 3.11 dependencies.
- Stage 6 unit and API checks: 201 passed, 1 non-blocking warning.
- Isolated localhost PostgreSQL 16 integration: 9 passed; disposable Docker container removed.
- Render Docker build and startup complete, service deploy status `live`.
- Two **synthetic** clients were inserted in Neon by the restricted app role:
  - Client 1: `STAGE6_SYNTH_A_20261105`
  - Client 2: `STAGE6_SYNTH_B_20261105`
- No real customer data was migrated. No paid plan, production deploy or merge.

## Next acceptance gate

Run the HTTP smoke against the live Render service from a network-enabled machine:

```powershell
cd backend
git pull --ff-only
.\.venv-py311\Scripts\python.exe scripts\stage6_live_smoke.py
```

Provide the **staging-only** login password when prompted. The smoke script checks:
- Readiness 200 and unauthenticated Stage 6 rejection.
- Authenticated login and session.
- Synthetic client list and detail for A/B.
- Stage 6 capability on both clients.
- Missing-client handling and logout.

The live HTTP check has **not yet run successfully** and must not be marked PASS.
This staging environment does not establish correctness of all user-interface flows,
all financial results, tax/net computation, or production deploy readiness.

## Guardrails

- Do not point the active Render service at Neon.
- Do not merge the PR until live HTTP and manual browser review acceptance.
- Use synthetic data only in staging.
- Do not trigger GitHub Actions.
