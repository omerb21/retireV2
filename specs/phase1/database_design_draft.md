**V1 Database Design Draft**

Scope: V1 fixation only. This is a conceptual relational model, not SQL, ORM, or migration design.

**1. Required Tables**

Minimal V1 tables:

1. `clients`
2. `client_profiles`
3. `employment_records`
4. `grants`
5. `actual_capitalizations`
6. `fixation_runs`
7. `fixation_input_snapshots`
8. `fixation_results`
9. `fixation_audit_rows`
10. `fixation_validation_errors`

Optional only if authentication is included in V1:
- `users`

**2. Table Details**

**clients**

Purpose: root client record.

Fields:
- `client_id`: stable identifier, required.
- `display_name`: text, required.
- `status`: enum/conceptual status, required.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- One client has one `client_profile`.
- One client has many `employment_records`.
- One client has many `grants`.
- One client has many `actual_capitalizations`.
- One client has many `fixation_runs`.

Unique constraints:
- `client_id` unique.
- Optional later: unique external identifier if one is introduced.

What writes it:
- Client creation/update API.

What reads it:
- Client list.
- Client profile screen.
- Fixation orchestration.

---

**client_profiles**

Purpose: V1 demographic and eligibility-related source data.

Fields:
- `client_profile_id`: stable identifier, required.
- `client_id`: required relationship to `clients`.
- `birth_date`: date, optional unless V1 validation requires it for user workflow.
- `gender`: controlled value, optional unless V1 validation requires it for user workflow.
- `notes`: text, optional.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- Belongs to one `client`.

Unique constraints:
- One profile per client.

What writes it:
- Client profile screen/API.

What reads it:
- Client profile screen.
- Fixation orchestration if eligibility data is displayed or used outside engine input assembly.

Important:
- `client_profiles` must not store calculated eligibility as authoritative unless a later decision explicitly adds that.

---

**employment_records**

Purpose: source employment periods used for grants and planner context.

Fields:
- `employment_record_id`: stable identifier, required.
- `client_id`: required relationship to `clients`.
- `employer_name`: text, required.
- `work_start_date`: date, required.
- `work_end_date`: date, optional if current employment is allowed; required when linked to a V1 grant.
- `is_current`: boolean, required.
- `notes`: text, optional.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- Belongs to one `client`.
- May be referenced by `grants`.

Unique constraints:
- None required for V1.
- Optional later duplicate prevention: same client + employer + start date.

What writes it:
- Employment screen/API.

What reads it:
- Employment screen.
- Grants screen.
- Fixation input assembly.

---

**grants**

Purpose: source grant records used by Fixation Engine.

Fields:
- `grant_id`: stable identifier, required.
- `client_id`: required relationship to `clients`.
- `employment_record_id`: optional relationship to `employment_records`.
- `employer_name`: text, optional if linked employment supplies it.
- `nominal_amount`: money/decimal, optional.
- `indexed_amount`: money/decimal, required for V1 fixation.
- `grant_date`: date, required.
- `work_start_date`: date, required.
- `work_end_date`: date, required.
- `notes`: text, optional.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- Belongs to one `client`.
- Optionally references one `employment_record`.

Unique constraints:
- `grant_id` unique.
- Optional later duplicate prevention: same client + grant date + indexed amount + employer.

What writes it:
- Grants screen/API.

What reads it:
- Grants screen.
- Fixation input assembly.
- Fixation audit display through references only; audit itself comes from engine output.

Important:
- No grant impact field as source data.
- No indexation fallback field.
- No “calculated by frontend” field.

---

**actual_capitalizations**

Purpose: source records for actual historical capitalizations/commutations that consume exempt capital.

Fields:
- `capitalization_id`: stable identifier, required.
- `client_id`: required relationship to `clients`.
- `amount`: money/decimal, required.
- `capitalization_date`: date, required.
- `source_label`: text, optional.
- `notes`: text, optional.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- Belongs to one `client`.

Unique constraints:
- `capitalization_id` unique.
- Optional later duplicate prevention: same client + date + amount + source label.

What writes it:
- Actual Capitalizations screen/API.

What reads it:
- Actual Capitalizations screen.
- Fixation input assembly.

Important:
- This table is for actual historical exemption usage only.
- Scenario commutations must not be stored here in V1.

---

**fixation_runs**

Purpose: calculation run metadata and immutable run identity.

Fields:
- `fixation_run_id`: stable identifier, required.
- `client_id`: required relationship to `clients`.
- `calculation_version`: text, required.
- `status`: enum, required. Values conceptually: `success`, `validation_failed`.
- `created_at`: datetime, required.
- `created_by`: user/reference text, optional depending on auth decision.
- `source_data_version_label`: text, optional.
- `is_latest`: boolean, required.
- `notes`: text, optional.

Relationships:
- Belongs to one `client`.
- Has one `fixation_input_snapshot`.
- Has zero or one `fixation_result`, depending on validation failure handling.
- Has many `fixation_audit_rows`.
- Has many `fixation_validation_errors`.

Unique constraints:
- `fixation_run_id` unique.
- At most one latest successful/current run per client, if `is_latest` is used.

What writes it:
- Fixation calculate/save API.

What reads it:
- Fixation result screen.
- Fixation history screen.
- Future scenario orchestration.

Important:
- A run is immutable after creation, except administrative metadata explicitly allowed later.
- Recalculation creates a new run.

---

**fixation_input_snapshots**

Purpose: immutable snapshot of the exact `FixationInput` sent to the engine.

Fields:
- `fixation_input_snapshot_id`: stable identifier, required.
- `fixation_run_id`: required relationship to `fixation_runs`.
- `input_contract_version`: text, required.
- `input_payload`: structured object/JSON conceptually, required.
- `created_at`: datetime, required.

Relationships:
- Belongs to one `fixation_run`.

Unique constraints:
- One input snapshot per fixation run.

What writes it:
- Fixation calculate/save API after assembling engine input.

What reads it:
- Fixation history.
- Audit/review.
- Future regression/debug tools.

Important:
- Snapshot must contain all required deterministic inputs.
- Snapshot must not be rebuilt from current source data after the run.

---

**fixation_results**

Purpose: immutable saved `FixationResult` output from the engine.

Fields:
- `fixation_result_id`: stable identifier, required.
- `fixation_run_id`: required relationship to `fixation_runs`.
- `result_contract_version`: text, required.
- `initial_exempt_capital`: money/decimal, required on successful run.
- `grant_impact_total`: money/decimal, required on successful run.
- `future_grant_reserved`: money/decimal, required on successful run.
- `future_grant_impact`: money/decimal, required on successful run.
- `actual_capitalization_impact`: money/decimal, required on successful run.
- `idf_impact`: money/decimal, required on successful run.
- `total_impact`: money/decimal, required on successful run.
- `remaining_exempt_capital`: money/decimal, required on successful run.
- `monthly_exempt_pension`: money/decimal, required on successful run.
- `capital_exemption_percentage`: decimal, required on successful run.
- `pension_exemption_percentage`: decimal, required on successful run.
- `result_payload`: structured object/JSON conceptually, required.
- `created_at`: datetime, required.

Relationships:
- Belongs to one `fixation_run`.

Unique constraints:
- One result per successful fixation run.

What writes it:
- Fixation calculate/save API using engine output only.

What reads it:
- Fixation result screen.
- Fixation history.
- Future scenario/cashflow modules.

Important:
- Scalar fields are duplicated from `result_payload` only for querying/display convenience.
- If scalar and payload ever differ, the run is invalid; implementation must prevent this.
- No UI or API may patch these values.

---

**fixation_audit_rows**

Purpose: immutable normalized audit rows returned by the engine.

Fields:
- `fixation_audit_row_id`: stable identifier, required.
- `fixation_run_id`: required relationship to `fixation_runs`.
- `row_order`: integer, required.
- `category`: enum, required.
- `source_id`: text, optional.
- `label`: text, required.
- `input_amount`: money/decimal, optional.
- `output_amount`: money/decimal, required.
- `impact_amount`: money/decimal, required.
- `details_payload`: structured object/JSON conceptually, required.

Relationships:
- Belongs to one `fixation_run`.

Unique constraints:
- Unique `fixation_run_id + row_order`.
- Optional: unique `fixation_run_id + row_id` if engine supplies row ids.

What writes it:
- Fixation calculate/save API using engine audit rows only.

What reads it:
- Fixation result/audit screen.
- History/review.

Important:
- Audit rows are not source data.
- Audit rows must not be recalculated on read.

---

**fixation_validation_errors**

Purpose: immutable validation errors returned by engine/contract validation for failed runs.

Fields:
- `fixation_validation_error_id`: stable identifier, required.
- `fixation_run_id`: required relationship to `fixation_runs`.
- `error_order`: integer, required.
- `code`: text, required.
- `path`: text, required.
- `message`: text, required.
- `severity`: enum, required.
- `source_id`: text, optional.

Relationships:
- Belongs to one `fixation_run`.

Unique constraints:
- Unique `fixation_run_id + error_order`.

What writes it:
- Fixation validate/calculate API.

What reads it:
- Fixation calculation screen.
- Fixation history.

Important:
- Validation errors are stored for failed runs if the product decision is to keep failed calculation history.
- If failed runs are not persisted in V1, this table may be deferred.

---

**users** Optional For V1

Purpose: minimal identity for audit metadata if authentication is included.

Fields:
- `user_id`: stable identifier, required.
- `display_name`: text, required.
- `email`: text, optional depending on auth choice.
- `role`: controlled value, required.
- `status`: controlled value, required.
- `created_at`: datetime, required.
- `updated_at`: datetime, required.

Relationships:
- May be referenced by `fixation_runs.created_by`.

Unique constraints:
- `user_id` unique.
- `email` unique if email auth is used.

What writes it:
- Auth/admin process.

What reads it:
- Audit/history views.

**3. Required Separation**

**Source Data**

Tables:
- `clients`
- `client_profiles`
- `employment_records`
- `grants`
- `actual_capitalizations`

Rules:
- Editable by user before calculation.
- Not overwritten by engine.
- Does not contain calculated impact authority.

**Input Snapshots**

Table:
- `fixation_input_snapshots`

Rules:
- Immutable.
- Contains exact engine input.
- Created at calculation time.
- Never rebuilt from current source data.

**Engine Outputs**

Table:
- `fixation_results`

Rules:
- Immutable.
- Written only from engine output.
- Not patched by API/UI/reporting.
- Recalculation creates a new result.

**Audit Rows**

Table:
- `fixation_audit_rows`

Rules:
- Immutable.
- Written only from engine output.
- Displayed as evidence.
- Not used as source data.

**Metadata**

Tables/fields:
- `fixation_runs`
- `created_at`
- `created_by`
- `calculation_version`
- `status`
- `is_latest`
- optional `users`

Rules:
- Metadata may support filtering/history.
- Metadata must not change calculation values.

**4. What Must NOT Be Stored In V1**

Do not store:

- Pension Engine outputs.
- Tax Engine outputs.
- Cashflow Engine outputs.
- Scenario comparison data.
- Scenario commutation mutation state.
- Report/PDF artifacts.
- LLM prompts.
- LLM responses.
- Chat history.
- Prompt-shaped calculation summaries.
- Frontend-calculated remaining exemption.
- Frontend-calculated grant impact.
- Frontend-calculated IDF impact.
- Hidden fallback year.
- Hidden fallback cap.
- Hidden fallback indexed amount.
- CBS/API response cache unless separately approved later.
- Parsed financial authority from remarks strings.
- Duplicate competing `remaining_exempt_capital` outside `fixation_results`.
- Mutable “current fixation result” that is overwritten without run history.

**5. Immutability / Versioning Rules**

- Every calculation creates a new `fixation_run`.
- Every run stores one immutable input snapshot.
- Every successful run stores one immutable result.
- Audit rows are immutable.
- Validation errors are immutable.
- Editing source data after a run does not change that run.
- Re-running after source data changes creates a new run.
- The latest run may be marked by metadata, but previous runs remain unchanged.
- Calculation version must be stored with every run.
- Contract version must be stored with every input snapshot and result.
- No lazy recalculation on read.
- No save endpoint may alter a prior engine result.
- If a run must be invalidated, store metadata/status; do not rewrite its numbers.

**6. Open Database Decisions To Lock Later**

- Final database technology: PostgreSQL, SQLite, or MySQL.
- Identifier strategy: UUID, integer sequence, or external ids.
- Money precision: decimal scale and rounding storage rules.
- JSON strategy: store full contract payload as JSON, normalized columns, or both.
- Failed-run persistence: whether validation-failed runs are stored in V1.
- `is_latest` strategy: boolean flag, query latest by timestamp, or separate pointer.
- User/auth tables: included in V1 or deferred.
- Soft delete vs hard delete for source data.
- Audit retention policy.
- Backup/export requirements.
- Multi-client search fields.
- Concurrency/version checks for editing source data.
- Whether source data edits after a saved run should mark latest run as stale.
- Whether business table versions are stored in V1 or only contract values are stored in snapshots.