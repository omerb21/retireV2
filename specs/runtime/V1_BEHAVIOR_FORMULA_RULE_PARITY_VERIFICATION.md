# V1 Behavior Formula Rule Parity Verification

## Purpose

This is the missing proof layer identified by V2-REQ-07. V1 -> Universe capability coverage was not enough, because a capability title does not define its business behavior. Universe -> Plan mapping was also not enough, because a requirement mapping does not by itself preserve formulas, rules, branches, precision, validations, generated outputs, or expected results.

Behavioral/formula/rule planning parity is verified only because the dedicated map and verifier pass.

## Evidence Basis

The behavior inventory was extracted from the named V1 source-verified map, audit, runtime addendum, clean route evidence, pytest collection/execution evidence, and the source archive referenced by that evidence. The resulting contracts retain exact V1 source paths/functions, related V1ITEM IDs, mapped Universe REQs, required V2 behavior, parity mode, precision, validation, expected-output source, reviewer gate, and future golden-test obligation.

No V1 code was copied into V2, and no product code was modified.

## Exact Verification Results

### Behavior/Formula/Rule Verifier

Command:

```text
python scripts/verify_v1_behavior_formula_rule_parity.py
```

Result:

```text
result=PASS
v1_behaviors_checked=35
behavior_unmapped_fail=0
req_references_checked=175
v1item_references_checked=61
formula_rows_checked=29
golden_tests_required=33
high_risk_domains_checked=17
```

### Behavior Verifier Mutation Tests

Command:

```text
pytest tests/test_verify_v1_behavior_formula_rule_parity.py -q
```

Result:

```text
..............                                                           [100%]
14 passed in 3.89s
```

The tests prove fail-closed behavior for unmapped rows, unknown REQ and V1ITEM references, empty required V2 behavior, missing formula/input/output fields, missing golden-test requirements, absent numeric tolerance, incomplete intentional-change review, missing high-risk domains, invalid final marker, and duplicate behavior IDs.

### Prior V1 -> Universe Layer

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
........                                                                 [100%]
8 passed in 2.60s
```

### Prior Universe -> Plan Layer

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
........                                                                 [100%]
8 passed in 1.96s
```

## Additional Inventory Counts

| Measure | Count |
|---|---:|
| Behavior rows | 35 |
| Formula/calculation rows mechanically checked | 29 |
| Generated-output/report rows | 20 |
| Validation/warning/error rows | 35 |
| Golden tests required | 33 |
| High-risk domains | 17 |
| BEHAVIOR_UNMAPPED_FAIL | 0 |

## What This Proves

- V1 capability coverage remains machine-verified.
- Universe-to-plan mapping remains machine-verified.
- The inventoried V1 business behaviors are expressed as explicit required V2 contracts rather than title-only mappings.
- Formula-sensitive rows name inputs, outputs, formula/rule behavior, precision, validation behavior, and golden-test obligations.
- Generated outputs name required content/structure and comparison requirements.
- Every referenced V1ITEM and REQ exists.
- All 17 mandatory high-risk domains are represented.
- No behavior remains `BEHAVIOR_UNMAPPED_FAIL`.
- Full V1-to-V2 planning completeness is proven at the behavior-contract mapping layer defined by V2-REQ-07.

## What This Does Not Prove

- It does not prove that V2 implements any mapped behavior.
- It does not prove runtime behavioral equivalence.
- It does not prove formula results against a running V2 system.
- It does not execute the required future golden tests.
- It does not prove implementation completeness or V1 runtime parity.
- It does not approve annual legal parameters, intentional changes, or domain decisions still marked for review.
- It does not authorize an implementation package or provide execution instructions.

## Governance State

- Full planning completeness at the behavior-contract mapping layer: `MACHINE_VERIFIED_PASS`.
- Runtime behavioral equivalence: `NOT_PROVEN`.
- Implementation completeness: `NOT_PROVEN`.
- Execution authorization: `NO`.
- 02M remains frozen.

V1_BEHAVIOR_FORMULA_RULE_PARITY_VERIFICATION_PASS
