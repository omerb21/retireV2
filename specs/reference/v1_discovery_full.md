I performed a read-only discovery pass. No code was modified. Base path used below:

`C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire`

**1. Entry Points**

| Entry point | Type | Who calls it | Triggers calculation |
|---|---|---|---|
| `app/routers/rights_fixation.py` `calculate_rights_fixation()` | API | `POST /api/v1/rights-fixation/calculate`, called by `frontend/src/pages/SimpleFixation/hooks/useFixationData.ts` | yes, main backend fixation calculation |
| `app/routers/rights_fixation.py` `save_rights_fixation()` | API | `POST /api/v1/rights-fixation/save`, called by `useFixationData.ts` | partially: persists frontend-calculated commutation/future grant fields; computes IDF impact |
| `app/routers/rights_fixation.py` `calculate_grant_effect()` | API | `POST /api/v1/rights-fixation/grant/effect` | yes, single grant impact |
| `app/routers/rights_fixation.py` `calculate_exemption_summary()` | API | `POST /api/v1/rights-fixation/exemption/summary` | yes, summary from supplied grant impacts |
| `app/routers/rights_fixation.py` `get_caps_for_year()` | API | `GET /api/v1/rights-fixation/caps/{year}` | yes, cap/exempt capital calculation only |
| `app/routers/rights_fixation.py` `calculate_eligibility_date()` | API | `POST /api/v1/rights-fixation/eligibility-date` | yes, eligibility date only |
| `app/routers/rights_fixation.py` `get_saved_fixation()` | API | `GET /api/v1/rights-fixation/client/{client_id}` | lazy recalculates derived exempt pension fields if missing |
| `app/routers/rights_fixation_parts/common.py` `calculate_and_save_fixation_for_client()` | service/helper | LLM tool, retirement cashflow, retirement scenario execution | yes, internal compute + persist |
| `app/services/llm_chat/tool_handlers/calculate_fixation_of_rights.py` `handle_calculate_fixation_of_rights()` | LLM tool handler | `CALCULATE_FIXATION_OF_RIGHTS` tool | yes |
| `app/services/llm_agent_tools/fixation_tools.py` `calculate_tax_exempt_pension()` | LLM tool/service | `CALCULATE_TAX_EXEMPT_PENSION` | yes, separate simplified simulation |
| `app/services/llm_agent_tools/retirement_cashflow_tools.py` `run_retirement_cashflow_analysis()` | LLM tool/service | `RUN_RETIREMENT_CASHFLOW_ANALYSIS` | yes when `apply_max_exemption=True` |
| `app/services/retirement_scenario_execution_service.py` `execute_retirement_scenario()` | service/orchestration | scenario execution API/tool path | yes, auto-fixation and commutation allocation |
| `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts` `calculatePensionSummary()` | frontend calculation | SimpleFixation save flow | yes, computes future grant reserve, commutation impact, final exempt pension |
| `app/routers/fixation.py` `compute_fixation()` | legacy/stub API | `POST /api/v1/fixation/{client_id}/compute` | factual stub only, returns `0.0`, does not use current formulas |

**2. Full Execution Path**

Main backend calculate path:

1. `app/routers/rights_fixation.py` `calculate_rights_fixation()`  
   Accepts either `{client_id}` or detailed payload.

2. `app/routers/rights_fixation.py` `calculate_rights_fixation()`  
   For `{client_id}`, loads `Client`, `Grant`, pension start date, statutory eligibility date.

3. `app/routers/rights_fixation.py` `calculate_rights_fixation()`  
   Blocks with `409` if age or pension-start eligibility fails.

4. `app/routers/rights_fixation.py` `calculate_rights_fixation()`  
   Builds `formatted_data` with `grants`, `eligibility_date`, `eligibility_year`, `birth_date`, `gender`.

5. `app/services/rights_fixation/core.py` `calculate_full_fixation()`  
   Iterates grants and calls `process_grant()`.

6. `app/services/rights_fixation/core.py` `process_grant()`  
   Calls `compute_grant_effect()` and merges its result into the grant dict.

7. `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`  
   Calculates indexed amount, 32-year work ratio, 15-year exclusion, and grant impact.

8. `app/services/rights_fixation/grant_impact.py` `compute_client_exemption()`  
   Calculates initial exempt capital, total grant impact, remaining exempt capital, monthly exemption.

9. `app/services/rights_fixation/core.py` `calculate_full_fixation()`  
   Returns `{grants, exemption_summary, eligibility_date, eligibility_year}`.

Save path:

1. `frontend/src/pages/SimpleFixation/hooks/useFixationData.ts` `handleCalculateFixation()`  
   Calls `calculatePensionSummary()`.

2. `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts` `calculatePensionSummary()`  
   Computes future grant impact, commutations, IDF impact subtraction, remaining exemption, exempt pension.

3. `frontend/src/pages/SimpleFixation/hooks/useFixationData.ts` `handleCalculateFixation()`  
   Builds `calculation_result.exemption_summary` and calls `POST /api/v1/rights-fixation/save`.

4. `app/routers/rights_fixation.py` `save_rights_fixation()`  
   Optionally computes IDF impact via `compute_idf_fixation_impact()`.

5. `app/routers/rights_fixation.py` `save_rights_fixation()`  
   Upserts `FixationResult.raw_result`, `raw_payload`, `exempt_capital_remaining`.

Internal scenario path:

1. `app/services/retirement_scenario_execution_service.py` `execute_retirement_scenario()`  
   Deletes old `FixationResult` rows.

2. `app/services/retirement_scenario_execution_service.py` `execute_retirement_scenario()`  
   Executes selected retirement scenario.

3. `app/routers/rights_fixation_parts/common.py` `calculate_and_save_fixation_for_client()`  
   Computes and persists fixation without enforcing today’s eligibility.

4. `app/services/retirement/services/commutation_exemption_service.py` `apply_exempt_capital_to_scenario_commutations()`  
   For max-capital scenario, allocates exempt capital to taxable scenario commutations.

5. `app/routers/rights_fixation_parts/common.py` `update_fixation_exempt_pension_fields()`  
   Recalculates derived exempt pension fields from persisted remaining capital.

**3. Data Structures In Use**

| Object | File | Relevant fields | Role |
|---|---|---|---|
| `FixationResult` | `app/models/fixation_result.py` | `id`, `client_id`, `created_at`, `exempt_capital_remaining`, `used_commutation`, `raw_payload`, `raw_result`, `notes` | persisted input/output |
| `Grant` | `app/models/grant.py` | `grant_amount`, `work_start_date`, `work_end_date`, `grant_date`, `grant_indexed_amount`, `limited_indexed_amount`, `grant_ratio`, `impact_on_exemption` | input/intermediate |
| `client_data` dict | `app/services/rights_fixation/core.py` | `grants`, `eligibility_date`, `eligibility_year`, `birth_date`, `gender` | input |
| processed grant dict | `app/services/rights_fixation/grant_impact.py` | `indexed_full`, `ratio_32y`, `limited_indexed_amount`, `impact_on_exemption`, `exclusion_reason` | intermediate/output |
| `exemption_summary` dict | `app/services/rights_fixation/grant_impact.py` | `exempt_capital_initial`, `total_impact`, `remaining_exempt_capital`, `remaining_monthly_exemption`, `eligibility_year`, `exemption_percentage`, `calculated_pension_exemption_percentage`, `general_exemption_percentage` | output |
| `IdfFixationResult` | `app/services/rights_fixation/idf_fixation.py` | `impact`, `overlap_months`, `base_reduction`, `monthly_reduction_for_calc`, `error` | intermediate/output |
| `ExemptionSummary` TS | `frontend/src/pages/SimpleFixation/types.ts` | `exempt_capital_initial`, `total_impact`, `remaining_exempt_capital`, `remaining_monthly_exemption`, `eligibility_year`, `exemption_percentage`, `idf_security_forces_impact` | frontend input |
| `PensionSummary` TS | `frontend/src/pages/SimpleFixation/types.ts` | `future_grant_reserved`, `future_grant_impact`, `total_discounts`, `remaining_exemption`, `pension_ceiling`, `exempt_pension_calculated` | frontend intermediate/output |
| `TaxCalculationInput` | `app/schemas/tax_schemas.py` | `exempt_pension_amount`, `pension_months_in_year`, `pension_income` | tax input |
| `FixationData` dataclass | `app/services/documents/data_fetchers/fixation_data.py` | `client`, `exemption_summary`, `grants_summary`, `raw_result`, `eligibility_date` | document/PDF delivery |

**4. Actual Formulas Found In Code**

Exempt capital ceiling:

```python
return get_monthly_cap(year) * MULTIPLIER * get_exemption_percentage(year)
```

File/function: `app/services/rights_fixation/exemption_caps.py` `calc_exempt_capital()`  
Calculates monthly cap × 180 × exemption percentage.

Grant indexation fallback:

```python
indexed_full = calculate_adjusted_amount(...)
if indexed_full is None:
    indexed_full = float(grant["grant_amount"])
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`  
Uses CBS CPI API result; falls back to nominal grant amount.

32-year limited grant:

```python
limited_indexed_amount = round(indexed_full * ratio, 2)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`  
Applies work ratio to indexed grant.

Grant impact:

```python
impact_on_exemption = round(limited_indexed_amount * 1.35, 2)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`  
Each relevant grant reduces exempt capital by 135% of limited indexed amount.

15-year exclusion:

```python
if years_diff > 15:
    impact_on_exemption = 0
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`  
Old grant has no impact.

Remaining exempt capital:

```python
remaining_exempt_capital = max(exempt_capital_initial - total_impact, 0)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_client_exemption()`  
Subtracts total grant impact from initial exempt capital.

Exemption percentage:

```python
calculated_exemption_percentage = (
    (remaining_exempt_capital / exempt_capital_initial)
    if exempt_capital_initial > 0
    else 0
)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_client_exemption()`  
Remaining capital divided by initial capital.

Exempt pension percentage:

```python
calculated_pension_exemption_percentage = (
    ((remaining_exempt_capital / 180) / pension_ceiling)
    if pension_ceiling > 0
    else 0
)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_client_exemption()`  
Monthly exempt amount divided by pension ceiling.

Monthly exemption:

```python
remaining_monthly_exemption = round(
    calculated_pension_exemption_percentage * pension_ceiling, 2
)
```

File/function: `app/services/rights_fixation/grant_impact.py` `compute_client_exemption()`  
Equivalent to `remaining_exempt_capital / 180` when ceiling > 0.

Frontend future grant reserve:

```typescript
const futureGrantImpact = futureGrantReserved * 1.35;
```

File/function: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts` `calculatePensionSummary()`  
Reserved future grant reduces exemption at 135%.

Frontend final remaining exemption:

```typescript
const remainingExemption = remainingExemptCapital - futureGrantImpact - totalDiscounts - idfImpact;
```

File/function: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts` `calculatePensionSummary()`  
Subtracts future grant, commutations, and IDF impact from backend remaining capital.

Frontend exempt pension:

```typescript
const baseAmount = remainingExemption / 180;
const percentage = pensionCeiling > 0 ? (baseAmount / pensionCeiling) * 100 : 0;
```

File/function: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts` `calculatePensionSummary()`  
Converts remaining exemption to monthly exempt pension and percent of ceiling.

IDF base reduction:

```python
base_reduction = reduction_amount_f * (original_percent_f / current_percent_f)
max_reduction = monthly_cap_f * 0.35
monthly_reduction_for_calc = min(base_reduction, max_reduction)
impact = round(monthly_reduction_for_calc * overlap_months, 2)
```

File/function: `app/services/rights_fixation/idf_fixation.py` `compute_idf_fixation_impact()`  
Computes security-forces commutation impact.

LLM simplified grant simulation:

```python
grant_offset_value = current_tax_exempt_grant_amount * OFFSET_FACTOR
remaining_capital_after_grant = max(
    0, total_exempt_capital - grant_offset_value
)
final_exempt_pension = remaining_capital_after_grant / CAPITALIZATION_FACTOR
```

File/function: `app/services/llm_agent_tools/fixation_tools.py` `calculate_tax_exempt_pension()`  
Separate LLM simulation using hardcoded constants.

Tax integration:

```python
exempt_pension_annual = (
    input_data.exempt_pension_amount * input_data.pension_months_in_year
)
pension_exemption = pension_exemption_regular + exempt_pension_annual
taxable_income = max(
    0, regular_taxable_income - pension_exemption - total_deductions
)
```

File/function: `app/services/tax_calculator.py` `calculate_comprehensive_tax()`  
Applies fixation exempt pension into tax calculation.

**5. Business Rules Found In Code**

| Rule | File/function | Exact condition | Behavior |
|---|---|---|---|
| Future years use 2028 cap/percentage | `exemption_caps.py` `get_monthly_cap()`, `get_exemption_percentage()` | `if year >= 2028` | returns 2028 values |
| Unknown year fallback | same | `ANNUAL_CAPS.get(year, ANNUAL_CAPS[2025])` | defaults cap to 2025 |
| Grant date fallback | `grant_impact.py` `compute_grant_effect()` | `grant.get("grant_date") or grant["work_end_date"]` | uses work end date if grant date missing |
| Indexation failure fallback | `grant_impact.py` | `if indexed_full is None` | uses nominal grant amount |
| 15-year rule | `grant_impact.py` | `if years_diff > 15` | impact set to `0`; adds `exclusion_reason` |
| Grant offset multiplier | `grant_impact.py` | else branch after 15-year check | impact = limited indexed amount × 1.35 |
| Eligibility API gate | `rights_fixation.py` `calculate_rights_fixation()` | `if not (age_condition_ok and pension_condition_ok)` | returns HTTP 409 shape |
| Internal flows skip eligibility gate | `common.py` `calculate_and_save_fixation_for_client()` | comment and no blocking condition | calculates even if not eligible today |
| Save does not auto-add IDF impact to remaining capital | `rights_fixation.py` `save_rights_fixation()` | IDF data present | stores `idf_security_forces_impact`, does not mutate `remaining_exempt_capital` there |
| Frontend subtracts IDF impact | `fixationCalculations.ts` | always via `idfImpact` value | `remainingExemption = ... - idfImpact` |
| Scenario max-capital applies exemption to commutations | `retirement_scenario_execution_service.py` | `if scenario_type == "scenario_2_max_capital"` | calls `apply_exempt_capital_to_scenario_commutations()` |
| Full commutation exemption | `commutation_exemption_service.py` | `if remaining_exempt + 1e-2 >= amount` | marks asset `tax_treatment = "exempt"` |
| Partial commutation exemption | same | remaining exempt less than amount | splits/creates exempt asset and leaves taxable remainder |
| LLM `force_max_exemption` override | `run_retirement_cashflow_analysis.py` | `if force_max_exemption` | sets `apply_max_exemption = True` |

**6. Branching Map**

Major branches:

| File/function | Condition | Effect |
|---|---|---|
| `rights_fixation.py` `calculate_rights_fixation()` | `"client_id" in client_data and "grants" not in client_data` | DB-driven flow |
| same | else | direct detailed-payload flow |
| same | client missing | HTTP 500, except disabled `if False and client_id == 2` branch |
| same | missing `birth_date` or `gender` | skips eligibility blocking and may produce `eligibility_date=None` |
| same | age/pension condition false | HTTP 409 response |
| `core.py` `calculate_full_fixation()` | missing `eligibility_date` | returns error dict |
| `grant_impact.py` `compute_grant_effect()` | indexation returns `None` | nominal fallback |
| same | `years_diff > 15` | no grant impact |
| same | exception | returns `None` |
| `grant_impact.py` `compute_client_exemption()` | `exempt_capital_initial > 0` | calculates percentage; else 0 |
| same | `pension_ceiling > 0` | calculates pension percentage; else 0 |
| `idf_fixation.py` `compute_idf_fixation_impact()` | missing/invalid amounts or percents | returns zero impact with error |
| same | `monthly_cap <= 0` | returns zero impact with error |
| same | no overlap period | returns zero impact with error |
| `rights_fixation.py` `get_saved_fixation()` | no row | returns success with null raw result |
| same | missing derived pension fields | calls lazy `update_fixation_exempt_pension_fields()` |
| `commutation_exemption_service.py` | no remaining exempt capital | no-op |
| same | no scenario commutations | no-op |
| same | enough exempt capital for asset | full exempt |
| same | insufficient exempt capital | partial exempt split |

**7. Dependencies And Coupling**

| Coupling | File | Exact dependency | Calculation depends on it? |
|---|---|---|---|
| Database | `rights_fixation.py` | `Client`, `Grant`, `FixationResult`, `get_db` | API DB-driven calculation depends on it |
| Retirement age | `rights_fixation.py`, `work_ratio.py`, `eligibility.py` | `calc_eligibility_date`, `get_retirement_date` | eligibility/date logic depends on it |
| Pension start date | `rights_fixation.py`, `common.py` | `get_effective_pension_start_date` | eligibility/effective year depends on it |
| CBS API | `indexation.py` | `requests.get(CBS_CPI_API...)` | grant indexation depends on it, but has nominal fallback |
| Frontend calculation | `useFixationData.ts`, `fixationCalculations.ts` | save payload precomputes future grant/commutation fields | current saved final exemption depends on frontend |
| LLM tools | `calculate_fixation_of_rights.py`, `fixation_tools.py`, `retirement_cashflow_tools.py` | tool handlers call fixation functions or duplicate simplified logic | some calculations depend directly |
| Prompt/tool definitions | `state_tools.py` | `CALCULATE_TAX_EXEMPT_PENSION`, `RUN_RETIREMENT_CASHFLOW_ANALYSIS` descriptions | delivery/orchestration layer |
| PDF generation | `form_161d_generator.py`, `documents/data_fetchers/fixation_data.py` | reads `FixationResult.raw_result` and formats fields | delivery layer, except it normalizes raw result in memory |
| Tax calculation | `tax_calculator.py` | `TaxCalculationInput.exempt_pension_amount` | tax result depends on fixation-derived monthly exemption |
| Scenario execution | `retirement_scenario_execution_service.py` | auto deletes/recreates fixation and applies commutation exemption | scenario flow depends on fixation |

**8. Output Contract Of Current System**

`POST /api/v1/rights-fixation/calculate` success:

```python
{
    "grants": processed_grants,
    "exemption_summary": exemption_summary,
    "eligibility_date": eligibility_date,
    "eligibility_year": eligibility_year,
}
```

`exemption_summary` from backend core:

```python
{
    "exempt_capital_initial": ...,
    "total_impact": ...,
    "remaining_exempt_capital": ...,
    "remaining_monthly_exemption": ...,
    "eligibility_year": ...,
    "exemption_percentage": ...,
    "calculated_pension_exemption_percentage": ...,
    "general_exemption_percentage": ...,
}
```

`POST /api/v1/rights-fixation/save`:

```python
{
    "success": True,
    "message": "...",
    "calculation_date": datetime.now().isoformat(),
}
```

`GET /api/v1/rights-fixation/client/{client_id}` with saved row:

```python
{
    "success": True,
    "calculation_date": result.created_at.isoformat(),
    "exempt_capital_remaining": result.exempt_capital_remaining,
    "raw_result": result.raw_result,
    "raw_payload": result.raw_payload,
    "eligible": eligible,
}
```

Legacy `POST /api/v1/fixation/{client_id}/compute`:

```python
{
    "client_id": client_id,
    "client_name": client.full_name,
    "persisted_id": row.id,
    "success": True,
    "status": "ok",
    "message": "Fixation computed successfully",
    "outputs": {
        "exempt_capital_remaining": 0.0,
        "used_commutation": 0.0,
        "annex_161d_ready": True,
        "status": "ok",
    },
    "engine_version": "fixation-sprint2-1",
}
```

LLM `CALCULATE_TAX_EXEMPT_PENSION` returns only `result` JSON:

```python
{
    "initial_exempt_pension": ...,
    "final_exempt_pension": ...,
    "exempt_grant_used": ...,
    "monthly_pension_loss": ...,
    "total_capital_offset": ...,
    "remaining_exempt_capital": ...,
    "scenarios_text": {...},
}
```

**9. Problems Found**

Factual only:

1. Duplicate calculation logic exists:
   - Backend core: `app/services/rights_fixation/grant_impact.py`
   - Frontend final exemption: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts`
   - LLM simplified simulation: `app/services/llm_agent_tools/fixation_tools.py`

2. Multiple sources of truth for `remaining_exempt_capital`:
   - `FixationResult.exempt_capital_remaining`
   - `FixationResult.raw_result["exemption_summary"]["remaining_exempt_capital"]`
   - frontend-saved `calculation_result.exemption_summary.remaining_exempt_capital`
   - documents fetcher overwrites summary from persisted field.

3. Some calculation is in the frontend save flow:
   - `future_grant_impact`, `total_discounts`, `remaining_exemption`, `remaining_monthly_exemption`, `exempt_pension_percentage` are computed in `useFixationData.ts` and `fixationCalculations.ts`.

4. Hidden fallback behavior exists:
   - Indexation failure falls back to nominal grant amount in `compute_grant_effect()`.
   - LLM tax-exempt pension falls back to hardcoded 2025 constants if no fixation row exists.

5. Eligibility behavior differs by entry point:
   - API `/calculate` enforces age/pension-start and can return 409.
   - `calculate_and_save_fixation_for_client()` deliberately does not enforce those conditions.

6. IDF impact handling is split:
   - Backend save computes and stores `idf_security_forces_impact`.
   - Frontend calculation subtracts `idfImpact` from final remaining exemption.
   - Backend save comment explicitly says it does not change `remaining_exempt_capital` for IDF at that point.

7. Legacy endpoint `app/routers/fixation.py` `compute_fixation()` persists a `FixationResult` with `exempt_capital_remaining=0.0` and `raw_result={"status": "ok"}` rather than using current fixation formulas.

8. `CommutationExemptionService` mutates capital assets and `FixationResult` during scenario execution, so fixation state is coupled to scenario side effects.

**10. Evidence**

All claims above are based on these exact functions/files:

- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\core.py`: `calculate_full_fixation()`, `process_grant()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\grant_impact.py`: `compute_grant_effect()`, `compute_client_exemption()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\exemption_caps.py`: `get_monthly_cap()`, `get_exemption_percentage()`, `calc_exempt_capital()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\indexation.py`: `calculate_adjusted_amount()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\work_ratio.py`: `work_ratio_within_last_32y()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\rights_fixation\idf_fixation.py`: `compute_idf_fixation_impact()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation.py`: all API entry points listed
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\routers\rights_fixation_parts\common.py`: `calculate_and_save_fixation_for_client()`, `update_fixation_exempt_pension_fields()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\frontend\src\pages\SimpleFixation\utils\fixationCalculations.ts`: `calculatePensionSummary()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\frontend\src\pages\SimpleFixation\hooks\useFixationData.ts`: `handleCalculateFixation()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\llm_agent_tools\fixation_tools.py`: `calculate_tax_exempt_pension()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\llm_agent_tools\retirement_cashflow_tools.py`: `run_retirement_cashflow_analysis()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\retirement\services\commutation_exemption_service.py`: `apply_exempt_capital_to_scenario_commutations()`
- `C:\Users\omer\OneDrive\AI PROJECTS\WINSURDF\dev\retire\app\services\tax_calculator.py`: `calculate_comprehensive_tax()`

Unclear from code: whether the current intended source of truth for final saved exemption is backend core, frontend `calculatePensionSummary()`, or persisted `FixationResult.exempt_capital_remaining`; all three are actively involved.