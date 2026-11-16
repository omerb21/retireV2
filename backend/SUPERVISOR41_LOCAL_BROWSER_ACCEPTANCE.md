# RETIRE V2 | Supervisor 41 | isolated Windows browser acceptance

## Run

From the **existing** RETIRE V2 worktree root in Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\run_supervisor41_browser_win.ps1
```

Prerequisites: running Docker Desktop with Linux containers, Node.js + npm,
an existing backend Python 3.11/3.12 virtual environment at
`backend/.venv-py311` or `backend/.venv-py312`, and access to download the
pinned `@playwright/test@1.56.1` plus Chromium the first time. Existing
backend Python dependencies must already be installed. The harness installs
missing frontend node packages into `node_modules`, without updating
`package.json` or `package-lock.json`.

**No production credentials or services are needed or used.** The script
overrides the current process `DATABASE_URL` to a fresh Docker PostgreSQL 16
instance listening on a random 127.0.0.1 port. The seed rejects any database
URL outside `127.0.0.1/localhost/::1` or not named
`retire_v2_supervisor41_test`. It invokes the repository's existing Alembic
migrations, and creates only an explicitly synthetic client, linked employment
and grant, pension severance component, and two draft alternatives.

Backend listens on `127.0.0.1:8001`; Vite uses `127.0.0.1:5173`, reusing
the existing proxy. Both ports are checked for availability before launch.
Vite is started with `--mode test` and backend with `APP_ENV=test`. This
uses the application's *existing* nonproduction auth bypass solely on
localhost. It is **not** a test of production authentication or CSRF.
The browser blocks external requests.

## Browser scenarios

The Playwright test drives the actual retirement workspace:

1. Opens the synthetic client, navigates to scenario planning.
2. Confirms the grant and pension severance source and planning-only disclosure.
3. Selects a proposed grant continuity and pension severance withdrawal.
4. Types `100.5`, saves, and checks canonical API amount `100.50`.
5. Switches to alternative B, confirms it is independent, and returns to A.
6. Reloads the browser and checks persistence.
7. Uses the **existing client grant update API** to revise the *synthetic*
   source and confirms the previous selection is blocked as stale.
8. Uses the **existing draft API** to allocate 150.00 from the 200.00
   pension component in B; then the UI attempts a further 100.50 and
   verifies HTTP 422, no partial persistence and a Hebrew error.
9. Asserts absence of browser console errors, unexpected network failures,
   tax-exemption, net-payment and approval claims.

This test intentionally expects an unresolved historical grant/pension
component overlap to remain blocked. It never produces an authorized payout.
It does not change financial calculation services, tax logic or production data.

## Evidence and cleanup

Every run creates a separate report directory under:
`%TEMP%\RETIRE_V2_SUPERVISOR41\<run-id>`.

The report contains `summary.txt`, browser screenshots,
`api-responses.json`, `browser-errors.json`, Playwright JSON/console
reports, and backend/frontend stdout/stderr. If execution fails before a
browser screenshot, `failure.txt` and available logs remain; failures are
**not** reported as PASS.

The harness terminates only the Backend/Vite process objects it started,
then checks the unique Docker label before stopping its own container by
the exact returned container ID. No broad `docker prune`, `docker stop`
by service name, port-based process killing, or worktree creation occurs.
Original process environment variables are restored.

## Gate

Only a completed local run with exit code 0, Playwright PASS and captured
evidence may close Supervisor 41. A code review, a working unit test, or
a standalone PostgreSQL test is **not** equivalent to browser acceptance.
