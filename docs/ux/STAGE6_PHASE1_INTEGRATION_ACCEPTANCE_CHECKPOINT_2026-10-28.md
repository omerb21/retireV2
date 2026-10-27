# Stage 6 P1A–P1D — integrated acceptance checkpoint (2026-10-28)

## Scope and examined revision
- Branch: `feature/professional-workspace-ux-first-20261022`.
- Implementation checkpoint HEAD: `beb6906f0979bb8d80fee7f4a19e4d35b50b5996`.
- Normative contracts: `docs/ux/STAGE6_BLOCKED_VERDICT_CONTRACT_REPAIR_2026-10-26.md`, N1.1–N1.6.
- P1A/B/C/D are **backend implementation slices**, not an approved production feature.

## Evidence inventory
- Work's reported local acceptance: 308 passing tests, zero functional failures; PostgreSQL 16.2 temporary integration 4 passed; `compileall` and `git diff --check` passed.
- GitHub connector independently confirmed that the final P1D commit is present and modified ten paths, including the estimate service, snapshot owner, professional approval reader, PTE tests, and PostgreSQL tests.
- These execution counts are **reported by Work**, not independently rerun for this checkpoint.
- Branch-vs-master comparison on this date: 683 commits ahead, 0 behind, 186 changed files reported by GitHub compare (which may be subject to compare-file limits). Therefore **do not treat merging the whole branch as a Stage 6-only operation**.

## Authority chain inspected (source review, not dynamic verification)
1. `scenario_permission_preview_service.derive_pension_action_permission_admission` owns P1A rule permission and rejects a non-PostgreSQL, non-repeatable-read, or writable admission snapshot.
2. `scenario_pension_factor_admission_write_service` and migration `d6f1a9c3b704` implement append-only P1B, serializable writes, authenticated actor and revision CAS.
3. `scenario_pension_factor_admission_read_service` rederives current context and rejects stale factor approvals.
4. `pension_monthly_basis_service`, `pension_temporal_basis_service` and `planning_input_service` produce M1/M2/T1/T2/P1 under their original canonical ownership.
5. `scenario_snapshot_candidate_service.build_manifest_candidate_snapshot` owns the read-only database snapshot; its guarded extension supplies the Stage 6 P1D calculation only after P1A/B/C.
6. `scenario_stage6_single_pension_estimate_service` uses the existing `pension_target_date_execution_service.execute_from_planning_result`, with N1.4 result envelopes and no new persisted financial result.

## Integration gap — user-facing workflow
The backend service is not the same as a usable application feature.
- The scanned API registration (`backend/app/main.py`) includes `scenario_draft_router` and `scenario_permission_preview_router`, but **does not register a Stage 6 estimate route**.
- `backend/app/api/scenario_draft_routes.py` exposes draft CRUD and documentary `calculation-admission`, but **no Stage 6 professional factor approval / single-decision estimate endpoint**.
- UI entry, authentication-dependent factor entry/review and presentation of N1.4 output have **not been accepted or verified** under this package.
- This is a deliberate *deployment / UI integration gate*, not evidence that P1A–P1D calculation contracts failed.

## Release disposition
- `P1A_P1D_BACKEND_IMPLEMENTED=YES`
- `P1D_LOCAL_TEST_EVIDENCE=REPORTED_308_PASS`
- `INDEPENDENT_INTEGRATION_ACCEPTANCE=PENDING`
- `COST_CONTROLLED_CI=NOT_RUN`
- `PUBLIC_OR_USER_FACING_FEATURE=NOT_EXPOSED`
- `MERGE=NOT_AUTHORIZED`
- `DEPLOYMENT=NOT_AUTHORIZED`

## Follow-on acceptance order
1. Obtain one independent *read-only* security/functional review of the **final** Stage 6 commit, checking source authority, exact canonical fingerprints, N1.4 states, transaction boundaries, error handling and the existing PTE regression suite. Distinguish source inspection from test execution.
2. Run exactly one budgeted CI integration gate **only after a suitable workflow/runner and explicit run authorization exist**; do not assume a configured workflow. Preserve local PostgreSQL evidence and report actual logs.
3. Separately scope an API/UI delivery slice: authenticated professional coefficient admission, current approval read, and scenario gross-estimate presentation with explicit nonbinding/assumption labels, fail-closed output and no public exposure by default.
4. Consider merge or Railway deployment only after source-independent acceptance, CI results, migration compatibility, release diff review and explicit release approval.

This checkpoint records remaining operational evidence and product integration gaps. It does not alter financial logic or relax governance.
