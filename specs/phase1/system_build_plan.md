**System Build Plan**

**1. V1 Scope**

Included in V1:

- Client creation and profile.
- Pension portfolio data entry only as source data.
- Employment history required for grants.
- Grant data entry.
- Explicit indexed grant values.
- Actual capitalization / actual commutation entry.
- IDF/security-forces fixation inputs.
- Deterministic Fixation Engine.
- Fixation calculation result.
- Fixation audit rows.
- Save and retrieve fixation calculation runs.
- Basic scenario input shell only if needed to package a final fixation-based plan.
- Final fixation summary screen.

Explicitly excluded from V1:

- Pension Engine.
- Tax Engine.
- Cashflow Engine.
- Full Scenario Builder.
- Scenario comparison.
- LLM/chat/agent features.
- PDF/report generation.
- External CPI/indexation API.
- Automatic indexation.
- Authentication beyond whatever minimal local access decision is locked separately.
- Admin settings screens.
- Business table editing UI.
- Pension projection.
- Retirement cashflow planning.
- Tax projection.
- Document/form generation.
- Any frontend calculation authority.

V1 goal: rebuild the deterministic fixation workflow correctly before rebuilding broader retirement planning.

**2. Build Phases In Strict Order**

**Phase 0: Decision Lock And Project Rules**

Goal: freeze V1 scope and implementation constraints before any coding.

Components built:
- None.

Dependencies:
- Approved blueprint.
- Approved Golden Fixation Cases.
- Approved V1 decisions.

Definition of done:
- V1 included/excluded list is accepted.
- Engine boundary is accepted.
- Data ownership rules are accepted.
- Golden cases are accepted.
- No open decision blocks Phase 1.

Must NOT be built:
- No code.
- No screens.
- No APIs.
- No database schema.

Move to next phase when:
- All V1 decisions are explicitly locked.

---

**Phase 1: Domain Contracts**

Goal: define deterministic input/output contracts for V1 fixation.

Components built:
- Fixation input contract.
- Fixation output contract.
- Grant input contract.
- Actual capitalization input contract.
- IDF input contract.
- Audit row contract.
- Validation error contract.

Dependencies:
- Phase 0.

Definition of done:
- Every required V1 input is named.
- Every V1 output is named.
- No field depends on DB, UI, LLM, external API, or hidden state.
- Contracts cover all Golden Fixation Cases.

Must NOT be built:
- No engine implementation.
- No database.
- No UI.
- No API.
- No folder decisions beyond what implementation later requires.

Move to next phase when:
- Contracts can express all Golden Cases without extra assumptions.

---

**Phase 2: Fixation Engine**

Goal: build the pure deterministic Fixation Engine.

Components built:
- Initial exempt capital calculation.
- Grant impact calculation.
- 15-year exclusion handling.
- 32-year work ratio handling.
- Future grant reserve impact.
- Actual capitalization impact.
- IDF impact.
- Total impact.
- Remaining exempt capital.
- Monthly exempt pension.
- Exemption percentages.
- Audit rows.
- Validation errors.

Dependencies:
- Phase 1 contracts.
- Golden Fixation Cases.

Definition of done:
- Engine has no DB access.
- Engine has no IO.
- Engine has no frontend dependency.
- Engine has no external API call.
- Engine has no LLM dependency.
- Engine has no hidden fallback.
- Engine passes all Golden Fixation Cases exactly.
- Missing required data returns explicit validation failure.

Must NOT be built:
- No persistence.
- No API routes.
- No UI.
- No scenario mutation.
- No pension/tax/cashflow logic.
- No indexation API.

Move to next phase when:
- All Golden Cases pass exactly.
- Engine output is stable and deterministic.

---

**Phase 3: Minimal V1 Database Model**

Goal: persist only source data and fixation calculation runs required for V1.

Components built:
- Client.
- Client profile.
- Employment record.
- Grant.
- Actual capitalization / actual commutation.
- Fixation input snapshot.
- Fixation result.
- Fixation audit row or audit payload.
- Calculation metadata.

Dependencies:
- Phase 1 contracts.
- Phase 2 engine output.

Definition of done:
- Source data is separate from calculated results.
- Actual capitalizations are separate from scenario commutations.
- Fixation result stores engine output, not frontend-computed values.
- Input snapshot is preserved.
- Calculation version/timestamp is saved.
- No lazy recalculation is required on read.

Must NOT be built:
- No scenario result mutation.
- No pension projection tables.
- No tax result tables.
- No cashflow result tables.
- No report artifacts.
- No LLM/chat persistence.
- No admin table editor.

Move to next phase when:
- Database can store and retrieve one full V1 fixation run without losing input/output separation.

---

**Phase 4: Minimal V1 API**

Goal: expose deterministic V1 operations without business logic in routes.

Components built:
- Client create/read/update.
- Employment create/read/update/delete.
- Grant create/read/update/delete.
- Actual capitalization create/read/update/delete.
- Fixation validate.
- Fixation calculate.
- Fixation save result.
- Fixation get latest result.
- Fixation get calculation history.

Dependencies:
- Phase 2 engine.
- Phase 3 database model.

Definition of done:
- API calls engine through service/orchestration layer.
- API does not contain formulas.
- API does not patch calculation outputs.
- API does not perform hidden fallback.
- API returns validation errors from engine/contracts.
- Saved result equals engine output.

Must NOT be built:
- No scenario builder API.
- No pension projection API.
- No tax API.
- No cashflow API.
- No report/PDF API.
- No LLM endpoints.
- No external indexation endpoint.

Move to next phase when:
- API can complete full V1 fixation flow using persisted source data and return exact engine output.

---

**Phase 5: Minimal V1 UI Screens**

Goal: build only screens required to enter data, run fixation, and review saved output.

Components built:
- Client List.
- Client Profile.
- Employment History.
- Grants.
- Actual Capitalizations.
- Fixation Calculation.
- Fixation Result / Audit History.

Dependencies:
- Phase 4 API.
- Phase 1 contracts.

Definition of done:
- UI sends source inputs to API.
- UI displays engine outputs only.
- UI does not calculate fixation fields.
- UI does not calculate remaining exempt capital.
- UI does not calculate IDF impact.
- UI does not calculate grant impact.
- UI displays validation errors clearly.
- UI can reload saved fixation result without recalculation.

Must NOT be built:
- No pension projection screen.
- No tax screen.
- No cashflow screen.
- No scenario comparison.
- No final PDF/report screen.
- No admin settings.
- No chatbot.
- No frontend-only calculation helpers for business results.

Move to next phase when:
- User can create a client, enter V1 data, run fixation, save result, reload result, and inspect audit rows.

---

**Phase 6: End-To-End V1 Verification**

Goal: verify the full V1 workflow against Golden Cases and source-of-truth rules.

Components built:
- No new business components.
- Verification harness/process only.

Dependencies:
- Phases 1-5.

Definition of done:
- Golden Cases pass at engine level.
- Golden Cases pass through API.
- UI displays the same values returned by API.
- Saved and reloaded results match original engine output.
- No forbidden pattern appears in V1 implementation.
- Missing data behavior is explicit and deterministic.

Must NOT be built:
- No new features.
- No report generation.
- No scenario features.
- No pension/tax/cashflow engines.

Move to next phase when:
- V1 fixation workflow is accepted as complete.

---

**Phase 7: V1 Release Hardening**

Goal: prepare V1 for use without expanding scope.

Components built:
- Error handling polish.
- Logging for calculation runs.
- Basic operational checks.
- Data backup/export if required by deployment decision.
- Access control only if already locked for V1.

Dependencies:
- Phase 6 acceptance.

Definition of done:
- No calculation behavior changes.
- No scope expansion.
- Release checklist complete.
- Known limitations documented.

Must NOT be built:
- No V2 modules.
- No new formulas.
- No scenario expansion.
- No reporting/PDF unless explicitly added to V1 scope before Phase 0 lock.

Move to next phase when:
- V1 is deployable and accepted.

**3. Dependency Graph**

```text
Decision Lock
  -> Domain Contracts
    -> Fixation Engine
      -> Minimal Database Model
        -> Minimal API
          -> Minimal UI
            -> End-To-End Verification
              -> Release Hardening
```

Module dependency graph:

```text
UI
  -> API
    -> Application Services / Orchestration
      -> Fixation Engine
      -> Database

Fixation Engine
  -> Domain Contracts only

Database
  -> Stores source data, input snapshots, engine outputs

API
  -> Must not depend on frontend calculations
  -> Must not contain formulas

UI
  -> Must not depend on local business formulas
```

Forbidden dependency graph:

```text
Fixation Engine -> Database       forbidden
Fixation Engine -> UI             forbidden
Fixation Engine -> LLM            forbidden
Fixation Engine -> External API   forbidden
UI -> Business Formulas           forbidden
API Router -> Business Formulas   forbidden
Report/PDF -> Business Formulas   forbidden
Scenario -> Mutate Fixation       forbidden
```

**4. Minimal Data Model Required For V1 Only**

Required entities:

- Client.
- Client Profile.
- Employment Record.
- Grant.
- Actual Capitalization / Actual Commutation.
- IDF Fixation Input, if not embedded in fixation input snapshot.
- Fixation Input Snapshot.
- Fixation Result.
- Fixation Audit Row or audit payload.
- Calculation Metadata.

Required separation:

- Source data separate from calculation result.
- Input snapshot separate from current editable source data.
- Actual capitalizations separate from scenario commutations.
- Audit data attached to calculation result.
- Saved result immutable except explicit recalculation creates a new run.

Not included in V1 data model:

- Scenario comparison.
- Pension projection result.
- Tax result.
- Cashflow result.
- Report artifact.
- Chat/LLM memory.
- Prompt history.
- Admin-managed business table UI.

**5. Minimal Screens Required For V1 Only**

Required:

1. Client List  
Create/open clients.

2. Client Profile  
Enter demographics and eligibility-related source data.

3. Employment History  
Enter work periods used by grants.

4. Grants  
Enter grant data and explicit indexed values.

5. Actual Capitalizations  
Enter actual exemption-consuming capitalizations/commutations.

6. Fixation Calculation  
Enter future grant reserve and IDF inputs, validate, run calculation.

7. Fixation Result / Audit History  
Show saved result, audit rows, and prior calculation runs.

Excluded:

- Pension projection.
- Tax projection.
- Cashflow.
- Scenario builder.
- Scenario comparison.
- Reports/PDF.
- Chat/LLM.
- Admin table editor.

**6. Minimal API Required For V1 Only**

Client:
- Create client.
- Get client.
- Update client.
- List clients.

Employment:
- Create employment record.
- List employment records.
- Update employment record.
- Delete employment record.

Grants:
- Create grant.
- List grants.
- Update grant.
- Delete grant.

Actual capitalizations:
- Create actual capitalization.
- List actual capitalizations.
- Update actual capitalization.
- Delete actual capitalization.

Fixation:
- Validate fixation input.
- Calculate fixation without saving.
- Save fixation calculation result.
- Get latest fixation result.
- Get fixation history.
- Get one fixation calculation run by id.

Not included:
- Pension scenario API.
- Tax API.
- Cashflow API.
- Report API.
- LLM API.
- External indexation API.

**7. What Must NOT Be Built In Each Phase**

Phase 0:
- Nothing technical.

Phase 1:
- No implementation.
- No database.
- No UI.
- No formulas beyond already locked business behavior.

Phase 2:
- No persistence.
- No APIs.
- No UI.
- No external services.

Phase 3:
- No new calculations.
- No scenario tables.
- No report tables.
- No pension/tax/cashflow tables.

Phase 4:
- No formulas in routes.
- No frontend-specific API behavior.
- No hidden fallback.
- No report/scenario APIs.

Phase 5:
- No frontend business calculations.
- No scenario UI.
- No pension/tax/cashflow UI.
- No PDF UI.
- No LLM UI.

Phase 6:
- No new features.
- No behavior changes except fixing deviations from locked behavior.

Phase 7:
- No scope expansion.
- No new business behavior.
- No V2 modules.

**8. Criteria For Moving Between Phases**

Move from Phase 0 to 1:
- V1 scope and decisions are locked.

Move from Phase 1 to 2:
- Contracts cover every Golden Case.

Move from Phase 2 to 3:
- Fixation Engine passes every Golden Case exactly.

Move from Phase 3 to 4:
- Database can persist source data, input snapshot, output, audit, and metadata separately.

Move from Phase 4 to 5:
- API can run, save, and retrieve fixation without changing engine output.

Move from Phase 5 to 6:
- UI completes the full V1 user workflow using only API-returned calculations.

Move from Phase 6 to 7:
- Engine, API, persistence, and UI all match Golden Cases and source-of-truth rules.

Move from Phase 7 to release:
- No forbidden patterns present.
- No unresolved V1 blocker.
- Known exclusions documented.
- V1 accepted as fixation-only rebuild.