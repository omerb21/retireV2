#!/usr/bin/env python3
"""Verify RAW-REM-02 false-positive/trivial-logic classifications."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


OUTCOMES = {
    "RAWLOGIC_FALSE_POSITIVE_WITH_REASON",
    "RAWLOGIC_TRIVIAL_CRUD_OR_TRANSPORT_WITH_REASON",
    "RAWLOGIC_DUPLICATE_OR_GENERATED_WITH_REASON",
    "RAWLOGIC_REAL_REQUIRES_MAPPING",
    "RAWLOGIC_NOT_APPLICABLE_WITH_REASON",
    "RAWLOGIC_CLASSIFICATION_UNCERTAIN_BLOCKED",
}
SAFE_CLASSIFICATIONS = {
    "RAWLOGIC_FALSE_POSITIVE_WITH_REASON",
    "RAWLOGIC_TRIVIAL_CRUD_OR_TRANSPORT_WITH_REASON",
    "RAWLOGIC_DUPLICATE_OR_GENERATED_WITH_REASON",
    "RAWLOGIC_NOT_APPLICABLE_WITH_REASON",
}
HIGH_RISK_RE = re.compile(
    r"tax|fixation|161d|indexation|\bcpi\b|\bcbs\b|\blmas\b|clearinghouse|"
    r"balance.?ledger|pension.?coefficient|annuity|scenario|cashflow|report|\bpdf\b|"
    r"validation|warning|error",
    re.IGNORECASE,
)
SAFE_REASON_RE = re.compile(r"non-business|non-independent|generated|duplicate|transport-only", re.IGNORECASE)
PASS_MARKER = "RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION_PASS"
FAIL_MARKER = "RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION_FAIL"
DECISIONS_MARKER = "RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_DECISIONS_CREATED"


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
    result = []
    for line in text.splitlines():
        if not re.match(r"^\|\s*V1LOGIC-\d{3,}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == width:
            result.append(cells)
    return result


def expand_scope(value: str) -> set[str]:
    result = set()
    for start, end in re.findall(r"V1LOGIC-(\d{3,})(?:\.\.V1LOGIC-(\d{3,}))?", value):
        result.update(f"V1LOGIC-{number:03d}" for number in range(int(start), int(end or start) + 1))
    return result


def add(failures, code, logic_id, expected, actual, source):
    failures.append(Failure(code, logic_id or "not_applicable", expected, actual, str(source)))


def verify(repo_root: Path):
    paths = {
        "inventory": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_INVENTORY.md",
        "audit": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_COVERAGE_AUDIT.md",
        "plan": repo_root / "specs/runtime/V1_SOURCE_RAW_LOGIC_REMEDIATION_PLAN.md",
        "classification": repo_root / "specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_CLASSIFICATION.md",
        "decisions": repo_root / "specs/runtime/raw_remediation/RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_DECISIONS.md",
    }
    failures = []
    try:
        text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    except OSError as exc:
        add(failures, "REQUIRED_FILE_READ_ERROR", "", "all required files readable", str(exc), repo_root)
        return failures, {}

    section = re.search(r"^### RAW-REM-02 .*?(?=^### RAW-REM-03 )", text["plan"], re.MULTILINE | re.DOTALL)
    scope_match = re.search(r"Target V1LOGIC scope \((\d+) rows\): `([^`]+)`", section.group(0) if section else "")
    if not scope_match:
        add(failures, "RAW_REM_02_SCOPE_UNPARSEABLE", "", "committed RAW-REM-02 scope", "missing", paths["plan"])
        scope = set()
    else:
        scope = expand_scope(scope_match.group(2))
        if int(scope_match.group(1)) != 732 or len(scope) != 732:
            add(failures, "RAW_REM_02_SCOPE_COUNT_INVALID", "", "732 unique IDs", f"declared={scope_match.group(1)}; parsed={len(scope)}", paths["plan"])

    inventory_rows = parse_rows(text["inventory"], 22)
    audit_rows = parse_rows(text["audit"], 13)
    classification_rows = parse_rows(text["classification"], 13)
    decision_rows = parse_rows(text["decisions"], 5)
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

    classified: dict[str, list[list[str]]] = {}
    decided: dict[str, list[list[str]]] = {}
    for row in classification_rows:
        classified.setdefault(row[0], []).append(row)
    for row in decision_rows:
        decided.setdefault(row[0], []).append(row)
    for logic_id in sorted(scope):
        if len(classified.get(logic_id, [])) != 1:
            add(failures, "CLASSIFICATION_CARDINALITY", logic_id, "exactly one row", str(len(classified.get(logic_id, []))), paths["classification"])
        if len(decided.get(logic_id, [])) != 1:
            add(failures, "DECISION_CARDINALITY", logic_id, "exactly one row", str(len(decided.get(logic_id, []))), paths["decisions"])
    for logic_id in sorted(set(decided) - scope):
        code = "SOURCE_UNCERTAIN_ID_IN_DECISIONS" if logic_id in uncertain else "OUT_OF_SCOPE_DECISION"
        add(failures, code, logic_id, "RAW-REM-02 scope ID", "out-of-scope ID", paths["decisions"])

    for row in classification_rows:
        logic_id, outcome, reason, package, blocks = row[0], row[6], row[7], row[10], row[11]
        if logic_id not in scope:
            add(failures, "OUT_OF_SCOPE_CLASSIFICATION", logic_id, "RAW-REM-02 scope ID", logic_id, paths["classification"])
        if logic_id not in inventory:
            add(failures, "UNKNOWN_INVENTORY_ID", logic_id, "existing inventory ID", logic_id, paths["inventory"])
        if logic_id not in audit or audit[logic_id][9] != "V1LOGIC_UNCOVERED_FAIL":
            add(failures, "TARGET_NOT_ORIGINAL_UNCOVERED", logic_id, "original uncovered row", audit.get(logic_id, ["missing"])[-1], paths["audit"])
        if outcome not in OUTCOMES:
            add(failures, "INVALID_CLASSIFICATION_OUTCOME", logic_id, "allowed outcome", outcome, paths["classification"])
        if not row[5].strip():
            add(failures, "SOURCE_EVIDENCE_EMPTY", logic_id, "non-empty source evidence", "empty", paths["classification"])
        if not reason.strip():
            add(failures, "CLASSIFICATION_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["classification"])
        if blocks not in {"YES", "NO"}:
            add(failures, "INVALID_BLOCKS_VALUE", logic_id, "YES or NO", blocks, paths["classification"])
        if outcome == "RAWLOGIC_REAL_REQUIRES_MAPPING" and not re.fullmatch(r"RAW-REM-(?:0[3-9]|10)", package):
            add(failures, "REAL_MAPPING_PACKAGE_INVALID", logic_id, "RAW-REM-03..RAW-REM-10", package or "empty", paths["classification"])
        if outcome == "RAWLOGIC_CLASSIFICATION_UNCERTAIN_BLOCKED" and blocks != "YES":
            add(failures, "UNCERTAIN_CLASSIFICATION_NOT_BLOCKING", logic_id, "YES", blocks, paths["classification"])
        inv = inventory.get(logic_id)
        risk_text = " ".join((inv[1], inv[2], inv[3], inv[6], inv[9], inv[13])) if inv else ""
        if outcome in SAFE_CLASSIFICATIONS and HIGH_RISK_RE.search(risk_text) and not SAFE_REASON_RE.search(reason):
            add(failures, "HIGH_RISK_UNSAFE_CLASSIFICATION", logic_id, "explicit non-business/non-independent/generated/duplicate/transport-only reason", reason, paths["classification"])

    for row in decision_rows:
        logic_id, outcome, blocks, package, reason = row
        if outcome not in OUTCOMES:
            add(failures, "INVALID_DECISION_OUTCOME", logic_id, "allowed outcome", outcome, paths["decisions"])
        if not reason.strip():
            add(failures, "DECISION_REASON_EMPTY", logic_id, "non-empty reason", "empty", paths["decisions"])
        if outcome == "RAWLOGIC_REAL_REQUIRES_MAPPING" and not re.fullmatch(r"RAW-REM-(?:0[3-9]|10)", package):
            add(failures, "DECISION_REAL_MAPPING_PACKAGE_INVALID", logic_id, "RAW-REM-03..RAW-REM-10", package or "empty", paths["decisions"])
        if outcome == "RAWLOGIC_CLASSIFICATION_UNCERTAIN_BLOCKED" and blocks != "YES":
            add(failures, "DECISION_UNCERTAIN_NOT_BLOCKING", logic_id, "YES", blocks, paths["decisions"])
        source = classified.get(logic_id, [])
        if len(source) == 1 and (outcome, blocks, package, reason) != (source[0][6], source[0][11], source[0][10], source[0][7]):
            add(failures, "CLASSIFICATION_DECISION_MISMATCH", logic_id, "matching outcome/blocks/package/reason", "values differ", paths["decisions"])

    if text["classification"].count(PASS_MARKER) != 1 or text["classification"].count(FAIL_MARKER) != 0:
        add(failures, "INVALID_CLASSIFICATION_FINAL_MARKER", "", "one PASS and zero FAIL markers", f"PASS={text['classification'].count(PASS_MARKER)}; FAIL={text['classification'].count(FAIL_MARKER)}", paths["classification"])
    if text["decisions"].count(DECISIONS_MARKER) != 1:
        add(failures, "INVALID_DECISIONS_MARKER", "", "exactly one decisions marker", str(text["decisions"].count(DECISIONS_MARKER)), paths["decisions"])

    counts_by_outcome = Counter(row[1] for row in decision_rows if row[0] in scope)
    counts = {
        "raw_rem_02_items_checked": len(scope),
        "false_positive": counts_by_outcome["RAWLOGIC_FALSE_POSITIVE_WITH_REASON"],
        "trivial_crud_or_transport": counts_by_outcome["RAWLOGIC_TRIVIAL_CRUD_OR_TRANSPORT_WITH_REASON"],
        "duplicate_or_generated": counts_by_outcome["RAWLOGIC_DUPLICATE_OR_GENERATED_WITH_REASON"],
        "real_requires_mapping": counts_by_outcome["RAWLOGIC_REAL_REQUIRES_MAPPING"],
        "not_applicable": counts_by_outcome["RAWLOGIC_NOT_APPLICABLE_WITH_REASON"],
        "classification_uncertain_blocked": counts_by_outcome["RAWLOGIC_CLASSIFICATION_UNCERTAIN_BLOCKED"],
        "remaining_blocking": sum(row[2] == "YES" for row in decision_rows if row[0] in scope),
    }
    return failures, counts


def main() -> int:
    failures, counts = verify(parse_args().repo_root.resolve())
    if failures:
        print("RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_VERIFICATION_FAIL")
        for failure in failures:
            print(f"failure_code={failure.code}; V1_Logic_ID={failure.logic_id}; expected={failure.expected}; actual={failure.actual}; source_file={failure.source_file}")
        return 1
    print("RAW_REM_02_FALSE_POSITIVE_TRIVIAL_LOGIC_VERIFICATION_PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
