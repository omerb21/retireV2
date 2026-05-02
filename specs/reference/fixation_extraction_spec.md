**Fixation Extraction Spec**

**1. Authoritative Behavior To Preserve**

- Exempt capital ceiling by eligibility year:
  `monthly_cap(year) * 180 * exemption_percentage(year)`  
  Source: `app/services/rights_fixation/exemption_caps.py` `calc_exempt_capital()`.

- Year-based monthly cap and exemption percentage tables for known years.  
  Source: `ANNUAL_CAPS`, `EXEMPTION_PERCENTAGES`.

- Grant impact flow:
  indexed grant amount → 32-year work ratio → limited indexed amount → impact at `1.35`.  
  Source: `app/services/rights_fixation/grant_impact.py` `compute_grant_effect()`.

- 15-year grant exclusion:
  if years between grant date and eligibility date is greater than `15`, grant impact is `0`.  
  Source: `compute_grant_effect()`.

- Remaining exempt capital:
  `max(initial_exempt_capital - total_impact, 0)`.  
  Source: `compute_client_exemption()`.

- Monthly exempt pension:
  `remaining_exempt_capital / 180`.  
  Existing code expresses this via percentage × cap, but it is algebraically the same when cap > 0.  
  Sources: `compute_client_exemption()`, `update_fixation_exempt_pension_fields()`.

- Exempt pension percentage:
  `(remaining_exempt_capital / 180) / pension_ceiling`.  
  Source: `compute_client_exemption()`, `update_fixation_exempt_pension_fields()`.

- IDF/security-forces impact formula:
  `base_reduction = reduction_amount * (original_percent / current_percent)`  
  `monthly_reduction_for_calc = min(base_reduction, monthly_cap * 0.35)`  
  `impact = monthly_reduction_for_calc * overlap_months`  
  Source: `app/services/rights_fixation/idf_fixation.py` `compute_idf_fixation_impact()`.

- Future grant reserve impact as `future_grant_reserved * 1.35`, but only as deterministic engine input/output, not frontend logic.  
  Source currently: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts`.

- Commutation impact as a direct reduction from remaining exempt capital when applicable.  
  Current source: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts`, `app/services/retirement/services/commutation_exemption_service.py`.

**2. Behavior To Reject**

- Frontend calculations must not enter V1 as calculation authority.  
  Current files: `frontend/src/pages/SimpleFixation/utils/fixationCalculations.ts`, `useFixationData.ts`.

- Fallback to nominal indexation must not enter V1.  
  Current behavior: `compute_grant_effect()` uses nominal `grant_amount` when `calculate_adjusted_amount()` returns `None`.

- Fallback to 2025 caps must not enter V1.  
  Current behavior: `get_monthly_cap()` and `get_exemption_percentage()` default unknown years to 2025 values.

- LLM duplicate calculations must not enter V1.  
  Current file: `app/services/llm_agent_tools/fixation_tools.py`.

- Legacy zero-result endpoint must not enter V1.  
  Current file: `app/routers/fixation.py` `compute_fixation()`.

- Scenario side-effect mutation must not enter V1 engine.  
  Current files: `app/services/retirement_scenario_execution_service.py`, `commutation_exemption_service.py`.

- Multiple sources of truth must not enter V1:
  `FixationResult.exempt_capital_remaining`, `raw_result.exemption_summary.remaining_exempt_capital`, frontend save payload, and document normalization currently compete.

- Hidden lazy recalculation must not enter V1.  
  Current behavior: `get_saved_fixation()` calls `update_fixation_exempt_pension_fields()` if fields are missing.

- External API dependency inside calculation must not enter V1.  
  Current file: `app/services/rights_fixation/indexation.py`.

- Persistence inside calculation must not enter V1.  
  Current file: `app/routers/rights_fixation_parts/common.py`.

**3. Required Deterministic Inputs**

A V1 calculation must receive all data explicitly:

- `eligibility_date`
- `eligibility_year`
- `monthly_cap`
- `exemption_percentage`
- `capitalization_factor`, currently `180`
- `grant_impact_factor`, currently `1.35`
- `grants[]`:
  - `id`
  - `employer_name`
  - `grant_amount`
  - `grant_date`
  - `work_start_date`
  - `work_end_date`
  - `indexed_amount`
- `future_grant_reserved`, optional numeric, default decision unclear
- `commutations[]`, if applicable:
  - `id`
  - `amount`
  - `tax_treatment` or explicit inclusion flag
  - `source_type`
- `idf_security_forces`, optional:
  - `enabled`
  - `reduction_amount`
  - `original_commutation_percent`
  - `current_commutation_percent`
  - `monthly_cap`
  - `eligibility_date`
  - `commutation_date`
  - `promoter_age_date`

No DB, frontend state, LLM state, current date, external CPI API, or persisted fixation row may be required.

**4. Required Deterministic Outputs**

Final V1 output contract:

```ts
{
  eligibility_date: string;
  eligibility_year: number;

  initial_exempt_capital: number;

  grants: AuditGrantRow[];

  grant_impact_total: number;
  future_grant_reserved: number;
  future_grant_impact: number;

  commutation_impact: number;

  idf_impact: number;
  idf_detail?: {
    base_reduction: number;
    monthly_reduction_for_calc: number;
    overlap_months: number;
    error?: string | null;
  };

  total_impact: number;
  remaining_exempt_capital: number;

  monthly_exempt_pension: number;
  exemption_percentage: number;
  exempt_pension_percentage: number;

  audit_rows: AuditRow[];
}
```

Audit grant row:

```ts
{
  id?: string | number;
  employer_name?: string;
  grant_amount: number;
  grant_date: string;
  work_start_date: string;
  work_end_date: string;
  indexed_amount: number;
  ratio_32y: number;
  limited_indexed_amount: number;
  impact_on_exemption: number;
  exclusion_reason?: string | null;
}
```

Audit row:

```ts
{
  type: "grant" | "future_grant" | "commutation" | "idf" | "summary";
  label: string;
  input_amount?: number;
  calculated_amount?: number;
  impact?: number;
  rule: string;
}
```

**5. Formula Map**

| Formula | Old source | Status | Reason |
|---|---|---|---|
| `monthly_cap * 180 * exemption_percentage` | `exemption_caps.py` `calc_exempt_capital()` | preserve | core useful behavior |
| yearly cap table | `exemption_caps.py` | preserve known-year table | discovered source of current constants |
| fallback unknown year to 2025 | `get_monthly_cap()`, `get_exemption_percentage()` | reject | hidden fallback |
| year >= 2028 uses 2028 value | same | needs business decision | code says future years use 2028; legal/current intent unclear from code |
| `indexed_full * ratio` | `grant_impact.py` | preserve | core grant calculation |
| nominal fallback if indexation fails | `grant_impact.py` | reject | nondeterministic hidden fallback |
| 15-year exclusion | `grant_impact.py` | preserve | explicit business rule |
| `limited_indexed_amount * 1.35` | `grant_impact.py` | preserve | explicit grant impact rule |
| `max(initial - total_impact, 0)` | `compute_client_exemption()` | preserve | core summary |
| `(remaining / initial)` | `compute_client_exemption()` | preserve | current exemption percentage |
| `(remaining / 180) / pension_ceiling` | `compute_client_exemption()` | preserve | current exempt pension percentage |
| `remaining / 180` | `update_fixation_exempt_pension_fields()`, PDF generator | preserve | current useful monthly exemption |
| `futureGrantReserved * 1.35` | frontend `fixationCalculations.ts` | preserve but move into engine | useful behavior currently in wrong layer |
| `remaining - future - commutations - idf` | frontend `fixationCalculations.ts` | preserve but move into engine | final useful behavior currently in wrong layer |
| IDF formula | `idf_fixation.py` | preserve | explicit backend deterministic helper |
| LLM 2025 hardcoded simulation | `llm_agent_tools/fixation_tools.py` | reject | duplicate and hardcoded |
| max exemption in cashflow as `monthly_cap * exemption_percentage` | `retirement_cashflow_tools.py` | move outside engine | tax/cashflow delivery behavior, not fixation engine core |

**6. Branch Map**

| Branch | Old source | Status |
|---|---|---|
| client_id API branch loads DB | `rights_fixation.py` `calculate_rights_fixation()` | move outside engine |
| detailed payload branch | same | preserve as engine-style input concept |
| client missing -> HTTP 500 | same | move outside engine |
| eligibility gate returns 409 | same | move outside engine / needs business decision |
| missing demographic data does not block | same | needs business decision |
| internal helper ignores eligibility gate | `common.py` | reject from engine |
| missing eligibility date returns error dict | `core.py` | preserve as deterministic validation failure, not silent output |
| indexation failure -> nominal amount | `grant_impact.py` | reject |
| `years_diff > 15` -> impact 0 | `grant_impact.py` | preserve |
| exception in grant effect -> `None` | `grant_impact.py` | reject |
| `exempt_capital_initial <= 0` -> percentage 0 | `grant_impact.py` | preserve as validation/zero guard |
| `pension_ceiling <= 0` -> pension percentage 0 | same | preserve as validation/zero guard |
| IDF missing values -> zero with error | `idf_fixation.py` | needs business decision |
| no saved fixation -> null shape | `get_saved_fixation()` | move outside engine |
| lazy update missing fields | `get_saved_fixation()` | reject |
| scenario type max capital applies commutations | `retirement_scenario_execution_service.py` | move outside engine |
| commutation full/partial mutation | `commutation_exemption_service.py` | reject mutation; preserve impact concept only |
| LLM force max exemption | `run_retirement_cashflow_analysis.py` | move outside engine |

**7. V1 Engine Boundary**

The new Fixation Engine is allowed to do only this:

- Pure deterministic calculation.
- Accept fully explicit input data.
- Validate required deterministic inputs.
- Calculate:
  - initial exempt capital
  - grant impacts
  - future grant impact
  - commutation impact
  - IDF impact
  - total impact
  - remaining exempt capital
  - monthly exempt pension
  - exemption percentages
  - audit rows
- Return a deterministic output object.

The engine must not:

- Read or write DB.
- Call external APIs.
- Use current date implicitly.
- Read frontend state.
- Depend on LLM/tool/orchestration state.
- Persist `FixationResult`.
- Mutate scenarios, pensions, capital assets, or grants.
- Perform PDF/report formatting.
- Apply hidden fallback values.
- Lazily repair missing fields.
- Choose defaults from 2025 or nominal grant values when inputs are missing.

**8. Open Questions**

- Whether `year >= 2028` should permanently use 2028 cap and 67%, or whether V1 should require explicit values for every future year.

- Whether missing/invalid IDF inputs should produce zero impact with an error, or fail the full engine validation.

- Whether eligibility gating belongs before engine execution or whether engine should calculate regardless of eligibility and return eligibility metadata separately.

- Whether future grant reserve is always subject to `1.35`, with no indexation or 32-year ratio.

- Whether commutation impact should be supplied as an already-final amount, or derived from detailed commutation rows.

- Whether `exemption_percentage` should mean `remaining_exempt_capital / initial_exempt_capital` or the pension exemption percentage. Current code uses both names in nearby contexts.

- Whether negative final remaining exemption after frontend-style deductions should be clamped to zero. Backend grant summary clamps, frontend final calculation currently does not clamp.

- Whether IDF impact should reduce `remaining_exempt_capital` in the authoritative result. Current save path stores IDF impact separately; frontend subtracts it.