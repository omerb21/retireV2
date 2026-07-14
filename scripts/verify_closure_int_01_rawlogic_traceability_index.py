from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PLAN_PASS = "CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_PASS"
PLAN_FAIL = "CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_FAIL"
INDEX_MARKER = "CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX_CREATED"
ALLOWED_RAW_REM = {"RAW-REM-03", "RAW-REM-04", "RAW-REM-05"}
ALLOWED_STATUS = {"NOT_CLOSED", "PLANNED_FOR_CLOSURE_PACKAGE", "CLOSED_BY_FUTURE_PATCH"}
RECOGNIZED_CLOSURE_PACKAGES = {
    "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS",
    "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS",
}
EXPECTED_CLOSURE_03A_ROWS = 91
EXPECTED_CLOSURE_03B_ROWS = 45
EXPECTED_CLOSED_ROWS = EXPECTED_CLOSURE_03A_ROWS + EXPECTED_CLOSURE_03B_ROWS
ALLOWED_ARTIFACTS = {
    "BEHAVIOR_FORMULA_RULE_PARITY_MAP",
    "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES",
    "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP",
    "V2_REQUIRED_CAPABILITY_UNIVERSE",
    "RAWLOGIC_CLOSURE_BRIDGE",
    "RAWLOGIC_CLOSURE_VERIFIER",
    "RAWLOGIC_REGRESSION_REBASE",
    "DOMAIN_DECISION_RECORD",
    "MANUAL_SOURCE_REVIEW_RECORD",
}
SOURCE_DRIVEN_PACKAGES = {
    "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS",
    "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS",
    "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE",
    "CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS",
    "CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS",
    "CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS",
    "CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE",
    "CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS",
    "CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS",
    "CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS",
    "CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE",
}
ALL_SUMMARY_PACKAGES = SOURCE_DRIVEN_PACKAGES | {
    "CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX",
    "CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE",
    "CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE",
}


@dataclass(frozen=True)
class Failure:
    code: str
    logic_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the CLOSURE-INT-01 traceability index.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def add(failures: list[Failure], code: str, logic_id: str, expected: str, actual: str, source: Path) -> None:
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def parse_rows(text: str, width: int) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width and re.fullmatch(r"V1LOGIC-\d{3,}", cells[0]):
            rows.append(cells)
    return rows


def parse_behavior_contract_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 13 and re.fullmatch(r"C03A-BEH-\d{3}", cells[0]):
            rows.append(cells)
    return rows


def parse_formula_rule_contract_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 14 and re.fullmatch(r"C03B-FR-\d{3}", cells[0]):
            rows.append(cells)
    return rows


def section(text: str, heading: str, next_heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*$.*?(?=^{re.escape(next_heading)}\s*$)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(0) if match else ""


def expected_destination(raw_rem: str, decision: list[str]) -> tuple[str, str, str]:
    outcome = decision[2]
    rules = {
        "RAW-REM-03": {
            "TAXMAP_NEEDS_BEHAVIOR_CONTRACT": ("CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT": ("CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN": ("CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS;CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "RAWLOGIC_CLOSURE_BRIDGE"),
            "TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT": ("CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "NONE"),
            "TAXMAP_NEEDS_REQ_MAPPING": ("CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE", "V2_REQUIRED_CAPABILITY_UNIVERSE", "RAWLOGIC_CLOSURE_BRIDGE"),
            "TAXMAP_NEEDS_V1ITEM_LINK": ("CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE", "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP", "RAWLOGIC_CLOSURE_BRIDGE"),
            "TAXMAP_NEEDS_DOMAIN_DECISION": ("DOMAIN_DECISION_RECORD", "DOMAIN_DECISION_RECORD", "NONE"),
            "TAXMAP_NEEDS_MANUAL_SOURCE_REVIEW": ("MANUAL_SOURCE_REVIEW_RECORD", "MANUAL_SOURCE_REVIEW_RECORD", "NONE"),
        },
        "RAW-REM-04": {
            "CLRMAPP_NEEDS_BEHAVIOR_CONTRACT": ("CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_PARSER_SCHEMA_CONTRACT": ("CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_NORMALIZED_IMPORT_CONTRACT": ("CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_BALANCE_LEDGER_RULE_CONTRACT": ("CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_SOURCE_PRESERVATION_CONTRACT": ("CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_AUDIT_TRACEABILITY_CONTRACT": ("CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "CLRMAPP_NEEDS_BEHAVIOR_AND_GOLDEN": ("CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS;CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "RAWLOGIC_CLOSURE_BRIDGE"),
            "CLRMAPP_NEEDS_GOLDEN_EXPECTED_OUTPUT": ("CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "NONE"),
            "CLRMAPP_NEEDS_REQ_MAPPING": ("CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE", "V2_REQUIRED_CAPABILITY_UNIVERSE", "RAWLOGIC_CLOSURE_BRIDGE"),
            "CLRMAPP_NEEDS_V1ITEM_LINK": ("CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE", "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP", "RAWLOGIC_CLOSURE_BRIDGE"),
        },
        "RAW-REM-05": {
            "PENMAP_NEEDS_BEHAVIOR_CONTRACT": ("CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_COEFFICIENT_TABLE_CONTRACT": ("CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_ANNUITY_CONVERSION_CONTRACT": ("CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_FORMULA_RULE_CONTRACT": ("CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_CAPITAL_PENSION_CLASSIFICATION_CONTRACT": ("CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_MANUAL_OVERRIDE_CONTRACT": ("CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_VALIDATION_WARNING_CONTRACT": ("CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS", "BEHAVIOR_FORMULA_RULE_PARITY_MAP", "NONE"),
            "PENMAP_NEEDS_BEHAVIOR_AND_GOLDEN": ("CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS;CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "RAWLOGIC_CLOSURE_BRIDGE"),
            "PENMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT": ("CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS", "GOLDEN_MASTER_EXPECTED_OUTPUT_CASES", "NONE"),
            "PENMAP_NEEDS_REQ_MAPPING": ("CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE", "V2_REQUIRED_CAPABILITY_UNIVERSE", "RAWLOGIC_CLOSURE_BRIDGE"),
            "PENMAP_NEEDS_V1ITEM_LINK": ("CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE", "V1_TO_UNIVERSE_EXHAUSTIVENESS_MAP", "RAWLOGIC_CLOSURE_BRIDGE"),
        },
    }
    out_of_scope = {
        "RAW-REM-03": "TAXMAP_OUT_OF_SCOPE_FOR_RAW_REM_03",
        "RAW-REM-04": "CLRMAPP_OUT_OF_SCOPE_FOR_RAW_REM_04",
        "RAW-REM-05": "PENMAP_OUT_OF_SCOPE_FOR_RAW_REM_05",
    }
    if outcome == out_of_scope[raw_rem]:
        return decision[5], "RAWLOGIC_CLOSURE_BRIDGE", "NONE"
    if outcome not in rules[raw_rem]:
        raise KeyError(f"unsupported outcome {raw_rem}:{outcome}")
    return rules[raw_rem][outcome]


def verify(repo_root: Path) -> tuple[list[Failure], dict[str, int]]:
    paths = {
        "plan": repo_root / "specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX.md",
        "index": repo_root / "specs/runtime/raw_remediation/closure/CLOSURE_INT_01_RAWLOGIC_TRACEABILITY_INDEX.md",
        "closure_plan": repo_root / "specs/runtime/raw_remediation/V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05.md",
        "RAW-REM-03": repo_root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md",
        "RAW-REM-04": repo_root / "specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_DECISIONS.md",
        "RAW-REM-05": repo_root / "specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS.md",
        "closure_03a": repo_root / "specs/runtime/raw_remediation/closure/CLOSURE_03A_TAX_BEHAVIOR_CONTRACTS.md",
        "closure_03b": repo_root / "specs/runtime/raw_remediation/closure/CLOSURE_03B_TAX_FORMULA_RULE_CONTRACTS.md",
        "behavior_map": repo_root / "specs/runtime/V1_BEHAVIOR_FORMULA_RULE_PARITY_MAP.md",
    }
    failures: list[Failure] = []
    texts: dict[str, str] = {}
    for key, path in paths.items():
        try:
            texts[key] = path.read_text(encoding="utf-8")
        except OSError as exc:
            add(failures, "REQUIRED_FILE_READ_ERROR", "", "readable required file", str(exc), path)
    if failures:
        return failures, {}

    decisions: dict[str, tuple[str, list[str]]] = {}
    for raw_rem in sorted(ALLOWED_RAW_REM):
        rows = parse_rows(texts[raw_rem], 7)
        for row in rows:
            if row[0] in decisions:
                add(failures, "DUPLICATE_SOURCE_DECISION", row[0], "one source decision", raw_rem, paths[raw_rem])
            decisions[row[0]] = (raw_rem, row)

    index_rows = parse_rows(texts["index"], 11)
    indexed: dict[str, list[list[str]]] = {}
    for row in index_rows:
        indexed.setdefault(row[0], []).append(row)
    for logic_id in sorted(decisions):
        if len(indexed.get(logic_id, [])) != 1:
            add(failures, "INDEX_CARDINALITY", logic_id, "exactly one row", str(len(indexed.get(logic_id, []))), paths["index"])
    for logic_id in sorted(set(indexed) - set(decisions)):
        add(failures, "EXTRA_INDEX_LOGIC_ID", logic_id, "RAW-REM-03/04/05 decision ID", "extra", paths["index"])

    closure_report_03a: dict[str, list[list[str]]] = {}
    for row in parse_rows(texts["closure_03a"], 9):
        closure_report_03a.setdefault(row[0], []).append(row)
    closure_report_03b: dict[str, list[list[str]]] = {}
    for row in parse_rows(texts["closure_03b"], 10):
        closure_report_03b.setdefault(row[0], []).append(row)
    behavior_contract_section_03a = section(
        texts["behavior_map"],
        "## 11A. CLOSURE-03A Tax Behavior Contracts",
        "## 11B. CLOSURE-03B Tax Formula/Rule Contracts",
    )
    behavior_contracts_03a: dict[str, list[list[str]]] = {}
    for row in parse_behavior_contract_rows(behavior_contract_section_03a):
        behavior_contracts_03a.setdefault(row[1], []).append(row)
    formula_rule_contract_section_03b = section(
        texts["behavior_map"],
        "## 11B. CLOSURE-03B Tax Formula/Rule Contracts",
        "## 12. Final Status",
    )
    formula_rule_contracts_03b: dict[str, list[list[str]]] = {}
    for row in parse_formula_rule_contract_rows(formula_rule_contract_section_03b):
        formula_rule_contracts_03b.setdefault(row[1], []).append(row)

    referenced_packages: set[str] = set()
    artifact_types: set[str] = set()
    valid_closure_03a: set[str] = set()
    valid_closure_03b: set[str] = set()
    invalid_closed: set[str] = set()

    def add_closed_failure(code: str, logic_id: str, expected: str, actual: str, source: Path) -> None:
        invalid_closed.add(logic_id)
        add(failures, code, logic_id, expected, actual, source)

    for row in index_rows:
        logic_id, raw_rem, source_file, outcome, subdomain, package, primary, secondary, status, evidence, _notes = row
        if raw_rem not in ALLOWED_RAW_REM:
            add(failures, "INVALID_SOURCE_RAW_REM", logic_id, "RAW-REM-03/04/05", raw_rem, paths["index"])
            continue
        source = decisions.get(logic_id)
        if source is None:
            continue
        expected_raw, decision = source
        expected_source = paths[expected_raw].relative_to(repo_root).as_posix()
        if raw_rem != expected_raw:
            add(failures, "SOURCE_RAW_REM_MISMATCH", logic_id, expected_raw, raw_rem, paths["index"])
        if source_file != expected_source:
            add(failures, "SOURCE_DECISION_FILE_MISMATCH", logic_id, expected_source, source_file, paths["index"])
        if outcome != decision[2] or subdomain != decision[1]:
            add(failures, "SOURCE_DECISION_VALUE_MISMATCH", logic_id, f"{decision[2]} / {decision[1]}", f"{outcome} / {subdomain}", paths["index"])
        try:
            expected_package, expected_primary, expected_secondary = expected_destination(raw_rem, decision)
        except KeyError as exc:
            add(failures, "UNSUPPORTED_SOURCE_OUTCOME", logic_id, "mapped outcome", str(exc), paths[raw_rem])
            continue
        if (package, primary, secondary) != (expected_package, expected_primary, expected_secondary):
            add(failures, "DESTINATION_MAPPING_MISMATCH", logic_id, f"{expected_package} / {expected_primary} / {expected_secondary}", f"{package} / {primary} / {secondary}", paths["index"])
        if not package:
            add(failures, "FUTURE_PACKAGE_EMPTY", logic_id, "non-empty future package", "empty", paths["index"])
        if primary not in ALLOWED_ARTIFACTS:
            add(failures, "INVALID_TARGET_ARTIFACT_TYPE", logic_id, "allowed target artifact", primary, paths["index"])
        if secondary != "NONE" and secondary not in ALLOWED_ARTIFACTS:
            add(failures, "INVALID_SECONDARY_ARTIFACT_TYPE", logic_id, "NONE or allowed artifact", secondary, paths["index"])
        if status not in ALLOWED_STATUS:
            add(failures, "INVALID_CLOSURE_STATUS", logic_id, ", ".join(sorted(ALLOWED_STATUS)), status, paths["index"])
        elif status == "CLOSED_BY_FUTURE_PATCH":
            package_ref, separator, contract_ref = evidence.partition(":")
            row_valid = True

            def reject(code: str, expected: str, actual: str, source_path: Path = paths["index"]) -> None:
                nonlocal row_valid
                row_valid = False
                add_closed_failure(code, logic_id, expected, actual, source_path)

            if evidence == "EMPTY_NOT_CLOSED" or not separator or not contract_ref:
                reject("CLOSED_EVIDENCE_MISSING", "recognized package ID and contract ID", evidence)
            if raw_rem != "RAW-REM-03":
                reject("CLOSED_SOURCE_NOT_ALLOWED", "RAW-REM-03", raw_rem)
            if package_ref not in RECOGNIZED_CLOSURE_PACKAGES:
                reject("UNKNOWN_CLOSURE_PACKAGE", ", ".join(sorted(RECOGNIZED_CLOSURE_PACKAGES)), package_ref or "empty")
            elif package_ref == "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS":
                report_rows = closure_report_03a.get(logic_id, [])
                behavior_rows = behavior_contracts_03a.get(logic_id, [])
                if outcome != "TAXMAP_NEEDS_BEHAVIOR_CONTRACT":
                    reject("CLOSED_OUTCOME_NOT_SELECTED", "TAXMAP_NEEDS_BEHAVIOR_CONTRACT", outcome)
                if len(report_rows) != 1:
                    reject("CLOSURE_03A_REPORT_CARDINALITY", "exactly one report row", str(len(report_rows)), paths["closure_03a"])
                else:
                    report = report_rows[0]
                    if report[1] != contract_ref or report[6] != evidence or report[7] != "CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT":
                        reject(
                            "CLOSURE_03A_REPORT_MISMATCH",
                            f"{contract_ref} / {evidence} / CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT",
                            f"{report[1]} / {report[6]} / {report[7]}",
                            paths["closure_03a"],
                        )
                if len(behavior_rows) != 1:
                    reject("CLOSURE_03A_BEHAVIOR_MAP_CARDINALITY", "exactly one behavior contract", str(len(behavior_rows)), paths["behavior_map"])
                else:
                    behavior = behavior_rows[0]
                    if (
                        behavior[0] != contract_ref
                        or behavior[2] != "RAW-REM-03"
                        or behavior[3] != "TAXMAP_NEEDS_BEHAVIOR_CONTRACT"
                        or behavior[10] != package_ref
                        or behavior[11] != "CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT"
                    ):
                        reject(
                            "CLOSURE_03A_BEHAVIOR_MAP_MISMATCH",
                            f"{contract_ref} / RAW-REM-03 / TAXMAP_NEEDS_BEHAVIOR_CONTRACT / {package_ref} / CLOSED_BY_CLOSURE_03A_BEHAVIOR_CONTRACT",
                            f"{behavior[0]} / {behavior[2]} / {behavior[3]} / {behavior[10]} / {behavior[11]}",
                            paths["behavior_map"],
                        )
                if row_valid:
                    valid_closure_03a.add(logic_id)
            elif package_ref == "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS":
                report_rows = closure_report_03b.get(logic_id, [])
                formula_rows = formula_rule_contracts_03b.get(logic_id, [])
                if outcome != "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT":
                    reject("CLOSED_OUTCOME_NOT_SELECTED", "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT", outcome)
                if len(report_rows) != 1:
                    reject("CLOSURE_03B_REPORT_CARDINALITY", "exactly one report row", str(len(report_rows)), paths["closure_03b"])
                else:
                    report = report_rows[0]
                    if report[1] != contract_ref or report[7] != evidence or report[8] != "CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT":
                        reject(
                            "CLOSURE_03B_REPORT_MISMATCH",
                            f"{contract_ref} / {evidence} / CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT",
                            f"{report[1]} / {report[7]} / {report[8]}",
                            paths["closure_03b"],
                        )
                if len(formula_rows) != 1:
                    reject("CLOSURE_03B_BEHAVIOR_MAP_CARDINALITY", "exactly one formula/rule contract", str(len(formula_rows)), paths["behavior_map"])
                else:
                    formula = formula_rows[0]
                    if (
                        formula[0] != contract_ref
                        or formula[2] != "RAW-REM-03"
                        or formula[3] != "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT"
                        or formula[11] != package_ref
                        or formula[12] != "CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT"
                    ):
                        reject(
                            "CLOSURE_03B_BEHAVIOR_MAP_MISMATCH",
                            f"{contract_ref} / RAW-REM-03 / TAXMAP_NEEDS_FORMULA_RULE_CONTRACT / {package_ref} / CLOSED_BY_CLOSURE_03B_FORMULA_RULE_CONTRACT",
                            f"{formula[0]} / {formula[2]} / {formula[3]} / {formula[11]} / {formula[12]}",
                            paths["behavior_map"],
                        )
                if row_valid:
                    valid_closure_03b.add(logic_id)
        elif evidence != "EMPTY_NOT_CLOSED":
            add(failures, "INVALID_CLOSURE_EVIDENCE", logic_id, "EMPTY_NOT_CLOSED for a non-closed row", evidence, paths["index"])
        referenced_packages.update(part for part in package.split(";") if part.startswith("CLOSURE-"))
        artifact_types.add(primary)
        if secondary != "NONE":
            artifact_types.add(secondary)

    source_counts = Counter(row[1] for row in index_rows)
    expected_counts = {"RAW-REM-03": 927, "RAW-REM-04": 104, "RAW-REM-05": 424}
    if len(index_rows) != 1455:
        add(failures, "TOTAL_ROW_COUNT_INVALID", "", "1455", str(len(index_rows)), paths["index"])
    for raw_rem, expected in expected_counts.items():
        if source_counts[raw_rem] != expected:
            add(failures, "SOURCE_ROW_COUNT_INVALID", "", f"{raw_rem}={expected}", str(source_counts[raw_rem]), paths["index"])

    closed_rows = sum(row[8] == "CLOSED_BY_FUTURE_PATCH" for row in index_rows)
    if closed_rows != EXPECTED_CLOSED_ROWS:
        add(failures, "CLOSED_ROW_COUNT_INVALID", "", str(EXPECTED_CLOSED_ROWS), str(closed_rows), paths["index"])
    if len(valid_closure_03a) != EXPECTED_CLOSURE_03A_ROWS:
        add(failures, "CLOSURE_03A_VALID_ROW_COUNT_INVALID", "", str(EXPECTED_CLOSURE_03A_ROWS), str(len(valid_closure_03a)), paths["index"])
    if len(valid_closure_03b) != EXPECTED_CLOSURE_03B_ROWS:
        add(failures, "CLOSURE_03B_VALID_ROW_COUNT_INVALID", "", str(EXPECTED_CLOSURE_03B_ROWS), str(len(valid_closure_03b)), paths["index"])

    summary = section(texts["plan"], "## 8. Summary by Future Closure Package", "## 9. Traceability Integrity Rules")
    for package_id in ALL_SUMMARY_PACKAGES:
        if summary.count(f"| {package_id} |") != 1:
            add(failures, "SUMMARY_PACKAGE_CARDINALITY", "", f"{package_id} exactly once", str(summary.count(f"| {package_id} |")), paths["plan"])
    for package_id in SOURCE_DRIVEN_PACKAGES:
        if package_id not in referenced_packages:
            add(failures, "SOURCE_DRIVEN_PACKAGE_UNREFERENCED", "", package_id, "missing", paths["index"])

    required_plan_values = {
        "RAW_COVERAGE_STATUS_INVALID": "Raw V1 source logic coverage: `FAIL`",
        "PLANNING_COMPLETENESS_INVALID": "Full planning completeness: `NOT_PROVEN`",
        "EXECUTION_AUTHORIZATION_INVALID": "Execution authorized: `NO`",
        "02M_STATUS_INVALID": "02M: `FROZEN`",
    }
    for code, value in required_plan_values.items():
        if value not in texts["plan"]:
            add(failures, code, "", value, "missing", paths["plan"])
    forbidden_patterns = {
        "RAW_COVERAGE_FIXED_CLAIM": r"(?i)raw V1 source logic coverage\s*(?:is|:)\s*`?FIXED`?",
        "IMPLEMENTATION_RECOMMENDED": r"(?i)(?:recommend(?:ed|ation)?|next step)\s*:\s*(?:begin|start|proceed with|authorize)[^\n]{0,40}implementation",
        "02M_UNFROZEN": r"(?i)02M\s*(?:is|:)\s*`?UNFROZEN`?",
        "COVERAGE_CLOSURE_CLAIM": r"(?i)coverage closure has (?:already )?happened",
    }
    for code, pattern in forbidden_patterns.items():
        match = re.search(pattern, texts["plan"])
        if match:
            add(failures, code, "", "forbidden conclusion absent", match.group(0), paths["plan"])

    index_forbidden_patterns = {
        "INDEX_IMPLEMENTATION_READINESS_CLAIM": r"(?i)(?:implementation|execution)\s*(?:is|:)\s*`?(?:READY|AUTHORIZED|COMPLETE|YES)`?",
        "INDEX_FULL_PLANNING_COMPLETENESS_CLAIM": r"(?i)full planning completeness\s*(?:is|:)\s*`?(?:PROVEN|PASS|COMPLETE)`?",
        "INDEX_02M_UNFROZEN": r"(?i)02M\s*(?:is|:)\s*`?UNFROZEN`?",
    }
    for code, pattern in index_forbidden_patterns.items():
        match = re.search(pattern, texts["index"])
        if match:
            add(failures, code, "", "forbidden row conclusion absent", match.group(0), paths["index"])

    if texts["plan"].count(PLAN_PASS) != 1 or texts["plan"].count(PLAN_FAIL) != 0:
        add(failures, "INVALID_PLAN_MARKER", "", "one PASS and zero FAIL markers", f"PASS={texts['plan'].count(PLAN_PASS)}; FAIL={texts['plan'].count(PLAN_FAIL)}", paths["plan"])
    if texts["index"].count(INDEX_MARKER) != 1:
        add(failures, "INVALID_INDEX_MARKER", "", "exactly one index marker", str(texts["index"].count(INDEX_MARKER)), paths["index"])
    if "READY_FOR_REVIEW" in texts["plan"] or "READY_FOR_REVIEW" in texts["index"]:
        add(failures, "READY_FOR_REVIEW_FORBIDDEN", "", "zero occurrences", "present", paths["plan"])

    counts = {
        "traceability_rows": len(index_rows),
        "raw_rem_03_rows": source_counts["RAW-REM-03"],
        "raw_rem_04_rows": source_counts["RAW-REM-04"],
        "raw_rem_05_rows": source_counts["RAW-REM-05"],
        "closed_rows": closed_rows,
        "closure_03a_closed_rows": len(valid_closure_03a),
        "closure_03b_closed_rows": len(valid_closure_03b),
        "invalid_closed_rows": len(invalid_closed),
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("CLOSURE_INT_01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
