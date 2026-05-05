# Phase 4 Readiness / Execution Task Draft - Fixation Engine

## 1. Task Control

- Current phase: Phase 4 readiness / execution drafting
- Draft type: Supervisor-reviewable execution task draft
- Execution authorization status: not authorized by this draft
- Coding authorization: no
- Purpose: define the controlled future Phase 4 execution scope for deterministic Fixation Engine implementation, based only on the approved Formula Lock and Golden Lock artifacts
- Supervisor review required: yes

This draft does not authorize coding, does not start Phase 4 execution, and must not be sent to the Coding Model unless separately approved by the Supervisor.

## 2. Approved Source Artifacts

Future Phase 4 execution must follow only these approved sources:

- Phase 1 domain contracts
- Phase 2 consolidated artifact package
- Phase 3 domain contract implementation
- targeted Phase 3 amendment
- approved Formula Lock
- approved Corrected Golden Calculation / Lock Artifact
- approved Final Golden Validation Payload Set

No other behavior source is authorized for Phase 4 execution.

## 3. Readiness Confirmation

Confirmed readiness state:

- formulas locked
- successful Golden outputs locked
- validation-only Golden cases locked
- AuditRow.stage_order locked
- no Golden blockers remain
- validation path/code blockers resolved
- Phase 4 execution still requires explicit Supervisor approval
- no coding is authorized by this readiness draft

## 4. Proposed Phase 4 Execution Scope

If later approved by Supervisor, Phase 4 execution must be limited strictly to:

- deterministic Fixation Engine implementation
- approved Formula Lock only
- approved contract inputs only
- approved contract outputs only
- approved AuditRows only
- approved validation failure behavior only
- approved Golden cases as engine-level verification only

The engine must implement only the locked behavior needed to satisfy the approved successful and validation-only Golden cases.

## 5. Explicit Out-of-Scope Items

The following are excluded:

- API routes
- service/orchestration implementation
- DB/persistence
- frontend/UI
- reports/PDF
- scenario/cashflow/tax/pension modules
- LLM/agent behavior
- external lookup
- CPI lookup
- fallback/default behavior
- V1 code copying
- contract redesign
- broad refactor
- unrelated contract amendments
- additional business formulas
- new Golden cases
- new validation categories
- current-date based behavior

## 6. Implementation Boundary

The future engine implementation must comply with these boundaries:

- engine must be deterministic
- no current date
- no external API
- no CPI lookup
- no inferred values
- no hidden defaults
- no mutation of previous results
- no V1 code copying
- no V1 architecture adoption
- no fallback/default behavior
- failed validation returns ValidationError only
- no FixationResult object of any kind on validation failure, including FixationResult(status="validation_failed")
- no AuditRows on validation failure
- successful calculations must produce expected FixationResult
- successful calculations must produce approved AuditRows with locked stage_order

## 7. Test Boundary

Allowed tests only:

- engine-level tests for approved Golden successful cases
- engine-level tests for approved validation-only cases

Forbidden tests:

- no API tests
- no DB tests
- no UI tests
- no service/orchestration tests
- no E2E tests
- no report/PDF tests
- no scenario/cashflow/tax/pension module tests
- no LLM/agent tests
- no tests requiring external lookup
- no tests requiring CPI lookup
- no tests that add unapproved formulas or behaviors

## 8. Required Execution Report Format

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

## 9. Stop Conditions

The future executor must stop and report if:

* any approved formula is unclear
* any Golden expected output cannot be matched
* contract change is required
* API/service/UI/DB/persistence work is required
* frontend work is required
* CPI lookup is required
* external lookup is required
* fallback/default behavior is needed
* V1 code copying is needed
* V1 architecture adoption is needed
* new business decision is required
* test behavior conflicts with Golden Lock
* validation failure would produce any FixationResult object
* validation failure would produce AuditRows
* implementation would require hidden default or inferred value
* implementation would require broad refactor
* implementation would require changing Phase 1, Phase 2, Phase 3, or targeted amendment decisions

No workaround is allowed for a stop condition.
