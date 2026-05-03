# Consolidated Phase 2 Artifact Package

## 1. Package Control

* Package purpose: create one clean, complete, persistable Phase 2 documentation package for Supervisor review, so Phase 2 decisions do not rely on conversation memory.
* Current project state: Phase 1 locked, repository clean, Phase 2 deliverables approved, Phase 3 drafting paused until this package is reviewed.
* Phase 1 status: locked.
* Phase 2 status: complete, pending consolidation approval.
* Phase 3 status: not active; drafting paused until this package is approved.
* Permission to code: no.
* Coding Model status: blocked.

This package follows the correction that Phase 3 task drafting must not proceed until Phase 2 documentation is consolidated into a persistable artifact package. 

---

## 2. Included Approved Deliverables

### Phase 2 Planning Document

* Status: approved.
* Supervisor decision: approved for next Supervisor-controlled step.
* Remaining blocker: no.

### Contract Interpretation and Validation Mapping

* Status: approved.
* Supervisor decision: approved with one non-blocking Supervisor condition.
* Remaining blocker: no, because the condition was resolved through the approved Pre-Implementation Lock Items document.

### Pre-Implementation Lock Items

* Status: approved.
* Supervisor decision: approved.
* Remaining blocker: no.

### Phase 3 Readiness Transition Document

* Status: approved.
* Supervisor decision: Phase 2 complete, with readiness to draft a future Phase 3 implementation task only for Supervisor review.
* Remaining blocker: yes for execution, no for Phase 2 completion. Coding remains unauthorized.

---

# 3. Phase 2 Planning Document

## Phase 2 Planning Document - Contract Implementation Preparation

### 1. Phase Status

* Current phase: Phase 2 - Contract Implementation Preparation.
* Previous phase status: Phase 1 complete, locked, committed, and repository-clean.
* Repository state: clean.
* Permission to code: no.

Phase 1 is not reopened. The current work is planning only.

Phase 1 closure confirms the core flow is complete, with no backend changes, no UI business logic, route-state-only data flow, no global/shared state, and backend as source of truth.

The Cleanup / Rollback Summary confirms the system is stable, prior violations were resolved or correctly classified, and UI Phase 1 core flow was implemented.

### 2. Phase 2 Goal

Prepare an exact implementation-ready interpretation of the approved Phase 1 contracts before any further coding begins.

The practical goal is to make sure a later implementation task can be drafted without inventing fields, adding fallback behavior, introducing formulas, or reopening Phase 1.

Phase 2 is preparation only. It does not implement contracts, does not add tests, and does not touch backend, frontend, database, API, engine, or UI.

Phase 2 scope is limited to contract interpretation, validation behavior mapping, error code/path conventions, and boundary expectations.

### 3. Allowed Work

Allowed Phase 2 work:

1. Review approved Phase 1 contracts conceptually.
2. Interpret each contract into implementation-ready requirements.
3. Identify required fields.
4. Identify optional fields only if already approved.
5. Map validation behavior.
6. Map stable validation error paths.
7. Map stable validation error codes.
8. Define blocking versus non-blocking validation expectations.
9. Confirm engine/API/service/UI boundary expectations.
10. Confirm that all approved Golden Cases can be represented by the contracts.
11. Create an ambiguity and open-question list if needed.
12. Prepare the planning basis for a later Supervisor-approved implementation task.

No implementation happens in this phase.

### 4. Forbidden Work

Forbidden Phase 2 work:

1. No code.
2. No implementation file paths.
3. No formulas.
4. No calculation logic.
5. No engine logic.
6. No persistence.
7. No database schema changes.
8. No migrations.
9. No API business routes.
10. No UI forms.
11. No frontend work.
12. No backend implementation.
13. No tests yet unless explicitly scoped later.
14. No reopening Phase 1.
15. No adding missing Phase 1 deferred items.
16. No history screen implementation.
17. No run detail implementation.
18. No UI smoke test implementation.
19. No validation-depth implementation.
20. No UX improvements.
21. No pension scope.
22. No tax scope.
23. No cashflow scope.
24. No scenario scope.
25. No report or PDF scope.
26. No LLM or agent scope.
27. No authentication implementation.
28. No external integrations.
29. No fallback behavior.
30. No hidden defaults.
31. No V1 code reuse.

### 5. Contract Review Checklist

Each contract must be reviewed only at the planning level.

#### FixationInput

Confirm:

* Every required input is explicit.
* No input depends on DB state, UI state, browser state, hidden state, or external API.
* All fields required for Golden Case representation exist.
* Missing required data blocks calculation.
* No fallback or inferred value is allowed.
* Field names and meanings are stable.
* The contract can be used consistently by validation, engine, service, API, and UI.

#### GrantInput

Confirm:

* Grant fields are explicit.
* Date-related grant fields are defined clearly enough for validation.
* Numeric grant fields are defined clearly enough for validation.
* Grant inclusion/exclusion status can be represented if approved by the contracts.
* Multiple grants can be represented.
* Grant validation errors can map to stable item-level paths.
* No grant value is inferred by UI, API, service, or database.

#### ActualCapitalizationInput

Confirm:

* Actual capitalization events can be represented explicitly.
* Required date fields are clear.
* Required numeric fields are clear.
* Multiple actual capitalizations can be represented.
* Validation errors can map to stable item-level paths.
* The contract does not require external lookup or automatic indexation.
* No value is inferred or defaulted.

#### IDFInput

Confirm:

* IDF-specific input is explicit.
* Required IDF fields are clear.
* Optional IDF fields, if any, are approved.
* Validation paths for IDF fields are stable.
* IDF input can be omitted only if the approved contract allows omission.
* No IDF calculation behavior is described or implemented in Phase 2.

#### FixationResult

Confirm:

* Result fields are output-only.
* Result fields are deterministic engine outputs.
* Result fields are not editable by UI.
* Result fields are not produced by API routes or services.
* Result fields are sufficient for persistence and display.
* No result field depends on current date unless supplied through approved input.
* No result field is calculated outside the engine.

#### AuditRow

Confirm:

* Audit rows can describe calculation trace outputs without exposing implementation details.
* Audit row structure is stable.
* Audit rows are engine-produced or contract-defined outputs.
* Audit rows are displayable by API/UI without reinterpretation.
* Audit rows are immutable once saved.
* Audit rows do not become a second calculation authority.

#### ValidationError

Confirm:

* Validation errors have stable paths.
* Validation errors have stable codes.
* Validation errors can represent missing required fields.
* Validation errors can represent invalid date values.
* Validation errors can represent invalid numeric values.
* Validation errors can represent invalid nested grant, capitalization, and IDF inputs.
* Validation errors clearly distinguish blocking errors from any allowed non-blocking notices.
* Failed validation cannot produce a saved success result.

### 6. Validation Mapping Checklist

Before any implementation, the following must be mapped.

#### Required Fields

Confirm:

* Which fields are required at the top-level FixationInput.
* Which fields are required inside GrantInput.
* Which fields are required inside ActualCapitalizationInput.
* Which fields are required inside IDFInput.
* Which result and audit fields are output-only.
* Which missing fields block calculation.

#### Date Validation

Confirm:

* Which fields are dates.
* Accepted date meaning.
* Invalid date behavior.
* Missing required date behavior.
* Stable error path for each date field.
* Stable error code for each date failure type.

No date fallback is allowed.

#### Numeric Validation

Confirm:

* Which fields are numeric.
* Whether zero is allowed per field.
* Whether negative values are allowed per field.
* Missing numeric behavior.
* Invalid numeric behavior.
* Stable error path for each numeric field.
* Stable error code for each numeric failure type.

No silent zero behavior is allowed.

#### Grant Validation

Confirm:

* Required grant-level fields.
* Item-level validation path format.
* Multiple grant validation behavior.
* Whether one invalid grant blocks the full calculation.
* Error code convention for grant-specific failures.

#### Actual Capitalization Validation

Confirm:

* Required actual-capitalization fields.
* Item-level validation path format.
* Multiple actual-capitalization validation behavior.
* Whether one invalid actual capitalization blocks the full calculation.
* Error code convention for actual-capitalization failures.

#### IDF Validation

Confirm:

* Required IDF fields when IDF input exists.
* Whether IDF input itself is optional or required.
* Field-level validation paths.
* Error code convention for IDF-specific failures.
* Blocking behavior for invalid IDF input.

#### Global Fixation Input Validation

Confirm:

* Cross-contract requiredness without defining formulas.
* Whether inconsistent input combinations block calculation.
* Whether empty nested lists are allowed.
* Whether missing nested sections are allowed.
* Stable top-level error paths.
* Stable global error codes.

#### Stable Error Paths

Confirm:

* Top-level field path convention.
* Nested object path convention.
* List item path convention.
* Path convention for grant items.
* Path convention for actual capitalization items.
* Path convention for IDF fields.
* Path convention for global input errors.

#### Stable Error Codes

Confirm:

* Required-field error code convention.
* Invalid-date error code convention.
* Invalid-number error code convention.
* Invalid-nested-item error code convention.
* Invalid-global-input error code convention.
* No ad hoc free-text-only errors.

#### Blocking vs Non-Blocking Validation

Confirm:

* Required input failures are blocking.
* Invalid data failures are blocking.
* Failed validation cannot produce a saved success result.
* Non-blocking notices are allowed only if already approved by the contracts.
* No warning-only continuation for required calculation inputs.

### 7. Boundary Expectations

#### Contracts

Expected boundary:

* Define allowed shapes.
* Define requiredness.
* Define output structures.
* Define validation error structures.
* Do not calculate.
* Do not infer values.
* Do not access DB, API, UI, browser, or external services.

#### Validation

Expected boundary:

* Checks shape, requiredness, dates, numbers, and approved consistency rules.
* Produces stable error paths and codes.
* Blocks invalid calculation input.
* Does not calculate business results.
* Does not apply defaults or fallback values.
* Does not replace engine authority.

#### Engine

Expected boundary:

* Future calculation authority only.
* Accepts approved contract input.
* Returns approved contract output.
* Produces deterministic result and audit output.
* Does not access DB.
* Does not call API.
* Does not depend on UI.
* Does not use hidden state.
* Does not use external services.

#### Service / Orchestration

Expected boundary:

* Future coordination layer only.
* Loads approved source data.
* Assembles explicit engine input.
* Calls engine.
* Persists exact input snapshot and exact output.
* Does not contain formulas.
* Does not patch engine output.
* Does not infer missing calculation values.

#### API

Expected boundary:

* Transport boundary only.
* Receives requests.
* Calls services.
* Returns contract-aligned responses.
* Does not calculate.
* Does not add frontend-specific hacks.
* Does not introduce hidden defaults.
* Does not mutate historical results.

#### UI

Expected boundary:

* Collects and displays data only.
* Uses API client boundary.
* Does not calculate.
* Does not transform business values.
* Does not infer missing inputs.
* Does not use global/shared state, browser storage, or query params for this locked flow.
* Displays backend/API/engine outputs only.

### 8. Golden Case Representability Check

Phase 2 must verify that every approved Golden Case can be expressed using the approved contracts, without calculating expected values.

The representability check must confirm:

1. Each Golden Case has all required top-level FixationInput fields.
2. Each Golden Case can express its required grants through GrantInput.
3. Each Golden Case can express actual capitalization events through ActualCapitalizationInput where relevant.
4. Each Golden Case can express IDF input through IDFInput where relevant.
5. Each Golden Case can produce a FixationResult shape without needing additional unapproved output fields.
6. Each Golden Case can produce AuditRow entries without requiring unapproved trace fields.
7. Each validation failure case can be represented through ValidationError.
8. No Golden Case requires V1-only fields.
9. No Golden Case requires hidden defaults.
10. No Golden Case requires UI/API/service calculation behavior.
11. No Golden Case requires external API/indexation.
12. No Golden Case requires pension, tax, cashflow, scenario, report, LLM, or auth scope.

No expected numeric values are calculated in Phase 2.

### 9. Ambiguity / Open Question Protocol

Phase 2 must stop and document an open question if any of the following appears:

1. A required field is unclear.
2. A field meaning is unclear.
3. A Golden Case cannot be represented by the approved contracts.
4. A V1-only field appears necessary.
5. A validation rule is unclear.
6. An error path convention is unclear.
7. An error code convention is unclear.
8. Blocking versus non-blocking validation is unclear.
9. A formula appears necessary to interpret the contract.
10. A fallback/default appears necessary.
11. Current date behavior appears necessary but is not explicitly supplied by input.
12. External API/indexation appears necessary.
13. UI calculation appears necessary.
14. API calculation appears necessary.
15. Service formula logic appears necessary.
16. DB access inside engine appears necessary.
17. Any scope outside Phase 2 preparation appears necessary.

Each open question must document:

* Question.
* Affected contract.
* Affected validation area.
* Affected Golden Case, if any.
* Relevant approved artifact.
* Why the current approved spec is insufficient.
* Risk if unresolved.
* Decision required before implementation.

No silent decision is allowed.

### 10. Acceptance Criteria For Phase 2

Phase 2 planning is complete only when:

1. All approved contracts have been reviewed conceptually.
2. Requiredness expectations are documented.
3. Validation categories are mapped.
4. Stable error path conventions are defined at planning level.
5. Stable error code conventions are defined at planning level.
6. Blocking versus non-blocking validation behavior is defined.
7. Boundaries between contracts, validation, engine, service, API, and UI are clear.
8. All approved Golden Cases are confirmed representable by the contracts.
9. No Golden Case requires unapproved fields.
10. No Phase 1 item is reopened.
11. No coding instruction has been issued.
12. No implementation paths have been specified.
13. No formulas have been introduced.
14. No backend, frontend, API, DB, persistence, engine, or UI scope has been added.
15. Open questions are either empty or explicitly documented as blockers.

Acceptance gate: no contract ambiguity remains before implementation can be prepared.

### 11. Output Expected From Coding Model Later

After Supervisor approval only, a future implementation task would need a high-level implementation package for the next phase.

That future task would likely require:

* Approved contract interpretation.
* Approved validation mapping.
* Approved error code/path conventions.
* Approved boundary expectations.
* Approved confirmation that Golden Cases are representable.
* Approved open-question resolutions, if any.

No implementation task is written now.

The Coding Model must not receive coding instructions until Supervisor approval is completed.

### 12. Final Instructor Decision

**PHASE 2 PLANNING READY FOR SUPERVISOR REVIEW**

---

# 4. Supervisor Approval - Phase 2 Planning

## Supervisor Decision

**APPROVED FOR NEXT SUPERVISOR-CONTROLLED STEP**

## Key Approval Conditions

The Phase 2 Planning Document was approved because it:

* stayed within Contract Implementation Preparation;
* correctly treated Phase 2 as planning only;
* did not authorize code;
* did not address the Coding Model;
* did not include implementation details;
* did not reopen Phase 1;
* did not add deferred Phase 1 items;
* did not expand into Phase 3;
* preserved the locked architecture and source-of-truth boundaries.

## Result

The Instructor was allowed to prepare the next non-coding Phase 2 deliverable:

**Contract Interpretation and Validation Mapping**

Coding remained blocked.

---
# 5. Contract Interpretation and Validation Mapping

## Contract Interpretation and Validation Mapping - Phase 2

### 1. Phase Control

* Current phase: Phase 2 - Contract Implementation Preparation.
* Permission to code: no.
* Coding Model status: blocked.
* Scope boundary: non-coding contract interpretation and validation mapping only.

Phase 1 remains locked. No implementation, no tests, no file paths, no schemas, no formulas, no backend work, no frontend work, and no deferred Phase 1 items are included in this deliverable.

### 2. Contract Inventory

The contracts to be interpreted at planning level are:

1. FixationInput.
2. GrantInput.
3. ActualCapitalizationInput.
4. IDFInput.
5. FixationResult.
6. AuditRow.
7. ValidationError.

### 3. FixationInput Interpretation

#### Required input categories

FixationInput must represent the complete calculation input required by the fixation workflow.

At planning level, required categories are:

* client-related calculation context;
* eligibility-related context;
* fixation parameter context;
* employment/work-period context where required by the approved contracts;
* grant input collection where relevant;
* actual capitalization input collection where relevant;
* IDF-related input where relevant;
* values required to allow deterministic engine execution;
* values required to allow Golden Case representation.

Every required category must be explicit. No required value may depend on hidden state, current UI state, database inference, external lookup, or automatic fallback.

#### Optional input categories, only if approved

Optional categories may exist only when already approved by the contracts.

Possible optional categories at this interpretation level:

* empty or omitted grant collection, if the approved contract allows cases without grants;
* empty or omitted actual capitalization collection, if the approved contract allows cases without actual capitalizations;
* IDF input, if approved as relevant only for IDF scenarios;
* optional metadata that does not affect calculation authority.

No optional category may become a hidden fallback mechanism.

#### Prohibited inferred values

The following are prohibited:

* inferred missing dates;
* inferred missing numeric values;
* silent zero values;
* default eligibility assumptions;
* default cap assumptions;
* automatic indexation;
* external API lookup;
* current-date dependency unless supplied as approved input;
* values derived by UI;
* values derived by API routes;
* values invented by service/orchestration;
* V1-only fields added for convenience.

#### Validation responsibility

FixationInput validation must confirm:

* required top-level input categories are present;
* required nested input categories are present when relevant;
* date values are valid where dates are required;
* numeric values are valid where numbers are required;
* nested collections are valid;
* global input consistency is sufficient to allow deterministic calculation;
* failed required validation blocks calculation.

Validation must not calculate business results.

#### Representability requirements for Golden Cases

FixationInput must be able to represent:

* base case;
* grant scenarios;
* 15-year exclusion scenario;
* partial 32-year ratio scenario;
* multiple grant scenario;
* future grant reserve scenario;
* actual capitalization scenario;
* IDF scenario;
* combined scenario;
* zero remaining exemption scenario;
* ratio boundary scenarios;
* validation failure scenarios.

No Golden Case may require unapproved fields or hidden defaults.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the approved contracts already define the exact concrete fields for each required category before Phase 3 begins.

### 4. GrantInput Interpretation

#### Required grant categories

GrantInput must represent each grant that may affect the fixation calculation.

At planning level, required categories are:

* grant identity or description category, if approved;
* grant date category;
* grant amount category;
* grant classification/category needed by the approved contracts;
* any approved category needed to determine whether the grant participates in the calculation;
* any approved category needed for Golden Case representation.

#### Date-related categories

GrantInput must clearly identify all grant-related dates required by the approved contracts.

Validation must confirm:

* required grant dates are present;
* date values are valid;
* date paths are item-specific;
* invalid grant dates block calculation where the grant is part of required calculation input.

No grant date may be inferred from another date unless explicitly approved.

#### Numeric categories

GrantInput must clearly identify all numeric grant values required by the approved contracts.

Validation must confirm:

* required numeric values are present;
* numeric values are valid;
* disallowed negative or invalid values are blocked;
* silent zero is not used for missing required data.

#### Multiple grant handling

The contract must support multiple grants.

Planning expectation:

* each grant is validated as an individual item;
* multiple grants can exist in the same FixationInput;
* one invalid required grant item blocks successful calculation;
* item-specific validation errors must identify the relevant grant item.

#### Item-level validation expectation

Grant validation must produce stable item-level error paths and stable error codes.

The validation structure must make clear:

* which grant item failed;
* which field category failed;
* why it failed;
* whether the failure blocks calculation.

#### Prohibited inference/defaulting

The following are prohibited:

* default grant amount;
* default grant date;
* default grant classification;
* automatic grant exclusion unless explicitly represented and approved;
* deriving grant values from V1-only fields;
* deriving grant values from UI or API route logic.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the approved contracts define the required grant categories and the allowed grant classifications before implementation.

### 5. ActualCapitalizationInput Interpretation

#### Required event categories

ActualCapitalizationInput must represent actual exemption-consuming capitalization events.

At planning level, required categories are:

* event date category;
* event amount category;
* event classification or description category, if approved;
* any approved category required to represent actual capitalization Golden Cases.

#### Date-related categories

Actual capitalization events must include the approved date category required for validation and representability.

Validation must confirm:

* required event dates are present;
* date values are valid;
* date errors identify the specific event item;
* invalid event dates block calculation when the event is part of required calculation input.

#### Numeric categories

Actual capitalization events must include the approved numeric amount category.

Validation must confirm:

* required event amounts are present;
* event amounts are valid numbers;
* disallowed negative or invalid values are blocked;
* missing required amounts do not become zero.

#### Multiple capitalization handling

The contract must support multiple actual capitalization events.

Planning expectation:

* each event is validated separately;
* item-level errors are stable;
* one invalid required event blocks successful calculation;
* multiple valid events can be represented together.

#### Item-level validation expectation

Actual capitalization validation must identify:

* the relevant event item;
* the failed field category;
* the failure reason;
* blocking status.

#### Prohibition on automatic indexation/external lookup

ActualCapitalizationInput must not depend on:

* automatic indexation;
* external CPI lookup;
* external API lookup;
* database-side calculation;
* UI-side calculation;
* service-side formula logic.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the approved contracts define the exact event categories and whether the collection may be empty.

### 6. IDFInput Interpretation

#### Whether IDF input is optional or required according to approved contracts

At planning level, IDFInput should be treated as conditionally relevant.

It is required only when the approved contracts identify the case as requiring IDF-specific input. It should not be forced into non-IDF scenarios unless the approved contracts say otherwise.

#### Required categories if IDF input exists

If IDFInput exists, it must include every approved category required to represent the IDF Golden Case.

Planning-level categories may include:

* IDF eligibility/context category;
* IDF-specific date category, if approved;
* IDF-specific numeric category, if approved;
* IDF-specific classification category, if approved.

No concrete field list is defined in this document.

#### Validation expectation

Validation must confirm:

* required IDF categories are present when IDFInput exists and is relevant;
* IDF date categories are valid if present;
* IDF numeric categories are valid if present;
* IDF validation errors use stable paths and codes;
* invalid required IDF input blocks successful calculation.

#### Omission behavior

Planning expectation:

* omission is allowed for non-IDF cases if approved by the contracts;
* omission is not allowed where the approved contract requires IDF input;
* omission must not trigger hidden defaults;
* omission must not cause the engine, API, service, or UI to infer IDF values.

#### Ambiguity risk

Potential ambiguity exists only if the approved contracts do not explicitly state whether IDFInput is optional, required, or conditionally required.

At this planning level, this is not marked as a blocker because the Build Spec identifies IDFInput as a contract and IDF impact as a Golden Case category.

### 7. FixationResult Interpretation

#### Output-only nature

FixationResult is output-only.

It must represent the deterministic result produced by the future fixation engine. It is not a user input structure and must not be edited by UI or patched by service/API.

#### Engine authority

Only the fixation engine may produce FixationResult values.

The API may return result values.

The service may persist and retrieve result values.

The UI may display result values.

None of those layers may produce or calculate the result values.

#### Persistence/display sufficiency

FixationResult must be sufficient for:

* saving immutable calculation output;
* reloading a saved run;
* displaying result values in UI;
* comparing saved output to engine output during future verification;
* reproducing output from the saved input snapshot.

#### Prohibition on API/service/UI production of result values

Forbidden:

* API route formulas;
* service formulas;
* UI formulas;
* frontend result patching;
* UI transformation of financial values;
* persistence-side calculation;
* result mutation after save.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the approved contracts define the exact result fields before implementation.

### 8. AuditRow Interpretation

#### Audit purpose

AuditRow exists to support explainability and reproducibility of the fixation calculation.

At planning level, AuditRow should describe calculation trace information in a stable, displayable structure without becoming a separate calculation system.

#### Engine/contract output nature

AuditRow is expected to be:

* contract-defined;
* produced as part of deterministic engine output;
* saved with the run;
* readable later without recalculation;
* displayable without UI interpretation.

#### Immutability expectation

Audit rows must be immutable once saved.

They must remain tied to the saved calculation run and must not change when source data is edited later.

#### Display without reinterpretation

Audit rows must be displayable by API/UI without:

* recalculating;
* translating business meaning into new values;
* deriving missing figures;
* changing result values;
* becoming an alternate financial authority.

#### Prohibition on becoming second calculation authority

AuditRow must not:

* contain independent formulas;
* override FixationResult;
* be used to calculate result values in UI/API/service;
* become a workaround for missing result fields.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the approved contracts define the required audit row structure before implementation.

### 9. ValidationError Interpretation

#### Stable path requirement

ValidationError must include a stable path that identifies where the validation problem occurred.

Planning-level path types:

* top-level field path;
* nested object field path;
* list item field path;
* global input path.

#### Stable code requirement

ValidationError must include a stable code that identifies the type of validation failure.

Codes must be suitable for future API/UI display and testing without relying only on free text.

#### Blocking error representation

ValidationError must clearly support blocking errors.

Blocking errors include:

* missing required calculation input;
* invalid required date;
* invalid required numeric value;
* invalid required nested item;
* invalid global input combination where approved;
* unsupported or unapproved value where relevant.

Failed validation cannot produce a saved success result.

#### Nested error representation

ValidationError must represent nested failures for:

* grant items;
* actual capitalization items;
* IDF fields;
* nested objects inside FixationInput, if approved.

#### No free-text-only validation

Free text may be used for human-readable display, but it cannot be the only validation structure.

A valid validation error must have a stable location and stable failure classification.

#### Ambiguity risk

No open ambiguity is identified at this planning level, provided the exact path and code conventions are approved before implementation.

### 10. Validation Mapping

#### Required-field validation

Planning expectation:

* missing required fields block calculation;
* missing required nested fields block calculation;
* required collection behavior must be explicit;
* no required value may be silently defaulted;
* no missing numeric value becomes zero.

#### Date validation

Planning expectation:

* invalid required dates block calculation;
* missing required dates block calculation;
* date errors must identify the exact field or item;
* no date fallback is allowed;
* no current-date assumption is allowed unless current date is an approved supplied input.

#### Numeric validation

Planning expectation:

* invalid required numbers block calculation;
* missing required numbers block calculation;
* disallowed negative values block calculation;
* field-specific zero rules must be defined before implementation;
* no silent zero behavior is allowed.

#### Grant validation

Planning expectation:

* required grant fields are validated per item;
* invalid grant items produce item-level errors;
* invalid required grant data blocks calculation;
* multiple grant errors may be represented together;
* no grant value is inferred.

#### Actual capitalization validation

Planning expectation:

* required actual capitalization fields are validated per item;
* invalid event items produce item-level errors;
* invalid required event data blocks calculation;
* multiple event errors may be represented together;
* no automatic indexation or external lookup is allowed.

#### IDF validation

Planning expectation:

* IDF input is validated when present or required by the approved contract;
* invalid required IDF data blocks calculation;
* omitted IDF input is allowed only for scenarios where the approved contract allows omission;
* no IDF value is inferred.

#### Global input validation

Planning expectation:

* global validation may check whether the total input package is sufficiently complete;
* global validation must not calculate business results;
* global errors must have stable paths and stable codes;
* global validation may block calculation where the approved contract requires it.

#### Blocking vs non-blocking behavior

Planning expectation:

* required-field failures are blocking;
* invalid date failures are blocking;
* invalid numeric failures are blocking;
* invalid nested item failures are blocking when the nested item is calculation-relevant;
* unsupported or unapproved values are blocking;
* non-blocking notices are allowed only if already approved;
* warning-only continuation is not allowed for required calculation input.

### 11. Error Path Convention Proposal

Planning-level convention only.

#### Top-level fields

Top-level errors should identify the direct input category or field category in FixationInput.

Example at concept level:

* fixation input category;
* eligibility category;
* parameter category;
* employment/work-period category.

No implementation-specific syntax is defined here.

#### Nested objects

Nested object errors should identify:

* parent category;
* nested category;
* failed field category.

Example at concept level:

* client/profile context category;
* nested eligibility field category;
* nested fixation parameter category.

#### List items

List item errors should identify:

* collection category;
* item position or item identity, if approved;
* failed field category.

Relevant collections:

* grants;
* actual capitalizations;
* any other approved nested collection.

#### Global input errors

Global errors should identify the whole input package rather than a single field.

Planning-level use cases:

* invalid overall combination;
* insufficient calculation context;
* unsupported approved-contract combination;
* required scenario context missing.

No code syntax, schema notation, enum, or implementation path is created in this document.

### 12. Error Code Convention Proposal

Planning-level convention only.

#### Missing required value

Use a stable code category for missing required input.

Purpose:

* identify absent required top-level values;
* identify absent required nested values;
* distinguish missing from invalid.

#### Invalid date

Use a stable code category for invalid date input.

Purpose:

* identify malformed or unacceptable date values;
* distinguish date failures from numeric or requiredness failures.

#### Invalid number

Use a stable code category for invalid numeric input.

Purpose:

* identify invalid numeric values;
* identify disallowed numeric ranges where approved;
* distinguish invalid numbers from missing numbers.

#### Invalid nested item

Use a stable code category for invalid collection items.

Purpose:

* identify grant item failures;
* identify actual capitalization item failures;
* identify other approved nested item failures.

#### Invalid global combination

Use a stable code category for invalid whole-input combinations.

Purpose:

* identify input package inconsistency;
* identify unsupported combinations where approved;
* identify missing scenario-level context.

#### Unsupported or unapproved value

Use a stable code category for values that are not permitted by the approved contracts.

Purpose:

* block V1-only or invented values;
* prevent unsupported classifications;
* prevent implementation from accepting unapproved shortcuts.

No implementation enums, constants, class names, or code identifiers are created here.

### 13. Golden Case Representability Matrix

No numeric values are calculated in this matrix.

| Golden Case Category         | Representability Assessment                                                                                                                                             |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| base case                    | Appears representable by FixationInput and FixationResult, assuming all approved required base input categories are present                                             |
| single grant full impact     | Appears representable through FixationInput with one GrantInput item                                                                                                    |
| 15-year exclusion            | Appears representable through approved grant/date/context categories, assuming the contracts include the required date/context inputs                                   |
| partial 32-year ratio        | Appears representable through approved employment/work-period or ratio-related input categories, assuming those categories are present in the contracts                 |
| multiple grants              | Appears representable through multiple GrantInput items                                                                                                                 |
| future grant reserve only    | Appears representable through GrantInput or approved fixation input category for future grant reserve, assuming the approved contracts explicitly include that category |
| actual capitalization impact | Appears representable through ActualCapitalizationInput                                                                                                                 |
| IDF impact                   | Appears representable through IDFInput, assuming conditional IDF input rules are defined in the approved contracts                                                      |
| combined full scenario       | Appears representable through combined FixationInput containing grant, actual capitalization, IDF, and required global context categories                               |
| zero remaining exemption     | Appears representable as a FixationResult outcome, without calculating values here                                                                                      |
| ratio boundaries             | Appears representable if approved ratio/work-period input categories are explicit in FixationInput                                                                      |
| validation failure cases     | Appears representable through ValidationError with stable paths and codes                                                                                               |

### 14. Open Questions

No open questions identified at this planning level.

Planning note: before any Phase 3 implementation task is written, the Supervisor should confirm that the approved contracts already contain the concrete field definitions needed for:

* IDFInput conditional requiredness;
* future grant reserve representation;
* ratio/work-period representation;
* exact required versus optional nested collections;
* exact validation path and code convention.

This is not a Phase 2 blocker at the current interpretation level, but it must be locked before implementation.

### 15. Instructor Final Decision

**CONTRACT INTERPRETATION READY FOR SUPERVISOR REVIEW**

---

# 6. Supervisor Approval - Contract Interpretation and Validation Mapping

## Approval Decision

**APPROVED WITH ONE NON-BLOCKING SUPERVISOR CONDITION**

## Approval Basis

The document was approved because it:

* stayed within approved Phase 2 scope;
* remained non-coding;
* did not address the Coding Model;
* did not include file paths;
* did not include schemas/classes/models;
* did not include tests;
* did not introduce formulas;
* did not reopen Phase 1;
* correctly framed the deliverable as contract interpretation and validation mapping only.

## Non-Blocking Supervisor Condition

The document stated:

**“No open questions identified at this planning level.”**

That was accepted for the deliverable, but the planning note in section 14 was elevated into a pre-implementation lock requirement.

Before any Phase 3 implementation task could be written, the following five items had to be explicitly confirmed from the approved contracts:

1. IDFInput conditional requiredness.
2. Future grant reserve representation.
3. Ratio/work-period representation.
4. Exact required versus optional nested collections.
5. Exact validation path and code convention.

## Result

The condition did not block approval of the Contract Interpretation document.

It did block moving into implementation wording until the five items were locked.

Coding Model remained blocked.

---

# 7. Pre-Implementation Lock Items

## Pre-Implementation Lock Items - Phase 2

### 1. Phase Control

* Current phase: Phase 2 - Contract Implementation Preparation.
* Permission to code: no.
* Coding Model status: blocked.
* Phase 3 status: not allowed yet.
* Purpose of this document: explicitly lock the five Supervisor-identified pre-implementation items before any future Phase 3 implementation task can be written.

This document is non-coding only. It does not create implementation instructions, does not define concrete schemas, does not include formulas, does not add tests, and does not reopen Phase 1.

### 2. Supervisor Condition Summary

The Supervisor required that the following five items be explicitly locked before any Phase 3 implementation wording:

1. IDFInput conditional requiredness.
2. Future grant reserve representation.
3. Ratio/work-period representation.
4. Exact required versus optional nested collections.
5. Exact validation path and code convention.

This condition does not reopen Phase 1 and does not authorize Phase 3. It only permits a final Phase 2 lock document.

### 3. Lock Item 1 - IDFInput Conditional Requiredness

#### When IDFInput is required

IDFInput is required only when the approved calculation scenario is IDF-relevant.

At planning level, an IDF-relevant scenario means a case where the approved contract requires IDF-specific context in order to represent the scenario and allow the future engine to produce IDF-related output.

IDFInput is not a universal requirement for every FixationInput.

#### When IDFInput may be omitted

IDFInput may be omitted when the scenario is not IDF-relevant.

Omission is valid only if the approved contract does not require IDF-specific context for that scenario.

Omission must not trigger:

* hidden defaults;
* inferred IDF values;
* service-side assumptions;
* API-side assumptions;
* UI-side assumptions;
* fallback behavior.

#### What happens if IDFInput is present but incomplete

If IDFInput is present, it must be complete according to the approved required categories for IDFInput.

An incomplete IDFInput is invalid.

The validation outcome must be blocking when the missing or invalid IDF category is required for the scenario.

#### What happens if IDFInput is omitted in an IDF-relevant scenario

If IDFInput is omitted in an IDF-relevant scenario, validation must block calculation.

The omission must be represented as a stable validation error. It must not be repaired through inference, fallback, or default values.

#### Validation outcome

* Non-IDF scenario with omitted IDFInput: valid, if omission is allowed by the approved contract.
* IDF-relevant scenario with complete IDFInput: valid at contract level, subject to all other validations.
* IDF-relevant scenario with omitted IDFInput: blocking validation error.
* IDFInput present but incomplete: blocking validation error.
* IDFInput present with invalid date/numeric/category values: blocking validation error.

#### Lock status

Locked at contract/planning level.

Reason: the approved Phase 1 Build Spec identifies IDFInput as one of the Phase 1 contract components and identifies IDF impact as a Golden Case category, while Phase 2 is permitted to lock requiredness and validation behavior without implementing fields or formulas.

### 4. Lock Item 2 - Future Grant Reserve Representation

#### Where future grant reserve is represented

Future grant reserve must be represented as an explicit approved input category within the fixation calculation input package.

At planning level, it is part of the broader FixationInput package and may be represented through either:

* a dedicated future-grant-reserve category inside FixationInput, if the approved contracts define it that way;
* a specific approved grant-related category, if the approved contracts define future grant reserve as part of GrantInput.

This document does not invent a concrete field.

#### Whether it is part of GrantInput or FixationInput category

Locked interpretation:

Future grant reserve belongs to the approved fixation input contract package. Its exact placement must follow the approved contract wording.

Planning rule:

* If the approved contracts define future grant reserve as a grant item, it is represented through GrantInput.
* If the approved contracts define it as a fixation-level reserve category, it is represented through FixationInput.
* It must not be inferred from ordinary grants unless the approved contracts explicitly say so.

#### Whether absence is allowed

Absence is allowed in scenarios where no future grant reserve is being claimed or represented.

Absence is not allowed in the future grant reserve Golden Case or any scenario where the user/input package indicates that a future grant reserve is part of the calculation context.

#### How the scenario is represented without inference

The scenario must be represented by explicit input.

The system must not infer future grant reserve from:

* age;
* employment status;
* grant history;
* missing current grant;
* client profile;
* UI state;
* API assumptions;
* service assumptions;
* V1 behavior.

#### Validation outcome

* Scenario does not include future grant reserve: absence is valid if the approved contract allows it.
* Scenario includes future grant reserve but reserve category is missing: blocking validation error.
* Future grant reserve category is present but incomplete: blocking validation error.
* Future grant reserve category contains invalid date/numeric/category values: blocking validation error.

#### Lock status

Locked at contract/planning level.

Reason: the approved Phase 1 Build Spec includes future grant reserve impact as part of the future engine behavior and includes a Golden Case for future grant reserve only. This lock does not define formulas or implementation fields.

### 5. Lock Item 3 - Ratio / Work-Period Representation

#### What input category represents work-period or ratio context

The work-period or ratio context must be represented as an explicit approved input category within FixationInput.

At planning level, this means the contract must contain enough approved source context to represent:

* full work-period cases;
* partial work-period cases;
* ratio boundary cases;
* Golden Cases requiring partial ratio behavior.

#### Whether direct ratio input is allowed or prohibited

Direct ratio input is prohibited unless explicitly approved by the contracts.

Planning rule:

* The preferred contract interpretation is raw work-period context as input.
* A direct ratio may be accepted only if the approved contracts explicitly define direct ratio as an input category.
* If the contracts do not explicitly approve direct ratio input, the future engine remains the only authority to determine ratio behavior from approved input context.

#### Whether raw work-period context is required

Raw work-period context is required when the scenario depends on work-period or ratio behavior and the approved contracts do not explicitly allow direct ratio input.

The input package must be sufficient for deterministic future engine execution without UI/API/service calculation.

#### How boundary cases are representable

Boundary cases must be representable through explicit approved input categories.

At planning level, boundary cases include:

* full period boundary;
* partial period boundary;
* minimum or maximum relevant period category, if approved;
* invalid or out-of-range context, if relevant to validation.

No calculation details are defined here.

#### Validation outcome

* Required work-period context missing in a ratio-relevant scenario: blocking validation error.
* Work-period context present but incomplete: blocking validation error.
* Work-period context present but invalid: blocking validation error.
* Direct ratio supplied without contract approval: unsupported/unapproved value error.
* Direct ratio supplied with explicit contract approval: valid at contract level, subject to all other validations.

#### Lock status

Locked at contract/planning level.

Reason: the approved Phase 1 Build Spec identifies 32-year work ratio behavior and ratio boundaries as future engine/Golden Case categories. This document only locks the input-authority boundary and representability rule, without formula or calculation detail.

### 6. Lock Item 4 - Required vs Optional Nested Collections

#### Grant collection requiredness

Grant collection is conditionally required.

Planning rule:

* If the scenario includes grants or a Golden Case requires grants, the grant collection must be present and valid.
* If the scenario has no grants, the collection may be empty or omitted only if the approved contract allows no-grant scenarios to be represented that way.
* The absence of grants must not be interpreted as hidden grant data.

#### Actual capitalization collection requiredness

Actual capitalization collection is conditionally required.

Planning rule:

* If the scenario includes actual capitalization impact, the collection must be present and valid.
* If the scenario has no actual capitalization events, the collection may be empty or omitted only if the approved contract allows that representation.
* Missing actual capitalization events must not be inferred from other fields.

#### IDF input requiredness

IDFInput is conditionally required.

Planning rule:

* Required for IDF-relevant scenarios.
* May be omitted for non-IDF scenarios, if allowed by the approved contract.
* Present but incomplete IDFInput is invalid.

#### Empty collection behavior

Empty collection behavior must be explicit.

Planning-level lock:

* Empty grant collection is valid only for scenarios where no grants are represented and the approved contract allows empty grant collection.
* Empty actual capitalization collection is valid only for scenarios where no actual capitalization events are represented and the approved contract allows empty actual capitalization collection.
* Empty collections cannot be used to hide missing required scenario data.

#### Omitted collection behavior

Omitted collection behavior must be explicit.

Planning-level lock:

* Omission is valid only where the approved contract allows omission.
* Omission is invalid where the scenario requires the collection.
* Omitted required collection produces a blocking validation error.
* Omission must not trigger automatic empty-list defaulting unless the approved contract explicitly treats omission and empty collection as equivalent.

#### Invalid item behavior

If a nested collection contains an invalid item:

* the item-level error must identify the affected collection;
* the item-level error must identify the affected item;
* the item-level error must identify the failed category;
* the failure must block calculation if the item is part of required calculation input.

#### Validation outcome

* Required collection missing: blocking validation error.
* Required collection empty: blocking validation error if scenario requires at least one item.
* Optional collection omitted: valid only if approved.
* Optional collection empty: valid only if approved.
* Collection contains invalid item: blocking validation error.
* Collection contains unsupported item category: blocking validation error.

#### Lock status

Locked at contract/planning level.

Reason: Phase 1 validation behavior requires missing required calculation input to block calculation, invalid data to avoid fallback, and validation errors to map to contract fields.

### 7. Lock Item 5 - Validation Path and Code Convention

Planning-level convention only. No implementation enum, constant, class, schema, or file path is created.

#### Top-level path convention

Top-level validation paths must identify the affected top-level FixationInput category.

A top-level path is used when the error belongs directly to the whole input package category rather than a nested object or list item.

#### Nested object path convention

Nested object paths must identify:

* parent category;
* nested category;
* failed field/category.

This applies to approved nested objects inside FixationInput.

#### List item path convention

List item paths must identify:

* collection category;
* item position or approved item identity;
* failed field/category.

This applies to grant items, actual capitalization items, and any other approved nested collection.

#### Global error path convention

Global input errors must identify the full input package rather than a specific single field.

Global paths are used only when the validation issue is a whole-input consistency issue that cannot be honestly attributed to one field.

#### Missing required code convention

Missing required value errors must use a stable code category for missing required input.

This category applies to:

* missing top-level required categories;
* missing nested required categories;
* missing required item fields;
* missing conditionally required scenario input.

#### Invalid date code convention

Invalid date errors must use a stable code category for invalid date input.

This category applies to:

* invalid required date;
* unacceptable date format or meaning;
* missing date only when classified separately as missing required value, if the convention requires separation.

#### Invalid number code convention

Invalid number errors must use a stable code category for invalid numeric input.

This category applies to:

* invalid number;
* disallowed negative value;
* disallowed numeric range;
* invalid zero where zero is not allowed by the approved contract.

#### Invalid nested item code convention

Invalid nested item errors must use a stable code category for invalid collection items.

This category applies to:

* invalid grant item;
* invalid actual capitalization item;
* invalid approved nested collection item.

#### Invalid global input code convention

Invalid global input errors must use a stable code category for invalid whole-input combinations.

This category applies to:

* insufficient scenario context;
* inconsistent input package;
* unsupported approved-contract combination;
* conditionally required context missing at whole-input level.

#### Unsupported value code convention

Unsupported or unapproved value errors must use a stable code category.

This category applies to:

* unapproved classification;
* V1-only value;
* direct ratio input when not approved;
* unsupported scenario marker;
* unapproved nested item type;
* any value outside the approved contracts.

#### Lock status

Locked at planning level.

Reason: Phase 1 contract-locking requires validation errors to have stable paths and codes, while Phase 2 allows preparing error code/path conventions without implementation.

### 8. Lock Status Matrix

| Item                                    | Status | Reason                                                                                                                       | Decision needed, if blocked |
| --------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| IDFInput conditional requiredness       | LOCKED | IDFInput is conditionally required only for IDF-relevant scenarios; omission is valid only for non-IDF scenarios if approved | None                        |
| Future grant reserve representation     | LOCKED | Future grant reserve must be explicit within the approved fixation input package and cannot be inferred                      | None                        |
| Ratio/work-period representation        | LOCKED | Ratio/work-period context must be explicit; direct ratio input is prohibited unless explicitly approved                      | None                        |
| Required vs optional nested collections | LOCKED | Nested collection requiredness is scenario-dependent, and invalid/missing required data blocks calculation                   | None                        |
| Validation path and code convention     | LOCKED | Stable planning-level path and code categories are defined without implementation enums or code constants                    | None                        |

### 9. Impact on Phase 3 Readiness

After this document, a Phase 3 implementation task can be written only if the Supervisor approves this lock document.

Subject to Supervisor approval, the five Supervisor-identified pre-implementation ambiguity items are locked at contract/planning level.

This does not itself authorize implementation. It only removes the specific pre-implementation condition that blocked Phase 3 wording.

Phase 3 remains not allowed until Supervisor approval is received.

### 10. Open Questions

No open questions remain for the five Supervisor lock items.

### 11. Instructor Final Decision

**PRE-IMPLEMENTATION LOCK ITEMS READY FOR SUPERVISOR REVIEW**

---

# 8. Supervisor Approval - Pre-Implementation Lock Items

## Approval Decision

**APPROVED**

## Approval Basis

The Supervisor approved the Pre-Implementation Lock Items document because it:

* stayed within Phase 2;
* remained non-coding;
* did not write implementation instructions;
* did not address the Coding Model;
* did not include file paths;
* did not include schemas/classes/models;
* did not include tests;
* did not include formulas;
* did not reopen Phase 1;
* did not move into Phase 3;
* did not invent contract fields.

## Confirmation of Five Lock Items

The Supervisor-approved lock items were:

1. IDFInput conditional requiredness: approved.
2. Future grant reserve representation: approved.
3. Ratio/work-period representation: approved.
4. Required versus optional nested collections: approved.
5. Validation path and code convention: approved.

## Coding Status

Coding Model remained blocked.

Coding was not authorized.

---
# 9. Phase 3 Readiness Transition Document

## Phase 3 Readiness Transition Document

### 1. Phase Control

* Current phase: Phase 2 - Contract Implementation Preparation.
* Phase 2 status: pending final Supervisor transition decision.
* Phase 3 status: not open.
* Permission to code: no.
* Coding Model status: blocked.

This document is a transition assessment only. It does not authorize implementation, does not create an implementation task, and does not move the process into execution.

### 2. Approved Phase 2 Deliverables

#### Phase 2 Planning Document

* Status: approved.
* Supervisor decision: approved for next Supervisor-controlled step.
* Remaining blocker: no.

#### Contract Interpretation and Validation Mapping

* Status: approved.
* Supervisor decision: approved with one non-blocking Supervisor condition.
* Remaining blocker: no, because the condition was handled in the next approved Phase 2 deliverable.

#### Pre-Implementation Lock Items

* Status: approved.
* Supervisor decision: approved.
* Remaining blocker: no.

### 3. Supervisor Conditions Status

#### IDFInput conditional requiredness

* Status: resolved.
* Notes: locked as conditionally required for IDF-relevant scenarios, omissible only for non-IDF scenarios where approved.

#### Future grant reserve representation

* Status: resolved.
* Notes: locked as an explicit approved input category within the fixation input package, not inferred from other context.

#### Ratio/work-period representation

* Status: resolved.
* Notes: locked as explicit work-period or ratio context according to approved contracts, with direct ratio input prohibited unless explicitly approved.

#### Exact required versus optional nested collections

* Status: resolved.
* Notes: locked as scenario-dependent, with missing or invalid required nested data producing blocking validation.

#### Exact validation path and code convention

* Status: resolved.
* Notes: locked at planning level for top-level, nested, list-item, and global paths, plus stable code categories for required, date, number, nested item, global input, and unsupported value failures.

### 4. Phase 2 Completion Assessment

Phase 2 has completed its allowed purpose.

#### Contract interpretation

Complete.

The Phase 2 deliverables identified and interpreted the approved contract set:

* FixationInput.
* GrantInput.
* ActualCapitalizationInput.
* IDFInput.
* FixationResult.
* AuditRow.
* ValidationError.

#### Validation behavior mapping

Complete.

The deliverables mapped required-field validation, date validation, numeric validation, grant validation, actual capitalization validation, IDF validation, global input validation, and blocking versus non-blocking behavior.

#### Error path/code planning

Complete.

The deliverables defined planning-level conventions for:

* top-level paths;
* nested object paths;
* list item paths;
* global input paths;
* missing required value codes;
* invalid date codes;
* invalid number codes;
* invalid nested item codes;
* invalid global input codes;
* unsupported or unapproved value codes.

No implementation enums, constants, schemas, classes, or code constructs were created.

#### Boundary expectations

Complete.

The deliverables preserved the approved boundaries:

* contracts define shape and requiredness only;
* validation checks approved validity rules only;
* engine remains the future calculation authority;
* service/orchestration coordinates only;
* API does not calculate;
* UI does not calculate;
* no fallback, hidden defaults, automatic indexation, or external lookup.

#### Golden Case representability

Complete.

The deliverables confirmed planning-level representability for the approved Golden Case categories without calculating expected numeric values.

#### Ambiguity handling

Complete.

The previous Supervisor condition was converted into explicit pre-implementation lock items and approved. No Phase 2 ambiguity remains for transition purposes.

### 5. Remaining Open Questions

No Phase 2 open questions remain.

### 6. Phase 3 Entry Boundary

Phase 3 may cover only the implementation of approved Phase 1 domain contracts after Supervisor approval.

Allowed Phase 3 scope, only after approval:

* implementation of approved Phase 1 domain contracts;
* required validation shape;
* contract-level validation behavior;
* stable validation error representation;
* no calculations.

Forbidden Phase 3 scope:

* no formulas;
* no engine behavior;
* no DB writes;
* no persistence;
* no API business logic;
* no UI logic;
* no service/orchestration implementation;
* no tests unless explicitly scoped by the approved Phase 3 task;
* no reopening Phase 1;
* no deferred Phase 1 items;
* no pension, tax, cashflow, scenario, report, LLM, auth, or external integration scope.

### 7. Explicit Non-Authorization

This document does not authorize coding.

This document does not go to the Coding Model.

This document does not itself open Phase 3 execution.

This document does not include implementation instructions.

Supervisor approval is required before any Phase 3 implementation task is drafted or sent.

### 8. Instructor Recommendation

**PHASE 2 COMPLETE - READY FOR SUPERVISOR DECISION ON PHASE 3 TASK DRAFTING**

---

# 10. Supervisor Approval - Phase 3 Readiness Transition

## Phase 2 Complete Decision

The Supervisor approved the Phase 3 Readiness Transition Document and confirmed Phase 2 completion for transition purposes.

## Approval for Instructor to Draft Phase 3 Implementation Task for Supervisor Review

The Supervisor approval allowed the Instructor to draft a future Phase 3 implementation task for Supervisor review.

This approval did not authorize sending an implementation task to the Coding Model.

## Coding Authorization

Coding is still not authorized.

## Coding Model Status

Coding Model remains blocked.

## Correction After Approval

A later correction paused Phase 3 task drafting until this consolidated Phase 2 artifact package is prepared and reviewed.

The current allowed step is therefore this consolidated package, not Phase 3 task drafting. 

---

# 11. Consolidated Phase 2 Final State

* Phase 2 is complete.
* Phase 2 has no remaining open questions.
* The Supervisor’s five pre-implementation lock conditions were resolved.
* Phase 3 drafting may resume only after this consolidated package is approved.
* Coding is still not authorized.
* Coding Model remains blocked.
* This package does not authorize execution.
* This package does not reopen Phase 1.
* This package does not add deferred Phase 1 items.
* This package does not move into Phase 3.
* This package preserves the approved decisions and boundaries.

The requested package purpose is to create one clean, complete, persistable Phase 2 documentation package without relying on conversation memory. 

---

# 12. Persistence Recommendation

After Supervisor approval, this consolidated package should be persisted into the repository documentation/specs area as the official Phase 2 artifact package.

No instruction is given here to Codex, the Coding Model, or any implementation actor.

No file path is specified in this document.

---

# 13. Instructor Final Decision

**CONSOLIDATED PHASE 2 ARTIFACT PACKAGE READY FOR SUPERVISOR REVIEW**
