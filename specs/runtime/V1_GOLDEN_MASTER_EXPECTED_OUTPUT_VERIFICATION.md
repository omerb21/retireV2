# V1 Golden Master Expected Output Verification

## Purpose

This is the missing expected-output proof layer after V2-REQ-08. V1 behavior-contract mapping was necessary but was not enough to prove future runtime equivalence, because a behavior contract without a concrete input and expected result cannot serve as an executable comparison oracle.

Golden-master expected-output coverage is verified only because the dedicated case map and verifier pass.

## Evidence Basis

The package read the six required V1 evidence files and inspected the V1 source archive in place without extracting or modifying it. Archive inspection identified 329 fixture, snapshot, report, PDF, scenario, cashflow, fixation, tax, coefficient, or portfolio candidates. Named assertions were inspected for 161D field mapping, PDF fallback and RTL shaping, cashflow grid/result validation, pension-portfolio gap consistency, and route validation errors.

Concrete arithmetic cases are direct reconstructions of named V1 formulas. Generated-output cases assert source-backed fields, formats, content, ownership, RTL behavior, and artifact validity rather than invented binary output.

## Golden Verifier Result

Command:

```text
python scripts/verify_v1_golden_master_expected_outputs.py
```

Result:

```text
result=PASS
golden_cases_checked=35
golden_case_missing_fail=0
manual_domain_decisions=0
behaviors_with_required_golden_tests_checked=35
req_references_checked=175
v1behavior_references_checked=35
v1item_references_checked=61
high_risk_domains_checked=17
```

## Golden Verifier Mutation Tests

Command:

```text
pytest tests/test_verify_v1_golden_master_expected_outputs.py -q
```

Result:

```text
.............                                                            [100%]
13 passed in 4.41s
```

The mutation suite proves fail-closed behavior for missing and manual-decision statuses, unknown REQ/V1BEHAVIOR/V1ITEM references, empty concrete input/expected result/test type, lost required-behavior coverage, missing high-risk domains, invalid final marker, and duplicate Golden Case IDs.

## Prior Proof Layers Re-run

### Behavior/Formula/Rule Mapping

```text
V1_BEHAVIOR_FORMULA_RULE_PARITY_VERIFICATION_PASS
v1_behaviors_checked=35
behavior_unmapped_fail=0
req_references_checked=175
v1item_references_checked=61
formula_rows_checked=29
golden_tests_required=33
high_risk_domains_checked=17
```

Tests:

```text
14 passed in 3.74s
```

### V1 -> Universe Capability Coverage

```text
V1_TO_UNIVERSE_EXHAUSTIVENESS_VERIFICATION_PASS
v1_items_checked=494
v1_unmapped_fail=0
req_references_checked=2497
excluded_or_not_applicable=11
replaced_or_duplicate=16
```

Tests:

```text
8 passed in 2.53s
```

### Universe -> Plan Mapping

```text
MACHINE_UNIVERSE_COVERAGE_VERIFICATION_PASS
requirements_checked=137
failed_requirements=0
req_unmapped=0
ledger_rows=113
gap_rows=96
domain_decisions=4
```

Tests:

```text
8 passed in 2.46s
```

## Exact Coverage Counts

| Measure | Count |
|---|---:|
| Golden cases | 35 |
| GOLDEN_CASE_READY | 34 |
| GOLDEN_CASE_INTENTIONAL_CHANGE_REQUIRED | 1 |
| GOLDEN_CASE_MISSING_FAIL | 0 |
| GOLDEN_CASE_MANUAL_DOMAIN_DECISION_REQUIRED | 0 |
| Required behaviors covered | 35 |
| High-risk domains | 17 |
| REQ references | 175 |
| V1BEHAVIOR references | 35 |
| V1ITEM references | 61 |

## What This Proves

- Every required behavior in the V2-REQ-08 map has at least one concrete V1-derived or explicitly reconstructable expected-output case.
- Formula cases contain concrete inputs, intermediate calculations, expected results, and precision.
- Scenario and cashflow cases contain concrete rows, aggregates, and required branches.
- Generated-output cases contain concrete fields/content/format/RTL/ownership assertions and named source evidence.
- Validation and warning cases contain concrete invalid conditions and expected blocking/error results.
- No golden case is missing and no unresolved manual domain decision remains.
- Every referenced REQ, V1BEHAVIOR, and V1ITEM exists.
- All 17 required high-risk domains are represented.

## What This Does Not Prove

- It does not run V2.
- It does not prove V2 produces the same outputs as V1.
- It does not prove runtime behavioral equivalence.
- It does not prove implementation completeness or V1 runtime parity.
- It does not approve or execute the intentional planner-delivery change.
- It does not authorize implementation or create execution instructions.

## Governance State

- Golden-master expected-output coverage: `MACHINE_VERIFIED_PASS`.
- Runtime behavioral equivalence: `NOT_PROVEN`.
- V2 implementation completeness: `NOT_PROVEN`.
- Execution authorization: `NO`.
- 02M remains frozen.

V1_GOLDEN_MASTER_EXPECTED_OUTPUT_VERIFICATION_PASS
