**Fixation V1 Domain Contracts**

All dates are ISO strings: `YYYY-MM-DD`.  
All money fields are numbers in ILS.  
All percentages are decimal values unless explicitly named as “percent points”.  
No field depends on DB, UI, external API, hidden state, or fallback behavior.

**1. FixationInput Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `calculation_id` | string | optional | Caller-provided stable id for tracing this calculation. | If present, non-empty string. |
| `calculation_version` | string | required | Business contract version used for this calculation. | Must be non-empty. |
| `eligibility_date` | date string | required | Effective eligibility date used by fixation. | Valid ISO date. |
| `eligibility_year` | integer | required | Year used for cap and exemption percentage. | Must match `eligibility_date` year unless explicitly approved before implementation. |
| `monthly_cap` | number | required | Monthly exempt pension cap for eligibility year. | Must be greater than `0`. No fallback allowed. |
| `exemption_percentage` | number | required | Statutory exemption percentage for eligibility year. | Must be `>= 0` and `<= 1`. No fallback allowed. |
| `capital_multiplier` | number | required | Capital multiplier used to derive exempt capital entitlement. | Must be greater than `0`. For V1 expected value is explicit, not implicit. |
| `grants` | `GrantInput[]` | required | Grants participating in fixation evaluation. Empty array allowed. | Must be array. Every item must be valid. |
| `future_grant_reserved` | number | required | Future grant amount reserved for future exemption usage. | Must be `>= 0`. |
| `actual_capitalizations` | `ActualCapitalizationInput[]` | required | Actual historical capitalizations/commutations that consume exempt capital. Empty array allowed. | Must be array. Every item must be valid. |
| `idf` | `IDFInput \| null` | required | IDF/security-forces fixation input. `null` means not applicable. | If not null, must be fully valid. |
| `metadata` | object | optional | Non-calculation trace metadata. | Must not affect calculation. |

Forbidden in `FixationInput`:
- DB ids as required calculation authority.
- UI-only fields.
- Precomputed frontend results.
- External API response placeholders.
- “Use latest cap” flags.
- “Fallback year” fields.
- Any missing-value fallback indicator.

**2. GrantInput Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `grant_id` | string | required | Stable caller-provided grant identifier for audit rows. | Non-empty string. |
| `employer_name` | string | optional | Human-readable employer/source label. | If present, non-empty after trim. |
| `nominal_amount` | number | optional | Original nominal grant amount, for audit/display only. | If present, must be `>= 0`. Must not replace `indexed_amount`. |
| `indexed_amount` | number | required | Explicit deterministic indexed grant amount used by engine. | Must be `>= 0`. No indexation call or nominal fallback allowed. |
| `grant_date` | date string | required | Date used for 15-year rule evaluation. | Valid ISO date. |
| `work_start_date` | date string | required | Employment start date used for work-ratio evaluation. | Valid ISO date. Must be before `work_end_date`. |
| `work_end_date` | date string | required | Employment end date used for work-ratio evaluation. | Valid ISO date. Must be after `work_start_date`. |

Forbidden in `GrantInput`:
- Missing `indexed_amount`.
- “Index this automatically” flag.
- CPI source/API fields.
- Precomputed grant impact from UI.
- Hidden exclusion flags without date evidence.

**3. ActualCapitalizationInput Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `capitalization_id` | string | required | Stable caller-provided id for audit rows. | Non-empty string. |
| `amount` | number | required | Actual exemption-consuming capitalization/commutation amount. | Must be `>= 0`. |
| `capitalization_date` | date string | required | Date of actual capitalization/commutation. | Valid ISO date. |
| `source_label` | string | optional | Human-readable source description. | If present, non-empty after trim. |
| `notes` | string | optional | Non-calculation notes. | Must not affect calculation. |

Forbidden in `ActualCapitalizationInput`:
- Parsing from remarks strings.
- Scenario commutation asset references.
- Tax-treatment inference.
- DB asset fields as calculation authority.
- Precomputed remaining exemption.

**4. IDFInput Schema**

`idf` is either `null` or a complete object.

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `idf_id` | string | required | Stable caller-provided id for audit rows. | Non-empty string. |
| `reduction_amount` | number | required | Monthly reduction amount used for IDF impact. | Must be greater than `0`. |
| `original_commutation_percent` | number | required | Original commutation percent points. | Must be greater than `0`. |
| `current_commutation_percent` | number | required | Current commutation percent points. | Must be greater than `0`. |
| `commutation_date` | date string | required | Date of relevant commutation. | Valid ISO date. |
| `promoter_age_date` | date string | required | Date used as IDF overlap end. | Valid ISO date. |
| `source_label` | string | optional | Human-readable IDF/source label. | If present, non-empty after trim. |

IDF validation:
- `promoter_age_date` must be after the later of `commutation_date` and eligibility date.
- Percent fields are percent-point numbers, e.g. `25`, not `0.25`.
- Parent `monthly_cap` is used; no duplicate monthly cap inside `IDFInput`.

IDF overlap lock (approved):

- `overlap_start` = later of `commutation_date` and `eligibility_date`
- `overlap_end` = `promoter_age_date`

- `overlap_end` must be strictly after `overlap_start`

- `overlap_months` = number of full calendar months between `overlap_start` and `overlap_end`
- Partial months are not counted

- `idf_impact` = `monthly_reduction_for_calc * overlap_months`

- No intermediate rounding is performed.
- Final monetary outputs are rounded only at final result field level to 2 decimal places.

Forbidden in `IDFInput`:
- Frontend-computed IDF impact.
- Display-only IDF fields as authority.
- Missing promoter age date.
- Mixed percent formats.

**5. FixationResult Schema**

| Field | Type | Required | Description |
|---|---:|---:|---|
| `calculation_id` | string \| null | required | Echo of input id, or null if not supplied. |
| `calculation_version` | string | required | Version used. |
| `status` | `"success" \| "validation_failed"` | required | Calculation status. |
| `validation_errors` | `ValidationError[]` | required | Empty on success. |
| `eligibility_date` | date string | required | Echoed effective eligibility date. |
| `eligibility_year` | integer | required | Echoed eligibility year. |
| `monthly_cap` | number | required | Echoed monthly cap. |
| `exemption_percentage` | number | required | Echoed exemption percentage. |
| `capital_multiplier` | number | required | Echoed multiplier. |
| `initial_exempt_capital` | number | required | Initial exempt capital entitlement. |
| `grant_impact_total` | number | required | Total impact from grants. |
| `future_grant_reserved` | number | required | Echoed future grant reserve. |
| `future_grant_impact` | number | required | Impact from future grant reserve. |
| `actual_capitalization_impact` | number | required | Total impact from actual capitalizations. |
| `idf_impact` | number | required | IDF impact; `0` if not applicable. |
| `total_impact` | number | required | Total impact from all categories. |
| `remaining_exempt_capital` | number | required | Remaining exempt capital after impacts. |
| `monthly_exempt_pension` | number | required | Monthly exempt pension amount. |
| `capital_exemption_percentage` | number | required | Remaining capital as percentage of initial exempt capital. |
| `pension_exemption_percentage` | number | required | Pension exemption percentage derived by engine. |
| `grant_results` | `GrantResult[]` | required | Deterministic per-grant result summaries. |
| `actual_capitalization_results` | `ActualCapitalizationResult[]` | required | Deterministic per-capitalization result summaries. |
| `idf_result` | `IDFResult \| null` | required | Deterministic IDF result summary, or null. |
| `audit_rows` | `AuditRow[]` | required | Full calculation audit trail. |

Result rules:
- On `validation_failed`, all numeric result fields must be omitted; only echo fields, status, and validation_errors are present.
- On `success`, all result fields above must be present.
- No result field may be patched by API, UI, persistence, or report generation.

Zero entitlement lock (approved):

If `initial_exempt_capital == 0`:
- `remaining_exempt_capital = 0`
- `monthly_exempt_pension = 0`
- `capital_exemption_percentage = 0`
- `pension_exemption_percentage = 0`

- No division is performed in this case.
- This is a deterministic output rule, not fallback behavior.

**6. AuditRow Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `row_id` | string | required | Stable row id within result. | Non-empty. |
| `category` | enum | required | Audit category. | Allowed: `initial_entitlement`, `grant`, `future_grant_reserve`, `actual_capitalization`, `idf`, `total`, `remaining_exemption`. |
| `source_id` | string \| null | required | Related input id, if any. | Required for grant/capitalization/IDF rows. |
| `label` | string | required | Human-readable label. | Non-empty. |
| `input_amount` | number \| null | required | Source amount relevant to the row. | Null only when not applicable. |
| `output_amount` | number | required | Amount produced by this audit row. | Must be deterministic number. |
| `impact_amount` | number | required | Exemption impact caused by this row. | Must be `>= 0`. |
| `details` | object | required | Structured deterministic explanation data. | Must not contain UI-only or DB-only fields. |

Audit rules:
- Every non-zero impact must have at least one audit row.
- Excluded grants must have an audit row showing zero impact and reason.
- IDF not applicable does not require an audit row.
- Audit rows must be sufficient to reproduce why each impact was included or excluded.

**7. ValidationError Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `code` | string | required | Stable machine-readable error code. | Non-empty. |
| `path` | string | required | Contract path to invalid field. | Example: `grants[0].indexed_amount`. |
| `message` | string | required | Human-readable explanation. | Non-empty. |
| `severity` | `"error"` | required | V1 only supports blocking validation errors. | Must be `error`. |
| `source_id` | string \| null | required | Related input id, if available. | Null if global input error. |

Required validation error categories:
- Missing required field.
- Invalid date.
- Invalid numeric value.
- Unknown or inconsistent eligibility year.
- Missing explicit monthly cap.
- Missing explicit exemption percentage.
- Missing explicit indexed grant amount.
- Invalid work date range.
- Invalid IDF percent format/value.
- Invalid IDF date range.
- Unsupported missing data.

**8. GrantResult Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `grant_id` | string | required | Echo of input grant_id. | Non-empty. |
| `indexed_amount` | number | required | Echo of input indexed_amount. | Must be `>= 0`. |
| `limited_indexed_amount` | number | required | Indexed amount limited by 32-year work ratio. | Must be `>= 0`. |
| `impact_amount` | number | required | Exemption impact after 15-year rule and multiplier. | Must be `>= 0`. |
| `exclusion_reason` | string \| null | required | Reason for zero impact if excluded. | Null if impact > 0. |

Work-ratio lock (approved):

- The 32-year work ratio is calculated using a day-based convention.
- The eligible work period is limited to the last 32 calendar years prior to eligibility_date.
- `work_years_ratio = eligible_work_days / total_days_in_32_year_window`
- Ratio is capped to the range `[0,1]`.

Leap-day calendar-year normalization:
- When calculating the 32-year window start from eligibility_date, subtract 32 calendar years.
- If eligibility_date is February 29 and the target year does not contain February 29, the window start date is February 28 of the target year.
- This is an explicit deterministic date-normalization rule, not fallback behavior.
- No other invalid date normalization is allowed.

- `grant_impact = indexed_amount * 1.35 * work_years_ratio`

- No intermediate rounding is performed.
- Final monetary outputs are rounded only at final result field level to 2 decimal places.

**9. ActualCapitalizationResult Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `capitalization_id` | string | required | Echo of input capitalization_id. | Non-empty. |
| `amount` | number | required | Echo of input amount. | Must be `>= 0`. |
| `impact_amount` | number | required | Exemption impact (direct reduction). | Must be `>= 0`. |

**10. IDFResult Schema**

| Field | Type | Required | Description | Validation |
|---|---:|---:|---|---|
| `idf_id` | string | required | Echo of input idf_id. | Non-empty. |
| `base_reduction` | number | required | `reduction_amount * (original_percent / current_percent)`. | Must be `> 0`. |
| `monthly_reduction_for_calc` | number | required | `min(base_reduction, monthly_cap * 0.35)`. | Must be `> 0`. |
| `overlap_months` | number | required | Overlap months used for impact. | Must be `> 0`. |
| `impact_amount` | number | required | Final IDF impact. | Must be `>= 0`. |

**11. Forbidden validation behavior**
- Silent fallback.
- Silent zero result for required data.
- Warning-only continuation for required calculation inputs.
- Replacing missing indexed value with nominal amount.
- Replacing missing year data with 2025 or 2028 values.