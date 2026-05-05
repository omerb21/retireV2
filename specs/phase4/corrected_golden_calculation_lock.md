# Corrected Golden Calculation / Lock Artifact - Phase 4 Fixation Engine

## 1. Correction Control

- Current phase: Phase 4 planning / Golden Calculation Lock correction
- Artifact type: corrected Supervisor-reviewable Golden Calculation / Lock Artifact
- Correction reason: prior artifact was not approved due to AuditRow.stage_order conflict
- Coding authorization: no
- Phase 4 execution status: blocked, not started
- Golden values status: locked for Phase 4 planning after Supervisor approval
- Purpose: correct only the AuditRow stage_order values so they align with the already-approved Formula Lock audit baseline
- Supervisor review required: yes

This artifact does not authorize coding, does not start Phase 4 execution, does not modify contracts, does not add tests, does not change formulas, does not change payloads, and does not introduce new Golden cases.

## 2. Supervisor Blocking Issue Recap

- The prior Golden Calculation / Lock Artifact was not approved.
- The only blocking issue was AuditRow.stage_order conflict.
- Numerical calculations were not rejected.
- Validation-only cases were not rejected.
- This correction aligns all AuditRows to the already-approved Formula Lock stage order.
- No new audit-order decision is introduced.
- No formulas are changed.
- No payloads are changed.
- No validation cases are changed.

## 3. Approved Formula Lock Audit Stage Order

The approved audit stage order is:

1. input validation passed
2. initial entitlement
3. grant impact
4. 15-year exclusion
5. 32-year ratio
6. future grant reserve
7. actual capitalization impact
8. IDF treatment
9. total impact aggregation
10. remaining exemption
11. exempt pension

This is the only audit order used in this corrected artifact.

## 4. Correction Rule

- All AuditRows must use the approved stage_order above.
- grant_impact AuditRows must use stage_order: 3.
- 15_year_exclusion AuditRows must use stage_order: 4.
- 32_year_ratio AuditRows must use stage_order: 5.
- future_grant_reserve AuditRows must use stage_order: 6.
- actual_capitalization AuditRows must use stage_order: 7.
- idf_treatment AuditRows must use stage_order: 8.
- total_impact AuditRows must use stage_order: 9.
- remaining_exemption AuditRows must use stage_order: 10.
- exempt_pension AuditRows must use stage_order: 11.
- stage_order changes do not change numerical calculations.
- Formulas, payloads, validation cases, and expected numeric outputs remain unchanged.

## 5. Corrected Golden Case Calculations

## GC01_BASE_CASE

### Approved input payload

```yaml
case_name: "GC01_BASE_CASE"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants: []
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 10,000 × 0.57 × 180 = 1,026,000.00
grant_impact = 0.00
future_reserve_impact = 0.00
actual_capitalization_impact = 0.00
idf_impact = 0.00, informational only
total_impact = 0.00
remaining_exemption = max(1,026,000.00 - 0.00, 0) = 1,026,000.00
exempt_pension = 1,026,000.00 / 180 = 5,700.00
```

### Expected FixationResult

```yaml
case_name: "GC01_BASE_CASE"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
idf_informational_only: true
idf_impact_in_total: 0.00
total_impact: 0.00
remaining_exemption: 1026000.00
exempt_pension: 5700.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"
    impact_amount: 0.00
    details:
      status: "passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    input_amount: 10000.00
    output_amount: 1026000.00
    details:
      monthly_cap: 10000.00
      exemption_percentage: 0.57
      capital_multiplier: 180

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 0.00
    details:
      grant_impact: 0.00
      future_reserve_impact: 0.00
      actual_capitalization_impact: 0.00
      idf_excluded_as_informational: true

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    input_amount: 1026000.00
    impact_amount: 0.00
    output_amount: 1026000.00
    details:
      zero_floor_applied: false

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    input_amount: 1026000.00
    output_amount: 5700.00
    details:
      capital_multiplier: 180
```

Expected ValidationErrors: none

Status: LOCKED

## GC02_SINGLE_GRANT_FULL_IMPACT

### Approved input payload

```yaml
case_name: "GC02_SINGLE_GRANT_FULL_IMPACT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_001"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 10,000 × 0.57 × 180 = 1,026,000.00
grant date 2024-01-01 is after boundary 2011-01-01, so included
work period 1994-01-01 to 2026-01-01 = 32 years
ratio_32y = 1.0
qualifying_grant_amount = 100,000.00 × 1.0 = 100,000.00
grant_impact = 100,000.00 × 1.35 = 135,000.00
total_impact = 135,000.00
remaining_exemption = 1,026,000.00 - 135,000.00 = 891,000.00
exempt_pension = 891,000.00 / 180 = 4,950.00
```

### Expected FixationResult

```yaml
case_name: "GC02_SINGLE_GRANT_FULL_IMPACT"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 135000.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
idf_informational_only: true
idf_impact_in_total: 0.00
total_impact: 135000.00
remaining_exemption: 891000.00
exempt_pension: 4950.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"
    details:
      status: "passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00
    details:
      monthly_cap: 10000.00
      exemption_percentage: 0.57
      capital_multiplier: 180

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_001"
    input_amount: 100000.00
    impact_amount: 135000.00
    details:
      component_type: "historical_grant"
      pre_multiplier_amount: 100000.00
      multiplier: 1.35
      post_multiplier_impact: 135000.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_001"
    input_amount: 100000.00
    output_amount: 100000.00
    details:
      grant_date: "2024-01-01"
      boundary_date: "2011-01-01"
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "grant_001"
    input_amount: 100000.00
    output_amount: 100000.00
    details:
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
      ratio_32y: 1.0
      capped: false

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 135000.00
    details:
      grant_impact: 135000.00
      future_reserve_impact: 0.00
      actual_capitalization_impact: 0.00
      idf_excluded_as_informational: true

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    input_amount: 1026000.00
    impact_amount: 135000.00
    output_amount: 891000.00
    details:
      zero_floor_applied: false

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    input_amount: 891000.00
    output_amount: 4950.00
    details:
      capital_multiplier: 180
```

Expected ValidationErrors: none

Status: LOCKED
## GC03A_15Y_ONE_DAY_BEFORE_BOUNDARY

### Approved input payload

```yaml
case_name: "GC03A_15Y_ONE_DAY_BEFORE_BOUNDARY"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_15y_before"
      indexed_amount: 100000.00
      grant_date: "2010-12-31"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
grant date 2010-12-31 is before boundary 2011-01-01
grant is excluded
grant_impact = 0.00
total_impact = 0.00
remaining_exemption = 1,026,000.00
exempt_pension = 5,700.00
```

### Expected FixationResult

```yaml
case_name: "GC03A_15Y_ONE_DAY_BEFORE_BOUNDARY"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
total_impact: 0.00
remaining_exemption: 1026000.00
exempt_pension: 5700.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"
    details:
      status: "passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_15y_before"
    input_amount: 100000.00
    impact_amount: 0.00
    details:
      component_type: "historical_grant"
      excluded_by_15_year_rule: true
      post_multiplier_impact: 0.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_15y_before"
    input_amount: 100000.00
    output_amount: 0.00
    details:
      grant_date: "2010-12-31"
      boundary_date: "2011-01-01"
      included: false

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 0.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 1026000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5700.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC03B_15Y_EXACTLY_ON_BOUNDARY

### Approved input payload

```yaml
case_name: "GC03B_15Y_EXACTLY_ON_BOUNDARY"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_15y_exact"
      indexed_amount: 100000.00
      grant_date: "2011-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
grant date 2011-01-01 is exactly on boundary
approved Golden convention treats exactly-on-boundary as excluded
grant_impact = 0.00
total_impact = 0.00
remaining_exemption = 1,026,000.00
exempt_pension = 5,700.00
```

### Expected FixationResult

```yaml
case_name: "GC03B_15Y_EXACTLY_ON_BOUNDARY"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
total_impact: 0.00
remaining_exemption: 1026000.00
exempt_pension: 5700.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_15y_exact"
    input_amount: 100000.00
    impact_amount: 0.00
    details:
      component_type: "historical_grant"
      excluded_by_15_year_rule: true
      post_multiplier_impact: 0.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_15y_exact"
    input_amount: 100000.00
    output_amount: 0.00
    details:
      grant_date: "2011-01-01"
      boundary_date: "2011-01-01"
      included: false

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 0.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 1026000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5700.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC03C_15Y_ONE_DAY_AFTER_BOUNDARY

### Approved input payload

```yaml
case_name: "GC03C_15Y_ONE_DAY_AFTER_BOUNDARY"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_15y_after"
      indexed_amount: 100000.00
      grant_date: "2011-01-02"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
grant date 2011-01-02 is after boundary 2011-01-01
grant is included
ratio_32y = 1.0
grant_impact = 100,000.00 × 1.0 × 1.35 = 135,000.00
total_impact = 135,000.00
remaining_exemption = 891,000.00
exempt_pension = 4,950.00
```

### Expected FixationResult

```yaml
case_name: "GC03C_15Y_ONE_DAY_AFTER_BOUNDARY"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 135000.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
total_impact: 135000.00
remaining_exemption: 891000.00
exempt_pension: 4950.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_15y_after"
    input_amount: 100000.00
    impact_amount: 135000.00
    details:
      component_type: "historical_grant"
      pre_multiplier_amount: 100000.00
      multiplier: 1.35
      post_multiplier_impact: 135000.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_15y_after"
    input_amount: 100000.00
    output_amount: 100000.00
    details:
      grant_date: "2011-01-02"
      boundary_date: "2011-01-01"
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "grant_15y_after"
    input_amount: 100000.00
    output_amount: 100000.00
    details:
      ratio_32y: 1.0

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 135000.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 891000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 4950.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC04A_32Y_FULL_PERIOD

### Approved input payload

```yaml
case_name: "GC04A_32Y_FULL_PERIOD"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_32y_full"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
work period = 32 years
ratio_32y = 1.0
grant_impact = 100,000.00 × 1.0 × 1.35 = 135,000.00
total_impact = 135,000.00
remaining_exemption = 891,000.00
exempt_pension = 4,950.00
```

### Expected FixationResult

```yaml
case_name: "GC04A_32Y_FULL_PERIOD"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 135000.00
total_impact: 135000.00
remaining_exemption: 891000.00
exempt_pension: 4950.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_32y_full"
    input_amount: 100000.00
    impact_amount: 135000.00
    details:
      multiplier: 1.35
      post_multiplier_impact: 135000.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_32y_full"
    output_amount: 100000.00
    details:
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "grant_32y_full"
    details:
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
      ratio_32y: 1.0
      capped: false

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 135000.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 891000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 4950.00
```

Expected ValidationErrors: none

Status: LOCKED
## GC04B_32Y_PARTIAL_PERIOD

### Approved input payload

```yaml
case_name: "GC04B_32Y_PARTIAL_PERIOD"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_32y_partial"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "2010-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
work period 2010-01-01 to 2026-01-01 = 16 years
ratio_32y = 16 / 32 = 0.5
qualifying_grant_amount = 100,000.00 × 0.5 = 50,000.00
grant_impact = 50,000.00 × 1.35 = 67,500.00
total_impact = 67,500.00
remaining_exemption = 1,026,000.00 - 67,500.00 = 958,500.00
exempt_pension = 958,500.00 / 180 = 5,325.00
```

### Expected FixationResult

```yaml
case_name: "GC04B_32Y_PARTIAL_PERIOD"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 67500.00
total_impact: 67500.00
remaining_exemption: 958500.00
exempt_pension: 5325.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_32y_partial"
    input_amount: 50000.00
    impact_amount: 67500.00
    details:
      pre_multiplier_amount: 50000.00
      multiplier: 1.35
      post_multiplier_impact: 67500.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_32y_partial"
    output_amount: 100000.00
    details:
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "grant_32y_partial"
    input_amount: 100000.00
    output_amount: 50000.00
    details:
      work_start_date: "2010-01-01"
      work_end_date: "2026-01-01"
      ratio_32y: 0.5
      capped: false

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 67500.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 958500.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5325.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC04C_32Y_OVER_CAP

### Approved input payload

```yaml
case_name: "GC04C_32Y_OVER_CAP"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_32y_over_cap"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "1991-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
work period 1991-01-01 to 2026-01-01 = 35 years
raw ratio = 35 / 32 = 1.09375
ratio_32y capped = 1.0
grant_impact = 100,000.00 × 1.0 × 1.35 = 135,000.00
total_impact = 135,000.00
remaining_exemption = 891,000.00
exempt_pension = 4,950.00
```

### Expected FixationResult

```yaml
case_name: "GC04C_32Y_OVER_CAP"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 135000.00
total_impact: 135000.00
remaining_exemption: 891000.00
exempt_pension: 4950.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "grant_32y_over_cap"
    input_amount: 100000.00
    impact_amount: 135000.00
    details:
      multiplier: 1.35
      post_multiplier_impact: 135000.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "grant_32y_over_cap"
    output_amount: 100000.00
    details:
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "grant_32y_over_cap"
    input_amount: 100000.00
    output_amount: 100000.00
    details:
      work_start_date: "1991-01-01"
      work_end_date: "2026-01-01"
      raw_ratio_32y: 1.09375
      ratio_32y: 1.0
      capped: true

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 135000.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 891000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 4950.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC05_MULTIPLE_GRANTS

### Approved input payload

```yaml
case_name: "GC05_MULTIPLE_GRANTS"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_multi_included_full"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
    - grant_id: "grant_multi_excluded_15y"
      indexed_amount: 80000.00
      grant_date: "2010-12-31"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
    - grant_id: "grant_multi_included_partial"
      indexed_amount: 60000.00
      grant_date: "2023-06-01"
      work_start_date: "2010-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00

Grant 1:
included by 15-year rule
ratio = 1.0
impact = 100,000.00 × 1.0 × 1.35 = 135,000.00

Grant 2:
grant date 2010-12-31 before boundary
excluded
impact = 0.00

Grant 3:
included by 15-year rule
ratio = 0.5
impact = 60,000.00 × 0.5 × 1.35 = 40,500.00

total_grant_impact = 135,000.00 + 0.00 + 40,500.00 = 175,500.00
total_impact = 175,500.00
remaining_exemption = 1,026,000.00 - 175,500.00 = 850,500.00
exempt_pension = 850,500.00 / 180 = 4,725.00
```

### Expected FixationResult

```yaml
case_name: "GC05_MULTIPLE_GRANTS"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 175500.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
total_impact: 175500.00
remaining_exemption: 850500.00
exempt_pension: 4725.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    impact_amount: 175500.00
    details:
      multiplier: 1.35
      grants:
        - source_id: "grant_multi_included_full"
          pre_multiplier_amount: 100000.00
          post_multiplier_impact: 135000.00
        - source_id: "grant_multi_excluded_15y"
          pre_multiplier_amount: 0.00
          post_multiplier_impact: 0.00
        - source_id: "grant_multi_included_partial"
          pre_multiplier_amount: 30000.00
          post_multiplier_impact: 40500.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    details:
      grants:
        - source_id: "grant_multi_included_full"
          grant_date: "2024-01-01"
          included: true
        - source_id: "grant_multi_excluded_15y"
          grant_date: "2010-12-31"
          included: false
        - source_id: "grant_multi_included_partial"
          grant_date: "2023-06-01"
          included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    details:
      grants:
        - source_id: "grant_multi_included_full"
          ratio_32y: 1.0
        - source_id: "grant_multi_included_partial"
          ratio_32y: 0.5

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 175500.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 850500.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 4725.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC06_ACTUAL_CAPITALIZATION_IMPACT

### Approved input payload

```yaml
case_name: "GC06_ACTUAL_CAPITALIZATION_IMPACT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants: []
  future_grant_reserved: 0.00
  actual_capitalizations:
    - capitalization_id: "cap_001"
      amount: 60000.00
      capitalization_date: "2024-06-01"
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
actual_capitalization_amount = 60,000.00
no multiplier
actual_capitalization_impact = 60,000.00
total_impact = 60,000.00
remaining_exemption = 966,000.00
exempt_pension = 966,000.00 / 180 = 5,366.67
```

### Expected FixationResult

```yaml
case_name: "GC06_ACTUAL_CAPITALIZATION_IMPACT"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 60000.00
total_impact: 60000.00
remaining_exemption: 966000.00
exempt_pension: 5366.67
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 7
    category: "actual_capitalization"
    label: "actual capitalization impact"
    source_id: "cap_001"
    input_amount: 60000.00
    impact_amount: 60000.00
    details:
      capitalization_date: "2024-06-01"
      multiplier: null
      component_type: "actual_capitalization"

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 60000.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 966000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5366.67
```

Expected ValidationErrors: none

Status: LOCKED
## GC07_IDF_INFORMATIONAL_ONLY

### Approved input payload

```yaml
case_name: "GC07_IDF_INFORMATIONAL_ONLY"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: true
  grants: []
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf:
    idf_id: "idf_001"
    reduction_amount: 25000.00
    original_commutation_percent: 25.00
    current_commutation_percent: 10.00
    commutation_date: "2020-01-01"
    promoter_age_date: "2026-01-01"
    source_label: "golden_idf_sample"
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
IDF input valid
IDF is informational only
IDF impact included in total impact = 0.00
total_impact = 0.00
remaining_exemption = 1,026,000.00
exempt_pension = 5,700.00
```

### Expected FixationResult

```yaml
case_name: "GC07_IDF_INFORMATIONAL_ONLY"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 0.00
idf_result:
  informational_only: true
  reduction_amount: 25000.00
  original_commutation_percent: 25.00
  current_commutation_percent: 10.00
total_impact: 0.00
remaining_exemption: 1026000.00
exempt_pension: 5700.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 8
    category: "idf_treatment"
    label: "IDF informational treatment"
    source_id: "idf_001"
    input_amount: 25000.00
    impact_amount: 0.00
    details:
      informational_only: true
      no_total_impact_effect: true
      no_remaining_exemption_effect: true
      no_exempt_pension_effect: true

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 0.00
    details:
      idf_excluded_as_informational: true

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 1026000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5700.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC08_FUTURE_GRANT_RESERVE_ONLY

### Approved input payload

```yaml
case_name: "GC08_FUTURE_GRANT_RESERVE_ONLY"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants: []
  future_grant_reserved: 50000.00
  actual_capitalizations: []
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00
future_grant_reserved = 50,000.00
future reserve multiplier = 1.35
future_reserve_impact = 50,000.00 × 1.35 = 67,500.00
total_impact = 67,500.00
remaining_exemption = 958,500.00
exempt_pension = 958,500.00 / 180 = 5,325.00
```

### Expected FixationResult

```yaml
case_name: "GC08_FUTURE_GRANT_RESERVE_ONLY"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 0.00
future_grant_reserved_impact: 67500.00
actual_capitalization_impact: 0.00
total_impact: 67500.00
remaining_exemption: 958500.00
exempt_pension: 5325.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 6
    category: "future_grant_reserve"
    label: "future grant reserve"
    input_amount: 50000.00
    impact_amount: 67500.00
    details:
      component_type: "future_reserve"
      pre_multiplier_amount: 50000.00
      multiplier: 1.35
      post_multiplier_impact: 67500.00
      effect_on_remaining_exemption: 67500.00

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 67500.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 958500.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 5325.00
```

Expected ValidationErrors: none

Status: LOCKED

## GC09_COMBINED_FULL_SCENARIO

### Approved input payload

```yaml
case_name: "GC09_COMBINED_FULL_SCENARIO"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: true
  grants:
    - grant_id: "combined_grant_included"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "2010-01-01"
      work_end_date: "2026-01-01"
    - grant_id: "combined_grant_excluded"
      indexed_amount: 80000.00
      grant_date: "2010-12-31"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 50000.00
  actual_capitalizations:
    - capitalization_id: "combined_cap_001"
      amount: 60000.00
      capitalization_date: "2024-06-01"
  idf:
    idf_id: "combined_idf_001"
    reduction_amount: 25000.00
    original_commutation_percent: 25.00
    current_commutation_percent: 10.00
    commutation_date: "2020-01-01"
    promoter_age_date: "2026-01-01"
    source_label: "combined_idf_sample"
```

### Step-by-step calculation

```text
initial_entitlement = 1,026,000.00

Grant 1:
indexed_amount = 100,000.00
grant date 2024-01-01 included
work period 2010-01-01 to 2026-01-01 = 16 years
ratio_32y = 0.5
pre_multiplier_amount = 100,000.00 × 0.5 = 50,000.00
grant_impact = 50,000.00 × 1.35 = 67,500.00

Grant 2:
indexed_amount = 80,000.00
grant date 2010-12-31 excluded
grant_impact = 0.00

Future reserve:
50,000.00 × 1.35 = 67,500.00

Actual capitalization:
60,000.00, no multiplier

IDF:
informational only, excluded from total impact

total_impact = 67,500.00 + 67,500.00 + 60,000.00 = 195,000.00
remaining_exemption = 1,026,000.00 - 195,000.00 = 831,000.00
exempt_pension = 831,000.00 / 180 = 4,616.67
```

### Expected FixationResult

```yaml
case_name: "GC09_COMBINED_FULL_SCENARIO"
status: "success"
initial_entitlement: 1026000.00
grant_impact: 67500.00
future_grant_reserved_impact: 67500.00
actual_capitalization_impact: 60000.00
idf_result:
  informational_only: true
  reduction_amount: 25000.00
total_impact: 195000.00
remaining_exemption: 831000.00
exempt_pension: 4616.67
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 1026000.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    impact_amount: 67500.00
    details:
      grants:
        - source_id: "combined_grant_included"
          pre_multiplier_amount: 50000.00
          multiplier: 1.35
          post_multiplier_impact: 67500.00
        - source_id: "combined_grant_excluded"
          post_multiplier_impact: 0.00

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    details:
      grants:
        - source_id: "combined_grant_included"
          grant_date: "2024-01-01"
          included: true
        - source_id: "combined_grant_excluded"
          grant_date: "2010-12-31"
          included: false

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "combined_grant_included"
    details:
      work_start_date: "2010-01-01"
      work_end_date: "2026-01-01"
      ratio_32y: 0.5

  - stage_order: 6
    category: "future_grant_reserve"
    label: "future grant reserve"
    input_amount: 50000.00
    impact_amount: 67500.00
    details:
      multiplier: 1.35
      post_multiplier_impact: 67500.00

  - stage_order: 7
    category: "actual_capitalization"
    label: "actual capitalization impact"
    source_id: "combined_cap_001"
    input_amount: 60000.00
    impact_amount: 60000.00
    details:
      capitalization_date: "2024-06-01"

  - stage_order: 8
    category: "idf_treatment"
    label: "IDF informational treatment"
    source_id: "combined_idf_001"
    impact_amount: 0.00
    details:
      informational_only: true
      no_total_impact_effect: true

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 195000.00
    details:
      grant_impact: 67500.00
      future_reserve_impact: 67500.00
      actual_capitalization_impact: 60000.00
      idf_excluded_as_informational: true

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    output_amount: 831000.00

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    output_amount: 4616.67
```

Expected ValidationErrors: none

Status: LOCKED

## GC10_ZERO_REMAINING_EXEMPTION

### Approved input payload

```yaml
case_name: "GC10_ZERO_REMAINING_EXEMPTION"
input_payload:
  monthly_cap: 1000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "zero_floor_grant"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations:
    - capitalization_id: "zero_floor_cap"
      amount: 60000.00
      capitalization_date: "2024-06-01"
  idf: null
```

### Step-by-step calculation

```text
initial_entitlement = 1,000 × 0.57 × 180 = 102,600.00

Grant:
100,000.00 × 1.0 × 1.35 = 135,000.00

Actual capitalization:
60,000.00

total_impact = 135,000.00 + 60,000.00 = 195,000.00
remaining_exemption before floor = 102,600.00 - 195,000.00 = -92,400.00
remaining_exemption after zero floor = 0.00
exempt_pension = 0.00 / 180 = 0.00
```

### Expected FixationResult

```yaml
case_name: "GC10_ZERO_REMAINING_EXEMPTION"
status: "success"
initial_entitlement: 102600.00
grant_impact: 135000.00
future_grant_reserved_impact: 0.00
actual_capitalization_impact: 60000.00
total_impact: 195000.00
remaining_exemption_before_floor: -92400.00
remaining_exemption: 0.00
exempt_pension: 0.00
```

### Corrected AuditRows

```yaml
audit_rows:
  - stage_order: 1
    category: "input_validation"
    label: "input validation passed"

  - stage_order: 2
    category: "initial_entitlement"
    label: "initial entitlement"
    output_amount: 102600.00

  - stage_order: 3
    category: "grant_impact"
    label: "grant impact"
    source_id: "zero_floor_grant"
    input_amount: 100000.00
    impact_amount: 135000.00
    details:
      multiplier: 1.35

  - stage_order: 4
    category: "15_year_exclusion"
    label: "15-year exclusion"
    source_id: "zero_floor_grant"
    details:
      included: true

  - stage_order: 5
    category: "32_year_ratio"
    label: "32-year ratio"
    source_id: "zero_floor_grant"
    details:
      ratio_32y: 1.0

  - stage_order: 7
    category: "actual_capitalization"
    label: "actual capitalization impact"
    source_id: "zero_floor_cap"
    input_amount: 60000.00
    impact_amount: 60000.00

  - stage_order: 9
    category: "total_impact"
    label: "total impact aggregation"
    output_amount: 195000.00

  - stage_order: 10
    category: "remaining_exemption"
    label: "remaining exemption"
    input_amount: 102600.00
    impact_amount: 195000.00
    output_amount: 0.00
    details:
      remaining_before_floor: -92400.00
      zero_floor_applied: true

  - stage_order: 11
    category: "exempt_pension"
    label: "exempt pension"
    input_amount: 0.00
    output_amount: 0.00
```

Expected ValidationErrors: none

Status: LOCKED
## 6. AuditRow Correction Requirements

Confirmed:

* Any grant_impact AuditRow uses stage_order: 3.
* Any 15_year_exclusion AuditRow uses stage_order: 4.
* Any 32_year_ratio AuditRow uses stage_order: 5.
* future_grant_reserve uses stage_order: 6.
* actual_capitalization uses stage_order: 7.
* idf_treatment uses stage_order: 8.
* total_impact uses stage_order: 9.
* remaining_exemption uses stage_order: 10.
* exempt_pension uses stage_order: 11.

## 7. Validation-Only Cases

All validation-only cases remain unchanged.

For all validation-only cases:

* ValidationError only
* no successful FixationResult
* no AuditRows
* blocking: true
* path/code unchanged
* status: LOCKED

### GC11A

```yaml
case_name: "GC11A_VALIDATION_MISSING_GRANT_DATE"
expected_validation:
  - path: "grants[0].grant_date"
    code: "MISSING_REQUIRED_VALUE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC11B

```yaml
case_name: "GC11B_VALIDATION_MISSING_IDF_INPUT"
expected_validation:
  - path: "fixation_input"
    code: "INVALID_GLOBAL_INPUT"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC11C

```yaml
case_name: "GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT"
expected_validation:
  - path: "future_grant_reserved"
    code: "MISSING_REQUIRED_VALUE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC11D

```yaml
case_name: "GC11D_VALIDATION_INVALID_AMOUNT"
expected_validation:
  - path: "grants[0].indexed_amount"
    code: "INVALID_NESTED_ITEM"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC11E

```yaml
case_name: "GC11E_VALIDATION_INVALID_DATE"
expected_validation:
  - path: "grants[0].grant_date"
    code: "INVALID_DATE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC11F

```yaml
case_name: "GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT"
expected_validation:
  - path: "grants[0].work_start_date"
    code: "INVALID_DATE"
    blocking: true
  - path: "grants[0].work_end_date"
    code: "INVALID_DATE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC04D

```yaml
case_name: "GC04D_ZERO_WORK_PERIOD"
expected_validation:
  - path: "grants[0]"
    code: "INVALID_NESTED_ITEM"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

### GC04E

```yaml
case_name: "GC04E_MISSING_WORK_PERIOD_CONTEXT"
expected_validation:
  - path: "grants[0].work_start_date"
    code: "INVALID_DATE"
    blocking: true
  - path: "grants[0].work_end_date"
    code: "INVALID_DATE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 8. Corrected Golden Summary Matrix

| Case name                                      | Type            | Expected total impact | Expected remaining exemption | Expected exempt pension | Validation output if any                                          | Audit stage_order corrected | Status |
| ---------------------------------------------- | --------------- | --------------------: | ---------------------------: | ----------------------: | ----------------------------------------------------------------- | --------------------------- | ------ |
| GC01_BASE_CASE                                 | successful      |                  0.00 |                 1,026,000.00 |                5,700.00 | none                                                              | yes                         | LOCKED |
| GC02_SINGLE_GRANT_FULL_IMPACT                  | successful      |            135,000.00 |                   891,000.00 |                4,950.00 | none                                                              | yes                         | LOCKED |
| GC03A_15Y_ONE_DAY_BEFORE_BOUNDARY              | successful      |                  0.00 |                 1,026,000.00 |                5,700.00 | none                                                              | yes                         | LOCKED |
| GC03B_15Y_EXACTLY_ON_BOUNDARY                  | successful      |                  0.00 |                 1,026,000.00 |                5,700.00 | none                                                              | yes                         | LOCKED |
| GC03C_15Y_ONE_DAY_AFTER_BOUNDARY               | successful      |            135,000.00 |                   891,000.00 |                4,950.00 | none                                                              | yes                         | LOCKED |
| GC04A_32Y_FULL_PERIOD                          | successful      |            135,000.00 |                   891,000.00 |                4,950.00 | none                                                              | yes                         | LOCKED |
| GC04B_32Y_PARTIAL_PERIOD                       | successful      |             67,500.00 |                   958,500.00 |                5,325.00 | none                                                              | yes                         | LOCKED |
| GC04C_32Y_OVER_CAP                             | successful      |            135,000.00 |                   891,000.00 |                4,950.00 | none                                                              | yes                         | LOCKED |
| GC05_MULTIPLE_GRANTS                           | successful      |            175,500.00 |                   850,500.00 |                4,725.00 | none                                                              | yes                         | LOCKED |
| GC06_ACTUAL_CAPITALIZATION_IMPACT              | successful      |             60,000.00 |                   966,000.00 |                5,366.67 | none                                                              | yes                         | LOCKED |
| GC07_IDF_INFORMATIONAL_ONLY                    | successful      |                  0.00 |                 1,026,000.00 |                5,700.00 | none                                                              | yes                         | LOCKED |
| GC08_FUTURE_GRANT_RESERVE_ONLY                 | successful      |             67,500.00 |                   958,500.00 |                5,325.00 | none                                                              | yes                         | LOCKED |
| GC09_COMBINED_FULL_SCENARIO                    | successful      |            195,000.00 |                   831,000.00 |                4,616.67 | none                                                              | yes                         | LOCKED |
| GC10_ZERO_REMAINING_EXEMPTION                  | successful      |            195,000.00 |                         0.00 |                    0.00 | none                                                              | yes                         | LOCKED |
| GC11A_VALIDATION_MISSING_GRANT_DATE            | validation-only |                   n/a |                          n/a |                     n/a | grants[0].grant_date / MISSING_REQUIRED_VALUE                     | n/a                         | LOCKED |
| GC11B_VALIDATION_MISSING_IDF_INPUT             | validation-only |                   n/a |                          n/a |                     n/a | fixation_input / INVALID_GLOBAL_INPUT                             | n/a                         | LOCKED |
| GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT | validation-only |                   n/a |                          n/a |                     n/a | future_grant_reserved / MISSING_REQUIRED_VALUE                    | n/a                         | LOCKED |
| GC11D_VALIDATION_INVALID_AMOUNT                | validation-only |                   n/a |                          n/a |                     n/a | grants[0].indexed_amount / INVALID_NESTED_ITEM                    | n/a                         | LOCKED |
| GC11E_VALIDATION_INVALID_DATE                  | validation-only |                   n/a |                          n/a |                     n/a | grants[0].grant_date / INVALID_DATE                               | n/a                         | LOCKED |
| GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT   | validation-only |                   n/a |                          n/a |                     n/a | grants[0].work_start_date, grants[0].work_end_date / INVALID_DATE | n/a                         | LOCKED |
| GC04D_ZERO_WORK_PERIOD                         | validation-only |                   n/a |                          n/a |                     n/a | grants[0] / INVALID_NESTED_ITEM                                   | n/a                         | LOCKED |
| GC04E_MISSING_WORK_PERIOD_CONTEXT              | validation-only |                   n/a |                          n/a |                     n/a | grants[0].work_start_date, grants[0].work_end_date / INVALID_DATE | n/a                         | LOCKED |

## 9. Remaining Blockers

No Golden output remains blocked in this corrected artifact.

Golden values are ready for Supervisor approval.

Phase 4 execution remains blocked until separately authorized.

No coding is authorized.
