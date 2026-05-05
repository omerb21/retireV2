# Final Golden Validation Payload Set - Phase 4 Fixation Engine

## 1. Validation Payload Set Control

- Current phase: Phase 4 planning / Golden validation payload lock
- Artifact type: final validation-only Golden payload set
- Execution status: Phase 4 execution remains blocked
- Coding authorization: no
- Formula Lock status: approved
- Golden values status: approved and locked for validation-only cases
- Purpose: incorporate all Supervisor-approved validation payloads and approved ValidationError.path / ValidationError.code outputs into one final validation-only Golden payload set
- Supervisor review required: yes

This artifact does not authorize coding, does not start Phase 4 execution, does not calculate Golden numerical values, does not create successful FixationResult, does not create AuditRows for validation failures, does not modify contracts, and does not add tests.

## 2. Approved Validation Policy

On validation failure, return ValidationError only.
Do not return any FixationResult object, including FixationResult(status="validation_failed").
Do not generate AuditRows on validation failure.
All validation failures are blocking.

Confirmed validation policy:

- failed validation returns ValidationError only
- no successful FixationResult on validation failure
- no AuditRows on validation failure
- all validation errors are blocking
- stable path/code must match the Supervisor-approved results
- no fallback/default correction is allowed
- no inferred value is allowed

## 3. Approved Validation Cases Included

This final validation payload set includes:

- GC11A_VALIDATION_MISSING_GRANT_DATE
- GC11B_VALIDATION_MISSING_IDF_INPUT
- GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT
- GC11D_VALIDATION_INVALID_AMOUNT
- GC11E_VALIDATION_INVALID_DATE
- GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT
- GC04D_ZERO_WORK_PERIOD
- GC04E_MISSING_WORK_PERIOD_CONTEXT

## 4. Final Validation Payload - GC11A_VALIDATION_MISSING_GRANT_DATE

```yaml
case_name: "GC11A_VALIDATION_MISSING_GRANT_DATE"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "invalid_missing_grant_date"
      grant_date: null
      indexed_amount: 100000.00
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
expected_validation:
  - path: "grants[0].grant_date"
    code: "MISSING_REQUIRED_VALUE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 5. Final Validation Payload - GC11B_VALIDATION_MISSING_IDF_INPUT

```yaml
case_name: "GC11B_VALIDATION_MISSING_IDF_INPUT"
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
  idf: null
expected_validation:
  - path: "fixation_input"
    code: "INVALID_GLOBAL_INPUT"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 6. Final Validation Payload - GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT

```yaml
case_name: "GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants: []
  actual_capitalizations: []
  idf: null
expected_validation:
  - path: "future_grant_reserved"
    code: "MISSING_REQUIRED_VALUE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

Note: future_grant_reserved is intentionally omitted.

## 7. Final Validation Payload - GC11D_VALIDATION_INVALID_AMOUNT

```yaml
case_name: "GC11D_VALIDATION_INVALID_AMOUNT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "invalid_negative_amount"
      indexed_amount: -1000.00
      grant_date: "2024-01-01"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
expected_validation:
  - path: "grants[0].indexed_amount"
    code: "INVALID_NESTED_ITEM"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 8. Final Validation Payload - GC11E_VALIDATION_INVALID_DATE

```yaml
case_name: "GC11E_VALIDATION_INVALID_DATE"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "invalid_date_grant"
      indexed_amount: 100000.00
      grant_date: "not-a-date"
      work_start_date: "1994-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
expected_validation:
  - path: "grants[0].grant_date"
    code: "INVALID_DATE"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 9. Final Validation Payload - GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT

```yaml
case_name: "GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "invalid_missing_work_period"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: null
      work_end_date: null
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
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

## 10. Final Validation Payload - GC04D_ZERO_WORK_PERIOD

```yaml
case_name: "GC04D_ZERO_WORK_PERIOD"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_zero_work_period"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: "2026-01-01"
      work_end_date: "2026-01-01"
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
expected_validation:
  - path: "grants[0]"
    code: "INVALID_NESTED_ITEM"
    blocking: true
successful_fixation_result: false
audit_rows: []
status: "LOCKED"
```

## 11. Final Validation Payload - GC04E_MISSING_WORK_PERIOD_CONTEXT

```yaml
case_name: "GC04E_MISSING_WORK_PERIOD_CONTEXT"
input_payload:
  monthly_cap: 10000.00
  exemption_percentage: 0.57
  capital_multiplier: 180
  eligibility_date: "2026-01-01"
  eligibility_year: 2026
  idf_relevant: false
  grants:
    - grant_id: "grant_missing_work_period_context"
      indexed_amount: 100000.00
      grant_date: "2024-01-01"
      work_start_date: null
      work_end_date: null
  future_grant_reserved: 0.00
  actual_capitalizations: []
  idf: null
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

## 12. Validation Payload Summary Table

| Case name                                      | Expected path(s)                                   | Expected code(s)           | Blocking | Successful FixationResult produced | AuditRows produced | Status |
| ---------------------------------------------- | -------------------------------------------------- | -------------------------- | -------- | ---------------------------------- | ------------------ | ------ |
| GC11A_VALIDATION_MISSING_GRANT_DATE            | grants[0].grant_date                               | MISSING_REQUIRED_VALUE     | yes      | no                                 | no                 | LOCKED |
| GC11B_VALIDATION_MISSING_IDF_INPUT             | fixation_input                                     | INVALID_GLOBAL_INPUT       | yes      | no                                 | no                 | LOCKED |
| GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT | future_grant_reserved                              | MISSING_REQUIRED_VALUE     | yes      | no                                 | no                 | LOCKED |
| GC11D_VALIDATION_INVALID_AMOUNT                | grants[0].indexed_amount                           | INVALID_NESTED_ITEM        | yes      | no                                 | no                 | LOCKED |
| GC11E_VALIDATION_INVALID_DATE                  | grants[0].grant_date                               | INVALID_DATE               | yes      | no                                 | no                 | LOCKED |
| GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT   | grants[0].work_start_date; grants[0].work_end_date | INVALID_DATE; INVALID_DATE | yes      | no                                 | no                 | LOCKED |
| GC04D_ZERO_WORK_PERIOD                         | grants[0]                                          | INVALID_NESTED_ITEM        | yes      | no                                 | no                 | LOCKED |
| GC04E_MISSING_WORK_PERIOD_CONTEXT              | grants[0].work_start_date; grants[0].work_end_date | INVALID_DATE; INVALID_DATE | yes      | no                                 | no                 | LOCKED |

## 13. Remaining Blockers

* No validation path/code blockers remain.
* Golden numerical values are locked in the corrected Golden Calculation / Lock Artifact.
* Phase 4 execution remains blocked until separately authorized.
* No coding is authorized.
