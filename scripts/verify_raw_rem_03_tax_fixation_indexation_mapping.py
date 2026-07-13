#!/usr/bin/env python3
"""Verify the RAW-REM-03 tax/fixation/indexation mapping package."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


OUTCOMES = {
    "TAXMAP_NEEDS_BEHAVIOR_CONTRACT",
    "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT",
    "TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
    "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
    "TAXMAP_NEEDS_REQ_MAPPING",
    "TAXMAP_NEEDS_V1ITEM_LINK",
    "TAXMAP_NEEDS_DOMAIN_DECISION",
    "TAXMAP_NEEDS_MANUAL_SOURCE_REVIEW",
    "TAXMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON",
    "TAXMAP_NOT_APPLICABLE_WITH_REASON",
    "TAXMAP_OUT_OF_SCOPE_FOR_RAW_REM_03",
    "TAXMAP_UNCLASSIFIED_FAIL",
}
FORMULA_TYPES = {
    "V1LOGIC_CONSTANT",
    "V1LOGIC_FORMULA",
    "V1LOGIC_INDEXATION_CPI",
    "V1LOGIC_RETIREMENT_AGE_RULE",
    "V1LOGIC_SCENARIO_CASHFLOW_RULE",
    "V1LOGIC_TAX_PARAMETER",
}
UNSUPPORTED_RE = re.compile(
    r"\bassumed\b|\bprobably\b|\bstandard tax rule\b|\bby law generally\b",
    re.IGNORECASE,
)
FORBIDDEN_CLAIM_RE = re.compile(
    r"\bcovered\b|\bcomplete\b|\bparity proven\b|\bimplementation ready\b",
    re.IGNORECASE,
)
PASS_MARKER = "RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_MAPPING_PASS"
FAIL_MARKER = "RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_MAPPING_FAIL"
DECISIONS_MARKER = "RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS_CREATED"


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
    scope_match = re.search(
        r"Target V1LOGIC scope \(([\d,]+) rows\): `([^`]+)`",
        section.group(0) if section else "",
    )
    if not scope_match:
        return 0, set()
    return int(scope_match.group(1).replace(",", "")), expand_scope(scope_match.group(2))


def add(failures, code, logic_id, expected, actual, source):
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def verify(repo_root: Path):
    paths = {
        "inventory": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md",
        "audit": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md",
        "plan": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md",
        "mapping": repo_root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_MAPPING.md",
        "decisions": repo_root / "specs/runtime/raw_remediation/RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_DECISIONS.md",
    }
    failures = []
    try:
        text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    except OSError as exc:
        add(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), repo_root)
        return failures, {}

    declared, scope = package_scope(text["plan"], "RAW-REM-03", "RAW-REM-04")
    _, scope_01 = package_scope(text["plan"], "RAW-REM-01", "RAW-REM-02")
    _, scope_02 = package_scope(text["plan"], "RAW-REM-02", "RAW-REM-03")
    if declared != 927 or len(scope) != 927:
        add(failures, "RAW_REM_03_SCOPE_COUNT_INVALID", "", "927 unique IDs", f"declared={declared}; parsed={len(scope)}", paths["plan"])

    inventory_rows = parse_rows(text["inventory"], 22)
    audit_rows = parse_rows(text["audit"], 13)
    mapping_rows = section_rows(text["mapping"], "## 5. Decision Table", "## 6. Summary by Mapping Outcome", 15)
    formula_rows = section_rows(text["mapping"], "## 8. Formula/Rule Inventory", "## 9. Golden Expected-Output Candidate Inventory", 9)
    golden_rows = section_rows(text["mapping"], "## 9. Golden Expected-Output Candidate Inventory", "## 10. Domain Decision Inventory", 7)
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
        elif logic_id in scope_02:
            code = "RAW_REM_02_ONLY_ID_IN_DECISIONS"
        else:
            code = "OUT_OF_SCOPE_DECISION"
        add(failures, code, logic_id, "RAW-REM-03 scope ID", "out-of-scope ID", paths["decisions"])

    for row in mapping_rows:
        logic_id, outcome, reason, next_package, blocks = row[0], row[6], row[11], row[12], row[13]
        if logic_id not in scope:
            add(failures, "OUT_OF_SCOPE_MAPPING", logic_id, "RAW-REM-03 scope ID", logic_id, paths["mapping"])
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
        if outcome.startswith("TAXMAP_NEEDS_") and blocks != "YES":
            add(failures, "NEEDS_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["mapping"])
        if outcome == "TAXMAP_UNCLASSIFIED_FAIL":
            add(failures, "UNCLASSIFIED_IN_PASS_PACKAGE", logic_id, "classified outcome", outcome, paths["mapping"])
        if outcome == "TAXMAP_OUT_OF_SCOPE_FOR_RAW_REM_03" and not re.fullmatch(r"RAW-REM-(?:0[4-9]|10)", next_package):
            add(failures, "OUT_OF_SCOPE_TARGET_MISSING", logic_id, "RAW-REM-04..RAW-REM-10", next_package or "empty", paths["mapping"])
        if outcome == "TAXMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON" and (not reason or blocks != "YES"):
            add(failures, "INTENTIONAL_CHANGE_UNSAFE", logic_id, "explicit reason and YES", f"reason={bool(reason)}; blocks={blocks}", paths["mapping"])
        if outcome in {"TAXMAP_NOT_APPLICABLE_WITH_REASON", "TAXMAP_OUT_OF_SCOPE_FOR_RAW_REM_03"} and "V1 archive" not in reason:
            add(failures, "HIGH_RISK_CLOSURE_WITHOUT_SOURCE_REASON", logic_id, "explicit V1 archive reason", reason, paths["mapping"])
        checked_text = " ".join((row[7], row[11], row[14]))
        if UNSUPPORTED_RE.search(checked_text):
            add(failures, "UNSUPPORTED_FORMULA_LANGUAGE", logic_id, "source-grounded language", checked_text, paths["mapping"])
        if FORBIDDEN_CLAIM_RE.search(checked_text):
            add(failures, "FORBIDDEN_HIGH_RISK_CLAIM", logic_id, "no closure/readiness claim", checked_text, paths["mapping"])

    for row in decision_rows:
        logic_id, subdomain, outcome, blocks, artifact, next_package, reason = row
        if outcome not in OUTCOMES:
            add(failures, "INVALID_DECISION_OUTCOME", logic_id, "allowed outcome", outcome, paths["decisions"])
        if not reason:
            add(failures, "DECISION_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["decisions"])
        if outcome.startswith("TAXMAP_NEEDS_") and blocks != "YES":
            add(failures, "DECISION_NEEDS_OUTCOME_NOT_BLOCKING", logic_id, "YES", blocks, paths["decisions"])
        if outcome == "TAXMAP_UNCLASSIFIED_FAIL":
            add(failures, "DECISION_UNCLASSIFIED_IN_PASS_PACKAGE", logic_id, "classified outcome", outcome, paths["decisions"])
        if UNSUPPORTED_RE.search(reason):
            add(failures, "UNSUPPORTED_FORMULA_LANGUAGE", logic_id, "source-grounded language", reason, paths["decisions"])
        source = mapped.get(logic_id, [])
        if len(source) == 1:
            expected = (source[0][5], source[0][6], source[0][13], source[0][7], source[0][12], source[0][11])
            if (subdomain, outcome, blocks, artifact, next_package, reason) != expected:
                add(failures, "MAPPING_DECISION_MISMATCH", logic_id, "matching mapping values", "values differ", paths["decisions"])

    formula_ids = {logic_id for logic_id in scope if inventory.get(logic_id, ["", "", ""])[2] in FORMULA_TYPES}
    formula_index = {row[0]: row for row in formula_rows}
    for logic_id in sorted(formula_ids - set(formula_index)):
        add(failures, "FORMULA_INVENTORY_MISSING", logic_id, "formula/rule inventory row", "missing", paths["mapping"])
    for row in formula_rows:
        if row[0] in scope and (not row[2] or not row[3] or not row[4] or not row[5] or not row[6]):
            add(failures, "FORMULA_REQUIRED_FIELD_EMPTY", row[0], "non-empty source/formula/inputs/outputs/contract", "empty", paths["mapping"])
        if UNSUPPORTED_RE.search(" ".join((row[6], row[8]))):
            add(failures, "UNSUPPORTED_FORMULA_LANGUAGE", row[0], "source-grounded language", "unsupported phrase", paths["mapping"])

    golden_index = {row[0]: row for row in golden_rows}
    golden_required = {row[0] for row in mapping_rows if row[6] in {"TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT", "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN"}}
    for logic_id in sorted(golden_required - set(golden_index)):
        add(failures, "GOLDEN_CANDIDATE_MISSING", logic_id, "golden candidate row", "missing", paths["mapping"])
    for row in golden_rows:
        if row[0] in scope and (not row[2] or not row[3] or "@L" not in row[3]):
            add(failures, "GOLDEN_EXPECTED_OUTPUT_SOURCE_INVALID", row[0], "non-empty source reference containing @L", row[3] or "empty", paths["mapping"])

    if text["mapping"].count(PASS_MARKER) != 1 or text["mapping"].count(FAIL_MARKER) != 0:
        add(failures, "INVALID_MAPPING_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={text['mapping'].count(PASS_MARKER)}; FAIL={text['mapping'].count(FAIL_MARKER)}", paths["mapping"])
    if text["decisions"].count(DECISIONS_MARKER) != 1:
        add(failures, "INVALID_DECISIONS_MARKER", "", "exactly one decisions marker", str(text["decisions"].count(DECISIONS_MARKER)), paths["decisions"])

    counts_by_outcome = Counter(row[2] for row in decision_rows if row[0] in scope)
    keys = {
        "needs_behavior_contract": "TAXMAP_NEEDS_BEHAVIOR_CONTRACT",
        "needs_formula_rule_contract": "TAXMAP_NEEDS_FORMULA_RULE_CONTRACT",
        "needs_golden_expected_output": "TAXMAP_NEEDS_GOLDEN_EXPECTED_OUTPUT",
        "needs_behavior_and_golden": "TAXMAP_NEEDS_BEHAVIOR_AND_GOLDEN",
        "needs_req_mapping": "TAXMAP_NEEDS_REQ_MAPPING",
        "needs_v1item_link": "TAXMAP_NEEDS_V1ITEM_LINK",
        "needs_domain_decision": "TAXMAP_NEEDS_DOMAIN_DECISION",
        "needs_manual_source_review": "TAXMAP_NEEDS_MANUAL_SOURCE_REVIEW",
        "intentional_change_candidate": "TAXMAP_INTENTIONAL_CHANGE_CANDIDATE_WITH_REASON",
        "not_applicable": "TAXMAP_NOT_APPLICABLE_WITH_REASON",
        "out_of_scope_for_raw_rem_03": "TAXMAP_OUT_OF_SCOPE_FOR_RAW_REM_03",
    }
    counts = {"raw_rem_03_items_checked": len(scope)}
    counts.update({key: counts_by_outcome[outcome] for key, outcome in keys.items()})
    counts["remaining_blocking"] = sum(row[3] == "YES" for row in decision_rows if row[0] in scope)
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("RAW_REM_03_HIGH_RISK_TAX_FIXATION_INDEXATION_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
