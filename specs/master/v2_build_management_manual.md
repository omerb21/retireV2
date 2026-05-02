**V2 Build Management Manual**

**1. Build Governance Rules**

V2 is a from-scratch rebuild. The existing V1 system is read-only reference only.

Non-negotiable rules:

- Build only from approved V2 specs.
- Do not copy V1 code, folders, models, routers, services, components, tests, LLM tools, or scenario logic.
- All calculations happen only inside calculation engines.
- Phase 1 includes only the Fixation workflow.
- No calculations in API routes.
- No calculations in UI.
- No DB access inside engines.
- No external API calls inside engines.
- No fallback behavior.
- No hidden state.
- No mutation of past calculation results.
- Every calculation run must be immutable.
- Every saved output must be reproducible from its saved input snapshot.
- If a required behavior is not specified, stop and raise an open question.
- If V1 conflicts with approved specs, approved specs win.
- If V1 contains extra behavior not in approved specs, do not implement it.

**2. Artifact Hierarchy**

If artifacts conflict, this hierarchy decides what wins:

1. Current explicit user instruction.
2. V2 Build Management Manual.
3. Phase 1 Build Spec.
4. Project Initialization Spec.
5. Domain Contracts.
6. Golden Fixation Cases.
7. Database Design Draft.
8. Screen Flow Spec.
9. Tech Stack Lock / Decision Map.
10. V2 Full System Master Spec / Rebuild Blueprint.
11. V1 discovery and extraction findings.

Conflict rules:

- Domain Contracts win over old V1 field shapes.
- Golden Cases win over any implementation expectation.
- Phase 1 Build Spec wins over broader V2 blueprint for Phase 1 scope.
- Database Design Draft wins for V1 persistence scope.
- Screen Flow Spec wins for V1 UI workflow.
- Tech Stack Lock wins over general technology preference.
- V1 evidence is reference only, never authority.

**3. Full Phase Sequence**

1. Project Initialization
2. Contract Implementation Preparation
3. Domain Contract Implementation
4. Fixation Engine Implementation
5. Golden Engine Tests
6. Database Schema Implementation
7. Persistence Tests
8. Service / Orchestration Implementation
9. API Implementation
10. API Tests
11. Frontend Screens
12. UI Smoke Tests
13. End-to-End Verification
14. Release Hardening
15. Phase 1 Release Gate

No phase may start before the previous phase passes its acceptance gate unless explicitly approved.

**4. Phase Specifications**

**Phase 1: Project Initialization**

Goal:
- Initialize the V2 project shell without business behavior.

Inputs required:
- Project Initialization Spec.
- Tech Stack Lock.
- Phase 1 Build Spec.

Implementation scope:
- FastAPI backend shell.
- React frontend shell.
- Local-first environment setup.
- PostgreSQL connection configuration.
- Alembic initialization.
- Pytest and FastAPI TestClient setup.
- Health/status endpoint only.
- Placeholder frontend routes only.

Forbidden scope:
- No engine logic.
- No formulas.
- No business API.
- No business DB tables.
- No real UI forms.
- No auth implementation.
- No external integrations.
- No V1 imports or copied code.

Required outputs:
- Backend shell runnable.
- Frontend shell runnable.
- Health/status endpoint.
- Initial test setup.

Required tests:
- Backend app imports.
- Health/status endpoint responds.
- Optional frontend shell render test.

Report format:
- What shell components were created.
- Tests run and result.
- Confirmation that no business logic exists.
- Confirmation that no V1 code was copied.
- Open questions.

Acceptance gate:
- Backend and frontend shells run locally.
- Health test passes.
- No business behavior exists.

Stop conditions:
- Need to add business schema.
- Need to add engine/domain logic.
- Need to copy V1.
- Need external integration.
- Locked stack cannot be initialized as specified.

---

**Phase 2: Contract Implementation Preparation**

Goal:
- Prepare exact implementation-ready interpretation of approved contracts.

Inputs required:
- Domain Contracts.
- Golden Fixation Cases.
- Phase 1 Build Spec.

Implementation scope:
- Contract interpretation.
- Validation behavior mapping.
- Error code/path conventions.
- Engine/API/service boundary expectations.

Forbidden scope:
- No formulas.
- No engine logic.
- No persistence.
- No API business routes.
- No UI forms.

Required outputs:
- Contract implementation checklist.
- Validation checklist.
- Open ambiguity list, if any.

Required tests:
- None required yet unless implementation begins.

Report format:
- Contracts reviewed.
- Ambiguities found.
- Confirmation all Golden Cases are representable.

Acceptance gate:
- No contract ambiguity remains.

Stop conditions:
- Any required field is unclear.
- Any Golden Case cannot be represented.
- Any V1-only field appears necessary.

---

**Phase 3: Domain Contract Implementation**

Goal:
- Implement the approved Phase 1 contracts without calculations.

Inputs required:
- Domain Contracts.
- Phase 2 preparation result.

Implementation scope:
- FixationInput.
- GrantInput.
- ActualCapitalizationInput.
- IDFInput.
- FixationResult.
- AuditRow.
- ValidationError.
- Required validation shape.

Forbidden scope:
- No formulas.
- No engine behavior.
- No DB writes.
- No API business logic.
- No UI logic.

Required outputs:
- Contract definitions.
- Contract validation behavior.

Required tests:
- Required field validation.
- Invalid date validation.
- Invalid numeric validation.
- Grant validation.
- Actual capitalization validation.
- IDF validation.
- ValidationError shape.

Report format:
- Contracts implemented.
- Tests added/run.
- Deviations from spec, if any.
- Open questions.

Acceptance gate:
- Contracts match Domain Contracts exactly.
- Validation tests pass.

Stop conditions:
- Contract requires modification.
- Validation behavior is unclear.
- Need fallback/default to proceed.

---

**Phase 4: Fixation Engine Implementation**

Goal:
- Build the pure deterministic Fixation Engine.

Inputs required:
- Domain Contracts.
- Golden Fixation Cases.
- Phase 1 Build Spec.
- V1 discovery only if clarification is needed.

Implementation scope:
- Fixation Engine only.
- Deterministic validation handling.
- Deterministic result output.
- Audit row production.

Forbidden scope:
- No DB access.
- No API logic.
- No UI logic.
- No external API.
- No LLM.
- No scenario logic.
- No pension/tax/cashflow logic.
- No fallback behavior.
- No copied V1 code.

Required outputs:
- Pure engine.
- Engine-level validation behavior.
- Engine audit output.

Required tests:
- Engine unit tests.
- Validation failure tests.
- Determinism tests.

Report format:
- Engine behaviors implemented.
- Tests run.
- Confirmation no DB/API/UI dependency.
- Confirmation no V1 code copied.

Acceptance gate:
- Engine is pure and deterministic.
- No forbidden dependency exists.

Stop conditions:
- Formula unclear.
- Golden expected value disputed.
- Need current date, DB, API, UI, or fallback.
- V1 behavior not covered by spec appears necessary.

---

**Phase 5: Golden Engine Tests**

Goal:
- Lock exact numerical behavior.

Inputs required:
- Golden Fixation Cases.
- Fixation Engine.

Implementation scope:
- Engine-level Golden tests only.

Forbidden scope:
- No API tests.
- No DB tests.
- No UI tests.
- No external dependencies.
- No tolerance changes unless approved.

Required outputs:
- Golden test suite for all approved cases.

Required tests:
- Base case.
- Single grant.
- 15-year exclusion.
- Partial 32-year ratio.
- Multiple grants.
- Future grant reserve.
- Actual capitalization.
- IDF.
- Combined scenario.
- Zero remaining exemption.
- Ratio boundaries.

Report format:
- Golden pass/fail matrix.
- Numeric mismatches, if any.
- Decision needed, if any.

Acceptance gate:
- All Golden tests pass exactly.

Stop conditions:
- Any Golden mismatch.
- Need to weaken expected values.
- Need undocumented behavior.

---

**Phase 6: Database Schema Implementation**

Goal:
- Implement minimal relational persistence for V1 fixation.

Inputs required:
- Database Design Draft.
- Domain Contracts.
- Phase 1 Build Spec.

Implementation scope:
- Clients.
- Client profiles.
- Employment records.
- Grants.
- Actual capitalizations.
- Fixation runs.
- Fixation input snapshots.
- Fixation results.
- Fixation audit rows.
- Fixation validation errors.

Forbidden scope:
- No pension tables.
- No tax tables.
- No cashflow tables.
- No scenario tables.
- No report/PDF tables.
- No LLM/chat tables.
- No auth schema unless separately locked.
- No DB-side calculations.
- No mutable single-result shortcut.

Required outputs:
- V1 schema implementation.
- Migration for V1 schema.
- Schema integrity checks.

Required tests:
- Migration applies.
- Basic persistence works.
- Relationships work.
- Required constraints work.

Report format:
- Tables added.
- Migration status.
- Tests run.
- Confirmation excluded tables were not added.

Acceptance gate:
- Schema supports source/snapshot/output/audit separation.
- Schema supports immutable runs.

Stop conditions:
- Need table outside V1 scope.
- Immutability cannot be represented.
- Source/result separation becomes ambiguous.

---

**Phase 7: Persistence Tests**

Goal:
- Prove database behavior follows immutability and source-of-truth rules.

Inputs required:
- Database schema.
- Domain Contracts.
- Database Design Draft.

Implementation scope:
- Persistence tests only.

Forbidden scope:
- No API/UI.
- No formulas in persistence.
- No extra schema.

Required outputs:
- Persistence test suite.

Required tests:
- Source data save/read.
- Input snapshot save/read.
- Engine output save/read.
- Audit row save/read.
- Validation error save/read if failed runs are stored.
- Recalculation creates a new run.
- Old run does not mutate.
- Source edits do not alter old runs.

Report format:
- Tests added.
- Tests run.
- Immutability confirmation.
- Any persistence issue.

Acceptance gate:
- Persistence tests pass.

Stop conditions:
- Saved result can be mutated unintentionally.
- Old run changes after source edit.
- Input snapshot cannot reproduce output.

---

**Phase 8: Service / Orchestration Implementation**

Goal:
- Coordinate source data, engine execution, and persistence without calculations.

Inputs required:
- Engine.
- Database schema.
- Domain Contracts.
- Phase 1 Build Spec.

Implementation scope:
- Source data services.
- Fixation input assembly.
- Engine invocation.
- Save run.
- Retrieve latest result.
- Retrieve history.
- Retrieve run detail.

Forbidden scope:
- No formulas.
- No fallback behavior.
- No patching engine output.
- No V1 service reuse.
- No scenario mutation.
- No LLM/tool behavior.

Required outputs:
- Service/orchestration layer.
- Service tests.

Required tests:
- Input assembly.
- Engine called exactly for calculation.
- Exact engine output persisted.
- Validation failure handling.
- History retrieval.
- Old runs immutable.

Report format:
- Services implemented.
- Tests run.
- Confirmation services contain no formulas.
- Open questions.

Acceptance gate:
- Services coordinate workflow without owning calculations.

Stop conditions:
- Service needs to invent missing values.
- Service needs formula logic.
- Service needs fallback.

---

**Phase 9: API Implementation**

Goal:
- Expose Phase 1 workflow through FastAPI.

Inputs required:
- Services.
- Domain Contracts.
- Screen Flow Spec.
- Phase 1 Build Spec.

Implementation scope:
- Clients API.
- Client Profiles API.
- Employment Records API.
- Grants API.
- Actual Capitalizations API.
- Fixation Validate API.
- Fixation Calculate API.
- Fixation Save API.
- Latest Result API.
- History API.
- Run Detail API.

Forbidden scope:
- No formulas in routes.
- No excluded APIs.
- No LLM endpoints.
- No report/PDF endpoints.
- No pension/tax/cashflow/scenario endpoints.
- No auth implementation.
- No frontend-specific hacks.

Required outputs:
- Phase 1 API endpoints.
- Stable request/response/error behavior.

Required tests:
- API group tests.
- Invalid input tests.
- Calculate/save/reload tests.
- History tests.
- API-level Golden tests.

Report format:
- API groups implemented.
- Tests run.
- Contract mismatches.
- Confirmation no formulas in API.

Acceptance gate:
- Full backend workflow works through API.

Stop conditions:
- API needs calculation logic.
- API needs field not in Domain Contracts.
- API needs fallback/default.

---

**Phase 10: API Tests**

Goal:
- Verify backend behavior through HTTP boundary.

Inputs required:
- API implementation.
- Golden Cases.
- Domain Contracts.

Implementation scope:
- FastAPI TestClient tests.

Forbidden scope:
- No UI.
- No external integrations.
- No mocked engine that hides behavior.

Required outputs:
- API test suite.

Required tests:
- CRUD source data.
- Validate fixation.
- Calculate fixation.
- Save fixation.
- Latest result.
- History.
- Run detail.
- API Golden Cases.
- Error cases.

Report format:
- API tests added.
- Test pass/fail.
- Failures with endpoint and expected/actual.

Acceptance gate:
- API test suite passes.

Stop conditions:
- API output differs from engine.
- Saved result differs from API result.
- Old run mutation detected.

---

**Phase 11: Frontend Screens**

Goal:
- Build Phase 1 UI workflow without frontend calculations.

Inputs required:
- Screen Flow Spec.
- API contracts.
- Phase 1 Build Spec.

Implementation scope:
- Client List.
- Create Client.
- Client Profile.
- Employment History.
- Grants.
- Actual Capitalizations.
- Fixation Parameters.
- Fixation Result.
- Fixation Audit / History.

Forbidden scope:
- No frontend business calculations.
- No local cap tables.
- No grant impact utilities.
- No IDF utilities.
- No scenario/pension/tax/cashflow/report/chat UI.
- No templates or boilerplates.

Required outputs:
- Working UI workflow.
- API-connected screens.

Required tests:
- UI smoke tests.
- API value display checks.
- Validation display checks.

Report format:
- Screens implemented.
- API calls used.
- Tests run.
- Confirmation UI does not calculate.

Acceptance gate:
- User can complete full V1 fixation workflow.

Stop conditions:
- UI needs to calculate business field.
- API missing required endpoint.
- Screen requires behavior outside spec.

---

**Phase 12: UI Smoke Tests**

Goal:
- Verify core user flow and UI source-of-truth behavior.

Inputs required:
- Frontend screens.
- API implementation.

Implementation scope:
- Smoke tests only.

Forbidden scope:
- No new features.
- No calculation helpers.
- No business assertions from frontend-computed values.

Required outputs:
- UI smoke test suite.

Required tests:
- Create client.
- Enter profile.
- Enter employment.
- Enter grants.
- Enter actual capitalizations.
- Enter fixation parameters.
- Run calculation.
- Save result.
- View audit/history.
- Display validation errors.

Report format:
- Smoke tests added/run.
- Screens covered.
- Failures and suspected layer.

Acceptance gate:
- Core UI workflow passes.

Stop conditions:
- UI displays value not returned by API.
- UI calculates business field.
- Saved result mismatch.

---

**Phase 13: End-To-End Verification**

Goal:
- Verify complete Phase 1 system against all specs.

Inputs required:
- All previous phases.

Implementation scope:
- Verification only.

Forbidden scope:
- No new features.
- No spec changes without formal update.
- No weakening tests.

Required outputs:
- E2E verification report.
- Forbidden-pattern review.
- Open question list.

Required tests:
- Full test suite.
- Engine Golden tests.
- API Golden tests.
- Persistence tests.
- UI smoke tests.

Report format:
- Overall status.
- Test summary.
- Forbidden-pattern checklist.
- Release blockers.

Acceptance gate:
- All tests pass.
- No forbidden patterns found.
- No unresolved Phase 1 blockers.

Stop conditions:
- Any test failure.
- Any forbidden pattern.
- Any unreproducible saved result.

---

**Phase 14: Release Hardening**

Goal:
- Prepare Phase 1 for local-first release without expanding scope.

Inputs required:
- Successful End-to-End Verification.

Implementation scope:
- Error handling polish.
- Logging/observability for calculation runs.
- Local setup documentation.
- Known limitation documentation.
- Final regression run.

Forbidden scope:
- No new business features.
- No formula changes.
- No PDF/reporting.
- No auth implementation unless separately locked.
- No scenario/pension/tax/cashflow work.

Required outputs:
- Release notes.
- Known exclusions.
- Local run instructions.
- Final test report.

Required tests:
- Full regression suite.

Report format:
- Hardening changes.
- Tests run.
- Scope confirmation.
- Remaining known limitations.

Acceptance gate:
- Ready for Phase 1 release review.

Stop conditions:
- Hardening requires business behavior change.
- New blocker discovered.

---

**Phase 15: Phase 1 Release Gate**

Goal:
- Decide whether Phase 1 is complete.

Inputs required:
- Final test report.
- E2E verification report.
- Release notes.
- Open questions list.

Implementation scope:
- None.

Forbidden scope:
- No implementation during gate.

Required outputs:
- Release approval or rejection.
- Blocker list if rejected.

Required tests:
- Full suite must already pass.

Report format:
- Release readiness matrix.
- Pass/fail decision.
- Blockers.
- Deferred non-Phase-1 items.

Acceptance gate:
- All release gate criteria in section 10 pass.

Stop conditions:
- Any unresolved Phase 1 blocker.

**5. Standard Report Format After Every Task**

Every coding task must return this format:

```text
Task Summary
- What was implemented:
- What was intentionally not implemented:

Phase Alignment
- Current phase:
- Approved artifact followed:
- Scope boundaries respected: yes/no

Files / Areas Changed
- ...

Spec Compliance
- No V1 code copied: yes/no
- No excluded Phase 1 scope added: yes/no
- No calculations outside engines: yes/no
- No fallback behavior added: yes/no
- No past-result mutation added: yes/no

Tests
- Tests added/updated:
- Tests run:
- Result:
- Failures, if any:

Behavior Notes
- Business behavior changed: yes/no
- If yes, approved by which artifact:

Open Questions
- ...

Next Step
- ...
```

**6. Standard Correction Workflow When Tests Fail**

1. Stop feature work.
2. Identify failing layer:
   - Contract.
   - Engine.
   - Persistence.
   - Service.
   - API.
   - UI.
   - E2E.
3. Compare expected behavior to highest-ranking relevant artifact.
4. If implementation is wrong, fix implementation.
5. If test is wrong, update test only if the spec proves it.
6. If spec is unclear, stop and raise open question.
7. Re-run affected tests.
8. Re-run broader regression group.
9. Report root cause, fix, and remaining risk.

Forbidden during correction:

- Do not weaken Golden values.
- Do not add fallback.
- Do not patch API/UI to hide engine failure.
- Do not mutate saved data to make tests pass.
- Do not copy V1 behavior to resolve ambiguity.
- Do not skip failing tests.
- Do not add tolerance unless explicitly approved.

**7. Rules For Using V1 As Reference-Only**

Allowed:

- Read V1 to understand prior behavior.
- Read V1 to understand approved formulas.
- Read V1 to identify edge cases.
- Read V1 to identify known mistakes to avoid.
- Use V1 discovery reports as evidence.

Forbidden:

- Copy V1 code.
- Copy V1 folder structure.
- Copy V1 models.
- Copy V1 routers.
- Copy V1 services.
- Copy V1 frontend components.
- Reuse V1 frontend calculations.
- Reuse V1 LLM/tool logic.
- Reuse V1 scenario mutation logic.
- Reuse V1 fallback behavior.
- Treat V1 as authority over approved specs.

If V1 contains behavior not defined in V2 specs:
- Record as open question.
- Do not implement.

If V1 conflicts with V2 specs:
- Follow V2 specs.
- Mention conflict in task report if relevant.

**8. Rules For Preventing Scope Creep**

Scope control rules:

- Every task must identify its phase.
- Every implementation must map to an approved included scope item.
- Excluded modules must not be stubbed unless required by Project Initialization Spec.
- No “while we’re here” additions.
- No new fields outside contracts.
- No new tables outside Database Design Draft.
- No new screens outside Screen Flow Spec.
- No new APIs outside Phase 1 API groups.
- No external integration.
- No auth implementation.
- No reports/PDF.
- No pension/tax/cashflow/scenario work.
- No LLM/chat features.

Scope creep indicators:

- New field not in Domain Contracts.
- New table not in Database Design Draft.
- New screen not in Screen Flow Spec.
- Calculation outside engine.
- New external dependency.
- New report/export feature.
- New scenario behavior.
- New fallback/default.

If scope creep appears:
- Stop.
- Report the issue.
- Ask for spec update decision.

**9. Rules For Updating Specs When Open Questions Appear**

Open question workflow:

1. Stop implementation at the ambiguity.
2. Document:
   - Question.
   - Affected phase.
   - Affected artifact.
   - Evidence from approved spec.
   - Evidence from V1 if relevant.
   - Options.
   - Risk if unresolved.
3. Do not choose silently.
4. Wait for decision.
5. Update the highest necessary artifact.
6. Update dependent artifacts if needed.
7. Resume only after decision is locked.

Which artifact to update:

- Business behavior change: Domain Contracts and Golden Cases.
- Persistence change: Database Design Draft.
- Workflow change: Screen Flow Spec.
- Phase scope change: Phase 1 Build Spec.
- Tech change: Tech Stack Lock.
- Governance change: Build Management Manual.
- Initialization change: Project Initialization Spec.

**10. Final Release Gate For Phase 1**

Phase 1 can release only if all gates pass.

**Scope Gate**
- Included Phase 1 scope complete.
- Excluded scope absent.
- No pension, tax, cashflow, scenario, report, LLM, or auth implementation.

**Architecture Gate**
- Calculations only inside Fixation Engine.
- API routes contain no formulas.
- UI contains no formulas.
- Engine has no DB access.
- Engine has no IO or external API access.
- Past runs immutable.
- Saved outputs reproducible from snapshots.

**Business Gate**
- Domain Contracts implemented.
- Golden Cases pass exactly.
- Validation behavior matches spec.
- No fallback behavior exists.

**Database Gate**
- Source data separate from snapshots.
- Snapshots separate from outputs.
- Outputs separate from audit rows.
- Calculation history works.
- Old runs remain readable and unchanged.

**API Gate**
- All required API groups implemented.
- API tests pass.
- API output matches engine output.
- Saved result matches engine output.

**UI Gate**
- Required screens implemented.
- Full workflow works.
- UI displays API outputs only.
- Validation errors visible.
- Audit/history visible.

**Testing Gate**
- Contract tests pass.
- Engine tests pass.
- Golden tests pass.
- Persistence tests pass.
- Service tests pass.
- API tests pass.
- UI smoke tests pass.
- Full regression suite passes.

**V1 Separation Gate**
- No V1 code copied.
- No V1 structure copied.
- No V1 fallback reused.
- No V1 frontend calculations reused.
- No V1 LLM/tool/scenario mutation logic reused.

**Documentation Gate**
- Release notes complete.
- Known exclusions documented.
- Open questions list empty or explicitly deferred outside Phase 1.
- Local-first operation documented.

If any gate fails:
- Phase 1 is not releasable.
- Return to correction workflow.
- Do not expand scope to compensate.