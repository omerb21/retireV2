# V2-REQ-13 Coverage Closure Plan From RAW-REM-03 To RAW-REM-05

## 1. Current Truth Statement

- Raw V1 source logic coverage currently `FAILS`.
- RAW-REM-03 through RAW-REM-05 are committed mapping packages, not closure packages.
- RAW-REM-03 through RAW-REM-05 mapped `1,455` items.
- RAW-REM-03 through RAW-REM-05 resolved `0` items.
- RAW-REM-03 through RAW-REM-05 still have `1,455` blocking items.
- This package defines future closure patch packages only.
- This package does not patch core maps.
- This package does not fix raw coverage.
- Full planning completeness remains `NOT_PROVEN`.
- Execution remains unauthorized.
- 02M remains frozen.

## 2. Closure Scope

### RAW-REM-03

- Items: `927`
- `needs_behavior_contract=91`
- `needs_formula_rule_contract=45`
- `needs_behavior_and_golden=791`
- Formula/rule inventory: `209`
- Golden expected-output candidates: `791`
- Remaining blocking: `927`

### RAW-REM-04

- Items: `104`
- `needs_behavior_contract=2`
- `needs_parser_schema_contract=20`
- `needs_normalized_import_contract=18`
- `needs_balance_ledger_rule_contract=7`
- `needs_source_preservation_contract=2`
- `needs_audit_traceability_contract=1`
- `needs_behavior_and_golden=7`
- `out_of_scope_for_raw_rem_04=47`
- Parser/schema/ledger inventory: `57`
- Golden expected-output candidates: `7`
- Source-preservation/audit inventory: `3`
- Remaining blocking: `104`

### RAW-REM-05

- Items: `424`
- `needs_behavior_contract=23`
- `needs_coefficient_table_contract=4`
- `needs_annuity_conversion_contract=8`
- `needs_capital_pension_classification_contract=43`
- `needs_manual_override_contract=3`
- `needs_validation_warning_contract=34`
- `needs_behavior_and_golden=309`
- Formula/coefficient/conversion inventory: `424`
- Golden expected-output candidates: `309`
- Remaining blocking: `424`

### Totals

- Closure-scope items: `1,455`
- Closure-scope resolved: `0`
- Closure-scope remaining blocking: `1,455`
- Golden candidate total: `1,107`
- Tax formula/rule inventory: `209`
- Parser/schema/ledger inventory: `57`
- Pension formula/coefficient/conversion inventory: `424`

## 3. Definition of Coverage Closure

Coverage closure requires all of the following:

- Relevant RAW-REM decision rows are represented in the correct core planning artifacts.
- Behavior, formula, and rule contracts are created or expanded.
- Golden expected-output cases are created where required.
- V1LOGIC IDs are linked from closure artifacts.
- Verifiers enforce the new links.
- The raw logic coverage verifier recognizes the closed items, or a documented audited bridge exists.
- All affected prior verifier tests pass.
- No formulas, expected outputs, parser schemas, coefficients, tax rules, or legal interpretations are invented.
- Raw coverage failure counts are reduced only by verifier-backed evidence.
- Coverage closure does not itself authorize implementation.

Mapping decisions alone do not satisfy this definition. No closure is completed by this plan.

## 4. Closure Package Families

### A. CLOSURE-03-TAX

RAW-REM-03 tax, fixation, and indexation closure family:

- `CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS`
- `CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS`
- `CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS`
- `CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE`

### B. CLOSURE-04-CLEARINGHOUSE

RAW-REM-04 clearinghouse, parser, and ledger closure family:

- `CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS`
- `CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS`
- `CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS`
- `CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS`
- `CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE`

### C. CLOSURE-05-PENSION-CONVERSION

RAW-REM-05 pension coefficient, annuity, and capital conversion closure family:

- `CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS`
- `CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS`
- `CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS`
- `CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS`
- `CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE`

### D. CLOSURE-INTEGRATION

Cross-package traceability and verification family:

- `CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX`
- `CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE`
- `CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE`

## 5. Future Package Table

| package ID | source RAW-REM | target item scope | expected item count or exact count source | target artifacts to modify in the future | verifier updates required in the future | expected effect on raw coverage failure count | prerequisites | forbidden actions | exit criteria | status |
|---|---|---|---|---|---|---|---|---|---|---|
| CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX | RAW-REM-03..05 | All decision rows in the three closure families | 1,455 exact decision rows | New audited RAWLOGIC-to-core traceability index; V1-to-Universe map only where a source-grounded link is missing | New index verifier and mutation tests; raw verifier bridge contract defined but not activated | 0; creates traceability only | Committed RAW-REM-03..05 decisions | No core status change, invented link, failure reduction, or product code | Every one of 1,455 IDs appears once with target artifact, candidate contract, and source decision reference | NOT_STARTED |
| CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS | RAW-REM-03 | Behavior-contract and behavior-plus-golden decisions | 882 rows from 91 behavior-only plus 791 behavior-and-golden decisions | V1 behavior/formula/rule parity map; traceability index | Behavior verifier and tests enforce V1LOGIC source links and required contract fields | 0 until bridge verification; candidate scope limited to evidenced IDs | CLOSURE-INT-01 | No legal interpretation, formula invention, implementation, or premature closure | Exact IDs have source-grounded behavior contracts and behavior verifier passes | NOT_STARTED |
| CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS | RAW-REM-03 | Formula/rule inventory rows and formula-bearing behavior decisions | 209 exact inventory rows; 45 formula-rule outcome rows are included | V1 behavior/formula/rule parity map; traceability index | Formula-field, source-reference, golden-required, and V1LOGIC-link checks | 0 until bridge verification; no predetermined reduction | CLOSURE-03A | No invented tax, fixation, indexation, rounding, or legal rule | Every inventory row is linked to a complete source-grounded contract and verifier tests pass | NOT_STARTED |
| CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS | RAW-REM-03 | Golden candidate inventory | 791 exact candidate rows | V1 golden master expected-output cases; traceability index | Golden verifier/tests enforce source inputs, expected outputs, behavior links, and V1LOGIC links | 0 until source-backed golden evidence and bridge verification | CLOSURE-03A; CLOSURE-03B | No invented expected value, fixture, tolerance, or legal result | Each candidate is represented by a source-extractable case or remains explicitly blocking | NOT_STARTED |
| CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE | RAW-REM-03 | All tax/fixation/indexation closure candidates | 927 exact RAW-REM-03 IDs | Audited closure bridge/index; core maps only for verified links | Raw logic coverage verifier/tests consume verified bridge and reject stale or unsupported closure | Evidence-determined reduction only for IDs satisfying all closure gates | CLOSURE-03A..03C | No blanket coverage status, broad wildcard, or failure-count override | Exact closed-ID set is mechanically proved; unrelated failures remain unchanged | NOT_STARTED |
| CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS | RAW-REM-05 | Behavior-contract and behavior-plus-golden decisions | 332 rows from 23 behavior-only plus 309 behavior-and-golden decisions | V1 behavior/formula/rule parity map; traceability index | Behavior verifier/tests enforce V1LOGIC source links and conversion fields | 0 until bridge verification; candidate scope limited to evidenced IDs | CLOSURE-INT-01 | No coefficient, annuity, classification, override, or implementation invention | Exact IDs have source-grounded behavior contracts and behavior verifier passes | NOT_STARTED |
| CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS | RAW-REM-05 | Coefficient-table and annuity-conversion decisions | 12 rows from 4 coefficient plus 8 annuity decisions; source inventory remains 424 | V1 behavior/formula/rule parity map; traceability index | Rule/source/input/output/golden and V1LOGIC-link checks | 0 until bridge verification; no predetermined reduction | CLOSURE-05A | No invented coefficient value, lookup policy, annuity formula, or expected result | Every target has complete source-grounded rule fields and verifier tests pass | NOT_STARTED |
| CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS | RAW-REM-05 | Classification, override, and conversion-validation decisions | 80 rows from 43 classification, 3 override, and 34 validation decisions | V1 behavior/formula/rule parity map; traceability index; Universe only if a verified requirement gap exists | Classification/override/validation source-link checks and mutation tests | 0 until bridge verification; no predetermined reduction | CLOSURE-05A | No invented product classification, withdrawal treatment, default, or permission behavior | Exact IDs have evidenced contracts or remain explicitly blocking | NOT_STARTED |
| CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS | RAW-REM-05 | Golden candidate inventory | 309 exact candidate rows | V1 golden master expected-output cases; traceability index | Golden verifier/tests enforce source inputs, expected outputs, behavior links, and V1LOGIC links | 0 until source-backed golden evidence and bridge verification | CLOSURE-05A..05C | No invented balance, annuity, coefficient, capital, or pension output | Each candidate is represented by source-extractable evidence or remains explicitly blocking | NOT_STARTED |
| CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE | RAW-REM-05 | All pension-conversion closure candidates | 424 exact RAW-REM-05 IDs | Audited closure bridge/index; core maps only for verified links | Raw logic coverage verifier/tests consume verified bridge and reject unsupported closure | Evidence-determined reduction only for IDs satisfying all closure gates | CLOSURE-05A..05D | No blanket coverage status or failure-count override | Exact closed-ID set is mechanically proved; unrelated failures remain unchanged | NOT_STARTED |
| CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS | RAW-REM-04 | Behavior-contract and behavior-plus-golden decisions | 9 rows from 2 behavior-only plus 7 behavior-and-golden decisions | V1 behavior/formula/rule parity map; traceability index | Behavior verifier/tests enforce parser/ledger V1LOGIC links | 0 until bridge verification; candidate scope limited to evidenced IDs | CLOSURE-INT-01 | No parser, field, ledger, or product implementation invention | Exact IDs have source-grounded behavior contracts and verifier passes | NOT_STARTED |
| CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS | RAW-REM-04 | Parser-schema and normalized-import decisions | 38 rows from 20 schema plus 18 normalized-import decisions | V1 behavior/formula/rule parity map; traceability index; Universe only for a verified requirement gap | Schema/field/source-preservation and V1LOGIC-link checks | 0 until bridge verification; no predetermined reduction | CLOSURE-04A | No invented schema field, normalization, default, or external format rule | Each exact source field and normalization rule is contracted or remains blocking | NOT_STARTED |
| CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS | RAW-REM-04 | Ledger, source-preservation, and audit-traceability decisions | 10 rows from 7 ledger, 2 preservation, and 1 audit decisions | V1 behavior/formula/rule parity map; traceability index | Ledger invariants, provenance, audit, and V1LOGIC-link checks | 0 until bridge verification; no predetermined reduction | CLOSURE-04A; CLOSURE-04B | No invented reconciliation, provenance, balance, or audit behavior | Exact rows have source-grounded ledger and traceability contracts | NOT_STARTED |
| CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS | RAW-REM-04 | Golden candidate inventory | 7 exact candidate rows | V1 golden master expected-output cases; traceability index | Golden verifier/tests enforce source fixtures, parsed/ledger outputs, and V1LOGIC links | 0 until source-backed golden evidence and bridge verification | CLOSURE-04A..04C | No invented parser fixture, normalized record, ledger value, or expected output | Each candidate is source-extractable or remains explicitly blocking | NOT_STARTED |
| CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE | RAW-REM-04 | All clearinghouse closure candidates, including routed rows | 104 exact RAW-REM-04 IDs; 47 retain explicit onward routing | Audited closure bridge/index; core maps only for verified links | Raw verifier/tests enforce closed IDs and preserve routed-row blocking state | Evidence-determined reduction only for IDs satisfying all closure gates | CLOSURE-04A..04D; routing evidence for 47 rows | No blanket closure of routed rows or failure-count override | Exact closed-ID set is proved; routed IDs remain blocking unless separately evidenced | NOT_STARTED |
| CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE | RAW-REM-03..05 | Integrated closure bridge and all affected core controls | 1,455 candidate IDs; exact closed subset comes from family bridges | Raw closure bridge/index and verifier scripts/tests | Cross-check behavior, golden, V1ITEM, REQ, V1LOGIC, source, and status cardinality | No predetermined reduction; exposes only mechanically eligible IDs | CLOSURE-03D; CLOSURE-05E; CLOSURE-04E | No bypass, allow-all bridge, or inferred reference | Integrated verifier rejects missing, duplicate, stale, unsupported, and cross-map-inconsistent links | NOT_STARTED |
| CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE | RAW-REM-03..05 | Verified integrated closed-ID set and preserved unresolved population | Up to 1,455 candidates; exact reduction derived by verifier, never predeclared | Raw coverage audit/verification only as supported by exact evidence; verification reports | Run all affected verifiers/tests and prove arithmetic reconciliation | Exact verifier-backed reduction; all unsupported IDs remain failed | CLOSURE-INT-02 and passing family/core verifiers | No manual count edit, unsupported PASS marker, implementation, or scope erasure | New failure counts reconcile to exact closed IDs; all unrelated failures and RAW-REM-06..10 scope remain | NOT_STARTED |

## 6. Recommended Closure Order

1. `CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX`
2. `CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS`
3. `CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS`
4. `CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS`
5. `CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE`
6. `CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS`
7. `CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS`
8. `CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS`
9. `CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS`
10. `CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE`
11. `CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS`
12. `CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS`
13. `CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS`
14. `CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS`
15. `CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE`
16. `CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE`
17. `CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE`

Traceability comes first so every later contract has a mechanically testable source-to-core destination. Tax and fixation follow because they carry the highest legal and calculation risk. Pension conversion follows because it is calculation-heavy and interacts with later scenario work. Clearinghouse follows because 47 items were routed onward and parser closure may depend on broader RAW-REM-06..10 routing. Family bridges, the integrated verifier, and the final regression/rebase gate prevent mapping rows from being treated as closed without evidence.

## 7. Minimum Acceptance Criteria for Any Future Closure Package

A future closure package is acceptable only if:

- it lists exact V1LOGIC IDs being closed;
- it cites source-grounded RAW-REM decision rows;
- it modifies only declared target artifacts;
- it updates relevant verifier tests;
- it does not invent formulas, expected outputs, schemas, coefficients, or legal rules;
- it reduces raw coverage failures only through verifiable mapping;
- it preserves all unrelated failure counts;
- it does not authorize implementation; and
- it leaves 02M frozen unless a later explicit management decision changes status.

## 8. Closure vs Implementation Boundary

- Coverage closure may update planning, specification, and test artifacts.
- Coverage closure may not create product code.
- Coverage closure may not create UI or backend implementation.
- Coverage closure may not start 02M.
- Coverage closure may not claim V2 is behaviorally equivalent at runtime.

## 9. Relationship to RAW-REM-06..10

- RAW-REM-06..10 remain necessary unless a later scope decision changes them.
- V2-REQ-13 does not cancel RAW-REM-06..10.
- V2-REQ-13 prevents blind continuation by introducing closure planning now.
- After one or more closure packages are completed, management can decide whether to continue RAW-REM-06 or continue closure packages.

## 10. Risk Register

| risk | why it matters | mitigation in closure plan | blocking yes/no |
|---|---|---|---|
| Mapping-only loop | More mapping can accumulate without changing core controls or failure state. | Introduce bounded contract, bridge, and rebase packages now. | YES |
| Invented formulas | Unsupported tax, annuity, or conversion logic would create false parity. | Require source decision rows, complete formula fields, and mutation-tested verifier checks. | YES |
| Invented golden outputs | Fabricated expected values would make golden tests meaningless. | Require extractable V1 source/fixture evidence or retain blocking status. | YES |
| Raw verifier not connected to closure artifacts | Core maps could change while raw failures remain unproved. | Build family bridges and an integrated raw-closure verifier before rebase. | YES |
| Overlarge closure packages | Large mixed patches obscure evidence and review boundaries. | Split work into 17 ordered packages with exact source scopes. | YES |
| Accidental implementation start | Planning closure could be mistaken for product authorization. | Forbid product code and retain execution status `NO`. | YES |
| Unfreezing 02M too early | A planning artifact cannot grant milestone authority. | Keep 02M `FROZEN` unless a later explicit management decision changes it. | YES |
| Ignoring RAW-REM-06..10 | Unprocessed logic would remain outside the closure proof. | Preserve those packages as necessary future scope unless formally changed. | YES |
| Reducing failure counts without evidence | Manual count changes would manufacture progress. | Permit reductions only in the final rebase from exact verifier-backed closed IDs. | YES |

## 11. Current Status

- Raw V1 source logic coverage: `FAIL`
- Full planning completeness: `NOT_PROVEN`
- Runtime behavioral equivalence: `NOT_PROVEN`
- Implementation completeness: `NOT_PROVEN`
- Execution authorized: `NO`
- 02M: `FROZEN`
- V2-REQ-13 does not change those statuses.

## 12. Final Marker

V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05_PASS
