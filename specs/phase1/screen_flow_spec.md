**V1 Screen Flow Specification**

**1. Screen List In Workflow Order**

1. Client List
2. Create Client
3. Client Profile
4. Employment History
5. Grants
6. Actual Capitalizations
7. Fixation Parameters
8. Fixation Calculation Result
9. Fixation Audit / History

**2. Screen Specifications**

**1. Client List**

Purpose:
- Show existing clients and allow user to open or create a client.

Fields shown:
- Client name.
- Client status.
- Last updated date.
- Latest fixation status if available.
- Latest fixation calculation date if available.

Fields entered:
- Search/filter text, optional.

Buttons/actions:
- Create Client.
- Open Client.
- Refresh List.

Validations displayed:
- None for calculation.
- Search has no business validation.

API calls needed:
- List clients.
- Optional: get latest fixation summary per client if supported by API.

Save behavior:
- No save on this screen.

Navigation rules:
- `Create Client` goes to Create Client screen.
- `Open Client` goes to Client Profile.
- If client has missing profile data, show status but do not block opening.

Forbidden behaviors:
- No fixation calculation.
- No derived financial values calculated in UI.
- No stale result repair.

---

**2. Create Client**

Purpose:
- Create the root client record.

Fields shown:
- Empty client creation form.

Fields entered:
- Client display name.
- Optional status/notes if included in V1.

Buttons/actions:
- Save Client.
- Cancel.

Validations displayed:
- Client name required.
- Duplicate warning only if API supports it.
- Invalid characters/length only if contract defines it.

API calls needed:
- Create client.

Save behavior:
- On successful save, create client record only.
- No profile, grant, employment, or calculation result is created automatically unless explicitly entered later.

Navigation rules:
- After successful save, go to Client Profile.
- Cancel returns to Client List.

Forbidden behaviors:
- No default financial data creation.
- No automatic fixation run.
- No hidden profile assumptions.

---

**3. Client Profile**

Purpose:
- Enter demographic and eligibility-related source data.

Fields shown:
- Client display name.
- Birth date.
- Gender.
- Notes.
- Latest fixation status summary, read-only if available.

Fields entered:
- Display name.
- Birth date.
- Gender.
- Notes.

Buttons/actions:
- Save Profile.
- Continue to Employment.
- Back to Client List.

Validations displayed:
- Display name required.
- Birth date must be valid date if entered.
- Gender must be allowed value if entered.
- Missing profile fields shown as warnings only unless required by later workflow.

API calls needed:
- Get client.
- Update client/profile.
- Get latest fixation summary, optional.

Save behavior:
- Saves only client/profile source data.
- Does not modify existing fixation runs.

Navigation rules:
- User may continue even if optional fields are missing.
- If required fields for later validation are missing, later Fixation Parameters/Run screen blocks calculation.

Forbidden behaviors:
- UI must not calculate eligibility date as authoritative.
- UI must not calculate exemption year.
- UI must not update saved fixation result after profile edit.
- UI must not silently mark old calculation as recalculated.

---

**4. Employment History**

Purpose:
- Enter work periods used by grants and planning context.

Fields shown:
- Existing employment records.
- Employer name.
- Work start date.
- Work end date.
- Current employment indicator.
- Notes.

Fields entered:
- Employer name.
- Work start date.
- Work end date.
- Current employment indicator.
- Notes.

Buttons/actions:
- Add Employment.
- Edit Employment.
- Delete Employment.
- Save Employment.
- Continue to Grants.
- Back to Profile.

Validations displayed:
- Employer name required.
- Start date required.
- End date required unless current employment is allowed.
- End date must be after start date when present.
- Delete confirmation if record is referenced by a grant.

API calls needed:
- List employment records.
- Create employment record.
- Update employment record.
- Delete employment record.

Save behavior:
- Saves employment source data only.
- Does not update grant records automatically unless user explicitly edits grants.
- Does not update previous calculation snapshots.

Navigation rules:
- Continue to Grants always allowed.
- If no employment records exist, Grants screen can still allow manual grant work dates.

Forbidden behaviors:
- No work-ratio calculation in UI.
- No grant impact calculation.
- No mutation of saved fixation runs.

---

**5. Grants**

Purpose:
- Enter grants used by Fixation Engine.

Fields shown:
- Grant list.
- Employer/source label.
- Nominal amount.
- Indexed amount.
- Grant date.
- Work start date.
- Work end date.
- Linked employment record if supported.
- Notes.
- Latest saved calculation impact shown only from saved Fixation Result, if available.

Fields entered:
- Employer/source label.
- Nominal amount, optional.
- Indexed amount, required for calculation.
- Grant date.
- Work start date.
- Work end date.
- Notes.

Buttons/actions:
- Add Grant.
- Edit Grant.
- Delete Grant.
- Save Grant.
- Continue to Actual Capitalizations.
- Back to Employment.

Validations displayed:
- Indexed amount required.
- Indexed amount must be non-negative.
- Nominal amount must be non-negative if entered.
- Grant date required.
- Work start date required.
- Work end date required.
- Work end date must be after work start date.
- Employer/source label optional unless business rule later requires it.

API calls needed:
- List grants.
- Create grant.
- Update grant.
- Delete grant.

Save behavior:
- Saves grant source data.
- Does not save calculated impact.
- Does not calculate indexation.
- Existing fixation results remain immutable.

Navigation rules:
- User may continue with zero grants.
- User may not run calculation later if any included grant is invalid.

Forbidden behaviors:
- UI must not calculate indexed amount.
- UI must not call CPI/indexation services.
- UI must not calculate 15-year exclusion.
- UI must not calculate 32-year ratio.
- UI must not calculate grant impact.
- UI must not fallback from missing indexed amount to nominal amount.

---

**6. Actual Capitalizations**

Purpose:
- Enter actual historical capitalizations/commutations that consume exempt capital.

Fields shown:
- Existing actual capitalization records.
- Amount.
- Capitalization date.
- Source label.
- Notes.

Fields entered:
- Amount.
- Capitalization date.
- Source label.
- Notes.

Buttons/actions:
- Add Capitalization.
- Edit Capitalization.
- Delete Capitalization.
- Save Capitalization.
- Continue to Fixation Parameters.
- Back to Grants.

Validations displayed:
- Amount required.
- Amount must be non-negative.
- Date required.
- Date must be valid.
- Source label optional unless later locked as required.

API calls needed:
- List actual capitalizations.
- Create actual capitalization.
- Update actual capitalization.
- Delete actual capitalization.

Save behavior:
- Saves actual capitalization source data only.
- Does not mutate saved fixation results.
- Does not store scenario commutations.

Navigation rules:
- User may continue with zero actual capitalizations.
- User may not include invalid capitalization records in calculation.

Forbidden behaviors:
- UI must not infer actual capitalizations from pension assets.
- UI must not parse remarks strings.
- UI must not mix scenario commutations into actual capitalization list.
- UI must not calculate capitalization impact.

---

**7. Fixation Parameters**

Purpose:
- Assemble explicit deterministic fixation parameters and run validation/calculation.

Fields shown:
- Eligibility date.
- Eligibility year.
- Monthly cap.
- Exemption percentage.
- Capital multiplier.
- Future grant reserved.
- IDF section, enabled/disabled.
- IDF fields if applicable.
- Summary of grants count.
- Summary of actual capitalization count.
- Current input readiness status.

Fields entered:
- Eligibility date.
- Eligibility year.
- Monthly cap.
- Exemption percentage.
- Capital multiplier.
- Future grant reserved.
- IDF applicable yes/no.
- IDF reduction amount.
- IDF original commutation percent.
- IDF current commutation percent.
- IDF commutation date.
- IDF promoter age date.
- IDF source label.

Buttons/actions:
- Validate Inputs.
- Run Calculation.
- Save Draft Parameters only if V1 supports draft source persistence.
- Back to Actual Capitalizations.
- Continue to Result after successful calculation.

Validations displayed:
- Eligibility date required.
- Eligibility year required.
- Monthly cap required and greater than zero.
- Exemption percentage required and between 0 and 1.
- Capital multiplier required and greater than zero.
- Future grant reserved required and non-negative.
- If IDF applicable: all IDF fields required.
- IDF percent values must be greater than zero.
- IDF dates must be valid.
- All grants must have valid required fields.
- All actual capitalizations must have valid required fields.

API calls needed:
- Get client source data needed for calculation.
- Validate fixation input.
- Calculate fixation.

Save behavior:
- Running calculation does not automatically create immutable saved result unless user confirms Save Result on Result screen, unless V1 explicitly chooses calculate-and-save together.
- If draft parameters are saved, they are source/input-prep data only, not calculation output.

Navigation rules:
- User cannot go to Result without successful calculation.
- User can go back and edit source data.
- Editing source data after a calculation requires rerun before saving a new result.

Forbidden behaviors:
- UI must not calculate initial exempt capital.
- UI must not calculate IDF impact.
- UI must not calculate future grant impact.
- UI must not calculate total impact.
- UI must not fill missing cap or percentage from hardcoded fallback.
- UI must not hide validation errors.
- UI must not continue calculation with missing required inputs.

---

**8. Fixation Calculation Result**

Purpose:
- Display engine output and allow user to save immutable calculation result.

Fields shown:
- Calculation status.
- Eligibility date/year.
- Monthly cap.
- Exemption percentage.
- Initial exempt capital.
- Grant impact total.
- Future grant reserved.
- Future grant impact.
- Actual capitalization impact.
- IDF impact.
- Total impact.
- Remaining exempt capital.
- Monthly exempt pension.
- Capital exemption percentage.
- Pension exemption percentage.
- Validation errors if calculation failed.
- Audit preview.

Fields entered:
- Optional user notes if supported.

Buttons/actions:
- Save Result.
- Discard Result.
- Back to Fixation Parameters.
- View Full Audit.
- Recalculate if inputs changed.

Validations displayed:
- If status is validation failed, show blocking errors.
- If source data changed since calculation, show stale unsaved calculation warning.
- Save disabled unless calculation status is success.

API calls needed:
- Calculate fixation, already called from previous screen or called here.
- Save fixation result.
- Get saved fixation result after save.

Save behavior:
- Saves exact engine input snapshot.
- Saves exact engine output.
- Saves audit rows.
- Saves metadata.
- Does not modify previous runs.
- New save creates new immutable run.

Navigation rules:
- After save, user may go to Audit/History.
- If user goes back and changes inputs, current unsaved result becomes stale.
- Saved result is read-only.

Forbidden behaviors:
- UI must not alter engine output before saving.
- UI must not recalculate display fields.
- UI must not patch missing fields.
- UI must not overwrite previous run.
- UI must not save frontend-computed values.

---

**9. Fixation Audit / History**

Purpose:
- Show saved calculation runs and audit evidence.

Fields shown:
- Calculation run list.
- Run date.
- Run status.
- Calculation version.
- Created by if available.
- Latest marker.
- Result summary.
- Audit rows for selected run.
- Input snapshot view if supported.
- Validation errors for failed runs if persisted.

Fields entered:
- Optional notes only if allowed.

Buttons/actions:
- Select Run.
- View Audit Rows.
- View Input Snapshot.
- Mark as latest only if V1 supports explicit run selection.
- Return to Fixation Parameters.
- Start New Calculation.

Validations displayed:
- None for calculation.
- If selected run is not latest, show non-latest indicator.
- If source data changed after run, show stale indicator only if supported.

API calls needed:
- Get fixation history.
- Get fixation run by id.
- Get latest fixation result.

Save behavior:
- No calculation values saved.
- Optional notes/metadata only if supported.
- Historical outputs remain immutable.

Navigation rules:
- From latest result, user can start new calculation.
- Opening old run is read-only.
- Editing source data happens on source screens, not inside history.

Forbidden behaviors:
- No lazy recalculation.
- No editing historical outputs.
- No fixing missing fields on read.
- No report-style recomputation.
- No comparison calculations beyond displaying saved values.

**3. Full User Flow**

1. User opens Client List.
2. User selects Create Client.
3. User enters client display name.
4. System creates client.
5. User lands on Client Profile.
6. User enters profile fields.
7. User saves profile.
8. User continues to Employment History.
9. User enters employment records or skips if not needed.
10. User continues to Grants.
11. User enters grants with explicit indexed amounts and dates.
12. User continues to Actual Capitalizations.
13. User enters actual historical capitalizations/commutations or leaves empty.
14. User continues to Fixation Parameters.
15. User enters eligibility date/year, monthly cap, exemption percentage, multiplier, future grant reserve, and IDF inputs if applicable.
16. User selects Validate Inputs or Run Calculation.
17. UI sends full deterministic input to API.
18. API returns validation errors or successful engine result.
19. If validation fails, UI displays errors and blocks saving.
20. If calculation succeeds, user views Fixation Calculation Result.
21. User reviews result summary.
22. User opens audit preview/full audit if needed.
23. User selects Save Result.
24. System saves immutable run, input snapshot, result, audit rows, and metadata.
25. User views Audit / History.
26. User may start a new calculation later, which creates a new run.

**4. Error States**

Client/API errors:
- Client not found.
- Save failed.
- Network/server error.
- Unauthorized if auth exists.

Validation errors:
- Missing eligibility date.
- Missing eligibility year.
- Missing monthly cap.
- Missing exemption percentage.
- Missing capital multiplier.
- Missing indexed grant amount.
- Invalid grant dates.
- Invalid actual capitalization amount/date.
- Missing IDF fields when IDF is applicable.
- Invalid IDF percent values.
- Invalid IDF date range.

Calculation errors:
- Engine returns `validation_failed`.
- Engine contract mismatch.
- Calculation unavailable due to invalid input.

Display rules:
- Errors must show field path where possible.
- Save Result must be disabled on validation failure.
- UI must not replace errors with fallback values.
- UI must not continue with partial result.

**5. Empty States**

Client List:
- “No clients yet” with Create Client action.

Employment History:
- “No employment records entered” with Add Employment action.

Grants:
- “No grants entered” with Add Grant action.
- Zero grants is valid.

Actual Capitalizations:
- “No actual capitalizations entered” with Add Capitalization action.
- Zero actual capitalizations is valid.

Fixation History:
- “No fixation calculations saved yet” with Start Calculation action.

Fixation Result:
- No result shown until calculation succeeds or validation errors are returned.

**6. Read-Only States After Saved Calculation**

Saved calculation run:
- All result fields read-only.
- Audit rows read-only.
- Input snapshot read-only.
- Validation errors read-only.
- Calculation metadata read-only.

Source data after saved calculation:
- May remain editable.
- Editing source data must not change old saved run.
- If stale indicator is supported, edited source data may mark prior result as stale, but must not recalculate it.

History:
- Old runs read-only.
- Latest run read-only.
- New calculation creates new run.

**7. What The UI Must Never Calculate**

The UI must never calculate:

- Initial exempt capital.
- Monthly cap lookup.
- Exemption percentage lookup.
- Grant 15-year exclusion.
- 32-year work ratio.
- Limited indexed grant amount.
- Grant impact.
- Future grant impact.
- Actual capitalization impact.
- IDF base reduction.
- IDF monthly reduction cap.
- IDF overlap months.
- IDF impact.
- Total impact.
- Remaining exempt capital.
- Monthly exempt pension.
- Capital exemption percentage.
- Pension exemption percentage.
- Audit row amounts.
- Validation substitutions or fallbacks.
- Any saved result field.

The UI may only:
- Collect inputs.
- Display API/engine outputs.
- Display validation errors.
- Format numbers and dates for presentation without changing stored/calculated values.