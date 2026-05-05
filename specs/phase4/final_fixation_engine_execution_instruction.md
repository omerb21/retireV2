# Final Phase 4 Fixation Engine Execution Instruction

## 1. Execution Control

- Current phase: Phase 4 Fixation Engine execution preparation
- Instruction type: final Supervisor-reviewable execution instruction
- Execution authorization status: not authorized by this instruction draft
- Coding authorization: no
- Purpose: define the final controlled execution instruction for deterministic Fixation Engine implementation, limited strictly to the approved Formula Lock and Golden Lock artifacts
- Supervisor review required: yes

This instruction draft does not start Phase 4 execution and must not be sent to the Coding Model unless the Supervisor separately approves final execution.

## 2. Approved Source Artifacts

Phase 4 execution, if Supervisor approves, must follow only these approved artifacts:

- Phase 1 domain contracts
- Phase 2 consolidated artifact package
- Phase 3 domain contract implementation
- targeted Phase 3 amendment
- approved Formula Lock
- approved Corrected Golden Calculation / Lock Artifact
- approved Final Golden Validation Payload Set
- approved Phase 4 Readiness / Execution Task Draft

No other source may be used as execution authority.

## 3. Execution Scope

If Supervisor approves this final execution instruction, the execution scope is limited strictly to:

- deterministic Fixation Engine implementation only
- approved contract inputs only
- approved contract outputs only
- approved formulas only
- approved AuditRows only
- approved validation failure behavior only
- approved Golden successful cases only
- approved Golden validation cases only

The engine must implement only what is required to satisfy the approved Golden successful and validation-only cases.

## 4. Implementation Requirements

The future execution must implement only the locked deterministic Fixation Engine behavior:

1. Initial entitlement
2. Grant impact
3. 15-year exclusion
4. 32-year ratio
5. Future grant reserve
6. Actual capitalization
7. IDF informational-only treatment
8. Total impact aggregation
9. Remaining exemption with zero floor
10. Exempt pension
11. AuditRows with locked stage_order
12. Validation failure output behavior

Implementation must follow the approved Formula Lock and Golden Lock exactly. No formula extension is allowed.

## 5. Validation Failure Requirements

On validation failure, return ValidationError only.
Do not return any FixationResult object, including FixationResult(status="validation_failed").
Do not generate AuditRows on validation failure.
All validation failures are blocking.

Validation failure behavior must match the approved Final Golden Validation Payload Set exactly:

- failed validation returns ValidationError only
- no FixationResult object of any kind on validation failure
- no AuditRows on validation failure
- all validation failures are blocking
- ValidationError.path and ValidationError.code must match the locked validation cases

Locked validation cases include:

- GC11A_VALIDATION_MISSING_GRANT_DATE
- GC11B_VALIDATION_MISSING_IDF_INPUT
- GC11C_VALIDATION_MISSING_FUTURE_RESERVE_AMOUNT
- GC11D_VALIDATION_INVALID_AMOUNT
- GC11E_VALIDATION_INVALID_DATE
- GC11F_VALIDATION_MISSING_WORK_PERIOD_CONTEXT
- GC04D_ZERO_WORK_PERIOD
- GC04E_MISSING_WORK_PERIOD_CONTEXT

## 6. Test Requirements

Allowed tests only:

- engine-level Golden successful case tests
- engine-level Golden validation-only case tests
- exact match to approved Golden outputs
- exact match to approved AuditRows and locked stage_order
- exact match to approved ValidationError.path and ValidationError.code

Forbidden test scope:

- no API tests
- no service/orchestration tests
- no DB/persistence tests
- no frontend/UI tests
- no report/PDF tests
- no scenario/cashflow/tax/pension module tests
- no LLM/agent tests
- no E2E tests
- no tests for unapproved formulas
- no tests for unapproved Golden cases

## 7. Forbidden Scope

The following are forbidden:

- API routes
- service/orchestration
- DB/persistence
- frontend/UI
- reports/PDF
- scenario/cashflow/tax/pension modules
- LLM/agent behavior
- external lookup
- CPI lookup
- fallback/default behavior
- current-date behavior
- V1 code copying
- V1 architecture adoption
- contract redesign
- broad refactor
- new formulas
- new Golden cases
- new validation categories
- hidden defaults
- inferred values
- mutation of previous results
- changes to Phase 1, Phase 2, Phase 3, or targeted amendment decisions

## 8. Stop Conditions

The executor must stop and report if:

- any approved Golden output cannot be matched
- contract change is required
- any approved formula is unclear
- API/service/UI/DB/persistence work is required
- frontend work is required
- CPI lookup is required
- external lookup is required
- fallback/default behavior is needed
- hidden default or inferred value is required
- new business decision is needed
- V1 code copying is needed
- V1 architecture adoption is needed
- broad refactor is needed
- validation failure would produce any FixationResult object
- validation failure would produce AuditRows
- test behavior conflicts with approved Golden Lock
- implementation requires adding a new validation category
- implementation requires adding a new Golden case

No workaround is allowed for a stop condition.

## 9. Required Execution Report

```text
Phase 4 Fixation Engine Execution Report

Task Summary
- What was implemented:
- What was intentionally not implemented:

Phase Alignment
- Current phase:
- Approved artifacts followed:
- Scope boundaries respected: yes/no

Files / Areas Changed
- Files changed:
- Engine files changed:
- Contract files changed:
- API/service/UI/DB/frontend/persistence files changed:

Tests
- Tests added/changed:
- Exact test command run:
- Full test output:
- Golden successful cases passed:
- Golden validation cases passed:
- Result:

Golden Case Coverage
- Successful Golden cases passed:
- Validation-only Golden cases passed:
- Any Golden mismatch:

Scope Compliance
- Formulas added beyond lock:
- Contract changes:
- API/service/UI/DB/frontend/persistence changes:
- CPI lookup:
- External lookup:
- Fallback/default behavior:
- V1 code copied:
- Broad refactor:

Behavior Notes
- Business behavior changed outside approved Formula Lock:
- AuditRows generated on validation failure:
- Successful FixationResult generated on validation failure:

Open Questions
- ...

Final Status
- Phase 4 execution completed:
- Blockers:
```
