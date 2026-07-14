from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PASS_MARKER = "V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05_PASS"
FAIL_MARKER = "V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05_FAIL"
PACKAGE_IDS = (
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
    "CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX",
    "CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE",
    "CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE",
)
RECOMMENDED_ORDER = (
    "CLOSURE-INT-01_RAWLOGIC_TO_CORE_MAP_TRACEABILITY_INDEX",
    "CLOSURE-03A_TAX_BEHAVIOR_CONTRACTS",
    "CLOSURE-03B_TAX_FORMULA_RULE_CONTRACTS",
    "CLOSURE-03C_TAX_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-03D_TAX_CORE_VERIFIER_BRIDGE",
    "CLOSURE-05A_PENSION_CONVERSION_BEHAVIOR_CONTRACTS",
    "CLOSURE-05B_COEFFICIENT_AND_ANNUITY_RULE_CONTRACTS",
    "CLOSURE-05C_CAPITAL_PENSION_CLASSIFICATION_AND_OVERRIDE_CONTRACTS",
    "CLOSURE-05D_PENSION_CONVERSION_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-05E_PENSION_CONVERSION_CORE_VERIFIER_BRIDGE",
    "CLOSURE-04A_CLEARINGHOUSE_BEHAVIOR_CONTRACTS",
    "CLOSURE-04B_PARSER_SCHEMA_AND_NORMALIZED_IMPORT_CONTRACTS",
    "CLOSURE-04C_BALANCE_LEDGER_SOURCE_TRACEABILITY_CONTRACTS",
    "CLOSURE-04D_CLEARINGHOUSE_GOLDEN_EXPECTED_OUTPUTS",
    "CLOSURE-04E_CLEARINGHOUSE_CORE_VERIFIER_BRIDGE",
    "CLOSURE-INT-02_RAWLOGIC_CLOSURE_VERIFIER_UPDATE",
    "CLOSURE-INT-03_REGRESSION_AND_FAILURE_COUNT_REBASE",
)


@dataclass(frozen=True)
class Failure:
    code: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the V2-REQ-13 coverage-closure plan.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def add(failures: list[Failure], code: str, expected: str, actual: str, source: Path) -> None:
    failures.append(Failure(code, expected, actual, str(source)))


def require_text(failures: list[Failure], text: str, value: str, code: str, source: Path) -> None:
    if value not in text:
        add(failures, code, value, "missing", source)


def section(text: str, heading: str, next_heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*$.*?(?=^{re.escape(next_heading)}\s*$)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(0) if match else ""


def table_rows(text: str, width: int) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width and cells[0] != "package ID":
            rows.append(cells)
    return rows


def verify(repo_root: Path) -> tuple[list[Failure], dict[str, int | str]]:
    paths = {
        "plan": repo_root / "specs/runtime/raw_remediation/V2_REQ_13_COVERAGE_CLOSURE_PLAN_FROM_RAW_REM_03_TO_05.md",
        "checkpoint": repo_root / "specs/runtime/raw_remediation/V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT.md",
        "raw03": repo_root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION.md",
        "raw04": repo_root / "specs/runtime/raw_remediation/RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_VERIFICATION.md",
        "raw05": repo_root / "specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION.md",
    }
    failures: list[Failure] = []
    texts: dict[str, str] = {}
    for key, path in paths.items():
        try:
            texts[key] = path.read_text(encoding="utf-8")
        except OSError as exc:
            add(failures, "REQUIRED_FILE_READ_ERROR", "readable required file", str(exc), path)
    if failures:
        return failures, {}

    plan = texts["plan"]
    if plan.count(PASS_MARKER) != 1 or plan.count(FAIL_MARKER) != 0:
        add(
            failures,
            "INVALID_FINAL_MARKER",
            "one PASS and zero FAIL markers",
            f"PASS={plan.count(PASS_MARKER)}; FAIL={plan.count(FAIL_MARKER)}",
            paths["plan"],
        )
    if "READY_FOR_REVIEW" in plan:
        add(failures, "READY_FOR_REVIEW_FORBIDDEN", "zero occurrences", str(plan.count("READY_FOR_REVIEW")), paths["plan"])

    required_values = {
        "RAW_COVERAGE_STATUS_INVALID": "Raw V1 source logic coverage: `FAIL`",
        "PLANNING_COMPLETENESS_INVALID": "Full planning completeness: `NOT_PROVEN`",
        "EXECUTION_AUTHORIZATION_INVALID": "Execution authorized: `NO`",
        "02M_STATUS_INVALID": "02M: `FROZEN`",
        "CLOSURE_SCOPE_INVALID": "Closure-scope items: `1,455`",
        "CLOSURE_RESOLVED_INVALID": "Closure-scope resolved: `0`",
        "CLOSURE_BLOCKING_INVALID": "Closure-scope remaining blocking: `1,455`",
        "GOLDEN_TOTAL_INVALID": "Golden candidate total: `1,107`",
        "TAX_INVENTORY_INVALID": "Tax formula/rule inventory: `209`",
        "PARSER_INVENTORY_INVALID": "Parser/schema/ledger inventory: `57`",
        "PENSION_INVENTORY_INVALID": "Pension formula/coefficient/conversion inventory: `424`",
        "RAW_REM_06_TO_10_NECESSITY_MISSING": "RAW-REM-06..10 remain necessary unless a later scope decision changes them.",
    }
    for code, value in required_values.items():
        require_text(failures, plan, value, code, paths["plan"])

    for key, marker in {
        "checkpoint": "V2_REQ_12_RAW_REMEDIATION_PROGRESS_CHECKPOINT_PASS",
        "raw03": "RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION_PASS",
        "raw04": "RAW_REM_04_CLEARINGHOUSE_PARSER_BALANCE_LEDGER_VERIFICATION_PASS",
        "raw05": "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION_PASS",
    }.items():
        if marker not in texts[key]:
            add(failures, f"UPSTREAM_{key.upper()}_INVALID", "PASS marker present", "missing", paths[key])

    future_table = section(plan, "## 5. Future Package Table", "## 6. Recommended Closure Order")
    rows = table_rows(future_table, 11)
    package_counts = {package_id: sum(row[0] == package_id for row in rows) for package_id in PACKAGE_IDS}
    for package_id, count in package_counts.items():
        if count != 1:
            add(failures, "PACKAGE_TABLE_CARDINALITY", f"{package_id} exactly once", str(count), paths["plan"])
    unexpected = [row[0] for row in rows if row[0] not in PACKAGE_IDS]
    if unexpected:
        add(failures, "UNEXPECTED_PACKAGE_ID", "only required package IDs", ",".join(unexpected), paths["plan"])
    for row in rows:
        if row[10] != "NOT_STARTED":
            add(failures, "PACKAGE_STATUS_INVALID", f"{row[0]}=NOT_STARTED", row[10], paths["plan"])

    order_text = section(plan, "## 6. Recommended Closure Order", "## 7. Minimum Acceptance Criteria for Any Future Closure Package")
    actual_order = re.findall(r"^\d+\. `([^`]+)`\s*$", order_text, re.MULTILINE)
    if actual_order != list(RECOMMENDED_ORDER):
        add(failures, "RECOMMENDED_ORDER_INVALID", "exact 17-package order", ",".join(actual_order), paths["plan"])
    if not actual_order or actual_order[0] != RECOMMENDED_ORDER[0]:
        add(failures, "RECOMMENDED_FIRST_INVALID", RECOMMENDED_ORDER[0], actual_order[0] if actual_order else "missing", paths["plan"])
    if not actual_order or actual_order[-1] != RECOMMENDED_ORDER[-1]:
        add(failures, "RECOMMENDED_LAST_INVALID", RECOMMENDED_ORDER[-1], actual_order[-1] if actual_order else "missing", paths["plan"])

    forbidden_patterns = {
        "IMPLEMENTATION_RECOMMENDED": r"(?i)(?:recommend(?:ed|ation)?|next step)\s*:\s*(?:begin|start|proceed with|authorize)[^\n]{0,40}implementation",
        "02M_RECOMMENDED": r"(?i)(?:recommend(?:ed|ation)?|next step)\s*:\s*(?:proceed to|begin|start|unfreeze|authorize)[^\n]{0,20}02M",
        "PLANNING_COMPLETENESS_CLAIMED": r"(?i)full planning completeness\s*(?:is|:)\s*`?(?:PROVEN|PASS|COMPLETE)`?",
        "RAW_REM_06_TO_10_DECLARED_UNNECESSARY": r"(?i)RAW-REM-06\.\.10 (?:are|is) unnecessary",
        "CLOSURE_ALREADY_CLAIMED": r"(?i)closure has (?:already )?happened",
    }
    for code, pattern in forbidden_patterns.items():
        match = re.search(pattern, plan)
        if match:
            add(failures, code, "forbidden conclusion absent", match.group(0), paths["plan"])

    counts: dict[str, int | str] = {
        "closure_scope_items": 1455,
        "closure_resolved_items": 0,
        "closure_remaining_blocking": 1455,
        "golden_candidate_total": 1107,
        "closure_packages_defined": len(rows),
        "recommended_first": RECOMMENDED_ORDER[0],
        "recommended_last": RECOMMENDED_ORDER[-1],
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("V2_REQ_13_COVERAGE_CLOSURE_PLAN_VERIFICATION_FAIL")
        for failure in failures:
            print(
                f"failure_code={failure.code}; expected={failure.expected}; "
                f"actual={failure.actual}; source_file={failure.source_file}"
            )
        return 1
    print("V2_REQ_13_COVERAGE_CLOSURE_PLAN_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
