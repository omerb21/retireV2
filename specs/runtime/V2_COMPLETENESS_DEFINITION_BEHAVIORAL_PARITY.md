# V2 Completeness Definition: Behavioral Parity

## 1. Current Correction Statement

The previous proof stack is valid but insufficient for the user's intended meaning of completeness.

It proves:

- V1 evidence items are mapped to the Required Capability Universe or explicitly classified.
- Required Capability Universe items are mapped to the V2 planning controls.

It does not prove:

- identical formulas;
- identical business rules;
- identical calculation paths;
- identical edge-case behavior;
- identical rounding;
- identical inputs or outputs;
- identical generated documents;
- behavioral equivalence;
- V1 parity; or
- implementation readiness.

Capability coverage is therefore a necessary proof layer, but it is not the definition of full V1-to-V2 planning completeness.

## 2. Correct Definition of Complete V2 Build Plan

A V2 build plan is complete only when every discovered V1 capability has all of the following:

### A. Capability Coverage

The V1 item maps to an existing Universe Requirement ID or has an explicit justified classification.

### B. Behavioral Contract

The V1 behavior is described with enough specificity to prevent title-only coverage. The contract must identify observable behavior, not merely a feature name, domain label, heading, milestone, or gap row.

### C. Formula/Rule Contract Where Applicable

Every applicable calculation, tax rule, indexation rule, exemption rule, pension rule, scenario rule, report rule, validation rule, and decision rule must be captured explicitly. The contract must preserve the calculation path and rule conditions needed to reproduce expected behavior.

### D. Parity Mode

Each behavior must use exactly one applicable parity mode:

- `EXACT_MATCH_REQUIRED`
- `NUMERIC_TOLERANCE_ALLOWED`
- `STRUCTURAL_EQUIVALENCE_ALLOWED`
- `INTENTIONAL_CHANGE_REQUIRED`
- `NOT_APPLICABLE_WITH_REASON`

### E. Evidence Requirement

The behavior must be backed by one or more named sources: V1 source, route evidence, test evidence, runtime evidence, expected output, or an explicit manual domain decision. Similar wording is not evidence of equivalence.

### F. Test Requirement

For calculation, report, scenario, tax, and fixation logic, the future plan must require a golden-master test or another explicit expected-behavior test. The test source, inputs, expected output, precision, and permitted tolerance must be named.

### G. Change Control

Any intentional change from V1 must document:

- the exact changed behavior;
- the reason for the change;
- the prior V1 evidence;
- the required V2 behavior;
- the decision owner;
- the approval status; and
- the tests required to prevent an accidental change from being presented as intentional.

No intentional change is approved merely because it appears in a map or planning document.

## 3. Invalid Completeness Definitions

The following definitions are invalid:

- "Complete" cannot mean only that a V1 capability is mapped to a REQ.
- "Complete" cannot mean only that the Universe is mapped to the plan.
- "Complete" cannot mean there is a heading, milestone, or gap row.
- "Complete" cannot mean a future package will figure out the behavior.
- "Complete" cannot rely on similar wording between V1 and V2.
- "Complete" cannot be claimed before behavioral, formula, and rule parity mapping exists.

Accordingly, the current capability and requirement-mapping proofs must not be described as full V1-to-V2 planning completeness.

## 4. Required Next Proof Layer

Required next proof layer:

`V2-REQ-08_V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP`

Purpose:

Create a V1 behavior, formula, and rule inventory and map every evidenced behavior to the required V2 behavior or to an explicit justified disposition.

Required status for each V1 behavior:

- `BEHAVIOR_EXACT_MATCH_REQUIRED`
- `BEHAVIOR_NUMERIC_TOLERANCE_ALLOWED`
- `BEHAVIOR_STRUCTURAL_EQUIVALENCE_ALLOWED`
- `BEHAVIOR_INTENTIONAL_CHANGE_REQUIRED`
- `BEHAVIOR_NOT_APPLICABLE_WITH_REASON`
- `BEHAVIOR_UNMAPPED_FAIL`

Any `BEHAVIOR_UNMAPPED_FAIL` blocks planning completeness. The existence of this required next layer does not authorize that package or any implementation package; separate explicit authority remains required.

## 5. Mandatory Behavior Contract Fields

Every future V2-REQ-08 behavior row must include:

| Field | Requirement |
|---|---|
| V1 Behavior ID | Stable unique identifier. |
| Related V1ITEM ID | Link to the existing V1-origin inventory item. |
| V1 capability / route / function / test / evidence source | Exact named evidence reference. |
| Business behavior summary | Observable business behavior, not a title. |
| Input fields | Complete named input set, including units and optionality where evidenced. |
| Output fields | Complete named output set, including units and structure where evidenced. |
| Formula / calculation rule if any | Exact formula, sequence, parameter source, and conditions. |
| Business rule if any | Exact rule, trigger, branch, and consequence. |
| Edge cases | Boundaries, missing data, zero/negative values, dates, and exceptional branches. |
| Rounding / precision | Scale, rounding mode, intermediate precision, final precision, and tolerance. |
| Error and validation behavior | Validation trigger, error/warning result, and blocking behavior. |
| Generated document/report behavior if any | Fields, layout-significant content, calculations, and output structure. |
| Required V2 behavior | Explicit behavior V2 must preserve or intentionally change. |
| Parity mode | One permitted behavior parity status. |
| Golden test required: YES/NO | Mandatory decision with rationale when NO. |
| Expected output source | Named V1 fixture, test, runtime artifact, document, or approved decision. |
| Mapped Universe Requirement ID(s) | Existing REQ identifiers only. |
| Mapped gap / milestone / package | Named planning destination without creating execution authority. |
| Status | Current proof status of the behavior row. |
| Reviewer decision required: YES/NO | Explicit review gate. |
| Notes | Evidence limits, dependencies, and unresolved questions. |

## 6. High-Risk Domains Requiring Behavior Contracts

Behavior contracts are mandatory for at least these high-risk domains:

- Fixation rights / 161D
- Severance grants
- Exemptions
- Commutation / capitalization
- Pension coefficient / annuity logic
- Pension portfolio calculations
- Capital asset conversion
- Indexation / CPI / historical values
- Tax brackets / marginal tax / annual parameters
- Prisa / spreading, if present in V1 evidence
- Scenario generation
- Scenario comparison
- Cashflow
- Reports / PDF / generated forms
- Validation / missing information / warnings
- Planner recommendation rules
- Audit / traceability behavior

Presence in this list is not implementation authorization. Each domain still requires exact V1 evidence, a behavior-level mapping, and its own later package authority.

## 7. Updated Project Status

V1 capability coverage:
MACHINE_VERIFIED_PASS

Universe to plan mapping:
MACHINE_VERIFIED_PASS

V1 behavioral/formula/rule parity:
NOT_PROVEN

Full V1-to-V2 planning completeness:
NOT_PROVEN

Execution phase:
BLOCKED

02M:
FROZEN

## 8. Official Allowed Statement After This Package

Allowed:

"The project has machine-verified V1 capability coverage and machine-verified Universe-to-plan mapping, but full V1-to-V2 planning completeness remains blocked until V1 behavioral/formula/rule parity is mapped and verified."

Forbidden:

- "The V2 build plan is complete."
- "The plan is fully complete against V1."
- "V1 parity is planned."
- "Implementation can begin."
- "02M can be unfrozen."

## 9. Final Marker

V2_COMPLETENESS_REDEFINED_AS_BEHAVIORAL_PARITY
