**System Rebuild Blueprint**

**1. System Purpose And Boundaries**

The system exists to help retirement planners create deterministic, auditable retirement plans for clients.

It must support:

- Client data collection.
- Pension portfolio inventory.
- Employment and grant history.
- Rights fixation calculation.
- Pension projection.
- Tax calculation.
- Retirement cashflow planning.
- Scenario comparison.
- Final retirement plan output.

The system must not be a free-form advisory chatbot, a spreadsheet clone, or a UI-driven calculation surface. Calculations must be owned by deterministic business engines, not by frontend components, prompts, routers, or persistence side effects.

Business boundary:

- The system calculates and presents retirement planning outputs.
- It does not invent missing financial facts.
- It does not silently substitute default business values.
- It does not allow LLMs, UI state, or document generators to become calculation authority.

**2. User Roles**

**Planner / Advisor**

Primary user. Creates clients, enters data, builds scenarios, reviews outputs, and generates retirement plans.

Permissions:
- Create and edit clients.
- Enter pension, employment, grant, commutation, and income data.
- Run calculations.
- Save scenarios.
- Generate reports.

**Reviewer / Senior Advisor**

Reviews calculations and final plans.

Permissions:
- View clients and scenarios.
- Review audit trails.
- Approve final plan outputs.
- Flag missing or questionable data.

**Admin**

Configures system-wide settings.

Permissions:
- Manage users.
- Manage static tables after business approval.
- Manage authentication and access.
- Configure reporting templates where supported.

**Read-Only Viewer**

Can view client plans and reports but cannot change source data or calculations.

**3. Full Workflow**

1. User creates a client.
2. User enters demographic data.
3. User enters pension portfolio data.
4. User enters employment history.
5. User enters grant history and explicit indexed values where required.
6. User enters actual capitalizations / commutations that consumed exemption.
7. User enters IDF/security-forces fixation inputs if relevant.
8. User enters current and projected income/expenses.
9. System validates required source data.
10. User runs Fixation calculation.
11. User reviews Fixation audit trail.
12. User builds one or more retirement scenarios.
13. Pension Engine calculates pension outputs for each scenario.
14. Tax Engine calculates tax impact.
15. Cashflow Engine calculates retirement cashflow.
16. User compares scenarios.
17. User selects a final plan.
18. System saves final scenario and engine outputs.
19. User generates final report/PDF if reporting is in scope.

**4. Required Screens**

V2 full system screens:

- Login / Access.
- Client List.
- Client Profile.
- Pension Portfolio.
- Employment History.
- Grants And Severance.
- Actual Capitalizations / Commutations.
- Fixation Calculation.
- Income And Expenses.
- Scenario Builder.
- Scenario Results.
- Scenario Comparison.
- Final Retirement Plan.
- Reports / Documents.
- Admin Settings.
- Audit / Calculation History.

**5. Screen Specifications**

**Login / Access**

Purpose: authenticate user and establish access permissions.

Data shown:
- Login status.
- Authentication errors.

Data entered:
- Credentials or external auth details, depending on chosen authentication strategy.

Actions:
- Sign in.
- Sign out.

Validations:
- Required credentials.
- Valid user.
- Active account.

What is saved:
- No business data.

What is calculated:
- Nothing.

Module owner:
- Authentication layer, not business modules.

Forbidden behaviors:
- No financial data access before authentication.
- No role bypass.
- No calculation logic.

---

**Client List**

Purpose: find, create, and open clients.

Data shown:
- Client name.
- Identifier.
- Status.
- Last updated date.
- Plan status.

Data entered:
- Search/filter terms.
- New client basic details.

Actions:
- Create client.
- Open client.
- Archive/deactivate client if permitted.

Validations:
- Required client identity fields.
- Duplicate detection rules, if defined.

What is saved:
- Client shell record.

What is calculated:
- Nothing financial.

Module owner:
- Data/API layer.

Forbidden behaviors:
- No retirement calculations.
- No hidden client defaults that affect calculations.

---

**Client Profile**

Purpose: maintain demographic and planning baseline data.

Data shown:
- Name.
- Birth date.
- Gender.
- Marital/family status if in scope.
- Retirement planning status.
- Pension start assumptions if stored at profile level.

Data entered:
- Demographic fields.
- Planning metadata.

Actions:
- Save profile.
- Validate profile completeness.

Validations:
- Required fields for downstream calculations.
- Valid dates.
- Valid gender/category values.
- No impossible dates.

What is saved:
- Client profile facts.

What is calculated:
- Eligibility may be displayed only if produced by an engine or validation service.
- No fixation calculation.

Module owner:
- Data layer for persistence.
- Eligibility responsibility must be locked before implementation.

Forbidden behaviors:
- No frontend-calculated eligibility as source of truth.
- No implicit fallback age rules unless explicitly locked.
- No calculation side effects.

---

**Pension Portfolio**

Purpose: capture pension assets and pension-income sources.

Data shown:
- Pension funds.
- Balances.
- Pension amounts.
- Tax treatment classification.
- Start dates.
- Source metadata.

Data entered:
- Pension fund/account data.
- Manual assumptions if required.
- Tax classification inputs.

Actions:
- Add pension source.
- Edit pension source.
- Remove pension source.
- Validate portfolio completeness.

Validations:
- Non-negative balances.
- Required fund identity fields.
- Required dates where used.
- Valid tax classification.
- No negative pension income unless explicitly modeled.

What is saved:
- Pension portfolio source data.

What is calculated:
- No final pension projection on this screen unless user explicitly runs Pension Engine.
- Any preview must be labeled non-authoritative unless saved engine output.

Module owner:
- Pension Engine owns pension calculations.
- Data layer owns pension facts.

Forbidden behaviors:
- No scenario mutation of base pension funds.
- No commutation side effects on source data unless user explicitly executes a real transaction.
- No frontend pension formulas as source of truth.

---

**Employment History**

Purpose: capture employment periods used by grants, severance, and planning context.

Data shown:
- Employers.
- Work start/end dates.
- Salary fields if in scope.
- Current employment status.

Data entered:
- Employer name.
- Employment dates.
- Salary details if needed.
- Current/future employment assumptions if in scope.

Actions:
- Add employment.
- Edit employment.
- Mark current employment.
- Validate dates.

Validations:
- Start date before end date.
- Required employer name.
- No invalid date formats.
- Business decision needed on overlapping employment.

What is saved:
- Employment records and assumptions.

What is calculated:
- Nothing final.

Module owner:
- Data layer.
- Engines consume employment context only as explicit inputs.

Forbidden behaviors:
- No grant impact calculation here.
- No hidden current-employer snapshot mutation.

---

**Grants And Severance**

Purpose: capture grants relevant to fixation and retirement planning.

Data shown:
- Grant amount.
- Grant date.
- Employment period.
- Indexed value if provided.
- Whether grant participates in fixation.
- Calculation audit after Fixation Engine runs.

Data entered:
- Grant nominal amount.
- Explicit indexed amount for deterministic V1/V2 calculation unless indexation responsibility is separately locked.
- Grant date.
- Work start/end date.
- Employer reference.

Actions:
- Add grant.
- Edit grant.
- Mark grant as excluded only through explicit business reason.
- Validate grants.
- Send grants to Fixation Engine.

Validations:
- Required amount.
- Required dates.
- Indexed amount required if engine does not perform indexation.
- Non-negative values.
- Work dates valid.

What is saved:
- Grant source data.
- Explicit indexed amount if required.
- No calculated impact unless saved as engine output.

What is calculated:
- Grant impact only by Fixation Engine.

Module owner:
- Fixation Engine.

Forbidden behaviors:
- No hidden nominal fallback.
- No frontend grant impact calculation.
- No duplicate router/service calculation.
- No API indexation call inside deterministic calculation unless explicitly approved.

---

**Actual Capitalizations / Commutations**

Purpose: capture actual historical capitalizations or commutations that consume exempt capital.

Data shown:
- Actual capitalization records.
- Amount.
- Date.
- Source.
- Whether included in fixation.
- Audit status.

Data entered:
- Capitalization/commutation amount.
- Date.
- Source description.
- Supporting reference.

Actions:
- Add actual capitalization.
- Edit actual capitalization.
- Include/exclude from fixation with explicit reason.

Validations:
- Amount required.
- Date required.
- Non-negative amount.
- Source required.
- No duplicate record if duplicate rules are defined.

What is saved:
- Actual capitalization facts.

What is calculated:
- Fixation Engine calculates impact on remaining exempt capital.

Module owner:
- Fixation Engine for exemption impact.
- Pension Engine only for pension-income effects of scenario commutations.

Forbidden behaviors:
- No inferring actual capitalizations from asset remarks.
- No regex parsing as authority.
- No scenario commutations mixed with actual historical usage.
- No mutation of saved fixation from scenario execution.

---

**Fixation Calculation**

Purpose: produce the authoritative fixation result.

Data shown:
- Eligibility context.
- Initial exempt capital.
- Grant impacts.
- Future grant reserve impact.
- Actual capitalization impact.
- IDF impact.
- Total impact.
- Remaining exempt capital.
- Exempt pension.
- Audit rows.
- Validation errors.

Data entered:
- Future grant reserve.
- IDF/security-forces inputs if applicable.
- Explicit selection of included actual capitalizations.
- Any required calculation parameters not already entered.

Actions:
- Validate inputs.
- Run Fixation Engine.
- Save fixation result.
- View audit.
- Lock result for scenario use.

Validations:
- Required deterministic inputs present.
- Cap/percentage present for eligibility year.
- No unknown-year fallback.
- No missing indexed grant values if required.
- IDF inputs complete when IDF applies.
- Actual capitalization inputs complete.

What is saved:
- Input snapshot.
- Engine output.
- Audit trail.
- Calculation version.
- Timestamp/user.

What is calculated:
- Full fixation result.

Module owner:
- Fixation Engine.

Forbidden behaviors:
- No frontend calculation authority.
- No LLM calculation.
- No save-time recalculation that changes result.
- No lazy recalculation on read.
- No hidden fallback to 2025 or 2028.
- No DB writes inside engine.

---

**Income And Expenses**

Purpose: capture non-pension income, expenses, and planning assumptions.

Data shown:
- Recurring expenses.
- Other income.
- One-time cashflows.
- Inflation/indexation assumptions if in scope.

Data entered:
- Expense items.
- Income items.
- Timing and recurrence.
- Tax classification hints if required.

Actions:
- Add income.
- Add expense.
- Edit assumptions.
- Validate timeline.

Validations:
- Non-negative values unless explicitly supported.
- Valid periods.
- Required frequency.
- Required tax classification where needed.

What is saved:
- Cashflow source assumptions.

What is calculated:
- Nothing final until Cashflow Engine runs.

Module owner:
- Cashflow Engine consumes these assumptions.
- Tax Engine handles tax treatment.

Forbidden behaviors:
- No manual override of engine-calculated tax.
- No hidden inflation/indexation defaults unless locked.

---

**Scenario Builder**

Purpose: define retirement plan alternatives.

Data shown:
- Available source data.
- Existing fixation result status.
- Pension assumptions.
- Planned commutations/withdrawals.
- Retirement date options.
- Scenario assumptions.

Data entered:
- Scenario name.
- Retirement date.
- Pension choices.
- Commutation choices.
- Withdrawal choices.
- Income/expense assumptions.

Actions:
- Create scenario.
- Duplicate scenario.
- Run scenario.
- Save scenario input.
- Compare scenarios.

Validations:
- Scenario must reference immutable source snapshot.
- Fixation result required where exemption is used.
- Commutation amount cannot exceed available source.
- Required assumptions complete.

What is saved:
- Scenario input bundle.
- References to source snapshots.
- User choices.

What is calculated:
- Nothing directly; it calls engines.

Module owner:
- Scenario Builder orchestrates.
- Engines calculate.

Forbidden behaviors:
- No direct financial formulas.
- No mutation of base client facts.
- No mutation of saved fixation result.
- No scenario side effects treated as actual facts.

---

**Scenario Results**

Purpose: display one scenario’s engine outputs.

Data shown:
- Fixation result used.
- Pension projection.
- Tax results.
- Cashflow timeline.
- Warnings and validation notes.
- Engine audit references.

Data entered:
- None, except optional scenario notes.

Actions:
- Save result.
- Rerun scenario from same input.
- Export result if reporting scope allows.

Validations:
- Output must match input version.
- Stale source-data warning if source changed.

What is saved:
- Engine outputs.
- Final scenario result snapshot.
- Notes.

What is calculated:
- Results are calculated by engines before display.

Module owner:
- Cashflow Engine produces final plan result.
- Tax/Pension/Fixation engines produce their domain outputs.

Forbidden behaviors:
- No recalculation in UI.
- No patching missing fields.
- No display layer altering persisted outputs.

---

**Scenario Comparison**

Purpose: compare multiple scenarios.

Data shown:
- Key outputs side by side.
- Net cashflow differences.
- Tax differences.
- Pension differences.
- Exemption usage differences.
- Risks/warnings.

Data entered:
- Scenario selection.
- Optional comparison notes.

Actions:
- Select final scenario.
- Archive scenario.
- Duplicate scenario.

Validations:
- Scenarios must be comparable over compatible periods, or mismatch must be shown.

What is saved:
- Selected final scenario marker.
- Comparison notes if entered.

What is calculated:
- Comparison summaries from existing scenario outputs.

Module owner:
- Orchestration/comparison service.
- No financial formulas beyond summarizing existing outputs.

Forbidden behaviors:
- No recalculating engine outputs.
- No changing scenario results through comparison.

---

**Final Retirement Plan**

Purpose: present the selected plan as the planner-approved final output.

Data shown:
- Client summary.
- Selected scenario.
- Fixation result.
- Pension plan.
- Tax projection.
- Cashflow projection.
- Key assumptions.
- Warnings.
- Audit references.

Data entered:
- Planner notes.
- Approval status.

Actions:
- Approve plan.
- Generate report.
- Reopen scenario if allowed.

Validations:
- Required engine outputs exist.
- Source snapshot locked.
- No unresolved critical validation errors.

What is saved:
- Final plan record.
- Approval metadata.
- Selected scenario reference.
- Final output snapshot.

What is calculated:
- Nothing new; final plan packages prior outputs.

Module owner:
- Orchestration layer packages.
- Engines remain source of calculation truth.

Forbidden behaviors:
- No final-plan-only calculations.
- No manual override without explicit override model and audit.
- No report generator changing numbers.

---

**Reports / Documents**

Purpose: produce human-readable output from saved calculation results.

Data shown:
- Available reports.
- Generation status.
- Report history.

Data entered:
- Report options if in scope.
- Notes/cover text if in scope.

Actions:
- Generate report.
- Download/view report.
- Regenerate from saved final plan.

Validations:
- Final plan exists.
- Required report data exists.

What is saved:
- Report metadata.
- Generated artifact reference if applicable.

What is calculated:
- Nothing. Reports render saved outputs.

Module owner:
- Presentation/reporting layer.

Forbidden behaviors:
- No calculation in PDF generation.
- No hardcoded pension caps.
- No recomputing exemption fields.
- No changing saved outputs.

---

**Admin Settings**

Purpose: manage system configuration and controlled business tables.

Data shown:
- Users.
- Roles.
- Static tables if admin-managed.
- System configuration.

Data entered:
- User/role changes.
- Approved table updates.
- Configuration changes.

Actions:
- Manage access.
- Update approved tables.
- View audit.

Validations:
- Permission checks.
- Business approval required for calculation tables.
- Effective date/version required for table changes.

What is saved:
- Settings.
- Table versions.
- Admin audit logs.

What is calculated:
- Nothing.

Module owner:
- Admin/data layer.

Forbidden behaviors:
- No ad hoc business rule changes without versioning.
- No untracked calculation parameter edits.

---

**Audit / Calculation History**

Purpose: show saved engine runs, inputs, outputs, and changes over time.

Data shown:
- Calculation version.
- Input snapshot.
- Output snapshot.
- User.
- Timestamp.
- Engine version.
- Validation results.

Data entered:
- Optional notes.

Actions:
- View run.
- Compare runs.
- Restore as scenario input if explicitly supported.

Validations:
- Read permissions.
- Snapshot integrity.

What is saved:
- Notes only, unless restoring creates a new scenario.

What is calculated:
- Nothing.

Module owner:
- Data/orchestration layer.

Forbidden behaviors:
- No lazy recalculation.
- No editing historical outputs.

**6. Core Business Modules**

- Fixation Engine.
- Pension Engine.
- Tax Engine.
- Cashflow Engine.
- Scenario Builder.
- Eligibility/Validation module, if separated by decision.
- Reporting Renderer, non-calculating.
- Data Snapshot service, non-calculating.

**7. Data Model Inventory**

Conceptual entities:

- User.
- Role.
- Client.
- Client Profile.
- Pension Source.
- Employment Record.
- Grant.
- Indexed Grant Value.
- Actual Capitalization / Actual Commutation.
- IDF Fixation Input.
- Fixation Calculation Input Snapshot.
- Fixation Calculation Result.
- Income Item.
- Expense Item.
- Tax Assumption.
- Scenario.
- Scenario Input Snapshot.
- Pension Engine Result.
- Tax Engine Result.
- Cashflow Engine Result.
- Scenario Result.
- Final Retirement Plan.
- Report Artifact.
- Calculation Audit Record.
- Business Table Version.

Important distinction:

- Actual historical facts and scenario assumptions must be separate.
- Engine input snapshots and engine outputs must be separate.
- Display artifacts must not be source data.

**8. Calculation Engines And Responsibilities**

**Fixation Engine**

Owns:
- Exempt capital entitlement.
- Grant impact.
- Future grant reserve impact.
- Actual capitalization impact.
- IDF impact.
- Remaining exempt capital.
- Exempt pension entitlement.
- Fixation audit rows.

Does not own:
- Pension projection.
- Tax.
- Cashflow.
- Persistence.
- CPI/API calls unless explicitly locked later.

**Pension Engine**

Owns:
- Pension-source projection.
- Pension income timeline.
- Pension impact of planned commutations.
- Pension output for tax and cashflow.

Does not own:
- Exempt capital usage.
- Grant impact.
- Tax calculation.
- Final plan packaging.

**Tax Engine**

Owns:
- Tax treatment and tax results.
- Net-of-tax income outputs.
- Tax summaries.

Does not own:
- Fixation entitlement.
- Pension projection.
- Scenario creation.

**Cashflow Engine**

Owns:
- Period-by-period retirement cashflow.
- Aggregated plan results.
- Net cashflow outputs.

Does not own:
- Domain-specific calculations from Fixation, Pension, or Tax.

**Scenario Builder**

Owns:
- Creating scenario input bundles.
- Sequencing engine calls.
- Comparing scenario outputs.

Does not own:
- Formula logic.
- Persistence side effects that alter base facts.
- Calculation authority.

**9. Source-Of-Truth Rules**

**Exempt Capital**

Only Fixation Engine output is authoritative.

**Exempt Pension**

Only Fixation Engine output is authoritative.

**Grant Impact**

Only Fixation Engine output is authoritative.

**Future Grant Reserve Impact**

Only Fixation Engine output is authoritative.

**Actual Capitalization Impact**

Only Fixation Engine output is authoritative, based on explicit actual capitalization inputs.

**Scenario Commutation Pension Effect**

Only Pension Engine output is authoritative.

**Scenario Exemption Usage**

Must be explicit input to Fixation Engine or scenario-specific fixation run. It must not mutate saved base fixation.

**IDF Impact**

Only Fixation Engine output is authoritative.

**Tax Result**

Only Tax Engine output is authoritative.

**Cashflow Result**

Only Cashflow Engine output is authoritative.

**Final Plan**

Final plan is a packaged snapshot of engine outputs, not a recalculation surface.

**10. Layer Separation**

**UI**

Responsibilities:
- Data entry.
- Display.
- User actions.
- Validation hints.
- Formatting.

Must not:
- Own financial calculations.
- Save computed values as authority unless returned by API from engines.
- Apply hidden defaults.

**API**

Responsibilities:
- Authentication.
- Request validation.
- Calling orchestration/services.
- Returning engine outputs.
- Error handling.

Must not:
- Contain formulas.
- Patch results.
- Duplicate engine logic.
- Mutate calculation outputs on read.

**Services**

Responsibilities:
- Application workflows.
- Data snapshot creation.
- Engine input preparation.
- Engine sequencing.
- Persistence coordination.

Must not:
- Duplicate formulas.
- Make hidden business decisions.
- Use DB side effects as calculation mechanism.

**Engines**

Responsibilities:
- Pure deterministic calculations.
- Domain-specific results.
- Audit rows.
- Explicit validation errors.

Must not:
- Read/write DB.
- Call external APIs.
- Call LLMs.
- Access UI state.
- Depend on hidden state.

**Database**

Responsibilities:
- Persist source data.
- Persist snapshots.
- Persist engine outputs.
- Persist audit and reports.

Must not:
- Be used as a calculation engine.
- Store ambiguous mixed actual/scenario state.
- Trigger hidden recalculations.

**11. Forbidden Patterns Based On Old System**

Strictly forbidden:

- Frontend calculations as source of truth.
- Duplicate calculations across frontend/backend/services.
- Hidden fallback to nominal indexation.
- Hidden fallback to 2025 caps.
- Hidden fallback to 2028 future values.
- LLM involvement in deterministic calculations.
- DB writes inside engines.
- Scenario mutation of saved calculation results.
- Lazy recalculation when reading saved data.
- Calculation inside API routers.
- Calculation inside document/PDF generation.
- Calculation inside prompt shaping.
- Regex parsing of remarks as financial authority.
- Inferring actual commutations from display assets.
- Mixing actual capitalizations and scenario commutations.
- Silent zero outputs for missing required data.
- Save endpoints changing business results outside engine output.
- Frontend and backend disagreeing on IDF impact.
- Multiple remaining exempt capital values in competing places.
- Reports hardcoding caps or exemption values.
- External API calls inside deterministic engine runs.

**12. Open Decisions To Lock Before Code**

**Frontend Strategy**

Must decide:
- Web app framework.
- State management strategy.
- Form strategy.
- Validation display strategy.
- Whether V1 is desktop-like planner workflow or simpler wizard.
- How audit trails are displayed.

Must lock before code because UI must not become a calculation layer.

**Backend Strategy**

Must decide:
- API style.
- Runtime/platform.
- Validation approach.
- Engine invocation pattern.
- Error contract.
- Snapshot/versioning approach.

Must lock before code because routers/services must not absorb business logic.

**Database Choice**

Must decide:
- Database engine.
- Migration strategy.
- JSON vs relational boundaries.
- Snapshot storage strategy.
- Audit retention strategy.

Must lock before code because actual/scenario/source/output separation depends on it.

**Hosting**

Must decide:
- Local-only, cloud, or hybrid.
- Single-tenant or multi-tenant.
- Backup policy.
- File/report storage.
- Environment separation.

Must lock before code because security, persistence, and reporting depend on it.

**Authentication**

Must decide:
- User/password, SSO, or other provider.
- Role model.
- Admin permissions.
- Audit identity requirements.

Must lock before code because financial client data requires access control.

**Reporting / PDF Scope**

Must decide:
- Whether reports are in V1.
- Which reports are required.
- Whether official forms are generated.
- Whether reports render saved outputs only.
- Report audit/version requirements.

Must lock before code because old reports contained calculation leakage.

**V1 Screen Scope**

Must decide:
- Minimum screens for first rebuild release.
- Whether V1 includes full scenario builder or fixation-first workflow.
- Whether admin screens are included.
- Whether report screens are included.

Must lock before code because workflow breadth affects data contracts.

**V1 Calculation Scope**

Must decide:
- Fixation only or full retirement plan.
- Which pension calculations are included.
- Which tax calculations are included.
- Whether cashflow is included.
- Whether IDF is included.
- Whether actual capitalizations are included.
- Whether indexation is external input or calculated from approved deterministic tables.

Must lock before code because calculation boundaries must be stable before implementation.