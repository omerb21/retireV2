**Phase 1 Build Spec**

**1. Phase 1 Goal**

Build the first deterministic V2 slice of the retirement planning system: the complete V1 fixation workflow from source-data entry to immutable saved fixation result and audit history.

Phase 1 proves the core architectural rules:

- Engines are the only calculation layer.
- API does not calculate.
- UI does not calculate.
- Database stores source data, input snapshots, immutable outputs, audit rows, and metadata separately.
- Every fixation run is reproducible from its saved input snapshot.
- No V1 code or architecture is reused.

**2. Exact Included Scope**

Included:

- Client.
- Client Profile.
- Employment Records.
- Grants.
- Actual Capitalizations.
- Fixation Parameters.
- Fixation Engine.
- Fixation Result.
- Audit Rows.
- Calculation History.
- Backend API for the above.
- React custom UI for the above.
- PostgreSQL persistence.
- SQLAlchemy ORM.
- Alembic migrations.
- Pydantic validation.
- Pytest tests.
- FastAPI TestClient API tests.
- Golden fixation tests.
- Local-first build/run workflow.
- Auth-ready metadata only where needed, without authentication implementation.

**3. Exact Excluded Scope**

Excluded:

- Pension Engine.
- Tax Engine.
- Cashflow Engine.
- Scenario Builder.
- Scenario Comparison.
- PDF / Reports.
- LLM / Agent.
- External integrations.
- Automatic indexation.
- Authentication implementation.
- Admin screens.
- Business table management UI.
- Templates.
- Boilerplates.
- Any frontend calculation authority.
- Any API-layer calculation.
- Any DB access inside engines.
- Any mutation of historical calculation results.

**4. Strict Build Order**

1. Lock Phase 1 contracts.
2. Define validation behavior.
3. Build pure Fixation Engine.
4. Build Golden tests for engine.
5. Define database schema conceptually and then implement persistence.
6. Build persistence tests.
7. Build backend service/orchestration layer.
8. Build API groups.
9. Build API tests.
10. Build frontend screens.
11. Build UI smoke tests.
12. Run end-to-end acceptance against Golden Cases.
13. Release gate review.

No later step may begin until the prior step meets its acceptance criteria.

**5. Build Steps**

**Step 1: Lock Phase 1 Contracts**

Purpose:
- Freeze the exact input/output contracts used by engine, API, database snapshots, and UI.

Conceptual components:
- FixationInput contract.
- GrantInput contract.
- ActualCapitalizationInput contract.
- IDFInput contract.
- FixationResult contract.
- AuditRow contract.
- ValidationError contract.

Dependencies:
- Approved Domain Contracts.
- Approved Golden Fixation Cases.
- Approved Build Plan.

Acceptance criteria:
- Every required input is explicit.
- No input field depends on DB, UI, external API, or hidden state.
- Every output is deterministic.
- All Golden Cases can be expressed by the contracts.
- Validation errors have stable paths and codes.

Forbidden actions:
- No code.
- No folders.
- No framework-specific model decisions.
- No adding fallback fields.
- No adding fields just because they existed in V1.

---

**Step 2: Lock Validation Behavior**

Purpose:
- Define what blocks calculation before implementation begins.

Conceptual components:
- Required-field validation.
- Date validation.
- Numeric validation.
- Grant validation.
- Actual capitalization validation.
- IDF validation.
- Global fixation input validation.

Dependencies:
- Step 1 contracts.

Acceptance criteria:
- Missing required calculation input always blocks calculation.
- Invalid data never falls back.
- Validation errors map to contract fields.
- UI/API/engine all use the same validation meaning.
- Failed validation cannot produce saved success result.

Forbidden actions:
- No warning-only continuation for required inputs.
- No silent zero behavior for missing required data.
- No nominal fallback.
- No 2025/2028 fallback.
- No frontend-only validation as authority.

---

**Step 3: Build Pure Fixation Engine**

Purpose:
- Create the deterministic calculation engine for Phase 1 fixation.

Conceptual components:
- Engine input validator boundary.
- Initial entitlement calculation.
- Grant impact calculation.
- 15-year exclusion behavior.
- 32-year work ratio behavior.
- Future grant reserve impact.
- Actual capitalization impact.
- IDF impact.
- Total impact.
- Remaining exemption.
- Exempt pension output.
- Audit row generation.
- Validation error output.

Dependencies:
- Step 1 contracts.
- Step 2 validation behavior.

Acceptance criteria:
- Engine accepts only contract input.
- Engine returns only contract output.
- Engine has no DB access.
- Engine has no IO.
- Engine has no external API access.
- Engine has no UI dependency.
- Engine has no hidden state.
- Engine does not mutate input.
- Engine does not depend on current date except where explicitly supplied in input.

Forbidden actions:
- No copying V1 code.
- No using V1 folder structure.
- No fallback behavior.
- No logging as calculation output.
- No scenario logic.
- No pension/tax/cashflow logic.
- No database calls.

---

**Step 4: Build Golden Engine Tests**

Purpose:
- Lock exact deterministic behavior before persistence/API/UI exists.

Conceptual components:
- Golden Case 1: base case.
- Golden Case 2: single grant full impact.
- Golden Case 3: 15-year exclusion.
- Golden Case 4: partial 32-year ratio.
- Golden Case 5: multiple grants.
- Golden Case 6: future grant reserve only.
- Golden Case 7: actual capitalization impact.
- Golden Case 8: IDF impact.
- Golden Case 9: combined full scenario.
- Golden Case 10: zero remaining exemption.
- Golden Case 11: ratio boundaries.
- Validation failure tests.

Dependencies:
- Step 3 engine.

Acceptance criteria:
- Every Golden Case passes exactly.
- Expected numeric values match approved Golden Cases.
- Validation failures return stable error codes and paths.
- Tests do not require DB.
- Tests do not require API.
- Tests do not require external services.

Forbidden actions:
- No snapshotting approximate outputs.
- No tolerance that hides rounding mistakes unless explicitly approved.
- No external CPI/API dependency.
- No UI-based tests here.

---

**Step 5: Build V1 Persistence Model**

Purpose:
- Store only Phase 1 source data, input snapshots, immutable outputs, audit rows, validation errors, and metadata.

Conceptual components:
- Client persistence.
- Client profile persistence.
- Employment records persistence.
- Grants persistence.
- Actual capitalizations persistence.
- Fixation runs metadata.
- Fixation input snapshots.
- Fixation results.
- Fixation audit rows.
- Fixation validation errors.

Dependencies:
- Approved V1 Database Design Draft.
- Step 1 contracts.

Acceptance criteria:
- Source data is separate from engine outputs.
- Input snapshots are immutable.
- Results are immutable.
- Audit rows are immutable.
- Previous runs are never overwritten.
- Latest run can be identified without mutating old values.
- Database stores enough information to reproduce every run.

Forbidden actions:
- No pension/tax/cashflow/scenario tables.
- No report tables.
- No chat/LLM tables.
- No frontend-calculated fields as source of truth.
- No mutable single “current result” record that loses history.
- No DB triggers or persistence side effects that calculate business values.

---

**Step 6: Build Persistence Tests**

Purpose:
- Prove database separation and immutability.

Conceptual components:
- Source data persistence tests.
- Input snapshot persistence tests.
- Result persistence tests.
- Audit row persistence tests.
- History tests.
- Immutability tests.

Dependencies:
- Step 5 persistence model.

Acceptance criteria:
- Creating source data does not create calculation outputs.
- Saving a run creates metadata, input snapshot, output, and audit rows.
- Editing source data after a run does not change the run.
- Recalculation creates a new run.
- Old runs remain readable.
- Saved result equals engine output.

Forbidden actions:
- No calculations in tests except through engine.
- No manually patching database rows to satisfy assertions.
- No mutation of previous results.

---

**Step 7: Build Backend Service / Orchestration Layer**

Purpose:
- Coordinate data loading, contract assembly, engine execution, and persistence without containing formulas.

Conceptual components:
- Client source-data service.
- Fixation input assembly service.
- Fixation calculation orchestration.
- Fixation run persistence service.
- Fixation history retrieval service.

Dependencies:
- Step 3 engine.
- Step 5 persistence.
- Step 6 persistence tests.

Acceptance criteria:
- Services assemble explicit engine input.
- Services call engine.
- Services persist exact input snapshot and exact output.
- Services do not calculate business formulas.
- Services do not patch engine output.
- Services do not perform hidden fallback.
- Services do not mutate old runs.

Forbidden actions:
- No formula logic.
- No V1 service reuse.
- No scenario mutation.
- No LLM/tool logic.
- No external indexation.
- No deriving missing values from defaults.

---

**Step 8: Build API Groups**

Purpose:
- Expose Phase 1 workflow through FastAPI without calculation logic in routes.

Conceptual API groups:
- Clients.
- Client Profiles.
- Employment Records.
- Grants.
- Actual Capitalizations.
- Fixation Validation.
- Fixation Calculation.
- Fixation Save.
- Fixation Latest Result.
- Fixation History.
- Fixation Run Detail.

Dependencies:
- Step 7 services.
- Step 1 contracts.
- Step 2 validation behavior.

Acceptance criteria:
- API validates request shapes.
- API calls services.
- API returns contract-aligned responses.
- API does not calculate financial values.
- API does not write partial calculation results unless contract allows failed-run history.
- API error responses are stable and explicit.

Forbidden actions:
- No formulas in routes.
- No frontend-specific response hacks.
- No hidden fallback.
- No PDF/report endpoints.
- No LLM endpoints.
- No pension/tax/cashflow/scenario endpoints.

---

**Step 9: Build API Tests**

Purpose:
- Verify backend workflow from request to saved immutable run.

Conceptual components:
- Client API tests.
- Profile API tests.
- Employment API tests.
- Grants API tests.
- Actual Capitalization API tests.
- Fixation validate API tests.
- Fixation calculate API tests.
- Fixation save API tests.
- Fixation history API tests.
- API-level Golden Case tests.

Dependencies:
- Step 8 API groups.

Acceptance criteria:
- API can complete full Phase 1 flow.
- API calculation result equals engine Golden output.
- Saved result equals API calculation result.
- Reloaded result equals saved result.
- Invalid inputs return validation errors.
- Old runs remain immutable.

Forbidden actions:
- No UI involvement.
- No external services.
- No test-only calculation shortcuts.
- No accepting approximate behavior that violates Golden Cases.

---

**Step 10: Build Frontend Screens**

Purpose:
- Provide Phase 1 user workflow using API as the only calculation source.

Required screens:
- Client List.
- Create Client.
- Client Profile.
- Employment History.
- Grants.
- Actual Capitalizations.
- Fixation Parameters.
- Fixation Calculation Result.
- Fixation Audit / History.

Dependencies:
- Step 8 API.
- V1 Screen Flow Specification.

Acceptance criteria:
- User can create client.
- User can enter profile.
- User can enter employment records.
- User can enter grants with explicit indexed values.
- User can enter actual capitalizations.
- User can enter fixation parameters.
- User can run calculation.
- User can save result.
- User can view audit/history.
- UI displays API/engine outputs only.

Forbidden actions:
- No frontend financial calculations.
- No cap lookup.
- No grant impact calculation.
- No IDF impact calculation.
- No remaining exemption calculation.
- No hidden fallback values.
- No template use.
- No low-code/admin-template import.
- No LLM/chat UI.

---

**Step 11: Build UI Smoke Tests**

Purpose:
- Verify the user workflow works and UI does not become calculation authority.

Conceptual components:
- Create client smoke test.
- Enter profile smoke test.
- Enter grants smoke test.
- Enter actual capitalizations smoke test.
- Run fixation smoke test.
- Save result smoke test.
- View audit/history smoke test.
- Validation error display smoke test.

Dependencies:
- Step 10 frontend screens.
- Step 8 API.

Acceptance criteria:
- Core workflow completes.
- Validation errors are visible.
- Saved result reloads correctly.
- Displayed values match API response.
- UI does not use local calculation outputs.

Forbidden actions:
- No asserting against frontend-computed values.
- No mocking engine results in a way that hides API issues.
- No visual-only acceptance without data verification.

---

**Step 12: End-To-End Phase 1 Acceptance**

Purpose:
- Verify Phase 1 as one complete fixation system.

Conceptual components:
- Golden Cases through engine.
- Golden Cases through API.
- Selected Golden Cases through UI workflow.
- Immutability verification.
- Source-of-truth verification.
- Forbidden-pattern review.

Dependencies:
- Steps 1-11.

Acceptance criteria:
- All Golden tests pass.
- All API tests pass.
- UI smoke tests pass.
- No calculations exist in UI.
- No calculations exist in API routes.
- No DB access exists inside engine.
- Old runs are immutable.
- Every saved result is reproducible from snapshot.
- Excluded Phase 1 scope is absent.

Forbidden actions:
- No new features to satisfy acceptance.
- No weakening tests.
- No moving formulas into services/routes/UI.
- No importing or copying V1 implementation.

**6. Required Backend Layers**

Required conceptual backend layers:

1. API layer  
Receives requests, validates transport shape, calls services, returns responses.

2. Application service/orchestration layer  
Loads source data, assembles engine input, calls engine, persists snapshots/results/history.

3. Engine layer  
Pure deterministic Fixation Engine only.

4. Data access layer  
Persists source data, snapshots, results, audit rows, validation errors, metadata.

5. Validation/contracts layer  
Defines Pydantic request/response/domain contracts and validation errors.

Layer rules:
- API does not calculate.
- Services do not calculate formulas.
- Engine does not access DB.
- Data layer does not calculate.
- Validation does not perform fallback.

**7. Required Frontend Screens**

Required:

1. Client List
2. Create Client
3. Client Profile
4. Employment History
5. Grants
6. Actual Capitalizations
7. Fixation Parameters
8. Fixation Calculation Result
9. Fixation Audit / History

Screen rules:
- Screens collect and display data only.
- Screens never calculate business results.
- Screens never patch engine outputs.
- Screens never infer missing inputs.
- Screens never reuse V1 components.

**8. Required Database Tables**

Conceptual tables:

1. Clients.
2. Client Profiles.
3. Employment Records.
4. Grants.
5. Actual Capitalizations.
6. Fixation Runs.
7. Fixation Input Snapshots.
8. Fixation Results.
9. Fixation Audit Rows.
10. Fixation Validation Errors.

Optional only if auth-ready metadata requires it:
- Users placeholder/reference, without implementing authentication.

Database rules:
- Source data separate from snapshots.
- Snapshots separate from outputs.
- Outputs separate from audit rows.
- Runs immutable.
- Recalculation creates new run.
- No pension/tax/cashflow/scenario/report/LLM tables in Phase 1.

**9. Required API Groups**

Required API groups:

1. Clients
2. Client Profiles
3. Employment Records
4. Grants
5. Actual Capitalizations
6. Fixation Validate
7. Fixation Calculate
8. Fixation Save
9. Fixation Latest Result
10. Fixation History
11. Fixation Run Detail

API rules:
- No calculations in route handlers.
- No hidden defaults.
- No mutation of old runs.
- No external integrations.
- No excluded-scope endpoints.

**10. Required Tests**

Required test groups:

**Engine tests**
- All Golden Fixation Cases.
- Validation failures.
- Boundary cases.
- Determinism checks.

**Persistence tests**
- Source data save/read.
- Snapshot immutability.
- Result immutability.
- Audit row persistence.
- Recalculation creates new run.
- Source edit does not alter old run.

**Service tests**
- Input assembly.
- Engine call.
- Exact output persistence.
- No fallback behavior.
- Validation failure handling.

**API tests**
- CRUD for Phase 1 source data.
- Validate/calculate/save fixation.
- Latest result retrieval.
- History retrieval.
- Invalid input responses.
- API-level Golden Cases.

**Frontend smoke tests**
- Full workflow.
- Validation display.
- Result display.
- Audit/history display.
- Reload saved result.

**Forbidden-pattern checks**
- No UI calculation authority.
- No route formulas.
- No DB inside engine.
- No external API in engine.
- No V1 module reuse.

**11. Release Gate**

Phase 1 is complete only when:

- Included scope is fully built.
- Excluded scope is absent.
- All Golden Cases pass at engine level.
- All Golden Cases pass through API where applicable.
- Full user workflow works in UI.
- Saved results are immutable.
- Input snapshots reproduce outputs.
- Audit rows are saved and viewable.
- No calculations exist in UI.
- No calculations exist in API routes.
- No DB access exists inside engines.
- No fallback behavior exists.
- No V1 code, folder structure, routers, models, services, components, LLM logic, or scenario mutation logic has been reused.
- Open questions are documented and not silently implemented.

**12. Stop Conditions**

Development must halt if any of the following occurs:

- A required calculation behavior is unclear from approved spec.
- V1 behavior conflicts with approved spec.
- A desired field exists only in V1 and not in V2 contracts.
- A developer needs to add fallback behavior to proceed.
- A calculation appears necessary in UI.
- A calculation appears necessary in API route.
- Engine needs DB access.
- External API/indexation is needed.
- Authentication implementation becomes necessary.
- Pension/tax/cashflow/scenario/report scope is requested during Phase 1.
- Golden Case expected value is disputed.
- Database model cannot preserve immutable runs.
- Saved result cannot be reproduced from input snapshot.
- Any shortcut would weaken source-of-truth rules.

When a stop condition occurs:
- Do not implement around it.
- Record the open question.
- Return to decision lock before coding continues.