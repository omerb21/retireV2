# RETIRE V2 — Stage 6 professional workflow integration (2026-10-28)

## Owner decision and scope
After the P1A–P1D service-layer acceptance evidence (308 tests reported passing by Work), this package adds **a staging-gated professional UI/API workflow**. It does NOT approve production exposure, Railway deployment, database migration, or real-world pension entitlement.

### The existing canonical owners remain unchanged
- Scenario decisions: `scenario_draft_service` / `ScenarioDraftPanel`.
- SC-05C election: `scenario_pension_election_store_service.replace_elections` with scenario-version CAS and its existing Pydantic schema.
- P1B professional factor: `append_authenticated_serializable_factor_admission` with actor from signed session and PostgreSQL SERIALIZABLE CAS.
- P1D gross estimate: `estimate_single_pension_decision` with the current DB-owned read-only snapshot and PTE once.
- There is NO second formula, second rules engine, auto coefficient lookup, indexed estimate, production conversion or client-provided admission authority.

## Closed operator sequence
1. Select a saved draft scenario and one pension decision.
2. Read the current versioned SC-05C election state.
3. Enter pension date, survivor terms, age difference, company and payout option; save elections with expected scenario version. This invalidates older factor admissions.
4. Request informational `latest_admission_revision` + `scenario_version` from PostgreSQL. The cursor is **NOT proof of a valid admission**.
5. Enter exact positive divisor, evidence category and reference. POST professional factor admission, using signed session actor and server-side serializable CAS.
6. Request the read-only gross estimate and display a monthly amount only for a complete N1.4 `RESULT_READY` envelope matching current scenario/decision, professional admission, nonempty provenance, amount and result digest. Otherwise display blockers only.
7. Editing an election or switching a scenario invalidates locally displayed estimate evidence. No automatic estimate execution.

## Activation safety — disabled by default
Both API routers are included in `app.main.create_app` **only if all hold**:
- `config.production is True` (the full authenticated middleware, CSRF and edge protections are active);
- `STAGE6_PREVIEW_ENABLED=1`;
- `RAILWAY_ENVIRONMENT_NAME=staging` (exact string).

Never set the preview flag in the production Railway environment. Even if accidentally set there, the environment-name gate prevents mount. Development-mode middleware bypasses session enforcement, so Stage 6 is intentionally **NOT** mounted in ordinary `APP_ENV=development` runs.

The frontend component is shown only if the **build-time** `VITE_STAGE6_PREVIEW_ENABLED=1`. API and UI flags must be enabled only in a dedicated controlled staging setup. They have not been enabled or deployed by this package.

### Auth and provenance
- All APIs run behind signed authenticated sessions.
- Election PUT also explicitly rechecks origin and CSRF for defense in depth.
- Factor POST accepts only expected version/revision, exact divisor and professional evidence fields. Never actor, factor source, five hashes or authorization flags.
- Revision GET is informational; its response contains `authority_state=NOT_EVALUATED`.
- Preview and receipts carry `no-store`.
- Stage 6 remains isolated from tax, eligibility, CPI/indexation, capital assets, implementation of pension withdrawals and the general assessor.

## Evidence/remaining gates
- **Code completed and locally verified:** backend routes, typed frontend clients, integrated draft UI, separate factor acknowledgment UI and fail-closed validation of the complete N1.4 estimate envelope, including client binding.
- **Backend evidence:** 233 focused Stage 6, P1A–P1D, PTE and governance tests passed; 45 security, draft and election regressions passed. Four dedicated PostgreSQL 16.2 tests passed for election persistence, factor-admission CAS/rollback, snapshot composition and READY/BLOCKED estimation.
- **Frontend evidence:** 17 focused Vitest tests passed and the TypeScript/Vite production build passed.
- **Not performed:** GitHub Actions, merge, deployment, live staging verification or production database changes.
- **Release gate remains BLOCKED:** local validation does not authorize production exposure. A separately authorized integration run in the authenticated staging topology and a separate release decision remain required.

Status: `STAGE6_WORKFLOW_READY_FOR_REVIEW` — **not** `PRODUCTION_READY`.
