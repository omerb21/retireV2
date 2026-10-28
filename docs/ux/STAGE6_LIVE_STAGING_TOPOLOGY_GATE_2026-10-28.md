# RETIRE V2 — Live staging prerequisite and independent gate (2026-10-28)

## Source of truth: read-only account inventory, no changes

Railway project **Retirement  App** (`1ba75e37-06dd-4ad1-a1fe-ebde8c8cf61a`) presently has exactly one environment, `production` (`78a0701f-3265-4a32-bc72-874e4b9b797e`).

Its live services are `retire` (`cca5a322-3226-4de8-be79-f92402872606`), `RETAPP` (`1c2783dc-d03c-4a48-b40e-451c9abf77fe`), and `Postgres-I-0m` (`abe193f0-7559-437e-b31a-ebd81a70dd6d`). Both application services point to **`omerb21/retire`, `main`**, not `omerb21/retireV2`.

A separate Railway project **Ben-Zvi Client Portal Staging** (`611adb45-b1ac-457b-ba2e-7ac05cff8205`) has a `staging` environment, but its services belong to `omerb21/backtest-pro` and `omerb21/ben-zvi`. **Do not reuse** this project/database for the retirement calculator.

## GitHub verification
- Final locally tested workflow commit (reported by Work): `3da267358caae23ddaaacf39aa6c88d56544cccf`.
- GitHub combined commit status returned no statuses; workflow-runs lookup returned no runs for this commit.
- At inventory time, the Stage 6 feature branch compared to `master` had **729 commits ahead and 0 behind, 200 changed files**. A whole-branch merge is not an acceptable Stage 6-only release gate without a full diff review.

## Required staging topology (not yet provisioned)
1. Use a newly isolated staging project or a dedicated environment in an explicitly approved project. Its services must not share the production PostgreSQL database, credentials, volume, domains or mutable state.
2. Stage a new deployment of `omerb21/retireV2` pinned to the reviewed commit (or separately reviewed fast-forward); never substitute the `omerb21/retire` production source.
3. Provision an **independent PostgreSQL** database and run Alembic migration compatibility / rollback rehearsal on synthetic data.
4. Apply the ordinary production-security middleware to staging. The implementation gates Stage 6 API mounting on `config.production == True`, `STAGE6_PREVIEW_ENABLED=1`, and `RAILWAY_ENVIRONMENT_NAME=staging`. The frontend requires build-time `VITE_STAGE6_PREVIEW_ENABLED=1`. Both flags are OFF by default.
5. Never point staging to real client data or attach the current production Postgres volume; use synthetic fixtures. Verify session issuance, edge-origin checks, CSRF and no-cache.
6. Test the entire operator flow: saved scenario -> versioned pension election -> authenticated professional factor CAS -> current admission check -> read-only snapshot -> PTE exactly once -> closed READY/BLOCKED result. Test invalidations and transaction rollback.
7. Turn the preview flag OFF after the isolated acceptance run; do not merge or deploy to production as part of this verification.

## Gate status and ownership
- `CODE_REVIEW=ACCEPTED_FOR_STAGING_VALIDATION`
- `WORK_LOCAL_TEST_EVIDENCE=299_PASS_0_FAIL_REPORTED`
- `GITHUB_CI_FOR_FINAL_HEAD=NO_RUNS_RECORDED`
- `RETIRE_V2_STAGING_TOPOLOGY=ABSENT`
- `STAGING_DEPLOYMENT=NOT_PERFORMED`
- `PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED`

**Actual blocker:** no independently configured retirement V2 staging environment or isolated database is presently available. Creating cloud services and executing a live staging deployment requires a separate explicit operational go-ahead because it may incur charges and mutate the Railway account. This document is not that approval.

No Railway or GitHub Actions mutations were performed during this inventory.
