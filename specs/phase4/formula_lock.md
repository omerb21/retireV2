# Updated Phase 4 Formula and Golden Case Lock Document

## 1. Lock Control

- Current phase: Phase 4 planning / Formula and Golden Case Lock
- Document type: updated Formula and Golden Case Lock documentation
- Execution status: Phase 4 execution remains blocked
- Coding authorization: no
- Purpose: incorporate all approved business decisions into a single lock document so Supervisor can decide whether Formula Lock is ready for approval and whether Golden Case definition may proceed
- Supervisor review required: yes

This document does not authorize coding, does not start Phase 4 execution, does not write engine implementation instructions, does not modify contracts, and does not create implementation prompts.

## 2. Approved Source Decisions

The following decisions are approved and incorporated into this document:

1. No fallback/default behavior.
2. No CPI lookup inside the engine.
3. Engine receives explicit indexed/effective input or deterministic explicit indexation input.
4. 15-year boundary convention approved.
5. 32-year ratio convention approved.
6. Rounding baseline approved.
7. AuditRow.stage_order available.
8. Failed validation returns ValidationError only.
9. No audit rows on failed validation.
10. Actual capitalization treatment approved.
11. IDF informational-only treatment approved.
12. Future reserve amount basis and impact treatment approved.
13. Grant multiplier locked at 1.35.
14. Future reserve multiplier locked at 1.35 if exemption-consuming grant-like reserve.

Approved multiplier application order:

1. Start with explicit indexed/effective amount.
2. Apply the 15-year exclusion rule.
3. Apply the 32-year ratio / qualifying limitation, if applicable.
4. Apply the 1.35 multiplier to the qualifying impact amount.
5. Include the resulting impact in total impact.
6. Reduce remaining exemption through total impact.
7. Exempt pension is affected only through reduced remaining exemption.

## 3. Formula Lock - Initial Entitlement

### Approved formula

Initial entitlement is calculated from the approved deterministic contract inputs:

initial_entitlement = monthly_cap × exemption_percentage × capital_multiplier

At this lock level:

- no CPI lookup is allowed
- no hidden current-date default is allowed
- no fallback source value is allowed
- required source values must be explicit and deterministic

### Required inputs

- monthly_cap
- exemption_percentage
- capital_multiplier
- eligibility_date
- eligibility_year

### Outputs affected

- initial entitlement result component
- remaining exemption
- exempt pension
- AuditRow

### Rounding

- no unapproved intermediate rounding
- final money outputs rounded to 2 decimals
- audit displayed values follow approved audit/output rounding policy

### AuditRow expectation

AuditRow should record:

- stage_order
- stage/category: initial entitlement
- input/source amount
- output amount
- relevant details

### Status

LOCKED

## 4. Formula Lock - Grant Impact

### Approved formula

Grant impact uses explicit indexed/effective grant amount.

Formula sequence:

1. Start with explicit indexed/effective grant amount.
2. Apply the 15-year exclusion rule.
3. Apply the 32-year ratio / qualifying limitation where applicable.
4. Apply multiplier 1.35 to the qualifying impact amount.
5. Include resulting impact in total impact.
6. Reduce remaining exemption through total impact.
7. Affect exempt pension only through reduced remaining exemption.

### Required inputs

- explicit indexed/effective grant amount
- grant date
- eligibility date
- work-period / qualifying limitation context where applicable
- deterministic input required for ratio calculation
- no CPI lookup inside engine

### Outputs affected

- grant impact component
- total impact
- remaining exemption
- exempt pension
- AuditRow

### AuditRow details

AuditRow should identify:

- component type: historical grant
- pre-multiplier amount
- 15-year inclusion/exclusion result
- ratio_32y detail where applicable
- multiplier value: 1.35
- post-multiplier impact
- effect on total impact and remaining exemption

### Rounding

- no unapproved intermediate rounding
- final money outputs rounded to 2 decimals
- audit displayed values follow approved audit/output rounding policy

### Status

LOCKED

## 5. Formula Lock - 15-Year Exclusion

### Compared dates

- Grant payment/event date
- Eligibility date

### Boundary date logic

The boundary is determined relative to the eligibility date according to the approved 15-year convention.

### Included / excluded behavior

- Grant before the approved 15-year impact window is excluded from grant impact.
- Grant exactly on the boundary date is excluded for the approved Golden cases.
- Grant after the boundary date is included in grant impact.

### Validation behavior for missing grant date

- Missing grant date blocks validation.
- No fallback to work end date.
- No inferred grant date.

### AuditRow expectation

AuditRow should record:

- stage_order
- grant date
- eligibility date
- boundary result
- included/excluded status
- relevant amount affected

### Status

LOCKED

## 6. Formula Lock - 32-Year Ratio

### Approved convention

- Denominator: 32 years.
- Numerator: qualifying work-period context.
- Cap: 1.0.
- Floor: 0.0.
- Invalid or missing work-period context blocks validation.
- ratio_32y is AuditRow detail only, not a formal result output.

### Required inputs

- explicit qualifying work-period context
- no hidden retirement-age fallback
- no exception-to-zero fallback

### Rounding / display

- internal ratio follows approved deterministic calculation policy
- displayed/audit ratio follows approved rounding baseline
- no unapproved intermediate rounding

### AuditRow expectation

AuditRow should record:

- stage_order
- stage/category: 32-year ratio
- qualifying work-period context
- denominator: 32 years
- ratio_32y detail
- cap/floor application where applicable

### Status

LOCKED

## 7. Formula Lock - Future Grant Reserve

### Approved formula

Future grant reserve is a separate exemption-consuming component when classified as grant-like reserve.

Formula sequence:

1. Start with explicit effective/indexed future reserve amount or deterministic explicit input.
2. No CPI lookup inside engine.
3. No fallback from missing reserve amount.
4. Apply multiplier 1.35 if classified as exemption-consuming grant-like reserve.
5. Include resulting impact in total impact.
6. Reduce remaining exemption through total impact.
7. Affect exempt pension only through reduced remaining exemption.

### Required inputs

- future_grant_reserved scalar
- no current-date default
- missing reserve amount blocks validation

### Outputs affected

- future reserve component
- total impact
- remaining exemption
- exempt pension
- AuditRow

### AuditRow details

AuditRow should identify:

- stage_order
- component type: future reserve
- amount basis
- pre-multiplier amount
- multiplier value: 1.35, if applicable
- post-multiplier impact
- effect on remaining exemption

### Rounding

- no unapproved intermediate rounding
- final money outputs rounded to 2 decimals
- audit displayed values follow approved audit/output rounding policy

### Status

LOCKED

## 8. Formula Lock - Actual Capitalization

### Approved formula

Actual capitalization uses explicit effective amount supplied in input.

Formula policy:

- no multiplier by default
- multiple events are summed by effective impacts before final output rounding
- date is validation/context/audit only unless later approved otherwise
- included in total impact
- reduces remaining exemption through total impact
- affects exempt pension only through reduced remaining exemption

### Required inputs

- explicit amount per event
- capitalization_date
- per-event structure
- multiple-event collection where applicable

### Outputs affected

- actual capitalization component
- total impact
- remaining exemption
- exempt pension
- AuditRow

### AuditRow expectation

AuditRow should record:

- stage_order
- component type: actual capitalization
- event details
- effective amount
- summed impact
- effect on total impact and remaining exemption

### Status

LOCKED

## 9. Formula Lock - IDF Informational Treatment

### Approved treatment

IDF is informational only.

It:

- does not enter total impact
- does not reduce remaining exemption
- does not affect exempt pension
- has informational output through IDFResult
- uses the IDFResult informational-only marker
- uses the FixationInput IDF-relevant marker for conditional requiredness

### Validation behavior

- invalid or missing required IDF input blocks validation
- no V1-style zero impact with error
- no fallback/default behavior

### AuditRow expectation

For valid successful calculations, AuditRow should record:

- stage_order
- stage/category: IDF treatment
- IDF informational-only status
- no effect on total impact
- no effect on remaining exemption
- no effect on exempt pension

### Status

LOCKED

## 10. Formula Lock - Total Impact Aggregation

### Components included

Total impact includes:

- historical grant impact after 15-year exclusion, ratio/qualifying limitation, and multiplier 1.35
- future grant reserve impact if exemption-consuming grant-like reserve, including multiplier 1.35
- actual capitalization impact
- any other explicitly approved exemption-consuming component

### Components excluded

Total impact excludes:

- IDF informational-only result
- validation errors
- audit-only details
- fallback/default values
- any unapproved component

### Ordering

Approved audit order:

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

### Rounding

- no unapproved intermediate rounding
- final money outputs rounded to 2 decimals
- audit displayed values follow approved audit/output rounding policy

### AuditRow expectation

AuditRow should record:

- included components
- excluded informational components
- total impact amount
- effect on remaining exemption

### Status

LOCKED

## 11. Formula Lock - Remaining Exemption

### Source values

Remaining exemption uses:

- initial entitlement
- total impact

### Approved convention

remaining_exemption = initial_entitlement - total_impact

### Zero floor behavior

Remaining exemption may not go below zero.

If total impact exceeds initial entitlement:

- remaining exemption is zero
- excess negative result is not carried into exempt pension
- audit should show the floor effect

### Rounding

- final money output rounded to 2 decimals
- no unapproved intermediate rounding

### AuditRow expectation

AuditRow should record:

- stage_order
- initial entitlement
- total impact
- remaining exemption before floor, if relevant
- remaining exemption after floor

### Status

LOCKED

## 12. Formula Lock - Exempt Pension

### Source values

Exempt pension is derived from remaining exemption according to the approved conversion convention:

exempt_pension = remaining_exemption / capital_multiplier

### Relationship to remaining exemption

- exempt pension is affected only through remaining exemption
- reductions caused by grant impact, future reserve, or actual capitalization affect exempt pension only by reducing remaining exemption
- IDF informational-only result does not affect exempt pension

### Rounding

- final money output rounded to 2 decimals
- no unapproved intermediate rounding

### AuditRow expectation

AuditRow should record:

- stage_order
- remaining exemption source
- conversion basis
- exempt pension output

### Status

LOCKED

## 13. Validation Failure Output Policy

### Approved policy

On validation failure, return ValidationError only.
Do not return any FixationResult object, including FixationResult(status="validation_failed").
Do not generate AuditRows on validation failure.
All validation failures are blocking.

Additional locked rules:

- Stable error paths and codes must be used.
- Missing required fields block validation.
- Invalid dates/numbers block validation.
- Invalid/missing required IDF input blocks validation.
- Missing required reserve amount blocks validation.
- Missing deterministic indexation input blocks validation if required.

### Status

LOCKED

## 14. Audit Row Lock

### Approved audit stages

The approved audit stage baseline is:

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

### stage_order usage

Each AuditRow must include stage_order.

- lower order appears earlier
- order is deterministic
- stage_order supports reproducibility and Golden audit expectations

### Required audit detail per stage

Audit rows should include relevant details for:

- input/source amount
- output amount
- impact amount
- component type
- included/excluded status
- ratio_32y where applicable
- multiplier value where applicable
- pre-multiplier amount where applicable
- post-multiplier impact where applicable
- effect on remaining exemption where applicable

### Multiplier audit detail

Grant and future reserve AuditRows must identify:

- pre-multiplier amount
- multiplier value: 1.35
- post-multiplier impact
- component type

### ratio_32y audit detail

ratio_32y appears only in AuditRow detail, not as formal result output.

### IDF informational detail

IDF AuditRow must identify:

- informational-only treatment
- no effect on total impact
- no effect on remaining exemption
- no effect on exempt pension

### Future reserve audit detail

Future reserve AuditRow must include:

- amount basis
- multiplier used, if any
- impact amount
- effect on remaining exemption

### Status

LOCKED

## 15. Golden Case Readiness

Golden Cases can now be prepared for Supervisor review, but only from:

- locked formulas
- deterministic explicit inputs
- approved rounding policy
- approved audit stage_order rules
- approved validation failure policy

No Golden value may be invented without exact case input payload and locked formula application.

Golden Case preparation remains documentation/lock work only. It does not authorize Phase 4 execution or engine implementation.

## 16. Required Golden Case Matrix

| Golden Case | Required content | Status |
|---|---|---|
| base case | exact input payload, expected FixationResult, expected AuditRows with stage_order, rounding assumptions | READY TO DEFINE |
| single grant full impact | explicit indexed/effective grant amount, multiplier 1.35, expected impact, audit details | READY TO DEFINE |
| 15-year exclusion boundaries | inside / outside / exactly-on-boundary inputs, expected inclusion/exclusion, audit rows | READY TO DEFINE |
| 32-year ratio boundaries | full, partial, capped, invalid/missing context cases, ratio_32y audit detail | READY TO DEFINE |
| multiple grants | explicit amounts/dates, mixed exclusion status, total grant impact, audit rows | READY TO DEFINE |
| actual capitalization impact | explicit effective amount, event date, impact, audit row, remaining exemption effect | READY TO DEFINE |
| IDF informational-only case | IDF-relevant marker, IDFResult informational-only marker, no total impact effect, audit row | READY TO DEFINE |
| future grant reserve only | explicit effective/indexed reserve amount, multiplier 1.35 if grant-like, impact, audit row | READY TO DEFINE |
| combined full scenario | grants, future reserve, actual capitalization, IDF informational-only, total impact, remaining exemption, exempt pension | READY TO DEFINE |
| zero remaining exemption | total impact exceeds entitlement, zero floor, audit row | READY TO DEFINE |
| validation failure cases | expected ValidationErrors only, no FixationResult success, no AuditRows | READY TO DEFINE |

## 17. Remaining Blockers

No remaining business formula blocker is identified in this document.

Formula Lock is ready for Supervisor approval.

Golden Case values are not yet written in this document. They may now be prepared as a separate Golden Case Matrix/Lock artifact using the locked formulas and exact deterministic input payloads.

Phase 4 execution remains blocked until separately authorized after Formula and Golden Case Lock approval.
