#!/usr/bin/env python3
"""Verify RAW-REM-05 pension/coefficient/annuity/capital-conversion mapping evidence."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


OUTCOMES = {
    "PENMAP_NEEDS_BEHAVIOR_CONTRACT",
    "PENMAP_NEEDS_FORMULA_RULE_CONTRACT",
    "PENMAP_NEEDS_COEFFICIENT_TABLE_CONTRACT",
    "PENMAP_NEEDS_ANNUITY_CONVERSION_CONTRACT",
    "PENMAP_NEEDS_CAPITAL_PENSION_CLASSIFICATION_CONTRACT",
    "PENMAP_NEEDS_MANUAL_OVERRIDE_CONTRACT",
    "PENMAP_NEEDS_VALIDATION_WARNING_CONTRACT",
    "PENMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
    "PENMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
    "PENMAP_NEEDS_REQ_MAPPING",
    "PENMAP_NEEDS_V1ITEM_LINK",
    "PENMAP_NEEDS_MANUAL_SOURCE_REVIEW",
    "PENMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON",
    "PENMAP_NOT_APPLICABLE_WITH_REASON",
    "PENMAP_OUT_OF_SCOPE_FOR_RAW_REM_05",
    "PENMAP_UNCLASSIFIED_FAIL",
}
RULE_OUTCOMES = {
    "PENMAP_NEEDS_BEHAVIOR_CONTRACT",
    "PENMAP_NEEDS_FORMULA_RULE_CONTRACT",
    "PENMAP_NEEDS_COEFFICIENT_TABLE_CONTRACT",
    "PENMAP_NEEDS_ANNUITY_CONVERSION_CONTRACT",
    "PENMAP_NEEDS_CAPITAL_PENSION_CLASSIFICATION_CONTRACT",
    "PENMAP_NEEDS_MANUAL_OVERRIDE_CONTRACT",
    "PENMAP_NEEDS_VALIDATION_WARNING_CONTRACT",
    "PENMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
    "PENMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
}
GOLDEN_OUTCOMES = {"PENMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT", "PENMAP_NEEDS_BEHAVIOR_AND_GOLDEN"}
MANUAL_OUTCOMES = {"PENMAP_NEEDS_MANUAL_OVERRIDE_CONTRACT"}
UNSUPPORTED_RE = re.compile(
    r"\bassumed\b|\bprobably\b|\bstandard coefficient\b|\bshould map to\b|"
    r"\btypical pension\b|\bexpected annuity\b",
    re.IGNORECASE,
)
FORBIDDEN_CLAIM_RE = re.compile(
    r"\bcovered\b|\bcomplete\b|\bparity proven\b|\bimplementation ready\b",
    re.IGNORECASE,
)
PASS_MARKER = "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING_PASS"
FAIL_MARKER = "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING_FAIL"
DECISIONS_MARKER = "RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS_CREATED"


@dataclass(frozen=True)
class Failure:
    code: str
    logic_id: str
    expected: str
    actual: str
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def parse_rows(text: str, width: int) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1LOGIC-\d{3,}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            rows.append(cells)
    return rows


def section_rows(text: str, heading: str, next_heading: str, width: int) -> list[list[str]]:
    match = re.search(
        rf"^{re.escape(heading)}\s*$.*?(?=^{re.escape(next_heading)}\s*$)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return parse_rows(match.group(0) if match else "", width)


def expand_scope(value: str) -> set[str]:
    result = set()
    for start, end in re.findall(r"V1LOGIC-(\d{3,})(?:\.\.V1LOGIC-(\d{3,}))?", value):
        result.update(f"V1LOGIC-{number:03d}" for number in range(int(start), int(end or start) + 1))
    return result


def package_scope(plan: str, package: str, next_package: str) -> tuple[int, set[str]]:
    section = re.search(
        rf"^### {re.escape(package)} .*?(?=^### {re.escape(next_package)} )",
        plan,
        re.MULTILINE | re.DOTALL,
    )
    match = re.search(r"Target V1LOGIC scope \(([\d,]+) rows\): `([^`]+)`", section.group(0) if section else "")
    if not match:
        return 0, set()
    return int(match.group(1).replace(",", "")), expand_scope(match.group(2))


def add(failures, code, logic_id, expected, actual, source):
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def verify(repo_root: Path):
    paths = {
        "inventory": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md",
        "audit": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md",
        "plan": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md",
        "mapping": repo_root / "specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_MAPPING.md",
        "decisions": repo_root / "specs/runtime/raw_remediation/RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_DECISIONS.md",
    }
    failures = []
    try:
        text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    except OSError as exc:
        add(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), repo_root)
        return failures, {}

    declared, scope = package_scope(text["plan"], "RAW-REM-05", "RAW-REM-06")
    _, scope_01 = package_scope(text["plan"], "RAW-REM-01", "RAW-REM-02")
    _, scope_02 = package_scope(text["plan"], "RAW-REM-02", "RAW-REM-03")
    _, scope_03 = package_scope(text["plan"], "RAW-REM-03", "RAW-REM-04")
    _, scope_04 = package_scope(text["plan"], "RAW-REM-04", "RAW-REM-05")
    if declared != 424 or len(scope) != 424:
        add(failures, "RAW_REM_05_SCOPE_COUNT_INVALID", "", "424 unique IDs", f"declared={declared}; parsed={len(scope)}", paths["plan"])

    inventory_rows = parse_rows(text["inventory"], 22)
    audit_rows = parse_rows(text["audit"], 13)
    mapping_rows = section_rows(text["mapping"], "## 5. Decision Table", "## 6. Summary by Mapping Outcome", 15)
    rule_rows = section_rows(text["mapping"], "## 8. Formula / Coefficient / Conversion Rule Inventory", "## 9. Golden Expected-Output Candidate Inventory", 9)
    golden_rows = section_rows(text["mapping"], "## 9. Golden Expected-Output Candidate Inventory", "## 10. Manual Override / Planner Assumption Inventory", 7)
    manual_rows = section_rows(text["mapping"], "## 10. Manual Override / Planner Assumption Inventory", "## 11. Out-of-Scope Routing", 7)
    decision_rows = parse_rows(text["decisions"], 7)
    inventory = {row[0]: row for row in inventory_rows}
    audit = {row[0]: row for row in audit_rows}

    uncertain = {row[0] for row in audit_rows if row[9] == "V1LOGIC_SOURCE_UNCERTAIN_FAIL"}
    uncovered_count = sum(row[9] == "V1LOGIC_UNCOVERED_FAIL" for row in audit_rows)
    if len(uncertain) != 234:
        add(failures, "SOURCE_UNCERTAIN_BASELINE_CHANGED", "", "234", str(len(uncertain)), paths["audit"])
    if uncovered_count != 6457:
        add(failures, "UNCOVERED_BASELINE_CHANGED", "", "6457", str(uncovered_count), paths["audit"])
    if text["audit"].count("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_FAIL") != 1 or text["audit"].count("V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT_PASS") != 0:
        add(failures, "ORIGINAL_AUDIT_MARKER_CHANGED", "", "one FAIL and zero PASS markers", "marker mismatch", paths["audit"])

    mapped: dict[str, list[list[str]]] = {}
    decided: dict[str, list[list[str]]] = {}
    for row in mapping_rows:
        mapped.setdefault(row[0], []).append(row)
    for row in decision_rows:
        decided.setdefault(row[0], []).append(row)
    for logic_id in sorted(scope):
        if len(mapped.get(logic_id, [])) != 1:
            add(failures, "MAPPING_CARDINALITY", logic_id, "exactly one row", str(len(mapped.get(logic_id, []))), paths["mapping"])
        if len(decided.get(logic_id, [])) != 1:
            add(failures, "DECISION_CARDINALITY", logic_id, "exactly one row", str(len(decided.get(logic_id, []))), paths["decisions"])
    for logic_id in sorted(set(decided) - scope):
        if logic_id in scope_01:
            code = "RAW_REM_01_ID_IN_DECISIONS"
        elif logic_id in scope_02 or logic_id in scope_03 or logic_id in scope_04:
            code = "RAW_REM_02_03_OR_04_ONLY_ID_IN_DECISIONS"
        else:
            code = "OUT_OF_SCOPE_DECISION"
        add(failures, code, logic_id, "RAW-REM-05 scope ID", "out-of-scope ID", paths["decisions"])

    for row in mapping_rows:
        logic_id, outcome, reason, next_package, blocks = row[0], row[6], row[11], row[12], row[13]
        if logic_id not in scope:
            add(failures, "OUT_OF_SCOPE_MAPPING", logic_id, "RAW-REM-05 scope ID", logic_id, paths["mapping"])
        if logic_id not in inventory:
            add(failures, "UNKNOWN_INVENTORY_ID", logic_id, "existing inventory ID", logic_id, paths["inventory"])
        if logic_id not in audit or audit[logic_id][9] != "V1LOGIC_UNCOVERED_FAIL":
            add(failures, "TARGET_NOT_ORIGINAL_UNCOVERED", logic_id, "original uncovered row", audit.get(logic_id, ["missing"])[-1], paths["audit"])
        if outcome not in OUTCOMES:
            add(failures, "INVALID_MAPPING_OUTCOME", logic_id, "allowed outcome", outcome, paths["mapping"])
        if not row[3] or not row[4]:
            add(failures, "SOURCE_EVIDENCE_EMPTY", logic_id, "source reference and checked evidence", "empty", paths["mapping"])
        if not reason:
            add(failures, "DECISION_REASON_EMPTY", logic_id, "non-empty source-grounded reason", "empty", paths["mapping"])
        if blocks not in {"YES", "NO"}:
            add(failures, "INVALID_BLOCKS_VALUE", logic_id, "YES or NO", blocks, paths["mapping"])
        if outcome.startswith("PENMAP_NEEDS_") and blocks != "YES":
            add(failures, "NEEDS_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["mapping"])
        if outcome == "PENMAP_UNCLASSIFIED_FAIL":
            add(failures, "UNCLASSIFIED_IN_PASS_PACKAGE", logic_id, "classified outcome", outcome, paths["mapping"])
        if outcome == "PENMAP_OUT_OF_SCOPE_FOR_RAW_REM_05" and not re.fullmatch(r"RAW-REM-(?:0[6-9]|10)", next_package):
            add(failures, "OUT_OF_SCOPE_TARGET_MISSING", logic_id, "RAW-REM-06..RAW-REM-10", next_package or "empty", paths["mapping"])
        if outcome == "PENMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON" and (not reason or blocks != "YES"):
            add(failures, "INTENTIONAL_CHANGE_UNSAFE", logic_id, "explicit reason and YES", f"reason={bool(reason)}; blocks={blocks}", paths["mapping"])
        if outcome in {"PENMAP_NOT_APPLICABLE_WITH_REASON", "PENMAP_OUT_OF_SCOPE_FOR_RAW_REM_05"} and "V1 archive" not in reason:
            add(failures, "HIGH_RISK_CLOSURE_WITHOUT_SOURCE_REASON", logic_id, "explicit V1 archive reason", reason, paths["mapping"])
        checked = " ".join((row[7], row[11], row[14]))
        if UNSUPPORTED_RE.search(checked):
            add(failures, "UNSUPPORTED_COEFFICIENT_LANGUAGE", logic_id, "source-grounded language", checked, paths["mapping"])
        if FORBIDDEN_CLAIM_RE.search(checked):
            add(failures, "FORBIDDEN_HIGH_RISK_CLAIM", logic_id, "no closure/readiness claim", checked, paths["mapping"])

    for row in decision_rows:
        logic_id, subdomain, outcome, blocks, artifact, next_package, reason = row
        if outcome not in OUTCOMES:
            add(failures, "INVALID_DECISION_OUTCOME", logic_id, "allowed outcome", outcome, paths["decisions"])
        if not reason:
            add(failures, "DECISION_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["decisions"])
        if outcome.startswith("PENMAP_NEEDS_") and blocks != "YES":
            add(failures, "DECISION_NEEDS_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["decisions"])
        if outcome == "PENMAP_UNCLASSIFIED_FAIL":
            add(failures, "DECISION_UNCLASSIFIED_IN_PASS_PACKAGE", logic_id, "classified outcome", outcome, paths["decisions"])
        if UNSUPPORTED_RE.search(reason):
            add(failures, "UNSUPPORTED_COEFFICIENT_LANGUAGE", logic_id, "source-grounded language", reason, paths["decisions"])
        source = mapped.get(logic_id, [])
        if len(source) == 1:
            expected = (source[0][5], source[0][6], source[0][13], source[0][7], source[0][12], source[0][11])
            if (subdomain, outcome, blocks, artifact, next_package, reason) != expected:
                add(failures, "MAPPING_DECISION_MISMATCH", logic_id, "matching mapping values", "values differ", paths["decisions"])

    expected_rule_ids = {row[0] for row in mapping_rows if row[6] in RULE_OUTCOMES}
    rule_index = {row[0]: row for row in rule_rows}
    for logic_id in sorted(expected_rule_ids - set(rule_index)):
        add(failures, "COEFFICIENT_CONVERSION_INVENTORY_MISSING", logic_id, "formula/coefficient/conversion inventory row", "missing", paths["mapping"])
    for row in rule_rows:
        if row[0] in scope and (not row[2] or not row[3] or not row[4] or not row[5] or not row[6]):
            add(failures, "COEFFICIENT_CONVERSION_REQUIRED_FIELD_EMPTY", row[0], "non-empty source/rule/inputs/outputs/contract", "empty", paths["mapping"])
        if UNSUPPORTED_RE.search(" ".join((row[6], row[8]))):
            add(failures, "UNSUPPORTED_COEFFICIENT_LANGUAGE", row[0], "source-grounded language", "unsupported phrase", paths["mapping"])

    golden_index = {row[0]: row for row in golden_rows}
    expected_golden_ids = {row[0] for row in mapping_rows if row[6] in GOLDEN_OUTCOMES}
    for logic_id in sorted(expected_golden_ids - set(golden_index)):
        add(failures, "GOLDEN_CANDIDATE_MISSING", logic_id, "golden candidate row", "missing", paths["mapping"])
    for row in golden_rows:
        if row[0] in scope and (not row[2] or not row[3] or "@L" not in row[3]):
            add(failures, "GOLDEN_EXPECTED_OUTPUT_SOURCE_INVALID", row[0], "source reference containing @L", row[3] or "empty", paths["mapping"])

    manual_index = {row[0]: row for row in manual_rows}
    expected_manual_ids = {row[0] for row in mapping_rows if row[6] in MANUAL_OUTCOMES}
    for logic_id in sorted(expected_manual_ids - set(manual_index)):
        add(failures, "MANUAL_OVERRIDE_INVENTORY_MISSING", logic_id, "manual override/planner assumption row", "missing", paths["mapping"])

    if text["mapping"].count(PASS_MARKER) != 1 or text["mapping"].count(FAIL_MARKER) != 0:
        add(failures, "INVALID_MAPPING_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={text['mapping'].count(PASS_MARKER)}; FAIL={text['mapping'].count(FAIL_MARKER)}", paths["mapping"])
    if text["decisions"].count(DECISIONS_MARKER) != 1:
        add(failures, "INVALID_DECISIONS_MARKER", "", "exactly one decisions marker", str(text["decisions"].count(DECISIONS_MARKER)), paths["decisions"])

    counts_by_outcome = Counter(row[2] for row in decision_rows if row[0] in scope)
    key_map = {
        "needs_behavior_contract": "PENMAP_NEEDS_BEHAVIOR_CONTRACT",
        "needs_formula_rule_contract": "PENMAP_NEEDS_FORMULA_RULE_CONTRACT",
        "needs_coefficient_table_contract": "PENMAP_NEEDS_COEFFICIENT_TABLE_CONTRACT",
        "needs_annuity_conversion_contract": "PENMAP_NEEDS_ANNUITY_CONVERSION_CONTRACT",
        "needs_capital_pension_classification_contract": "PENMAP_NEEDS_CAPITAL_PENSION_CLASSIFICATION_CONTRACT",
        "needs_manual_override_contract": "PENMAP_NEEDS_MANUAL_OVERRIDE_CONTRACT",
        "needs_validation_warning_contract": "PENMAP_NEEDS_VALIDATION_WARNING_CONTRACT",
        "needs_golden_expected_output": "PENMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
        "needs_behavior_and_golden": "PENMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
        "needs_req_mapping": "PENMAP_NEEDS_REQ_MAPPING",
        "needs_v1item_link": "PENMAP_NEEDS_V1ITEM_LINK",
        "needs_manual_source_review": "PENMAP_NEEDS_MANUAL_SOURCE_REVIEW",
        "intentional_change_candidate": "PENMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON",
        "not_applicable": "PENMAP_NOT_APPLICABLE_WITH_REASON",
        "out_of_scope_for_raw_rem_05": "PENMAP_OUT_OF_SCOPE_FOR_RAW_REM_05",
    }
    counts = {"raw_rem_05_items_checked": len(scope)}
    counts.update({key: counts_by_outcome[outcome] for key, outcome in key_map.items()})
    counts["remaining_blocking"] = sum(row[3] == "YES" for row in decision_rows if row[0] in scope)
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("RAW_REM_05_PENSION_COEFFICIENT_ANNUITY_CAPITAL_CONVERSION_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
