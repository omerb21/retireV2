# RETIRE V2 | UNIFIED WORKSPACE PKG-01 | Acceptance and Next-Slice Proposal

Date: 2026-11-16
Authority: supervisor instruction 190
Scope: documentation and planning only, not a release authorization
Product repository: `omerb21/retireV2`
Approved product SHA: `c623577b76317009e2262c5b7fc23d1fe19c66b7`
Test branch: `test/pkg01-gha-acceptance-20261116`
Accepted test SHA: `dd6b79b6f85f167ce7b396a0b6843dc734cc4285`
PR #7: Draft, unchanged

## 1. PKG-01 acceptance gate record

| Gate | Decision | Exact evidence / limitation |
| --- | --- | --- |
| A - isolated functional acceptance | **PASS / CLOSED** | GitHub Actions run [43858567692](https://github.com/omerb21/retireV2/actions/runs/43858567692), 11 Playwright Chromium tests passed, zero failed / errors / skipped, against real localhost backend + disposable PostgreSQL 16 |
| B - live Railway Staging functional acceptance | **OPEN / NOT PASS** | Deployed app SHA and readiness health alone are not live authenticated browser acceptance. No live Staging write/persistence/identity validation was performed |
| Production release | **NOT AUTHORIZED** | Gate B remains required before release of the relevant version |

### Approved Gate A evidence

- Workflow run: https://github.com/omerb21/retireV2/actions/runs/43858567692
- GitHub Actions artifact: https://github.com/omerb21/retireV2/actions/runs/43858567692/artifacts/14222261903
- Artifact name: `retire-v2-pkg01-acceptance-43858567692`.
- CI accepted product baseline: `c623577b76317009e2262c5b7fc23d1fe19c66b7`; test-only SHA: `dd6b79b6f85f167ce7b396a0b6843dc734cc4285`.
- Test file: `frontend/e2e/pkg01-acceptance.spec.ts`.
- Workflow: `.github/workflows/retire-v2-pkg01-acceptance.yml`.
- Test result: **11/11 PASS**, Chromium, 1 worker, 0 retries. JUnit in artifact: `acceptance-evidence/pkg01-junit.xml`. Browser log: `acceptance-evidence/pkg01-playwright.log`.
- Browser screenshots in `frontend/test-results/`: `01-client-a.png`, `03-missing-region.png`, `04-missing-saved.png`, `06-assumptions-region.png`, `07-assumption-saved.png`, `09-after-reload.png`, `10-isolated-client-b.png`.
- PostgreSQL and isolation proof: `acceptance-evidence/postgresql-version.txt`, `acceptance-evidence/isolation-guard.txt`, `acceptance-evidence/local-docker.log`; database `retirement_v2_synthetic`, PostgreSQL 16 with tmpfs and no published DB port. Backend and Vite are localhost-only. GitHub Actions cleanup removed temporary containers and volumes.
- Functional coverage: create synthetic client; step 3 navigation; missing-information display/create; save/reload and backend GET; planner-assumption display/create; inter-step persistence; second-client UI and API isolation; cross-client API read and write probes return 404 without changing owner records.
- Limitation: client-scoped record ownership was tested, not privilege separation between two distinct authenticated actors. The tests do not replace live Staging acceptance.

### Gate B reference only, not acceptance

Railway Staging `retire-v2-app` deployment `07a9b7aa-902e-4978-9465-9538589dbff0`, commit `c623577b76317009e2262c5b7fc23d1fe19c66b7`, returned SUCCESS and HTTP 200 at `/healthz/ready`. Functional UI and authenticated live persistence were **not** approved.

**Closure:** Supervisor instruction 190 closes Gate A with the above immutable run reference. Keep Gate B OPEN. Do not repeat PKG-01 acceptance without a product change or new finding. No Merge, Deploy or PR state change.

## 2. Next proposed slice, subject to supervisor approval

### UNIFIED WORKSPACE PKG-02 - supplementary planning-input editor integration

**Status: PROPOSED ONLY / NOT AUTHORIZED FOR IMPLEMENTATION.**

Grounding in existing project plan:
- `docs/ux/PROFESSIONAL_WORKSPACE_INTEGRATION.md`: subsequent slices integrate end-to-end supplementary facts inside the ordinary workspace, preserving source-of-truth APIs.
- `docs/ux/SUPERVISOR130_UI_WRITE_OWNERSHIP.md`: controlled exception **EX-S02** retains dedicated writers for actual capitalizations, capital assets, recurring income and recurring expenses until embedded editors demonstrate full parity.
- At the accepted product SHA, `frontend/src/pages/RetirementWorkspaceScreen.tsx`, step 3 shows these sections and sends users to the specialized `/actual-capitalizations` or `/planning-input` editor instead of providing an embedded ordinary-workflow editor.

**Proposal:** embed the four EX-S02 factual editors inside step 3, using existing accepted client-scoped APIs and canonical records. Preserve a visible route to the legacy editors; do not remove, hide or disable them in this package. No new database entity, calculated output or pension/capital conversion.

**Proposed scope:**
1. Actual capitalizations: display/edit existing recorded facts and their provenance/status using existing contracts.
2. Capital assets: embedded create/edit only for fields and validations already exposed by accepted API.
3. Recurring income and recurring expenses: embedded create/edit using the accepted APIs and units, with explicit sources and no inferred monetary amounts.
4. Existing unsaved-change protection, loading/error/empty states, and client-switch isolation in the unified workspace.
5. Do not create any second source of truth or duplicate backend write mechanism.

**Dependencies before implementation:**
- Supervisor approval of exact package scope and file allowlist.
- Read-only parity matrix for the four specialist writers and current client-scoped API contracts, covering required fields, permissions, validation, provenance, lifecycle, and edit/version semantics.
- If parity requires any backend/schema change or an authority outside existing contracts, stop and seek separate approval.
- Preserve completed PKG-01 Gate A as accepted baseline and leave Gate B open.
- Keep the legacy tools available for operations not yet covered by the embedded editors.

**Suggested acceptance criteria, approval pending:**
1. Four embedded sections display only the selected client's real API data, including empty/error/loading states.
2. All approved create/update interactions persist through real backend and PostgreSQL, then survive full reload, step switch, and client switch.
3. Values, units, date semantics, nullable fields, provenance and validation are consistent with the established specialist editors and backend.
4. A failed write, 409/version conflict where applicable, or invalid input cannot display a false save success or discard an unsaved draft.
5. On client A -> B -> A, no stale fields, in-flight results, drafts, or source data leak between clients; direct cross-client record IDs are rejected by the server.
6. Legacy specialist writers remain accessible and function unchanged; no tax, scenario, reporting, PDF, source import, calculation or canonical-conversion logic is altered.
7. Targeted frontend/API tests and a real-browser PostgreSQL 16 isolated journey are PASS with JUnit, screenshots and log artifacts. Live Staging gate remains separate.

**Explicit exclusions:** no legacy-screen removal, no schema/migration, no new calculations, tax/exemption/161d changes, no automated recommendation, no imports, no reports, no Production/Deploy, no Merge.

**Next decision:** supervisor to approve/modify/reject the PKG-02 scope and exact allowed file set before any application implementation.
